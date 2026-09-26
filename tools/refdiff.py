"""Compare the local demangler against the bundled GCC oracle, one prefix at a
time, and report the first divergence point for each mismatch.

    py -3 tools/refdiff.py <prefix> [count]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wmwtools import cxxfilt  # noqa: E402

REF = Path(__file__).resolve().parent.parent / "out" / "symbols" / "reference.tsv"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main() -> int:
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    shown = 0
    matched = 0
    total = 0
    for line in REF.open(encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2 or not parts[0].startswith(prefix):
            continue
        mangled, want = parts[0], parts[1]
        total += 1
        got = cxxfilt.demangle(mangled)
        if norm(got) == norm(want):
            matched += 1
            continue
        if shown >= limit:
            continue
        shown += 1
        a, b = norm(got), norm(want)
        i = next(
            (i for i in range(min(len(a), len(b))) if a[i] != b[i]),
            min(len(a), len(b)),
        )
        print("M   : %s" % mangled)
        print("mine: %s" % got)
        print("ref : %s" % want)
        print("  diverges at %d" % i)
        print("  mine |%s|" % a[max(0, i - 45) : i + 55])
        print("  ref  |%s|" % b[max(0, i - 45) : i + 55])
        print()
    print("prefix %r: %d/%d match (%.1f%%)" % (prefix, matched, total, 100.0 * matched / max(total, 1)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
