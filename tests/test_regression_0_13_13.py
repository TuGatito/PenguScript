"""Regression tests for PenguScript 0.13.13.

Covers:
- C5 & m12: _infer_node_type scope isolation, cleanup, and no redundant define("self")
- C6: Destructuring of array literals and 2D arrays produces valid C99
- H4: in / not in over arrays and lists of strings and structs uses string/memcmp equality
- M8: Detection of tail if_stmt / unless_stmt without returns in non-void weaves (E0020)
- M9: Omen variant payload expected type propagation in struct_init
- m13: Deep RefType/FrozenType unwrapping in _frozen_write_block
- Version: version sync across toolchain files to 0.13.13
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import (
    SemanticError, TypeMismatchError, SelfDotAccessError
)
from pengu_parser.pengu_types import (
    OmenType, STRING_TYPE, INT_TYPE, BaseType, RuneType, RefType
)
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
import pengu_version


def test_version_sync_0_13_13():
    """Verify that version 0.13.13 is synced across toolchain."""
    assert pengu_version.__version__ == "0.13.13"
    assert pengu_version.FALLBACK_VERSION == "0.13.13"
    assert PENGU_VERSION == "0.13.13"
    assert pengu_version.read_version_file() == "0.13.13"


@requires_cc
def test_c5_infer_node_type_scope_isolation():
    """C5: _infer_node_type does not leak scopes or symbols to global scope."""
    code = """rune Foo:
    val as int

enchanting Foo:
    weave bar into int:
        var x as int is 5
        let t is judge x:
            when 1 -> "a"
            else -> "b"
        return 0

weave other into int:
    return 1

weave main into int:
    var f as Foo with:
        set .val is 1
    calling f.bar
    return calling other - 1
"""
    check_ok(code)
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(filename="test.pengu")
    checker.check(tree, source=code)
    codegen = PenguCodegen(checker.symbols, ["test.pengu"])
    codegen.collect_declarations([("test.pengu", tree)])
    codegen.generate_bundle()

    # After full translation, codegen symbols current_scope must be the root/global scope
    assert codegen.symbols.current_scope.parent is None
    # 'self' and local variables like 'x' or 't' from enchanting must NOT exist in global scope
    assert codegen.symbols.lookup("self") is None
    assert codegen.symbols.lookup("x") is None
    assert codegen.symbols.lookup("t") is None

    res = compile_run(code, tag="test_c5_scope_isolation")
    assert res.returncode == 0


@requires_cc
def test_c6_destructure_array_literal_and_2d():
    """C6: Destructuring array literals and 2D arrays emits valid C99."""
    code = """weave main into int:
    let a, b, c is [10, 20, 30]
    let row1, row2 is [[1, 2], [3, 4]]
    if a == 10 and b == 20 and c == 30 and (row1 at 0) == 1 and (row2 at 1) == 4:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    # Must NOT emit invalid scalar pointer initialization
    assert "* _destruct_1 = {" not in c
    assert "* _destruct_2 = {" not in c
    res = compile_run(code, tag="test_c6_array_destructure")
    assert res.returncode == 0


@requires_cc
def test_h4_in_array_of_string_and_struct():
    """H4: in / not in on arrays of strings and structs compiles and executes correctly."""
    code = """rune Item:
    id as int
    code as int

weave main into int:
    var names as array of string with size 3 is ["alpha", "beta", "gamma"]
    if not ("beta" in names):
        return 1
    if "delta" in names:
        return 2

    var it1 as Item with:
        set .id is 1
        set .code is 100
    var it2 as Item with:
        set .id is 2
        set .code is 200

    var items as array of Item with size 2 is [it1, it2]
    var target as Item with:
        set .id is 2
        set .code is 200
    if not (target in items):
        return 3
    return 0
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "pengu_string_equal" in c
    assert "memcmp" in c
    res = compile_run(code, tag="test_h4_in_arrays")
    assert res.returncode == 0


def test_m8_reject_tail_if_without_returns_in_non_void_weave():
    """M8: Tail if_stmt without returns in non-void function is rejected with E0020."""
    code = """weave pick with flag as bool into int:
    if flag:
        calling spark.println with "yes"
    else:
        calling spark.println with "no"
"""
    check_error(code, "E0020")


@requires_cc
def test_m8_accept_tail_if_with_exhaustive_returns():
    """M8: Tail if_stmt where all branches return is accepted and compiles cleanly."""
    code = """weave pick with flag as bool into int:
    if flag:
        return 10
    else:
        return 20

weave main into int:
    let r1 is calling pick with true
    let r2 is calling pick with false
    if r1 == 10 and r2 == 20:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_m8_tail_if_exhaustive")
    assert res.returncode == 0


def test_m9_struct_init_omen_payload_expected_type():
    """M9: struct_init propagates expected type to omen payload fields."""
    code = """omen NetworkState:
    Disconnected
    Connected with session_id as string

weave main into int:
    var s as NetworkState is with:
        set .Connected is with:
            set .session_id is 42
    return 0
"""
    check_error(code, "E0005")


def test_m13_frozen_write_block_deep_reference():
    """m13: Writing through a ref to frozen pointee is rejected with E0003."""
    code = """rune Data:
    num as int

weave test with p as ref to frozen Data into void:
    set p->num is 10
"""
    check_error(code, "E0003")
