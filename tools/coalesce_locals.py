"""Coalesce the decompiler's register copies in ``out/src`` back into locals.

After the stack protector is gone (see ``tools/shape_source.py``) the next
mechanical artefact in the bodies is the *register copy*.  Ghidra models each
ARM64 register as a variable, so a value the source held in one local often
travels through two or three of them, and a spilled value is written to a
``*Stack_*`` slot and read straight back::

    uVar5 = (ulong)(abStack_40[0] >> 1);
    uVar3 = uVar5;                 // register alias: uVar3 is just uVar5
    ...
    uStack_98 = param_4;           // argument spilled to a slot
    ...
    uVar7 = uStack_98;

None of those copies are in the source; they are the decompiler naming the
same value twice.  Two sound rewrites remove them.

**Copy propagation, within a basic block.**  Walking the straight-line runs of
plain statements that the decompiler emits, an assignment ``x = y;`` (both
plain locals, no cast) records that ``x`` currently *is* ``y``; every later
read of ``x`` in the same run is rewritten to ``y``.  The alias is dropped the
moment ``y`` is reassigned, and the whole environment is cleared at any control
line (``if``, ``while``, ``goto``, ``return``, a label, a brace), so an alias
never crosses a branch.  Because locals whose address is taken are excluded
entirely, a call in the run can never observe one behind the rewrite.

**Single-assignment coalescing, across blocks.**  Where a name is assigned
exactly once in the whole body, a copy can be folded even across control flow:

  * **alias** -- ``a = b;`` with ``a`` assigned only here and ``b`` *never*
    assigned (a local or a parameter).  Every read of ``a`` becomes a read of
    ``b`` and ``a``'s declaration is dropped; ``b`` is immutable, so this is
    safe across loops and gotos.
  * **temporary** -- ``a = b;`` with ``a`` assigned only here and ``b``
    assigned exactly once, before the copy.  ``b`` holds one value from its
    definition on, so ``b`` and ``a`` are one variable: uses of ``b`` become
    uses of ``a``, ``b``'s declaration is dropped and the copy disappears.

In both rules ``a`` must not be read before the copy (a stack slot the
decompiler reused would hold another variable there).

Finally, any copy left with no reader at all is a dead store and is deleted,
and declarations no longer mentioned are dropped.  Only copies written at the
top level of the body (two-space indent, never inside a brace) drive the
single-assignment rules; propagation additionally handles nested copies, but
only within a run.  Comments and string literals are masked out first, so an
identifier mentioned in a demangled-name comment is never rewritten.  The pass
runs to a fixpoint, is idempotent, and ``--check`` fails while any coalescible
copy remains.

Output: rewritten in place under ``out/src`` (``--check`` only reports).
"""

from __future__ import annotations

import argparse
import os
import re
import sys

MARK = re.compile(r"(?=^/\* ok  address )", re.M)

# A scalar local declaration: "<type> <name>;", no array, no initialiser.
DECL = re.compile(r"^  +([A-Za-z_][A-Za-z0-9_:<>, \*]*?[ \*])([A-Za-z_]\w*);\s*$")
# Top-level (two-space) register copy: "  a = b;".
COPY = re.compile(r"^  ([A-Za-z_]\w*) = ([A-Za-z_]\w*);$")
# Any copy at any indent (for dead-store removal).
PURE_COPY = re.compile(r"^\s*([A-Za-z_]\w*) = ([A-Za-z_]\w*);\s*$")
# Leading local assignment of a statement.
ASSIGN = re.compile(r"^(\s*)([A-Za-z_]\w*) = (.*)$")
WORD = re.compile(r"[A-Za-z_]\w*")
IDENT = re.compile(r"[A-Za-z_]\w*")
FIRST = re.compile(r"([A-Za-z_]\w*)")
CONTROL = {"if", "else", "while", "for", "do", "switch", "goto", "return",
           "break", "continue", "case", "default"}


def mask_comments(lines):
    """Return ``lines`` with comment and string-literal regions blanked out.

    Lengths (and therefore identifier column offsets) are preserved, so a
    substitution position found in the mask splices cleanly into the real line.
    """
    out = []
    state = None  # None | "'" | '"' | "line" | "block"
    for line in lines:
        line = line or ""
        buf = list(line)
        i = 0
        n = len(line)
        while i < n:
            c = line[i]
            if state is None:
                if c == "/" and i + 1 < n and line[i + 1] == "/":
                    state = "line"
                    buf[i] = buf[i + 1] = " "
                    i += 2
                    continue
                if c == "/" and i + 1 < n and line[i + 1] == "*":
                    state = "block"
                    buf[i] = buf[i + 1] = " "
                    i += 2
                    continue
                if c == '"':
                    state = '"'
                    buf[i] = " "
                    i += 1
                    continue
                if c == "'":
                    state = "'"
                    buf[i] = " "
                    i += 1
                    continue
            else:
                buf[i] = " "
                if state == "line":
                    i += 1
                    continue
                if state == "block":
                    if c == "*" and i + 1 < n and line[i + 1] == "/":
                        buf[i + 1] = " "
                        i += 2
                        state = None
                        continue
                    i += 1
                    continue
                if c == "\\":
                    if i + 1 < n:
                        buf[i + 1] = " "
                    i += 2
                    continue
                if c == state:
                    state = None
                i += 1
                continue
            i += 1
        out.append("".join(buf))
    return out


def params_of(sig):
    """Set of parameter names in a definition signature line."""
    lf = sig.rfind("(")
    if lf < 0 or not sig.rstrip().endswith(")"):
        return set()
    inner = sig[lf + 1:sig.rstrip().rfind(")")]
    if inner.strip() in ("", "void"):
        return set()
    names = set()
    depth = 0
    piece = ""
    for ch in inner + ",":
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            toks = WORD.findall(piece)
            if len(toks) >= 2:
                names.add(toks[-1])
            piece = ""
        else:
            piece += ch
    return names


def _subst(line, masked, old, new):
    """Replace identifier ``old`` with ``new`` in ``line``, skipping comments."""
    if old == new:
        return line
    out = []
    i = 0
    for m in re.finditer(r"\b%s\b" % re.escape(old), masked):
        out.append(line[i:m.start()])
        out.append(new)
        i = m.end()
    out.append(line[i:])
    return "".join(out)


def _apply_map(real, mask, mapping):
    """Replace every identifier in ``real`` that is a key of ``mapping``."""
    out = []
    i = 0
    for m in IDENT.finditer(mask):
        word = m.group(0)
        out.append(real[i:m.start()])
        out.append(mapping.get(word, word))
        i = m.end()
    out.append(real[i:])
    return "".join(out)


def _resolve(env, name):
    seen = set()
    while name in env and name not in seen:
        seen.add(name)
        name = env[name]
    return name


def _is_plain(masked):
    s = masked.strip()
    if not s or not s.endswith(";"):
        return False
    if "{" in s or "}" in s:
        return False
    m = FIRST.match(s)
    if not m or m.group(1) in CONTROL:
        return False
    if re.match(r"^[A-Za-z_]\w*:$", s):
        return False
    return True


def plan(text):
    """Coalesce copies in every function of ``text``. Return (new, stats)."""
    stats = {"prop": 0, "alias": 0, "temp": 0, "dead": 0, "decls": 0,
             "functions": 0}
    chunks = []
    for part in MARK.split(text):
        if not part.startswith("/* ok"):
            chunks.append(part)
            continue
        new, changed = _plan_block(part, stats)
        if changed:
            stats["functions"] += 1
        chunks.append(new)
    return "".join(chunks), stats


def _plan_block(block, stats):
    lines = block.split("\n")
    try:
        bi = lines.index("{")
    except ValueError:
        return block, False

    sig = ""
    for k in range(bi - 1, -1, -1):
        if lines[k].strip():
            sig = lines[k]
            break
    params = params_of(sig)

    decls = {}
    decl_idx = {}
    j = bi + 1
    while j < len(lines):
        line = lines[j] or ""
        if line.strip() == "":
            j += 1
            continue
        m = DECL.match(line)
        ft = FIRST.match(line.strip())
        if not m or (ft and ft.group(1) in CONTROL):
            break
        name = m.group(2)
        if name not in decls:
            decls[name] = m.group(1).strip()
            decl_idx[name] = j
        j += 1

    if not decls and not params:
        return block, False

    body_idx = [i for i in range(bi + 1, len(lines))
                if i not in set(decl_idx.values())]
    if not body_idx:
        return block, False

    names = set(decls) | set(params)
    first_mask = mask_comments(lines)
    first_code = "\n".join(first_mask[i] for i in body_idx)
    addr = {nm for nm in names if re.search(r"&\s*%s\b" % re.escape(nm), first_code)}

    changed = False
    for _ in range(64):
        step = False
        step |= _propagate(lines, body_idx, names, addr, stats)
        step |= _single_assign(lines, body_idx, decls, params, addr, stats)

        # dead copies: a copy whose target is never read is a dead store.
        masked = mask_comments(lines)
        code = "\n".join(masked[k] for k in body_idx)
        for i in body_idx:
            if lines[i] is None:
                continue
            m = PURE_COPY.match(masked[i])
            if not m:
                continue
            a = m.group(1)
            if a not in decls:
                continue
            uses = len(re.findall(r"\b%s\b" % re.escape(a), code))
            # writes only at statement start: "*a = .." and "a[i] = .." are
            # reads of a, not assignments to it.
            writes = len(re.findall(r"(?m)^\s*%s\s*=(?!=)" % re.escape(a), code))
            if uses <= writes:
                lines[i] = None
                stats["dead"] += 1
                step = True

        # drop declarations no longer mentioned anywhere in the body.
        masked = mask_comments(lines)
        live = "\n".join(masked[k] for k in body_idx)
        for nm, idx in list(decl_idx.items()):
            if not re.search(r"\b%s\b" % re.escape(nm), live):
                lines[idx] = None
                stats["decls"] += 1
                step = True
                del decl_idx[nm]
                del decls[nm]

        if not step:
            break
        changed = True

    if not changed:
        return block, False
    return "\n".join(ln for ln in lines if ln is not None), True


def _propagate(lines, body_idx, names, addr, stats):
    """Within each straight-line run, rewrite reads of an aliased local."""
    masked = mask_comments(lines)
    env = {}
    changed = False
    for i in body_idx:
        raw = lines[i]
        if raw is None:
            env = {}
            continue
        stripped = raw.strip()
        if stripped == "":
            continue
        if stripped.startswith("/*") or stripped.startswith("//"):
            continue
        mline = masked[i]
        if not _is_plain(mline):
            env = {}
            continue
        am = ASSIGN.match(mline)
        w = am.group(2) if am else None
        off = am.start(3) if am else None
        if w is not None and w not in names:
            w = None  # assignment to a global/field, not a local

        mapping = {k: _resolve(env, k) for k in env}
        if mapping:
            if off is None:
                new = _apply_map(raw, mline, mapping)
                if new != raw:
                    lines[i] = new
                    stats["prop"] += len(mapping)
                    changed = True
            else:
                head = raw[:off]
                new = _apply_map(raw[off:], mline[off:], mapping)
                if head + new != raw:
                    lines[i] = head + new
                    stats["prop"] += len(mapping)
                    changed = True

        if w is not None:
            env = {k: v for k, v in env.items() if v != w}
            cm = PURE_COPY.match(mline)
            if (cm and cm.group(1) == w and cm.group(2) in names
                    and w not in addr and cm.group(2) not in addr):
                env[w] = _resolve(env, cm.group(2))
            else:
                env.pop(w, None)
    return changed


def _single_assign(lines, body_idx, decls, params, addr, stats):
    """Fold copies where the destination is assigned exactly once."""
    masked = mask_comments(lines)
    code = "\n".join(masked[k] for k in body_idx)
    writes = {}

    def nwrite(name):
        if name not in writes:
            writes[name] = len(re.findall(
                r"(?<![\w.>])%s\s*=\s*(?!=)" % re.escape(name), code))
        return writes[name]

    for i in body_idx:
        if lines[i] is None:
            continue
        cm = COPY.match(masked[i])
        if not cm:
            continue
        a, b = cm.group(1), cm.group(2)
        if a == b or a in addr or b in addr:
            continue
        if a in decls and decls[a] != decls.get(b, decls[a]):
            continue
        if nwrite(a) != 1:
            continue
        if any(re.search(r"\b%s\b" % re.escape(a), masked[k])
               for k in body_idx if k < i):
            continue
        if b not in decls and b not in params:
            continue
        if nwrite(b) == 0:  # b immutable: a is just b
            for k in body_idx:
                if k != i and lines[k] is not None:
                    lines[k] = _subst(lines[k], masked[k], a, b)
            lines[i] = None
            stats["alias"] += 1
            return True
        if b in decls and nwrite(b) == 1:  # b a single-use temporary
            bidx = [k for k in body_idx if k != i and
                    re.match(r"^  %s = " % re.escape(b), masked[k] or "")]
            if len(bidx) == 1 and bidx[0] < i:
                pre = [k for k in body_idx if k < i and k != bidx[0]]
                if not any(re.search(r"\b%s\b" % re.escape(b), masked[k])
                           for k in pre):
                    for k in body_idx:
                        if k != i and lines[k] is not None:
                            lines[k] = _subst(lines[k], masked[k], b, a)
                    lines[i] = None
                    stats["temp"] += 1
                    return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Coalesce decompiler register copies.")
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--check", action="store_true",
                    help="report remaining copies instead of rewriting")
    args = ap.parse_args(argv)

    total = {"prop": 0, "alias": 0, "temp": 0, "dead": 0, "decls": 0,
             "functions": 0}
    changed_files = 0
    for base, _, files in os.walk(args.src):
        for name in sorted(files):
            if not name.endswith(".cpp"):
                continue
            path = os.path.join(base, name)
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read().replace("\r\n", "\n")
            new, stats = plan(text)
            if not stats["functions"]:
                continue
            changed_files += 1
            for k in total:
                total[k] += stats[k]
            if not args.check:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new)

    print("propagated %d, alias %d, temp %d, dead copies %d, "
          "declarations dropped %d, functions %d, files %d"
          % (total["prop"], total["alias"], total["temp"], total["dead"],
             total["decls"], total["functions"], changed_files))
    if args.check and total["functions"]:
        print("FAIL: coalescible copies remain", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
