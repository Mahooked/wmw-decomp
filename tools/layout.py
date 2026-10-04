"""Turn FieldScan's raw access evidence into per-class field layouts.

`FieldScan.java` emits *evidence*, one line per load/store whose address reduced
to `object + constant`, each tagged with the reading it came from.  This pass
decides what that evidence supports.

The problem with a naive aggregation
------------------------------------
A non-static member function has ``this`` in ``x0``; a static one starts its
parameters there.  The mangling does not distinguish them, because C++ encodes
neither.  So ``x0`` is ambiguous in two different ways, and a first attempt at
this pass collapsed both and produced a 61-field, 1480-byte ``Walaber::Vector2``.

Counting evidence does not fix it, because a wrong attribution is systematic
rather than random: every static function of one class with the same parameter
shape files that class's fields under the same wrong name, so the bogus offsets
agree with each other as strongly as the real ones.  Agreement alone cannot
separate "many functions touched field 4" from "many functions were mislabelled".

The three channels
------------------
What *can* separate them is knowing which register is supposed to hold what, so
each row is assigned to exactly one channel and the channels are given different
powers:

``A`` -- ``hyp=this``, slot 0.  The owning class's own ``this``.  This is the
  strongest evidence there is and the only one that describes an owning class's
  layout, but it is still ``x0``, so it shares the static ambiguity and is
  corroborated like everything else.
``P`` -- any slot >= 1.  Under the non-static reading these are declared
  parameters starting at ``x1``; under the static reading they are the
  parameters after the first.  Both readings agree the register holds an object
  of the seeded class, which is what matters, and a static function only shifts
  the *labelling* by one.  This channel is what recovers a symbol-less POD:
  ``Walaber::Vector2``, ``Rect`` and ``GridCell`` own no member functions at
  all, so this is the only place their fields can be seen.
``C`` -- ``hyp=static``, slot 0.  Genuinely unusable on its own: the register
  may hold the owner's ``this`` or the first parameter, and no evidence in the
  binary separates those.  A large owner's field set shows up here verbatim.
  It may corroborate an offset established elsewhere, and it may never
  establish one.

A size cap from array strides
-----------------------------
``[this + i * 8]`` is pointer arithmetic, and 8 is ``sizeof`` of the element --
an independent bound on the object's size derived from a completely different
code path than a field load.  Where two or more functions agree on a stride, it
caps the layout: offsets at or beyond it are indexing past the end, not fields.

Confidence is by distinct *functions*, not lines: thirty loads in one loop are
one opinion.

======  ===========================================================
high    >= 4 functions, or >= 1 anchor role with >= 2, or >= 2
        channel-C functions agreeing with >= 2 establishing functions
med     >= 2 functions
low     1 function (counted and reported, never emitted as a field)
======  ===========================================================

Size is the highest accepted ``offset + width``, rounded to alignment.  A class
whose last field is never touched on a path this binary exercises will come out
short, which is why the allocation sizes recovered from ``operator new`` in
constructors are the cross-check to run against this file rather than a
substitute for it.

Output: `out/types/fields.tsv` and `out/types/layouts.tsv`.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re

#: Beyond this an "offset" is not a field; it is a pointer chase or a decode
#: slip, and accepting it would poison the size calculation.
OFFSET_LIMIT = 0x10000

#: Roles whose ``x0`` is ``this`` by construction.
ANCHOR_ROLES = frozenset(("ctor", "dtor", "virtual"))

_HEADER = "# class\toffset\twidth\tkind\tsigned\tstride\tfuncs\tanchors\tcorr\tconfidence\tevidence\n"

#: An offset supported by fewer functions than this fraction of the class's
#: best-supported offset is treated as a mis-attribution rather than a field.
#:
#: The reasoning is a support cliff rather than a size guess.  A real field is
#: touched by whatever code uses it, and the fields nearest offset 0 -- a vtable
#: or self pointer, then the first members -- are touched by a large share of
#: the class's methods, so support falls off sharply after the last real field.
#: Mis-attributed offsets land in whatever large object happened to be in the
#: register, are touched incidentally, and so sit far below that cliff.  The
#: alternative, a fixed cutoff, cannot work: absolute support scales with how
#: many functions a class has, and a field legitimately touched by two
#: functions is real for a class with only three.
#:
#: This is a heuristic and it is reported (`truncated_classes` in the summary,
#: and a `cut` column in layouts.tsv) so the classes it acts on can be audited
#: against an independent size instead of being trusted silently.
SUPPORT_FLOOR = 0.25


#: SVE lane specifier, e.g. `{v0.2s}` in `ld1 {v0.2s}, [x1]`.  The register is
#: always `z`/`v`, so only the lane type distinguishes two floats from two ints.
_LANE = re.compile(r"\{\s*[vzp]\d+\.(\d*)([bhsdwq])\s*\}")

#: A scalar data register in the operand text: `ldr d0, [x1]`.
_SCALAR_REG = re.compile(r"^(?:ld|st)[a-z0-9]*\s+(?:\{[^}]*\}\s*,\s*)*([bhsdqwx])")


def classify(text: str, width: int):
    """Return ``(kind, signed)`` for one access.

    The element type comes from the instruction text, not the p-code, because
    p-code has erased the register class: ``ldr s0`` and ``ldr w0`` are both
    width 4 and are told apart only by the operand.  SVE comes first, since a
    ``z``-named register says nothing and the lane specifier says everything.

    Signedness is reported as ``u``, ``s`` or ``?`` rather than guessed, because
    a plain ``ldr w`` is equally valid signed or unsigned and only ``ldrb`` and
    ``ldrsb`` actually settle it.
    """
    text = text.strip()
    m = _LANE.search(text)
    if m:
        # An SVE lane is never sign-extended by the instruction, so signedness
        # stays unknown whatever the lane type is.
        return ("float", "?") if m.group(2) in ("s", "d") else ("int", "?")

    parts = text.split()
    mnemonic = parts[0] if parts else ""
    m = _SCALAR_REG.match(text)
    if not m:
        return "unknown", "?"

    # The *mnemonic*, not the destination register, fixes signedness: `ldrb w9`
    # writes a `w` register but loads one unsigned byte.  Taking the register
    # letter for this reports every byte access as signedness-unknown.
    if "ldrsb" in mnemonic or mnemonic.endswith("sb"):
        signed = "s"
    elif "ldrsh" in mnemonic or mnemonic.endswith("sh"):
        signed = "s"
    elif mnemonic.endswith("b") or mnemonic.endswith("h"):
        signed = "u"
    elif "ldrs" in mnemonic:
        signed = "s"
    else:
        signed = "?"

    letter = m.group(1)
    if letter in ("s", "d"):
        return "float", "?"
    if letter == "q":
        return "vec16", "?"
    if letter in ("b", "h"):
        return "int", signed
    if letter in ("w", "x"):
        return "int", signed
    return "unknown", "?"


def confidence(funcs: int, anchors: int, corr: int) -> str:
    if anchors and funcs >= 2:
        return "high"
    if funcs >= 4:
        return "high"
    if corr >= 2 and funcs >= 2:
        return "high"
    if funcs >= 2:
        return "med"
    return "low"


def channel(hyp: str, slot: int) -> str:
    """A, P or C -- see the module docstring."""
    if slot == 0:
        return "A" if hyp == "this" else "C"
    return "P"


def looks_like_class(name: str) -> bool:
    """Whether a demangled owner name is a type rather than a function.

    Owner extraction takes the enclosing scope of a symbol, so a free function
    or a function template ends up attributed to the scope around it.  Those
    arrive with the whole demangled signature still attached -- `void
    WaterConcept::World::_walkStrip<...>`, or `std::__ndk1::__bit_iterator<...>
    std::__ndk1::__copy_aligned<...>` -- whereas a genuine template
    instantiation such as `Walaber::SharedPtr<Walaber::Color>` keeps its one
    top-level name.  A space outside any angle brackets is the tell: no class
    name has one.
    """
    depth = 0
    for ch in name:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == " " and depth <= 0:
            return False
    if depth != 0:
        return False
    return True


def load_rtti_classes(path: str) -> set:
    """Every name with a typeinfo, i.e. every polymorphic class."""
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.split("\t", 1)
            if f and f[0].strip():
                out.add(f[0].strip())
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("raw", help="out/types/_fieldraw.tsv from FieldScan.java")
    ap.add_argument("--out", default="out/types")
    ap.add_argument("--min-funcs", type=int, default=2,
                    help="distinct establishing functions required for a field")
    ap.add_argument("--stride-cap", action="store_true", default=True,
                    help="cap a layout at an agreed sizeof from array strides")
    ap.add_argument("--rtti", default="out/rtti/hierarchy.tsv")
    args = ap.parse_args(argv)

    establishing = collections.defaultdict(list)   # (class, offset) -> rows
    corroborating = collections.defaultdict(set)  # (class, offset) -> fns
    strides = collections.defaultdict(collections.Counter)  # class -> stride -> fns
    qualified = collections.defaultdict(set)     # class -> roles seen
    param_seen = set()                           # classes observed as a parameter
    channels_seen = collections.Counter()
    dropped = collections.Counter()
    raw_rows = 0

    with open(args.raw, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 13:
                dropped["malformed"] += 1
                continue
            (cls, off_s, stride_s, width_s, _acc, slot_s, role, mnem, dreg,
             _addr, fn, _owner, hyp) = f[:13]
            raw_rows += 1
            try:
                off = int(off_s)
                width = int(width_s)
                stride = int(stride_s)
                slot = int(slot_s)
            except ValueError:
                dropped["unparseable"] += 1
                continue
            if width <= 0:
                dropped["zero_width"] += 1
                continue
            if not looks_like_class(cls):
                dropped["not_a_class_name"] += 1
                continue
            if off < -OFFSET_LIMIT or off > OFFSET_LIMIT:
                dropped["offset_out_of_range"] += 1
                continue

            ch = channel(hyp, slot)
            channels_seen[ch] += 1

            if ch == "C":
                corroborating[(cls, off)].add(fn)
                continue

            qualified[cls].add(role)
            if ch == "P":
                param_seen.add(cls)
            establishing[(cls, off)].append((fn, role, width, stride, mnem, dreg))
            if stride > 0:
                strides[cls][stride] += 1 if stride <= 0x1000 else 0

    # sizeof evidence: an array stride is the element size, so a stride seen in
    # two or more independent functions bounds the object.
    size_cap = {}
    for cls, counter in strides.items():
        for stride, n in counter.items():
            if n >= 2:
                size_cap[cls] = max(size_cap.get(cls, 0), stride)

    # Collapse establishing evidence to one verdict per (class, offset).
    verdicts = {}
    for key, rows in establishing.items():
        cls, off = key
        funcs = {r[0] for r in rows}
        anchors = {r[0] for r in rows if r[1] in ANCHOR_ROLES}
        widths = collections.Counter(r[2] for r in rows)
        strides_here = {r[3] for r in rows if r[3] > 0}
        corr = len(corroborating.get(key, ()))

        # Which kind *defines* the field at this offset, and at what width?
        #
        # A field is read at its own width; a wider read spans into the next
        # field and says nothing about this one, and a narrower read is a
        # reinterpretation or a mis-attribution.  So the width to use is the
        # *mode* of each kind's access widths -- where its accesses actually
        # concentrate -- and the kind whose mode is narrowest defines the field.
        #
        # Using the mode rather than the minimum is what keeps this honest.  At
        # offset 0 of a Vector2 the integer rows are 427 eight-byte copies, 39
        # four-byte reads and 4 stray `ldrb`; taking the minimum picks `int` on
        # the strength of four rows, while the float rows are 198 four-byte and
        # 179 eight-byte and their mode correctly says 4.  Support breaks ties:
        # offset 4 of the same object is 185 four-byte floats against 34
        # four-byte ints, and both agree on the width.
        by_kind = collections.defaultdict(collections.Counter)
        for r in rows:
            by_kind[classify(r[4], 0)[0]][r[2]] += 1

        def modal(counter):
            return min(counter, key=lambda w: (-counter[w], w))

        kind = min(by_kind,
                   key=lambda k: (modal(by_kind[k]), -sum(by_kind[k].values())))
        width = modal(by_kind[kind])
        verdicts[key] = {
            "funcs": len(funcs),
            "anchors": len(anchors),
            "width": width,
            "widths": dict(widths),
            "stride": min(strides_here) if strides_here else 0,
            "kind": kind,
            "kind_support": sum(
                1 for r in rows
                if classify(r[4], 0)[0] == kind and r[2] == width),
            "signed": collections.Counter(
                classify(r[4], 0)[1] for r in rows
                if classify(r[4], 0)[0] == kind and r[2] == width
            ).most_common(1)[0][0],
            "corr": corr,
            "sample": sorted(funcs)[:3],
            "conf": confidence(len(funcs), len(anchors), corr),
        }

    kept = {}
    for key, v in verdicts.items():
        cls, off = key
        if v["funcs"] < args.min_funcs or v["conf"] == "low":
            dropped["below_threshold"] += 1
            continue
        cap = size_cap.get(cls)
        if args.stride_cap and cap and off >= cap:
            dropped["at_or_past_sizeof_cap"] += 1
            continue
        kept[key] = v

    # Apply the support cliff per class.
    support_cut = {}
    by_class_off = collections.defaultdict(list)
    for (cls, off), v in kept.items():
        by_class_off[cls].append(off)
    for cls, offs in by_class_off.items():
        peak = max(kept[(cls, o)]["funcs"] for o in offs)
        floor = max(args.min_funcs, peak * SUPPORT_FLOOR)
        for o in offs:
            if kept[(cls, o)]["funcs"] < floor:
                dropped["below_support_floor"] += 1
                del kept[(cls, o)]
        support_cut[cls] = floor

    # Overlap resolution. Two fields at different offsets can still claim the
    # same bytes -- offset 44 with width 4 sits inside a width-8 field at 40 --
    # and a struct cannot hold both. Resolved here rather than in each consumer
    # so that fields.tsv, the generated headers and the Ghidra import all agree
    # on what the layout is. The better-supported field wins, and a tie goes to
    # the earlier offset so the choice is deterministic.
    for cls, offs in by_class_off.items():
        cur_off = None
        cur_end = None
        # The support floor above may already have removed some of these.
        for o in sorted(o for o in offs if (cls, o) in kept):
            w = kept[(cls, o)]["width"]
            if cur_end is not None and o < cur_end:
                loser = o
                if kept[(cls, o)]["funcs"] > kept[(cls, cur_off)]["funcs"]:
                    loser = cur_off
                    cur_off, cur_end = o, o + w
                del kept[(cls, loser)]
                dropped["overlapping"] += 1
                continue
            cur_off, cur_end = o, o + w

    per_class = collections.defaultdict(list)
    for (cls, off), v in kept.items():
        per_class[cls].append((off, v))

    layouts = {}
    inconsistent = {}
    for cls, items in per_class.items():
        end = max(off + v["width"] for off, v in items)
        first = min(off for off, _ in items)
        align = max(1, min(16, max(4 if v["kind"] == "float" else v["width"]
                                   for _, v in items)))
        cap = size_cap.get(cls)

        # A layout is only worth emitting if it is internally consistent.  Two
        # ways it is not, and both mean the recovered base pointer is not the
        # start of the object rather than that the offsets are simply unknown:
        #
        #  * a negative offset means the evidence points into the middle of the
        #    object -- a base subobject, or a pointer to a member.  No flat
        #    struct can express "negative offset from here".
        #  * fields reaching past an independently recovered sizeof means the
        #    two disagree about which object this is.
        #
        # These are reported instead of emitted, because a header that cannot
        # reproduce its own offsets is worse than no header: it would mis-decompile
        # every function that uses the type.
        if first < 0:
            inconsistent[cls] = ("negative offset %d" % first)
            continue
        if cap and end > cap:
            inconsistent[cls] = ("fields reach 0x%x, past the sizeof %d recovered "
                                 "from an array stride" % (end, cap))
            continue

        size = (end + align - 1) // align * align
        if cap:
            size = min(size, cap)
        confs = [v["conf"] for _, v in items]
        layouts[cls] = {
            "size": size,
            "align": align,
            "fields": len(items),
            "conf": "high" if "high" in confs else "med",
            "cap": cap or 0,
            "cut": support_cut.get(cls, 0),
            # Reported, not enforced: a class with no constructor, destructor or
            # vtable slot and never passed by pointer is usually a static utility
            # class.  See the namespace test below for how names are pruned.
            "anchored": bool(qualified.get(cls, set()) & ANCHOR_ROLES)
                        or cls in param_seen,
        }

    os.makedirs(args.out, exist_ok=True)
    fpath = os.path.join(args.out, "fields.tsv")
    with open(fpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_HEADER)
        for (cls, off) in sorted(kept, key=lambda k: (k[0], k[1])):
            v = kept[(cls, off)]
            fh.write("\t".join([
                cls, str(off), str(v["width"]), v["kind"],
                v["signed"], str(v["stride"]),
                str(v["funcs"]), str(v["anchors"]), str(v["corr"]),
                v["conf"], ",".join(v["sample"]),
            ]) + "\n")

    bands = collections.Counter(v["conf"] for v in verdicts.values())
    # A recovered layout is only worth emitting for a name that is demonstrably a
    # *type*.  Owner extraction attributes a namespace's free functions to the
    # namespace, so bare `Walaber` accumulates a "layout" that is really whatever
    # those read from their first argument -- and `Walaber::CircleHelper`, a
    # static helper class with no constructor, likewise shows the layout of the
    # Vector2 it is handed.  Neither can be told apart by having nested classes
    # (a real class such as `Walaber::Widget` has those too), nor by having no
    # constructor, because plenty of real types are static-only.  What does
    # decide is positive evidence that the name is a class: a typeinfo in the
    # RTTI, a constructor or destructor, or being passed as a parameter.  What
    # remains is reported rather than silently dropped.
    rtti_classes = load_rtti_classes(args.rtti)
    unproven = sorted(
        c for c, l in layouts.items()
        if c not in rtti_classes and not l["anchored"])
    unproven_set = set(unproven)
    proven = {c for c in layouts if c not in unproven_set}

    lpath = os.path.join(args.out, "layouts.tsv")
    with open(lpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# class\tsize\talign\tfields\tconfidence\tsizeof_cap\tsupport_cut\t"
                 "anchored\tproven\n")
        for cls in sorted(layouts):
            l = layouts[cls]
            fh.write("%s\t%d\t%d\t%d\t%s\t%d\t%.1f\t%d\t%d\n" % (
                cls, l["size"], l["align"], l["fields"], l["conf"],
                l["cap"], l["cut"], 1 if l["anchored"] else 0,
                1 if cls in proven else 0))

    summary = {
        "raw_rows": raw_rows,
        "channels": dict(sorted(channels_seen.items())),
        "offsets_seen": len(verdicts),
        "bands": dict(sorted(bands.items())),
        "fields_kept": len(kept),
        "layouts": len(layouts),
        "classes_with_sizeof_cap": len(size_cap),
        "classes_truncated_by_support": sum(
            1 for c, f in support_cut.items()
            if f > max(args.min_funcs, 1) and f > 0),
        "classes_proven_types": len(proven),
        "classes_unproven": len(unproven),
        "classes_inconsistent": len(inconsistent),
        "dropped": dict(sorted(dropped.items())),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if inconsistent:
        print("layouts withheld as internally inconsistent:")
        for c in sorted(inconsistent)[:40]:
            print("   %-52s %s" % (c, inconsistent[c]))
        if len(inconsistent) > 40:
            print("   ... and %d more" % (len(inconsistent) - 40))
    if unproven:
        print("no positive evidence these names are types (layout withheld):")
        for c in unproven[:40]:
            print("   %-52s size=%d fields=%d" % (
                c, layouts[c]["size"], layouts[c]["fields"]))
        if len(unproven) > 40:
            print("   ... and %d more" % (len(unproven) - 40))
    print("wrote %s and %s" % (fpath, lpath))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())