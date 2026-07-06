"""SSL (Boomerang Semantic Spec Language) -> P-Code (partial, §6.3).

SSL bodies are RTL assignment lists inside ``MNEMONIC ops { ... }``. We map a
single trailing `` := `` assignment of the form ``reg <- reg OP imm`` to a P-Code
``set!``; multi-RTL or flag/alias writes return None (semantics=null is legal).
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from . import register_transcoder
from ._common import wrap

_ASSIGN = re.compile(r"([A-Za-z_][\w]*)\s*:=\s*(.+)")


@register_transcoder("ssl", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    last = ""
    for ln in text.splitlines():
        if ":=" in ln:
            last = ln.strip().rstrip(";")
    m = _ASSIGN.match(last)
    if not m:
        return None
    loc, expr = m.group(1), m.group(2).strip()
    return wrap(raw.mnemonic or "op", f"(set! {loc} {expr})")
