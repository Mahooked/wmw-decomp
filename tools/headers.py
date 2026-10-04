"""Emit C++ headers from the recovered layouts.

This is the step that unblocks the README's remaining item.  `fields.tsv` and
`layouts.tsv` say what each class looks like; Ghidra cannot use that until it is
a real type, and a type has to be a real struct before the decompiler will size
pointers, index arrays or slice members correctly.

Flat structs, on purpose
------------------------
A class with a base at a non-zero offset would normally be written with
inheritance, and this does not do that.  A derived class's recovered offsets
include its bases' fields, so writing `: Base` and only the derived fields would
be equivalent -- but only when the base's own layout was also recovered, and 486
layouts from 6,741 members does not mean every base is among them.  A flat
struct is offset-correct on its own and depends on nothing, so a header can
never be wrong because some *other* header is missing.  The bases are recorded
as a comment instead, and inheritance can be reintroduced once coverage is
complete.

Fields are named `f_<offset>` because the binary does not record their names.
That is a real limitation, not a placeholder to be filled in later: the mangling
carries types but never identifiers, and the 458 `get*`/`set*` accessor symbols
are the only naming evidence available and are not yet mapped onto offsets.  The
offsets, widths and element types are what this pass establishes.

Gaps are filled with explicit padding so that every later field keeps its true
offset, and any overlap between two accepted fields is resolved in favour of the
better-supported one and counted, since an overlap means the layout model is
wrong for that class rather than that the evidence was merely noisy.

Output: `out/types/include/<Namespace>/<Class>.h` and `out/types/include/wmw_types.h`.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re

#: (kind, signedness, width) -> C type.  Signedness unknown is signed for the
#: wider integers, which is what a bare `ldr w` is most often.
_CTYPES = {
    ("int", "u", 1): "uint8_t", ("int", "u", 2): "uint16_t",
    ("int", "u", 4): "uint32_t", ("int", "u", 8): "uint64_t",
    ("int", "s", 1): "int8_t", ("int", "s", 2): "int16_t",
    ("int", "s", 4): "int32_t", ("int", "s", 8): "int64_t",
    ("int", "?", 1): "uint8_t", ("int", "?", 2): "uint16_t",
    ("int", "?", 4): "int32_t", ("int", "?", 8): "uint64_t",
    ("float", "?", 4): "float", ("float", "?", 8): "double",
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ctype(kind: str, signed: str, width: int) -> str:
    got = _CTYPES.get((kind, signed, width))
    if got:
        return got
    if width == 16:
        # A 16-byte SIMD value; kept as two 64-bit halves so alignment and size
        # both survive.
        return "uint64_t"
    if width in (1, 2, 4, 8):
        return "uint8_t"
    return "uint8_t"


_SIZEOF = {"uint8_t": 1, "uint16_t": 2, "uint32_t": 4, "uint64_t": 8,
           "int8_t": 1, "int16_t": 2, "int32_t": 4, "int64_t": 8,
           "float": 4, "double": 8}

#: Narrower spellings to try when the recovered type does not fit its offset.
_FALLBACK = ("uint32_t", "uint16_t", "uint8_t")


def place(cursor: int, ctype_name: str):
    """Byte offset of `ctype_name` if appended at `cursor` under natural alignment."""
    size = _SIZEOF[ctype_name]
    align = min(size, 8)
    return (cursor + align - 1) // align * align


def fit(cursor: int, want: int, chosen: str):
    """Pick a type that lands exactly on `want`, narrowing `chosen` if need be.

    A recovered offset is authoritative -- it is what the binary actually
    addressed -- so when the inferred type cannot sit there under natural
    alignment, the inference is the thing that is wrong, not the offset.  A
    field the machine touched at offset 1 can only be a byte, so the type is
    narrowed until it fits rather than the offset being bent to fit the type.
    """
    if place(cursor, chosen) == want:
        return chosen, True
    for alt in _FALLBACK:
        if _SIZEOF[alt] > _SIZEOF[chosen]:
            continue
        if place(cursor, alt) == want:
            return alt, False
    return None, False


#: Windows refuses paths over 260 characters, and a libc++ template
#: instantiation can flatten to several hundred.  Anything past this is folded
#: into one directory under a name that is still deterministic and still unique.
MAX_PATH = 200


def path_for(class_name: str) -> str:
    """`Walaber::Vector2` -> `Walaber/Vector2`; templates flattened.

    Template arguments are flattened into directories so the tree stays
    browsable, but that is what produces the absurd paths:
    `std::__ndk1::__split_buffer<std::__ndk1::basic_string<char, ...>>` nests
    four levels deep and overruns MAX_PATH, at which point the header cannot be
    written, let alone indexed by git.  Such a name is instead replaced by a
    single directory holding a readable prefix and a hash of the full name --
    unique, deterministic, and short.
    """
    parts = []
    for seg in class_name.split("::"):
        seg = re.sub(r"[^A-Za-z0-9_]", "_", seg)
        if seg and _IDENT.match(seg):
            parts.append(seg)
        elif seg:
            parts.append("_" + seg)
    path = "/".join(parts)
    if len(path) <= MAX_PATH:
        return path
    flat = re.sub(r"[^A-Za-z0-9_]", "_", class_name)[-40:].lstrip("_")
    digest = hashlib.sha1(class_name.encode("utf-8")).hexdigest()[:12]
    return "_long/" + flat + "_" + digest


def load_hierarchy(path: str) -> dict:
    """class -> list of (base, offset)."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 7:
                continue
            bases = []
            for item in f[6].split(";"):
                item = item.strip()
                if not item or "@" not in item:
                    continue
                name, _, off = item.rpartition("@")
                try:
                    bases.append((name, int(off, 0)))
                except ValueError:
                    continue
            out[f[0]] = bases
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fields", default="out/types/fields.tsv")
    ap.add_argument("--layouts", default="out/types/layouts.tsv")
    ap.add_argument("--hierarchy", default="out/rtti/hierarchy.tsv")
    ap.add_argument("--out", default="out/types/include")
    args = ap.parse_args(argv)

    fields = collections.defaultdict(list)
    with open(args.fields, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 11:
                continue
            cls, off = f[0], int(f[1])
            fields[cls].append({
                "offset": off, "width": int(f[2]), "kind": f[3],
                "signed": f[4], "stride": int(f[5]), "funcs": int(f[6]),
                "anchors": int(f[7]), "conf": f[9],
            })

    layouts = {}
    with open(args.layouts, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 9:
                continue
            layouts[f[0]] = {
                "size": int(f[1]), "align": int(f[2]), "conf": f[4],
                "proven": int(f[8]),
            }

    hierarchy = load_hierarchy(args.hierarchy)

    stats = collections.Counter()
    index = []
    os.makedirs(args.out, exist_ok=True)

    for cls in sorted(layouts):
        if cls not in fields or not layouts[cls].get("proven", 0):
            # Layouts.tsv withholds a name it cannot show is a type; see the
            # namespace discussion there.
            if cls in fields:
                stats["unproven_skipped"] += 1
            continue
        items = sorted(fields[cls], key=lambda r: (r["offset"], -r["funcs"]))

        # Resolve overlaps: keep the better-supported field, drop the rest.
        kept = []
        for it in items:
            if kept and it["offset"] < kept[-1]["offset"] + kept[-1]["width"]:
                stats["overlap_dropped"] += 1
                if it["funcs"] > kept[-1]["funcs"]:
                    stats["overlap_replaced"] += 1
                    kept[-1] = it
                continue
            kept.append(it)

        bases = hierarchy.get(cls, [])
        body = []
        if bases:
            body.append("    // bases: " +
                        ", ".join("%s@%d" % (b, o) for b, o in bases))
        body.append("    // size %d, align %d, confidence %s" % (
            layouts[cls]["size"], layouts[cls]["align"], layouts[cls]["conf"]))

        cursor = 0
        if kept and kept[0]["offset"] < 0:
            body.append("    uint8_t _pre[%d];" % (-kept[0]["offset"]))
            cursor = -kept[0]["offset"]
        for it in kept:
            if it["offset"] > cursor:
                body.append("    uint8_t _pad%d[%d];" %
                            (it["offset"], it["offset"] - cursor))
                cursor = it["offset"]
            want = ctype(it["kind"], it["signed"], it["width"])
            if it["width"] == 16:
                want = "uint64_t"
            note = ""
            if it["stride"]:
                note = "  // indexed, stride %d" % it["stride"]
            chosen, exact = fit(cursor, it["offset"], want)
            if chosen is None:
                # Nothing aligns here; fall back to bytes so the offset survives.
                chosen = "uint8_t"
                body.append("    uint8_t f_0x%x[%d];%s  // type unplaced" %
                            (it["offset"], it["width"], note))
                cursor = it["offset"] + it["width"]
                stats["unplaced"] += 1
                continue
            if not exact:
                stats["type_narrowed"] += 1
            body.append("    %s f_0x%x;%s" % (chosen, it["offset"], note))
            cursor = it["offset"] + _SIZEOF[chosen]

        size = layouts[cls]["size"]
        if cursor < size:
            body.append("    uint8_t _tail[%d];" % (size - cursor))
        elif cursor > size:
            # Should not happen: size is derived from the highest field. Kept
            # explicit so a future change cannot silently shrink a struct.
            stats["size_mismatch"] += 1

        rel = path_for(cls)
        guard = "WMW_" + re.sub(r"[^A-Za-z0-9]", "_", cls).upper() + "_H"
        hpath = os.path.join(args.out, *rel.split("/")) + ".h"
        os.makedirs(os.path.dirname(hpath), exist_ok=True)

        # `struct Walaber::Vector2` is not valid C++: a qualified name cannot be
        # declared without the enclosing namespaces in scope, so they are opened
        # explicitly.  This keeps the headers compilable, which is what makes
        # them worth checking against a compiler at all.
        if "::" in cls:
            ns, _, bare = cls.rpartition("::")
            open_ns = "".join("namespace %s {\n" % seg
                              for seg in path_for(ns).split("/"))
            close_ns = "}  // namespace %s\n" % ns
            decl = "struct %s {" % bare
        else:
            open_ns = ""
            close_ns = ""
            decl = "struct %s {" % cls

        with open(hpath, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("// Recovered from %s. Offsets and element types are derived\n"
                     "// from load/store evidence in the binary; field names are not\n"
                     "// recorded anywhere in it.\n" % cls)
            fh.write("#ifndef %s\n#define %s\n\n#include <stdint.h>\n\n"
                     % (guard, guard))
            fh.write(open_ns)
            fh.write("%s\n%s\n};\n\n" % (decl, "\n".join(body)))
            fh.write(close_ns)
            fh.write("#endif\n")
        stats["headers"] += 1
        index.append((cls, rel + ".h", size, layouts[cls]["align"],
                      layouts[cls]["conf"], len(kept)))

    with open(os.path.join(args.out, "wmw_types.h"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write("// Every recovered layout, for Ghidra's type importer.\n")
        fh.write("#ifndef WMW_TYPES_H\n#define WMW_TYPES_H\n\n")
        for cls, rel, *_ in index:
            fh.write('#include "%s"\n' % rel)
        fh.write("\n#endif\n")

    ipath = os.path.join(args.out, "..", "typeindex.tsv")
    with open(ipath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\theader\tsize\talign\tconfidence\tfields\n")
        for cls, rel, size, align, conf, n in index:
            fh.write("%s\t%s\t%d\t%d\t%s\t%d\n" % (cls, rel, size, align, conf, n))

    summary = dict(sorted(stats.items()))
    summary["layouts_without_fields"] = len(layouts) - stats["headers"]
    summary["typeindex"] = len(index)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("wrote %d headers under %s and %s" % (stats["headers"], args.out, ipath))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())