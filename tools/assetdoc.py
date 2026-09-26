#!/usr/bin/env python3
"""Document the game's XML asset formats and inventory the asset tree.

Levels, interactive objects, and most configuration ship as XML, so the schema
can be recovered exactly rather than guessed. This tool records, per element
path: how often it occurs, which attributes it takes, and the *shape* of each
attribute's value. Shapes are recorded instead of values so the format is
documented without redistributing level layouts or object placement data.

Usage:
    python tools/assetdoc.py <apk-root> [--out out/assets]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Attribute value shapes. Ordered most specific first.
_SHAPES = [
    (re.compile(r"^-?\d+$"), "int"),
    (re.compile(r"^-?\d+\.\d+$"), "float"),
    (re.compile(r"^-?\d+(\.\d+)? -?\d+(\.\d+)?$"), "two floats"),
    (re.compile(r"^-?\d+(\.\d+)? -?\d+(\.\d+)? -?\d+(\.\d+)?$"), "three floats"),
    (re.compile(r"^-?\d+(\.\d+)? -?\d+(\.\d+)? -?\d+(\.\d+)? -?\d+(\.\d+)?$"),
     "four floats"),
    (re.compile(r"^(true|false)$", re.I), "bool"),
    (re.compile(r"^/[\w/.-]+$"), "asset path"),
    (re.compile(r"^[\w.-]+\.(png|xml|webp|wav|mp3|fnt|sprite|ani|ps|bin)$", re.I),
     "file name"),
    (re.compile(r"^\d+ \d+ \d+ \d+$"), "rgba"),
]


def shape_of(value: str) -> str:
    v = value.strip()
    if not v:
        return "empty"
    for rx, name in _SHAPES:
        if rx.match(v):
            return name
    if re.match(r"^-?\d+(\.\d+)?(,-?\d+(\.\d+)?)+$", v):
        return "number list"
    if re.match(r"^[\w.]+;[\w.]+$", v):
        return "pair"
    if "," in v and all(p.strip() for p in v.split(",")):
        return "comma list"
    return "string"


def path_of(el: ET.Element, parent: str) -> str:
    """Dotted path, ignoring the numeric index of repeated siblings."""
    return "%s/%s" % (parent, el.tag)


class Vocab:
    """Accumulates the element/attribute vocabulary across many documents."""

    def __init__(self) -> None:
        self.elems: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter
        )
        # How many times each element path was itself instantiated. Tracked
        # separately from elems, which counts the children hanging off a path,
        # so the rendered table does not repeat the same number twice.
        self.instances: collections.Counter = collections.Counter()
        self.attrs: dict[str, dict[str, collections.Counter]] = (
            collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        )
        self.files = 0
        self.parse_errors: list[str] = []

    def add_file(self, path: Path) -> None:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            self.parse_errors.append("%s: %s" % (path.name, exc))
            return
        self.files += 1
        self._walk(root, "")

    def _walk(self, el: ET.Element, parent: str) -> None:
        p = path_of(el, parent)
        self.instances[p] += 1
        for k, v in el.attrib.items():
            self.attrs[p][k][shape_of(v)] += 1
        for child in el:
            self.elems[p][child.tag] += 1
            self._walk(child, p)

    def render(self, title: str) -> str:
        paths = set(self.instances) | set(self.elems)
        L = [title, "",
             "Parsed %d files; %d distinct element paths." % (self.files, len(paths)),
             "",
             "'instances' counts how many times that element occurs across all",
             "files; 'children' is the breakdown of what it contains.", ""]
        if self.parse_errors:
            L.append("Parse errors (%d):" % len(self.parse_errors))
            for e in self.parse_errors[:10]:
                L.append("    %s" % e)
            L.append("")
        L.append("%-52s %9s  %s" % ("element path", "instances", "attributes (value shape)"))
        L.append("-" * 100)
        for path in sorted(paths, key=lambda k: -self.instances.get(k, 0)):
            a = self.attrs.get(path, {})
            astr = "  ".join(
                "%s:%s" % (k, "/".join(sorted(a[k]))) for k in sorted(a)
            )
            L.append("%-52s %9d  %s" % (path or "(root)", self.instances.get(path, 0), astr))
            kids = self.elems.get(path)
            if kids:
                L.append("%-52s %9s  children: %s"
                         % ("", "", ", ".join("%s x%d" % (t, c)
                                              for t, c in kids.most_common(8))))
        return "\n".join(L) + "\n"


def inventory(root: Path) -> list[dict]:
    rows = []
    for d in sorted(p for p in root.rglob("*") if p.is_dir()):
        files = [f for f in d.iterdir() if f.is_file()]
        if not files:
            continue
        by_ext: collections.Counter = collections.Counter()
        for f in files:
            by_ext[f.suffix.lower() or "(none)"] += 1
        rows.append(
            {
                "dir": str(d.relative_to(root)).replace("\\", "/"),
                "files": len(files),
                "bytes": sum(f.stat().st_size for f in files),
                "by_ext": dict(by_ext.most_common()),
            }
        )
    return rows


def render_inventory(rows: list[dict], root: Path) -> str:
    L = ["# Asset inventory", "",
         "Extracted APK root: %s" % root, ""]
    L.append("%-34s %7s %11s  %s" % ("directory", "files", "bytes", "extensions"))
    L.append("-" * 96)
    for r in rows:
        exts = ", ".join(
            "%s x%d" % (e.lstrip("."), c) for e, c in list(r["by_ext"].items())[:6]
        )
        L.append("%-34s %7d %11d  %s" % (r["dir"], r["files"], r["bytes"], exts))
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="extracted APK root")
    ap.add_argument("--out", default="out/assets")
    args = ap.parse_args(argv[1:])

    root = Path(args.root)
    assets = root / "assets"
    if not assets.is_dir():
        print("assetdoc: no assets directory under %s" % root, file=sys.stderr)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    inv = inventory(assets)
    (out / "inventory.md").write_text(
        render_inventory(inv, assets), encoding="utf-8", newline="\n"
    )

    reports = {}
    for label, rel, pattern in (
        ("levels", "Levels", "*.xml"),
        ("objects", "Objects", "*.hs"),
        ("imagelists", "Textures", "*.imagelist"),
    ):
        d = assets / rel
        files = sorted(d.glob(pattern)) if d.is_dir() else []
        v = Vocab()
        for f in files:
            v.add_file(f)
        if not files:
            continue
        (out / ("%s.md" % label)).write_text(
            v.render("# %s format (%s/%s)" % (label.capitalize(), rel, pattern)),
            encoding="utf-8",
            newline="\n",
        )
        reports[label] = {
            "files": len(files),
            "element_paths": len(v.elems),
            "parse_errors": len(v.parse_errors),
        }
        print(
            "assetdoc: %-11s %4d files, %3d element paths, %d parse errors"
            % (label, len(files), len(v.elems), len(v.parse_errors))
        )

    (out / "assetdoc.json").write_text(
        json.dumps({"inventory": inv, "formats": reports}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print("assetdoc: %d asset directories catalogued" % len(inv))
    print("assetdoc: wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
