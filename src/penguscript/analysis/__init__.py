"""PenguScript analysis, symbol resolution, and type checking package."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.collector import Collector, collect
from penguscript.analysis.diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
    Label,
    Suggestion,
    format_analysis_diagnostic,
)
from penguscript.analysis.imports import (
    ModuleGraph,
    ModuleGraphBuilder,
    build_module_graph,
    resolve_import_path,
)
from penguscript.analysis.prelude import (
    BUILTIN_CONSTANTS,
    BUILTIN_PRIMITIVES,
    get_prelude_scope,
    get_prelude_symbols,
)
from penguscript.analysis.realms import (
    analyze_realms_and_visibility,
    compute_visibility,
    merge_realms,
)
from penguscript.analysis.resolver import (
    ProjectResolutionResult,
    ResolutionResult,
    Resolver,
    resolve_module,
    resolve_project,
)
from penguscript.analysis.scope_checks import (
    ShadowingAndLoopChecker,
    check_module_scopes,
    check_project_scopes,
)
from penguscript.analysis.symbols import (
    AnnotatedModule,
    AnnotatedProject,
    NodeId,
    RawModuleDecl,
    RealmSymbolTable,
    ResolvedImport,
    Scope,
    ScopeKind,
    Symbol,
    SymbolId,
    SymbolKind,
)
from penguscript.analysis.visitor import ASTVisitor
from penguscript.frontend.ast_nodes import Module
from penguscript.frontend.parser import parse


def analyze_project(
    project_root: Path | str,
    std_root: Path | None = None,
) -> AnnotatedProject:
    """Analyze an entire PenguScript project directory or file entry-point."""
    target = Path(project_root).resolve()
    entry_points: list[Path] | None = None

    if target.is_file():
        entry_points = [target]
        root = target.parent
        cur = target.parent
        while cur != cur.parent:
            if (cur / "pengu.toml").is_file():
                root = cur
                break
            cur = cur.parent
    else:
        root = target

    # 1. Build module dependency graph (Pass 1 & imports)
    graph = build_module_graph(
        project_root=root,
        std_root=std_root,
        entry_points=entry_points,
    )
    all_diagnostics: list[Diagnostic] = list(graph.diagnostics)

    # 2. Merge realms across files
    realms, merge_diags = merge_realms(graph.modules, graph)
    all_diagnostics.extend(merge_diags)

    # 3. Compute visibility per module
    annotated_modules, vis_diags = compute_visibility(graph.modules, realms, graph)
    all_diagnostics.extend(vis_diags)

    # 4. Parse AST for each module
    parsed_modules: dict[Path, Module] = {}
    for p in graph.modules:
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8")
                parsed_modules[p] = parse(text)
            except Exception as e:
                all_diagnostics.append(
                    Diagnostic(
                        code="E1000",
                        message=f"Syntax error in '{p.name}': {e}",
                        source_file=p,
                    )
                )

    # 5. Pass 2: Resolver (scopes and reference binding)
    proj_res = resolve_project(parsed_modules, annotated_modules, realms)
    all_diagnostics.extend(proj_res.diagnostics)

    # 6. Scope and lint checks (warnings W23xx and loop checks)
    scope_diags = check_project_scopes(
        modules=parsed_modules,
        annotated_modules=annotated_modules,
        realms=realms,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        mutated_symbols=proj_res.mutated_symbols,
    )
    all_diagnostics.extend(scope_diags)

    # 7. Sort diagnostics deterministically by (path, line, col, code)
    sorted_diags = sorted(
        all_diagnostics,
        key=lambda d: (
            str(d.source_file or ""),
            d.span.line if d.span else 0,
            d.span.col if d.span else 0,
            d.code,
        ),
    )

    return AnnotatedProject(
        realms=realms,
        modules=annotated_modules,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        diagnostics=sorted_diags,
    )


def analyze_text(
    code: str,
    filename: str = "snippet.pengu",
) -> AnnotatedProject:
    """Analyze a single in-memory code snippet."""
    path = Path("/workspace") / filename
    try:
        mod = parse(code)
    except Exception as e:
        diag = Diagnostic(
            code="E1000",
            message=f"Syntax error: {e}",
            source_file=path,
        )
        return AnnotatedProject(
            realms={},
            modules={},
            references={},
            symbols_to_refs={},
            diagnostics=[diag],
        )

    raw = collect(mod, path)
    realms, merge_diags = merge_realms({path: raw})
    annotated, vis_diags = compute_visibility({path: raw}, realms, None)

    proj_res = resolve_project({path: mod}, annotated, realms)
    scope_diags = check_project_scopes(
        modules={path: mod},
        annotated_modules=annotated,
        realms=realms,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        mutated_symbols=proj_res.mutated_symbols,
    )

    all_diags = list(raw.diagnostics) + merge_diags + vis_diags + proj_res.diagnostics + scope_diags
    sorted_diags = sorted(
        all_diags,
        key=lambda d: (
            str(d.source_file or ""),
            d.span.line if d.span else 0,
            d.span.col if d.span else 0,
            d.code,
        ),
    )

    return AnnotatedProject(
        realms=realms,
        modules=annotated,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        diagnostics=sorted_diags,
    )


__all__ = [
    "ASTVisitor",
    "AnnotatedModule",
    "AnnotatedProject",
    "BUILTIN_CONSTANTS",
    "BUILTIN_PRIMITIVES",
    "Collector",
    "Diagnostic",
    "DiagnosticSeverity",
    "Label",
    "ModuleGraph",
    "ModuleGraphBuilder",
    "NodeId",
    "ProjectResolutionResult",
    "RawModuleDecl",
    "RealmSymbolTable",
    "ResolutionResult",
    "ResolvedImport",
    "Resolver",
    "Scope",
    "ScopeKind",
    "ShadowingAndLoopChecker",
    "Suggestion",
    "Symbol",
    "SymbolId",
    "SymbolKind",
    "analyze_project",
    "analyze_realms_and_visibility",
    "analyze_text",
    "build_module_graph",
    "check_module_scopes",
    "check_project_scopes",
    "collect",
    "compute_visibility",
    "format_analysis_diagnostic",
    "get_prelude_scope",
    "get_prelude_symbols",
    "merge_realms",
    "resolve_import_path",
    "resolve_module",
    "resolve_project",
]
