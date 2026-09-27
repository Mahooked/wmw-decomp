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

# Expression operator encodings with their operand counts, mirroring GCC's
# cplus_demangle_operators table (cp-demangle.c): _parse_expr needs the arity
# to know how many subexpressions each operator consumes.  The display string
# is what d_print_expr_op appends verbatim, so spacing matters ("sizeof ",
# "delete[] ", "alignof ").
_EXPR_OPS = {
    "aN": ("&=", 2), "aS": ("=", 2), "aa": ("&&", 2), "ad": ("&", 1),
    "an": ("&", 2), "at": ("alignof ", 1), "aw": ("co_await ", 1),
    "az": ("alignof ", 1), "cc": ("const_cast", 2), "cl": ("()", 2),
    "cm": (",", 2), "co": ("~", 1), "dV": ("/=", 2), "dX": ("[...]", 3),
    "da": ("delete[] ", 1), "dc": ("dynamic_cast", 2), "de": ("*", 1),
    "di": ("=", 2), "dl": ("delete ", 1), "ds": (".*", 2), "dt": (".", 2),
    "dv": ("/", 2), "dx": ("]=", 2), "eO": ("^=", 2), "eo": ("^", 2),
    "eq": ("==", 2), "fL": ("...", 3), "fR": ("...", 3), "fl": ("...", 2),
    "fr": ("...", 2), "ge": (">=", 2), "gs": ("::", 1), "gt": (">", 2),
    "ix": ("[]", 2), "lS": ("<<=", 2), "le": ("<=", 2),
    "li": ('operator"" ', 1), "ls": ("<<", 2), "lt": ("<", 2),
    "mI": ("-=", 2), "mL": ("*=", 2), "mi": ("-", 2), "ml": ("*", 2),
    "mm": ("--", 1), "na": ("new[]", 3), "ne": ("!=", 2), "ng": ("-", 1),
    "nt": ("!", 1), "nw": ("new", 3), "nx": ("noexcept", 1),
    "oR": ("|=", 2), "oo": ("||", 2), "or": ("|", 2), "pL": ("+=", 2),
    "pl": ("+", 2), "pm": ("->*", 2), "pp": ("++", 1), "ps": ("+", 1),
    "pt": ("->", 2), "qu": ("?", 3), "rM": ("%=", 2), "rS": (">>=", 2),
    "rc": ("reinterpret_cast", 2), "rm": ("%", 2), "rs": (">>", 2),
    "sP": ("sizeof...", 1), "sZ": ("sizeof...", 1),
    "sc": ("static_cast", 2), "ss": ("<=>", 2), "st": ("sizeof ", 1),
    "sz": ("sizeof ", 1), "tr": ("throw", 0), "tw": ("throw ", 1),
}


def _operand(text: str, simple: bool) -> str:
    """Parenthesise an expression operand the way GCC's d_print_subexpr does:
    names and qualified names stand alone, everything else is wrapped."""
    return text if simple else "(%s)" % text


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
        # Parallel to targs: which index in each scope holds a ``J`` argument
        # pack, and the pack's elements.  GCC stores a pack as *one* template
        # argument (a TEMPLATE_ARGLIST node), so ``T<n>_`` numbering counts it
        # as a single slot -- the numbering here must agree.
        self.targ_packs: list[list[tuple[int, list[str]]]] = []
        # Which pack element a T-reference resolves to while a ``Dp`` pack
        # expansion is being rendered; 0 outside an expansion, exactly like
        # cp-demangle.c's dpi->pack_index.
        self.pack_index = 0
        self._pack_hit: Optional[list[str]] = None
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
        if c.isdigit() or ("A" <= c <= "Z"):
            # Itanium numbering is not what it looks like: 'S_' is the first
            # substitution, then 'S0_' the second, 'S1_' the third, so the
            # sequence-id is offset by one.  The sequence-id is base 36, with
            # A-Z as the digits after 0-9 -- libc++ reaches subs[11+] here, so
            # 'SA_' is the 12th entry and 'SB_' the 13th, not a bad token.
            num = 0
            while True:
                ch = self.s[self.i] if self.i < len(self.s) else ""
                if ch == "_":
                    self.i += 1
                    break
                if ch.isdigit():
                    digit = ord(ch) - 48
                elif "A" <= ch <= "Z":
                    digit = ord(ch) - 55
                else:
                    raise _Fail("bad substitution id %r" % ch)
                num = num * 36 + digit
                self.i += 1
            self.sub_is_reference = True
            return self._sub_at(num + 1)
        self.sub_is_reference = False
        if c == "t":
            # `St` introduces the std component; the name that follows is
            # folded into it, which is what the substitution indices in this
            # binary are built around.
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

    def _signed_number(self) -> int:
        """Parse ``<number>``, which is negative when prefixed with ``n``."""
        neg = self.eat("n")
        n = self._number()
        return -n if neg else n

    def _skip_call_offset(self, kind: str) -> None:
        """Skip a ``<call-offset>`` in front of a thunk's base encoding.

        ``h <nv-offset> _`` for a non-virtual thunk, or
        ``v <v-offset> _ <virtual-offset> _`` for a virtual one.  The offsets
        are not printed, but they have to be consumed to reach the base.
        """
        self._signed_number()
        self.expect("_")
        if kind == "v":
            self._signed_number()
            self.expect("_")

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
                components.append(self._template_param(self._compact_number()))
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
                    # The ctor/dtor is named after the class itself: strip only
                    # the last component's template arguments, then anything a
                    # `St`-folded component carries in front of the class name.
                    simple = _split_template(components[last_name_idx])[0]
                    simple = simple.rpartition("::")[2] or simple
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
        packs: list[tuple[int, list[str]]] = []
        args = self._parse_template_arglist(packs=packs)
        # The arguments name types for the rest of the enclosing template, so
        # make them visible to any T_ reference that follows.
        self.targs.append(args)
        self.targ_packs.append(packs)
        return "<" + ", ".join(a for a in args if a) + ">"

    def _parse_template_arglist(
        self, stop_before_e: bool = False, packs: Optional[list] = None
    ) -> list[str]:
        """Parse ``<template-arg>+``.

        Inside a ``J`` argument pack the arguments carry no ``I`` and no
        closing ``E`` of their own -- the pack's single ``E`` is the only
        terminator -- so ``stop_before_e`` leaves that ``E`` for the caller.

        A ``J`` pack becomes a single argument (its elements rendered
        comma-separated, so the visible output is unchanged) because GCC
        counts it as one slot in ``T<n>_`` numbering; ``packs`` records
        ``(index, elements)`` so ``Dp`` can later expand over the elements.
        """
        args: list[str] = []
        while True:
            if self.eof():
                raise _Fail("eof in template args")
            if self.peek() == "E":
                if not stop_before_e:
                    self.i += 1
                return args
            if self.peek() == "J":
                # <template-arg> ::= J <template-args> E is an argument pack.
                # GCC prints tuple<J[RK i]> as `tuple<int const&>` and
                # tuple<J[]> as `tuple<>`, so the elements join with ", ".
                self.i += 1
                elems = self._parse_template_arglist(stop_before_e=True)
                self.eat("E")
                if packs is not None:
                    packs.append((len(args), elems))
                args.append(", ".join(e for e in elems if e))
                continue
            # NB: a leading 'L' is not a separate marker here.  GCC routes
            # 'L' straight to d_expr_primary, which consumes the whole literal
            # (``Lb1_`` is the bool value true); swallowing the 'L' first would
            # leave ``b1_`` to be misread as the type `bool`.
            args.append(self._parse_template_arg())
        return args

    def _parse_template_arg(self) -> str:
        c = self.peek()
        if c == "X":
            # <template-arg> ::= X <expression> E -- the expression is the
            # rendered argument (enable_if<cond> needs the condition text),
            # and the E closing the X is this argument's own, not the
            # enclosing argument list's.
            self.i += 1
            text = self._parse_expr()
            self.expect("E")
            return text
        if c == "L":
            self.i += 1
            lit = self._parse_literal()
            return lit
        if c == "J":
            # Handled by _parse_template_arglist, which splices the pack into
            # the enclosing argument list instead of bracketing it.
            self.i += 1
            return self._parse_template_args_body()
        if c == "T":
            # d_template_arg's default case is cplus_demangle_type, so a
            # template-param used as an argument is registered as a
            # substitution candidate just like any other non-builtin type.
            self.i += 1
            return self.add_sub(self._template_param(self._compact_number()))
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
        return self._parse_expr_ex()[0]

    def _parse_expr_ex(self) -> tuple[str, bool]:
        """Parse an Itanium <expression> (ABI 5.1.1, GCC d_expression_1).

        Returns ``(text, simple)``.  ``simple`` marks the renderings GCC's
        d_print_subexpr leaves unparenthesised (unqualified and qualified
        names); every other operand gets wrapped in parentheses exactly as
        cp-demangle.c does.
        """
        if self.eof():
            raise _Fail("eof in expression")
        c = self.peek()
        if c == "L":
            self.i += 1
            return self._parse_literal(), False
        if c == "T":
            self.i += 1
            return self._template_param(self._compact_number()), False
        if self.peek(2) == "sr":
            return self._parse_unresolved_name()
        if self.peek(2) == "sp":
            # PACK_EXPANSION in an expression: the pack elements print
            # comma-separated, like the Dp expansion of a template argument.
            self.i += 2
            return self._parse_expr_ex()
        if self.peek(2) == "fp":
            # Function parameter used in a late-specified return type.
            self.i += 2
            if self.eat("T"):
                return "this", True
            index = self._number() + 1
            return "param %d" % index, True
        if c.isdigit():
            # A bare name used as an expression, e.g. a dependent call.
            nm = self._parse_unqualified_name()
            if self.peek() == "I":
                self.i += 1
                return nm + self._parse_template_args_body(), False
            return nm, True
        if self.peek(2) == "on":
            # operator-function-id: `on` followed by the operator code.
            self.i += 2
            nm = self._parse_unqualified_name()
            if self.peek() == "I":
                self.i += 1
                return nm + self._parse_template_args_body(), False
            return nm, True
        if self.peek(2) in ("il", "tl"):
            two = self.peek(2)
            self.i += 2
            typ = self._parse_type() if two == "tl" else ""
            items = []
            while not self.eof() and self.peek() != "E":
                items.append(self._parse_expr())
                if not self.eat(","):
                    break
            self.expect("E")
            body = "{%s}" % ", ".join(items)
            return (typ + body if typ else body), True
        if c == "u":
            # vendor extended expression: u <source-name> <template-arg>* E
            self.i += 1
            nm = self._parse_source_name()
            items = self._parse_template_arglist()
            if items:
                return nm + "<" + ", ".join(a for a in items if a) + ">", False
            return nm, False
        two = self.peek(2)
        if two == "cv":
            # cast: (type) operand; the `_` form carries an expression list
            self.i += 2
            typ = self._parse_type()
            if self.eat("_"):
                items = self._parse_exprlist("E")
                return "(%s)(%s)" % (typ, ", ".join(items)), False
            operand, simple = self._parse_expr_ex()
            return "(%s)%s" % (typ, _operand(operand, simple)), False
        if len(two) == 2 and two[0] == "v" and two[1].isdigit():
            # vendor extended operator: v <digit-arity> <source-name>
            arity = int(two[1])
            self.i += 2
            nm = self._parse_source_name()
            return self._finish_expr_op("v?", "operator " + nm, arity), False
        if two in _EXPR_OPS:
            op, arity = _EXPR_OPS[two]
            self.i += 2
            return self._finish_expr_op(two, op, arity), False
        # Anything we do not recognise: consume a character and mark the gap
        # so a triage diff shows it, while guaranteeing forward progress.
        self.next()
        return "?", False

    def _parse_expr_op_code(self) -> str:
        """Fold expressions embed a second operator code before their
        operands (``fl <binary operator-name> <expression>``)."""
        two = self.peek(2)
        if two in _EXPR_OPS:
            self.i += 2
            return _EXPR_OPS[two][0]
        raise _Fail("bad fold operator %r" % two)

    def _finish_expr_op(self, code: str, op: str, arity: int) -> str:
        """Parse an operator's operands and render it, following GCC's
        printing rules for unary/binary/ternary expressions."""
        if arity == 0:
            return op
        if arity == 1:
            if code in ("st", "sz", "at", "az"):
                # sizeof(T)/alignof(T): the operand is a type, but a
                # template-param (T_) arrives through the expression grammar.
                if self.peek() == "T":
                    operand, _ = self._parse_expr_ex()
                else:
                    operand = self._parse_type()
                return "%s(%s)" % (op, operand)
            if code == "sZ":
                # sizeof...(T): GCC replaces the whole expression with the
                # pack's length.
                self._pack_hit = None
                operand, _ = self._parse_expr_ex()
                if self._pack_hit is not None:
                    return str(len(self._pack_hit))
                return operand
            if code == "sP":
                # sizeof...(args): GCC prints the argument count.
                return str(len(self._parse_template_arglist()))
            if code == "nx":
                operand, _ = self._parse_expr_ex()
                return "%s(%s)" % (op, operand)
            if code in ("pp", "mm"):
                # An underscore right after the code is the prefix form
                # (``pp_ <expression>`` in the ABI); without it GCC renders
                # the postfix form.
                prefix = self.eat("_")
                operand, simple = self._parse_expr_ex()
                if prefix:
                    return op + _operand(operand, simple)
                return _operand(operand, simple) + op
            if code == "gs":
                # No parentheses after the scope operator.
                operand, _ = self._parse_expr_ex()
                return "::" + operand
            operand, simple = self._parse_expr_ex()
            return op + _operand(operand, simple)
        if arity == 2:
            if code == "cl":
                # cl <expression>+ E: a call; the parentheses come from the
                # argument list itself.
                callee, simple = self._parse_expr_ex()
                args = self._parse_exprlist("E")
                return "%s(%s)" % (_operand(callee, simple), ", ".join(args))
            if code == "ix":
                left, ls = self._parse_expr_ex()
                right, rs = self._parse_expr_ex()
                return "%s[%s]" % (_operand(left, ls), _operand(right, rs))
            if code in ("fl", "fr"):
                # unary folds: (... op expr) and (expr op ...)
                inner = self._parse_expr_op_code()
                operand, _ = self._parse_expr_ex()
                if code == "fl":
                    return "(... %s %s)" % (inner, operand)
                return "(%s %s ...)" % (operand, inner)
            left, ls = self._parse_expr_ex()
            right, rs = self._parse_expr_ex()
            return "%s%s%s" % (_operand(left, ls), op, _operand(right, rs))
        # arity == 3
        if code == "qu":
            first, fs = self._parse_expr_ex()
            second, ss = self._parse_expr_ex()
            third, ts = self._parse_expr_ex()
            return "%s?%s:%s" % (_operand(first, fs), _operand(second, ss),
                                 _operand(third, ts))
        if code in ("nw", "na"):
            # [gs] nw <expression>* _ <type> E  (or a trailing initializer)
            self._parse_exprlist("_")
            typ = self._parse_type()
            if self.peek() == "E":
                self.i += 1
            elif self.peek(2) in ("il", "tl"):
                self._parse_expr()
            return "%s %s" % (op, typ)
        if code == "dX":
            # designated range: [begin ... end] = expr
            first, _ = self._parse_expr_ex()
            second, _ = self._parse_expr_ex()
            third, _ = self._parse_expr_ex()
            return "[%s ... %s]=%s" % (first, second, third)
        if code in ("fL", "fR"):
            # binary folds: (expr op ... op expr)
            inner = self._parse_expr_op_code()
            left, _ = self._parse_expr_ex()
            right, _ = self._parse_expr_ex()
            return "(%s %s ... %s %s)" % (left, inner, inner, right)
        return op

    def _parse_exprlist(self, term: str) -> list[str]:
        """Parse comma-separated expressions up to and including ``term``
        (GCC's d_exprlist)."""
        items: list[str] = []
        while True:
            if self.eof():
                raise _Fail("eof in expression list")
            if self.peek() == term:
                self.i += 1
                return items
            items.append(self._parse_expr())
            if self.peek() == term:
                continue
            if not self.eat(","):
                raise _Fail("expected %r in expression list" % term)

    def _parse_unresolved_name(self) -> tuple[str, bool]:
        """<unresolved-name> ::= [gs] sr <unresolved-type> <base-unresolved-name>

        GCC's d_unresolved_name.  Returns (text, simple).
        """
        if self.peek(2) == "gs":
            self.i += 2
            if self.peek(2) != "sr":
                raise _Fail("gs without sr")
            self.i += 2
            text, simple = self._parse_unresolved_body()
            return "::" + text, simple
        if self.peek(2) != "sr":
            raise _Fail("expected sr at %d" % self.i)
        self.i += 2
        return self._parse_unresolved_body()

    def _parse_unresolved_body(self) -> tuple[str, bool]:
        if self.eof():
            raise _Fail("eof after sr")
        c = self.peek()
        if c.isdigit() or (c != "" and c.islower()) or c in ("C", "U", "L"):
            # The old syntax (sr1A1x) and the new one (sr1AE1x) share a
            # prefix; GCC parses d_prefix and then swallows the separating
            # 'E' when present.
            prefix = self._parse_sr_prefix()
            self.eat("E")
        else:
            prefix = self._parse_type()
        base = self._parse_unqualified_name()
        text = "%s::%s" % (prefix, base)
        if self.peek() == "I":
            self.i += 1
            return text + self._parse_template_args_body(), False
        return text, True

    def _parse_sr_prefix(self) -> str:
        """GCC's d_prefix with substable=0: a chain of unqualified names,
        substitutions and template arguments terminated by 'E'."""
        ret = ""
        while True:
            c = self.peek()
            if c == "":
                raise _Fail("eof in sr prefix")
            if c == "D" and self.peek(2) in ("DT", "Dt"):
                # decltype in the prefix position
                ret = self._parse_type()
            elif c == "I":
                if not ret:
                    raise _Fail("template args without prefix")
                self.i += 1
                ret = ret + self._parse_template_args_body()
            elif c == "T":
                if ret:
                    raise _Fail("template param inside sr prefix")
                self.i += 1
                ret = self._template_param(self._compact_number())
            elif c == "M":
                # lambda scope marker: consume and continue
                self.i += 1
                continue
            elif c == "S":
                self.i += 1
                ret = self.parse_substitution()
                # GCC `continue`s here, skipping the E check; a following E
                # ends the prefix on the next iteration instead.
                continue
            elif c in ("E", "I"):
                break
            else:
                if not (c.isdigit() or c in ("C", "D") or c.islower()):
                    break
                part = self._parse_unqualified_name()
                ret = "%s::%s" % (ret, part) if ret else part
            if self.peek() == "E":
                break
        if not ret:
            raise _Fail("empty sr prefix")
        return ret

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
            del self.targ_packs[mark:]

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

    def _compact_number(self) -> int:
        """Decode GCC's ``d_compact_number``: ``_`` is 0 and ``N`` means N+1.

        This is why ``T_`` and ``T0_`` name *different* parameters.  For
        ``operator+<char, char_traits<char>, allocator<char>>`` the first
        argument is written ``T_``, the second ``T0_`` and the third ``T1_``.
        """
        if self.eat("_"):
            return 0
        if self.eat("n"):
            raise _Fail("negative template param")
        n = self._number()
        if not self.eat("_"):
            raise _Fail("bad template param")
        return n + 1

    def _template_param(self, index: int) -> str:
        """Resolve ``T_``/``T<n>_`` against the enclosing template arguments.

        A parameter type is written in terms of the template's own arguments
        (``...__push_back_slow_pathIRKS2_EEvOT_`` is
        ``void vector<...>::__push_back_slow_path<T>(T&&)``), so the arguments
        have to be in scope while the signature is rendered.

        An argument that is a ``J`` pack is one slot (as in GCC's numbering);
        resolving it yields element ``pack_index`` of the pack -- element 0
        outside an expansion, the current element during a ``Dp`` expansion.
        """
        for si in range(len(self.targs) - 1, -1, -1):
            scope = self.targs[si]
            if 0 <= index < len(scope):
                for start, elems in self.targ_packs[si]:
                    if start == index:
                        # First pack the pattern touches: that is the pack
                        # cp-demangle.c's d_find_pack would expand over.
                        if self._pack_hit is None:
                            self._pack_hit = elems
                        if not elems:
                            return ""
                        k = self.pack_index
                        if not 0 <= k < len(elems):
                            k = 0
                        return elems[k]
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
            if nxt == "p":
                # <type> ::= Dp <type> -- a pack expansion.  cp-demangle.c
                # finds the argument pack the pattern references and prints
                # the pattern once per element with dpi->pack_index = i, so
                # `RKT_DpOT0_` over a three-element pack yields four
                # parameters, with reference collapsing applied per element
                # (``X const& &&`` collapses back to ``X const&``).
                self.i += 1
                pre = list(self.subs)
                save = self.i
                hold_idx = self.pack_index
                prior_hit = self._pack_hit
                self._pack_hit = None
                pat = self._parse_type()
                hit = self._pack_hit
                self._pack_hit = prior_hit
                if hit is None:
                    # No argument pack in the pattern: print it as it stands.
                    return pat
                keep = list(self.subs)
                end = self.i
                out = []
                for k in range(len(hit)):
                    self.i = save
                    self.subs[:] = pre
                    self.pack_index = k
                    self._pack_hit = None
                    out.append(self._parse_type())
                self.subs[:] = keep
                self.i = end
                self.pack_index = hold_idx
                self._pack_hit = prior_hit
                return ", ".join(out)
            two = "D" + nxt
            if two in BUILTIN_TYPES:
                self.i += 1
                return BUILTIN_TYPES[two]
            self.i += 1
            return BUILTIN_TYPES.get("D" + nxt, "auto")
        if c == "P":
            self.i += 1
            if self.peek() == "F":
                # A pointer to a function type carries its '*' inside the
                # parentheses: `PFvPvE` is `void (*)(void*)`, not
                # `void (void*)*`.
                return self.add_sub(self._parse_fnptr())
            return self.add_sub(self._parse_type() + "*")
        if c == "R":
            self.i += 1
            if self.peek(2) == "PF":
                # A reference to a function pointer renders the & inside the
                # parentheses: `RP F...E` is `RET (*&)(params)`, not
                # `RET (*)(params)&`.
                self.i += 1  # the 'P'; GCC registers pointer then reference
                return self.add_sub(self._parse_fnptr("&"))
            return self.add_sub(self._collapse_ref(self._parse_type(), "&"))
        if c == "O":
            self.i += 1
            if self.peek(2) == "PF":
                self.i += 1
                return self.add_sub(self._parse_fnptr("&&"))
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
            # <function-type> ::= F [Y] <bare-function-type> E.  Without the
            # 'Y' the first type of the bare-function-type *is* the return
            # type, so `FvPvE` is `void (void*)` rather than `(void, void*)`.
            self.i += 1
            ret, params = self._parse_fn_sig()
            # GCC's can_subst stays set for 'F', so the completed function
            # type is a substitution candidate; skipping it shifted every
            # later S<n>_ index (how S9_ lost __sort's parameter list).
            return self.add_sub("%s (%s)" % (ret, params))
        if c == "M":
            self.i += 1
            cls = self._parse_type()
            member = self._parse_type()
            return "%s %s::*" % (member, cls)
        if c == "T":
            # <template-param> ::= T_ | T <parameter-2 non-negative number> _
            # A template-param reached as a <type> leaves cplus_demangle_type's
            # can_subst set, so it is registered like any other non-builtin type
            # -- that is what puts basic_string's three arguments at indices
            # 7-9 and the completed basic_string at 10.
            self.i += 1
            return self.add_sub(self._template_param(self._compact_number()))
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

    def _parse_fn_sig(self) -> tuple[str, str]:
        """Parse ``[Y] <bare-function-type> E``, returning ``(ret, params)``.

        Without the ``Y`` the first type of the bare-function-type is the
        return type, which is why ``FvPvE`` is ``void (void*)`` and not
        ``(void, void*)``.
        """
        self.eat("Y")
        ret = "" if self.eof() or self.peek() == "E" else self._parse_type()
        params = self._parse_params()
        self.eat("E")
        return ret, params

    def _parse_fnptr(self, ref: str = "") -> str:
        """Parse a ``P F ... E`` pointer-to-function as ``RET (*)(params)``.

        GCC registers three substitutions for ``RPF...E`` — the function type,
        the pointer, and the reference — in that order, so a missing entry here
        shifts every later ``S<n>_`` index.
        """
        self.expect("F")
        ret, params = self._parse_fn_sig()
        self.add_sub("%s (%s)" % (ret, params))
        if ref:
            # R/O consumed the 'P', so the pointer substitution is ours too.
            self.add_sub("%s (*)(%s)" % (ret, params))
            return "%s (*%s)(%s)" % (ret, ref, params)
        return "%s (*)(%s)" % (ret, params)

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
            name = sub + self._maybe_template_args()
            if is_function:
                # A substitution-rooted encoding still carries its
                # bare-function-type: `_ZSt18uncaught_exceptionv` ends in the
                # `v` for its empty parameter list.
                ret, params = self._parse_function_params()
                if ret:
                    name = ret + " " + name
                name += params
            return name
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
            if kind in "hv":  # thunk to
                # T <call-offset> <base encoding>.  This binary is full of
                # them: every virtual destructor and overriding method gets a
                # non-virtual (and often a virtual) thunk.
                self.i += 2
                label = "virtual" if kind == "v" else "non-virtual"
                self._skip_call_offset(kind)
                return "%s thunk to %s" % (label, self._parse_encoding())
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
