"""Resolve call-target placeholders in ``out/src`` to real symbol names.

Why this is needed
------------------
``DecompileAll.java`` rebuilds function boundaries from the ELF symbol table
and sweeps the gaps.  That names every function that has a symbol -- but a
shared library built without ``-Bsymbolic`` calls all of its *exported*
functions through the PLT, and a PLT stub carries no symbol of its own.  So
the decompiler sees a branch to an anonymous stub and prints it as
``func_0x00169310(...)`` or ``FUN_0016a330()`` even though the import is fully
named in ``.dynsym``.

This is by far the largest readability defect in the output: of 66,330
call-target placeholders, 64,007 (96%) point at a PLT stub.  A live probe
shows the mapping is exact: the AArch64 PLT stub is

    adrp x16, page(GOT[n])
    ldr  x17, [x16, #imm]
    add  x16, x16, #imm
    br   x17

so the ``adrp``+``ldr`` pair names the GOT slot, ``.rela.plt`` maps that slot
to a ``.dynsym`` index, and ``.dynsym`` gives the mangled name -- which is the
Itanium encoding of the function that is really being called.  No guesswork:
every step is a lookup the linker itself performed.

Two independent facts make the read trustworthy rather than plausible:

  * every PLT entry between the first and the last decodes to a GOT slot that
    ``.rela.plt`` actually contains (4,765 of 4,766; the odd one out is the
    unpadded tail), and
  * the names that result are ordinary: ``operator new``, ``fopen``,
    ``__cxa_uncaught_exceptions``, ``Walaber::ProgrammaticTexture2D::
    ProgrammaticTexture2D``.

What it does
------------
For each ``out/src/**/*.cpp`` it rewrites the placeholder tokens

    FUN_<8hex>        func_0x<hex>

whose address is a PLT stub, to the recovered qualified name (the demangled
symbol with its parameter list stripped, so it reads as a callee rather than a
declaration).  Placeholders that point at a gap function inside ``.text`` are
left untouched -- those genuinely have no symbol.

It also writes ``out/symbols/imports.tsv`` (one row per PLT entry) as the
machine-readable evidence, and ``--check`` re-derives the replacement set and
fails if any resolvable placeholder survives, which is the gate.

This is a post-pass over generated output, not a decompiler change: it is
idempotent, and ``tools/ghidra/DecompileAll.java`` would ideally install the
same names in Ghidra so the disassembly benefits too -- but the naming has to
happen from the relocation table either way, and doing it here keeps the
result reproducible without a Ghidra run.

Usage:
    py tools/resolve_refs.py <libwmw.so> [--src out/src] [--check]
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wmwtools.elf import ELF  # noqa: E402
from wmwtools.signature import signature  # noqa: E402

# AArch64 PLT stub: adrp x16, #imm  ;  ldr x17, [x16, #imm12*8]
_ADRP_MASK, _ADRP_OP = 0x9F000000, 0x90000000
_LDR_MASK, _LDR_OP = 0xFFC00000, 0xF9400000

_PLACEHOLDER = re.compile(r"\b(?:FUN_([0-9a-fA-F]{8})|func_0x([0-9a-fA-F]+))\b")

_HEADER_OLD = "   ELF symbol table in out/symbols/functions.tsv */"
_HEADER_NEW = (
    "   ELF symbol table in out/symbols/functions.tsv; call targets\n"
    "   resolved from PLT imports by tools/resolve_refs.py */"
)


def _qualified(mangled: str) -> str:
    """The callee name for ``mangled``: demangled, minus its parameter list."""
    if not mangled:
        return ""
    # Drop a symbol-version suffix (``memcpy@GLIBC_2.17``) if one is present.
    name = mangled.split("@", 1)[0]
    sig = signature(name)
    if sig is not None and sig.name:
        if sig.name.startswith("raw:"):
            return name
        return sig.name
    return name


def decode_plt_stub(elf: ELF, addr: int):
    """Return the GOT slot an AArch64 PLT stub loads from, or ``None``."""
    data = elf.read(addr, 8)
    if len(data) < 8:
        return None
    w0, w1 = struct.unpack_from("<II", data, 0)
    if (w0 & _ADRP_MASK) != _ADRP_OP:
        return None
    imm = (((w0 >> 5) & 0x7FFFF) << 2) | ((w0 >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    page = (addr & ~0xFFF) + (imm << 12)
    if (w1 & _LDR_MASK) != _LDR_OP:
        return None
    return page + ((w1 >> 10) & 0xFFF) * 8


def build_imports(elf: ELF):
    """(addr -> name) for every PLT stub, plus the provenance rows.

    Returns ``(names, rows, stats)`` where ``rows`` is a list of
    ``(plt_addr, got_slot, symidx, mangled, name)`` and ``stats`` records the
    decode attempts for the report.
    """
    plt = elf.section(".plt")
    if plt is None or plt.size < 32:
        return {}, [], {"plt": 0, "decoded": 0, "bad": 0}
    dynsym = elf.symbols("dyn")
    off2sym = {}
    for r_offset, r_info, _addend in elf.relocs_for(".rela.plt"):
        off2sym[r_offset] = r_info >> 32

    names = {}
    rows = []
    decoded = bad = 0
    for i in range(1, plt.size // 16):
        addr = plt.addr + i * 16
        slot = decode_plt_stub(elf, addr)
        idx = off2sym.get(slot) if slot is not None else None
        if idx is None:
            bad += 1
            continue
        decoded += 1
        mangled = dynsym[idx].name if 0 <= idx < len(dynsym) else ""
        name = _qualified(mangled)
        if not name:
            bad += 1
            continue
        names[addr] = name
        rows.append((addr, slot, idx, mangled, name))
    return names, rows, {"plt": plt.size // 16 - 1, "decoded": decoded, "bad": bad}


def _placeholder_addrs(text: str):
    for m in _PLACEHOLDER.finditer(text):
        yield int(m.group(1) or m.group(2), 16)


def rewrite_file(path: str, names: dict) -> int:
    text = open(path, encoding="utf-8", errors="replace").read()
    hits = sum(1 for a in _placeholder_addrs(text) if a in names)
    if hits == 0:
        return 0

    def sub(m: re.Match) -> str:
        addr = int(m.group(1) or m.group(2), 16)
        return names.get(addr, m.group(0))

    new = _PLACEHOLDER.sub(sub, text)
    if _HEADER_OLD in new:
        new = new.replace(_HEADER_OLD, _HEADER_NEW)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("so", help="path to libwmw.so (arm64-v8a)")
    ap.add_argument("--src", default=os.path.join("out", "src"),
                    help="decompiled tree to rewrite (default: out/src)")
    ap.add_argument("--imports-out",
                    default=os.path.join("out", "symbols", "imports.tsv"))
    ap.add_argument("--check", action="store_true",
                    help="do not write; fail if a resolvable placeholder remains")
    args = ap.parse_args(argv)

    if not os.path.exists(args.so):
        print("resolve_refs: no such file: %s" % args.so, file=sys.stderr)
        return 2

    elf = ELF(args.so)
    names, rows, stats = build_imports(elf)
    print("PLT entries           %6d" % stats["plt"])
    print("  decoded to a import %6d" % stats["decoded"])
    print("  undecodable         %6d" % stats["bad"])
    print("resolvable targets    %6d" % len(names))

    if args.check:
        files = total = unresolved = 0
        for base, _dirs, fnames in os.walk(args.src):
            for name in fnames:
                if not name.endswith(".cpp"):
                    continue
                files += 1
                text = open(os.path.join(base, name), encoding="utf-8",
                            errors="replace").read()
                for addr in _placeholder_addrs(text):
                    total += 1
                    if addr in names:
                        unresolved += 1
        print("check: %d files, %d placeholders, %d resolvable but left"
              % (files, total, unresolved))
        if unresolved:
            print("resolve_refs: FAIL", file=sys.stderr)
            return 1
        print("resolve_refs: ok")
        return 0

    os.makedirs(os.path.dirname(args.imports_out), exist_ok=True)
    with open(args.imports_out, "w", encoding="utf-8", newline="") as fh:
        fh.write("# plt_addr\tgot_slot\tsymidx\tmangled\tname\n")
        for addr, slot, idx, mangled, name in sorted(rows):
            fh.write("0x%x\t0x%x\t%d\t%s\t%s\n" % (addr, slot, idx, mangled, name))

    files = replaced = 0
    for base, _dirs, fnames in os.walk(args.src):
        for name in fnames:
            if not name.endswith(".cpp"):
                continue
            files += 1
            replaced += rewrite_file(os.path.join(base, name), names)
    print("scanned files         %6d" % files)
    print("placeholders replaced %6d" % replaced)
    print("wrote %s" % args.imports_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
