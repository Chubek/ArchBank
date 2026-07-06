# uMDesc — Micro Machine Description Language

uMDesc is a small, declarative ISA-description language for ArchBank. It is
**nML-adjacent, not S-Expr-based**: brace-block structure, C-like punctuation,
keyword-led declarations. It captures the static machine model (word size,
endianness, register files, instruction formats, operand modes, and per-op
syntax/image/action) that the CIR’s dynamic encoding forms cannot express
uniformly across heterogeneous banks.

## Design goals

1. **Close to nML** — same vocabulary (`arch`, `register`, `mode`, `format`,
   `op`, `syntax`, `image`, `action`) and the same field/image/action split.
2. **Non-S-Expr** — braces, semicolons, infix operators; readable by humans who
   know nML or ADL.
3. **Minimal but real** — one grammar, parseable by SLY, with a typed AST and
   an abstract base visitor. Per-op semantic *transcoding* is left for later;
   `action` bodies are a structured statement list, not free text.
4. **ArchBank-shaped** — fields align with the CIR `FieldSpec` layer
   (`Fixed`/`Operand`), formats align with `emit_encoding`, ops align with
   `InstructionRecord`.

## Lexical

- Comments: `//` to end of line, and `/* ... */` blocks (may nest).
- Identifiers: `[A-Za-z_][A-Za-z0-9_.]*` (a `.` is allowed so `R8.R15`-style or
  dotted register names lex as one token where useful; ranges use `..`).
- Integers: decimal (`64`) or hex (`0x10`).
- Strings: `"..."` (no escapes beyond `\"`).
- Keywords (reserved): `arch register mode format op alias wordsize endianness
  little big syntax image action`.
- Punctuation: `{ } [ ] ( ) , : ; = .. + - & | ^ ~`

## Grammar

```
file        := decl*
decl        := arch
arch        := "arch" IDENT "{" arch-stmt* "}"
arch-stmt   := wordsize | endianness | register | mode | format | op | alias
wordsize    := "wordsize" INT ";"
endianness  := "endianness" ("little" | "big") ";"
register    := "register" IDENT "[" INT "," INT "]"
              ( "=" "{" namelist "}" )? ";"
namelist    := IDENT ("," IDENT)*
mode        := "mode" IDENT "(" params? ")" "{" mode-stmt* "}"
format      := "format" IDENT "{" field* "}"
field       := IDENT ("[" intrange "]")? ","?      // width or lo..hi range
intrange    := INT (".." INT)?
op          := "op" IDENT "(" params? ")" "{" op-attr* "}"
params      := param ("," param)*
param       := IDENT ":" IDENT                    // name : type-name
op-attr     := syntax | image | action
syntax      := "syntax" STRING ";"
image       := "image" STRING ";"
action      := "action" "{" stmt* "}"
stmt        := assign | call
assign      := lvalue "=" expr ";"
call        := IDENT "(" args? ")" ";"
lvalue      := IDENT ("[" INT "]")?
expr        := term (("+"|"-"|"|"|"&"|"^") term)*
term        := INT | IDENT | IDENT "[" INT "]" | "(" expr ")"
alias       := "alias" IDENT "=" IDENT ";"
```

## Static semantics

- `register NAME[count, width]` — `count` slots, each `width` bits. The
  optional `{ namelist }` binds symbolic names to slots `0..count-1`.
- `format` — an MSB-first ordered field list; a field `[w]` is a fixed-width
  slot, `[lo..hi]` a variable-width slot (matches CIR `width="variable"`).
  Field order is the encoding order fed to `emit_encoding`.
- `op` — one instruction. `params` name operand slots and their register-class
  type. `syntax` is the assembler text (`$name` placeholders). `image` is the
  symbolic encoding template. `action` is a structured statement list
  (assignments + calls) over `lvalue`s and `expr`s; the base visitor walks it
  but transcoding to P-Code is out of scope here.
- `mode` — an addressing/operand mode (nML `mode`); body reserved.
- `alias` — register aliasing (`alias PC = R15;`).

## Example

```
arch arm-a32 {
    wordsize 32;
    endianness little;

    register GPR[16, 32] = { r0 r1 r2 r3 r4 r5 r6 r7 r8 r9 r10 fp ip sp lr pc };
    register CPSR[1, 32];
    alias FP = r11;
    alias IP = r12;
    alias LR = r14;
    alias PC = r15;

    format arm {
        cond[4] op[2] imm[1] opcode[4] S[1] Rn[4] Rd[4] operand2[12]
    }

    op ADD(cond: cond, Rd: GPR, Rn: GPR, operand2: operand2) {
        syntax "add$cond $Rd, $Rn, $operand2";
        image "0x0 /op=0 /S=0";
        action {
            Rd = Rn + operand2;
            flags(Rd);
        }
    }
}
```

## Pipeline placement

uMDesc sits beside the L2 schema as a *human-authored* machine model. Future
work: a visitor that lowers a `uMDesc` `arch` into `ArchSchema`/`FieldSpec`
records and a transcoder that lowers `action` bodies into P-Code
`(define-semantics ...)`. For now only the parser, AST, and an abstract base
visitor exist.
