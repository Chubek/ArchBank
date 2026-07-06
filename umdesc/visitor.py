"""uMDesc base visitor.

Abstract walker over the AST in :mod:`umdes.ast_nodes`. Subclasses override
the ``visit_*`` hooks they care about; defaults recurse into children so a
partial visitor still traverses the whole tree. Transcoding (e.g. to
``ArchSchema`` or P-Code) is left for later — this class fixes the traversal
contract only.
"""
from __future__ import annotations

from abc import ABC
from typing import Any

from . import ast_nodes as A

# All concrete AST node classes (for generic recursion dispatch).
_NODE_TYPES = tuple(v for v in vars(A).values()
                    if isinstance(v, type) and hasattr(v, "__dataclass_fields__"))


class BaseVisitor(ABC):
    """Abstract recursive AST visitor. Not instantiated directly; concrete
    visitors inherit and override ``visit_*`` methods."""

    # --- entry ----------------------------------------------------------
    def visit(self, node: Any) -> Any:
        if node is None:
            return None
        if isinstance(node, list):
            return [self.visit(n) for n in node]
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            return self.generic_visit(node)
        return method(node)

    def generic_visit(self, node: Any) -> Any:
        """Default: recurse into dataclass fields that are nodes or node lists."""
        for value in getattr(node, "__dict__", {}).values():
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, _NODE_TYPES):
                        self.visit(v)
            elif isinstance(value, _NODE_TYPES):
                self.visit(value)
        return None

    # --- file / arch ----------------------------------------------------
    def visit_File(self, node: A.File) -> Any:
        return [self.visit(d) for d in node.decls]

    def visit_Arch(self, node: A.Arch) -> Any:
        return [self.visit(s) for s in node.body]

    # --- declarations ---------------------------------------------------
    def visit_Wordsize(self, node: A.Wordsize) -> Any:
        return None

    def visit_Endianness(self, node: A.Endianness) -> Any:
        return None

    def visit_Alias(self, node: A.Alias) -> Any:
        return None

    def visit_RegisterDecl(self, node: A.RegisterDecl) -> Any:
        return None

    def visit_FormatDecl(self, node: A.FormatDecl) -> Any:
        return [self.visit(f) for f in node.fields]

    def visit_Field(self, node: A.Field) -> Any:
        return None

    def visit_ModeDecl(self, node: A.ModeDecl) -> Any:
        return None

    def visit_OpDecl(self, node: A.OpDecl) -> Any:
        return [self.visit(a) for a in node.attrs]

    # --- op attributes --------------------------------------------------
    def visit_SyntaxAttr(self, node: A.SyntaxAttr) -> Any:
        return None

    def visit_ImageAttr(self, node: A.ImageAttr) -> Any:
        return None

    def visit_ActionAttr(self, node: A.ActionAttr) -> Any:
        return [self.visit(s) for s in node.stmts]

    # --- statements -----------------------------------------------------
    def visit_Assignment(self, node: A.Assignment) -> Any:
        self.visit(node.lhs)
        return self.visit(node.rhs)

    def visit_Call(self, node: A.Call) -> Any:
        return [self.visit(a) for a in node.args]

    def visit_LValue(self, node: A.LValue) -> Any:
        return None

    # --- expressions ----------------------------------------------------
    def visit_IntLit(self, node: A.IntLit) -> Any:
        return None

    def visit_IdentRef(self, node: A.IdentRef) -> Any:
        return None

    def visit_IndexRef(self, node: A.IndexRef) -> Any:
        return None

    def visit_BinOp(self, node: A.BinOp) -> Any:
        self.visit(node.left)
        return self.visit(node.right)
