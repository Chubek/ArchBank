"""P-Code sub-package: L5 emitter, L6 decoder, foreign-semantics transcoders."""
from .emitter import (
    FieldLayout,
    Fixed,
    Operand,
    emit_encoding,
    const_literal,
)
from .decoder import decode_signature, DecodeResult

__all__ = [
    "FieldLayout",
    "Fixed",
    "Operand",
    "emit_encoding",
    "const_literal",
    "decode_signature",
    "DecodeResult",
]
