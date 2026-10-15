"""``@mutates`` — one C function, two surface forms.

``@mutates`` marks a method whose *result* the compiler assigns back to the
receiver.  The declaration is written as a pure function (``self`` is an
immutable value, the body ``return``s the new value), so:

* ``calling x.foo with args`` is a **statement** that mutates ``x``;
* ``calling x.get_foo with args`` is the **pure** form and returns the value;
* exactly **one** C function (``<T>_foo``) is ever emitted.

Everything here is parse/check/emit — no C compiler, no subprocess.  The
end-to-end half lives in ``test_mutates_e2e.py``.
"""
from __future__ import annotations

from lark import Tree

import pytest

pytestmark = pytest.mark.smoke


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _iter_trees(node):
    """Yields every Tree in the subtree, including ``node``."""
    if isinstance(node, Tree):
        yield node
        for child in node.children:
            yield from _iter_trees(child)


def _codes(errors):
    return [e.code for e in errors]


MUTATING_INT = """
enchanting int:
    @mutates
    weave twice into int:
        return self + self
"""


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------

def test_mutates_is_registered(parse_and_check):
    errors, _, symbols = parse_and_check(MUTATING_INT)
    assert errors == [], [str(e) for e in errors]
    entry = symbols.mutating_methods[("int", "twice")]
    assert entry["getter"] == "get_twice"
    assert entry["self_is_value"] is True


def test_mutates_registers_under_the_shard_key(parse_and_check):
    """A ``shard T`` declaration serves every receiver, so it is keyed by the shard."""
    errors, _, symbols = parse_and_check("""
enchanting shard T where T: Num and T: Ordo and T: Par:
    @mutates
    weave clamp with lo as T, hi as T into T:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self
""")
    assert errors == [], [str(e) for e in errors]
    assert ("__shard__", "clamp") in symbols.mutating_methods


def test_plain_weave_is_not_mutating(parse_and_check):
    errors, _, symbols = parse_and_check("""
enchanting int:
    weave twice into int:
        return self + self
""")
    assert errors == []
    assert ("int", "twice") not in symbols.mutating_methods


# ---------------------------------------------------------------------------
# E0067 — placement and shape
# ---------------------------------------------------------------------------

def test_mutates_on_top_level_weave_is_e0067(parse_and_check):
    errors, _, _ = parse_and_check("""
@mutates
weave twice with x as int into int:
    return x + x
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_on_declare_is_e0067(parse_and_check):
    errors, _, _ = parse_and_check("""
@mutates
declare twice with x as int into int
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_in_bind_block_is_e0067(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Box:
    n as int
bind Box with Ordered:
    @mutates
    weave twice into Box:
        return self
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_with_arguments_is_e0067(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    @mutates(1)
    weave twice into int:
        return self + self
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_requires_the_receiver_type_as_return(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    @mutates
    weave twice into bool:
        return true
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_body_may_not_assign_through_arrow(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Bag:
    n as int
enchanting Bag:
    @mutates
    weave bump into Bag:
        set self->n is 1
        return self
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_body_may_not_assign_essence_of_self(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Bag:
    n as int
enchanting Bag:
    @mutates
    weave bump into Bag:
        set essence of self is self
        return self
""")
    assert "E0067" in _codes(errors), [str(e) for e in errors]


def test_mutates_does_not_relax_the_primitive_self_rule(parse_and_check):
    """`set self` stays E0006 inside a primitive method: the body is pure."""
    errors, _, _ = parse_and_check("""
enchanting int:
    @mutates
    weave twice into int:
        set self is self + self
        return self
""")
    assert "E0006" in _codes(errors), [str(e) for e in errors]


# ---------------------------------------------------------------------------
# E0068 — the reserved getter spelling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("order", ["before", "after"])
def test_explicit_getter_collision_is_e0068(parse_and_check, order):
    """The collision is detected whichever declaration comes first."""
    mutating = """
    @mutates
    weave twice into int:
        return self + self
"""
    getter = """
    weave get_twice into int:
        return self + self
"""
    body = mutating + getter if order == "before" else getter + mutating
    errors, _, _ = parse_and_check("enchanting int:\n" + body)
    assert "E0068" in _codes(errors), [str(e) for e in errors]


# ---------------------------------------------------------------------------
# E0066 — value position
# ---------------------------------------------------------------------------

def test_expression_position_is_e0066(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave main into int:
    var x as int is 5
    var r as int is calling x.twice
    return r
""")
    assert "E0066" in _codes(errors), [str(e) for e in errors]


def test_argument_position_is_e0066(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave take with v as int into void:
    return
weave main into int:
    var x as int is 5
    calling take with (calling x.twice)
    return 0
""")
    assert "E0066" in _codes(errors), [str(e) for e in errors]


def test_return_position_is_e0066(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave main into int:
    var x as int is 5
    return calling x.twice
""")
    assert "E0066" in _codes(errors), [str(e) for e in errors]


def test_getter_in_expression_is_allowed(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave main into int:
    var x as int is 5
    var r as int is calling x.get_twice
    return r
""")
    assert errors == [], [str(e) for e in errors]


# ---------------------------------------------------------------------------
# E0006 — the receiver must be writable
# ---------------------------------------------------------------------------

def test_mutating_a_let_is_e0006(parse_and_check):
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave main into int:
    let x as int is 5
    calling x.twice
    return 0
""")
    assert "E0006" in _codes(errors), [str(e) for e in errors]


def test_a_literal_receiver_does_not_even_parse():
    """A method call needs an access chain as its target, so there is no
    'mutate a temporary' hazard to report: ``calling 5.twice`` is a parse error.
    """
    from pengu_parser.pengu_errors import ParseError
    from pengu_parser.pengu_parser import PenguParser

    with pytest.raises(ParseError):
        PenguParser().parse(MUTATING_INT + """
weave main into int:
    calling 5.twice
    return 0
""")


# ---------------------------------------------------------------------------
# the statement rewrite
# ---------------------------------------------------------------------------

def test_statement_call_is_rewritten_to_a_set(parse_and_check):
    """The checker rewrites the call in place, which is what makes E0006 free."""
    errors, ast, _ = parse_and_check(MUTATING_INT + """
weave main into int:
    var x as int is 5
    calling x.twice
    return 0
""")
    assert errors == [], [str(e) for e in errors]
    setters = [t for t in _iter_trees(ast) if t.data == "set_stmt"]
    assert setters, "the mutating statement was not rewritten into a 'set'"
    names = [
        str(da.children[0])
        for t in setters
        for da in _iter_trees(t)
        if da.data == "dot_access" and da.children
    ]
    assert "get_twice" in names, names


def test_non_returning_body_names_the_mutating_call(parse_and_check):
    """E0020 must describe what the user wrote, not the rewrite's 'set'."""
    errors, _, _ = parse_and_check(MUTATING_INT + """
weave bad into int:
    var x as int is 5
    calling x.twice
""")
    e0020 = [e for e in errors if e.code == "E0020"]
    assert e0020, [str(e) for e in errors]
    assert "mutating method twice" in str(e0020[0]), str(e0020[0])


# ---------------------------------------------------------------------------
# emitted C — one function, assignment at the call site
# ---------------------------------------------------------------------------

def test_one_c_function_and_an_assignment(emit_c):
    c = emit_c(MUTATING_INT + """
weave main into int:
    var x as int is 5
    calling x.twice
    return 0
""")
    assert "int32_t int_twice(int32_t self)" in c
    # Only one C function: the getter is a surface alias, never a second symbol.
    assert "int_get_twice" not in c
    assert "x = int_twice(x);" in c


def test_getter_emits_the_same_function_without_assigning(emit_c):
    c = emit_c(MUTATING_INT + """
weave main into int:
    var x as int is 5
    var r as int is calling x.get_twice
    return r
""")
    assert "int32_t int_twice(int32_t self)" in c
    assert "int_get_twice" not in c
    assert "int32_t r = int_twice(x);" in c


def test_shard_mutates_emits_one_function_per_receiver(emit_c):
    c = emit_c("""
enchanting shard T where T: Num and T: Ordo and T: Par:
    @mutates
    weave clamp with lo as T, hi as T into T:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self
weave main into int:
    var x as int is 50
    calling x.clamp with 0, 10
    var f as float is 1.0
    calling f.clamp with 0.0, 2.0
    return x
""")
    assert "int32_t int_clamp(int32_t self, int32_t lo, int32_t hi)" in c
    assert "float float_clamp(float self, float lo, float hi)" in c
    assert "get_clamp" not in c
    assert "x = int_clamp(x, 0, 10);" in c
