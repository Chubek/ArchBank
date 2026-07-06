"""BSON backend (XTRAKT.md §8.2). Minimal, dependency-free BSON codec for the
canonical container object; ``BitVec`` rides as a nested ``{width,hex}`` doc,
matching MongoDB round-trip semantics. Sufficient types: dict, list, str,
int32/int64, float, bool, null.
"""
from __future__ import annotations
import struct
from typing import Iterable, Iterator

from ..cir import InstructionRecord
from .base import StorageBackend, register_backend, schema_to_doc, schema_from_doc

# BSON element type tags
_T_FLOAT = 0x01
_T_STR = 0x02
_T_DOC = 0x03
_T_ARR = 0x04
_T_BOOL = 0x08
_T_NULL = 0x0A
_T_INT32 = 0x10
_T_INT64 = 0x12

INT32_MIN, INT32_MAX = -(2 ** 31), 2 ** 31


def _cstring(s: str) -> bytes:
    return s.encode("utf-8") + b"\x00"


def _enc_doc(d: dict) -> bytes:
    body = b"".join(
        (bytes([_type_byte(v)]) + _cstring(str(k)) + _payload(v))
        for k, v in d.items()
    )
    return struct.pack("<i", len(body) + 5) + body + b"\x00"


def _type_byte(v):
    if v is None: return _T_NULL
    if isinstance(v, bool): return _T_BOOL
    if isinstance(v, int):
        return _T_INT32 if INT32_MIN <= v < INT32_MAX else _T_INT64
    if isinstance(v, float): return _T_FLOAT
    if isinstance(v, str): return _T_STR
    if isinstance(v, list): return _T_ARR
    if isinstance(v, dict): return _T_DOC
    return _T_STR

def _payload(v):
    if v is None: return b""
    if isinstance(v, bool): return b"\x01" if v else b"\x00"
    if isinstance(v, int):
        if INT32_MIN <= v < INT32_MAX:
            return struct.pack("<i", v)
        return struct.pack("<q", v)
    if isinstance(v, float): return struct.pack("<d", v)
    if isinstance(v, str):
        b = v.encode("utf-8")
        return struct.pack("<i", len(b) + 1) + b + b"\x00"
    if isinstance(v, list): return _enc_doc({str(i): x for i, x in enumerate(v)})
    if isinstance(v, dict): return _enc_doc(v)
    b = str(v).encode("utf-8")
    return struct.pack("<i", len(b) + 1) + b + b"\x00"


def encode(doc: dict) -> bytes:
    return _enc_doc(doc)


def _dec_doc(buf: bytes, off: int) -> tuple[dict, int]:
    size = struct.unpack_from("<i", buf, off)[0]
    end = off + size
    off += 4
    out: dict = {}
    while off < end - 1:
        tag = buf[off]; off += 1
        k_end = buf.index(b"\x00", off)
        key = buf[off:k_end].decode("utf-8"); off = k_end + 1
        val, off = _dec_val(buf, off, tag)
        out[key] = val
    return out, end


def _dec_val(buf: bytes, off: int, tag: int) -> tuple[object, int]:
    if tag == _T_NULL: return None, off
    if tag == _T_BOOL: return buf[off] != 0, off + 1
    if tag == _T_INT32:
        return struct.unpack_from("<i", buf, off)[0], off + 4
    if tag == _T_INT64:
        return struct.unpack_from("<q", buf, off)[0], off + 8
    if tag == _T_FLOAT:
        return struct.unpack_from("<d", buf, off)[0], off + 8
    if tag == _T_STR:
        ln = struct.unpack_from("<i", buf, off)[0]; off += 4
        s = buf[off:off + ln - 1].decode("utf-8"); return s, off + ln
    if tag == _T_DOC:
        d, end = _dec_doc(buf, off); return d, end
    if tag == _T_ARR:
        d, end = _dec_doc(buf, off)
        return [d[str(i)] for i in range(len(d))], end
    raise ValueError(f"unsupported BSON tag {tag}")


def decode(buf: bytes) -> dict:
    doc, _ = _dec_doc(buf, 0)
    return doc


@register_backend("bson")
class BSONBackend(StorageBackend):

    def open(self, target: str, mode: str = "w") -> "BSONBackend":
        self.target = target
        self.mode = mode
        self._schemas: list = []
        self._recs: list[InstructionRecord] = []
        if mode == "r":
            with open(self.target, "rb") as fh:
                doc = decode(fh.read())
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
        with open(self.target, "wb") as fh:
            fh.write(encode(doc))

    def close(self):
        if self.mode == "w":
            self.commit()
