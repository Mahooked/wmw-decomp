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
  kind     mangled | thunk | c

Parameter types are separated with '|' rather than ',' because a type like
``void (*)(int, char)`` contains a comma, and a TSV column has to stay
unambiguous.  ``ret`` is intentionally absent: the ABI does not encode the
return type of a non-template function, so there is nothing truthful to write.

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
        rows.append(
            "\t".join(
                (
                    address,
                    size,
                    mangled,
                    sig.name,
                    "|".join(sig.params),
                    sig.kind,
                )
            )
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# address\tsize\tmangled\tname\tparams\tkind\n")
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
    return 0 if counts["none"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
