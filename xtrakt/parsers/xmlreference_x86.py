"""L3 — ref.x86asm.net XML opcode-table parser (BANKS.yaml xmlreference-x86).

Source: ``x86reference.xml`` — a structured one-byte + two-byte opcode map
(DTD/XSD-validated). Shape::

    x86reference
      one-byte / two-byte
        pri_opcd[value]      primary opcode byte (hex)
          entry
            syntax{ mnem, dst, src }
            grp1 / grp2 / grp3   semantic category tags
            modif_f / def_f      flag read / write sets
            note

``pri_opcd@value`` -> Fixed(8) opcode byte; ``syntax/mnem`` -> mnemonic;
``dst``/``src`` -> operand slots (carrying @type: gen/b/vqp/...). grp1..3 ->
category; modif_f/def_f -> flags_read/flags_write. x86-64 variable width ->
decode_schematic=True (§6.2). ElementTree (stdlib) — lxml not required.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import ClassVar

from ..cir import RawRecord
from ..pcode.emitter import Fixed, Operand
from .base import SourceParser, ParseResult, register_parser

# @type attr -> (slot name, width, op_type). 'b'/'vqp' are width-qualified
# general operands; the rest are abstract operand classes.
_OP_TYPE = {
    "gen": ("dst", 8, "GPR"),
    "b": ("dst", 8, "GPR"),
    "vqp": ("dst", 16, "GPR"),
    "vds": ("dst", 32, "GPR"),
    "1": ("imm", 8, "IMM"),
    "is": ("imm", 8, "IMM"),
    "iv": ("imm", 16, "IMM"),
}


def _operand(slot: str, type_attr: str | None) -> Operand | None:
    if not type_attr:
        return None
    name, w, t = _OP_TYPE.get(type_attr, (slot, 8, "GPR"))
    return Operand(slot, name, w, t)


def _flags(spec: ET.Element | None) -> list[str]:
    if spec is None or not (spec.text or "").strip():
        return []
    return [t for t in spec.text.strip().split() if t and t != "0"]


@register_parser
class XmlReferenceParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["xmlreference-x86"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        path = os.path.join(root, "x86reference.xml")
        if not os.path.exists(path):
            return ParseResult(note="x86reference.xml not found")
        tree = ET.parse(path)
        recs: list[RawRecord] = []
        partial = 0
        for section in ("one-byte", "two-byte"):
            sec = tree.find(section)
            if sec is None:
                continue
            for opcd in sec.findall("pri_opcd"):
                value = (opcd.get("value") or "").strip()
                if not value:
                    partial += 1
                    continue
                try:
                    byte = int(value, 16)
                except ValueError:
                    partial += 1
                    continue
                for entry_el in opcd.findall("entry"):
                    rec = self._record(entry_el, byte, section)
                    if rec is None:
                        partial += 1
                        continue
                    recs.append(rec)
        return ParseResult(records=recs, partial=partial,
                           note=f"{len(recs)} x86 entries from {section}")

    @staticmethod
    def _record(entry_el: ET.Element, byte: int, section: str) -> RawRecord | None:
        syn = entry_el.find("syntax")
        if syn is None:
            return None
        mnem_el = syn.find("mnem")
        if mnem_el is None or not (mnem_el.text or "").strip():
            return None
        mnem = mnem_el.text.strip().lower()
        layout: list = [Fixed(8, byte)]
        fields: dict = {}
        for slot in ("dst", "src"):
            el = syn.find(slot)
            if el is None:
                continue
            op = _operand(slot, el.get("type"))
            if op is not None:
                layout.append(op)
        category = " ".join((entry_el.find(f"grp{i}").text or "").strip()
                            for i in (1, 2, 3)
                            if entry_el.find(f"grp{i}") is not None
                            and (entry_el.find(f"grp{i}").text or "").strip())
        return RawRecord(
            mnemonic=mnem,
            arch_hint="x86-64", isa_ext="base",
            encoding_class="prefix-modrm", bank_id="xmlreference-x86",
            layout=layout, width="variable",
            fields=fields,
            meta={"opcode_byte": f"{byte:02x}", "section": section,
                  "category": category or None,
                  "flags_read": _flags(entry_el.find("modif_f")) or None,
                  "flags_write": _flags(entry_el.find("def_f")) or None},
        )
