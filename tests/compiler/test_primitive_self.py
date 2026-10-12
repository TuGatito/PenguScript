"""Phase 2 — `self` is a *value* in primitive methods, a reference elsewhere.

This is the rule the whole feature hangs on: `int32_t` has no identity in C, so
`self` is passed by value.  Consequences, each pinned by one test below:

* the registered signature carries no `ref to` and `self_is_value` is True;
* `set self is …` is E0006 (there is no storage to assign to);
* `self->field` is E0003 (there is nothing to dereference);
* a method of a *rune*, a collection or a string keeps `ref to T`/`T* self`.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_self_is_value_not_ref(parse_and_check):
    _, _, symbols = parse_and_check("""
enchanting int:
    weave double into int:
        return self + self
""")
    method = symbols.methods[("int", "double")]
    assert method.self_is_value is True
    # `self` is not part of `params` (it is implicit), so the observable proof is
    # the flag plus the return type being the primitive itself.
    assert str(method.return_type) == "int"


def test_value_self_supports_arithmetic(parse_and_check):
    """The bug this fixes: `ref to int` made `self + 1` a type error."""
    errors, _, _ = parse_and_check("""
enchanting int:
    weave inc into int:
        return self + 1
""")
    assert errors == [], [str(e) for e in errors]


def test_value_self_supports_comparison(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave is_big into bool:
        return self > 100
""")
    assert errors == []


def test_set_self_rejected(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave bad into int:
        set self is 42
        return self
""")
    assert any(e.code == "E0006" for e in errors), [e.code for e in errors]
    assert any("primitive" in str(e) for e in errors if e.code == "E0006")


def test_self_arrow_rejected(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave bad into int:
        return self->value
""")
    assert any(e.code == "E0003" for e in errors), [e.code for e in errors]


@pytest.mark.parametrize("prim", ["i64", "u32", "char", "bool", "usize"])
def test_every_primitive_self_is_value(parse_and_check, prim):
    _, _, symbols = parse_and_check(f"""
enchanting {prim}:
    weave identity into {prim}:
        return self
""")
    key = ("int", "identity") if prim in ("i32", "int32", "int32_t") else (prim, "identity")
    assert symbols.methods[key].self_is_value is True


def test_rune_self_is_still_a_reference(parse_and_check):
    _, _, symbols = parse_and_check("""
rune Player:
    hp as int
enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount
""")
    assert symbols.methods[("Player", "heal")].self_is_value is False


def test_collection_self_is_still_a_reference(parse_and_check):
    _, _, symbols = parse_and_check("""
enchanting list of int:
    weave total into int:
        return 0
""")
    assert symbols.methods[("list of int", "total")].self_is_value is False


def test_string_self_is_still_a_reference(parse_and_check):
    """A string owns heap memory, so it is explicitly *not* a value receiver."""
    errors, _, symbols = parse_and_check("""
enchanting string:
    weave show into void:
        return
""")
    assert errors == []
    assert symbols.methods[("string", "show")].self_is_value is False


def test_shard_self_is_a_value(parse_and_check):
    """A bare `shard T` has no fields either, so it shares the scalar rule."""
    _, _, symbols = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T
""")
    assert symbols.methods[("__shard__", "is_even")].self_is_value is True


def test_primitive_method_can_call_another_on_self(parse_and_check):
    """`calling self.is_even` from `is_odd` resolves inside the method scope."""
    errors, _, symbols = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T
    weave is_odd into bool:
        return not calling self.is_even
""")
    assert errors == []
    assert ("__shard__", "is_odd") in symbols.methods
