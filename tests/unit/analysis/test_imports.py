"""Unit tests for Analysis Sub-fase 2: Module graph, import resolution, and cycle detection."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.imports import (
    build_module_graph,
    resolve_import_path,
)

FIXTURES_IMPORTS_DIR = Path(__file__).parent.parent.parent / "fixtures" / "symbols" / "imports"


def test_resolve_import_path_good() -> None:
    """Test resolving project-relative and bare module paths."""
    proj_root = FIXTURES_IMPORTS_DIR / "good"
    main_file = proj_root / "src" / "main.pengu"

    # Bare path to index module
    math_resolved, diag1 = resolve_import_path("math", from_file=main_file, project_root=proj_root)
    assert diag1 is None
    assert math_resolved is not None
    assert math_resolved.name == "index.pengu"
    assert math_resolved.parent.name == "math"

    # Submodule path
    geom_resolved, diag2 = resolve_import_path(
        "math/geometry", from_file=main_file, project_root=proj_root
    )
    assert diag2 is None
    assert geom_resolved is not None
    assert geom_resolved.name == "geometry.pengu"

    # Relative path from index.pengu to geometry.pengu
    index_file = proj_root / "src" / "math" / "index.pengu"
    rel_resolved, diag3 = resolve_import_path(
        "./geometry", from_file=index_file, project_root=proj_root
    )
    assert diag3 is None
    assert rel_resolved is not None
    assert rel_resolved.name == "geometry.pengu"


def test_resolve_import_path_empty_e2004() -> None:
    """Empty import path must emit E2004."""
    proj_root = FIXTURES_IMPORTS_DIR / "bad" / "empty"
    file = proj_root / "empty.pengu"

    resolved, diag = resolve_import_path("", from_file=file, project_root=proj_root)
    assert resolved is None
    assert diag is not None
    assert diag.code == "E2004"


def test_resolve_import_path_escape_e2005() -> None:
    """Relative import escaping project root must emit E2005."""
    proj_root = FIXTURES_IMPORTS_DIR / "bad" / "escape"
    file = proj_root / "sub" / "escape.pengu"

    resolved, diag = resolve_import_path(
        "../../../../../../../outside", from_file=file, project_root=proj_root
    )
    assert resolved is None
    assert diag is not None
    assert diag.code == "E2005"


def test_resolve_import_path_missing_e2001() -> None:
    """Non-existent import target must emit E2001."""
    proj_root = FIXTURES_IMPORTS_DIR / "bad" / "not_found"
    file = proj_root / "missing.pengu"

    resolved, diag = resolve_import_path(
        "non_existent_module", from_file=file, project_root=proj_root
    )
    assert resolved is None
    assert diag is not None
    assert diag.code == "E2001"


def test_build_module_graph_good_project() -> None:
    """Test graph construction, dependency edges, and topological order on valid project."""
    proj_root = FIXTURES_IMPORTS_DIR / "good"
    graph = build_module_graph(project_root=proj_root)

    assert graph.is_acyclic() is True
    assert len(graph.diagnostics) == 0, [str(d) for d in graph.diagnostics]

    # Verify all 3 modules were loaded
    names = {p.name for p in graph.modules}
    assert names == {"geometry.pengu", "index.pengu", "main.pengu"}

    # Find the specific paths
    geom_path = next(p for p in graph.modules if p.name == "geometry.pengu")
    index_path = next(p for p in graph.modules if p.name == "index.pengu")
    main_path = next(p for p in graph.modules if p.name == "main.pengu")

    # Verify dependency edges
    assert geom_path in graph.dependencies[index_path]
    assert index_path in graph.dependencies[main_path]
    assert geom_path in graph.dependencies[main_path]

    # Verify reverse dependents
    assert index_path in graph.dependents[geom_path]
    assert main_path in graph.dependents[geom_path]
    assert main_path in graph.dependents[index_path]

    # Verify topological order: geometry must come before index, and index before main
    order = graph.topological_order
    assert order.index(geom_path) < order.index(index_path)
    assert order.index(index_path) < order.index(main_path)


def test_build_module_graph_cycle_e2002() -> None:
    """Test cycle detection across 3 modules (a -> b -> c -> a)."""
    proj_root = FIXTURES_IMPORTS_DIR / "bad" / "cycle"
    graph = build_module_graph(project_root=proj_root)

    assert graph.is_acyclic() is False
    cycle_diags = [d for d in graph.diagnostics if d.code == "E2002"]
    assert len(cycle_diags) >= 1

    diag = cycle_diags[0]
    assert "Import cycle detected" in diag.message
    # Check that secondary labels document the chain
    assert len(diag.secondary_labels) > 0


def test_build_module_graph_self_import_e2008() -> None:
    """Test self-import detection emitting E2008."""
    proj_root = FIXTURES_IMPORTS_DIR / "bad" / "self_import"
    graph = build_module_graph(project_root=proj_root)

    self_diags = [d for d in graph.diagnostics if d.code == "E2008"]
    assert len(self_diags) == 1
    assert "cannot import itself" in self_diags[0].message


def test_build_module_graph_missing_and_empty() -> None:
    """Test diagnostics propagation for missing and empty imports in graph."""
    proj_missing = FIXTURES_IMPORTS_DIR / "bad" / "not_found"
    graph_missing = build_module_graph(project_root=proj_missing)
    assert any(d.code == "E2001" for d in graph_missing.diagnostics)

    proj_empty = FIXTURES_IMPORTS_DIR / "bad" / "empty"
    graph_empty = build_module_graph(project_root=proj_empty)
    assert any(d.code == "E2004" for d in graph_empty.diagnostics)
