"""L3 — Felix Cloutier x86 JSON reference parser (BANKS.yaml courtier-x86).

Source: ``felixcloutier_x86.json`` — a structured scrape of the Intel/AMD SDM
instruction pages. Shape: ``pages[].tables[].rows[]`` with a header row whose
columns include ``Opcode`` and ``Instruction``.

  - ``Opcode``        : space-separated hex bytes + operand markers
                        ("14 ib", "63 /r", "REX.W + 89 /r")
  - ``Instruction``   : "MNEMONIC operand, operand" ("ADC AL, imm8")

Opcode -> MSB-first field layout (Fixed bytes + Operand markers); the
Instruction cell -> mnemonic + operand signature. x86-64 is variable-width ->
decode_schematic=True (§6.2).
"""
from __future__ import annotations

import json
import os
from typing import ClassVar

from ..cir import RawRecord
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser

# Operand marker -> (width, op_type). x86 immediate/register-operand notations.
_OP_MARKERS = {
    "ib": (8, "IMM"), "iw": (16, "IMM"), "id": (32, "IMM"), "iq": (64, "IMM"),
    "cb": (8, "IMM"), "cw": (16, "IMM"), "cd": (32, "IMM"),
    "zb": (8, "IMM"), "zw": (16, "IMM"),
}


def _opcode_layout(op: str) -> list:
    """Opcode cell -> MSB-first field layout. Unknown tokens (REX.W, +, ...)
    are skipped: they are prefix/opcode decorations, not field slots."""
    layout: list = []
    for raw in op.split():
        tok = raw.strip().lstrip("+").rstrip(",")
        if not tok:
            continue
        low = tok.lower()
        if low in _OP_MARKERS:
            w, t = _OP_MARKERS[low]
            layout.append(Operand(low, low, w, t))
            continue
        if low == "/r":                       # ModRM: reg + r/m
            layout.append(Operand("/r", "modrm", 8, "GPR"))
            continue
        if len(low) == 2 and low[0] == "/" and low[1].isdigit():  # /0../7
            layout.append(Operand(low, "regfield", 3, "GPR"))
            continue
        if len(tok) <= 2 and all(c in "0123456789abcdefABCDEF" for c in tok):
            layout.append(Fixed(8, int(tok, 16)))   # opcode byte
            continue
        # REX.W, prefix mnemonics, etc. -> not a field slot
    return layout


def _mnemonic_and_operands(instruction: str) -> tuple[str, str]:
    parts = instruction.strip().split(None, 1)
    mnem = parts[0] if parts else ""
    operands = parts[1].strip() if len(parts) > 1 else ""
    return mnem.lower(), operands


def _row_columns(header: list) -> dict[str, int]:
    return {str(h).strip(): i for i, h in enumerate(header)}


@register_parser
class CourtierJsonParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["courtier-x86"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        path = os.path.join(root, "felixcloutier_x86.json")
        if not os.path.exists(path):
            return ParseResult(note="felixcloutier_x86.json not found")
        data = json.load(open(path, encoding="utf-8"))
        recs: list[RawRecord] = []
        partial = 0
        for page in data.get("pages", []):
            for table in page.get("tables", []):
                rows = table.get("rows") or []
                if not rows:
                    continue
                cols = _row_columns(rows[0])
                oi, ii = cols.get("Opcode"), cols.get("Instruction")
                if oi is None or ii is None:
                    partial += len(rows) - 1
                    continue
                for row in rows[1:]:
                    if max(oi, ii) >= len(row):
                        partial += 1
                        continue
                    op = (row[oi] or "").strip()
                    inst = (row[ii] or "").strip()
                    if not op or not inst:
                        partial += 1
                        continue
                    layout = _opcode_layout(op)
                    if not layout:
                        partial += 1
                        continue
                    mnem, operands = _mnemonic_and_operands(inst)
                    if not mnem:
                        partial += 1
                        continue
                    recs.append(RawRecord(
                        mnemonic=mnem,
                        arch_hint="x86-64", isa_ext="base",
                        encoding_class="prefix-modrm", bank_id="courtier-x86",
                        layout=layout, width="variable",
                        fields={},
                        meta={"operands": operands, "opcode": op,
                              "description": self._cell(row, cols, "Description")},
                    ))
        return ParseResult(records=recs, partial=partial,
                           note=f"{len(recs)} x86 rows from {path}")

    @staticmethod
    def _cell(row: list, cols: dict[str, int], name: str) -> str:
        i = cols.get(name)
        if i is None or i >= len(row):
            return ""
        return str(row[i] or "").strip()
