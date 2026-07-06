"""L3 — AsmJIT asmdb JSON parser (XTRAKT.md §4.1, BANKS.yaml asmjit-db).

Real parser for the three pipe-separated ``op`` layouts:
  - isa_aarch64.json:  ``data[].op``  = MSB-first ``00011010|000|Rm|..``  (32-bit)
  - isa_aarch32.json:  ``data[].a32|t32|t16`` = same layout               (32/16-bit)
  - isa_x86.json:      ``instructions[].op`` = ``E4 ib`` byte+operand     (variable)

Fixed-width arches (aarch64, arm-a32) yield real field layouts -> real
(mask, match). x86 is variable -> decode_schematic=True (§6.2).
"""
from __future__ import annotations

import json
import os
import re
from typing import ClassVar

from ..cir import RawRecord, BitVec
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser

_GPR = {"Rm", "Rn", "Rd", "Rs", "Rt", "Ra", "Rt2", "RdHi", "RdLo"}
_BARE_WIDTH = {"cond": 4, "sz": 2, "op": 1, "s": 1, "Q": 1, "L": 1}


def _segment(tok: str, gpr_width: int):
    tok = tok.strip()
    if all(c in "01" for c in tok) and tok:                 # fixed binary run
        return Fixed(len(tok), int(tok, 2))
    m = re.match(r"^([A-Za-z_]\w*)\[(\d+)(?::(\d+))?\]$", tok)
    if m:
        name = m.group(1)
        hi = int(m.group(2))
        lo = int(m.group(3) or m.group(2))
        return Operand(name, name, abs(hi - lo) + 1, _op_type(name))
    if ":" in tok:
        name, w = tok.split(":", 1)
        return Operand(name, name, int(w), _op_type(name))
    # bare named field
    w = _BARE_WIDTH.get(tok, gpr_width)
    return Operand(tok, tok, w, _op_type(tok))


def _op_type(name: str) -> str:
    n = name.lower()
    if n in {"cond"}:
        return "COND"
    if any(k in n for k in ("imm", "sop", "option", "sz", "n", "fb", "msz",
                            "op", "s", "q", "l")):
        return "IMM"
    return "GPR"


def _layout_from_opstring(op: str, gpr_width: int):
    return [_segment(t, gpr_width) for t in op.split("|") if t]


def _fields_from_layout(layout) -> dict:
    out: dict[str, object] = {}
    for seg in layout:
        if isinstance(seg, Operand):
            nm = seg.name.lower()
            if nm in {"rd", "rn", "rs", "rm", "rt", "ra"}:
                out[nm] = BitVec(seg.width, 0)
            elif "imm" in nm:
                out.setdefault("imm", BitVec(seg.width, 0))
    return out


def _mnemonic(inst: str) -> str:
    return inst.strip().split()[0].split("|")[0] if inst.strip() else ""


@register_parser
class AsmjitJsonParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["asmjit-db"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        recs: list[RawRecord] = []
        partial = 0
        recs, p1 = self._do_aarch64(root, recs); partial += p1
        recs, p2 = self._do_aarch32(root, recs); partial += p2
        recs, p3 = self._do_x86(root, recs); partial += p3
        return ParseResult(records=recs, partial=partial)

    # ── aarch64 (fixed-32) ──
    def _do_aarch64(self, root, recs):
        f = os.path.join(root, "isa_aarch64.json")
        if not os.path.exists(f):
            return recs, 0
        d = json.load(open(f))
        partial = 0
        for grp in d.get("instructions", []):
            for item in (grp.get("data") or []):
                op = item.get("op")
                if not op:
                    partial += 1; continue
                layout = _layout_from_opstring(op, 5)
                recs.append(RawRecord(
                    mnemonic=_mnemonic(item.get("inst", "")),
                    arch_hint="aarch64", isa_ext="base",
                    encoding_class="fixed-32", bank_id="asmjit-db",
                    layout=layout, width=32,
                    fields=_fields_from_layout(layout),
                ))
        # SME supplement
        fsme = os.path.join(root, "isa_aarch64_sme.json")
        if os.path.exists(fsme):
            d2 = json.load(open(fsme))
            for grp in d2.get("instructions", []):
                for item in (grp.get("data") or []):
                    op = item.get("op")
                    if not op:
                        continue
                    recs.append(RawRecord(
                        mnemonic=_mnemonic(item.get("inst", "")),
                        arch_hint="aarch64", isa_ext="sme",
                        encoding_class="fixed-32", bank_id="asmjit-db",
                        layout=_layout_from_opstring(op, 5), width=32,
                        fields=_fields_from_layout(_layout_from_opstring(op, 5)),
                    ))
        return recs, partial

    # ── aarch32 (A32/T32; fixed-32, T16=16) ──
    def _do_aarch32(self, root, recs):
        f = os.path.join(root, "isa_aarch32.json")
        if not os.path.exists(f):
            return recs, 0
        d = json.load(open(f))
        partial = 0
        for grp in d.get("instructions", []):
            for item in (grp.get("data") or []):
                form = next((k for k in ("a32", "t32", "t16") if k in item), None)
                if not form:
                    partial += 1; continue
                layout = _layout_from_opstring(item[form], 4)
                width = 16 if form == "t16" else 32
                recs.append(RawRecord(
                    mnemonic=_mnemonic(item.get("inst", "")),
                    arch_hint="arm-a32", isa_ext=form,
                    encoding_class="fixed-32", bank_id="asmjit-db",
                    layout=layout, width=width,
                    fields=_fields_from_layout(layout),
                ))
        return recs, partial

    # ── x86 (variable) ──
    def _do_x86(self, root, recs):
        f = os.path.join(root, "isa_x86.json")
        if not os.path.exists(f):
            return recs, 0
        d = json.load(open(f))
        partial = 0
        for grp in d.get("instructions", []):
            for item in (grp.get("instructions") or []):
                op = item.get("op")
                formkey = next((k for k in ("any", "asz", "osz", "rex", "rep")
                                if k in item), None)
                inst = item.get(formkey) if formkey else ""
                if not op:
                    partial += 1; continue
                layout = self._x86_layout(op)
                recs.append(RawRecord(
                    mnemonic=_mnemonic(inst or ""),
                    arch_hint="x86-64", isa_ext="base",
                    encoding_class="prefix-modrm", bank_id="asmjit-db",
                    layout=layout, width="variable",
                    fields={},
                ))
        return recs, partial

    @staticmethod
    def _x86_layout(op: str):
        """Hex bytes -> Fixed(8); operand markers -> Operand. Fixed opcode slice."""
        _OPW = {"ib": 8, "iw": 16, "id": 32, "iq": 64, "iw2": 16, "cb": 8, "cw": 16,
                "cd": 32, "/r": 8}
        out = []
        for tok in op.split():
            if all(c in "0123456789abcdefABCDEF" for c in tok) and len(tok) <= 2:
                out.append(Fixed(8, int(tok, 16)))
            else:
                w = _OPW.get(tok.rstrip(","), 8)
                out.append(Operand(tok.replace("/", "_"), tok, w, "IMM"))
        return out
