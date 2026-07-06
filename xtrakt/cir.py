"""CIR: Canonical Intermediate Representation (XTRAKT.md §3).

Pure value objects. Every backend (de)serializes the same canonical doc via
``to_doc`` / ``from_doc``; this single contract is the operational basis of
backend agnosticism and the §14 round-trip guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Iterator, Optional, Union

# FieldValue is the union of JSON-native values plus BitVec (§3.1).
FieldValue = Any

# ───────────────────────────── BitVec ─────────────────────────────


class BitVec:
    """Fixed-width bitvector. Identity = (width, value)."""

    __slots__ = ("width", "value")

    def __init__(self, width: int, value: int = 0):
        if width < 0:
            raise ValueError(f"BitVec width must be >= 0, got {width}")
        self.width = int(width)
        self.value = int(value) & ((1 << self.width) - 1) if self.width else 0

    # ── constructors ──
    @classmethod
    def from_hex(cls, hex_str: str, width: Optional[int] = None) -> "BitVec":
        h = hex_str.strip().lower().removeprefix("0x")
        w = width if width is not None else 4 * len(h)
        return cls(w, int(h, 16))

    @classmethod
    def from_bin(cls, bin_str: str) -> "BitVec":
        b = bin_str.replace("_", "")
        return cls(len(b), int(b, 2))

    # ── projection ──
    @property
    def hex(self) -> str:
        if self.width == 0:
            return "0"
        nib = (self.width + 3) // 4
        return format(self.value, f"0{nib}x")

    def __int__(self) -> int:
        return self.value

    def __eq__(self, o: object) -> bool:
        return isinstance(o, BitVec) and o.width == self.width and o.value == self.value

    def __hash__(self) -> int:
        return hash((self.width, self.value))

    def __repr__(self) -> str:
        return f"BitVec({self.width}, 0x{self.value:x})"

    def to_doc(self) -> dict:
        return {"width": self.width, "hex": self.hex}

    @classmethod
    def from_doc(cls, d: dict) -> "BitVec":
        return cls.from_hex(d["hex"], width=d.get("width"))


def bv(width: int, value: int = 0) -> BitVec:
    return BitVec(width, value)


def ones(width: int) -> int:
    """Low ``width`` bits set."""
    return (1 << width) - 1 if width > 0 else 0


def is_bv(o: Any) -> bool:
    return isinstance(o, BitVec)


# ──────────────────────── FieldValue coercion ──────────────────────

# FieldValue = str | int | bool | list | dict | BitVec. BitVec is the only
# non-JSON-native carrier; everything else round-trips untouched.


def coerce_field(raw: Any, kind: Optional[str] = None, width: Any = None) -> Any:
    """Coerce a raw value into a JSON-native FieldValue (or BitVec).

    ``kind`` follows RECORDS.yaml field kinds: str|enum|list|int|bool|bv|pcode|
    struct|<operand-type>. For ``bv`` the value is normalized to a BitVec whose
    width is taken from ``width`` (int) when determinable.
    """
    if raw is None:
        return None
    if isinstance(raw, BitVec):
        return raw
    k = (kind or "").lower()
    if k == "bv":
        return _coerce_bv(raw, width)
    if k in ("list",) or isinstance(raw, (list, tuple)):
        return [coerce_field(x) for x in raw]
    if isinstance(raw, dict):
        return {str(kk): coerce_field(vv) for kk, vv in raw.items()}
    if isinstance(raw, bool):  # before int
        return raw
    if isinstance(raw, int):
        return raw
    # str / everything else
    return str(raw) if not isinstance(raw, str) else raw


def _coerce_bv(raw: Any, width: Any) -> BitVec:
    if isinstance(raw, BitVec):
        return raw
    if isinstance(raw, dict) and ("hex" in raw or "width" in raw):
        return BitVec.from_doc(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s.startswith("0x") or all(c in "0-9a-f" for c in s):
            w = _width_of(width)
            return BitVec.from_hex(s.removeprefix("0x"), width=w)
        if s.startswith("#x"):
            return BitVec.from_hex(s[2:], width=_width_of(width))
        if s.startswith("#b"):
            return BitVec.from_bin(s[2:])
        # plain decimal
        try:
            return BitVec(_width_of(width) or 1, int(s, 0))
        except ValueError:
            return BitVec(0, 0)
    if isinstance(raw, int):
        return BitVec(_width_of(width) or max(1, raw.bit_length()), raw)
    return BitVec(0, 0)


def _width_of(width: Any) -> Optional[int]:
    if width is None:
        return None
    if isinstance(width, bool):
        return None
    if isinstance(width, int):
        return width
    s = str(width).strip().strip("{}")
    # forms like "8", "8-24", "{0,8,16,32}", "variable"
    if s.isdigit():
        return int(s)
    # take the first integer token if present
    for tok in s.replace("-", " ").replace(",", " ").split():
        if tok.isdigit():
            return int(tok)
    return None


# ──────────────────────── canonical doc ────────────────────────────

# record_base field order (RECORDS.yaml). Drives ordered serialization.
_BASE_FIELDS = (
    "mnemonic",
    "aliases",
    "isa_ext",
    "cpuid",
    "encoding_class",
    "encoding_function",
    "decode_mask",
    "decode_match",
    "semantics",
    "flags_read",
    "flags_write",
    "memory_access",
    "category",
    "privilege",
)


def _field_to_doc(v: Any) -> Any:
    if isinstance(v, BitVec):
        return v.to_doc()
    if isinstance(v, (list, tuple)):
        return [_field_to_doc(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _field_to_doc(x) for k, x in v.items()}
    return v


def _field_from_doc(v: Any) -> Any:
    if isinstance(v, dict) and "width" in v and "hex" in v and len(v) == 2:
        return BitVec.from_doc(v)
    if isinstance(v, list):
        return [_field_from_doc(x) for x in v]
    if isinstance(v, dict):
        return {k: _field_from_doc(x) for k, x in v.items()}
    return v


# ──────────────────────── InstructionRecord ────────────────────────


@dataclass
class InstructionRecord:
    arch: str
    mnemonic: str
    isa_ext: str
    encoding_class: str
    encoding_function: str
    decode_mask: Optional[BitVec] = None
    decode_match: Optional[BitVec] = None
    semantics: Optional[str] = None
    aliases: Optional[list[str]] = None
    cpuid: Optional[str] = None
    flags_read: Optional[list[str]] = None
    flags_write: Optional[list[str]] = None
    memory_access: Optional[str] = None
    category: Optional[str] = None
    privilege: Optional[str] = None
    fields: dict[str, Any] = dc_field(default_factory=dict)
    source_banks: list[str] = dc_field(default_factory=list)
    decode_schematic: bool = False

    # ── identity / dedup (§3.2) ──
    @property
    def operand_signature(self) -> str:
        """Stable signature over arch fields, excluding derived/const bits."""
        parts = []
        for k in sorted(self.fields):
            v = self.fields[k]
            if isinstance(v, BitVec):
                parts.append(f"{k}:bv{v.width}")
            elif isinstance(v, list):
                parts.append(f"{k}:list{len(v)}")
            elif isinstance(v, dict):
                parts.append(f"{k}:dict")
            else:
                parts.append(f"{k}:{type(v).__name__}")
        return ",".join(parts)

    @property
    def key(self) -> tuple:
        return (self.arch, self.mnemonic, self.encoding_class,
                self.operand_signature, self.isa_ext)

    def clone(self) -> "InstructionRecord":
        import copy
        return copy.deepcopy(self)

    # ── (de)serialization ──
    def to_doc(self) -> dict:
        d: dict[str, Any] = {"arch": self.arch}
        for f in _BASE_FIELDS:
            val = getattr(self, f)
            if f in ("decode_mask", "decode_match"):
                d[f] = val.to_doc() if val is not None else None
            else:
                d[f] = _field_to_doc(val)
        d["fields"] = {k: _field_to_doc(v) for k, v in self.fields.items()}
        d["source_banks"] = list(self.source_banks)
        d["decode_schematic"] = bool(self.decode_schematic)
        return d

    @classmethod
    def from_doc(cls, d: dict) -> "InstructionRecord":
        kw: dict[str, Any] = {"arch": d.get("arch", "")}
        for f in _BASE_FIELDS:
            if f not in d:
                continue
            val = d[f]
            if f in ("decode_mask", "decode_match"):
                kw[f] = BitVec.from_doc(val) if val else None
            else:
                kw[f] = _field_from_doc(val)
        kw["fields"] = {k: _field_from_doc(v) for k, v in (d.get("fields") or {}).items()}
        kw["source_banks"] = list(d.get("source_banks") or [])
        kw["decode_schematic"] = bool(d.get("decode_schematic", False))
        return cls(**kw)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, InstructionRecord) and self.to_doc() == o.to_doc()

    def __hash__(self) -> int:
        return hash(self.key)


# ───────────────────────── RawRecord / Reject ──────────────────────


@dataclass
class RawRecord:
    """Source-shaped, pre-schema record (L3 output). Loose by design."""

    fields: dict[str, Any] = dc_field(default_factory=dict)
    # carries everything L4 needs to resolve schema + emit P-Code:
    mnemonic: str = ""
    fmt: str = ""                       # sub-format / operand form tag
    arch_hint: Optional[str] = None     # bank's declared arch (override)
    isa_ext: str = ""
    encoding_class: Optional[str] = None
    bank_id: str = ""
    # field layout for L5 (MSB-first); list of FieldLayout items
    layout: list = dc_field(default_factory=list)
    width: Any = None                   # int | "variable"
    semantics: Optional[str] = None
    # free-form passthrough for normalizer coercion
    meta: dict[str, Any] = dc_field(default_factory=dict)

    def get(self, k: str, default=None):
        return self.fields.get(k, default)


@dataclass
class Reject:
    """A record rejected by L4, with reason + provenance."""

    reason: str
    bank_id: str = ""
    mnemonic: str = ""
    key: Any = None
    detail: Any = None
