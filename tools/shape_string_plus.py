#!/usr/bin/env python3
"""Name libc++ string ``operator+`` calls and bodies in their ABI shape.

The AArch64 ABI lowers these three ``basic_string`` return-by-value overloads
to a hidden result pointer plus their two source operands.  Ghidra prints that
as a qualified ``operator+`` call with three arguments, and emits the matching
function bodies with three parameters.  C++ forbids three-argument operator
functions, even when the third parameter is the hidden result storage.

This pass renames only those code occurrences to ``__decomp_string_plus`` and
drops the explicit function-template arguments from its call sites.  The
original demangled signatures in comments are kept intact.  The syntax gate
then harvests ordinary helper overloads from the three decompiled bodies.
"""

from __future__ import annotations

import argparse
import glob
import os
import re

_CALL = re.compile(r"std::__ndk1::operator\+<")
_DEF = re.compile(r"std::__ndk1::operator\+\s*\(")
_HELPER = "std::__ndk1::__decomp_string_plus"


def mask_comments(text):
    """Blank block comments while preserving offsets and newlines."""
    return re.sub(
        r"/\*.*?\*/",
        lambda m: "".join("\n" if c == "\n" else " "
                           for c in m.group(0)),
        text,
        flags=re.S,
    )


def shape_text(text):
    """Return transformed text and ``(call_count, definition_count)``."""
    code = mask_comments(text)
    edits = []
    calls = 0
    for match in _CALL.finditer(code):
        i = match.end()
        depth = 1
        while i < len(code) and depth:
            if code[i] == "<":
                depth += 1
            elif code[i] == ">":
                depth -= 1
            i += 1
        if depth:
            continue
        j = i
        while j < len(code) and code[j].isspace():
            j += 1
        if j < len(code) and code[j] == "(":
            edits.append((match.start(), i, _HELPER))
            calls += 1

    definitions = 0
    for match in _DEF.finditer(code):
        edits.append((match.start(), match.end() - 1, _HELPER))
        definitions += 1

    if not edits:
        return text, (0, 0)
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text, (calls, definitions)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="fail if any eligible operator+ shape remains")
    args = ap.parse_args(argv)

    paths = sorted(glob.glob(os.path.join(args.src, "**", "*.cpp"),
                              recursive=True))
    files = calls = definitions = 0
    for path in paths:
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            original = fh.read()
        shaped, counts = shape_text(original)
        if shaped == original:
            continue
        files += 1
        calls += counts[0]
        definitions += counts[1]
        if not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(shaped)

    print("files %d, call sites %d, definitions %d%s" % (
        files, calls, definitions, " (dry run)" if args.dry_run else ""))
    if args.check and (calls or definitions):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
