"""Query Ghidra's bundled GCC demangler about hand-written manglings.

The real binary answers questions the corpus alone cannot, e.g. whether a
``K`` applied to a builtin enters the substitution table.  Because it is a black
box, the cleanest way to learn a rule is to ask it directly.

    py -3 tools/refprobe.py _ZN3Foo3barERKS_S0_ _ZN3Foo3barINS_3BazEEEv
    py -3 tools/refprobe.py --file names.txt
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXES = [
    Path(r"C:\Users\Mahook\AppData\Local\Temp\opencode\ghidra_12.1.4_PUBLIC\GPL\DemanglerGnu\os\win_x86_64\demangler_gnu_v2_41.exe"),
    Path(r"C:\Users\Mahook\AppData\Local\Temp\opencode\ghidra_12.1.4_PUBLIC\GPL\DemanglerGnu\os\win_x86_64\demangler_gnu_v2_24.exe"),
]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wmwtools import cxxfilt  # noqa: E402


def ask(names: list[str]) -> dict[str, str]:
    exe = next((e for e in EXES if e.is_file()), None)
    if exe is None:
        raise SystemExit("refprobe: bundled demangler not found")
    proc = subprocess.run(
        [str(exe)],
        input="\n".join(names) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    out = [ln.rstrip("\n") for ln in proc.stdout.splitlines()]
    if len(out) != len(names):
        raise SystemExit("refprobe: %d results for %d names" % (len(out), len(names)))
    return dict(zip(names, out))


def main(argv: list[str]) -> int:
    if "--file" in argv:
        path = Path(argv[argv.index("--file") + 1])
        names = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        names = [a for a in argv[1:] if not a.startswith("-")]
    if not names:
        raise SystemExit(__doc__)
    ref = ask(names)
    for n in names:
        want = ref[n]
        got = cxxfilt.demangle(n)
        flag = "ok  " if got == want else ("raw " if got == n else "DIFF")
        print("%s %s" % (flag, n))
        print("     gcc: %s" % want)
        if flag != "ok  ":
            print("     ours: %s" % got)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
