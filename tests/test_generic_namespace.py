"""Tests for namespace-aware mangling of monomorphized generic functions (FASE 1 - 1.5)."""
import os
import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_project import resolve_imports


def _build_and_check(tmp_path, files):
    for rel_path, content in files.items():
        full_p = tmp_path / rel_path
        full_p.parent.mkdir(parents=True, exist_ok=True)
        full_p.write_text(content, encoding="utf-8")

    parser = PenguParser()
    order = resolve_imports(str(tmp_path), "main.pengu", parser)
    trees = []
    checker = PenguChecker(base_dir=str(tmp_path))
    for i, filepath in enumerate(order):
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(code)
        checker.check(
            tree, source=code, filename=filepath,
            reset_symbols=(i == 0), import_order=order,
        )
        trees.append((filepath, tree))

    assert len(checker.errors) == 0, f"Checker errors: {[str(e) for e in checker.errors]}"
    codegen = PenguCodegen(
        symbols=checker.symbols, import_order=order, base_dir=str(tmp_path)
    )
    codegen.collect_declarations(trees)
    c_code = codegen.generate_bundle()
    return checker, codegen, c_code


def test_cross_module_generic_function_namespacing(tmp_path):
    """Two modules export generic function 'wrap' with same name.

    Both must monomorphize with their respective module prefixes and not collide in C.
    """
    files = {
        "mod_a.pengu": """
weave wrap shard T with x as T into T:
    return x
""",
        "mod_b.pengu": """
weave wrap shard T with x as T into T:
    return x
""",
        "main.pengu": """
import mod_a
import mod_b

weave main into int:
    let a as int is calling mod_a.wrap with 42
    let b as int is calling mod_b.wrap with 100
    return a + b
""",
    }
    checker, codegen, c_code = _build_and_check(tmp_path, files)

    # Check that both monomorphized functions exist in symbols
    mono_keys = list(checker.symbols.monomorphized_functions.keys())
    assert any("mod_a_wrap" in k for k in mono_keys), f"mod_a_wrap not found in {mono_keys}"
    assert any("mod_b_wrap" in k for k in mono_keys), f"mod_b_wrap not found in {mono_keys}"

    # In C output, both distinct functions must be emitted and called
    assert "mod_a_wrap_int(42)" in c_code or "mod_a_wrap_int32(42)" in c_code
    assert "mod_b_wrap_int(100)" in c_code or "mod_b_wrap_int32(100)" in c_code


def test_cross_module_generic_different_types(tmp_path):
    """Module generic called with multiple types across modules."""
    files = {
        "helper.pengu": """
weave identity shard T with val as T into T:
    return val
""",
        "main.pengu": """
import helper

weave main into int:
    let i as int is calling helper.identity with 7
    let f as float is calling helper.identity with 3.14
    return i
""",
    }
    checker, codegen, c_code = _build_and_check(tmp_path, files)
    assert "helper_identity_int" in c_code or "helper_identity_int32" in c_code
    assert "helper_identity_float" in c_code
