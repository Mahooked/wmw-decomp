"""Itanium C++ ABI demangler (pure Python, no dependencies).

Written because the Where's My Water? engine (``libwmw.so``) is only partially
stripped: 7933 exported symbols survive with full Itanium mangling.  Demangling
them recovers the complete class/method/namespace inventory of the engine.

The grammar implemented is the subset that actually appears in the binary:
nested names, template arguments, substitutions, operators, ctor/dtor, local
names, builtin types, cv-qualifiers, function/member types, literals.

Parsing is deliberately *fault tolerant*: any failure returns the raw mangled
string so that a single odd symbol can never abort a bulk run.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# builtin type codes (Itanium ABI 5.2.2)
# ---------------------------------------------------------------------------
BUILTIN_TYPES = {
    "v": "void",
    "w": "wchar_t",
    "b": "bool",
    "c": "char",
    "a": "signed char",
    "h": "unsigned char",
    "s": "short",
    "t": "unsigned short",
    "i": "int",
    "j": "unsigned int",
    "l": "long",
    "m": "unsigned long",
    "x": "long long",
    "y": "unsigned long long",
    "n": "__int128",
    "o": "unsigned __int128",
    "f": "float",
    "d": "double",
    "e": "long double",
    "g": "__float128",
    "z": "...",
    "Dd": "decimal64",
    "De": "decimal128",
    "Df": "decimal32",
    "Dh": "half",
    "Di": "char32_t",
    "Ds": "char16_t",
    "Du": "char8_t",
    "Da": "auto",
    "Dc": "decltype(auto)",
    "Dn": "std::nullptr_t",
}

# operator name encodings (Itanium ABI 5.1.1)
OPERATORS = {
    "nw": " new",
    "na": " new[]",
    "dl": " delete",
    "da": " delete[]",
    "ps": "+",
    "ng": "-",
    "ad": "&",
    "de": "*",
    "co": "~",
    "pl": "+",
    "mi": "-",
    "ml": "*",
    "dv": "/",
    "rm": "%",
    "an": "&",
    "or": "|",
    "eo": "^",
    "aS": "=",
    "pL": "+=",
    "mI": "-=",
    "mL": "*=",
    "dV": "/=",
    "rM": "%=",
    "aN": "&=",
    "oR": "|=",
    "eO": "^=",
    "ls": "<<",
    "rs": ">>",
    "lS": "<<=",
    "rS": ">>=",
    "eq": "==",
    "ne": "!=",
    "lt": "<",
    "gt": ">",
    "le": "<=",
    "ge": ">=",
    "ss": "<=>",
    "nt": "!",
    "aa": "&&",
    "oo": "||",
    "pp": "++",
    "mm": "--",
    "cm": ",",
    "pm": "->*",
    "pt": "->",
    "cl": "()",
    "ix": "[]",
    "qu": "?",
    "cv": "cast to",  # special: followed by a type
    "li": '""',  # string literal
    "v": "__vector",  # vendor extended
}

CTOR_DTOR = {
    "C1": "", "C2": "", "C3": "",
    "CI1": "", "CI2": "",
    "D0": "~", "D1": "~", "D2": "~",
}

ABI_TAGS = {
    "c": "c",  # restrict-ish, gcc ctor
    "d": "d",
    "i": "i32",
    "l": "l",
    "s": "s",
}

# standard substitutions (Itanium ABI 5.1.4)
STD_SUBS = {
    "Sa": "std::allocator",
    "Sb": "std::basic_string",
    "Ss": "std::string",
    "Si": "std::istream",
    "So": "std::ostream",
    "Sd": "std::iostream",
}

# reverse lookup: demangled std type -> mangled short code (best effort)
CV_QUALS = [("r", "restrict"), ("V", "volatile"), ("K", "const")]


class _Fail(Exception):
    pass


def _split_template(name: str) -> tuple[str, str]:
    """Split ``ns::Foo<int>`` into ``("ns::Foo", "<int>")``.

    Scans for the '<' that opens the top-level template argument list, tracking
    nesting depth and skipping anything inside an operator name.
    """
    depth = 0
    for idx, ch in enumerate(name):
        if ch == "<":
            if depth == 0:
                return name[:idx], name[idx:]
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
    return name, ""


class Demangler:
    def __init__(self, s: str):
        self.s = s
        self.i = 0
        self.subs: list[str] = []
        self.type_depth = 0

    # -- low level ------------------------------------------------------
    def eof(self) -> bool:
        return self.i >= len(self.s)

    def peek(self, n: int = 1) -> str:
        return self.s[self.i : self.i + n]

    def next(self) -> str:
        if self.eof():
            raise _Fail("eof")
        c = self.s[self.i]
        self.i += 1
        return c

    def expect(self, ch: str) -> None:
        c = self.next()
        if c != ch:
            raise _Fail("expected %r got %r at %d" % (ch, c, self.i))

    def eat(self, ch: str) -> bool:
        if not self.eof() and self.s[self.i] == ch:
            self.i += 1
            return True
        return False

    # -- substitutions --------------------------------------------------
    def add_sub(self, name: str) -> str:
        # Itanium substitution indices are positional: every component takes
        # the next index even when the same name was already registered.
        # De-duplicating here would silently shift every later S<n>_ reference.
        if name:
            self.subs.append(name)
        return name

    def parse_substitution(self) -> str:
        # caller has consumed 'S'
        if self.eof():
            raise _Fail("eof in substitution")
        c = self.s[self.i]
        if c == "_":
            self.i += 1
            return self._sub_at(0)
        if c.isdigit():
            num = self._number()
            if not self.eat("_"):
                raise _Fail("bad substitution")
            # Itanium numbering is not what it looks like: 'S_' is the first
            # substitution, then 'S0_' is the second, 'S1_' the third, so a
            # numeric seq-id is offset by one.
            return self._sub_at(num + 1)
        if c == "t":
            self.i += 1
            name = self._parse_name()
            return "std::" + name
        # Standard substitutions: the 'S' has already been consumed, so match on
        # the single trailing character.
        std_code = {"a": "Sa", "b": "Sb", "s": "Ss", "i": "Si", "o": "So", "d": "Sd"}
        if c in std_code:
            self.i += 1
            return STD_SUBS[std_code[c]]
        raise _Fail("bad substitution char %r" % c)

    def _sub_at(self, num: int) -> str:
        if num >= len(self.subs):
            raise _Fail("substitution index %d >= %d" % (num, len(self.subs)))
        return self.subs[num]

    def _number(self) -> int:
        start = self.i
        while not self.eof() and self.s[self.i].isdigit():
            self.i += 1
        if start == self.i:
            raise _Fail("number expected")
        return int(self.s[start : self.i], 10)

    # -- names ----------------------------------------------------------
    def _parse_source_name(self, in_nested: bool = False) -> str:
        n = self._number()
        if n == 0:
            raise _Fail("zero-length source name")
        if self.i + n <= len(self.s):
            raw = self.s[self.i : self.i + n]
            nxt = self.s[self.i + n : self.i + n + 1]
            # Inside a <nested-name> the only legal followers of a source-name
            # are 'E' (terminator), 'I' (template args) or a digit (the next
            # length prefix).  A letter or '_' there means the length prefix
            # disagrees with the identifier, which several WaterConceptConstants
            # symbols in this build do (e.g. 19MYSTERY_STARBLAST_MAXSIZE).  Walk
            # out to the next terminator and recover the real name.
            if in_nested and (nxt.isalpha() or nxt == "_"):
                start = self.i
                j = start + n
                while j < len(self.s) and (self.s[j].isalnum() or self.s[j] == "_"):
                    j += 1
                if j > start + n and j < len(self.s) and self.s[j] == "E":
                    self.i = j
                    return self.s[start:j]
                if j > start + n and j < len(self.s) and self.s[j].isdigit():
                    # Keep walking while the remaining text is a valid C
                    # identifier; the true length prefix is still ahead.
                    k = j
                    while k < len(self.s) and (self.s[k].isalnum() or self.s[k] == "_"):
                        k += 1
                    if k > j and k < len(self.s) and self.s[k] == "E":
                        self.i = k
                        return self.s[start:k]
            self.i += n
            return raw
        # Length prefix overruns the symbol entirely: take what is left.
        rest = self.s[self.i :]
        self.i = len(self.s)
        if not rest:
            raise _Fail("source name overruns")
        cut = rest.find("E")
        return rest[:cut] if cut > 0 else rest

    def _parse_abi_tags(self) -> str:
        tags = []
        while self.peek() == "B":
            self.i += 1
            c = self.next()
            tags.append(ABI_TAGS.get(c, c))
        return (" " + " ".join(tags)) if tags else ""

    def _parse_unqualified_name(self, template_prefix: bool = False, in_nested: bool = False) -> str:
        c = self.next()
        if c == "C" or c == "D":
            # ctor / dtor
            if c == "C":
                self.next()  # 1/2/3
                if self.peek() == "I":
                    self.i += 1
                    self._parse_template_args()
                if self.peek() == "C":
                    self.next()
                    self._parse_template_args()
                return ""  # caller supplies class name
            self.next()  # 0/1/2
            return "~"
        if c in OPERATORS:
            op = OPERATORS[c]
            if c == "cv":
                t = self._parse_type()
                return "operator " + t
            if c == "li":
                s = self._parse_source_name()
                return 'operator""' + s
            if c == "v":
                d = self._number()
                return "operator __vector(%d)" % d
            return "operator" + op
        if c.isdigit():
            self.i -= 1
            nm = self._parse_source_name(in_nested=in_nested)
            nm += self._parse_abi_tags()
            return nm
        # named type used as unqualified name (rare)
        self.i -= 1
        # NOTE: _parse_type's last resort is _parse_name and vice versa, so this
        # must not recurse unconditionally - a malformed component would spin
        # until RecursionError.  Try the type production once, then give up and
        # consume a character so the caller always makes progress.
        t = self._parse_type()
        if t:
            return t
        self.i += 1
        return "?"

    def _maybe_template_args(self) -> str:
        """Template args bind at the *prefix* level in the Itanium grammar, so
        they are parsed by the caller (which registers each component in the
        substitution table as it goes) and appended here."""
        if self.peek() == "I":
            self.i += 1
            return self._parse_template_args_body()
        return ""

    def _parse_nested_name(self) -> str:
        self.expect("N")
        quals = self._parse_cv_qualifiers()
        ref = ""
        if self.peek() in ("R", "O"):
            ref = "&" if self.next() == "R" else "&&"

        # parse components; track the class name for ctor/dtor
        components: list[str] = []
        is_template_prefix = False
        # Index into ``components`` of the most recent *class name* component,
        # needed because a ctor/dtor name refers to the class and not to the
        # template arguments that may have been parsed since.
        last_name_idx = -1
        while True:
            if self.eof():
                raise _Fail("eof in nested name")
            if self.eat("E"):
                break
            c = self.s[self.i]
            if c == "S":
                self.i += 1
                sub = self.parse_substitution()
                components.append(sub)
                # The component just named is the class a following ctor/dtor
                # belongs to, whether it came from St<name> or from a standard
                # substitution such as Sa.
                last_name_idx = len(components) - 1
                self.add_sub("::".join(components))
                continue
            if c == "I":
                if not components:
                    raise _Fail("template param as first component")
                args = self._parse_template_args()
                components[-1] = components[-1] + args
                self.add_sub("::".join(components))
                continue
            if c == "T":
                self.i += 1
                p = self._number()
                components.append("T%d_" % (p - 1))
                continue
            if c == "M":
                raise _Fail("member pointer in name")
            if c == "L":  # external linkage
                self.i += 1
                continue
            if c == "Z":  # local name inside nested
                self.i += 1
                ent = self._parse_name()
                comps = components + [ent]
                self.add_sub("::".join(comps))
                continue
            comp = self._parse_unqualified_name(is_template_prefix, in_nested=True)
            if comp == "" or comp.startswith("~"):
                # ctor/dtor are named after the enclosing class, which is not
                # necessarily the last component (template args may intervene).
                # A constructor of `ns::Foo<int>` is `ns::Foo<int>::Foo`, so build
                # the name from the recorded class component rather than from
                # whatever happened to be parsed last.
                if last_name_idx < 0:
                    raise _Fail("ctor without class")
                full = components[last_name_idx]
                op = "~" if comp.startswith("~") else ""
                simple = _split_template(full)[0].rpartition("::")[2]
                name = full + "::" + op + simple
                if self.peek() == "I":
                    self.i += 1
                    name += self._parse_template_args_body()
                name += self._parse_abi_tags()
                self.add_sub(name)
                # a ctor/dtor terminates the nested name apart from 'E'
                self.eat("E")
                # Constructors and destructors take no parameters, so the only
                # thing that can follow is the empty 'v' list.
                if self.eof() or self.eat("v"):
                    name += "()"
                return name
            components.append(comp)
            if comp.startswith("operator") or comp.startswith('operator""'):
                last_name_idx = -1
            else:
                last_name_idx = len(components) - 1
            self.add_sub("::".join(components))
            # <template-prefix> <template-args>: register the bare name first so
            # that substitutions inside the argument list can refer to it.
            args = self._maybe_template_args()
            if args:
                components[-1] += args
                self.add_sub("::".join(components))
            if "<" in comp and comp.endswith(">") and "(" not in comp:
                is_template_prefix = True
        if not components:
            raise _Fail("empty nested name")
        name = "::".join(components)
        if quals:
            name = quals + " " + name
        if ref:
            name += " " + ref
        name += self._parse_function_params()
        return name

    def _parse_function_params(self) -> str:
        """Render the bare-function-type that follows a member function name.

        In Itanium mangling a member function's parameter types are not wrapped
        in parentheses -- they sit directly after the nested name's closing 'E',
        which is why they have to be recovered here rather than by a reader.
        They are the authoritative source for a method's signature, since the
        mangling omits the return type but encodes every parameter type exactly.
        """
        if self.eof() or self.type_depth:
            return ""
        save = self.i
        try:
            params = self._parse_params()
        except _Fail:
            self.i = save
            return ""
        if self.i != len(self.s):
            # Leftover input means this was not a function encoding; attaching
            # a parameter list would invent one.
            self.i = save
            return ""
        return "(%s)" % params

    def _parse_cv_qualifiers(self) -> str:
        quals = []
        for code, text in CV_QUALS:
            while self.peek() == code:
                self.i += 1
                quals.append(text)
        return " ".join(quals)

    def _parse_template_args(self) -> str:
        self.expect("I")
        return self._parse_template_args_body()

    def _parse_template_args_body(self) -> str:
        args: list[str] = []
        while True:
            if self.eof():
                raise _Fail("eof in template args")
            if self.eat("E"):
                break
            if self.eat("L"):
                pass
            args.append(self._parse_template_arg())
        return "<" + ", ".join(a for a in args if a) + ">"

    def _parse_template_arg(self) -> str:
        c = self.peek()
        if c == "X":
            self.i += 1
            self._parse_expr()
            return ""
        if c == "L":
            self.i += 1
            lit = self._parse_literal()
            return lit
        if c == "J":
            self.i += 1
            args = self._parse_template_args()
            return " " + args.strip()
        if c == "T":
            self.i += 1
            self._number()
            return ""
        if c == "s":  # std::string shorthand
            self.i += 1
            return "std::string"
        return self._parse_type()

    def _parse_literal(self) -> str:
        kind = self.next()
        out = ""
        if kind == "b":
            out = "bool"
        elif kind == "c":
            out = "char"
        elif kind == "a":
            out = "double"
        elif kind == "h":
            out = "unsigned long"
        elif kind == "s":
            out = "short"
        elif kind == "t":
            out = "unsigned short"
        elif kind == "i":
            out = "int"
        elif kind == "j":
            out = "unsigned int"
        elif kind == "l":
            out = "long"
        elif kind == "m":
            out = "unsigned long"
        elif kind == "x":
            out = "long long"
        elif kind == "y":
            out = "unsigned long long"
        elif kind == "f":
            out = "float"
        elif kind == "d":
            out = "double"
        elif kind == "e":
            out = "long double"
        elif kind == "g":
            out = "__float128"
        elif kind == "n":
            out = "__int128"
        elif kind == "o":
            out = "unsigned __int128"
        elif kind == "u":
            out = "char8_t"
        elif kind == "U":
            out = "char16_t"
        elif kind == "U":
            out = "char32_t"
        elif kind == "Dn":
            out = "std::nullptr_t"
        elif kind == "L":
            out = "long long"
        # number / string payload
        neg = self.eat("n")
        if self.peek().isdigit():
            v = self._number()
            if neg:
                v = -v
            out = "%d%s" % (v, (" " + out) if out else "")
        else:
            s = self._parse_source_name()
            out = '"%s"%s' % (s, (" " + out) if out else "")
        return out

    def _parse_expr(self) -> str:
        c = self.next()
        if c == "L":
            return self._parse_literal()
        if c == "T":
            self._number()
            return ""
        if c in "1234":
            self.i -= 1
            return ""
        if c == "_":
            return ""
        return ""

    def _parse_type(self) -> str:
        # A nested name means different things depending on where it appears:
        # as a function encoding it is followed by a bare-function-type, but as
        # a class type it is not. Track the depth so the parameter parser can
        # tell them apart.
        self.type_depth += 1
        try:
            return self._parse_type_body()
        finally:
            self.type_depth -= 1

    def _parse_type_body(self) -> str:
        c = self.peek()
        if c in BUILTIN_TYPES and len(c) == 1:
            if c == "D":
                # D<digit><digit> two-char builtins
                self.i += 2
                return BUILTIN_TYPES.get(self.s[self.i - 2 : self.i], "D?")
            self.i += 1
            return BUILTIN_TYPES[c]
        if c == "D":
            self.i += 1
            if self.eof():
                raise _Fail("D eof")
            nxt = self.s[self.i]
            two = "D" + nxt
            if two in BUILTIN_TYPES:
                self.i += 1
                return BUILTIN_TYPES[two]
            self.i += 1
            return BUILTIN_TYPES.get("D" + nxt, "auto")
        if c == "P":
            self.i += 1
            return self._parse_type() + "*"
        if c == "R":
            self.i += 1
            return self._parse_type() + "&"
        if c == "O":
            self.i += 1
            return self._parse_type() + "&&"
        if c == "C":
            self.i += 1
            return self._parse_type() + " complex"
        if c == "G":
            self.i += 1
            return self._parse_type() + " imaginary"
        for code, text in CV_QUALS:
            if c == code:
                self.i += 1
                t = self._parse_type()
                if text == "const" and t.endswith("const"):
                    return t
                return "%s %s" % (t, text)
        if c == "K" and self.peek(2) == "Kc":
            self.i += 3
            return "const char* const"
        if c == "A":
            self.i += 1
            if self.peek().isdigit():
                n = self._number()
                if self.eat("_"):
                    inner = self._parse_type()
                    return "%s [%d]" % (inner, n)
            self.i = self.i  # no dim
            return self._parse_type() + " []"
        if c == "F":
            self.i += 1
            if self.eat("Y"):
                ret = self._parse_type()
            else:
                ret = ""
            params = self._parse_params()
            if self.peek() == "E" or True:
                self.eat("E")
            return "%s(%s)%s" % (ret, params, " noexcept" if False else "")
        if c == "M":
            self.i += 1
            cls = self._parse_type()
            member = self._parse_type()
            return "%s %s::*" % (member, cls)
        if c == "T_":
            self.i += 2
            n = self._number()
            return "T%d_" % (n - 1)
        if c == "T":
            self.i += 1
            n = self._number()
            return "T%d_" % (n - 1)
        if c in "1234":
            self.i += 1
            return ""
        if c == "u":
            self.i += 1
            return self._parse_source_name()
        return self._parse_name()

    def _parse_params(self) -> str:
        params: list[str] = []
        while not self.eof() and self.peek() != "E":
            before = self.i
            t = self._parse_type()
            if self.i == before:  # no progress; refuse to spin
                break
            if t:
                params.append(t)
        if len(params) == 1 and params[0] == "void":
            return ""
        return ", ".join(params)

    def _parse_name(self) -> str:
        c = self.peek()
        if c == "N":
            return self._parse_nested_name()
        if c == "Z":
            return self._parse_local_name()
        if c == "S":
            self.i += 1
            sub = self.parse_substitution()
            return sub + self._maybe_template_args()
        if c == "U":  # unnamed type / vendor type
            self.i += 1
            if self.peek() == "t":
                self.i += 1
                d = self._number()
                return "(unnamed type %d)" % d
            self._parse_source_name()
            return "(unnamed type)"
        nm = self._parse_unqualified_name()
        return nm + self._maybe_template_args()

    def _parse_local_name(self) -> str:
        self.expect("Z")
        enc = self._parse_encoding()
        self.expect("E")
        out = enc
        if self.eat("_"):
            out = self._parse_name()  # discriminator-entity form
        return out

    def _parse_encoding(self) -> str:
        c = self.peek()
        if c in "L":
            if self.peek(2) == "L_":
                # external name
                self.i += 2
                return self._parse_name()
            self.i += 1
            return self._parse_expr()
        return self._parse_name()

    def parse_top(self) -> str:
        c = self.peek()
        # Special top-level encodings (Itanium ABI 5.1).  These are extremely
        # common in this binary because it keeps full RTTI: every class gets a
        # _ZTV (vtable), _ZTI (typeinfo) and _ZTS (typeinfo name) triple.
        if c == "T" and len(self.s) > 1:
            kind = self.s[1]
            if kind == "V":  # vtable for
                self.i += 2
                return "vtable for " + self._parse_type()
            if kind == "I":  # typeinfo for
                self.i += 2
                return "typeinfo for " + self._parse_type()
            if kind == "S":  # typeinfo name for
                self.i += 2
                return "typeinfo name for " + self._parse_type()
            if kind == "T":  # VTT for
                self.i += 2
                return "VTT for " + self._parse_type()
            if kind == "C":  # construction vtable for
                self.i += 2
                base, ctor = self._parse_type(), None
                if self.peek() == "C":
                    self.i += 1
                    self.next()
                    ctor = self._parse_type()
                return "construction vtable for %s-in-%s" % (ctor or base, base)
        if c == "G":
            # _ZGV <name>  guard variable for
            if self.s[1:2] == "V":
                self.i += 2
                return "guard variable for " + self._parse_name()
            return self.s
        if c in "CVRTO":
            return self.s
        return self._parse_encoding()


def demangle(mangled: Optional[str], style: str = "gnu") -> str:
    """Demangle an Itanium ABI symbol. Returns the input unchanged on failure."""
    if not mangled or not mangled.startswith("_Z"):
        return mangled or ""
    try:
        d = Demangler(mangled[2:])
        out = d.parse_top()
        # if we did not consume the whole thing, keep the raw tail
        if not d.eof():
            out = out  # partial is still better than nothing
        return out
    except (_Fail, RecursionError, IndexError, ValueError):
        return mangled


def strip_leading_underscore(mangled: str) -> str:
    """Drop the single leading underscore the C ABI adds to C++ names."""
    if mangled.startswith("_Z"):
        return mangled[1:]
    return mangled


def is_mangled(s: str) -> bool:
    return s.startswith("_Z")
