"""End-to-end tests for ``std.lingua`` (UTF-8 over codepoints).

Each test compiles one PenguScript program that carries many assertions: C
compilation is the expensive step, so the suite batches. A failed assertion
panics inside the program, which makes ``compile_and_run`` fail with the
program's own message.
"""
from __future__ import annotations

import pytest


def test_decode_encode_queries_and_utf16(compile_and_run):
    source = r'''
import std.spark
import std.scrolls
import std.ward
import std.lingua

weave cp with value as u32 into Codepoint:
    return value to Codepoint

weave roundtrip with original as string into void:
    var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with original
    calling ward.assert_true with decoded.is_ok
    var cps as list of Codepoint is decoded.value
    var encoded as result of string to LinguaError is calling lingua.encode with cps
    calling ward.assert_true with encoded.is_ok
    var text as string is encoded.value
    calling ward.assert_eq_int with (calling scrolls.compare with text, original), 0
    banish encoded
    banish decoded

weave main into int:
    calling roundtrip with ""
    calling roundtrip with "hola"
    calling roundtrip with "ñ"
    calling roundtrip with "日本語"
    calling roundtrip with "😀"
    calling roundtrip with "año 😀 日本語"

    calling ward.assert_eq_int with (calling lingua.codepoint_count with "ñ😀"), 2
    calling ward.assert_eq_int with (calling lingua.codepoint_count with ""), 0
    calling ward.assert_eq_int with (calling lingua.utf16_length with "😀"), 2
    calling ward.assert_eq_int with (calling lingua.utf16_length with "ñ"), 1
    calling ward.assert_eq_int with (calling lingua.utf16_length with "a😀"), 3

    let (high, low) is calling lingua.to_utf16 with (0x1F600 to Codepoint)
    calling ward.assert_eq_int with (high to int), 0xD83D
    calling ward.assert_eq_int with (low to int), 0xDE00

    calling ward.assert_true with (calling lingua.is_ascii with (calling cp with 0x41))
    calling ward.assert_false with (calling lingua.is_ascii with (calling cp with 0xF1))
    calling ward.assert_true with (calling lingua.is_bmp with (calling cp with 0xFFFF))
    calling ward.assert_false with (calling lingua.is_bmp with (calling cp with 0x10000))
    calling ward.assert_true with (calling lingua.is_letter with (calling cp with 0x65E5))
    calling ward.assert_true with (calling lingua.is_letter with (calling cp with 0x0416))
    calling ward.assert_false with (calling lingua.is_letter with (calling cp with 0x31))
    calling ward.assert_true with (calling lingua.is_digit with (calling cp with 0x0661))
    calling ward.assert_true with (calling lingua.is_whitespace with (calling cp with 0x3000))
    calling ward.assert_true with (calling lingua.is_punctuation with (calling cp with 0x2E))
    calling ward.assert_true with (calling lingua.is_symbol with (calling cp with 0x2192))
    calling ward.assert_true with (calling lingua.is_control with (calling cp with 0x0A))
    calling ward.assert_true with (calling lingua.is_surrogate with (calling cp with 0xD800))

    var from as result of Codepoint to LinguaError is calling lingua.from_u32 with 0x1F600
    calling ward.assert_true with from.is_ok
    calling ward.assert_eq_int with ((from.value) to u32) to int, 0x1F600
    banish from
    var surrogate as result of Codepoint to LinguaError is calling lingua.from_u32 with 0xD800
    calling ward.assert_false with surrogate.is_ok
    banish surrogate
    var over as result of Codepoint to LinguaError is calling lingua.from_u32 with 0x110000
    calling ward.assert_false with over.is_ok
    banish over

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_validation_errors_and_offsets(compile_and_run):
    source = r'''
import std.spark
import std.ward
import std.lingua

weave kind_of with s as string into int:
    var r as result of list of Codepoint to LinguaError is calling lingua.decode with s
    if r.is_ok:
        banish r
        return -1
    var e as LinguaError is r.error
    var kind as int is judge e:
        when InvalidByte -> 1
        when TruncatedSequence -> 2
        when OverlongEncoding -> 3
        when SurrogateCodepoint -> 4
        when CodepointOutOfRange -> 5
        when IndexOutOfRange -> 6
    banish r
    return kind

weave offset_of with s as string into int:
    var r as result of list of Codepoint to LinguaError is calling lingua.decode with s
    if r.is_ok:
        banish r
        return -1
    var e as LinguaError is r.error
    var offset as int is judge e:
        when InvalidByte with offset -> offset
        when TruncatedSequence with offset -> offset
        when OverlongEncoding with offset -> offset
        when SurrogateCodepoint with offset -> offset
        when CodepointOutOfRange with offset -> offset
        when IndexOutOfRange with index -> index
    banish r
    return offset

weave main into int:
    calling ward.assert_true with (calling lingua.is_valid with "")
    calling ward.assert_true with (calling lingua.is_valid with "ñ😀")
    calling ward.assert_false with (calling lingua.is_valid with "\xFF")
    calling ward.assert_false with (calling lingua.is_valid with "\x80")

    var good as result of void to LinguaError is calling lingua.validate with "ñ"
    calling ward.assert_true with good.is_ok
    banish good
    var bad as result of void to LinguaError is calling lingua.validate with "a\xFF"
    calling ward.assert_false with bad.is_ok
    banish bad

    calling ward.assert_eq_int with (calling kind_of with "\xFF"), 1
    calling ward.assert_eq_int with (calling kind_of with "\xE2\x82"), 2
    calling ward.assert_eq_int with (calling kind_of with "\xC0\x80"), 3
    calling ward.assert_eq_int with (calling kind_of with "\xED\xA0\x80"), 4
    calling ward.assert_eq_int with (calling kind_of with "\xF4\x90\x80\x80"), 5
    calling ward.assert_eq_int with (calling kind_of with "ok"), -1

    calling ward.assert_eq_int with (calling offset_of with "a\xFF"), 1
    calling ward.assert_eq_int with (calling offset_of with "ab\xC0\x80"), 2

    var at as result of (Codepoint, int) to LinguaError is calling lingua.codepoint_at with "año", 1
    calling ward.assert_true with at.is_ok
    let (cp, used) is at.value
    calling ward.assert_eq_int with (cp to u32) to int, 0xF1
    calling ward.assert_eq_int with used, 2
    banish at

    var past as result of (Codepoint, int) to LinguaError is calling lingua.codepoint_at with "a", 9
    calling ward.assert_false with past.is_ok
    banish past

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_navigation_and_graphemes(compile_and_run):
    source = r'''
import std.spark
import std.ward
import std.lingua

weave main into int:
    var off as result of int to LinguaError is calling lingua.byte_offset_of with "año", 2
    calling ward.assert_true with off.is_ok
    calling ward.assert_eq_int with off.value, 3
    banish off

    var zero as result of int to LinguaError is calling lingua.byte_offset_of with "año", 0
    calling ward.assert_eq_int with zero.value, 0
    banish zero

    var missing as result of int to LinguaError is calling lingua.byte_offset_of with "año", 9
    calling ward.assert_false with missing.is_ok
    banish missing

    var next as result of (Codepoint, int) to LinguaError is calling lingua.next_codepoint with "año", 0
    let (next_cp, next_off) is next.value
    calling ward.assert_eq_int with (next_cp to u32) to int, 0x61
    calling ward.assert_eq_int with next_off, 1
    banish next

    var prev as result of (Codepoint, int) to LinguaError is calling lingua.prev_codepoint with "año", 3
    let (prev_cp, prev_off) is prev.value
    calling ward.assert_eq_int with (prev_cp to u32) to int, 0xF1
    calling ward.assert_eq_int with prev_off, 1
    banish prev

    var bad_prev as result of (Codepoint, int) to LinguaError is calling lingua.prev_codepoint with "año", 2
    calling ward.assert_false with bad_prev.is_ok
    banish bad_prev

    var prefix as result of (list of Codepoint, int) to LinguaError is calling lingua.decode_prefix with "añb", 2
    let (cps, used) is prefix.value
    calling ward.assert_eq_int with cps.len, 2
    calling ward.assert_eq_int with used, 3
    banish prefix

    calling ward.assert_eq_int with (calling lingua.grapheme_count with "a\u0301"), 1
    calling ward.assert_eq_int with (calling lingua.grapheme_count with "😀"), 1
    calling ward.assert_eq_int with (calling lingua.grapheme_count with "ab"), 2
    calling ward.assert_eq_int with (calling lingua.grapheme_count with "\xFF"), -1

    calling spark.println with "DONE"
    return 0
'''
    assert "DONE" in compile_and_run(source)


def test_decode_fuzz_never_panics_and_roundtrips(compile_and_run):
    """1 000 pseudo-random byte strings: decode is total, valid ones round-trip."""
    source = r'''
import std.spark
import std.builder
import std.scrolls
import std.lot
import std.ward
import std.lingua

weave main into int:
    calling lot.seed with 12345
    var round as int is 0
    var rejected as int is 0
    var iter as int is 0
    while iter < 1000:
        var sb as StringBuilder is calling StringBuilder.new
        var length as int is (calling lot.rand_between with 0, 24)
        var j as int is 0
        while j < length:
            var b as int is calling lot.rand_between with 0, 255
            calling sb.append_char with (b to char)
            set j is j + 1
        var raw as string is calling sb.finish
        banish sb
        var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with raw
        if decoded.is_ok:
            var cps as list of Codepoint is decoded.value
            var encoded as result of string to LinguaError is calling lingua.encode with cps
            calling ward.assert_true with encoded.is_ok
            var text as string is encoded.value
            calling ward.assert_eq_int with (calling scrolls.compare with text, raw), 0
            banish encoded
            banish decoded
            set round is round + 1
        else:
            banish decoded
            set rejected is rejected + 1
        banish raw
        set iter is iter + 1
    calling ward.assert_eq_int with iter, 1000
    calling ward.assert_eq_int with round + rejected, 1000
    calling ward.assert_true with round > 0
    calling spark.println with "round={round} rejected={rejected}"
    calling spark.println with "DONE"
    return 0
'''
    out = compile_and_run(source)
    assert "DONE" in out
    assert "FAIL" not in out
