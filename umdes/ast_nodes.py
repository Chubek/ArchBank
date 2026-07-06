"""uMDesc AST — typed dataclasses mirroring the grammar in `uMDesc.md`.

Field width is `int` for a fixed slot, or a `(lo, hi)` tuple for a variable
range (`[lo..hi]`); `None` means the field carries no width annotation (an
abstract operand slot, resolved by a `mode`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


# --- expressions (action bodies) -----------------------------------------

@dataclass
class IntLit:
    value: int


@dataclass
class IdentRef:
    name: str


@dataclass
class IndexRef:
    base: str
    index: int


@dataclass
class BinOp:
    op: str
    left: object
    right: object


Expr = Union[IntLit, IdentRef, IndexRef, BinOp]


@dataclass
class LValue:
    name: str
    index: Optional[int] = None


@dataclass
class Assignment:
    lhs: LValue
    rhs: Expr


@dataclass
class Call:
    name: str
    args: list[Expr]


Stmt = Union[Assignment, Call]


# --- op attributes --------------------------------------------------------

@dataclass
class SyntaxAttr:
    text: str


@dataclass
class ImageAttr:
    text: str


@dataclass
class ActionAttr:
    stmts: list[Stmt]


OpAttr = Union[SyntaxAttr, ImageAttr, ActionAttr]


# --- declarations ---------------------------------------------------------

@dataclass
class Param:
    name: str
    type_name: str


@dataclass
class Field:
    """A format field. ``width`` is int (fixed), ``(lo,hi)`` (variable), or
    None (abstract slot)."""
    name: str
    width: Union[int, tuple[int, int], None] = None


@dataclass
class FormatDecl:
    name: str
    fields: list[Field]


@dataclass
class ModeDecl:
    name: str
    params: list[Param]
    body: list[object] = field(default_factory=list)   # reserved


@dataclass
class OpDecl:
    name: str
    params: list[Param]
    attrs: list[OpAttr]


@dataclass
class RegisterDecl:
    name: str
    count: int
    width: int
    names: Optional[list[str]] = None


@dataclass
class Alias:
    name: str
    target: str


@dataclass
class Wordsize:
    value: int


@dataclass
class Endianness:
    value: str          # "little" | "big"


ArchStmt = Union[Wordsize, Endianness, RegisterDecl, Alias,
                 FormatDecl, ModeDecl, OpDecl]


@dataclass
class Arch:
    name: str
    body: list[ArchStmt]


@dataclass
class File:
    decls: list[Arch]
