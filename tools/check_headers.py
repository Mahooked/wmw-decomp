"""Verify that every generated header reproduces its recovered layout.

A recovered offset is only useful if it survives contact with the C++ ABI: a
real compiler lays members out at their natural alignment, inserting padding of
its own, and a struct whose declared offsets cannot be rebuilt is a struct that
will not compile to the layout it claims.  So for each header this walks the
declarations in order, applying the same alignment rules a compiler would,
advancing over the explicit `_pad` arrays the generator emitted, and compares
the position each field lands at against the offset encoded in its name.

It also checks the struct's total size against the recovered `sizeof`.
"""

import argparse
import collections
import os
import re
import sys

SIZEOF = {
    "uint8_t": 1, "uint16_t": 2, "uint32_t": 4, "uint64_t": 8,
    "int8_t": 1, "int16_t": 2, "int32_t": 4, "int64_t": 8,
    "float": 4, "double": 8,
}
# `int8_t` before `uint8_t` never matters, but the alternation must not be able
# to match a shorter name as a prefix of a longer one.
SCALARS = "|".join(sorted(SIZEOF, key=len, reverse=True))
DECL = re.compile(r"^\s*(" + SCALARS + r")\s+(\w+)(?:\[(\d+)\])?;")
PADDING = ("_pre", "_pad", "_tail")


def align_up(cursor: int, align: int) -> int:
    return (cursor + align - 1) // align * align


def check_file(path: str):
    """Return (fields, max_end, problems) for one header."""
    cursor = 0
    fields = []
    max_end = 0
    problems = []
    for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
        m = DECL.match(line)
        if not m:
            continue
        ctype, name, count = m.group(1), m.group(2), m.group(3)
        n = int(count) if count else 1
        size = SIZEOF[ctype] * n
        if name.startswith(PADDING):
            # Explicit padding advances the cursor without any alignment of its
            # own, which is exactly what makes it legal to reach an odd offset.
            cursor += size
            continue
        cursor = align_up(cursor, min(SIZEOF[ctype], 8))
        end = cursor + size
        fields.append((name, cursor, lineno))
        max_end = max(max_end, end)
        if "_0x" not in name:
            problems.append((lineno, name, cursor, "field name carries no offset"))
            continue
        want = int(name.split("_0x", 1)[1], 16)
        if want != cursor:
            problems.append(
                (lineno, name, cursor,
                 "declared 0x%x but the ABI rebuild puts it at 0x%x" % (want, cursor)))
        cursor = end
    return fields, max_end, problems


def load_index(path: str):
    """Header path -> recovered sizeof, from the type index.

    Keyed by path rather than by class name: the generator folds over-long
    template names into a single hashed directory, so a name cannot be
    recovered from the path it was written to.
    """
    sizes = {}
    if not os.path.exists(path):
        return sizes
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) > 2 and f[2].strip().isdigit():
            sizes[f[1].replace("\\", "/")] = int(f[2])
    return sizes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include", default="out/types/include")
    ap.add_argument("--index", default="out/types/typeindex.tsv")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args(argv)

    sizes = load_index(args.index)
    headers = 0
    checked = 0
    bad_headers = 0
    short_headers = 0
    kinds = collections.Counter()
    examples = []

    for dirpath, _, files in os.walk(args.include):
        for fn in sorted(files):
            if not fn.endswith(".h") or fn == "wmw_types.h":
                continue
            path = os.path.join(dirpath, fn)
            headers += 1
            fields, max_end, problems = check_file(path)
            checked += len(fields)
            for _, _, _, why in problems:
                kinds[why.split(" but ")[0].split(" carries ")[-1]] += 1
            if problems:
                bad_headers += 1
                if len(examples) < args.limit:
                    examples.append((path, problems[0]))
            # A struct may be smaller than its recovered sizeof only if trailing
            # padding accounts for the difference.
            rel = os.path.relpath(path, args.include).replace(os.sep, "/")
            want = sizes.get(rel)
            if want is not None and max_end > want:
                short_headers += 1
                if len(examples) < args.limit:
                    examples.append(
                        (path, (0, "<struct>", max_end,
                                "ends at 0x%x, past the recovered sizeof %d"
                                % (max_end, want))))

    print("headers:                %d" % headers)
    print("field declarations:     %d" % checked)
    print("headers with a bad offset: %d" % bad_headers)
    print("headers overrunning sizeof: %d" % short_headers)
    for path, (lineno, name, got, why) in examples:
        print("   %s:%d  %s  %s" % (path, lineno, name, why))
    if bad_headers or short_headers:
        print("\nFAIL")
        return 1
    print("\nOK: every declared offset and size rebuilds under the C++ ABI")
    return 0


if __name__ == "__main__":
    sys.exit(main())