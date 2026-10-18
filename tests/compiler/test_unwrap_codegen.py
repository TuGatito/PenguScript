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
