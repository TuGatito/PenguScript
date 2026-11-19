"""Unit tests for Analysis Sub-fase 3: Realm merging across files and visibility computation."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.imports import build_module_graph
from penguscript.analysis.realms import (
    analyze_realms_and_visibility,
    compute_visibility,
    merge_realms,
)

FIXTURES_REALMS_DIR = Path(__file__).parent.parent.parent / "fixtures" / "symbols" / "realms"


def test_reopened_realms_merging_good() -> None:
    """Test that multiple files declaring the same realm merge their symbols cleanly."""
    proj_root = FIXTURES_REALMS_DIR / "good"
    graph = build_module_graph(project_root=proj_root)
    assert graph.is_acyclic() is True

    realms, diags = merge_realms(modules=graph.modules, graph=graph)
    assert len(diags) == 0, [str(d) for d in diags]

    # Verify geometry realm has symbols merged from both circles.pengu and squares.pengu
    assert "geometry" in realms
    geom_table = realms["geometry"]
    assert "pi" in geom_table.symbols
    assert "circle_area" in geom_table.symbols
    assert "square_area" in geom_table.symbols

    # Verify by_path tracking
    circles_path = next(p for p in graph.modules if p.name == "circles.pengu")
    squares_path = next(p for p in graph.modules if p.name == "squares.pengu")
    assert "circle_area" in geom_table.by_path[circles_path]
    assert "square_area" in geom_table.by_path[squares_path]


def test_visibility_computation_good() -> None:
    """Test visible_realms and visible_symbols for plain and selective imports."""
    proj_root = FIXTURES_REALMS_DIR / "good"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(modules=graph.modules, graph=graph)

    annotated, diags = compute_visibility(modules=graph.modules, realms=realms, graph=graph)
    assert len(diags) == 0, [str(d) for d in diags]

    main_path = next(p for p in graph.modules if p.name == "main.pengu")
    main_mod = annotated[main_path]

    # Visible realms in main.pengu: its own realm ("app") and alias "geom" -> "geometry"
    assert main_mod.visible_realms["app"] == "app"
    assert main_mod.visible_realms["geom"] == "geometry"

    # Visible symbols in main.pengu: local "run_app" and selective import "sq_area"
    assert "run_app" in main_mod.visible_symbols
    assert "sq_area" in main_mod.visible_symbols
    assert main_mod.visible_symbols["sq_area"].name == "square_area"

    # Reopened realm files see their own realm symbols directly without prefix
    circles_path = next(p for p in graph.modules if p.name == "circles.pengu")
    circles_mod = annotated[circles_path]
    assert "circle_area" in circles_mod.visible_symbols
    assert "square_area" in circles_mod.visible_symbols


def test_cross_file_collision_e2201() -> None:
    """Two files declaring the same top-level symbol in the same realm must emit E2201."""
    proj_root = FIXTURES_REALMS_DIR / "bad" / "cross_collision"
    graph = build_module_graph(project_root=proj_root)

    realms, diags = merge_realms(modules=graph.modules, graph=graph)
    collision_diags = [d for d in diags if d.code == "E2201"]
    assert len(collision_diags) == 1

    diag = collision_diags[0]
    assert "Duplicate top-level symbol 'pi'" in diag.message
    assert len(diag.secondary_labels) == 1
    assert "first declared in" in diag.secondary_labels[0].message


def test_selective_import_not_found_e2003() -> None:
    """Selective import referencing non-existent symbol in target realm must emit E2003."""
    proj_root = FIXTURES_REALMS_DIR / "bad" / "selective_not_found"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(modules=graph.modules, graph=graph)

    annotated, diags = compute_visibility(modules=graph.modules, realms=realms, graph=graph)
    e2003_diags = [d for d in diags if d.code == "E2003"]
    assert len(e2003_diags) == 1
    assert "non_existent_func" in e2003_diags[0].message
    assert "math" in e2003_diags[0].message


def test_import_alias_collision_e2006() -> None:
    """Two imports binding the same local alias must emit E2006."""
    proj_root = FIXTURES_REALMS_DIR / "bad" / "alias_collision"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(modules=graph.modules, graph=graph)

    annotated, diags = compute_visibility(modules=graph.modules, realms=realms, graph=graph)
    e2006_diags = [d for d in diags if d.code == "E2006"]
    assert len(e2006_diags) >= 1
    assert "collision_alias" in e2006_diags[0].message


def test_enchanting_unknown_target_e2217() -> None:
    """Enchanting a target type not declared in the realm must emit E2217."""
    proj_root = FIXTURES_REALMS_DIR / "bad" / "enchanting_unknown"
    graph = build_module_graph(project_root=proj_root)

    realms, diags = merge_realms(modules=graph.modules, graph=graph)
    e2217_diags = [d for d in diags if d.code == "E2217"]
    assert len(e2217_diags) == 1
    assert "NonExistentRune" in e2217_diags[0].message


def test_analyze_realms_and_visibility_pipeline() -> None:
    """Test full analyze_realms_and_visibility orchestrator."""
    proj_root = FIXTURES_REALMS_DIR / "good"
    graph = build_module_graph(project_root=proj_root)

    realms, annotated, diags = analyze_realms_and_visibility(graph)
    assert len(diags) == 0
    assert len(realms) == 2  # geometry, app
    assert len(annotated) == 3  # circles, squares, main
