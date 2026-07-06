"""L3 — riscv-opcodes parser (XTRAKT.md §4.1, BANKS.yaml riscv-opcodes).

Real parser for the canonical RISC-V encoding DB. Line grammar::

    mnemonic operands... hi..lo=val ...

``hi..lo`` are MSB-first inclusive bit indices; ``val`` is hex (0x..) or decimal.
Operand bit-ranges and widths come from ``arg_lut.csv``. Each line becomes one
field layout (MSB-first) -> L5 emits a faithful ``define-encoding``; L6 inverts
it to the canonical (mask, match). Pseudo-op / arch-qualified (``::``) tokens
are skipped so the real mnemonic surfaces.
"""
from __future__ import annotations

import csv
import glob
import os
import re
from typing import ClassVar

from ..cir import RawRecord, BitVec
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser

_ARCH = "riscv"
_GPR = {"rd", "rs1", "rs2", "rs3", "rt", "rd_rs1", "rd_rs1_p", "rd_rs1_n0",
        "rd_p", "rd_n0", "rs1_p"}
_RM = {"rm", "funct3"}


def _load_arg_lut(path: str) -> dict[str, tuple[int, int]]:
    lut: dict[str, tuple[int, int]] = {}
    if not os.path.exists(path):
        return lut
    with open(path, "r", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            row = [c.strip().strip('"') for c in row if c.strip() != ""]
            if len(row) >= 3 and row[1].isdigit() and row[2].isdigit():
                lut[row[0]] = (int(row[1]), int(row[2]))
    return lut


def _ext_from_filename(name: str) -> str:
    base = os.path.basename(name)
    for pre in ("rv32_", "rv64_", "rv_"):
        if base.startswith(pre):
            base = base[len(pre):]
            break
    return base


def _parse_val(tok: str) -> int:
    t = tok.strip().lower()
    if t.startswith("0x"):
        return int(t, 16)
    if t.startswith("0b"):
        return int(t, 2)
    return int(t, 10)


def _op_type(name: str) -> str:
    if name in _GPR or name.startswith("rd") or name.startswith("rs"):
        return "GPR"
    if name in _RM:
        return "RM"
    if name.startswith("csr"):
        return "CSR"
    return "IMM"


def _schema_field(op: str, width: int):
    """Map an operand name to a schema-aligned (field_name, value) for rec.fields."""
    if op in ("rd", "rs1", "rs2", "rs3", "rt"):
        return op, BitVec(width or 5, 0)
    if op in ("rm",):
        return "rm", BitVec(width or 3, 0)
    if "imm" in op:
        return "imm", BitVec(width or 1, 0)
    return None


def _parse_line(line: str, arg_lut: dict[str, tuple[int, int]]):
    """Return (mnemonic, layout, width, fields) or None if unparseable."""
    # strip comment
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    toks = line.split()
    # drop $directives and arch-qualified qualifiers
    clean = [t for t in toks if not t.startswith("$") and "::" not in t]
    if not clean:
        return None
    mnemonic = clean[0]
    operands: list[str] = []
    segs: list[tuple[int, int, object]] = []   # (msb, lsb, seg)
    for t in clean[1:]:
        if "=" in t:
            rng, val = t.split("=", 1)
            if ".." not in rng:
                return None
            hi_s, lo_s = rng.split("..", 1)
            try:
                hi, lo = int(hi_s), int(lo_s)
            except ValueError:
                return None
            msb, lsb = max(hi, lo), min(hi, lo)
            segs.append((msb, lsb, Fixed(msb - lsb + 1, _parse_val(val))))
        else:
            operands.append(t)

    # place operands via arg_lut
    for op in operands:
        rng = arg_lut.get(op)
        if rng is None:
            return None                  # unknown operand slot -> skip line
        msb, lsb = max(rng), min(rng)
        segs.append((msb, lsb, Operand(op, op, msb - lsb + 1, _op_type(op))))

    if not segs:
        return None
    segs.sort(key=lambda s: s[0], reverse=True)     # MSB-first
    # contiguity check
    top = segs[0][0]
    width = top + 1
    cur = width - 1
    layout = []
    for msb, lsb, seg in segs:
        if msb != cur:
            return None                  # gap or overlap -> malformed
        layout.append(seg)
        cur = lsb - 1
    if cur != -1:
        return None                      # low bits uncovered

    fields: dict[str, object] = {}
    for op in operands:
        rng = arg_lut.get(op)
        w = (max(rng) - min(rng) + 1) if rng else 0
        sf = _schema_field(op, w)
        if sf:
            fields[sf[0]] = sf[1]
    return mnemonic, layout, width, fields


@register_parser
class RiscvOpcodesParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["riscv-opcodes"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        arg_lut = _load_arg_lut(os.path.join(root, "arg_lut.csv"))
        files = sorted(glob.glob(os.path.join(root, "extensions", "*")))
        if not files:                                # fallback to top-level rv_*
            files = sorted(glob.glob(os.path.join(root, "rv_*")))
        recs: list[RawRecord] = []
        partial = 0
        for f in files:
            if not os.path.isfile(f):
                continue
            ext = _ext_from_filename(f)
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    parsed = _parse_line(line, arg_lut)
                    if parsed is None:
                        if line.strip() and not line.lstrip().startswith("#"):
                            partial += 1
                        continue
                    mnem, layout, width, fields = parsed
                    recs.append(RawRecord(
                        mnemonic=mnem,
                        arch_hint=_ARCH,
                        isa_ext=ext,
                        encoding_class="fixed-32",
                        bank_id="riscv-opcodes",
                        layout=layout,
                        width=width,
                        fields=dict(fields),
                    ))
        return ParseResult(records=recs, partial=partial,
                           note=f"{len(files)} extension files")
