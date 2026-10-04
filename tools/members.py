"""Inventory the binary's member functions, keyed by owning class.

Field-layout recovery needs to know, for every function in `.text`, *which
class it belongs to*, because only a non-static member function has a `this`
in `x0` and therefore only a member function reveals a class's field offsets.
The symbol table already answers this -- the Itanium mangling encodes the
enclosing class as the nested-name prefix -- so this tool is a classification
pass over `out/symbols/functions.tsv` rather than a guess.

Two things it deliberately records, because both decide whether an offset can
be trusted later:

* ``role`` -- ``ctor``, ``dtor``, ``virtual``, ``method``, ``operator``,
  ``thunk``, ``conversion``.  A constructor, destructor or vtable slot is a
  *provably* non-static member function, so any `this`-relative access in one
  is real.  A plain method might be static, and the mangling does not
  distinguish the two.
* ``evidence`` -- ``vtable`` when the address is a primary-vtable slot target
  read out of the RTTI (see `out/rtti/vtables.tsv`), ``"`` otherwise.

Owner extraction is done on the demangled string rather than by re-parsing the
mangling, because the demangler's `_parse_nested_name` mis-reads a destructor
that reuses the class's own length prefix (`_ZN3FMOD4SoundD1Ev` comes back as
`FMO::~FMO` instead of `FMOD::Sound::~Sound`).  Splitting at the last `::` is
correct for every case that matters here:

    Walaber::Widget::setPos        -> Walaber::Widget
    Walaber::Widget::~Widget       -> Walaber::Widget
    FMOD::Sound::~Sound            -> FMOD::Sound
    Walaber::Vector2::operator+    -> Walaber::Vector2
    non-virtual thunk to Foo::bar   -> Foo            (prefix stripped)

A name whose last segment carries no `::` at all is a free function and gets
owner ``""``.  Namespaces therefore show up as owners too, which is why the
field-layout pass treats the owner list as a candidate set and requires
corroboration per class rather than trusting it.

It also records the two things `FieldScan` needs to turn a body into field
offsets:

* ``params`` -- the exact parameter list, so a class passed by pointer or
  reference can be used as a *second* object base.  This is not a luxury: a POD
  class such as `Walaber::Vector2` has no symbols of its own, so the only
  place its layout can be observed is the signature of some function that
  takes one.
* ``seeds`` -- the register each such parameter arrives in, for the field
  scanner to seed its dataflow with.

Register assignment follows AAPCS64, which is what decides ``seeds``:

* A *non-static* member function spends ``x0`` on ``this``, so the first
  *listed* parameter is in ``x1``.  Constructors, destructors and vtable slots
  are provably non-static, so they get that shift.
* A plain ``method`` might be static, and nothing in the mangling says which.
  Rather than guess, both shifts are emitted; they land in different slots and
  the corroboration pass in ``layout.py`` keeps only what agrees.

Output: `out/types/members.tsv`.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wmwtools.signature import signature, strip_thunk  # noqa: E402

HEADER = (
    "# address\tsize\tclass\trole\tmangled\tname\tevidence\tparams\tseeds_this\t"
    "seeds_static\n"
)


def _fmt_seeds(seeds) -> str:
    """Render seeds as `reg,class,v` / `reg,class,p`, `|`-separated.

    Commas separate the tuple and pipes separate the entries because a class
    name contains `::`, which rules out colons; and a class name cannot contain
    a comma here, since `object_class` rejects every template argument.
    """
    return "|".join("%d,%s,%s" % (r, c, "v" if byval else "p")
                    for r, c, byval in seeds)

#: Roles that cannot be static, so ``x0`` is certainly ``this``.
NONSTATIC_ROLES = frozenset(("ctor", "dtor", "virtual"))

#: Parameter types that travel in FP registers under AAPCS64.
_FP_TYPES = frozenset(("float", "double", "long double", "__fp16"))

#: Scalar types that are never a class object, however they are decorated.
_SCALARS = frozenset((
    "void", "bool", "char", "char8_t", "char16_t", "char32_t", "wchar_t",
    "signed char", "unsigned char", "short", "unsigned short", "int",
    "unsigned int", "long", "unsigned long", "long long", "unsigned long long",
    "float", "double", "long double", "__fp16", "__int128", "unsigned __int128",
))

#: A qualified C++ name with no template arguments and no spaces.  Requiring at
#: least one ``::`` is what keeps a plain scalar or an unqualified typedef out.
_CLASS_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_~][A-Za-z0-9_]*)+$")

#: A thunk renders as `non-virtual thunk to Foo::bar` / `virtual thunk to ...`;
#: the real owner is after the prefix.
_THUNK_TO = re.compile(r"^(?:(?:covariant )?return adjustment|non-virtual|virtual)?\s*"
                       r"thunk to ")


def owner_of(qualified: str) -> str:
    """Return the owning class of a parameterless qualified name.

    Returns ``""`` for a free function, and ``"?"`` when the name could not be
    parsed (the demangler leaves a bad symbol mangled, and a mangled string has
    no ``::``).
    """
    m = _THUNK_TO.match(qualified)
    if m:
        qualified = qualified[m.end():]
    cut = qualified.rfind("::")
    if cut <= 0:
        return ""
    return qualified[:cut]


def classify(qualified: str, owner: str) -> str:
    """Label the member function from its qualified name alone."""
    tail = qualified.rsplit("::", 1)[-1] if owner else qualified
    bare = tail.split("(")[0]
    if bare.startswith("~"):
        return "dtor"
    if bare.startswith("operator"):
        return "operator"
    # A constructor's name is the class's own unqualified name.
    if owner and bare == owner.rsplit("::", 1)[-1]:
        return "ctor"
    return "method"


def load_vtable_targets(path: str) -> dict:
    """Address -> class, for every primary-vtable slot target."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 5:
                continue
            out.setdefault(int(f[4], 16), f[0])
    return out


def object_class(param: str):
    """Class named by a parameter, if it arrives as one register-held object.

    Returns ``(class, byval)`` or ``None``.  A pointer, reference and by-value
    object are all single registers under AAPCS64 and so can each seed the field
    scanner's dataflow; anything else -- a template (its mangling says nothing
    about the layout), a function pointer, a two-register struct passed by
    value -- cannot.
    """
    s = param.strip()
    if not s or "<" in s or "(" in s:
        return None
    if s.endswith("*") or s.endswith("&"):
        s = s[:-1]
        byval = False
    else:
        byval = True
    s = " ".join(w for w in s.split() if w not in ("const", "volatile"))
    if s in _SCALARS or " " in s or not _CLASS_NAME.match(s):
        return None
    return s, byval


def _register_walk(params, shift):
    """(register, class, byval) for one reading of the parameter list.

    Registers are assigned the way AAPCS64 does -- integer arguments take the
    next free ``x`` register, FP arguments take the next ``s``/``d`` register, and
    each argument as a whole is rounded up to its own class.

    An FP-register parameter is skipped: a by-value class whose members are
    floats can be passed in ``s0``/``d0`` under the homogeneous-aggregate rule,
    and this does not attempt that case.
    """
    out = []
    claimed = set()
    int_idx = 0
    for param in params:
        if param.strip() in _FP_TYPES:
            continue
        obj = object_class(param)
        if obj is not None:
            reg = int_idx + shift
            cls, byval = obj
            # Two parameters can land on one register across readings; the first
            # claim wins rather than interleaving.
            if reg <= 7 and reg not in claimed:
                claimed.add(reg)
                out.append((reg, cls, byval))
        int_idx += 1
    return out


def seed_registers(params, nonstatic):
    """Return ``(seeds_this, seeds_static)``: the two readings of a body.

    ``seeds_this`` is the non-static reading -- ``x0`` is ``this``, so the first
    listed parameter is in ``x1``.  It is emitted for every role.

    ``seeds_static`` is the static reading -- parameters start at ``x0`` with no
    ``this`` at all.  It is emitted only for roles that *might* be static,
    because for a constructor, destructor or vtable slot ``x0`` is ``this`` by
    construction and the reading is not merely unlikely but impossible.

    The two are kept in separate columns rather than merged, because both place
    an object in ``x0`` and a merged list cannot say which reading produced an
    access.  ``FieldScan`` scans each reading separately and tags the result, so
    evidence for one never corroborates the other.
    """
    seeds_this = _register_walk(params, 1)
    if nonstatic:
        return seeds_this, []
    return seeds_this, _register_walk(params, 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("functions", help="out/symbols/functions.tsv")
    ap.add_argument("--vtables", default=None,
                    help="out/rtti/vtables.tsv (marks vtable slot targets)")
    ap.add_argument("--out", default="out/types/members.tsv")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(args.functions))
    root = os.path.dirname(os.path.dirname(here))
    vtables = args.vtables or os.path.join(root, "out", "rtti", "vtables.tsv")
    vtab = load_vtable_targets(vtables)

    rows = []
    roles = collections.Counter()
    by_class = collections.defaultdict(collections.Counter)
    unparsed = 0
    thunks = 0
    seeded = 0

    with open(args.functions, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 4:
                continue
            addr, size, mangled, demangled = f[0], f[1], f[2], f[3]

            sig = signature(mangled)
            if sig is None:
                unparsed += 1
                continue
            if sig.kind == "thunk":
                thunks += 1
            qualified = sig.name
            owner = owner_of(qualified)
            if not owner:
                continue
            role = classify(qualified, owner)
            if role == "method" and vtab.get(int(addr, 16)) == owner:
                role = "virtual"
            evidence = "vtable" if vtab.get(int(addr, 16)) == owner else ""
            params = sig.params
            seeds_this, seeds_static = seed_registers(params,
                                                      role in NONSTATIC_ROLES)
            rows.append((addr, size, owner, role, mangled, qualified, evidence,
                         "|".join(params),
                         _fmt_seeds(seeds_this),
                         _fmt_seeds(seeds_static)))
            roles[role] += 1
            by_class[owner][role] += 1
            seeded += bool(seeds_this)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER)
        for r in rows:
            fh.write("\t".join(r) + "\n")

    # A class is only worth scanning for fields if it owns at least one
    # provably non-static member function.
    anchored = sorted(
        c for c, roles_ in by_class.items()
        if roles_["ctor"] or roles_["dtor"] or roles_["virtual"]
    )
    summary = {
        "members": len(rows),
        "classes_with_members": len(by_class),
        "members_with_param_seeds": seeded,
        "roles": dict(sorted(roles.items())),
        "thunks": thunks,
        "unparsed_signatures": unparsed,
        "classes_with_anchor": len(anchored),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    anchor_path = os.path.join(os.path.dirname(os.path.abspath(args.out)),
                               "anchor_classes.txt")
    with open(anchor_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# classes owning a ctor, dtor or vtable slot: provably non-static\n")
        for c in anchored:
            fh.write(c + "\n")
    print("wrote %s and %s" % (args.out, anchor_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
