"""``std.sourcemap`` — offset/line/column mapping and CRLF handling."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.sourcemap

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


def test_sourcemap_positions_offsets_and_lines(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var m as SourceMap is calling SourceMap.from_source with "a\\nb"
    defer banish m
    calling eq_i with (calling m.line_count), 2, "line_count"
    calling eq_i with (calling m.source_len), 3, "source_len"
    calling eq_s with (calling m.source), "a\\nb", "source copy"

    var p0 as Position is calling m.position_at with 0
    calling eq_i with p0.line, 1, "p0 line"
    calling eq_i with p0.col, 1, "p0 col"
    var p1 as Position is calling m.position_at with 1
    calling eq_i with p1.line, 1, "p1 line"
    calling eq_i with p1.col, 2, "p1 col (newline byte)"
    var p2 as Position is calling m.position_at with 2
    calling eq_i with p2.line, 2, "p2 line"
    calling eq_i with p2.col, 1, "p2 col"
    var p3 as Position is calling m.position_at with 3
    calling eq_i with p3.line, 2, "p3 line"
    calling eq_i with p3.col, 2, "p3 col (EOF)"
    var pn as Position is calling m.position_at with -9
    calling eq_i with pn.line, 1, "clamp negative line"
    calling eq_i with pn.col, 1, "clamp negative col"
    var pb as Position is calling m.position_at with 99
    calling eq_i with pb.line, 2, "clamp big line"
    calling eq_i with pb.col, 2, "clamp big col"

    calling eq_i with (calling m.offset_of with 1, 1), 0, "off 1,1"
    calling eq_i with (calling m.offset_of with 1, 2), 1, "off newline"
    calling eq_i with (calling m.offset_of with 2, 1), 2, "off 2,1"
    calling eq_i with (calling m.offset_of with 2, 2), 3, "off EOF"

    var t1 as string is calling m.line_text with 1
    defer banish t1
    calling eq_s with t1, "a", "line1"
    var t2 as string is calling m.line_text with 2
    defer banish t2
    calling eq_s with t2, "b", "line2"

    var span as SourceSpan is calling m.line_span with 1
    calling eq_i with span.start.line, 1, "span start line"
    calling eq_i with span.start.col, 1, "span start col"
    calling eq_i with span.end.line, 1, "span end line"
    calling eq_i with span.end.col, 2, "span end col"

    var s2 as SourceSpan is calling m.span_at with 0, 3
    calling eq_i with s2.start.line, 1, "span_at start"
    calling eq_i with s2.end.line, 2, "span_at end"
    let (ps, pe) is calling m.span_to_positions with s2
    calling eq_i with ps.line, 1, "unpack start"
    calling eq_i with pe.col, 2, "unpack end"

    calling eq_b with (calling m.is_valid_offset with 0), true, "valid off0"
    calling eq_b with (calling m.is_valid_offset with 3), true, "valid off3"
    calling eq_b with (calling m.is_valid_offset with 4), false, "invalid off4"
    calling eq_b with (calling m.is_valid_offset with -1), false, "invalid off-1"
    calling eq_b with (calling m.is_valid_position with (with line is 2, col is 2)), true, "valid pos"
    calling eq_b with (calling m.is_valid_position with (with line is 3, col is 1)), false, "invalid line"
    calling eq_b with (calling m.is_valid_position with (with line is 2, col is 3)), false, "invalid col"
    calling eq_i with (calling m.clamp_offset with -7), 0, "clamp -7"
    calling eq_i with (calling m.clamp_offset with 8), 3, "clamp 8"
    calling spark.println with "DONE"
    return 0
""")


def test_sourcemap_empty_trailing_crlf_and_unicode(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var empty as SourceMap is calling SourceMap.from_source with ""
    defer banish empty
    calling eq_i with (calling empty.line_count), 1, "empty lines"
    calling eq_i with (calling empty.source_len), 0, "empty len"
    var et as string is calling empty.line_text with 1
    defer banish et
    calling eq_s with et, "", "empty line"
    var ep as Position is calling empty.position_at with 0
    calling eq_i with ep.line, 1, "empty pos line"
    calling eq_i with ep.col, 1, "empty pos col"
    calling eq_i with (calling empty.offset_of with 1, 1), 0, "empty off"

    var nl as SourceMap is calling SourceMap.from_source with "a\\n"
    defer banish nl
    calling eq_i with (calling nl.line_count), 2, "trailing newline lines"
    var nt as string is calling nl.line_text with 2
    defer banish nt
    calling eq_s with nt, "", "trailing line 2"
    var np as Position is calling nl.position_at with 2
    calling eq_i with np.line, 2, "trailing pos line"
    calling eq_i with np.col, 1, "trailing pos col"

    var crlf as SourceMap is calling SourceMap.from_source with "a\\r\\nb"
    defer banish crlf
    calling eq_i with (calling crlf.line_count), 2, "crlf lines"
    var ct as string is calling crlf.line_text with 1
    defer banish ct
    calling eq_s with ct, "a", "crlf line1 without CR"
    var c2 as string is calling crlf.line_text with 2
    defer banish c2
    calling eq_s with c2, "b", "crlf line2"
    calling eq_i with (calling crlf.offset_of with 2, 1), 3, "crlf line2 offset"
    var cp as Position is calling crlf.position_at with 1
    calling eq_i with cp.line, 1, "crlf CR line"
    calling eq_i with cp.col, 2, "crlf CR col"

    var blank as SourceMap is calling SourceMap.from_source with "a\\n\\nb"
    defer banish blank
    calling eq_i with (calling blank.line_count), 3, "blank lines"
    var bt as string is calling blank.line_text with 2
    defer banish bt
    calling eq_s with bt, "", "blank middle"

    var uni as SourceMap is calling SourceMap.from_source with "ñ\\n"
    defer banish uni
    var ut as string is calling uni.line_text with 1
    defer banish ut
    calling eq_s with ut, "ñ", "unicode line"
    calling eq_i with (calling uni.source_len), 3, "unicode bytes"
    calling eq_i with (calling uni.offset_of with 1, 3), 2, "unicode col3"
    var us as SourceSpan is calling uni.line_span with 1
    calling eq_i with us.end.col, 3, "unicode span end"
    calling spark.println with "DONE"
    return 0
""")


@pytest.mark.parametrize("body, expected", [
    ("calling m.offset_of with 0, 1", "line out of range"),
    ("calling m.offset_of with 1, 0", "column must be >= 1"),
    ("calling m.offset_of with 1, 99", "past end of line"),
    ("calling m.line_text with 0", "line out of range"),
    ("var s as SourceSpan is calling m.span_at with 2, 1", "end before start"),
])
def test_sourcemap_panics_are_fatal(run_pengu, body, expected):
    res = run_pengu(f"""
import std.spark
import std.sourcemap

weave main into int:
    var m as SourceMap is calling SourceMap.from_source with "abc\\ndef"
    defer banish m
    {body}
    calling spark.println with "SHOULD NOT REACH"
    return 0
""")
    assert res.returncode != 0
    assert expected in (res.stderr + res.stdout), (res.stdout, res.stderr)
