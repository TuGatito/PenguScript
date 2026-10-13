"""`std.littera` — the ASCII classification predicates.

Two programs: the character classes (`is_digit`, `is_alpha`, `is_alnum`,
`is_upper`, `is_lower`, `is_hex_digit`) and the "shape" predicates (`is_space`,
`is_whitespace`, `is_control`, `is_printable`, `is_punctuation`, `is_ascii`),
each with its boundary neighbours.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.littera

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_character_classes(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as char is '0'
    var nine as char is '9'
    var below_digit as char is '/'
    var above_digit as char is ':'
    var a as char is 'a'
    var z as char is 'z'
    var big_a as char is 'A'
    var big_z as char is 'Z'
    var backtick as char is '`'
    var brace as char is '{'
    var nul as char is '\\0'
    var del as char is '\\x7F'
    calling eq_b with (calling zero.is_digit), true, "0 is digit"
    calling eq_b with (calling nine.is_digit), true, "9 is digit"
    calling eq_b with (calling below_digit.is_digit), false, "/ is not digit"
    calling eq_b with (calling above_digit.is_digit), false, ": is not digit"
    calling eq_b with (calling a.is_alpha), true, "a is alpha"
    calling eq_b with (calling z.is_alpha), true, "z is alpha"
    calling eq_b with (calling big_a.is_alpha), true, "A is alpha"
    calling eq_b with (calling big_z.is_alpha), true, "Z is alpha"
    calling eq_b with (calling backtick.is_alpha), false, "backtick is not alpha"
    calling eq_b with (calling brace.is_alpha), false, "{ is not alpha"
    calling eq_b with (calling a.is_alnum), true, "a is alnum"
    calling eq_b with (calling nine.is_alnum), true, "9 is alnum"
    calling eq_b with (calling above_digit.is_alnum), false, ": is not alnum"
    calling eq_b with (calling a.is_upper), false, "a is not upper"
    calling eq_b with (calling big_a.is_upper), true, "A is upper"
    calling eq_b with (calling a.is_lower), true, "a is lower"
    calling eq_b with (calling big_a.is_lower), false, "A is not lower"
    calling eq_b with (calling a.is_hex_digit), true, "a is hex"
    calling eq_b with (calling big_z.is_hex_digit), false, "Z is not hex"
    calling eq_b with (calling nul.is_ascii), true, "NUL is ascii"
    calling eq_b with (calling del.is_ascii), true, "DEL is ascii"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_shape_predicates(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var sp as char is ' '
    var tab as char is '\\t'
    var nl as char is '\\n'
    var cr as char is '\\r'
    var ff as char is '\\f'
    var vt as char is '\\v'
    var a as char is 'a'
    var bang as char is '!'
    var tilde as char is '~'
    var del as char is '\\x7F'
    var esc as char is '\\x1B'
    calling eq_b with (calling sp.is_space), true, "space is space"
    calling eq_b with (calling tab.is_space), false, "tab is not space"
    calling eq_b with (calling tab.is_whitespace), true, "tab is whitespace"
    calling eq_b with (calling nl.is_whitespace), true, "newline is whitespace"
    calling eq_b with (calling cr.is_whitespace), true, "CR is whitespace"
    calling eq_b with (calling ff.is_whitespace), true, "FF is whitespace"
    calling eq_b with (calling vt.is_whitespace), true, "VT is whitespace"
    calling eq_b with (calling a.is_whitespace), false, "a is not whitespace"
    calling eq_b with (calling nl.is_control), true, "newline is control"
    calling eq_b with (calling esc.is_control), true, "ESC is control"
    calling eq_b with (calling del.is_control), true, "DEL is control"
    calling eq_b with (calling sp.is_control), false, "space is not control"
    calling eq_b with (calling sp.is_printable), true, "space is printable"
    calling eq_b with (calling tilde.is_printable), true, "tilde is printable"
    calling eq_b with (calling del.is_printable), false, "DEL is not printable"
    calling eq_b with (calling nl.is_printable), false, "newline is not printable"
    calling eq_b with (calling bang.is_punctuation), true, "! is punctuation"
    calling eq_b with (calling tilde.is_punctuation), true, "~ is punctuation"
    calling eq_b with (calling a.is_punctuation), false, "a is not punctuation"
    calling eq_b with (calling sp.is_punctuation), false, "space is not punctuation"
    calling eq_b with (calling del.is_punctuation), false, "DEL is not punctuation"
    var b as byte is 200
    var high as char is (b to char)
    calling eq_b with (calling high.is_ascii), false, "0xC8 is not ascii"
    calling eq_b with (calling high.is_printable), false, "0xC8 is not printable"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
