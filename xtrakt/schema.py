"""L2 — schema load: RECORDS.yaml -> record_base, ArchSchema[] (XTRAKT.md §2.2).

Builds the per-arch record shape and the bank->arch membership maps used by
L3/L4 to resolve an arch from a bank id and to gate semantics attachment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .manifest import _load_yaml


@dataclass
class FieldSpec:
    name: str
    kind: str = "str"
    width: Any = None
    required: bool = False
    note: str = ""
    access: str = ""
    operand: str = ""          # operand-type tag if kind is an operand (GPR/IMM/...)

    @property
    def fixed_width(self) -> Optional[int]:
        return _parse_width(self.width)


@dataclass
class RecordBase:
    fields: list[FieldSpec] = field(default_factory=list)

    @property
    def required(self) -> set[str]:
        return {f.name for f in self.fields if f.required}

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.fields]


@dataclass
class ArchSchema:
    arch: str
    full_name: str = ""
    encoding_class: str = ""
    width_bits: Any = None
    operand_types: list[str] = field(default_factory=list)
    encoding_banks: list[str] = field(default_factory=list)
    semantics_banks: list[str] = field(default_factory=list)
    record: list[FieldSpec] = field(default_factory=list)
    encoding_function: str = ""
    semantics: str = ""
    notes: str = ""

    # ── width projection ──
    @property
    def fixed_width(self) -> Optional[int]:
        """Integer instruction width, or None for variable/packet/stack encodings."""
        return _parse_width(self.width_bits)

    @property
    def is_variable(self) -> bool:
        s = str(self.width_bits).lower()
        return "variable" in s or "packet" in s or "stack" in s

    # ── record-field layout template (MSB-first, §2.2) ──
    @property
    def layout_template(self) -> list[FieldSpec]:
        """Arch record[] in declared order = MSB-first field layout template."""
        return list(self.record)

    def field_by_name(self, name: str) -> Optional[FieldSpec]:
        for f in self.record:
            if f.name == name:
                return f
        return None


# ──────────────────────────── parsing ────────────────────────────

def _parse_width(w: Any) -> Optional[int]:
    """Extract a single integer width from RECORDS.yaml width forms.

    32 -> 32; "variable" -> None; "{16 (T16), 32 (T32, A32)}" -> 32 (largest);
    "{0,8,16,32}" -> 32; "8-24" -> 8 (lower, conservative for mask slice).
    """
    if w is None:
        return None
    if isinstance(w, bool):
        return None
    if isinstance(w, int):
        return w
    s = str(w).strip().lower()
    if not s or "variable" in s or "packet" in s or "stack" in s:
        return None
    nums = [int(t) for t in re.findall(r"\d+", s.replace("-", " "))]
    if not nums:
        return None
    # forms with '-' denote a range (fixed slice lower bound); else take max
    return max(nums) if "-" not in str(w) else min(nums)


def _spec(d: dict) -> FieldSpec:
    kind = str(d.get("kind", "str"))
    name = str(d.get("name", ""))
    # multi-name shorthand: "{name: rn, rd, kind: GPR, width: 5}"
    return FieldSpec(
        name=name,
        kind=kind,
        width=d.get("width"),
        required=bool(d.get("required", False)),
        note=str(d.get("note", "") or ""),
        access=str(d.get("access", "") or ""),
        operand=kind,   # kinds like GPR/IMM/COND are operand-type tags
    )


def _expand_specs(item: dict) -> list[FieldSpec]:
    """Expand a record[] entry; some entries use `name: "rn, rd"` shorthand."""
    name = str(item.get("name", ""))
    specs = _spec(item)
    if "," in name and " " not in name.strip().replace(",", ""):
        # split sibling fields sharing kind/width
        out = []
        for nm in [n.strip() for n in name.split(",") if n.strip()]:
            s = FieldSpec(name=nm, kind=specs.kind, width=specs.width,
                          required=specs.required, note=specs.note,
                          access=specs.access, operand=specs.operand)
            out.append(s)
        return out
    return [specs]


def load_schema(records_path: str) -> tuple[RecordBase, list[ArchSchema]]:
    """Load RECORDS.yaml -> (record_base, [ArchSchema])."""
    data = _load_yaml(records_path)
    rb_raw = data.get("record_base", {}) or {}
    base_fields = rb_raw.get("fields", []) or []
    base = RecordBase(fields=[_spec(f) for f in base_fields])

    arches: list[ArchSchema] = []
    for a in data.get("architectures", []) or []:
        rec_specs: list[FieldSpec] = []
        for item in (a.get("record", []) or []):
            rec_specs.extend(_expand_specs(item))
        arches.append(ArchSchema(
            arch=str(a.get("arch", "")),
            full_name=str(a.get("full_name", "") or ""),
            encoding_class=str(a.get("encoding_class", "") or ""),
            width_bits=a.get("width_bits"),
            operand_types=list(a.get("operand_types", []) or []),
            encoding_banks=list(a.get("encoding_banks", []) or []),
            semantics_banks=list(a.get("semantics_banks", []) or []),
            record=rec_specs,
            encoding_function=str(a.get("encoding_function", "") or ""),
            semantics=str(a.get("semantics", "") or ""),
            notes=str(a.get("notes", "") or ""),
        ))
    return base, arches


# ──────────────────────────── bank maps ────────────────────────────

@dataclass
class BankArchMap:
    """bank_id -> {arch: role} where role in {'enc','sem','both'}."""
    by_bank: dict[str, dict[str, str]] = field(default_factory=dict)

    def arches(self, bank_id: str) -> list[str]:
        return list(self.by_bank.get(bank_id, {}).keys())

    def role(self, bank_id: str, arch: str) -> Optional[str]:
        return self.by_bank.get(bank_id, {}).get(arch)

    def is_semantics_bank(self, bank_id: str, arch: str) -> bool:
        r = self.role(bank_id, arch)
        return r in ("sem", "both")

    def is_encoding_bank(self, bank_id: str, arch: str) -> bool:
        r = self.role(bank_id, arch)
        return r in ("enc", "both")


def bank_arch_map(arches: list[ArchSchema]) -> BankArchMap:
    m = BankArchMap()
    for sc in arches:
        for b in sc.encoding_banks:
            cur = m.by_bank.setdefault(b, {})
            cur[sc.arch] = "both" if cur.get(sc.arch) == "sem" else "enc"
        for b in sc.semantics_banks:
            cur = m.by_bank.setdefault(b, {})
            cur[sc.arch] = "both" if cur.get(sc.arch) == "enc" else "sem"
    return m


def resolve_arch(raw_arch: Optional[str], bank_id: str,
                 bam: BankArchMap, by_name: dict[str, ArchSchema]) -> Optional[ArchSchema]:
    """§13: arch resolution never guesses. Order: raw hint > single-arch bank."""
    if raw_arch:
        sc = by_name.get(raw_arch)
        if sc:
            return sc
        # tolerate aliases
        for k, v in by_name.items():
            if raw_arch.lower() in (k.lower(), v.full_name.lower()):
                return v
    cand = bam.arches(bank_id)
    if len(cand) == 1:
        return by_name.get(cand[0])
    return None     # ambiguous or unknown -> reject


def schema_index(arches: list[ArchSchema]) -> dict[str, ArchSchema]:
    return {sc.arch: sc for sc in arches}
