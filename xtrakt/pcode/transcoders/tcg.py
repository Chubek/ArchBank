"""QEMU TCG helper / decodetree -> P-Code (sparse, §6.3).

TCG semantics are C helper calls emitted from ``translate.c``; full lifter
synthesis is out of scope. We record the helper-function name as a P-Code
foreign call so semantics coverage is visible. Returns None when no helper is
named.
"""
from __future__ import annotations
import re
from ...cir import RawRecord
from . import register_transcoder


_HELPER = re.compile(r"\b(gen_|helper_)([A-Za-z_][\w]*)\s*\(")


@register_transcoder("tcg", coverage="sparse")
def transcode(text: str, raw: RawRecord):
    m = _HELPER.search(text)
    if not m:
        return None
    helper = m.group(2)
    name = raw.mnemonic or "op"
    return (f"(define-semantics ({name}) ;; (:source tcg)\n"
            f"  (foreign-call {helper}))")
