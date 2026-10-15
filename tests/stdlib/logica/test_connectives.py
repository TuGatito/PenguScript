"""`std.logica` — the logical connectives, as full truth tables.

Two programs: the chainable versions of the language operators
(`and_with`, `or_with`, `toggle`) and the derived connectives
(`xor`, `iff`, `nand`, `nor`, `implies`). Every table is enumerated over all
four operand pairs; `implies` in particular is checked pair by pair, because
material implication is the one that surprises readers.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.logica

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_chainable_operators(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var t as bool is true
    var f as bool is false
    calling eq_b with (calling t.get_toggle), false, "toggle true"
    calling eq_b with (calling f.get_toggle), true, "toggle false"
    var once as bool is calling t.get_toggle
    var twice as bool is calling once.get_toggle
    calling eq_b with twice, true, "toggle twice is identity"
    calling eq_b with (calling t.get_and_with with t), true, "T and T"
    calling eq_b with (calling t.get_and_with with f), false, "T and F"
    calling eq_b with (calling f.get_and_with with t), false, "F and T"
    calling eq_b with (calling f.get_and_with with f), false, "F and F"
    calling eq_b with (calling t.get_or_with with t), true, "T or T"
    calling eq_b with (calling t.get_or_with with f), true, "T or F"
    calling eq_b with (calling f.get_or_with with t), true, "F or T"
    calling eq_b with (calling f.get_or_with with f), false, "F or F"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_derived_connectives(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var t as bool is true
    var f as bool is false
    calling eq_b with (calling t.get_xor with t), false, "T xor T"
    calling eq_b with (calling t.get_xor with f), true, "T xor F"
    calling eq_b with (calling f.get_xor with t), true, "F xor T"
    calling eq_b with (calling f.get_xor with f), false, "F xor F"
    calling eq_b with (calling t.get_iff with t), true, "T iff T"
    calling eq_b with (calling t.get_iff with f), false, "T iff F"
    calling eq_b with (calling f.get_iff with t), false, "F iff T"
    calling eq_b with (calling f.get_iff with f), true, "F iff F"
    calling eq_b with (calling t.get_nand with t), false, "T nand T"
    calling eq_b with (calling t.get_nand with f), true, "T nand F"
    calling eq_b with (calling f.get_nand with t), true, "F nand T"
    calling eq_b with (calling f.get_nand with f), true, "F nand F"
    calling eq_b with (calling t.get_nor with t), false, "T nor T"
    calling eq_b with (calling t.get_nor with f), false, "T nor F"
    calling eq_b with (calling f.get_nor with t), false, "F nor T"
    calling eq_b with (calling f.get_nor with f), true, "F nor F"
    calling eq_b with (calling t.get_implies with t), true, "T implies T"
    calling eq_b with (calling t.get_implies with f), false, "T implies F"
    calling eq_b with (calling f.get_implies with t), true, "F implies T"
    calling eq_b with (calling f.get_implies with f), true, "F implies F"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
