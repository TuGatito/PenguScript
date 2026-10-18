"""``std.diagnostic`` — positionaless diagnostics, sources, filters and JSON."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_SRC = r'''
import std.spark
import std.diagnostic as diag

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, name as string into void:
    if not got:
        calling spark.println with "FAIL {name}"

weave has_text with s as string, needle as string into bool:
    var n as int is s length
    var m as int is needle length
    if m == 0:
        return true
    if m > n:
        return false
    var hb as ref to frozen byte is bytes of s
    var nb as ref to frozen byte is bytes of needle
    var i as int is 0
    while i + m <= n:
        var same as bool is true
        var k as int is 0
        while k < m and same:
            if ((hb at (i + k)) to int) != ((nb at k) to int):
                set same is false
            set k is k + 1
        if same:
            return true
        set i is i + 1
    return false

weave main into int:
    # No labels at all: header only.
    var bag as DiagnosticBag is calling DiagnosticBag.new
    defer banish bag
    var plain as Diagnostic is calling diag.diagnostic with diag.Severity.Error, "", "internal error", (calling diag.no_labels), (maybe none), (maybe none), (calling diag.no_related)
    calling bag.add with plain
    var text as string is calling bag.render_plain
    calling eq_b with (calling has_text with text, "error: internal error"), "header"
    calling eq_b with (not calling has_text with text, "-->"), "no arrow"
    banish text

    # Labels without a primary are rendered as position-only lines.
    var ls as list of Label is list of Label
    calling ls.push with (calling diag.label with (calling diag.span_point with "", 3, 4, 0), "not primary", false)
    calling bag.add with (calling diag.diagnostic with diag.Severity.Warning, "W", "no primary", ls, (maybe none), (maybe none), (calling diag.no_related))
    var text2 as string is calling bag.render_plain
    calling eq_b with (calling has_text with text2, "3:4: not primary"), "position fallback"
    banish text2

    # A span in a file with no registered source still prints its position.
    var unknown as Span is calling diag.span_from_positions with "unknown.pengu", 7, 2, 7, 5, 20, 23
    var lb as Label is calling diag.label with unknown, "here", true
    calling bag.add with (calling diag.diagnostic with diag.Severity.Info, "", "missing source", (calling diag.labels with lb), (maybe none), (maybe none), (calling diag.no_related))
    var text3 as string is calling bag.render_plain
    calling eq_b with (calling has_text with text3, "--> unknown.pengu:7:2"), "unknown arrow"
    calling eq_b with (calling has_text with text3, "= 7:2: here"), "unknown label"
    banish text3

    # Filters are deep copies; freeing them must not disturb the bag.
    var errs as list of Diagnostic is calling bag.errors_only
    calling eq_i with errs.len, 1, "errors_only"
    calling diag.free_diagnostics with errs
    calling eq_i with (calling bag.len), 3, "bag intact"
    var we as list of Diagnostic is calling bag.warnings_and_errors
    calling eq_i with we.len, 2, "warnings_and_errors"
    calling diag.free_diagnostics with we

    # render_json on an empty bag is [].
    var empty as DiagnosticBag is calling DiagnosticBag.new
    var js as string is calling empty.render_json
    calling eq_b with (js == "[]"), "empty json"
    banish js
    banish empty

    # span_merge covers both spans and keeps a's file.
    var a as Span is calling diag.span_from_positions with "x.pengu", 1, 1, 1, 2, 0, 1
    var b as Span is calling diag.span_from_positions with "x.pengu", 2, 3, 2, 4, 5, 6
    var m as diag.Span is calling diag.span_merge with a, b
    calling eq_i with m.start_line, 1, "merge start"
    calling eq_i with m.end_line, 2, "merge end"
    calling eq_i with m.start_byte, 0, "merge start byte"
    calling eq_i with m.end_byte, 6, "merge end byte"
    banish a
    banish b
    banish m

    # source_of returns an owned copy.
    calling bag.add_source with "s.pengu", "abc"
    var so as maybe string is calling bag.source_of with "s.pengu"
    var copy as string is calling diag_test_take_string with (sigil of so)
    calling eq_b with (copy == "abc"), "source copy"
    banish copy
    calling bag.clear
    calling eq_i with (calling bag.len), 0, "clear"
    calling spark.println with "DONE"
    return 0

antiquus diag_test_take_string with m as ref to maybe string into string:
    r"""
if (m && m->is_present && m->value) {
    PenguString out = *(PenguString *)m->value;
    free(m->value);
    m->value = NULL;
    m->is_present = false;
    return out;
}
return pengu_string_from_cstr("");
"""
'''


def test_diagnostic_edge_cases(compile_and_run):
    out = compile_and_run(_SRC)
    assert "DONE" in out, out
    assert "FAIL" not in out, out
