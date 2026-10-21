#!/usr/bin/env python3
"""Drop explicit template arguments from calls to flattened functions.

Ghidra spells a call the way the callee's symbol demangles, explicit template
arguments included::

    std::__ndk1::__tree_balance_after_insert<std::__ndk1::__tree_node_base<void*>*>(root, x);
    std::__ndk1::getline<char, std::__ndk1::char_traits<char>, std::__ndk1::allocator<char>>(in, str, c);

The definition behind that spelling, however, was recovered as an *ordinary*
function: the demangler flattened the instantiation, so ``out/src`` declares
``void std::__ndk1::__tree_balance_after_insert(long *, long *)``.  There is no
template for the arguments to bind to, and the compiler rejects the call
("'__tree_balance_after_insert' does not name a template but is followed by
template arguments").

Rewriting the call to ``..._after_insert(root, x)`` matches the declaration the
tree actually has and is what the rest of the recovered bodies do -- they call
these helpers with plain arguments.  Only calls whose callee resolves to a
function or member the tree defines are touched, so a class-template
construction (``std::__ndk1::vector<int>(n)``) keeps its arguments.

Comment text (the recovered signature in every file header) is left alone:
offsets are preserved by blanking comments rather than deleting them.
"""

import argparse
import collections
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: A qualified name that is followed by ``<``.  The argument list is walked by
#: hand because its own template arguments nest (``f<char, traits<char>>``).
_HEAD = re.compile(r"(?<![A-Za-z0-9_:>])((?:[A-Za-z_]\w*::)+[A-Za-z_]\w*)\s*<")


def mask_comments(text):
    """``text`` with every ``/* ... */`` blanked out, offsets preserved."""
    chars = list(text)
    i = 0
    n = len(text)
    while True:
        start = text.find("/*", i)
        if start < 0:
            return "".join(chars)
        end = text.find("*/", start + 2)
        end = n if end < 0 else end + 2
        for k in range(start, end):
            if chars[k] != "\n":
                chars[k] = " "
        i = end


def calls(code):
    """Yield ``(owner, name, start, stop)`` for every template-argument call.

    ``start``/``stop`` bracket the ``<...>`` that should go away.
    """
    n = len(code)
    for m in _HEAD.finditer(code):
        i = m.end()
        depth = 1
        while i < n and depth:
            c = code[i]
            if c == "<":
                depth += 1
            elif c == ">":
                depth -= 1
            elif c in ";{}":
                break
            i += 1
        if depth or i >= n:
            continue
        close = i - 1
        j = i
        while j < n and code[j] in " \t\r\n":
            j += 1
        if j >= n or code[j] != "(":
            continue
        depth = 0
        while j < n:
            c = code[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            elif c in ";{}":
                j = n
                break
            j += 1
        while j < n and code[j] in " \t\r\n":
            j += 1
        if code.startswith("::", j):
            # Ghidra names a static local ``f<...>(args...)::local``: the
            # spelling is used as a type there, not called.
            continue
        owner, name = m.group(1).rsplit("::", 1)
        yield owner, name, m.end(1), close + 1


def _declared(model, owner, name):
    """Is ``name`` a function or member that a call spelled by ``owner`` hits?"""
    owners = [ns for ns, bucket in model.funcs.items() if name in bucket]
    owners += [cls for cls, bucket in model.members.items() if name in bucket]
    for declared in owners:
        if declared == owner:
            return True
        if declared.endswith("::" + owner):
            return True
        if owner.endswith("::" + declared):
            return True
    return False


def _record(path, names):
    """Remember the calls that spelled template arguments (union, sorted)."""
    if not path:
        return
    old = set()
    if os.path.exists(path):
        old = set(line.strip() for line in
                  open(path, encoding="utf-8", errors="replace")
                  if line.strip())
    if old >= names:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for name in sorted(old | names):
            fh.write(name + "\n")


def shape_file(path, model, stats, dry_run=False, sink=None):
    text = open(path, encoding="utf-8", errors="replace").read()
    code = mask_comments(text)
    edits = []
    for owner, name, start, stop in calls(code):
        if not _declared(model, owner, name):
            stats["other"] += 1
            continue
        edits.append((start, stop))
        stats["calls"] += 1
        stats["names"][name] += 1
        stats["evidence"].add(owner + "::" + name)
        if sink is not None:
            line = text[text.rfind("\n", 0, start) + 1:start]
            sink.write("%s: %s...<%s>(...)\n" % (path, line.strip()[-60:],
                                                 text[start + 1:stop - 1][:40]))
    if not edits:
        return 0
    if dry_run:
        return len(edits)
    for start, stop in reversed(edits):
        text = text[:start] + text[stop:]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return len(edits)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--types", default=os.path.join("out", "types"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0,
                    help="print the first N rewrites")
    ap.add_argument("--record", default=os.path.join("out", "check",
                                                     "tmpl_calls.tsv"),
                    help="where to remember the names called as templates")
    args = ap.parse_args(argv)

    import check_syntax

    model = check_syntax.Model()
    check_syntax.load_classes(model, args.types)
    check_syntax.load_fields(model, args.types)
    check_syntax.scan(model, args.src)

    stats = collections.Counter()
    stats["names"] = collections.Counter()
    stats["evidence"] = set()
    shown = 0
    sink = sys.stdout if args.show else None
    files = 0
    paths = sorted(glob.glob(os.path.join(args.src, "**", "*.cpp"),
                             recursive=True))
    for path in paths:
        if sink is not None and shown >= args.show:
            sink = None
        count = shape_file(path, model, stats, args.dry_run, sink)
        shown += count if sink is not None else 0
        if count:
            files += 1
    if not args.dry_run:
        _record(args.record, stats["evidence"])
    print("files %d, changed %d, calls %d, other %d%s"
          % (len(paths), files, stats["calls"], stats["other"],
             " (dry run)" if args.dry_run else ""))
    for name, count in stats["names"].most_common():
        print("  %5d  %s" % (count, name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
