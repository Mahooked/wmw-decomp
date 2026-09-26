#!/usr/bin/env python3
"""Build a reference demangling set from Ghidra's bundled GNU demangler.

Ghidra ships GCC's c++filt as a standalone executable under
GPL/DemanglerGnu/os/<platform>/. It is the closest thing to an authority
available offline, so it is used two ways:

  1. as ground truth to measure tools/wmwtools/cxxfilt.py against, and
  2. as a fallback for symbols the local demangler cannot render.

Two versions are run because GCC 4.1 and GCC 2.24 fail on different
symbols; where they agree, the result is very likely correct.

Usage:
    python tools/refdemangle.py <ghidra-root> --symbols out/symbols/functions.tsv \
        --out out/symbols/reference.tsv
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def candidates(ghidra: Path) -> list[Path]:
    base = ghidra / "GPL" / "DemanglerGnu" / "os"
    found: list[Path] = []
    if base.is_dir():
        found += sorted(p for p in base.rglob("demangler_gnu_*") if p.is_file())
    # Newest first: the higher GCC version handles more of the STL internals.
    found.sort(key=lambda p: p.name, reverse=True)
    return found


def run(exe: Path, names: list[str]) -> dict[str, str]:
    """Pipe every name through one demangler build."""
    payload = "\n".join(names) + "\n"
    try:
        proc = subprocess.run(
            [str(exe)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print("refdemangle: %s: %s" % (exe.name, exc), file=sys.stderr)
        return {}
    out = [ln.rstrip("\n") for ln in proc.stdout.splitlines()]
    if len(out) != len(names):
        print(
            "refdemangle: %s returned %d lines for %d names"
            % (exe.name, len(out), len(names)),
            file=sys.stderr,
        )
        return {}
    return dict(zip(names, out))


def read_names(tsv: Path) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    with tsv.open(encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or len(row) < 3:
                continue
            m = row[2]
            if m.startswith("_Z") and m not in seen:
                seen.add(m)
                names.append(m)
    return names


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ghidra")
    ap.add_argument("--symbols", default="out/symbols/functions.tsv")
    ap.add_argument("--out", default="out/symbols/reference.tsv")
    args = ap.parse_args(argv[1:])

    tsv = Path(args.symbols)
    if not tsv.is_file():
        print("refdemangle: no %s" % tsv, file=sys.stderr)
        return 1
    names = read_names(tsv)
    print("refdemangle: %d distinct mangled names" % len(names))

    exes = candidates(Path(args.ghidra))
    if not exes:
        print("refdemangle: no bundled demangler found", file=sys.stderr)
        return 1

    per_exe: dict[str, dict[str, str]] = {}
    for exe in exes:
        res = run(exe, names)
        if not res:
            continue
        good = sum(1 for n in names if res.get(n, n) != n)
        per_exe[exe.name] = res
        print("refdemangle:   %-28s resolved %d/%d" % (exe.name, good, len(names)))

    # Merge: prefer any build that produced something other than the input.
    merged: dict[str, str] = {}
    agree = 0
    for n in names:
        vals = [r[n] for r in per_exe.values() if n in r and r[n] != n]
        if not vals:
            merged[n] = n
            continue
        if len(set(vals)) == 1:
            agree += 1
        merged[n] = vals[0]
    resolved = sum(1 for n in names if merged[n] != n)
    print(
        "refdemangle: merged %d/%d resolved, %d identical across builds"
        % (resolved, len(names), agree)
    )

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("#\tmangled\treference\n")
        for n in names:
            fh.write("%s\t%s\n" % (n, merged[n]))
    print("refdemangle: wrote %s" % outp)
    (outp.with_suffix(".json")).write_text(
        json.dumps(
            {
                "names": len(names),
                "resolved": resolved,
                "identical_across_builds": agree,
                "builds": sorted(per_exe),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
