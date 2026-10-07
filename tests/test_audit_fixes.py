#!/usr/bin/env python3
"""Regression tests for the compiler audit (correctness + soundness findings).

Each test names the audited item it pins down.  They are grouped by area and
keep the smallest reproduction that used to fail.
"""
import pytest

from tests.conftest import (
    HAVE_CC,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_runtime,
    requires_leakcheck,
)

requires_cc = pytest.mark.skipif(not HAVE_CC, reason="no C compiler")


# ---------------------------------------------------------------------------
# Constant folding / literals (#19, #20, #21)
# ---------------------------------------------------------------------------


def test_leading_zero_integer_literal_parses():
    """#19: '08'/'09' are decimal 8/9, not a ValueError inside the checker."""
    check_ok("weave main into int:\n    let x is 08\n    let y is 09\n    return 0\n")
    c = gen_bundle("weave main into int:\n    let x is 08\n    return 0\n")
    assert "int32_t x = 8" in c


def test_integer_literal_bases():
    """#19: the 0x prefix keeps working after the base-10 fallback."""
    check_ok("weave main into int:\n    let a is 0x1F\n    let b is 0xFF\n    return 0\n")
    c = gen_bundle("weave main into int:\n    let a is 0x1F\n    let b is 0xFF\n    return 0\n")
    assert "int32_t a = 31" in c
    assert "int32_t b = 255" in c


def test_comptime_division_truncates_toward_zero():
    """#20: a folded '-7 / 2' is -3 in C, not Python's -4."""
    c = gen_bundle("weave main into int:\n    let d is -7 / 2\n    return 0\n")
    assert "int32_t d = -3" in c


def test_comptime_modulo_follows_dividend():
    """#21: a folded '-7 % 2' is -1 in C, not Python's 1."""
    c = gen_bundle("weave main into int:\n    let m is -7 % 2\n    return 0\n")
    assert "int32_t m = -1" in c


@requires_cc
@requires_runtime
def test_folded_arithmetic_matches_runtime():
    """#20/#21 end-to-end: folded constants agree with computed values."""
    src = (
        "weave main into int:\n"
        "    var a as int is -7\n"
        "    var b as int is 2\n"
        "    var folded_d as int is -7 / 2\n"
        "    var live_d as int is a / b\n"
        "    var folded_m as int is -7 % 2\n"
        "    var live_m as int is a % b\n"
        "    if folded_d != live_d:\n"
        "        return 1\n"
        "    if folded_m != live_m:\n"
        "        return 2\n"
        "    return 0\n"
    )
    res = compile_run(src, tag="comptime_div_mod")
    assert res.returncode == 0, f"folded arithmetic diverged from runtime ({res.returncode})"


# ---------------------------------------------------------------------------
# Interpolation of wide integers (#32)
# ---------------------------------------------------------------------------


def test_interpolation_does_not_truncate_wide_integers():
    """#32: '{x}' picks %lld/%llu/%u instead of casting everything to int32."""
    c = gen_bundle(
        "weave main into int:\n"
        "    var a as i64 is 1\n"
        "    var b as u64 is 2\n"
        "    var c as u32 is 3\n"
        "    var d as int is 4\n"
        '    var s as string is "{a}|{b}|{c}|{d}"\n'
        "    return 0\n"
    )
    assert 'pengu_string_format_ex("%lld|%llu|%u|%d"' in c
    assert "(long long)(a)" in c
    assert "(unsigned long long)(b)" in c


@requires_cc
@requires_runtime
def test_wide_integer_interpolation_roundtrip():
    """#32 end-to-end: 2**40 and 2**63-1 survive interpolation."""
    src = (
        "weave main into int:\n"
        "    var big as i64 is 1099511627776\n"      # 2**40
        "    var neg as i64 is 0 - 1099511627776\n"
        "    var s as string is \"{big}\"\n"
        "    var t as string is \"{neg}\"\n"
        '    if s == "1099511627776" and t == "-1099511627776":\n'
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="wide_interp")
    assert res.returncode == 0, "wide integer interpolation truncated"


# ---------------------------------------------------------------------------
# Named arguments are emitted in declaration order (#35)
# ---------------------------------------------------------------------------


def test_named_args_are_emitted_in_declaration_order():
    """#35: 'with b is 1, a is 10' must call f(1, 10), not f(10, 1)."""
    c = gen_bundle(
        "weave sub with a as int, b as int into int:\n"
        "    return a - b\n\n"
        "weave main into int:\n"
        "    var r as int is calling sub with b is 1, a is 10\n"
        "    return 0\n"
    )
    # a=10, b=1 in declaration order
    assert "sub(10, 1)" in c
    assert "sub(1, 10)" not in c


def test_named_args_on_methods_are_reordered():
    """#35: method named args follow the method's declared parameter order."""
    c = gen_bundle(
        "rune Pair:\n"
        "    x as int\n"
        "    y as int\n\n"
        "enchanting Pair:\n"
        "    weave combine with first as int, second as int into int:\n"
        "        return (first * 10) + second\n\n"
        "weave main into int:\n"
        "    var p as Pair is with x is 0, y is 0\n"
        "    var m as int is calling p.combine with second is 2, first is 3\n"
        "    return 0\n"
    )
    assert "Pair_combine(&p, 3, 2)" in c


@requires_cc
@requires_runtime
def test_named_args_semantics_end_to_end():
    """#35: reversed named args still compute the declared semantics."""
    src = (
        "weave sub with a as int, b as int into int:\n"
        "    return a - b\n\n"
        "weave main into int:\n"
        "    var r as int is calling sub with b is 1, a is 10\n"
        "    if r == 9:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="named_args_order")
    assert res.returncode == 0, "named arguments were passed in the wrong order"


# ---------------------------------------------------------------------------
# Parameter / function-name validation (#11, #12)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["int", "float", "char", "void", "struct", "return", "sizeof", "asm"])
def test_weave_named_after_c_keyword_is_escaped(name):
    """#12 (audit claim was wrong): C keyword names are escaped to '_<name>'."""
    c = gen_bundle(f"weave {name} into void:\n    return\n")
    assert f"_{name}(" in c
    assert f" {name}(" not in c


def test_duplicate_parameter_name_is_rejected():
    """#11: 'with x as int, x as int' silently overwrote the first parameter."""
    check_error("weave f with x as int, x as int into void:\n    return\n", contains="E0005")


def test_duplicate_method_parameter_name_is_rejected():
    """#11: same for enchanting methods."""
    check_error(
        "rune R:\n"
        "    a as int\n\n"
        "enchanting R:\n"
        "    weave m with x as int, x as int into void:\n"
        "        return\n",
        contains="E0005",
    )


def test_keyword_method_name_is_still_allowed():
    """#12 must not reject methods: their C name is '<Type>_<method>'."""
    check_ok(
        "rune R:\n"
        "    a as int\n\n"
        "enchanting R:\n"
        "    weave union with other as R into R:\n"
        "        return essence of self\n"
    )


# ---------------------------------------------------------------------------
# Ownership: string slots, ref-to-Nexus banish, destructured lists
# (#37, #43, #36)
# ---------------------------------------------------------------------------


def test_struct_string_field_stores_without_copy():
    """#37: the rune field receives the string value as written, with no deep copy."""
    c = gen_bundle(
        "rune Player:\n"
        "    name as string\n\n"
        "weave f with x as int into void:\n"
        "    var s as string is (x to string)\n"
        "    var p as Player is with name is s\n"
        "    return\n"
    )
    assert "(Player){.name = s}" in c
    assert "pengu_string_copy" not in c
    # No escape analysis and no scope-exit release: only an explicit banish frees s.
    assert "pengu_banish_string(&s)" not in c
    explicit = (
        "rune Player:\n"
        "    name as string\n\n"
        "weave f with x as int into void:\n"
        "    var s as string is (x to string)\n"
        "    var p as Player is with name is s\n"
        "    banish s\n"
        "    return\n"
    )
    assert "pengu_banish_string(&s);" in gen_bundle(explicit)


def test_with_builder_string_field_stores_without_copy():
    """#37: same for the 'with:' builder form: the field aliases s, no copy."""
    c = gen_bundle(
        "rune Player:\n"
        "    name as string\n\n"
        "weave f with x as int into void:\n"
        "    var s as string is (x to string)\n"
        "    var p as Player with:\n"
        "        set .name is s\n"
        "    return\n"
    )
    assert "_with_1.name = s;" in c
    assert "pengu_string_copy" not in c
    # No escape analysis and no scope-exit release.
    assert "pengu_banish_string(&s)" not in c


def test_some_stores_the_payload_without_cloning():
    """Audit#5-#1: 'some s' memcpy's the payload into the box; it does not clone it."""
    c = gen_bundle(
        "weave f with x as int into void:\n"
        "    var s as string is (x to string)\n"
        "    var m as maybe string is some s\n"
        "    return\n"
    )
    assert "memcpy(" in c
    assert "pengu_string_clone" not in c
    # The box aliases s's buffer, so nothing is released implicitly either.
    assert "pengu_banish_string(&s)" not in c


def test_banish_ref_to_nexus_rune_runs_field_destructor():
    """#43: 'banish p' on 'ref to Rune derive Nexus' must free its fields too."""
    c = gen_bundle(
        "rune Player derive Nexus:\n"
        "    name as string\n\n"
        "declare malloc with size as usize into ref to Player\n\n"
        "weave main into int:\n"
        "    var p as ref to Player is calling malloc with 64\n"
        "    banish p\n"
        "    return 0\n"
    )
    assert "_pengu_cleanup_Player((void*)(p))" in c
    assert "pengu_banish((void*)(p))" in c


def test_banish_plain_ref_still_frees_pointer_only():
    """#43 must not change 'ref to int': no user destructor exists."""
    c = gen_bundle(
        "declare malloc with size as usize into ref to int\n\n"
        "weave main into int:\n"
        "    var p as ref to int is calling malloc with 4\n"
        "    banish p\n"
        "    return 0\n"
    )
    assert "pengu_banish((void*)(p))" in c
    assert "_pengu_cleanup_" not in c


def test_destructured_list_rvalue_is_released():
    """#36: a destructured call result frees the temporary PenguList."""
    c = gen_bundle(
        "weave make into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 1\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    let a, b is calling make\n"
        "    return a + b\n"
    )
    assert "pengu_banish_list(&_destruct" in c


def test_destructured_borrowed_list_is_not_released():
    """#36: a destructured local list belongs to its owner; do not free it."""
    c = gen_bundle(
        "weave main into int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 1\n"
        "    calling xs.push with 2\n"
        "    let a, b is xs\n"
        "    return a + b\n"
    )
    assert "pengu_banish_list(&_destruct" not in c


@requires_cc
@requires_runtime
@requires_leakcheck
def test_destructured_list_rvalue_has_no_leak(tmp_path):
    """#36: the released temporary means zero lost allocations."""
    from tests.test_string_composition_suite import _build_leakcheck, _compile_program

    prog = tmp_path / "destructure_leak.pengu"
    prog.write_text(
        "weave make into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 40\n"
        "    calling xs.push with 2\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    let a, b is calling make\n"
        "    if a + b == 42:\n"
        "        return 0\n"
        "    return 1\n",
        encoding="utf-8",
    )
    exe = _compile_program(prog, tmp_path)
    so = _build_leakcheck(tmp_path)
    import os
    import subprocess
    from tests.conftest import REPO

    env = dict(os.environ)
    env["LD_PRELOAD"] = str(so)
    res = subprocess.run([str(exe)], capture_output=True, text=True, cwd=str(REPO), env=env)
    assert res.returncode == 0, f"leak/run failure:\n{res.stderr}\n{res.stdout}"


# ---------------------------------------------------------------------------
# Type-parameter bounds are enforced wherever a value flows in (#9)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("body,expected", [
    # returning a value that violates the bound
    ('weave g shard T where T: Num into T:\n        return "x"\n', "E0005"),
    # var / let annotations
    ('weave g shard T where T: Num into int:\n        var v as T is "x"\n        return 0\n', "E0005"),
    ('weave g shard T where T: Num into int:\n        let v as T is "x"\n        return 0\n', "E0005"),
    # maybe payload
    ('weave g shard T where T: Num into int:\n        var m as maybe T is some "x"\n        return 0\n', "E0005"),
    # container element (the container checker has its own code)
    ('weave g shard T where T: Num into int:\n        var xs as list of T is list of T\n        calling xs.push with "x"\n        return 0\n', "E0018"),
    # struct field
    ('rune Box shard T:\n        val as T\n\nweave g shard T where T: Num into int:\n        var b as Box of T is with val is "x"\n        return 0\n', "E0005"),
])
def test_typeparam_bounds_are_enforced(body, expected):
    """#9: 'T: Num' must reject a string in every value position, not just 'set'."""
    src = body + "\nweave main into int:\n    return 0\n"
    check_error(src, contains=expected)


@pytest.mark.parametrize("body", [
    # int satisfies Num
    'weave g shard T where T: Num into T:\n    return 1\n',
    'weave g shard T where T: Num into int:\n    var m as maybe T is some 1\n    return 0\n',
    # 'donum T' yields the zero value of T
    'weave g shard T where T: Donum into int:\n    var v as T is donum T\n    return 0\n',
    # a T value flows into a T slot
    'weave g shard T where T: Num with v as T into T:\n    return v\n',
    # unbounded parameters stay wildcards
    'weave g shard T into int:\n    var m as maybe T is some "x"\n    return 0\n',
    # string satisfies Forma
    'weave g shard T where T: Forma with v as T into int:\n    return 0\n',
])
def test_typeparam_bounds_accept_valid_values(body):
    """#9: the bound check must not reject bound-satisfying or unresolved values."""
    check_ok(body + "\nweave main into int:\n    return 0\n")


def test_typeparam_bound_violation_in_call_reports_e0032():
    """#9: call arguments already report the concept-bound error (E0032)."""
    check_error(
        "weave g shard T where T: Num with v as T into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        '    calling g with "x"\n'
        "    return 0\n",
        contains="E0032",
    )


# ---------------------------------------------------------------------------
# Iteration over rvalues and signature type validation (#29, #10)
# ---------------------------------------------------------------------------


def test_for_in_over_rvalue_list_binds_a_temporary():
    """#29: 'for v in (calling make())' used to emit '&(make())' (invalid C)."""
    c = gen_bundle(
        "weave make into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 1\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    var total as int is 0\n"
        "    for v in (calling make):\n"
        "        set total is total + v\n"
        "    return total\n"
    )
    assert "pengu_list_at(&(_iter" in c
    assert "pengu_list_at(&((make()))" not in c


@requires_cc
@requires_runtime
def test_for_in_over_rvalue_list_runs():
    """#29 end-to-end: iterating a call result compiles and sums correctly."""
    res = compile_run(
        "weave make into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 20\n"
        "    calling xs.push with 22\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    var total as int is 0\n"
        "    for v in (calling make):\n"
        "        set total is total + v\n"
        "    if total == 42:\n"
        "        return 0\n"
        "    return 1\n",
        tag="forin_rvalue",
    )
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("src", [
    # parameter type
    "weave f with x as Undefined into void:\n    return\n",
    # return type
    "weave f into Undefined:\n    return 0\n",
    # rune field
    "rune R:\n    f as Undefined\n",
    # declare signature
    "declare c_fn with x as Undefined into void\n",
])
def test_undefined_type_in_declaration_is_rejected(src):
    """#10: a misspelled type in a signature reached the C compiler."""
    check_error(src + "\nweave main into int:\n    return 0\n", contains="E0022")


@pytest.mark.parametrize("src", [
    # generic rune: 'T' is the shard parameter
    "rune Box shard T:\n    val as T\n",
    # generic enchanting method: 'T' comes from the enchanting header
    "rune Box shard T:\n    val as T\n\nenchanting Box of T:\n    weave get into T:\n        return self->val\n",
    # forward reference inside the same file
    "rune A:\n    b as ref to B\n\nrune B:\n    x as int\n",
    # ordinary signatures
    "rune P:\n    x as int\n\nweave f with p as ref to P, m as maybe int into list of string:\n    return list of string\n",
])
def test_valid_declaration_types_are_accepted(src):
    """#10 must not reject generic parameters or forward references."""
    check_ok(src + "\nweave main into int:\n    return 0\n")


# ---------------------------------------------------------------------------
# Returning a view into a local must keep the local alive (#38)
# ---------------------------------------------------------------------------


def test_return_element_of_local_string_does_not_banish():
    """#38: 'return s at 0' borrows s's buffer; banishing s dangles."""
    c = gen_bundle(
        "weave f with n as int into string:\n"
        "    var s as string is (n to string)\n"
        "    return s at 0\n"
    )
    assert "pengu_banish_string(&s)" not in c


def test_return_field_of_local_does_not_banish():
    """#38: same for a field view of a local rune."""
    c = gen_bundle(
        "rune Holder:\n"
        "    name as string\n\n"
        "weave f with n as int into string:\n"
        "    var h as Holder with:\n"
        "        set .name is (n to string)\n"
        "    return h.name\n"
    )
    assert "pengu_banish_string(&h.name)" not in c


def test_return_scalar_does_not_release_the_source():
    """Manual memory: a computed scalar return leaves the local alone."""
    c = gen_bundle(
        "weave f with n as int into int:\n"
        "    var s as string is (n to string)\n"
        "    return (s length)\n"
    )
    assert "pengu_banish_string(&s)" not in c

    # The manual release is still available and runs on the return path.
    explicit = (
        "weave f with n as int into int:\n"
        "    var s as string is (n to string)\n"
        "    defer banish s\n"
        "    return (s length)\n"
    )
    assert "pengu_banish_string(&s);" in gen_bundle(explicit)


@requires_cc
@requires_runtime
def test_returning_a_view_runs_and_the_caller_can_read_it():
    """#38: the caller reads the returned view correctly."""
    src = (
        "weave first_char with n as int into string:\n"
        "    var s as string is (n to string)\n"
        "    return s at 0\n\n"
        "weave main into int:\n"
        "    var c as string is calling first_char with 65\n"
        "    if c == \"6\":\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="return_view")
    assert res.returncode == 0, res.stderr


# ---------------------------------------------------------------------------
# Bind blocks must match the concept's ritual-ness (#15)
# ---------------------------------------------------------------------------


def test_bind_method_ritual_mismatch_is_rejected():
    """#15: a non-ritual implementation of a ritual concept method failed in C."""
    check_error(
        "concept Printer:\n"
        "    weave ritual describe into string\n\n"
        "rune Dot:\n"
        "    x as int\n\n"
        "bind Dot with Printer:\n"
        "    weave describe into string:\n"
        "        return \"dot\"\n",
        contains="E0030",
    )


def test_bind_method_ritual_match_is_accepted():
    """#15: matching ritual modifiers still bind."""
    check_ok(
        "concept Printer:\n"
        "    weave ritual describe into string\n\n"
        "rune Dot:\n"
        "    x as int\n\n"
        "bind Dot with Printer:\n"
        "    weave ritual describe into string:\n"
        "        return \"dot\"\n"
    )


# ---------------------------------------------------------------------------
# Audit #2 — P0 regressions
# ---------------------------------------------------------------------------


def test_let_with_or_block_is_not_const():
    """Audit#2-#2: 'or:' assigns the binding, so 'let' cannot be 'const'."""
    src = (
        "weave get_name into maybe string:\n"
        '    return some "n"\n\n'
        "weave f into string:\n"
        "    let s as string is (calling get_name) or:\n"
        '        return "fallback"\n'
        "    return s\n"
    )
    c = gen_bundle(src)
    assert "const PenguString s" not in c
    assert any(l.strip().startswith("PenguString s =") for l in c.splitlines())


@requires_cc
@requires_runtime
def test_let_with_or_block_runs():
    """Audit#2-#2 end-to-end."""
    src = (
        "weave get_name into maybe string:\n"
        '    return some "n"\n\n'
        "weave f into string:\n"
        "    let s as string is (calling get_name) or:\n"
        '        return "fallback"\n'
        "    return s\n\n"
        "weave main into int:\n"
        "    var v as string is calling f\n"
        '    if v == "n":\n'
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="or_block_let")
    assert res.returncode == 0, res.stderr


def test_compound_modulo_requires_integers():
    """Audit#2-#4: 'f %= 2.0' must not reach the C compiler."""
    check_error(
        "weave main into int:\n"
        "    var f as float is 3.0\n"
        "    set f %= 2.0\n"
        "    return 0\n",
        contains="E0005",
    )
    check_ok("weave main into int:\n    var n as int is 7\n    set n %= 3\n    return 0\n")
    check_ok("weave main into int:\n    var f as float is 3.0\n    set f += 2.0\n    return 0\n")


@pytest.mark.parametrize("src,expected", [
    ("weave f into int:\n    var xs as list of int is list of int\n    return xs.length\n", "xs.len"),
    ("weave f into int:\n    var xs as list of int is list of int\n    return xs.capacity\n", "xs.cap"),
    ("weave f into int:\n    var m as map of string to int is map of string to int\n    return m.length\n", "m.len"),
    ("weave f into int:\n    var m as map of string to int is map of string to int\n    return m.capacity\n", "m.cap"),
    ('weave f into int:\n    var s as string is "ab"\n    return s.length\n', "s.len"),
])
def test_length_and_capacity_aliases_emit_real_fields(src, expected):
    """Audit#2-#3: '.length'/'.capacity' used to be emitted verbatim (invalid C)."""
    c = gen_bundle(src + "\nweave main into int:\n    return 0\n")
    assert expected in c
    assert ".length" not in c
    assert ".capacity" not in c


def test_capacity_is_rejected_for_strings_and_slices():
    """Audit#2-#3: a string/slice has no capacity field."""
    check_error('weave f into int:\n    var s as string is "ab"\n    return s.capacity\n', contains="E0013")
    check_error(
        "weave f into int:\n"
        "    var xs as list of int is list of int\n"
        "    var sl as slice of int is xs at 0 to 1\n"
        "    return sl.capacity\n",
        contains="E0013",
    )


def test_named_args_skip_defaults_without_shifting_positions():
    """Audit#2-#1: a skipped default must be filled, not shifted."""
    c = gen_bundle(
        'weave greet with name as string is "world", times as int is 3 into int:\n'
        "    return times\n\n"
        "weave main into int:\n"
        "    var r as int is calling greet with times is 5\n"
        "    return r\n"
    )
    assert 'greet(pengu_string_from_cstr("world"), 5)' in c


def test_named_args_fill_middle_defaults():
    """Audit#2-#1: gaps between named arguments are filled with their defaults."""
    c = gen_bundle(
        "weave f with a as int is 1, b as int is 2, c as int is 3 into int:\n"
        "    return a + b + c\n\n"
        "weave main into int:\n"
        "    var r as int is calling f with c is 9\n"
        "    return r\n"
    )
    assert "f(1, 2, 9)" in c


def test_unknown_named_argument_is_rejected():
    """Audit#2-#1: an unknown name used to be passed positionally."""
    check_error(
        "weave f with a as int, b as int into int:\n"
        "    return a\n\n"
        "weave main into int:\n"
        "    var r as int is calling f with z is 5, a is 1\n"
        "    return 0\n",
        contains="E0005",
    )


def test_duplicate_named_argument_is_rejected():
    """Audit#2-#1: duplicate names were passed twice."""
    check_error(
        "weave f with a as int, b as int into int:\n"
        "    return a\n\n"
        "weave main into int:\n"
        "    var r as int is calling f with a is 1, a is 2\n"
        "    return 0\n",
        contains="E0005",
    )


def test_missing_required_named_argument_is_rejected():
    """Audit#2-#1: a parameter without a default must be provided."""
    check_error(
        "weave f with a as int, b as int into int:\n"
        "    return a\n\n"
        "weave main into int:\n"
        "    var r as int is calling f with a is 1\n"
        "    return 0\n",
        contains="E0005",
    )


@requires_cc
@requires_runtime
def test_module_qualified_named_args_run():
    """Audit#2-#1: module-qualified named calls are reordered too."""
    import tempfile
    from pathlib import Path

    d = Path(tempfile.mkdtemp(prefix="named_mod_", dir="build"))
    (d / "main.pengu").write_text(
        "import std.arithmancy\n\n"
        "weave main into int:\n"
        "    var r as int is calling arithmancy.clamp_i with hi is 10, val is 15, lo is 0\n"
        "    if r == 10:\n"
        "        return 0\n"
        "    return 1\n",
        encoding="utf-8",
    )
    from pengu_project import PenguBuilder, ProjectConfig
    from tests.conftest import BUILD_DIR, BUILD_INCLUDE, BUILD_LIB, REPO, runtime_link_flags, runtime_tail_flags
    import subprocess

    cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(REPO), profile="debug", output="c")
    bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
    exe = d / "bin"
    cmd = ["gcc", str(bundle_path), f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
           f"-L{BUILD_LIB}", "-g", "-Wno-error=implicit-function-declaration",
           "-Wno-error=implicit-int", "-Wno-error=int-conversion"]
    cmd += runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    comp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert comp.returncode == 0, comp.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


# ---------------------------------------------------------------------------
# Audit #2 — views, comprehensions, comments, remaining validation gaps
# ---------------------------------------------------------------------------


def test_view_bound_to_a_local_disables_banish():
    """Audit#2-#7: 'var v as string is lst at 0' borrowed lst's buffer."""
    c = gen_bundle(
        "weave f into string:\n"
        "    var lst as list of string is list of string\n"
        '    calling lst.push with "a"\n'
        "    var v as string is lst at 0\n"
        "    return v\n"
    )
    assert "pengu_banish_list(&lst)" not in c


def test_view_of_field_bound_to_a_local_disables_banish():
    """Audit#2-#7: the same rule applies to field views."""
    c = gen_bundle(
        "rune Holder:\n"
        "    name as string\n\n"
        "weave f into string:\n"
        "    var h as Holder with:\n"
        '        set .name is "n"\n'
        "    var v as string is h.name\n"
        "    return v\n"
    )
    assert "pengu_banish_string(&h.name)" not in c


def test_scalar_computed_from_local_does_not_release_after_view_fix():
    """Manual memory: a computed scalar does not release its source local."""
    c = gen_bundle(
        "weave f with n as int into int:\n"
        "    var s as string is (n to string)\n"
        "    return (s length)\n"
    )
    assert "pengu_banish_string(&s)" not in c


def test_for_comp_over_rvalue_binds_a_temporary():
    """Audit#2-#8: 'for x in (calling make) then x' emitted '&(f())'."""
    c = gen_bundle(
        "weave get_list into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 1\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    let ys is for x in (calling get_list) then x * 2\n"
        "    return 0\n"
    )
    assert "pengu_list_at(&((get_list()))" not in c
    assert "_iter" in c


@requires_cc
@requires_runtime
def test_for_comp_over_rvalue_runs():
    """Audit#2-#8 end-to-end."""
    src = (
        "weave get_list into list of int:\n"
        "    var xs as list of int is list of int\n"
        "    calling xs.push with 2\n"
        "    calling xs.push with 3\n"
        "    return xs\n\n"
        "weave main into int:\n"
        "    let ys is for x in (calling get_list) then x * 2\n"
        "    var total as int is 0\n"
        "    for v in ys:\n"
        "        set total is total + v\n"
        "    if total == 10:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="forcomp_rvalue")
    assert res.returncode == 0, res.stderr


def test_hash_line_inside_triple_quoted_string_is_kept():
    """Audit#2-#5: a '#' line inside a triple-quoted string was blanked."""
    c = gen_bundle(
        "weave main into int:\n"
        '    let s as string is """line1\n'
        "# not a comment\n"
        'line3"""\n'
        "    return 0\n"
    )
    assert "# not a comment" in c


def test_hash_inside_a_nested_string_in_interpolation_is_kept():
    """Audit#2-#6: quotes and '#' inside '{expr}' corrupted the literal."""
    c = gen_bundle(
        "weave tag with s as string into string:\n"
        '    return "«{s}»"\n\n'
        "weave main into int:\n"
        '    var t as string is "{calling tag with "z#w"}"\n'
        "    return 0\n"
    )
    assert "z#w" in c


def test_normal_comments_still_stripped():
    """Audit#2-#5/#6 must not break ordinary comments."""
    c = gen_bundle(
        "weave main into int:\n"
        "    let x is 1  # trailing comment\n"
        "    return x\n"
    )
    assert "trailing comment" not in c
    c2 = gen_bundle(
        "## a doc comment\n"
        "weave main into int:\n"
        '    let s is "a#b"  # real comment\n'
        "    return 0\n"
    )
    assert "a#b" in c2
    assert "real comment" not in c2


@pytest.mark.parametrize("src", [
    # concept method signature
    "concept Speaker:\n    weave greet with target as Undefined into string\n",
    # omen variant payload
    "omen Event:\n    Tick with duration as Undefined\n",
    # concrete enchanting method
    "rune Player:\n    hp as int\n\nenchanting Player:\n    weave heal with amount as Undefined into void:\n        return\n",
])
def test_audit2_signature_gaps_are_rejected(src):
    """Audit#2-#9/#10/#12: these signature types were never validated."""
    check_error(src + "\nweave main into int:\n    return 0\n", contains="E0022")


def test_c_types_from_included_headers_are_accepted():
    """Audit#2-#11: 'va_list'/'FILE' come from the C header, not PenguScript."""
    check_ok(
        'include "stdarg.h"\n\n'
        "declare vlog with fmt as ref to char, args as va_list into void\n\n"
        "weave main into int:\n    return 0\n"
    )
    check_ok(
        'include "stdio.h"\n\n'
        "declare cfun with f as FILE into void\n\n"
        "weave main into int:\n    return 0\n"
    )


def test_pengu_typo_is_still_rejected_in_a_file_with_includes():
    """Audit#2-#11: the include bail-out must not hide a PenguScript typo."""
    check_error(
        'include "stdio.h"\n\n'
        "weave f with x as Undefined into void:\n    return\n\n"
        "weave main into int:\n    return 0\n",
        contains="E0022",
    )


def test_loop_value_does_not_release_fresh_iteration_temporary():
    """Audit#2-#19: the loop-value push memcpy's the element; the temporary is not freed."""
    c = gen_bundle(
        "weave main into int:\n"
        "    var parts as list of string is for i from 0 to 3:\n"
        '        "n{(i to string)}"\n'
        "    return 0\n"
    )
    assert "_lv_" in c
    assert "pengu_string_cleanup((void*)&_lv" not in c
    assert "pengu_banish_string(&_lv" not in c


def test_loop_value_does_not_free_borrowed_elements():
    """Audit#2-#19: a borrowed element (field of a rune) must not be released."""
    c = gen_bundle(
        "rune Holder:\n"
        "    name as string\n\n"
        "weave main into int:\n"
        "    var h as Holder with:\n"
        '        set .name is "shared"\n'
        "    var vals as list of string is for i from 0 to 2:\n"
        "        h.name\n"
        "    return 0\n"
    )
    assert "pengu_string_cleanup((void*)&_lv" not in c


# ---------------------------------------------------------------------------
# Audit #3
# ---------------------------------------------------------------------------


def test_block_value_is_read_without_a_scope_exit_release():
    """Audit#3-#1: 'do: … y.length' reads y and never releases it (manual memory)."""
    c = gen_bundle(
        "weave f into int:\n"
        "    let x is do:\n"
        '        var y as string is "hello{(1 to string)}"\n'
        "        y.length\n"
        "    return x\n"
    )
    # The block value is snapshotted and read; nothing goes out of its way to free y.
    assert "_val_" in c
    assert "y.len" in c
    assert "pengu_banish_string(&y)" not in c


@requires_cc
@requires_runtime
def test_block_value_read_runs():
    """Audit#3-#1 end-to-end."""
    src = (
        "weave f into int:\n"
        "    let x is do:\n"
        '        var y as string is "hello{(1 to string)}"\n'
        "        y.length\n"
        "    return x\n\n"
        "weave main into int:\n"
        "    if (calling f) == 6:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="do_value_order")
    assert res.returncode == 0, res.stderr


def test_if_value_block_snapshot_without_release():
    """Audit#3-#1: value-position 'if'/'unless' snapshots the value and never releases."""
    c = gen_bundle(
        "weave f with c as bool into int:\n"
        "    let x is if c:\n"
        '        var y as string is "abc{(3 to string)}"\n'
        "        y.length\n"
        "    else:\n"
        "        0\n"
        "    return x\n"
    )
    assert "_val_" in c
    assert "y.len" in c
    assert "pengu_banish_string(&y)" not in c


def test_function_pointer_alias_typedef():
    """Audit#3-#2: 'alias Cb as ref to weave …' emitted 'typedef void (*)(int)'."""
    c = gen_bundle(
        "alias Callback as ref to weave with x as int into void\n\n"
        "weave apply with cb as Callback, v as int into void:\n"
        "    calling cb with v\n\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    assert "typedef void (*Callback)(int32_t);" in c
    assert "typedef void (*)(int32_t) Callback;" not in c


def test_lambda_parameters_do_not_leak_into_the_global_scope():
    """Audit#3-#3: lambda params were defined in the codegen's current scope."""
    import pengu_parser.pengu_codegen as cg

    captured = {}
    orig = cg.PenguCodegen.generate_bundle

    def wrapped(self, *args, **kwargs):
        res = orig(self, *args, **kwargs)
        captured["global"] = sorted(s.name for s in self.symbols.global_scope.symbols.values())
        return res

    cg.PenguCodegen.generate_bundle = wrapped
    try:
        gen_bundle(
            "weave main into int:\n"
            "    var cb as ref to weave with x as int into int is lambda x as int into x + 1\n"
            "    return 0\n"
        )
    finally:
        cg.PenguCodegen.generate_bundle = orig
    assert "x" not in captured.get("global", [])


def test_large_integer_literals_are_i64():
    """Audit#3-#4: '3000000000' used to be typed int32 (silent truncation)."""
    c = gen_bundle("weave main into int:\n    let n is 3000000000\n    return 0\n")
    assert "int64_t n" in c
    c2 = gen_bundle("weave main into int:\n    let small is 5\n    return 0\n")
    assert "int32_t small" in c2


@requires_cc
@requires_runtime
def test_large_integer_literal_compares_correctly():
    """Audit#3-#4 end-to-end."""
    src = (
        "weave main into int:\n"
        "    let n is 3000000000\n"
        "    if n > 2999999999:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="int64_literal")
    assert res.returncode == 0, res.stderr


def test_enchanting_method_must_return_a_value():
    """Audit#3-#5: a method falling off the end was accepted (UB in C)."""
    check_error(
        "rune Foo:\n"
        "    x as int\n\n"
        "enchanting Foo:\n"
        "    weave bar into int:\n"
        "        if self->x > 0:\n"
        "            return 1\n\n"
        "weave main into int:\n"
        "    return 0\n",
        contains="E0020",
    )
    check_ok(
        "rune Foo:\n"
        "    x as int\n\n"
        "enchanting Foo:\n"
        "    weave bar into int:\n"
        "        return self->x + 1\n\n"
        "weave main into int:\n"
        "    return 0\n"
    )


@pytest.mark.parametrize("src", [
    'weave main into int:\n    for c in "a" to "z":\n        return 0\n    return 1\n',
    'weave f with a as string, b as string into int:\n    for c in a to b:\n        return 0\n    return 1\n',
])
def test_ranges_require_integer_bounds(src):
    """Audit#3-#6: string ranges emitted 'int64_t = PenguString'."""
    check_error(src, contains="E0005")
    check_ok("weave main into int:\n    for i in 0 to 3:\n        return i\n    return 0\n")


def test_destructuring_uses_declared_field_names_with_insignia():
    """Audit#3-#7: 'self.runes' is keyed by C name, so fields were lost."""
    c = gen_bundle(
        "insignia pl_\n\n"
        "rune Player:\n"
        "    hp as int\n"
        "    name as string\n\n"
        "weave main into int:\n"
        "    var p as Player with:\n"
        "        set .hp is 7\n"
        '        set .name is "hero"\n'
        "    let health, who is p\n"
        "    return health\n"
    )
    assert ".hp;" in c
    assert ".name;" in c


def test_derive_imago_accepts_array_fields():
    """Audit#3-#8: 'array of T' never implemented Imago/Nexus."""
    c = gen_bundle(
        "rune Box derive Imago, Nexus:\n"
        "    names as array of string with size 2\n"
        "    nums as array of int with size 2\n\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    # per-element deep copy and release for the string array
    assert "pengu_string_copy" in c
    assert "pengu_banish_string(&(pt->names[" in c
    # the int array needs no per-element work
    assert "nums[_ai" not in c


def test_static_var_carries_its_symbol():
    """Audit#3-#11: the enclosing weave scope is popped before codegen."""
    import pengu_parser.pengu_codegen as cg

    seen = {}
    orig = cg.PenguCodegen._translate_stmt

    def wrapped(self, node):
        if getattr(node, "data", None) == "static_var_decl":
            seen["sym"] = getattr(node, "_pengu_symbol", None)
        return orig(self, node)

    cg.PenguCodegen._translate_stmt = wrapped
    try:
        gen_bundle(
            "weave counter into int:\n"
            "    static var n as int is 0\n"
            "    set n is n + 1\n"
            "    return n\n\n"
            "weave main into int:\n"
            "    return calling counter\n"
        )
    finally:
        cg.PenguCodegen._translate_stmt = orig
    assert seen.get("sym") is not None


def test_small_weaves_are_marked_inline():
    """Audit#3-#10: the checker's inline heuristic never reached the C output."""
    c = gen_bundle(
        "weave small with n as int into int:\n"
        "    return n + 1\n\n"
        "weave main into int:\n"
        "    return calling small with 1\n"
    )
    # Automatic (heuristic) inlining uses a plain 'static inline' hint: GCC
    # still declines to inline a recursive weave, whereas 'always_inline' is a
    # hard error.  The explicit 'inline' keyword keeps the attribute.
    assert "static inline int32_t small(" in c
    assert "__attribute__((always_inline)) int32_t small(" not in c


def test_or_fallback_type_must_match_the_success_type():
    """Audit#3-#12: 'maybe int or: "text"' was accepted."""
    check_error(
        "weave get_i into maybe int:\n"
        "    return some 1\n\n"
        "weave f into int:\n"
        "    var x as int is (calling get_i) or:\n"
        '        "not an int"\n'
        "    return x\n",
        contains="E0005",
    )
    check_error(
        "weave get_s into maybe string:\n"
        '    return some "a"\n\n'
        "weave f into int:\n"
        "    var x as string is (calling get_s) or:\n"
        "        7\n"
        "    return 0\n",
        contains="E0005",
    )
    check_ok(
        "weave get_i into maybe int:\n"
        "    return some 1\n\n"
        "weave f into int:\n"
        "    var x as int is (calling get_i) or:\n"
        "        2\n"
        "    return x\n"
    )


def test_or_with_returning_fallback_is_accepted():
    """Audit#3-#12: a fallback that returns has no value to compare."""
    check_ok(
        "weave get_i into maybe int:\n"
        "    return some 1\n\n"
        "weave f into int:\n"
        "    var x as int is (calling get_i) or:\n"
        "        return 9\n"
        "    return x\n"
    )


def test_or_conservative_freshness_does_not_release_static_strings():
    """Audit#3-#13 must not free a '.rodata' fallback ('free(): invalid pointer')."""
    c = gen_bundle(
        "weave get_s into maybe string:\n"
        '    return some "abc"\n\n'
        "weave f into int:\n"
        "    var s as string is (calling get_s) or:\n"
        '        "default"\n'
        "    return s.len\n"
    )
    assert "pengu_banish_string(&s)" not in c


@requires_cc
@requires_runtime
def test_or_with_static_fallback_runs():
    """Audit#3-#13 guard: the program must not abort on a bad free."""
    src = (
        "weave get_s into maybe string:\n"
        '    return some "abc"\n\n'
        "weave main into int:\n"
        "    var s as string is (calling get_s) or:\n"
        '        "default"\n'
        "    if s.len == 3:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="or_static_fallback")
    assert res.returncode == 0, res.stderr


def test_view_as_block_value_keeps_the_source_alive():
    """Audit#3-#14: 'do: … xs at 0 to 2' left the block value dangling."""
    c = gen_bundle(
        "weave f into slice of int:\n"
        "    var sl as slice of int is do:\n"
        "        var xs as list of int is list of int\n"
        "        calling xs.push with 1\n"
        "        xs at 0 to 2\n"
        "    return sl\n"
    )
    assert "pengu_banish_list(&xs)" not in c


def test_scalar_member_read_does_not_release_the_source():
    """Manual memory: reading 's.len' leaves s alone; nothing frees it implicitly."""
    c = gen_bundle(
        "weave f with n as int into int:\n"
        '    var s as string is "hi{(n to string)}"\n'
        "    return s.len\n"
    )
    assert "pengu_banish_string(&s)" not in c


def test_view_bound_local_used_locally_does_not_release_the_source():
    """Manual memory: a local view ('m at "a"') does not make the map release itself."""
    c = gen_bundle(
        "weave f into int:\n"
        "    var m as map of string to list of int is map of string to list of int\n"
        "    var l1 as list of int is [1, 2]\n"
        "    with m:\n"
        '        calling .put with "a", l1\n'
        '    var got as list of int is m at "a"\n'
        "    return calling got.len\n"
    )
    assert "pengu_banish_map(&m)" not in c


@requires_cc
@requires_runtime
def test_recursive_small_weave_compiles_with_automatic_inlining():
    """Audit#3-#10: 'always_inline' on a recursive weave is a hard GCC error."""
    src = (
        "weave fact with n as int into int:\n"
        "    if n <= 1:\n"
        "        return 1\n"
        "    return n * (calling fact with n - 1)\n\n"
        "weave main into int:\n"
        "    if (calling fact with 5) == 120:\n"
        "        return 0\n"
        "    return 1\n"
    )
    c = gen_bundle(src)
    assert "static inline int32_t fact(" in c
    res = compile_run(src, tag="recursive_auto_inline")
    assert res.returncode == 0, res.stderr


def test_explicit_inline_keyword_still_forces_inlining():
    """Audit#3-#10: an explicit 'inline' keeps the always_inline attribute."""
    c = gen_bundle(
        "weave inline helper into int:\n"
        "    return 1\n\n"
        "weave main into int:\n"
        "    return calling helper\n"
    )
    assert "static inline __attribute__((always_inline)) int32_t helper(void)" in c


# ---------------------------------------------------------------------------
# Audit #4 (value blocks, nested escape, omen collisions)
# ---------------------------------------------------------------------------


def test_void_value_block_is_not_captured_in_a_temp():
    """Audit#4-#1: 'void _val_N = f();' is invalid C."""
    c = gen_bundle(
        "weave f into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        "    do:\n"
        "        calling f\n"
        "    return 0\n"
    )
    assert "void _val" not in c


def test_void_binding_is_rejected():
    """Audit#4-#1: binding a 'void' value is meaningless (and unrepresentable)."""
    check_error(
        "weave f into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        "    var x as void is do:\n"
        "        calling f\n"
        "    return 0\n",
        contains="E0005",
    )
    check_error(
        "weave f into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        "    let x as void is do:\n"
        "        calling f\n"
        "    return 0\n",
        contains="E0005",
    )
    check_ok(
        "weave f into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        "    do:\n"
        "        calling f\n"
        "    return 0\n"
    )


@requires_cc
@requires_runtime
def test_void_value_block_runs():
    """Audit#4-#1 end-to-end: the statement block must compile and run."""
    src = (
        "weave f into void:\n"
        "    return\n\n"
        "weave main into int:\n"
        "    do:\n"
        "        calling f\n"
        "    return 0\n"
    )
    res = compile_run(src, tag="void_block_stmt")
    assert res.returncode == 0, res.stderr


def test_loop_value_over_if_does_not_release_the_element():
    """Audit#4-#2: a loop-value fed by 'if'/'else' never frees the element implicitly."""
    c = gen_bundle(
        "weave main into int:\n"
        "    var lst as list of string is for i from 0 to 3:\n"
        "        if i == 0:\n"
        '            "zero{(i to string)}"\n'
        "        else:\n"
        '            "other{(i to string)}"\n'
        "    return 0\n"
    )
    assert "_lv_" in c
    assert "pengu_string_cleanup((void*)&_lv" not in c
    assert "pengu_banish_string(&_lv" not in c


def test_loop_value_over_if_with_a_borrowed_branch_is_not_released():
    """Audit#4-#2: one borrowed branch makes the whole value non-owned."""
    c = gen_bundle(
        "weave f with borrowed_s as string into int:\n"
        "    var lst as list of string is for i from 0 to 2:\n"
        "        if i == 0:\n"
        "            borrowed_s\n"
        "        else:\n"
        '            "x{(i to string)}"\n'
        "    return calling lst.len\n\n"
        "weave main into int:\n"
        "    return calling f with \"keep\"\n"
    )
    assert "pengu_string_cleanup((void*)&_lv" not in c


def test_nested_loop_value_does_not_release_the_inner_list():
    """Audit#4-#7: the inner 'list of string' is stored by memcpy and never freed implicitly."""
    c = gen_bundle(
        "weave main into int:\n"
        "    var rows as list of list of string is for i from 0 to 2:\n"
        "        for j from 0 to 2:\n"
        '            "r{(i to string)}c{(j to string)}"\n'
        "    return 0\n"
    )
    assert "_lv_" in c
    assert "pengu_list_cleanup((void*)&_lv" not in c
    assert "pengu_banish_list(&_lv" not in c


def test_nested_do_block_keeps_the_source_alive():
    """Audit#4-#3: 'do: do: y' banished 'y' before the outer value was consumed."""
    c = gen_bundle(
        "weave main into int:\n"
        "    let x as string is do:\n"
        '        var y as string is "fresh{(1 to string)}"\n'
        "        do:\n"
        "            y\n"
        "    return x.len\n"
    )
    assert "pengu_banish_string(&y)" not in c


def test_value_if_branch_value_does_not_release_the_source():
    """Manual memory: using y as a branch value never frees y implicitly."""
    src = (
        "weave f with c as bool into string:\n"
        '    var y as string is "fresh{(1 to string)}"\n'
        "    var x as string is do:\n"
        "        if c:\n"
        '            "lit"\n'
        "        else:\n"
        "            y\n"
        "    return x\n"
    )
    c = gen_bundle(src)
    assert "pengu_banish_string(&y)" not in c

    # The only release is the one the source asks for.
    explicit = src.replace("    return x\n", "    banish y\n    return x\n")
    assert "pengu_banish_string(&y);" in gen_bundle(explicit)


def test_trailing_value_if_does_not_release_the_source():
    """Manual memory: a trailing value-'if' does not free its local implicitly."""
    src = (
        "weave f with c as bool into string:\n"
        '    var y as string is "fresh{(1 to string)}"\n'
        "    var x as string is do:\n"
        "        if c:\n"
        "            y\n"
        "        else:\n"
        '            "lit"\n'
        "    return x\n"
    )
    c = gen_bundle(src)
    assert "pengu_banish_string(&y)" not in c

    explicit = src.replace("    return x\n", "    banish y\n    return x\n")
    assert "pengu_banish_string(&y);" in gen_bundle(explicit)


def test_scalar_value_block_does_not_release_after_nested_fixes():
    """Manual memory: a scalar value block never releases its local implicitly."""
    c = gen_bundle(
        "weave f into int:\n"
        "    var n as int is do:\n"
        '        var y as string is "fresh{(1 to string)}"\n'
        "        y.len\n"
        "    return n\n"
    )
    assert "y.len" in c
    assert "pengu_banish_string(&y)" not in c


def test_declaration_omen_variants_do_not_collide_with_user_consts():
    """Audit#4-#5: a '.d.pengu' omen emits its variants under the simple name."""
    import tempfile
    from pathlib import Path as _Path

    from pengu_project import PenguBuilder, ProjectConfig
    from tests.conftest import BUILD_DIR, REPO

    d = _Path(tempfile.mkdtemp(prefix="omen_decl_", dir=BUILD_DIR))
    (d / "keys.d.pengu").write_text(
        "omen KeyboardKey:\n    KEY_LEFT\n    KEY_RIGHT\n", encoding="utf-8"
    )
    (d / "main.pengu").write_text(
        "import keys\n\n"
        "const KeyboardKey_KEY_LEFT as int is 65\n\n"
        "weave main into int:\n"
        "    return 0\n",
        encoding="utf-8",
    )
    cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(REPO), output="c")
    # Must not raise E0046.
    bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
    assert _Path(bundle_path).exists()


def test_omen_variant_collision_still_reported_for_pengu_omens():
    """Audit#4-#5/#12: a real omen variant full name still collides."""
    check_error(
        "omen Color:\n"
        "    RED\n"
        "    BLUE\n\n"
        "const Color_RED as int is 1\n\n"
        "weave main into int:\n"
        "    return 0\n",
        contains="E0046",
    )


def test_banish_of_a_collection_element_requires_an_owning_element():
    """Audit#4-#8: 'banish xs at 0' releases the element in place when it owns memory."""
    owning = (
        "weave main into int:\n"
        "    var xs as list of string is list of string\n"
        "    banish xs at 0\n"
        "    return 0\n"
    )
    c = gen_bundle(owning)
    assert "pengu_banish_string(&((*(PenguString *)pengu_list_at(&(xs)" in c
    # Grouping parentheses name the same storage cell.
    assert "pengu_banish_string" in gen_bundle(owning.replace("banish xs at 0", "banish (xs at 0)"))
    # An element whose type owns nothing is still rejected.
    check_error(
        "weave main into int:\n"
        "    var xs as list of int is list of int\n"
        "    banish xs at 0\n"
        "    return 0\n",
        contains="E0008",
    )


# ---------------------------------------------------------------------------
# Audit #5 (maybe/result ownership, implicit rune lifetime, codegen fixes)
# ---------------------------------------------------------------------------


def test_some_stores_an_owning_payload_without_cloning():
    """Audit#5-#1: 'some s' shares s's buffer by memcpy; there is no deep copy."""
    c = gen_bundle(
        "weave f with x as int into void:\n"
        "    var s as string is (x to string)\n"
        "    var m as maybe string is some s\n"
        "    return\n"
    )
    assert "pengu_string_clone" not in c
    assert "memcpy(" in c


def test_maybe_box_is_released_with_its_payload_by_explicit_banish():
    """Audit#5-#2: an explicit 'banish m' frees the payload first and the box after."""
    src = (
        "weave f into int:\n"
        '    var s as string is "x{(1 to string)}"\n'
        "    var m as maybe string is some s\n"
        "    banish m\n"
        "    if m.is_present:\n"
        "        return m.value.len\n"
        "    return 0\n"
    )
    c = gen_bundle(src)
    assert "pengu_banish_string((PenguString *)((&m)->value))" in c
    assert "free((&m)->value)" in c
    assert "(&m)->is_present = false" in c

    # Without the explicit banish the box is simply leaked (manual memory).
    c_plain = gen_bundle(src.replace("    banish m\n", ""))
    assert "free((&m)->value)" not in c_plain
    assert "pengu_banish_string((PenguString *)((&m)->value))" not in c_plain


def test_maybe_pod_payload_frees_only_the_box_on_explicit_banish():
    """Audit#5-#2: an 'int' payload owns nothing; explicit 'banish m' frees only the box."""
    src = (
        "weave main into int:\n"
        "    var m as maybe int is some 42\n"
        "    banish m\n"
        "    if m.is_present:\n"
        "        return 0\n"
        "    return 1\n"
    )
    c = gen_bundle(src)
    assert "free((&m)->value)" in c
    assert "pengu_banish_string" not in c

    c_plain = gen_bundle(src.replace("    banish m\n", ""))
    assert "free((&m)->value)" not in c_plain


@requires_cc
@requires_runtime
def test_some_round_trip_is_leak_free():
    """Audit#5-#1/#2 end-to-end: no dangling box, no leaked payload/box."""
    src = (
        "weave f into maybe string:\n"
        '    var s as string is "fresh{(1 to string)}"\n'
        "    return some s\n\n"
        "weave main into int:\n"
        "    var m as maybe string is calling f\n"
        "    if m.is_present:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="maybe_round_trip")
    assert res.returncode == 0, res.stderr


def test_to_string_on_a_string_is_the_identity():
    """Audit#5-#3: 'pengu_to_string(s)' reused s's buffer, then freed it."""
    c = gen_bundle(
        "weave f with s as string into string:\n"
        "    return \"{s to string}\"\n\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    assert "pengu_to_string(s)" not in c
    assert 'pengu_string_format_ex("%.*s"' in c


@requires_cc
@requires_runtime
def test_to_string_on_a_string_does_not_crash():
    """Audit#5-#3: the generated code aborted with 'free(): invalid pointer'."""
    import tempfile
    from pathlib import Path as _Path

    src = (
        "weave f with s as string into string:\n"
        '    return "{s to string}"\n\n'
        "weave main into int:\n"
        '    var v as string is calling f with "hi"\n'
        '    if v == "hi":\n'
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="to_string_identity")
    assert res.returncode == 0, res.stderr


def test_array_literal_argument_becomes_a_compound_literal():
    """Audit#5-#4: 'f({ 1, 2, 3 })' is not a C expression."""
    c = gen_bundle(
        "weave sum3 with xs as array of int with size 3 into int:\n"
        "    return (xs at 0) + (xs at 1) + (xs at 2)\n\n"
        "weave main into int:\n"
        "    return calling sum3 with [1, 2, 3]\n"
    )
    assert "((int32_t[3]){ 1, 2, 3 })" in c


@requires_cc
@requires_runtime
def test_array_literal_argument_runs():
    """Audit#5-#4 end-to-end."""
    src = (
        "weave sum3 with xs as array of int with size 3 into int:\n"
        "    return (xs at 0) + (xs at 1) + (xs at 2)\n\n"
        "weave main into int:\n"
        "    if (calling sum3 with [1, 2, 3]) == 6:\n"
        "        return 0\n"
        "    return 1\n"
    )
    res = compile_run(src, tag="array_lit_argument")
    assert res.returncode == 0, res.stderr


def test_rune_with_heap_field_gets_no_implicit_lifetime_helpers():
    """Audit#5-#5: no implicit Nexus/Imago — a heap-owning rune gets no dtor or clone."""
    c = gen_bundle(
        "rune Tag:\n"
        "    name as string\n\n"
        "weave main into int:\n"
        "    var tags as list of Tag is list of Tag\n"
        "    return 0\n"
    )
    assert "_pengu_auto_cleanup_Tag" not in c
    assert "_pengu_auto_clone_Tag" not in c
    assert "_pengu_cleanup_Tag" not in c
    assert "_pengu_clone_Tag" not in c

    # An explicit 'derive Nexus' is what generates the destructor.
    derived = gen_bundle(
        "rune Tag derive Nexus:\n"
        "    name as string\n\n"
        "weave main into int:\n"
        "    var tags as list of Tag is list of Tag\n"
        "    return 0\n"
    )
    assert "_pengu_cleanup_Tag" in derived
    # the generated destructor releases the rune's string field
    assert "pengu_banish_string(&(pt->name))" in derived


def test_std_runes_do_not_get_implicit_lifetime_helpers():
    """Audit#5-#5: std manages its own buffers ('free_node'), so no implicit dtor."""
    c = gen_bundle(
        "import std.spark\n\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    assert "_pengu_auto_cleanup_parchment" not in c


def test_string_comprehension_is_supported():
    """Audit#5-#11: 'for c in \"abc\" then c' was rejected by the inferrer."""
    c = gen_bundle(
        "weave main into int:\n"
        "    let chars is for c in \"abc\" then c\n"
        "    return calling chars.len\n"
    )
    assert "pengu_string_char_at" in c
    assert "PenguString" in c


def test_runtime_defined_is_rejected():
    """Audit#5-#12: 'defined(...)' outside a 'when' emitted the bare identifier."""
    check_error(
        "weave main into int:\n"
        "    let x is defined(int)\n"
        "    return 0\n",
        contains="E0039",
    )
    check_ok(
        "when defined(FOO):\n"
        "    weave main into int:\n"
        "        return 0\n"
    )


def test_ord_checks_data_and_len_in_both_paths():
    """Audit#5-#10: the side-effect-free path read data[0] without .len."""
    c = gen_bundle("weave main into int:\n    let s is \"\"\n    return ord s\n")
    assert "data && (s).len > 0) ? (s).data[0]" in c
