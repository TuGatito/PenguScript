"""Lark CST to PenguScript AST transformer."""

from __future__ import annotations

import ast
from typing import Any

from lark import Token, Transformer, v_args

from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Block,
    BoolLit,
    Break,
    Call,
    Cast,
    CompoundAssign,
    ConstDecl,
    ConstructorCall,
    ConstructorDecl,
    Continue,
    DerefTarget,
    DestructorDecl,
    EchoDecl,
    EllipsisLit,
    ElseIfClause,
    EnchantingDecl,
    EnumVariant,
    Expression,
    ExprStmt,
    ExprTarget,
    FieldAccess,
    FloatLit,
    FnType,
    ForClause,
    ForIter,
    ForNumeric,
    FunctionLiteral,
    HexLit,
    Ident,
    If,
    IfBlockExpr,
    IfInline,
    ImportSymbol,
    Index,
    IntLit,
    InvokeDecl,
    ListComp,
    ListLit,
    LiteralType,
    MapEntry,
    MapLit,
    MethodCall,
    MethodDecl,
    Module,
    NamedType,
    Node,
    NoneLit,
    NullptrLit,
    OmenDecl,
    OmenVariant,
    OperatorDecl,
    Parameter,
    Paren,
    ParentCall,
    Pass,
    Range,
    RealmAccess,
    RealmDecl,
    Repeat,
    RuneDecl,
    RuneField,
    SealDecl,
    SelfField,
    SelfFieldTarget,
    SelfMethodCall,
    SelfRef,
    SetLit,
    SigilConstraint,
    SigilParam,
    Statement,
    StringInterp,
    StringLit,
    Target,
    TupleLiteral,
    TypeExpr,
    TypeStaticAccess,
    Unary,
    Unless,
    UnsafeBlock,
    Until,
    VarTarget,
    While,
)
from penguscript.frontend.span import Span


def _unquote_string(s: str) -> str:
    """Safely decode and unquote string token."""
    try:
        val = ast.literal_eval(s)
        if isinstance(val, str):
            return val
        return str(val)
    except Exception:
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s


def _to_target(node: Node) -> Target:
    """Convert expression or target node to Target."""
    if isinstance(node, Target):
        return node
    if isinstance(node, Ident):
        return VarTarget(name=node.name, span=node.span)
    if isinstance(node, SelfField):
        return SelfFieldTarget(name=node.name, span=node.span)
    if isinstance(node, Expression):
        return ExprTarget(expr=node, span=node.span)
    raise TypeError(f"Invalid target: {node}")


@v_args(inline=True, meta=True)
class PenguTransformer(Transformer[Any, Node]):
    """Transforms Lark parse tree into PenguScript AST dataclasses."""

    # --- Module and Blocks ---

    def module(self, meta: Any, *children: Any) -> Module:
        """Module root."""
        decls: list[Node] = []
        for child in children:
            if isinstance(child, (Statement, Expression, Node)):
                decls.append(child)
        return Module(declarations=decls, span=Span.from_meta(meta))

    def block(self, meta: Any, *children: Any) -> Block:
        """Indented block of statements."""
        stmts: list[Statement] = []
        for child in children:
            if isinstance(child, Statement):
                stmts.append(child)
            elif isinstance(child, Expression):
                stmts.append(ExprStmt(expr=child, span=child.span))
        return Block(statements=stmts, span=Span.from_meta(meta))

    # --- Top-Level Declarations (Phase 4) ---

    def realm_decl(self, meta: Any, realm_tok: Token, name_tok: Token) -> RealmDecl:
        return RealmDecl(name=str(name_tok.value), span=Span.from_meta(meta))

    def import_symbol(self, meta: Any, *children: Any) -> ImportSymbol:
        name = str(children[0].value)
        alias: str | None = None
        if len(children) >= 3 and getattr(children[1], "type", None) == "AS":
            alias = str(children[2].value)
        return ImportSymbol(name=name, alias=alias, span=Span.from_meta(meta))

    def invoke_module(self, meta: Any, *children: Any) -> InvokeDecl:
        path_tok = next(c for c in children if isinstance(c, Token) and c.type == "STRING")
        path = _unquote_string(str(path_tok.value))
        alias: str | None = None
        as_idx = next(
            (i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "AS"),
            None,
        )
        if as_idx is not None and as_idx + 1 < len(children):
            alias = str(children[as_idx + 1].value)
        return InvokeDecl(path=path, alias=alias, symbols=[], span=Span.from_meta(meta))

    def invoke_selective(self, meta: Any, *children: Any) -> InvokeDecl:
        symbols: list[ImportSymbol] = [c for c in children if isinstance(c, ImportSymbol)]
        path_tok = next(c for c in children if isinstance(c, Token) and c.type == "STRING")
        path = _unquote_string(str(path_tok.value))
        return InvokeDecl(path=path, alias=None, symbols=symbols, span=Span.from_meta(meta))

    def const_decl(self, meta: Any, *children: Any) -> ConstDecl:
        name = str(children[1].value)
        type_ann = next((c for c in children if isinstance(c, TypeExpr)), None)
        value = next(c for c in children if isinstance(c, Expression))
        return ConstDecl(
            name=name,
            value=value,
            type_annotation=type_ann,
            span=Span.from_meta(meta),
        )

    def echo_decl(self, meta: Any, *children: Any) -> EchoDecl:
        name = str(children[1].value)
        sigils: list[SigilParam] = []
        for c in children:
            if isinstance(c, list) and c and isinstance(c[0], SigilParam):
                sigils = c
                break
        type_params: list[str] = [s.name for s in sigils]
        assign_idx = next(
            i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "ASSIGN"
        )
        if not type_params:
            for c in children[2:assign_idx]:
                if isinstance(c, Token) and c.type == "TYPE_IDENT":
                    type_params.append(str(c.value))
        target_type = next(c for c in children[assign_idx + 1 :] if isinstance(c, TypeExpr))
        return EchoDecl(
            name=name,
            type_params=type_params,
            sigils=sigils,
            target_type=target_type,
            span=Span.from_meta(meta),
        )

    def seal_decl(self, meta: Any, *children: Any) -> SealDecl:
        name = str(children[1].value)
        sigils: list[SigilParam] = []
        for c in children:
            if isinstance(c, list) and c and isinstance(c[0], SigilParam):
                sigils = c
                break
        type_params: list[str] = [s.name for s in sigils]
        assign_idx = next(
            i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "ASSIGN"
        )
        if not type_params:
            for c in children[2:assign_idx]:
                if isinstance(c, Token) and c.type == "TYPE_IDENT":
                    type_params.append(str(c.value))
        target_type = next(c for c in children[assign_idx + 1 :] if isinstance(c, TypeExpr))
        return SealDecl(
            name=name,
            type_params=type_params,
            sigils=sigils,
            target_type=target_type,
            span=Span.from_meta(meta),
        )

    def omen_variant(self, meta: Any, *children: Any) -> OmenVariant:
        name_tok = children[0]
        name = str(name_tok.value)
        expr = next((c for c in children[1:] if isinstance(c, Expression)), None)
        return OmenVariant(name=name, value=expr, span=Span.from_meta(meta))

    def omen_variants(self, meta: Any, *children: Any) -> list[OmenVariant]:
        return [c for c in children if isinstance(c, OmenVariant)]

    def omen_body(self, meta: Any, *children: Any) -> list[OmenVariant]:
        variants: list[OmenVariant] = []
        for c in children:
            if isinstance(c, list):
                variants.extend(c)
        return variants

    def omen_decl(self, meta: Any, *children: Any) -> OmenDecl:
        is_flags = any(isinstance(c, Token) and c.type == "FLAGS" for c in children)
        type_ident_tok = next(
            c for c in children if isinstance(c, Token) and c.type == "TYPE_IDENT"
        )
        name = str(type_ident_tok.value)
        underlying = next((c for c in children if isinstance(c, TypeExpr)), None)
        variants = next((c for c in children if isinstance(c, list)), [])
        return OmenDecl(
            name=name,
            variants=variants,
            underlying_type=underlying,
            is_flags=is_flags,
            span=Span.from_meta(meta),
        )

    def rune_field(self, meta: Any, *children: Any) -> RuneField:
        name = str(children[0].value)
        type_ann = next(c for c in children if isinstance(c, TypeExpr))
        def_val = next((c for c in children if isinstance(c, Expression)), None)
        return RuneField(
            name=name,
            type_annotation=type_ann,
            default_value=def_val,
            span=Span.from_meta(meta),
        )

    def constructor_decl(self, meta: Any, *children: Any) -> ConstructorDecl:
        params: list[Parameter] = [c for c in children if isinstance(c, Parameter)]
        body: Block = next(c for c in children if isinstance(c, Block))
        return ConstructorDecl(params=params, body=body, span=Span.from_meta(meta))

    def destructor_decl(self, meta: Any, *children: Any) -> DestructorDecl:
        body: Block = next(c for c in children if isinstance(c, Block))
        return DestructorDecl(body=body, span=Span.from_meta(meta))

    def rune_body(self, meta: Any, *children: Any) -> list[Node]:
        items: list[Node] = []
        for c in children:
            if isinstance(c, (RuneField, ConstructorDecl, DestructorDecl)):
                items.append(c)
        return items

    def rune_decl(self, meta: Any, *children: Any) -> RuneDecl:
        name = str(children[1].value)
        sigils: list[SigilParam] = []
        for c in children:
            if isinstance(c, list) and c and isinstance(c[0], SigilParam):
                sigils = c
                break
        type_params: list[str] = [s.name for s in sigils]
        heir_idx = next(
            (i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "HEIR"),
            None,
        )
        body_idx = next(
            i
            for i, c in enumerate(children)
            if isinstance(c, list) and (not c or not isinstance(c[0], SigilParam))
        )
        limit = heir_idx if heir_idx is not None else body_idx
        if not type_params:
            for c in children[2:limit]:
                if isinstance(c, Token) and c.type == "TYPE_IDENT":
                    type_params.append(str(c.value))
        parent: TypeExpr | None = None
        if heir_idx is not None:
            parent = next(c for c in children[heir_idx + 1 : body_idx] if isinstance(c, TypeExpr))
        body_items: list[Node] = children[body_idx]
        fields = [c for c in body_items if isinstance(c, RuneField)]
        constructor = next((c for c in body_items if isinstance(c, ConstructorDecl)), None)
        destructor = next((c for c in body_items if isinstance(c, DestructorDecl)), None)
        return RuneDecl(
            name=name,
            type_params=type_params,
            parent=parent,
            fields=fields,
            constructor=constructor,
            destructor=destructor,
            sigils=sigils,
            span=Span.from_meta(meta),
        )

    def method_decl(self, meta: Any, *children: Any) -> MethodDecl:
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        is_unsafe = any(isinstance(c, Token) and c.type == "UNSAFE" for c in children)
        ident_tok = next(c for c in children if isinstance(c, Token) and c.type == "IDENT")
        name = str(ident_tok.value)
        fn = next(c for c in children if isinstance(c, FunctionLiteral))
        return MethodDecl(
            name=name,
            function=fn,
            is_mut=is_mut,
            is_unsafe=is_unsafe,
            span=Span.from_meta(meta),
        )

    def op_index(self, meta: Any, *children: Any) -> str:
        return "[]"

    def op_call(self, meta: Any, *children: Any) -> str:
        return "()"

    def operator_decl(self, meta: Any, *children: Any) -> OperatorDecl:
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        is_unsafe = any(isinstance(c, Token) and c.type == "UNSAFE" for c in children)
        assign_idx = next(
            i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "ASSIGN"
        )
        op_part = children[assign_idx - 1]
        if isinstance(op_part, str):
            op_val = op_part
        elif isinstance(op_part, Token):
            op_val = str(op_part.value)
        elif hasattr(op_part, "children") and op_part.children:
            op_val = str(op_part.children[0].value)
        else:
            op_val = str(op_part)
        fn = next(c for c in children if isinstance(c, FunctionLiteral))
        return OperatorDecl(
            op=op_val,
            function=fn,
            is_mut=is_mut,
            is_unsafe=is_unsafe,
            span=Span.from_meta(meta),
        )

    def enchanting_body(
        self, meta: Any, *children: Any
    ) -> tuple[list[MethodDecl | OperatorDecl | ConstructorDecl | DestructorDecl], Block | None]:
        members: list[MethodDecl | OperatorDecl | ConstructorDecl | DestructorDecl] = [
            c
            for c in children
            if isinstance(c, (MethodDecl, OperatorDecl, ConstructorDecl, DestructorDecl))
        ]
        pass_item = next((c for c in children if isinstance(c, Pass)), None)
        body = Block(statements=[pass_item]) if pass_item else None
        return (members, body)

    def enchanting_decl(self, meta: Any, *children: Any) -> EnchantingDecl:
        target_type = next(c for c in children if isinstance(c, TypeExpr))
        members: list[MethodDecl | OperatorDecl | ConstructorDecl | DestructorDecl] = []
        body: Block | Statement | None = None
        for c in children:
            if isinstance(c, tuple):
                members = c[0]
                body = c[1]
            elif isinstance(c, list):
                members = c
            elif isinstance(c, (Block, Statement)):
                body = c
        return EnchantingDecl(
            target_type=target_type,
            members=members,
            body=body,
            span=Span.from_meta(meta),
        )

    # --- Literals ---

    def int_lit(self, meta: Any, tok: Token) -> IntLit:
        cleaned = str(tok.value).replace("_", "")
        return IntLit(value=int(cleaned), raw=str(tok.value), span=Span.from_meta(meta))

    def hex_lit(self, meta: Any, tok: Token) -> HexLit:
        cleaned = str(tok.value).replace("_", "")
        return HexLit(value=int(cleaned, 16), raw=str(tok.value), span=Span.from_meta(meta))

    def float_lit(self, meta: Any, tok: Token) -> FloatLit:
        cleaned = str(tok.value).replace("_", "")
        return FloatLit(value=float(cleaned), raw=str(tok.value), span=Span.from_meta(meta))

    def string_lit(self, meta: Any, tok: Token) -> StringLit | StringInterp:
        import re

        raw = str(tok.value)
        is_fstring = raw.startswith("f") or raw.startswith("F")
        content = raw[1:] if is_fstring else raw
        inner = content[1:-1]

        if is_fstring:
            pattern = re.compile(r"(#\{[^}]*\}|\{[^}]*\})")
        elif "#{" in inner:
            pattern = re.compile(r"(#\{[^}]*\})")
        else:
            return StringLit(value=_unquote_string(raw), span=Span.from_meta(meta))

        parts: list[str | Expression] = []
        last_end = 0
        from penguscript.frontend.parser import parse_expr

        for m in pattern.finditer(inner):
            start, end = m.span()
            if start > last_end:
                parts.append(inner[last_end:start])
            expr_str = m.group(0)
            if expr_str.startswith("#{") and expr_str.endswith("}"):
                code = expr_str[2:-1].strip()
            elif expr_str.startswith("{") and expr_str.endswith("}"):
                code = expr_str[1:-1].strip()
            else:
                code = expr_str
            parts.append(parse_expr(code))
            last_end = end

        if last_end < len(inner):
            parts.append(inner[last_end:])

        return StringInterp(parts=parts, span=Span.from_meta(meta))

    def bool_lit(self, meta: Any, tok: Token) -> BoolLit:
        return BoolLit(value=(str(tok.value) == "true"), span=Span.from_meta(meta))

    def none_lit(self, meta: Any, tok: Token) -> NoneLit:
        return NoneLit(span=Span.from_meta(meta))

    def nullptr_lit(self, meta: Any, tok: Token) -> NullptrLit:
        return NullptrLit(span=Span.from_meta(meta))

    # --- Identifiers and Accesses ---

    def type_call(self, meta: Any, *children: Any) -> ConstructorCall:
        name = str(children[0].value)
        type_args: list[TypeExpr] = []
        lpar_idx = next(
            i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "LPAR"
        )
        for c in children[1:lpar_idx]:
            if isinstance(c, TypeExpr):
                type_args.append(c)
        args: list[Expression] = [c for c in children[lpar_idx + 1 :] if isinstance(c, Expression)]
        target_type = NamedType(name=name, args=type_args, span=Span.from_meta(meta))
        return ConstructorCall(target_type=target_type, args=args, span=Span.from_meta(meta))

    def ident(self, meta: Any, tok: Token) -> Ident:
        return Ident(name=str(tok.value), span=Span.from_meta(meta))

    def ellipsis_lit(self, meta: Any, tok: Token) -> EllipsisLit:
        return EllipsisLit(span=Span.from_meta(meta))

    def enum_variant(
        self, meta: Any, enum_tok: Token, sep: Token, variant_tok: Token
    ) -> EnumVariant:
        return EnumVariant(
            enum_name=str(enum_tok.value),
            variant_name=str(variant_tok.value),
            span=Span.from_meta(meta),
        )

    def type_static_access(
        self, meta: Any, type_tok: Token, sep: Token, method_tok: Token
    ) -> TypeStaticAccess:
        return TypeStaticAccess(
            type_name=str(type_tok.value),
            method_name=str(method_tok.value),
            span=Span.from_meta(meta),
        )

    def realm_access(self, meta: Any, realm_tok: Token, sep: Token, name_tok: Token) -> RealmAccess:
        return RealmAccess(
            realm=str(realm_tok.value),
            name=str(name_tok.value),
            span=Span.from_meta(meta),
        )

    def self_ref(self, meta: Any, tok: Token) -> SelfRef:
        return SelfRef(span=Span.from_meta(meta))

    def self_field(self, meta: Any, at_tok: Token, name_tok: Token) -> SelfField:
        return SelfField(name=str(name_tok.value), span=Span.from_meta(meta))

    def self_method_call(self, meta: Any, *children: Any) -> SelfMethodCall:
        name = str(children[1].value)
        args: list[Expression] = [arg for arg in children[2:] if isinstance(arg, Expression)]
        return SelfMethodCall(name=name, args=args, span=Span.from_meta(meta))

    def paren_expr(self, meta: Any, *children: Any) -> Paren:
        expr = next(c for c in children if isinstance(c, Expression))
        return Paren(inner=expr, span=Span.from_meta(meta))

    # --- Unary operations ---

    def unary_deref(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="*", operand=expr, span=Span.from_meta(meta))

    def unary_neg(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="-", operand=expr, span=Span.from_meta(meta))

    def unary_bitnot(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="~", operand=expr, span=Span.from_meta(meta))

    def unary_len(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="#", operand=expr, span=Span.from_meta(meta))

    def unary_ref(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="&", operand=expr, span=Span.from_meta(meta))

    def unary_not(self, meta: Any, *children: Any) -> Unary:
        expr = next(c for c in children if isinstance(c, Expression))
        return Unary(op="not", operand=expr, span=Span.from_meta(meta))

    # --- Binary operations ---

    def _fold_binary(self, meta: Any, children: tuple[Any, ...]) -> Expression:
        if len(children) == 1:
            res: Expression = children[0]
            return res
        left: Expression = children[0]
        i = 1
        while i < len(children):
            op_node = children[i]
            op = str(op_node.value if hasattr(op_node, "value") else op_node)
            right_expr: Expression = children[i + 1]
            left = Binary(op=op, left=left, right=right_expr, span=Span.from_meta(meta))
            i += 2
        return left

    def or_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def and_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def bwor_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def bwxor_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def bwand_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def cmp_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def range_op(self, meta: Any, left: Expression, op_tok: Token, right: Expression) -> Range:
        op = str(op_tok.value)
        return Range(start=left, end=right, inclusive=(op == ".."), span=Span.from_meta(meta))

    def shift_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def add_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def mul_expr(self, meta: Any, *children: Any) -> Expression:
        return self._fold_binary(meta, children)

    def cast_op(self, meta: Any, *children: Any) -> Cast:
        expr: Expression = children[0]
        target_type: TypeExpr = children[-1]
        return Cast(expr=expr, target_type=target_type, span=Span.from_meta(meta))

    # --- Postfix operations ---

    def call(self, meta: Any, *children: Any) -> tuple[str, list[Expression], Span | None]:
        args: list[Expression] = [c for c in children if isinstance(c, Expression)]
        return ("call", args, Span.from_meta(meta))

    def generic_call(
        self, meta: Any, *children: Any
    ) -> tuple[str, list[TypeExpr], list[Expression], Span | None]:
        type_args: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        args: list[Expression] = [c for c in children if isinstance(c, Expression)]
        return ("generic_call", type_args, args, Span.from_meta(meta))

    def generic_comp(
        self, meta: Any, *children: Any
    ) -> tuple[str, list[TypeExpr], Expression, list[ForClause], Span | None]:
        type_args: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        element = next(c for c in children if isinstance(c, Expression))
        clauses = [c for c in children if isinstance(c, ForClause)]
        return ("generic_comp", type_args, element, clauses, Span.from_meta(meta))

    def generic_list_lit(
        self, meta: Any, *children: Any
    ) -> tuple[str, list[TypeExpr], list[Expression], Span | None]:
        type_args: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        elements = [c for c in children if isinstance(c, Expression)]
        return ("generic_list_lit", type_args, elements, Span.from_meta(meta))

    def generic_map_lit(
        self, meta: Any, *children: Any
    ) -> tuple[str, list[TypeExpr], list[MapEntry], Span | None]:
        type_args: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        entries = [c for c in children if isinstance(c, MapEntry)]
        return ("generic_map_lit", type_args, entries, Span.from_meta(meta))

    def call_no_args(self, meta: Any, *children: Any) -> tuple[str, list[Expression], Span | None]:
        return ("call", [], Span.from_meta(meta))

    def index(self, meta: Any, *children: Any) -> tuple[str, list[Expression], Span | None]:
        indices: list[Expression] = [c for c in children if isinstance(c, Expression)]
        return ("index", indices, Span.from_meta(meta))

    def field_access(
        self, meta: Any, dot_tok: Token, name_tok: Token
    ) -> tuple[str, str, Span | None]:
        return ("field_access", str(name_tok.value), Span.from_meta(meta))

    def method_call(
        self, meta: Any, *children: Any
    ) -> tuple[str, str, list[Expression], Span | None]:
        name = str(children[1].value)
        args: list[Expression] = [c for c in children[2:] if isinstance(c, Expression)]
        return ("method_call", name, args, Span.from_meta(meta))

    def method_call_no_args(
        self, meta: Any, *children: Any
    ) -> tuple[str, str, list[Expression], Span | None]:
        name = str(children[1].value)
        return ("method_call", name, [], Span.from_meta(meta))

    def postfix_expr(self, meta: Any, *children: Any) -> Expression:
        res: Expression = children[0]
        for op in children[1:]:
            kind = op[0]
            if kind == "call":
                res = Call(callee=res, args=op[1], span=op[2])
            elif kind == "generic_call":
                if isinstance(res, FieldAccess):
                    res = MethodCall(
                        target=res.target,
                        method_name=res.field_name,
                        args=op[2],
                        type_args=op[1],
                        span=op[3],
                    )
                else:
                    res = Call(callee=res, args=op[2], type_args=op[1], span=op[3])
            elif kind == "generic_list_lit":
                type_name = res.name if isinstance(res, Ident) else str(res)
                target_type = NamedType(name=type_name, args=op[1], span=res.span)
                res = ListLit(elements=op[2], type_prefix=target_type, span=Span.from_meta(meta))
            elif kind == "generic_comp":
                type_name = res.name if isinstance(res, Ident) else str(res)
                target_type = NamedType(name=type_name, args=op[1], span=res.span)
                res = ListComp(
                    element=op[2],
                    for_clauses=op[3],
                    type_prefix=target_type,
                    span=Span.from_meta(meta),
                )
            elif kind == "generic_map_lit":
                type_name = res.name if isinstance(res, Ident) else str(res)
                target_type = NamedType(name=type_name, args=op[1], span=res.span)
                res = MapLit(entries=op[2], type_prefix=target_type, span=Span.from_meta(meta))
            elif kind == "index":
                res = Index(target=res, indices=op[1], span=op[2])
            elif kind == "field_access":
                res = FieldAccess(target=res, field_name=op[1], span=op[2])
            elif kind == "method_call":
                res = MethodCall(target=res, method_name=op[1], args=op[2], span=op[3])
        return res

    # --- Collections ---

    def tuple_literal(self, meta: Any, *children: Any) -> TupleLiteral:
        elements: list[Expression] = [c for c in children if isinstance(c, Expression)]
        return TupleLiteral(elements=elements, span=Span.from_meta(meta))

    def list_literal(self, meta: Any, *children: Any) -> ListLit:
        type_prefix: TypeExpr | None = None
        elements: list[Expression] = []
        for c in children:
            if isinstance(c, TypeExpr):
                type_prefix = c
            elif isinstance(c, Expression):
                elements.append(c)
        return ListLit(elements=elements, type_prefix=type_prefix, span=Span.from_meta(meta))

    def list_comp(self, meta: Any, *children: Any) -> ListComp:
        type_prefix: NamedType | None = next(
            (c for c in children if isinstance(c, NamedType)), None
        )
        element = next(
            c for c in children if isinstance(c, Expression) and not isinstance(c, ListComp)
        )
        clauses = [c for c in children if isinstance(c, ForClause)]
        return ListComp(
            element=element,
            for_clauses=clauses,
            type_prefix=type_prefix,
            span=Span.from_meta(meta),
        )

    def comp_for_iter(self, meta: Any, *children: Any) -> ForClause:
        binding = children[0]
        idx_var, target_name, is_mut = binding
        iterable = next(c for c in children[1:] if isinstance(c, Expression))
        return ForClause(
            target=target_name,
            iterable=iterable,
            index_var=idx_var,
            is_mut=is_mut,
            span=Span.from_meta(meta),
        )

    def comp_for_numeric(self, meta: Any, *children: Any) -> ForClause:
        ident_tok = children[0]
        var_name = str(ident_tok.value)
        var_type = next((c for c in children[1:] if isinstance(c, TypeExpr)), None)
        exprs = [c for c in children[1:] if isinstance(c, Expression)]
        start_expr = exprs[0]
        end_expr = exprs[1]
        step_expr = exprs[2] if len(exprs) > 2 else None
        return ForClause(
            target=var_name,
            start=start_expr,
            end=end_expr,
            step=step_expr,
            var_type=var_type,
            span=Span.from_meta(meta),
        )

    def comp_if(self, meta: Any, *children: Any) -> Expression:
        return next(c for c in children if isinstance(c, Expression))

    def comp_for(self, meta: Any, *children: Any) -> ForClause:
        clause = next(c for c in children if isinstance(c, ForClause))
        cond = next((c for c in children if isinstance(c, Expression)), None)
        if cond is not None:
            return ForClause(
                target=clause.target,
                iterable=clause.iterable,
                index_var=clause.index_var,
                is_mut=clause.is_mut,
                start=clause.start,
                end=clause.end,
                step=clause.step,
                var_type=clause.var_type,
                condition=cond,
                span=Span.from_meta(meta),
            )
        return clause

    def map_entry(self, meta: Any, key: Expression, colon_tok: Token, val: Expression) -> MapEntry:
        return MapEntry(key=key, value=val, span=Span.from_meta(meta))

    def map_literal(self, meta: Any, *children: Any) -> MapLit:
        type_prefix: TypeExpr | None = None
        entries: list[MapEntry] = []
        for c in children:
            if isinstance(c, TypeExpr):
                type_prefix = c
            elif isinstance(c, MapEntry):
                entries.append(c)
        return MapLit(entries=entries, type_prefix=type_prefix, span=Span.from_meta(meta))

    def set_literal(self, meta: Any, *children: Any) -> SetLit:
        raw_prefix = str(children[0].value).strip()
        prefix = "unordered_set" if "unordered_set" in raw_prefix else "set"
        elements: list[Expression] = [c for c in children[1:] if isinstance(c, Expression)]
        return SetLit(elements=elements, prefix=prefix, span=Span.from_meta(meta))

    # --- Types & Sigils ---

    def literal_type(self, meta: Any, *children: Any) -> LiteralType:
        raw_val = str(children[0].value)
        val: int | str = int(raw_val) if raw_val.isdigit() else raw_val
        return LiteralType(value=val, span=Span.from_meta(meta))

    def sigil_constraint(self, meta: Any, *children: Any) -> SigilConstraint:
        name = str(children[0].value)
        args: list[TypeExpr] = [c for c in children[1:] if isinstance(c, TypeExpr)]
        return SigilConstraint(name=name, args=args, span=Span.from_meta(meta))

    def sigil_param(self, meta: Any, *children: Any) -> SigilParam:
        name = str(children[0].value)
        constraints: list[SigilConstraint] = [
            c for c in children[1:] if isinstance(c, SigilConstraint)
        ]
        return SigilParam(name=name, constraints=constraints, span=Span.from_meta(meta))

    def sigil_params(self, meta: Any, *children: Any) -> list[SigilParam]:
        return [c for c in children if isinstance(c, SigilParam)]

    def type_prefix(self, meta: Any, *children: Any) -> NamedType:
        name = str(children[0].value)
        args: list[TypeExpr] = [c for c in children[1:] if isinstance(c, TypeExpr)]
        return NamedType(name=name, args=args, span=Span.from_meta(meta))

    def named_type(self, meta: Any, *children: Any) -> NamedType:
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        name_token = next(
            c for c in children if isinstance(c, Token) and c.type in ("TYPE_IDENT", "IDENT")
        )
        name = str(name_token.value)
        args: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        is_opt = any(getattr(c, "type", None) == "QUESTION" for c in children)
        return NamedType(
            name=name,
            args=args,
            is_optional=is_opt,
            is_mut=is_mut,
            span=Span.from_meta(meta),
        )

    def type_expr(self, meta: Any, *children: Any) -> TypeExpr:
        if len(children) == 1 and isinstance(children[0], TypeExpr):
            return children[0]
        return self.named_type(meta, *children)

    def fn_type(self, meta: Any, *children: Any) -> FnType:
        types: list[TypeExpr] = [c for c in children if isinstance(c, TypeExpr)]
        param_types = types[:-1]
        return_type = types[-1]
        return FnType(param_types=param_types, return_type=return_type, span=Span.from_meta(meta))

    # --- Control Flow ---

    def if_stmt(self, meta: Any, *children: Any) -> If:
        cond: Expression = children[1]
        then_block: Block = children[2]
        else_if_clauses: list[ElseIfClause] = []
        else_block: Block | None = None

        idx = 3
        while idx < len(children):
            c = children[idx]
            if isinstance(c, Token) and c.type == "ELSE":
                next_c = children[idx + 1] if idx + 1 < len(children) else None
                if isinstance(next_c, Token) and next_c.type == "IF":
                    # else if cond block
                    ei_cond = children[idx + 2]
                    ei_block = children[idx + 3]
                    else_if_clauses.append(ElseIfClause(condition=ei_cond, body=ei_block))
                    idx += 4
                elif isinstance(next_c, Block):
                    else_block = next_c
                    idx += 2
                else:
                    idx += 1
            else:
                idx += 1

        return If(
            condition=cond,
            then_block=then_block,
            else_if_clauses=else_if_clauses,
            else_block=else_block,
            span=Span.from_meta(meta),
        )

    def if_inline(self, meta: Any, *children: Any) -> IfInline:
        exprs = [c for c in children if isinstance(c, Expression)]
        res = exprs[-1]
        i = len(exprs) - 3
        while i >= 0:
            cond = exprs[i]
            then_expr = exprs[i + 1]
            res = IfInline(
                condition=cond,
                then_expr=then_expr,
                else_expr=res,
                span=Span.from_meta(meta),
            )
            i -= 2
        assert isinstance(res, IfInline)
        return res

    def if_block_expr(self, meta: Any, *children: Any) -> IfBlockExpr:
        cond = next(c for c in children if isinstance(c, Expression))
        blocks = [c for c in children if isinstance(c, Block)]
        main_body = blocks[0]
        else_block = blocks[-1] if len(blocks) > 1 else None

        else_if_clauses: list[ElseIfClause] = []
        i = 1
        while i < len(children) - 1:
            if (
                isinstance(children[i], Token)
                and children[i].type == "ELSE"
                and i + 1 < len(children)
                and isinstance(children[i + 1], Token)
                and children[i + 1].type == "IF"
            ):
                clause_cond = next(c for c in children[i + 2 :] if isinstance(c, Expression))
                clause_block = next(c for c in children[i + 2 :] if isinstance(c, Block))
                else_if_clauses.append(ElseIfClause(condition=clause_cond, body=clause_block))
            i += 1

        return IfBlockExpr(
            condition=cond,
            body=main_body,
            else_if_clauses=else_if_clauses,
            else_block=else_block,
            span=Span.from_meta(meta),
        )

    def unless_stmt(self, meta: Any, *children: Any) -> Unless:
        cond = children[1]
        body = children[2]
        else_block = next((c for c in children[3:] if isinstance(c, Block)), None)
        return Unless(condition=cond, body=body, else_block=else_block, span=Span.from_meta(meta))

    def while_stmt(self, meta: Any, *children: Any) -> While:
        cond = children[1]
        body = children[2]
        else_block = next((c for c in children[3:] if isinstance(c, Block)), None)
        return While(condition=cond, body=body, else_block=else_block, span=Span.from_meta(meta))

    def until_stmt(self, meta: Any, *children: Any) -> Until:
        cond = children[1]
        body = children[2]
        else_block = next((c for c in children[3:] if isinstance(c, Block)), None)
        return Until(condition=cond, body=body, else_block=else_block, span=Span.from_meta(meta))

    def repeat_stmt(self, meta: Any, *children: Any) -> Repeat:
        body = children[1]
        until_idx = next(
            i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "UNTIL"
        )
        cond = children[until_idx + 1]
        else_block = next((c for c in children[until_idx + 2 :] if isinstance(c, Block)), None)
        return Repeat(body=body, condition=cond, else_block=else_block, span=Span.from_meta(meta))

    def for_numeric(self, meta: Any, *children: Any) -> ForNumeric:
        var_name = str(children[1].value)
        type_ann: TypeExpr | None = None
        exprs: list[Expression] = []
        body: Block | None = None
        else_block: Block | None = None

        for c in children[2:]:
            if isinstance(c, TypeExpr):
                type_ann = c
            elif isinstance(c, Expression):
                exprs.append(c)
            elif isinstance(c, Block):
                if body is None:
                    body = c
                else:
                    else_block = c

        assert body is not None, "Missing body in for loop"
        start_expr = exprs[0]
        end_expr = exprs[1]
        step_expr = exprs[2] if len(exprs) > 2 else None

        return ForNumeric(
            var_name=var_name,
            start=start_expr,
            end=end_expr,
            step=step_expr,
            var_type=type_ann,
            body=body,
            else_block=else_block,
            span=Span.from_meta(meta),
        )

    def for_iter_index_val(self, meta: Any, *children: Any) -> tuple[str, str, bool]:
        index_var = str(children[0].value)
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        val_var = str(children[-1].value)
        return (index_var, val_var, is_mut)

    def for_iter_val(self, meta: Any, *children: Any) -> tuple[None, str, bool]:
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        val_var = str(children[-1].value)
        return (None, val_var, is_mut)

    def for_iter(self, meta: Any, *children: Any) -> ForIter:
        bindings = children[1]
        index_var, target, is_mut = bindings
        iterable = children[3]
        blocks = [c for c in children[4:] if isinstance(c, Block)]
        body = blocks[0]
        else_block = blocks[1] if len(blocks) > 1 else None

        return ForIter(
            target=target,
            iterable=iterable,
            body=body,
            index_var=index_var,
            is_mut=is_mut,
            else_block=else_block,
            span=Span.from_meta(meta),
        )

    def break_stmt(self, meta: Any, *children: Any) -> Break:
        val = next((c for c in children if isinstance(c, Expression)), None)
        return Break(value=val, span=Span.from_meta(meta))

    def continue_stmt(self, meta: Any, *children: Any) -> Continue:
        return Continue(span=Span.from_meta(meta))

    def pass_stmt(self, meta: Any, *children: Any) -> Pass:
        return Pass(span=Span.from_meta(meta))

    def unsafe_block(self, meta: Any, *children: Any) -> UnsafeBlock:
        body = next(c for c in children if isinstance(c, Block))
        return UnsafeBlock(body=body, span=Span.from_meta(meta))

    def parent_stmt(self, meta: Any, *children: Any) -> ParentCall:
        args: list[Expression] = [c for c in children if isinstance(c, Expression)]
        return ParentCall(args=args, span=Span.from_meta(meta))

    # --- Functions ---

    def param(self, meta: Any, *children: Any) -> Parameter:
        is_mut = any(isinstance(c, Token) and c.type == "MUT" for c in children)
        ident_tok = next(c for c in children if isinstance(c, Token) and c.type == "IDENT")
        name = str(ident_tok.value)
        type_ann = next((c for c in children if isinstance(c, TypeExpr)), None)
        def_val = next((c for c in children if isinstance(c, Expression)), None)
        return Parameter(
            name=name,
            type_annotation=type_ann,
            default_value=def_val,
            is_mut=is_mut,
            span=Span.from_meta(meta),
        )

    PRIMITIVE_TYPES: set[str] = {
        "void",
        "int",
        "float",
        "double",
        "bool",
        "string",
        "char",
        "byte",
        "size_t",
        "int8_t",
        "int16_t",
        "int32_t",
        "int64_t",
        "uint8_t",
        "uint16_t",
        "uint32_t",
        "uint64_t",
    }

    def fn_block(self, meta: Any, *children: Any) -> FunctionLiteral:
        sigils: list[SigilParam] = []
        for c in children:
            if isinstance(c, list) and c and isinstance(c[0], SigilParam):
                sigils = c
                break
            if isinstance(c, SigilParam):
                sigils.append(c)
        params: list[Parameter] = [c for c in children if isinstance(c, Parameter)]
        ret_type: TypeExpr = next(c for c in children if isinstance(c, TypeExpr))
        block: Block = next(c for c in children if isinstance(c, Block))
        return FunctionLiteral(
            params=params,
            return_type=ret_type,
            body=block,
            sigils=sigils,
            span=Span.from_meta(meta),
        )

    def fn_inline(self, meta: Any, *children: Any) -> FunctionLiteral:
        sigils: list[SigilParam] = []
        for c in children:
            if isinstance(c, list) and c and isinstance(c[0], SigilParam):
                sigils = c
                break
            if isinstance(c, SigilParam):
                sigils.append(c)
        params: list[Parameter] = [c for c in children if isinstance(c, Parameter)]
        expr: Expression = next(c for c in children if isinstance(c, Expression))
        if isinstance(expr, Ident) and expr.name in self.PRIMITIVE_TYPES:
            return FunctionLiteral(
                params=params,
                return_type=NamedType(name=expr.name, span=expr.span),
                body=None,
                sigils=sigils,
                span=Span.from_meta(meta),
            )
        return FunctionLiteral(
            params=params,
            return_type=None,
            body=expr,
            sigils=sigils,
            span=Span.from_meta(meta),
        )

    # --- Statements & Assignments ---

    def deref_target(self, meta: Any, *children: Any) -> DerefTarget:
        inner = next(c for c in children if isinstance(c, (Target, Expression)))
        target = _to_target(inner) if isinstance(inner, Expression) else inner
        return DerefTarget(target=target, span=Span.from_meta(meta))

    def assign(self, meta: Any, *children: Any) -> Assign:
        is_mut = False
        is_static = False
        is_unsafe = False
        targets: list[Target] = []
        type_ann: TypeExpr | None = None
        value: Expression | None = None

        idx = 0
        while idx < len(children):
            c = children[idx]
            if isinstance(c, Token) and c.type == "MUT":
                is_mut = True
                idx += 1
            elif isinstance(c, Token) and c.type == "STATIC":
                is_static = True
                idx += 1
            elif isinstance(c, Token) and c.type == "UNSAFE":
                is_unsafe = True
                idx += 1
            else:
                break

        assign_idx = next(
            (i for i, c in enumerate(children) if isinstance(c, Token) and c.type == "ASSIGN"),
            None,
        )

        if assign_idx is not None:
            for c in children[idx:assign_idx]:
                if isinstance(c, TypeExpr):
                    type_ann = c
                elif isinstance(c, Target):
                    targets.append(c)
                elif isinstance(c, Expression):
                    targets.append(_to_target(c))
            rhs_exprs = [c for c in children[assign_idx + 1 :] if isinstance(c, Expression)]
            if len(rhs_exprs) == 1:
                value = rhs_exprs[0]
            elif len(rhs_exprs) > 1:
                value = TupleLiteral(elements=rhs_exprs, span=Span.from_meta(meta))
        else:
            for c in children[idx:]:
                if isinstance(c, TypeExpr):
                    type_ann = c
                elif isinstance(c, Expression):
                    targets.append(_to_target(c))
                elif isinstance(c, Target):
                    targets.append(c)

            if targets:
                last = targets.pop()
                if isinstance(last, ExprTarget):
                    value = last.expr
                elif isinstance(last, VarTarget):
                    value = Ident(name=last.name, span=last.span)
                elif isinstance(last, SelfFieldTarget):
                    value = SelfField(name=last.name, span=last.span)

        assert value is not None, "Assignment missing value"
        return Assign(
            targets=targets,
            value=value,
            type_annotation=type_ann,
            is_mut=is_mut,
            is_static=is_static,
            is_unsafe=is_unsafe,
            span=Span.from_meta(meta),
        )

    def compound_assign(self, meta: Any, *children: Any) -> CompoundAssign:
        target = _to_target(children[0])
        op_child = children[1]
        if hasattr(op_child, "value"):
            op = str(op_child.value)
        elif hasattr(op_child, "children") and op_child.children:
            op = str(op_child.children[0].value)
        else:
            op = str(op_child)
        value = children[2]
        return CompoundAssign(target=target, op=op, value=value, span=Span.from_meta(meta))

    def expr_stmt(self, meta: Any, expr: Expression) -> ExprStmt:
        return ExprStmt(expr=expr, span=Span.from_meta(meta))
