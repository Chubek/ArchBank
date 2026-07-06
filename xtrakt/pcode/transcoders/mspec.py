"""Simulator (Pydgin/IMPACT m_spec) -> P-Code (sparse, §6.3).

Maps the trivial ``self.regs[rd] = self.regs[rs1] + imm`` execute()-style
assignment to a P-Code ``set!``. Anything beyond a single GPR assignment
returns None.
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from . import register_transcoder
from ._common import wrap

_PY = re.compile(
    r"self\.regs?\[(\w+)\]\s*=\s*.*?regs?\[(\w+)\]\s*([+\-*/])\s*(\w+)"
)


@register_transcoder("mspec", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    m = _PY.search(text)
    if not m:
        return None
    rd, rs, op, imm = m.groups()
    op = {"+": "+", "-": "-", "*": "*", "/": "/"}[op]
    body = f"(set! GPR[{rd}] ({op} GPR[{rs}] {imm}))"
    return wrap(raw.mnemonic or "op", body)
