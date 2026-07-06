"""NASM insns.dat parser."""
from __future__ import annotations

import glob
import os
import re
from typing import ClassVar

from .base import ParseResult, SourceParser, register_parser
from .common import raw_record, token_layout

_ROW = re.compile(r"^\s*(?:\$\S+\s+)?([A-Za-z][\w.]+)\s+(.+?)\s+\[\s*(.+?)\s*\]\s+([A-Za-z0-9_,!]+)")


def _opcode_tokens(code: str) -> list[str]:
    if ":" in code:
        code = code.split(":", 1)[1]
    return [part.strip() for part in code.replace("\t", " ").split() if part.strip()]


@register_parser
class NasmDataParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["nasm-data"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        files = sorted(glob.glob(os.path.join(root, "**", "insns.dat"), recursive=True))
        records = []
        partial = 0
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip() or line.lstrip().startswith(";"):
                        continue
                    match = _ROW.match(line)
                    if not match:
                        partial += 1
                        continue
                    mnemonic, operands, code, flags = match.groups()
                    if code.strip() == "ignore" or "PSEUDO" in flags:
                        continue
                    layout = token_layout(_opcode_tokens(code))
                    if not layout:
                        partial += 1
                        continue
                    records.append(raw_record(
                        mnemonic, entry.id, "x86-64", layout,
                        isa_ext=flags.split(",", 1)[0].lower(),
                        encoding_class="prefix-modrm",
                        operands=operands.strip(),
                        flags=flags.strip(),
                        source=os.path.relpath(path, root),
                    ))
        return ParseResult(records=records, partial=partial, note=f"{len(records)} nasm rows")
