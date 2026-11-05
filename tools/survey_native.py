"""Native code survey for libwmw.so.

Produces the inventory that drives everything downstream:

  out/symbols/functions.tsv   address, size, mangled, demangled
  out/symbols/classes.tsv     one row per RTTI-confirmed class
  out/symbols/summary.json    counts by namespace / class
  out/headers/*.h             reconstructed class headers

The binary is only partially stripped, so the symbol table is the backbone of
the whole decompilation: it names every function and, through the ``_ZTV``/
``_ZTI`` triples, every polymorphic class.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wmwtools.cxxfilt import demangle  # noqa: E402
from wmwtools.elf import ELF, STT_FUNC, STT_OBJECT  # noqa: E402

# Symbol kinds we can tell apart from the demangled prefix.
RE_VTABLE = re.compile(r"^vtable for (.+)$")
RE_TINFO = re.compile(r"^typeinfo for (.+)$")


def split_scope(dem: str) -> tuple[str, str]:
    """Split a demangled name into (owner, member).

    ``Walaber::Widget_Label::reloadFont`` -> ``Walaber::Widget_Label``, ``reloadFont``
    Operators and template noise are kept with the member half.
    """
    # Function templates keep their args; cut at the first '(' that starts the
    # parameter list rather than at '::' inside <> or ().
    depth_paren = 0
    depth_ang = 0
    last_sep = -1
    i = 0
    while i < len(dem):
        c = dem[i]
        if c == "(":
            depth_paren += 1
        elif c == ")":
            depth_paren = max(0, depth_paren - 1)
        elif c == "<":
            depth_ang += 1
        elif c == ">":
            depth_ang = max(0, depth_ang - 1)
        elif c == ":" and depth_paren == 0 and depth_ang == 0:
            if i + 1 < len(dem) and dem[i + 1] == ":":
                last_sep = i
                i += 1
        i += 1
    if last_sep < 0:
        return "", dem
    return dem[:last_sep], dem[last_sep + 2 :]


def build(so_path: str | os.PathLike[str]) -> dict:
    elf = ELF(os.fspath(so_path))

    funcs = []
    data_syms = []
    vtables = []
    tinfos = []

    for sym in elf.symbols("all"):
        if not sym.name:
            continue
        dem = demangle(sym.name) if sym.name.startswith("_Z") else sym.name
        if sym.is_function and sym.value:
            funcs.append((sym.value, sym.size, sym.name, dem))
        elif sym.type == STT_OBJECT and sym.value:
            data_syms.append((sym.value, sym.size, sym.name, dem))
        m = RE_VTABLE.match(dem)
        if m:
            vtables.append((sym.value, sym.size, sym.name, m.group(1)))
            continue
        m = RE_TINFO.match(dem)
        if m:
            tinfos.append((sym.value, sym.size, sym.name, m.group(1)))
            continue
    funcs.sort()

    return dict(
        elf=elf,
        funcs=funcs,
        data_syms=data_syms,
        vtables=vtables,
        tinfos=tinfos,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("so", type=os.fspath, help="path to libwmw.so")
    ap.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out"),
        help="output directory (default: this repository's out/)",
    )
    args = ap.parse_args(argv)
    if not os.path.isfile(args.so):
        ap.error("input shared library not found: %s" % args.so)

    st = build(args.so)
    elf: ELF = st["elf"]
    funcs = st["funcs"]
    out = args.out

    os.makedirs(os.path.join(out, "symbols"), exist_ok=True)

    # ---- functions.tsv -------------------------------------------------
    fp = os.path.join(out, "symbols", "functions.tsv")
    with open(fp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# address\tsize\tmangled\tdemangled\n")
        for addr, size, mn, dm in funcs:
            fh.write("0x%x\t%d\t%s\t%s\n" % (addr, size, mn, dm))
    print("wrote %s (%d functions)" % (fp, len(funcs)))

    # ---- class inventory ---------------------------------------------
    classes: dict[str, dict] = {}
    for addr, size, mn, dem in st["vtables"]:
        classes.setdefault(dem, {"methods": []})["vtable"] = addr
    for addr, size, mn, dem in st["tinfos"]:
        classes.setdefault(dem, {"methods": []})["typeinfo"] = addr

    # methods per class
    for addr, size, mn, dm in funcs:
        owner, member = split_scope(dm)
        if not owner or not member:
            continue
        if owner in classes:
            classes[owner]["methods"].append((addr, size, member, mn))
    for c in classes.values():
        c["methods"].sort()

    cp = os.path.join(out, "symbols", "classes.tsv")
    with open(cp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\tvtable\ttypeinfo\tmethod_symbols\n")
        for dem in sorted(classes):
            c = classes[dem]
            fh.write(
                "%s\t%s\t%s\t%d\n"
                % (
                    dem,
                    hex(c["vtable"]) if c.get("vtable") else "-",
                    hex(c["typeinfo"]) if c.get("typeinfo") else "-",
                    len(c["methods"]),
                )
            )
    print("wrote %s (%d RTTI classes)" % (cp, len(classes)))

    # ---- summary ------------------------------------------------------
    ns = Counter()
    for addr, size, mn, dm in funcs:
        parts = dm.split("::")
        ns[parts[0] if len(parts) > 1 else "<global>"] += 1
    summary = {
        "so": os.path.basename(args.so),
        "so_size": len(elf.data),
        "sections": {s.name: s.size for s in elf.sections if s.name},
        "dynsym_count": len(elf.symbols("dyn")),
        "function_symbols": len(funcs),
        "rtti_classes": len(classes),
        "vtable_symbols": len(st["vtables"]),
        "typeinfo_symbols": len(st["tinfos"]),
        "data_symbols": len(st["data_syms"]),
        "by_namespace": dict(ns.most_common()),
    }
    sp = os.path.join(out, "symbols", "summary.json")
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print("wrote %s" % sp)
    for k, v in summary.items():
        if k not in ("sections", "by_namespace"):
            print("   %-20s %s" % (k, v))
    print("\ntop namespaces:")
    for k, v in ns.most_common(15):
        print("   %-24s %d" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
