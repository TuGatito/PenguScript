"""Pass 2: Lexical scope resolution and symbol reference binding."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from penguscript.analysis.diagnostics import Diagnostic, Label
from penguscript.analysis.prelude import get_prelude_symbols
from penguscript.analysis.suggestions import find_best_matches
from penguscript.analysis.symbols import (
    AnnotatedModule,
    NodeId,
    RealmSymbolTable,
    Scope,
    ScopeKind,
    Symbol,
    SymbolId,
    SymbolKind,
)
from penguscript.analysis.visitor import ASTVisitor
from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Block,
    Break,
    Call,
    Cast,
    CompoundAssign,
    ConstDecl,
    ConstructorCall,
    ConstructorDecl,
    Continue,
    DestructorDecl,
    EchoDecl,
    ElseIfClause,
    EnchantingDecl,
    EnumVariant,
    ExprStmt,
    ExprTarget,
    FieldAccess,
    ForIter,
    ForNumeric,
    FunctionDecl,
    FunctionLiteral,
    Ident,
    If,
    IfBlockExpr,
    IfInline,
    Index,
    ListComp,
    ListLit,
    MapLit,
    MethodCall,
    MethodDecl,
    Module,
    NamedType,
    Node,
    OperatorDecl,
    ParentCall,
    Range,
    RealmAccess,
    Repeat,
    RuneDecl,
    SealDecl,
    SelfField,
    SelfFieldTarget,
    SelfMethodCall,
    SelfRef,
    SetLit,
    StringInterp,
    TupleLiteral,
    TypeStaticAccess,
    Unary,
    Unless,
    UnsafeBlock,
    Until,
    VarTarget,
    While,
)
from penguscript.frontend.span import Span

_EMPTY_SPAN = Span(0, 0, 1, 1)


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """Outcome of resolving references for a module."""

    references: dict[NodeId, Symbol]
    symbols_to_refs: dict[SymbolId, list[NodeId]]
    diagnostics: list[Diagnostic]
    mutated_symbols: frozenset[SymbolId] = frozenset()


class Resolver(ASTVisitor):
    """Pass 2 Visitor: manages scope stacks, resolves symbols, and binds references."""

    def __init__(
        self,
        module_path: Path,
        annotated_module: AnnotatedModule,
        realms: dict[str, RealmSymbolTable],
        rune_declarations: dict[str, RuneDecl] | None = None,
        echo_declarations: dict[str, EchoDecl] | None = None,
        prelude: dict[str, Symbol] | None = None,
    ) -> None:
        self.module_path = module_path
        self.annotated_module = annotated_module
        self.current_realm = annotated_module.declared_realm
        self.realms = realms
        self.rune_declarations = rune_declarations if rune_declarations is not None else {}
        self.echo_declarations = echo_declarations if echo_declarations is not None else {}
        self.prelude = prelude if prelude is not None else get_prelude_symbols()

        self.references: dict[NodeId, Symbol] = {}
        self.symbols_to_refs: dict[SymbolId, list[NodeId]] = {}
        self.mutated_symbols: set[SymbolId] = set()
        self.diagnostics: list[Diagnostic] = []

        # Scope stack: Prelude -> Module -> ...
        self.scope_stack: list[Scope] = []
        self._init_scopes()

        # Stack of future local declarations per block for E2315
        self.block_future_locals: list[dict[str, Span]] = []

    def _init_scopes(self) -> None:
        prelude_scope = Scope(kind=ScopeKind.PRELUDE)
        for sym in self.prelude.values():
            prelude_scope.define(sym)

        module_scope = Scope(kind=ScopeKind.MODULE, parent=prelude_scope)

        # 1. Own realm symbols
        realm_table = self.realms.get(self.current_realm)
        if realm_table is not None:
            for sym in realm_table.symbols.values():
                module_scope.define(sym)

        # 2. Visible symbols from selective imports
        for sym in self.annotated_module.visible_symbols.values():
            module_scope.define(sym)

        self.scope_stack = [prelude_scope, module_scope]

    # --- Scope Management Helpers ---

    @property
    def current_scope(self) -> Scope:
        return self.scope_stack[-1]

    def push_scope(self, scope: Scope) -> None:
        self.scope_stack.append(scope)

    def pop_scope(self) -> Scope:
        return self.scope_stack.pop()

    @property
    def in_loop(self) -> bool:
        return any(s.in_loop for s in reversed(self.scope_stack))

    @property
    def in_constructor(self) -> bool:
        return any(s.in_constructor for s in reversed(self.scope_stack))

    @property
    def current_rune(self) -> str | None:
        for s in reversed(self.scope_stack):
            if s.enclosing_rune is not None:
                return s.enclosing_rune
        return None

    def record_reference(self, node: Node, symbol: Symbol) -> None:
        span = node.span or _EMPTY_SPAN
        node_id = NodeId(self.module_path, span)
        self.references[node_id] = symbol
        self.symbols_to_refs.setdefault(symbol.id, []).append(node_id)

    def _all_visible_names(self) -> Iterable[str]:
        names: set[str] = set()
        for scope in self.scope_stack:
            names.update(scope.symbols.keys())
        return names

    def _all_type_names(self) -> Iterable[str]:
        types: set[str] = set()
        for name, sym in self.prelude.items():
            if sym.kind == SymbolKind.BUILTIN_TYPE:
                types.add(name)
        realm_tbl = self.realms.get(self.current_realm)
        if realm_tbl is not None:
            for name, sym in realm_tbl.symbols.items():
                if sym.kind in (SymbolKind.RUNE, SymbolKind.OMEN, SymbolKind.ECHO, SymbolKind.SEAL):
                    types.add(name)
        for name, sym in self.annotated_module.visible_symbols.items():
            if sym.kind in (SymbolKind.RUNE, SymbolKind.OMEN, SymbolKind.ECHO, SymbolKind.SEAL):
                types.add(name)
        return types

    def _find_rune_field(self, rune_name: str, field_name: str) -> Symbol | None:
        # 1. Search in current realm's rune_fields
        table = self.realms.get(self.current_realm)
        if table is not None and rune_name in table.rune_fields:
            fields = table.rune_fields[rune_name]
            if field_name in fields:
                return fields[field_name]

        # 2. Search in visible symbols (if rune is imported)
        if rune_name in self.annotated_module.visible_symbols:
            rune_sym = self.annotated_module.visible_symbols[rune_name]
            if rune_sym.realm and rune_sym.realm in self.realms:
                r_tbl = self.realms[rune_sym.realm]
                if rune_name in r_tbl.rune_fields and field_name in r_tbl.rune_fields[rune_name]:
                    return r_tbl.rune_fields[rune_name][field_name]

        # 3. Check parent (heir) hierarchy
        rune_decl = self.rune_declarations.get(rune_name)
        if (
            rune_decl is not None
            and rune_decl.parent is not None
            and isinstance(rune_decl.parent, NamedType)
        ):
            return self._find_rune_field(rune_decl.parent.name, field_name)

        return None

    def _find_rune_method(self, rune_name: str, method_name: str) -> Symbol | None:
        # 1. Search in current realm's rune_methods
        table = self.realms.get(self.current_realm)
        if table is not None and rune_name in table.rune_methods:
            methods = table.rune_methods[rune_name]
            if method_name in methods:
                return methods[method_name]

        # 2. Search in visible symbols
        if rune_name in self.annotated_module.visible_symbols:
            rune_sym = self.annotated_module.visible_symbols[rune_name]
            if rune_sym.realm and rune_sym.realm in self.realms:
                r_tbl = self.realms[rune_sym.realm]
                if rune_name in r_tbl.rune_methods and method_name in r_tbl.rune_methods[rune_name]:
                    return r_tbl.rune_methods[rune_name][method_name]

        # 3. Check parent (heir) hierarchy
        rune_decl = self.rune_declarations.get(rune_name)
        if (
            rune_decl is not None
            and rune_decl.parent is not None
            and isinstance(rune_decl.parent, NamedType)
        ):
            return self._find_rune_method(rune_decl.parent.name, method_name)

        return None

    # --- Visitor Methods ---

    def visit_module(self, node: Module) -> None:
        for decl in node.declarations:
            self.visit(decl)

    def visit_function_decl(self, node: FunctionDecl) -> None:
        sym = self.current_scope.lookup_local(node.name)
        if sym is not None:
            self.record_reference(node, sym)
        self.visit(node.function)

    def visit_function_literal(self, node: FunctionLiteral) -> None:
        fn_scope = Scope(
            kind=ScopeKind.FUNCTION,
            parent=self.current_scope,
            enclosing_rune=self.current_rune,
        )
        self.push_scope(fn_scope)

        # 1. Register generic sigils (<T, U>)
        for sigil in node.sigils:
            s_sym = Symbol(
                id=SymbolId(self.module_path, sigil.span or _EMPTY_SPAN),
                name=sigil.name,
                kind=SymbolKind.SIGIL,
                realm=self.current_realm,
                decl_node_id=NodeId(self.module_path, sigil.span or _EMPTY_SPAN),
            )
            fn_scope.define(s_sym)
            self.record_reference(sigil, s_sym)

        # 2. Register parameters
        for param in node.params:
            p_sym = Symbol(
                id=SymbolId(self.module_path, param.span or _EMPTY_SPAN),
                name=param.name,
                kind=SymbolKind.PARAMETER,
                realm=self.current_realm,
                is_mut=param.is_mut,
                decl_node_id=NodeId(self.module_path, param.span or _EMPTY_SPAN),
            )
            fn_scope.define(p_sym)
            self.record_reference(param, p_sym)
            if param.type_annotation is not None:
                self.visit(param.type_annotation)
            if param.default_value is not None:
                self.visit(param.default_value)

        # 3. Return type
        if node.return_type is not None:
            self.visit(node.return_type)

        # 4. Body
        if node.body is not None:
            self.visit(node.body)

        self.pop_scope()

    def visit_rune_decl(self, node: RuneDecl) -> None:
        rune_scope = Scope(
            kind=ScopeKind.RUNE,
            parent=self.current_scope,
            enclosing_rune=node.name,
        )
        self.push_scope(rune_scope)

        # Register generic sigils
        for sigil in node.sigils:
            s_sym = Symbol(
                id=SymbolId(self.module_path, sigil.span or _EMPTY_SPAN),
                name=sigil.name,
                kind=SymbolKind.SIGIL,
                realm=self.current_realm,
                decl_node_id=NodeId(self.module_path, sigil.span or _EMPTY_SPAN),
            )
            rune_scope.define(s_sym)
            self.record_reference(sigil, s_sym)

        if node.parent is not None:
            self.visit(node.parent)
            if isinstance(node.parent, NamedType):
                parent_name = node.parent.name
                parent_sym = self.current_scope.lookup(parent_name)
                if parent_sym is not None:
                    # E2213: heir target is not a rune
                    if parent_sym.kind != SymbolKind.RUNE:
                        self.diagnostics.append(
                            Diagnostic(
                                code="E2213",
                                message=(
                                    f"Inheritance target '{parent_name}' is not a rune "
                                    f"(it is a {parent_sym.kind.name.lower()})"
                                ),
                                span=node.parent.span,
                                source_file=self.module_path,
                            )
                        )
                    # E2214: generic rune inherited without type arguments
                    elif parent_sym.sigils and not node.parent.args:
                        self.diagnostics.append(
                            Diagnostic(
                                code="E2214",
                                message=(
                                    f"Inherited rune '{parent_name}' is generic but inherited "
                                    "without type arguments"
                                ),
                                span=node.parent.span,
                                source_file=self.module_path,
                                hint=f"Instantiate type arguments: '{parent_name}<int>'",
                            )
                        )

                # E2221: Inheritance cycle
                cur_name: str | None = parent_name
                cycle_visited: set[str] = {node.name}
                while cur_name:
                    if cur_name in cycle_visited:
                        self.diagnostics.append(
                            Diagnostic(
                                code="E2221",
                                message=(
                                    f"Inheritance cycle detected: '{node.name}' -> '{cur_name}'"
                                ),
                                span=node.parent.span,
                                source_file=self.module_path,
                            )
                        )
                        break
                    cycle_visited.add(cur_name)
                    p_decl = self.rune_declarations.get(cur_name)
                    cur_name = (
                        p_decl.parent.name
                        if p_decl and isinstance(p_decl.parent, NamedType)
                        else None
                    )

        for f in node.fields:
            self.visit(f.type_annotation)
            if f.default_value is not None:
                self.visit(f.default_value)

        if node.constructor is not None:
            self.visit(node.constructor)

        if node.destructor is not None:
            self.visit(node.destructor)

        self.pop_scope()

    def visit_enchanting_decl(self, node: EnchantingDecl) -> None:
        self.visit(node.target_type)
        enclosing_name = node.target_type.name if isinstance(node.target_type, NamedType) else None

        # Check E2218: generic enchanting matches rune sigils
        if isinstance(node.target_type, NamedType):
            target_name = node.target_type.name
            r_decl = self.rune_declarations.get(target_name)
            if r_decl is not None and r_decl.sigils and node.target_type.args:
                expected_sigils = [s.name for s in r_decl.sigils]
                actual_sigils = [a.name for a in node.target_type.args if isinstance(a, NamedType)]
                if expected_sigils != actual_sigils:
                    self.diagnostics.append(
                        Diagnostic(
                            code="E2218",
                            message=(
                                f"Enchanting block for generic rune '{target_name}' has "
                                f"mismatched sigils: expected <{', '.join(expected_sigils)}>, "
                                f"got <{', '.join(actual_sigils)}>"
                            ),
                            span=node.target_type.span,
                            source_file=self.module_path,
                        )
                    )

        enc_scope = Scope(
            kind=ScopeKind.RUNE,
            parent=self.current_scope,
            enclosing_rune=enclosing_name,
        )
        self.push_scope(enc_scope)

        for member in node.members:
            self.visit(member)

        self.pop_scope()

    def visit_constructor_decl(self, node: ConstructorDecl) -> None:
        # Check E2311: parent(...) must be the first statement in constructor
        if node.body and node.body.statements:
            for idx, stmt in enumerate(node.body.statements):
                if isinstance(stmt, ParentCall) and idx > 0:
                    self.diagnostics.append(
                        Diagnostic(
                            code="E2311",
                            message="'parent(...)' must be the first statement in the constructor",
                            span=stmt.span or node.body.span,
                            source_file=self.module_path,
                            hint="Move the 'parent(...)' call to the beginning of the constructor",
                        )
                    )

        ctor_scope = Scope(
            kind=ScopeKind.FUNCTION,
            parent=self.current_scope,
            enclosing_rune=self.current_rune,
            in_constructor=True,
        )
        self.push_scope(ctor_scope)

        for param in node.params:
            p_sym = Symbol(
                id=SymbolId(self.module_path, param.span or _EMPTY_SPAN),
                name=param.name,
                kind=SymbolKind.PARAMETER,
                realm=self.current_realm,
                is_mut=param.is_mut,
                decl_node_id=NodeId(self.module_path, param.span or _EMPTY_SPAN),
            )
            ctor_scope.define(p_sym)
            self.record_reference(param, p_sym)
            if param.type_annotation is not None:
                self.visit(param.type_annotation)
            if param.default_value is not None:
                self.visit(param.default_value)

        self.visit(node.body)
        self.pop_scope()

    def visit_destructor_decl(self, node: DestructorDecl) -> None:
        dtor_scope = Scope(
            kind=ScopeKind.FUNCTION,
            parent=self.current_scope,
            enclosing_rune=self.current_rune,
        )
        self.push_scope(dtor_scope)
        self.visit(node.body)
        self.pop_scope()

    def visit_method_decl(self, node: MethodDecl) -> None:
        self.visit(node.function)

    def visit_operator_decl(self, node: OperatorDecl) -> None:
        # Check E2209: free operator collides with enchanting operator
        if self.current_rune is None and node.function.params:
            first_type = node.function.params[0].type_annotation
            if isinstance(first_type, NamedType):
                t_name = first_type.name
                r_tbl = self.realms.get(self.current_realm)
                if (
                    r_tbl is not None
                    and t_name in r_tbl.rune_methods
                    and (
                        node.op in r_tbl.rune_methods[t_name]
                        or f"op_{node.op}" in r_tbl.rune_methods[t_name]
                    )
                ):
                    self.diagnostics.append(
                        Diagnostic(
                            code="E2209",
                            message=(
                                f"Free operator '{node.op}' collides with enchanting operator "
                                f"on '{t_name}'"
                            ),
                            span=node.span,
                            source_file=self.module_path,
                        )
                    )
        self.visit(node.function)

    def visit_parent_call(self, node: ParentCall) -> None:
        if not self.in_constructor:
            self.diagnostics.append(
                Diagnostic(
                    code="E2309",
                    message="'parent(...)' can only be called inside a constructor",
                    span=node.span,
                    source_file=self.module_path,
                )
            )
        else:
            cur_rune = self.current_rune
            rune_decl = self.rune_declarations.get(cur_rune) if cur_rune else None
            if rune_decl is None or rune_decl.parent is None:
                self.diagnostics.append(
                    Diagnostic(
                        code="E2310",
                        message=(
                            f"'parent(...)' called in rune '{cur_rune or 'unknown'}' which does "
                            "not inherit from any parent ('heir')"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                    )
                )

        for arg in node.args:
            self.visit(arg)

    def visit_self_ref(self, node: SelfRef) -> None:
        if self.current_rune is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2306",
                    message=(
                        "'@' (self) cannot be used outside a method, constructor, or destructor"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )

    def visit_self_field(self, node: SelfField) -> None:
        if self.current_rune is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2306",
                    message=(
                        "'@' (self) cannot be used outside a method, constructor, or destructor"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
            return

        field_sym = self._find_rune_field(self.current_rune, node.name)
        if field_sym is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2307",
                    message=f"Field '@{node.name}' does not exist on rune '{self.current_rune}'",
                    span=node.span,
                    source_file=self.module_path,
                )
            )
        else:
            self.record_reference(node, field_sym)

    def visit_self_method_call(self, node: SelfMethodCall) -> None:
        if self.current_rune is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2306",
                    message=(
                        "'@' (self) cannot be used outside a method, constructor, or destructor"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
        else:
            method_sym = self._find_rune_method(self.current_rune, node.name)
            if method_sym is None:
                self.diagnostics.append(
                    Diagnostic(
                        code="E2308",
                        message=(
                            f"Method '@{node.name}' does not exist on rune '{self.current_rune}'"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                    )
                )
            else:
                self.record_reference(node, method_sym)

        for arg in node.args:
            self.visit(arg)

    def visit_self_field_target(self, node: SelfFieldTarget) -> None:
        if self.current_rune is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2306",
                    message=(
                        "'@' (self) cannot be used outside a method, constructor, or destructor"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
            return

        field_sym = self._find_rune_field(self.current_rune, node.name)
        if field_sym is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2307",
                    message=f"Field '@{node.name}' does not exist on rune '{self.current_rune}'",
                    span=node.span,
                    source_file=self.module_path,
                )
            )
        else:
            self.record_reference(node, field_sym)

    def visit_ident(self, node: Ident) -> None:
        sym = self.current_scope.lookup(node.name)
        if sym is not None:
            self.record_reference(node, sym)
            return

        # Check E2315: used before declaration in the same block
        for future_map in reversed(self.block_future_locals):
            if node.name in future_map:
                decl_span = future_map[node.name]
                self.diagnostics.append(
                    Diagnostic(
                        code="E2315",
                        message=(
                            f"Local variable '{node.name}' used before declaration in the "
                            "same block"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                        secondary_labels=(
                            (Label(span=decl_span, message="declared later here"),)
                            if decl_span
                            else ()
                        ),
                        hint=f"Move the declaration of '{node.name}' before its first use",
                    )
                )
                return

        # Check if identifier names an imported realm
        if node.name in self.annotated_module.visible_realms:
            self.diagnostics.append(
                Diagnostic(
                    code="E2301",
                    message=f"Undefined identifier '{node.name}'",
                    span=node.span,
                    source_file=self.module_path,
                    notes=(
                        f"'{node.name}' is an imported realm; access its members using "
                        f"'{node.name}::<member>'",
                    ),
                )
            )
            return

        # E2301: Undefined identifier
        matches = find_best_matches(node.name, self._all_visible_names())
        hint = f"Did you mean '{matches[0]}'?" if matches else None
        self.diagnostics.append(
            Diagnostic(
                code="E2301",
                message=f"Undefined identifier '{node.name}'",
                span=node.span,
                source_file=self.module_path,
                hint=hint,
            )
        )

    def visit_realm_access(self, node: RealmAccess) -> None:
        # Check E2318: Dynamic variable accessed with ::
        sym = self.current_scope.lookup(node.realm)
        if sym is not None and sym.kind in (SymbolKind.LOCAL, SymbolKind.PARAMETER):
            self.diagnostics.append(
                Diagnostic(
                    code="E2318",
                    message=(
                        f"Dynamic variable '{node.realm}' cannot be accessed with '::'. "
                        "Use '.' instead"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                    hint=f"Use '{node.realm}.{node.name}'",
                )
            )
            return

        # Check E2302: Unresolved realm prefix
        if node.realm not in self.annotated_module.visible_realms:
            self.diagnostics.append(
                Diagnostic(
                    code="E2302",
                    message=f"Unresolved realm prefix '{node.realm}'",
                    span=node.span,
                    source_file=self.module_path,
                    hint=f"Import realm '{node.realm}' with 'invoke {node.realm}'",
                )
            )
            return

        target_realm = self.annotated_module.visible_realms[node.realm]
        realm_table = self.realms.get(target_realm)
        if realm_table is None or node.name not in realm_table.symbols:
            hint = None
            if realm_table is not None:
                matches = find_best_matches(node.name, realm_table.symbols.keys())
                if matches:
                    hint = f"Did you mean '{matches[0]}'?"
            self.diagnostics.append(
                Diagnostic(
                    code="E2303",
                    message=f"Symbol '{node.name}' not found in realm '{node.realm}'",
                    span=node.span,
                    source_file=self.module_path,
                    hint=hint,
                )
            )
            return

        target_sym = realm_table.symbols[node.name]
        self.record_reference(node, target_sym)

    def visit_enum_variant(self, node: EnumVariant) -> None:
        sym = self.current_scope.lookup(node.enum_name)
        if sym is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2313",
                    message=(
                        f"Type '{node.enum_name}' does not exist in realm, imports, or prelude"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
            return

        if sym.kind != SymbolKind.OMEN:
            self.diagnostics.append(
                Diagnostic(
                    code="E2314",
                    message=(
                        f"Static member access '{node.enum_name}::{node.variant_name}' is not "
                        f"supported for {sym.kind.name.lower()}"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
            return

        realm_name = sym.realm or self.current_realm
        realm_table = self.realms.get(realm_name)
        variants = realm_table.omen_variants.get(node.enum_name, {}) if realm_table else {}

        if node.variant_name not in variants:
            hint = None
            matches = find_best_matches(node.variant_name, variants.keys())
            if matches:
                hint = f"Did you mean '{matches[0]}'?"
            self.diagnostics.append(
                Diagnostic(
                    code="E2303",
                    message=f"Variant '{node.variant_name}' not found on omen '{node.enum_name}'",
                    span=node.span,
                    source_file=self.module_path,
                    hint=hint,
                )
            )
        else:
            self.record_reference(node, variants[node.variant_name])

    def visit_type_static_access(self, node: TypeStaticAccess) -> None:
        sym = self.current_scope.lookup(node.type_name)
        if sym is None:
            self.diagnostics.append(
                Diagnostic(
                    code="E2313",
                    message=(
                        f"Type '{node.type_name}' does not exist in realm, imports, or prelude"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )
            return

        if sym.kind == SymbolKind.RUNE:
            realm_name = sym.realm or self.current_realm
            realm_table = self.realms.get(realm_name)
            methods = realm_table.rune_methods.get(node.type_name, {}) if realm_table else {}
            if node.method_name in methods:
                self.record_reference(node, methods[node.method_name])
            else:
                hint = None
                matches = find_best_matches(node.method_name, methods.keys())
                if matches:
                    hint = f"Did you mean '{matches[0]}'?"
                self.diagnostics.append(
                    Diagnostic(
                        code="E2303",
                        message=(
                            f"Static member '{node.method_name}' not found on type "
                            f"'{node.type_name}'"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                        hint=hint,
                    )
                )
        else:
            self.diagnostics.append(
                Diagnostic(
                    code="E2314",
                    message=(
                        f"Static member access '{node.type_name}::{node.method_name}' is not "
                        f"supported for {sym.kind.name.lower()}"
                    ),
                    span=node.span,
                    source_file=self.module_path,
                )
            )

    def visit_named_type(self, node: NamedType) -> None:
        sym = self.current_scope.lookup(node.name)
        valid_type_kinds = (
            SymbolKind.SIGIL,
            SymbolKind.RUNE,
            SymbolKind.OMEN,
            SymbolKind.ECHO,
            SymbolKind.SEAL,
            SymbolKind.BUILTIN_TYPE,
        )

        if sym is not None:
            if sym.kind in valid_type_kinds:
                self.record_reference(node, sym)
            else:
                self.diagnostics.append(
                    Diagnostic(
                        code="E2313",
                        message=f"'{node.name}' is a {sym.kind.name.lower()}, not a type",
                        span=node.span,
                        source_file=self.module_path,
                    )
                )
        else:
            # Check E2312 vs E2313
            if len(node.name) == 1 and node.name.isupper():
                self.diagnostics.append(
                    Diagnostic(
                        code="E2312",
                        message=(
                            f"Type parameter '{node.name}' is not declared in generic "
                            "parameters ('<...>')"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                        hint=f"Add '<{node.name}>' to the enclosing generic declaration",
                    )
                )
            else:
                matches = find_best_matches(node.name, self._all_type_names())
                hint = f"Did you mean '{matches[0]}'?" if matches else None
                self.diagnostics.append(
                    Diagnostic(
                        code="E2313",
                        message=f"Type '{node.name}' does not exist in realm, imports, or prelude",
                        span=node.span,
                        source_file=self.module_path,
                        hint=hint,
                    )
                )

        for arg in node.args:
            self.visit(arg)

    def visit_field_access(self, node: FieldAccess) -> None:
        if (
            isinstance(node.target, Ident)
            and node.target.name in self.annotated_module.visible_realms
        ):
            local_sym = self.current_scope.lookup(node.target.name)
            if local_sym is None or local_sym.kind not in (
                SymbolKind.LOCAL,
                SymbolKind.PARAMETER,
            ):
                self.diagnostics.append(
                    Diagnostic(
                        code="E2319",
                        message=(
                            f"Realm '{node.target.name}' cannot be accessed with '.'. "
                            f"Use '::' instead (e.g. '{node.target.name}::{node.field_name}')"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                        hint=f"Use '{node.target.name}::{node.field_name}'",
                    )
                )
                return

        self.visit(node.target)

    def visit_method_call(self, node: MethodCall) -> None:
        if (
            isinstance(node.target, Ident)
            and node.target.name in self.annotated_module.visible_realms
        ):
            local_sym = self.current_scope.lookup(node.target.name)
            if local_sym is None or local_sym.kind not in (
                SymbolKind.LOCAL,
                SymbolKind.PARAMETER,
            ):
                self.diagnostics.append(
                    Diagnostic(
                        code="E2319",
                        message=(
                            f"Realm '{node.target.name}' cannot be accessed with '.'. "
                            f"Use '::' instead (e.g. '{node.target.name}::{node.method_name}')"
                        ),
                        span=node.span,
                        source_file=self.module_path,
                        hint=f"Use '{node.target.name}::{node.method_name}'",
                    )
                )
                return

        self.visit(node.target)
        for arg in node.args:
            self.visit(arg)
        for targ in node.type_args:
            self.visit(targ)

    def visit_constructor_call(self, node: ConstructorCall) -> None:
        self.visit(node.target_type)
        for arg in node.args:
            self.visit(arg)

    def visit_call(self, node: Call) -> None:
        self.visit(node.callee)
        for arg in node.args:
            self.visit(arg)
        for targ in node.type_args:
            self.visit(targ)

    def visit_cast(self, node: Cast) -> None:
        self.visit(node.expr)
        self.visit(node.target_type)

    def visit_unary(self, node: Unary) -> None:
        self.visit(node.operand)

    def visit_binary(self, node: Binary) -> None:
        self.visit(node.left)
        self.visit(node.right)

    def visit_range(self, node: Range) -> None:
        self.visit(node.start)
        self.visit(node.end)

    def visit_index(self, node: Index) -> None:
        self.visit(node.target)
        for idx in node.indices:
            self.visit(idx)

    def visit_tuple_literal(self, node: TupleLiteral) -> None:
        for elem in node.elements:
            self.visit(elem)

    def visit_list_lit(self, node: ListLit) -> None:
        if node.type_prefix is not None:
            self.visit(node.type_prefix)
        for elem in node.elements:
            self.visit(elem)

    def visit_map_lit(self, node: MapLit) -> None:
        if node.type_prefix is not None:
            self.visit(node.type_prefix)
        for entry in node.entries:
            self.visit(entry.key)
            self.visit(entry.value)

    def visit_set_lit(self, node: SetLit) -> None:
        for elem in node.elements:
            self.visit(elem)

    def visit_string_interp(self, node: StringInterp) -> None:
        for part in node.parts:
            if isinstance(part, Node):
                self.visit(part)

    def visit_if_inline(self, node: IfInline) -> None:
        self.visit(node.condition)
        self.visit(node.then_expr)
        self.visit(node.else_expr)

    def visit_if_block_expr(self, node: IfBlockExpr) -> None:
        self.visit(node.condition)
        self.visit(node.body)
        for clause in node.else_if_clauses:
            self.visit(clause)
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_else_if_clause(self, node: ElseIfClause) -> None:
        self.visit(node.condition)
        self.visit(node.body)

    def visit_if(self, node: If) -> None:
        self.visit(node.condition)
        self.visit(node.then_block)
        for clause in node.else_if_clauses:
            self.visit(clause)
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_unless(self, node: Unless) -> None:
        self.visit(node.condition)
        self.visit(node.body)
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_while(self, node: While) -> None:
        self.visit(node.condition)
        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        self.push_scope(loop_scope)
        self.visit(node.body)
        self.pop_scope()
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_until(self, node: Until) -> None:
        self.visit(node.condition)
        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        self.push_scope(loop_scope)
        self.visit(node.body)
        self.pop_scope()
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_repeat(self, node: Repeat) -> None:
        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        self.push_scope(loop_scope)
        self.visit(node.body)
        self.pop_scope()
        self.visit(node.condition)
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_for_numeric(self, node: ForNumeric) -> None:
        self.visit(node.start)
        self.visit(node.end)
        if node.step is not None:
            self.visit(node.step)
        if node.var_type is not None:
            self.visit(node.var_type)

        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        self.push_scope(loop_scope)

        var_sym = Symbol(
            id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
            name=node.var_name,
            kind=SymbolKind.LOCAL,
            realm=self.current_realm,
            decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
        )
        loop_scope.define(var_sym)

        self.visit(node.body)
        self.pop_scope()

        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_for_iter(self, node: ForIter) -> None:
        self.visit(node.iterable)

        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        self.push_scope(loop_scope)

        target_sym = Symbol(
            id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
            name=node.target,
            kind=SymbolKind.LOCAL,
            realm=self.current_realm,
            is_mut=node.is_mut,
            decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
        )
        loop_scope.define(target_sym)

        if node.index_var is not None:
            idx_sym = Symbol(
                id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
                name=node.index_var,
                kind=SymbolKind.LOCAL,
                realm=self.current_realm,
                decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
            )
            loop_scope.define(idx_sym)

        self.visit(node.body)
        self.pop_scope()

        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_list_comp(self, node: ListComp) -> None:
        comp_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope)
        self.push_scope(comp_scope)

        for clause in node.for_clauses:
            if clause.iterable is not None:
                self.visit(clause.iterable)
            if clause.start is not None:
                self.visit(clause.start)
            if clause.end is not None:
                self.visit(clause.end)
            if clause.step is not None:
                self.visit(clause.step)

            c_sym = Symbol(
                id=SymbolId(self.module_path, clause.span or _EMPTY_SPAN),
                name=clause.target,
                kind=SymbolKind.LOCAL,
                realm=self.current_realm,
                is_mut=clause.is_mut,
                decl_node_id=NodeId(self.module_path, clause.span or _EMPTY_SPAN),
            )
            comp_scope.define(c_sym)

            if clause.index_var is not None:
                idx_sym = Symbol(
                    id=SymbolId(self.module_path, clause.span or _EMPTY_SPAN),
                    name=clause.index_var,
                    kind=SymbolKind.LOCAL,
                    realm=self.current_realm,
                    decl_node_id=NodeId(self.module_path, clause.span or _EMPTY_SPAN),
                )
                comp_scope.define(idx_sym)

            if clause.condition is not None:
                self.visit(clause.condition)

        self.visit(node.element)
        self.pop_scope()

    def visit_break(self, node: Break) -> None:
        if not self.in_loop:
            self.diagnostics.append(
                Diagnostic(
                    code="E2320",
                    message="'break' statement outside of a loop",
                    span=node.span,
                    source_file=self.module_path,
                )
            )
        if node.value is not None:
            self.visit(node.value)

    def visit_continue(self, node: Continue) -> None:
        if not self.in_loop:
            self.diagnostics.append(
                Diagnostic(
                    code="E2321",
                    message="'continue' statement outside of a loop",
                    span=node.span,
                    source_file=self.module_path,
                )
            )

    def visit_unsafe_block(self, node: UnsafeBlock) -> None:
        self.visit(node.body)

    def visit_expr_stmt(self, node: ExprStmt) -> None:
        self.visit(node.expr)

    def visit_compound_assign(self, node: CompoundAssign) -> None:
        self.visit(node.value)
        self.visit(node.target)
        if isinstance(node.target, (VarTarget, Ident)):
            sym = self.current_scope.lookup(node.target.name)
            if sym is not None:
                self.mutated_symbols.add(sym.id)

    def visit_expr_target(self, node: ExprTarget) -> None:
        self.visit(node.expr)

    def visit_const_decl(self, node: ConstDecl) -> None:
        if node.type_annotation is not None:
            self.visit(node.type_annotation)
        self.visit(node.value)

    def visit_echo_decl(self, node: EchoDecl) -> None:
        self.visit(node.target_type)
        if isinstance(node.target_type, NamedType):
            cur_alias: str | None = node.target_type.name
            visited_aliases: set[str] = {node.name}
            while cur_alias:
                if cur_alias in visited_aliases:
                    self.diagnostics.append(
                        Diagnostic(
                            code="E2220",
                            message=(
                                f"Cycle detected in type aliases: '{node.name}' -> '{cur_alias}'"
                            ),
                            span=node.span,
                            source_file=self.module_path,
                        )
                    )
                    break
                visited_aliases.add(cur_alias)
                p_echo = self.echo_declarations.get(cur_alias)
                cur_alias = (
                    p_echo.target_type.name
                    if p_echo and isinstance(p_echo.target_type, NamedType)
                    else None
                )

    def visit_seal_decl(self, node: SealDecl) -> None:
        self.visit(node.target_type)

    def visit_block(self, node: Block) -> None:
        block_scope = Scope(
            kind=ScopeKind.BLOCK,
            parent=self.current_scope,
            in_loop=self.current_scope.in_loop,
            in_constructor=self.current_scope.in_constructor,
            enclosing_rune=self.current_rune,
        )
        self.push_scope(block_scope)

        # Pre-scan block statements for declared local variables (for E2315)
        future_map: dict[str, Span] = {}
        for stmt in node.statements:
            if isinstance(stmt, Assign):
                for t in stmt.targets:
                    if isinstance(t, VarTarget) and t.name not in future_map:
                        future_map[t.name] = t.span or _EMPTY_SPAN
            elif isinstance(stmt, ForNumeric) and stmt.var_name not in future_map:
                future_map[stmt.var_name] = stmt.span or _EMPTY_SPAN
            elif isinstance(stmt, ForIter):
                if stmt.target not in future_map:
                    future_map[stmt.target] = stmt.span or _EMPTY_SPAN
                if stmt.index_var and stmt.index_var not in future_map:
                    future_map[stmt.index_var] = stmt.span or _EMPTY_SPAN

        self.block_future_locals.append(future_map)

        for stmt in node.statements:
            self.visit(stmt)

        self.block_future_locals.pop()
        self.pop_scope()

    def visit_assign(self, node: Assign) -> None:
        # 1. Visit value and type annotation first (in current scope)
        self.visit(node.value)
        if node.type_annotation is not None:
            self.visit(node.type_annotation)

        # 2. Process targets
        for target in node.targets:
            if isinstance(target, VarTarget):
                var_name = target.name
                # Remove from future locals map
                if self.block_future_locals and var_name in self.block_future_locals[-1]:
                    del self.block_future_locals[-1][var_name]

                local_sym = self.current_scope.lookup_local(var_name)
                if local_sym is not None:
                    # Redeclaration in the same scope (E2317)
                    if node.is_mut or node.type_annotation is not None:
                        prev_label = (
                            Label(span=local_sym.id.span, message="first declared here")
                            if local_sym.id.span
                            else None
                        )
                        self.diagnostics.append(
                            Diagnostic(
                                code="E2317",
                                message=(
                                    f"Duplicate variable declaration '{var_name}' in the same scope"
                                ),
                                span=target.span,
                                source_file=self.module_path,
                                secondary_labels=(prev_label,) if prev_label else (),
                                hint=(
                                    f"Remove 'mut' or the type annotation to reassign '{var_name}'"
                                ),
                            )
                        )
                    else:
                        # Reassignment to existing local
                        self.mutated_symbols.add(local_sym.id)
                        self.record_reference(target, local_sym)
                else:
                    # Check outer scopes: is it a reassignment to an outer local variable?
                    outer_sym = self.current_scope.lookup(var_name)
                    if (
                        outer_sym is not None
                        and not node.is_mut
                        and node.type_annotation is None
                        and outer_sym.kind in (SymbolKind.LOCAL, SymbolKind.PARAMETER)
                    ):
                        self.mutated_symbols.add(outer_sym.id)
                        self.record_reference(target, outer_sym)
                    else:
                        # New local variable declaration
                        new_sym = Symbol(
                            id=SymbolId(self.module_path, target.span or _EMPTY_SPAN),
                            name=var_name,
                            kind=SymbolKind.LOCAL,
                            realm=self.current_realm,
                            is_mut=node.is_mut,
                            decl_node_id=NodeId(self.module_path, target.span or _EMPTY_SPAN),
                        )
                        self.current_scope.define(new_sym)
                        self.record_reference(target, new_sym)
            else:
                self.visit(target)


def resolve_module(
    module: Module,
    module_path: Path,
    annotated_module: AnnotatedModule,
    realms: dict[str, RealmSymbolTable],
    rune_declarations: dict[str, RuneDecl] | None = None,
    echo_declarations: dict[str, EchoDecl] | None = None,
    prelude: dict[str, Symbol] | None = None,
) -> ResolutionResult:
    """Resolve symbol references for a single module."""
    resolver = Resolver(
        module_path=module_path,
        annotated_module=annotated_module,
        realms=realms,
        rune_declarations=rune_declarations,
        echo_declarations=echo_declarations,
        prelude=prelude,
    )
    resolver.visit(module)
    return ResolutionResult(
        references=resolver.references,
        symbols_to_refs=resolver.symbols_to_refs,
        diagnostics=resolver.diagnostics,
        mutated_symbols=frozenset(resolver.mutated_symbols),
    )


@dataclass(frozen=True, slots=True)
class ProjectResolutionResult:
    """Consolidated project resolution results."""

    references: dict[NodeId, Symbol]
    symbols_to_refs: dict[SymbolId, list[NodeId]]
    diagnostics: list[Diagnostic]
    mutated_symbols: frozenset[SymbolId] = frozenset()

    def __iter__(self) -> Any:
        return iter((self.references, self.symbols_to_refs, self.diagnostics))


def resolve_project(
    modules: dict[Path, Module],
    annotated_modules: dict[Path, AnnotatedModule],
    realms: dict[str, RealmSymbolTable],
) -> ProjectResolutionResult:
    """Resolve symbol references across all modules in a project."""
    rune_decls: dict[str, RuneDecl] = {}
    echo_decls: dict[str, EchoDecl] = {}
    for mod in modules.values():
        for decl in mod.declarations:
            if isinstance(decl, RuneDecl):
                rune_decls[decl.name] = decl
            elif isinstance(decl, EchoDecl):
                echo_decls[decl.name] = decl

    all_references: dict[NodeId, Symbol] = {}
    all_symbols_to_refs: dict[SymbolId, list[NodeId]] = {}
    all_mutated_symbols: set[SymbolId] = set()
    all_diagnostics: list[Diagnostic] = []

    for path, mod in sorted(modules.items(), key=lambda x: str(x[0])):
        ann_mod = annotated_modules.get(path)
        if ann_mod is None:
            continue
        res = resolve_module(
            module=mod,
            module_path=path,
            annotated_module=ann_mod,
            realms=realms,
            rune_declarations=rune_decls,
            echo_declarations=echo_decls,
        )
        all_references.update(res.references)
        all_mutated_symbols.update(res.mutated_symbols)
        for s_id, refs in res.symbols_to_refs.items():
            all_symbols_to_refs.setdefault(s_id, []).extend(refs)
        all_diagnostics.extend(res.diagnostics)

    return ProjectResolutionResult(
        references=all_references,
        symbols_to_refs=all_symbols_to_refs,
        diagnostics=all_diagnostics,
        mutated_symbols=frozenset(all_mutated_symbols),
    )


__all__ = [
    "ProjectResolutionResult",
    "ResolutionResult",
    "Resolver",
    "resolve_module",
    "resolve_project",
]
