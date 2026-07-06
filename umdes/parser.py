"""uMDesc SLY parser. Produces the typed AST in :mod:`umdes.ast_nodes`.

Grammar per `uMDesc.md`. Operator precedence is declared so `action` body
expressions parse without left-recursion ambiguity.

Keyword lexemes (`op`, `mode`, `format`, ...) are reserved only as declaration
*leaders*; in any name slot they still lex as keyword tokens but are accepted by
the ``ident`` nonterminal below. This is what lets the spec's own example parse —
``format { cond[4] op[2] imm[1] ... }`` uses ``op`` as a field name even though
``op`` is a keyword. Without this, a hard keyword could never be a name.
"""
from __future__ import annotations

from sly import Parser

from .lexer import Lexer
from . import ast_nodes as A


class Parser(Parser):
    tokens = Lexer.tokens
    debugfile = None

    precedence = (
        ("left", "|", "^"),
        ("left", "&"),
        ("left", "+", "-"),
    )

    # --- top level ------------------------------------------------------
    @_("arch_list")
    def program(self, p):
        return A.File(decls=p.arch_list)

    @_("arch")
    def arch_list(self, p):
        return [p.arch]

    @_("arch_list arch")
    def arch_list(self, p):
        return p.arch_list + [p.arch]

    @_("ARCH name '{' arch_stmts '}'")
    def arch(self, p):
        return A.Arch(name=p.name, body=p.arch_stmts)

    # arch ids carry hyphens and digit segments (x86-64, mos6502, m68k);
    # '-' stays an operator in action exprs because those are space-separated.
    @_("name_part")
    def name(self, p):
        return p.name_part

    @_("name '-' name_part")
    def name(self, p):
        return f"{p.name}-{p.name_part}"

    @_("IDENT")
    def name_part(self, p):
        return p.IDENT

    @_("INT")
    def name_part(self, p):
        return str(p.INT)

    # Any user-chosen name accepts identifier lexemes *and* keyword lexemes.
    # The keyword tokens reach here because the lexer promotes reserved words,
    # but a name slot (field, register, op, param, alias, lvalue, call, expr)
    # should not be blocked merely for spelling like a keyword.
    @_("IDENT", "ARCH", "REGISTER", "MODE", "FORMAT", "OP", "ALIAS",
       "WORDSIZE", "ENDIANNESS", "LITTLE", "BIG", "SYNTAX", "IMAGE", "ACTION")
    def ident(self, p):
        return p[0]

    @_("")
    def arch_stmts(self, p):
        return []

    @_("arch_stmts arch_stmt")
    def arch_stmts(self, p):
        return p.arch_stmts + [p.arch_stmt]

    # --- simple arch statements ----------------------------------------
    @_("WORDSIZE INT ';'")
    def arch_stmt(self, p):
        return A.Wordsize(value=p.INT)

    @_("ENDIANNESS endian ';'")
    def arch_stmt(self, p):
        return A.Endianness(value=p.endian)

    @_("LITTLE")
    def endian(self, p):
        return "little"

    @_("BIG")
    def endian(self, p):
        return "big"

    @_("ALIAS ident '=' ident ';'")
    def arch_stmt(self, p):
        return A.Alias(name=p.ident0, target=p.ident1)

    @_("REGISTER ident '[' INT ',' INT ']' opt_names ';' ")
    def arch_stmt(self, p):
        return A.RegisterDecl(name=p.ident, count=p.INT0, width=p.INT1,
                              names=p.opt_names)

    @_("")
    def opt_names(self, p):
        return None

    @_("'=' '{' name_list '}'")
    def opt_names(self, p):
        return p.name_list

    @_("ident")
    def name_list(self, p):
        return [p.ident]

    @_("name_list ident")
    def name_list(self, p):
        return p.name_list + [p.ident]

    @_("name_list ',' ident")
    def name_list(self, p):
        return p.name_list + [p.ident]

    # --- format ---------------------------------------------------------
    @_("FORMAT ident '{' field_list '}'")
    def arch_stmt(self, p):
        return A.FormatDecl(name=p.ident, fields=p.field_list)

    @_("")
    def field_list(self, p):
        return []

    @_("field_list field")
    def field_list(self, p):
        return p.field_list + [p.field]

    @_("ident opt_width opt_comma")
    def field(self, p):
        return A.Field(name=p.ident, width=p.opt_width)

    @_("")
    def opt_comma(self, p):
        return None

    @_("','")
    def opt_comma(self, p):
        return None

    @_("")
    def opt_width(self, p):
        return None

    @_("'[' intrange ']'")
    def opt_width(self, p):
        return p.intrange

    @_("INT")
    def intrange(self, p):
        return p.INT

    @_("INT DOTDOT INT")
    def intrange(self, p):
        return (p.INT0, p.INT1)

    # --- mode (body reserved) ------------------------------------------
    @_("MODE ident '(' opt_params ')' '{' '}'")
    def arch_stmt(self, p):
        return A.ModeDecl(name=p.ident, params=p.opt_params, body=[])

    # --- op -------------------------------------------------------------
    @_("OP ident '(' opt_params ')' '{' op_attrs '}'")
    def arch_stmt(self, p):
        return A.OpDecl(name=p.ident, params=p.opt_params, attrs=p.op_attrs)

    @_("")
    def opt_params(self, p):
        return []

    @_("param_list")
    def opt_params(self, p):
        return p.param_list

    @_("param")
    def param_list(self, p):
        return [p.param]

    @_("param_list ',' param")
    def param_list(self, p):
        return p.param_list + [p.param]

    @_("ident ':' ident")
    def param(self, p):
        return A.Param(name=p.ident0, type_name=p.ident1)

    @_("")
    def op_attrs(self, p):
        return []

    @_("op_attrs op_attr")
    def op_attrs(self, p):
        return p.op_attrs + [p.op_attr]

    @_("SYNTAX STRING ';'")
    def op_attr(self, p):
        return A.SyntaxAttr(text=p.STRING)

    @_("IMAGE STRING ';'")
    def op_attr(self, p):
        return A.ImageAttr(text=p.STRING)

    @_("ACTION '{' stmts '}'")
    def op_attr(self, p):
        return A.ActionAttr(stmts=p.stmts)

    @_("")
    def stmts(self, p):
        return []

    @_("stmts stmt")
    def stmts(self, p):
        return p.stmts + [p.stmt]

    @_("lvalue '=' expr ';'")
    def stmt(self, p):
        return A.Assignment(lhs=p.lvalue, rhs=p.expr)

    @_("ident '(' opt_args ')' ';'")
    def stmt(self, p):
        return A.Call(name=p.ident, args=p.opt_args)

    @_("")
    def opt_args(self, p):
        return []

    @_("arg_list")
    def opt_args(self, p):
        return p.arg_list

    @_("expr")
    def arg_list(self, p):
        return [p.expr]

    @_("arg_list ',' expr")
    def arg_list(self, p):
        return p.arg_list + [p.expr]

    @_("ident")
    def lvalue(self, p):
        return A.LValue(name=p.ident)

    @_("ident '[' INT ']'")
    def lvalue(self, p):
        return A.LValue(name=p.ident, index=p.INT)

    # --- expressions ----------------------------------------------------
    @_("INT")
    def expr(self, p):
        return A.IntLit(value=p.INT)

    @_("ident")
    def expr(self, p):
        return A.IdentRef(name=p.ident)

    @_("ident '[' INT ']'")
    def expr(self, p):
        return A.IndexRef(base=p.ident, index=p.INT)

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    @_("expr '+' expr", "expr '-' expr", "expr '|' expr",
       "expr '&' expr", "expr '^' expr")
    def expr(self, p):
        return A.BinOp(op=p[1], left=p.expr0, right=p.expr1)

    def error(self, t):
        if t is None:
            raise SyntaxError("uMDesc parser: unexpected end of input")
        raise SyntaxError(f"uMDesc parser: unexpected {t.type} "
                          f"({t.value!r}) at line {t.lineno}")
