"""End-to-end tests for ``std.regulus`` (tiny-regex-c wrapper)."""
from __future__ import annotations


def test_compile_match_and_ranges(compile_and_run):
    source = r'''
import std.spark
import std.scrolls
import std.ward
import std.regulus

weave same with a as string, b as string into void:
    calling ward.assert_eq_int with (calling scrolls.compare with a, b), 0

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    calling ward.assert_true with cr.is_ok
    var rx as Regex is cr.value
    defer banish cr
    calling ward.assert_eq_int with (calling scrolls.compare with (calling rx.pattern), "[0-9]+"), 0
    calling ward.assert_true with (calling rx.is_match with "abc123")
    calling ward.assert_false with (calling rx.is_match with "abcdef")

    var first as maybe Match is calling rx.match with "abc123def456"
    calling ward.assert_true with (first is present)
    calling ward.assert_eq_int with first.value.start, 3
    calling ward.assert_eq_int with first.value.end, 6
    banish first

    var all as list of Match is calling rx.matches with "abc123def456"
    calling ward.assert_eq_int with all.len, 2
    var m0 as Match is all at 0
    var m1 as Match is all at 1
    calling ward.assert_eq_int with m0.start, 3
    calling ward.assert_eq_int with m1.start, 9
    banish all

    var at as maybe Match is calling rx.match_at with "abc123def456", 6
    calling ward.assert_true with (at is present)
    calling ward.assert_eq_int with at.value.start, 9
    banish at

    var none as maybe Match is calling rx.match with "abcdef"
    calling ward.assert_false with (none is present)
    banish none
    var out as maybe Match is calling rx.match_at with "abc", 99
    calling ward.assert_false with (out is present)
    banish out

    var anchored as result of Regex to RegexError is calling Regex.compile with "^abc$"
    var arx as Regex is anchored.value
    defer banish anchored
    calling ward.assert_true with (calling arx.is_match with "abc")
    calling ward.assert_false with (calling arx.is_match with "abcd")

    var dot as result of Regex to RegexError is calling Regex.compile with "a.b"
    var drx as Regex is dot.value
    defer banish dot
    calling ward.assert_true with (calling drx.is_match with "axb")
    calling ward.assert_false with (calling drx.is_match with "ab")

    var classes as result of Regex to RegexError is calling Regex.compile with "\\d\\w\\s"
    var crx as Regex is classes.value
    defer banish classes
    calling ward.assert_true with (calling crx.is_match with "1a ")

    var empty as result of Regex to RegexError is calling Regex.compile with ""
    calling ward.assert_true with empty.is_ok
    var erx as Regex is empty.value
    defer banish empty
    calling ward.assert_true with (calling erx.is_match with "")
    calling ward.assert_true with (calling erx.is_match with "anything")
    var empties as list of Match is calling erx.matches with "ab"
    calling ward.assert_eq_int with empties.len, 3
    banish empties

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_replace_split_escape_and_convenience(compile_and_run):
    source = r'''
import std.spark
import std.scrolls
import std.ward
import std.regulus

weave same with a as string, b as string into void:
    calling ward.assert_eq_int with (calling scrolls.compare with a, b), 0

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    var rx as Regex is cr.value
    defer banish cr

    var one as string is calling rx.replace_first with "abc123def456", "N"
    calling same with one, "abcNdef456"
    banish one
    var every as string is calling rx.replace_all with "abc123def456", "N"
    calling same with every, "abcNdefN"
    banish every
    var untouched as string is calling rx.replace_all with "abcdef", "N"
    calling same with untouched, "abcdef"
    banish untouched

    var ws as result of Regex to RegexError is calling Regex.compile with "\\s+"
    var wrx as Regex is ws.value
    defer banish ws
    var parts as list of string is calling wrx.split with "a b  c"
    calling ward.assert_eq_int with parts.len, 3
    calling same with (parts at 0), "a"
    calling same with (parts at 1), "b"
    calling same with (parts at 2), "c"
    var i as int is 0
    while i < parts.len:
        banish (parts at i)
        set i is i + 1
    banish parts

    var commas as result of Regex to RegexError is calling Regex.compile with ","
    var crx as Regex is commas.value
    defer banish commas
    var fields as list of string is calling crx.split with ",a,,b,"
    calling ward.assert_eq_int with fields.len, 5
    calling same with (fields at 0), ""
    calling same with (fields at 4), ""
    set i is 0
    while i < fields.len:
        banish (fields at i)
        set i is i + 1
    banish fields

    var quoted as string is calling regulus.escape with "a.b*c"
    calling same with quoted, r"a\.b\*c"
    banish quoted
    var meta as string is calling regulus.escape with r".^$*+?()[]{}|\-"
    var literal as result of Regex to RegexError is calling Regex.compile with meta
    calling ward.assert_true with literal.is_ok
    var lrx as Regex is literal.value
    defer banish literal
    calling ward.assert_true with (calling lrx.is_match with r".^$*+?()[]{}|\-")
    banish meta

    var one_shot as result of bool to RegexError is calling regulus.is_match with "[0-9]+", "abc123"
    calling ward.assert_true with one_shot.is_ok
    calling ward.assert_true with one_shot.value
    banish one_shot
    var bad_shot as result of bool to RegexError is calling regulus.is_match with "[", "abc"
    calling ward.assert_false with bad_shot.is_ok
    banish bad_shot

    var found as result of maybe Match to RegexError is calling regulus.find_first with "[0-9]+", "abc123"
    calling ward.assert_true with found.is_ok
    calling ward.assert_true with (found.value is present)
    calling ward.assert_eq_int with found.value.value.start, 3
    banish found
    var missing as result of maybe Match to RegexError is calling regulus.find_first with "[0-9]+", "abc"
    calling ward.assert_true with missing.is_ok
    calling ward.assert_false with (missing.value is present)
    banish missing

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_errors_and_limits(compile_and_run):
    source = r'''
import std.spark
import std.builder
import std.ward
import std.regulus

weave kind_of with pattern as string into int:
    var r as result of Regex to RegexError is calling Regex.compile with pattern
    if r.is_ok:
        banish r
        return 0
    var e as RegexError is r.error
    var kind as int is judge e:
        when PatternTooLong -> 2
        when OutOfMemory -> 3
        when InvalidSyntax with position -> 1
    banish r
    return kind

weave main into int:
    calling ward.assert_eq_int with (calling kind_of with "[a-z"), 1
    calling ward.assert_eq_int with (calling kind_of with "ab["), 1
    calling ward.assert_eq_int with (calling kind_of with "abc\\"), 1
    calling ward.assert_eq_int with (calling kind_of with "abc"), 0

    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    var i as int is 0
    while i < 300:
        calling sb.append with "a"
        set i is i + 1
    var long_pattern as string is calling sb.to_string
    defer banish long_pattern
    calling ward.assert_eq_int with (calling kind_of with long_pattern), 2

    var valid as result of Regex to RegexError is calling Regex.compile with "a+"
    calling ward.assert_true with valid.is_ok
    var rx as Regex is valid.value
    defer banish valid
    calling ward.assert_true with (calling rx.is_match with "baa")

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_fuzz_escape_is_always_a_literal(compile_and_run):
    """500 pseudo-random literals: escape(p) compiles and matches p, never more."""
    source = r'''
import std.spark
import std.builder
import std.scrolls
import std.lot
import std.ward
import std.regulus

weave main into int:
    calling lot.seed with 987654
    var iter as int is 0
    while iter < 500:
        var sb as StringBuilder is calling StringBuilder.new
        var length as int is (calling lot.rand_between with 0, 20)
        var j as int is 0
        while j < length:
            var b as int is calling lot.rand_between with 32, 126
            calling sb.append_char with (b to char)
            set j is j + 1
        var literal as string is calling sb.finish
        banish sb

        var quoted as string is calling regulus.escape with literal
        var compiled as result of Regex to RegexError is calling Regex.compile with quoted
        calling ward.assert_true with compiled.is_ok
        var rx as Regex is compiled.value
        calling ward.assert_true with (calling rx.is_match with literal)

        banish compiled
        banish quoted
        banish literal
        set iter is iter + 1
    calling ward.assert_eq_int with iter, 500
    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)
