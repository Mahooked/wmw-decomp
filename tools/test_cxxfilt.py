"""Regression test: run the local demangler over the GCC reference corpus.

Every mangled name in out/symbols/reference.tsv must demangle to GCC's own
rendering (whitespace-normalised).  Exits non-zero on any mismatch, so it can
gate a change to wmwtools/cxxfilt.py:

    py -3 tools/test_cxxfilt.py
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
    if not REF.is_file():
        print("test_cxxfilt: missing %s" % REF, file=sys.stderr)
        return 2
    total = matched = 0
    failed: list[str] = []
    for line in REF.open(encoding="utf-8"):
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2 or not parts[0]:
            continue
        mangled, want = parts[0], parts[1]
        total += 1
        try:
            got = cxxfilt.demangle(mangled)
        except Exception as exc:  # a crash is a failure, not an error
            failed.append("%s: raised %s" % (mangled, exc))
            continue
        if norm(got) == norm(want):
            matched += 1
        elif len(failed) < 10:
            failed.append("%s\n  mine: %s\n  gcc : %s" % (mangled, got, want))
    for msg in failed:
        print(msg)
    print("test_cxxfilt: %d/%d match" % (matched, total))
    return 0 if matched == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
