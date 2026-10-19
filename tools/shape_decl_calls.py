#!/usr/bin/env python3
"""Turn Ghidra's declaration-shaped calls back into call expressions.

When the decompiler cannot name the object of a template member (or the
template arguments of a function template), it prints the *call* the way a
definition is printed, with the return type in front::

    void std::__ndk1::vector<int, ...>::__push_back_slow_path<int>(obj, arg);
    std::__ndk1::basic_string<char, ...> std::__ndk1::operator+<char, ...>(a, b);

At block scope such a line is a declaration, which C++ forbids ("definition
or redeclaration not allowed inside a function").  Neither can be a variable
declaration: the declared name is qualified and carries explicit template
arguments.  Dropping the return type leaves a well-formed call expression.

Only statements that are indented (inside a body) are touched, and only when
the text before the argument list looks like a type and the text after it like
a qualified, explicitly-instantiated name.  Idempotent: a shaped line starts
with the name, so it no longer has a type to find.
"""

import argparse
import glob
import os
import re
import sys

#: Tokens that can only start a statement, never a return type.
_STATEMENTS = {
    "return", "if", "else", "while", "for", "do", "switch", "case", "default",
    "throw", "try", "catch", "delete", "new", "sizeof", "goto", "break",
    "continue", "static_cast", "reinterpret_cast", "const_cast",
    "dynamic_cast", "typeid", "alignof", "co_return", "co_await", "co_yield",
}

_TYPE = re.compile(r"^[A-Za-z_][\w:<>,\s*&]*$")
_NAME = re.compile(r"^[A-Za-z_~][^(){};]*$")


def _params_open(body):
    """Index of the ``(`` matching the final ``)`` of ``body``."""
    depth = 0
    for i in range(len(body) - 1, -1, -1):
        c = body[i]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                return i
    return None


def _name_start(body, stop):
    """Walk back over a qualified name, over its template arguments."""
    angle = 0
    i = stop - 1
    while i >= 0:
        c = body[i]
        if c == ">":
            angle += 1
        elif c == "<":
            if angle == 0:
                break
            angle -= 1
        elif c.isspace() and angle == 0:
            break
        i -= 1
    return i + 1


def shape_line(line):
    """Return ``line`` without its return type, or ``None`` when it fits."""
    stripped = line.rstrip("\r\n")
    body = stripped.strip()
    indent = len(stripped) - len(stripped.lstrip())
    if not indent or not body.endswith(");") or body.startswith("//"):
        return None
    here = body.rfind(")")
    if here != len(body) - 2:
        return None
    open_paren = _params_open(body[:here + 1])
    if open_paren is None:
        return None
    start = _name_start(body, open_paren)
    name = body[start:open_paren]
    type_ = body[:start].strip()
    if not name or "::" not in name or "<" not in name:
        return None
    if not _NAME.match(name) or not _TYPE.match(type_):
        return None
    if type_.split()[0] in _STATEMENTS:
        return None
    ending = line[len(stripped):]
    return line[:indent] + name + body[open_paren:] + ending


def shape_file(path, stats, dry_run=False, sink=None):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    changed = 0
    for line in text.splitlines(keepends=True):
        new = shape_line(line)
        if new is None or new == line:
            out.append(line)
            continue
        changed += 1
        out.append(new)
        stats["shaped"] += 1
        if sink is not None:
            sink.write("%s: %s\n    -> %s\n" % (path, line.strip()[:160],
                                               new.strip()[:160]))
    if changed and not dry_run:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(out))
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0,
                    help="print the first N rewrites")
    args = ap.parse_args(argv)
    stats = {"shaped": 0}
    shown = []
    sink = sys.stdout if args.show else None
    files = 0
    shapes = 0
    paths = sorted(glob.glob(os.path.join(args.src, "**", "*.cpp"),
                             recursive=True))
    for path in paths:
        if sink is not None and stats["shaped"] >= args.show:
            sink = None
        count = shape_file(path, stats, args.dry_run, sink)
        if count:
            files += 1
            shapes += count
    print("files %d, changed %d, statements %d%s"
          % (len(paths), files, shapes, " (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
