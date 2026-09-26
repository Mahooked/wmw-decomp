#!/usr/bin/env python3
"""Recover C++ class hierarchy and virtual method tables from Itanium RTTI.

The binary still carries full RTTI: one __class_type_info object per class plus
a vtable per polymorphic class. That is enough to rebuild the inheritance graph
and the exact virtual method list, which the decompiler output alone cannot
give you.

Pointer caveat
--------------
libwmw.so is a PIE, so every pointer in .data.rel.ro is zero in the file and
filled in by the dynamic linker. The real value lives in the .rela.dyn addend,
so reads must be relocation aware. Three reloc types matter on AArch64:

    R_AARCH64_RELATIVE (1027)  value = addend                (local symbols)
    R_AARCH64_ABS64    (257)   value = sym.value + addend
    R_AARCH64_GLOB_DAT (1025)  value = sym.value

Anything without a relocation is read straight from the file.

What the mangled name does and does not give us
-----------------------------------------------
Parameter types ARE encoded in the mangled name, so signatures recovered here
are exact -- except for the return type, which Itanium mangling omits. Headers
therefore mark it unknown rather than guessing.

Usage:  py tools/rtti.py <path-to-libwmw.so> [outdir]
"""

from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wmwtools import cxxfilt, elf  # noqa: E402

R_AARCH64_ABS64 = 257
R_AARCH64_GLOB_DAT = 1025
R_AARCH64_RELATIVE = 1027

# Layout constants from the Itanium C++ ABI (__type_info hierarchy).
PTR = 8
TI_VPTR = 0
TI_NAME = 8
SI_BASE = 16          # __si_class_type_info
VMI_FLAGS = 16        # __vmi_class_type_info
VMI_COUNT = 20
VMI_BASES = 24
VMI_ENTRY = 16        # { __class_type_info*, long __offset_flags }

# __offset_flags bit layout.
OF_VIRTUAL_MASK = 0x1
OF_PUBLIC_MASK = 0x2
OF_OFFSET_SHIFT = 8

# A vtable's address point is two words past its start: offset-to-top, then the
# typeinfo pointer that identifies the class the vtable belongs to.
VT_OFFSET_TO_TOP = 0
VT_TYPEINFO = 8
VT_HEADER = PTR * 2

GAME_NAMESPACES = ("Walaber", "WaterConcept")


class Image:
    """Relocation-aware view of the binary's link-time pointer values."""

    def __init__(self, path: str | Path) -> None:
        self.elf = elf.ELF(str(path))
        self.path = str(path)
        self.dynsym = self.elf.symbols("dyn")
        self.relocs: dict[int, int] = {}
        for sec in (".rela.dyn", ".rela.plt"):
            for r_offset, r_info, addend in self.elf.relocs_for(sec):
                rtype = r_info & 0xFFFFFFFF
                symidx = r_info >> 32
                if rtype == R_AARCH64_RELATIVE:
                    value = addend
                elif rtype in (R_AARCH64_ABS64, R_AARCH64_GLOB_DAT):
                    if symidx >= len(self.dynsym):
                        continue
                    base = self.dynsym[symidx].value
                    value = base + addend if rtype == R_AARCH64_ABS64 else base
                else:
                    continue
                # A reloc wins over file bytes: the bytes are zero pre-link.
                self.relocs[r_offset] = value

    def ptr(self, vaddr: int) -> int:
        if vaddr in self.relocs:
            return self.relocs[vaddr]
        return self.elf.u64_at(vaddr)

    def sptr(self, vaddr: int) -> int:
        v = self.ptr(vaddr)
        return v - (1 << 64) if v >= (1 << 63) else v

    def u32(self, vaddr: int) -> int:
        return self.elf.u32_at(vaddr)

    def cstr(self, vaddr: int) -> str:
        if not vaddr or self.elf.section_for_vaddr(vaddr) is None:
            return ""
        try:
            return self.elf.cstring_at(vaddr)
        except Exception:
            return ""


def type_name(encoding: str) -> str:
    """Turn an Itanium type encoding into a readable type name.

    cxxfilt.demangle leaves a bare type encoding alone, but it does understand
    the _ZTS spelling, so route through that. Non-class encodings (builtin and
    typedef types) have no _ZTS form and are returned as-is.
    """
    if not encoding:
        return "?"
    if encoding.startswith("N") or encoding.startswith("S"):
        try:
            out = cxxfilt.demangle("_ZTS" + encoding)
        except Exception:
            return encoding
        marker = "typeinfo name for "
        if marker in out:
            return out.split(marker, 1)[1]
        return out
    return encoding


def split_signature(demangled: str) -> tuple[str, str, str]:
    """Split a demangled symbol into (qualified owner, name, parameters)."""
    head, _, rest = demangled.partition("(")
    params = rest[:-1] if rest.endswith(")") else rest
    if "::" in head:
        owner, _, name = head.rpartition("::")
    else:
        owner, name = "", head
    return owner, name, (params if params.strip() else "void")


class ClassInfo:
    def __init__(self, ti_addr: int, ti_size: int) -> None:
        self.ti_addr = ti_addr
        self.ti_size = ti_size
        self.name = "?"
        self.kind = "class"
        self.vtable = 0
        self.vtable_size = 0
        self.bases: list[dict] = []
        self.vtables: list[dict] = []
        self.vfuncs: list[dict] = []

    @property
    def namespace(self) -> str:
        return self.name.split("::", 1)[0] if "::" in self.name else ""

    def primary_base(self) -> "ClassInfo | None":
        for b in self.bases:
            if b["public"] and not b["virtual"]:
                return b["_ref"]
        return None


def collect_typeinfo(img: Image) -> dict[int, ClassInfo]:
    """Map typeinfo address -> ClassInfo for every _ZTI object."""
    kind_by_vptr: dict[int, str] = {}
    for sym in img.elf.symbols():
        if not sym.name.startswith("_ZTVN10__cxxabiv1"):
            continue
        for suffix, kind in (
            ("__vmi_class_type_infoE", "vmi"),
            ("__si_class_type_infoE", "si"),
            ("__class_type_infoE", "class"),
        ):
            if sym.name.endswith(suffix):
                kind_by_vptr[sym.value + VT_HEADER] = kind

    # The vtable symbol spells the same type, with a _ZTV prefix instead of
    # _ZTI, so pair them up by name rather than by address.
    vtables = {
        s.name: (s.value, s.size)
        for s in img.elf.symbols()
        if s.name.startswith("_ZTV") and s.value and not s.is_undefined
    }

    classes: dict[int, ClassInfo] = {}
    for sym in img.elf.symbols():
        if not sym.name.startswith("_ZTI") or sym.name.startswith("_ZTIN10__cxxabiv1"):
            continue
        if not sym.value or sym.is_undefined:
            continue
        info = ClassInfo(sym.value, sym.size)
        vptr = img.ptr(sym.value + TI_VPTR)
        info.kind = kind_by_vptr.get(vptr, "class")
        info.name = type_name(img.cstr(img.ptr(sym.value + TI_NAME)))
        hit = vtables.get("_ZTV" + sym.name[4:])
        if hit:
            info.vtable, info.vtable_size = hit
        classes[sym.value] = info
    return classes


def attach_bases(img: Image, classes: dict[int, ClassInfo]) -> None:
    for info in classes.values():
        try:
            if info.kind == "si":
                base_ti = img.ptr(info.ti_addr + SI_BASE)
                info.bases.append(
                    {
                        "ti": base_ti,
                        "offset": 0,
                        "virtual": False,
                        "public": True,
                        "_ref": classes.get(base_ti),
                    }
                )
            elif info.kind == "vmi":
                count = img.u32(info.ti_addr + VMI_COUNT)
                if count > 256:  # corrupt; refuse rather than walk off
                    continue
                for i in range(count):
                    entry = info.ti_addr + VMI_BASES + i * VMI_ENTRY
                    base_ti = img.ptr(entry)
                    offset_flags = img.sptr(entry + PTR)
                    info.bases.append(
                        {
                            "ti": base_ti,
                            "offset": offset_flags >> OF_OFFSET_SHIFT,
                            "virtual": bool(offset_flags & OF_VIRTUAL_MASK),
                            "public": bool(offset_flags & OF_PUBLIC_MASK),
                            "_ref": classes.get(base_ti),
                        }
                    )
        except Exception:
            continue


def demangler_stats(img: Image) -> dict:
    """How much of the C++ surface the local demangler actually renders.

    Recorded so the limitation is visible in the artifact rather than implied.
    The known weak spot is deep template-argument substitution: instantiations
    of std::__ndk1::__tree and of Walaber::SharedPtr with nested template
    arguments either stay mangled or resolve S<n>_ to the wrong entry.
    """
    text_lo, text_hi = img.elf.text_range() or (0, 0)
    game = total = readable = with_params = 0
    for sym in img.elf.symbols("dyn"):
        if not sym.is_function or not sym.name.startswith("_Z"):
            continue
        if not (text_lo <= sym.value < text_hi):
            continue
        if not any(ns in sym.name for ns in GAME_NAMESPACES):
            continue
        total += 1
        game += 1
        try:
            dem = cxxfilt.demangle(sym.name)
        except Exception:
            continue
        if dem != sym.name:
            readable += 1
            if "(" in dem:
                with_params += 1
    return {
        "game_cxx_symbols": total,
        "demangled": readable,
        "with_parameter_list": with_params,
        "left_mangled": total - readable,
        "known_weakness": "std::__ndk1::__tree and SharedPtr template substitutions",
    }


def address_map(img: Image) -> dict[int, str]:
    """Function address -> mangled name, preferring dynamic symbols."""
    out: dict[int, str] = {}
    for sym in img.elf.symbols():
        if sym.is_function and sym.value and not sym.name.startswith("_ZTI"):
            out.setdefault(sym.value, sym.name)
    return out


def load_gnu_names(path: Path) -> dict[int, str]:
    """Address -> GNU-demangled name, from tools/ghidra/ExportSymbols.java.

    Ghidra's demangler is the authority where it is available. This file is
    optional: without it the from-scratch demangler is used, which handles most
    symbols but not the template-argument substitutions (see validate_demangler).
    """
    out: dict[int, str] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or "\t" not in line:
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            try:
                addr = int(parts[0], 16)
            except ValueError:
                continue
            if parts[3]:
                out[addr] = parts[3]
    return out


def _norm_name(s: str) -> str:
    """Normalise the presentation differences between the two renderers.

    Ghidra writes 'std::__ndk1::' inline, spells the const qualifier
    'Language_const' instead of 'Language const', and writes 'unsigned_int'.
    """
    s = s.replace("std::__ndk1::", "").replace("_const", "const")
    s = s.replace("unsigned_int", "unsigned").replace(" ", "")
    return s


def validate_demangler(gnu: dict[int, str], addr_to_sym: dict[int, str]) -> dict:
    """Cross-check the local demangler against Ghidra's stored symbol names.

    This is a sanity check, not ground truth. Ghidra's ELF importer stores only
    the demangled *name* for a symbol -- no return type, no parameter list -- so
    the only fair comparison is whether Ghidra's name appears as a suffix of the
    locally rendered one. The sample is also biased: it is almost entirely
    std::__ndk1 internals, the hardest substitution cases, so the absolute
    numbers understate the demangler on ordinary game code. See
    demangler_coverage for the figure that matters.
    """
    agree = differ = unparsed = 0
    examples: list[str] = []
    for addr, theirs in gnu.items():
        mangle = addr_to_sym.get(addr)
        if not mangle:
            continue
        try:
            mine = cxxfilt.demangle(mangle)
        except Exception:
            mine = ""
        if not mine or mine == mangle:
            unparsed += 1
            continue
        if _norm_name(theirs) in _norm_name(mine):
            agree += 1
        else:
            differ += 1
            if len(examples) < 6:
                examples.append("substitution differs: %s" % mangle[:58])
    return {
        "oracle": "ghidra symbol table (name only, std::__ndk1 biased)",
        "compared": agree + differ + unparsed,
        "name_agrees": agree,
        "name_differs": differ,
        "unparsed": unparsed,
        "examples": examples,
    }


def attach_vtables(
    img: Image,
    classes: dict[int, ClassInfo],
    addr_to_sym: dict[int, str],
    gnu: dict[int, str] | None = None,
) -> None:
    """Read each class's primary vtable.

    The ABI puts the primary vtable first in the _ZTV blob: an offset-to-top of
    zero, then the typeinfo pointer for the most-derived class, then the
    virtual function pointers. Anchoring on that fixed position rather than
    scanning for typeinfo pointers matters -- a scan runs straight into the
    neighbouring classes' vtables, which sit back to back in .data.rel.ro, and
    attributes their methods to the wrong class.

    Secondary vtables (one per non-primary base, plus thunk groups for virtual
    inheritance) are skipped on purpose. They hold thunks and base-class
    overrides, and the inheritance graph already records the bases.
    """
    text_lo, text_hi = img.elf.text_range() or (0, 0)
    max_slots = 512
    gnu = gnu or {}

    for info in classes.values():
        if not info.vtable:
            continue
        hdr = info.vtable + VT_TYPEINFO
        if img.ptr(hdr) != info.ti_addr:
            continue  # no primary vtable for this class

        count = 0
        while count < max_slots:
            a = img.ptr(hdr + PTR + count * PTR)
            if not (text_lo <= a < text_hi):
                break
            count += 1
        if not count:
            continue

        info.vtables.append(
            {
                "index": 0,
                "header": info.vtable,
                "typeinfo": info.ti_addr,
                "offset_to_top": img.sptr(info.vtable),
                "count": count,
            }
        )
        for i in range(count):
            slot_addr = hdr + PTR + i * PTR
            a = img.ptr(slot_addr)
            mangle = addr_to_sym.get(a, "")
            # The local demangler is used for the signature. Ghidra's symbol
            # table is not an authority here: for ELF imports it stores only the
            # bare demangled *name* (no return type, no parameters), and it
            # misresolves some template substitutions ("unsigned_int",
            # "int_const&", a dropped "std::__ndk1::" qualifier). Losing the
            # parameter list would be a downgrade, so gnu is only a cross-check.
            try:
                demangled = cxxfilt.demangle(mangle) if mangle else ""
            except Exception:
                demangled = ""
            info.vfuncs.append(
                {
                    "vtable": 0,
                    "slot": i,
                    "offset_to_top": 0,
                    "address": a,
                    "mangled": mangle,
                    "demangled": demangled,
                }
            )


def base_name(ref: ClassInfo | None, fallback: int) -> str:
    if ref is not None and ref.name != "?":
        return ref.name
    return "typeinfo@0x%x" % fallback


_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]")


def safe_filename(name: str) -> str:
    """Template instantiations put <, >, , and spaces in class names."""
    return _UNSAFE.sub("_", name)


def write_reports(
    out: Path,
    classes: dict[int, ClassInfo],
    img: Image,
    demangler: dict | None = None,
) -> tuple[int, int, int]:
    out.mkdir(parents=True, exist_ok=True)
    ordered = sorted(classes.values(), key=lambda c: c.name)
    game = [c for c in ordered if c.namespace in GAME_NAMESPACES]

    # -- hierarchy.tsv ---------------------------------------------------
    hp = out / "hierarchy.tsv"
    total_bases = 0
    with hp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\ttypeinfo\tkind\tvtable\tbases\tdetails\n")
        for c in ordered:
            parts = []
            for b in c.bases:
                total_bases += 1
                parts.append(
                    "%s%s@%d%s"
                    % (
                        "" if b["public"] else "non-public ",
                        base_name(b["_ref"], b["ti"]),
                        b["offset"],
                        " virtual" if b["virtual"] else "",
                    )
                )
            fh.write(
                "%s\t0x%x\t%s\t0x%x\t%d\t%s\n"
                % (
                    c.name,
                    c.ti_addr,
                    c.kind,
                    c.vtable,
                    len(c.bases),
                    "; ".join(parts),
                )
            )

    # -- vtables.tsv ----------------------------------------------------
    vp = out / "vtables.tsv"
    total_vfuncs = 0
    with vp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# class\tvtable\toffset_to_top\tslot\taddress\tmangled\tdemangled\n"
        )
        for c in ordered:
            for v in c.vfuncs:
                total_vfuncs += 1
                fh.write(
                    "%s\t%d\t%d\t%d\t0x%x\t%s\t%s\n"
                    % (
                        c.name,
                        v["vtable"],
                        v["offset_to_top"],
                        v["slot"],
                        v["address"],
                        v["mangled"],
                        v["demangled"],
                    )
                )

    # -- headers --------------------------------------------------------
    hd = out / "headers"
    if hd.exists():
        for old in hd.glob("*.hpp"):
            old.unlink()
    hd.mkdir(parents=True, exist_ok=True)
    for c in game:
        if not c.vfuncs:
            continue
        base = c.primary_base()
        decl = " : public %s" % base_name(base, 0) if base else ""
        lines = [
            "// Generated by tools/rtti.py -- do not edit by hand.",
            "// Inheritance and the virtual method list come from the binary's RTTI",
            "// and vtables, so they are exact. Return types are not encoded in the",
            "// Itanium mangling and are marked /*ret*/; fill them in by hand.",
            "#pragma once",
            "",
            "namespace %s {" % c.namespace,
            "",
            "class %s%s {" % (c.name.split("::", 1)[1], decl),
        ]
        for b in c.bases:
            if not b["public"]:
                lines.append(
                    "  // non-public base: %s (offset %d)"
                    % (base_name(b["_ref"], b["ti"]), b["offset"])
                )
        lines.append("public:")
        by_vtable: dict[int, list[dict]] = defaultdict(list)
        for v in c.vfuncs:
            by_vtable[v["vtable"]].append(v)
        for vt_index in sorted(by_vtable):
            if vt_index != 0:
                lines.append(
                    "  // vtable %d: subobject at offset %d"
                    % (vt_index, by_vtable[vt_index][0]["offset_to_top"])
                )
            for v in by_vtable[vt_index]:
                if v["demangled"]:
                    _, nm, params = split_signature(v["demangled"])
                    owner_ok = v["demangled"].startswith(c.name + "::")
                    label = nm if owner_ok else "v%d_%s" % (v["slot"], nm)
                else:
                    params = "/* unknown */"
                    label = "v%d" % v["slot"]
                lines.append(
                    "  virtual /*ret*/ void %s(%s);  // 0x%x%s"
                    % (
                        label,
                        params,
                        v["address"],
                        "" if v["mangled"] else " (no symbol)",
                    )
                )
        lines += ["};", "", "}  // namespace %s" % c.namespace, ""]
        (hd / (safe_filename(c.name.replace("::", "_")) + ".hpp")).write_text(
            "\n".join(lines), encoding="utf-8", newline="\n"
        )

    # -- summary.json ---------------------------------------------------
    ns_count: dict[str, int] = defaultdict(int)
    ns_vfuncs: dict[str, int] = defaultdict(int)
    for c in ordered:
        ns_count[c.namespace or "(global)"] += 1
        ns_vfuncs[c.namespace or "(global)"] += len(c.vfuncs)
    derived = sum(1 for c in ordered if c.bases)
    summary = {
        "binary": Path(img.path).name,
        "classes": len(ordered),
        "game_classes": len(game),
        "with_bases": derived,
        "polymorphic": sum(1 for c in ordered if c.vfuncs),
        "base_edges": total_bases,
        "virtual_functions": total_vfuncs,
        "by_namespace": dict(sorted(ns_count.items(), key=lambda kv: -kv[1])),
        "vfuncs_by_namespace": dict(
            sorted(ns_vfuncs.items(), key=lambda kv: -kv[1])
        ),
    }
    if demangler is not None:
        summary["demangler_check"] = demangler
    summary["demangler_coverage"] = demangler_stats(img)
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return len(ordered), derived, total_vfuncs


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    lib = argv[1]
    out = Path(argv[2]) if len(argv) > 2 else Path("out/rtti")
    gnu_path = Path(argv[3]) if len(argv) > 3 else out.parent / "symbols" / "gnu_symbols.tsv"
    if not Path(lib).is_file():
        print("rtti: no such file: %s" % lib, file=sys.stderr)
        return 1

    img = Image(lib)
    classes = collect_typeinfo(img)
    attach_bases(img, classes)
    addr_to_sym = address_map(img)
    gnu = load_gnu_names(gnu_path)
    if gnu:
        print("rtti: %d GNU-demangled names from %s" % (len(gnu), gnu_path))
    check = validate_demangler(gnu, addr_to_sym) if gnu else None
    if check:
        print(
            "rtti: name cross-check vs Ghidra: %d agree, %d differ, %d unparsed"
            % (check["name_agrees"], check["name_differs"], check["unparsed"])
        )
    attach_vtables(img, classes, addr_to_sym, gnu)
    n, derived, nvf = write_reports(out, classes, img, check)

    print("rtti: %d classes (%d with bases, %d virtual functions)" % (n, derived, nvf))
    print("rtti: wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
