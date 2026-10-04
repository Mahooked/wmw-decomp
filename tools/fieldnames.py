"""Recover field names from the accessor symbols.

`headers.py` has to call every field `f_0x<offset>`, because the binary records
no identifiers anywhere.  That is enough to decompile correctly and useless to
read.  The one naming evidence the binary does contain is the set of `get*`/
`set*`/`is*`/`has*` member functions: Itanium mangling keeps the member name even
when the field's name is gone, so `getVisible` implies a field called `visible`.

The evidence is indirect, so the rules below are all ways of saying "this
accessor did not actually tell us which field it meant".  A wrong name is worse
than no name, because it reads as knowledge rather than as a placeholder.

Only `hyp=this` rows whose memory operand is based on `x0` are considered
----------------------------------------------------------------------
`_fieldraw.tsv` records one hypothesis per row, not a measurement.  A static
member function has no `this`, so its first argument lands in `x0` and every
access it makes is attributed to an object that is not there -- `Node::
setLocalPosition` reads the *argument's* first eight bytes, not a field of
`Node`.  `hyp=this` is still not enough on its own, so the base register is
re-read from the disassembly text: `[x1]` is somebody else's data whatever the
hypothesis column claims, `[x0]` is the only register that can be the object.

An accessor must read one offset, one direction
------------------------------------------------
`GameState::getGoalProgress` and `getGoalOverflow` each load the 16-byte pair at
`0x30` with a single `ldp`.  Both halves are real fields; the instruction simply
cannot say which is which, so naming either is a coin flip.

The direction must also match the verb.  A setter that only *loads* is the tell
that the attributed access is not the field being set: `Camera::setPosition`
loads `0x88`, checks it, and lets an inlined helper do the storing.  A getter
that only stores has the same problem mirrored.  Setters that legitimately load
(`setSoundsPaused` reads the old value to decide whether to fire an event) also
fail this way, but they lose nothing, because such a setter is already sharing
its offset with other accessors and is rejected below.

Several accessors on one offset is a warning, not a majority vote
---------------------------------------------------------------
`Camera::setPosition`, `setSize`, `setWidth`, `setHeight` and `isAnimating` all
read `0x88`.  Five different names for one byte is not five votes for the first
one seen; `0x88` is a guard flag that all five check before doing their real
work.  So an offset named by two different accessor names is rejected outright.
Agreement is accepted instead, and recorded as a vote count: `getSoundsPaused`
and `setSoundsPaused` both reduce to `soundsPaused`, which is corroboration the
binary actually provides.

A vote count of 1 is weaker, and the headers say so
---------------------------------------------------
A lone `getWorldPosition` reading one byte at `Node+124` is exactly what a dirty
flag looks like, and `Node+125`/`Node+126` are equally single-vote names from
`getWorldScale`/`getWorldAngle`.  Nothing in the binary distinguishes "the flag
that says the position is stale" from "the position", so these are emitted with
their vote count and left for a reader to judge; the offset name remains
available for anything that looks wrong.

Owners come from function ranges, not instruction starts
-------------------------------------------------------
`members.tsv` is the authority, and an access belongs to the function whose body
contains it.  Matching on address equality happens to catch only accessors whose
first instruction touches a field; matching on containment finds all of them.
Addresses claimed by more than one class are skipped rather than resolved, since
guessing an owner is the one failure this pass must not have.

Output: `out/types/fieldnames.tsv`, consumed by `headers.py --names`.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import json
import re

#: `getFoo`/`setFoo`/`isFoo`/`hasFoo`.  A leading underscore is allowed, since
#: `_hasRequirements` is a private accessor and still names its field.
ACCESSOR = re.compile(r"^_?(get|set|is|has)([A-Z]\w*)$")

#: The base register of a memory operand, e.g. `ldr x8, [x0, #0x88]` -> `x0`,
#: `ldp x10, x8, [x0, #0x30]` -> `x0`, `str wzr, [x0], #8` -> `x0`.
BASE_REG = re.compile(r"\[(\w+)")

#: `x0` and `w0` are the same physical register spelled for the operation's size.
THIS_REGS = frozenset(("x0", "w0"))

#: C++ keywords, plus the members `headers.py` invents for padding and pre-gap
#: bytes.  A recovered name colliding with one of these would not compile.
RESERVED = frozenset("""
alignas alignof and and_eq asm auto bitand bitor bool break case catch char
char8_t char16_t char32_t class compl concept const consteval constexpr
constinit const_cast continue co_await co_return co_yield decltype default
delete do double dynamic_cast else enum explicit export extern false float for
friend goto if inline int long mutable namespace new noexcept not not_eq
nullptr operator or or_eq private protected public register reinterpret_cast
requires return short signed sizeof static static_assert static_cast struct
switch template this thread_local throw true try typedef typeid typename union
unsigned using virtual void volatile wchar_t while xor xor_eq
_f _pad _pre _tail
""".split())


def lower_first(word: str) -> str:
    """`WorldPosition` -> `worldPosition`; leaves an initialism like `URL` alone."""
    if len(word) > 1 and word[1].isupper():
        return word
    return word[0].lower() + word[1:]


def field_name(verb: str, suffix: str) -> str:
    """Accessor name -> plausible field name.

    `is`/`has` are kept as predicates rather than flattened.  The field behind
    `isAnimating` is a flag the class also sets directly, and calling it
    `animating` would read as a value rather than as the answer to a question.
    """
    return verb + suffix if verb in ("is", "has") else lower_first(suffix)


def read_tsv(path: str):
    """Yield dict rows from a `#`-commented TSV, rejoining rows split by a newline.

    Some evidence columns carry free text that contains a newline, so a short
    row is a continuation rather than a malformed record.
    """
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        header = None
        pending = None
        for line in fh:
            if pending is not None:
                line = pending + "\n" + line.rstrip("\n\r")
                pending = None
            if line.startswith("#"):
                if header is None:
                    header = [h.strip() for h in
                              line.lstrip("#").rstrip("\n\r").split("\t")]
                continue
            if not line.strip():
                continue
            f = line.rstrip("\n\r").split("\t")
            if header and len(f) < len(header):
                pending = line.rstrip("\n\r")
                continue
            if header:
                yield dict(zip(header, f))


def owner_index(path: str):
    """(sorted starts, parallel ends, parallel class-or-None) for range lookup.

    A function range claimed by more than one class maps to `None` so the caller
    skips it; picking one would be a guess, and a name attached to the wrong class
    is the failure this whole pass exists to avoid.
    """
    spans = []
    for row in read_tsv(path):
        try:
            start = int(row["address"], 16)
            size = int(row["size"])
        except (KeyError, TypeError, ValueError):
            continue
        if size > 0:
            spans.append((start, start + size, row.get("class", "")))
    spans.sort()
    starts, ends, classes = [], [], []
    for start, end, cls in spans:
        if starts and start < starts[-1]:
            # Overlapping bodies: two symbols describing the same code.  Whichever
            # class comes second would shadow the first, so both are dropped.
            ends[-1] = 0
            starts[-1] = 0
        starts.append(start)
        ends.append(end)
        classes.append(cls)
    return starts, ends, classes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fieldraw", default="out/types/_fieldraw.tsv")
    ap.add_argument("--members", default="out/types/members.tsv")
    ap.add_argument("--out", default="out/types/fieldnames.tsv")
    args = ap.parse_args(argv)

    starts, ends, classes = owner_index(args.members)

    # (class, function) -> {offset: {access kinds}}
    reads = collections.defaultdict(lambda: collections.defaultdict(set))
    accessor_of = {}
    dropped = collections.Counter()
    for row in read_tsv(args.fieldraw):
        if row.get("hyp") != "this":
            continue
        m = ACCESSOR.match(row.get("fn") or "")
        if not m:
            continue
        base = BASE_REG.search(row.get("mnem") or "")
        if base is None or base.group(1) not in THIS_REGS:
            # Somebody else's data: a parameter, a local, or a saved register.
            dropped["base_register_is_not_this"] += 1
            continue
        try:
            addr = int(row["addr"], 16)
            off = int(row["offset"])
        except (KeyError, TypeError, ValueError):
            continue
        i = bisect.bisect_right(starts, addr) - 1
        if i < 0 or ends[i] == 0 or addr >= ends[i]:
            dropped["address_outside_any_function"] += 1
            continue
        key = (classes[i], row["fn"])
        reads[key][off].add(row.get("access", ""))
        accessor_of[key] = (m.group(1), m.group(2))

    # (class, offset) -> {name: [accessors]}
    votes = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    reasons = collections.Counter()
    for key, byoff in reads.items():
        cls, fn = key
        verb, suffix = accessor_of[key]
        if len(byoff) != 1:
            reasons["accessor_touches_several_fields"] += 1
            continue
        off, kinds = next(iter(byoff.items()))
        if kinds - {"load"} and kinds - {"store"}:
            reasons["accessor_reads_and_writes"] += 1
            continue
        want_kind = "store" if verb == "set" else "load"
        if kinds != {want_kind}:
            # Mixed direction already counted above, so this is the accessor
            # doing the opposite of what its name says.
            reasons["setter_that_only_loads" if verb == "set"
                    else "getter_that_only_stores"] += 1
            continue
        want = field_name(verb, suffix)
        if want in RESERVED:
            reasons["name_is_reserved_word"] += 1
            continue
        votes[cls][off][want].append(fn)

    # class -> offset -> (name, votes); an offset claimed under two names is
    # ambiguous, and ambiguity is not resolved by picking the first.
    names = collections.defaultdict(dict)
    for cls, byoff in votes.items():
        for off, byname in byoff.items():
            if len(byname) > 1:
                reasons["offset_has_several_names"] += 1
                continue
            (nm, fns), = byname.items()
            names[cls][off] = (nm, len(fns))

    # A name may appear at most once per class, or the struct will not compile.
    for cls, slot in names.items():
        byname = collections.defaultdict(list)
        for off, (nm, _) in slot.items():
            byname[nm].append(off)
        for nm, offs in byname.items():
            if len(offs) > 1:
                for off in offs:
                    del slot[off]
                reasons["name_repeated_in_class"] += 1

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\toffset\tname\tvotes\taccessors\n")
        for cls in sorted(names):
            for off in sorted(names[cls]):
                nm, n = names[cls][off]
                fns = sorted(votes[cls][off][nm])
                fh.write("%s\t%d\t%s\t%d\t%s\n" % (cls, off, nm, n, ",".join(fns)))

    summary = dict(sorted(reasons.items()))
    summary.update({k: v for k, v in sorted(dropped.items())})
    summary["accessor_functions"] = len(reads)
    summary["classes_named"] = len(names)
    summary["fields_named"] = sum(len(v) for v in names.values())
    summary["fields_single_accessor"] = sum(
        1 for slot in names.values() for _, n in slot.values() if n == 1)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())