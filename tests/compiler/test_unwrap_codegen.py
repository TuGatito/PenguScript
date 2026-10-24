"""Unwrap codegen: `or else`, `or return` and `try`.

Two behaviours are asserted here, and both were bugs:

1. **Box ownership.** `maybe`/`result` payloads live in a heap box. When the
   operand is an *rvalue* (`calling make() or else …`, `some x or else …`) the
   expression owns that box and must release it after copying the payload out;
   otherwise every evaluation leaks 16 bytes. When the operand is an *lvalue*
   (`m or else …`) the variable owns the box and the expression must leave it
   alone, because the program will `banish m` later.
2. **`result of void`.** The "validate and propagate" idiom, `try calling
   validate with x`, has no payload to copy out. Declaring a `void` temporary
   for it is invalid C, so the void case must run the failure check and stop.
"""
from __future__ import annotations


def test_or_else_releases_an_rvalue_box(emit_c):
    c = emit_c("""
weave make into maybe string:
    return some "x"

weave main into int:
    var s as string is (calling make) or else "y"
    banish s
    return 0
""")
    # The success branch takes the payload, then frees only the box.
    assert "free(_unwrap" in c
    assert ".value = NULL" in c
    assert "is_present = false" in c


def test_or_else_does_not_release_an_lvalue_box(emit_c):
    c = emit_c("""
weave main into int:
    var m as maybe string is some "x"
    var s as string is (m or else "y")
    banish s
    banish m
    return 0
""")
    unwrap = next(line for line in c.splitlines() if "_unwrap" in line)
    assert "free(_unwrap" not in unwrap, unwrap


def test_or_else_releases_a_discarded_result_error(emit_c):
    c = emit_c("""
weave risk into result of int to string:
    return calling err_of with "boom"

weave main into int:
    var n as int is (calling risk) or else 7
    return n
""")
    # The fallback is used, so the error payload and its box are released.
    assert "err_val" in c
    assert "free(_unwrap" in c


def test_try_over_a_void_result_compiles_and_propagates(compile_and_run):
    out = compile_and_run("""
omen Problem:
    Bad with why as string

weave check with ok as bool into result of void to Problem:
    if ok:
        return calling ok_of with 0
    return calling err_of with (with Bad is "nope")

weave run with ok as bool into result of int to Problem:
    try calling check with ok
    return calling ok_of with 42

weave main into int:
    var good as result of int to Problem is calling run with true
    if not good.is_ok:
        return 1
    if good.value != 42:
        return 2
    banish good

    var bad as result of int to Problem is calling run with false
    if bad.is_ok:
        return 3
    # `error` is the `or:` block's contextual binding, so it cannot be used as
    # an ordinary variable name here; `problem` is a borrowed copy of the
    # payload that `banish bad` releases.
    var problem as Problem is bad.error
    judge problem:
        when Bad with why ->
            if (why length) == 0:
                return 4
    banish bad
    return 0
""")
    assert out.strip() == ""


def test_boxing_moves_an_owning_source(emit_c):
    """`some s` moves `s`: the generated C empties the source slot."""
    c = emit_c("""
weave main into int:
    var s as string is "{1}"
    var m as maybe string is some s
    banish m
    banish s
    return 0
""")
    assert "(s).data = NULL" in c, c
    assert "(s).is_owned = 0" in c, c
    assert "if (_maybe" in c and ".value) {" in c, c


def test_or_block_releases_a_result_rvalue_box(emit_c):
    """`or:` over a result rvalue frees the box after copying the payload."""
    c = emit_c("""
weave f into result of string to string:
    return calling ok_of with "x"

weave main into int:
    var s as string is (calling f) or:
        return 1
    banish s
    return 0
""")
    assert "free(_res" in c, c
    assert ".ok_val = NULL" in c, c
    assert ".err_val = NULL" in c, c
    # The payload itself is moved into `s`, not freed with the box.
    assert "pengu_banish_string(&s)" in c, c


def test_boxing_then_banishing_both_does_not_double_free(compile_and_run):
    """The constructor is a move; `banish` of the source is a no-op."""
    out = compile_and_run("""
weave main into int:
    var s as string is "{1}"
    var m as maybe string is some s
    banish m
    banish s

    var t as string is "{2}"
    var r as result of string to string is calling ok_of with t
    banish r
    banish t

    var u as string is "{3}"
    var e as result of string to string is calling err_of with u
    banish e
    banish u
    return 0
""")
    assert out.strip() == "", out


def test_boxing_a_parameter_clones_and_keeps_the_caller_owner(compile_and_run):
    """A callee cannot move the caller's slot: boxing a parameter clones it."""
    out = compile_and_run("""
weave wrap with s as string into maybe string:
    return some s

weave wrap_ok with s as string into result of string to string:
    return calling ok_of with s

weave wrap_err with s as string into result of int to string:
    return calling err_of with s

weave main into int:
    var s as string is "{1}"
    var m as maybe string is calling wrap with s
    banish m
    banish s

    var t as string is "{2}"
    var r as result of string to string is calling wrap_ok with t
    banish r
    banish t

    var u as string is "{3}"
    var e as result of int to string is calling wrap_err with u
    banish e
    banish u
    return 0
""")
    assert out.strip() == "", out


def test_or_block_releases_a_result_error_box(emit_c):
    """The failure path frees the box after copying `error` out of it."""
    c = emit_c("""
weave f into result of int to string:
    return calling err_of with "boom"

weave main into int:
    var n as int is (calling f) or:
        return 1
    return n
""")
    assert "free(_res" in c, c
    assert ".err_val = NULL" in c, c


def test_or_block_can_rebox_the_contextual_error(compile_and_run):
    """`return calling err_of with error` resolves `error` in codegen."""
    out = compile_and_run("""
weave f into result of int to string:
    return calling err_of with "boom"

weave g into result of int to string:
    var n as int is (calling f) or:
        return calling err_of with error
    return calling ok_of with n

weave main into int:
    var r as result of int to string is calling g
    banish r
    return 0
""")
    assert out.strip() == "", out
