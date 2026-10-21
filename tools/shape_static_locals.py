#!/usr/bin/env python3
"""Recover a function-local static that Ghidra named by full signature.

Ghidra qualifies a static local with the function it belongs to, and for a
template it prints the whole signature rather than a name::

    _walkStrip<WaterConcept::ConsiderSameDefault>(WaterConcept::GridCell, ..., int)
    ::stripID = _walkStrip<ConsiderSameDefault>(..., int)::stripID + 1;

That is not C++: the "call" is really a declaration whose parameter list is
made of type names, so it cannot sit where an expression belongs, and once the
callee is declared a template (see ``tools/shape_tmpl_calls.py``) the compiler
starts parsing those type names as arguments -- one such statement is worth a
hundred diagnostics.  The original source said just ``stripID``.

Only the *signature* form is rewritten: the qualifier must be a qualified name
with optional template arguments and a parameter list in which every component
is a type spelling and at least one is a pointer, a reference or a template
use.  A plain call that is followed by ``::`` (``getInstancePtr()::instance``)
can be a value argument, so it is left alone.  The file gains one
``static long long NAME;`` per recovered name, which is what a static local
degrades to once it is lifted to file scope.
"""

import argparse
import glob
import os
import re
import sys

#: A parameter that is a type spelling, not a value.
_COMPONENT = re.compile(r"^[A-Za-z_][\w\s:<>,&*]*$")
_QUALIFIER = re.compile(r"^[A-Za-z_]\w*(::[A-Za-z_]\w*)*$")


def _skip_ws_back(text, i):
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    return i


def _match_back(text, i):
    """Index of the ``(`` matching the ``)`` at ``i``, or ``None``."""
    depth = 0
    while i >= 0:
        c = text[i]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                return i
        elif c in ";{}":
            return None
        i -= 1
    return None


def _angle_back(text, i):
    """Index of the ``<`` matching the ``>`` at ``i``, or ``None``."""
    depth = 0
    while i >= 0:
        c = text[i]
        if c == ">":
            depth += 1
        elif c == "<":
            depth -= 1
            if depth == 0:
                return i
        elif c in ";{}()":
            return None
        i -= 1
    return None


def _type_list(args):
    """Does ``args`` hold nothing but type spellings, one of them interesting?"""
    if not args.strip():
        return False
    rich = False
    for part in args.split(","):
        part = part.strip()
        if not part or not _COMPONENT.match(part):
            return False
        rich = rich or any(c in part for c in "<>&*")
    return rich


def static_locals(code):
    """Yield ``(qualifier start, name start, name)`` for every ``sig::var``."""
    n = len(code)
    pos = 0
    while True:
        at = code.find("::", pos)
        if at < 0:
            return
        pos = at + 1
        close = _skip_ws_back(code, at - 1)
        if close < 0 or code[close] != ")":
            continue
        open_paren = _match_back(code, close)
        if open_paren is None or not _type_list(code[open_paren + 1:close]):
            continue
        k = _skip_ws_back(code, open_paren - 1)
        if k >= 0 and code[k] == ">":
            angle = _angle_back(code, k)
            if angle is None:
                continue
            k = _skip_ws_back(code, angle - 1)
        stop = k + 1
        while k >= 0 and (code[k].isalnum() or code[k] in "_:"):
            k -= 1
        qualifier = code[k + 1:stop]
        if not _QUALIFIER.match(qualifier):
            continue
        start = k + 1
        var = at + 2
        while var < n and code[var] in " \t\r\n":
            var += 1
        end = var
        while end < n and (code[end].isalnum() or code[end] == "_"):
            end += 1
        if end == var:
            continue
        yield start, end, code[var:end]


def shape_file(path, stats, dry_run=False, sink=None):
    text = open(path, encoding="utf-8", errors="replace").read()
    chars = list(text)
    i = 0
    while True:                       # blank comments, offsets preserved
        start = text.find("/*", i)
        if start < 0:
            break
        end = text.find("*/", start + 2)
        end = len(text) if end < 0 else end + 2
        for k in range(start, end):
            if chars[k] != "\n":
                chars[k] = " "
        i = end
    code = "".join(chars)

    edits = []
    names = []
    for start, end, name in static_locals(code):
        edits.append((start, end, name))
        if name not in names:
            names.append(name)
        stats["statics"] += 1
        if sink is not None:
            sink.write("%s: %s -> %s\n" % (path, code[start:end].strip()[:90],
                                           name))
    if not edits:
        return 0
    if dry_run:
        return len(edits)
    for start, end, name in reversed(edits):
        text = text[:start] + name + text[end:]
    if names:
        head = "".join("static long long %s;\n" % name for name in names)
        text = head + text
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return len(edits)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0,
                    help="print the first N rewrites")
    args = ap.parse_args(argv)
    stats = {"statics": 0}
    sink = sys.stdout if args.show else None
    files = 0
    shapes = 0
    paths = sorted(glob.glob(os.path.join(args.src, "**", "*.cpp"),
                             recursive=True))
    for path in paths:
        if sink is not None and stats["statics"] >= args.show:
            sink = None
        count = shape_file(path, stats, args.dry_run, sink)
        if count:
            files += 1
            shapes += count
    print("files %d, changed %d, statics %d%s"
          % (len(paths), files, shapes, " (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
