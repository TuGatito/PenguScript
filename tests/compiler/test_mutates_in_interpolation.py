"""Regression: E0066 survives a string interpolation.

A mutating call in value position is ``E0066``.  Inside ``"{...}"`` the
interpolation handler used a bare ``except Exception`` that re-labelled the
sub-expression's diagnostic as a generic ``E0019``:

    E0019 Invalid expression inside string interpolation '{calling x.twice}':
    'twice' mutates its receiver and cannot be used in expression position

The code was wrong and the ``help:`` ("use ``get_<name>``") was dropped.  The
sub-expression already carries the precise diagnostic, so it is re-raised with
its own code and guidance; only the position moves, to the interpolation.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke

MUTATING = """
enchanting int:
    @mutates
    weave twice into int:
        return self + self
"""


def test_mutating_call_in_interpolation_reports_e0066(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING + """
weave main into int:
    var x as int is 5
    var s as string is "value={calling x.twice}"
    return 0
""")
    codes = [e.code for e in errors]
    assert "E0066" in codes, [str(e) for e in errors]
    assert "E0019" not in codes, (
        "the interpolation handler re-labelled E0066 as E0019: " + str([str(e) for e in errors])
    )


def test_the_message_and_help_are_preserved(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING + """
weave main into int:
    var x as int is 5
    var s as string is "value={calling x.twice}"
    return 0
""")
    err = next(e for e in errors if e.code == "E0066")
    assert "mutates its receiver" in err.message
    assert err.help and "get_" in err.help, f"lost the `help:` guidance: {err.help!r}"


def test_the_imported_module_getter_also_reports_e0066(parse_and_check):
    """Same path, but resolved through an import rather than a local block."""
    errors, _, _ = parse_and_check("""
import std.logica

weave main into int:
    var a as bool is true
    var b as bool is false
    var s as string is "v={calling a.implies with b}"
    return 0
""")
    codes = [e.code for e in errors]
    assert "E0066" in codes, [str(e) for e in errors]
    assert "E0019" not in codes, [str(e) for e in errors]


def test_a_genuine_interpolation_error_still_reports_e0019(parse_and_check):
    """The fix is narrow: real interpolation errors keep their own diagnostic."""
    errors, _, _ = parse_and_check("""
weave main into int:
    var s as string is "value={1 +}"
    return 0
""")
    assert errors, "a malformed interpolation expression was accepted"
    assert all(e.code != "E0066" for e in errors), [str(e) for e in errors]


def test_undefined_variable_in_interpolation_still_reports_e0019(parse_and_check):
    errors, _, _ = parse_and_check("""
weave main into int:
    var s as string is "value={nope}"
    return 0
""")
    codes = [e.code for e in errors]
    assert any(c in ("E0019", "E0004") for c in codes), [str(e) for e in errors]
