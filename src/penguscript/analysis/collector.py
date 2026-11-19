"""Pass 1: Collector extracting top-level symbols and checking intra-file declarations."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.diagnostics import Diagnostic, Label
from penguscript.analysis.symbols import (
    NodeId,
    RawModuleDecl,
    Symbol,
    SymbolId,
    SymbolKind,
)
from penguscript.analysis.visitor import ASTVisitor
from penguscript.frontend.ast_nodes import (
    Assign,
    ConstDecl,
    ConstructorDecl,
    DestructorDecl,
    EchoDecl,
    EnchantingDecl,
    FunctionLiteral,
    HexLit,
    IntLit,
    InvokeDecl,
    MethodDecl,
    Module,
    OmenDecl,
    OperatorDecl,
    Parameter,
    RealmDecl,
    RuneDecl,
    SealDecl,
    SigilParam,
    VarTarget,
)

RESERVED_KEYWORDS: frozenset[str] = frozenset(
    {
        "mut",
        "const",
        "static",
        "realm",
        "invoke",
        "from",
        "as",
        "rune",
        "enchanting",
        "heir",
        "omen",
        "flags",
        "echo",
        "seal",
        "constructor",
        "destructor",
        "operator",
        "unsafe",
        "parent",
        "if",
        "else",
        "then",
        "unless",
        "while",
        "until",
        "repeat",
        "for",
        "in",
        "break",
        "continue",
        "not",
        "and",
        "or",
        "needs",
        "function",
        "true",
        "false",
        "none",
        "nullopt",
        "nullptr",
        "pass",
    }
)


class Collector(ASTVisitor):
    """Pass 1 visitor that extracts top-level symbols, imports, and validates declarations."""

    def __init__(self, path: Path | str = "<stdin>") -> None:
        self.path = Path(path) if isinstance(path, str) else path
        self.raw = RawModuleDecl(
            path=self.path,
            declared_realm="",
            is_explicit_realm=False,
        )

    def collect(self, module: Module) -> RawModuleDecl:
        """Run collection over an AST Module."""
        self._determine_realm(module)
        self.visit(module)
        return self.raw

    def _determine_realm(self, module: Module) -> None:
        """Determine whether the realm is explicitly declared or implicit from file path."""
        realms = [d for d in module.declarations if isinstance(d, RealmDecl)]

        if len(realms) > 1:
            for extra in realms[1:]:
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2102",
                        message=f"Multiple realm declarations in file '{self.path}'",
                        span=extra.span,
                        source_file=self.path,
                    )
                )

        if realms:
            r = realms[0]
            self.raw.declared_realm = r.name
            self.raw.is_explicit_realm = True
            self.raw.realm_span = r.span

            # Check if realm name is a reserved keyword (E2103)
            if r.name in RESERVED_KEYWORDS:
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2103",
                        message=f"Realm name '{r.name}' is a reserved keyword",
                        span=r.span,
                        source_file=self.path,
                    )
                )
        else:
            # Implicit realm from filename
            stem = self.path.stem
            if stem == "index" and self.path.parent.name and self.path.parent.name != ".":
                self.raw.declared_realm = self.path.parent.name
            elif stem and stem != "<stdin>":
                self.raw.declared_realm = stem
            else:
                self.raw.declared_realm = "main"
            self.raw.is_explicit_realm = False

    def visit_module(self, node: Module) -> None:
        """Visit top-level declarations in the module."""
        # Check if realm was declared after statements (E2101)
        found_non_header = False
        for decl in node.declarations:
            if isinstance(decl, RealmDecl):
                if found_non_header:
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2101",
                            message=f"Realm '{decl.name}' declared after executable statements",
                            span=decl.span,
                            source_file=self.path,
                        )
                    )
            elif isinstance(decl, InvokeDecl):
                if found_non_header:
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2007",
                            message="Import 'invoke' declared after executable statements",
                            span=decl.span,
                            source_file=self.path,
                            hint="Place all 'invoke' declarations at the top of the file",
                        )
                    )
                self.raw.imports.append(decl)
            else:
                found_non_header = True
                self.visit(decl)

    def _register_top_symbol(self, symbol: Symbol) -> bool:
        """Register a top-level symbol in raw_module. Return False and emit E2201 on collision."""
        existing = self.raw.symbols.get(symbol.name)
        if existing is not None:
            prev_label = (
                Label(span=existing.id.span, message="previously declared here")
                if existing.id.span
                else None
            )
            labels = (prev_label,) if prev_label else ()
            self.raw.diagnostics.append(
                Diagnostic(
                    code="E2201",
                    message=(
                        f"Duplicate top-level symbol '{symbol.name}' in realm "
                        f"'{self.raw.declared_realm}'"
                    ),
                    span=symbol.id.span,
                    source_file=self.path,
                    secondary_labels=labels,
                    notes=(
                        f"Realms merge across files; '{symbol.name}' is already defined in this "
                        "module",
                    ),
                )
            )
            return False
        self.raw.symbols[symbol.name] = symbol
        return True

    def _check_sigils(self, entity_name: str, sigils: list[SigilParam]) -> None:
        """Check duplicate sigils (E2210) and sigils colliding with the entity name (E2211)."""
        seen_sigils: dict[str, SigilParam] = {}
        for s in sigils:
            if s.name == entity_name:
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2211",
                        message=(
                            f"Sigil '{s.name}' cannot have the same name as enclosing "
                            f"'{entity_name}'"
                        ),
                        span=s.span,
                        source_file=self.path,
                    )
                )
            if s.name in seen_sigils:
                prev_s = seen_sigils[s.name]
                labels = (
                    (Label(span=prev_s.span, message="first declared here"),)
                    if prev_s.span is not None
                    else ()
                )
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2210",
                        message=f"Duplicate generic sigil parameter '{s.name}'",
                        span=s.span,
                        source_file=self.path,
                        secondary_labels=labels,
                    )
                )
            else:
                seen_sigils[s.name] = s

    def _check_params(self, params: list[Parameter]) -> None:
        """Check duplicate parameter names in function signatures (E2219)."""
        seen: dict[str, Parameter] = {}
        for p in params:
            if p.name in seen:
                prev_p = seen[p.name]
                labels = (
                    (Label(span=prev_p.span, message="previously declared here"),)
                    if prev_p.span is not None
                    else ()
                )
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2219",
                        message=f"Duplicate parameter '{p.name}' in function signature",
                        span=p.span,
                        source_file=self.path,
                        secondary_labels=labels,
                    )
                )
            else:
                seen[p.name] = p

    def visit_const_decl(self, node: ConstDecl) -> None:
        """Register top-level constant."""
        sym_id = SymbolId(module_path=self.path, span=node.span or node.value.span)  # type: ignore[arg-type]
        sym = Symbol(
            id=sym_id,
            name=node.name,
            kind=SymbolKind.CONST,
            realm=self.raw.declared_realm,
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

    def visit_echo_decl(self, node: EchoDecl) -> None:
        """Register transparent type alias (echo)."""
        self._check_sigils(node.name, node.sigils)
        sym_id = SymbolId(module_path=self.path, span=node.span)  # type: ignore[arg-type]
        sym = Symbol(
            id=sym_id,
            name=node.name,
            kind=SymbolKind.ECHO,
            realm=self.raw.declared_realm,
            sigils=tuple(s.name for s in node.sigils) if node.sigils else tuple(node.type_params),
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

    def visit_seal_decl(self, node: SealDecl) -> None:
        """Register opaque newtype (seal)."""
        self._check_sigils(node.name, node.sigils)
        sym_id = SymbolId(module_path=self.path, span=node.span)  # type: ignore[arg-type]
        sym = Symbol(
            id=sym_id,
            name=node.name,
            kind=SymbolKind.SEAL,
            realm=self.raw.declared_realm,
            sigils=tuple(s.name for s in node.sigils) if node.sigils else tuple(node.type_params),
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

    def visit_omen_decl(self, node: OmenDecl) -> None:
        """Register scoped enumeration (omen or flags omen) and its variants."""
        sym_id = SymbolId(module_path=self.path, span=node.span)  # type: ignore[arg-type]
        sym = Symbol(
            id=sym_id,
            name=node.name,
            kind=SymbolKind.OMEN,
            realm=self.raw.declared_realm,
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

        # Process variants
        variants_table: dict[str, Symbol] = {}
        for v in node.variants:
            if v.name in variants_table:
                prev = variants_table[v.name]
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2203",
                        message=f"Duplicate variant '{v.name}' in omen '{node.name}'",
                        span=v.span,
                        source_file=self.path,
                        secondary_labels=(Label(span=prev.id.span, message="first declared here"),)
                        if prev.id.span
                        else (),
                    )
                )
            else:
                var_sym_id = SymbolId(module_path=self.path, span=v.span)  # type: ignore[arg-type]
                variants_table[v.name] = Symbol(
                    id=var_sym_id,
                    name=v.name,
                    kind=SymbolKind.OMEN_VARIANT,
                    realm=self.raw.declared_realm,
                    decl_node_id=NodeId(self.path, v.span) if v.span else None,
                )

            # Validate variant value
            if v.value is not None:
                if node.is_flags:
                    # Flags variant must be a power of two
                    val_int: int | None = None
                    if isinstance(v.value, (IntLit, HexLit)):
                        val_int = v.value.value

                    if val_int is None or val_int <= 0 or (val_int & (val_int - 1)) != 0:
                        self.raw.diagnostics.append(
                            Diagnostic(
                                code="E2216",
                                message=(
                                    f"Variant '{v.name}' in flags omen '{node.name}' must have a "
                                    f"power-of-two value (1, 2, 4, 8...), got '{v.value}'"
                                ),
                                span=v.value.span or v.span,
                                source_file=self.path,
                            )
                        )
                else:
                    # Standard omen variant must be an integer literal
                    if not isinstance(v.value, (IntLit, HexLit)):
                        self.raw.diagnostics.append(
                            Diagnostic(
                                code="E2215",
                                message=(
                                    f"Variant '{v.name}' in omen '{node.name}' has non-integer "
                                    f"literal value"
                                ),
                                span=v.value.span or v.span,
                                source_file=self.path,
                            )
                        )

        self.raw.omen_variants[node.name] = variants_table

    def visit_rune_decl(self, node: RuneDecl) -> None:
        """Register rune (struct) definition and its fields."""
        # Self-inheritance check (E2212)
        if node.parent is not None:
            parent_name = getattr(node.parent, "name", None)
            if parent_name == node.name:
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2212",
                        message=f"Rune '{node.name}' cannot inherit from itself (self-inheritance)",
                        span=node.parent.span or node.span,
                        source_file=self.path,
                    )
                )

        sigils_list = node.sigils if node.sigils else [SigilParam(name=p) for p in node.type_params]
        self._check_sigils(node.name, sigils_list)

        sym_id = SymbolId(module_path=self.path, span=node.span)  # type: ignore[arg-type]
        sym = Symbol(
            id=sym_id,
            name=node.name,
            kind=SymbolKind.RUNE,
            realm=self.raw.declared_realm,
            sigils=tuple(s.name for s in sigils_list),
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

        # Fields
        fields_table: dict[str, Symbol] = {}
        for f in node.fields:
            if f.name in fields_table:
                prev = fields_table[f.name]
                self.raw.diagnostics.append(
                    Diagnostic(
                        code="E2202",
                        message=f"Duplicate field '{f.name}' in rune '{node.name}'",
                        span=f.span,
                        source_file=self.path,
                        secondary_labels=(Label(span=prev.id.span, message="first declared here"),)
                        if prev.id.span
                        else (),
                    )
                )
            else:
                f_sym_id = SymbolId(module_path=self.path, span=f.span)  # type: ignore[arg-type]
                fields_table[f.name] = Symbol(
                    id=f_sym_id,
                    name=f.name,
                    kind=SymbolKind.FIELD,
                    realm=self.raw.declared_realm,
                    decl_node_id=NodeId(self.path, f.span) if f.span else None,
                )
        self.raw.rune_fields[node.name] = fields_table

        # Check constructor / destructor inside rune
        if node.constructor is not None:
            self._check_params(node.constructor.params)

    def visit_enchanting_decl(self, node: EnchantingDecl) -> None:
        """Register methods, operators, and lifecycle in an enchanting block."""
        target_name = getattr(node.target_type, "name", str(node.target_type))
        if node.span is not None:
            self.raw.enchanting_spans[target_name] = node.span
        elif node.target_type.span is not None:
            self.raw.enchanting_spans[target_name] = node.target_type.span
        methods_table = self.raw.rune_methods.setdefault(target_name, {})
        rune_fields = self.raw.rune_fields.get(target_name, {})

        seen_constructors: list[ConstructorDecl] = []
        seen_destructors: list[DestructorDecl] = []

        for m in node.members:
            if isinstance(m, MethodDecl):
                # Check collision with field (E2205)
                if m.name in rune_fields:
                    field_sym = rune_fields[m.name]
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2205",
                            message=(
                                f"Method '{m.name}' in enchanting '{target_name}' collides with "
                                f"rune field of the same name"
                            ),
                            span=m.span,
                            source_file=self.path,
                            secondary_labels=(
                                Label(
                                    span=field_sym.id.span,
                                    message="field declared here",
                                ),
                            )
                            if field_sym.id.span
                            else (),
                        )
                    )

                # Check duplicate method (E2204)
                if m.name in methods_table:
                    prev = methods_table[m.name]
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2204",
                            message=f"Duplicate method '{m.name}' in enchanting '{target_name}'",
                            span=m.span,
                            source_file=self.path,
                            secondary_labels=(
                                Label(span=prev.id.span, message="first declared here"),
                            )
                            if prev.id.span
                            else (),
                        )
                    )
                else:
                    self._check_params(m.function.params)
                    self._check_sigils(m.name, m.function.sigils)
                    m_sym_id = SymbolId(module_path=self.path, span=m.span)  # type: ignore[arg-type]
                    methods_table[m.name] = Symbol(
                        id=m_sym_id,
                        name=m.name,
                        kind=SymbolKind.METHOD,
                        realm=self.raw.declared_realm,
                        is_mut=m.is_mut,
                        is_unsafe=m.is_unsafe,
                        is_private=m.name.startswith("_"),
                        sigils=tuple(s.name for s in m.function.sigils),
                        decl_node_id=NodeId(self.path, m.span) if m.span else None,
                    )

            elif isinstance(m, OperatorDecl):
                # Check duplicate operator overload with identical symbol (E2208)
                op_key = f"op_{m.op}"
                if op_key in methods_table:
                    prev = methods_table[op_key]
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2208",
                            message=(
                                f"Duplicate operator '{m.op}' overload in enchanting "
                                f"'{target_name}'"
                            ),
                            span=m.span,
                            source_file=self.path,
                            secondary_labels=(
                                Label(span=prev.id.span, message="first declared here"),
                            )
                            if prev.id.span
                            else (),
                        )
                    )
                else:
                    self._check_params(m.function.params)
                    op_sym_id = SymbolId(module_path=self.path, span=m.span)  # type: ignore[arg-type]
                    methods_table[op_key] = Symbol(
                        id=op_sym_id,
                        name=m.op,
                        kind=SymbolKind.OPERATOR,
                        realm=self.raw.declared_realm,
                        is_mut=m.is_mut,
                        is_unsafe=m.is_unsafe,
                        decl_node_id=NodeId(self.path, m.span) if m.span else None,
                    )

            elif isinstance(m, ConstructorDecl):
                if seen_constructors:
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2206",
                            message=(
                                f"Multiple constructor declarations in rune/enchanting "
                                f"'{target_name}'"
                            ),
                            span=m.span,
                            source_file=self.path,
                        )
                    )
                else:
                    seen_constructors.append(m)
                    self._check_params(m.params)

            elif isinstance(m, DestructorDecl):
                if seen_destructors:
                    self.raw.diagnostics.append(
                        Diagnostic(
                            code="E2207",
                            message=(
                                f"Multiple destructor declarations in rune/enchanting "
                                f"'{target_name}'"
                            ),
                            span=m.span,
                            source_file=self.path,
                        )
                    )
                else:
                    seen_destructors.append(m)

    def visit_operator_decl(self, node: OperatorDecl) -> None:
        """Register free operator declaration."""
        op_sym_id = SymbolId(module_path=self.path, span=node.span)  # type: ignore[arg-type]
        self._check_params(node.function.params)
        sym = Symbol(
            id=op_sym_id,
            name=f"operator_{node.op}",
            kind=SymbolKind.FREE_OPERATOR,
            realm=self.raw.declared_realm,
            is_mut=node.is_mut,
            is_unsafe=node.is_unsafe,
            decl_node_id=NodeId(self.path, node.span) if node.span else None,
        )
        self._register_top_symbol(sym)

    def visit_assign(self, node: Assign) -> None:
        """Register top-level assignments (functions or global values)."""
        is_fn = isinstance(node.value, FunctionLiteral)

        for target in node.targets:
            if isinstance(target, VarTarget):
                name = target.name
                sym_id = SymbolId(module_path=self.path, span=target.span or node.span)  # type: ignore[arg-type]

                if is_fn:
                    fn_val: FunctionLiteral = node.value  # type: ignore[assignment]
                    self._check_sigils(name, fn_val.sigils)
                    self._check_params(fn_val.params)
                    sym = Symbol(
                        id=sym_id,
                        name=name,
                        kind=SymbolKind.FUNCTION,
                        realm=self.raw.declared_realm,
                        is_mut=node.is_mut,
                        is_unsafe=node.is_unsafe,
                        is_private=name.startswith("_"),
                        sigils=tuple(s.name for s in fn_val.sigils),
                        decl_node_id=NodeId(self.path, node.span) if node.span else None,
                    )
                else:
                    sym = Symbol(
                        id=sym_id,
                        name=name,
                        kind=SymbolKind.CONST,
                        realm=self.raw.declared_realm,
                        is_mut=node.is_mut,
                        is_unsafe=node.is_unsafe,
                        is_private=name.startswith("_"),
                        decl_node_id=NodeId(self.path, node.span) if node.span else None,
                    )

                self._register_top_symbol(sym)


def collect(module: Module, path: Path | str = "<stdin>") -> RawModuleDecl:
    """Convenience helper to run Pass 1 collection on a Module AST."""
    return Collector(path=path).collect(module)


__all__ = ["Collector", "RESERVED_KEYWORDS", "collect"]
