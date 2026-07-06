"""Configuration (XTRAKT.md §10). Declarative YAML."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from .manifest import _load_yaml


@dataclass
class BackendSpec:
    name: str
    target: str


@dataclass
class Config:
    manifest: str = "BANKS.yaml"
    records: str = "RECORDS.yaml"
    base_dir: str = "."                # repo root for bank/ resolution
    banks: Any = "all"                 # "all" | list[str]
    arches: Any = "all"                # "all" | list[str]
    backends: list[BackendSpec] = field(default_factory=list)
    precedence: list[str] = field(default_factory=list)   # bank ids, highest first
    workers: int = 1

    def bank_filter(self, bid: str) -> bool:
        return self.banks == "all" or bid in self.banks

    def arch_filter(self, arch: str) -> bool:
        return self.arches == "all" or arch in self.arches

    def precedence_of(self, bank_id: str) -> int:
        try:
            return -self.precedence.index(bank_id)      # earlier = higher
        except ValueError:
            return 0

    @classmethod
    def from_dict(cls, d: dict, base_dir: str = ".") -> "Config":
        backends = [BackendSpec(b["name"], b["target"]) for b in (d.get("backends") or [])]
        return cls(
            manifest=d.get("manifest", os.path.join(base_dir, "BANKS.yaml")),
            records=d.get("records", os.path.join(base_dir, "RECORDS.yaml")),
            base_dir=base_dir,
            banks=d.get("banks", "all"),
            arches=d.get("arches", "all"),
            backends=backends,
            precedence=list(d.get("precedence") or []),
            workers=int(d.get("workers", 1)),
        )

    @classmethod
    def load(cls, path: str) -> "Config":
        d = _load_yaml(path) or {}
        base = os.path.dirname(os.path.abspath(path)) or "."
        # resolve manifest/records relative to the config file's dir if relative
        return cls.from_dict(d, base)


DEFAULT_CONFIG = """
manifest: BANKS.yaml
records:  RECORDS.yaml
banks:    all
arches:   all
backends:
  - {name: sqlite3, target: archbank.db}
  - {name: json,    target: archbank.json}
precedence: []
workers: 1
"""
