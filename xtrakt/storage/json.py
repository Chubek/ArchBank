"""JSON backend (XTRAKT.md §8.2). Container: version + schemas + records."""
from __future__ import annotations
import json as _json
from typing import Iterable, Iterator, Optional

from ..cir import InstructionRecord
from .base import StorageBackend, register_backend, schema_to_doc, schema_from_doc

VERSION = "1.0.0"


@register_backend("json")
class JSONBackend(StorageBackend):

    def open(self, target: str, mode: str = "w") -> "JSONBackend":
        self.target = target
        self.mode = mode
        self._schemas: list = []
        self._recs: list[InstructionRecord] = []
        if mode == "r":
            self._load()
        return self

    def _load(self):
        with open(self.target, "r", encoding="utf-8") as fh:
            doc = _json.load(fh)
        self._schemas = [schema_from_doc(s) for s in doc.get("schemas", [])]
        self._recs = [InstructionRecord.from_doc(r) for r in doc.get("records", [])]

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
        doc = {"version": VERSION,
               "schemas": [schema_to_doc(s) for s in self._schemas],
               "records": [r.to_doc() for r in self._recs]}
        with open(self.target, "w", encoding="utf-8") as fh:
            _json.dump(doc, fh, indent=2, sort_keys=False)

    def close(self):
        if self.mode == "w":
            self.commit()
