"""Count source-layout metrics in decompiled output, for the README table.

Counts, over the .cpp files under <dir> (lines starting with "/*" skipped):
  - f_0x  field accesses rendered as f_0x<offset>
  - DAT_  DAT_<address> placeholder tokens
  - param generic param_N parameter names

The no-layout control and the layout-enabled run come from the same Ghidra
pipeline (fresh import -> DecompileAll); the control adds -nolayout as the
8th script argument so only the layouts differ.

Usage:  py tools/srcstats.py <out-dir>
"""
import os
import re
import sys


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join("out", "src")
    f0x = dat = param = files = 0
    for base, _dirs, names in os.walk(root):
        for name in names:
            if not name.endswith(".cpp"):
                continue
            files += 1
            body = [
                line for line in open(os.path.join(base, name), encoding="utf-8",
                                      errors="replace").read().splitlines()
                if not line.startswith("/*")
            ]
            text = "\n".join(body)
            f0x += len(re.findall(r"\bf_0x[0-9a-f]+\b", text))
            dat += len(re.findall(r"\bDAT_[0-9a-f]+\b", text))
            param += len(re.findall(r"\bparam_[0-9]+\b", text))
    print("files     %6d" % files)
    print("f_0x      %6d" % f0x)
    print("DAT_      %6d" % dat)
    print("param_N   %6d" % param)


if __name__ == "__main__":
    main()