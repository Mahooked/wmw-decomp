"""shape_ctor_calls.py -- turn Ghidra's static-form constructor/destructor
calls into real C++, and bind the object parameter of constructor
definitions to `this`.

Ghidra decompiles a constructor call as a static function call,

    WaterConcept::WCScreen::WCScreen(this, 5);

which clang parses as a constructor *name* in expression position and rejects
(``qualified reference to 'WCScreen' is a constructor name rather than a
type``).  Same story for destructor calls (``Walaber::Widget::~Widget(p)``).
This pass rewrites, on indented (call-site) lines only:

    QUAL::Cls(obj, a, b)  ->  new ((void *)(obj)) QUAL::Cls(a, b)
    QUAL::~Cls(obj)       ->  ((QUAL::Cls *)obj)->~Cls()

and on definitions:

  * constructor definitions: when the definition carries exactly one more
    parameter than the Itanium demangled signature in out/src/_index.tsv
    (Ghidra bound the object register as `param_1` / `p0` / `in_x0`), the
    first parameter is dropped and body uses are bound to `this`, so the
    definition matches the placement-new call sites;
  * destructor definitions: their parameters were stripped earlier, so
    dangling `param_1` / `p0` body uses (the object) are bound to `this`.

Template-qualified destructor calls are rewritten too, keeping the template
arguments on both sides (`Walaber::SharedPtr<X>::~SharedPtr(p)` ->
`((Walaber::SharedPtr<X> *)p)->~SharedPtr<X>()`), because clang only
recognises the identifier after `~` as a destructor name when it names a
*type* -- a bare template name is rejected.  Template-qualified constructor
calls are still skipped, as are calls whose parentheses do not close on the
same line, zero-argument calls (no object to place), and destructor calls
with an arity other than 1.

Usage:
    py tools/shape_ctor_calls.py            # apply, print stats
    py tools/shape_ctor_calls.py --check    # exit 1 if any file would change
"""

import argparse
import os
import re
import sys
from collections import Counter

MARKER = re.compile(r'/\*[^*]*?address\s+(0x[0-9a-fA-F]+)\s+size\s+\d+\s*\*/')

# Definition signature: must start at column 0 with an identifier, so
# indented call sites never match.  Group 1 = qualified name (greedy, so a
# regular member `A::B::setLayer` yields qualifier `A::B` != name and is
# not mistaken for a constructor), group 2 = "~" for a destructor,
# group 3 = final name.
DEFSIG = re.compile(r'^([A-Za-z_]\w*(?:::\w+)*)::(~?)([A-Za-z_]\w*)\s*\(')

# Call sites: every `::~name(` / `::name(` on a line.  The qualifier is
# recovered by walking backwards from the "::" (see extract_qual), which --
# unlike a regex -- can cross template arguments, so `Walaber::SharedPtr<X>::
# ~SharedPtr(p)` is reached too.  A qualifier with no "::" at all (e.g.
# `vector<int>::vector(`) is rejected, matching the previous look-behind.
SITE = re.compile(r'::(~?)([A-Za-z_]\w*)\s*\(')

# Ghidra's spelling of a bound (or inferred) parameter.  Anything else in a
# first-parameter position is a type name or an unnamed parameter -- we do
# not drop those.
PARAM_NAME = re.compile(r'^(?:param_\d+|p\d+|in_[xw]\d+|this|lpStack_\w+|'
                        r'puStack_\w+|param_\d+_0)$')


def read_component(text, i):
    """Read the (possibly template-argument-bearing) identifier ending at i.

    Returns (start, spelling) or None.  ``A::B<X, Y>::`` read at the colon
    after B yields ``('...B' index, 'B<X, Y>')``; nested ``<...>`` are paired
    by counting angle brackets backwards.
    """
    if i > 0 and text[i - 1] == '>':
        k = i - 1
        depth = 1
        while k > 0 and depth:
            k -= 1
            if text[k] == '>':
                depth += 1
            elif text[k] == '<':
                depth -= 1
        if depth:
            return None
        k2 = k
        while k2 > 0 and (text[k2 - 1].isalnum() or text[k2 - 1] == '_'):
            k2 -= 1
        if k2 == k:
            return None
        return k2, text[k2:i]
    j = i
    while j > 0 and (text[j - 1].isalnum() or text[j - 1] == '_'):
        j -= 1
    if j == i:
        return None
    return j, text[j:i]


def extract_qual(text, colon_pos):
    """Recover the qualified name whose last ``::`` sits at colon_pos.

    Returns (start, qualifier, targs, base) where targs are the template
    arguments of the qualifier's final component (``''`` when it has none)
    and base is that component's name without its arguments, or None when
    the text is not a qualified name (no ``::`` at all, unbalanced or bare
    angle brackets).
    """
    i = colon_pos
    comps = []
    targs = ''
    base = ''
    got_last = False
    while True:
        r = read_component(text, i)
        if r is None:
            return None
        start, comp = r
        if not got_last:
            base = comp.split('<', 1)[0]
            if comp.endswith('>'):
                targs = comp[comp.index('<') + 1:-1]
            got_last = True
        comps.insert(0, comp)
        if start >= 2 and text[start - 2:start] == '::':
            i = start - 2
            continue
        break
    qual = '::'.join(comps)
    if '::' not in qual:
        return None
    if start > 0 and (text[start - 1].isalnum() or text[start - 1] in '_:'):
        return None
    return start, qual, targs, base


def match_paren(text, open_idx):
    """Index of the `)` closing the `(` at open_idx, or -1 if unbalanced."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def split_top(s):
    """Split on commas at ()[]{}<> depth 0 (keeps CONCAT44(a, b) together)."""
    parts = []
    cur = []
    depth = 0
    angle = 0
    for ch in s:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == '<':
            angle += 1
        elif ch == '>':
            if angle > 0:
                angle -= 1
        if ch == ',' and depth == 0 and angle == 0:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append(''.join(cur))
    return [p.strip() for p in parts]


def top_comma_pos(s):
    """Byte offset of the first comma at ()[]{}<> depth 0, or -1."""
    depth = 0
    angle = 0
    for i, ch in enumerate(s):
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == '<':
            angle += 1
        elif ch == '>':
            if angle > 0:
                angle -= 1
        elif ch == ',' and depth == 0 and angle == 0:
            return i
    return -1


def true_arity(demangled):
    """Top-level parameter count of `Ns::Name(params)` (templates skipped)."""
    if not demangled:
        return None
    angle = 0
    open_idx = -1
    for i, ch in enumerate(demangled):
        if ch == '<':
            angle += 1
        elif ch == '>':
            if angle > 0:
                angle -= 1
        elif ch == '(' and angle == 0:
            open_idx = i
            break
    if open_idx < 0:
        return None
    close = match_paren(demangled, open_idx)
    if close < 0:
        return None
    inner = demangled[open_idx + 1:close]
    if not inner.strip():
        return 0
    return len(split_top(inner))


def load_index(path):
    index = {}
    if not os.path.exists(path):
        return index
    with open(path, encoding='utf-8', errors='replace', newline='') as fh:
        for line in fh:
            cols = line.rstrip('\r\n').split('\t')
            if len(cols) >= 5:
                index[cols[1].lower()] = cols[4]
    return index


def rewrite_calls(line):
    """Rewrite dtor then ctor call sites on one (indented) line, right to left."""
    changed = 0
    stripped = line.lstrip()
    if not stripped or stripped[:2] in ('//', '/*'):
        return line, 0

    # --- destructor calls: exactly one argument (the object) -------------
    # Right to left; a rewrite inside a further-left call's parentheses makes
    # that call's close index stale, so it is skipped (`boundary`).
    boundary = len(line)
    for m in reversed(list(SITE.finditer(line))):
        tilde, name = m.group(1), m.group(2)
        if tilde != '~':
            continue
        eq = extract_qual(line, m.start())
        if eq is None:
            continue
        start, qual, targs, base = eq
        if base != name:
            continue
        open_idx = m.end() - 1
        close = match_paren(line, open_idx)
        if close < 0 or close >= boundary:
            continue
        args = split_top(line[open_idx + 1:close])
        if len(args) != 1 or not args[0]:
            continue
        if targs:
            # Template-qualified (`Walaber::SharedPtr<X>::~SharedPtr(p)`):
            # the bare name after `~` only names a template, so spell the
            # arguments in the explicit destructor call as well.
            repl = '((%s *)%s)->~%s<%s>()' % (qual, args[0], name, targs)
        else:
            repl = '((%s *)%s)->~%s()' % (qual, args[0], name)
        line = line[:start] + repl + line[close + 1:]
        boundary = start
        changed += 1

    # --- constructor calls: first argument is the constructed object -----
    # Template-qualified constructor calls (`vector<T>::vector(...)`) stay
    # untouched, as before: their qualifiers cross a `>` the old regex could
    # not, and placement-new on an undefined template adds nothing.
    boundary = len(line)
    for m in reversed(list(SITE.finditer(line))):
        tilde, name = m.group(1), m.group(2)
        if tilde == '~':
            continue
        eq = extract_qual(line, m.start())
        if eq is None:
            continue
        start, qual, targs, base = eq
        if targs or base != name:
            continue
        open_idx = m.end() - 1
        close = match_paren(line, open_idx)
        if close < 0 or close >= boundary:
            continue
        args_raw = line[open_idx + 1:close]
        if not args_raw.strip():
            continue            # no object argument: nothing to place it on
        cut = top_comma_pos(args_raw)
        if cut < 0:
            obj, rest = args_raw.strip(), ''
        else:
            obj, rest = args_raw[:cut].strip(), args_raw[cut + 1:].strip()
        repl = 'new ((void *)(%s)) %s(%s)' % (obj, qual, rest)
        line = line[:start] + repl + line[close + 1:]
        boundary = start
        changed += 1
    return line, changed


def find_sig(body):
    """Locate a ctor/dtor definition signature in a block body.

    Returns (sig_line_index, open_paren_offset, close_paren_offset) or None.
    """
    offset = 0
    lines = body.split('\n')
    for li, line in enumerate(lines):
        m = DEFSIG.match(line)
        if m:
            if m.group(1).split('::')[-1] != m.group(3):
                return None            # regular member, not a ctor/dtor
            open_in_line = line.index('(', m.start(3))
            close = match_paren(body, offset + open_in_line)
            if close < 0:
                return None
            if not body[close + 1:close + 80].lstrip().startswith('{'):
                return None            # a declaration or expression, not a def
            return li, offset + open_in_line, close
        offset += len(line) + 1
        if li > 60:
            break
    return None


def process_block(body, addr, index, stats):
    sig = find_sig(body)
    if sig:
        li, sig_open, sig_close = sig
        m = DEFSIG.match(body.split('\n')[li])
        qual, tilde, name = m.group(1), m.group(2), m.group(3)
        if tilde == '~':
            # --- destructor definition: no params, bind dangling object uses
            stats['dtor_defs'] += 1
            tail = body[sig_close + 1:]
            new_tail, n1 = re.subn(r'(?<![\w:])param_1(?![\w:])', 'this', tail)
            new_tail, n2 = re.subn(r'(?<![\w:])p0(?![\w:])', 'this', new_tail)
            if n1 + n2:
                stats['dtor_body_fixed'] += 1
                stats['dtor_body_names'] += n1 + n2
                body = body[:sig_close + 1] + new_tail
        else:
            # --- constructor definition: maybe drop the object parameter ----
            stats['ctor_defs'] += 1
            params = body[sig_open + 1:sig_close]
            parts = split_top(params) if params.strip() else []
            n_def = len(parts)
            n_true = true_arity(index.get(addr))
            if n_true is None:
                stats['ctor_no_index'] += 1
            elif n_def == n_true + 1 and n_def >= 1:
                pname = parts[0].replace('*', ' ').replace('&', ' ').split()
                pname = pname[-1] if pname else ''
                if not PARAM_NAME.match(pname):
                    stats['ctor_param_unparsed'] += 1
                else:
                    cut = top_comma_pos(params)
                    new_params = params[cut + 1:].lstrip() if cut >= 0 else ''
                    body = body[:sig_open + 1] + new_params + body[sig_close:]
                    stats['ctor_dropped'] += 1
                    if pname != 'this':
                        nl = body.find('\n', sig_open)
                        head = body[:nl] if nl >= 0 else body
                        tail = body[nl:] if nl >= 0 else ''
                        tail, nsub = re.subn(
                            r'(?<![\w:])%s(?![\w:])' % re.escape(pname),
                            'this', tail)
                        body = head + tail
                        stats['ctor_body_names'] += nsub
            elif n_true is not None and n_def != n_true:
                stats['ctor_arity_mismatch'] += 1

    # --- call sites: every indented line ---------------------------------
    total = 0
    new_lines = []
    for line in body.split('\n'):
        if line[:1] in (' ', '\t'):
            line, n = rewrite_calls(line)
            total += n
        new_lines.append(line)
    if total:
        stats['calls'] += total
    return '\n'.join(new_lines)


def process(text, index, stats):
    marks = list(MARKER.finditer(text))
    out = []
    prev = 0
    for i, mk in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append(text[prev:mk.end()])
        out.append(process_block(text[mk.end():end], mk.group(1).lower(),
                                 index, stats))
        prev = end
    out.append(text[prev:])
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', nargs='?', default='out/src')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--index', default=None)
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = args.src if os.path.isabs(args.src) else os.path.join(root, args.src)
    index_path = args.index or os.path.join(src, '_index.tsv')
    index = load_index(index_path)

    changed = 0
    stats = Counter()
    for base, _dirs, names in os.walk(src):
        for name in sorted(names):
            if not name.endswith('.cpp'):
                continue
            p = os.path.join(base, name)
            with open(p, encoding='utf-8', errors='surrogateescape',
                      newline='') as fh:
                text = fh.read()
            new = process(text, index, stats)
            if new != text:
                changed += 1
                if not args.check:
                    with open(p, 'w', encoding='utf-8',
                              errors='surrogateescape', newline='') as fh:
                        fh.write(new)

    for k in sorted(stats):
        print('%-22s %6d' % (k, stats[k]))
    print('files changed: %d' % changed)
    if args.check:
        return 1 if changed else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
