#!/usr/bin/env python3
"""Index the APK's classes.dex and binary AndroidManifest.xml.

No Android tooling is available in this environment, so the two formats are
parsed directly. Both are small here (a 160 KB dex, a 6 KB manifest); the goal
is a faithful structural record, not a full framework reimplementation.

The interesting product is the JNI surface: the native methods declared in the
dex, which are the Java-side entry points into libwmw.so. Those are matched
against the library's exported symbols so the bridge is documented end to end.

Usage:
    python tools/apkindex.py <apk-root> [--out out/apk]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ACC_NATIVE = 0x0100
ACC_PUBLIC = 0x0001
ACC_STATIC = 0x0008
ACC_INTERFACE = 0x0200

NO_INDEX = 0xFFFFFFFF


# ---------------------------------------------------------------- dex


class Dex:
    def __init__(self, data: bytes) -> None:
        self.d = data
        if data[:4] != b"dex\n":
            raise ValueError("not a dex file: %r" % data[:8])
        (
            self.file_size,
            self.header_size,
            self.endian_tag,
            self.link_size,
            self.link_off,
            self.map_off,
            self.string_ids_size,
            self.string_ids_off,
            self.type_ids_size,
            self.type_ids_off,
            self.proto_ids_size,
            self.proto_ids_off,
            self.field_ids_size,
            self.field_ids_off,
            self.method_ids_size,
            self.method_ids_off,
            self.class_defs_size,
            self.class_defs_off,
            self.data_size,
            self.data_off,
        ) = struct.unpack_from("<20I", data, 32)

    # -- primitives ----------------------------------------------------

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.d, off)[0]

    def u16(self, off: int) -> int:
        return struct.unpack_from("<H", self.d, off)[0]

    def uleb128(self, off: int) -> tuple[int, int]:
        """Return (value, new_offset). DEX uses LEB128 for the encoded arrays."""
        result = 0
        shift = 0
        while True:
            byte = self.d[off]
            off += 1
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result, off
            shift += 7

    # -- tables --------------------------------------------------------

    def string(self, idx: int) -> str:
        """Read a MUTF-8 string_data_item. Only the ASCII range occurs here."""
        if idx == NO_INDEX or idx >= self.string_ids_size:
            return ""
        off = self.u32(self.string_ids_off + idx * 4)
        _, off = self.uleb128(off)  # utf16 length, unused
        end = self.d.index(b"\x00", off)
        return self.d[off:end].decode("utf-8", "replace")

    def type_str(self, idx: int) -> str:
        if idx == NO_INDEX or idx >= self.type_ids_size:
            return ""
        return self.string(self.u32(self.type_ids_off + idx * 4))

    def method(self, idx: int) -> tuple[str, str, str]:
        """(class descriptor, name, prototype) for a method_id."""
        off = self.method_ids_off + idx * 8
        cls = self.type_str(self.u16(off))
        proto = self.u16(off + 2)
        name = self.string(self.u32(off + 4))
        return cls, name, self.proto(proto)

    def proto(self, idx: int) -> str:
        off = self.proto_ids_off + idx * 12
        ret = self.type_str(self.u32(off + 4))
        params_off = self.u32(off + 8)
        if not params_off:
            return "%s()" % ret
        n = self.u32(params_off)
        types = [self.type_str(self.u16(params_off + 4 + i * 2)) for i in range(n)]
        return "%s(%s)" % (ret, ", ".join(types))

    # -- class_data ----------------------------------------------------

    def class_methods(self, class_data_off: int) -> list[tuple[int, int, int, int]]:
        """Return [(method_idx, access_flags, code_off, ...)] for one class.

        encoded_method is (method_idx_diff, access_flags, code_off); the indices
        are deltas that accumulate within the class.
        """
        if not class_data_off:
            return []
        off = class_data_off
        static_fields, off = self.uleb128(off)
        instance_fields, off = self.uleb128(off)
        direct_methods, off = self.uleb128(off)
        virtual_methods, off = self.uleb128(off)
        for _ in range(static_fields + instance_fields):
            _, off = self.uleb128(off)
            _, off = self.uleb128(off)
        out = []
        for count in (direct_methods, virtual_methods):
            idx = 0
            for _ in range(count):
                diff, off = self.uleb128(off)
                flags, off = self.uleb128(off)
                code, off = self.uleb128(off)
                idx += diff
                out.append((idx, flags, code))
        return out

    def classes(self) -> list[dict]:
        out = []
        for i in range(self.class_defs_size):
            off = self.class_defs_off + i * 32
            class_idx = self.u32(off)
            flags = self.u32(off + 4)
            super_idx = self.u32(off + 8)
            class_data_off = self.u32(off + 24)
            entry = {
                "descriptor": self.type_str(class_idx),
                "super": self.type_str(super_idx),
                "access_flags": flags,
                "is_interface": bool(flags & ACC_INTERFACE),
                "methods": [],
                "natives": [],
            }
            for mid, mflags, code in self.class_methods(class_data_off):
                cls, name, proto = self.method(mid)
                rec = {
                    "name": name,
                    "proto": proto,
                    "static": bool(mflags & ACC_STATIC),
                    "public": bool(mflags & ACC_PUBLIC),
                }
                entry["methods"].append(rec)
                if mflags & ACC_NATIVE:
                    # JNI resolution looks up Class.method, or Class.method and
                    # the short name, in the shared library.
                    entry["natives"].append(
                        {
                            "name": name,
                            "proto": proto,
                            "static": rec["static"],
                            "symbol": "%s.%s" % (cls.lstrip("L").rstrip(";"), name),
                            "short_symbol": name,
                        }
                    )
            out.append(entry)
        return out


# ---------------------------------------------------------------- axml


class Axml:
    """Minimal binary AndroidManifest.xml reader.

    Only what is needed for a structural record: the string pool and the
    START_TAG chunks, which carry the element/attribute tree. Attribute
    values that are not string references are typed by the value type.
    """

    CHUNK_STRING = 0x001C0001
    RES_STRING = 0x00000001
    TYPE_REFERENCE = 0x01
    TYPE_STRING = 0x03
    TYPE_INT_DEC = 0x10
    TYPE_INT_HEX = 0x11
    TYPE_INT_BOOLEAN = 0x12

    def __init__(self, data: bytes) -> None:
        if struct.unpack_from("<I", data, 0)[0] != 0x00080003:
            raise ValueError("not a binary xml file")
        self.d = data
        self.strings: list[str] = []
        self._read_strings()

    def _read_strings(self) -> None:
        # Walk the top-level chunks until the string pool is found.
        off = 8
        while off < len(self.d):
            ctype, size = struct.unpack_from("<II", self.d, off)
            if size < 8 or off + size > len(self.d):
                break
            if ctype == self.CHUNK_STRING:
                self._parse_string_pool(off)
                return
            off += size

    def _parse_string_pool(self, off: int) -> None:
        count, style_count, flags, str_start, style_start = struct.unpack_from(
            "<5I", self.d, off + 8
        )
        utf8 = bool(flags & (1 << 8))
        offsets = struct.unpack_from("<%dI" % count, self.d, off + 28)
        base = off + str_start
        for o in offsets:
            p = base + o
            if utf8:
                # Two uleb128s (utf16 length, byte length) then the bytes.
                _, p = self._uleb(p)
                n, p = self._uleb(p)
                self.strings.append(self.d[p : p + n].decode("utf-8", "replace"))
            else:
                n = struct.unpack_from("<H", self.d, p)[0]
                self.strings.append(
                    self.d[p + 2 : p + 2 + n * 2].decode("utf-16-le", "replace")
                )
        del style_count, style_start

    def _uleb(self, off: int) -> tuple[int, int]:
        result = 0
        shift = 0
        while True:
            b = self.d[off]
            off += 1
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                return result, off
            shift += 7

    def _string(self, idx: int) -> str:
        return self.strings[idx] if 0 <= idx < len(self.strings) else ""

    def elements(self) -> list[dict]:
        out: list[dict] = []
        off = 8
        depth = 0
        while off < len(self.d):
            ctype, size = struct.unpack_from("<II", self.d, off)
            if size < 8 or off + size > len(self.d):
                break
            if ctype == 0x00100102:  # START_ELEMENT
                # ResXMLTree_node is type/size/lineNumber/comment (16 bytes),
                # then attrExt: ns, name, attributeStart, attributeSize,
                # attributeCount, idIndex, classIndex, styleIndex.
                ns, name, attr_start, attr_size, attr_count = struct.unpack_from(
                    "<IIHHH", self.d, off + 16
                )
                attrs = {}
                p = off + 16 + attr_start
                for _ in range(attr_count):
                    a_ns, a_name, raw, typed, a_data = struct.unpack_from(
                        "<5i", self.d, p
                    )
                    a_type = (typed >> 24) & 0xFF
                    attrs[self._string(a_name) or "ns%d" % a_ns] = self._value(
                        a_type, raw, a_data
                    )
                    p += 20
                out.append(
                    {
                        "depth": depth,
                        "tag": self._string(name),
                        "ns": self._string(ns),
                        "attributes": attrs,
                    }
                )
                depth += 1
            elif ctype == 0x00100103:  # END_ELEMENT
                depth = max(0, depth - 1)
            off += size
        return out

    def _value(self, vtype: int, raw: int, data: int) -> object:
        if raw != NO_INDEX and 0 <= raw < len(self.strings):
            return self.strings[raw]
        if vtype == self.TYPE_STRING:
            return self._string(data)
        if vtype == self.TYPE_REFERENCE:
            return "@0x%08x" % (data & 0xFFFFFFFF)
        if vtype == self.TYPE_INT_BOOLEAN:
            return bool(data)
        if vtype == self.TYPE_INT_HEX:
            return "0x%x" % data
        if vtype == self.TYPE_INT_DEC:
            return data
        return data


# ---------------------------------------------------------------- report


def jni_name(descriptor: str, method: str) -> str:
    """Build the static JNI symbol for a native method.

    JNI mangles a class or method name by escaping '_' as '_1' and '/' as '_',
    then joining as Java_<class>_<method>. Getting this wrong makes every
    native method look unresolved, which is how the first pass reported 0/55
    even though the library exports 48 Java_* symbols.
    """
    cls = descriptor.lstrip("L").rstrip(";")
    esc = lambda s: s.replace("_", "_1").replace("/", "_")  # noqa: E731
    return "Java_%s_%s" % (esc(cls), esc(method))


def report(dex: Dex, axml: Axml | None, lib_syms: set[str]) -> dict:
    classes = dex.classes()
    natives = []
    for c in classes:
        for n in c["natives"]:
            jni = jni_name(c["descriptor"], n["name"])
            natives.append(
                {
                    "class": c["descriptor"],
                    "symbol": n["symbol"],
                    "jni_symbol": jni,
                    "short_symbol": n["short_symbol"],
                    "proto": n["proto"],
                    "static": n["static"],
                    "resolved_in_lib": jni in lib_syms,
                }
            )
    resolved = sum(1 for n in natives if n["resolved_in_lib"])
    # Split by ownership: the game's own natives must all be in libwmw.so, while
    # bundled third-party SDKs (FMOD audio, Play Billing) bring their own
    # libraries and are expected to be absent.
    own = [n for n in natives if n["class"].startswith("Lcom/disney/")]
    third = [n for n in natives if not n["class"].startswith("Lcom/disney/")]
    return {
        "dex": {
            "file_size": dex.file_size,
            "header_size": dex.header_size,
            "string_ids": dex.string_ids_size,
            "type_ids": dex.type_ids_size,
            "proto_ids": dex.proto_ids_size,
            "field_ids": dex.field_ids_size,
            "method_ids": dex.method_ids_size,
            "class_defs": dex.class_defs_size,
        },
        "manifest": (
            [
                {"depth": e["depth"], "tag": e["tag"], "attributes": e["attributes"]}
                for e in axml.elements()
            ]
            if axml
            else []
        ),
        "classes": classes,
        "jni": {
            "native_methods": len(natives),
            "resolved_in_libwmw": resolved,
            "game_native_methods": len(own),
            "game_resolved": sum(1 for n in own if n["resolved_in_lib"]),
            "third_party_native_methods": len(third),
            "third_party_classes": sorted({n["class"] for n in third}),
            "unresolved": [n["jni_symbol"] for n in natives if not n["resolved_in_lib"]],
            "entries": natives,
        },
    }


def render(rep: dict) -> str:
    L: list[str] = []
    d = rep["dex"]
    L.append("# classes.dex")
    L.append("")
    L.append("    file_size=%(file_size)d header=%(header_size)d"
             % d)
    L.append("    strings=%(string_ids)d types=%(type_ids)d protos=%(proto_ids)d"
             % d)
    L.append("    fields=%(field_ids)d methods=%(method_ids)d classes=%(class_defs)d"
             % d)
    L.append("")
    L.append("## Classes (%d)" % len(rep["classes"]))
    L.append("")
    for c in rep["classes"]:
        kind = "interface" if c["is_interface"] else "class"
        sup = c["super"] or "-"
        L.append("    %-8s %s  extends %s  (%d methods, %d native)"
                 % (kind, c["descriptor"], sup, len(c["methods"]), len(c["natives"])))
    L.append("")
    j = rep["jni"]
    L.append("## JNI surface")
    L.append("")
    L.append("    %d native methods declared in the dex" % j["native_methods"])
    L.append("      game-owned (com.disney.*): %d, %d resolved in libwmw.so"
             % (j["game_native_methods"], j["game_resolved"]))
    L.append("      third-party SDKs:         %d, in %s"
             % (j["third_party_native_methods"],
                ", ".join(c.lstrip("L").rstrip(";") for c in j["third_party_classes"])))
    L.append("")
    for n in j["entries"]:
        L.append("    %-8s %-62s %s"
                 % ("static" if n["static"] else "virtual",
                    n["jni_symbol"], n["proto"]))
        if not n["resolved_in_lib"]:
            L.append("             ^^ declared native but not an export of libwmw.so")
    L.append("")
    if rep["manifest"]:
        L.append("## AndroidManifest.xml")
        L.append("")
        for e in rep["manifest"]:
            pad = "  " * e["depth"]
            attrs = " ".join(
                '%s="%s"' % (k, v) for k, v in e["attributes"].items()
            )
            L.append("    %s<%s %s>" % (pad, e["tag"], attrs))
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="extracted APK root")
    ap.add_argument("--out", default="out/apk")
    args = ap.parse_args(argv[1:])

    root = Path(args.root)
    dex_path = root / "classes.dex"
    if not dex_path.is_file():
        print("apkindex: no classes.dex under %s" % root, file=sys.stderr)
        return 1

    dex = Dex(dex_path.read_bytes())

    axml = None
    man = root / "AndroidManifest.xml"
    if man.is_file():
        try:
            axml = Axml(man.read_bytes())
        except ValueError as exc:
            print("apkindex: manifest: %s" % exc, file=sys.stderr)

    lib_syms: set[str] = set()
    lib = root / "lib" / "arm64-v8a" / "libwmw.so"
    if lib.is_file():
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from wmwtools.elf import ELF

            lib_syms = {s.name for s in ELF(str(lib)).symbols("dyn")}
        except Exception as exc:  # noqa: BLE001 - optional enrichment
            print("apkindex: libwmw.so symbols unavailable: %s" % exc, file=sys.stderr)

    rep = report(dex, axml, lib_syms)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dex.md").write_text(render(rep), encoding="utf-8", newline="\n")
    (out / "apkindex.json").write_text(
        json.dumps(rep, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "apkindex: %d classes, %d methods, %d native (JNI), %d manifest elements"
        % (
            len(rep["classes"]),
            dex.method_ids_size,
            rep["jni"]["native_methods"],
            len(rep["manifest"]),
        )
    )
    print("apkindex: wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
