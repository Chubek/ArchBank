"""L6 — decode signature: encoding_function -> (decode_mask, decode_match).

Implements P-Code.md §6. Walks the emitted ``(cat ...)`` MSB-first; each
``(const ...)`` contributes a fixed (mask,match) pair, each ``(field ...)``
contributes don't-care. Anything richer than a flat field/const cat
(branching, computed-width prefixes, format tables) yields ``schematic=True``
with a null mask — never fabricated (XTRAKT.md §6.2, §13).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..cir import BitVec, ones
from . import sexpr
from .sexpr import PCodeError


@dataclass
class DecodeResult:
    mask: Optional[BitVec]
    match: Optional[BitVec]
    schematic: bool
    note: str = ""


# sentinel: an element whose bit-width we cannot statically account for
class _Unknown:
    pass


_UNKNOWN = _Unknown()


def _seg_width_and_kind(form: list) -> tuple[int, str, Any]:
    """Return (width, kind, payload) for a cat element.

    kind in {'fixed','var','unknown'}; payload is the const value or None.
    """
    head = form[0]
    if head == "const" and len(form) >= 2 and isinstance(form[1], BitVec):
        return form[1].width, "fixed", form[1].value
    if head == "field" and len(form) >= 4 and isinstance(form[-1], int):
        return int(form[-1]), "var", None
    if head == "const" and len(form) >= 2:        # const of non-literal expr
        return 0, "unknown", None
    return 0, "unknown", None


def _flatten(expr: Any) -> list:
    """Flatten a body expr into an MSB-first list of cat-element forms.

    Returns a flat list of forms, or raises _Schematic if the body uses
    constructs that defeat a uniform mask.
    """
    if not isinstance(expr, list):
        raise _Schematic("non-form body")
    head = expr[0] if expr else None
    if head == "cat":
        out: list = []
        for child in expr[1:]:
            out.extend(_flatten(child))
        return out
    if head in ("let", "let*") and len(expr) >= 3:
        # (let/let* (bindings...) BODY) -> flatten BODY
        return _flatten(expr[-1])
    # leaf element: const / field / other
    return [expr]


class _Schematic(Exception):
    """Raised when the body cannot yield a uniform bit-mask."""


def decode_signature(encoding_function: str, width: Any) -> DecodeResult:
    """Invert an encoding function into its decode signature."""
    if not encoding_function or not encoding_function.strip():
        return DecodeResult(None, None, True, "no encoding_function")

    try:
        form = sexpr.read_one(encoding_function)
    except (PCodeError, ValueError) as e:
        return DecodeResult(None, None, True, f"unparseable: {e}")

    if not sexpr.is_form(form, "define-encoding"):
        return DecodeResult(None, None, True, "not a define-encoding")

    # (define-encoding (name decls...) WIDTH BODY)
    body_forms = form[2:]
    if len(body_forms) < 2:
        return DecodeResult(None, None, True, "malformed define-encoding")
    w_tok = body_forms[-2] if isinstance(body_forms[-2], int) else body_forms[-2]
    body = body_forms[-1]

    instr_width = width if isinstance(width, int) else (
        w_tok if isinstance(w_tok, int) else None
    )
    if instr_width is None:
        return DecodeResult(None, None, True, "variable/indeterminate width")

    try:
        segs = _flatten(body)
        mask = 0
        match = 0
        top = instr_width                       # current top bit index (MSB=0)
        accounted = 0
        for seg in segs:
            if not isinstance(seg, list) or not seg:
                raise _Schematic("non-form segment")
            w, kind, payload = _seg_width_and_kind(seg)
            if kind == "unknown":
                raise _Schematic(f"unknown-width element: {seg[0]}")
            lo = top - w                         # LSB-side offset of this segment
            if lo < 0:
                raise _Schematic("segment overruns instruction width")
            if kind == "fixed":
                mask |= ones(w) << lo
                match |= (int(payload) & ones(w)) << lo
            top = lo
            accounted += w

        if accounted != instr_width:
            raise _Schematic(
                f"segments account for {accounted} != {instr_width} bits"
            )
    except _Schematic as s:
        return DecodeResult(None, None, True, f"schematic body: {s}")

    return DecodeResult(BitVec(instr_width, mask), BitVec(instr_width, match), False)
