"""sqlite3 backend — hybrid schema (XTRAKT.md §8.3). record_base columns are
first-class (indexable); arch-specific fields live in a JSON column. Round-trip
is exact: SELECT rebuilds the canonical doc and ``InstructionRecord.from_doc``.
"""
from __future__ import annotations
import hashlib
import json as _json
import sqlite3
from typing import Iterable, Iterator, Optional

from ..cir import InstructionRecord
from .base import StorageBackend, register_backend, schema_to_doc, schema_from_doc
from ..schema import ArchSchema

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records(
  arch TEXT, mnemonic TEXT, isa_ext TEXT, encoding_class TEXT,
  category TEXT, privilege TEXT, memory_access TEXT,
  encoding_function TEXT, semantics TEXT,
  decode_mask TEXT, decode_match TEXT, decode_schematic INTEGER,
  aliases TEXT, cpuid TEXT, flags_read TEXT, flags_write TEXT,
  source_banks TEXT, fields TEXT, fields_sig TEXT,
  PRIMARY KEY(arch, mnemonic, encoding_class, isa_ext, fields_sig)
);
CREATE INDEX IF NOT EXISTS ix_mnemonic ON records(mnemonic);
CREATE INDEX IF NOT EXISTS ix_arch     ON records(arch);
CREATE TABLE IF NOT EXISTS schemas(arch TEXT PRIMARY KEY, doc TEXT);
CREATE TABLE IF NOT EXISTS banks(id TEXT PRIMARY KEY, name TEXT,
                                 directory TEXT, yielded INTEGER);
"""


def _sig(rec: InstructionRecord) -> str:
    return hashlib.sha1(rec.operand_signature.encode("utf-8")).hexdigest()[:16]


def _j(v) -> str:
    return _json.dumps(v)


@register_backend("sqlite3")
class SQLiteBackend(StorageBackend):

    def open(self, target: str, mode: str = "w") -> "SQLiteBackend":
        self.target = target
        self.mode = mode
        self._conn = sqlite3.connect(target, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        if mode == "w":
            self._conn.executescript(_SCHEMA)
        return self

    # ── write ──
    def put_schemas(self, schemas: Iterable[ArchSchema]):
        self._conn.execute("DELETE FROM schemas")
        for sc in schemas:
            self._conn.execute(
                "INSERT OR REPLACE INTO schemas(arch, doc) VALUES (?,?)",
                (sc.arch, _j(schema_to_doc(sc))),
            )

    def put_records(self, records: Iterable[InstructionRecord]):
        rows = []
        for r in records:
            d = r.to_doc()
            rows.append((
                r.arch, r.mnemonic, r.isa_ext, r.encoding_class,
                r.category, r.privilege, r.memory_access,
                r.encoding_function, r.semantics,
                _j(d["decode_mask"]), _j(d["decode_match"]),
                int(r.decode_schematic),
                _j(r.aliases), r.cpuid, _j(r.flags_read), _j(r.flags_write),
                _j(r.source_banks), _j(d["fields"]), _sig(r),
            ))
        self._conn.executemany(
            "INSERT OR REPLACE INTO records("
            "arch,mnemonic,isa_ext,encoding_class,category,privilege,memory_access,"
            "encoding_function,semantics,decode_mask,decode_match,decode_schematic,"
            "aliases,cpuid,flags_read,flags_write,source_banks,fields,fields_sig"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    def put_bank(self, bank_id: str, name: str, directory: str, yielded: int):
        self._conn.execute(
            "INSERT OR REPLACE INTO banks(id,name,directory,yielded) VALUES (?,?,?,?)",
            (bank_id, name, directory, yielded))

    # ── read ──
    def get_records(self, *, arch: Optional[str] = None,
                    mnemonic: Optional[str] = None) -> Iterator[InstructionRecord]:
        q = "SELECT * FROM records"
        where, args = [], []
        if arch:
            where.append("arch=?"); args.append(arch)
        if mnemonic:
            where.append("mnemonic=?"); args.append(mnemonic)
        if where:
            q += " WHERE " + " AND ".join(where)
        for row in self._conn.execute(q, args):
            yield InstructionRecord.from_doc(self._row_to_doc(row))

    @staticmethod
    def _row_to_doc(row) -> dict:
        def jget(k):
            v = row[k]
            return _json.loads(v) if v is not None else None
        return {
            "arch": row["arch"],
            "mnemonic": row["mnemonic"],
            "aliases": jget("aliases"),
            "isa_ext": row["isa_ext"],
            "cpuid": row["cpuid"],
            "encoding_class": row["encoding_class"],
            "encoding_function": row["encoding_function"] or "",
            "decode_mask": jget("decode_mask"),
            "decode_match": jget("decode_match"),
            "semantics": row["semantics"],
            "flags_read": jget("flags_read"),
            "flags_write": jget("flags_write"),
            "memory_access": row["memory_access"],
            "category": row["category"],
            "privilege": row["privilege"],
            "fields": jget("fields") or {},
            "source_banks": jget("source_banks") or [],
            "decode_schematic": bool(row["decode_schematic"]),
        }

    def get_schemas(self) -> list[ArchSchema]:
        return [schema_from_doc(_json.loads(r["doc"]))
                for r in self._conn.execute("SELECT doc FROM schemas")]

    # ── transactions ──
    def begin(self): self._conn.execute("BEGIN")
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
