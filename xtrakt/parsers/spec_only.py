"""L3 — spec-only banks (XTRAKT.md §4.1, §13).

Banks that carry register/feature/category models but no encodings yield zero
Instruction Records by design. The pipeline logs ``yielded=0`` and records
provenance (a known no-op source); the run continues.
"""
from __future__ import annotations
from typing import ClassVar

from .base import SourceParser, ParseResult, register_parser


@register_parser
class SpecOnlyParser(SourceParser):
    bank_ids: ClassVar[list[str]] = [
        "libvirt-cpu", "pistachio-arch", "libjit-spec",
    ]
    spec_only: ClassVar[bool] = True

    def parse(self, entry, base_dir: str) -> ParseResult:
        return ParseResult(records=[], partial=0,
                           note="spec-only: register/feature model, 0 instruction records")


@register_parser
class NotImplementedParser(SourceParser):
    """Banks whose dedicated parser is not yet wired. Returns zero records with
    an explicit note so the run report surfaces them (never silent). Add a real
    parser in parsers/ + register_parser to enable (§12, open-closed)."""
    bank_ids: ClassVar[list[str]] = []   # fallback parser; never registered
    spec_only: ClassVar[bool] = False

    def parse(self, entry, base_dir: str) -> ParseResult:
        return ParseResult(records=[], partial=0,
                           note=f"parser not implemented for {entry.id}")
