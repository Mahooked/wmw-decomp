"""Verify that every recovered enum is genuinely attested by the binary.

The enum pipeline (`enumparams.py` -> `EnumScan.java` -> `enums.py`) produces its
declarations from the constants the binary compares and masks against each
enum-typed register.  Those declarations are only as good as the evidence, so
the gate re-derives the verdict from the raw evidence (`_enumraw.tsv`) -- the
same rules `enums.py` applies, stated so the two agree -- and then checks that

  - `enums.tsv` records exactly the proven enums, with non-empty member lists
    and no duplicate values, and
  - every header named in `enums.tsv` really exists, declares the expected enum,
    and has one `E_<Name>_<ord>` enumerator per recorded member with the right
    value.

A value enum is proven when it has >= 2 distinct values and >= 2 distinct
evidence functions; a flags enum when its AND masks are >= 2 distinct powers of
two.  This is the two-independent-agreeing-readings rule the rest of the repo
uses, applied to constant compares instead of field offsets.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

MAX_VALUE = 0x7FFFFFFF


def load_evidence(path: str):
    rows = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 5:
            continue
        rows.setdefault(f[0], []).append((int(f[1], 16), f[2], f[4]))
    return rows


def derive(name: str, rows):
    """Same verdict rules as tools/enums.py, so the gate cannot drift."""
    cmp_vals, cmp_funcs, and_masks = set(), set(), set()
    for value, kind, func in rows:
        if kind in ("cmp", "store") and 0 <= value <= MAX_VALUE:
            cmp_vals.add(value)
            cmp_funcs.add(func)
        elif kind == "and" and value > 0 and (value & (value - 1)) == 0:
            and_masks.add(value)
    if len(and_masks) >= 2:
        return ("flags", sorted(and_masks))
    if len(cmp_vals) >= 2 and len(cmp_funcs) >= 2:
        return ("values", sorted(cmp_vals))
    return None


def load_tsv(path: str):
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 6:
            continue
        out[f[0]] = {
            "kind": f[1],
            "members": [int(v, 16) for v in f[3].split()],
            "head": f[5],
        }
    return out


def check_header(path: str, name: str, kind: str, members):
    problems = []
    if not os.path.exists(path):
        return ["missing header %s" % path]
    base = name.rsplit("::", 1)[1]
    body = open(path, encoding="utf-8").read()
    if "enum %s {" % base not in body:
        problems.append("header does not declare enum %s" % base)
    for ordinal, value in enumerate(members):
        label = "E_%s_%d" % (base, ordinal)
        if not re.search(r"%s\s*=\s*%d\b" % (label, value), body):
            problems.append("missing enumerator %s = 0x%x" % (label, value))
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", default="out/types/_enumraw.tsv")
    ap.add_argument("--enums", default="out/types/enums.tsv")
    ap.add_argument("--include", default="out/types/include")
    args = ap.parse_args(argv)

    evidence = load_evidence(args.raw)
    tsv = load_tsv(args.enums)
    problems = []

    derived = {}
    for name, rows in evidence.items():
        verdict = derive(name, rows)
        if verdict:
            derived[name] = verdict

    if set(derived) != set(tsv):
        missing = sorted(set(derived) - set(tsv))
        extra = sorted(set(tsv) - set(derived))
        if missing:
            problems.append("enums.tsv omits proven enums: %s" % ", ".join(missing))
        if extra:
            problems.append("enums.tsv declares unproven enums: %s" % ", ".join(extra))

    rejected = []
    for name, entry in sorted(tsv.items()):
        verdict = derived.get(name)
        if verdict is None:
            rejected.append(name)
            continue
        kind, members = verdict
        if entry["kind"] != kind:
            rejected.append(name)
            continue
        if len(entry["members"]) != len(members) or entry["members"] != members:
            rejected.append("%s (members differ)" % name)
            continue
        if len(set(entry["members"])) != len(entry["members"]):
            problems.append("duplicate member values in %s" % name)
        problems.extend(check_header(
            os.path.join(args.include, entry["head"].replace("/", os.sep)),
            name, entry["kind"], entry["members"]))

    print("evidence rows:      %d" % sum(len(v) for v in evidence.values()))
    print("enums in enums.tsv: %d" % len(tsv))
    print("proven by evidence: %d" % len(derived))
    print("unproven declared:  %d" % len(rejected))
    for name in rejected:
        print("   rejected %s" % name)
    for why in problems:
        print("   FAIL  %s" % why)
    if problems:
        print("\nFAIL")
        return 1
    print("\nOK: %d enums match the evidence and rebuild their headers" % len(tsv))
    return 0


if __name__ == "__main__":
    sys.exit(main())