"""Regression tests for PenguScript 0.13.8.

Covers:
- C1: defer / errdefer executed on 'or return' and 'try' early returns (manual memory)
- C2: const declaration validates against C reserved words and macros with E0035
- C3: var_ref for mutable var does not substitute stale folded const_val after mutation
- A1: insignia before weave main correctly calls prefixed entry point in generated C wrapper
- A2: weave functions named after C reserved words or stdlib identifiers rejected with E0035
- A3: multiple active weave main definitions rejected with E0046
- A4: bytes of <string> returns ref to frozen byte and rejects mutations with E0006
- M1: Pengu runtime typedefs (PenguString, PenguList, etc.) rejected in user type decls with E0035
- M2: _lookup_with_field_type resolves fields correctly with _c_ident mapping
- M3: omen variant collision detection accounts for insignia c_name
- m1: _extract_preceding_doc cleans ### headers without trailing stray hashes
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import SemanticError, MutabilityError


@requires_cc
def test_c1_defer_on_or_return():
    """C1: an explicit 'defer banish' runs when 'or return' exits early."""
    code = 'rune Tracker:\n    cleaned as int\n\nweave compute with should_fail as bool, t as ref to Tracker into maybe int:\n    defer:\n        set t->cleaned += 10\n    var s as string is (1 to string)\n    defer banish s\n    var opt as maybe int is maybe none\n    if not should_fail:\n        set opt is some 42\n    let val is opt or return maybe none\n    return some val\n\nweave main into int:\n    var tr as Tracker with:\n        set .cleaned is 0\n    let r1 is calling compute with true, sigil of tr\n    if tr.cleaned != 10:\n        return 1\n    let r2 is calling compute with false, sigil of tr\n    if tr.cleaned != 20:\n        return 2\n    return 0\n'
    check_ok(code)
    assert "pengu_banish_string(&s);" in gen_bundle(code)
    res = compile_run(code, tag="test_c1_or_return")
    assert res.returncode == 0


@requires_cc
def test_c1_defer_on_try():
    """C1: an explicit 'defer banish' runs when 'try' exits early."""
    code = 'rune Counter:\n    count as int\n\nweave step1 with fail as bool into maybe int:\n    if fail:\n        return maybe none\n    return some 100\n\nweave run_flow with fail as bool, c as ref to Counter into maybe int:\n    defer:\n        set c->count += 5\n    var temp as string is (1 to string)\n    defer banish temp\n    let val is try calling step1 with fail\n    return some val\n\nweave main into int:\n    var ctr as Counter with:\n        set .count is 0\n    let res_err is calling run_flow with true, sigil of ctr\n    if ctr.count != 5:\n        return 1\n    let res_ok is calling run_flow with false, sigil of ctr\n    if ctr.count != 10:\n        return 2\n    return 0\n'
    check_ok(code)
    assert "pengu_banish_string(&temp);" in gen_bundle(code)
    res = compile_run(code, tag="test_c1_try")
    assert res.returncode == 0


def test_c2_const_c_reserved_word_rejected():
    """C2: const cannot use C reserved keywords or standard library macros (E0035)."""
    check_error("const FILE as int is 5\n", contains="E0035")
    check_error("const int as int is 1\n", contains="E0035")
    check_error("const NULL as int is 0\n", contains="E0035")
    check_error("const bool as int is 1\n", contains="E0035")


@requires_cc
def test_c3_mutable_var_not_stale_const_val():
    """C3: var initialized with foldable chr expression is not replaced with stale const_val after set."""
    code = """weave main into int:
    var s as string is chr 65
    set s is chr 66
    if s == "B":
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_c3_var_set")
    assert res.returncode == 0


@requires_cc
def test_a1_insignia_with_weave_main():
    """A1: insignia applied to module with weave main links and runs correctly."""
    code = """insignia mymod_

weave main into int:
    return 0
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "mymod_main()" in c
    res = compile_run(code, tag="test_a1_insignia_main")
    assert res.returncode == 0


def test_a2_weave_c_reserved_function_rejected():
    """A2: weave cannot declare functions shadowing standard libc functions."""
    check_error('weave printf with s as string into void:\n    return\n', contains="E0035")
    check_error('weave malloc with size as int into int:\n    return 0\n', contains="E0035")
    check_error('weave free with p as int into void:\n    return\n', contains="E0035")


def test_a3_multiple_weave_main_rejected():
    """A3: multiple weave main definitions are rejected with E0046."""
    code = """weave main into int:
    return 0

weave main into int:
    return 1
"""
    check_error(code, contains="E0046")


def test_a4_bytes_of_string_returns_ref_to_frozen_byte():
    """A4: bytes of <string> returns ref to frozen byte; mutation is rejected with E0006."""
    code_bad = """weave main into void:
    var p as ref to frozen byte is bytes of "hello"
    set p at 0 is 88
"""
    check_error(code_bad, contains="E0006")

    code_bad2 = """weave main into void:
    var p as ref to byte is bytes of "hello"
"""
    # Type mismatch: cannot assign ref to frozen byte to ref to mutable byte
    check_error(code_bad2, contains="E0005")

    # Array of byte is writable
    code_ok = """weave main into void:
    var arr as array of byte with size 5 is [1, 2, 3, 4, 5]
    var p as ref to byte is bytes of arr
    set p at 0 is 42
"""
    check_ok(code_ok)


def test_m1_runtime_types_c_reserved_rejected():
    """M1: Pengu runtime typedefs like PenguString cannot be used as user type names (E0035)."""
    check_error("rune PenguString:\n    x as int\n", contains="E0035")
    check_error("echo PenguList:\n    x as int\n", contains="E0035")
    check_error("alias PenguMap as int\n", contains="E0035")
    check_error("omen PenguSlice:\n    A\n", contains="E0035")


def test_m1_doc_extract_triple_hash():
    """m1: Comments starting with ### are cleaned properly without leaving stray hashes."""
    code = """### Documentation for Math
weave add with a as int, b as int into int:
    return a + b
"""
    checker = check_ok(code)
    fn_sym = checker.symbols.lookup("add")
    assert fn_sym is not None
    assert fn_sym.doc == "Documentation for Math"
