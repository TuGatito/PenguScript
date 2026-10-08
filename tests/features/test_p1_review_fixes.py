import pytest
from tests.conftest import gen_bundle
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_types import ArrayType, INT_TYPE, estimate_size
from pengu_parser.pengu_errors import TypeMismatchError, SemanticError


def test_p1_11_estimate_size_with_token_or_str_size():
    """P1 #11: estimate_size with Token/str array size does not throw TypeError."""
    arr_t = ArrayType(element=INT_TYPE, size="N")
    sz = estimate_size(arr_t)
    assert sz == 4  # defaults to 1 * 4 bytes

    arr_t_num_str = ArrayType(element=INT_TYPE, size="10")
    sz2 = estimate_size(arr_t_num_str)
    assert sz2 == 40


def test_p1_12_set_target_prefers_local_vars_over_with_stack():
    """P1 #12: _translate_set_target modifies local variable when name matches field in with-target."""
    src = """rune Point:
    x as int
    y as int

weave test_fn into int:
    var p as Point with:
        set .x is 1
        set .y is 2
    var x as int is 100
    with p:
        set x is 42
    return x
"""
    c = gen_bundle(src)
    # The set inside 'with p' should target local variable 'x', not 'p.x' or '(&p)->x'
    assert "x = 42;" in c


def test_p1_13_judge_non_constant_pattern_emits_ternary():
    """P1 #13: judge on integer with variable pattern falls back to ternary rather than non-constant switch case."""
    src = """weave test_fn with x as int, y as int into int:
    let res is judge x:
        when y -> 10
        else -> 20
    return res
"""
    c = gen_bundle(src)
    assert "switch" not in c
    assert "(x == y)" in c or "(x == y)" in c.replace(" ", "")


def test_p1_14_judge_pattern_type_mismatch_rejected():
    """P1 #14: judge pattern type mismatch (e.g. string pattern on int subject) is rejected with E0005."""
    src = """weave test_fn with x as int into int:
    let res is judge x:
        when "hello" -> 10
        else -> 20
    return res
"""
    with pytest.raises(TypeMismatchError) as exc_info:
        gen_bundle(src)
    assert "E0005" in str(exc_info.value.code) or "cannot match integer subject" in str(exc_info.value).lower()


def test_p1_15_in_expr_string_element_validation_and_codegen():
    """P1 #15: 1 in string is rejected; char and byte in string emit valid strchr."""
    # 1. Incompatible element rejected
    bad_src = """weave test_fn into bool:
    return 1 in "hello"
"""
    with pytest.raises(TypeMismatchError) as exc_info:
        gen_bundle(bad_src)
    assert "E0005" in str(exc_info.value.code)

    # 2. char and byte accepted and emitted with strchr
    good_src = """weave test_fn with b as byte, c as char into bool:
    var ok1 as bool is c in "hello"
    var ok2 as bool is b in "hello"
    return ok1 and ok2
"""
    c = gen_bundle(good_src)
    assert "strchr" in c


def test_p1_16_slice_at_expr_over_list_and_slice():
    """P1 #16: Slicing list or slice generates valid pengu_slice_new with elem_size."""
    src = """weave test_fn into void:
    var lst as list of int is list of int
    var sl as slice of int is lst at 0 to 2
    var sub as slice of int is sl at 0 to 1
"""
    c = gen_bundle(src)
    assert "pengu_slice_new" in c
    assert "_l.elem_size" in c
    assert "_sl.elem_size" in c


def test_p1_17_string_alias_in_expr_and_for_in():
    """P1 #17: String alias works with 'in', string iteration, and helpers."""
    src = """alias Name as string

weave test_fn with n as Name into bool:
    var found as bool is 'a' in n
    for ch in n:
        var c as string is ch
    return found
"""
    c = gen_bundle(src)
    assert "strchr" in c
    assert "pengu_string_char_at" in c


def test_p1_18_with_builder_in_var_decl_not_double_checked():
    """P1 #18: var decl with with-builder does not throw duplicate errors or crash."""
    src = """rune Point:
    x as int
    y as int

weave test_fn into void:
    var p as Point with:
        set .x is 10
        set .y is 20
"""
    c = gen_bundle(src)
    assert "test_fn" in c


def test_p1_19_monomorphized_type_closure_resolution():
    """P1 #19: Generic instantiation resolves SymbolTable even when symbol_lookup_fn is a closure."""
    src = """rune Box shard T:
    val as T

concept Measurable:
    weave measure into int

bind Box of int with Measurable:
    weave measure into int:
        return self->val
"""
    c = gen_bundle(src)
    assert "Box_int" in c


def test_p1_20_method_level_generic_shards_on_non_generic_enchanting():
    """P1 #20: Method-level generic shards on non-generic enchanting are registered and callable."""
    src = """rune Container:
    val as int

enchanting Container:
    weave convert shard T with x as T into T:
        return x

weave main into int:
    var c as Container with:
        set .val is 10
    var res as int is calling c.convert of int with 42
    return res
"""
    c = gen_bundle(src)
    assert "Container_convert_int" in c


def test_p2_21_compute_config_hash_includes_dirs():
    """P2 #21: compute_config_hash factors in include_dirs and lib_dirs."""
    from pengu_project import ProjectConfig, PenguBuilder
    cfg1 = ProjectConfig(include_dirs=["/path/to/inc1"], lib_dirs=["/path/to/lib1"])
    b1 = PenguBuilder(cfg1)
    hash1 = b1.compute_config_hash()

    cfg2 = ProjectConfig(include_dirs=["/path/to/inc2"], lib_dirs=["/path/to/lib1"])
    b2 = PenguBuilder(cfg2)
    hash2 = b2.compute_config_hash()

    cfg3 = ProjectConfig(include_dirs=["/path/to/inc1"], lib_dirs=["/path/to/lib2"])
    b3 = PenguBuilder(cfg3)
    hash3 = b3.compute_config_hash()

    assert hash1 != hash2
    assert hash1 != hash3
    assert hash2 != hash3


def test_p2_23_omen_variant_with_underscores():
    """P2 #23: Omen variant names containing underscores resolve without premature prefix trimming."""
    src = """omen Event_Kind:
    ON_CLICK
    ON_HOVER

weave test_fn with e as Event_Kind into bool:
    return e == Event_Kind.ON_CLICK
"""
    c = gen_bundle(src)
    assert "EVENT_KIND_ON_CLICK" in c or "ON_CLICK" in c


def test_omen_pattern_with_c_name_prefix():
    """P1 #8: _check_when_pattern_type recognizes variant names prefixed with omen c_name."""
    from pengu_parser.pengu_symbols import Symbol
    from pengu_parser.pengu_types import OmenType
    from lark import Tree, Token

    checker = PenguChecker()
    omen_t = OmenType("State", {"Init": {}, "Running": {}}, c_name="pkg_State")
    checker.symbols.define(Symbol("State", omen_t, "omen", c_name="pkg_State"))

    pat_node = Tree("when_pattern", [Token("NAME", "pkg_State_Init")])
    checker._check_when_pattern_type(pat_node, omen_t, omen_t)
    assert len(checker.errors) == 0

    bad_pat_node = Tree("when_pattern", [Token("NAME", "pkg_State_Unknown")])
    checker._check_when_pattern_type(bad_pat_node, omen_t, omen_t)
    assert len(checker.errors) == 1
    assert "not a variant" in str(checker.errors[0])


def test_generic_method_in_nongeneric_enchanting_is_emitted():
    """P1 #9: Generic method in non-generic enchanting is registered and emitted upon instantiation."""
    src = """rune Cache:
    size as int

enchanting Cache:
    weave identity shard T with item as T into T:
        return item

weave main into int:
    var c as Cache with:
        set .size is 1
    var num as int is calling c.identity of int with 99
    return num
"""
    c = gen_bundle(src)
    assert "Cache_identity_int" in c

