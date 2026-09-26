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
    "Dn": "decltype(nullptr)",
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
    """Split ``ns::Foo<int>::bar`` into ``("ns::Foo", "<int>")``.

    Finds the ``<`` that opens the top-level argument list and the matching
    ``>``, tracking nesting so that a nested ``char_traits<char>`` does not end
    the search early -- and so that trailing ``::member`` is left out.
    """
    depth = 0
    start = -1
    for idx, ch in enumerate(name):
        if ch == "<":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == ">":
            depth -= 1
            if depth <= 0:
                if start < 0:
                    return name, ""
                return name[:start], name[start : idx + 1]
    return name, ""


# Print styles, mirroring the d_builtin_type_print enum in cp-demangle.c.
_D_DEFAULT = 0
_D_FLOAT = 1
_D_INT = 2
_D_UNSIGNED = 3
_D_LONG = 4
_D_UNSIGNED_LONG = 5
_D_LONG_LONG = 6
_D_UNSIGNED_LONG_LONG = 7
_D_VOID = 8
_D_BOOL = 9

# GCC prints an integral <literal> template-argument bare, with just the width
# suffix (cplus_demangle_builtin_types' d_builtin_type_print column).
_NUMERIC_SUFFIXES = {
    _D_INT: "",
    _D_UNSIGNED: "u",
    _D_LONG: "l",
    _D_UNSIGNED_LONG: "ul",
    _D_LONG_LONG: "ll",
    _D_UNSIGNED_LONG_LONG: "ull",
}

# cplus_demangle_builtin_types, verbatim.  Note 'a' is signed char and 'h' is
# unsigned char -- both are easy to mistake for float types.
_BUILTIN_TYPES = {
    "a": ("signed char", _D_DEFAULT),
    "b": ("bool", _D_BOOL),
    "c": ("char", _D_DEFAULT),
    "d": ("double", _D_FLOAT),
    "e": ("long double", _D_FLOAT),
    "f": ("float", _D_FLOAT),
    "g": ("__float128", _D_FLOAT),
    "h": ("unsigned char", _D_DEFAULT),
    "i": ("int", _D_INT),
    "j": ("unsigned int", _D_UNSIGNED),
    "l": ("long", _D_LONG),
    "m": ("unsigned long", _D_UNSIGNED_LONG),
    "n": ("__int128", _D_DEFAULT),
    "o": ("unsigned __int128", _D_DEFAULT),
    "s": ("short", _D_DEFAULT),
    "t": ("unsigned short", _D_DEFAULT),
    "u": ("char8_t", _D_DEFAULT),
    "U": ("char16_t", _D_DEFAULT),
    "V": ("char32_t", _D_DEFAULT),
    "v": ("void", _D_VOID),
    "w": ("wchar_t", _D_DEFAULT),
    "x": ("long long", _D_LONG_LONG),
    "y": ("unsigned long long", _D_UNSIGNED_LONG_LONG),
    "z": ("...", _D_DEFAULT),
}


class Demangler:
    def __init__(self, s: str):
        self.s = s
        self.i = 0
        self.subs: list[str] = []
        self.sub_is_reference = False
        self.name_is_template = False
        self.targs: list[list[str]] = []
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
        """Resolve an ``S...`` substitution.

        Sets :attr:`sub_is_reference` to say whether this read an *existing*
        table entry (``S_``/``S<n>_``) or introduced a new component via a
        standard substitution (``St``/``Sa``/...).  GCC's ``d_prefix`` only
        registers the latter, because the former is already in the table and
        re-adding it would shift every later index.
        """
        # caller has consumed 'S'
        if self.eof():
            raise _Fail("eof in substitution")
        c = self.s[self.i]
        if c == "_":
            self.i += 1
            self.sub_is_reference = True
            return self._sub_at(0)
        if c.isdigit():
            num = self._number()
            if not self.eat("_"):
                raise _Fail("bad substitution")
            # Itanium numbering is not what it looks like: 'S_' is the first
            # substitution, then 'S0_' is the second, 'S1_' the third, so a
            # numeric seq-id is offset by one.
            self.sub_is_reference = True
            return self._sub_at(num + 1)
        self.sub_is_reference = False
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
        # <operator-name> codes are two characters ("aS" is operator=, "ls" is
        # operator<<), so the table has to be probed with both.
        two = self.s[self.i - 1 : self.i + 1]
        if two in OPERATORS:
            self.i += 1
            op = OPERATORS[two]
            if two == "cv":
                t = self._parse_type()
                return "operator " + t
            if two == "li":
                s = self._parse_source_name()
                return 'operator""' + s
            if two == "v":
                d = self._number()
                return "operator __vector(%d)" % d
            return "operator" + op
        if c in OPERATORS:
            op = OPERATORS[c]
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

    def _parse_nested_name(self, is_function: bool = False) -> str:
        """Parse ``N [<CV-qualifiers>] [<ref-qualifier>] <prefix> <unqualified-name> E``.

        The substitution bookkeeping mirrors GCC's ``d_prefix``
        (GPL/DemanglerGnu/src/demangler_gnu_*/c/cp-demangle.c), which is the
        authority for this binary.  Two rules there are easy to get wrong and
        both shift every later index:

        * a component is registered only if the next character is *not* ``E``
          -- the component immediately before ``E`` is the trailing
          <unqualified-name> and is never a substitution, and
        * a component that was itself *read from* the table (``S_``/``S<n>_``)
          is skipped via ``continue`` and not re-registered, while a standard
          substitution (``St``, ``Sa``, ...) does introduce a new component.
        """
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
        ctor_name: Optional[str] = None
        while True:
            if self.eof():
                raise _Fail("eof in nested name")
            if self.eat("E"):
                break
            c = self.s[self.i]
            from_sub = False
            if c == "S":
                self.i += 1
                sub = self.parse_substitution()
                components.append(sub)
                from_sub = self.sub_is_reference
                # The component just named is the class a following ctor/dtor
                # belongs to, whether it came from St<name> or from a standard
                # substitution such as Sa.
                last_name_idx = len(components) - 1
            elif c == "I":
                if not components:
                    raise _Fail("template param as first component")
                args = self._parse_template_args()
                components[-1] = components[-1] + args
            elif c == "T":
                self.i += 1
                p = self._number()
                components.append("T%d_" % (p - 1))
                last_name_idx = len(components) - 1
            elif c == "M":
                raise _Fail("member pointer in name")
            elif c == "L":  # external linkage
                self.i += 1
                continue
            elif c == "Z":  # local name inside nested
                self.i += 1
                ent = self._parse_name()
                components.append(ent)
                last_name_idx = len(components) - 1
            else:
                comp = self._parse_unqualified_name(is_template_prefix, in_nested=True)
                if comp == "" or comp.startswith("~"):
                    # A ctor/dtor is named after the enclosing class, which is
                    # not necessarily the last component (template args may
                    # intervene).  The qualifier is the whole enclosing scope, so
                    # every component up to the class name is kept; only the
                    # trailing `~Foo` part is unqualified.
                    if last_name_idx < 0:
                        raise _Fail("ctor without class")
                    full = "::".join(components[: last_name_idx + 1])
                    op = "~" if comp.startswith("~") else ""
                    simple = _split_template(full)[0].rpartition("::")[2]
                    ctor_name = full + "::" + op + simple
                    if self.peek() == "I":
                        self.i += 1
                        ctor_name += self._parse_template_args_body()
                    ctor_name += self._parse_abi_tags()
                    # A ctor/dtor terminates the nested name apart from 'E' and,
                    # being the trailing <unqualified-name>, is not registered.
                    self.eat("E")
                    if self.eof():
                        return ctor_name + "()"
                    break
                components.append(comp)
                if comp.startswith("operator") or comp.startswith('operator""'):
                    last_name_idx = -1
                else:
                    last_name_idx = len(components) - 1
                if self.peek() == "I":
                    # A bare <unscoped-template-name> is a substitution
                    # candidate in its own right: it is entered before the
                    # arguments are parsed, so an ``S<n>_`` inside them can
                    # refer back to it.
                    self.add_sub("::".join(components))
                args = self._maybe_template_args()
                if args:
                    components[-1] += args
                    # The trailing <unqualified-name> carried <template-args>, so
                    # this is a function template instantiation.  Those encode
                    # their return type ahead of the parameter list; a plain
                    # function does not.
                    self.name_is_template = True
                else:
                    self.name_is_template = False
                if "<" in comp and comp.endswith(">") and "(" not in comp:
                    is_template_prefix = True
            if self.peek() == "E":
                # The component before 'E' is the trailing <unqualified-name>,
                # which d_prefix never registers.  In a *type* context the
                # completed type is still a substitution candidate (GCC's
                # `can_subst` check at the end of cplus_demangle_type), so it is
                # registered here instead.
                if not is_function and not from_sub:
                    self.add_sub("::".join(components))
                self.i += 1  # consume the 'E' that closed the nested name
                break
            if not from_sub:
                self.add_sub("::".join(components))
        if ctor_name is not None:
            name = ctor_name
            self.name_is_template = False
        else:
            if not components:
                raise _Fail("empty nested name")
            name = "::".join(components)
        if quals:
            tail = quals
        else:
            tail = ""
        if ref:
            tail = (tail + " " + ref).strip()
        ret, params = self._parse_function_params()
        if ret:
            name = ret + " " + name
        name += params
        if tail:
            # CV-/ref-qualifiers trail the parameter list: `Foo::bar(int) const`.
            name += " " + tail
        return name

    def _parse_function_params(self) -> tuple[str, str]:
        """Render the bare-function-type that follows a member function name.

        Returns ``(return_type, "(params)")``.  The return type is non-empty
        only for function *template* instantiations, which encode it ahead of
        the parameter list (``...barIiEEvOT_`` is ``void Foo::bar<int>(int&&)``)
        because it cannot be deduced from the arguments.

        In Itanium mangling a member function's parameter types are not wrapped
        in parentheses -- they sit directly after the nested name's closing 'E',
        which is why they have to be recovered here rather than by a reader.
        They are the authoritative source for a method's signature, since the
        mangling omits the return type but encodes every parameter type exactly.
        """
        if self.eof() or self.type_depth:
            return "", ""
        save = self.i
        save_subs = len(self.subs)
        ret = ""
        try:
            if self.name_is_template:
                # A template instantiation must carry its return type; GCC
                # rejects the encoding outright when it is missing, so a failure
                # here has to propagate rather than be silently dropped.
                ret = self._parse_type()
            params = self._parse_params()
        except _Fail:
            self.i = save
            del self.subs[save_subs:]
            return "", ""
        if self.i != len(self.s):
            # Leftover input means this was not a function encoding; attaching
            # a parameter list would invent one.
            self.i = save
            del self.subs[save_subs:]
            return "", ""
        return ret, "(%s)" % params

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
            # NB: a leading 'L' is not a separate marker here.  GCC routes
            # 'L' straight to d_expr_primary, which consumes the whole literal
            # (``Lb1_`` is the bool value true); swallowing the 'L' first would
            # leave ``b1_`` to be misread as the type `bool`.
            args.append(self._parse_template_arg())
        # The arguments name types for the rest of the enclosing template, so
        # make them visible to any T_ reference that follows.
        self.targs.append(args)
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
        name, style = _BUILTIN_TYPES.get(kind, ("", _D_DEFAULT))
        # decltype(nullptr) is a builtin with no value payload: d_expr_primary
        # returns the type as-is when the literal is immediately closed.
        if kind == "D" and self.peek() == "n":
            self.i += 1
            self.eat("E")
            return BUILTIN_TYPES["Dn"]
        neg = self.eat("n")
        is_number = self.peek().isdigit()
        value = str(self._number()) if is_number else self._parse_source_name()
        # d_expr_primary ends with d_check_char(di, 'E'); the '_' terminator of
        # the bare <literal> production is not used inside a <template-arg>.
        if not self.eat("E"):
            self.eat("_")
        if style in _NUMERIC_SUFFIXES:
            # GCC prints integral literals bare, with only the width suffix, so
            # that Foo<10u> stays a non-type template argument.
            if style == _D_BOOL:
                return "false" if (neg or value == "0") else "true"
            return "%s%s%s" % ("-" if neg else "", value, _NUMERIC_SUFFIXES[style])
        if style == _D_BOOL:
            return "false" if (neg or value == "0") else "true"
        # Everything else keeps the type, parenthesised, as in Foo<(char)97>.
        out = "(%s)" % name if name else ""
        if style == _D_FLOAT:
            return out
        return "%s%s%s" % (out, "-" if neg else "", value)

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
        mark = len(self.targs)
        try:
            return self._parse_type_body()
        finally:
            self.type_depth -= 1
            # Template arguments only name types inside the template that
            # introduced them.
            del self.targs[mark:]

    @staticmethod
    def _collapse_ref(base: str, op: str) -> str:
        """Apply C++ reference collapsing to a rendered reference type.

        A <template-param> can itself resolve to a reference -- ``O T_`` in
        ``vector<T>::__push_back_slow_path(T)`` is an rvalue reference to a
        parameter already declared ``T const&``.  Collapsing turns ``X& &&``
        back into ``X&``, which is the type the source actually has.
        """
        if base.endswith("&&"):
            return base[:-2] + ("&" if op == "&" else "&&")
        if base.endswith("&"):
            return base[:-1] + "&"
        return base + op

    def _template_param(self, index: int) -> str:
        """Resolve ``T_``/``T<n>_`` against the enclosing template arguments.

        A parameter type is written in terms of the template's own arguments
        (``...__push_back_slow_pathIRKS2_EEvOT_`` is
        ``void vector<...>::__push_back_slow_path<T>(T&&)``), so the arguments
        have to be in scope while the signature is rendered.
        """
        for scope in reversed(self.targs):
            if 0 <= index < len(scope):
                return scope[index]
        return "T%d_" % index

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
            return self.add_sub(self._parse_type() + "*")
        if c == "R":
            self.i += 1
            return self.add_sub(self._collapse_ref(self._parse_type(), "&"))
        if c == "O":
            self.i += 1
            return self.add_sub(self._collapse_ref(self._parse_type(), "&&"))
        if c == "C":
            self.i += 1
            return self.add_sub(self._parse_type() + " complex")
        if c == "G":
            self.i += 1
            return self.add_sub(self._parse_type() + " imaginary")
        for code, text in CV_QUALS:
            if c == code:
                self.i += 1
                t = self._parse_type()
                if text == "const" and t.endswith("const"):
                    return t
                return self.add_sub("%s %s" % (t, text))
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
        if c == "T":
            # <template-param> ::= T_ | T <parameter-2 non-negative number> _
            self.i += 1
            if self.eat("_"):
                return self._template_param(0)
            n = self._number()
            if not self.eat("_"):
                raise _Fail("bad template param")
            return self._template_param(n)
        if c == "u":
            self.i += 1
            return self._parse_source_name()
        if c.isdigit():
            # <class-enum-type> ::= <name>, and an unscoped <name> starts with a
            # <source-name>, i.e. a length.  GCC reaches these through
            # d_class_enum_type -> d_name, whose trailing check registers the
            # completed name (cp-demangle.c:1535).  Types spelled as a nested
            # name or a substitution are already registered by their own path.
            return self.add_sub(self._parse_name())
        return self._parse_name()

    def _parse_params(self) -> str:
        """Parse a bare-function-type.

        Parameter types are *not* registered here: they are ordinary <type>s and
        ``_parse_type_body`` already enters each non-builtin one into the
        substitution table, exactly where GCC's ``can_subst`` check in
        ``cplus_demangle_type`` does.  Registering again would shift every
        later index, which is how ``...EP8_jobjectP10_jmethodID`` used to lose
        its whole parameter list.
        """
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

    def _parse_name(self, is_function: bool = False) -> str:
        c = self.peek()
        if c == "N":
            return self._parse_nested_name(is_function)
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
        args = self._maybe_template_args()
        name = nm + args
        self.name_is_template = bool(args)
        if is_function:
            # GCC's d_encoding parses the bare-function-type after *any* <name>,
            # not just a nested one, so an unqualified `fPKcj` still yields its
            # parameter list.
            ret, params = self._parse_function_params()
            if ret:
                name = ret + " " + name
            name += params
        return name

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
                return self._parse_name(is_function=True)
            self.i += 1
            return self._parse_expr()
        # An <encoding> is a function: its nested name is followed by a
        # bare-function-type rather than being a type in its own right.
        return self._parse_name(is_function=True)

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
