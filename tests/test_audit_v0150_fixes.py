"""Regression tests for PenguScript 0.15.0 compiler audit fixes (C1-C9, I1-I10, etc.)."""

import pytest
from pathlib import Path
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_types import BaseType
from tests.conftest import (
    check_ok,
    check_error,
    compile_run,
    check_c_syntax,
    gen_bundle,
    requires_runtime,
)


# ─── C1: _int_interp_spec duplicate decorator ─────────────────────────
class TestC1_IntInterpSpecDecorator:
    def test_staticmethod_is_callable(self):
        """_int_interp_spec is a callable static method without duplicate decorator."""
        assert callable(PenguCodegen._int_interp_spec)
        spec, cast = PenguCodegen._int_interp_spec(BaseType("i64"))
        assert spec == "%lld"
        assert cast == "long long"

        spec_u, cast_u = PenguCodegen._int_interp_spec(BaseType("u64"))
        assert spec_u == "%llu"
        assert cast_u == "unsigned long long"


# ─── C2: field_access over maybe field emits payload cast ─────────────
class TestC2_FieldAccessMaybeCast:
    @requires_runtime
    def test_nested_rune_maybe_field_value_cast(self):
        """field_access on composite rune.maybe.value properly emits cast."""
        code = """
import std.spark

rune Inner:
    m as maybe int

rune Outer:
    inner as Inner

weave main into int:
    var inn as Inner with:
        set .m is some 123
    var o as Outer with:
        set .inner is inn
    if o.inner.m is present:
        var v as int is o.inner.m.value
        calling spark.println with "{v}"
    return 0
"""
        res = compile_run(code, tag="test_c2_nested")
        assert res.stdout.strip() == "123"


# ─── C3: list.push/contains/index_of evaluates argument only once ─────
class TestC3_ListArgSingleEvaluation:
    @requires_runtime
    def test_push_side_effects_once(self):
        """Calling push with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_push")
        assert res.stdout.count("GEN CALLED") == 1

    @requires_runtime
    def test_contains_side_effects_once(self):
        """Calling contains with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with "item"
    let has is calling xs.contains with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_contains")
        assert res.stdout.count("GEN CALLED") == 1


# ─── C4: Algebraic omens without derive Nexus emit cleanup helpers ────
class TestC4_AlgebraicOmenNexus:
    @requires_runtime
    def test_algebraic_omen_list_cleanup_and_clone(self):
        """Algebraic omens with heap payloads automatically emit cleanup/clone for lists."""
        code = """
import std.spark

omen Event:
    Msg with text as string

weave main into int:
    var l as list of Event is list of Event
    let ev as Event is with text is "hello"
    calling l.push with ev
    calling spark.println with "OK"
    return 0
"""
        res = compile_run(code, tag="test_c4_run")
        assert res.stdout.strip() == "OK"


# ─── C5: String-valued omen variants are typed as frozen string ───────
class TestC5_StringOmenFrozen:
    def test_banish_string_omen_variant_rejected(self):
        """String-valued omen variants cannot be banished directly or via variable."""
        from pengu_parser.pengu_errors import InvalidMemoryOpError, TypeMismatchError
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code_banish_direct = """
omen Color with string:
    Red

weave main into void:
    banish Color.Red
"""
        p = PenguParser()
        checker = PenguChecker()
        with pytest.raises(InvalidMemoryOpError):
            checker.check(p.parse(code_banish_direct))

        code_banish_var = """
omen Color with string:
    Red

weave main into void:
    var c is Color.Red
    banish c
"""
        with pytest.raises(InvalidMemoryOpError):
            checker.check(p.parse(code_banish_var))

        code_assign_mutable = """
omen Color with string:
    Red

weave main into void:
    var s as string is Color.Red
"""
        with pytest.raises(TypeMismatchError):
            checker.check(p.parse(code_assign_mutable))

        code_valid_frozen = """
omen Color with string:
    Red

weave main into void:
    var s as frozen string is Color.Red
    var inf is Color.Red
"""
        assert checker.check(p.parse(code_valid_frozen)) == []


# ─── C6: Array passed to slice parameter wraps in PenguSlice ──────────
class TestC6_ArrayToSliceParam:
    @requires_runtime
    def test_array_variable_passed_to_slice_param(self):
        """Passing an array variable to a slice of T parameter compiles and runs."""
        code = """
weave sum with s as slice of int into int:
    let a, b, c is s
    return a + b + c

weave main into int:
    var arr as array of int with size 3 is [10, 20, 30]
    let total is calling sum with arr
    if total == 60:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_c6_var")
        assert res.returncode == 0

    @requires_runtime
    def test_array_literal_passed_to_slice_param(self):
        """Passing an array literal to a slice of T parameter compiles and runs."""
        code = """
weave sum with s as slice of int into int:
    let a, b, c is s
    return a + b + c

weave main into int:
    let total is calling sum with [5, 15, 25]
    if total == 45:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_c6_lit")
        assert res.returncode == 0


# ─── C7: for from to loops use int64_t for counter ────────────────────
class TestC7_ForRangeInt64:
    @requires_runtime
    def test_for_range_with_64bit_bounds(self):
        """for from to loop counter uses int64_t and does not overflow on 64-bit bounds."""
        code = """
weave main into int:
    var count as i64 is 0
    for i from 0 to 5000000000 step 1000000000:
        set count is count + 1
    if count == 5:
        return 0
    return 1
"""
        c = gen_bundle(code)
        assert "for (int64_t i = 0;" in c
        check_c_syntax(c)
        res = compile_run(code, tag="test_c7_run")
        assert res.returncode == 0


# ─── C8: Reject redeclaration in the same scope ───────────────────────
class TestC8_RedeclarationError:
    def test_redefinition_in_same_scope_rejected(self):
        """Redefining a variable or let in the same scope produces E0035."""
        from pengu_parser.pengu_errors import SemanticError
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        p = PenguParser()
        checker = PenguChecker()

        code_var = """
weave main into void:
    var x is 1
    var x is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_var))
        assert exc_info.value.code == "E0035"

        code_let = """
weave main into void:
    let y is 1
    let y is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_let))
        assert exc_info.value.code == "E0035"

        code_var_let = """
weave main into void:
    var z is 1
    let z is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_var_let))
        assert exc_info.value.code == "E0035"

        code_destruct_dup = """
weave main into void:
    let a, a is [1, 2]
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_destruct_dup))
        assert exc_info.value.code == "E0035"

    def test_nested_scope_shadowing_allowed(self):
        """Shadowing in a distinct inner block scope is permitted."""
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code = """
weave main into void:
    var x is 1
    if true:
        var x is 2
"""
        p = PenguParser()
        checker = PenguChecker()
        assert checker.check(p.parse(code)) == []

    def test_discard_identifier_multiple_allowed(self):
        """The discard identifier '_' can appear multiple times."""
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code = """
weave main into void:
    var _ is 1
    var _ is 2
    let _ is 3
"""
        p = PenguParser()
        checker = PenguChecker()
        assert checker.check(p.parse(code)) == []


# ─── C9: Support binary literals, underscores, and escapes ────────────
class TestC9_LexerLiterals:
    @requires_runtime
    def test_binary_literals_and_visual_separators(self):
        """Binary literals and visual underscores in ints/floats parse and execute."""
        code = """
weave main into int:
    var mask is 0b1010
    var million is 1_000_000
    var hex_val is 0xFF_FF
    var bin_sep is 0b1111_0000
    var flt is 1_000.5
    var ch_hex is '\\x41'
    var ch_oct is '\\101'

    if mask != 10:
        return 1
    if million != 1000000:
        return 2
    if hex_val != 65535:
        return 3
    if bin_sep != 240:
        return 4
    if flt < 1000.4 or flt > 1000.6:
        return 5
    if ch_hex != 'A':
        return 6
    if ch_oct != 'A':
        return 7
    return 0
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_c9_literals")
        assert res.returncode == 0


# ─── I2: English error message for unregistered lambda ────────────────
class TestI2_EnglishErrorMessage:
    def test_unregistered_lambda_error_in_english(self):
        """Unregistered lambda raises English error message."""
        from pengu_parser.pengu_errors import SemanticError
        from lark import Tree
        cg = PenguCodegen(None, ["test.pengu"], ".")
        node = Tree("lambda_expr", [])
        with pytest.raises(SemanticError) as exc_info:
            cg._translate_expr(node)
        assert "lambda not registered; run pre-scan before codegen" in str(exc_info.value)


# ─── I6: string_lit recognized and dead code removed ──────────────────
class TestI6_DeadCodeInterpolatedString:
    def test_is_string_expr_handles_string_lit(self):
        """_is_string_expr accurately detects string_lit and tokens."""
        from lark import Tree, Token
        cg = PenguCodegen(None, ["test.pengu"], ".")
        node = Tree("string_lit", [Token("STRING", '"hello"')])
        assert cg._is_string_expr(node) is True
        token = Token("STRING", '"world"')
        assert cg._is_string_expr(token) is True


# ─── I7: Struct init escape analysis cleans dead type rules ───────────
class TestI7_DeadCodeStructInitRules:
    def test_struct_init_type_extracts_correct_type(self):
        """Escape analysis correctly finds struct type on custom_type annotation."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker

        code = """
rune Point:
    x as int
    y as int

weave main into void:
    var p as Point is with x is 1, y is 2
"""
        p = PenguParser()
        checker = PenguChecker()
        assert checker.check(p.parse(code)) == []


# ─── I3: unless statement emits W0004 for constant conditions ─────────
class TestI3_UnlessUnreachableCodeWarning:
    def test_unless_constant_condition_warnings(self):
        """unless emits W0004 for unreachable then and else branches."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker

        p = PenguParser()
        code_true = """
weave main into void:
    unless true:
        calling print with "unreachable"
"""
        c1 = PenguChecker()
        c1.check(p.parse(code_true))
        assert "[W0004] Unreachable code in then branch" in c1.warnings

        code_false = """
weave main into void:
    unless false:
        calling print with "reachable"
    else:
        calling print with "unreachable else"
"""
        c2 = PenguChecker()
        c2.check(p.parse(code_false))
        assert "[W0004] Unreachable code in else branch" in c2.warnings


# ─── I4: Clarified generic parameter default error message ────────────
class TestI4_GenericDefaultMessage:
    def test_generic_default_error_message(self):
        """Generic parameter default error clearly identifies generic type."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_errors import SemanticError

        code = """
weave bad_fn shard T with x as T is 0 into T:
    return x

weave main into void:
    return
"""
        p = PenguParser()
        checker = PenguChecker()
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code))
        msg = str(exc_info.value)
        assert "Generic parameter 'x' of generic type 'T' cannot have a default value" in msg


# ─── I8: Realistic 64-bit estimate_size for collections and maybe ─────
class TestI8_EstimateSizeRealistic:
    def test_estimate_size_values(self):
        """estimate_size matches 64-bit C layout for list, map, slice, maybe."""
        from pengu_parser.pengu_types import (
            ListType, MapType, SliceType, MaybeType, INT_TYPE, STRING_TYPE,
            estimate_size
        )
        assert estimate_size(SliceType(INT_TYPE)) == 24
        assert estimate_size(ListType(INT_TYPE)) == 40
        assert estimate_size(MapType(STRING_TYPE, INT_TYPE)) == 64
        assert estimate_size(MaybeType(INT_TYPE)) == 16


# ─── I10: Dynamic step zero terminates without infinite loop ──────────
class TestI10_DynamicStepZero:
    @requires_runtime
    def test_dynamic_step_zero_terminates(self):
        """Dynamic step of zero evaluates condition to false and does not loop infinitely."""
        code = """
weave main into int:
    var s as int is 0
    var count as int is 0
    for i from 0 to 10 step s:
        set count is count + 1
    if count == 0:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_i10_run")
        assert res.returncode == 0


# ─── I1: Dynamic indentation in for_comp, result, maybe constructors ──
class TestI1_ComprehensionIndentation:
    def test_for_comp_dynamic_indentation(self):
        """List comprehension internal statements follow scope indentation."""
        code = """
weave foo into list of int:
    var xs as list of int is for x in [1, 2, 3] then x * 2
    return xs
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        # Inside foo (2 spaces), comprehension temporary list declaration should be indented with 4 spaces
        assert "    PenguList _comp_list" in c


# ─── M1: Clearer error message in _check_with_builder ─────────────────
class TestM1_WithBuilderErrorMessage:
    def test_with_builder_rejects_invalid_stmt_cleanly(self):
        """Invalid statement inside 'with:' block formats inner node cleanly."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_errors import InvalidBuilderStatementError

        code = """
rune Point:
    x as int
    y as int

weave main into void:
    var p as Point with:
        var bad as int is 10
"""
        p = PenguParser()
        checker = PenguChecker()
        with pytest.raises(InvalidBuilderStatementError) as exc_info:
            checker.check(p.parse(code))
        msg = str(exc_info.value)
        assert "'with:' block only allows 'set .field is ...' assignments" in msg
        assert "not 'var_decl'" in msg


# ─── M2: var_ref and or_block expression translation ──────────────────
class TestM2_VarRefOrBlockFlow:
    @requires_runtime
    def test_var_ref_inside_and_after_or_block(self):
        """Variable references inside and around 'or:' blocks resolve correctly."""
        code = """
weave fallback into int:
    return 99

weave test_or with m as maybe int into int:
    var res as int is m or:
        var fb as int is calling fallback
        return fb
    return res

weave main into int:
    var m as maybe int is some 42
    var v as int is calling test_or with m
    if v == 42:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_m2_run")
        assert res.returncode == 0


# ─── M3: Inline prefix distinction (explicit vs auto_inline) ──────────
class TestM3_InlinePrefixDistinction:
    def test_inline_prefix_behavior(self):
        """_inline_prefix returns always_inline only for explicit inlining."""
        assert PenguCodegen._inline_prefix({"is_inline": False}) == ""
        assert PenguCodegen._inline_prefix({"is_inline": True, "auto_inline": True}) == "static inline "
        assert PenguCodegen._inline_prefix({"is_inline": True, "auto_inline": False}) == "static inline __attribute__((always_inline)) "

    def test_explicit_inline_weave_emission(self):
        """Explicit inline weave emits always_inline attribute."""
        code = """
inline weave add with a as int, b as int into int:
    return a + b

weave main into int:
    var r as int is calling add with 2, 3
    if r == 5:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        assert "__attribute__((always_inline))" in c
        res = compile_run(code, tag="test_m3_inline")
        assert res.returncode == 0


# ─── M4: type_owns_heap consolidation ─────────────────────────────────
class TestM4_TypeOwnsHeapConsolidation:
    def test_type_owns_heap_symbols_resolution(self):
        """type_owns_heap resolves rune fields through symbols when passed."""
        from pengu_parser.pengu_types import (
            type_owns_heap, RuneType, STRING_TYPE, INT_TYPE
        )
        from pengu_parser.pengu_symbols import SymbolTable

        # A rune with no fields on the type object itself
        r = RuneType("Container", fields={})
        assert not type_owns_heap(r)

        # When symbols has Container with a string field, type_owns_heap detects it
        syms = SymbolTable()
        syms.runes["Container"] = RuneType("Container", fields={"name": STRING_TYPE})
        assert type_owns_heap(r, symbols=syms)

        # With only integer field, does not own heap
        syms_int = SymbolTable()
        syms_int.runes["Container"] = RuneType("Container", fields={"count": INT_TYPE})
        assert not type_owns_heap(r, symbols=syms_int)


# ─── M5: Omen file paths tracking for implicit lifetimes ──────────────
class TestM5_OmenFilePathTracking:
    def test_omen_filepath_recorded(self):
        """Omens record their definition file path in _rune_file_paths."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_codegen import PenguCodegen

        code = """
omen Status:
    Ok
    Err with msg as string
"""
        p = PenguParser()
        ast = p.parse(code)
        codegen = PenguCodegen()
        codegen.collect_declarations([("/app/status.pengu", ast)])
        assert codegen._rune_file_paths.get("Status") == "/app/status.pengu"
        assert codegen._implicit_lifetime_allowed(codegen._rune_file_paths.get("Status", "")) is True


# ─── M6: Builtin list/map method defensive guards for empty arguments ─
class TestM6_BuiltinMethodsDefensiveGuards:
    @requires_runtime
    def test_calling_list_methods_normal_behavior(self):
        """List built-in methods push, pop, len, contains, index_of work properly."""
        code = """
weave main into int:
    var xs as list of int is list of int
    calling xs.push with 42
    if calling xs.contains with 42:
        if (calling xs.index_of with 42) == 0:
            var popped as int is calling xs.pop
            if popped == 42:
                return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_m6_list")
        assert res.returncode == 0


# ─── M7: Shadowing global function warning W0005 ──────────────────────
class TestM7_ShadowingGlobalFunctionWarning:
    def test_var_shadowing_global_weave_emits_warning(self):
        """Declaring a local var/let that shadows a global function emits W0005 warning."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker

        code = """
weave helper into int:
    return 100

weave main into int:
    var helper as int is 42
    return helper
"""
        p = PenguParser()
        checker = PenguChecker()
        checker.check(p.parse(code))
        assert any("[W0005] Variable 'helper' shadows global function 'helper'" in w for w in checker.warnings)


# ─── M8: Named argument reordering with defaults ──────────────────────
class TestM8_NamedArgReordering:
    @requires_runtime
    def test_named_args_reordered_with_defaults(self):
        """Named arguments reordered properly even when some have defaults."""
        code = """
weave format_coords with x as int, y as int is 10, z as int is 20 into int:
    return x * 100 + y * 10 + z

weave main into int:
    var r1 as int is calling format_coords with z is 5, x is 1
    if r1 == 205:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_m8_named_args")
        assert res.returncode == 0


# ─── M9: _rune_derives_explicitly documentation and behavior ──────────
class TestM9_RuneDerivesExplicitlyDocs:
    def test_rune_derives_explicitly_recognition(self):
        """_rune_derives_explicitly identifies explicit derive and bindings."""
        from pengu_parser.pengu_codegen import PenguCodegen
        from pengu_parser.pengu_types import RuneType
        from pengu_parser.pengu_symbols import SymbolTable

        codegen = PenguCodegen()
        codegen.symbols = SymbolTable()

        # Rune with explicit derive Nexus
        r1 = RuneType("ExplicitRune", derived_concepts=["Nexus"])
        assert codegen._rune_derives_explicitly(r1, "Nexus") is True
        assert codegen._rune_derives_explicitly(r1, "Imago") is False

        # Rune without explicit derive
        r2 = RuneType("PlainRune", derived_concepts=[])
        assert codegen._rune_derives_explicitly(r2, "Nexus") is False


# ─── m1: _translate_string_lit signature cleanup ──────────────────────
class Test_m1_TranslateStringLitSignature:
    def test_signature_no_context_hint(self):
        """_translate_string_lit has clean signature without dead context_hint parameter."""
        import inspect
        from pengu_parser.pengu_codegen import PenguCodegen
        sig = inspect.signature(PenguCodegen._translate_string_lit)
        assert "context_hint" not in sig.parameters


# ─── m2: _check_var_decl allows non-lvalue expressions ────────────────
class Test_m2_VarDeclInitializerLvalueAudit:
    def test_var_decl_allows_rvalue_expressions(self):
        """Variable declarations cleanly allow literals, arithmetic, and temporary expressions."""
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker

        code = """
weave main into void:
    var a as int is 1 + 2
    var b as int is 100 * 3
    var c as string is "hello world"
    return
"""
        p = PenguParser()
        checker = PenguChecker()
        checker.check(p.parse(code))
        assert len(checker.errors) == 0


# ─── m3: AliasType.can_cast_to consistency with is_compatible ─────────
class Test_m3_AliasTypeCanCastTo:
    def test_alias_can_cast_to_frozen_and_alias(self):
        """AliasType.can_cast_to properly delegates to FrozenType and matching Alias."""
        from pengu_parser.pengu_types import AliasType, FrozenType, INT_TYPE

        a1 = AliasType("MyInt", INT_TYPE)
        a2 = AliasType("MyInt", INT_TYPE)
        frozen_int = FrozenType(INT_TYPE)

        assert a1.can_cast_to(frozen_int) is True
        assert a1.can_cast_to(a2) is True
        assert a1.is_compatible(frozen_int) is True
        assert a1.is_compatible(a2) is True


# ─── m4: Grammar comment ignore rules documentation and parsing ───────
class Test_m4_GrammarCommentHandling:
    def test_block_and_line_comments_handled(self):
        """Block comments (##...##) and line comments (#...) are properly ignored."""
        from pengu_parser.pengu_parser import PenguParser

        code = """
##
Block comment
spanning multiple lines
##
weave main into int:
    # Single-line comment inside function
    return 0  ## inline doc comment ##
"""
        p = PenguParser()
        ast = p.parse(code)
        assert ast is not None
        assert ast.data == "start"

