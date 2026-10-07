"""Aggregate enum evidence into declarations and recovered headers.

`tools/enumparams.py` decided which registers hold which enum types and
`tools/ghidra/EnumScan.java` collected the constant comparisons (evidence rows in
`out/types/_enumraw.tsv`).  This pass turns that evidence into a *verdict* the
same way `layout.py` does for struct fields: an enum is declared only when the
sum of the evidence supports it, and everything else is left silent rather than
guessed.

Rules (the verification gate in `tools/check_enums.py` enforces exactly these):

  - "values" enums: the members are the constants the binary compares the type
    against (`cmp`) or stores into enum-typed slots (`store`).  A value must be
    a plausible enumerator (`0 <= v <= 0x7fffffff`; larger values are absolute
    addresses or -1 sentinels and are dropped).  A values enum is *proven* when
    it has both >= 2 distinct values and >= 2 distinct evidence functions --
    the same two-independent-agreeing-readings rule that rejects stray false
    positives elsewhere in the repo.
  - "flags" enums: members are the AND masks (`and`) the binary tests the type
    with.  A mask must be a power of two (a real bit flag); masks like
    `0xff`/`0xff00`/`0xff000000` are byte-rounding of unrelated data and are
    dropped.  A flags enum is *proven* when it has >= 2 power-of-two members;
    the flag members themselves are the enumerators.
  - Single-read functions never prove anything (a lone `cmp e, #0` is a null or
    boolean test, not an enumerator).
  - Names also recovered earlier as *single-field* layouts (a value-typed enum
    reached through a reference reads as `*(int*)p`, i.e. one int at offset 0,
    which is what put e.g. `AnimationEventType` in layouts.tsv) are retracted
    here: the recovered header replaces the fake one-field struct whose file and
    include guard it shares, and enums.tsv records the supersession.

Enumerator *names* are not encoded anywhere in the binary -- only values are.
The mechanical names `E_<Name>_<value>` exist so the output recompiles and the
header stays checkable; recovering the real identifiers is the later re-inference
step the README already reserves.

Inputs: out/types/_enumraw.tsv, out/types/layouts.tsv
Outputs: out/types/enums.tsv, out/types/include/<Ns>/<Name>.h
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "out" / "types" / "_enumraw.tsv"
LAYOUTS = ROOT / "out" / "types" / "layouts.tsv"
OUT = ROOT / "out" / "types" / "enums.tsv"
INCLUDE = ROOT / "out" / "types" / "include"

#: A plausible enumerator.  Larger constants are addresses, pointers or the
#: `-1` sentinel spelled as 0xffffffff, none of which is an enumerator.
MAX_VALUE = 0x7FFFFFFF

#: Third-party namespaces never get game-owned enum headers.
_VENDOR = ("std::", "std::__ndk1::", "ndk::", "FMOD::")


def load_layouts(path: Path):
    """Field counts per class, and the single-field layout suspects.

    Mirrors enumparams.py's reading so the `supersedes` note is consistent.
    """
    fields = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return fields
    for line in lines:
        if line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 4:
            continue
        if f[0] in ("Walaber", "WaterConcept", "WaterConceptConstants"):
            continue
        try:
            fields[f[0]] = int(f[3])
        except ValueError:
            continue
    return fields


def load_evidence(path: Path):
    """Group raw evidence rows by enum name -> list of (value, kind, func)."""
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 5:
            continue
        e, value, kind = f[0], int(f[1], 16), f[2]
        func = f[4]
        rows.setdefault(e, []).append((value, kind, func))
    return rows


def evaluate(name: str, rows, layout_fields: dict):
    """Verdict for one enum: members, kind, and an explainer string."""
    cmp_vals = set()
    cmp_funcs = set()
    and_masks = set()
    for value, kind, func in rows:
        if kind in ("cmp", "store") and 0 <= value <= MAX_VALUE:
            cmp_vals.add(value)
            cmp_funcs.add(func)
        elif kind == "and" and value > 0 and (value & (value - 1)) == 0:
            and_masks.add(value)

    note = []
    if name.startswith(_VENDOR):
        return None, "vendor namespace, skipped"
    # A single-field layout means the value-typed enum was probably read through
    # a reference and mis-filed as a one-int struct; the header is retracted.
    supersedes = layout_fields.get(name) == 1
    if supersedes:
        note.append("supersedes 1-field layout")

    if len(and_masks) >= 2:
        return ("flags", sorted(and_masks)), "; ".join(
            note + ["flags: %d masks, %d distinct" % (len(and_masks), len(and_masks))]
        )

    if len(cmp_vals) >= 2 and len(cmp_funcs) >= 2:
        return ("values", sorted(cmp_vals)), "; ".join(
            note + ["values: %d from %d funcs" % (len(cmp_vals), len(cmp_funcs))]
        )

    return None, "; ".join(
        note + ["insufficient: values=%d funcs=%d masks=%d" % (
            len(cmp_vals), len(cmp_funcs), len(and_masks))]
    )


def header_path(namespace: str, name: str) -> Path:
    parts = namespace.split("::")
    return INCLUDE.joinpath(*parts, name + ".h")


def emit_header(path: Path, name: str, kind: str, members):
    """Write one enum header, replacing a fake struct header if present."""
    ns, base = name.rsplit("::", 1)
    guard = "WMW_" + ns.upper().replace("::", "__") + "__" + base.upper() + "_H"
    lines = [
        "// Recovered from %s by tools/enums.py; the values are the compile-time" % name,
        "// constants the binary compares/stores against this type.",
        "//",
        "// Enumerator names are not encoded in the binary; E_<> = value is a",
        "// placeholder for the re-inference step.",
        "#ifndef %s" % guard,
        "#define %s" % guard,
        "",
    ]
    for band in ns.split("::"):
        lines.append("namespace %s {" % band)
        break
    lines.append("enum %s {" % base)
    for ordinal, v in enumerate(members):
        lines.append("    E_%s_%d = %d," % (base, ordinal, v))
    lines.append("};")
    for band in reversed(ns.split("::")):
        lines.append("}  // namespace %s" % band)
    lines.append("#endif")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    evidence = load_evidence(RAW)
    layout_fields = load_layouts(LAYOUTS)
    proven = {}
    notes = {}
    for name in sorted(evidence):
        verdict, why = evaluate(name, evidence[name], layout_fields)
        if verdict is None:
            notes[name] = why
            continue
        kind, members = verdict
        proven[name] = (kind, members)
        notes[name] = why

    emitted = 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# enum\tkind\tmembers\tvalues\tfuncs\thead\tnote\n")
        for name in sorted(proven):
            kind, members = proven[name]
            vals = " ".join("0x%x" % v for v in members)
            funcs = len({f for _, _, f in evidence[name]})
            ns, base = name.rsplit("::", 1)
            hp = header_path(ns, base)
            fh.write("%s\t%s\t%d\t%s\t%d\t%s\t%s\n" % (
                name, kind, len(members), vals, funcs,
                str(hp.relative_to(INCLUDE)).replace("\\", "/"), notes[name]))
            emit_header(hp, name, kind, members)
            emitted += 1

    print("enums: %d proven enums emitted, %d evaluated, %d unproven" % (
        emitted, len(evidence), len(notes)))
    for name in sorted(proven):
        kind, members = proven[name]
        print("   PROVEN   %-52s %-6s %s" % (
            name, kind, " ".join("0x%x" % v for v in members)))
    for name, why in sorted(notes.items()):
        if "insufficient" in why:
            print("   unproven %s" % name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())