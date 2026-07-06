"""uMDesc SLY lexer. Token set per `uMDesc.md`.

Nested `/* ... */` comments are stripped by hand-balancing in the BLOCK_COMMENT
rule, since a single regex cannot nest.
"""
from __future__ import annotations

from sly import Lexer

# Token-name constants (defined before the class so the `tokens` set resolves).
ARCH = "ARCH"
REGISTER = "REGISTER"
MODE = "MODE"
FORMAT = "FORMAT"
OP = "OP"
ALIAS = "ALIAS"
WORDSIZE = "WORDSIZE"
ENDIANNESS = "ENDIANNESS"
LITTLE = "LITTLE"
BIG = "BIG"
SYNTAX = "SYNTAX"
IMAGE = "IMAGE"
ACTION = "ACTION"
IDENT = "IDENT"
INT = "INT"
STRING = "STRING"
DOTDOT = "DOTDOT"

_KEYWORDS = {
    "arch": ARCH, "register": REGISTER, "mode": MODE,
    "format": FORMAT, "op": OP, "alias": ALIAS,
    "wordsize": WORDSIZE, "endianness": ENDIANNESS,
    "little": LITTLE, "big": BIG,
    "syntax": SYNTAX, "image": IMAGE, "action": ACTION,
}


class Lexer(Lexer):
    tokens = {
        ARCH, REGISTER, MODE, FORMAT, OP, ALIAS,
        WORDSIZE, ENDIANNESS, LITTLE, BIG,
        SYNTAX, IMAGE, ACTION,
        IDENT, INT, STRING, DOTDOT,
    }
    ignore = " \t\r"
    literals = {
        "{", "}", "[", "]", "(", ")", ",", ":", ";", "=",
        "+", "-", "|", "&", "^", "~",
    }

    # --- comments --------------------------------------------------------
    @_(r"//[^\n]*")
    def LINE_COMMENT(self, t):
        return None

    @_(r"/\*")
    def BLOCK_COMMENT(self, t):
        # Hand-balanced scan for nested `/* ... */` (a single regex cannot
        # nest). SLY exposes the input as `self.text` and the scan cursor as
        # `self.index`, already advanced past the opening `/*`; `t.index` is the
        # start of that opener. We walk to the balanced closer, then move the
        # cursor past it and count the newlines we swallowed.
        text = self.text
        pos = self.index
        depth = 1
        while depth > 0 and pos < len(text):
            if text.startswith("/*", pos):
                depth += 1
                pos += 2
            elif text.startswith("*/", pos):
                depth -= 1
                pos += 2
            else:
                pos += 1
        if depth != 0:
            raise SyntaxError("uMDesc: unterminated block comment")
        self.lineno += text.count("\n", t.index, pos)
        self.index = pos
        return None

    # --- newlines (counted for error position, otherwise ignored) -------
    @_(r"\n+")
    def newline(self, t):
        self.lineno += t.value.count("\n")

    # --- dotdot before IDENT: `..` must not split into two literal dots -
    #     there is no `.` literal, so this is the only `.`-bearing token.
    @_(r"\.\.")
    def DOTDOT(self, t):
        return t

    # --- literals --------------------------------------------------------
    @_(r"0[xX][0-9a-fA-F]+|\d+")
    def INT(self, t):
        t.value = int(t.value, 0)
        return t

    @_(r'"([^"\\]|\\.)*"')
    def STRING(self, t):
        # Spec: no escapes beyond `\"`. The regex admits any `\x` so an escaped
        # quote never terminates the string; only `\"` is decoded to `"`.
        t.value = t.value[1:-1].replace('\\"', '"')
        return t

    # --- identifiers + keywords -----------------------------------------
    # Per spec, a `.` is part of an identifier so `R8.R15`-style dotted names
    # lex as one token. `..` (ranges) still wins for `0..15` because an IDENT
    # cannot *start* at a `.`; DOTDOT is matched there instead.
    @_(r"[A-Za-z_][A-Za-z0-9_.]*")
    def IDENT(self, t):
        kw = _KEYWORDS.get(t.value)
        if kw is not None:
            t.type = kw
        return t

    def error(self, t):
        raise SyntaxError(f"uMDesc lexer: illegal char {t.value[0]!r} "
                          f"at line {self.lineno}")
