"""``std.builder`` — the ``StringBuilder`` surface.

The happy-path programs batch many assertions into one build (compiling is the
expensive part); the panic paths use ``run_pengu`` because they must observe a
non-zero exit status instead of a successful run.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.builder

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
"""


def test_builder_append_and_queries(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling eq_i with (calling sb.len), 0, "new len"
    calling eq_i with (calling sb.capacity), 64, "new cap"
    calling eq_b with (calling sb.is_empty), true, "new empty"
    calling sb.append with ""
    calling eq_i with (calling sb.len), 0, "empty append no-op"

    calling sb.append with "Hola"
    calling sb.append_char with ' '
    calling sb.append with "mundo"
    calling eq_s with (calling sb.to_string), "Hola mundo", "append"
    calling eq_i with (calling sb.len), 10, "len"
    calling eq_i with (calling sb.char_at with 0 to int), 72, "char_at"
    calling eq_i with (calling sb.byte_at with 1 to int), 111, "byte_at"
    calling eq_b with (calling sb.is_empty), false, "not empty"

    calling sb.set_char_at with 0, 'h'
    calling eq_s with (calling sb.to_string), "hola mundo", "set_char_at"
    calling sb.insert_at with 0, ">> "
    calling eq_s with (calling sb.to_string), ">> hola mundo", "insert front"
    calling sb.insert_at with (calling sb.len), "!"
    calling eq_s with (calling sb.to_string), ">> hola mundo!", "insert end"
    calling sb.truncate with 99
    calling eq_i with (calling sb.len), 15, "truncate no-op"
    calling sb.truncate with 14
    calling eq_s with (calling sb.to_string), ">> hola mundo", "truncate"
    calling sb.reverse
    calling eq_s with (calling sb.to_string), "odnum aloh >>", "reverse"
    calling sb.reverse

    var view as slice of byte is calling sb.bytes_view
    calling eq_i with view.length, 13, "view len"
    calling eq_i with ((view at 0) to int), 62, "view byte"

    calling sb.clear
    calling eq_i with (calling sb.len), 0, "clear len"
    calling eq_i with (calling sb.capacity), 64, "clear keeps cap"
    calling eq_s with (calling sb.to_string), "", "clear text"

    var sub as StringBuilder is calling StringBuilder.from_string with "abcdef"
    defer banish sub
    var a as string is calling sub.substring with 1, 4
    defer banish a
    calling eq_s with a, "bcd", "substring"
    var b as string is calling sub.substring with 2, 99
    defer banish b
    calling eq_s with b, "cdef", "substring clamps end"
    var c as string is calling sub.substring with 3, 3
    defer banish c
    calling eq_s with c, "", "substring empty"
    calling spark.println with "DONE"
    return 0
""")


def test_builder_numbers_repeat_and_bytes(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var nums as StringBuilder is calling StringBuilder.with_capacity with 0
    defer banish nums
    calling nums.append_int with 0
    calling nums.append with ","
    calling nums.append_int with -42
    calling nums.append with ","
    calling nums.append_int with 2147483647
    calling nums.append with ","
    calling nums.append_int with -2147483648
    calling nums.append with ","
    calling nums.append_i64 with 9223372036854775807
    calling nums.append with ","
    calling nums.append_i64 with -9223372036854775808
    calling eq_s with (calling nums.to_string), "0,-42,2147483647,-2147483648,9223372036854775807,-9223372036854775808", "ints"

    var fl as StringBuilder is calling StringBuilder.new
    defer banish fl
    calling fl.append_float with 0.0
    calling fl.append with ","
    calling fl.append_float with -0.0
    calling fl.append with ","
    calling fl.append_float with 1.5
    calling fl.append with ","
    calling fl.append_f64 with 3.141592653589793
    calling fl.append with ","
    calling fl.append_float with (1.0 / 0.0)
    calling fl.append with ","
    calling fl.append_float with (-1.0 / 0.0)
    calling fl.append with ","
    calling fl.append_float with (0.0 / 0.0)
    calling eq_s with (calling fl.to_string), "0,-0,1.5,3.14159,inf,-inf,-nan", "floats (%%g, like to string)"

    var bo as StringBuilder is calling StringBuilder.new
    defer banish bo
    calling bo.append_bool with true
    calling bo.append with ","
    calling bo.append_bool with false
    calling eq_s with (calling bo.to_string), "true,false", "bools"

    var rep as StringBuilder is calling StringBuilder.new
    defer banish rep
    calling rep.append_repeat with "ab", 3
    calling rep.append with "|"
    calling rep.append_repeat with "x", 0
    calling rep.append_repeat with "", 10
    calling rep.append_spaces with 3
    calling eq_s with (calling rep.to_string), "ababab|   ", "repeat/spaces"

    var arr as array of byte with size 4 is [65, 66, 0, 67]
    var sl as slice of byte is arr at 0 to 4
    var by as StringBuilder is calling StringBuilder.new
    defer banish by
    calling by.append_bytes with sl
    calling eq_i with (calling by.len), 4, "append_bytes len"
    calling eq_i with ((calling by.byte_at with 2) to int), 0, "append_bytes NUL"
    calling by.append_slice with (bytes of "Z"), 1
    calling eq_i with ((calling by.byte_at with 4) to int), 90, "append_slice"
    calling spark.println with "DONE"
    return 0
""")


def test_builder_growth_finish_and_reuse(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var big as StringBuilder is calling StringBuilder.new
    defer banish big
    var i as int is 0
    while i < 1000:
        calling big.append with "0123456789"
        set i is i + 1
    calling eq_i with (calling big.len), 10000, "big len"
    if (calling big.capacity) < 10000:
        calling spark.println with "FAIL big capacity"
    calling big.shrink_to_fit
    calling eq_i with (calling big.capacity), 10000, "shrink cap"
    var snapshot as string is calling big.to_string
    defer banish snapshot
    calling eq_i with (snapshot length), 10000, "snapshot len"
    calling big.append with "!"
    calling eq_i with (calling big.len), 10001, "usable after to_string"

    var fin as string is calling big.finish
    defer banish fin
    calling eq_i with (fin length), 10001, "finish len"
    calling eq_i with (calling big.len), 0, "finish resets len"
    calling eq_i with (calling big.capacity), 0, "finish resets cap"
    banish big                     # no-op: finish handed the buffer away
    var again as StringBuilder is calling StringBuilder.new
    defer banish again
    calling again.append with "again"
    calling eq_s with (calling again.to_string), "again", "reuse after finish"

    var r as StringBuilder is calling StringBuilder.new
    calling r.append with "abc"
    calling r.reset
    calling eq_i with (calling r.capacity), 0, "reset cap"
    var empty_done as string is calling r.finish
    defer banish empty_done
    calling eq_i with (empty_done length), 0, "finish after reset is empty"
    calling r.append with "z"
    calling eq_s with (calling r.to_string), "z", "reuse after reset/finish"
    banish r
    calling spark.println with "DONE"
    return 0
""")


@pytest.mark.parametrize("body, expected", [
    ('calling sb.insert_at with 99, "x"', "position out of bounds"),
    ('calling sb.set_char_at with 1, \'x\'', "set_char_at"),
    ('calling sb.char_at with 1', "char_at"),
    ('calling sb.byte_at with 1', "byte_at"),
    ('var s as string is calling sb.substring with 2, 1', "start > end"),
])
def test_builder_panics_are_fatal(run_pengu, body, expected):
    res = run_pengu(f"""
import std.spark
import std.builder

weave main into int:
    var sb as StringBuilder is calling StringBuilder.from_string with "a"
    defer banish sb
    {body}
    calling spark.println with "SHOULD NOT REACH"
    return 0
""")
    assert res.returncode != 0
    assert expected in (res.stderr + res.stdout), (res.stdout, res.stderr)


def test_builder_rejects_negative_capacity(run_pengu):
    res = run_pengu("""
import std.builder

weave main into int:
    var sb as StringBuilder is calling StringBuilder.with_capacity with -1
    banish sb
    return 0
""")
    assert res.returncode != 0, res.stdout
