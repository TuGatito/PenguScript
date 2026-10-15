"""Regression: a nested ``@mutates`` monomorphization must be emitted.

Nested shard calls are monomorphized by ``collect_declarations``' fixpoint, which
reads the method name straight from the body AST.  A ``@mutates`` method is
reached as ``get_<name>``, so the inner instance was not registered there and
only appeared later, during body generation -- after the definitions had already
been assembled.  The call site still emitted the symbol:

    error: declaración implícita de la función 'u8_abs'; ¿quiso decir 'u32_abs'?

Only *some* widths failed, depending on which body happened to reach the instance
first, which is why it survived the module's own tests.  Monomorphization is a
whole-project pass, so these tests go through the driver (``pengu expand``).
"""
from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture
def expand(pengu_cli, tmp_path):
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


@pytest.mark.parametrize("width", ["u8", "i8", "u16", "u32", "i64"])
def test_nested_mutates_monomorphization_is_defined(expand, width):
    """`gcd`'s body calls `a.get_abs`; every width it is instantiated at needs it."""
    c = expand(f"""
import std.integrum

weave main into int:
    var small as {width} is 12
    var g as {width} is calling small.get_gcd with 18
    return g to int
""", tag=f"gcd_{width}")
    assert _defined(c, f"{width}_gcd"), f"{width}_gcd was not emitted"
    assert _defined(c, f"{width}_abs"), (
        f"{width}_abs is called inside {width}_gcd but was never defined:\n"
        + "\n".join(l for l in c.splitlines() if f"{width}_abs" in l)
    )


def test_the_nested_call_is_not_an_implicit_declaration(expand):
    """A declaration without a definition is exactly the bug: assert both."""
    c = expand("""
import std.integrum

weave main into int:
    var small as u8 is 12
    var g as u8 is calling small.get_gcd with 18
    return g to int
""", tag="gcd_decl")
    assert "uint8_t u8_abs(uint8_t self);" in c, "no forward declaration for u8_abs"
    assert _defined(c, "u8_abs"), "forward-declared but never defined"


def test_lcm_also_reaches_the_nested_getter(expand):
    """`lcm` calls `p.get_abs` too -- a second body, same requirement."""
    c = expand("""
import std.integrum

weave main into int:
    var a as u8 is 4
    var b as u8 is 6
    var m as u8 is calling a.get_lcm with b
    return m to int
""", tag="lcm_u8")
    assert _defined(c, "u8_lcm")
    assert _defined(c, "u8_abs")


def test_a_primitive_alias_shares_the_canonical_symbol(expand):
    """`i32` is an alias of `int`, so the instance is `int_gcd`, not `i32_gcd`."""
    c = expand("""
import std.integrum

weave main into int:
    var small as i32 is 12
    var g as i32 is calling small.get_gcd with 18
    return g
""", tag="alias_i32")
    assert _defined(c, "int_gcd")
    assert _defined(c, "int_abs")
    assert not _defined(c, "i32_gcd"), "the alias spelling emitted a second instance"
