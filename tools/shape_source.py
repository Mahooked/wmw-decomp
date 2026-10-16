"""Shape the decompiled bodies in ``out/src`` back toward source.

Ghidra decompiles machine code, so every body carries work the *compiler* added
and the original source never had.  The biggest and most mechanical of those
artefacts is the stack protector (``-fstack-protector``): a canary loaded from
the thread-control block at function entry and compared at every exit.  It is
pure ABI, present in 2,513 of the 8,229 bodies, and reads as noise:

    lVar1 = tpidr_el0;
    lStack_38 = *(long *)(lVar1 + 0x28);
    ...
    if (*(long *)(lVar1 + 0x28) == lStack_38) {
      return;
    }
    __stack_chk_fail();
    return;

The source had none of it.  This pass deletes the two entry lines, the guard
test, the ``__stack_chk_fail`` call and the now-dead locals, leaving the body's
own ``return`` untouched.  Removing the epilogue rather than the body's return
is deliberate: the trailing ``return`` belongs to the function, the ``if``
around the call belongs to the compiler.

Two shapes occur, because the compiler is free to invert the test::

    if (guard == canary) { return; }        // fall through to the abort
    __stack_chk_fail();
    return;

    if (guard != canary) { __stack_chk_fail(); return; }
    return;

Both are handled, whichever local the decompiler chose for the TCB pointer or
the canary, provided the guard block contains nothing but returns.  Anything
else is left exactly as it was and counted as *unstrippable*, because a guard
test interleaved with real code is not an artefact to be sliced out on a guess.

Conservative by construction: a function is only rewritten when the canary and
the TCB local are provably dead afterwards, so a stack slot the decompiler
reused for a real local can never lose its initialiser.  The pass is idempotent
-- a stripped body no longer contains the pattern -- and ``--check`` fails while
any strippable body remains.

Output: rewritten in place under ``out/src`` (``--check`` only reports).
"""

from __future__ import annotations

import argparse
import os
import re
import sys

MARK = re.compile(r"(?=^/\* ok  address )", re.M)

RE_GV = re.compile(r"^(\s*)([A-Za-z_]\w*) = tpidr_el0;$")
# The canary lives in a scalar local or in one element of a small saved-register
# array; the TCB pointer is always a plain local.
OPERAND = r"[A-Za-z_]\w*(?:\[\d+\])?"
RE_CAN_SAVE = re.compile(
    r"^(\s*)(%s) = \*\(long \*\)\(([A-Za-z_]\w*) \+ 0x28\);$" % OPERAND)
RE_IF_EQ = re.compile(
    r"^(\s*)if \(\*\(long \*\)\(([A-Za-z_]\w*) \+ 0x28\) == (%s)\) \{$"
    % OPERAND)
RE_IF_NE = re.compile(
    r"^(\s*)if \(\*\(long \*\)\(([A-Za-z_]\w*) \+ 0x28\) != (%s)\) \{$"
    % OPERAND)
# __stack_chk_fail is declared noreturn, but Ghidra sometimes types it as
# returning, so the call can appear as `uVar3 = __stack_chk_fail();`, handed a
# spurious argument (`__stack_chk_fail(uVar5);`) or cast to a pointer
# (`plVar4 = (long *)__stack_chk_fail();`).
RE_CHK = re.compile(
    r"^\s*(?:[A-Za-z_]\w* = )?(?:\([^()]*\)\s*)?__stack_chk_fail\([^;()]*\);$")
RE_DECL_LONG = re.compile(
    r"^(\s*)(long|undefined[0-9]*|ulong|int|uint|float|double|char|byte|short"
    r"|code)\s+([A-Za-z_]\w*)(\s*\[[^\]]*\])*;$")

# A guard-block line that is safe to delete: a return, possibly with the return
# expression wrapped over several lines, and nothing with its own scope.
CONTROL = re.compile(r"\b(if|else|for|while|switch|do|goto|case)\b")


def _is_returnish(line: str) -> bool:
    if "{" in line or "}" in line:
        return False
    if CONTROL.search(line):
        return False
    return True


def strip_block(block: str):
    """Strip the stack protector from one function block.

    Returns ``(new_block, stripped)``; ``new_block is block`` when nothing was
    done.  A block that still needs stripping but does not match the expected
    shape is reported as unstrippable by :func:`plan`.
    """
    lines = block.split("\n")

    gv = None
    gi = None
    for i, line in enumerate(lines):
        m = RE_GV.match(line)
        if m:
            gv, gi = m.group(2), i
            break

    canary = None
    ci = None
    for i, line in enumerate(lines):
        m = RE_CAN_SAVE.match(line)
        if m and gv is not None and m.group(3) == gv:
            canary, ci = m.group(2), i
            break

    chk = [i for i, line in enumerate(lines) if RE_CHK.match(line)]
    if gv is None or canary is None or len(chk) != 1:
        return block, False
    k = chk[0]

    # The guard test is the nearest `if` above the abort; its operator picks
    # the shape.  `==` falls through to the abort (the abort is *after* the
    # block); `!=` jumps over it (the abort is *inside* the block).
    o = kind = None
    for i in range(k - 1, -1, -1):
        if RE_IF_EQ.match(lines[i]):
            o, kind = i, "eq"
            break
        if RE_IF_NE.match(lines[i]):
            o, kind = i, "ne"
            break
    if o is None:
        return block, False
    m = (RE_IF_EQ if kind == "eq" else RE_IF_NE).match(lines[o])
    if m.group(2) != gv or m.group(3) != canary:
        return block, False

    remove = set()
    if kind == "eq":
        # Variant A: the test falls through to the abort.
        if not (k >= 1 and lines[k - 1].strip() == "}"):
            return block, False
        body = lines[o + 1:k - 1]
        if not body or not all(_is_returnish(x) for x in body):
            return block, False
        if "return" not in "\n".join(body):
            return block, False
        remove.update(range(o, k + 1))
    else:
        # Variant B: the test jumps over the abort.
        c = None
        for i in range(k + 1, len(lines)):
            if lines[i].strip() == "}":
                c = i
                break
            if not _is_returnish(lines[i]):
                return block, False
        if c is None:
            return block, False
        body = lines[o + 1:c]
        if not all(_is_returnish(x) or RE_CHK.match(x) for x in body):
            return block, False
        if "return" not in "\n".join(body):
            return block, False
        remove.update(range(o, c + 1))

    # The two entry lines go too, but only if they are not already inside the
    # removed epilogue.
    remove.add(gi)
    remove.add(ci)

    # A canary stored in an array element is only dead if the whole array is.
    dead_names = [gv, canary.split("[")[0]]

    def is_dead_decl(line):
        m = RE_DECL_LONG.match(line)
        return bool(m and m.group(3) in dead_names)

    # Drop the guard's own declarations with the guard.
    kept = [
        ln for i, ln in enumerate(lines)
        if i not in remove and not is_dead_decl(ln)
    ]
    remaining = "\n".join(kept)
    # A canary or TCB local that is still referenced is a real local the
    # decompiler reused for that slot: leave the whole block alone.
    for name in dead_names:
        if re.search(r"\b%s\b" % re.escape(name), remaining):
            return block, False
    return remaining, True


def plan(text: str):
    """Return ``(edits, stats)`` for a whole file, without applying them.

    ``edits`` is a list of ``(start, end, replacement)`` spans.
    """
    parts = MARK.split(text)
    stats = {"stripped": 0, "unstrippable": 0}
    out = []
    for part in parts:
        if not part.startswith("/* ok  address "):
            out.append(part)
            continue
        new, done = strip_block(part)
        if done:
            out.append(new)
            stats["stripped"] += 1
        else:
            out.append(part)
            if "tpidr_el0" in part or "__stack_chk_fail" in part:
                stats["unstrippable"] += 1
    return "".join(out), stats


def process_file(path: str):
    text = open(path, encoding="utf-8", errors="replace").read()
    new, stats = plan(text)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--check", action="store_true",
                    help="fail if any strippable stack protector remains")
    args = ap.parse_args(argv)

    files = stripped = unstrippable = 0
    for base, _dirs, fnames in os.walk(args.src):
        for name in fnames:
            if not name.endswith(".cpp"):
                continue
            files += 1
            path = os.path.join(base, name)
            if args.check:
                text = open(path, encoding="utf-8",
                            errors="replace").read()
                _new, stats = plan(text)
            else:
                stats = process_file(path)
            stripped += stats["stripped"]
            unstrippable += stats["unstrippable"]

    print("scanned files              %6d" % files)
    print("stack protectors stripped  %6d" % stripped)
    print("left alone (not the shape) %6d" % unstrippable)
    if args.check:
        if stripped:
            print("shape_source: %d stack protectors still strippable"
                  % stripped, file=sys.stderr)
            return 1
        print("shape_source: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
