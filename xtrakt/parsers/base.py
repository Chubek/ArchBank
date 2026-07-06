"""L3 — source parsers (XTRAKT.md §4). One parser (or one shared format-family
parser) per bank; produces raw, source-shaped RawRecords. Parsers carry format
knowledge only — schema knowledge is L4's job. Registry is the extension point.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Iterator

from ..manifest import BankEntry
from ..cir import RawRecord

PARSERS: dict[str, type["SourceParser"]] = {}


@dataclass
class ParseResult:
    records: list[RawRecord] = field(default_factory=list)
    partial: int = 0          # count of malformed/skipped lines
    note: str = ""


class SourceParser(ABC):
    bank_ids: ClassVar[list[str]] = []
    spec_only: ClassVar[bool] = False   # yields 0 instruction records

    @abstractmethod
    def parse(self, entry: BankEntry, base_dir: str) -> ParseResult: ...


def register_parser(cls):
    for bid in cls.bank_ids:
        PARSERS[bid] = cls
    return cls


def parser_for(bank_id: str) -> type[SourceParser]:
    """Resolve a bank id to its parser class. Unwired banks fall back to
    NotImplementedParser (zero records, explicit note) so the run is isolated
    and the gap is surfaced in the report rather than silently dropped."""
    if bank_id in PARSERS:
        return PARSERS[bank_id]
    from .spec_only import NotImplementedParser
    return NotImplementedParser


# eager-import concrete parsers -> populates the registry
from . import (  # noqa: E402,F401
    riscv_opcodes,
    asmjit_json,
    x86_dataset,
    ctable,
    nasm_data,
    tablegen,
    source_scan,
    metadata_only,
    spec_only,
    courtier_json,
    xmlreference_x86,
    wabt_wasm,
    smlnj_targets,
    hotspot_adl,
)
