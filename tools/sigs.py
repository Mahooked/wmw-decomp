"""Emit the prototype tables ``out/symbols/signatures.tsv`` and ``classnames.txt``.

``functions.tsv`` already carries the demangled name, which *contains* the exact
parameter types.  What is missing is the parameter list in a form a Ghidra
script can use: ``DecompileAll.java`` cannot run Python, so the prototypes are
precomputed here and read back as a table.

``signatures.tsv`` columns:

  address  entry point, matching functions.tsv
  size     ELF st_size
  mangled  the .dynsym name
  name     qualified name with the parameter list removed
  params   parameter types, '|'-separated (they contain commas)
  gtype    the same list, normalised for Ghidra's C parser
  notes    '|'-separated flags for any lossy rewrite applied to gtype
  kind     mangled | thunk | c

Parameter types are separated with '|' rather than ',' because a type like
``void (*)(int, char)`` contains a comma, and a TSV column has to stay
unambiguous.  ``ret`` is intentionally absent: the ABI does not encode the
return type of a non-template function, so there is nothing truthful to write.

A second, normalised column is written for Ghidra: ``gtype`` is the same type
with the parts its C parser cannot express removed, so a prototype is rejected
far less often.  Two rewrites apply, and both are measured losses rather than
guesses:

``const``
    Ghidra's parser rejects ``const`` in *any* position, including
    ``int const`` ("Can't resolve datatype: const"), so a const-qualified
    parameter is written without it.  The qualifier is carried in ``params``
    and in the emitted prototype comments; only the Ghidra-facing column drops
    it.  2,593 of 9,952 parameters are affected.

``T &``
    A reference is silently degraded to a by-value type, which under AArch64 is
    actively wrong rather than merely imprecise.  Every reference is therefore
    emitted as ``T *``.  For the pointer-shaped references this is exactly what
    was passed; for the others it is the closest honest approximation and is
    flagged in the ``notes`` column.

Neither rewrite invents structure: a template type is passed through unchanged
so the parser rejects it, because a fabricated stand-in would silently change
the meaning of the signature.

``classnames.txt`` is the set of project class names that appear as parameter
types.  These are the names Ghidra is given an opaque structure for, because its
C parser cannot resolve ``Walaber::Vector2 *`` otherwise.  They come from the
parameter types rather than from ``classes.tsv``, which is built from RTTI and so
only knows the *polymorphic* classes -- ``Walaber::Vector2``, 366 parameters
worth, has no vtable and never appears there.

    py -3 tools/sigs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wmwtools.signature import signature  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FUNCS = ROOT / "out" / "symbols" / "functions.tsv"
OUT = ROOT / "out" / "symbols" / "signatures.tsv"
CLASSES = ROOT / "out" / "symbols" / "classnames.txt"

# A plain qualified name: no template arguments, no pointer or reference.
CLASS_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)+$")

# Ghidra's C parser has two measured limitations that this table works around.
# Each rewrite is recorded in the notes column so the loss is visible rather than
# silent. See the module docstring.
# GCC renders the qualifier postfix, as in "Walaber::Vector2 const&", and the
# pre-C++11 form "const int" also appears in template arguments. Both have to go,
# so match the keyword as a standalone word in either position.
_CONST = re.compile(r"\bconst\b\s*")


def ghidra_type(t: str) -> tuple[str, str]:
    """Normalise one recovered type for Ghidra's C parser.

    Returns (type, note) where note is "" when the type passed through unchanged.
    """
    notes = []
    out = t
    # "char const*", "int const&" and "const int" all become "char *" / "int *".
    new = _CONST.sub("", out)
    if new != out:
        notes.append("const-stripped")
        out = new
    if "&" in out:
        # A reference is mis-typed as by-value by the parser, which is wrong on
        # AArch64; a pointer is the closest correct approximation.
        notes.append("ref-as-ptr")
        out = out.replace("&", "*")
    out = re.sub(r"\s+", " ", out).strip()
    # A dropped const can leave "* *" or a space before the star; neither parses.
    out = out.replace("* *", "**")
    out = re.sub(r"\s+\*", "*", out)
    return out, "|".join(notes)


def class_names(params: list[str]) -> set[str]:
    out = set()
    for t in params:
        base = t.replace("*", "").replace("&", "").strip()
        if CLASS_NAME.match(base):
            out.add(base)
    return out


def main() -> int:
    if not FUNCS.is_file():
        print("sigs: missing %s" % FUNCS, file=sys.stderr)
        return 2

    rows = []
    counts = {"mangled": 0, "thunk": 0, "c": 0, "none": 0}
    params_total = 0
    with_param_types = 0
    classes: set[str] = set()
    note_counts: dict[str, int] = {}

    for line in FUNCS.open(encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3 or not parts[0]:
            continue
        address, size, mangled = parts[0], parts[1], parts[2]
        sig = signature(mangled)
        if sig is None:
            counts["none"] += 1
            continue
        counts[sig.kind] += 1
        params_total += len(sig.params)
        if sig.params:
            with_param_types += 1
        classes |= class_names(sig.params)
        gtypes = []
        notes = []
        for p in sig.params:
            g, n = ghidra_type(p)
            gtypes.append(g)
            notes.append(n)
            for flag in (x for x in n.split("|") if x):
                note_counts[flag] = note_counts.get(flag, 0) + 1
        rows.append(
            "\t".join(
                (
                    address,
                    size,
                    mangled,
                    sig.name,
                    "|".join(sig.params),
                    "|".join(gtypes),
                    "|".join(notes),
                    sig.kind,
                )
            )
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# address\tsize\tmangled\tname\tparams\tgtype\tnotes\tkind\n"
        )
        for row in rows:
            fh.write(row + "\n")

    with CLASSES.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class names appearing as parameter types\n")
        for name in sorted(classes):
            fh.write(name + "\n")

    print(
        "sigs: %d symbols -> %s (%d mangled, %d thunk, %d C, %d unresolved)"
        % (
            len(rows),
            OUT.relative_to(ROOT),
            counts["mangled"],
            counts["thunk"],
            counts["c"],
            counts["none"],
        )
    )
    print(
        "sigs: %d parameters recovered across %d symbols that take arguments"
        % (params_total, with_param_types)
    )
    print("sigs: %d distinct class types -> %s" % (len(classes), CLASSES.relative_to(ROOT)))
    if note_counts:
        detail = ", ".join(
            "%s %d" % (k, v) for k, v in sorted(note_counts.items())
        )
        print("sigs: gtype rewrites applied to parameters: %s" % detail)
    return 0 if counts["none"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
