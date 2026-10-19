#!/usr/bin/env python3
"""Shape recovered definitions of template members into legal C++.

The decompiler prints a definition of a member of a class template with the
template arguments spelled out and nothing else, e.g.::

    void std::__ndk1::basic_string<char,...>::~basic_string(byte *param_1)
    { ... }

Compiled, that is three errors at once: an out-of-line member of a class
template needs ``template<>``, a constructor/destructor cannot have a return
type, and a destructor cannot have parameters.  The parameter is the object the
decompiler passes explicitly, so the body is rewritten to use ``this``.

Run once over ``out/src/_tmpl`` (idempotent; already-shaped blocks are left
alone).  ``tools/shape_decl_calls.py`` handles the matching call statements.
"""

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_syntax as cs

_INT_PARAM = re.compile(r"^\s*int(\s+\w+)?\s*$")
_IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")


def _header_start(block):
    """Offset of the declaration proper, past the leading comment blocks."""
    return re.match(r"(?:\s|/\*.*?\*/)*", block, re.S).end()


def _first_param_name(params):
    parts = cs._split_commas(params)
    if not parts:
        return None
    m = re.search(r"([A-Za-z_]\w*)\s*$", parts[0])
    return m.group(1) if m else None


def shape_block(block, stats):
    """Return ``block`` with its definition header made legal."""
    brace = block.find("{")
    if brace < 0:
        return block
    decl = block[:brace]
    span = cs.param_span(decl)
    if span is None:
        return block
    head = cs.strip_comments(decl[:span[0]])
    if re.match(r"\s*template\s*<", head):
        stats["already"] += 1
        return block
    got = cs.split_name(re.sub(r"\s*::\s+", "::",
                               re.sub(r"\s+::", "::", head)))
    if got is None:
        stats["unparsed"] += 1
        return block
    ret, qname = got
    comps = cs._split_qname(qname)
    if len(comps) < 2:
        return block
    qual, last = comps[:-1], comps[-1]
    class_is_template = any("<" in c for c in qual)
    if not class_is_template and "<" not in last:
        return block                      # not a template member at all
    if last.startswith("operator") and not (
            cs._OPSPELL.match(last) or _IDENTIFIER.match(last)):
        return block                      # not spellable (operator new, ...)
    params = " ".join(decl[span[0] + 1:span[1]].split())

    is_dtor = class_is_template and last.startswith("~")
    is_ctor = (class_is_template and not is_dtor
               and last == cs._strip_angles(qual[-1]))
    is_member_tmpl = "<" in last and not last.startswith("operator")
    is_op = last.startswith("operator") and bool(cs._OPSPELL.match(last))
    objform = (class_is_template and is_op and last != "operator()"
               and ("," in params or (last in ("operator++", "operator--")
                                      and not _INT_PARAM.match(params))))

    new_name = "::".join(qual + [cs._strip_angles(last) if is_member_tmpl
                                 else last])
    new_ret = ret
    new_params = params
    dropped = None
    if is_dtor:
        new_ret, new_params = "", ""
        dropped = _first_param_name(params)
    elif is_ctor:
        new_ret = ""
    elif objform:
        parts = cs._split_commas(params)
        dropped = _first_param_name(parts[0])
        new_params = ",".join(p.strip() for p in parts[1:])

    prefix = "template<> " if class_is_template else ""
    header = "%s%s%s(%s)" % (prefix, (new_ret + " ") if new_ret else "",
                             new_name, new_params)
    start = _header_start(block)
    new_block = block[:start] + header + block[span[1] + 1:]

    if dropped and dropped != "this":
        body = len(block[:start]) + len(header)
        at = new_block.find("{", body)
        if at >= 0:
            new_block = (new_block[:at]
                         + re.sub(r"\b%s\b" % re.escape(dropped),
                                  "(byte *)this", new_block[at:]))

    if is_dtor:
        stats["dtor"] += 1
    elif is_ctor:
        stats["ctor"] += 1
    elif objform:
        stats["operator-objform"] += 1
    elif is_member_tmpl:
        stats["member-template"] += 1
    elif class_is_template:
        stats["member"] += 1
    else:
        stats["free-template"] += 1
    return new_block


def shape_file(path, stats):
    text = open(path, encoding="utf-8", errors="replace").read()
    text = text.replace("\r\n", "\n")
    pieces = []
    pos = 0
    marks = list(cs._MARKER.finditer(text))
    for idx, mark in enumerate(marks):
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
        pieces.append(text[pos:mark.end()])
        pieces.append(shape_block(text[mark.end():end], stats))
        pos = end
    pieces.append(text[pos:])
    new = "".join(pieces)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src", "_tmpl"))
    args = ap.parse_args(argv)
    stats = {"dtor": 0, "ctor": 0, "operator-objform": 0, "member": 0,
             "member-template": 0, "free-template": 0, "already": 0,
             "unparsed": 0}
    changed = 0
    paths = sorted(glob.glob(os.path.join(args.src, "*.cpp")))
    for path in paths:
        if shape_file(path, stats):
            changed += 1
    print("files %d, changed %d" % (len(paths), changed))
    for key in ("member", "ctor", "dtor", "operator-objform", "member-template",
                "free-template", "already", "unparsed"):
        if stats[key]:
            print("  %-18s %5d" % (key, stats[key]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
