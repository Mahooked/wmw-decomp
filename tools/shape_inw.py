#!/usr/bin/env python3
"""
Shape pass: add unbound input registers (in_xN/in_wN) to parameter lists.

Ghidra sometimes binds a parameter to a register while another input register
the body reads stays unbound (``long *in_x0;`` declared in the body).  The
definition then has fewer parameters than the call sites pass:

    int  Walaber::SoundManager::soundCountForGroup(int p0)   // body reads in_w1
    ...
    Walaber::SoundManager::soundCountForGroup(uVar17, 0x79);  // two args

For ``in_xN``/``in_wN`` whose declaration line exists in the body:

  * N == 0                  -> the register precedes every bound parameter
                               (usually the object): insert at the front.
  * N == number of params   -> the register follows them: append at the end.

Appends (``in_xN`` with N == arity) are structurally forced by AAPCS64 and are
always applied.  Front inserts (``in_x0``, the register preceding every bound
parameter) are only applied when call sites of the same qualified name
corroborate the extra argument -- the tree contains definitions whose bodies
read x0 while their call sites display no extra argument (the object is not
re-shown), and adding a parameter there would only move the error from
"too many arguments" to "too few".

The declaration line is removed from the body (a parameter and a local of the
same name cannot coexist); uses keep the register's name as the parameter name.
"""

import argparse
import collections
import os
import re
import sys

MARKER = re.compile(r"/\*[^*]*?address\s+0x[0-9a-fA-F]+\s+size\s+\d+\s*\*/")
DECL = re.compile(r"^\s*([\w\s\*<>,:]*?)\b(in_(x|w)(\d+))\b\s*;$")
USE_ANY = re.compile(r"\b(in_(x|w)(\d+))\b")
CALL = re.compile(r"([\w:~]+)\s*\(")
# Ghidra writes every function signature at column 0; template-qualified names
# contain commas, and statement lines are indented -- but reject lines ending
# in `{`/`&&`/`||`/`,` so a wrapped `if (` continuation can never match.
SIG_START = re.compile(r"^[A-Za-z_~][\w:<>,>&*~\s]*\(")
SIG_END_BAD = ("{", "&&", "||", ",")


def _split_top(inner):
    """Split on top-level commas, tracking (), [], {} and <> nesting."""
    depth = 0
    parts = []
    cur = []
    for ch in inner:
        if ch in "([{<":
            depth += 1
            cur.append(ch)
        elif ch in ")]}>":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return [p for p in (s.strip() for s in parts) if p]


def arity_of(text):
    """Arity of a call/param list inside text, or None if unbalanced."""
    i = text.find("(")
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        ch = text[j]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                inner = text[i + 1:j]
                if not inner.strip() or inner.strip() == "void":
                    return 0
                return len(_split_top(inner))
    return None


def parse_sig(line):
    """(qualified name, arity) of a column-0 signature line, or None."""
    if not SIG_START.match(line):
        return None
    s = line.strip()
    if ";" in s or s.endswith(SIG_END_BAD):
        return None
    m = re.search(r"([\w:~]+)\s*\(", s)
    if not m:
        return None
    n = arity_of(s)
    if n is None:
        return None
    return (m.group(1), n)


def find_decl_type(body_lines, reg):
    pat = re.compile(r"^\s*([\w\s\*<>,:]*?)\b" + re.escape(reg) + r"\b\s*;$")
    for idx, line in enumerate(body_lines):
        if line.strip().startswith("/*"):
            continue
        m = pat.match(line)
        if m:
            return (m.group(1).strip(), idx)
    return None


def iter_blocks(text):
    marks = list(MARKER.finditer(text))
    for idx, mk in enumerate(marks):
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
        yield mk, text[mk.end():end]


def analyse_block(body_lines):
    """Decide the register inserts for one definition block.

    Returns (qname, np, inserts_front, inserts_end, remove_lines) or None.
    """
    sig = ""
    sig_idx = -1
    for i, line in enumerate(body_lines):
        s = line.strip()
        if SIG_START.match(line) and ";" not in s \
                and not s.endswith(SIG_END_BAD):
            sig = s
            sig_idx = i
            break
    if not sig:
        return None
    np = arity_of(sig)
    if np is None:
        return None
    m = re.search(r"([\w:~]+)\s*\(", sig)
    if not m:
        return None
    qname = m.group(1)

    used = set()
    for line in body_lines:
        if line.strip().startswith("/*"):
            continue
        dm = DECL.match(line)
        for m in USE_ANY.finditer(line):
            reg = m.group(1)
            if dm and dm.group(2) == reg:
                continue
            used.add(reg)
    if not used:
        return None

    inserts_front = []
    inserts_end = []
    decls = {}
    for reg in sorted(used, key=lambda r: (int(r.rsplit("w")[-1].rsplit("x")[-1]), r)):
        mnum = re.match(r"in_(x|w)(\d+)$", reg)
        if not mnum:
            continue
        num = int(mnum.group(2))
        dt = find_decl_type(body_lines, reg)
        if not dt:
            continue
        decltype, dline = dt
        decls[reg] = (decltype, dline)
        if num == 0:
            inserts_front.append((reg, decltype))
        elif num == np:
            inserts_end.append((reg, decltype))
        else:
            return None            # ambiguous shape: leave the block alone
    if not inserts_front and not inserts_end:
        return None
    return (qname, np, sig_idx, inserts_front, inserts_end, decls)


def rebuild_sig(sig, inserts_front, inserts_end):
    i = sig.rfind(")")
    if i < 0:
        return None
    inner = sig[sig.find("(") + 1:i].strip()
    parts = []
    for r, t in inserts_front:
        parts.append((t + " " + r).strip())
    if inner and inner != "void":
        parts.append(inner)
    for r, t in inserts_end:
        parts.append((t + " " + r).strip())
    newinner = ", ".join(p for p in parts if p)
    if not newinner:
        newinner = "void"
    return sig[:sig.find("(") + 1] + newinner + sig[i:]


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None


def collect(src):
    """Walk A: candidates + every call arity in the tree."""
    candidates = []
    callmap = collections.defaultdict(collections.Counter)
    files = []
    for base, _dirs, names in os.walk(src):
        for name in sorted(names):
            if name.endswith(".cpp"):
                files.append(os.path.join(base, name))
    for path in files:
        text = read(path)
        if text is None:
            continue
        for mk, body in iter_blocks(text):
            body_lines = body.splitlines(True)
            info = analyse_block(body_lines)
            if info:
                candidates.append((path, mk.start(), info))
            for line in body.splitlines():
                if line.strip().startswith(("/*", "//")):
                    continue
                for m in CALL.finditer(line):
                    n = arity_of(line[m.start():])
                    if n is not None:
                        callmap[m.group(1)][n] += 1
    return files, candidates, callmap


def decide(candidates, callmap):
    """Gate front inserts on call-site corroboration; appends always apply.

    Returns (kept, skipped) where each kept entry is
    (path, pos, (qname, np, sig_idx, fronts, ends, decls)) with ``fronts``
    filtered to the corroborated subset (possibly empty).
    """
    kept, skipped = [], 0
    for cand in candidates:
        path, pos, info = cand
        qname, np = info[0], info[1]
        fronts, ends, decls = info[3], info[4], info[5]
        use_front = fronts
        if fronts:
            target = np + len(fronts) + len(ends)
            ca = callmap.get(qname)
            total = sum(ca.values()) if ca else 0
            match = ca.get(target, 0) if ca else 0
            if not (match >= 1 and match * 2 >= total):
                use_front = []
        if not use_front and not ends:
            skipped += 1
            continue
        kept.append((path, pos, (qname, np, info[2], use_front, ends, decls)))
    return kept, skipped


def apply(files, kept, check):
    """Walk B: rewrite the corroborated blocks (keyed by marker offset)."""
    wanted = collections.defaultdict(dict)
    for path, pos, info in kept:
        wanted[path][pos] = info
    changed_total = 0
    for path in files:
        if path not in wanted:
            continue
        text = read(path)
        if text is None:
            continue
        by_pos = wanted[path]
        out = []
        last = 0
        changed = 0
        for mk, body in iter_blocks(text):
            info = by_pos.get(mk.start())
            if info is None:
                continue
            _qname, np, sig_idx, fronts, ends, decls = info
            body_lines = body.splitlines(True)
            removes = sorted((decls[r][1] for r, _t in fronts + ends),
                             reverse=True)
            for dline in removes:
                if 0 <= dline < len(body_lines):
                    body_lines.pop(dline)
            newsig = rebuild_sig(body_lines[sig_idx].strip(),
                                 fronts, ends) if sig_idx < len(body_lines) else None
            if newsig is None:
                continue
            if not newsig.endswith("\n"):
                newsig += "\n"
            body_lines[sig_idx] = newsig
            new_body = "".join(body_lines)
            if new_body != body:
                changed += 1
            out.append(text[last:mk.end()])
            out.append(new_body)
            last = mk.end() + len(body)
        if not out:
            continue
        out.append(text[last:])
        new_text = "".join(out)
        changed_total += changed
        if not check and changed:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_text)
    return changed_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="out/src")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files, candidates, callmap = collect(args.src)
    kept, skipped = decide(candidates, callmap)
    changed = apply(files, kept, args.check)
    print("files scanned         %6d" % len(files))
    print("register candidates   %6d" % len(candidates))
    print("  corroborated        %6d" % len(kept))
    print("  uncalled/uncorrobed %6d" % skipped)
    print("blocks changed        %6d" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
