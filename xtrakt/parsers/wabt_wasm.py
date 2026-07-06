"""L3 — Wabt WebAssembly opcode parser (BANKS.yaml wabt-wasm).

Source: ``opcode.cc`` + ``opcode-code-table.c`` — C++ that expands the
``WABT_OPCODE`` X-macro to build the opcode info table and enum. Both files
``#include "wabt/opcode.def"``, the X-macro opcode table, but ``opcode.def`` is
NOT shipped in this bank snapshot: the macro expands to nothing and no opcode
row is recoverable here.

Spec-only in this snapshot. The parser scans for ``opcode.def`` (and any
``*.def``) so the gap is surfaced explicitly in the run report rather than
silently dropped. Re-add ``opcode.def`` to enable real WASM records; the macro
signature already documents the per-opcode schema:

    WABT_OPCODE(rtype, type1, type2, type3, mem_size, prefix, code,
                Name, text, decomp)
"""
from __future__ import annotations

import os
from typing import ClassVar

from .base import SourceParser, ParseResult, register_parser


@register_parser
class WabtWasmParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["wabt-wasm"]
    spec_only: ClassVar[bool] = True

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        # The X-macro table is the only real opcode source; without it the
        # C++ consumers expand to nothing.
        def_found = False
        for dp, _dn, fns in os.walk(root):
            for fn in fns:
                if fn.endswith(".def"):
                    def_found = True
                    break
            if def_found:
                break
        if def_found:
            note = "opcode.def present but X-macro expansion not yet wired; 0 records"
        else:
            note = ("spec-only: opcode.def missing from bank; WABT_OPCODE X-macro "
                    "expands to nothing, 0 instruction records")
        return ParseResult(records=[], partial=0, note=note)
