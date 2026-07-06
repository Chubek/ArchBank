"""LLVM TableGen selection DAG -> P-Code (sparse, §6.3).

A ``(set FPR/GPR dst (op ...))`` pattern fragment is lifted to a P-Code
``set!`` over the destination. Patterns with multiple roots or custom nodes
return None.
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from . import register_transcoder
from ._common import wrap

_SET = re.compile(r"\(set\s+\((GPR|FPR|VEC)\((\w+)\)\)\s+\(([+\-*/]|add|sub|mul|udiv|sdiv)\s+([^\)]+)\)\)")


@register_transcoder("dag", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    m = _SET.search(text)
    if not m:
        return None
    file_, dst, op, args = m.groups()
    op = {"add": "+", "sub": "-", "mul": "*", "udiv": "/", "sdiv": "/"}.get(op, op)
    return wrap(raw.mnemonic or "op",
                f"(set! {file_}[{dst}] ({op} {args}))")
