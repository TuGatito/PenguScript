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


def test_narrow_and_pointer_sized_casts_are_casts_not_ranges(emit_c):
    """`x to T` for every documented scalar alias lowers to a C cast.

    The cast detector used a hard-coded list of primitive names that left out
    `usize`/`isize`/`size_t` and the fixed-width `int8`..`uint64` spellings, so
    `(n length) to usize` was emitted as a *range*
    (`(PenguRange){ .start = ..., .end = (int64_t)(usize) }`) and the C compiler
    reported an undeclared `usize`.  The predicate now comes from
    `canonical_primitive_name`, the same alias table the type system uses.
    """
    c = emit_c("""
weave pointer_sized with n as int into usize:
    return n to usize

weave signed_sized with n as int into isize:
    return n to isize

weave c_spelling with n as int into size_t:
    return n to size_t

weave narrow_signed with n as int into i8:
    return n to i8

weave narrow_unsigned with n as int into u16:
    return n to u16

weave fixed_width with n as int into uint64:
    return n to uint64
""")
    assert "(PenguRange){" not in c, c
    assert "((size_t)(n))" in c, c
    assert "((intptr_t)(n))" in c, c
    assert "((int8_t)(n))" in c, c
    assert "((uint16_t)(n))" in c, c
    assert "((uint64_t)(n))" in c, c
