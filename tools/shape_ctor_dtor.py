"""Strip illegal return types from constructors and destructors.

Ghidra emits definitions like ``void WaterConcept::Bomb::Bomb(...)`` and
``void WaterConcept::Bomb::~Bomb(...)`` — constructors and destructors may not
have a return type in C++. It also sometimes emits a parameter for
destructors (e.g. ``void A::~A(void *param_1)``) which is illegal. This tool
rewrites only those specific, well-defined cases.
"""

from __future__ import annotations

import argparse
import os
import re
import sys


_MARKER = re.compile(r"/\*[^*]*?address\s+0x[0-9a-fA-F]+\s+size\s+\d+\s*\*/")
_IDENT = re.compile(r"[A-Za-z_~]\w*")


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _skip_comment(text: str, i: int) -> int:
    if i < len(text) - 1 and text[i] == "/" and text[i + 1] == "*":
        j = text.find("*/", i + 2)
        return len(text) if j < 0 else j + 2
    return i


def param_span(decl: str):
    i, n = 0, len(decl)
    while i < n:
        j = _skip_comment(decl, i)
        if j != i:
            i = j
            continue
        if decl[i] == "(":
            depth, k = 0, i
            while k < n:
                j = _skip_comment(decl, k)
                if j != k:
                    k = j
                    continue
                if decl[k] == "(":
                    depth += 1
                elif decl[k] == ")":
                    depth -= 1
                    if depth == 0:
                        return (i, k)
                k += 1
            return None
        i += 1
    return None


def _parse_component(s: str, i: int):
    m = _IDENT.match(s, i)
    if not m:
        return None
    return m.end()


def _parse_name(s: str, i: int):
    j = _parse_component(s, i)
    if j is None:
        return None
    while j + 1 < len(s) and s[j] == ":" and s[j + 1] == ":":
        k = _parse_component(s, j + 2)
        if k is None:
            return None
        j = k
    return j


def split_name(pre: str):
    s = " ".join(pre.split())
    starts = [0] + [i + 1 for i, c in enumerate(s) if c in " *&"]
    for st in starts:
        while st < len(s) and s[st] in " *&":
            st += 1
        if st >= len(s):
            continue
        if _parse_name(s, st) == len(s):
            return s[:st].rstrip(), s[st:]
    return None


def is_ctor_or_dtor(qname: str, short: str) -> tuple[bool, bool]:
    parts = qname.split("::")
    if len(parts) < 2:
        return False, False
    clsname = parts[-2]
    name = parts[-1]
    is_dtor = name.startswith("~")
    base = name[1:] if is_dtor else name
    if base != clsname:
        return False, False
    return (not is_dtor), is_dtor


def strip_ctor_dtor(src_dir: str, check: bool = False) -> int:
    changes = 0
    for base, _dirs, names in os.walk(src_dir):
        for name in sorted(names):
            if not name.endswith(".cpp"):
                continue
            path = os.path.join(base, name)
            text = open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
            out = text
            marks = list(_MARKER.finditer(text))
            for idx, mk in enumerate(marks):
                end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
                block = text[mk.end():end]
                brace = block.find("{")
                if brace < 0:
                    continue
                decl = block[:brace]
                span = param_span(decl)
                if span is None:
                    continue
                pre = strip_comments(decl[:span[0]])
                got = split_name(pre)
                if got is None:
                    continue
                ret, qname = got
                params = " ".join(strip_comments(decl[span[0]:span[1] + 1]).split())  # keep parens
                post = " ".join(strip_comments(decl[span[1] + 1:]).split())
                short = qname.split("::")[-1]
                is_ctor, is_dtor = is_ctor_or_dtor(qname, short)
                if not (is_ctor or is_dtor):
                    continue
                new_pre = pre
                if ret:
                    # strip leading return type (keep qualifiers on the name)
                    # simple: remove from start up to qname
                    new_pre = qname
                new_head = new_pre
                if is_dtor:
                    # strip params if any
                    inner = params.strip("()").strip()
                    if inner:  # always illegal for dtor
                        params_new = "()"
                        changes += 1
                        new_head = "%s%s" % (new_pre, params_new)
                        if post:
                            new_head = "%s %s" % (new_head, post)
                        old_head = decl
                        out = out.replace(old_head, new_head, 1)
                        continue
                # ctor: keep params, just strip ret
                if ret:
                    new_head = "%s%s" % (new_pre, params)
                    if post:
                        new_head = "%s %s" % (new_head, post)
                    old_head = decl
                    if old_head != new_head:
                        out = out.replace(old_head, new_head, 1)
                        changes += 1
                        continue
            if not check and out != text:
                open(path, "w", encoding="utf-8", newline="\n").write(out)
            elif check and out != text:
                changes += 1  # count files/occurrences? report total replacements count
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    n = strip_ctor_dtor(args.src, check=args.check)
    if args.check:
        if n:
            print("shape_ctor_dtor: %d ctor/dtor definitions need fixing" % n, file=sys.stderr)
            return 1
        print("shape_ctor_dtor: ok")
        return 0
    print("shape_ctor_dtor: fixed %d ctor/dtor definitions" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
