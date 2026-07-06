"""L3 — OpenJDK HotSpot ADL parser (BANKS.yaml hotspot-cpu).

Source: per-arch source trees (aarch64, arm, ppc, riscv, s390, x86, zero),
each with ``<arch>.ad`` (+ GC frags under ``gc/``). The ``.ad`` ``instruct``
blocks are machine-instruction selection rules::

    instruct <name>(<operand decls>) %{
      match(...);
      format %{ "ASM $op ..." %};
      ins_encode(<enc-class>(...));
      ins_pipe(...);
    %}

``format`` -> real assembly mnemonic (first token) + operand placeholders;
``ins_encode`` -> symbolic encoding class (no byte layout). ``zero/`` is the
interpreter backend (no machine ISA) -> skipped.

Multi-arch bank: each record carries an arch_hint from the .ad path. Encoding
is symbolic -> prebuilt ``define-encoding`` form, width=variable ->
decode_schematic=True (§6.2). L4 resolves arch per-record via the hint (§13).
"""
from __future__ import annotations

import os
import re
from typing import ClassVar

from ..cir import RawRecord
from .base import SourceParser, ParseResult, register_parser

# HotSpot arch dir -> ArchBank arch id. 'zero' (interpreter) is skipped.
_ARCH_DIR = {
    "aarch64": "aarch64", "arm": "arm-a32", "ppc": "powerpc",
    "riscv": "riscv", "s390": "s390", "x86": "x86-64",
}

_INSTRUCT = re.compile(r"^\s*instruct\s+(\w+)\s*\(([^)]*)\)\s*%?\s*\{?\s*$",
                       re.M)
_FORMAT = re.compile(r'format\s*%?\s*\{\s*"(.+?)"\s*%\s*\}', re.S)
_INS_ENCODE = re.compile(r"ins_encode\s*\(([^)]*)\)")
_ASM_MNEM = re.compile(r"\s*([A-Za-z][\w.]*)")


def _operand_names(decls: str) -> list[str]:
    """`iRegINoSp dst, memory1 mem` -> ['dst', 'mem'] (last token of each decl)."""
    names: list[str] = []
    for decl in decls.split(","):
        parts = decl.strip().split()
        if parts:
            names.append(parts[-1])
    return names


def _arch_for_path(path: str) -> str | None:
    parts = path.replace(os.sep, "/").split("/")
    for seg in parts:
        if seg in _ARCH_DIR:
            return _ARCH_DIR[seg]
    return None


def _mnemonic_from_format(fmt: str) -> str:
    m = _ASM_MNEM.match(fmt.strip())
    return m.group(1).lower() if m else ""


def _matching_close(text: str, start: int) -> int:
    """Index of the ``%}`` that closes the instruct block opened before
    ``start``. Tracks nested ``%{``/``%}`` (format, ins_encode). -1 if
    unbalanced."""
    depth = 1
    i = start
    while True:
        opn = text.find("%{", i)
        cls = text.find("%}", i)
        if cls == -1:
            return -1
        if opn != -1 and opn < cls:
            depth += 1
            i = opn + 2
        else:
            depth -= 1
            if depth == 0:
                return cls
            i = cls + 2


@register_parser
class HotspotAdlParser(SourceParser):
    bank_ids: ClassVar[list[str]] = ["hotspot-cpu"]

    def parse(self, entry, base_dir: str) -> ParseResult:
        root = entry.resolve(base_dir)
        recs: list[RawRecord] = []
        partial = 0
        for dirpath, _dn, fns in os.walk(root):
            arch = _arch_for_path(dirpath)
            for fn in sorted(fns):
                if not fn.endswith(".ad"):
                    continue
                if arch is None:          # 'zero' or unmapped -> skip
                    continue
                n, p = self._parse_file(os.path.join(dirpath, fn), arch)
                recs.extend(n)
                partial += p
        return ParseResult(records=recs, partial=partial,
                           note=f"{len(recs)} instruct blocks")

    @staticmethod
    def _parse_file(path: str, arch: str) -> tuple[list[RawRecord], int]:
        text = open(path, encoding="utf-8", errors="replace").read()
        recs: list[RawRecord] = []
        partial = 0
        # iterate instruct blocks: header line ... matching closing %}
        for m in _INSTRUCT.finditer(text):
            name, decls = m.group(1), m.group(2)
            # body = balanced %{ ... %} after the header (format/ins_encode
            # carry nested %{ %} pairs, so a naive find('%}') truncates early).
            start = m.end()
            close = _matching_close(text, start)
            if close == -1:
                partial += 1
                continue
            body = text[start:close]
            fmt_m = _FORMAT.search(body)
            if not fmt_m:
                partial += 1
                continue
            mnem = _mnemonic_from_format(fmt_m.group(1))
            if not mnem:
                partial += 1
                continue
            enc_m = _INS_ENCODE.search(body)
            enc_class = enc_m.group(1).strip() if enc_m else ""
            operands = _operand_names(decls)
            enc_fn = (f"(define-encoding ({name}) variable\n  "
                      f"(symbolic \"{enc_class}\"))")
            recs.append(RawRecord(
                mnemonic=mnem,
                arch_hint=arch, isa_ext="base",
                encoding_class="variable", bank_id="hotspot-cpu",
                layout=[], width="variable",
                fields={},
                meta={"rule": name, "operands": ", ".join(operands),
                      "encoding_function": enc_fn,
                      "format": fmt_m.group(1).strip(),
                      "source": os.path.relpath(path, os.path.dirname(path))},
            ))
        return recs, partial
