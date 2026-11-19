"""Realm merging across files and module visibility computation."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from penguscript.analysis.diagnostics import Diagnostic, Label
from penguscript.analysis.imports import ModuleGraph
from penguscript.analysis.symbols import (
    AnnotatedModule,
    RawModuleDecl,
    RealmSymbolTable,
    ResolvedImport,
    Symbol,
    SymbolKind,
)
from penguscript.frontend.span import Span


def merge_realms(
    modules: dict[Path, RawModuleDecl],
    graph: ModuleGraph | None = None,
) -> tuple[dict[str, RealmSymbolTable], list[Diagnostic]]:
    """Merge symbol declarations from all modules belonging to the same realm.

    Detects cross-file collisions (E2201, E2202, E2204) and invalid enchanting
    targets (E2217).
    """
    diagnostics: list[Diagnostic] = []

    # Intermediate mutable tables per realm
    realm_symbols: dict[str, dict[str, Symbol]] = {}
    realm_fields: dict[str, dict[str, dict[str, Symbol]]] = {}
    realm_methods: dict[str, dict[str, dict[str, Symbol]]] = {}
    realm_variants: dict[str, dict[str, dict[str, Symbol]]] = {}
    realm_by_path: dict[str, dict[Path, set[str]]] = {}
    realm_enchantings: dict[str, dict[str, tuple[Path, Span]]] = {}

    # Order of processing: topological if graph available, else sorted paths
    order = (
        [p for p in graph.topological_order if p in modules]
        if graph is not None
        else sorted(modules.keys())
    )
    # Include any modules not in topological order
    for p in sorted(modules.keys()):
        if p not in order:
            order.append(p)

    for mod_path in order:
        raw = modules[mod_path]
        realm_name = raw.declared_realm

        symbols_map = realm_symbols.setdefault(realm_name, {})
        fields_map = realm_fields.setdefault(realm_name, {})
        methods_map = realm_methods.setdefault(realm_name, {})
        variants_map = realm_variants.setdefault(realm_name, {})
        by_path_map = realm_by_path.setdefault(realm_name, {})
        enchanting_map = realm_enchantings.setdefault(realm_name, {})

        by_path_map.setdefault(mod_path, set())

        # 1. Merge top-level symbols and detect cross-file collisions (E2201)
        for sym_name, sym in raw.symbols.items():
            if sym_name in symbols_map:
                existing = symbols_map[sym_name]
                if existing.id.module_path != mod_path:
                    prev_label = (
                        Label(
                            span=existing.id.span,
                            message=f"first declared in '{existing.id.module_path.name}'",
                        )
                        if existing.id.span
                        else None
                    )
                    diagnostics.append(
                        Diagnostic(
                            code="E2201",
                            message=(
                                f"Duplicate top-level symbol '{sym_name}' in realm '{realm_name}'"
                            ),
                            span=sym.id.span,
                            source_file=mod_path,
                            secondary_labels=(prev_label,) if prev_label else (),
                            notes=(
                                "Realms merge across files; rename one of the declarations or "
                                "use distinct realms",
                            ),
                        )
                    )
            else:
                symbols_map[sym_name] = sym
                by_path_map[mod_path].add(sym_name)

        # 2. Merge rune fields and detect cross-file collisions (E2202)
        for rune_name, fields in raw.rune_fields.items():
            target_fields = fields_map.setdefault(rune_name, {})
            for f_name, f_sym in fields.items():
                if f_name in target_fields:
                    existing_f = target_fields[f_name]
                    if existing_f.id.module_path != mod_path:
                        prev_label = (
                            Label(
                                span=existing_f.id.span,
                                message=f"first declared in '{existing_f.id.module_path.name}'",
                            )
                            if existing_f.id.span
                            else None
                        )
                        diagnostics.append(
                            Diagnostic(
                                code="E2202",
                                message=(
                                    f"Duplicate field '{f_name}' in rune '{rune_name}' across "
                                    "reopened realm files"
                                ),
                                span=f_sym.id.span,
                                source_file=mod_path,
                                secondary_labels=(prev_label,) if prev_label else (),
                            )
                        )
                else:
                    target_fields[f_name] = f_sym

        # 3. Merge rune methods and detect cross-file collisions (E2204)
        for rune_name, methods in raw.rune_methods.items():
            target_methods = methods_map.setdefault(rune_name, {})
            for m_name, m_sym in methods.items():
                if m_name in target_methods:
                    existing_m = target_methods[m_name]
                    if existing_m.id.module_path != mod_path:
                        prev_label = (
                            Label(
                                span=existing_m.id.span,
                                message=f"first declared in '{existing_m.id.module_path.name}'",
                            )
                            if existing_m.id.span
                            else None
                        )
                        diagnostics.append(
                            Diagnostic(
                                code="E2204",
                                message=(
                                    f"Duplicate method '{m_name}' in enchanting '{rune_name}' "
                                    "across reopened realm files"
                                ),
                                span=m_sym.id.span,
                                source_file=mod_path,
                                secondary_labels=(prev_label,) if prev_label else (),
                            )
                        )
                else:
                    target_methods[m_name] = m_sym

        # 4. Merge omen variants and detect cross-file collisions (E2203)
        for omen_name, variants in raw.omen_variants.items():
            target_vars = variants_map.setdefault(omen_name, {})
            for v_name, v_sym in variants.items():
                if v_name in target_vars:
                    existing_v = target_vars[v_name]
                    if existing_v.id.module_path != mod_path:
                        prev_label = (
                            Label(
                                span=existing_v.id.span,
                                message=f"first declared in '{existing_v.id.module_path.name}'",
                            )
                            if existing_v.id.span
                            else None
                        )
                        diagnostics.append(
                            Diagnostic(
                                code="E2203",
                                message=(
                                    f"Duplicate variant '{v_name}' in omen '{omen_name}' across "
                                    "reopened realm files"
                                ),
                                span=v_sym.id.span,
                                source_file=mod_path,
                                secondary_labels=(prev_label,) if prev_label else (),
                            )
                        )
                else:
                    target_vars[v_name] = v_sym

        # Record enchanting locations for post-validation
        for target_name, enc_span in raw.enchanting_spans.items():
            enchanting_map[target_name] = (mod_path, enc_span)

    # Validate enchanting blocks: target type must exist in realm (E2217)
    valid_type_kinds = (
        SymbolKind.RUNE,
        SymbolKind.OMEN,
        SymbolKind.SEAL,
        SymbolKind.ECHO,
        SymbolKind.BUILTIN_TYPE,
    )
    for realm_name, enc_dict in realm_enchantings.items():
        sym_dict = realm_symbols.get(realm_name, {})
        for target_name, (file_path, enc_span) in enc_dict.items():
            if target_name not in sym_dict:
                diagnostics.append(
                    Diagnostic(
                        code="E2217",
                        message=(
                            f"Enchanting target type '{target_name}' is not declared in realm "
                            f"'{realm_name}'"
                        ),
                        span=enc_span,
                        source_file=file_path,
                        hint=f"Declare 'rune {target_name}' or 'omen {target_name}' in this realm",
                    )
                )
            elif sym_dict[target_name].kind not in valid_type_kinds:
                diagnostics.append(
                    Diagnostic(
                        code="E2217",
                        message=(
                            f"Enchanting target '{target_name}' is not a type (it is a "
                            f"{sym_dict[target_name].kind.name.lower()})"
                        ),
                        span=enc_span,
                        source_file=file_path,
                    )
                )

    # Freeze into immutable RealmSymbolTable instances
    realms: dict[str, RealmSymbolTable] = {}
    for realm_name, syms in realm_symbols.items():
        fields_frozen = {
            r: MappingProxyType(f) for r, f in realm_fields.get(realm_name, {}).items()
        }
        methods_frozen = {
            r: MappingProxyType(m) for r, m in realm_methods.get(realm_name, {}).items()
        }
        variants_frozen = {
            o: MappingProxyType(v) for o, v in realm_variants.get(realm_name, {}).items()
        }
        by_path_frozen = {p: frozenset(s) for p, s in realm_by_path.get(realm_name, {}).items()}

        realms[realm_name] = RealmSymbolTable(
            name=realm_name,
            symbols=MappingProxyType(syms),
            rune_fields=MappingProxyType(fields_frozen),
            rune_methods=MappingProxyType(methods_frozen),
            omen_variants=MappingProxyType(variants_frozen),
            by_path=MappingProxyType(by_path_frozen),
        )

    return realms, diagnostics


def compute_visibility(
    modules: dict[Path, RawModuleDecl],
    realms: dict[str, RealmSymbolTable],
    graph: ModuleGraph | None = None,
) -> tuple[dict[Path, AnnotatedModule], list[Diagnostic]]:
    """Compute visible realms and visible symbols for each module.

    Emits E2003 (selective import symbol not found) and E2006 (alias collision).
    """
    diagnostics: list[Diagnostic] = []
    annotated: dict[Path, AnnotatedModule] = {}

    for mod_path, raw in modules.items():
        declared_realm = raw.declared_realm
        visible_realms: dict[str, str] = {declared_realm: declared_realm}
        visible_symbols: dict[str, Symbol] = {}
        resolved_imports: list[ResolvedImport] = []

        # 1. Populate symbols belonging to this file's realm
        realm_table = realms.get(declared_realm)
        if realm_table is not None:
            for s_name, sym in realm_table.symbols.items():
                visible_symbols[s_name] = sym

        # 2. Process each invoke declaration
        for invoke in raw.imports:
            if graph is None:
                continue

            # Find the target module in graph edges
            target_path: Path | None = None
            for dep in graph.dependencies.get(mod_path, []):
                inv_node = graph.import_nodes.get((mod_path, dep))
                if inv_node is not None and inv_node == invoke:
                    target_path = dep
                    break

            # If not matched directly, check by target filename/stem
            if target_path is None:
                for dep in graph.dependencies.get(mod_path, []):
                    clean_inv = invoke.path.strip()
                    if dep.stem == clean_inv or dep.parent.name == clean_inv:
                        target_path = dep
                        break

            if target_path is None or target_path not in modules:
                # Import errors (E2001, E2004, etc.) are already recorded in graph
                continue

            target_raw = modules[target_path]
            target_realm = target_raw.declared_realm
            target_table = realms.get(target_realm)

            if invoke.symbols:
                # Selective import: invoke {format as fmt, println} from "std/fmt"
                imported_map: dict[str, Symbol] = {}

                for item in invoke.symbols:
                    src_name = item.name
                    visible_name = item.alias if item.alias is not None else item.name

                    if target_table is None or src_name not in target_table.symbols:
                        # E2003: Symbol not found in imported realm
                        notes: tuple[str, ...] = ()
                        if target_table is not None and target_table.symbols:
                            avail = ", ".join(sorted(target_table.symbols.keys()))
                            notes = (f"Available symbols in realm '{target_realm}': {avail}",)

                        diagnostics.append(
                            Diagnostic(
                                code="E2003",
                                message=(
                                    f"Symbol '{src_name}' not found in imported realm "
                                    f"'{target_realm}'"
                                ),
                                span=item.span or invoke.span,
                                source_file=mod_path,
                                notes=notes,
                            )
                        )
                    else:
                        target_sym = target_table.symbols[src_name]

                        # Check collision in visible_symbols (E2006)
                        if visible_name in visible_symbols:
                            existing = visible_symbols[visible_name]
                            prev_label = (
                                Label(
                                    span=existing.id.span,
                                    message="already visible from here",
                                )
                                if existing.id.span
                                else None
                            )
                            diagnostics.append(
                                Diagnostic(
                                    code="E2006",
                                    message=(
                                        f"Imported symbol '{visible_name}' collides with "
                                        "an already visible symbol"
                                    ),
                                    span=item.span or invoke.span,
                                    source_file=mod_path,
                                    secondary_labels=(prev_label,) if prev_label else (),
                                )
                            )
                        else:
                            visible_symbols[visible_name] = target_sym
                            imported_map[visible_name] = target_sym

                resolved_imports.append(
                    ResolvedImport(
                        source_span=invoke.span or Span(0, 0, 1, 1),
                        target_path=target_path,
                        target_realm=target_realm,
                        kind="selective",
                        local_alias=None,
                        imported_symbols=MappingProxyType(imported_map),
                    )
                )

            else:
                # Plain import: invoke "math" [as alias]
                local_alias = invoke.alias if invoke.alias is not None else target_realm

                # Check alias collision (E2006)
                if local_alias in visible_realms and visible_realms[local_alias] != target_realm:
                    diagnostics.append(
                        Diagnostic(
                            code="E2006",
                            message=(
                                f"Import alias '{local_alias}' collides with an already visible "
                                f"realm '{visible_realms[local_alias]}'"
                            ),
                            span=invoke.span,
                            source_file=mod_path,
                        )
                    )
                elif local_alias in raw.symbols:
                    sym = raw.symbols[local_alias]
                    prev_label = (
                        Label(
                            span=sym.id.span,
                            message="local symbol declared here",
                        )
                        if sym.id.span
                        else None
                    )
                    diagnostics.append(
                        Diagnostic(
                            code="E2006",
                            message=(
                                f"Import alias '{local_alias}' collides with a locally declared "
                                "symbol"
                            ),
                            span=invoke.span,
                            source_file=mod_path,
                            secondary_labels=(prev_label,) if prev_label else (),
                        )
                    )
                else:
                    visible_realms[local_alias] = target_realm

                resolved_imports.append(
                    ResolvedImport(
                        source_span=invoke.span or Span(0, 0, 1, 1),
                        target_path=target_path,
                        target_realm=target_realm,
                        kind="plain",
                        local_alias=invoke.alias,
                        imported_symbols=MappingProxyType({}),
                    )
                )

        annotated[mod_path] = AnnotatedModule(
            path=mod_path,
            declared_realm=declared_realm,
            imports=tuple(resolved_imports),
            visible_realms=MappingProxyType(visible_realms),
            visible_symbols=MappingProxyType(visible_symbols),
            local_symbols=MappingProxyType(raw.symbols),
        )

    return annotated, diagnostics


def analyze_realms_and_visibility(
    graph: ModuleGraph,
) -> tuple[dict[str, RealmSymbolTable], dict[Path, AnnotatedModule], list[Diagnostic]]:
    """Convenience pipeline to merge realms and compute visibility from a ModuleGraph."""
    all_diags: list[Diagnostic] = list(graph.diagnostics)

    realms, merge_diags = merge_realms(modules=graph.modules, graph=graph)
    all_diags.extend(merge_diags)

    annotated, vis_diags = compute_visibility(modules=graph.modules, realms=realms, graph=graph)
    all_diags.extend(vis_diags)

    return realms, annotated, all_diags


__all__ = [
    "analyze_realms_and_visibility",
    "compute_visibility",
    "merge_realms",
]
