"""Shared parser helpers for L3 source-family parsers."""
from __future__ import annotations

import os
import re
from typing import Iterable

from ..cir import BitVec, RawRecord
from ..pcode.emitter import Fixed, Operand

_HEX_BYTE = re.compile(r"^(?:0x)?[0-9a-fA-F]{2}h?$")
_HEX_RUN = re.compile(r"^[0-9a-fA-F]{4,}$")

ARCH_ALIASES = (
    ("x86-64", ("x86_64", "x86-64", "amd64", "x64", "i386", "i686", "x86")),
    ("aarch64", ("aarch64", "arm64")),
    ("arm-a32", ("armv7", "thumb", "arm32", "arm")),
    ("riscv", ("riscv64", "riscv32", "riscv", "rv64", "rv32")),
    ("mips", ("mips64", "mips32", "mips")),
    ("mos6502", ("mos65xx", "m6502", "6502", "65c02", "65816")),
)


def iter_source_files(root: str, suffixes: tuple[str, ...]) -> Iterable[str]:
    if not os.path.exists(root):
        return
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(suffixes):
                yield os.path.join(dirpath, filename)


def arch_from_path(path: str, default: str | None = None) -> str | None:
    text = path.replace(os.sep, "/").lower()
    for arch, aliases in ARCH_ALIASES:
        if any(f"/{alias}/" in text or f"/{alias}" in text or alias in text for alias in aliases):
            return arch
    return default


def clean_c_line(line: str) -> str:
    return line.split("//", 1)[0].split(";", 1)[0].strip()


def parse_int(token: str) -> int | None:
    text = token.strip().rstrip(",")
    try:
        return int(text, 0)
    except ValueError:
        if text.lower().endswith("h"):
            try:
                return int(text[:-1], 16)
            except ValueError:
                return None
    return None


def byte_value(token: str) -> int | None:
    text = token.strip().rstrip(",").lower()
    if text.endswith("h"):
        text = text[:-1]
    if text.startswith("0x"):
        text = text[2:]
    if len(text) == 2 and all(ch in "0123456789abcdef" for ch in text):
        return int(text, 16)
    return None


def token_layout(tokens: Iterable[str]) -> list:
    layout = []
    for raw in tokens:
        token = raw.strip().strip("[],{}()")
        if not token or token in {":", "|"}:
            continue
        if _HEX_RUN.match(token) and len(token) % 2 == 0:
            layout.extend(Fixed(8, int(token[index:index + 2], 16))
                          for index in range(0, len(token), 2))
            continue
        byte = byte_value(token)
        if byte is not None:
            layout.append(Fixed(8, byte))
            continue
        if _looks_like_operand(token):
            layout.append(Operand(_field_name(token), token, _operand_width(token), _operand_type(token)))
    return layout


def _looks_like_operand(token: str) -> bool:
    low = token.lower()
    return (
        low.startswith("/")
        or "#" in low
        or low in {"ib", "iw", "id", "iq", "cb", "cw", "cd", "rb", "rw", "rd", "rel8", "rel32"}
        or low.startswith(("imm", "disp", "rel", "modrm", "sib", "rm", "reg"))
    )


def _field_name(token: str) -> str:
    return re.sub(r"\W+", "_", token.strip("/#")).strip("_") or "op"


def _operand_width(token: str) -> int:
    low = token.lower()
    if any(mark in low for mark in ("iq", "64", "qword")):
        return 64
    if any(mark in low for mark in ("id", "cd", "rel32", "32", "dword")):
        return 32
    if any(mark in low for mark in ("iw", "cw", "16", "word")):
        return 16
    return 8


def _operand_type(token: str) -> str:
    low = token.lower()
    if low.startswith(("r", "reg", "rm")) or low.startswith("/"):
        return "GPR"
    return "IMM"


def fields_from_layout(layout: list) -> dict:
    fields: dict[str, object] = {}
    for segment in layout:
        if not isinstance(segment, Operand):
            continue
        name = segment.name.lower()
        if name in {"rd", "rs1", "rs2", "rn", "rm", "rt"}:
            fields[name] = BitVec(segment.width or 5, 0)
        elif "imm" in name or "disp" in name:
            fields.setdefault("imm", BitVec(segment.width or 1, 0))
    return fields


def raw_record(mnemonic: str, bank_id: str, arch_hint: str | None, layout: list,
               isa_ext: str = "base", encoding_class: str = "variable",
               width: object = "variable", **meta) -> RawRecord:
    return RawRecord(
        mnemonic=mnemonic.strip().lower(),
        arch_hint=arch_hint,
        isa_ext=isa_ext or "base",
        encoding_class=encoding_class,
        bank_id=bank_id,
        layout=layout,
        width=width,
        fields=fields_from_layout(layout),
        meta={key: value for key, value in meta.items() if value is not None},
    )
