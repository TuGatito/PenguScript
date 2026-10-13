"""Pointer-assignability rules around ``ref to void``.

C's ``void*`` is the universal object pointer: a ``T*`` converts to either
``void*`` or ``const void*``, and a ``void*`` converts *back* to a typed ``T*``
without an explicit cast. PenguScript mirrors that direction for the void
wildcard, but keeps const-correctness: dropping ``frozen`` is still rejected.

The rule was introduced for FFI shims (``malloc`` returns ``void*``) and is
what lets ``std.memoria`` declare the runtime allocators as ``ref to void``
while its ``shard T`` wrappers return ``ref to T`` with no ``transmute`` and no
spurious ``[W0001]``.

These tests are the regression lock: if the wildcard arm in
``RefType.is_compatible`` is tightened, they fail.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_void_star_assigns_to_typed_ref(parse_and_check):
    """``ref to void`` -> ``ref to T`` is implicit (C ``void*`` semantics)."""
    errors, _, _ = parse_and_check("""
declare c_alloc with n as usize into ref to void

weave alloc_int into ref to int:
    return calling c_alloc with 4

weave main into int:
    return 0
""")
    assert errors == [], [e.code for e in errors]


def test_void_star_assigns_to_frozen_typed_ref(parse_and_check):
    """``ref to void`` -> ``ref to frozen T`` adds const, which is safe."""
    errors, _, _ = parse_and_check("""
declare c_alloc with n as usize into ref to void

weave alloc_const_int into ref to frozen int:
    return calling c_alloc with 4

weave main into int:
    return 0
""")
    assert errors == [], [e.code for e in errors]


def test_const_void_star_assigns_to_const_typed_ref(parse_and_check):
    """``ref to frozen void`` -> ``ref to frozen T`` is const to const."""
    errors, _, _ = parse_and_check("""
declare c_get_const into ref to frozen void

weave get_const_int into ref to frozen int:
    return calling c_get_const

weave main into int:
    return 0
""")
    assert errors == [], [e.code for e in errors]


def test_const_void_star_does_not_assign_to_mutable_ref(parse_and_check):
    """``ref to frozen void`` -> ``ref to T`` would drop const: rejected."""
    errors, _, _ = parse_and_check("""
declare c_get_const into ref to frozen void

weave bad into ref to int:
    return calling c_get_const

weave main into int:
    return 0
""")
    assert errors, "dropping const through a void wildcard must be an error"


def test_typed_ref_assigns_to_void_and_const_void(parse_and_check):
    """The existing widening directions stay accepted."""
    errors, _, _ = parse_and_check("""
weave take_void with p as ref to void into void:
    return

weave take_const_void with p as ref to frozen void into void:
    return

weave drive with p as ref to int into void:
    calling take_void with p
    calling take_const_void with p
    return

weave main into int:
    return 0
""")
    assert errors == [], [e.code for e in errors]


def test_std_memoria_compiles_without_transmute(parse_and_check):
    """The shipped module must not need an unsafe cast anywhere."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    source = (root / "std" / "memoria.pengu").read_text(encoding="utf-8")
    assert "transmute" not in source, (
        "std/memoria.pengu must rely on the void* wildcard, not transmute"
    )
