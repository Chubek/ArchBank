"""LLVM-style TableGen instruction parser."""
from __future__ import annotations

import os
import re
from typing import ClassVar

from ..pcode.emitter import Fixed, Operand
from .base import ParseResult, SourceParser, register_parser
from .common import arch_from_path, raw_record

_DEF = re.compile(r"^\s*def\s+([A-Za-z_][\w$]*)\b")
_ASM = re.compile(r'AsmString\s*=\s*"([^"]+)"')
_BIT = re.compile(r"Inst\{(\d+)(?:-(\d+))?\}\s*=\s*(0b[01_]+|0x[0-9A-Fa-f_]+|\d+)")


def _mnemonic(block_name: str, body: str) -> str:
    match = _ASM.search(body)
    if match:
        asm = match.group(1).strip()
        if asm:
            return asm.split()[0].split("\t", 1)[0].strip("$").lower()
    return block_name.lower()


def _layout_from_bits(body: str, width: int = 32) -> list:
    segments: list[tuple[int, int, Fixed]] = []
    for match in _BIT.finditer(body):
        hi = int(match.group(1))
        lo = int(match.group(2) or match.group(1))
        msb, lsb = max(hi, lo), min(hi, lo)
        value = int(match.group(3).replace("_", ""), 0)
        segments.append((msb, lsb, Fixed(msb - lsb + 1, value)))
    if not segments:
        return []
    segments.sort(key=lambda item: item[0], reverse=True)
    layout = []
    cursor = width - 1
    for msb, lsb, fixed in segments:
        if msb > cursor:
            continue
        if msb < cursor:
            gap_width = cursor - msb
            layout.append(Operand(f"gap_{cursor}_{msb + 1}", "op", gap_width, "IMM"))
        layout.append(fixed)
        cursor = lsb - 1
    if cursor >= 0:
        layout.append(Operand(f"gap_{cursor}_0", "op", cursor + 1, "IMM"))
    return layout


@register_parser
class TableGenParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["llvm-td"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        records = []
        partial = 0
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith(".td") or "Instr" not in filename:
                    continue
                path = os.path.join(dirpath, filename)
                arch = arch_from_path(path)
                text = open(path, encoding="utf-8", errors="replace").read()
                starts = [(match.start(), match.group(1)) for match in _DEF.finditer(text)]
                for index, (start, name) in enumerate(starts):
                    end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
                    body = text[start:end]
                    layout = _layout_from_bits(body)
                    if not layout:
                        partial += 1
                        continue
                    records.append(raw_record(
                        _mnemonic(name, body), entry.id, arch, layout,
                        encoding_class="fixed-32", width=32,
                        source=os.path.relpath(path, root),
                    ))
        return ParseResult(records=records, partial=partial, note=f"{len(records)} tablegen defs")
