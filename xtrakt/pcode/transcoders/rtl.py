"""GCC RTL (.md define_insn) -> P-Code (partial, §6.3).

Captures the RTL template of a ``define_insn`` and emits it verbatim inside a
``define-semantics`` skeleton flagged ``(:source rtl)``. RTL is not P-Code, so
this is a faithful passthrough marker, not an evaluation-ready lift; consumers
that need evaluable semantics treat it as None. Returns None if no template.
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from . import register_transcoder


@register_transcoder("rtl", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    m = re.search(r"\(define_insn\b.*?\[(.*?)\]\s*\"?([^\"]*)\"?",
                  text, re.S)
    if not m:
        return None
    template = m.group(1).strip()
    if not template:
        return None
    name = raw.mnemonic or (m.group(0).split('"')[1] if '"' in m.group(0) else "op")
    return (f"(define-semantics ({name}) ;; (:source rtl)\n"
            f"  {template.splitlines()[0]})")
