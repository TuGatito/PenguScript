"""Phase 2 — bounds on a `shard T` receiver.

`enchanting shard T where T: Integrum:` declares one body for every type that
satisfies the bound, and the bound is enforced where the body is instantiated:
`float.is_even` is E0005, not a C compile error three phases later.

The one deliberate *deviation* from the design note is documented in
`test_uncast_literal_is_accepted_because_std_relies_on_it`: the note asked for
E0005 on `self % 2`, but `std/loom.pengu` writes exactly that inside a
`shard T where T: Integrum` weave, so rejecting it would stop an existing
program from compiling — which the same note forbids.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_integrum_method_is_available_on_int_receivers(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave check with a as int, b as i64, c as u32 into bool:
    return calling a.is_even and calling b.is_even and calling c.is_even
""")
    assert errors == []


def test_integrum_bound_rejects_float_receiver(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave check with a as float into bool:
    return calling a.is_even
""")
    assert any(e.code == "E0005" for e in errors), [e.code for e in errors]
    assert any("Integrum" in str(e) for e in errors)


def test_num_bound_accepts_float_receiver(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Num:
    weave to_f64 into f64:
        return self to f64

weave check with a as f32 into f64:
    return calling a.to_f64
""")
    assert errors == []


def test_monomorphization_is_per_receiver(parse_and_check):
    _, _, symbols = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave check with a as int, b as i64 into bool:
    if calling a.is_even:
        return calling b.is_even
    return false
""")
    assert "int_is_even" in symbols.monomorphized_methods
    assert "i64_is_even" in symbols.monomorphized_methods


def test_modulo_on_a_float_bound_is_rejected(parse_and_check):
    """`%` needs Integrum; a Num-only bound must not grant it."""
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Num:
    weave bad into bool:
        return (self % (2 to T)) == donum T
""")
    assert any(e.code == "E0049" for e in errors), [e.code for e in errors]


def test_uncast_literal_is_accepted_because_std_relies_on_it(parse_and_check):
    """`self % 2` with a bare literal stays legal.

    `std/loom.pengu`'s `count_if_even shard T where T: Integrum and T: Par`
    patches every element with `(x % 2) == 0`, and the emitter produces valid C
    for every integer width.  Making it E0005 would break a shipped module, so
    the permissive reading wins; `(2 to T)` remains the precise spelling.
    """
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % 2) == donum T

weave check with a as int into bool:
    return calling a.is_even
""")
    assert errors == [], [str(e) for e in errors]


def test_bound_violation_message_names_the_method(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave check with a as f64 into bool:
    return calling a.is_even
""")
    text = " ".join(str(e) for e in errors)
    assert "is_even" in text and "f64" in text


def test_integrum_bound_grants_ordering(parse_and_check):
    """`Integrum` grants `< <= > >=`, like it already granted `== !=`.

    Every type satisfying `Integrum` is an integer primitive, and every integer
    primitive is ordered, so the canonical `while (k * k) <= n` trial-division
    idiom must not need a redundant `and T: Ordo`.
    """
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_prime_small into bool:
        if self < (2 to T):
            return false
        var k as T is (2 to T)
        while (k * k) <= self:
            if (self % k) == donum T:
                return false
            set k is k + (1 to T)
        return true
""")
    assert errors == [], [str(e) for e in errors]


def test_real_bound_grants_ordering(parse_and_check):
    """`Real` grants `< <= > >=` too: `approx_eq` is `(a - b).abs < eps`.

    Uses `T`-typed operands only: an `int` literal cannot be cast to `T: Real`
    (`int` does not implement `Real`, so `BaseType.is_compatible(TypeParam)`
    rejects `1 to T`). That is a separate, pre-existing restriction.
    """
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Real:
    weave ordered into bool:
        if self < self:
            return false
        return (self <= self) and (self > donum T)
""")
    assert errors == [], [str(e) for e in errors]


def test_num_bound_does_not_grant_ordering(parse_and_check):
    """The extra grants are a property of the refinements, not of `Num`.

    `T: Num` must keep rejecting `<` with E0049, otherwise the monotone chain
    documented in LANGUAGE.md §10.9 would be false.
    """
    errors, _, _ = parse_and_check("""
enchanting shard T where T: Num:
    weave bad into bool:
        return self < donum T
""")
    assert any(e.code == "E0049" for e in errors), [e.code for e in errors]

