"""L5 — P-Code emitter: field layout -> encoding_function (P-Code.md §3, XTRAKT.md §6.1).

A field layout is an MSB-first list of segments. Each segment is either a
fixed const or an operand slot. The emitter turns it into a
``(define-encoding (name <op-decls>) <width> (cat <forms>))`` and asserts that
field widths sum to ``<width>`` for fixed-width instructions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from ..cir import BitVec


@dataclass
class Fixed:
    """A const bit field: ``width`` bits holding integer ``value``."""
    width: int
    value: int

    def __post_init__(self):
        self.value = int(self.value) & ((1 << self.width) - 1) if self.width else 0


@dataclass
class Operand:
    """An operand-bearing field: ``name`` tags the bit range, ``operand`` names
    the declared slot (often equal to ``name``), at encoding ``width``."""
    name: str
    operand: Optional[str] = None
    width: int = 0
    op_type: str = "IMM"          # operand-type tag (:TYPE) for the decl

    def __postinit__(self):
        if self.operand is None:
            self.operand = self.name


FieldLayout = list[Union[Fixed, Operand]]


def const_literal(width: int, value: int) -> str:
    """Render a const literal whose width survives the sexpr round-trip.

    ``#x`` only for nibble-aligned widths (digit count == width); ``#b`` for
    every other width so non-aligned widths (e.g. 13) are not silently padded
    to the next nibble (which would corrupt the L6 width accounting).
    """
    if width <= 0:
        return "#b0"
    mask = (1 << width) - 1
    if width % 4 == 0:
        return "#x" + format(value & mask, f"0{width // 4}x")
    return "#b" + format(value & mask, f"0{width}b")


def _op_decls(layout: FieldLayout) -> list[tuple[str, str, int]]:
    """Operand declarations (name, type, width), first-seen, deduped by name."""
    seen: dict[str, tuple[str, str, int]] = {}
    for seg in layout:
        if isinstance(seg, Operand):
            op = seg.operand or seg.name
            if op not in seen:
                seen[op] = (op, seg.op_type or "IMM", seg.width or 0)
    return list(seen.values())


def _render_seg(seg: Union[Fixed, Operand]) -> str:
    if isinstance(seg, Fixed):
        return f"(const {const_literal(seg.width, seg.value)})"
    op = seg.operand or seg.name
    w = seg.width or 0
    return f"(field {seg.name} {op} {w})"


def _width_token(width: Any) -> str:
    if isinstance(width, int):
        return str(width)
    return str(width)


def emit_encoding(name: str, layout: FieldLayout,
                  width: Any = "variable",
                  op_decls: Optional[list[tuple[str, str, int]]] = None,
                  op_types: Optional[dict[str, str]] = None) -> str:
    """Render a ``(define-encoding ...)`` form from an MSB-first field layout.

    - ``op_decls``: override operand declaration list (name,type,width).
    - ``op_types``: map operand name -> :TYPE tag to repair inferred tags.
    Width-sum is asserted for integer ``width`` (P-Code §5).
    """
    decls = list(op_decls) if op_decls is not None else _op_decls(layout)
    if op_types:
        decls = [(n, op_types.get(n, t), w) for (n, t, w) in decls]

    decl_str = " ".join(
        f"({n} :{t} {w})" if w else f"({n} :{t})" for (n, t, w) in decls
    )
    body = "(cat " + " ".join(_render_seg(s) for s in layout) + ")"
    wt = _width_token(width)

    if isinstance(width, int):
        total = sum(
            (s.width if isinstance(s, Fixed) else s.width) for s in layout
        )
        if total != width:
            raise ValueError(
                f"emit_encoding({name}): field widths sum to {total} != width {width}"
            )
    if decl_str:
        return f"(define-encoding ({name} {decl_str}) {wt}\n  {body})"
    return f"(define-encoding ({name}) {wt}\n  {body})"


def emit_semantics(name: str, body: str,
                   decls: Optional[list[tuple[str, str, int]]] = None) -> str:
    """Wrap a foreign-transcoded or hand-written semantic body."""
    if body.lstrip().startswith("(define-semantics"):
        return body
    decl_str = " ".join(f"({n} :{t})" for (n, t, _w) in (decls or []))
    return f"(define-semantics ({name} {decl_str})\n  {body.strip()})"
