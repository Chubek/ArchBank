"""L7 — storage backends (XTRAKT.md §8).

A backend is a pure (de)serializer of the CIR. ``adaptability`` has three
meanings (choose-at-runtime, migrate, extend) all served by one registry.
``convert`` migrates between any two backends losslessly (§8.4, §14).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Iterable, Iterator, Optional

from ..cir import InstructionRecord
from ..schema import ArchSchema, FieldSpec

BACKENDS: dict[str, type["StorageBackend"]] = {}


def register_backend(name: str):
    def deco(cls):
        BACKENDS[name] = cls
        cls.name = name
        return cls
    return deco


# ─────────────────────────── schema (de)ser ───────────────────────────

def schema_to_doc(sc: ArchSchema) -> dict:
    return {
        "arch": sc.arch,
        "full_name": sc.full_name,
        "encoding_class": sc.encoding_class,
        "width_bits": sc.width_bits,
        "operand_types": list(sc.operand_types),
        "encoding_banks": list(sc.encoding_banks),
        "semantics_banks": list(sc.semantics_banks),
        "record": [
            {"name": f.name, "kind": f.kind, "width": f.width,
             "required": f.required, "note": f.note, "access": f.access}
            for f in sc.record
        ],
        "encoding_function": sc.encoding_function,
        "semantics": sc.semantics,
        "notes": sc.notes,
    }


def schema_from_doc(d: dict) -> ArchSchema:
    rec = [FieldSpec(
        name=f.get("name", ""), kind=f.get("kind", "str"), width=f.get("width"),
        required=bool(f.get("required", False)), note=f.get("note", "") or "",
        access=f.get("access", "") or "", operand=f.get("kind", "str"),
    ) for f in (d.get("record") or [])]
    return ArchSchema(
        arch=d.get("arch", ""), full_name=d.get("full_name", "") or "",
        encoding_class=d.get("encoding_class", "") or "",
        width_bits=d.get("width_bits"),
        operand_types=list(d.get("operand_types") or []),
        encoding_banks=list(d.get("encoding_banks") or []),
        semantics_banks=list(d.get("semantics_banks") or []),
        record=rec,
        encoding_function=d.get("encoding_function", "") or "",
        semantics=d.get("semantics", "") or "",
        notes=d.get("notes", "") or "",
    )


# ─────────────────────────── ABC ───────────────────────────

class StorageBackend(ABC):
    name: str = ""
    writable_target: bool = True        # False for read-only views

    def __init__(self):
        self.target: Any = None
        self.mode: str = "w"

    @abstractmethod
    def open(self, target: str, mode: str = "w") -> "StorageBackend": ...

    def put_schemas(self, schemas: Iterable[ArchSchema]) -> None:
        """Default: no-op. Backends with a schema table override."""
        return None

    @abstractmethod
    def put_records(self, records: Iterable[InstructionRecord]) -> None: ...

    def get_records(self, *, arch: Optional[str] = None,
                    mnemonic: Optional[str] = None) -> Iterator[InstructionRecord]:
        raise NotImplementedError(f"{self.name} is write-only")

    def get_schemas(self) -> list[ArchSchema]:
        return []

    # transactions: no-op for file backends
    def begin(self) -> None: pass
    def commit(self) -> None: pass
    def rollback(self) -> None: pass
    def close(self) -> None: pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ─────────────────────────── migration ───────────────────────────

def convert(src_backend: str, src_target: str,
            dst_backend: str, dst_target: str) -> int:
    """§8.4: read A -> write B. Same CIR => lossless across all defaults."""
    src_cls = BACKENDS.get(src_backend)
    dst_cls = BACKENDS.get(dst_backend)
    if src_cls is None or dst_cls is None:
        raise KeyError(f"unknown backend: {src_backend!r} or {dst_backend!r}")
    src = src_cls().open(src_target, mode="r")
    dst = dst_cls().open(dst_target, mode="w")
    try:
        schemas = src.get_schemas()
        if schemas:
            dst.put_schemas(schemas)
        recs = list(src.get_records())
        dst.begin()
        dst.put_records(recs)
        dst.commit()
        return len(recs)
    finally:
        src.close()
        dst.close()


# eager-import defaults so the registry is populated on package import
from . import json as _json  # noqa: E402,F401
from . import yaml as _yaml  # noqa: E402,F401
from . import sqlite as _sqlite  # noqa: E402,F401
from . import xml as _xml  # noqa: E402,F401
from . import bson as _bson  # noqa: E402,F401
