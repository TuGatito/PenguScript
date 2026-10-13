"""`ord` on a `char`, and the cast rules around `string`.

Two Phase 3.4 fixes live here:

* `LANGUAGE.md` §4.1 documents `ord` as accepting "a single character string or
  char literal", but the checker only accepted a `string`, so `ord c` with
  `c: char` was `E0005` and the C lowering assumed a `PenguString`.
* The checker accepted `string to int` / `to char` / `to float`, for which the C
  backend has no lowering: it emitted `(int32_t)(PenguString)` (invalid C) for
  the integer targets and a silent `0` for `float`.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_ord_accepts_a_char_operand(parse_and_check):
    errors, _, _ = parse_and_check("""
weave code_of with c as char into int:
    return ord c

weave literal_code into int:
    return ord 'A'
""")
    assert errors == [], [str(e) for e in errors]


def test_ord_still_accepts_a_one_character_string(parse_and_check):
    errors, _, _ = parse_and_check("""
weave code_of with s as string into int:
    return ord s

weave literal_code into int:
    return ord "a"
""")
    assert errors == [], [str(e) for e in errors]


def test_ord_rejects_a_non_character_operand(parse_and_check):
    errors, _, _ = parse_and_check("""
weave bad into int:
    return ord 5
""")
    assert any(e.code == "E0005" for e in errors), [e.code for e in errors]


def test_ord_on_char_reads_the_unsigned_byte(emit_c):
    """`ord c` must not go through the `PenguString` lowering (`(c).data`)."""
    c = emit_c("""
weave code_of with ch as char into int:
    return ord ch
""")
    assert "((int32_t)((unsigned char)(ch)))" in c
    assert "(ch).data" not in c


def test_string_to_number_casts_are_rejected(parse_and_check):
    """Text to number is `parse_int`/`parse_float`/`ord`, never a cast."""
    for target in ("int", "i64", "float", "f64", "char", "byte"):
        errors, _, _ = parse_and_check(f"""
weave bad with s as string into {target}:
    return s to {target}
""")
        assert any(e.code == "E0005" for e in errors), (target, [e.code for e in errors])


def test_number_and_char_casts_still_work(parse_and_check):
    """`char -> int`, `int -> char`, `byte -> char` and `char -> string` stay."""
    errors, _, _ = parse_and_check("""
weave round_trip with c as char, b as byte into char:
    var n as int is c to int
    var m as int is b to int
    var s as string is c to string
    if s == "":
        return b to char
    return (n + m) to char
""")
    assert errors == [], [str(e) for e in errors]
