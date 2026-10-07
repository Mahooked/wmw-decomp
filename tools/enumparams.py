"""Inventory enum-typed parameters and emit the ABI register seed table.

The Itanium ABI does not encode enumerator values, but it *does* encode the enum
type itself: an enum passed as a function parameter appears in the mangled name
as an ordinary qualified name, indistinguishable there from a class.  The
distinguishing evidence is behavioural -- classes get field accesses and
eventually a verified layout, enums get compared against and assigned
constants -- so this pass and `EnumScan.java` split the work the same way
`layout.py` and `FieldScan.java` do: this file decides *which registers hold
which enum types*, the Ghidra script accumulates the constant comparisons, and
the aggregator decides what the evidence supports.

Register allocation mirrors DecompileAll.java exactly (AAPCS64): integer and
pointer arguments take the next ``x`` register, floating-point the next vector
file register, with an independent counter per bank.  Only the *base* register
name is written here -- an enum by value arrives in a ``w`` register and is
only distinguishable at comparison time, and the scanner canonicalises
x/w/s/d views by base register anyway.

A function-template instance keeps its *substituted* argument types as real
parameters (`_walkStrip<ConsiderSameAll>` really takes a ``ConsiderSameAll``
value argument, exactly as GCC renders it), so the parameter list is taken at
face value; no template-argument filtering applies.

Enum suspects are seed candidates: class-like names appearing as parameter
types plus single-field layout names (a value-typed enum read through a
reference looks exactly like a one-int struct at offset 0).  Confirmed structs
are excluded by positive class evidence: a typeinfo in the RTTI, an anchor role
(constructor/destructor/vtable slot), a multi-field layout, or a third-party
namespace (`std::__ndk1`, `ndk`, `FMOD`).

Output: `out/types/_enumparams.tsv` (address, function, register, enum, byval)
and an inventory summary printed to stdout.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wmwtools.signature import signature  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FUNCS = ROOT / "out" / "symbols" / "functions.tsv"
OUT = ROOT / "out" / "types" / "_enumparams.tsv"

#: A plain qualified name: no template arguments, no pointers or references.
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)+$")

#: Third-party / vendored namespaces never get game-owned enum headers.
_VENDOR = ("std::", "std::__ndk1::", "ndk::", "FMOD::")

#: AAPCS64 integer argument registers (the scanner uses base names; the
#: 4-byte view for an `int` enum is resolved at comparison time).
X_REGS = ["x%d" % i for i in range(8)]


def load_set(path: str, col: int = 0, skip_prefix: tuple = ()) -> set:
    out = set()
    if not Path(path).is_file():
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if f and len(f) > col and f[col].strip():
                out.add(f[col].strip())
    return out


def is_float_type(param: str) -> int:
    """Return byte length for a floating parameter type, else 0.

    The recovered spelling is the demangler's, so floats appear as `float` /
    `double`, and pointers/references to them carry `*`/`&`, which makes the
    base word matchable.
    """
    word = re.sub(r"[*&]|\bconst\b|\bvolatile\b", "", param).strip()
    word = re.sub(r"\s+", " ", word)
    if word == "float":
        return 4
    if word == "double":
        return 8
    return 0


def base_name(param: str):
    """Return ``(name, deref)`` for a parameter whose core is a qualified name.

    ``deref`` is 2 for a reference, 1 for a pointer, 0 for a by-value type.
    """
    s = param
    s = re.sub(r"\b(?:const|volatile)\b\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    stars = s.count("*")
    refs = s.count("&")
    core = s.replace("*", "").replace("&", "").strip()
    if NAME.match(core):
        return core, refs + stars
    return None, refs + stars


def main(argv=None) -> int:
    from argparse import ArgumentParser
    p = ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rtti", default=str(ROOT / "out" / "rtti" / "hierarchy.tsv"))
    p.add_argument("--layouts", default=str(ROOT / "out" / "types" / "layouts.tsv"))
    p.add_argument("--anchors", default=str(ROOT / "out" / "types" / "anchor_classes.txt"))
    p.add_argument("--out", default=str(OUT))
    args = p.parse_args(argv)

    rtti = load_set(args.rtti)
    anchors = load_set(args.anchors)

    layout_fields = {}
    layout_kind = {}
    layout_fields = {}
    if Path(args.layouts).is_file():
        with open(args.layouts, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                f = line.rstrip("\n").split("\t")
                if len(f) < 4:
                    continue
                cls = f[0]
                if cls in ("Walaber", "WaterConcept", "WaterConceptConstants"):
                    continue
                try:
                    layout_fields[cls] = int(f[3])
                except ValueError:
                    continue
    seeds = []  # (addr, name, reg, enum, byval)
    skipped = {"malformed": 0, "unparseable": 0}
    funcs_parsed = 0

    with open(FUNCS, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 3 or not f[0]:
                skipped["malformed"] += 1
                continue
            addr = f[0]
            mangled = f[2]
            sig = signature(mangled)
            if sig is None:
                skipped["unparseable"] += 1
                continue
            funcs_parsed += 1
            params = list(sig.params)

            int_idx = 0
            for pp in params:
                name, deref = base_name(pp)
                if not name:
                    if not is_float_type(pp):
                        int_idx += 1
                    continue
                if name.startswith(_VENDOR):
                    int_idx += 1
                    continue
                # Enum suspects: a class that is provably polymorphic (typeinfo,
                # anchor role) is never an enum.  Otherwise a single-field
                # layout is exactly how a value-typed enum read through a
                # reference looks -- those are the *best* suspects.  Multi-field
                # layouts stay confirmed structs.
                if name in rtti or name in anchors:
                    candidate = False
                elif name in layout_fields:
                    candidate = layout_fields[name] == 1
                else:
                    candidate = True
                if not candidate:
                    int_idx += 1
                    continue
                if int_idx >= 8:
                    break
                reg = X_REGS[int_idx]
                int_idx += 1
                byval = 1 if deref == 0 else 0
                param_uses.setdefault(name, []).append(addr)
                seeds.append((addr, sig.name, reg, name, byval))

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# address\tfunc\treg\tenum\tbyval\n")
        for addr, name, reg, enum, byval in sorted(seeds):
            fh.write("%s\t%s\t%s\t%s\t%d\n" % (addr, name, reg, enum, byval))

    # ---- inventory --------------------------------------------------------
    by_enum = {}
    for addr, name, reg, enum, byval in seeds:
        by_enum.setdefault(enum, []).append((addr, byval))

    print("enumparams: parsed %d functions, %d seeds, %d distinct enum suspects"
          % (funcs_parsed, len(seeds), len(by_enum)))
    print("enumparams: wrote %s" % args.out)
    for enum in sorted(by_enum, key=lambda e: -len(by_enum[e])):
        used = by_enum[enum]
        byref = sum(1 for _, bv in used if not bv)
        print("   %-58s seeds=%-4d funcs=%-4d byref=%d" % (
            enum, len(used), len({a for a, _ in used}), byref))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())