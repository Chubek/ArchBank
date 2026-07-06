"""L5 semantics transcoders (XTRAKT.md §6.3).

One transcoder per foreign formalism. All are best-effort: returning ``None``
is legal (``semantics=null``). The registry is the open-closed extension point
(§12); a coverage map is emitted alongside the run so absent semantics is
visible, never silent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ...cir import RawRecord

Transcoder = Callable[[str, RawRecord], Optional[str]]


@dataclass
class TranscoderEntry:
    name: str                 # formalism id: sleigh|ssl|rtl|tcg|mspec|dag
    fn: Transcoder
    coverage: str = "partial"  # partial | sparse


TRANSCODERS: dict[str, TranscoderEntry] = {}


def register_transcoder(name: str, coverage: str = "partial"):
    def deco(fn: Transcoder) -> Transcoder:
        TRANSCODERS[name] = TranscoderEntry(name, fn, coverage)
        return fn
    return deco


def transcode(formalism: str, source_text: str, raw: RawRecord) -> Optional[str]:
    """Map a foreign-semantics text to P-Code, or None if unmappable."""
    entry = TRANSCODERS.get(formalism)
    if entry is None or not source_text:
        return None
    try:
        return entry.fn(source_text, raw)
    except Exception:
        return None


def coverage_map() -> dict[str, str]:
    return {name: e.coverage for name, e in TRANSCODERS.items()}


# ── registry of source formalisms -> transcoder name (per §6.3) ──
BANK_FORMALISM: dict[str, str] = {
    "ghidra-cpu": "sleigh",
    "boomerang-ssl": "ssl",
    "fracture-target": "ssl",
    "gcc-md": "rtl",
    "lcc-md": "rtl",
    "qemu-targets": "tcg",
    "qemu-tcg": "tcg",
    "pydgin-arch": "mspec",
    "impact-mspec": "mspec",
    "decaf-qemu": "tcg",
    "llvm-td": "dag",
    "miasm-arch": "miasm",
    "gem5-arch": "gem5",
}


def formalism_for(bank_id: str) -> Optional[str]:
    return BANK_FORMALISM.get(bank_id)


# eager-import the concrete transcoders to populate the registry
from . import sleigh, ssl, rtl, tcg, mspec, dag  # noqa: F401,E402
