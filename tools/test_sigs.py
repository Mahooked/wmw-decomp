"""Regression test: recovered prototypes must match GCC's own rendering.

The Itanium ABI encodes every parameter type in the symbol, and ``cxxfilt``
already prints them, so GCC's demangled rendering is an independent oracle for
the parameter list this repository recovers.  For every C++ function symbol in
``out/symbols/functions.tsv``:

  * the mangling must parse,
  * the recovered parameter list must equal the oracle's, and
  * ``void`` must collapse to no parameters.

Exits non-zero on any disagreement, so it gates changes to
``wmwtools/signature.py``:

    py -3 tools/test_sigs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wmwtools.signature import signature, split_params  # noqa: E402

FUNCS = Path(__file__).resolve().parent.parent / "out" / "symbols" / "functions.tsv"

MAX_REPORTED = 15


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def oracle_params(demangled: str) -> list[str] | None:
    """Pull the parameter list back out of GCC's rendering of the name.

    Returns ``None`` when the rendering has no parameter list at all, which is
    not evidence of a defect -- the oracle simply has nothing to say.
    """
    text = demangled.replace("operator()", "OPERATOR_CALL")
    depth = 0
    start = None
    last = None
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                last = (start, i)
                start = None
    if last is None:
        return None
    a, b = last
    body = text[a + 1:b]
    return split_params(body.replace("OPERATOR_CALL", "operator()"))


def main() -> int:
    if not FUNCS.is_file():
        print("test_sigs: missing %s" % FUNCS, file=sys.stderr)
        return 2

    mangled_total = compared = agree = unparsed = no_oracle = 0
    problems: list[str] = []

    for line in FUNCS.open(encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        mangled, demangled = parts[2], parts[3]
        if not mangled.startswith("_Z"):
            continue
        mangled_total += 1

        sig = signature(mangled)
        if sig is None or sig.kind == "c":
            unparsed += 1
            if len(problems) < MAX_REPORTED:
                problems.append("did not parse: %s" % mangled)
            continue

        want = oracle_params(demangled)
        if want is None:
            no_oracle += 1
            continue

        compared += 1
        if [norm(p) for p in sig.params] == [norm(p) for p in want]:
            agree += 1
        elif len(problems) < MAX_REPORTED:
            problems.append(
                "%s\n  mine: %s\n  gcc : %s"
                % (mangled, sig.params, want)
            )

    for msg in problems:
        print(msg)

    print(
        "test_sigs: %d C++ symbols, %d compared, %d agree, "
        "%d unparsed, %d without oracle (%.3f%%)"
        % (
            mangled_total,
            compared,
            agree,
            unparsed,
            no_oracle,
            100.0 * agree / max(1, compared),
        )
    )
    return 0 if agree == compared and unparsed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
