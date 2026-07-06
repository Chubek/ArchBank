"""CLI (XTRAKT.md §10). Surface: extract / banks / convert / check."""
from __future__ import annotations

import argparse
import os
import sys

from . import manifest as L1
from . import schema as L2
from .config import Config, DEFAULT_CONFIG
from .pipeline import extract
from .storage.base import BACKENDS, convert


def _load_config(args) -> Config:
    if args.config:
        cfg = Config.load(args.config)
    else:
        base = os.getcwd()
        cfg = Config.from_dict(__import__("yaml").safe_load(DEFAULT_CONFIG) or {}, base)
        cfg.manifest = os.path.join(base, "BANKS.yaml")
        cfg.records = os.path.join(base, "RECORDS.yaml")
        cfg.base_dir = base
    if getattr(args, "bank", None):
        cfg.banks = args.bank
    if getattr(args, "arch", None):
        cfg.arches = args.arch
    if getattr(args, "workers", None):
        cfg.workers = args.workers
    return cfg


def cmd_extract(args) -> int:
    cfg = _load_config(args)
    report = extract(cfg, dump_dir=args.idempotent)
    print(report.summary())
    return 0


def cmd_banks(args) -> int:
    base = os.getcwd()
    entries = L1.load(os.path.join(base, "BANKS.yaml"))
    _, arches = L2.load_schema(os.path.join(base, "RECORDS.yaml"))
    bam = L2.bank_arch_map(arches)
    rows = []
    for e in entries:
        a = bam.arches(e.id)
        if args.arch and args.arch not in a:
            continue
        rows.append((e.id, e.name, ",".join(a) or "-"))
    w = max((len(r[0]) for r in rows), default=10)
    print(f"{'id'.ljust(w)}  arches")
    for bid, name, a in rows:
        print(f"{bid.ljust(w)}  {a}")
    print(f"\n{len(rows)} banks" + (f" (arch={args.arch})" if args.arch else ""))
    return 0


def cmd_convert(args) -> int:
    n = convert(args.from_backend, args.input, args.to_backend, args.output)
    print(f"converted {n} records: {args.from_backend}({args.input}) -> "
          f"{args.to_backend}({args.output})")
    return 0


def cmd_check(args) -> int:
    cfg = _load_config(args)
    cfg.backends = []                 # no write
    report = extract(cfg)
    print(report.summary())
    if report.rejected or report.conflicts:
        print(f"\nCHECK FAILED: {report.rejected} rejected, "
              f"{len(report.conflicts)} conflicts")
        return 1
    print("\nCHECK OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xtrakt",
                                description="ArchBank extraction & storage pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="full run L1..L7")
    pe.add_argument("-c", "--config")
    pe.add_argument("-b", "--bank", action="append", default=None)
    pe.add_argument("-a", "--arch", action="append", default=None)
    pe.add_argument("--workers", type=int, default=None)
    pe.add_argument("--idempotent", default=None,
                    help="dir for content-hash stamps (skip unchanged banks)")
    pe.set_defaults(func=cmd_extract)

    pb = sub.add_parser("banks", help="list manifest / coverage")
    pb.add_argument("--arch", default=None)
    pb.set_defaults(func=cmd_banks)

    pc = sub.add_parser("convert", help="backend migration")
    pc.add_argument("--from", dest="from_backend", required=True,
                    choices=sorted(BACKENDS))
    pc.add_argument("--to", dest="to_backend", required=True,
                    choices=sorted(BACKENDS))
    pc.add_argument("--input", required=True)
    pc.add_argument("--output", required=True)
    pc.set_defaults(func=cmd_convert)

    pck = sub.add_parser("check", help="schema+mask validation, no write")
    pck.add_argument("-c", "--config")
    pck.add_argument("-b", "--bank", action="append", default=None)
    pck.set_defaults(func=cmd_check)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
