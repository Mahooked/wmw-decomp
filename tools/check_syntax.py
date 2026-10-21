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
        self.tmpl_members = collections.defaultdict(dict)
                                        # members harvested from template-
                                        # qualified definitions, keyed by the
                                        # primary template that owns them
        self.tmpl_args = collections.defaultdict(set)
                                        # (top-level arg count, all type-like)
                                        # per primary, from instantiation args
        self.tmpl_sigs = collections.defaultdict(dict)
                                        # (name, params, const) -> slot, so the
                                        # copies of one member recovered from
                                        # several specializations collapse
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
                head = strip_comments(decl[:span[0]])
                # A long recovered signature is wrapped after a "::" (or just
                # before one), which would otherwise pull the qualifier into
                # the return type: "void Walaber::\n Vector2::f" splits as
                # return type "void Walaber::" and name "Vector2::f".
                head = re.sub(r"\s*::\s+", "::", head)
                # ... and sometimes just *before* one: "num_get<...>\n   ::f".
                head = re.sub(r"\s+::", "::", head)
                # Definitions shaped by tools/shape_tmpl_defs.py carry the
                # explicit-specialization marker in front; it is not a type.
                head = re.sub(r"^\s*template\s*<>\s*", "", head)
                got = split_name(head)
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
                # A body that names ``this`` was shifted by apply_signatures:
                # its object is the implicit C++ this, so its declaration must
                # stay non-static.  Every other member body takes the object as
                # an explicit first parameter (Ghidra's static form), which is
                # also how the call sites spell it -- ``A::f(obj, args)``.
                uses_this = re.search(r"\bthis\b",
                                      strip_comments(block[brace:])) is not None
                add_definition(model, ret, qname, params, post, uses_this)


#: Template parameter lists for every primary template the prelude declares,
#: mirroring its spellings minus the default arguments (a default may only be
#: repeated, never introduced, on a later declaration).
_TMPL_PARAMS = {
    "std::__ndk1::allocator": "class T",
    "std::__ndk1::char_traits": "class T",
    "std::__ndk1::less": "class T",
    "std::__ndk1::hash": "class T",
    "std::__ndk1::pair": "class A, class B",
    "std::__ndk1::tuple": "class... T",
    "std::__ndk1::default_delete": "class T, class D",
    "std::__ndk1::unique_ptr": "class T, class D",
    "std::__ndk1::unique_lock": "class T",
    "std::__ndk1::lock_guard": "class T",
    "std::__ndk1::shared_ptr": "class T",
    "std::__ndk1::weak_ptr": "class T",
    "std::__ndk1::initializer_list": "class T",
    "std::__ndk1::iterator_traits": "class T",
    "std::__ndk1::reverse_iterator": "class T",
    "std::__ndk1::basic_string": "class C, class T, class A",
    "std::__ndk1::vector": "class T, class A",
    "std::__ndk1::deque": "class T, class A",
    "std::__ndk1::list": "class T, class A",
    "std::__ndk1::multiset": "class K, class C, class A",
    "std::__ndk1::map": "class K, class V, class C, class A",
    "std::__ndk1::multimap": "class K, class V, class C, class A",
    "std::__ndk1::set": "class K, class C, class A",
    "std::__ndk1::__tree": "class T, class C, class A",
    "std::__ndk1::__value_type": "class K, class V",
    "std::__ndk1::__map_value_compare": "class K, class V, class C, bool",
    "std::__ndk1::__tree_node": "class T, class P",
    "std::__ndk1::__tree_node_base": "class T",
    "std::__ndk1::__tree_end_node": "class T",
    "std::__ndk1::__tree_iterator": "class T, class N, class D",
    "std::__ndk1::__tree_const_iterator": "class T, class N, class D",
    "std::__ndk1::__tree_node_destructor": "class T",
    "std::__ndk1::__split_buffer": "class T, class A",
    "std::__ndk1::__deque_base": "class...",
    "std::__ndk1::__vector_base": "class T, class A",
    "std::__ndk1::__vector_base_common": "class T",
    "std::__ndk1::basic_ostream": "class C, class T",
    "std::__ndk1::basic_istream": "class C, class T",
    "std::__ndk1::basic_iostream": "class C, class T",
    "std::__ndk1::basic_streambuf": "class C, class T",
    "std::__ndk1::basic_stringbuf": "class C, class T, class A",
    "std::__ndk1::basic_filebuf": "class C, class T",
    "std::__ndk1::istreambuf_iterator": "class C, class T",
    "std::__ndk1::ostreambuf_iterator": "class C, class T",
    "std::__ndk1::__basic_string_common": "class C",
    "std::__ndk1::ctype": "class C",
    "std::__ndk1::codecvt": "class I, class E, class S",
    "std::__ndk1::moneypunct": "class C, bool",
    "std::__ndk1::moneypunct_byname": "class C, bool",
    "std::__ndk1::numpunct": "class C",
    "std::__ndk1::num_get": "class C, class I",
    "std::__ndk1::num_put": "class C, class O",
    "std::__ndk1::time_get": "class C, class I",
    "std::__ndk1::time_put": "class C, class O",
    "std::__ndk1::collate": "class C",
    "std::__ndk1::messages": "class C",
    "Walaber::SharedPtr": "class T",
    "Walaber::MemberCallback": "class T",
    "Walaber::WeakPtr": "class T",
}

#: Operator spellings a *member* may carry.  Ghidra also invents names like
#: ``operator_cast_to_map``; those are not C++ operators at all and would be a
#: parse error in every file that includes the preamble.
_OPSPELL = re.compile(
    r"^operator\s*(?:\[\]|\(\)|->\*|->|<<=|>>=|<=>|<<|>>|<=|>=|==|!=|&&|\|\||"
    r"\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|,|\+|-|\*|/|%|\^|&|\||~|!|=|<|>)$")


def _split_qname(qname):
    """Split a qualified name at ``::`` that sits outside any ``<...>``.

    ``basic_ostream<char, traits<char>>::sentry::sentry`` is not splittable by
    a plain ``str.split`` -- the commas and the ``>>`` inside the arguments
    carry no scope meaning, and ``operator<<``'s angle brackets are part of the
    operator's spelling rather than template arguments.
    """
    comps, i, start, depth = [], 0, 0, 0
    while i < len(qname):
        if qname.startswith("operator", i) and depth == 0 and not (
                qname[i - 1:i].isalnum() or qname[i - 1:i] == "_"):
            j = i + len("operator")
            while j < len(qname) and qname[j] in "[]()<>+-*/%^&|!~=":
                j += 1
            i = j
            continue
        if depth == 0 and qname.startswith("::", i):
            comps.append(qname[start:i])
            i += 2
            start = i
            continue
        if qname[i] == "<":
            depth += 1
        elif qname[i] == ">":
            depth = max(0, depth - 1)
        i += 1
    comps.append(qname[start:])
    return comps


def _strip_angles(text):
    """``basic_string<char, traits<char>>`` -> ``basic_string``."""
    return text.split("<", 1)[0]


def _split_commas(text):
    """Split an argument list at the commas that sit at depth zero."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c in "<([{":
            depth += 1
        elif c in ">)]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _looks_like_type(arg):
    """True when an instantiation argument spells a type, not a value."""
    a = arg.strip()
    if not a or not re.match(r"^[A-Za-z_][\w:<>,\s*&]*$", a):
        return False
    return re.search(r"\b(?:false|true)\b|(?<![\w:])\d|0x[0-9a-fA-F]+",
                     a) is None


def _canon_params(text):
    """Key by the parameter list C++ sees rather than by its spelling.

    The prelude spells its fixed-width integers as typedefs (``ulong`` and
    ``ulonglong`` are both ``unsigned long long``), and the decompiler picks
    either spelling for the same signature; comparing the raw text would keep
    both declarations and clang rejects the second.  Parameter names are
    equally irrelevant -- ``f(int a)`` and ``f(int b)`` are one function.
    """
    text = " ".join(text.split())
    text = re.sub(r"\bunsigned long long\b", "ulong", text)
    text = re.sub(r"\blong long\b", "longlong", text)
    text = re.sub(r"\bulonglong\b", "ulong", text)
    # Ghidra's width-named integers are typedefs of the same fundamental
    # types; one definition spells them either way.
    text = re.sub(r"\b(?:undefined1|uint1|undefined|uchar)\b", "uchar", text)
    text = re.sub(r"\b(?:undefined2|uint2|ushort)\b", "ushort", text)
    text = re.sub(r"\b(?:undefined3|undefined4|uint4|uint)\b", "uint", text)
    text = re.sub(r"\b(?:undefined5|undefined6|undefined7|undefined8|uint8)\b",
                  "ulong", text)
    text = re.sub(r"\bint1\b", "schar", text)
    text = re.sub(r"\b(?:int3|int4)\b", "int", text)
    text = re.sub(r"\b(?:int5|int6|int7|int8)\b", "longlong", text)
    parts = []
    for part in _split_commas(text):
        part = part.strip()
        m = re.match(r"^(.*?)([A-Za-z_]\w*)$", part, re.S)
        if (m and m.group(2) not in _PARAM_KEYWORDS and m.group(1)
                and re.search(r"[*&>\s]$", m.group(1))):
            part = m.group(1).strip()
        parts.append(part)
    return re.sub(r"\s+", "", ",".join(parts))


#: Words that end a parameter because they *are* its type, not its name.
_PARAM_KEYWORDS = frozenset("""
const volatile signed unsigned short long int char float double void bool
wchar_t char16_t char32_t struct class union enum typename auto
""".split())


def _nested_incomplete(model, text):
    """True when ``text`` names a member type of a class declared later.

    The primary templates are emitted before the recovered classes (the
    classes' fields need them complete), so a parameter spelling
    ``SomeClass::Nested`` cannot be declared there: ``SomeClass`` is only
    forward-declared and the nested name is unusable.  The definition then
    fails to match, which costs one diagnostic instead of poisoning every file
    through ``decls.h``.
    """
    for m in re.finditer(r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)+)::[A-Za-z_]",
                         text):
        if m.group(1) in model.classes:
            return True
    return False


def _harvest_template(model, ret, qname, params, post, uses_this):
    """Record one out-of-line definition of a member of a class template.

    ``void basic_string<char, A>::assign(long)`` is an explicit specialization
    of a member of the *primary* template; the member has to exist on the
    primary for either the definition or any call site to compile.  Record the
    member (and the shape of the template's arguments) so ``generate`` can put
    them there.
    """
    comps = _split_qname(qname)
    if len(comps) < 2:
        model.stats["skipped-template-fn"] += 1   # a free function template
        return
    if not any("<" in c for c in comps[:-1]):
        model.stats["skipped-template-fn"] += 1   # a namespace-only qualifier
        return
    name = comps[-1]
    if not re.match(r"^[A-Za-z_~]\w*$", name) and not (
            name.startswith("operator") and _OPSPELL.match(name)):
        # A member template (``__push_back_slow_path<int>``).  Its call sites
        # spell the template arguments, so the name still has to exist on the
        # primary; the greedy overload below is enough for them to resolve.
        base = _strip_angles(name)
        if re.match(r"^[A-Za-z_~]\w*$", base):
            model.tmpl_members[
                "::".join(_strip_angles(c) for c in comps[:-1])].setdefault(
                    base, [])
        model.stats["skipped-template-member"] += 1
        return
    if name.startswith(("non_virtual_thunk_to_", "virtual_thunk_to_",
                        "_thunk_to_")):
        model.stats["skipped-thunk"] += 1
        return
    owner = comps[:-1]
    cls = owner[-1]
    # A parameter Ghidra printed as ``void (*param_9)(void*)`` carries the
    # name inside the template argument; a declarator needs no name there.
    params = re.sub(r"\(\s*(\*+)\s*\w+\s*\)", r"(\1)", params)
    is_dtor = name.startswith("~")
    is_ctor = (not is_dtor) and name == _strip_angles(cls)
    is_op = name.startswith("operator") and bool(_OPSPELL.match(name))
    if is_op:
        if params.strip() in ("", "void"):
            model.stats["skipped-operator"] += 1
            return
        if name != "operator()" and (
                "," in params or (name in ("operator++", "operator--")
                                  and not re.match(r"^\s*int(\s+\w+)?\s*$",
                                                   params))):
            # Ghidra prints a member operator in static form, with the object
            # passed as the first argument; a member operator cannot declare
            # that parameter, so drop it.  The definition is shaped the same
            # way (tools/shape_tmpl_defs.py).
            params = ",".join(p.strip() for p in _split_commas(params)[1:])
    elif name.startswith("operator"):
        # ``operator_cast_to_map`` lexes as one identifier, not an operator,
        # so it is an ordinary member.
        model.stats["named-member-operator"] += 1
    for idx, c in enumerate(owner):
        if "<" in c:
            top = "::".join(_strip_angles(x) for x in owner[:idx + 1])
            if c.endswith(">"):
                args = [a for a in _split_commas(c[c.index("<") + 1:-1])
                        if a.strip()]
                model.tmpl_args[top].add(
                    (len(args), all(_looks_like_type(a) for a in args)))
            break
    key = "::".join(_strip_angles(c) for c in owner)
    if is_dtor:
        ret, params = "", ""
    elif is_ctor:
        ret = ""
    # The static-form call the decompiler prints passes the object as the
    # first argument, so a body that never names ``this`` is a free function
    # in disguise; the same rule keeps every operator non-static.
    static = not (is_ctor or is_dtor or is_op
                  or uses_this or "const" in post or "virtual" in post)
    if _nested_incomplete(model, params):
        model.stats["skipped-nested-type"] += 1
        return
    members = model.tmpl_members[key]
    bucket = members.setdefault(name, [])
    decl = _decl(ret, name, params, post, static)
    # The same member is recovered once per specialization, and the two copies
    # disagree on return type (``char *`` / ``wchar_t *``) and sometimes on
    # static-ness.  Only one declaration may exist per signature; the extra
    # copy would be an illegal overload.
    sig = (name, _canon_params(params),
           bool(re.search(r"\bconst\b", post)),
           bool(re.search(r"\bvirtual\b", post)))
    sigs = model.tmpl_sigs[key]
    if sig in sigs:
        if decl.startswith("static ") and not bucket[sigs[sig]].startswith(
                "static "):
            bucket[sigs[sig]] = decl
        return
    sigs[sig] = len(bucket)
    bucket.append(decl)


def _derive_params(model, key):
    """Template parameters for a primary the table does not know.

    Every recorded instantiation of the primary must agree on one arity and
    spell only types, then the primary can be declared with placeholder
    parameters of that arity.  A non-type argument (``moneypunct<char, false>``)
    means the placeholders cannot be assumed to be types, and the primary has
    to be added to the table instead.
    """
    seen = model.tmpl_args.get(key)
    if not seen:
        return None
    counts = {c for c, _t in seen}
    if len(counts) == 1 and all(t for _c, t in seen):
        return ", ".join("class _T%d" % i for i in range(counts.pop()))
    return None


def _emit_primary(model, key, params, defined):
    """A full definition of one primary template with recovered members.

    Each member carries its exact harvested declaration *and* a greedy
    variadic overload: a call site Ghidra printed with a different arity or an
    integer-typed object argument cannot match the exact declaration, and the
    member templates of libc++ are never visible anyway, so the overload is
    what makes those call sites resolve.
    """
    name = key.split("::")[-1]
    members = model.tmpl_members[key]
    lines = ["template <%s> struct %s {" % (params, name)]
    for short in sorted(members):
        for decl in members[short]:
            lines.append("  " + decl)
    child = key + "::"
    for sub in sorted(model.tmpl_members):
        if not sub.startswith(child) or sub[len(child):].count("::"):
            continue
        lines.append("  struct %s {" % sub[len(child):])
        for short in sorted(model.tmpl_members[sub]):
            for decl in model.tmpl_members[sub][short]:
                lines.append("    " + decl)
        lines.append("  };")
    lines.append("  template <class... _A> %s(_A...);" % name)
    if ("~" + name) not in members:
        lines.append("  ~%s();" % name)
    for short in sorted(members):
        if short.startswith("~") or short == name:
            continue
        if short.startswith("operator"):
            lines.append("  template <class... _A> _Datum %s(_A...);"
                         % short)
        else:
            # The trailing ellipsis matters: Ghidra writes a static-form call
            # as ``Class<T>::name<Args>(object, arg)``, which spells explicit
            # template arguments *and* passes the object on top.  A plain pack
            # would fix the arity to the number of explicit arguments.
            lines.append("  template <class... _A> static _Datum %s(_A..., ...);"
                         % short)
    lines.append("};")
    return "\n".join(lines)


def add_definition(model, ret, qname, params, post, uses_this=False):
    if "<" in qname or "<" in ret or "[" in ret:
        model.stats["skipped-template"] += 1
        if "<" in qname and "<" not in ret and "[" not in ret:
            _harvest_template(model, ret, qname, params, post, uses_this)
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
    if short in ("operator++", "operator--") and not re.match(
            r"^\s*int(\s+\w+)?\s*$", params):
        # A single-parameter ++/-- parses as the postfix form, whose parameter
        # must be exactly `int`.  Here the parameter is Ghidra's static-form
        # object pointer, which C++ gives no spelling for; declaring it would
        # error in every one of the 1,467 files that include the preamble.
        model.stats["skipped-operator"] += 1
        return
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
            _store(model.funcs[ns], name, _decl(ret, name, params, post))
        else:
            _store(model.funcs[""], qname, _decl(ret, qname, params, post))
        return
    ns, cls = parts
    short = cls[-1]
    owner = "::".join(cls[:-1])
    # A constructor or destructor cannot be static, and neither can an
    # operator whose call syntax needs an object (operator=, operator(),
    # operator[]).  A `this`-using body already has its object implicit.
    is_dtor = short.startswith("~")
    is_ctor = (not is_dtor) and len(cls) >= 2 and short == cls[-2]
    is_op = short.startswith("operator")
    static = (not (is_ctor or is_dtor or is_op or uses_this)
              and "const" not in post and "virtual" not in post)
    if owner:
        target = "::".join(ns + cls[:-1])
        if is_dtor:
            params, post = "", post
        elif is_ctor:
            ret = ""
        _store(model.members[target], short,
               _decl(ret, short, params, post, static))
    else:
        if is_dtor or short == cls[-1]:
            ret = ""
        _store(model.members["::".join(ns + cls)], short,
               _decl(ret, short, params, post))


def _store(bucket, key, decl):
    """Remember a declaration, keeping every overload of the same name.

    A class often defines the same method at several addresses (D1/D2 dtors,
    thunks resolved to distinct bodies) and genuinely overloads others
    (``setPosition(Vector2)`` and ``setPosition(float, float, float)``); a
    single slot silently dropped all but the last one seen, so call sites to
    the lost overloads read "no matching function".
    """
    seen = bucket.setdefault(key, [])
    if decl not in seen:
        seen.append(decl)


def _decl(ret, name, params, post, static=False):
    body = "%s(%s)" % (name, params)
    if post:
        body += " " + post
    text = ("%s %s;" % (ret, body)).strip() if ret else body + ";"
    return ("static " + text) if static else text


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
        for decl in model.members[qname][short]:
            out.append("%s  %s" % (indent, decl))
    # A constructor call site is rewritten to placement new -- `new (obj)
    # Cls(args)` -- but most called constructors have no decompiled body, so
    # every class gets one greedy constructor template covering every arity;
    # an exact overload from a definition still wins overload resolution.
    # Every class likewise gets a declared destructor, because the static-form
    # dtor call is rewritten to an explicit `((Cls *)obj)->~Cls()`.
    short = qname.split("::")[-1]
    out.append("%s  template <class... _A> %s(_A...);" % (indent, short))
    if ("~" + short) not in model.members.get(qname, {}):
        out.append("%s  ~%s();" % (indent, short))
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


# Declaring ANY global operator new/delete makes clang implicitly declare its
# whole standard allocation family, which pre-declares std::align_val_t as an
# *enum* (libc++ spells it `enum class align_val_t : size_t`).  Emitting our
# recovered `struct align_val_t` over it is then a tag-kind clash; no body
# spells the qualified name as code anyway (Ghidra flattens the definitions
# to `operator_new`), so the class is simply not emitted.
_CLANG_IMPLICIT = frozenset({"std::align_val_t"})


def add_greedy(model, path):
    """Declare a greedy overload for every name a call spelled as a template.

    ``tools/shape_tmpl_calls.py`` drops the explicit template arguments from
    calls whose callee the tree recovered as an ordinary function, and records
    the qualified names it saw.  The recovered declaration came from a single
    instantiation (``void __tree_remove(long *, long *)``), so a call made with
    another instantiation's argument types still does not convert.  A variadic
    overload of the same name accepts those calls; an exact overload recovered
    from a definition still wins, because a non-template beats a template.
    """
    if not path or not os.path.exists(path):
        return 0, 0
    added = 0
    skipped = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        qname = line.strip()
        if not qname:
            continue
        owner, name = qname.rsplit("::", 1)
        if name in model.members.get(owner, {}):
            model.members[owner][name].append(
                "template <class... _A> static _Datum %s(_A&&...);" % name)
            added += 1
        elif name in model.funcs.get(owner, {}):
            model.funcs[owner][name].append(
                "template <class... _A> _Datum %s(_A&&...);" % name)
            added += 1
        else:
            skipped += 1
    return added, skipped


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

    # Primary templates whose members the template-qualified definitions
    # proved exist.  A key whose owner is itself harvested is a nested class
    # and is emitted inside its owner's body.
    primaries = []
    defined = set()
    for key in sorted(model.tmpl_members):
        if "::".join(key.split("::")[:-1]) in model.tmpl_members:
            continue
        parts = key.split("::")
        if any("::".join(parts[:i]) in model.classes
               for i in range(1, len(parts))):
            # The template is a member of a class the generator declares (a
            # recovered static utility class), where a namespace-scope
            # definition would clash with that class.
            model.stats["skipped-template-in-class"] += 1
            continue
        params = _TMPL_PARAMS.get(key) or _derive_params(model, key)
        if params is None:
            model.stats["skipped-template-params"] += 1
            continue
        primaries.append((key, params))
        defined.add(key)

    for cls in sorted(model.classes):
        if cls in _CLANG_IMPLICIT:
            continue
        comps = cls.split("::")
        if len(comps) == 1 or "::".join(comps[:-1]) not in model.classes:
            out.append(_wrap(comps[:-1], "struct %s;" % comps[-1]))
    for t in sorted(model.templates - model.types):
        if t in defined:
            continue          # declared with its real parameters below
        comps = t.split("::")
        out.append(_wrap(comps[:-1], "template <class...> struct %s;" % comps[-1]))

    # Ghidra spells a type by flattening every "::" to "__"
    # (``Walaber__Vector2``), and the bodies freely mix that spelling with the
    # real scoped one (``Walaber::Vector2``).  The generator defines the class
    # under its real scope, so the flat spelling is a *different*, opaque type:
    # every member access or subscript through it reads "incomplete type", and
    # a call spelled with the scoped name matches no parameter declared with
    # the flat one.  Alias each flat spelling to the class it names.  A nested
    # class is skipped -- its owner has to be defined before the alias could
    # name it, which no earlier declaration can do.
    flat_alias = {}
    for cls in model.classes:
        if "<" in cls or cls in _CLANG_IMPLICIT:
            continue
        # ``std::exception`` and ``std::__ndk1::exception`` are the same
        # inline-namespace member, so the unqualified-in-std spelling is
        # ambiguous; only the explicitly nested ``std::__ndk1::`` form is safe.
        if cls.startswith("std::") and not cls.startswith("std::__ndk1::"):
            continue
        flat = cls.replace("::", "__")
        if flat == cls or cls.rsplit("::", 1)[0] in model.classes:
            continue
        flat_alias[flat] = cls
    for flat in sorted(flat_alias):
        out.append("using %s = %s;" % (flat, flat_alias[flat]))

    for t in extra:
        if t in flat_alias:
            continue
        comps = t.split("::")
        out.append(_wrap(comps[:-1], "struct %s;" % comps[-1]))
    declared = model.defined | set(model.funcs)
    out.append("\n".join("extern _Datum %s;" % s
                         for s in sorted(model.symbols) if s not in declared))

    # A definition of a member of a class template needs the primary template
    # to exist with that member declared; the prelude already declares the
    # libc++ primaries, so only the recovered game/ndk templates are declared
    # here, with their real parameters (a variadic forward would not do: the
    # members would land on a different template).
    for key, params in primaries:
        if key not in _TMPL_PARAMS:
            comps = key.split("::")
            out.append(_wrap(comps[:-1],
                             "template <%s> struct %s;" % (params, comps[-1])))
    for key, params in primaries:
        comps = key.split("::")
        out.append(_wrap(comps[:-1],
                         _emit_primary(model, key, params, defined)))

    emitted = set()
    for cls in sorted(model.classes):
        if cls in _CLANG_IMPLICIT:
            continue
        comps = cls.split("::")
        if len(comps) == 1 or "::".join(comps[:-1]) not in model.classes:
            buf = []
            emit_class(model, cls, buf, 0, emitted, set())
            out.append(_wrap(comps[:-1], "\n".join(buf)))
    for ns in sorted(model.funcs):
        decls = "\n".join(d for n in sorted(model.funcs[ns])
                          for d in model.funcs[ns][n])
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
    ap.add_argument("--tmpl-calls",
                    default=os.path.join("out", "check", "tmpl_calls.tsv"),
                    help="names that call sites spelled with template arguments")
    ap.add_argument("--decls-only", action="store_true",
                    help="check the generated declarations and stop")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    model = Model()
    load_classes(model, args.types)
    load_fields(model, args.types)
    scan(model, args.src)
    greedy, greedy_skipped = add_greedy(model, args.tmpl_calls)
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
    print("template-call overloads    %6d" % greedy)
    print("  unresolved               %6d" % greedy_skipped)
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
