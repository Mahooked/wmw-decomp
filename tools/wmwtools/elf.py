"""Minimal, dependency-free ELF64 reader.

Written for reverse-engineering libwmw.so from Where's My Water? (Android).
Supports both endiannesses, and knows how to translate virtual addresses to
file offsets using the program headers (which matters for the .so, whose
section addresses are not contiguous with the file layout).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Iterator

SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_NOBITS = 8
SHT_REL = 9
SHT_DYNSYM = 11
SHT_INIT_ARRAY = 14
SHT_FINI_ARRAY = 15
SHT_GNU_HASH = 0x6FFFFFF6
SHT_GNU_VERSYM = 0x6FFFFFFF
SHT_GNU_VERNEED = 0x6FFFFFFE

STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2
STT_SECTION = 3
STT_FILE = 4
STT_COMMON = 5
STT_TLS = 6
STT_GNU_IFUNC = 10

PT_LOAD = 1

# ARM64 relocations we care about.
R_AARCH64_ABS64 = 257
R_AARCH64_GLOB_DAT = 1025
R_AARCH64_JUMP_SLOT = 1026
R_AARCH64_RELATIVE = 1027


@dataclass
class Section:
    index: int
    name: str
    sh_type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    info: int
    align: int
    entsize: int
    data: bytes = b""

    @property
    def is_alloc(self) -> bool:
        return bool(self.flags & 0x2)


@dataclass
class Segment:
    p_type: int
    flags: int
    offset: int
    vaddr: int
    paddr: int
    filesz: int
    memsz: int
    align: int


@dataclass
class Symbol:
    name: str
    value: int
    size: int
    info: int
    other: int
    shndx: int
    table: str  # which symbol table it came from
    version: str = ""

    @property
    def type(self) -> int:
        return self.info & 0xF

    @property
    def bind(self) -> int:
        return self.info >> 4

    @property
    def is_function(self) -> bool:
        return self.type in (STT_FUNC, STT_GNU_IFUNC)

    @property
    def is_undefined(self) -> bool:
        return self.shndx == 0


class ELFError(Exception):
    pass


class ELF:
    """Parsed ELF64 image with helpers for reverse engineering."""

    def __init__(self, path_or_bytes):
        if isinstance(path_or_bytes, (bytes, bytearray)):
            self.data = bytes(path_or_bytes)
            self.path = "<bytes>"
        else:
            self.path = str(path_or_bytes)
            with open(path_or_bytes, "rb") as fh:
                self.data = fh.read()

        d = self.data
        if d[:4] != b"\x7fELF":
            raise ELFError("not an ELF file (bad magic)")
        if d[4] != 2:
            raise ELFError("only ELF64 is supported (EI_CLASS=%d)" % d[4])
        self.little = d[5] == 1
        end = "<" if self.little else ">"
        self.end = end

        self.e_type = struct.unpack_from(end + "H", d, 16)[0]
        self.e_machine = struct.unpack_from(end + "H", d, 18)[0]
        self.e_entry = struct.unpack_from(end + "Q", d, 24)[0]
        self.e_phoff = struct.unpack_from(end + "Q", d, 32)[0]
        self.e_shoff = struct.unpack_from(end + "Q", d, 40)[0]
        self.e_flags = struct.unpack_from(end + "I", d, 48)[0]
        self.e_ehsize = struct.unpack_from(end + "H", d, 52)[0]
        self.e_phentsize = struct.unpack_from(end + "H", d, 54)[0]
        self.e_phnum = struct.unpack_from(end + "H", d, 56)[0]
        self.e_shentsize = struct.unpack_from(end + "H", d, 58)[0]
        self.e_shnum = struct.unpack_from(end + "H", d, 60)[0]
        self.e_shstrndx = struct.unpack_from(end + "H", d, 62)[0]

        self.segments: list[Segment] = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            if off + 56 > len(d):
                break
            p_type, p_flags = struct.unpack_from(end + "II", d, off)
            p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from(
                end + "QQQQQQ", d, off + 8
            )
            self.segments.append(
                Segment(p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align)
            )

        self.sections: list[Section] = []
        raw: list[Section] = []
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            if off + 64 > len(d):
                break
            name, sh_type, flags, addr, offset, size, link, info, align, entsize = (
                struct.unpack_from(end + "IIQQQQIIQQ", d, off)
            )
            raw.append(
                Section(i, name, sh_type, flags, addr, offset, size, link, info, align, entsize)
            )

        # resolve section names (``name`` holds the .shstrtab offset until here)
        if 0 <= self.e_shstrndx < len(raw):
            st = raw[self.e_shstrndx]
            shstrtab = d[st.offset : st.offset + st.size]
            for s in raw:
                off = s.name
                if not isinstance(off, int) or off == 0 or off >= len(shstrtab):
                    if off == 0:
                        s.name = ""
                    continue
                end_i = shstrtab.find(b"\0", off)
                s.name = shstrtab[off : end_i if end_i >= 0 else len(shstrtab)].decode(
                    "utf-8", "replace"
                )
        # attach data payloads
        for s in raw:
            if s.sh_type != SHT_NOBITS and s.size:
                s.data = d[s.offset : s.offset + s.size]
        self.sections = raw

    # -- lookup helpers -------------------------------------------------

    def section(self, name: str) -> Section | None:
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def section_data(self, name: str) -> bytes:
        s = self.section(name)
        return s.data if s else b""

    def vaddr_to_offset(self, vaddr: int) -> int | None:
        for seg in self.segments:
            if seg.p_type != PT_LOAD:
                continue
            if seg.vaddr <= vaddr < seg.vaddr + seg.filesz:
                return seg.offset + (vaddr - seg.vaddr)
        return None

    def offset_to_vaddr(self, off: int) -> int | None:
        for seg in self.segments:
            if seg.p_type != PT_LOAD:
                continue
            if seg.offset <= off < seg.offset + seg.filesz:
                return seg.vaddr + (off - seg.offset)
        return None

    def section_for_vaddr(self, vaddr: int) -> Section | None:
        for s in self.sections:
            if s.is_alloc and s.sh_type != SHT_NOBITS:
                if s.addr <= vaddr < s.addr + s.size:
                    return s
        return None

    def section_name_for_vaddr(self, vaddr: int) -> str:
        s = self.section_for_vaddr(vaddr)
        return s.name if s else ""

    def read(self, vaddr: int, size: int) -> bytes:
        off = self.vaddr_to_offset(vaddr)
        if off is None:
            return b""
        return self.data[off : off + size]

    def cstring_at(self, vaddr: int, maxlen: int = 4096) -> str:
        off = self.vaddr_to_offset(vaddr)
        if off is None:
            return ""
        end = self.data.find(b"\0", off, off + maxlen)
        if end < 0:
            end = off + maxlen
        return self.data[off:end].decode("utf-8", "replace")

    def u64_at(self, vaddr: int) -> int:
        off = self.vaddr_to_offset(vaddr)
        if off is None or off + 8 > len(self.data):
            return 0
        return struct.unpack_from(self.end + "Q", self.data, off)[0]

    def i64_at(self, vaddr: int) -> int:
        v = self.u64_at(vaddr)
        return v - (1 << 64) if v >= (1 << 63) else v

    def u32_at(self, vaddr: int) -> int:
        off = self.vaddr_to_offset(vaddr)
        if off is None or off + 4 > len(self.data):
            return 0
        return struct.unpack_from(self.end + "I", self.data, off)[0]

    def relocs_for(self, section_name: str) -> list[tuple[int, int, int]]:
        """Return (offset, info, addend-ish) tuples for a reloc section."""
        s = self.section(section_name)
        if not s or not s.data:
            return []
        out = []
        if s.sh_type == SHT_RELA:
            step = 24
            fmt = self.end + "QQq"
        else:
            step = 16
            fmt = self.end + "QQ"
        for off in range(0, len(s.data) - step + 1, step):
            r_offset, r_info = struct.unpack_from(self.end + "QQ", s.data, off)
            addend = 0
            if s.sh_type == SHT_RELA:
                addend = struct.unpack_from(self.end + "q", s.data, off + 16)[0]
            out.append((r_offset, r_info, addend))
        return out

    # -- symbols --------------------------------------------------------

    def _read_symtab(self, sec: Section, table: str) -> list[Symbol]:
        if not sec.data:
            return []
        strsec = self.sections[sec.link] if sec.link < len(self.sections) else None
        strdata = strsec.data if strsec else b""
        step = sec.entsize or 24
        out: list[Symbol] = []
        for off in range(0, len(sec.data) - step + 1, step):
            st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from(
                self.end + "IBBHQQ", sec.data, off
            )
            name = ""
            if strdata and st_name < len(strdata):
                e = strdata.find(b"\0", st_name)
                name = strdata[st_name : e if e >= 0 else len(strdata)].decode("utf-8", "replace")
            out.append(Symbol(name, st_value, st_size, st_info, st_other, st_shndx, table))
        return out

    def symbols(self, which: str = "all") -> list[Symbol]:
        """which: 'dyn' | 'sym' | 'all'"""
        res: list[Symbol] = []
        want_dyn = which in ("dyn", "all")
        want_sym = which in ("sym", "all")
        if want_dyn:
            s = self.section(".dynsym")
            if s:
                res.extend(self._read_symtab(s, ".dynsym"))
        if want_sym:
            s = self.section(".symtab")
            if s:
                res.extend(self._read_symtab(s, ".symtab"))
        return res

    # -- convenience ----------------------------------------------------

    def all_strings(self, minlen: int = 4) -> Iterator[tuple[int, str]]:
        """Yield (vaddr, string) for printable runs in alloc sections."""
        for s in self.sections:
            if not s.is_alloc or s.sh_type == SHT_NOBITS or not s.data:
                continue
            buf = s.data
            i = 0
            n = len(buf)
            while i < n:
                b = buf[i]
                if 32 <= b < 127:
                    j = i
                    while j < n and 32 <= buf[j] < 127:
                        j += 1
                    if j - i >= minlen:
                        yield s.addr + i, buf[i:j].decode("ascii")
                    i = j + 1
                else:
                    i += 1

    def loaded_segments(self) -> list[Segment]:
        return [s for s in self.segments if s.p_type == PT_LOAD]

    def text_range(self) -> tuple[int, int] | None:
        t = self.section(".text")
        if t:
            return t.addr, t.addr + t.size
        return None

    def summary(self) -> str:
        lines = [
            "ELF64 %s-endian machine=%d type=%d" % ("little" if self.little else "big", self.e_machine, self.e_type),
            "entry=0x%x  shnum=%d  shoff=0x%x" % (self.e_entry, self.e_shnum, self.e_shoff),
            "",
            "%-24s %-6s %-14s %-14s %s" % ("section", "type", "vaddr", "size", "flags"),
        ]
        for s in self.sections:
            if not s.name:
                continue
            lines.append(
                "%-24s %-6d 0x%012x 0x%08x %s"
                % (s.name, s.sh_type, s.addr, s.size, "AXWMS"[0] if s.flags & 2 else " ")
            )
        return "\n".join(lines)
