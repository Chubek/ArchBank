"""Shared transcoder helpers."""
from __future__ import annotations
import re
from typing import Optional


def wrap(mnemonic: str, body: str, decls: Optional[list] = None) -> str:
    decl_str = " ".join(f"({n} :{t})" for (n, t) in (decls or []))
    return f"(define-semantics ({mnemonic} {decl_str})\n  {body.strip()})"


# SSL/GCC-RTL style register references: R1, r1, %eax, reg[1], GPR[1]
_REG = re.compile(r"\b([Rr])(\d{1,2})\b")
