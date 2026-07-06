"""uMDesc lexer/parser/AST/visitor tests. Specs live in umdes/specs/."""
from __future__ import annotations

from pathlib import Path

import pytest

from umdes import parse, Lexer, Parser, BaseVisitor
from umdes import ast_nodes as A

SPECS = Path(__file__).resolve().parent.parent / "umdes" / "specs"


# --- lexer ---------------------------------------------------------------

def _types(text):
    return [t.type for t in Lexer().tokenize(text)]


def test_keywords_lex_as_their_token():
    assert _types("arch op mode format") == ["ARCH", "OP", "MODE", "FORMAT"]


def test_dotted_identifier_is_one_token():
    [tok] = list(Lexer().tokenize("R8.R15"))
    assert tok.type == "IDENT" and tok.value == "R8.R15"


def test_dotdot_splits_int_range_not_identifier():
    assert _types("0..15") == ["INT", "DOTDOT", "INT"]


def test_int_decimal_and_hex():
    vals = {t.value for t in Lexer().tokenize("64 0x10 0xFF")}
    assert vals == {64, 16, 255}


def test_string_unescapes_embedded_quote():
    [tok] = list(Lexer().tokenize(r'"a\"b"'))
    assert tok.value == 'a"b'


def test_string_keeps_other_backslashes_literal():
    # Spec: only `\"` is an escape; `\n` is two literal chars, not a newline.
    [tok] = list(Lexer().tokenize(r'"a\nb"'))
    assert tok.value == r'a\nb'


def test_nested_block_comment_stripped():
    assert _types("/* a /* b */ c */ arch") == ["ARCH"]


def test_line_comment_stripped():
    assert _types("// c\narch") == ["ARCH"]


def test_lineno_tracks_through_block_comment():
    toks = list(Lexer().tokenize("arch x {\n/* a\n b\n c */\n wordsize 8; }"))
    ws = next(t for t in toks if t.type == "WORDSIZE")
    assert ws.lineno == 5


def test_illegal_char_raises():
    with pytest.raises(SyntaxError):
        list(Lexer().tokenize("arch x { @ }"))


def test_unterminated_block_comment_raises():
    with pytest.raises(SyntaxError):
        list(Lexer().tokenize("/* never ends"))


# --- parser / AST --------------------------------------------------------

def _arch(body: str) -> A.Arch:
    return parse(f"arch t {{ {body} }}").decls[0]


def test_wordsize_endianness():
    a = _arch("wordsize 0x20; endianness big;")
    assert isinstance(a.body[0], A.Wordsize) and a.body[0].value == 32
    assert isinstance(a.body[1], A.Endianness) and a.body[1].value == "big"


def test_register_count_width_and_namelist():
    a = _arch("register GPR[16, 32] = { r0 r1 r2 };")
    r = a.body[0]
    assert (r.name, r.count, r.width, r.names) == ("GPR", 16, 32, ["r0", "r1", "r2"])


def test_register_without_namelist():
    r = _arch("register CPSR[1, 32];").body[0]
    assert r.names is None


def test_alias():
    a = _arch("alias PC = r15;")
    assert (a.body[0].name, a.body[0].target) == ("PC", "r15")


def test_fixed_and_variable_field_widths():
    f = _arch("format f { a[4], b[0..15], c }").body[0]
    assert [(x.name, x.width) for x in f.fields] == [
        ("a", 4), ("b", (0, 15)), ("c", None),
    ]


def test_keyword_field_names_accepted():
    f = _arch("format f { op[2] mode[1] }").body[0]
    assert [x.name for x in f.fields] == ["op", "mode"]


def test_space_separated_fields_without_commas():
    f = _arch("format f { a[1] b[2] c[3] }").body[0]
    assert [x.name for x in f.fields] == ["a", "b", "c"]


def test_mode_declaration_body_reserved():
    m = _arch("mode imm8(src: u8) { }").body[0]
    assert (m.name, [(p.name, p.type_name) for p in m.params]) == (
        "imm8", [("src", "u8")])


def test_op_attrs_assignment_and_call():
    op = _arch(
        'op ADD(Rd: GPR, Rn: GPR, operand2: op2) {'
        ' syntax "add"; image "0x0";'
        ' action { Rd = Rn + operand2; flags(Rd); } }'
    ).body[0]
    assert op.name == "ADD"
    assert [(p.name, p.type_name) for p in op.params] == [
        ("Rd", "GPR"), ("Rn", "GPR"), ("operand2", "op2")]
    by = {type(a).__name__: a for a in op.attrs}
    assert by["SyntaxAttr"].text == "add"
    assert by["ImageAttr"].text == "0x0"
    asn, call = by["ActionAttr"].stmts
    assert isinstance(asn, A.Assignment) and asn.lhs.name == "Rd"
    assert asn.rhs == A.BinOp("+", A.IdentRef("Rn"), A.IdentRef("operand2"))
    assert call == A.Call("flags", [A.IdentRef("Rd")])


def test_action_operator_precedence():
    # + tightest, then &, then | :  a | b & c + d  ==  a | (b & (c + d))
    op = _arch("op P() { action { r = a | b & c + d; } }").body[0]
    e = op.attrs[0].stmts[0].rhs
    assert e.op == "|"
    assert e.right.op == "&"
    assert e.right.right.op == "+"


def test_indexed_lvalue_and_indexref():
    op = _arch("op P() { action { a[0] = b[1]; } }").body[0]
    asn = op.attrs[0].stmts[0]
    assert asn.lhs == A.LValue("a", 0)
    assert asn.rhs == A.IndexRef("b", 1)


def test_parenthesized_expr():
    op = _arch("op P() { action { r = (a | b) & c; } }").body[0]
    e = op.attrs[0].stmts[0].rhs
    assert e.op == "&" and e.left.op == "|"


def test_hyphenated_arch_name():
    assert _arch("wordsize 8;").name == "t"
    assert parse("arch x86-64 { wordsize 64; }").decls[0].name == "x86-64"


def test_multiple_arches_in_one_file():
    tree = parse("arch a { wordsize 8; } arch b { wordsize 16; }")
    assert [d.name for d in tree.decls] == ["a", "b"]


def test_parser_rejects_missing_width_value():
    with pytest.raises(SyntaxError):
        parse("arch x { wordsize ; }")


# --- bundled specs -------------------------------------------------------

def test_arm_a32_spec_parses():
    tree = parse((SPECS / "arm-a32.umdesc").read_text())
    arch = tree.decls[0]
    assert arch.name == "arm-a32"
    fmt = next(s for s in arch.body if isinstance(s, A.FormatDecl))
    # `op` is a keyword yet a legal field name here.
    assert [f.name for f in fmt.fields] == [
        "cond", "op", "imm", "opcode", "S", "Rn", "Rd", "operand2"]
    op = next(s for s in arch.body if isinstance(s, A.OpDecl))
    assert op.name == "ADD"


def test_mos6502_spec_variable_width_and_modes():
    arch = parse((SPECS / "mos6502.umdesc").read_text()).decls[0]
    fmt = next(s for s in arch.body if isinstance(s, A.FormatDecl))
    widths = {f.name: f.width for f in fmt.fields}
    assert widths["op"] == 3 and widths["mode"] == 1
    assert widths["operand"] == (0, 8)
    assert [s.name for s in arch.body if isinstance(s, A.ModeDecl)] == [
        "imm8", "zp"]


# --- visitor -------------------------------------------------------------

def test_base_visitor_traverses_whole_tree():
    tree = parse((SPECS / "arm-a32.umdesc").read_text())
    seen = []

    class V(BaseVisitor):
        def visit_OpDecl(self, n):
            seen.append(n.name)
            return super().visit_OpDecl(n)

        def visit_Call(self, n):
            seen.append(f"call:{n.name}")
            return super().visit_Call(n)

        def visit_Field(self, n):
            seen.append(f"field:{n.name}")

    V().visit(tree)
    assert "ADD" in seen and "call:flags" in seen and "field:op" in seen
