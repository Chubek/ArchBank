"""L4 — normalizer + dedup/merge (XTRAKT.md §5, §3.2).

Coerces a RawRecord against its ArchSchema into an InstructionRecord, emits
the encoding_function (L5), derives the decode signature (L6), and attaches
best-effort semantics. Validation is declarative against RECORDS.yaml, never a
hardcoded switch. The MergeIndex enforces the §3.2 union/flag contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from .cir import (
    InstructionRecord,
    RawRecord,
    Reject,
    BitVec,
    coerce_field,
)
from .schema import ArchSchema, BankArchMap
from .pcode.emitter import emit_encoding, Operand, Fixed
from .pcode.decoder import decode_signature
from .pcode import transcoders

REQUIRED_BASE = {"mnemonic", "isa_ext", "encoding_class"}


@dataclass
class Normalizer:
    bam: BankArchMap
    precedence: Callable[[str], int] = field(default=lambda _b: 0)

    # ── main entry ──
    def normalize(self, raw: RawRecord, schema: ArchSchema,
                  bank_id: str) -> InstructionRecord | Reject:
        mnem = (raw.mnemonic or raw.fields.get("mnemonic") or "").strip()
        if not mnem:
            return Reject("missing mnemonic", bank_id)

        # ── 3. required base set ──
        isa_ext = (raw.isa_ext or raw.fields.get("isa_ext") or "").strip()
        enc_class = (raw.encoding_class or raw.fields.get("encoding_class")
                     or schema.encoding_class or "").strip()
        missing = [n for n, v in [("mnemonic", mnem),
                                  ("isa_ext", isa_ext),
                                  ("encoding_class", enc_class)] if not v]
        if missing:
            return Reject(f"missing required base field(s): {missing}",
                          bank_id, mnem)

        # ── 4. encoding_function (mandatory) ──
        enc, schematic_by_layout = self._encoding(raw, schema)
        if enc is None:
            return Reject("no encoding_function (no layout, no prebuilt)",
                          bank_id, mnem)

        width = self._width(raw, schema)
        dec = decode_signature(enc, width)

        # ── 2. coerce arch fields per schema.record[] ──
        fields = self._coerce_fields(raw, schema)

        rec = InstructionRecord(
            arch=schema.arch,
            mnemonic=mnem,
            isa_ext=isa_ext or "base",
            encoding_class=enc_class,
            encoding_function=enc,
            decode_mask=dec.mask,
            decode_match=dec.match,
            semantics=None,
            aliases=_as_list(raw.fields.get("aliases")),
            cpuid=(raw.fields.get("cpuid") or None),
            flags_read=_as_list(raw.fields.get("flags_read")),
            flags_write=_as_list(raw.fields.get("flags_write")),
            memory_access=(raw.fields.get("memory_access") or None),
            category=(raw.fields.get("category") or None),
            privilege=(raw.fields.get("privilege") or None),
            fields=fields,
            source_banks=[bank_id],
            decode_schematic=dec.schematic,
        )
        # stamp schematic note into fields for downstream visibility
        if dec.schematic and dec.note:
            rec.fields.setdefault("_decode_note", dec.note)

        # ── 5. semantics (only from a semantics_bank with a transcoder) ──
        if self.bam.is_semantics_bank(bank_id, schema.arch):
            rec.semantics = self._semantics(raw, schema, bank_id)

        return rec

    # ── encoding source ──
    def _encoding(self, raw: RawRecord, schema: ArchSchema):
        layout = getattr(raw, "layout", None) or []
        if layout:
            op_decls = [(o.operand or o.name, o.op_type or "IMM", o.width)
                        for o in layout if isinstance(o, Operand)]
            try:
                return emit_encoding(raw.mnemonic, layout,
                                     self._width(raw, schema), op_decls), True
            except ValueError:
                return None, False
        pre = raw.fields.get("encoding_function") or raw.meta.get("encoding_function")
        if pre:
            return str(pre), False
        return None, False

    def _width(self, raw: RawRecord, schema: ArchSchema):
        if raw.width is not None:
            return raw.width
        w = schema.fixed_width
        return w if w is not None else "variable"

    # ── field coercion ──
    def _coerce_fields(self, raw: RawRecord, schema: ArchSchema) -> dict:
        out: dict[str, Any] = {}
        for spec in schema.record:
            if spec.name not in raw.fields:
                continue
            kind = spec.kind
            out[spec.name] = coerce_field(raw.fields[spec.name], kind, spec.width)
        # carry any extra passthrough fields the parser supplied
        for k, v in raw.fields.items():
            if k in out or k in REQUIRED_BASE or k in (
                    "aliases", "cpuid", "flags_read", "flags_write",
                    "memory_access", "category", "privilege", "encoding_function"):
                continue
            out.setdefault(k, coerce_field(v))
        return out

    # ── semantics ──
    def _semantics(self, raw: RawRecord, schema: ArchSchema, bank_id: str):
        if raw.semantics:
            return raw.semantics
        src = raw.meta.get("semantics_source") or raw.meta.get("foreign_semantics")
        form = transcoders.formalism_for(bank_id)
        if src and form:
            return transcoders.transcode(form, src, raw)
        return None


def _as_list(v) -> Optional[list]:
    if v is None:
        return None
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


# ──────────────────────────── merge index ────────────────────────────

@dataclass
class MergeIndex:
    """§3.2 dedup/merge. Union source_banks; keep highest-precedence
    encoding_function/semantics; flag conflicting encodings (never overwrite)."""
    precedence: Callable[[str], int] = field(default=lambda _b: 0)
    _by_key: dict[tuple, InstructionRecord] = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)

    def add(self, rec: InstructionRecord) -> InstructionRecord:
        k = rec.key
        prev = self._by_key.get(k)
        if prev is None:
            self._by_key[k] = rec
            return rec
        return self._merge(prev, rec)

    def _merge(self, prev: InstructionRecord, new: InstructionRecord) -> InstructionRecord:
        kept = prev if self.precedence(prev.source_banks[0]) >= \
            self.precedence(new.source_banks[0]) else new
        other = new if kept is prev else prev

        # union source_banks (dedup, preserve order)
        for b in other.source_banks:
            if b not in kept.source_banks:
                kept.source_banks.append(b)

        # conflicting encoding for one key -> flag, never overwrite
        if kept.encoding_function.strip() != other.encoding_function.strip():
            self.conflicts.append({
                "key": list(kept.key),
                "banks": list(kept.source_banks),
                "reason": "conflicting encoding_function",
            })
        # semantics: prefer kept's if present, else take other's
        if not kept.semantics and other.semantics:
            kept.semantics = other.semantics
        return kept

    def records(self) -> list[InstructionRecord]:
        return list(self._by_key.values())

    def get(self, **flt) -> list[InstructionRecord]:
        out = self.records()
        if "arch" in flt:
            out = [r for r in out if r.arch == flt["arch"]]
        if "mnemonic" in flt:
            out = [r for r in out if r.mnemonic == flt["mnemonic"]]
        return out
