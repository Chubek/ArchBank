"""xtrakt: declarative extraction-and-storage pipeline for ArchBank.

Layered L1..L8 (see XTRAKT.md §1). Package surface re-exports the CIR and
the two registries; everything else is imported by submodule path.
"""
from .cir import (
    BitVec,
    FieldValue,
    InstructionRecord,
    RawRecord,
    Reject,
    bv,
    ones,
    is_bv,
)
from .schema import ArchSchema, RecordBase, FieldSpec, load_schema, bank_arch_map

__all__ = [
    "BitVec",
    "FieldValue",
    "InstructionRecord",
    "RawRecord",
    "Reject",
    "bv",
    "ones",
    "is_bv",
    "ArchSchema",
    "RecordBase",
    "FieldSpec",
    "load_schema",
    "bank_arch_map",
]

__version__ = "1.0.0"
