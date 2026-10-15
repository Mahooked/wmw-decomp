"""Apply the exact parameter types from ``out/symbols/signatures.tsv`` to the
decompiled definitions in ``out/src``.

The Itanium ABI encodes every parameter type in the symbol and GCC's own
rendering of the name validates the parse (``test_sigs.py``), so the lists in
``signatures.tsv`` are exact rather than inferred.  Ghidra can only *apply* a
type it can resolve in its own type system, so the ones it rejected -- mostly
libc++ template types -- still read as ``undefined8 param_1``.  This pass writes
the exact type back as text, which needs no type system at all.

Alignment
---------
Ghidra numbers the inferred parameters ``param_1..`` in AAPCS64 allocation
order:

* A *free* function's order is source order, so a definition whose parameter
  count already equals the signature's is a straight positional rename:
  ``param_i`` takes type ``params[i-1]``.
* A non-static *member* also receives ``this`` in ``x0``, which the signature
  omits, so its count is exactly one greater.  There ``param_1`` *is* ``this``:
  it is dropped from the parameter list and renamed in the body, and the rest
  shift by one.

Any other count difference is left alone -- an alignment we cannot prove is a
wrong type waiting to happen.  A ``+1`` definition is only trusted when
``members.tsv`` lists it as a member, so a free function that merely happens to
carry one extra inferred argument is not mistaken for a method.

Only definitions whose parameters still contain ``undefined`` are touched, so
the pass is idempotent.  Comments are skipped when locating the parameter list,
nothing is rewritten inside a string, and the type is the true source type
(``params``, references kept) rather than Ghidra's pointer-normalised ``gtype``.
"""

import argparse
import os
import re
import sys

_ADDR = re.compile(r"/\*\s*ok\s+address\s+0x([0-9a-fA-F]+)\s+size\s+\d+\s*\*/")
_FUNC_PTR = re.compile(r"^(.*?)\(([^()]*\*&?)\)(.*)$")
_NAME = re.compile(r"([A-Za-z_]\w*)\s*$")


def load_signatures(path):
    """address -> list of exact parameter types."""
    sig = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 8 or not f[4]:
                continue
            try:
                sig[int(f[0], 16)] = f[4].split("|")
            except ValueError:
                continue
    return sig


def load_members(path):
    """addresses of the functions ``members.tsv`` classifies as members."""
    members = set()
    with open(path, encoding="utf-8") as fh:
        hdr = None
        for line in fh:
            if line.startswith("#"):
                hdr = [h.strip() for h in line.lstrip("#").rstrip("\n").split("\t")]
                continue
            f = line.rstrip("\n").split("\t")
            if hdr is None or "address" not in hdr:
                continue
            d = dict(zip(hdr, f))
            try:
                members.add(int(d["address"], 16))
            except (KeyError, ValueError):
                continue
    return members


def _skip_comment(text, i):
    """If a ``/* */`` comment starts at ``i``, return the index after it."""
    if text.startswith("/*", i):
        j = text.find("*/", i + 2)
        return len(text) if j < 0 else j + 2
    return i


def param_span(decl):
    """(open, close) indices of the definition's parameter list in ``decl``.

    Comments are skipped, so the leading ``/* mangled */`` / ``/* sig */``
    blocks cannot supply the parenthesis.  The first top-level ``(`` is the
    parameter list: the return type is a bare type with no parentheses.
    """
    i = 0
    n = len(decl)
    while i < n:
        j = _skip_comment(decl, i)
        if j != i:
            i = j
            continue
        if decl[i] == "(":
            depth = 0
            k = i
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


def split_params(inner):
    """Split a parameter list on top-level commas."""
    parts, depth, cur = [], 0, ""
    for c in inner:
        if c in "<([":
            depth += 1
        elif c in ">)]":
            depth -= 1
        if c == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts]


def name_of(rendered):
    m = _NAME.search(rendered)
    return m.group(1) if m else "arg"


def declare_param(type_str, name):
    """Render ``type name``, placing the name inside a function pointer."""
    t = type_str.strip()
    if t == "...":
        return "..."
    m = _FUNC_PTR.match(t)
    if m:
        return "%s(%s%s)%s" % (m.group(1), m.group(2), name, m.group(3))
    if t.endswith("*"):
        stars = len(t) - len(t.rstrip("*"))
        base = t[:-stars].rstrip()
        return "%s %s%s" % (base, "*" * stars, name)
    if t.endswith("&"):
        return "%s %s" % (t, name)
    return "%s %s" % (t, name)


def plan(text, sig, members):
    """Return (edits, stats) for one file.

    ``edits`` is a list of ``(start, end, replacement)`` to apply in reverse.
    """
    edits = []
    stats = {"applied": 0, "renamed": 0, "skipped": 0}
    marks = list(_ADDR.finditer(text))
    for idx, m in enumerate(marks):
        a = int(m.group(1), 16)
        if a not in sig:
            continue
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
        block = text[m.end():end]
        brace = block.find("{")
        if brace < 0:
            continue
        decl = block[:brace]
        span = param_span(decl)
        if span is None:
            continue
        opin, cpin = span
        inner = decl[opin + 1:cpin].strip()
        plist = [] if inner in ("", "void") else split_params(inner)
        if not any("undefined" in p for p in plist):
            continue  # already typed, or nothing we can name
        params = sig[a]
        delta = len(plist) - len(params)
        if delta == 0:
            names = [name_of(p) for p in plist]
            new_inner = ",".join(declare_param(params[i], names[i])
                                 for i in range(len(params)))
        elif delta == 1 and a in members:
            # param_1 is `this`; the survivors shift down so the definition
            # reads param_1..param_n alongside the signature.
            new_inner = ",".join(declare_param(params[i], "param_%d" % (i + 1))
                                 for i in range(len(params)))
            body = block[brace:]

            def shift(m):
                return "this" if m.group(1) == "1" else "param_%d" % (
                    int(m.group(1)) - 1)

            new_body = re.sub(r"\bparam_(\d+)\b", shift, body)
            if new_body != body:
                edits.append((m.end() + brace, end, new_body))
                stats["renamed"] += 1
        else:
            stats["skipped"] += 1
            continue
        edits.append((m.end() + opin + 1, m.end() + cpin, new_inner))
        stats["applied"] += 1
    return edits, stats


def process_file(path, sig, members):
    text = open(path, encoding="utf-8", errors="replace").read()
    edits, stats = plan(text, sig, members)
    if edits:
        for start, end, repl in sorted(edits, reverse=True):
            text = text[:start] + repl + text[end:]
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--signatures",
                    default=os.path.join("out", "symbols", "signatures.tsv"))
    ap.add_argument("--members",
                    default=os.path.join("out", "types", "members.tsv"))
    ap.add_argument("--check", action="store_true",
                    help="fail if any applicable definition is left untyped")
    args = ap.parse_args(argv)

    sig = load_signatures(args.signatures)
    members = load_members(args.members)
    print("signatures with parameters %6d" % len(sig))
    print("member functions           %6d" % len(members))

    files = applied = renamed = skipped = 0
    for base, _dirs, fnames in os.walk(args.src):
        for name in fnames:
            if not name.endswith(".cpp"):
                continue
            files += 1
            path = os.path.join(base, name)
            if args.check:
                text = open(path, encoding="utf-8", errors="replace").read()
                _edits, stats = plan(text, sig, members)
            else:
                stats = process_file(path, sig, members)
            applied += stats["applied"]
            renamed += stats["renamed"]
            skipped += stats["skipped"]

    print("scanned files              %6d" % files)
    print("definitions typed          %6d" % applied)
    print("  of those, member `this`  %6d" % renamed)
    print("left alone (other delta)   %6d" % skipped)
    if args.check:
        if applied:
            print("apply_signatures: %d definitions still applicable" % applied,
                  file=sys.stderr)
            return 1
        print("apply_signatures: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
