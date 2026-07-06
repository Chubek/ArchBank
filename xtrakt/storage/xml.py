"""XML backend (XTRAKT.md §8.2). Generic, type-preserving encoding of the
canonical container object so the CIR round-trips without a per-field schema.

Encoding rule (JSON-native -> XML):
    null/bool/int/str -> <v type=...>text</v>
    list              -> <v type="list"><v.../>...</v>
    dict              -> <v type="dict"><e key="k"><v.../></e>...</v>
The whole container {version, schemas, records} is one such value.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Iterable, Iterator

from ..cir import InstructionRecord
from .base import StorageBackend, register_backend, schema_to_doc, schema_from_doc


def _enc(val, tag="v"):
    el = ET.Element(tag)
    if val is None:
        el.set("type", "null"); return el
    if isinstance(val, bool):
        el.set("type", "bool"); el.text = "true" if val else "false"; return el
    if isinstance(val, int):
        el.set("type", "int"); el.text = str(val); return el
    if isinstance(val, float):
        el.set("type", "float"); el.text = repr(val); return el
    if isinstance(val, str):
        el.set("type", "str"); el.text = val; return el
    if isinstance(val, list):
        el.set("type", "list")
        for item in val:
            el.append(_enc(item, "v"))
        return el
    if isinstance(val, dict):
        el.set("type", "dict")
        for k, v in val.items():
            e = ET.SubElement(el, "e")
            e.set("key", str(k))
            e.append(_enc(v, "v"))
        return el
    # fallback: stringify
    el.set("type", "str"); el.text = str(val); return el


def _dec(el):
    t = el.get("type", "str")
    if t == "null":
        return None
    if t == "bool":
        return el.text == "true"
    if t == "int":
        return int(el.text)
    if t == "float":
        return float(el.text)
    if t == "str":
        return el.text if el.text is not None else ""
    if t == "list":
        return [_dec(c) for c in el.findall("v")]
    if t == "dict":
        out = {}
        for e in el.findall("e"):
            out[e.get("key")] = _dec(e.find("v"))
        return out
    return el.text


@register_backend("xml")
class XMLBackend(StorageBackend):

    def open(self, target: str, mode: str = "w") -> "XMLBackend":
        self.target = target
        self.mode = mode
        self._schemas: list = []
        self._recs: list[InstructionRecord] = []
        if mode == "r":
            tree = ET.parse(self.target)
            root = tree.getroot()            # <archbank>
            doc = _dec(root.find("v"))
            self._schemas = [schema_from_doc(s) for s in (doc or {}).get("schemas", [])]
            self._recs = [InstructionRecord.from_doc(r)
                          for r in (doc or {}).get("records", [])]
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
        root = ET.Element("archbank")
        root.append(_enc(doc, "v"))
        # pretty-print (py3.9+)
        try:
            ET.indent(root, space="  ")
        except AttributeError:
            pass
        ET.ElementTree(root).write(self.target, encoding="utf-8", xml_declaration=True)

    def close(self):
        if self.mode == "w":
            self.commit()
