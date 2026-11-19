"""Sub-fase 5: Scope analysis, unused warnings, privacy, and shadowing checks."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.diagnostics import Diagnostic, DiagnosticSeverity, Label
from penguscript.analysis.prelude import get_prelude_symbols
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
    Block,
    Break,
    Continue,
    ForIter,
    ForNumeric,
    FunctionLiteral,
    ListComp,
    Module,
    VarTarget,
)
from penguscript.frontend.span import Span

_EMPTY_SPAN = Span(0, 0, 1, 1)


class ShadowingAndLoopChecker(ASTVisitor):
    """Visitor that traverses module ASTs to check shadowing (W2307) and loop statements."""

    def __init__(
        self,
        module_path: Path,
        annotated_module: AnnotatedModule,
        realms: dict[str, RealmSymbolTable],
        prelude: dict[str, Symbol] | None = None,
    ) -> None:
        self.module_path = module_path
        self.annotated_module = annotated_module
        self.current_realm = annotated_module.declared_realm
        self.realms = realms
        self.prelude = prelude if prelude is not None else get_prelude_symbols()

        self.diagnostics: list[Diagnostic] = []
        self.scope_stack: list[Scope] = []
        self._init_scopes()

        # Track declared local and parameter symbols in this module
        self.declared_locals: list[Symbol] = []
        self.declared_params: list[Symbol] = []

    def _init_scopes(self) -> None:
        prelude_scope = Scope(kind=ScopeKind.PRELUDE)
        for sym in self.prelude.values():
            prelude_scope.define(sym)

        module_scope = Scope(kind=ScopeKind.MODULE, parent=prelude_scope)
        realm_table = self.realms.get(self.current_realm)
        if realm_table is not None:
            for sym in realm_table.symbols.values():
                module_scope.define(sym)

        for sym in self.annotated_module.visible_symbols.values():
            module_scope.define(sym)

        self.scope_stack = [prelude_scope, module_scope]

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

    def _check_shadowing(self, name: str, span: Span | None) -> None:
        if name.startswith("_"):
            return
        outer_sym = self.current_scope.lookup(name)
        if outer_sym is not None and outer_sym.kind in (
            SymbolKind.LOCAL,
            SymbolKind.PARAMETER,
            SymbolKind.FUNCTION,
            SymbolKind.CONST,
        ):
            prev_label = (
                Label(span=outer_sym.id.span, message=f"outer {outer_sym.kind.name.lower()} here")
                if outer_sym.id.span
                else None
            )
            self.diagnostics.append(
                Diagnostic(
                    code="W2307",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Local '{name}' shadows an outer declaration",
                    span=span or _EMPTY_SPAN,
                    source_file=self.module_path,
                    secondary_labels=(prev_label,) if prev_label else (),
                    hint=f"Rename '{name}' to avoid shadowing the outer symbol",
                )
            )

    # --- Visitor Methods ---

    def visit_module(self, node: Module) -> None:
        for decl in node.declarations:
            self.visit(decl)

    def visit_function_literal(self, node: FunctionLiteral) -> None:
        fn_scope = Scope(kind=ScopeKind.FUNCTION, parent=self.current_scope)

        for param in node.params:
            self._check_shadowing(param.name, param.span)
            p_sym = Symbol(
                id=SymbolId(self.module_path, param.span or _EMPTY_SPAN),
                name=param.name,
                kind=SymbolKind.PARAMETER,
                realm=self.current_realm,
                is_mut=param.is_mut,
                decl_node_id=NodeId(self.module_path, param.span or _EMPTY_SPAN),
            )
            fn_scope.define(p_sym)
            self.declared_params.append(p_sym)
            if param.type_annotation is not None:
                self.visit(param.type_annotation)
            if param.default_value is not None:
                self.visit(param.default_value)

        self.push_scope(fn_scope)
        if node.return_type is not None:
            self.visit(node.return_type)
        if node.body is not None:
            self.visit(node.body)
        self.pop_scope()

    def visit_block(self, node: Block) -> None:
        block_scope = Scope(
            kind=ScopeKind.BLOCK,
            parent=self.current_scope,
            in_loop=self.current_scope.in_loop,
            in_constructor=self.current_scope.in_constructor,
        )
        self.push_scope(block_scope)
        for stmt in node.statements:
            self.visit(stmt)
        self.pop_scope()

    def visit_assign(self, node: Assign) -> None:
        self.visit(node.value)
        if node.type_annotation is not None:
            self.visit(node.type_annotation)

        for target in node.targets:
            if isinstance(target, VarTarget):
                var_name = target.name
                existing = self.current_scope.lookup_local(var_name)
                if existing is None:
                    # New local variable declaration
                    self._check_shadowing(var_name, target.span)
                    sym = Symbol(
                        id=SymbolId(self.module_path, target.span or _EMPTY_SPAN),
                        name=var_name,
                        kind=SymbolKind.LOCAL,
                        realm=self.current_realm,
                        is_mut=node.is_mut,
                        decl_node_id=NodeId(self.module_path, target.span or _EMPTY_SPAN),
                    )
                    self.current_scope.define(sym)
                    self.declared_locals.append(sym)
            else:
                self.visit(target)

    def visit_for_numeric(self, node: ForNumeric) -> None:
        self.visit(node.start)
        self.visit(node.end)
        if node.step is not None:
            self.visit(node.step)

        self._check_shadowing(node.var_name, node.span)
        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        var_sym = Symbol(
            id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
            name=node.var_name,
            kind=SymbolKind.LOCAL,
            realm=self.current_realm,
            decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
        )
        loop_scope.define(var_sym)
        self.declared_locals.append(var_sym)

        self.push_scope(loop_scope)
        self.visit(node.body)
        self.pop_scope()

        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_for_iter(self, node: ForIter) -> None:
        self.visit(node.iterable)

        self._check_shadowing(node.target, node.span)
        loop_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope, in_loop=True)
        target_sym = Symbol(
            id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
            name=node.target,
            kind=SymbolKind.LOCAL,
            realm=self.current_realm,
            is_mut=node.is_mut,
            decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
        )
        loop_scope.define(target_sym)
        self.declared_locals.append(target_sym)

        if node.index_var is not None:
            self._check_shadowing(node.index_var, node.span)
            idx_sym = Symbol(
                id=SymbolId(self.module_path, node.span or _EMPTY_SPAN),
                name=node.index_var,
                kind=SymbolKind.LOCAL,
                realm=self.current_realm,
                decl_node_id=NodeId(self.module_path, node.span or _EMPTY_SPAN),
            )
            loop_scope.define(idx_sym)
            self.declared_locals.append(idx_sym)

        self.push_scope(loop_scope)
        self.visit(node.body)
        self.pop_scope()

        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_list_comp(self, node: ListComp) -> None:
        comp_scope = Scope(kind=ScopeKind.BLOCK, parent=self.current_scope)

        for clause in node.for_clauses:
            if clause.iterable is not None:
                self.visit(clause.iterable)
            self._check_shadowing(clause.target, clause.span)
            c_sym = Symbol(
                id=SymbolId(self.module_path, clause.span or _EMPTY_SPAN),
                name=clause.target,
                kind=SymbolKind.LOCAL,
                realm=self.current_realm,
                is_mut=clause.is_mut,
                decl_node_id=NodeId(self.module_path, clause.span or _EMPTY_SPAN),
            )
            comp_scope.define(c_sym)
            self.declared_locals.append(c_sym)

            if clause.index_var is not None:
                self._check_shadowing(clause.index_var, clause.span)
                idx_sym = Symbol(
                    id=SymbolId(self.module_path, clause.span or _EMPTY_SPAN),
                    name=clause.index_var,
                    kind=SymbolKind.LOCAL,
                    realm=self.current_realm,
                    decl_node_id=NodeId(self.module_path, clause.span or _EMPTY_SPAN),
                )
                comp_scope.define(idx_sym)
                self.declared_locals.append(idx_sym)

            if clause.condition is not None:
                self.visit(clause.condition)

        self.push_scope(comp_scope)
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


def check_module_scopes(
    module: Module,
    module_path: Path,
    annotated_module: AnnotatedModule,
    realms: dict[str, RealmSymbolTable],
    references: dict[NodeId, Symbol],
    symbols_to_refs: dict[SymbolId, list[NodeId]],
    mutated_symbols: frozenset[SymbolId] = frozenset(),
    prelude: dict[str, Symbol] | None = None,
) -> list[Diagnostic]:
    """Run scope and lint checks on a single module, returning diagnostics."""
    diagnostics: list[Diagnostic] = []

    # 1. Lexical pass for shadowing (W2307) and loop checks (E2320, E2321)
    checker = ShadowingAndLoopChecker(
        module_path=module_path,
        annotated_module=annotated_module,
        realms=realms,
        prelude=prelude,
    )
    checker.visit(module)
    diagnostics.extend(checker.diagnostics)

    # 2. Check unused local variables (W2301) and unmutated mut (W2306)
    for sym in checker.declared_locals:
        if sym.name.startswith("_"):
            continue

        # Look for usages other than its own declaration
        all_refs = symbols_to_refs.get(sym.id, [])
        non_decl_refs = [r for r in all_refs if r != sym.decl_node_id]

        if not non_decl_refs:
            diagnostics.append(
                Diagnostic(
                    code="W2301",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Unused local variable '{sym.name}'",
                    span=sym.id.span,
                    source_file=module_path,
                    hint=f"If intentional, prefix with an underscore: '_{sym.name}'",
                )
            )
        elif sym.is_mut and sym.id not in mutated_symbols:
            # W2306: Declared as mut but never reassigned/mutated
            diagnostics.append(
                Diagnostic(
                    code="W2306",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Variable '{sym.name}' is declared as 'mut' but never mutated",
                    span=sym.id.span,
                    source_file=module_path,
                    hint=f"Remove the 'mut' keyword: '{sym.name}'",
                )
            )

    # 3. Check unused parameters (W2302)
    for p_sym in checker.declared_params:
        if p_sym.name.startswith("_"):
            continue

        all_refs = symbols_to_refs.get(p_sym.id, [])
        non_decl_refs = [r for r in all_refs if r != p_sym.decl_node_id]

        if not non_decl_refs:
            diagnostics.append(
                Diagnostic(
                    code="W2302",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Unused parameter '{p_sym.name}'",
                    span=p_sym.id.span,
                    source_file=module_path,
                    hint=f"If intentional, prefix with an underscore: '_{p_sym.name}'",
                )
            )

    # 4. Check unused imports: plain realm imports (W2303) and selective imports (W2304)
    file_referenced_symbols: set[Symbol] = {
        sym for nid, sym in references.items() if nid.path == module_path
    }

    for imp in annotated_module.imports:
        if imp.kind == "plain":
            # Check if any symbol in file came from imp.target_realm
            realm_used = any(
                sym.realm == imp.target_realm for sym in file_referenced_symbols if sym.realm
            )
            if not realm_used:
                alias = imp.local_alias or imp.target_realm
                diagnostics.append(
                    Diagnostic(
                        code="W2303",
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Unused imported realm '{alias}'",
                        span=imp.source_span,
                        source_file=module_path,
                        hint=f"Remove unused import 'invoke \"{imp.target_path}\"'",
                    )
                )
        elif imp.kind == "selective":
            for sym_name, sym in imp.imported_symbols.items():
                if sym_name.startswith("_"):
                    continue
                if sym not in file_referenced_symbols:
                    diagnostics.append(
                        Diagnostic(
                            code="W2304",
                            severity=DiagnosticSeverity.WARNING,
                            message=f"Unused imported symbol '{sym_name}'",
                            span=imp.source_span,
                            source_file=module_path,
                            hint=f"Remove '{sym_name}' from the import list",
                        )
                    )

    # 5. Check private symbol access (W2305)
    for nid, sym in references.items():
        if (
            nid.path == module_path
            and (sym.name.startswith("_") or sym.is_private)
            and sym.id.module_path != module_path
        ):
            prev_label = (
                Label(span=sym.id.span, message="private symbol declared here")
                if sym.id.span
                else None
            )
            diagnostics.append(
                Diagnostic(
                    code="W2305",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        f"Access to private symbol '{sym.name}' defined in "
                        f"'{sym.id.module_path.name}'"
                    ),
                    span=nid.span,
                    source_file=module_path,
                    secondary_labels=(prev_label,) if prev_label else (),
                    hint=(
                        f"Symbol '{sym.name}' is private by convention (starts with '_'). "
                        "Expose a public function or export without leading '_'"
                    ),
                )
            )

    return diagnostics


def check_project_scopes(
    modules: dict[Path, Module],
    annotated_modules: dict[Path, AnnotatedModule],
    realms: dict[str, RealmSymbolTable],
    references: dict[NodeId, Symbol],
    symbols_to_refs: dict[SymbolId, list[NodeId]],
    mutated_symbols: frozenset[SymbolId] = frozenset(),
    prelude: dict[str, Symbol] | None = None,
) -> list[Diagnostic]:
    """Run all scope and warning checks across all modules in the project."""
    all_diagnostics: list[Diagnostic] = []

    # 1. Module-level scope checks
    for path, mod in sorted(modules.items(), key=lambda x: str(x[0])):
        ann_mod = annotated_modules.get(path)
        if ann_mod is None:
            continue
        diags = check_module_scopes(
            module=mod,
            module_path=path,
            annotated_module=ann_mod,
            realms=realms,
            references=references,
            symbols_to_refs=symbols_to_refs,
            mutated_symbols=mutated_symbols,
            prelude=prelude,
        )
        all_diagnostics.extend(diags)

    # 2. Project-wide checks: Unused top-level constants (W2308)
    for realm_name, realm in realms.items():
        for sym_name, sym in realm.symbols.items():
            if sym.kind == SymbolKind.CONST and not sym_name.startswith("_"):
                all_refs = symbols_to_refs.get(sym.id, [])
                non_decl_refs = [r for r in all_refs if r != sym.decl_node_id]
                if not non_decl_refs:
                    all_diagnostics.append(
                        Diagnostic(
                            code="W2308",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                f"Unused top-level constant '{sym_name}' in realm '{realm_name}'"
                            ),
                            span=sym.id.span,
                            source_file=sym.id.module_path,
                            hint=f"If intentional, prefix with an underscore: '_{sym_name}'",
                        )
                    )

    return all_diagnostics


__all__ = [
    "ShadowingAndLoopChecker",
    "check_module_scopes",
    "check_project_scopes",
]
