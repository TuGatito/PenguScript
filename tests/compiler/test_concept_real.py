"""Phase 2.5 — the `Real` concept (floating-point-only refinement of `Num`).

`Real` exists so a generic method can say "this only works on floats" without
duplicating the body per width: `enchanting shard T where T: Real:` is
instantiated for `float`, `f32`, `f64` and `double`, and for nothing else. It is
the mirror image of `Integrum`, and the two are *disjoint* branches of `Num`:

* `Integrum`  — integers only, adds `%` and the bitwise/shift operators;
* `Real`      — floats only, adds nothing `Num` does not already grant.

The fast half of this file pins the concept table itself (membership, aliases,
the `Real` ⇒ `Num` refinement and the disjointness); the checker half proves the
bound is enforced where a body is instantiated, so `int.is_nan` is `E0005`
instead of a C compile error three phases later. The compile-and-run case lives
in `test_concept_real_e2e.py`, which carries the `slow` marker on its own: the
`smoke` tier promises no C compilation, so a file that shells out must not be a
smoke target.
"""
from __future__ import annotations

import pytest

from pengu_parser.pengu_types import (
    CONCEPT_OPERATORS,
    CONCEPT_REFINES,
    BaseType,
    TypeParam,
    canonical_primitive_name,
    implements_concept,
    is_floating_type,
)

pytestmark = pytest.mark.smoke

#: Every spelling that must satisfy `Real` (the concept table's float names).
FLOATS = ("float", "f32", "f64", "double")

#: Spellings that must *not* satisfy `Real`: every integer width, the char/byte
#: scalars, bool and string.
NON_FLOATS = (
    "int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
    "usize", "isize", "byte", "char", "bool", "string",
)


# ---------------------------------------------------------------------------
# The table itself
# ---------------------------------------------------------------------------


def test_real_registered_with_the_num_operators():
    """`Real` grants at least everything `Num` grants (it is a refinement)."""
    assert set(CONCEPT_OPERATORS["Real"]) >= set(CONCEPT_OPERATORS["Num"])


def test_real_refines_num():
    assert CONCEPT_REFINES["Real"] == "Num"


def test_real_grants_equality_like_integrum():
    """Same rationale as `Integrum`: every float satisfies `Par`, so `is_nan`
    (`self != self`) must not need a redundant `and T: Par`."""
    assert {"eq", "ne"} <= set(CONCEPT_OPERATORS["Real"])


def test_real_and_integrum_are_disjoint_branches():
    """`Real` grants no integer-only operator, so the branches stay disjoint."""
    integer_only = {"mod", "band", "bor", "bxor", "shl", "shr", "bnot"}
    assert not (set(CONCEPT_OPERATORS["Real"]) & integer_only)


def test_is_floating_type_covers_all_aliases():
    for t in FLOATS:
        assert is_floating_type(t), f"{t} should be floating"


def test_is_floating_type_accepts_base_types():
    assert all(is_floating_type(BaseType(t)) for t in FLOATS)


def test_is_floating_type_rejects_every_integer():
    for t in NON_FLOATS:
        assert not is_floating_type(t), f"{t} should NOT be floating"


def test_is_floating_type_rejects_none_and_unknown_names():
    assert not is_floating_type(None) and not is_floating_type("Player")


def test_canonical_name_keeps_float_widths_distinct():
    """The method key is the canonical spelling: `float`/`f32` vs `f64`/`double`."""
    assert canonical_primitive_name("float") == canonical_primitive_name("f32")
    assert canonical_primitive_name("f64") == canonical_primitive_name("double")


@pytest.mark.parametrize("t", FLOATS)
def test_float_satisfies_real(t):
    assert implements_concept(BaseType(t), "Real", None)


@pytest.mark.parametrize("t", NON_FLOATS)
def test_non_float_does_not_satisfy_real(t):
    assert not implements_concept(BaseType(t), "Real", None)


def test_real_bound_implies_num_bound():
    """`T: Real` also satisfies a `T: Num` requirement (the monotone chain)."""
    assert implements_concept(TypeParam("T", bounds=["Real"]), "Num", None)


def test_num_bound_does_not_imply_real_bound():
    assert not implements_concept(TypeParam("T", bounds=["Num"]), "Real", None)


def test_integrum_bound_does_not_imply_real_bound():
    assert not implements_concept(TypeParam("T", bounds=["Integrum"]), "Real", None)


def test_real_type_parameter_is_numeric_and_float():
    t = TypeParam("T", bounds=["Real"])
    assert t.is_numeric() and t.is_float() and not t.is_int()


# ---------------------------------------------------------------------------
# The bound is enforced where the body is instantiated
# ---------------------------------------------------------------------------

_REAL_SHARD = """
enchanting shard T where T: Real:
    weave is_nan_ish into bool:
        return self != self
    weave double_f into T:
        return self + self
"""


@pytest.mark.parametrize("t", FLOATS)
def test_real_method_is_available_on_every_float_width(parse_and_check, t):
    errors, _, _ = parse_and_check(_REAL_SHARD + f"""
weave main into int:
    var x as {t} is (0.0 to {t})
    if calling x.is_nan_ish:
        return 1
    var y as {t} is calling x.double_f
    return 0
""")
    assert errors == [], f"{t} should satisfy Real: {[(e.code, str(e)) for e in errors]}"


@pytest.mark.parametrize("t", ("int", "i64", "u64", "byte", "char"))
def test_real_method_is_rejected_on_non_floats(parse_and_check, t):
    errors, _, _ = parse_and_check(_REAL_SHARD + f"""
weave main into int:
    var x as {t} is (0 to {t})
    if calling x.is_nan_ish:
        return 1
    return 0
""")
    assert any(e.code == "E0005" for e in errors), [e.code for e in errors]


def test_real_method_rejection_names_the_concept(parse_and_check):
    errors, _, _ = parse_and_check(_REAL_SHARD + """
weave main into int:
    var x as int is 0
    if calling x.is_nan_ish:
        return 1
    return 0
""")
    assert any("Real" in str(e) for e in errors), [str(e) for e in errors]


def test_real_bound_violation_is_e0032_and_names_the_concept(parse_and_check):
    errors, _, _ = parse_and_check("""
weave probe shard T where T: Real with x as T into bool:
    return true

weave main into int:
    var x as int is 0
    if calling probe with x:
        return 1
    return 0
""")
    text = " ".join(str(e) for e in errors)
    assert any(e.code == "E0032" for e in errors) and "Real" in text


def test_derive_real_is_rejected(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Money derive Real:
    amount as f64
""")
    assert any(e.code == "E0005" for e in errors), [e.code for e in errors]


def test_derive_real_message_names_the_concept(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Money derive Real:
    amount as f64
""")
    assert any("Real" in str(e) for e in errors), [str(e) for e in errors]


def test_real_bound_grants_arithmetic(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave twice_minus into T:
        return (self + self) - self
""")
    assert errors == [], [str(e) for e in errors]


def test_real_bound_grants_equality(parse_and_check):
    """The `is_nan` idiom: `self != self` with no extra `and T: Par`."""
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave is_nan_ish into bool:
        return self != self
""")
    assert errors == [], [str(e) for e in errors]


def test_real_bound_does_not_grant_modulo(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave bad into T:
        return self % 2
""")
    assert any(e.code == "E0049" for e in errors), [e.code for e in errors]


def test_real_bound_does_not_grant_bitwise(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave bad into T:
        return self & 1
""")
    assert any(e.code == "E0049" for e in errors), [e.code for e in errors]


def test_real_bound_is_defaultable(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave is_zero_f into bool:
        return self == donum T
""")
    assert errors == [], [str(e) for e in errors]


def test_real_bound_can_call_a_num_bound_method(parse_and_check):
    """`Real` ⇒ `Num`: a float-only generic may use a numeric-only method."""
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Num:
    weave twice into T:
        return self + self

weave call_num shard T where T: Real with x as T into T:
    return calling x.twice
""")
    assert errors == [], [str(e) for e in errors]


def test_real_method_monomorphizes_per_float_width(parse_and_check):
    """One body, one C function per concrete width -- like `Integrum`."""
    _, _, symbols = parse_and_check(_REAL_SHARD + """
weave main into int:
    var a as float is 1.0
    var b as f64 is 1.0
    var c as float is calling a.double_f
    var d as f64 is calling b.double_f
    return 0
""")
    assert {"float_double_f", "f64_double_f"} <= set(symbols.monomorphized_methods)
