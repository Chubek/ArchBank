"""L3 — generic C-table row parser (XTRAKT.md §4.1 'C tables / headers').

A best-effort, line-oriented extractor for static-array banks shaped as
``mnemonic  <opcode bytes ...>``. Bytes form the fixed opcode slice (variable
arches -> decode_schematic=True). Used where a dedicated parser is not yet
wired; partial counts surface unparseable rows.
"""
from __future__ import annotations

import os
import re
from typing import ClassVar

from ..cir import RawRecord
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser

# mnemonic (leading identifier) then 1+ opcode bytes (0xNN / NNh / 2-hex)
_ROW = re.compile(
    r"^\s*([A-Za-z_][\w.]+)\b[^\w]*((?:0[xX][0-9A-Fa-f]{2}|[0-9A-Fa-f]{2}[hH]?\b)(?:\s+(?:0[xX][0-9A-Fa-f]{2}|[0-9A-Fa-f]{2}[hH]?|\$?[0-9A-Fa-f]{2}))*)"
)


def _bytes_layout(tokens: list[str]):
    out = []
    for t in tokens:
        tt = t.lower().rstrip(",h")
        if tt.startswith("0x"):
            tt = tt[2:]
        if len(tt) == 2:
            try:
                out.append(Fixed(8, int(tt, 16)))
            except ValueError:
                out.append(Operand(t, t, 8, "IMM"))
        else:
            out.append(Operand(t, t, 8, "IMM"))
    return out


@register_parser
class CTableParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["acme-opcodes"]
    arch_hint: ClassVar[str] = "mos6502"
    enc_class: ClassVar[str] = "variable"

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        recs: list[RawRecord] = []
        partial = 0
        for dp, _, fns in os.walk(root):
            for fn in fns:
                if not fn.endswith((".i", ".inc", ".h", ".c")):
                    continue
                fp = os.path.join(dp, fn)
                for line in open(fp, encoding="utf-8", errors="replace"):
                    s = line.split(";", 1)[0].split("//", 1)[0]
                    m = _ROW.match(s)
                    if not m:
                        continue
                    mnem = m.group(1)
                    toks = m.group(2).split()
                    if not toks:
                        continue
                    # skip array-index / table-cookie false positives
                    if any(c in mnem for c in "=#"):
                        continue
                    layout = _bytes_layout(toks)
                    recs.append(RawRecord(
                        mnemonic=mnem.lower(),
                        arch_hint=self.arch_hint,
                        isa_ext="base",
                        encoding_class=self.enc_class,
                        bank_id=entry.id,
                        layout=layout,
                        width="variable",
                        fields={},
                    ))
        return ParseResult(records=recs, partial=partial, note="ctable scan")
