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

import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wmwtools.cxxfilt import demangle  # noqa: E402
from wmwtools.elf import ELF, STT_FUNC, STT_OBJECT  # noqa: E402

# Symbol kinds we can tell apart from the demangled prefix.
RE_VTABLE = re.compile(r"^vtable for (.+)$")
RE_TINFO = re.compile(r"^typeinfo for (.+)$")
RE_TNAME = re.compile(r"^typeinfo name for (.+)$")
RE_VTT = re.compile(r"^VTT for (.+)$")
RE_CTOR = re.compile(r"^.+::(~?[A-Za-z_][A-Za-z0-9_]*)(\(.*\))?( const)?$")


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


def is_ctor_like(member: str, owner: str) -> bool:
    """True for constructors, destructors, and the C1/C2/D0 manglings of both."""
    base = owner.split("<")[0]
    simple = base.rpartition("::")[2]
    if not simple:
        return False
    return member in (simple, "~" + simple)


def build(vaddr_base_shift: int = 0) -> dict:
    so = SO_PATH
    elf = ELF(so)

    funcs = []
    data_syms = []
    vtables = []
    tinfos = []
    tnames = []
    vtts = []

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
        m = RE_TNAME.match(dem)
        if m:
            tnames.append((sym.value, sym.size, sym.name, m.group(1)))
            continue
        m = RE_VTT.match(dem)
        if m:
            vtts.append((sym.value, sym.size, sym.name, m.group(1)))

    funcs.sort()
    # index by start address for later address->symbol lookups
    by_addr = {a: (a, sz, mn, dm) for a, sz, mn, dm in funcs}

    return dict(
        elf=elf,
        funcs=funcs,
        by_addr=by_addr,
        data_syms=data_syms,
        vtables=vtables,
        tinfos=tinfos,
        tnames=tnames,
        vtts=vtts,
    )


SO_PATH = r"C:\Users\Mahook\AppData\Local\Temp\opencode\wmw\lib\arm64-v8a\libwmw.so"
OUT = r"C:\AIC\wmw-decomp\out"


def main() -> int:
    st = build()
    elf: ELF = st["elf"]
    funcs = st["funcs"]

    os.makedirs(os.path.join(OUT, "symbols"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "headers"), exist_ok=True)

    # ---- functions.tsv -------------------------------------------------
    fp = os.path.join(OUT, "symbols", "functions.tsv")
    with open(fp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# address\tsize\tmangled\tdemangled\n")
        for addr, size, mn, dm in funcs:
            fh.write("0x%x\t%d\t%s\t%s\n" % (addr, size, mn, dm))
    print("wrote %s (%d functions)" % (fp, len(funcs)))

    # ---- class inventory ---------------------------------------------
    classes: dict[str, dict] = {}
    for addr, size, mn, dem in st["vtables"] + st["tinfos"]:
        e = classes.setdefault(
            dem, {"vtable": None, "typeinfo": None, "methods": [], "sizes": []}
        )
        if RE_TINFO.match("typeinfo for " + dem) or dem in [d for _, _, _, d in st["tinfos"]]:
            pass
    for addr, size, mn, dem in st["vtables"]:
        classes.setdefault(dem, {})["vtable"] = addr
    for addr, size, mn, dem in st["tinfos"]:
        classes.setdefault(dem, {})["typeinfo"] = addr

    # methods per class
    for addr, size, mn, dm in funcs:
        owner, member = split_scope(dm)
        if not owner or not member:
            continue
        if owner in classes:
            classes[owner]["methods"].append((addr, size, member, mn))
    for c in classes.values():
        c["methods"].sort()

    cp = os.path.join(OUT, "symbols", "classes.tsv")
    with open(cp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\tvtable\t typeinfo\tvfunc_symbols\tmethod_symbols\n")
        for dem in sorted(classes):
            c = classes[dem]
            fh.write(
                "%s\t%s\t%s\t%d\t%d\n"
                % (
                    dem,
                    hex(c["vtable"]) if c.get("vtable") else "-",
                    hex(c["typeinfo"]) if c.get("typeinfo") else "-",
                    len(c["methods"]),
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
        "so": os.path.basename(SO_PATH),
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
    sp = os.path.join(OUT, "symbols", "summary.json")
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
