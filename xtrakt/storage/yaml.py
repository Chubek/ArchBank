"""YAML backend: same container object as JSON, block style (human-edit)."""
from __future__ import annotations
from typing import Iterable, Iterator

from ..cir import InstructionRecord
from .base import StorageBackend, register_backend, schema_to_doc, schema_from_doc

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


@register_backend("yaml")
class YAMLBackend(StorageBackend):

    def open(self, target: str, mode: str = "w") -> "YAMLBackend":
        if yaml is None:
            raise RuntimeError("PyYAML required for the yaml backend")
        self.target = target
        self.mode = mode
        self._schemas: list = []
        self._recs: list[InstructionRecord] = []
        if mode == "r":
            with open(self.target, "r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
            self._schemas = [schema_from_doc(s) for s in doc.get("schemas", [])]
            self._recs = [InstructionRecord.from_doc(r) for r in doc.get("records", [])]
        return self

    def put_schemas(self, schemas):
        self._schemas = list(schemas)

    def put_records(self, records: Iterable[InstructionRecord]):
        self._recs = list(records)

    def get_records(self, *, arch=None, mnemonic=None) -> Iterator[InstructionRecord]:
        for r in self._recs:
            if arch and r.arch != arch:
                continue
            if mnemonic and r.mnemonic != mnemonic:
                continue
            yield r

    def get_schemas(self):
        return list(self._schemas)

    def commit(self):
        if self.mode == "r":
            return
        doc = {"version": "1.0.0",
               "schemas": [schema_to_doc(s) for s in self._schemas],
               "records": [r.to_doc() for r in self._recs]}
        with open(self.target, "w", encoding="utf-8") as fh:
            yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True)

    def close(self):
        if self.mode == "w":
            self.commit()
