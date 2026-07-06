$Version: 1.0.0
$Project: "ArchBank"
$Dataset: "P-Code.md"
$Description: >-
  P-Code: the ArchBank S-expression pseudo-code dialect (a Scheme
  subset) used to write Instruction-Record Encoding Functions and
  Semantics. See RECORDS.yaml for its use.

---

# P-Code

A minimal S-expression language, Scheme-dialect, for two roles inside an
Instruction Record (RECORDS.yaml):

1. **Encoding Function** — pure: `(operands, machine-state) -> bitvector`.
   Mandatory per record.
2. **Semantics** — effectful: `(operands, machine-state) -> state'`.
   Optional; present only where a bank offers behavioral data.

Design goals: evaluable, width-explicit, architecture-neutral, no hidden
lowering, side-effect-isolated.

---

## 1. Lexical Syntax

| Token         | Meaning                                                      |
|---------------|--------------------------------------------------------------|
| `(...)`       | list / form                                                  |
| `sym`         | symbol (identifier, opcode, operand)                         |
| `123`         | decimal integer                                              |
| `#x0F`        | hex bitvector literal (width = 4 × nibbles)                  |
| `#b1010_0011` | binary bitvector literal (width = digit count; `_` ignored)  |
| `"..."`       | string (asm template only; not evaluated)                    |
| `; ...`       | line comment                                                 |
| `a..b`        | bit range, inclusive, `a >= b`, big-endian bit index         |

Bit indexing: MSB = 0. `bits 31..0` denotes a 32-bit field in full.

---

## 2. Types

| Type       | Denotation                                   |
|------------|----------------------------------------------|
| `bv`       | bitvector of explicit width `n`              |
| `int`      | unbounded integer (indices, widths only)     |
| `bool`     | `{0,1}`                                      |
| `reg`      | register token (operand)                     |
| `mem`      | memory handle (load/store target)            |

Every `bv` carries its width. Width-mismatch in a binary op is an error
(no implicit coercion). Two bvs are equal only if same width and value.

**Width of a literal** = its digit count: `#b101` is `bv3`; `#x3F` is `bv8`;
`#x0001` is `bv16`.

**Operand declarations** bind a name to a typed slot:

```
(rd  :GPR 5)        ; general-register operand, 5-bit field
(rs1 :GPR 5)
(imm :IMM 12)       ; 12-bit immediate operand
(cond :COND 4)
(mem :MEM 32)
```

The trailing integer is the encoding width, i.e. the field consumes that
many bits. `:TYPE` is a category tag from the arch's register/operand
model (GPR, FPR, VEC, IMM, COND, PRED, MASK, MEM, LABEL, ...).

---

## 3. Encoding Function

A pure function returning a `bv` of a fixed instruction width.

```
(define-encoding (name (op :TYPE w) ...) <out-width>
  <expr> ...)
```

`<out-width>` is the emitted instruction width in bits. For
variable-length encodings the body selects width by branch
(see x86 example in RECORDS.yaml).

### 3.1 Constructors

| Form                       | Result                                         |
|----------------------------|------------------------------------------------|
| `(cat e1 e2 ... eN)`       | concatenation; e1 = most-significant           |
| `(bits e hi lo)`           | extract inclusive range -> `bv (hi-lo+1)`      |
| `(field name e w)`         | alias: assert `width(e)=w`, tag `name`, = `e`  |
| `(const #x.. / #b..)`      | literal as a fixed-width field                 |
| `(zext w e)`               | zero-extend `e` to width `w`                   |
| `(sext w e)`               | sign-extend `e` to width `w`                   |
| `(trunc w e)`              | keep low `w` bits                              |
| `(rep w e)`                | replicate `e` until width `w`                  |

### 3.2 Operators (width-preserving; operands equal width)

```
(+ - * / %)        arithmetic (two's-complement wrap on bv)
(& | ^ ~)          bitwise
(<< >> >>>)        logical left / logical right / arithmetic right
(if c t e)         ternary (c : bool)
```

### 3.3 Encoding state inputs

Some encodings depend on machine mode (operand size, current EL, PC).
These are read-only globals:

```
(mode)            ; e.g. :32, :64, :SVE, :thumb
(el)              ; exception level (AArch64)
(pc)              ; current program counter (for PC-relative)
(features ...)    ; feature-gate predicate
```

### 3.4 Example (RISC-V `ADDI`)

```
(define-encoding (addi (rd :GPR 5) (rs1 :GPR 5) (imm :IMM 12)) 32
  (cat (field imm imm 12)            ; imm[11:0]  (12)
       (field rs1 rs1 5)             ; rs1        (5)
       (const #b000)                 ; funct3     (3)
       (field rd  rd  5)             ; rd         (5)
       (const #b0010011)))           ; opcode OP-IMM (7)
```

Bit order is MSB-first, so the emitted 32-bit word reads left-to-right
as `imm(12) | rs1(5) | funct3(3) | rd(5) | opcode(7)` — the canonical
RISC-V layout (bits[31:20]=imm, [19:15]=rs1, [14:12]=funct3,
[11:7]=rd, [6:0]=opcode).

---

## 4. Semantics

An effectful function describing the instruction's state transition.
Pure expressions use §3.2 operators; effects use the forms below.

```
(define-semantics (name (op :TYPE w) ...)
  <effect or expr> ...)
```

A semantic body is an implicit `(seq ...)` of effects; the last value,
if pure, is the result expression (meaningful for `wasm`'s stack model).

### 4.1 Effects

| Form                                   | Meaning                                    |
|----------------------------------------|--------------------------------------------|
| `(set! loc expr)`                      | assign `loc <- expr`                       |
| `(set-flags! (name expr) ...)`         | assign named flags                         |
| `(load type addr)`                     | memory read (`type` = size/sign)           |
| `(store type addr val)`                | memory write                               |
| `(set-pc! expr)`                       | write PC (branch)                          |
| `(branch cond target)`                 | conditional jump                           |
| `(call target)` / `(return)`           | control transfer with link                 |
| `(push val)` / `(pop -> name)`         | operand-stack ops (WASM, x87)              |
| `(trap code)`                          | raise exception                            |
| `(seq e ...)`                          | left-to-right sequencing                   |
| `(when c e ...)` / `(unless c e ...)`  | guarded effects                            |
| `(let ((x e) ...) body)`               | pure binding                               |

### 4.2 Locations

```
GPR[i]            ; general register file
FPR[i] / VEC[i]   ; float / vector file
FLAG[name]        ; named flag (C,Z,N,V, ...)
MEM[addr :size]   ; memory at width
PC                ; program counter
```

### 4.3 Comparisons & flag helpers (return bool / bv)

```
(< <= = != >= >)  (signed)      ; also (u< u<= ...) unsigned
(add-with-carry a b cin)        ; -> (values sum cout) tuple
(overflow? a b op)              ; signed-overflow predicate
(msb e) (lsb e)                 ; single-bit extract
```

### 4.4 Example (AArch64 `ADDS` semantics sketch)

```
(define-semantics (adds-imm (rd :GPR 5) (rn :GPR 5) (imm :IMM 12) (sh :SH 1)) 32
  (let ((full (zext 64 (if (= sh 1) (<< imm 12) imm)))
        (a    (zext 64 GPR[rn]))
        (res  (+ a full)))
    (set! GPR[rd] (trunc 64 res))
    (set-flags! (N (msb res))
                (Z (= res 0))
                (C (carry-out a full))
                (V (overflow? a full +)))))
```

---

## 5. Conventions

- **Purity**: Encoding Functions are referentially transparent. Side
  effects appear only in Semantics.
- **Widths are explicit**: no `int`-to-`bv` promotion. Use
  `(zext/sext/trunc)` for width changes.
- **Field order** in `(cat ...)` is MSB-first text order, matching ISA
  manual diagrams. Field widths must sum to `<out-width>`.
- **Named fields**: `(field name ...)` is required for operand-bearing
  bits so a decoder can invert the encoding by field name.
- **Branching**: `(if c t e)` width-unifies `t`,`e`; both branches must
  yield equal-width bvs.
- **No hidden lowering**: SIMD/predication is expressed via explicit lane
  and mask operands; the dialect does not synthesize micro-ops.
- **Determinism**: P-Code excludes `(random)`, wall-clock, and
  unspecified evaluation order inside a single `(seq)` other than
  left-to-right.

---

## 6. Decoder Inversion

A record's Encoding Function is invertible by construction: collect the
`(field name e w)` and `(const ...)` forms; each yields a fixed
`(<mask>, <match>)` pair. The conjunction of all pairs is the
instruction's decode signature. Semantics is not inverted; it is
lifted verbatim to the target IR.
