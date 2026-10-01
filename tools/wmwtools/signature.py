"""Exact C++ prototypes for mangled symbols, recovered from the mangling.

GCC's demangled rendering already *contains* the exact parameter types -- the
Itanium ABI encodes every parameter type in the symbol, and
:func:`cxxfilt.demangle` prints it faithfully.  What it does not give us is
anything Ghidra can consume: the decompiler works from ``DataType`` objects, so
without help it infers ``undefined8 *param_1`` for everything.

This module re-parses the mangling to recover the parameter list as a list of
individual types, which is what a prototype needs.  It deliberately reuses
``cxxfilt``'s parser rather than re-encoding the grammar: ``_parse_params``
already walks a bare-function-type one ``<type>`` at a time, so subclassing it
to record each top-level type gives exact types with no second grammar to keep
in sync.  ``tools/test_sigs.py`` checks the result against GCC's own rendering
for all 6,769 C++ symbols in this binary.

Two ABI details worth knowing:

- The return type is *not* encoded for a non-template function, so it cannot be
  recovered here.  Ghidra's inference has to stand, and this module reports an
  empty return type rather than inventing one.
- A thunk (``_ZTh``/``_ZTv``/``_ZTc``) encodes a call offset and then the
  *target* encoding.  The thunk's real parameters are the target's, so the
  prefix is stripped and the remainder resolved recursively.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .cxxfilt import Demangler, demangle

__all__ = [
    "Signature",
    "signature",
    "split_params",
    "strip_thunk",
]


# _ZTh<call-offset>_  _ZTv<v-offset>_<nv-offset>_  _ZTc<v-offset>_<nv-offset>_
# A <number> is n-prefixed when negative, so the offset class must allow 'n'
# (`_ZThn16_...` is a non-virtual thunk to a function 16 bytes further back).
_THUNK = re.compile(r"^_ZT[hvc][0-9n]*_*")

# operator() is rendered with parens but is part of the name, not a param list.
_OPERATOR_CALL = "operator()"


class _Recorder(Demangler):
    """A ``Demangler`` that also reports the top-level parameter types.

    ``_parse_type`` recurses (a pointer parses its pointee), so capturing on
    every call would report ``(_JavaVM, _JavaVM*)`` for ``P7_JavaVM``.  A
    capture counts only when it is a direct child of the outermost
    bare-function-type, which ``type_depth`` already tracks.
    """

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._param_depth = 0
        self._base_type_depth = 0
        self._captured: List[str] = []
        self.params: Optional[List[str]] = None

    def _parse_params(self) -> str:
        self._param_depth += 1
        if self._param_depth == 1:
            self._base_type_depth = self.type_depth
        try:
            return super()._parse_params()
        finally:
            self._param_depth -= 1
            if self._param_depth == 0:
                self.params = list(self._captured)
                self._captured = []

    def _parse_type(self) -> str:
        before = self.i
        top_level = (
            self._param_depth == 1 and self.type_depth == self._base_type_depth
        )
        rendered = super()._parse_type()
        if top_level and self.i > before:
            self._captured.append(rendered)
        return rendered


class Signature:
    """A recovered prototype.

    Attributes:
        mangled: the symbol as it appears in ``.dynsym``.
        name: the demangled qualified name, without parameters.
        params: exact parameter types; empty for ``void``/no parameters.
        ret: return type, or ``""`` when the mangling does not encode one.
        kind: ``"mangled"``, ``"thunk"``, or ``"c"`` for an unmangled C symbol.
    """

    __slots__ = ("mangled", "name", "params", "ret", "kind")

    def __init__(
        self,
        mangled: str,
        name: str,
        params: List[str],
        ret: str = "",
        kind: str = "mangled",
    ) -> None:
        self.mangled = mangled
        self.name = name
        self.params = params
        self.ret = ret
        self.kind = kind

    @property
    def declaration(self) -> str:
        """The prototype as C++ source, e.g. ``void Foo::bar(int, char const*)``.

        Matches GCC's rendering, which is also what ``cxxfilt`` already prints,
        so this is primarily a stable machine-readable form.
        """
        return "%s%s(%s)" % (
            self.ret + " " if self.ret else "",
            self.name,
            ", ".join(self.params),
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Signature(%r)" % self.declaration


def strip_thunk(mangled: str) -> "tuple[str, bool]":
    """Remove a thunk prefix, returning ``(encoding, was_thunk)``.

    ``_ZTv0_n24_N3Walaber6EntityD1Ev`` holds a virtual and a non-virtual call
    offset before the real encoding; the parameters belong to the target.
    """
    m = _THUNK.match(mangled)
    if not m:
        return mangled, False
    return mangled[m.end():], True


def split_params(text: str) -> List[str]:
    """Split a rendered parameter list at top-level commas only.

    ``split(",")`` would tear ``void (*)(int, char)`` in half, so track the
    bracket depth and ignore commas nested inside ``()`` or ``<>``.
    """
    out: List[str] = []
    depth = 0
    cur = ""
    for ch in text:
        if ch in "(<":
            depth += 1
        elif ch in ")>":
            depth -= 1
        if ch == "," and depth == 0:
            piece = cur.strip()
            if piece:
                out.append(piece)
            cur = ""
        else:
            cur += ch
    piece = cur.strip()
    if piece:
        out.append(piece)
    # A lone `void` is the ABI's spelling of "no parameters".
    if len(out) == 1 and out[0] == "void":
        return []
    return out


def _qualified_name(demangled: str) -> str:
    """Strip the trailing parameter list from a demangled rendering.

    Keeps the last *top-level* bracket group, so a rendering like
    ``void (*)(int)`` nested in a template argument is left alone.
    """
    s = demangled.replace(_OPERATOR_CALL, "OPERATOR_CALL")
    depth = 0
    start = None
    last = None
    for i, ch in enumerate(s):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                last = (start, i)
                start = None
    if last is None:
        return demangled
    a, b = last
    return (s[:a] + s[b + 1:]).replace("OPERATOR_CALL", _OPERATOR_CALL)


def signature(mangled: str) -> Optional[Signature]:
    """Recover the prototype for ``mangled``, or ``None`` if it is not mangled."""
    if not mangled:
        return None
    if not mangled.startswith("_Z"):
        return Signature(mangled, mangled, [], kind="c")

    _, was_thunk = strip_thunk(mangled)
    kind = "thunk" if was_thunk else "mangled"

    # Parse the *whole* symbol, thunk prefix included. ``parse_top`` recognises
    # ``_ZT`` and skips the call offset itself, so a thunk's parameters are picked
    # up from the target encoding in one pass. Handing the bare remainder to the
    # parser instead would treat a nested name as a whole encoding and garble it
    # (``N3Walaber6EntityD1Ev`` renders as `Wal::signed char::bool::...`).
    try:
        rec = _Recorder(mangled[2:])
        rec.parse_top()
    except Exception:
        # cxxfilt swallows parse failures and returns the input unchanged; a
        # prototype we cannot build is better reported as absent than guessed.
        return None

    if rec.params is None:
        return None

    rendered = demangle(mangled)
    params = split_params(", ".join(rec.params))

    # Note: a constructor, destructor or conversion operator returns the object
    # it operates on, which no prototype spells out, and the return type of an
    # ordinary function is not encoded at all -- so `ret` stays empty.
    name = _qualified_name(rendered)
    return Signature(mangled, name, params, ret="", kind=kind)
