"""Consolidated PARSER / SEMANTIC-CHECKER / CONST-FOLDING / CODEGEN-EMISSION tests.

This single module merges the meaningful, toolchain-free coverage of the old
sprawling test suite (the originals lived in the previous, removed suite):

* test_01_imports, test_02_types, test_03_vars, test_04_arithmetic_bitwise,
  test_05_arrays_slices, test_06_structs, test_07_enchanting, test_08_functions,
  test_09_control, test_10_maybe_result, test_11_memory, test_12_integration
* semantic/* (arrays, c_interop, control, destructuring, enchanting,
  implicit_return, inference*, integration_fail, list_push_type, maybe,
  mutability, opaque, or_error, pointers, scope, string_interp, struct)
* test_all_types / test_types_compat / test_type_system_enhancements / test_null
  / test_named_args / test_named_positional / test_generics / test_omen_values
  / test_multi_error / test_rust_errors / test_variadic_many
  / test_ref_char_literals / test_codegen / test_codegen_fixes
  / test_const_folding / test_result_echo

NOTE: only pure parse/check/codegen-emission checks live here (no gcc).  Tests
are grouped into classes by topic; pytest.mark.parametrize compresses the
repetitive one-liner checks the originals spelled out with setUp/assertRaises.
"""

import re

import pytest

# Shared helpers from the new conftest.
from tests.conftest import check_ok, gen_bundle

# Compiler internals used for symbol-table introspection and for multi-module
# generic-monomorphization deduplication (which conftest cannot express).
from pengu_parser import PenguChecker, PenguParser
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_infer import ConstFolder
from pengu_parser.pengu_symbols import SymbolTable
from pengu_parser.pengu_types import (
    INT_TYPE,
    FLOAT_TYPE,
    STRING_TYPE,
    ListType,
    ManyType,
    MapType,
    ResultType,
    RuneType,
    mangle_type,
)

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def expect_error(source, filename="t.pengu", contains=None):
    """Assert ``source`` fails to compile; return the error text.

    ``contains`` may be a substring (or a list of substrings) of the message;
    an error code such as ``E0001`` is also accepted (codes are stored on the
    raised error, not in its message).

    Note: ``tests.conftest.check_error`` currently raises NameError (it refers
    to an undefined ``base_dir``), so this module carries its own equivalent.
    """
    tree = PenguParser().parse(source)
    checker = PenguChecker(base_dir=".")
    try:
        checker.check(tree, source=source, filename=filename)
    except PenguError as exc:
        text = str(exc)
        codes = [e.code for e in getattr(exc, "all_errors", [])] + [exc.code]
    except Exception as exc:  # noqa: BLE001 - keep whatever error was raised
        text = str(exc)
        codes = []
    else:
        raise AssertionError("expected a compile error but the source is clean")
    if contains is not None:
        wanted = [contains] if isinstance(contains, str) else contains
        for w in wanted:
            if w in text or w in codes:
                continue
            raise AssertionError(
                f"error {text!r} (codes {codes}) does not mention {w!r}"
            )
    return text


def strip_ansi(text):
    """Remove ANSI colour escapes pytest output from a rendered diagnostic."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def check_error_code(source, code):
    """Assert the raised error (or one of its accumulated errors) is ``code``."""
    tree = PenguParser().parse(source)
    checker = PenguChecker(base_dir=".")
    try:
        checker.check(tree, source=source, filename="t.pengu")
    except PenguError as exc:
        codes = [e.code for e in getattr(exc, "all_errors", [])]
        codes.append(getattr(exc, "code", None))
        assert code in codes, f"expected error {code}, got {codes}: {exc}"
        return exc
    raise AssertionError(f"expected error {code} but the source is clean")


# ---------------------------------------------------------------------------
# 1. Imports / includes / C-interop directives
# ---------------------------------------------------------------------------


class TestImportsAndCDirectives:
    """Top-level ``import`` / ``include`` / ``link`` / C-macro handling."""

    @pytest.mark.parametrize(
        "source",
        [
            "import src.components.Player\nimport src.math.Vec2\nimport my_module\n",
            'include "raylib.h"\ninclude "pengu_runtime.h"\n',
            'link "raylib"\nlink "m"\n',
            'import src.math.Vec2\ninclude "raylib.h"\nlink "raylib"\nlink "m"\n',
            'include "raylib.h"\nlink "raylib"\n\nweave main into int:\n  '
            'let k is KEY_W\n  let f is FLAG_WINDOW_RESIZABLE\n  return k\n',
            'include "<stdio.h>"\nweave main into void:\n  return\n',
        ],
    )
    def test_import_include_link_parse_and_check(self, source):
        check_ok(source)

    def test_c_define_without_include_fails(self):
        expect_error(
            "weave main into int:\n  let k is KEY_W\n  return k\n",
            contains=["C define 'KEY_W'", "include"],
        )

    def test_std_modules_import(self):
        check_ok('import std.spark\n\nweave main into void:\n  calling spark.println with "hi"\n')


# ---------------------------------------------------------------------------
# 2. Primitive / reference / collection / pointer-to-weave type aliases
# ---------------------------------------------------------------------------


class TestTypeAliases:
    """``alias`` declarations for every base/ref/collection shape."""

    @pytest.mark.parametrize(
        "source",
        [
            "\n".join(
                [
                    "alias MyInt as int",
                    "alias MyI32 as i32",
                    "alias MyI64 as i64",
                    "alias MyFloat as float",
                    "alias MyF32 as f32",
                    "alias MyF64 as f64",
                    "alias MyBool as bool",
                    "alias MyString as string",
                    "alias VoidPtr as ref to void",
                    "alias IntPtr as ref to int",
                ]
            ),
            "\n".join(
                [
                    "alias IntArray as array of int",
                    "alias IntSlice as slice of int",
                    "alias VecList as list of int",
                    "alias LookupMap as map of int to string",
                    "alias MaybeUser as maybe int",
                    "alias Texture as opaque",
                ]
            ),
            "\n".join(
                [
                    "alias AddFunc as ref to weave with int, int into int",
                    "alias WebUIHandler as ref to weave with e as ref to void into void",
                    "alias VoidCallback as ref to weave into void",
                ]
            ),
            "alias MyResult as result of int to string\n"
            "weave main into void:\n  var x as int is 10\n",
            "alias Texture as opaque\nweave main into void:\n  var t as opaque is null\n",
        ],
    )
    def test_alias_forms_check(self, source):
        check_ok(source)

    def test_result_alias_target_type(self):
        checker = check_ok(
            "alias MyResult as result of int to string\n"
            "weave main into void:\n  var x as int is 10\n"
        )
        alias = checker.symbols.aliases["MyResult"]
        assert isinstance(alias.target, ResultType)
        assert alias.target.ok_type == INT_TYPE
        assert alias.target.err_type == STRING_TYPE


# ---------------------------------------------------------------------------
# 3. Constants / var / let / scope placement rules
# ---------------------------------------------------------------------------


class TestDeclarationsScope:
    """Top-level const/var/let placement and const-inside-weave rules."""

    def test_valid_globals_and_locals(self):
        check_ok(
            """const MAX_ENTITIES as int is 1000
const PI as float is 3.14

rune Vec2:
  x as float
  y as float

weave main into int:
  var x as int is 10
  let y as int is 20
  var my_vec as Vec2 is with x is 1.0 and y is 2.0
  let a, b is my_vec
  set x is x + 1
  return 0
"""
        )

    def test_valid_constants_usable_inside_weave(self):
        check_ok(
            """const MAX as int is 100
const PI as float is 3.14

weave compute with a as int into int:
  var x as int is a
  let y as int is 20
  set x is x + y + MAX
  return x
"""
        )

    def test_const_inside_weave_fails(self):
        expect_error(
            "weave main into int:\n  const LOCAL_MAX as int is 100\n  return 0\n",
            contains=["E0001", "'const' is only allowed at top-level"],
        )

    def test_var_top_level_fails(self):
        expect_error(
            "var global_x as int is 10\nweave main into int:\n  return 0\n",
            contains=["E0002", "'var' is not allowed at top-level"],
        )

    def test_let_top_level_fails(self):
        expect_error(
            "let global_y as int is 10\nweave main into int:\n  return 0\n",
            contains=["E0002", "'let' is not allowed at top-level"],
        )


# ---------------------------------------------------------------------------
# 4. Mutability rules
# ---------------------------------------------------------------------------


class TestMutability:
    """var is mutable; let and const are immutable."""

    def test_var_mutable(self):
        check_ok("weave main into void:\n  var x as int is 10\n  set x is 20\n")

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into void:\n  let x as int is 10\n  set x is 20\n",
            "const MAX as int is 100\nweave main into void:\n  set MAX is 200\n",
            "weave main into void:\n  let x is 10\n  set x is 20\n",
        ],
    )
    def test_immutable_assignment_fails(self, source):
        expect_error(source, contains=["E0006"])

    def test_const_assignment_message(self):
        expect_error(
            "const MAX as int is 100\nweave main into void:\n  set MAX is 200\n",
            contains="Cannot assign to constant 'MAX'",
        )


# ---------------------------------------------------------------------------
# 5. Type compatibility, casts, arithmetic and bitwise ops
# ---------------------------------------------------------------------------


class TestTypeCompatAndOperators:
    """Implicit conversions are rejected; explicit casts/ops type-check."""

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into void:\n  let x as int is 3.14\n",
            "weave main into void:\n  let x as int is \"hello\"\n",
            "weave main into void:\n  let x as int is true\n",
        ],
    )
    def test_implicit_conversion_to_int_fails(self, source):
        expect_error(source, contains=["E0005", "declared as 'int'"])

    def test_explicit_casts_pass(self):
        check_ok(
            "weave main into void:\n"
            "  let x as int is 3.14 to int\n"
            "  let y as float is 3 to float\n"
        )

    def test_arithmetic_and_transmute_pass(self):
        check_ok(
            """include "raylib.h"

weave compute into void:
  let a is 10 + 20 * 2
  let b is (10 + 20) * 2
  let f as float is 10 to float
  let bits is transmute f to int

weave flags_test into void:
  let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
  let masked is flags & 0xFF
  let xored is flags ^ 1
  let not_flags is ~flags
  let shifted is 1 << 5
  let rshift is 32 >> 2
"""
        )

    def test_casts_simple(self):
        check_ok(
            "weave main into void:\n"
            "  let f as float is 10 to float\n"
            "  let i is f to int\n"
            "  let t is transmute f to int\n"
        )


# ---------------------------------------------------------------------------
# 6. Struct (rune) field access and struct-init inference
# ---------------------------------------------------------------------------


VEC2 = """rune Vec2:
  x as float
  y as float
"""


class TestStructFieldAccess:
    def test_valid_field_access(self):
        check_ok(
            VEC2
            + "weave main into float:\n"
            "  let v as Vec2 is with x is 10 and y is 20\n"
            "  return v.x + v.y\n"
        )

    def test_unknown_field_fails(self):
        expect_error(
            VEC2
            + "weave main into float:\n"
            "  let v as Vec2 is with x is 10 and y is 20\n"
            "  return v.z\n",
            contains=["E0013", "has no field 'z'"],
        )

    def test_field_on_primitive_fails(self):
        expect_error(
            "weave main into int:\n  let n as int is 10\n  return n.x\n",
            contains="Cannot access field 'x' on non-struct type 'int'",
        )

    def test_unknown_field_in_initializer_fails(self):
        expect_error(
            VEC2
            + "weave main into void:\n  let v is with unknown_field is 10\n",
            contains="no rune matches",
        )


class TestStructInitInference:
    """Inferring the rune behind a bare ``with ...`` struct initializer."""

    def test_explicit_annotation_passes(self):
        check_ok(
            VEC2
            + "weave main into void:\n  let v as Vec2 is with x is 1.0 and y is 2.0\n"
        )

    def test_single_match_inferred(self):
        check_ok(
            VEC2
            + "weave main into void:\n  let v is with x is 1.0 and y is 2.0\n"
        )

    @pytest.mark.parametrize(
        "source, fragments",
        [
            (
                "weave main into void:\n  let v is with x is 1.0 and y is 2.0\n",
                ["E0010", "no rune matches"],
            ),
            (
                VEC2
                + "rune Point2D:\n  x as float\n  y as float\n\n"
                "weave main into void:\n  let v is with x is 1.0 and y is 2.0\n",
                ["E0011", "Ambiguous"],
            ),
        ],
    )
    def test_no_match_or_ambiguous_fails(self, source, fragments):
        expect_error(source, contains=fragments)


class TestStructMemberMutation:
    def test_field_and_arrow_writes(self):
        check_ok(
            VEC2
            + """weave main into void:
  var v as Vec2 is with x is 10.0 and y is 20.0
  let vx is v.x
  set v.x is 100.0
  var vp as ref to Vec2 is sigil of v
  set vp->x is 100.0
"""
        )


# ---------------------------------------------------------------------------
# 7. Echo (union) and omen (tagged union) types
# ---------------------------------------------------------------------------


class TestEchoOmenSemantics:
    @pytest.mark.parametrize(
        "source",
        [
            "echo MyEcho:\n  a as int\n  b as float\n"
            "weave main into void:\n  var x as int is 10\n",
            "omen Result:\n  Ok with value as int\n  Err with msg as string\n"
            "weave main into void:\n  var x as int is 10\n",
            "omen Level:\n  ONE\n  TWO\n  THREE\n"
            "weave main into void:\n  var x as int is 10\n",
        ],
    )
    def test_echo_and_omen_declarations_check(self, source):
        check_ok(source)

    def test_echo_registered_with_fields(self):
        checker = check_ok(
            "echo MyEcho:\n  a as int\n  b as float\n"
            "weave main into void:\n  var x as int is 10\n"
        )
        echo = checker.symbols.echos["MyEcho"]
        assert "a" in echo.fields
        assert "b" in echo.fields

    def test_omen_variants_constructible(self):
        check_ok(
            """omen NetworkState:
  Disconnected
  Connecting with retry_count as int
  Connected with session_id as string
  Failed with error_code as int and reason as string

weave main into void:
  var state as NetworkState is with Connected is with session_id is "sess_123"
"""
        )

    def test_simple_enum_variants(self):
        check_ok(
            """omen Level:
  ONE
  TWO
  THREE

weave main into string:
  var l1 as Level is Level_ONE
  var l2 as Level is Level.TWO
  var l3 as Level is THREE
  let res is judge l2:
    when Level_ONE -> "1"
    when Level.TWO -> "2"
    when THREE -> "3"
    else -> "other"
  return res
"""
        )


class TestOmenValues:
    """Numeric enum values: explicit, auto-increment, const refs, errors."""

    def _variant_values(self, source, filename="t.pengu"):
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        checker.check(tree, source=source, filename=filename)
        return checker.symbols.lookup("Nivel").type.variant_values

    def test_explicit_start_auto_increment(self):
        vals = self._variant_values(
            "omen Nivel:\n    One is 3\n    Two\n    Three\n"
        )
        assert vals == {"One": 3, "Two": 4, "Three": 5}

    def test_all_explicit_values(self):
        vals = self._variant_values(
            "omen Nivel:\n    Uno is 1\n    Dos is 2\n    Tres is 3\n"
        )
        assert vals == {"Uno": 1, "Dos": 2, "Tres": 3}

    def test_mixed_auto_and_explicit(self):
        vals = self._variant_values(
            "omen Nivel:\n    Uno\n    Dos\n    Tres is 6\n    Cuatro\n"
        )
        assert vals == {"Uno": 0, "Dos": 1, "Tres": 6, "Cuatro": 7}

    def test_constant_expressions_and_references(self):
        vals = self._variant_values(
            "const BASE as int is 10\n\nomen Nivel:\n"
            "    None_ is 0\n    Start is BASE\n    Next\n    Shifted is 1 << 4\n"
        )
        assert vals == {"None_": 0, "Start": 10, "Next": 11, "Shifted": 16}

    @pytest.mark.parametrize(
        "source, code, fragment",
        [
            (
                "omen Mitad:\n    Uno\n    Dos\n    Tres is 5\n    Cuatro is 1\n",
                "E0027",
                "Duplicate value '1' in omen 'Mitad'",
            ),
            (
                "omen ResultPayload:\n    Ok with val as int\n    Err is 404 with msg as string\n",
                "E0028",
                "Value assignment is not allowed on algebraic omen variant",
            ),
            (
                "omen Floats:\n    A is 3.14\n    B\n",
                "E0029",
                "must be a compile-time integer constant",
            ),
        ],
    )
    def test_invalid_omen_values(self, source, code, fragment):
        exc = check_error_code(source, code)
        assert fragment in str(exc)


# ---------------------------------------------------------------------------
# 8. Arrays / slices / lists / maps (semantics)
# ---------------------------------------------------------------------------


class TestCollectionsSemantics:
    @pytest.mark.parametrize(
        "source",
        [
            "weave main into int:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  let slice_part is arr at 1 to 4\n"
            "  let length_val is arr length\n"
            "  return first\n",
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  set arr at 0 is 99\n"
            "  let part as slice of int is arr at 1 to 3\n"
            "  let n is part length\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  var m as map of int to string is map of int to string\n",
        ],
    )
    def test_array_slice_list_map_ops(self, source):
        check_ok(source)

    def test_non_int_index_fails(self):
        expect_error(
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            '  let item is arr at "invalid_index"\n',
            contains="index must be an integer",
        )

    def test_non_int_slice_bound_fails(self):
        expect_error(
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            '  let part is arr at "start" to 5\n',
            contains="Slice range bounds must be integers",
        )

    def test_array_size_expr_accepted(self):
        check_ok(
            "const SIZE as int is 4 + 4\n"
            "weave main into void:\n"
            "  var buf as array of int is array of int with size 4 + 4\n"
        )


class TestListPushType:
    @pytest.mark.parametrize(
        "source",
        [
            "weave main into void:\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  calling l.push with 5\n",
            VEC2
            + "weave main into void:\n"
            "  var l as list of Vec2 is list of Vec2 with capacity 10\n"
            "  calling l.push with with x is 1.0 and y is 2.0\n",
        ],
    )
    def test_push_compatible_passes(self, source):
        check_ok(source)

    @pytest.mark.parametrize(
        "source, fragment",
        [
            (
                "weave main into void:\n"
                "  var l as list of int is list of int with capacity 10\n"
                '  calling l.push with "hi"\n',
                "push expects int, got string",
            ),
            (
                VEC2
                + "weave main into void:\n"
                "  var l as list of Vec2 is list of Vec2 with capacity 10\n"
                "  calling l.push with 5\n",
                "push expects Vec2, got int",
            ),
        ],
    )
    def test_push_incompatible_fails(self, source, fragment):
        expect_error(source, contains=fragment)


# ---------------------------------------------------------------------------
# 9. maybe / result / or-error
# ---------------------------------------------------------------------------


class TestMaybeResultOrError:
    def test_maybe_decl_and_unwrap(self):
        check_ok(
            """rune User:
  name as string

weave main into string:
  let u as maybe User is maybe none
  let guest as string is "guest"
  let u2 as maybe string is maybe none
  let result is u2 or else guest
  return result
"""
        )

    def test_or_else_or_block_try(self):
        check_ok(
            """declare open_file with path as string into maybe string
declare print with msg as string into void

weave maybe_test into int:
  let user as maybe string is maybe none
  let name is user or else "guest"
  let u is user or return 1

  let file is calling open_file with "data.txt" or:
    let err is error
    calling print with err
    return 1

  let file2 is try calling open_file with "other.txt"
  return 0
"""
        )

    def test_or_error_simple(self):
        check_ok(
            """declare open_file with path as string into maybe string
declare print with msg as string into void

weave main into int:
  let opt as maybe string is maybe none
  let fallback is opt or else "default"

  let res is calling open_file with "test.txt" or:
    let err is error
    calling print with err
    return 1

  return 0
"""
        )

    def test_maybe_none_without_type_fails(self):
        expect_error(
            "weave main into void:\n  let u is maybe none\n",
            contains=["E0014", "requires explicit type context"],
        )

    def test_error_outside_or_block_fails(self):
        expect_error(
            "weave main into void:\n  let err is error\n",
            contains=["E0015", "'error' is only available inside 'or:'"],
        )

    def test_or_else_type_mismatch_fails(self):
        expect_error(
            "weave main into void:\n"
            "  let opt as maybe int is maybe none\n"
            '  let val is opt or else "string_fallback"\n',
            contains=["'or else' fallback type 'string' incompatible with 'int'"],
        )


# ---------------------------------------------------------------------------
# 10. Null handling
# ---------------------------------------------------------------------------


class TestNull:
    def test_null_pointer_decl_and_assign(self):
        check_ok(
            """rune Node:
    val as int
    next as ref to Node

weave test into void:
    var ptr as ref to int is null
    let obj as ref to Node is null
    var handle as opaque is null
    set ptr is null
    var n as Node is with val is 42 and next is null
"""
        )

    def test_null_comparisons(self):
        check_ok(
            """weave check_ptr with ptr as ref to int into bool:
    if ptr == null:
        return true
    if null != ptr:
        return false
    if null == null:
        return true
    return false
"""
        )

    def test_null_param_and_return(self):
        check_ok(
            """weave get_null into ref to int:
    return null

weave process_ptr with ptr as ref to int into void:
    var a as int is 0

weave test into void:
    var p as ref to int is calling get_null
    calling process_ptr with null
"""
        )

    @pytest.mark.parametrize(
        "source",
        [
            "weave test into void:\n    var x as int is null",
            "weave test into void:\n    var s as string is null",
            "weave test into void:\n    var b as bool is null",
        ],
    )
    def test_null_on_value_types_rejected(self, source):
        expect_error(source, contains="initialized with 'null'")

    def test_null_without_annotation_rejected(self):
        expect_error(
            "weave test into void:\n    var x is null",
            contains="requires an explicit type annotation",
        )
        expect_error(
            "weave test into void:\n    let y is null",
            contains="requires an explicit type annotation",
        )

    @pytest.mark.parametrize(
        "source, fragment",
        [
            (
                "weave test into void:\n"
                "    let x as int is 5\n"
                "    if x == null:\n        pass\n",
                "Cannot compare 'null' with non-pointer type 'int'",
            ),
            (
                'weave test into void:\n    var x as string is "a"\n    if x == null:\n        pass\n',
                "Cannot compare 'null' with non-pointer type 'string'",
            ),
            (
                "weave test into void:\n"
                "    var p as ref to int is null\n"
                "    if p < null:\n        pass\n",
                "Ordering comparison 'lt' is not supported for 'null'",
            ),
        ],
    )
    def test_null_bad_comparisons_rejected(self, source, fragment):
        expect_error(source, contains=fragment)

    def test_sigil_of_null_rejected(self):
        expect_error(
            "weave test into void:\n    var p as ref to ref to int is sigil of null\n",
            contains="E0008",
        )


# ---------------------------------------------------------------------------
# 11. Pointers, sigil/essence, memory ops (banish / defer / errdefer)
# ---------------------------------------------------------------------------


class TestPointersAndMemory:
    def test_sigil_essence_roundtrip(self):
        check_ok(
            """weave main into int:
  var x as int is 42
  let p as ref to int is sigil of x
  let val as int is essence of p
  set essence of p is 100
  return val
"""
        )

    @pytest.mark.parametrize(
        "source, fragment",
        [
            (
                "weave main into void:\n  let p is sigil of 10\n",
                "Cannot take 'sigil of' a literal or temporary expression",
            ),
            (
                "const MAX as int is 100\n"
                "weave main into void:\n  let p is sigil of MAX\n",
                "Cannot take 'sigil of' constant 'MAX'",
            ),
        ],
    )
    def test_sigil_of_literal_or_const_fails(self, source, fragment):
        expect_error(source, contains=["E0008", fragment])

    def test_memory_management_ops(self):
        check_ok(
            """declare alloc with bytes as int into ref to int

weave test_memory into void:
  let p as ref to int is calling alloc with size of int
  defer banish p
  errdefer banish p
  set essence of p is 10
  banish p
"""
        )

    def test_maybe_ref_forward_structs(self):
        check_ok(
            """rune Node:
  value as int
  next as maybe ref to Node

rune Tree:
  root as maybe ref to Node
  count as int

weave create_tree into Tree:
  var n as Node is with value is 10 and next is maybe none
  return with root is maybe none and count is 1
"""
        )


# ---------------------------------------------------------------------------
# 12. Enchanting: self-> rules and member methods
# ---------------------------------------------------------------------------


class TestEnchantingSemantics:
    @pytest.mark.parametrize(
        "source",
        [
            VEC2
            + """enchanting Vec2:
  weave add with other as Vec2 into void:
    set self->x is self->x + other.x
    set self->y is self->y + other.y
""",
            VEC2
            + """enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    (self->x * self->x + self->y * self->y) to float

  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

weave main into void:
  let a as Vec2 is with x is 10 and y is 20
  let b as Vec2 is with x is 5 and y is 5
  let c is calling a.add with b
  var d as Vec2 is a
  calling d.move with 10, 0
""",
        ],
    )
    def test_enchanting_methods_check(self, source):
        check_ok(source)

    def test_self_dot_access_fails(self):
        expect_error(
            VEC2
            + """enchanting Vec2:
  weave move with dx as float into void:
    set self.x is self.x + dx
""",
            contains=["E0003", "must be accessed with '->', not '.'"],
        )

    def test_enchant_undefined_rune_fails(self):
        expect_error(
            """enchanting NonExistent:
  weave foo into void:
    return
""",
            contains="Cannot enchant undefined Rune",
        )


class TestGenericEnchantingSemantics:
    def test_generic_enchanting_method(self):
        check_ok(
            """rune Box shard T:
  value as T

enchanting Box of T:
  weave get into T:
    return self->value

weave main into void:
  let b as Box of int is with value is 99
  let v as int is calling b.get
"""
        )


# ---------------------------------------------------------------------------
# 13. Implicit returns and value-flow rules
# ---------------------------------------------------------------------------


class TestImplicitReturn:
    def test_expression_body_returns_value(self):
        check_ok("weave add with a as int, b as int into int:\n  a + b\n")

    @pytest.mark.parametrize(
        "source, fragment",
        [
            (
                'weave get_name into int:\n  "pengu"\n',
                "Implicit return type 'string' does not match weave return type 'int'",
            ),
            (
                'weave compute into int:\n  let x is 10\n  "not an int"\n',
                "Implicit return type 'string' does not match weave return type 'int'",
            ),
        ],
    )
    def test_implicit_return_mismatch_fails(self, source, fragment):
        expect_error(source, contains=["E0020", fragment])

    def test_bare_return_in_value_function_fails(self):
        expect_error(
            "weave get_number into int:\n  return\n",
            contains="Returned value of type 'void' does not match weave return type 'int'",
        )


# ---------------------------------------------------------------------------
# 14. Control-flow semantics (break/continue/for bounds)
# ---------------------------------------------------------------------------


class TestControlFlowSemantics:
    def test_rich_control_flow_checks(self):
        check_ok(
            """rune Player:
  x as float
  y as float

enchanting Player:
  weave move with dist as int into void:
    set self->x is self->x + dist

rune File:
  name as string

declare open with path as string into maybe File
declare print with val as string into void

weave test_flow with opt_x as maybe int, key as string, arr as list of int into int:
  var x as int is 0
  let color is if x > 10 then "red" else "blue"

  if file as File is calling open with "data.txt" is present:
    calling print with file.name

  if opt_x is present:
    return 1

  unless opt_x is present:
    return 1

  let state as string is judge key:
    when "w" -> "up"
    when "s" -> "down"
    else -> "idle"

  while x < 10:
    set x is x + 1
    if x == 5: continue
    if x == 9: break

  for i from 0 to 10:
    calling print with "loop"

  for item in arr:
    calling print with "item"

  var player as Player is with x is 10 and y is 20
  with player:
    set.x is 100
    set.y is 200
    calling.move with 5

  return 0
"""
        )

    def test_stepped_for_range(self):
        check_ok(
            """weave main with arr as list of int into int:
  var i as int is 0
  for idx from 0 to 10 step 2:
    set i is idx
  for item in arr:
    let val is item
  return 0
"""
        )

    @pytest.mark.parametrize(
        "source, fragment",
        [
            (
                "weave main into void:\n  break\n",
                "'break' is only allowed inside loops",
            ),
            (
                "weave main into void:\n  continue\n",
                "'continue' is only allowed inside loops",
            ),
            (
                'weave main into void:\n  for i from "start" to 10:\n    let x is i\n',
                "'for from' start bound must be integer",
            ),
            (
                "weave main into void:\n  set .x is 10\n",
                "used outside 'with' statement",
            ),
        ],
    )
    def test_invalid_control_flow_fails(self, source, fragment):
        expect_error(source, contains=fragment)


# ---------------------------------------------------------------------------
# 15. Functions: declarations, defaults, named/positional args, variadic
# ---------------------------------------------------------------------------


class TestFunctionDeclarations:
    def test_declares_inline_defaults_and_fn_pointer(self):
        check_ok(
            """weave add with a as int, b as int into int:
  a + b

weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

declare InitWindow with w as int, h as int, title as string into void
declare WindowShouldClose into bool

inline weave fast_add with a as int, b as int into int:
  a + b

weave main into int:
  calling DrawText with text is "hola" and x is 100
  calling DrawText with "hola", 100, 200
  let p_add is sigil of add
  return 0
"""
        )

    def test_mutually_recursive_weaves(self):
        check_ok(
            """weave is_even with n as int into bool:
  if n == 0:
    return true
  return calling is_odd with n - 1

weave is_odd with n as int into bool:
  if n == 0:
    return false
  return calling is_even with n - 1

weave main into void:
  var res as bool is calling is_even with 4
"""
        )

    def test_non_default_param_after_default_fails(self):
        expect_error(
            "weave bad_fn with a as int is 10, b as int into void:\n  return\n",
            contains="Non-default parameter 'b' follows default parameter",
        )


class TestNamedPositionalArgs:
    @pytest.mark.parametrize(
        "source",
        [
            """weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

weave main into void:
  calling DrawText with "hello", x is 10, y is 20
""",
            """weave foo with a as int, x as int, y as int into void:
  return

weave main into void:
  calling foo with 1 and x is 2 and y is 3
""",
            """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with 1 and 2
""",
            """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with x is 1 and y is 2
""",
        ],
    )
    def test_valid_argument_orderings(self, source):
        check_ok(source)

    @pytest.mark.parametrize(
        "source",
        [
            """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with x is 1 and 2
""",
            """weave foo with x as int, y as int, z as int into void:
  return

weave main into void:
  calling foo with x is 1 and y is 2 and 3
""",
            """weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

weave main into void:
  calling DrawText with x is 10, "hello"
""",
        ],
    )
    def test_positional_after_named_fails(self, source):
        expect_error(source, contains=["E0005", "Positional argument after named argument"])


class TestVariadicMany:
    def test_variadic_check_and_signature(self):
        source = """weave sum_all with base as int and values as many int into int:
    var total as int is base
    for v in values:
        set total is total + v
    return total

weave main into void:
    let r1 is calling sum_all with 10 and 20 and 30 and 40
    let r2 is calling sum_all with 100
"""
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        checker.check(tree, source=source, filename="t.pengu")
        fn = checker.symbols.functions["sum_all"]
        assert len(fn.params) == 2
        assert fn.params[0][0] == "base"
        assert fn.params[0][1] == INT_TYPE
        assert fn.params[1][0] == "values"
        assert isinstance(fn.params[1][1], ManyType)
        assert fn.params[1][1].element == INT_TYPE

    @pytest.mark.parametrize(
        "source, code, fragment",
        [
            (
                "weave bad_func with a as many int and b as many int into void:\n    return\n",
                "E0023",
                "Only one 'many' parameter is allowed",
            ),
            (
                "weave bad_func with a as many int and b as int into void:\n    return\n",
                "E0024",
                "The 'many' parameter must be the last parameter",
            ),
        ],
    )
    def test_variadic_declaration_errors(self, source, code, fragment):
        exc = check_error_code(source, code)
        assert fragment in str(exc)


# ---------------------------------------------------------------------------
# 16. Generics / shards
# ---------------------------------------------------------------------------


class TestGenericsSemantics:
    def test_generic_rune_and_function(self):
        check_ok(
            """rune Pair shard T and U:
  first as T
  second as U

weave identity shard T with x as T into T:
  return x

weave main into void:
  let p as Pair of int and float is with first is 42 and second is 3.14
  let a as int is calling identity with 100
  let s as string is calling identity with "pengu"
"""
        )

    def test_generic_swap(self):
        check_ok(
            """rune Pair shard T and U:
  first as T
  second as U

weave swap shard T and U with a as T, b as U into Pair of U and T:
  return with first is b and second is a

weave main into void:
  let p as Pair of float and int is calling swap with 10 and 2.5
"""
        )

    def test_generic_ritual_default_param(self):
        check_ok(
            """weave compute shard T with x as T, factor as int is 2 into int:
  return factor

weave main into void:
  let res is calling compute with "text"
"""
        )

    @pytest.mark.parametrize(
        "source, fragment",
        [
            # arity mismatch
            (
                """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair of int is with first is 1 and second is 2
""",
                "expects 2 type argument(s), got 1",
            ),
            # uninstantiated generic type
            (
                """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair is with first is 1 and second is 2
""",
                "requires type arguments",
            ),
            # duplicate type parameter
            (
                """rune Pair shard T and T:
  first as T
  second as T

weave main into void:
  return
""",
                "Duplicate type parameter in generic declaration 'Pair'",
            ),
            # default param depending on type parameter
            (
                """weave bad_fn shard T with x as T is 0 into T:
  return x

weave main into void:
  return
""",
                "cannot have a default value depending on type parameters",
            ),
        ],
    )
    def test_generic_declaration_errors(self, source, fragment):
        expect_error(source, contains=fragment)

    def test_type_param_outside_generic(self):
        check_error_code(
            "weave main into void:\n  let x as T is 10\n", "E0022"
        )


# ---------------------------------------------------------------------------
# 17. Concepts / bind / ritual / seals (type-system enhancements)
# ---------------------------------------------------------------------------


class TestConceptBindRitualSeal:
    @pytest.mark.parametrize(
        "source, code, fragment",
        [
            (
                """concept Adder:
  weave add with x as int, y as int into int

rune Calculator:
  dummy as int

bind Calculator with Adder:
  weave add with x as int into int:
    return x
""",
                "E0030",
                "parameter count mismatch",
            ),
            (
                """concept Greeter:
  weave greet into void
  weave goodbye into void

rune Person:
  name as string

bind Person with Greeter:
  weave greet into void:
    return
""",
                "E0031",
                "does not implement method 'goodbye'",
            ),
            (
                """concept Printable:
  weave print_me into void

rune Secret:
  data as int

weave output shard T where T: Printable with item as T into void:
  return

weave main into int:
  var s as Secret is with data is 123
  calling output with s
  return 0
""",
                "E0032",
                "does not implement concept 'Printable'",
            ),
            (
                """rune Point:
  x as int

enchanting Point:
  weave ritual create into Point:
    set self->x is 10
    return with x is 10
""",
                "E0033",
                "'self' cannot be used inside a 'ritual' method",
            ),
            (
                """rune Point:
  x as int

enchanting Point:
  weave ritual create into Point:
    return with x is 0

weave main into int:
  var p as Point is with x is 5
  var p2 as Point is calling p.create
  return 0
""",
                "E0034",
                "must be called on the type 'Point', not an instance",
            ),
        ],
    )
    def test_concept_ritual_errors(self, source, code, fragment):
        exc = check_error_code(source, code)
        assert fragment in str(exc)

    def test_seal_type_safety(self):
        check_ok(
            """seal UserId as int
seal PostId as int

weave process_user with u as UserId into int:
  return u to int

weave main into int:
  var u as UserId is 42 to UserId
  var p as PostId is 100 to PostId
  return calling process_user with u
"""
        )

    def test_seal_incompatible_assignment_fails(self):
        expect_error(
            """seal UserId as int
seal PostId as int

weave main into int:
  var u as UserId is 42 to UserId
  var p as PostId is u
  return 0
""",
            contains=["UserId", "PostId"],
        )

    def test_ritual_static_and_instance_method_semantics(self):
        check_ok(
            VEC2
            + """enchanting Vec2:
  weave ritual zero into Vec2:
    return with x is 0.0 and y is 0.0

  weave length_sq into float:
    return self->x * self->x + self->y * self->y

weave main into int:
  var v as Vec2 is calling Vec2.zero
  var len as float is calling v.length_sq
  return 0
"""
        )


# ---------------------------------------------------------------------------
# 18. Const folding (unit level + codegen emission)
# ---------------------------------------------------------------------------


class TestConstFolding:
    def test_arithmetic_folding(self):
        symbols = SymbolTable()
        folder = ConstFolder(symbols)
        tree = PenguParser().parse("const X as int is 10 + 20 * 2\n")
        expr = next(tree.find_data("const_decl")).children[-1]
        assert folder.fold(expr) == 50

    def test_bitwise_folding(self):
        symbols = SymbolTable()
        folder = ConstFolder(symbols)
        tree = PenguParser().parse("const FLAGS as int is (1 << 2) | (1 << 4)\n")
        expr = next(tree.find_data("const_decl")).children[-1]
        assert folder.fold(expr) == (4 | 16)

    def test_codegen_emits_folded_literal(self):
        c = gen_bundle("const A as int is 10 + 20\nweave main into void:\n  var x as int is A\n")
        assert "#define A 30" in c
        assert "int32_t x = 30;" in c

    def test_codegen_emits_folded_float_const(self):
        c = gen_bundle(
            "const PI as float is 3.5 + 0.5\nweave main into void:\n  var p as float is PI\n"
        )
        assert "#define PI" in c


class TestDeadCodeElimination:
    def test_constant_true_branch_only(self):
        c = gen_bundle(
            """weave main into void:
  var x as int is 0
  if true:
    set x is 1
  else:
    set x is 2
"""
        )
        assert "/* dead code eliminated (branch always true) */" in c
        assert "x = 1;" in c
        assert "x = 2;" not in c


# ---------------------------------------------------------------------------
# 19. Type-argument mangling
# ---------------------------------------------------------------------------


class TestTypeMangling:
    def test_mangle_names(self):
        assert mangle_type(RuneType(name="Pair", type_args=[INT_TYPE, FLOAT_TYPE])) == "Pair_int_float"
        assert mangle_type(ListType(element=INT_TYPE)) == "list_int"
        assert mangle_type(MapType(key=STRING_TYPE, value=INT_TYPE)) == "map_string_int"
        assert mangle_type(ResultType(ok_type=INT_TYPE, err_type=STRING_TYPE)) == "result_int_string"


# ---------------------------------------------------------------------------
# 20. Error diagnostics: error codes, rendering shape, multiple errors
# ---------------------------------------------------------------------------


E_CODE_CASES = [
    ("E0001", "weave main into void:\n  const X is 10"),
    ("E0002", "let v is 10"),
    (
        "E0003",
        "rune Player:\n  x as int\n\nenchanting Player:\n  weave move into void:\n    set self.x is 20",
    ),
    ("E0004", "weave main into void:\n  let x is unknown_var + 1"),
    ('E0005', 'weave main into void:\n  let x as int is "hello"'),
    ("E0006", "weave main into void:\n  let x is 10\n  set x is 20"),
    ("E0007", "weave main into void:\n  break"),
    ("E0008", "weave main into void:\n  let p is sigil of 123"),
    ("E0009", "weave main into void:\n  set .x is 10"),
    ("E0010", "weave main into void:\n  let v is with x is 1 and y is 2"),
    (
        "E0011",
        "rune Vec2A:\n  x as int\n  y as int\n\nrune Vec2B:\n  x as int\n  y as int\n\n"
        "weave main into void:\n  let v is with x is 1 and y is 2",
    ),
    (
        "E0012",
        "alias Texture as opaque\n\nweave main into void:\n  let t as Texture is with id is 1",
    ),
    (
        "E0013",
        "rune Point:\n  x as int\n\nweave main into void:\n  let p as Point is with x is 10\n  let z is p.z",
    ),
    ("E0014", "weave main into void:\n  let x is maybe none"),
    ("E0015", "weave main into void:\n  let e is error"),
    ("E0016", "weave main into void:\n  let key is KEY_W"),
    (
        "E0017",
        "rune Vec2:\n  x as int\n  y as int\n\nweave main into void:\n  let v as Vec2 is with x is 1 and y is 2\n  let a, b, c is v",
    ),
    (
        "E0018",
        'weave main into void:\n  var items as list of int is list of int with capacity 10\n  calling items.push with "invalid string"',
    ),
    (
        "E0019",
        'weave main into void:\n  let msg is "hello {missing_var}"',
    ),
    (
        "E0020",
        'weave compute into int:\n  let x is 10\n  "not an int"',
    ),
]


class TestErrorDiagnostics:
    @pytest.mark.parametrize("code, source", E_CODE_CASES)
    def test_error_code(self, code, source):
        exc = check_error_code(source, code)
        rendered = strip_ansi(getattr(exc, "rendered_all", None) or exc.render(source))
        assert f"error[{code}]" in rendered
        assert "= help:" in rendered
        assert "-->" in rendered
        assert "^" in rendered

    def test_multiple_errors_accumulate(self):
        source = """weave main into void:
  let a as int is 3.14
  let b as int is "hello"
  let c as int is true
"""
        exc = check_error_code(source, "E0005")
        assert len(exc.all_errors) >= 3
        assert exc.rendered_all.count("error[") >= 3
        assert exc.rendered_all.count("-->") >= 3

    def test_render_includes_source_line(self):
        exc = check_error_code("let v is 10", "E0002")
        rendered = strip_ansi(exc.render("let v is 10"))
        assert "error[E0002]" in rendered
        assert "-->" in rendered
        assert "^" in rendered
        assert "= help:" in rendered


# ---------------------------------------------------------------------------
# 21. Destructuring
# ---------------------------------------------------------------------------


class TestDestructuring:
    def test_rune_destructuring_valid(self):
        check_ok(
            VEC2
            + "weave main into float:\n"
            "  let v as Vec2 is with x is 1.0 and y is 2.0\n"
            "  let px, py is v\n"
            "  return px + py\n"
        )

    def test_array_destructuring_valid(self):
        check_ok(
            "weave main into int:\n"
            "  let arr is array of int with size 2\n"
            "  let a, b is arr\n"
            "  return a + b\n"
        )

    def test_count_mismatch_fails(self):
        expect_error(
            VEC2
            + "weave main into void:\n"
            "  let v as Vec2 is with x is 1.0 and y is 2.0\n"
            "  let px, py, pz is v\n",
            contains=["E0017", "Destructuring mismatch"],
        )


# ---------------------------------------------------------------------------
# 22. String interpolation
# ---------------------------------------------------------------------------


class TestStringInterpolation:
    def test_known_variable_passes(self):
        check_ok('weave main into void:\n  let name is "bob"\n  let s is "hi {name}"\n')

    def test_unknown_variable_fails(self):
        expect_error(
            'weave main into void:\n  let s is "hi {unknown}"\n',
            contains=["E0019", "Undefined variable 'unknown' in string interpolation"],
        )

    def test_interpolation_format_string_emission(self):
        c = gen_bundle(
            'weave main into void:\n'
            '  let name is "player1"\n'
            '  let x is 10\n'
            '  let msg is "player {name} at {x}"\n'
        )
        assert 'pengu_string_format("player %s at %d"' in c


# ---------------------------------------------------------------------------
# 23. Type inference (primitive + struct)
# ---------------------------------------------------------------------------


class TestTypeInference:
    def test_primitive_inference(self):
        check_ok(
            "weave main into void:\n"
            "  var x is 10\n"
            "  let y is 3.14\n"
            '  let s is "hi"\n'
            "  let b is true\n"
            "  set x is 20\n"
        )

    @pytest.mark.parametrize(
        "decl",
        [
            "let v as Vec2 is with x is 10 and y is 20",
            "let v is with x is 10 and y is 20",
            "let v is with x is 1 and y is 2",
        ],
    )
    def test_struct_init_inferred(self, decl):
        check_ok(VEC2 + f"weave main into void:\n  {decl}\n")


# ---------------------------------------------------------------------------
# 24. Codegen-emission shapes (no C compiler needed)
# ---------------------------------------------------------------------------


class TestCodegenEmissionStructs:
    def test_struct_union_alias_omen_emission(self):
        c = gen_bundle(
            """rune Vec2:
  x as float
  y as float

echo Value:
  as_int as int
  as_float as float

alias Score as int
alias Texture as opaque

omen NetworkState:
  Disconnected
  Connecting with retry_count as int
  Connected with session_id as string
  Failed with error_code as int and reason as string

weave struct_test into void:
  var v as Vec2 is with x is 10.0 and y is 20.0
  let vx is v.x
  set v.x is 100.0
  var val as Value is with as_int is 42
  var sc as Score is 100
  var state as NetworkState is with Connected is with session_id is "sess_123"
  var vp as ref to Vec2 is sigil of v
  set vp->x is 200.0
"""
        )
        assert "struct Vec2 {" in c
        assert "union Value {" in c
        assert "typedef int32_t Score;" in c
        assert "typedef struct Texture Texture;" in c
        assert "typedef enum NetworkState_Tag {" in c
        assert "struct NetworkState {" in c
        assert "Vec2 v = (Vec2){.x = 10.0f, .y = 20.0f}" in c
        assert "Value val = (Value){.as_int = 42};" in c
        assert "Score sc = 100;" in c
        assert ".data.Connected = {.session_id = pengu_string_from_cstr(\"sess_123\")}" in c
        assert "vp->x = 200.0f;" in c
        assert "/* stack */" in c

    def test_forward_declarations_before_definitions(self):
        c = gen_bundle(
            """rune Node:
  value as int
  next as maybe ref to Node

rune Tree:
  root as maybe ref to Node
  count as int

weave create_tree into Tree:
  var n as Node is with value is 10 and next is maybe none
  return with root is maybe none and count is 1
"""
        )
        assert "typedef struct Node Node;" in c
        assert "typedef struct Tree Tree;" in c
        assert "struct Node {" in c
        assert "struct Tree {" in c
        assert c.find("typedef struct Node Node;") < c.find("struct Node {")
        assert c.find("typedef struct Tree Tree;") < c.find("struct Tree {")


class TestCodegenEmissionEnums:
    def test_simple_enum_omen(self):
        c = gen_bundle(
            """omen Level:
  ONE
  TWO
  THREE

weave enum_test into string:
  var l1 as Level is Level_ONE
  var l2 as Level is Level.TWO
  var l3 as Level is THREE
  let res is judge l2:
    when Level_ONE -> "1"
    when Level.TWO -> "2"
    when THREE -> "3"
    else -> "other"
  return res
"""
        )
        assert "typedef enum Level Level;" in c
        assert "struct Level;" not in c
        assert "typedef enum Level {" in c
        assert "Level_ONE = 0," in c
        assert "Level_TWO = 1," in c
        assert "Level_THREE = 2," in c
        assert "} Level;" in c
        assert "struct Level {" not in c
        assert "Level l1 = Level_ONE;" in c
        assert "Level l2 = Level_TWO;" in c
        assert "Level l3 = Level_THREE;" in c
        assert 'case Level_ONE: _res = (pengu_string_from_cstr("1")); break;' in c
        assert 'case Level_TWO: _res = (pengu_string_from_cstr("2")); break;' in c
        assert 'case Level_THREE: _res = (pengu_string_from_cstr("3")); break;' in c

    def test_omen_variant_value_emission(self):
        c = gen_bundle(
            "omen Nivel:\n    One is 3\n    Two\n    Three\n\n"
            "weave enum_test into void:\n  var l as Nivel is Nivel_One\n"
        )
        assert "typedef enum Nivel {" in c
        assert "Nivel_One = 3," in c
        assert "Nivel_Two = 4," in c
        assert "Nivel_Three = 5," in c

    def test_omen_with_insignia_prefix(self):
        c = gen_bundle(
            "insignia ray_\n\nomen Key:\n    Space is 32\n    Escape is 256\n    Enter\n",
            filename="raylib.pengu",
        )
        assert "typedef enum ray_Key {" in c
        assert "ray_Key_Space = 32," in c
        assert "ray_Key_Escape = 256," in c
        assert "ray_Key_Enter = 257," in c


class TestCodegenEmissionEnchanting:
    def test_method_prototypes_and_definitions(self):
        c = gen_bundle(
            VEC2
            + """enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    return with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    return (self->x * self->x + self->y * self->y) to float

  weave move with dx as float and dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

weave main into void:
  var a as Vec2 is with x is 10.0 and y is 20.0
  var b as Vec2 is with x is 5.0 and y is 5.0
  let c as Vec2 is calling a.add with b
  calling a.move with 10.0 and 0.0
"""
        )
        assert "Vec2 Vec2_add(Vec2* self, Vec2 other);" in c
        assert "float Vec2_length(Vec2* self);" in c
        assert "void Vec2_move(Vec2* self, float dx, float dy);" in c
        assert "Vec2 Vec2_add(Vec2* restrict self, Vec2 other) {" in c
        assert "return (Vec2){.x = (self->x + other.x), .y = (self->y + other.y)};" in c
        assert "void Vec2_move(Vec2* restrict self, float dx, float dy) {" in c
        assert "const Vec2 c = Vec2_add(&a, b);" in c
        assert "Vec2_move(&a, 10.0f, 0.0f);" in c

    def test_enchanting_with_ptr_desugar(self):
        c = gen_bundle(
            """rune Player:
  x as int
  y as int
  health as int

enchanting Player:
  weave heal with amount as int into void:
    set self->health is self->health + amount

weave reset_player with p as ref to Player into void:
  with p:
    set.x is 100
    set.y is 200
    calling.heal with 50
"""
        )
        assert "p->x = 100;" in c
        assert "p->y = 200;" in c
        assert "Player_heal(p, 50);" in c

    def test_with_value_desugar(self):
        c = gen_bundle(
            """rune Player:
  x as int
  y as int

weave main into void:
  var player as Player is with x is 0 and y is 0
  with player:
    set x is 10
    set y is 20
"""
        )
        assert "player.x = 10;" in c
        assert "player.y = 20;" in c

    def test_ritual_call_site_mangling(self):
        # Ritual (static) enchanting methods emit clean prototypes/definitions
        # with no `self` parameter and no AST leak in the name.
        c = gen_bundle(
            VEC2
            + """enchanting Vec2:
  weave ritual zero into Vec2:
    return with x is 0.0 and y is 0.0

  weave ritual scale with f as float into Vec2:
    return with x is f and y is f

  weave length_sq into float:
    return self->x * self->x + self->y * self->y

weave main into int:
  var v as Vec2 is calling Vec2.zero
  var len as float is calling v.length_sq
  var w as Vec2 is calling Vec2.scale with 2.0
  return 0
"""
        )
        assert "Vec2 Vec2_zero(void);" in c
        assert "Vec2 Vec2_zero(void) {" in c
        assert "Vec2 Vec2_scale(float f);" in c
        assert "Vec2 Vec2_scale(float f) {" in c
        assert "Vec2_zero();" in c
        assert "Vec2_scale(2.0f);" in c
        assert "Vec2_length_sq(&v);" in c
        assert "Tree(" not in c
        assert "Token(" not in c


class TestCodegenEmissionArraysSlices:
    def test_collection_emission_shapes(self):
        c = gen_bundle(
            VEC2
            + """weave test_collections into void:
  let arr is array of int with size 10
  let first is arr at 0
  set arr at 0 is 99
  let part as slice of int is arr at 1 to 3
  let n is part length
  let evens is for x in arr when x % 2 == 0 then x
  let doubled is for x in arr then x * 2
  var vertices as list of Vec2 is list of Vec2 with capacity 100
  var lookup as map of int to Vec2 is map of int to Vec2
"""
        )
        assert "int32_t arr[10] = {0};" in c
        assert "arr[0] = 99;" in c
        assert "PenguSlice part = pengu_slice_new" in c
        assert "const int32_t n = part.len;" in c
        assert "PenguList evens = " in c
        assert "PenguList doubled = " in c
        assert "pengu_list_new(sizeof(Vec2), 100)" in c
        assert "pengu_map_new(sizeof(int32_t), sizeof(Vec2))" in c

    def test_array_literal_initializer(self):
        c = gen_bundle(
            "weave main into void:\n"
            "  var arr as array of int with size 5 is [1, 2, 3, 4, 5]\n"
            "  let x is arr at 2\n"
        )
        assert "int32_t arr[5] = { 1, 2, 3, 4, 5 }" in c

    def test_loop_and_index_emission(self):
        c = gen_bundle(
            """weave loops_demo into void:
  var x as int is 0
  while x < 10:
    set x is x + 1
    if x == 5:
      continue
    if x == 9:
      break

  var arr as array of int with size 5 is [1, 2, 3, 4, 5]
  for i from 0 to 5:
    set arr at i is (arr at i) * 2

  let part as slice of int is arr at 1 to 4
  for i from 0 to part.len:
    set part at i is (part at i) + 10

  for num in arr:
    let doubled is num * 2

  var lst as list of int is list of int with capacity 10
  for i from 0 to 5:
    calling lst.push with i * 10
  for i from 0 to lst.len:
    set lst at i is (lst at i) + 100
"""
        )
        assert "while ((x < 10)) {" in c
        assert "continue;" in c
        assert "break;" in c
        assert "for (int32_t i = 0; i < 5; i++) {" in c
        assert "arr[i] = (arr[i] * 2);" in c
        assert "for (int32_t i = 0; i < part.len; i++) {" in c
        assert "(((int32_t*)(part).data)[i]) = ((((int32_t*)(part).data)[i]) + 10);" in c
        assert "for (int32_t _idx_1 = 0; _idx_1 < 5; _idx_1++) {" in c
        assert "int32_t num = (arr)[_idx_1];" in c
        assert "for (int32_t i = 0; i < lst.len; i++) {" in c
        assert "(*(int32_t*)pengu_list_at(&(lst), i)) = ((*(int32_t*)pengu_list_at(&(lst), i)) + 100);" in c

    def test_judge_switch_emission(self):
        c = gen_bundle(
            """weave pattern_demo with key as int into string:
  let state as string is judge key:
    when 1 -> "Active"
    when 2 -> "Pending"
    when 3 -> "Finished"
    else -> "Unknown"
  return state
"""
        )
        assert 'case 1: _res = (pengu_string_from_cstr("Active")); break;' in c
        assert 'case 2: _res = (pengu_string_from_cstr("Pending")); break;' in c
        assert 'case 3: _res = (pengu_string_from_cstr("Finished")); break;' in c
        assert 'default: _res = (pengu_string_from_cstr("Unknown")); break;' in c

    def test_destructuring_emission(self):
        c = gen_bundle(
            VEC2
            + """weave test_destructure into void:
  var v as Vec2 is with x is 10.5 and y is 20.5
  let vx, vy is v
"""
        )
        assert "const float vx = _destruct_1.x;" in c
        assert "const float vy = _destruct_1.y;" in c

    def test_defer_runs_before_return(self):
        c = gen_bundle(
            """weave bar into void:
  return

weave foo into int:
  defer calling bar
  return 1
"""
        )
        assert "bar();" in c
        assert re.search(r"bar\(\);\s*return\b", c) is not None

    def test_no_auto_keyword_in_output(self):
        c = gen_bundle(
            VEC2
            + """weave main into void:
  var v as Vec2 is with x is 10 and y is 20
  let a, b is v
  var items as list of int is list of int with capacity 4
  for item in items:
    calling print with item
"""
        )
        assert re.search(r"\bauto\b", c) is None

    def test_main_renamed_to_pengu_main_with_wrapper(self):
        c = gen_bundle("weave main into void:\n  var x as int is 1\n")
        assert "void pengu_main(void)" in c
        assert "int main(int argc, char** argv) {" in c

    def test_mutual_recursion_prototypes(self):
        c = gen_bundle(
            """weave is_even with n as int into bool:
  if n == 0:
    return true
  return calling is_odd with n - 1

weave is_odd with n as int into bool:
  if n == 0:
    return false
  return calling is_even with n - 1

weave main into void:
  var res as bool is calling is_even with 4
"""
        )
        assert "bool is_even(int32_t n)" in c
        assert "bool is_odd(int32_t n)" in c


class TestCodegenEmissionGenerics:
    def test_rune_monomorphization(self):
        c = gen_bundle(
            """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair of int and float is with first is 42 and second is 3.14
  let f as int is p.first
  let s as float is p.second
"""
        )
        assert "struct Pair_int_float {" in c
        assert "int32_t first;" in c
        assert "float second;" in c

    def test_function_monomorphization_names(self):
        c = gen_bundle(
            """weave identity shard T with x as T into T:
  return x

weave main into void:
  let a as int is calling identity with 100
  let b as string is calling identity with "pengu"
"""
        )
        assert "identity_int" in c
        assert "identity_string(pengu_string_from_cstr(\"pengu\"))" in c
        assert "identity_int(100)" in c

    def test_generic_swap_names(self):
        c = gen_bundle(
            """rune Pair shard T and U:
  first as T
  second as U

weave swap shard T and U with a as T, b as U into Pair of U and T:
  return with first is b and second is a

weave main into void:
  let p as Pair of float and int is calling swap with 10 and 2.5
"""
        )
        assert "struct Pair_float_int {" in c
        assert "swap_int_float(10, 2.5f)" in c

    def test_generic_enchanting_method_name(self):
        c = gen_bundle(
            """rune Box shard T:
  value as T

enchanting Box of T:
  weave get into T:
    return self->value

weave main into void:
  let b as Box of int is with value is 99
  let v as int is calling b.get
"""
        )
        assert "struct Box_int {" in c
        assert "Box_int_get" in c

    def test_nested_generic_types(self):
        c = gen_bundle(
            """rune Container shard T:
  item as T

rune Pair shard A and B:
  first as A
  second as B

weave main into void:
  let c as Container of int is with item is 7
  let p as Pair of (Container of int) and string is with first is c and second is "box"
"""
        )
        assert "struct Container_int {" in c
        assert "struct Pair_Container_int_string {" in c

    def test_generic_alias_typedefs(self):
        c = gen_bundle(
            """rune Pair shard T and U:
  first as T
  second as U

alias IntPair as Pair of int and int
alias GenericPair shard V as Pair of V and string

weave main into void:
  let ip as IntPair is with first is 1 and second is 2
  let gp as GenericPair of float is with first is 1.5 and second is "hello"
"""
        )
        assert "typedef Pair_int_int IntPair;" in c
        assert "typedef Pair_float_string GenericPair_float;" in c

    def test_generic_omen_type_emission(self):
        c = gen_bundle(
            """omen Status shard T:
  Success with data as T
  Failure with code as int

weave main into void:
  let s as Status of string is with code is 404
  let ok as Status of string is with Success is with data is "hi"
"""
        )
        assert "struct Status_string {" in c
        assert "typedef enum Status_string_Tag {" in c
        # Specialized generic omens use the mangled name for the variable and
        # a single `data` union member matching the generated layout.
        assert "Status_string s = (Status_string){ .tag = Status_string_Failure, .data.Failure = {.code = 404} };" in c
        assert ".data.Success = {.data = pengu_string_from_cstr(\"hi\")}" in c
        assert "} data;" in c
        assert "} as;" not in c
        assert "Status_string_Status" not in c

    def test_generic_omen_bare_field_construction_resolves_variant(self):
        # `with code is 404` must resolve field `code` to its owning variant
        # (`Failure`) instead of emitting a bogus tag / dropping the payload.
        c = gen_bundle(
            """omen Status shard T:
  Success with data as T
  Failure with code as int
  Pending with reason as string

weave main into void:
  let s as Status of string is with code is 404
  let p as Status of string is with reason is "later"
"""
        )
        assert ".tag = Status_string_Failure, .data.Failure = {.code = 404}" in c
        assert ".tag = Status_string_Pending, .data.Pending = {.reason = pengu_string_from_cstr(\"later\")}" in c
        assert "Status_string_code" not in c

    def test_generic_omen_payload_conflicts_rejected(self):
        # Payload fields drawn from two different variants cannot form one value.
        from pengu_parser.pengu_errors import SemanticError
        from tests.conftest import gen_bundle

        with pytest.raises(SemanticError) as exc:
            gen_bundle(
                """omen Status shard T:
  Success with data as T
  Failure with code as int

weave main into void:
  let s as Status of string is with code is 404 and data is "x"
"""
            )
        assert "different variants" in str(exc.value)

    def test_explicit_type_args_monomorphization(self):
        c = gen_bundle(
            """rune Box shard T:
  item as T
  id as int

weave create_box shard T with val as T and id as int into Box of T:
  return with item is val and id is id

weave main into void:
  var int_box as Box of int is calling create_box of int with 42 and 1
  var str_box as Box of string is calling create_box of string with "Pengu" and 2
"""
        )
        assert "struct Box_int {" in c
        assert "struct Box_string {" in c
        assert "Box_int create_box_int(int32_t val, int32_t id)" in c
        assert "Box_string create_box_string(PenguString val, int32_t id)" in c
        assert "create_box_int(42, 1)" in c
        assert 'create_box_string(pengu_string_from_cstr("Pengu"), 2)' in c

    def test_duplicate_generic_instances_deduplicated(self):
        mod1 = """rune Pair shard T and U:
  first as T
  second as U

weave identity shard T with x as T into T:
  return x

weave use_mod1 into void:
  let p as Pair of int and float is with first is 1 and second is 2.0
  let y is calling identity with 10
"""
        mod2 = """weave use_mod2 into void:
  let p as Pair of int and float is with first is 10 and second is 20.0
  let z is calling identity with 99
"""
        parser = PenguParser()
        checker = PenguChecker(base_dir=".")
        t1 = parser.parse(mod1)
        checker.check(t1, filename="mod1.pengu", source=mod1)
        t2 = parser.parse(mod2)
        checker.check(t2, filename="mod2.pengu", source=mod2, reset_symbols=False)
        cg = PenguCodegen(
            checker.symbols, ["mod1.pengu", "mod2.pengu"], ".",
            compile_env=checker.compile_env,
        )
        cg.collect_declarations([("mod1.pengu", t1), ("mod2.pengu", t2)])
        c = cg.generate_bundle()
        assert c.count("struct Pair_int_float {") == 1
        assert c.count("int32_t identity_int(int32_t x) {") == 1

    def test_generic_default_param_folded_call(self):
        c = gen_bundle(
            """weave compute shard T with x as T, factor as int is 2 into int:
  return factor

weave main into void:
  let res is calling compute with "text"
"""
        )
        assert "compute_string" in c
        assert "compute_string(pengu_string_from_cstr(\"text\"), 2)" in c


class TestCodegenEmissionConcepts:
    def test_bind_methods_and_call_names(self):
        c = gen_bundle(
            """concept Drawable:
  weave draw into void
  weave ritual default_name into string

rune Circle:
  radius as float

bind Circle with Drawable:
  weave draw into void:
    set self->radius is self->radius + 1.0

  weave ritual default_name into string:
    return "Circle"

weave main into int:
  var c as Circle is with radius is 5.0
  calling c.draw
  var name as string is calling Circle.default_name
  return 0
"""
        )
        assert "Circle_draw(&c);" in c
        assert "Circle_default_name();" in c

    def test_generic_where_monomorph(self):
        c = gen_bundle(
            """concept Printable:
  weave print_me into void

rune Document:
  title as string

bind Document with Printable:
  weave print_me into void:
    return

weave output shard T where T: Printable with item as T into void:
  calling item.print_me

weave main into int:
  var doc as Document is with title is "Hello"
  calling output with doc
  return 0
"""
        )
        assert "Document_print_me" in c
        assert "output_Document" in c

    def test_seal_typedef_emission(self):
        c = gen_bundle(
            """seal UserId as int
seal PostId as int

weave process_user with u as UserId into int:
  return u to int

weave main into int:
  var u as UserId is 42 to UserId
  var p as PostId is 100 to PostId
  return calling process_user with u
"""
        )
        assert "typedef int32_t UserId;" in c
        assert "typedef int32_t PostId;" in c
        assert "process_user" in c


class TestCodegenEmissionNull:
    def test_null_initializers(self):
        c = gen_bundle(
            """rune Node:
    val as int
    next as ref to Node

weave test into void:
    var ptr as ref to int is null
    let obj as ref to Node is null
    var handle as opaque is null
    set ptr is null
    var n as Node is with val is 42 and next is null
"""
        )
        assert "int32_t* ptr = NULL;" in c
        assert "Node* obj = NULL;" in c
        assert "void* handle = NULL;" in c
        assert "ptr = NULL;" in c
        assert ".next = NULL" in c

    def test_null_comparison_emission(self):
        c = gen_bundle(
            """weave check_ptr with ptr as ref to int into bool:
    if ptr == null:
        return true
    if null != ptr:
        return false
    if null == null:
        return true
    return false
"""
        )
        assert "ptr == NULL" in c
        assert "NULL != ptr" in c

    def test_null_return_and_argument_emission(self):
        c = gen_bundle(
            """weave get_null into ref to int:
    return null

weave process_ptr with ptr as ref to int into void:
    var a as int is 0

weave test into void:
    var p as ref to int is calling get_null
    calling process_ptr with null
"""
        )
        assert "return NULL;" in c
        assert "process_ptr(NULL);" in c


class TestCodegenEmissionRefChar:
    def test_c_string_literal_emission(self):
        c = gen_bundle(
            """declare puts with s as ref to char into int

rune CMessage:
    text as ref to char
    id as int

weave main into int:
    let msg as ref to char is "Hello C World"
    let s2 as string is "Hello Pengu World"
    let item as CMessage is with text is "Greetings" and id is 42
    calling puts with "Direct C String"
    return 0
"""
        )
        assert 'char* msg = "Hello C World";' in c
        assert 'pengu_string_from_cstr("Hello Pengu World")' in c
        assert 'pengu_string_from_cstr("Hello C World")' not in c
        assert '.text = "Greetings"' in c
        assert 'pengu_string_from_cstr("Greetings")' not in c
        assert 'puts("Direct C String")' in c
        assert 'pengu_string_from_cstr("Direct C String")' not in c

    def test_interpolated_string_to_ref_char_rejected(self):
        expect_error(
            'weave main into int:\n'
            '    let name as string is "Pengu"\n'
            '    let c_str as ref to char is "Hello {name}"\n'
            '    return 0\n',
            contains="interpolation",
        )


class TestCodegenEmissionVariadic:
    def test_variadic_parameter_slice(self):
        c = gen_bundle(
            """weave process_nums with nums as many int into int:
    var total as int is 0
    for n in nums:
        set total is total + n
    return total

weave main into void:
    let res1 is calling process_nums with 1 and 2 and 3
    let res2 is calling process_nums
"""
        )
        assert "PenguSlice nums" in c
        assert "_tmp_arr" in c
        assert "process_nums(" in c

    def test_variadic_enchanting_method(self):
        c = gen_bundle(
            """rune Calculator:
    base as int

enchanting Calculator:
    weave add_many with extra as many int into int:
        var total as int is self->base
        for val in extra:
            set total is total + val
        return total

weave main into void:
    var calc is with base is 100
    let total is calling calc.add_many with 1 and 2 and 3
"""
        )
        assert "Calculator_add_many" in c
        assert "PenguSlice extra" in c


class TestCodegenEmissionMainEntry:
    def test_entry_point_wrapper(self):
        c = gen_bundle("weave main into int:\n    return 0\n")
        assert "int32_t pengu_main(void)" in c
        assert "int main(int argc, char** argv) {" in c
        assert "pengu_main();" in c
