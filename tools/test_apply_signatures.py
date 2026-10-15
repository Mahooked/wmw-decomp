"""Regression test for tools/apply_signatures.py.

Checks the pure helpers and the alignment rule on synthetic definitions, so a
change to the splitter, the name formatter or the +1/this decision is caught
without touching out/src:

    py -3 tools/test_apply_signatures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_signatures as A  # noqa: E402


def render(text, sig, members):
    edits, _stats = A.plan(text, sig, members)
    for start, end, repl in sorted(edits, reverse=True):
        text = text[:start] + repl + text[end:]
    return text


def check(name, got, want):
    if got != want:
        raise AssertionError("%s:\n  got  %r\n  want %r" % (name, got, want))


def test_helpers():
    check("pointer", A.declare_param("_JavaVM*", "p0"), "_JavaVM *p0")
    check("const ptr", A.declare_param("char const*", "p1"), "char const *p1")
    check("double ptr", A.declare_param("char**", "p2"), "char **p2")
    check("reference", A.declare_param("T const&", "p3"), "T const& p3")
    check("rvalue", A.declare_param("T&&", "p4"), "T&& p4")
    check("plain", A.declare_param("unsigned int", "p5"), "unsigned int p5")
    check("func ptr", A.declare_param("void (*)()", "p6"), "void (*p6)()")
    check("func ptr ref", A.declare_param("bool (*&)(int)", "p7"),
          "bool (*&p7)(int)")
    check("varargs", A.declare_param("...", "ignored"), "...")
    check("split", A.split_params("a,b<c,d>,e"),
          ["a", "b<c,d>", "e"])
    check("span skips comment",
          A.param_span("/* f(int) */ void g(int a)"), (19, 25))


def test_delta0():
    text = ("/* ok  address 0x2000  size 4 */\n"
            "void bar(long param_1,undefined4 param_2)\n"
            "{\n  param_1 = param_2;\n}\n")
    out = render(text, {0x2000: ["Walaber::Sprite*", "unsigned int"]}, {})
    check("delta0 typed", "void bar(Walaber::Sprite *param_1,unsigned int param_2)" in out, True)


def test_delta1_member():
    # A virtual method with arguments: provably non-static, no floating point,
    # so the +1 is `this`.
    text = ("/* ok  address 0x3000  size 4 */\n"
            "void Baz::qux(undefined8 param_1,byte *param_2,uint param_3)\n"
            "{\n  param_1[2] = param_2;\n  param_3 = param_3;\n}\n")
    sig = {0x3000: ["S const&", "unsigned int"]}
    out = render(text, sig, {0x3000: "virtual"})
    check("delta1 decl", "void Baz::qux(S const& param_1,unsigned int param_2)" in out, True)
    check("delta1 body this", "this[2] = param_1;" in out, True)
    check("delta1 body shift", "param_2 = param_2;" in out, True)


def test_zero_arg_member():
    # A 0-argument member still has `this`: the signature list is empty, so the
    # +1 definition is exactly `this` (no types to write).
    text = ("/* ok  address 0x6000  size 4 */\n"
            "void Baz::~Baz(undefined8 *param_1)\n"
            "{\n  param_1[0] = 0;\n}\n")
    out = render(text, {0x6000: []}, {0x6000: "dtor"})
    check("zero-arg dtor decl", "void Baz::~Baz()" in out, True)
    check("zero-arg dtor body", "this[0] = 0;" in out, True)


def test_delta1_not_member_skipped():
    # `method` might be static, and a class-returning free function also gets a
    # hidden first pointer: neither may be rewritten to `this`.
    text = ("/* ok  address 0x4000  size 4 */\n"
            "void f(undefined8 param_1,byte *param_2)\n"
            "{\n  param_2 = param_1;\n}\n")
    check("method untouched", render(text, {0x4000: ["T const&"]}, {0x4000: "method"}), text)
    check("no role untouched", render(text, {0x4000: ["T const&"]}, {}), text)


def test_ctor_with_args_skipped():
    # A constructor for a class with virtual bases takes a VTT pointer in x0 and
    # `this` in x1: the +1 could be either, so a constructor with arguments is
    # left alone even though it is provably non-static.
    text = ("/* ok  address 0x7000  size 4 */\n"
            "void Baz::Baz(undefined8 param_1,byte *param_2)\n"
            "{\n  param_2 = param_1;\n}\n")
    check("ctor with args untouched",
          render(text, {0x7000: ["T const&"]}, {0x7000: "ctor"}), text)


def test_fp_signature_skipped():
    # A floating-point parameter is listed ahead of the register parameters, so
    # any signature that names one is not mapped positionally.
    d0 = ("/* ok  address 0x8000  size 4 */\n"
          "void h(long param_1,undefined4 param_2)\n"
          "{\n  param_1 = param_2;\n}\n")
    check("delta0 with float untouched",
          render(d0, {0x8000: ["int", "float"]}, {}), d0)
    d1 = ("/* ok  address 0x9000  size 4 */\n"
          "void Baz::v(undefined8 param_1,undefined4 param_2)\n"
          "{\n  param_1 = param_2;\n}\n")
    check("delta1 with float untouched",
          render(d1, {0x9000: ["float"]}, {0x9000: "virtual"}), d1)


def test_already_typed_skipped():
    text = ("/* ok  address 0x5000  size 4 */\n"
            "void g(Walaber::Sprite *p0)\n{\n  p0 = p0;\n}\n")
    out = render(text, {0x5000: ["Walaber::Sprite*"]}, {})
    check("typed untouched", out, text)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print("test_apply_signatures: %d groups ok" % len(tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
