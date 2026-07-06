"""L3 — SML/NJ backend machine-specification parser (BANKS.yaml smlnj-targets).

Source: ``amd64-spec.sml`` + ``arm64-spec.sml`` — each a
``structure <Arch>Spec : MACH_SPEC`` declaring target ABI/register-frame
SCALARS (wordByteWidth, numRegs, numArgRegs, numFloatRegs, spillAreaSz, ...).
MACH_SPEC carries frame layout, register counts, and calling conventions; it
defines NO instruction encodings.

Spec-only: 0 instruction records. The parser reads the scalars into ``meta``
(provenance for the ABI/register model, useful as a semantics-adjacent source
for x86-64 / aarch64) and yields 0 records with an explicit note.
"""
from __future__ import annotations

import os
import re
from typing import ClassVar

from .base import SourceParser, ParseResult, register_parser

_SCALAR = re.compile(r"^\s*val\s+(\w+)\s*=\s*(.+?)\s*(?:\(\*.*\*\))?\s*$")
_ARCH = re.compile(r'val\s+architecture\s*=\s*"([^"]+)"')
_ARCH_DIR = {"amd64": "x86-64", "arm64": "aarch64", "x86_64": "x86-64"}


def _read_scalars(path: str) -> dict:
    out: dict[str, str] = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.split("(*", 1)[0]
            m = _SCALAR.match(line)
            if not m:
                continue
            name, value = m.group(1), m.group(2).strip().rstrip(",")
            if name and value and not value.startswith("structure"):
                out[name] = value
    am = _ARCH.search(open(path, encoding="utf-8", errors="replace").read())
    if am:
        out["architecture"] = am.group(1)
    return out


@register_parser
class SmlnjTargetsParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["smlnj-targets"]
    spec_only: ClassVar[bool] = True

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        specs: dict[str, dict] = {}
        for fn in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            if not fn.endswith(".sml"):
                continue
            specs[fn] = _read_scalars(os.path.join(root, fn))
        arches = ", ".join(sorted({s.get("architecture", "?") for s in specs.values()}))
        return ParseResult(
            records=[],
            partial=0,
            note=(f"spec-only: MACH_SPEC scalars for [{arches}] "
                  f"({len(specs)} files); 0 instruction records"),
        )
