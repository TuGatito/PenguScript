"""`std.numerus` — `min_with`, `max_with`, `clamp` and `is_between`.

Two programs: the pairwise selectors and the range restrictors. `clamp` and
`is_between` are exercised below, inside, above and on both inclusive edges, plus
a floating-point case.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.numerus

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_f with got as f64, want as f64, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_min_and_max_with(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var x as int is 3
    var big as int is 7
    var small as int is 2
    var f as f64 is 2.5
    var g as f64 is 3.5
    var u as u16 is 4
    calling eq_i with (calling x.min_with with big), 3, "min a<b"
    calling eq_i with (calling x.min_with with small), 2, "min a>b"
    calling eq_i with (calling x.min_with with x), 3, "min a==b"
    calling eq_i with (calling x.max_with with big), 7, "max a<b"
    calling eq_i with (calling x.max_with with small), 3, "max a>b"
    calling eq_i with (calling x.max_with with x), 3, "max a==b"
    calling eq_f with (calling f.min_with with g), 2.5, "min f64"
    calling eq_f with (calling f.max_with with g), 3.5, "max f64"
    calling eq_i with (calling u.min_with with 9), 4, "min unsigned"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_clamp_and_is_between(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var over as int is 200
    var under as int is -5
    var inside as int is 7
    var lo as int is 0
    var hi as int is 10
    calling eq_i with (calling over.clamp with 0, 120), 120, "clamp above"
    calling eq_i with (calling under.clamp with 0, 10), 0, "clamp below"
    calling eq_i with (calling inside.clamp with 0, 10), 7, "clamp inside"
    calling eq_i with (calling hi.clamp with 0, 10), 10, "clamp on hi"
    calling eq_i with (calling lo.clamp with 0, 10), 0, "clamp on lo"
    var f as f64 is 145.7
    calling eq_f with (calling f.clamp with 0.0, 100.0), 100.0, "clamp f64 above"
    var negf as f64 is -3.0
    calling eq_f with (calling negf.clamp with 0.0, 100.0), 0.0, "clamp f64 below"
    calling eq_b with (calling inside.is_between with 0, 10), true, "between inside"
    calling eq_b with (calling over.is_between with 0, 10), false, "between above"
    calling eq_b with (calling under.is_between with 0, 10), false, "between below"
    calling eq_b with (calling lo.is_between with 0, 10), true, "between lo edge"
    calling eq_b with (calling hi.is_between with 0, 10), true, "between hi edge"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
