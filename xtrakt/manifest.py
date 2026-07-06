"""L1 — manifest load: BANKS.yaml -> list[BankEntry] (XTRAKT.md §2.1, §1).

The manifest is a YAML list of bank entries plus `$`-prefixed header scalars
(version/project/...). Header keys are skipped; only dict entries carrying an
``id`` are bank entries.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BankEntry:
    id: str
    name: str = ""
    directory: str = ""
    sourced_from: str = ""
    extraction_hint: str = ""

    @property
    def root(self) -> str:
        """Absolute-ish path to the bank's source directory under the repo root."""
        return self.directory

    def resolve(self, base: str) -> str:
        return os.path.join(base, self.directory) if not os.path.isabs(self.directory) \
            else self.directory


def _load_yaml(path: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("PyYAML required to load YAML inputs (pip install pyyaml)") from e
    # The manifest/records files prefix a `$`-header (version/project/...) above
    # the real YAML payload. That header mixes scalar keys with a top-level
    # sequence, which is not valid YAML, so slice from the first top-level
    # sequence/mapping entry onward.
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    start = 0
    for i, ln in enumerate(lines):
        if ln[:1] in ("-",) or (ln and not ln[0].isspace() and ln.rstrip().endswith(":")):
            # a top-level list item is the canonical payload; a bare top-level
            # key introduces the real map only if no `$` header sentinel.
            if ln.startswith("- "):
                start = i
                break
            if not ln.startswith("$"):
                start = i
                break
    return yaml.safe_load("".join(lines[start:]))


def load(manifest_path: str) -> list[BankEntry]:
    """Load BANKS.yaml -> ordered list[BankEntry]."""
    data = _load_yaml(manifest_path)
    if isinstance(data, dict):                 # some manifests are keyed
        data = data.get("banks") or data.get("entries") or []
    out: list[BankEntry] = []
    for item in data or []:
        if not isinstance(item, dict) or "id" not in item:
            continue
        out.append(BankEntry(
            id=str(item["id"]),
            name=str(item.get("name", "")),
            directory=str(item.get("directory", "")),
            sourced_from=str(item.get("sourced_from", "") or ""),
            extraction_hint=str(item.get("extraction_hint", "") or ""),
        ))
    return out


def load_bank(banks_path: str, bank_id: str) -> Optional[BankEntry]:
    for e in load(banks_path):
        if e.id == bank_id:
            return e
    return None
