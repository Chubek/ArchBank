"""P-Code S-expression reader (P-Code.md §1).

Minimal lexer + parser for the ArchBank dialect. Produces nested Python lists:
lists -> list, symbols -> str, decimal ints -> int, ``#x/#b`` literals ->
``BitVec``, strings -> ``str``. Line comments start with ``;``.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from ..cir import BitVec


class PCodeError(ValueError):
    pass


# ──────────────────────────── lexer ─────────────────────────────

_SYMBOL_BREAK = set("()'\" \t\r\n;")
_DIGITS = set("0123456789")


def _tokenize(text: str) -> list[str]:
    toks: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == ";":                       # line comment
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c in "()'":
            toks.append(c)
            i += 1
            continue
        if c == '"':                       # string literal
            j = i + 1
            buf = ['"']
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j]); buf.append(text[j + 1]); j += 2; continue
                buf.append(text[j]); j += 1
            buf.append('"')
            toks.append("".join(buf))
            i = j + 1
            continue
        # atom: read until a break char
        j = i
        while j < n and text[j] not in _SYMBOL_BREAK:
            j += 1
        toks.append(text[i:j])
        i = j
    return toks


def _atom(tok: str) -> Any:
    if tok.startswith("#x") or tok.startswith("#X"):
        return BitVec.from_hex(tok[2:])
    if tok.startswith("#b") or tok.startswith("#B"):
        return BitVec.from_bin(tok[2:])
    if tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    # decimal int?
        # (keep symbols like name, +, <<, GPR[rd] as str)
    try:
        return int(tok, 10)
    except ValueError:
        return tok


def _parse_seq(toks: list[str], pos: int) -> tuple[list, int]:
    """Parse zero or more forms until a matching ')' or EOF. Returns (forms, pos)."""
    forms: list = []
    n = len(toks)
    while pos < n:
        t = toks[pos]
        if t == ")":
            return forms, pos + 1
        if t == "(":
            sub, pos = _parse_seq(toks, pos + 1)
            forms.append(sub)
        elif t == "'":                     # quote -> (quote <next>)
            pos += 1
            if pos < n and toks[pos] == "(":
                sub, pos = _parse_seq(toks, pos + 1)
                forms.append(["quote", sub])
            else:
                forms.append(["quote", _atom(toks[pos])]); pos += 1
        else:
            forms.append(_atom(t)); pos += 1
    return forms, pos


def read(text: str) -> list:
    """Parse P-Code text -> list of top-level forms."""
    return _parse_seq(_tokenize(text), 0)[0]


def read_one(text: str) -> Any:
    forms = read(text)
    if not forms:
        raise PCodeError("no form")
    return forms[0]


# ──────────────────────────── helpers ───────────────────────────

def is_form(x: Any, head: str) -> bool:
    return isinstance(x, list) and len(x) >= 1 and x[0] == head


def find_form(x: Any, head: str) -> Optional[list]:
    """First sub-form anywhere whose car == head."""
    if isinstance(x, list):
        if x and x[0] == head:
            return x
        for sub in x:
            r = find_form(sub, head)
            if r is not None:
                return r
    return None
