"""`frozen` — the read-only type qualifier (C's `const`).

Covers the syntax forms, the normalisation of `frozen ref to T`, the
assignability matrix (mutable → frozen flows, the reverse is an error), the C
spelling, the soft-keyword behaviour and the qsort use case end to end.
"""

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import CTypeMapper
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_types import (
    FrozenType, RefType, BaseType, INT_TYPE, STRING_TYPE, VOID_TYPE, ast_to_type,
)
from tests.conftest import compile_run, gen_bundle, requires_runtime

QSORT_SOURCE = """import std.spark

include "stdlib.h"

declare qsort with base as ref to void, nmemb as usize, size as usize, compar as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void

weave compare_ints with a as ref to frozen void, b as ref to frozen void into int:
    let xa is essence of (transmute a to ref to frozen int)
    let xb is essence of (transmute b to ref to frozen int)
    if xa < xb:
        return -1
    if xa > xb:
        return 1
    return 0

weave main into int:
    var xs as array of int with size 3 is [3, 1, 2]
    calling qsort with xs, 3, (size of int), compare_ints
    calling spark.println with ((xs at 0) to string)
    calling spark.println with ((xs at 1) to string)
    calling spark.println with ((xs at 2) to string)
    return 0
"""


def parse_type(source: str):
    """Parses ``weave f with a as <source> into void`` and returns the type."""
    tree = PenguParser().parse(f"weave f with a as {source} into void:\n    return\n")
    found = []

    def walk(node):
        if getattr(node, "data", None) == "param":
            found.append(node)
        for child in getattr(node, "children", []):
            walk(child)

    walk(tree)
    assert found, "param not found"
    return ast_to_type(found[0].children[1], lambda name: None)


def check(source: str):
    """Parses + type-checks ``source``."""
    tree = PenguParser().parse(source)
    PenguChecker(base_dir=".").check(tree, source=source, filename="t.pengu")


def check_error(source: str):
    """Parses + type-checks ``source`` expecting a failure; returns the error."""
    with pytest.raises(PenguError) as info:
        check(source)
    return info.value


class TestFrozenSyntax:
    def test_frozen_value(self):
        assert CTypeMapper.to_c_type(parse_type("frozen int")) == "const int32_t"

    def test_ref_to_frozen(self):
        assert CTypeMapper.to_c_type(parse_type("ref to frozen int")) == "const int32_t*"

    def test_frozen_ref_normalises_to_ref_to_frozen(self):
        # 'frozen ref to T' is sugar: the canonical form qualifies the pointee,
        # never the pointer (that is what 'let' expresses).
        sweet = parse_type("frozen ref to int")
        canonical = parse_type("ref to frozen int")
        assert isinstance(sweet, RefType)
        assert isinstance(sweet.target, FrozenType)
        assert sweet == canonical
        assert CTypeMapper.to_c_type(sweet) == "const int32_t*"

    def test_ref_to_frozen_void(self):
        assert CTypeMapper.to_c_type(parse_type("ref to frozen void")) == "const void*"

    def test_frozen_void(self):
        assert CTypeMapper.to_c_type(parse_type("frozen void")) == "const void"

    def test_frozen_user_type(self):
        assert CTypeMapper.to_c_type(parse_type("frozen Player")) == "const Player"

    def test_declarator_puts_the_identifier_first(self):
        t = parse_type("ref to frozen void")
        assert CTypeMapper.to_c_decl(t, "a") == "const void* a"
        assert CTypeMapper.to_c_decl(t, "a", restrict=True) == "const void* restrict a"

    def test_double_frozen_is_idempotent(self):
        assert parse_type("frozen frozen int") == parse_type("frozen int")

    def test_frozen_is_a_soft_keyword(self):
        # 'frozen' only acts in type position; identifiers keep working.
        check(
            "rune R:\n"
            "    frozen as int\n\n"
            "weave frozen into int:\n"
            "    return 1\n\n"
            "weave main into int:\n"
            "    var frozen as int is 3\n"
            "    var r as R is with frozen is frozen\n"
            "    return calling frozen\n"
        )

    def test_frozen_in_signature_example(self):
        check(
            "declare qsort with base as ref to void, nmemb as usize, size as usize,"
            " compar as ref to weave with a as ref to frozen void,"
            " b as ref to frozen void into int into void\n"
        )


class TestFrozenAssignability:
    def test_mutable_flows_into_frozen(self):
        assert INT_TYPE.is_compatible(FrozenType(INT_TYPE))
        assert RefType(INT_TYPE).is_compatible(RefType(FrozenType(INT_TYPE)))

    def test_frozen_does_not_flow_into_mutable(self):
        assert not FrozenType(INT_TYPE).is_compatible(INT_TYPE)
        assert not RefType(FrozenType(INT_TYPE)).is_compatible(RefType(INT_TYPE))

    def test_frozen_to_frozen(self):
        assert FrozenType(INT_TYPE).is_compatible(FrozenType(INT_TYPE))
        assert FrozenType(INT_TYPE) != INT_TYPE

    def test_predicates_delegate_to_the_target(self):
        frozen = FrozenType(INT_TYPE)
        assert frozen.is_numeric() and frozen.is_int() and not frozen.is_string()
        assert FrozenType(STRING_TYPE).is_string()

    def test_size_is_unchanged(self):
        from pengu_parser.pengu_types import estimate_size

        assert estimate_size(FrozenType(INT_TYPE)) == estimate_size(INT_TYPE)

    def test_passing_frozen_where_mutable_is_expected_is_e0005(self):
        exc = check_error(
            "declare take with p as ref to int into void\n\n"
            "weave main with q as ref to frozen int into int:\n"
            "    calling take with q\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"

    def test_passing_mutable_where_frozen_is_expected_is_clean(self):
        check(
            "declare take with p as ref to frozen int into void\n\n"
            "weave main with q as ref to int into int:\n"
            "    calling take with q\n"
            "    return 0\n"
        )

    def test_set_on_frozen_value_is_e0006(self):
        exc = check_error(
            "weave main into int:\n"
            "    var y as frozen int is 5\n"
            "    set y is 7\n"
            "    return 0\n"
        )
        assert exc.code == "E0006"

    def test_write_through_frozen_pointee_is_e0006(self):
        exc = check_error(
            "rune P:\n    x as int\n\n"
            "weave main with p as ref to frozen P into int:\n"
            "    set p->x is 1\n"
            "    return 0\n"
        )
        assert exc.code == "E0006"

    def test_rebinding_a_frozen_pointer_is_allowed(self):
        # 'frozen' qualifies the pointee, not the pointer: the pointer itself
        # stays assignable (C's 'const T* p' vs 'T* const p').
        check(
            "weave main with a as ref to frozen int, b as ref to frozen int into int:\n"
            "    var p as ref to frozen int is a\n"
            "    set p is b\n"
            "    return 0\n"
        )

    def test_frozen_value_needs_an_explicit_conversion(self):
        # Assignability is one-directional, so a frozen value landing in a
        # mutable slot is converted explicitly (or produced by an operation).
        assert check_error(
            "weave f with a as frozen int into int:\n    return a\n"
        ).code == "E0020"
        check("weave f with a as frozen int into int:\n    return (a to int)\n")
        check("weave f with a as frozen int into int:\n    return a + 0\n")
        check(
            "weave f with a as frozen int into int:\n"
            "    var n as int is (a to int)\n"
            "    return n\n"
        )

    def test_frozen_composes_with_containers_and_aliases(self):
        check("rune P:\n    x as frozen int\n")
        check("alias ConstInt as frozen int\nweave f with a as ConstInt into int:\n    return 0\n")
        check("weave f with a as maybe frozen int into int:\n    return 0\n")
        check("weave f with a as list of frozen int into int:\n    return 0\n")
        check("weave f with a as slice of frozen int into int:\n    return 0\n")
        check("weave f with a as frozen array of int with size 3 into int:\n    return 0\n")
        check("weave f into usize:\n    return size of frozen int\n")


class TestFrozenQSort:
    """The use case `frozen` exists for: a C callback taking `const void*`."""

    def test_callback_signature_is_const(self):
        code = gen_bundle(QSORT_SOURCE)
        assert "int32_t compare_ints(const void* a, const void* b)" in code
        assert "qsort(xs, 3, (sizeof(int32_t)), ((int32_t (*)(const void*, const void*))compare_ints))" in code

    @requires_runtime
    def test_sorts_through_the_c_callback(self):
        res = compile_run(QSORT_SOURCE, tag="qsort_frozen")
        assert res.stdout.split() == ["1", "2", "3"]


class TestArrayDecay:
    def test_array_is_accepted_where_a_pointer_is_expected(self):
        # C array-to-pointer decay: 'calling qsort with xs, …'.
        check(
            "declare take with p as ref to void into void\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 2 is [1, 2]\n"
            "    calling take with xs\n"
            "    return 0\n"
        )

    def test_incompatible_element_type_is_rejected(self):
        exc = check_error(
            "declare take with p as ref to string into void\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 2 is [1, 2]\n"
            "    calling take with xs\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"


class TestFrozenVoidPointer:
    """`ref to frozen void` (C's `const void*`) is the catch-all object pointer."""

    def test_frozen_void_accepts_any_pointee(self):
        # The C headers map 'const void*' to 'ref to frozen void', so it must
        # keep accepting every 'T*' the way 'ref to void' always has.
        check(
            "declare take with p as ref to frozen void into void\n\n"
            "weave main into int:\n"
            "    var f as f32 is 1.5\n"
            "    var n as int is 7\n"
            "    var b as bool is true\n"
            "    calling take with sigil of f\n"
            "    calling take with sigil of n\n"
            "    calling take with sigil of b\n"
            "    return 0\n"
        )

    def test_frozen_void_accepts_a_frozen_pointee(self):
        check(
            "declare take with p as ref to frozen void into void\n\n"
            "weave main with a as ref to frozen int into int:\n"
            "    calling take with a\n"
            "    return 0\n"
        )

    def test_void_accepts_a_frozen_pointee(self):
        # C allows adding 'const' at any depth: 'const T*' -> 'const void*' and
        # 'const T*' -> 'void*' are both valid implicit conversions.
        check(
            "declare take with p as ref to void into void\n\n"
            "weave main with a as ref to frozen int into int:\n"
            "    calling take with a\n"
            "    return 0\n"
        )

    def test_frozen_void_accepts_arrays(self):
        check(
            "declare take with p as ref to frozen void into void\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 2 is [1, 2]\n"
            "    calling take with xs\n"
            "    return 0\n"
        )

    def test_frozen_void_still_rejects_non_pointers(self):
        exc = check_error(
            "declare take with p as ref to frozen void into void\n\n"
            "weave main into int:\n"
            "    calling take with 3\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"

    def test_frozen_void_alias_is_also_a_wildcard(self):
        check(
            "alias ConstPtr as ref to frozen void\n"
            "declare take with p as ConstPtr into void\n\n"
            "weave main into int:\n"
            "    var n as int is 1\n"
            "    calling take with sigil of n\n"
            "    return 0\n"
        )

    def test_string_literal_converts_to_frozen_void(self):
        # The C bindings type 'const void*' as 'ref to frozen void', and C
        # allows 'char*' -> 'const void*': a string literal must still work.
        check(
            "declare take with p as ref to frozen void into void\n\n"
            "weave main into int:\n"
            "    calling take with \"literal\"\n"
            "    return 0\n"
        )

    def test_string_literal_is_emitted_as_a_c_literal(self):
        code = gen_bundle(
            "declare take with p as ref to frozen void into int\n\n"
            "weave main into int:\n"
            "    return calling take with \"hi\"\n"
        )
        assert 'take("hi")' in code
