"""Sleigh (.sinc) -> P-Code transcoder (partial, §6.3).

Handles the simplest SLEIGH p-code body: a single ``loc = expr;`` assignment
over register/flag locations. Anything multi-statement or using SLEIGH-specific
constructs (subpiece, user-defined ops beyond p-code core) returns None.
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from ..emitter import emit_semantics
from . import register_transcoder
from ._common import wrap

_ASSIGN = re.compile(
    r"^\s*([A-Za-z_][\w\[\].]*)\s*=\s*(.+?)\s*;?\s*$"
)


@register_transcoder("sleigh", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    # Take the constructor body: text after the mnemonic/operand line.
    # Conservatively handle one trailing assignment.
    line = text.strip().splitlines()[-1].strip() if text.strip() else ""
    m = _ASSIGN.match(line)
    if not m:
        return None
    loc, expr = m.group(1), m.group(2)
    pcode_expr = _translate(expr)
    if pcode_expr is None:
        return None
    body = f"(set! {_loc(loc)} {pcode_expr})"
    return wrap(raw.mnemonic or "op", body)


def _loc(loc: str) -> str:
    loc = loc.replace(".", "_")
    return loc


def _translate(expr: str):
    expr = expr.strip()
    # integer literal
    if re.fullmatch(r"0x[0-9a-fA-F]+|\d+", expr):
        return expr
    # simple binary add/sub: a + b
    m = re.fullmatch(r"(.+?)\s*([+\-&|])\s*(.+)", expr)
    if m:
        l, op, r = m.group(1).strip(), m.group(2), m.group(3).strip()
        op = {"+": "+", "-": "-", "&": "&", "|": "|"}.get(op)
        if op is None:
            return None
        return f"({op} {_translate(l) or l} {_translate(r) or r})"
    return None
