"""L8 — pipeline driver (XTRAKT.md §9).

Declarative DAG over L1..L7. Per-bank isolation (one failure never aborts the
run), idempotency (content-hash gate), optional concurrency, and a no-silent-
caps run report (zero-yield spec-only banks, rejections, conflicts, and
parser-not-implemented banks are all surfaced with counts).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Optional

from . import manifest as L1
from . import schema as L2
from . import normalize as L4
from .parsers import parser_for
from .pcode import transcoders
from .storage.base import BACKENDS
from .config import Config


@dataclass
class BankResult:
    id: str
    name: str
    yielded: int = 0
    rejected: int = 0
    partial: int = 0
    spec_only: bool = False
    not_implemented: bool = False
    error: Optional[str] = None
    note: str = ""


@dataclass
class RunReport:
    banks: list[BankResult] = field(default_factory=list)
    records: int = 0
    conflicts: list[dict] = field(default_factory=list)
    coverage: dict[str, str] = field(default_factory=dict)

    @property
    def total_yielded(self) -> int:
        return sum(b.yielded for b in self.banks)

    @property
    def rejected(self) -> int:
        return sum(b.rejected for b in self.banks)

    def summary(self) -> str:
        lines = [f"records={self.records}  yielded_total={self.total_yielded}  "
                 f"rejected={self.rejected}  conflicts={len(self.conflicts)}"]
        for b in self.banks:
            tag = ("ERR" if b.error else "NOP" if b.spec_only
                   else "TODO" if b.not_implemented else "OK ")
            lines.append(f"  [{tag}] {b.id:<22} yield={b.yielded:<5} "
                         f"rej={b.rejected:<4} partial={b.partial:<4} {b.note}")
        return "\n".join(lines)


class ParseError(Exception):
    pass


def _dir_hash(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.sha1()
    for dp, _, fns in sorted(os.walk(path)):
        for fn in sorted(fns):
            fp = os.path.join(dp, fn)
            h.update(fn.encode())
            try:
                st = os.stat(fp)
                h.update(str(st.st_size).encode())
            except OSError:
                pass
    return h.hexdigest()[:16]


def extract(config: Config, dump_dir: Optional[str] = None) -> RunReport:
    """Run L1..L7 end-to-end. Returns a RunReport; writes to configured backends."""
    report = RunReport(coverage=transcoders.coverage_map())
    base = config.base_dir or os.path.dirname(os.path.abspath(config.manifest)) or "."

    entries = [e for e in L1.load(config.manifest) if config.bank_filter(e.id)]
    base_fields, arches = L2.load_schema(config.records)
    bam = L2.bank_arch_map(arches)
    by_name = L2.schema_index(arches)

    normalizer = L4.Normalizer(bam, precedence=config.precedence_of)
    index = L4.MergeIndex(precedence=config.precedence_of)

    def handle(entry: L1.BankEntry) -> BankResult:
        res = BankResult(id=entry.id, name=entry.name)
        # idempotency gate
        dpath = entry.resolve(base)
        if dump_dir:
            stamp = os.path.join(dump_dir, f".{entry.id}.stamp")
            cur = _dir_hash(dpath)
            try:
                if cur and os.path.exists(stamp) and open(stamp).read() == cur:
                    res.note = "skipped (unchanged)"; return res
            except OSError:
                pass
        try:
            parser = parser_for(entry.id)()
            pres = parser.parse(entry, base)
            res.partial = pres.partial
            res.note = pres.note
            res.spec_only = getattr(parser, "spec_only", False)
            res.not_implemented = pres.note.startswith("parser not implemented")
            for raw in pres.records:
                sc = L2.resolve_arch(raw.arch_hint, entry.id, bam, by_name)
                if sc is None or not config.arch_filter(sc.arch):
                    res.rejected += 1
                    continue
                raw.bank_id = entry.id
                out = normalizer.normalize(raw, sc, entry.id)
                if isinstance(out, L4.Reject):
                    res.rejected += 1
                    continue
                index.add(out)
                res.yielded += 1
        except (ParseError, FileNotFoundError) as e:
            res.error = f"{type(e).__name__}: {e}"
        except Exception as e:                       # isolation: log, continue
            res.error = f"{type(e).__name__}: {e}"
        # persist idempotency stamp
        if dump_dir:
            try:
                cur = _dir_hash(dpath)
                if cur:
                    open(os.path.join(dump_dir, f".{entry.id}.stamp"), "w").write(cur)
            except OSError:
                pass
        return res

    # ── parse/normalize (sequential or parallel) ──
    if config.workers > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=config.workers) as ex:
            report.banks = list(ex.map(handle, entries))
        report.banks.sort(key=lambda b: [e.id for e in entries].index(b.id))
    else:
        report.banks = [handle(e) for e in entries]

    report.conflicts = list(index.conflicts)
    records = index.records()
    report.records = len(records)

    # ── single merged write per backend ──
    for spec in config.backends:
        cls = BACKENDS.get(spec.name)
        if cls is None:
            raise KeyError(f"unknown backend {spec.name!r}")
        bk = cls().open(spec.target, mode="w")
        bk.begin()
        bk.put_schemas(arches)
        bk.put_records(records)
        bk.commit()
        bk.close()

    return report
