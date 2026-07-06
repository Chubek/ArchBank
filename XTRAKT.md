$Version: 1.0.0
$Project: "ArchBank"
$Dataset: "XTRAKT.md"
$Description: >-
  Design specification for `xtrakt`, the ArchBank extractor library
  (package rooted at `xtrakt/`). `xtrakt` reads the bank manifest
  (BANKS.yaml) and the per-architecture Instruction-Record schema
  (RECORDS.yaml), parses each source, normalizes parsed records into the
  ArchBank Instruction Record, synthesizes P-Code (P-Code.md) for the
  encoding function and (where available) semantics, derives the decode
  signature, and persists the result through a pluggable, registry-backed
  storage layer (sqlite3 / JSON / YAML / BSON / XML by default; extensible).

---

# xtrakt

## 0. Scope

`xtrakt` is a **declarative extraction-and-storage pipeline**, not a
disassembler and not a P-Code evaluator.

In:

- `BANKS.yaml` — bank manifest; one `BankEntry` per source (id, directory,
  extraction_hint).
- `RECORDS.yaml` — `record_base` + per-arch `record` schema; the target
  Instruction-Record shape.
- `P-Code.md` — the S-expr dialect for `encoding_function` (mandatory) and
  `semantics` (optional).

Out:

- A set of normalized **Instruction Records** written to one or more
  **storage backends** in a backend-agnostic canonical form.

Non-goals (explicit):

- disassembly / assembly of bytes;
- P-Code evaluation, simulation, JIT;
- legality, selection, lowering, scheduling;
- register-allocation;
- any stateful machine model beyond field/value extraction.

---

## 1. Architecture

Layered; each layer is pure-data-in → pure-data-out. No layer reaches into
another's internals; control flows one direction (manifest → records).

```
BANKS.yaml ─┐
            ├─▶ L1 Manifest ─▶ L3 Parser ─▶ L4 Normalizer ─▶ L5 P-Code ─▶ L6 Mask ─▶ L7 Storage
RECORDS.yaml ┤     (work list)   (per-bank)   (raw→record)   (emit+   (decode    (backends)
            │                                                transcode) signature)
P-Code.md ──┘
                                                       L2 Schema (record_base + arch record)
                                                       L8 Pipeline (driver, isolation, dedup)
```

| Layer | Responsibility                                  | Input → Output                                   |
|-------|-------------------------------------------------|--------------------------------------------------|
| L1    | manifest load                                   | `BANKS.yaml` → `list[BankEntry]`                 |
| L2    | schema load                                     | `RECORDS.yaml` → `record_base`, `ArchSchema[]`   |
| L3    | source parse (per-bank, format-family)          | `BankEntry` → `Iterable[RawRecord]`              |
| L4    | normalize + validate + dedup                    | `RawRecord`+`ArchSchema` → `InstructionRecord`   |
| L5    | P-Code emit + foreign-semantics transcode       | field layout → `encoding_function`, `semantics`  |
| L6    | decode-signature derivation (P-Code §6)         | `encoding_function` → `(decode_mask,decode_match)`|
| L7    | storage (pluggable backends)                    | `InstructionRecord[]` → backend target           |
| L8    | orchestration, idempotency, isolation           | config → runs L1..L7                             |

Constraints:

- every `InstructionRecord` is a value object; backends are pure
  (de)serializers of it;
- `encoding_function` is mandatory (reject record if absent);
- `semantics` is optional; absence is a legal record, not an error;
- no silent caps / silent merges — partial parses and conflicts are logged
  with counts.

---

## 2. Inputs

### 2.1 Manifest (`BANKS.yaml`)

```
BankEntry:
  id: str               # primary key; referenced by RECORDS.yaml
  name: str
  directory: str        # path under bank/
  sourced_from: str
  extraction_hint: str  # prose strategy → drives L3 parser selection
```

L1 loads all 58 entries; the `extraction_hint` field is the parser-dispatch
signal (format family + arch coverage + known gotchas). L3 maps `id →
SourceParser`.

### 2.2 Schema (`RECORDS.yaml`)

```
record_base:   14 common fields (mnemonic, aliases, isa_ext, cpuid,
               encoding_class, encoding_function, decode_mask,
               decode_match, semantics, flags_read, flags_write,
               memory_access, category, privilege).
ArchSchema:    {arch, full_name, encoding_class, width_bits,
               operand_types, encoding_banks[], semantics_banks[],
               record[] (arch-specific fields)}.
```

`record[]` field order **is the MSB-first layout template** L5 uses to order
emitted P-Code fields. `encoding_banks`/`semantics_banks` constrain which
banks may contribute which half of a record (§6.3).

### 2.3 P-Code (`P-Code.md`)

L5 emits `define-encoding` / `define-semantics` forms; L6 inverts per §6
(collect `(field ...)` and `(const ...)`, each yields a `(mask,match)` pair).

---

## 3. Canonical Intermediate Representation (CIR)

The single backend-agnostic record object. Every backend serializes the
CIR; adding a backend never touches L3–L6.

```
InstructionRecord:                       # = record_base + arch fields
  arch: str
  # ── record_base ───────────────────────────────────────────────
  mnemonic:           str
  aliases:            list[str]?
  isa_ext:            str
  cpuid:              str?
  encoding_class:     enum               # from ArchSchema
  encoding_function:  str                # P-Code text (define-encoding …)
  decode_mask:        BitVec             # derived (L6)
  decode_match:       BitVec             # derived (L6)
  semantics:          str?               # P-Code text, or null
  flags_read:         list[str]?
  flags_write:        list[str]?
  memory_access:      enum?
  category:           str?
  privilege:          enum?
  # ── arch-specific fields ───────────────────────────────────────
  fields:             dict[str, FieldValue]   # ArchSchema.record[] names
  # ── provenance ────────────────────────────────────────────────
  source_banks:       list[str]               # BANKS.yaml ids
  decode_schematic:   bool                   # True ⇒ no uniform mask (§13)
```

### 3.1 FieldValue & BitVec

All field values are JSON-native (round-trippable through every backend):

```
FieldValue = str | int | bool | list[FieldValue] | dict | BitVec
BitVec     = {"width": int, "hex": str}      # width in bits; hex, lowercase, no prefix
```

`bv`-kind fields (`decode_mask`, `decode_match`, arch `bv` fields) all use
`BitVec`. The width is carried explicitly so leading zeros survive the
YAML/XML round trip. Example: RISC-V `addi` opcode `#b0010011` ⇒
`{"width":7,"hex":"13"}`.

### 3.2 Record identity / dedup key

```
key = (arch, mnemonic, encoding_class, operand_signature, isa_ext)
```

A key produced by several banks (an instruction in multiple
`encoding_banks`) is merged: `source_banks` unions; `encoding_function` /
`semantics` are kept from the highest-precedence bank (config-defined
order), conflicting encodings are **flagged**, never silently overwritten.

---

## 4. L3 — Source Parsers

One parser (or one shared format-family parser) per bank. A parser produces
**raw, source-shaped** records (`RawRecord`, a loose dict); it does not know
the ArchBank schema — that is L4's job. This keeps format knowledge and
schema knowledge separate.

```
class SourceParser(ABC):
    bank_ids: ClassVar[list[str]]          # BANKS.yaml ids this parser serves
    @abstractmethod
    def parse(self, entry: BankEntry) -> Iterator[RawRecord]: ...
```

Registration:

```
PARSERS: dict[str, type[SourceParser]] = {}      # bank_id -> SourceParser
def register_parser(cls): PARSERS[cls.bank_ids] = cls; return cls
# entry-point group: xtrakt.parsers  (plugin discovery)
```

### 4.1 Format families (parser reuse, not one-per-bank)

| Family             | Banks (examples)                                                  | Strategy (from extraction_hint)                            |
|--------------------|-------------------------------------------------------------------|------------------------------------------------------------|
| JSON DB            | asmjit-db, x86-dataset                                            | load; per-instruction dict → RawRecord                     |
| YAML/enc tables    | riscv-opcodes, mir-data, sljit-data                               | parse `enc`/opcode tables; one record per (mnemonic, fmt)  |
| TableGen (.td)     | llvm-td                                                           | `llvm-tblgen -dump-json` per target; **no regex scrape**   |
| XML                | xed-datafiles, capstone-arch (xml), zydis-metadata                | XML→RawRecord map                                          |
| C tables / headers | beaengine-instrset, nasm-data, fasm-inc, yasm-arch, distorm-disops| row-regex over static arrays; col = addressing mode        |
| C++ modules        | bochs-cpu, dynasm-opcodes                                         | scrape instruction-desc tables                             |
| Sleigh (.sleigh)   | ghidra-cpu                                                        | constructor+op pairs; semantics transcoder (§6.3)          |
| SSL                | boomerang-ssl, fracture-target                                    | semantic-transfer language → P-Code transcoder             |
| GCC `.md`          | gcc-md, lcc-md                                                    | `define_insn` RTL → P-Code transcoder                      |
| TCG / spec         | qemu-targets, qemu-tcg, pydgin-arch, impact-mspec, decaf-qemu     | helper/DSL → semantics; encoding sparse                    |
| Asm .inc / .i      | acme-opcodes, upython-asm, tcc-instrfiles                         | matrix: mnemonic × addressing mode                         |
| Spec-only (no enc) | libvirt-cpu, pistachio-arch, libjit-spec                          | register/feature model only → **zero instruction records** |

The spec-only banks yield no Instruction Records; L8 logs `yielded=0` and
moves on (provenance still recorded as a known no-op source).

---

## 5. L4 — Normalizer

```
class Normalizer:
    def normalize(self, raw: RawRecord, schema: ArchSchema) -> InstructionRecord | Reject
```

Steps:

1. resolve `arch` from bank→arch map (RECORDS.yaml `encoding_banks` /
   `semantics_banks` constrain membership);
2. coerce raw fields to `FieldValue` / `BitVec` per `schema.record[]`
   `kind`/`width`;
3. require `mnemonic`, `isa_ext`, `encoding_class` (record_base required
   set); reject otherwise;
4. attach `encoding_function` (from L5; mandatory) — reject if absent;
5. attach `semantics` if the bank is a `semantics_bank` AND a transcoder
   produced one (else null);
6. compute dedup key; merge / flag per §3.2.

Validation is declarative against `RECORDS.yaml`, never a hardcoded switch
(AGENTS.md §Architecture-2).

---

## 6. L5 — P-Code Synthesis

Two sub-layers: an **emitter** (encodings, always) and **transcoders**
(semantics, best-effort).

### 6.1 Emitter: field layout → `encoding_function`

Input: the instruction's MSB-first field list (bank layout or
`ArchSchema.record[]` order). Output: a `(define-encoding …)` form.

```
emit(name, width, fields) ->
  "(define-encoding (name <op-decls>) width (cat <forms>))"
  where each field:
    fixed bits   -> "(const #x..)"  / "(const #b..)"
    operand slot -> "(field <name> <operand> <width>)"
```

Width rule (P-Code §5): field widths in `(cat …)` must sum to `<width>`;
the emitter asserts this and rejects malformed banks. Operand declarations
come from `ArchSchema.record[]` for the operand-bearing fields.

RISC-V `addi` (matches RECORDS.yaml):

```
(define-encoding (addi (rd :GPR 5) (rs1 :GPR 5) (imm :IMM 12)) 32
  (cat (field imm imm 12) (field rs1 rs1 5) (const #b000)
       (field rd rd 5) (const #b0010011)))
```

### 6.2 Variable & packet encodings

- variable (x86-64, s390, m68k, mos6502, wasm): `<width>` is the fixed
  slice; prefix/extension bytes are emitted as separate fields and
  `decode_schematic=False`, but the mask spans only the fixed slice (prefix
  context is a join key, per RECORDS.yaml x86 notes);
- packet / format-table (hexagon, tricore): no uniform `(mask,match)`. The
  emitter emits the schematic form verbatim (`place-by-format`, already in
  RECORDS.yaml), sets `decode_schematic=True`, and L6 emits a **null mask**
  rather than fabricating one (§13).

### 6.3 Semantics transcoders (best-effort)

`semantics` exists only where a `semantics_bank` provides it in a form
xtrakt can map to P-Code. One transcoder per foreign formalism:

| Source formalism | Banks                       | Transcoder                | Coverage |
|------------------|-----------------------------|---------------------------|----------|
| Ghidra Sleigh    | ghidra-cpu                  | sleigh→P-Code             | partial  |
| SSL              | boomerang-ssl, fracture     | ssl→P-Code                | partial  |
| GCC RTL `.md`    | gcc-md, lcc-md              | rtl→P-Code                | partial  |
| QEMU TCG helpers | qemu-targets, qemu-tcg      | tcg→P-Code                | sparse   |
| Simulators       | pydgin-arch, impact-mspec   | mspec→P-Code              | sparse   |
| LLVM TableGen DAG| llvm-td (pattern fragments) | dag→P-Code                | sparse   |

No transcoder ⇒ `semantics=null` (legal). xtrakt **never synthesizes**
behavior it cannot source (AGENTS.md: no hidden lowering). A coverage map
(per-source-family) is emitted alongside the run so absent semantics is
visible, not silent.

---

## 7. L6 — Decode Signature

Implements P-Code.md §6. Walk the emitted `(cat …)`:

```
for each operand at bit-offset o, width w:
    (const c)   -> mask |= ones(o,w);  match |= c << o
    (field _ _ _) -> mask unchanged at o..o+w-1 (operand, don't-care)
decode_mask  = BitVec(width, mask)
decode_match = BitVec(width, match)
```

Stored in `record_base.decode_mask` / `decode_match`. For
`decode_schematic=True` records both are null with a `schematic` note
(Hexagon/TriCore honestly cannot yield a single bit-mask).

---

## 8. L7 — Storage Adapters (the "adaptable" layer)

A backend is a pure `(de)serialize` of the CIR. "Adaptable" has three
meanings, all satisfied by one mechanism (the registry):

1. **choose at run time** which backend(s) to write;
2. **migrate** between backends (`read A → write B`);
3. **extend** by registering a new backend — no pipeline change.

### 8.1 Backend contract

```
class StorageBackend(ABC):
    name: ClassVar[str]
    def open (self, target, mode="w"): ...
    def put_schemas (self, schemas: list[ArchSchema]): ...
    def put_records(self, records: Iterable[InstructionRecord]): ...
    def get_records(self, *, arch=None, mnemonic=None) -> Iterator[InstructionRecord]: ...
    def begin/commit/rollback (self): ...        # no-op for file backends
    def close (self): ...

BACKENDS: dict[str, type[StorageBackend]] = {
    "sqlite3": SQLiteBackend,
    "json":    JSONBackend,
    "yaml":    YAMLBackend,
    "bson":    BSONBackend,
    "xml":     XMLBackend,
}
def register_backend(name, cls): BACKENDS[name] = cls
# entry-point group: xtrakt.backends  (third-party backends)
```

A backend MAY be write-only (skip `get_records`); the pipeline still works
— read is only needed for migration/dedup reload.

### 8.2 Default backends

| Backend  | Target           | Shape                                                                                  | When                                |
|----------|------------------|----------------------------------------------------------------------------------------|-------------------------------------|
| sqlite3  | `.db` (default)  | hybrid (§8.3)                                                                          | queryable DB, indexing, scale       |
| json     | `.json`          | `{"version","schema","records":[CIR…]}`                                               | interchange, tooling                |
| yaml     | `.yaml`          | same object, block style                                                               | human-edit, diff, review            |
| bson     | `.bson` / Mongo  | CIR docs; `BitVec` as nested doc; MongoDB round-trip                                   | compact binary, Mongo integration   |
| xml      | `.xml`           | `<archbank><arch name=…><record …><field name=…>…</record></arch></archbank>` + XSD    | enterprise / XSD toolchains         |

### 8.3 sqlite3 hybrid schema (recommended default)

One uniform schema; arch-specific fields live in a JSON column (no per-arch
DDL explosion), record_base columns are first-class for indexing:

```
records(
  arch TEXT, mnemonic TEXT, isa_ext TEXT, encoding_class TEXT,
  category TEXT, privilege TEXT, memory_access TEXT,
  encoding_function TEXT,            -- P-Code
  semantics TEXT,                    -- P-Code or NULL
  decode_mask TEXT, decode_match TEXT,  -- BitVec JSON
  decode_schematic INTEGER,
  source_banks TEXT,                 -- JSON array of ids
  fields TEXT,                       -- JSON: arch-specific FieldValue map
  PRIMARY KEY(arch, mnemonic, encoding_class, isa_ext, fields_sig)
)
CREATE INDEX ix_mnemonic ON records(mnemonic);
CREATE INDEX ix_arch     ON records(arch);
schemas(arch TEXT PRIMARY KEY, record_base TEXT, record TEXT);  -- RECORDS.yaml shapes
banks(id TEXT PRIMARY KEY, name TEXT, directory TEXT, yielded INTEGER);
```

`BitVec` columns store the CIR dict as JSON text; sqlite JSON1 enables
in-DB queries on `fields` if needed.

### 8.4 Migration

```
convert(src_backend, src_target, dst_backend, dst_target):
    recs = src.open(src_target,"r").get_records()
    dst.open(dst_target,"w").put_records(recs)
```

Same CIR ⇒ lossless across all five defaults (verified by read-back
equality in the test harness).

---

## 9. L8 — Pipeline

Declarative DAG driver over L1..L7.

```
run(config):
    entries   = L1.load(manifest)                       # BANKS.yaml
    schemas   = L2.load_schema(records)                 # RECORDS.yaml
    arch_by_bank = L2.bank_arch_map(schemas)            # encoding/semantics banks
    backends  = [BACKENDS[n].open(...) for n in config.backends]
    for entry in entries:                               # per-bank, isolated
        try:
            raws = L3.PARSERS[entry.id]().parse(entry)
            for raw in raws:
                sch = schemas[arch_by_bank[entry.id][raw.fmt]]
                rec = L4.normalize(raw, sch)            # L5 + L6 inside
                if rec: merge(rec)                      # dedup/merge
        except ParseError as e:
            log(entry.id, e); continue                  # isolation: one bank ≠ abort
    for b in backends: b.put_schemas(schemas); b.put_records(all_records)
```

Properties:

- **isolation**: a bank's failure is logged with a count; the run continues;
- **idempotency**: content hash of `entry.directory` gates re-parse (skip if
  unchanged and a prior dump exists);
- **concurrency**: banks are independent ⇒ parallel parse/normalize, single
  merged write per backend;
- **no silent caps**: banks yielding 0 (spec-only), records rejected on
  schema violation, and conflicting-key merges are all surfaced in a run
  report, never dropped silently.

---

## 10. Configuration & CLI

Declarative YAML config (AGENTS.md §Architecture-2: prefer declarative):

```
manifest: BANKS.yaml
records:  RECORDS.yaml
banks:    all            # or [llvm-td, asmjit-db, …]
arches:   all            # or [x86-64, riscv, …]
backends:
  - {name: sqlite3, target: archbank.db}
  - {name: yaml,    target: archbank.yaml}
```

CLI surface (minimal):

```
xtrakt extract  [-c config]                 # full run
xtrakt banks    [--arch x86-64]             # list manifest / coverage
xtrakt convert  --from json --to sqlite3    # backend migration
xtrakt check    [-c config]                 # schema+mask validation, no write
```

---

## 11. Module Layout

```
xtrakt/
  __init__.py
  manifest.py            # L1: BANKS.yaml -> BankEntry[]
  schema.py              # L2: RECORDS.yaml -> record_base, ArchSchema[]
  cir.py                 # InstructionRecord, FieldValue, BitVec
  normalize.py           # L4: RawRecord -> InstructionRecord + dedup/merge
  pcode/
    emitter.py           # L5: field layout -> encoding_function
    decoder.py           # L6: encoding_function -> (decode_mask,decode_match)
    transcoders/         # L5 semantics: sleigh, ssl, rtl, tcg, mspec, dag
  parsers/               # L3: one module per bank family
    base.py              # SourceParser ABC + PARSERS registry + register_parser
    asmjit_json.py  llvm_td.py  xed_datafiles.py  capstone_arch.py
    ghidra_sleigh.py  riscv_opcodes.py  ctable.py  sleigh_ssl.py  ...
  storage/
    base.py              # StorageBackend ABC + BACKENDS + register_backend
    sqlite.py json.py yaml.py bson.py xml.py
  pipeline.py            # L8: driver, isolation, idempotency, report
  config.py  cli.py
```

---

## 12. Extensibility

| Add            | Mechanism                                                       | Touches             |
|----------------|-----------------------------------------------------------------|---------------------|
| bank parser    | subclass `SourceParser`, `register_parser`, or entry-point      | `parsers/` only     |
| storage format | subclass `StorageBackend`, `register_backend`, or entry-point   | `storage/` only     |
| arch schema    | add a `- arch:` block to `RECORDS.yaml`; add bank→arch links    | data only, no code  |
| semantics src  | add a transcoder in `pcode/transcoders/`                        | `pcode/` only       |

Each extension is additive; no existing layer is modified (open-closed).

---

## 13. Failure Modes

- **format-table arches** (hexagon, tricore): no uniform `(mask,match)`;
  `decode_schematic=True`, null mask, schematic `encoding_function` — never
  fabricated.
- **variable-length** (x86-64, s390, m68k, mos6502, wasm): mask spans fixed
  slice only; length/prefix is a separate join key, not a field.
- **semantics gaps**: no transcoder ⇒ `semantics=null`; recorded in coverage
  map, not silently dropped.
- **schema violation** (missing `encoding_function` / required base field):
  record rejected, logged with bank id.
- **ambiguous mnemonic→arch** (`add` is many arches): resolved by bank→arch
  map, never by guess; unmappable raw record rejected.
- **conflicting encoding for one key**: flagged, not overwritten.
- **spec-only bank** (libvirt-cpu et al.): `yielded=0`, logged, run
  continues.
- **partial parse** within a bank: emitted partial count + offset; bank
  marked incomplete, downstream merge still consumes what parsed.

---

## 14. Storage Fidelity (round-trip)

Any `InstructionRecord` written by any default backend is loadable back to
an equal CIR object; `convert(json → bson → xml → sqlite3 → yaml)` is
lossless. The test harness asserts CIR equality across the full backend
permutation per record — this is the operational definition of "adaptable".
