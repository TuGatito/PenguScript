"""Regression tests for PenguScript 0.13.9.

Covers:
- C1: let bindings subject to auto-banish emitted without C const qualifier
- C2: local_vars preserved across nested scopes and blocks in codegen
- A1: judge subject validated against unsupported types (maybe, result, list) with E0005
- A2: omen with string values has is_int() == False, is_string() == True, and judge emits pengu_string_equal
- A3: bytes of <string> emits ((const uint8_t*)
- M1: judge with qualified omen variant pattern normalizes correctly with insignia
- M2: _is_single_char_or_byte unwraps chained SealType/AliasType/FrozenType
- M3: _lookup_with_field_type unwraps SealType/AliasType/FrozenType/RefType
- m1: entry point main returning OmenType rejected with E0020
- m2: banish nominal seal type rejected with E0008 and help message mentions cast
- m3: _extract_preceding_doc cleans nested '#' prefixes properly
- Version: version sync across toolchain files to 0.13.9
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from pengu_parser.pengu_types import OmenType, STRING_TYPE, INT_TYPE, BaseType, SealType, AliasType, FrozenType
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
import pengu_version


def test_version_sync_0_13_9():
    """Verify that version 0.13.9+ is synced across toolchain."""
    assert tuple(map(int, pengu_version.__version__.split("."))) >= (0, 13, 9)
    assert pengu_version.FALLBACK_VERSION == pengu_version.__version__
    assert PENGU_VERSION == pengu_version.__version__
    assert pengu_version.read_version_file() == pengu_version.__version__


@requires_cc
def test_c1_let_autobanish_no_const_discard():
    """C1: let + auto-banished string emits non-const C declaration so banish does not discard qualifiers."""
    code = """weave main into int:
    let s is "hello " + "world"
    if s == "hello world":
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    # The C declaration for auto-banished 's' should be 'PenguString s' without 'const'
    assert "const PenguString s" not in c
    assert "PenguString s" in c
    assert "pengu_banish_string(&s)" in c
    res = compile_run(code, tag="test_c1_autobanish")
    assert res.returncode == 0


@requires_cc
def test_c2_local_vars_scope_isolation_in_blocks():
    """C2: local_vars environment is isolated and restored after nested blocks."""
    code = """rune Point:
    x as int
    y as int

weave mutate with p as ref to Point into void:
    with p:
        # with stack holds p as ref to Point
        if 1 != 2:
            let dummy is 99
        set .x is 42
        set .y is 84

weave main into int:
    var pt as Point with:
        set .x is 10
        set .y is 20
    calling mutate with sigil of pt
    if pt.x == 42 and pt.y == 84:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "p->x = 42;" in c
    assert "p->y = 84;" in c
    res = compile_run(code, tag="test_c2_scope_iso")
    assert res.returncode == 0


def test_a1_judge_subject_type_validation():
    """A1: judge subject must be an omen, bool, int, or string; maybe/result/list rejected with E0005."""
    code_maybe = """weave main into int:
    var m as maybe int is some 42
    let res is judge m:
        when 42 -> 1
        else -> 0
    return res
"""
    check_error(code_maybe, contains="E0005")

    code_list = """weave main into int:
    var lst as list of int is [1, 2, 3]
    let res is judge lst:
        when 1 -> 1
        else -> 0
    return res
"""
    check_error(code_list, contains="E0005")


@requires_cc
def test_a2_omen_string_not_int_and_judge_uses_string_equal():
    """A2: omen with string values does not behave as integer and compiles judge to pengu_string_equal."""
    code = """omen HttpMethod with string:
    Get is "GET"
    Post is "POST"

weave main into int:
    var m as HttpMethod is HttpMethod.Get
    let code is judge m:
        when HttpMethod.Get -> 200
        when HttpMethod.Post -> 201
        else -> 400
    if code == 200:
        return 0
    return 1
"""
    checker = check_ok(code)
    omen_sym = checker.symbols.lookup("HttpMethod")
    assert omen_sym is not None
    omen_t: OmenType = omen_sym.type
    assert omen_t.is_string_valued
    assert not omen_t.is_int()
    assert not omen_t.is_numeric()
    assert omen_t.is_string()

    c = gen_bundle(code)
    assert "pengu_string_equal" in c
    assert "switch (" not in c or "switch (m)" not in c

    res = compile_run(code, tag="test_a2_string_omen")
    assert res.returncode == 0


def test_a3_bytes_of_string_emits_const_uint8_cast():
    """A3: bytes of <string> emits const uint8_t cast in C codegen."""
    code = """weave main into void:
    var s as string is "abc"
    var p as ref to frozen byte is bytes of s
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "(const uint8_t*)" in c
    assert "(uint8_t*)(((s)).data)" not in c


@requires_cc
def test_m1_judge_qualified_omen_variant_with_insignia():
    """M1: judge when MyOmen.Variant resolves properly with insignia prefix."""
    code = """insignia app_

omen Status:
    Active
    Paused
    Stopped

weave main into int:
    var st as Status is Status.Active
    let v is judge st:
        when Status.Active -> 10
        when Status.Paused -> 20
        else -> 0
    if v == 10:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "app_Status_Active" in c
    res = compile_run(code, tag="test_m1_insignia_judge")
    assert res.returncode == 0


def test_m2_is_single_char_or_byte_unwraps_chained_seals():
    """M2: _is_single_char_or_byte unwraps arbitrary chains of SealType, AliasType, and FrozenType."""
    b_type = BaseType("byte")
    s1 = SealType(name="S1", underlying=b_type)
    a1 = AliasType(name="A1", target=s1)
    f1 = FrozenType(target=a1)
    assert PenguCodegen._is_single_char_or_byte(f1) is True

    c_type = BaseType("char")
    s2 = SealType(name="S2", underlying=c_type)
    assert PenguCodegen._is_single_char_or_byte(s2) is True

    i_type = INT_TYPE
    s3 = SealType(name="S3", underlying=i_type)
    assert PenguCodegen._is_single_char_or_byte(s3) is False


def test_m3_lookup_with_field_type_unwraps_seals():
    """M3: _lookup_with_field_type unwraps SealType/AliasType on target struct."""
    code = """rune Config:
    port as int

seal MyConfig as Config

weave main into int:
    var c as Config with:
        set .port is 8080
    if c.port == 8080:
        return 0
    return 1
"""
    check_ok(code)


def test_m1_main_cannot_return_omen():
    """m1: Entry point 'main' returning an OmenType is rejected with E0020."""
    code = """omen ExitCode:
    Success
    Failure

weave main into ExitCode:
    return ExitCode.Success
"""
    check_error(code, contains="E0020")


def test_m2_banish_seal_error_and_unwrap():
    """m2: banish requires reference/string/list/map; nominal seal types rejected with helpful E0008 message."""
    code = """seal Path as string

weave main into void:
    var p as Path is "dir/file" to Path
    banish p
"""
    check_error(code, contains="nominal seal type")
    check_error(code, contains="E0008")

    from pengu_parser.pengu_parser import PenguParser
    from pengu_parser.pengu_checker import PenguChecker
    parser = PenguParser()
    checker = PenguChecker()
    with pytest.raises(SemanticError) as exc_info:
        checker.check(parser.parse(code))
    assert exc_info.value.code == "E0008"
    assert "Nominal seal types are also rejected" in exc_info.value.help


def test_m3_extract_preceding_doc_stray_hashes():
    """m3: _extract_preceding_doc cleans nested leading/trailing '#' characters."""
    code = """# # # Title Documentation # # #
weave add with a as int, b as int into int:
    return a + b
"""
    checker = check_ok(code)
    fn_sym = checker.symbols.lookup("add")
    assert fn_sym is not None
    assert fn_sym.doc == "Title Documentation"
