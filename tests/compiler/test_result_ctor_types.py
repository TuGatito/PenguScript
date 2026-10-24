"""Type checking for the `ok_of` / `err_of` result constructors.

A result declares both payload types, and the constructor only supplies one of
them.  The missing side comes from the expected type; the supplied side must be
compatible with it.  Before this regression test the checker returned the
expected `ResultType` unconditionally, so `ok_of "text"` inside
`result of int to string` boxed a `PenguString` that consumers read as an
`int32_t`.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def _codes(errors):
    return [getattr(error, "code", None) for error in errors]


def test_ok_of_rejects_a_payload_of_the_wrong_type(parse_and_check):
    errors, _, _ = parse_and_check("""
weave bad into result of int to string:
    return calling ok_of with "not an int"

weave main into int:
    return 0
""")
    assert _codes(errors) == ["E0005"], errors


def test_err_of_rejects_a_payload_of_the_wrong_type(parse_and_check):
    errors, _, _ = parse_and_check("""
weave bad into result of int to string:
    return calling err_of with 42

weave main into int:
    return 0
""")
    assert _codes(errors) == ["E0005"], errors


def test_a_bare_result_uses_the_error_side_and_rejects_a_string(parse_and_check):
    # `result of int` is the legacy spelling whose error side is `error`
    # (`const char*`).  It must not degrade to `any` and accept every payload.
    errors, _, _ = parse_and_check("""
weave bad into result of int:
    return calling err_of with "boom"

weave main into int:
    return 0
""")
    assert _codes(errors) == ["E0005"], errors


def test_result_of_void_accepts_the_dummy_success_payload(parse_and_check):
    # The success side of `result of void` has no payload; the documented idiom
    # boxes a dummy that is never read.
    errors, _, _ = parse_and_check("""
weave check into result of void to string:
    return calling ok_of with 0

weave main into int:
    var r as result of void to string is calling check
    banish r
    return 0
""")
    assert errors == [], errors
