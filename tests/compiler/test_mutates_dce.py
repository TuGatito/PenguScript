"""Regression: dead-code elimination must not drop a ``@mutates`` weave.

A ``@mutates`` method is *reached* as ``get_<name>``, but its C symbol is still
``<T>_<name>``.  The reference collector reads raw identifiers, so a body that
only ever names ``get_implies`` left ``implies`` looking dead: DCE pruned the
``std/`` weave while the call site kept emitting ``bool_implies``, and the C
compiler reported an implicit declaration.

This only showed up once a *prunable* module (anything under ``std/``) was
annotated, which is why ``@mutates`` passed its own tests in 2.3.0 and broke on
the first real use.  DCE is a whole-project pass, so these tests go through the
driver (``pengu expand``) rather than a single-file bundle.
"""
from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture
def expand(pengu_cli, tmp_path):
    """Full pipeline -> the emitted C for a program that imports ``std``."""
    def _run(source: str, tag: str = "t") -> str:
        script = tmp_path / f"{tag}.pengu"
        script.write_text(source, encoding="utf-8")
        res = pengu_cli("expand", str(script))
        assert res.returncode == 0, f"expand failed:\n{res.stdout}\n{res.stderr}"
        return res.stdout
    return _run


def _defined(c_source: str, name: str) -> bool:
    """True when ``name`` is *defined* (a `{` body), not merely declared.

    Matches on the function name alone: the parameters carry C types
    (`uint8_t self`), not the PenguScript spelling (`u8 self`).
    """
    return re.search(rf"^[\w \*]+\b{re.escape(name)}\([^;{{]*\)\s*\{{",
                     c_source, re.M) is not None


def test_mutates_weave_survives_dce_when_only_the_getter_is_named(expand):
    """`get_implies` keeps `bool_implies` alive."""
    c = expand("""
import std.logica

weave main into int:
    var a as bool is true
    var b as bool is false
    var r as bool is calling a.get_implies with b
    return 0
""")
    assert _defined(c, "bool_implies"), (
        "DCE pruned the `@mutates` weave that `get_implies` reaches:\n"
        + "\n".join(l for l in c.splitlines() if "implies" in l)
    )


def test_mutates_weave_survives_dce_for_a_shard_method(expand):
    """The same holds for a `shard T` method reached by its getter."""
    c = expand("""
import std.numerus

weave main into int:
    var x as int is -5
    var y as int is calling x.get_abs
    return y
""")
    assert _defined(c, "int_abs"), (
        "DCE pruned numerus' `abs`:\n"
        + "\n".join(l for l in c.splitlines() if "int_abs" in l)
    )


def test_exactly_one_c_function_per_method(expand):
    """The alias must not emit a second, `get_`-named function."""
    c = expand("""
import std.logica

weave main into int:
    var a as bool is true
    var b as bool is false
    var r as bool is calling a.get_implies with b
    return 0
""")
    assert "bool_get_implies" not in c


def test_unused_weaves_are_still_pruned(expand):
    """The fix keeps a *referenced* weave; it must not disable DCE wholesale."""
    c = expand("""
import std.logica

weave main into int:
    var a as bool is true
    var r as bool is calling a.get_toggle
    return 0
""")
    assert _defined(c, "bool_toggle")
    assert not _defined(c, "bool_xor"), (
        "an unrelated, unused `enchanting` method was not pruned"
    )
