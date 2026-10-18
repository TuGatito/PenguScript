"""``std.json`` — edge cases not covered by the conformance corpus."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = '''
import std.spark
import std.json

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave eq_b with got as bool, name as string into void:
    if not got:
        calling spark.println with "FAIL {name}"
'''


def test_parse_errors_and_options(compile_and_run):
    out = compile_and_run(_PRE + r'''
weave fails with s as string, kind as json.JsonErrorKind, name as string into void:
    var r as result of JsonValue to json.JsonError is calling json.parse with s
    if r.is_ok:
        calling spark.println with "FAIL {name}: accepted"
    else:
        if r.error.kind != kind:
            calling spark.println with "FAIL {name}: wrong kind"
        if r.error.offset < 0:
            calling spark.println with "FAIL {name}: offset"
    banish r

weave main into int:
    calling fails with "", json.JsonErrorKind.UnexpectedEof, "empty"
    calling fails with "01", json.JsonErrorKind.InvalidNumber, "leading zero"
    calling fails with "-", json.JsonErrorKind.InvalidNumber, "lone minus"
    calling fails with "1e", json.JsonErrorKind.InvalidNumber, "lone exponent"
    calling fails with "1e9999", json.JsonErrorKind.InvalidNumber, "float range"
    calling fails with "9223372036854775808", json.JsonErrorKind.IntegerOverflow, "int overflow"
    calling fails with "\"\\uD83D\"", json.JsonErrorKind.InvalidUnicode, "high surrogate"
    calling fails with "\"\\uDE00\"", json.JsonErrorKind.InvalidUnicode, "low surrogate"
    calling fails with "\"\\q\"", json.JsonErrorKind.InvalidEscape, "escape"
    calling fails with "\"abc", json.JsonErrorKind.UnexpectedEof, "unterminated"
    calling fails with "nul", json.JsonErrorKind.InvalidLiteral, "literal"
    calling fails with "[1,2,]", json.JsonErrorKind.UnexpectedChar, "trailing comma"
    calling fails with r"""{"a":1}x""", json.JsonErrorKind.TrailingCharacters, "trailing"
    var o as json.ParseOptions is calling json.default_parse_options
    set o.allow_comments is true
    var c as result of JsonValue to json.JsonError is calling json.parse_with with "/*x*/ //y\n[1]", o
    calling eq_b with c.is_ok, "comments"
    banish c
    set o.allow_comments is false
    set o.allow_trailing_commas is true
    var t as result of JsonValue to json.JsonError is calling json.parse_with with "[1,]", o
    calling eq_b with t.is_ok, "trailing comma option"
    banish t
    set o.allow_trailing_commas is false
    set o.allow_non_standard is true
    var n as result of JsonValue to json.JsonError is calling json.parse_with with "NaN", o
    calling eq_b with n.is_ok, "NaN option"
    if n.is_ok:
        var nv as JsonValue is n.value
        var nf as maybe f64 is calling nv.as_float
        calling eq_b with (nf.is_present and (nf.value != nf.value)), "NaN value"
        banish nf
    banish n
    set o.allow_non_standard is false
    set o.strict is false
    var sc as result of JsonValue to json.JsonError is calling json.parse_with with "\"a\u0001b\"", o
    calling eq_b with sc.is_ok, "non-strict control"
    banish sc
    set o.strict is true
    set o.max_depth is 1
    var d as result of JsonValue to json.JsonError is calling json.parse_with with "[[1]]", o
    calling eq_b with (not d.is_ok), "depth"
    banish d
    calling spark.println with "DONE"
    return 0
''')


def test_serialize_and_queries(compile_and_run):
    out = compile_and_run(_PRE + r'''
weave main into int:
    var root as JsonValue is calling JsonValue.empty_object
    defer banish root
    var arr as JsonValue is calling JsonValue.empty_array
    calling arr.push_json with (calling JsonValue.int_val with 1)
    calling arr.push_json with (calling JsonValue.float_val with 0.1)
    calling arr.push_json with (calling JsonValue.string_val with "ñ😀")
    calling root.put_json with "b", arr
    calling root.put_json with "a", (calling JsonValue.bool_val with true)
    var compact as string is calling json.stringify with root
    calling eq_s with compact, r"""{"b":[1,0.1,"ñ😀"],"a":true}""", "compact"
    banish compact
    var pretty as string is calling json.stringify_pretty with root, 2
    calling eq_b with (pretty.length) > 0, "pretty"
    banish pretty
    var o as json.SerializeOptions is calling json.default_serialize_options
    set o.sort_keys is true
    set o.ensure_ascii is true
    set o.escape_slash is true
    set o.trailing_newline is true
    var opt as string is calling json.stringify_with with root, o
    calling eq_b with (calling contains with opt, "\\u00f1"), "ensure_ascii"
    calling eq_b with (calling contains with opt, "\\ud83d\\ude00"), "surrogate"
    var sorted_a as int is calling find_byte with opt, 97
    var sorted_b as int is calling find_byte with opt, 98
    calling eq_b with (sorted_a < sorted_b), "sorted"
    if (opt at ((opt length) - 1)) != "\n":
        calling spark.println with "FAIL trailing newline"
    banish opt
    var nan as JsonValue is calling JsonValue.float_val with (0.0 / 0.0)
    var tr as result of string to json.JsonError is calling json.try_stringify with nan, o
    calling eq_b with (not tr.is_ok), "try_stringify NaN"
    banish tr
    banish nan
    var ptr as JsonValue is calling json.get_or_null with root, "b"
    var at1 as JsonValue is calling json.at_or_null with ptr, 1
    var f as maybe f64 is calling at1.as_number
    calling eq_b with ((f or else 0.0) == 0.1), "as_number"
    banish f
    banish at1
    var i1 as JsonValue is calling json.at_or_null with ptr, 0
    var n1 as JsonValue is calling JsonValue.float_val with 1.0
    calling eq_b with (not calling i1.equals with n1), "strict int/float"
    calling eq_b with (calling i1.equals_numeric with n1), "numeric eq"
    banish n1
    banish i1
    var clone as JsonValue is calling root.clone
    calling eq_b with (calling root.equals with clone), "clone"
    banish clone
    var keys as list of string is calling root.keys
    calling eq_i with keys.len, 2, "keys"
    calling json.free_strings with keys
    banish ptr
    var ignored as int is judge root:
        when Obj with entries ->
            var vals as list of JsonValue is calling root.values
            calling eq_i with vals.len, 2, "values"
            calling json.free_values with vals
            0
        else -> 0
    calling spark.println with "DONE"
    return 0

weave contains with s as string, needle as string into bool:
    return (calling find_sub with s, needle) >= 0

weave find_byte with s as string, b as int into int:
    var raw as ref to frozen byte is bytes of s
    var i as int is 0
    while i < (s length):
        if ((raw at i) to int) == b:
            return i
        set i is i + 1
    return -1

weave find_sub with s as string, needle as string into int:
    var n as int is s length
    var m as int is needle length
    var i as int is 0
    while i + m <= n:
        var same as bool is true
        var k as int is 0
        while k < m and same:
            var raw as ref to frozen byte is bytes of s
            var nb as ref to frozen byte is bytes of needle
            if ((raw at (i + k)) to int) != ((nb at k) to int):
                set same is false
            set k is k + 1
        if same:
            return i
        set i is i + 1
    return -1
''')


def test_arena_and_schema(compile_and_run):
    out = compile_and_run(_PRE + r'''
import std.arena

weave main into int:
    var a as Arena is calling Arena.new
    defer calling a.free
    defer banish a
    var r as result of JsonValue to json.JsonError is calling json.parse_in_arena with r"""{"x":[1,{"y":"z"}]}""", (sigil of a)
    if not r.is_ok:
        calling spark.println with "FAIL arena parse"
        banish r
        return 1
    var root as JsonValue is r.value
    var p as maybe JsonValue is calling root.pointer with "/x/1/y"
    if p.is_present:
        var pv as JsonValue is calling json.take_value with (sigil of p)
        var ps as maybe string is calling pv.as_string
        var text as string is calling json.take_string with (sigil of ps)
        calling eq_s with text, "z", "arena pointer"
        banish text
        banish pv
    else:
        calling spark.println with "FAIL arena pointer"
    banish root
    calling json.discard_result_box with (sigil of r)
    var schema as JsonValue is calling JsonValue.empty_object
    calling schema.put_json with "type", (calling JsonValue.string_val with "array")
    var value as JsonValue is calling JsonValue.empty_array
    calling value.push_json with (calling JsonValue.int_val with 1)
    var errs as list of string is calling json.validate_schema with value, schema
    calling eq_i with errs.len, 0, "schema ok"
    calling json.free_strings with errs
    calling value.push_json with (calling JsonValue.string_val with "x")
    set errs is calling json.validate_schema with value, schema
    calling eq_i with errs.len, 1, "schema item type"
    calling json.free_strings with errs
    banish value
    banish schema
    calling spark.println with "DONE"
    return 0
''')
