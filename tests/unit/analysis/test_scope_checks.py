"""Unit tests for Analysis Sub-fase 5: Scope checks and warning diagnostics (W23xx)."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.collector import collect
from penguscript.analysis.realms import compute_visibility, merge_realms
from penguscript.analysis.resolver import resolve_module, resolve_project
from penguscript.analysis.scope_checks import check_module_scopes, check_project_scopes
from penguscript.frontend.ast_nodes import Module
from penguscript.frontend.parser import parse


def _pipeline_module(code: str, file_name: str = "test.pengu") -> list[str]:
    """Helper to run collector, realms, resolver, and scope checks on a snippet."""
    path = Path("/workspace") / file_name
    mod: Module = parse(code)
    raw = collect(mod, path)
    realms, _ = merge_realms({path: raw})
    annotated, _ = compute_visibility({path: raw}, realms, None)

    res = resolve_module(
        module=mod,
        module_path=path,
        annotated_module=annotated[path],
        realms=realms,
    )

    diags = check_module_scopes(
        module=mod,
        module_path=path,
        annotated_module=annotated[path],
        realms=realms,
        references=res.references,
        symbols_to_refs=res.symbols_to_refs,
        mutated_symbols=res.mutated_symbols,
    )
    return [d.code for d in diags]


def test_w2301_unused_local_variable() -> None:
    """Test W2301 is emitted for unused locals, but ignored for _prefixed names."""
    code = """realm test

test_func = () -> int
    unused_var = 10
    _allowed_unused = 20
    mut active = 5
    active = active + 1
    active
"""
    codes = _pipeline_module(code)
    assert "W2301" in codes
    assert codes.count("W2301") == 1  # Only unused_var, not _allowed_unused or active


def test_w2302_unused_parameter() -> None:
    """Test W2302 is emitted for unused formal parameters, except if _prefixed."""
    code = """realm test

calc = (used_param: int, unused_param: int, _ignored: int) -> int
    used_param + 10
"""
    codes = _pipeline_module(code)
    assert "W2302" in codes
    assert codes.count("W2302") == 1  # Only unused_param


def test_w2303_unused_realm_import() -> None:
    """Test W2303 is emitted when a plain imported realm is never referenced."""
    code = """realm test

invoke "std/math" as math

main = () -> int
    42
"""
    path = Path("/workspace/test.pengu")
    mod = parse(code)
    raw = collect(mod, path)
    realms, _ = merge_realms({path: raw})
    annotated, _ = compute_visibility({path: raw}, realms, None)

    # Mock 'math' in visible_realms
    ann = annotated[path]
    vis_realms = dict(ann.visible_realms)
    vis_realms["math"] = "math"
    from penguscript.analysis.symbols import ResolvedImport

    ann_with_math = ann.__class__(
        path=ann.path,
        declared_realm=ann.declared_realm,
        imports=(
            ResolvedImport(
                source_span=mod.declarations[1].span or raw.imports[0].span,  # type: ignore[arg-type]
                target_path=Path("std/math.pengu"),
                target_realm="math",
                kind="plain",
                local_alias="math",
            ),
        ),
        visible_realms=vis_realms,
        visible_symbols=ann.visible_symbols,
        local_symbols=ann.local_symbols,
    )

    res = resolve_module(mod, path, ann_with_math, realms)
    diags = check_module_scopes(
        module=mod,
        module_path=path,
        annotated_module=ann_with_math,
        realms=realms,
        references=res.references,
        symbols_to_refs=res.symbols_to_refs,
        mutated_symbols=res.mutated_symbols,
    )
    codes = [d.code for d in diags]
    assert "W2303" in codes


def test_w2304_unused_selective_import() -> None:
    """Test W2304 is emitted for selectively imported symbols that are never used."""
    code = """realm test

invoke {sqrt, pow} from "std/math"

compute = () -> double
    sqrt(16.0)
"""
    path = Path("/workspace/test.pengu")
    mod = parse(code)
    raw = collect(mod, path)
    realms, _ = merge_realms({path: raw})
    annotated, _ = compute_visibility({path: raw}, realms, None)

    from penguscript.analysis.symbols import ResolvedImport, Symbol, SymbolId, SymbolKind

    sqrt_sym = Symbol(
        id=SymbolId(Path("std/math.pengu"), mod.span or Path(".").stat()),  # type: ignore[arg-type]
        name="sqrt",
        kind=SymbolKind.FUNCTION,
        realm="math",
    )
    pow_sym = Symbol(
        id=SymbolId(Path("std/math.pengu"), mod.span or Path(".").stat()),  # type: ignore[arg-type]
        name="pow",
        kind=SymbolKind.FUNCTION,
        realm="math",
    )

    ann = annotated[path]
    vis_syms = dict(ann.visible_symbols)
    vis_syms["sqrt"] = sqrt_sym
    vis_syms["pow"] = pow_sym

    ann_mod = ann.__class__(
        path=ann.path,
        declared_realm=ann.declared_realm,
        imports=(
            ResolvedImport(
                source_span=mod.declarations[1].span or raw.imports[0].span,  # type: ignore[arg-type]
                target_path=Path("std/math.pengu"),
                target_realm="math",
                kind="selective",
                imported_symbols={"sqrt": sqrt_sym, "pow": pow_sym},
            ),
        ),
        visible_realms=ann.visible_realms,
        visible_symbols=vis_syms,
        local_symbols=ann.local_symbols,
    )

    res = resolve_module(mod, path, ann_mod, realms)
    diags = check_module_scopes(
        module=mod,
        module_path=path,
        annotated_module=ann_mod,
        realms=realms,
        references=res.references,
        symbols_to_refs=res.symbols_to_refs,
        mutated_symbols=res.mutated_symbols,
    )
    codes = [d.code for d in diags]
    assert "W2304" in codes


def test_w2305_private_symbol_access() -> None:
    """Test W2305 warning when accessing private _prefixed symbol from another file."""
    path_a = Path("/workspace/mod_a.pengu")
    path_b = Path("/workspace/mod_b.pengu")

    code_a = """realm shared

_internal_value = 100
"""
    code_b = """realm shared

get_value = () -> int
    _internal_value
"""
    mod_a = parse(code_a)
    mod_b = parse(code_b)

    raw_a = collect(mod_a, path_a)
    raw_b = collect(mod_b, path_b)

    realms, _ = merge_realms({path_a: raw_a, path_b: raw_b})
    annotated, _ = compute_visibility({path_a: raw_a, path_b: raw_b}, realms, None)

    proj_res = resolve_project({path_a: mod_a, path_b: mod_b}, annotated, realms)

    diags = check_project_scopes(
        modules={path_a: mod_a, path_b: mod_b},
        annotated_modules=annotated,
        realms=realms,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        mutated_symbols=proj_res.mutated_symbols,
    )
    codes = [d.code for d in diags]
    assert "W2305" in codes


def test_w2306_unmutated_mut_variable() -> None:
    """Test W2306 when mut variable is never reassigned or mutated."""
    code_unmutated = """realm test

test_func = () -> int
    mut x = 10
    x + 1
"""
    codes = _pipeline_module(code_unmutated)
    assert "W2306" in codes

    code_reassigned = """realm test

test_func = () -> int
    mut x = 10
    x = 20
    x
"""
    codes_reassigned = _pipeline_module(code_reassigned)
    assert "W2306" not in codes_reassigned

    code_compound = """realm test

test_func = () -> int
    mut x = 10
    x += 5
    x
"""
    codes_compound = _pipeline_module(code_compound)
    assert "W2306" not in codes_compound


def test_w2307_shadowing_variable_and_param() -> None:
    """Test W2307 when local variable or parameter shadows an outer symbol."""
    code = """realm test

global_func = () -> int
    42

test_func = (global_func: int) -> int
    global_func
"""
    codes = _pipeline_module(code)
    assert "W2307" in codes


def test_w2308_unused_constant_project_wide() -> None:
    """Test W2308 for unused top-level constant, except if _prefixed."""
    path = Path("/workspace/constants.pengu")
    code = """realm config

const unused_timeout = 5000
const _internal_timeout = 1000
const used_limit = 100

get_limit = () -> int
    used_limit
"""
    mod = parse(code)
    raw = collect(mod, path)
    realms, _ = merge_realms({path: raw})
    annotated, _ = compute_visibility({path: raw}, realms, None)

    proj_res = resolve_project({path: mod}, annotated, realms)
    diags = check_project_scopes(
        modules={path: mod},
        annotated_modules=annotated,
        realms=realms,
        references=proj_res.references,
        symbols_to_refs=proj_res.symbols_to_refs,
        mutated_symbols=proj_res.mutated_symbols,
    )
    codes = [d.code for d in diags]
    assert "W2308" in codes
    assert codes.count("W2308") == 1  # Only UNUSED_TIMEOUT, not _INTERNAL_TIMEOUT or USED_LIMIT
