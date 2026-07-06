"""Generic source/table scanner for C-like opcode banks."""
from __future__ import annotations

import os
import re
from typing import ClassVar

from ..pcode.emitter import Fixed, Operand
from .base import ParseResult, SourceParser, register_parser
from .common import arch_from_path, clean_c_line, iter_source_files, parse_int, raw_record, token_layout

_QUOTED = re.compile(r'"([A-Za-z][\w.$-]*)"')
_HEX_CONST = re.compile(r"\b(?:0x[0-9A-Fa-f]{2,16}|[0-9A-Fa-f]{2}h)\b")
_SHIFT_MACRO = re.compile(r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\s*\([^)]*\)\s+.*<<\s*(\d+)")
_OP_MACRO = re.compile(r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\s+([A-Z][A-Z0-9_]*)\((0x[0-9A-Fa-f]+|\d+)\)")


@register_parser
class GenericSourceParser(SourceParser):
    bank_ids: ClassVar[list[str]] = [
        "beaengine-instrset", "binaryen-wasm", "binaryninja-arch",
        "binutils-libopcode", "bochs-cpu", "capstone-arch",
        "decaf-qemu", "distorm-disops", "dynasm-opcodes",
        "dyninst-instrapi", "fasm-inc", "gem5-arch", "granary-arch",
        "gcc-md", "ghidra-cpu", "ildjit-vm", "impact-mspec", "keystone-arch", "libfirm-be",
        "lightning-jitfiles", "mir-data", "myjit-arch", "nanojit-instr",
        "openuh-be", "pcc-arch", "qemu-targets", "qemu-tcg",
        "radare2-opcodes", "sljit-data", "tcc-instrfiles",
        "upython-asm", "xbyak-instructions", "xed-datafiles", "yasm-arch",
    ]
    suffixes: ClassVar[tuple[str, ...]] = (
        ".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".i", ".inl", ".lua",
        ".md", ".py", ".rs", ".sinc", ".slaspec", ".sleigh",
    )

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        records = []
        partial = 0
        for path in iter_source_files(root, self.suffixes) or []:
            arch = arch_from_path(path)
            shifts: dict[str, int] = {}
            try:
                handle = open(path, encoding="utf-8", errors="replace")
            except OSError:
                continue
            with handle:
                for line in handle:
                    shift_match = _SHIFT_MACRO.match(line)
                    if shift_match:
                        shifts[shift_match.group(1)] = int(shift_match.group(2))
                        continue
                    macro_record = self._macro_record(line, entry.id, arch, shifts, root, path)
                    if macro_record is not None:
                        records.append(macro_record)
                        continue
                    row_records = self._quoted_records(line, entry.id, arch, root, path)
                    if row_records:
                        records.extend(row_records)
                    elif _looks_opcodeish(line):
                        partial += 1
        return ParseResult(records=records, partial=partial, note=f"{len(records)} source-scan rows")

    @staticmethod
    def _macro_record(line: str, bank_id: str, arch: str | None,
                      shifts: dict[str, int], root: str, path: str):
        match = _OP_MACRO.match(line)
        if not match or match.group(2) not in shifts:
            return None
        mnemonic, macro, value_text = match.groups()
        shift = shifts[macro]
        value = parse_int(value_text)
        if value is None or shift >= 32:
            return None
        fixed_width = 32 - shift
        layout = [Fixed(fixed_width, value)]
        if shift:
            layout.append(Operand("operands", "op", shift, "IMM"))
        return raw_record(
            mnemonic, bank_id, arch, layout,
            encoding_class="fixed-32", width=32,
            source=os.path.relpath(path, root),
        )

    @staticmethod
    def _quoted_records(line: str, bank_id: str, arch: str | None,
                        root: str, path: str) -> list:
        stripped = clean_c_line(line)
        names = _QUOTED.findall(stripped)
        if not names:
            return []
        tokens = _HEX_CONST.findall(stripped)
        if not tokens:
            return []
        layout = token_layout(tokens)
        if not layout:
            return []
        records = []
        for name in names[:1]:
            if len(name) > 32 or name.lower() in {"name", "none", "invalid", "unknown"}:
                continue
            records.append(raw_record(
                name, bank_id, arch, list(layout),
                encoding_class="prefix-modrm" if arch == "x86-64" else "variable",
                source=os.path.relpath(path, root),
            ))
        return records


def _looks_opcodeish(line: str) -> bool:
    low = line.lower()
    return "opcode" in low or "insn" in low or "instr" in low or "mnemonic" in low
