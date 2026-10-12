"""Phase 2 — `enchanting` accepts every primitive (parsing + registration).

`int` is a `base_type`, and the grammar's `enchanting_decl` now takes a
`type_or_param`, so `enchanting int:` and `enchanting shard T where T: …:` are
both productions of the same rule.  These tests are the cheap half: parse,
check, and look at what got registered.  Nothing here needs a C compiler.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.compiler.conftest import FIXTURES

pytestmark = pytest.mark.smoke

#: Every primitive spelling the grammar's `base_type` accepts, in the order the
#: task lists them.  `string` is deliberately absent: a string owns heap memory,
#: so its `self` stays `ref to string` (see `test_primitive_self.py`).
PRIMITIVES = (
    "int", "i8", "i16", "i32", "i64",
    "u8", "u16", "u32", "u64",
    "float", "f32", "f64", "char", "bool", "byte", "usize", "isize",
)


@pytest.mark.parametrize("prim", PRIMITIVES)
def test_all_primitives_accept_enchanting(parse_and_check, prim):
    errors, _, symbols = parse_and_check(f"""
enchanting {prim}:
    weave identity into {prim}:
        return self
""")
    assert errors == [], f"enchanting {prim} rejected: {[e.code for e in errors]}"
    assert symbols.methods, f"enchanting {prim} registered no method"


def test_enchanting_int_parses(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave abs into int:
        return self
""")
    assert errors == []


def test_enchanting_char_parses(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting char:
    weave to_upper into char:
        return self
""")
    assert errors == []


def test_enchanting_bool_parses(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting bool:
    weave to_int into int:
        return 0
""")
    assert errors == []


def test_enchanting_shard_numeric_parses(parse_and_check):
    """The canonical bounded-shard form from the design note."""
    errors, _, symbols = parse_and_check("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T
""")
    assert errors == []
    assert ("__shard__", "is_even") in symbols.methods


def test_enchanting_shard_unbounded_parses(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting shard T:
    weave identity into T:
        return self
""")
    assert errors == []


def test_multiple_methods_in_one_block(parse_and_check):
    errors, _, symbols = parse_and_check("""
enchanting int:
    weave clamp with lo as int, hi as int into int:
        return self
    weave double into int:
        return self + self
""")
    assert errors == []
    assert ("int", "clamp") in symbols.methods
    assert ("int", "double") in symbols.methods


def test_primitive_method_may_return_void(parse_and_check):
    """A void method is a pure function with no return value; nothing special."""
    errors, _, symbols = parse_and_check("""
enchanting int:
    weave show into void:
        return
""")
    assert errors == []
    assert ("int", "show") in symbols.methods


def test_canonical_name_merges_int_spellings(parse_and_check):
    """`int`, `i32` and `int32_t` are one C type, so they are one method key."""
    for spelling in ("int", "i32", "int32", "int32_t"):
        errors, _, symbols = parse_and_check(f"""
enchanting {spelling}:
    weave double into int:
        return self + self
""")
        assert errors == [], spelling
        assert ("int", "double") in symbols.methods, spelling


def test_enchanting_byte_is_the_u8_spelling(parse_and_check):
    """`byte` and `u8` are both `uint8_t`, so a byte receiver finds `u8` methods."""
    errors, _, _ = parse_and_check("""
enchanting u8:
    weave hi into int:
        return 1

weave f with b as byte into int:
    return calling b.hi
""")
    assert errors == []


def test_methods_are_opt_in(parse_and_check):
    """Without the `enchanting` block the call does not resolve (E0004)."""
    errors, _, _ = parse_and_check("""
weave main into int:
    var x as int is 1
    return calling x.double
""")
    assert any(e.code == "E0004" for e in errors), [e.code for e in errors]


@pytest.mark.parametrize("fixture", ["int_basic", "shard_numeric", "char_methods", "bool_methods"])
def test_fixture_programs_are_clean(parse_and_check, fixture):
    """The committed fixtures must parse and check; `coherence_conflict` is the
    one intentional failure and lives in `test_primitive_coherence.py`."""
    source = (FIXTURES / f"{fixture}.pengu").read_text(encoding="utf-8")
    errors, _, _ = parse_and_check(source, filename=str(FIXTURES / f"{fixture}.pengu"))
    assert errors == [], f"{fixture}.pengu: {[(e.code, str(e)) for e in errors]}"


def test_fixtures_directory_is_complete(pengu_root):
    """Guards against a fixture being renamed out from under the tests."""
    names = {p.stem for p in FIXTURES.glob("*.pengu")}
    expected = {"int_basic", "shard_numeric", "char_methods", "bool_methods", "coherence_conflict"}
    assert expected <= names, f"missing fixtures: {sorted(expected - names)}"
    assert isinstance(FIXTURES, Path)
