"""L3 — x86asm dataset CSV parser (BANKS.yaml x86-dataset).

One CSV per extension; columns: Instruction, Opcode (LEX notation), validity,
Feature Flags, Operand 1..4. The LEX opcode string (e.g. ``LEX.WN D5 ib``)
yields a fixed opcode-byte slice + operand markers -> x86-64, variable,
decode_schematic=True (§6.2). Feature Flags -> isa_ext.
"""
from __future__ import annotations

import csv
import glob
import os
from typing import ClassVar

from ..cir import RawRecord
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser


def _lex_layout(op: str):
    """LEX opcode -> field layout. Skip LEX.* markers; bytes -> Fixed; rest -> Operand."""
    out = []
    for tok in op.split():
        if tok.startswith("LEX"):
            continue
        t = tok.rstrip(",")
        if len(t) <= 2 and all(c in "0123456789abcdefABCDEF" for c in t):
            out.append(Fixed(8, int(t, 16)))
        else:
            out.append(Operand(t.replace("/", "_"), t, {"ib": 8, "iw": 16, "id": 32}.get(t, 8), "IMM"))
    return out


@register_parser
class X86DatasetParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["x86-dataset"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        data_dir = os.path.join(root, "data") if os.path.isdir(os.path.join(root, "data")) else root
        recs: list[RawRecord] = []
        partial = 0
        for f in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
            ext = os.path.splitext(os.path.basename(f))[0].replace("x86_", "")
            with open(f, newline="", encoding="utf-8") as fh:
                rdr = csv.DictReader(fh)
                for row in rdr:
                    op = (row.get("Opcode") or "").strip()
                    inst = (row.get("Instruction") or "").strip()
                    if not op or not inst:
                        partial += 1; continue
                    layout = _lex_layout(op)
                    if not layout:
                        partial += 1; continue
                    feats = (row.get("Feature Flags") or "").strip()
                    recs.append(RawRecord(
                        mnemonic=inst.split()[0],
                        arch_hint="x86-64",
                        isa_ext=feats.split()[0] if feats else (ext if ext != "base" else "base"),
                        encoding_class="prefix-modrm",
                        bank_id="x86-dataset",
                        layout=layout,
                        width="variable",
                        fields={},
                        meta={"description": (row.get("Description") or "").strip()},
                    ))
        return ParseResult(records=recs, partial=partial, note=f"{len(recs)} x86 rows")
