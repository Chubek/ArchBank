"""Explicit no-encoding parsers for metadata/semantics-only banks."""
from __future__ import annotations

from typing import ClassVar

from .base import ParseResult, SourceParser, register_parser


@register_parser
class MetadataOnlyParser(SourceParser):
    bank_ids: ClassVar[list[str]] = [
        "boomerang-ssl", "ddisasm-arch", "decaf-fpu", "fracture-target",
        "gdb-arch", "jikesrvm-burs", "lcc-md", "miasm-arch",
        "mlrisc-arch", "mlton-arch", "pydgin-arch", "pypy-jitbackend",
        "qbe-instr", "vex-vine", "zydis-metadata",
    ]
    spec_only: ClassVar[bool] = True

    def parse(self, entry, base_dir: str) -> ParseResult:
        return ParseResult(
            records=[],
            partial=0,
            note="metadata/semantics-only: 0 encoding records",
        )
