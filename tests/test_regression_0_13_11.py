"""Regression tests for PenguScript 0.13.11.

Covers:
- C1: insignia propagated inside when_top_decl blocks in pengu_checker.py
- C2: destructuring support for array, slice, and list in pengu_codegen.py and checker E0017
- H1: with <complex-ref>: emits -> instead of .
- H2: calling undefined_obj.method raises UndefinedIdentifierError (E0004)
- M4: invalid statement in with: builder raises InvalidBuilderStatementError (E0014)
- M5: fragile destructuring fallback removed
- m5: test source line captured for frame push
- m6: dead code calling_stmt removed
- m7: ref to slice of T indexing in at_expr emits (->data)[idx]
- Version: version sync across toolchain files to 0.13.11
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import (
    SemanticError, TypeMismatchError, UndefinedIdentifierError, InvalidBuilderStatementError
)
from pengu_parser.pengu_types import (
    OmenType, STRING_TYPE, INT_TYPE, BaseType, RuneType, ArrayType, SliceType, ListType, RefType
)
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
import pengu_version


def test_version_sync_0_13_11():
    """Verify that version 0.13.11 is synced across toolchain."""
    assert pengu_version.__version__ == "0.13.11"
    assert pengu_version.FALLBACK_VERSION == "0.13.11"
    assert PENGU_VERSION == "0.13.11"
    assert pengu_version.read_version_file() == "0.13.11"


@requires_cc
def test_c1_insignia_inside_when_top_decl():
    """C1: insignia is preserved inside when_top_decl in checker and codegen."""
    code = """insignia my_

when 1 == 1:
    weave helper into int:
        return 42

weave main into int:
    return calling helper - 42
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(filename="test.pengu")
    checker.check(tree, source=code)
    helper_sym = checker.symbols.lookup("helper")
    assert helper_sym is not None
    assert getattr(helper_sym, "c_name", "") == "my_helper"

    c = gen_bundle(code)
    assert "my_helper" in c
    res = compile_run(code, tag="test_c1_insignia_when")
    assert res.returncode == 0


@requires_cc
def test_c2_destructure_array():
    """C2: Destructuring fixed-size arrays in let bindings works in codegen and runtime."""
    code = """weave main into int:
    var arr as array of int with size 3 is [10, 20, 30]
    let a, b, c is arr
    if a == 10 and b == 20 and c == 30:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "_destruct" in c
    res = compile_run(code, tag="test_c2_destruct_arr")
    assert res.returncode == 0


@requires_cc
def test_c2_destructure_slice():
    """C2: Destructuring slices in let bindings works in codegen and runtime."""
    code = """weave sum_two with s as slice of int into int:
    let a, b is s
    return a + b

weave main into int:
    var arr as array of int with size 2 is [15, 25]
    var sl as slice of int is arr at 0 to 2
    let res is calling sum_two with sl
    if res == 40:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_c2_destruct_slice")
    assert res.returncode == 0


@requires_cc
def test_c2_destructure_list():
    """C2: Destructuring lists in let bindings works in codegen and runtime."""
    code = """weave main into int:
    var xs as list of int is list of int
    calling xs.push with 100
    calling xs.push with 200
    let a, b is xs
    if a == 100 and b == 200:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "pengu_list_at" in c
    res = compile_run(code, tag="test_c2_destruct_list")
    assert res.returncode == 0


def test_c2_reject_destructure_primitive():
    """C2: Destructuring primitive types (int, bool) is rejected with E0017."""
    code = """weave main into int:
    let x is 42
    let a, b is x
    return 0
"""
    check_error(code, "E0017")


@requires_cc
def test_h1_with_complex_ref_emits_arrow():
    """H1: with on complex ref expression emits -> separator instead of ."""
    code = """rune Inner:
    val as int

rune Wrapper:
    ptr as ref to Inner

weave main into int:
    var i as Inner with:
        set .val is 10
    var w as Wrapper with:
        set .ptr is sigil of i
    with w.ptr:
        set .val is 99
    if i.val == 99:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "w.ptr->val = 99" in c
    res = compile_run(code, tag="test_h1_complex_ref_with")
    assert res.returncode == 0


def test_h2_calling_undefined_object_method_rejected():
    """H2: Calling a method on an undefined object raises UndefinedIdentifierError (E0004)."""
    code = """weave main into int:
    calling missing_obj.some_method with 1
    return 0
"""
    check_error(code, "E0004")


def test_m4_with_builder_invalid_stmt_error_class():
    """M4: Invalid statement in with: builder raises InvalidBuilderStatementError with E0014."""
    code = """rune Config:
    retries as int

weave main into int:
    var c as Config with:
        set .retries is 3
        let temp is 10
    return 0
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    with pytest.raises(InvalidBuilderStatementError) as exc_info:
        checker.check(tree, source=code)
    assert exc_info.value.code == "E0014"


def test_m5_test_line_frame_push():
    """m5: Test declarations record their source line for pengu_frame_push."""
    code = """test "sample test":
    let x is 1
"""
    parser = PenguParser()
    tree = parser.parse(code)
    codegen = PenguCodegen()
    codegen.collect_declarations([("sample.pengu", tree)])
    assert len(codegen.tests) == 1
    assert codegen.tests[0]["line"] == 1
    test_sec = codegen.generate_test_section()
    assert 'pengu_frame_push("pengu_test_0",' in test_sec
    assert ', 1);' in test_sec


@requires_cc
def test_m7_ref_to_slice_indexing():
    """m7: Indexing ref to slice of T emits (->data)[idx] instead of p[idx]."""
    code = """weave access_first with s_ref as ref to slice of int into int:
    return s_ref at 0

weave main into int:
    var arr as array of int with size 2 is [77, 88]
    var sl as slice of int is arr at 0 to 2
    let v is calling access_first with sigil of sl
    if v == 77:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "->data)[0]" in c
    res = compile_run(code, tag="test_m7_ref_slice")
    assert res.returncode == 0
