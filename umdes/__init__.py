"""uMDesc — Micro Machine Description Language (nML-adjacent, non-S-Expr).

Public surface: AST node dataclasses, the SLY `Lexer`/`Parser`, and the
abstract `BaseVisitor`. See `uMDesc.md` for the language definition.

Per-architecture specs live in `umdes/specs/*.umdesc`.
"""
from __future__ import annotations

from .ast_nodes import (
    File, Arch, Wordsize, Endianness, RegisterDecl, Alias,
    FormatDecl, Field, ModeDecl, OpDecl, Param,
    SyntaxAttr, ImageAttr, ActionAttr, Assignment, Call, LValue,
    IntLit, IdentRef, IndexRef, BinOp,
)
from .lexer import Lexer
from .parser import Parser
from .visitor import BaseVisitor

__all__ = [
    "File", "Arch", "Wordsize", "Endianness", "RegisterDecl", "Alias",
    "FormatDecl", "Field", "ModeDecl", "OpDecl", "Param",
    "SyntaxAttr", "ImageAttr", "ActionAttr", "Assignment", "Call", "LValue",
    "IntLit", "IdentRef", "IndexRef", "BinOp",
    "Lexer", "Parser", "BaseVisitor", "parse",
]


def parse(text: str) -> File:
    """Parse uMDesc source text into a :class:`File` AST."""
    return Parser().parse(Lexer().tokenize(text))
