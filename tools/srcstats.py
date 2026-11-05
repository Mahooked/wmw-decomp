"""Count source-layout metrics in decompiled output, for the README table.

Counts, over the .cpp files under <dir> (lines starting with "/*" skipped):
  - f_0x  field accesses rendered as f_0x<offset>
  - DAT_  DAT_<address> placeholder tokens
  - param generic param_N parameter names
  - FUN_/func_0x unresolved call targets (PLT stubs resolve via resolve_refs.py)

The no-layout control and the layout-enabled run come from the same Ghidra
pipeline (fresh import -> DecompileAll); the control adds -nolayout as the
8th script argument so only the layouts differ.

Usage:  py tools/srcstats.py [out-dir]
"""
import argparse
import re
from pathlib import Path

PATTERNS = {
    "f0x": re.compile(r"\bf_0x[0-9a-f]+\b"),
    "dat": re.compile(r"\bDAT_[0-9a-f]+\b"),
    "param": re.compile(r"\bparam_[0-9]+\b"),
    "call": re.compile(r"\b(?:FUN_[0-9a-f]{8}|func_0x[0-9a-f]+)\b"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", type=Path, default=Path("out/src"),
                    help="source directory (default: out/src)")
    args = ap.parse_args()
    root: Path = args.root
    if not root.is_dir():
        ap.error("source directory not found: %s" % root)

    f0x = dat = param = call = files = 0
    for path in root.rglob("*.cpp"):
        files += 1
        with path.open(encoding="utf-8", errors="replace") as source:
            for line in source:
                if line.startswith("/*"):
                    continue
                f0x += len(PATTERNS["f0x"].findall(line))
                dat += len(PATTERNS["dat"].findall(line))
                param += len(PATTERNS["param"].findall(line))
                call += len(PATTERNS["call"].findall(line))
    print("files     %6d" % files)
    print("f_0x      %6d" % f0x)
    print("DAT_      %6d" % dat)
    print("param_N   %6d" % param)
    print("call      %6d" % call)


if __name__ == "__main__":
    main()
