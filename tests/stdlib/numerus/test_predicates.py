"""`std.numerus` — the predicate family.

Two programs: the sign triad (`is_zero`, `is_positive`, `is_negative`) and the
non-strict pair (`is_non_negative`, `is_non_positive`). The unsigned cases pin the
documented behaviour: an unsigned value is never negative and always
non-negative, even at zero.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.numerus

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_sign_triad(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var pos as int is 7
    var neg as int is -7
    var fzero as f64 is 0.0
    var fpos as f64 is 0.5
    var fneg as f64 is -0.5
    var uzero as u8 is 0
    var upos as u8 is 5
    calling eq_b with (calling zero.is_zero), true, "is_zero int zero"
    calling eq_b with (calling pos.is_zero), false, "is_zero int pos"
    calling eq_b with (calling neg.is_zero), false, "is_zero int neg"
    calling eq_b with (calling fzero.is_zero), true, "is_zero f64 zero"
    calling eq_b with (calling uzero.is_zero), true, "is_zero unsigned zero"
    calling eq_b with (calling pos.is_positive), true, "is_positive int pos"
    calling eq_b with (calling zero.is_positive), false, "is_positive int zero"
    calling eq_b with (calling neg.is_positive), false, "is_positive int neg"
    calling eq_b with (calling fpos.is_positive), true, "is_positive f64 pos"
    calling eq_b with (calling uzero.is_positive), false, "is_positive unsigned zero"
    calling eq_b with (calling neg.is_negative), true, "is_negative int neg"
    calling eq_b with (calling zero.is_negative), false, "is_negative int zero"
    calling eq_b with (calling pos.is_negative), false, "is_negative int pos"
    calling eq_b with (calling fneg.is_negative), true, "is_negative f64 neg"
    calling eq_b with (calling upos.is_negative), false, "is_negative unsigned"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_non_strict_predicates(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var pos as int is 1
    var neg as int is -1
    var uzero as u16 is 0
    var upos as u16 is 3
    calling eq_b with (calling pos.is_non_negative), true, "non_negative pos"
    calling eq_b with (calling zero.is_non_negative), true, "non_negative zero"
    calling eq_b with (calling neg.is_non_negative), false, "non_negative neg"
    calling eq_b with (calling uzero.is_non_negative), true, "non_negative unsigned zero"
    calling eq_b with (calling upos.is_non_negative), true, "non_negative unsigned pos"
    calling eq_b with (calling neg.is_non_positive), true, "non_positive neg"
    calling eq_b with (calling zero.is_non_positive), true, "non_positive zero"
    calling eq_b with (calling pos.is_non_positive), false, "non_positive pos"
    calling eq_b with (calling uzero.is_non_positive), true, "non_positive unsigned zero"
    calling eq_b with (calling upos.is_non_positive), false, "non_positive unsigned pos"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
