"""Regression test for tools/coalesce_locals.py.

Pins the copy-coalescing rules on synthetic bodies, so both the merges that
must happen and the ones that must be refused are exercised without touching
out/src:

    py -3 tools/test_coalesce_locals.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coalesce_locals as C  # noqa: E402


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError("%s%s" % (name, (": " + detail) if detail else ""))


def one(sig, decls, body, addr="0x1000"):
    decl = "".join("  %s;\n" % d for d in decls)
    return ("/* ok  address %s  size 100 */\n"
            "/* mangled: _Z3foov */\n"
            "/* %s */\n\n/* %s */\n\n%s\n\n{\n%s  \n%s}\n"
            % (addr, sig, sig, sig, decl, body))


def run(text):
    new, _ = C.plan(text)
    return new


def test_alias_of_parameter():
    t = one("void foo(int param_1)", ["int iVar1"],
            "  iVar1 = param_1;\n  return iVar1;\n")
    out = run(t)
    check("alias param: read retyped", "return param_1;" in out, out)
    check("alias param: local gone", "iVar1" not in out, out)
    check("alias param: copy gone", "iVar1 = param_1" not in out, out)


def test_alias_of_immutable_local():
    t = one("void foo(void)", ["int iVar1", "int iVar2"],
            "  iVar2 = 5;\n  iVar1 = iVar2;\n  return iVar1;\n")
    # iVar2 has a write, so this is the *temporary* rule, not the alias one.
    out = run(t)
    check("immutable local merged", "iVar1 = 5;" in out, out)
    check("temp source gone", "iVar2" not in out, out)


def test_temporary_merge():
    # iVar2 is a single-use temporary; its definition moves onto iVar1.
    t = one("void foo(int param_1)", ["int iVar1", "int iVar2"],
            "  iVar2 = param_1 + 1;\n  iVar1 = iVar2;\n  return iVar1;\n")
    out = run(t)
    check("temp: def moved", "iVar1 = param_1 + 1;" in out, out)
    check("temp: source gone", "iVar2" not in out, out)
    _, stats = C.plan(t)
    check("temp: counted as temp", stats["temp"] == 1 and stats["alias"] == 0,
          str(stats))


def test_reused_slot_kept():
    # iVar1 is read before the copy: the slot holds another value there.
    t = one("void foo(int param_1)", ["int iVar1"],
            "  bar(iVar1);\n  iVar1 = param_1;\n  return iVar1;\n")
    out = run(t)
    check("reused slot kept", out == t, out)


def test_source_written_twice_kept():
    t = one("void foo(int param_1)", ["int iVar1", "int iVar2"],
            "  iVar2 = 7;\n  iVar1 = iVar2;\n  iVar2 = 9;\n  return iVar1;\n")
    out = run(t)
    check("twice-written source kept", out == t, out)


def test_address_taken_kept():
    t = one("void foo(int param_1)", ["int iVar1"],
            "  iVar1 = param_1;\n  bar(&iVar1);\n  return iVar1;\n")
    out = run(t)
    check("address-taken kept", out == t, out)


def test_cast_copy_kept():
    t = one("void foo(long param_1)", ["int iVar1"],
            "  iVar1 = (int)param_1;\n  return iVar1;\n")
    out = run(t)
    check("cast copy kept", out == t, out)


def test_comment_untouched():
    t = one("void foo(int param_1)", ["int iVar1"],
            "  iVar1 = param_1;\n  /* iVar1 */\n  return iVar1;\n")
    out = run(t)
    check("comment preserved", "/* iVar1 */" in out, out)
    check("code rewritten", "return param_1;" in out, out)
    check("decl dropped", "int iVar1;" not in out, out)


def test_idempotent():
    t = one("void foo(int param_1)", ["int iVar1"],
            "  iVar1 = param_1;\n  return iVar1;\n")
    once = run(t)
    _, stats = C.plan(once)
    check("idempotent", stats["functions"] == 0, str(stats))


def test_plan_counts():
    b = one("void foo(int param_1)", ["int iVar1"],
            "  iVar1 = param_1;\n  return iVar1;\n")
    t = b + b
    new, stats = C.plan(t)
    check("plan functions", stats["functions"] == 2, str(stats))
    check("plan alias", stats["alias"] == 2, str(stats))
    check("plan decls", stats["decls"] == 2, str(stats))


def test_propagates_within_block():
    # uVar2 is reused (assigned twice); the reads between fold to its value.
    t = one("void foo(int param_1)", ["int iVar1", "int iVar2"],
            "  iVar2 = param_1;\n  iVar1 = iVar2;\n  bar(iVar1);\n"
            "  iVar2 = 9;\n  bar(iVar1, iVar2);\n")
    out = run(t)
    check("prop: read folded", "bar(param_1);" in out, out)
    check("prop: local gone", "iVar1" not in out, out)


def test_propagation_stops_at_block():
    # iVar2 is reused (two writes), so the cross-block rule cannot fold iVar1;
    # the in-block alias must not leak past the brace either.
    t = one("void foo(int param_1)", ["int iVar1", "int iVar2"],
            "  iVar1 = iVar2;\n  if (param_1 != 0) {\n    bar(iVar1);\n"
            "  }\n  iVar2 = 5;\n")
    out = run(t)
    check("prop: does not cross a brace", "bar(iVar1);" in out, out)
    check("prop: local kept", "int iVar1;" in out, out)


def test_propagation_invalidated_on_write():
    t = one("void foo(void)", ["int iVar1", "int iVar2"],
            "  iVar1 = iVar2;\n  bar(iVar1);\n  iVar2 = 9;\n  bar(iVar1);\n")
    out = run(t)
    # the first read folds to iVar2; after iVar2 is reassigned the alias is
    # dead and the second read keeps its own name.
    check("prop: before write folded", out.count("bar(iVar2);") == 1, out)
    check("prop: after write kept", "bar(iVar1);" in out, out)


def test_dead_copy_removed():
    t = one("void foo(int param_1)", ["int iVar1", "int iVar2"],
            "  iVar2 = param_1;\n  iVar1 = iVar2;\n  return 0;\n")
    out = run(t)
    check("dead copy removed", "iVar1" not in out and "iVar2" not in out, out)


def test_pointer_write_is_a_read():
    # "*iVar1 = .." reads iVar1; iVar1 is multi-assignment, so nothing else can
    # fold it and the dead-store rule must not delete the copy either.
    t = one("void foo(int *param_1)", ["int *iVar1", "int *iVar2"],
            "  iVar1 = iVar2;\n  iVar1 = param_1;\n  *iVar1 = 9;\n")
    out = run(t)
    check("pointer copy kept", "iVar1 = iVar2;" in out, out)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  %s" % t.__name__)
    print("%d groups passed" % len(tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
