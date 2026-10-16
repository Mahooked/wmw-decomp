"""Regression test for tools/shape_source.py.

Exercises the stack-protector stripping on synthetic bodies, so every shape the
compiler emits (and every shape that must be *left alone*) is pinned without
touching out/src:

    py -3 tools/test_shape_source.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shape_source as S  # noqa: E402


def check(name, got, want):
    if got != want:
        raise AssertionError("%s:\n  got  %r\n  want %r" % (name, got, want))


def strip(text):
    out, done = S.strip_block(text)
    return out if done else text


# A body whose guard uses the plain local form.
PROLOG = "  lVar1 = tpidr_el0;\n  lStack_18 = *(long *)(lVar1 + 0x28);\n"
DECLS = "  long lVar1;\n  long lStack_18;\n"


def test_variant_a_void():
    text = ("{\n" + DECLS + PROLOG + "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  __stack_chk_fail();\n"
            "  return;\n"
            "}\n")
    check("variant A void", strip(text),
          "{\n  a = 1;\n  return;\n}\n")


def test_variant_a_value():
    text = ("{\n" + DECLS + PROLOG + "  x = f();\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return uVar2;\n"
            "  }\n"
            "  uVar2 = __stack_chk_fail();\n"
            "  return uVar2;\n"
            "}\n")
    check("variant A value", strip(text),
          "{\n  x = f();\n  return uVar2;\n}\n")


def test_variant_b():
    text = ("{\n" + DECLS + PROLOG + "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) != lStack_18) {\n"
            "    __stack_chk_fail();\n"
            "    return;\n"
            "  }\n"
            "  return;\n"
            "}\n")
    check("variant B", strip(text),
          "{\n  a = 1;\n  return;\n}\n")


def test_abort_argument():
    text = ("{\n" + DECLS + PROLOG + "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  __stack_chk_fail(uVar5);\n"
            "  return;\n"
            "}\n")
    check("abort argument", strip(text),
          "{\n  a = 1;\n  return;\n}\n")


def test_abort_cast():
    text = ("{\n" + DECLS + PROLOG + "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  plVar4 = (long *)__stack_chk_fail();\n"
            "  return plVar4;\n"
            "}\n")
    check("abort cast", strip(text),
          "{\n  a = 1;\n  return plVar4;\n}\n")


def test_array_canary():
    text = ("{\n  long lVar1;\n  long alStack_38 [3];\n\n"
            "  lVar1 = tpidr_el0;\n"
            "  alStack_38[2] = *(long *)(lVar1 + 0x28);\n"
            "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) != alStack_38[2]) {\n"
            "    __stack_chk_fail();\n"
            "    return;\n"
            "  }\n"
            "  return;\n"
            "}\n")
    check("array canary", strip(text),
          "{\n\n  a = 1;\n  return;\n}\n")


def test_reused_canary_kept():
    # The canary local is used for something else, so the guard is not an
    # artefact that can be sliced out: everything must stay.
    text = ("{\n" + DECLS + PROLOG + "  lStack_18 = g();\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  __stack_chk_fail();\n"
            "  return;\n"
            "}\n")
    check("reused canary", strip(text), text)


def test_reused_tcb_kept():
    text = ("{\n" + DECLS + PROLOG + "  lVar1 = h();\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  __stack_chk_fail();\n"
            "  return;\n"
            "}\n")
    check("reused tcb", strip(text), text)


def test_no_guard():
    text = "{\n  a = 1;\n  return;\n}\n"
    check("no guard", strip(text), text)


def test_idempotent():
    text = ("{\n" + DECLS + PROLOG + "  a = 1;\n"
            "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
            "    return;\n"
            "  }\n"
            "  __stack_chk_fail();\n"
            "  return;\n"
            "}\n")
    once = strip(text)
    check("idempotent", strip(once), once)


def test_plan_counts():
    f = ("/* ok  address 0x1000  size 32 */\n"
         "void Foo::bar()\n\n{\n" + DECLS + PROLOG +
         "  if (*(long *)(lVar1 + 0x28) == lStack_18) {\n"
         "    return;\n"
         "  }\n"
         "  __stack_chk_fail();\n"
         "  return;\n"
         "}\n")
    text = "/* header */\n" + f + f
    new, stats = S.plan(text)
    check("plan stripped", stats["stripped"], 2)
    check("plan unstrippable", stats["unstrippable"], 0)
    check("plan idempotent", S.plan(new)[1]["stripped"], 0)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  %s" % t.__name__)
    print("%d groups passed" % len(tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
