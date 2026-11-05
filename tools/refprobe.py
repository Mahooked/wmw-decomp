r"""Query Ghidra's bundled GCC demangler about hand-written manglings.

The real binary answers questions the corpus alone cannot, e.g. whether a
``K`` applied to a builtin enters the substitution table.  Because it is a black
box, the cleanest way to learn a rule is to ask it directly.

    py -3 tools/refprobe.py --ghidra C:\path\to\ghidra_12.1.4_PUBLIC _ZN3Foo3barERKS_S0_
    py -3 tools/refprobe.py --exe C:\path\to\demangler_gnu_v2_41.exe --file names.txt
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wmwtools import cxxfilt  # noqa: E402
from refdemangle import candidates  # noqa: E402


def ask(names: list[str], exe: Path) -> dict[str, str]:
    try:
        proc = subprocess.run(
            [str(exe)],
            input="\n".join(names) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit("refprobe: %s: %s" % (exe, exc)) from exc
    if proc.returncode:
        detail = proc.stderr.strip() or "exit code %d" % proc.returncode
        raise SystemExit("refprobe: %s: %s" % (exe.name, detail))
    out = [ln.rstrip("\n") for ln in proc.stdout.splitlines()]
    if len(out) != len(names):
        raise SystemExit("refprobe: %d results for %d names" % (len(out), len(names)))
    return dict(zip(names, out))


def host_candidates(ghidra: Path) -> list[Path]:
    os_prefix = {"win32": "win_", "linux": "linux_", "darwin": "mac_"}.get(sys.platform)
    if not os_prefix:
        return []
    machine = platform.machine().lower()
    arch = "arm_64" if machine in ("arm64", "aarch64") else "x86_64"
    return [
        exe for exe in candidates(ghidra)
        if exe.parent.name.startswith(os_prefix) and arch in exe.parent.name
    ]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*", help="mangled names to probe")
    ap.add_argument("--file", type=Path, help="read mangled names, one per line")
    ap.add_argument(
        "--ghidra", type=Path,
        default=os.environ.get("GHIDRA_INSTALL_DIR") or os.environ.get("GHIDRA_HOME"),
        help="Ghidra install directory (default: GHIDRA_INSTALL_DIR or GHIDRA_HOME)",
    )
    ap.add_argument("--exe", type=Path, help="use this demangler executable directly")
    args = ap.parse_args(argv[1:])
    if args.file and args.names:
        ap.error("use positional names or --file, not both")
    names = (
        [ln.strip() for ln in args.file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if args.file else args.names
    )
    if not names:
        ap.error("provide one or more names, or use --file")
    exes = [args.exe] if args.exe else host_candidates(Path(args.ghidra)) if args.ghidra else []
    exe = next((e for e in exes if e.is_file()), None)
    if exe is None:
        ap.error("demangler not found; pass --ghidra, --exe, or set GHIDRA_INSTALL_DIR")
    ref = ask(names, exe)
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
