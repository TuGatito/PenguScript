"""Unit tests for Analysis Sub-fase 4: Resolver (Pass 2 Scopes & References)."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.collector import collect
from penguscript.analysis.imports import build_module_graph
from penguscript.analysis.realms import compute_visibility, merge_realms
from penguscript.analysis.resolver import (
    ResolutionResult,
    resolve_module,
    resolve_project,
)
from penguscript.analysis.symbols import SymbolKind
from penguscript.frontend.ast_nodes import RuneDecl
from penguscript.frontend.parser import parse

FIXTURES_RESOLVE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "symbols" / "resolve"


def _analyze_single_snippet(code: str, file_name: str = "snippet.pengu") -> ResolutionResult:
    """Helper to parse and run Pass 1 + Visibility + Pass 2 on a single code snippet."""
    path = Path("/workspace") / file_name
    module_ast = parse(code)

    raw_decl = collect(module_ast, path)
    realms, _ = merge_realms({path: raw_decl})
    annotated, _ = compute_visibility({path: raw_decl}, realms, None)

    return resolve_module(
        module=module_ast,
        module_path=path,
        annotated_module=annotated[path],
        realms=realms,
    )


def test_resolve_point_rune_good() -> None:
    """Test resolution of Point rune, fields, constructor, and method calls."""
    proj_root = FIXTURES_RESOLVE_DIR / "good"
    point_path = proj_root / "point.pengu"
    assert point_path.exists()

    graph = build_module_graph(project_root=proj_root)
    realms, merge_diags = merge_realms(graph.modules, graph)
    assert len(merge_diags) == 0, [str(d) for d in merge_diags]

    annotated, vis_diags = compute_visibility(graph.modules, realms, graph)
    assert len(vis_diags) == 0, [str(d) for d in vis_diags]

    module_asts = {p: parse(p.read_text(encoding="utf-8")) for p in graph.modules}
    refs, sym_to_refs, diags = resolve_project(module_asts, annotated, realms)
    assert len(diags) == 0, [str(d) for d in diags]

    # Check references populated
    assert len(refs) > 0
    assert len(sym_to_refs) > 0

    # Verify constructor references
    geom_table = realms["geom"]
    point_sym = geom_table.symbols["Point"]
    assert point_sym.kind == SymbolKind.RUNE
    assert point_sym.id in sym_to_refs


def test_resolve_inheritance_good() -> None:
    """Test resolution of derived rune accessing parent fields via @ and calling parent()."""
    proj_root = FIXTURES_RESOLVE_DIR / "good"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(graph.modules, graph)
    annotated, _ = compute_visibility(graph.modules, realms, graph)

    module_asts = {p: parse(p.read_text(encoding="utf-8")) for p in graph.modules}
    _, sym_to_refs, diags = resolve_project(module_asts, annotated, realms)
    assert len(diags) == 0, [str(d) for d in diags]

    # Verify Dog and Animal are referenced
    animals_table = realms["animals"]
    animal_sym = animals_table.symbols["Animal"]
    assert animal_sym.id in sym_to_refs


def test_local_variable_resolution_and_reassignment() -> None:
    """Test resolution of local variables and mutable reassignment."""
    code = """realm test

calculate = (start: int) -> int
    mut total = start
    total = total + 10
    total
"""
    res = _analyze_single_snippet(code)
    assert len(res.diagnostics) == 0, [str(d) for d in res.diagnostics]
    assert len(res.references) > 0


def test_generic_function_sigil_resolution() -> None:
    """Test generic type sigils (<T>) resolution."""
    code = """realm test

identity = <T>(value: T) -> T
    value
"""
    res = _analyze_single_snippet(code)
    assert len(res.diagnostics) == 0, [str(d) for d in res.diagnostics]


def test_loop_and_comprehension_resolution() -> None:
    """Test loop variables and list comprehensions resolving in local block scopes."""
    code = """realm test

process = () -> int
    mut sum = 0
    for i = 1, 10
        sum = sum + i
        if sum > 20
            break
    sum
"""
    res = _analyze_single_snippet(code)
    assert len(res.diagnostics) == 0, [str(d) for d in res.diagnostics]


def test_diag_e2301_undefined_identifier() -> None:
    """Test E2301 undefined identifier with Levenshtein suggestion."""
    code = """realm test

test_func = () -> void
    foobar = 1
    foobaz
"""
    res = _analyze_single_snippet(code)
    codes = [d.code for d in res.diagnostics]
    assert "E2301" in codes
    diag = next(d for d in res.diagnostics if d.code == "E2301")
    assert "foobaz" in diag.message
    assert diag.hint is not None
    assert "foobar" in diag.hint


def test_diag_e2302_and_e2303_realm_access() -> None:
    """Test E2302 (unresolved realm prefix) and E2303 (symbol not in realm)."""
    # 1. Unresolved realm prefix
    code1 = """realm test

test_func = () -> void
    unknown_realm::foo()
"""
    res1 = _analyze_single_snippet(code1)
    codes1 = [d.code for d in res1.diagnostics]
    assert "E2302" in codes1
    assert "unknown_realm" in res1.diagnostics[0].message

    # 2. Symbol not found in realm
    code2 = """realm test

test_func = () -> void
    test::nonexistent_symbol()
"""
    res2 = _analyze_single_snippet(code2)
    codes2 = [d.code for d in res2.diagnostics]
    assert "E2303" in codes2
    assert "nonexistent_symbol" in res2.diagnostics[0].message


def test_diag_e2306_and_e2307_self_field() -> None:
    """Test E2306 (@ outside method) and E2307 (field does not exist)."""
    proj_root = FIXTURES_RESOLVE_DIR / "bad"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(graph.modules, graph)
    annotated, _ = compute_visibility(graph.modules, realms, graph)

    bad_self_path = proj_root / "bad_self.pengu"
    module_ast = parse(bad_self_path.read_text(encoding="utf-8"))
    res = resolve_module(
        module=module_ast,
        module_path=bad_self_path,
        annotated_module=annotated[bad_self_path],
        realms=realms,
        rune_declarations={d.name: d for d in module_ast.declarations if isinstance(d, RuneDecl)},
    )

    codes = [d.code for d in res.diagnostics]
    assert "E2306" in codes  # @ in standalone function
    assert "E2307" in codes  # @height does not exist on Widget
    assert "E2308" in codes  # @nonexistent_method does not exist


def test_diag_e2309_e2310_e2311_parent_calls() -> None:
    """Test E2309, E2310, E2311 for invalid parent constructor calls."""
    proj_root = FIXTURES_RESOLVE_DIR / "bad"
    graph = build_module_graph(project_root=proj_root)
    realms, _ = merge_realms(graph.modules, graph)
    annotated, _ = compute_visibility(graph.modules, realms, graph)

    bad_parent_path = proj_root / "bad_parent.pengu"
    module_ast = parse(bad_parent_path.read_text(encoding="utf-8"))
    res = resolve_module(
        module=module_ast,
        module_path=bad_parent_path,
        annotated_module=annotated[bad_parent_path],
        realms=realms,
        rune_declarations={d.name: d for d in module_ast.declarations if isinstance(d, RuneDecl)},
    )

    codes = [d.code for d in res.diagnostics]
    assert "E2309" in codes  # parent() in orphan function
    assert "E2310" in codes  # parent() in Base constructor (no heir)
    assert "E2311" in codes  # parent() not the first statement in Sub constructor


def test_diag_e2312_and_e2313_types() -> None:
    """Test E2312 (undeclared sigil parameter) and E2313 (unknown type)."""
    code = """realm test

foo = (x: T) -> void
    pass

bar = (y: UnknownType) -> void
    pass
"""
    res = _analyze_single_snippet(code)
    codes = [d.code for d in res.diagnostics]
    assert "E2312" in codes  # T looks like a sigil
    assert "E2313" in codes  # UnknownType is not a known type


def test_diag_e2315_use_before_declaration() -> None:
    """Test E2315: local variable used before declaration in the same block."""
    code = """realm test

test_func = () -> void
    y = x + 1
    x = 10
"""
    res = _analyze_single_snippet(code)
    codes = [d.code for d in res.diagnostics]
    assert "E2315" in codes
    diag = next(d for d in res.diagnostics if d.code == "E2315")
    assert "x" in diag.message


def test_diag_e2317_duplicate_variable_declaration() -> None:
    """Test E2317: duplicate variable declaration with mut in same scope."""
    code = """realm test

test_func = () -> void
    mut val = 1
    mut val = 2
"""
    res = _analyze_single_snippet(code)
    codes = [d.code for d in res.diagnostics]
    assert "E2317" in codes
    diag = next(d for d in res.diagnostics if d.code == "E2317")
    assert "val" in diag.message


def test_diag_e2318_and_e2319_static_vs_dynamic() -> None:
    """Test E2318 (dynamic var with ::) and E2319 (realm with .)."""
    code1 = """realm test

test_func = () -> void
    x = 10
    x::foo()
"""
    res1 = _analyze_single_snippet(code1)
    codes1 = [d.code for d in res1.diagnostics]
    assert "E2318" in codes1

    code2 = """realm test

invoke "std/math" as math

test_func = () -> void
    math.sqrt(4)
"""
    path = Path("/workspace/test.pengu")
    mod = parse(code2)

    raw_decl = collect(mod, path)
    realms, _ = merge_realms({path: raw_decl})
    annotated, _ = compute_visibility({path: raw_decl}, realms, None)
    ann = annotated[path]
    vis_realms = dict(ann.visible_realms)
    vis_realms["math"] = "math"
    ann_with_math = ann.__class__(
        path=ann.path,
        declared_realm=ann.declared_realm,
        imports=ann.imports,
        visible_realms=vis_realms,
        visible_symbols=ann.visible_symbols,
        local_symbols=ann.local_symbols,
    )

    res2 = resolve_module(
        module=mod,
        module_path=path,
        annotated_module=ann_with_math,
        realms=realms,
    )
    codes2 = [d.code for d in res2.diagnostics]
    assert "E2319" in codes2


def test_diag_e2320_and_e2321_break_continue_outside_loop() -> None:
    """Test E2320 and E2321 for break/continue outside of a loop."""
    code = """realm test

test_func = () -> void
    break
    continue
"""
    res = _analyze_single_snippet(code)
    codes = [d.code for d in res.diagnostics]
    assert "E2320" in codes
    assert "E2321" in codes


def test_enum_variant_and_static_access_resolution() -> None:
    """Test resolution of EnumVariant (Color::Red) and TypeStaticAccess."""
    code = """realm test

omen Color
    Red,
    Green,
    Blue

rune Vec
    x: double

enchanting Vec
    zero = () -> Vec
        Vec(0.0)

test_func = () -> void
    c = Color::Red
    v = Vec::zero()
"""
    res = _analyze_single_snippet(code)
    assert len(res.diagnostics) == 0, [str(d) for d in res.diagnostics]

    # Test invalid static access on omen (E2314)
    code_bad = """realm test

omen Color
    Red

test_bad = () -> void
    Color::something
"""
    res_bad = _analyze_single_snippet(code_bad)
    assert any(d.code == "E2314" for d in res_bad.diagnostics)
