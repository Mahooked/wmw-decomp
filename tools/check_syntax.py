"""Point a real C++ compiler at the decompiled bodies and report what is
structurally wrong with them.

Why this exists
---------------
``out/src`` is Ghidra's output, not source.  Every body is a *fragment*: it
names types and calls functions that are defined in some other file and were
never declared, so nothing in the tree can be compiled on its own.  That is the
honest state of a decompilation, and it is also the thing standing between
"a folder of pseudocode" and "a program".

This tool makes the gap *measurable* rather than a matter of opinion.  It
synthesises the declarations the tree is missing, points ``clang++ -fsyntax-only``
at each file, and reports the diagnostics sorted by kind, so that the
structural defects (malformed C++ --- a destructor with parameters) separate from
the expected ones (a name that is defined two files away and simply has not been
declared yet).

How the missing declarations are synthesised
--------------------------------------------
An out-of-line definition in C++ --- ``void A::B::f(...) { }`` --- is only
well-formed if ``A::B`` was declared first and ``f`` matches a declaration in it.
So the declarations cannot be guessed: they have to be *read off the
definitions*.  This tool scans every ``/* ok address 0x… */`` block in ``out/src``,
parses the definition header, and rebuilds exactly the class and namespace
declarations those headers require:

* a member definition contributes a member declaration to its class;
* a namespace-scope definition contributes a namespace declaration;
* a class's fields come from the recovered layouts (``out/types/fields.tsv``), so
  the ``f_0x<offset>`` member reads the bodies already contain resolve;
* a type name the definitions mention but nothing declares is emitted as an
  opaque ``struct`` (Ghidra's flattened ``Walaber__Vector2`` is one of these).

Because the declarations are copied from the definitions they must match, the
remaining diagnostics are the ones worth reading.  The pass is a *gate*:
``--check`` exits non-zero while any error remains.

This does not make the tree compile.  It measures how far it is from compiling.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import os
import re
import subprocess
import sys

#: One recovered function: ``/* ok  address 0x…  size N */``.
_MARKER = re.compile(r"/\*[^*]*?address\s+0x[0-9a-fA-F]+\s+size\s+\d+\s*\*/")

_IDENT = re.compile(r"[A-Za-z_~]\w*")
_OPERATOR = re.compile(
    r"operator\s*(?:\[\]|\(\)|->\*|->|<<=|>>=|<=>|<<|>>|<=|>=|==|!=|&&|\|\||"
    r"\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|,|\+|-|\*|/|%|\^|&|\||~|!|=|<|>|"
    r"new\[\]|new|delete\[\]|delete|\s+\w+)")

#: Ghidra's placeholder globals (``DAT_00634ed4``, ``PTR__Message_0070cdc8``)
# and other hex-suffixed symbols.
_SYMBOL = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*_[0-9a-fA-F]{6,})\b")
_ARRAY = re.compile(r"\[[^\]]*\]")
#: Ghidra's sub-register fold helpers, e.g. ``CONCAT21``/``SUB81``/``ZEXT416``.
_FOLD = re.compile(r"\b(?:CONCAT|SUB|ZEXT|SEXT)\d+\b")

_GENERATED = os.path.join("out", "check", "_generated")

#: Primitive, keyword and libc names that must never be declared as types.
_PRIMITIVE = frozenset("""
undefined undefined1 undefined2 undefined4 undefined8 byte uchar ushort uint
ulong ulonglong longlong schar int1 int2 int3 int4 int5 int6 int7 int8
uint1 uint2 uint3 uint4 uint5 uint6 uint7 uint8 code uint8_t uint16_t uint32_t
uint64_t int8_t int16_t int32_t int64_t size_t ssize_t longdouble wchar16 tm
void bool char short int long float double signed unsigned wchar_t char16_t
char32_t __int128 __fp16 auto const volatile static inline virtual explicit
register extern mutable typedef struct class union enum namespace template
this true false nullptr operator new delete sizeof return
""".split())

#: Unqualified names that are class *templates* declared in the prelude; a
#: definition qualified by one of these is a member of a template, which cannot
#: be declared without the template's full definition.
_TEMPLATE = frozenset("""
allocator char_traits less hash pair tuple default_delete unique_ptr shared_ptr
weak_ptr initializer_list iterator_traits reverse_iterator basic_string vector
deque list map multimap set multiset __tree __value_type __map_value_compare
__tree_node __tree_node_base __tree_end_node __tree_iterator
__tree_const_iterator __tree_node_destructor __split_buffer __vector_base
__vector_base_common basic_ostream basic_istream basic_iostream basic_streambuf
basic_stringbuf basic_filebuf istreambuf_iterator ostreambuf_iterator
__basic_string_common ctype codecvt moneypunct moneypunct_byname numpunct
num_get num_put time_get time_put collate messages __num_get_signed_integral
__num_get_unsigned_integral SharedPtr MemberCallback WeakPtr unique_lock
lock_guard
""".split())

#: Names that are namespaces, never classes, however they are used.
_NAMESPACE_ROOT = frozenset((
    "std", "std::__ndk1", "ndk", "Walaber", "WaterConcept",
    "WaterConceptConstants", "__cxxabiv1", "__gnu_cxx", "FMOD", "std::__1",
))

#: Classes the prelude declares, so the class/namespace split stays consistent.
_PRELUDE_CLASSES = [
    "std::__ndk1::locale", "std::__ndk1::ios_base", "std::__ndk1::exception",
    "std::__ndk1::exception_ptr", "std::__ndk1::logic_error",
    "std::__ndk1::runtime_error", "std::__ndk1::piecewise_construct_t",
    "std::__ndk1::__shared_count", "std::__ndk1::__shared_weak_count",
    "std::__ndk1::__thread_struct", "std::__ndk1::mutex",
    "std::__ndk1::recursive_mutex", "std::__ndk1::condition_variable",
    "std::__ndk1::thread", "std::__ndk1::once_flag",
    "std::bad_cast", "std::bad_alloc", "std::bad_typeid",
    "std::bad_array_length", "std::bad_array_new_length", "std::exception",
    "std::type_info", "std::nested_exception",
]


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _skip_comment(text, i):
    if text.startswith("/*", i):
        j = text.find("*/", i + 2)
        return len(text) if j < 0 else j + 2
    return i


def param_span(decl):
    """(open, close) of the first top-level parameter list in ``decl``."""
    i, n = 0, len(decl)
    while i < n:
        j = _skip_comment(decl, i)
        if j != i:
            i = j
            continue
        if decl[i] == "(":
            depth, k = 0, i
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


def _parse_component(s, i):
    op = _OPERATOR.match(s, i)
    if op and op.group(0).startswith("operator"):
        return op.end()
    m = _IDENT.match(s, i)
    if not m:
        return None
    i = m.end()
    if i < len(s) and s[i] == "<":
        depth, j = 0, i
        while j < len(s):
            if s[j] == "<":
                depth += 1
            elif s[j] == ">":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        else:
            return None
        i = j
    return i


def _parse_name(s, i):
    j = _parse_component(s, i)
    if j is None:
        return None
    while s.startswith("::", j):
        k = _parse_component(s, j + 2)
        if k is None:
            return None
        j = k
    return j


def split_name(pre):
    """(return type, qualified name) from a definition header, or None."""
    s = " ".join(pre.split())
    starts = [0] + [i + 1 for i, c in enumerate(s) if c in " *"]
    for st in starts:
        while st < len(s) and s[st] in " *":
            st += 1
        if st >= len(s):
            continue
        if _parse_name(s, st) == len(s):
            return s[:st].strip(), s[st:]
    return None


class Model(object):
    def __init__(self):
        self.classes = set()          # every name proven to be a type
        self.fields = collections.defaultdict(list)
        self.members = collections.defaultdict(dict)
        self.funcs = collections.defaultdict(dict)
        self.defined = set()
        self.symbols = set()
        self.types = set()            # opaque structs the definitions mention
        self.templates = set()        # flattened template names they mention
        self.folds = set()            # sub-register fold helpers they call
        self.stats = collections.Counter()

    def split(self, qname):
        comps = qname.split("::")
        for i in range(len(comps)):
            if "::".join(comps[:i + 1]) in self.classes:
                return comps[:i], comps[i:]
        return None


def add_class(model, name):
    if not name or name.startswith("#") or "<" in name:
        return
    comps = name.split("::")
    if not all(re.match(r"^[A-Za-z_~]\w*$", c) for c in comps):
        return
    if name in _NAMESPACE_ROOT or comps[-1] in _TEMPLATE:
        return
    if name.startswith("non_virtual_thunk") or name.startswith("virtual_thunk"):
        return
    model.classes.add(name)


def load_classes(model, types_dir):
    for name in ("typeindex.tsv", "classes.tsv"):
        path = os.path.join(types_dir, name)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.rstrip("\n").split("\t")
            if f and f[0] and not f[0].startswith("#"):
                add_class(model, f[0])
    # members.tsv records the owning class of every classified member function,
    # including the many classes that have no recovered layout and are therefore
    # absent from typeindex.tsv.
    path = os.path.join(types_dir, "members.tsv")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="replace"):
            f = line.rstrip("\n").split("\t")
            if len(f) >= 3 and not f[0].startswith("#"):
                add_class(model, f[2])
    path = os.path.join(os.path.dirname(types_dir), "symbols", "classnames.txt")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="replace"):
            add_class(model, line.strip())
    for name in _PRELUDE_CLASSES:
        model.classes.add(name)


def load_fields(model, types_dir):
    path = os.path.join(types_dir, "fields.tsv")
    seen = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 5:
            continue
        cls, off, width, kind = f[0], f[1], f[2], f[3]
        try:
            off_i, w = int(off), int(width)
        except ValueError:
            continue
        if off_i < 0 or (cls, off_i) in seen:
            continue
        seen.add((cls, off_i))
        model.fields[cls].append((off_i, _ctype(kind, w), "f_0x%x" % off_i))


def _ctype(kind, width):
    if kind == "float":
        return {4: "float", 8: "double"}.get(width, "uint8_t")
    return {1: "uint8_t", 2: "uint16_t", 4: "int32_t", 8: "uint64_t"}.get(
        width, "uint8_t")


_CHAIN = re.compile(r"[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*")


def _type_names(text):
    """Type names a parameter/return type text mentions, split by usage.

    The body only ever writes the *flattened* form Ghidra resolved
    (``Walaber__Vector2``) or a real qualified name (``Walaber::Vector2``); both
    start the type with an upper-case or underscore character (or carry ``__``
    for a flattened name), while a declarator name (``p0``, ``param_1``) does
    not.  A name immediately followed by ``<`` is a template and is declared as
    a variadic template so its arity never has to be guessed.
    """
    structs, templates = set(), set()
    for m in _CHAIN.finditer(text):
        chain = m.group(0)
        last = chain.split("::")[-1]
        if last in _PRIMITIVE or last in _TEMPLATE:
            continue
        if not (re.match(r"^[A-Z_]", last) or "__" in last):
            continue
        if m.end() < len(text) and text[m.end()] == "<":
            templates.add(chain)
        else:
            structs.add(chain)
    return structs, templates


def scan(model, src):
    for base, _dirs, names in os.walk(src):
        for name in sorted(names):
            if not name.endswith(".cpp"):
                continue
            text = open(os.path.join(base, name), encoding="utf-8",
                        errors="replace").read().replace("\r\n", "\n")
            for m in _SYMBOL.finditer(text):
                model.symbols.add(m.group(1))
            model.folds.update(_FOLD.findall(text))
            marks = list(_MARKER.finditer(text))
            for idx, mk in enumerate(marks):
                end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
                block = text[mk.end():end]
                brace = block.find("{")
                if brace < 0:
                    continue
                decl = block[:brace]
                span = param_span(decl)
                if span is None:
                    model.stats["no-params"] += 1
                    continue
                got = split_name(strip_comments(decl[:span[0]]))
                if got is None:
                    model.stats["unparsed"] += 1
                    continue
                ret, qname = got
                params = " ".join(
                    strip_comments(decl[span[0] + 1:span[1]]).split())
                post = " ".join(strip_comments(decl[span[1] + 1:]).split())
                model.stats["defs"] += 1
                model.defined.add(qname)
                a, b = _type_names(_ARRAY.sub(" *", ret))
                model.types |= a
                model.templates |= b
                a, b = _type_names(params)
                model.types |= a
                model.templates |= b
                add_definition(model, ret, qname, params, post)


def add_definition(model, ret, qname, params, post):
    if "<" in qname or "<" in ret or "[" in ret:
        model.stats["skipped-template"] += 1
        return
    if qname.startswith(("non_virtual_thunk_to_", "virtual_thunk_to_",
                         "_thunk_to_")):
        model.stats["skipped-thunk"] += 1
        return
    short = qname.split("::")[-1]
    if short.startswith("operator") and params.strip() in ("", "void"):
        model.stats["skipped-operator"] += 1
        return
    if short == "operator[]" and params.count(","):
        model.stats["skipped-operator"] += 1
        return
    is_ctorlike = short.lstrip("~") == qname.split("::")[-2:][0] if "::" in qname else False
    if short.startswith("~") or (short == qname.split("::")[-2]
                                 if "::" in qname else False):
        ret = ""                    # a constructor or destructor has no return type
    parts = model.split(qname) if "::" in qname else None
    if parts is None:
        # No prefix is a known class, so the qualifier (if any) is a namespace.
        # A free operator has to name a class in its signature to be legal, and
        # the ones that do not are inside libc++ rather than in the game.
        if short.startswith("operator"):
            model.stats["skipped-operator"] += 1
            return
        if "::" in qname:
            ns, name = qname.rsplit("::", 1)
            model.funcs[ns][name] = _decl(ret, name, params, post)
        else:
            model.funcs[""][qname] = _decl(ret, qname, params, post)
        return
    ns, cls = parts
    short = cls[-1]
    owner = "::".join(cls[:-1])
    if owner:
        target = "::".join(ns + cls[:-1])
        if short.startswith("~"):
            params, post = "", post
        elif short == cls[-2]:
            ret = ""
        model.members[target][short] = _decl(ret, short, params, post)
    else:
        if short.startswith("~") or short == cls[-1]:
            ret = ""
        model.members["::".join(ns + cls)][short] = _decl(ret, short, params, post)


def _decl(ret, name, params, post):
    body = "%s(%s)" % (name, params)
    if post:
        body += " " + post
    return ("%s %s;" % (ret, body)).strip() if ret else body + ";"


def emit_class(model, qname, out, depth, emitted, stack):
    if qname in emitted:
        return
    if qname in stack:
        out.append("/* cycle: %s */" % qname)
        return
    stack.add(qname)
    indent = "  " * depth
    out.append("%sstruct %s {" % (indent, qname.split("::")[-1]))
    for other in sorted(model.classes):
        if (other.startswith(qname + "::")
                and other.count("::") == qname.count("::") + 1):
            emit_class(model, other, out, depth + 1, emitted, stack)
    for _off, ty, fname in sorted(model.fields.get(qname, [])):
        out.append("%s  %s %s;" % (indent, ty, fname))
    for short in sorted(model.members.get(qname, {})):
        out.append("%s  %s" % (indent, model.members[qname][short]))
    out.append("%s};" % indent)
    emitted.add(qname)
    stack.discard(qname)


def _wrap(ns, text):
    for part in reversed([p for p in ns if p]):
        text = "namespace %s { %s }" % (part, text)
    return text


def _prefixes(names):
    """Every proper ``::`` prefix of a set of qualified names."""
    out = set()
    for name in names:
        comps = name.split("::")
        for i in range(1, len(comps)):
            out.add("::".join(comps[:i]))
    return out


def generate(model, path):
    out = ["/* generated by tools/check_syntax.py -- do not edit */"]
    out.append("namespace std { inline namespace __ndk1 { } }")
    # Ghidra's sub-register folds: the set and arity come from the bodies, so
    # every name it actually calls is declared as a variadic template.
    for fold in sorted(model.folds):
        out.append("template <class... A> long long %s(A...);" % fold)

    # Everything a declaration below might name has to be declared *before* it.
    known_ns = _prefixes(model.classes) | _prefixes(list(model.funcs))
    known = model.classes | _PRIMITIVE | _TEMPLATE | known_ns | set(model.funcs)

    def _unknown(name):
        return name not in known and not any(
            p in model.classes for p in _prefixes([name]))

    extra = sorted(t for t in model.types if _unknown(t))

    for cls in sorted(model.classes):
        comps = cls.split("::")
        if len(comps) == 1 or "::".join(comps[:-1]) not in model.classes:
            out.append(_wrap(comps[:-1], "struct %s;" % comps[-1]))
    for t in sorted(model.templates - model.types):
        comps = t.split("::")
        out.append(_wrap(comps[:-1], "template <class...> struct %s;" % comps[-1]))
    for t in extra:
        comps = t.split("::")
        out.append(_wrap(comps[:-1], "struct %s;" % comps[-1]))
    declared = model.defined | set(model.funcs)
    out.append("\n".join("extern _Datum %s;" % s
                         for s in sorted(model.symbols) if s not in declared))

    emitted = set()
    for cls in sorted(model.classes):
        comps = cls.split("::")
        if len(comps) == 1 or "::".join(comps[:-1]) not in model.classes:
            buf = []
            emit_class(model, cls, buf, 0, emitted, set())
            out.append(_wrap(comps[:-1], "\n".join(buf)))
    for ns in sorted(model.funcs):
        decls = "\n".join(model.funcs[ns][n] for n in sorted(model.funcs[ns]))
        out.append(_wrap(ns.split("::") if ns else [""], decls))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return len(model.classes), len(model.members), len(extra)


def build_preamble(prelude, path):
    text = open(prelude, encoding="utf-8", errors="replace").read()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.write("\n#include \"decls.h\"\n")


def run_clang(clang, preamble, path):
    cmd = [clang, "-target", "aarch64-linux-gnu", "-std=gnu++17",
           "-fsyntax-only", "-ffreestanding", "-nostdinc", "-nostdinc++",
           "-w", "-ferror-limit=0", "-include", preamble, path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    except OSError as exc:
        return None, str(exc)
    msgs = [ln.split(": error: ", 1)[-1].split(": fatal error: ", 1)[-1]
            for ln in p.stderr.splitlines()
            if ": error: " in ln or ": fatal error: " in ln]
    return msgs, ""


def normalise(msg):
    msg = re.sub(r"'[^']*'", "'X'", msg)
    msg = re.sub(r"\b0x[0-9a-fA-F]+\b", "N", msg)
    msg = re.sub(r"\b\d+\b", "N", msg)
    return msg.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=os.path.join("out", "src"))
    ap.add_argument("--types", default=os.path.join("out", "types"))
    ap.add_argument("--prelude", default=os.path.join("out", "check", "prelude.h"))
    ap.add_argument("--out", default=_GENERATED)
    ap.add_argument("--clang", default="clang++")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--dump", default="")
    ap.add_argument("--decls-only", action="store_true",
                    help="check the generated declarations and stop")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    model = Model()
    load_classes(model, args.types)
    load_fields(model, args.types)
    scan(model, args.src)
    os.makedirs(args.out, exist_ok=True)
    decls = os.path.join(args.out, "decls.h")
    preamble = os.path.join(args.out, "preamble.h")
    nc, nm, ne = generate(model, decls)
    build_preamble(args.prelude, preamble)

    print("classes declared           %6d" % nc)
    print("member declarations        %6d" % nm)
    print("opaque structs declared    %6d" % ne)
    print("definitions parsed         %6d" % model.stats["defs"])
    print("  unparsed headers         %6d" % model.stats["unparsed"])
    print("  template/skipped         %6d" % model.stats["skipped-template"])
    print("placeholder globals        %6d" % len(model.symbols))

    if args.decls_only:
        empty = os.path.join(args.out, "_empty.cpp")
        with open(empty, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("/* the declarations alone */\n")
        msgs, err = run_clang(args.clang, preamble, empty)
        if msgs is None:
            print("clang failed: %s" % err, file=sys.stderr)
            return 2
        errors = collections.Counter(normalise(m) for m in msgs)
        print("\ndeclarations: %d errors" % len(msgs))
        for msg, count in errors.most_common(args.top):
            print("  %7d  %s" % (count, msg[:110]))
        return 1 if (args.check and msgs) else 0

    files = []
    for base, _dirs, names in os.walk(args.src):
        for name in sorted(names):
            if name.endswith(".cpp"):
                files.append(os.path.join(base, name))
    if args.only:
        files = [f for f in files if args.only in f.replace("\\", "/")]
    if args.sample:
        files = files[:args.sample]

    errors = collections.Counter()
    per_file = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for path, (msgs, err) in pool.map(
                lambda f: (f, run_clang(args.clang, preamble, f)), files):
            if msgs is None:
                print("clang failed: %s" % err, file=sys.stderr)
                return 2
            for msg in msgs:
                errors[normalise(msg)] += 1
            per_file.append((path, len(msgs), msgs))

    total = sum(n for _p, n, _m in per_file)
    print()
    print("files checked              %6d" % len(files))
    print("files with errors          %6d" % sum(1 for _p, n, _m in per_file if n))
    print("errors total               %6d" % total)
    print()
    print("top diagnostic kinds:")
    for msg, count in errors.most_common(args.top):
        print("  %7d  %s" % (count, msg[:110]))

    if args.dump:
        with open(args.dump, "w", encoding="utf-8", newline="\n") as fh:
            for path, _n, msgs in sorted(per_file, key=lambda r: -r[1]):
                for msg in msgs:
                    fh.write("%s\t%s\n" % (os.path.relpath(path, args.src), msg))
    if args.check and total:
        print("check_syntax: %d errors remain" % total, file=sys.stderr)
        return 1
    if args.check:
        print("check_syntax: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
