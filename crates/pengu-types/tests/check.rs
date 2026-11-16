//! Pruebas de C2: tipos, inferencia y literales.

use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::{CheckResult, Ty, check_crate};

fn check(source: &str) -> CheckResult {
    let parsed = parse_program(FileId::new(0), source);
    assert!(
        parsed.diagnostics.is_empty(),
        "errores de parser: {:?}",
        parsed.diagnostics
    );
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(
        lowered.diagnostics.is_empty(),
        "errores HIR: {:?}",
        lowered.diagnostics
    );
    check_crate(&lowered.krate)
}

fn codes(result: &CheckResult) -> Vec<&'static str> {
    result.diagnostics.iter().map(|d| d.code).collect()
}

fn has_type(result: &CheckResult, expected: Ty) -> bool {
    result.types.iter().any(|(_, ty)| *ty == expected)
}

#[test]
fn function_arithmetic_is_clean() {
    let result = check("add = (a: Int, b: Int) -> Int\n    a + b\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn incompatible_operands_are_rejected() {
    let result = check("bad = (a: Int, b: Str) -> Int\n    a + b\n");
    assert!(
        codes(&result).contains(&"PGS-E1402"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn numeric_literal_suffixes_are_inferred() {
    let result = check("f = () -> Unit\n    bind a = 1_i64\n    bind b = 2.5_f32\n    ()\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
    assert!(has_type(&result, Ty::I64));
    assert!(has_type(&result, Ty::F32));
}

#[test]
fn default_literals_are_int_and_float() {
    let result = check("f = () -> Unit\n    bind a = 42\n    bind b = 1.5\n    ()\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
    assert!(has_type(&result, Ty::Int));
    assert!(has_type(&result, Ty::Float));
}

#[test]
fn if_branch_mismatch_is_reported() {
    let result = check("f = (x: Bool) -> Int\n    if x then 1 else \"x\"\n");
    assert!(
        codes(&result).contains(&"PGS-E6002"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn option_try_unwraps() {
    let result = check("f = (x: ?Int) -> ?Int\n    bind y = x?\n    some(y)\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn try_on_non_option_is_rejected() {
    let result = check("f = (x: Int) -> Int\n    x?\n");
    assert!(
        codes(&result).contains(&"PGS-E1504"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn for_range_infers_element_type() {
    let result = check(
        "f = () -> Int\n    bind total = 0\n    for x in 0..5\n        total = total + x\n    total\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn match_arms_unify() {
    let result = check("f = (x: Int) -> Int\n    match x\n        when 0 then 1\n        else 2\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn tuple_fields_and_vector_index_work() {
    let result = check("f = (p: (Int, Bool)) -> Int\n    bind xs = Vec[1, 2]\n    p.0 + xs[0]\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn option_constructors_and_try_work() {
    let result = check("f = () -> ?Int\n    bind x = some(1)\n    bind y = x?\n    some(y)\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn format_and_interpolation_are_accepted() {
    let result = check("f = () -> String\n    format(\"#{1}\")\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn implicit_return_type_is_checked() {
    let result = check("bad = () -> Int\n    \"not an int\"\n");
    assert!(
        codes(&result).contains(&"PGS-E7002"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn function_calls_use_signatures() {
    let result =
        check("add = (a: Int, b: Int) -> Int\n    a + b\napply = () -> Int\n    add(1, 2)\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn loop_break_value_sets_type() {
    let result = check("f = () -> Int\n    loop\n        break 1\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn while_break_value_is_rejected() {
    let result = check("f = () -> Unit\n    while true\n        break 1\n");
    assert!(
        codes(&result).contains(&"PGS-E6005"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn integer_literal_out_of_range_is_rejected() {
    let result = check("f = () -> Unit\n    bind small: U8 = 300\n    ()\n");
    assert!(
        codes(&result).contains(&"PGS-E3001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn suffixed_integer_literal_out_of_range_is_rejected() {
    let result = check("f = () -> U8\n    300_u8\n");
    assert!(
        codes(&result).contains(&"PGS-E3001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn result_try_unwraps_ok_value() {
    let result =
        check("f = (x: Result[Int, Str]) -> Result[Int, Str]\n    bind y = x?\n    ok(y)\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn none_without_context_is_not_inferred() {
    let result = check("f = () -> Unit\n    bind x = none\n    ()\n");
    assert!(
        codes(&result).contains(&"PGS-E1508"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn err_without_success_type_is_rejected() {
    let result = check("f = () -> ?Int\n    bind x = err(\"x\")\n    some(0)\n");
    assert!(
        codes(&result).contains(&"PGS-E1507"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn empty_collections_use_expected_type() {
    let result = check(
        "f = () -> Unit\n    bind xs: Vec[Int] = Vec[]\n    bind ys: Set[Str] = Set[]\n    bind zs: [Int; 0] = []\n    ()\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn empty_collection_without_context_is_not_inferred() {
    let result = check("f = () -> Unit\n    bind xs = Vec[]\n    ()\n");
    assert!(
        codes(&result).contains(&"PGS-E3002"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn int_and_i32_are_aliases() {
    let result = check("f = (x: Int) -> I32\n    x\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn float_and_f64_are_aliases() {
    let result = check("f = (x: Float) -> F64\n    x\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn in_checks_range_element() {
    let result = check("f = (x: Int) -> Bool\n    x in 0..10\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn string_concat_accepts_str_ref() {
    let result = check("f = (s: String, t: &Str) -> String\n    s + t\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn try_in_non_option_return_is_rejected() {
    let result = check("f = (x: ?Int) -> Int\n    bind y = x?\n    y\n");
    assert!(
        codes(&result).contains(&"PGS-E1501"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn map_set_and_array_literals_type() {
    let result = check(
        "f = () -> Int\n    bind arr = [1, 2]\n    bind m = Map[\"a\": 1]\n    bind s = Set[1, 2]\n    arr[0] + m[\"a\"]\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn function_arity_is_checked() {
    let result = check("add = (a: Int, b: Int) -> Int\n    a + b\nf = () -> Int\n    add(1)\n");
    assert!(
        codes(&result).contains(&"PGS-E7005"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn function_argument_types_are_checked() {
    let result =
        check("add = (a: Int, b: Int) -> Int\n    a + b\nf = () -> Int\n    add(\"x\", 2)\n");
    assert!(
        codes(&result).contains(&"PGS-E7006"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn explicit_return_type_is_checked() {
    let result = check("f = () -> Int\n    return \"x\"\n");
    assert!(
        codes(&result).contains(&"PGS-E6006"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn print_and_format_are_builtins() {
    let result = check("f = () -> String\n    print(\"hello\")\n    format(\"{}\", 1)\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn empty_map_uses_expected_type() {
    let result = check("f = () -> Unit\n    bind m: Map[Str, Int] = Map[]\n    ()\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn if_without_else_requires_unit() {
    let result = check("f = () -> Unit\n    if true then 1\n");
    assert!(
        codes(&result).contains(&"PGS-E3001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn if_without_else_accepts_unit() {
    let result = check("f = () -> Unit\n    if true then print(\"x\")\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn numeric_and_char_casts_are_accepted() {
    let result = check(
        "f = () -> Unit\n    bind a = 300 as U8\n    bind b = 'P' as U32\n    bind c = 2 as Float\n    ()\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn invalid_casts_are_rejected() {
    let result = check("f = () -> Unit\n    bind a = \"x\" as Int\n    ()\n");
    assert!(
        codes(&result).contains(&"PGS-E1404"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn int_to_char_is_rejected() {
    let result = check("f = () -> Unit\n    bind a = 65 as Char\n    ()\n");
    assert!(
        codes(&result).contains(&"PGS-E1404"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn method_call_resolves_receiver_signature() {
    let result = check(
        "rune Point\n    x: Float\n    y: Float\n\nritual Point\n    x = (@) -> Float\n        @.x\n\ngrimoire\n    bind p = Point(x: 1.0, y: 2.0)\n    bind n: Float = p.x()\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn generic_function_infers_and_accepts_turbofish() {
    let result = check(
        "identity = [T](value: T) -> T\n    value\n\ngrimoire\n    bind n = identity(42)\n    bind s = identity[Str](\"pengu\")\n    print(n)\n    print(s)\n",
    );
    assert!(result.diagnostics.is_empty(), "{:?}", result.diagnostics);
}

#[test]
fn generic_bound_is_checked() {
    let result = check(
        "pact Eq\n    eq = (@, other: &Self) -> Bool\n\nsame = [T: Eq](a: T, b: T) -> Bool\n    a == b\n\ngrimoire\n    print(same(1, 2))\n",
    );
    assert!(result.diagnostics.is_empty(), "{:?}", result.diagnostics);
}

#[test]
fn unsatisfied_generic_bound_is_reported() {
    let result = check(
        "pact MyBound\n    holds = (@) -> Bool\n\nneeds = [T: MyBound](value: T) -> T\n    value\n\ngrimoire\n    bind n = needs(1)\n    print(n)\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1302"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn pact_impl_method_is_callable() {
    let result = check(
        "pact Shape\n    area = (@) -> Float\n\nrune Square\n    side: Float\n\nritual Square for Shape\n    area = (@) -> Float\n        @.side * @.side\n\ngrimoire\n    bind s = Square(side: 2.0)\n    bind a = s.area()\n    print(a)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn missing_pact_method_is_reported() {
    let result = check(
        "pact Shape\n    area = (@) -> Float\n\nrune Empty\n    x: Float\n\nritual Empty for Shape\n    other = (@) -> Float\n        0.0\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1201"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn user_operator_overload_is_used() {
    let result = check(
        "pact Add\n    add = (@, other: &Self) -> Self\n\nrune Vec2\n    x: Float\n    y: Float\n\nritual Vec2 for Add\n    add = (@, other: &Vec2) -> Vec2\n        Vec2(x: @.x + other.x, y: @.y + other.y)\n\ngrimoire\n    bind a = Vec2(x: 1.0, y: 2.0)\n    bind b = Vec2(x: 3.0, y: 4.0)\n    bind c = a + b\n    print(c.x)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn generic_record_infers_type_arguments() {
    let result = check(
        "rune Pair[A, B]\n    first: A\n    second: B\n\ngrimoire\n    bind p = Pair(first: 1, second: \"uno\")\n    bind a: Int = p.first\n    bind b: Str = p.second\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn mismatched_pact_method_signature_is_reported() {
    let result = check(
        "pact Shape\n    area = (@) -> Float\n\nrune Square\n    x: Float\n\nritual Square for Shape\n    area = (@) -> Int\n        1\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1202"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn overlapping_impls_are_reported() {
    let result = check(
        "pact Shape\n    area = (@) -> Float\n\nrune Square\n    x: Float\n\nritual Square for Shape\n    area = (@) -> Float\n        1.0\n\nritual Square for Shape\n    area = (@) -> Float\n        2.0\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1206"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn print_requires_show() {
    let result = check("rune P\n    x: Int\n\ngrimoire\n    print(P(x: 0))\n");
    assert!(
        codes(&result).contains(&"PGS-E1202"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn generic_pact_and_ritual_declare() {
    let result = check(
        "pact Container[T]\n    contains = (@, target: &T) -> Bool\n\nrune Wrap[T]\n    value: T\n\nritual[T] Wrap[T]\n    into_inner = (@own) -> T\n        @.value\n\ngrimoire\n    bind b = Wrap(value: 1)\n    bind x: Int = b.into_inner()\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn generic_pact_impl_signature_matches() {
    let result = check(
        "pact Container[T]\n    contains = (@, target: &T) -> Bool\n\nrune Wrap[T]\n    value: T\n\nritual[T] Wrap[T] for Container[T]\n    contains = (@, target: &T) -> Bool\n        false\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn valid_derives_are_accepted() {
    let result =
        check("@@derive(Debug, Clone, PartialEq)\nrune Point\n    x: Float\n    y: Float\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn eq_on_float_field_is_rejected() {
    let result = check("@@derive(Eq)\nrune Point\n    x: Float\n");
    assert!(has_code(&result, "PGS-E8007"), "{:?}", result.diagnostics);
}

#[test]
fn copy_without_clone_is_rejected() {
    let result = check("@@derive(Copy)\nrune Point\n    x: Int\n");
    assert!(has_code(&result, "PGS-E8007"), "{:?}", result.diagnostics);
}

#[test]
fn default_on_sum_is_rejected() {
    let result = check("@@derive(Default)\nenchanting Shape\n    Dot\n");
    assert!(has_code(&result, "PGS-E8007"), "{:?}", result.diagnostics);
}

#[test]
fn foreign_signature_is_accepted() {
    let result = check("foreign \"C\"\n    abs = (x: Int) -> Int\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn foreign_non_ffi_type_is_rejected() {
    assert!(
        hir_codes("foreign \"C\"\n    bad = (x: String) -> Int\n").contains(&"PGS-E1604"),
        "se esperaba PGS-E1604"
    );
}

#[test]
fn foreign_call_outside_curse_is_rejected() {
    let result =
        check("foreign \"C\"\n    abs = (x: Int) -> Int\n\ncall = () -> Int\n    abs(1)\n");
    assert!(has_code(&result, "PGS-E1602"), "{:?}", result.diagnostics);
}

#[test]
fn curse_function_call_outside_curse_is_rejected() {
    let result = check(
        "foreign \"C\"\n    read = (fd: Int) -> Int\n\n-- SAFETY: el llamador valida el descriptor\ncurse read_raw = (fd: Int) -> Int\n    read(fd)\n\ncall = () -> Int\n    read_raw(1)\n",
    );
    assert!(has_code(&result, "PGS-E1602"), "{:?}", result.diagnostics);
}

#[test]
fn curse_function_call_inside_curse_is_accepted() {
    let result = check(
        "foreign \"C\"\n    read = (fd: Int) -> Int\n\n-- SAFETY: el llamador valida el descriptor\ncurse read_raw = (fd: Int) -> Int\n    read(fd)\n\ncall = () -> Int\n    curse\n        read_raw(1)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn foreign_call_inside_curse_is_accepted() {
    let result = check(
        "foreign \"C\"\n    abs = (x: Int) -> Int\n\ncall = () -> Int\n    curse\n        abs(1)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn unknown_ffi_abi_is_rejected() {
    assert!(
        hir_codes("foreign \"rust\"\n    abs = (x: Int) -> Int\n").contains(&"PGS-E1605"),
        "se esperaba PGS-E1605"
    );
}

fn has_code(result: &CheckResult, code: &str) -> bool {
    result.diagnostics.iter().any(|d| d.code == code)
}

fn hir_codes(source: &str) -> Vec<&'static str> {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    lowered.diagnostics.iter().map(|d| d.code).collect()
}

#[test]
fn const_arithmetic_is_accepted() {
    let result = check("sigil X: Int = 2 + 3 * 4\n");
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn const_call_is_rejected() {
    let result = check("f = () -> Int\n    1\n\nsigil X: Int = f()\n");
    assert!(has_code(&result, "PGS-E1107"), "{:?}", result.diagnostics);
}

#[test]
fn const_division_by_zero_is_rejected() {
    let result = check("sigil X: Int = 1 / 0\n");
    assert!(has_code(&result, "PGS-E1403"), "{:?}", result.diagnostics);
}

#[test]
fn warnings_do_not_make_result_dirty() {
    let result = check(
        "enchanting E\n    A\n    B\n\ngrimoire\n    bind e = A\n    bind x = match e\n        when A then 1\n        when A then 2\n        when B then 3\n    print(x)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
    assert!(has_code(&result, "PGS-W9001"), "{:?}", result.diagnostics);
}

#[test]
fn non_bool_condition_uses_e6001() {
    let result = check("grimoire\n    if 1 then 2 else 3\n");
    assert!(
        codes(&result).contains(&"PGS-E6001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn call_arity_uses_e7005() {
    let result = check("f = (x: Int) -> Int\n    x\ng = () -> Int\n    f(1, 2)\n");
    assert!(
        codes(&result).contains(&"PGS-E7005"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn break_value_in_while_uses_e6005() {
    let result = check("f = () -> Unit\n    while true\n        break 1\n");
    assert!(
        codes(&result).contains(&"PGS-E6005"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn constant_array_index_out_of_bounds_uses_e3101() {
    let result = check("grimoire\n    print([1, 2][2])\n");
    assert!(
        codes(&result).contains(&"PGS-E3101"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn float_map_key_uses_e3102() {
    let result = check("grimoire\n    bind m = Map[1.5: 2]\n");
    assert!(
        codes(&result).contains(&"PGS-E3102"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn float_set_element_uses_e3103() {
    let result = check("grimoire\n    bind s = Set[1.5]\n");
    assert!(
        codes(&result).contains(&"PGS-E3103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn relic_reassignment_uses_e1108() {
    let result = check("relic X: Int = 1\ngrimoire\n    X = 2\n");
    assert!(
        codes(&result).contains(&"PGS-E1108"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn sigil_reassignment_uses_e1103() {
    let result = check("sigil X: Int = 1\ngrimoire\n    X = 2\n");
    assert!(
        codes(&result).contains(&"PGS-E1103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn empty_vec_without_annotation_uses_e3104() {
    let result = check("grimoire\n    bind v = Vec[]\n");
    assert!(
        codes(&result).contains(&"PGS-E3104"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn invalid_assignment_place_uses_e6007() {
    let result = check("grimoire\n    1 = 2\n");
    assert!(
        codes(&result).contains(&"PGS-E6007"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn break_value_type_mismatch_uses_e6008() {
    let result = check("f = () -> Int\n    loop\n        break 1\n        break \"x\"\n");
    assert!(
        codes(&result).contains(&"PGS-E6008"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unused_generic_uses_e1301() {
    let result = check("f = [T]() -> Int\n    1\n");
    assert!(
        codes(&result).contains(&"PGS-E1301"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn mismatched_operator_signature_uses_e1407() {
    let result = check(
        "pact Add\n    add = (@, other: &Self) -> Self\n\nrune V\n    x: Int\n\nritual V for Add\n    add = (@) -> V\n        V(x: 0)\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1407"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn private_field_access_uses_e1104() {
    let result = check(
        "scroll geometry\n    unveil rune Point\n        x: Int\n\ngrimoire\n    bind p = geometry::Point(x: 1)\n    print(p.x)\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1104"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn curse_without_ffi_uses_e1607() {
    let result = check("-- SAFETY: test\ncurse f = () -> Int\n    1\n");
    assert!(
        codes(&result).contains(&"PGS-E1607"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unreachable_statement_uses_w6001() {
    let result = check("f = () -> Int\n    return 1\n    2\n");
    assert!(
        codes(&result).contains(&"PGS-W6001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn constant_loop_condition_uses_w6002() {
    let result = check("f = () -> Unit\n    while true\n        break\n");
    assert!(
        codes(&result).contains(&"PGS-W6002"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unwrap_in_production_uses_w1501() {
    let result = check("f = () -> Int\n    some(1).unwrap()\n");
    assert!(
        codes(&result).contains(&"PGS-W1501"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn comparison_type_mismatch_uses_e1401() {
    let result = check("f = () -> Bool\n    1 == \"x\"\n");
    assert!(
        codes(&result).contains(&"PGS-E1401"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unused_binding_uses_w1101() {
    let result = check("f = () -> Unit\n    bind x = 1\n    return\n");
    assert!(
        codes(&result).contains(&"PGS-W1101"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn never_binding_uses_e7008() {
    let result = check("f = () -> Unit\n    bind x = loop\n        continue\n");
    assert!(
        codes(&result).contains(&"PGS-E7008"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn forbidden_operator_pact_uses_e1406() {
    let result = check(
        "pact Index\n    get = (@) -> Int\n\nrune P\n    x: Int\n\nritual P for Index\n    get = (@) -> Int\n        1\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E1406"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn result_without_error_uses_e3008() {
    let result = check("f = () -> Result[Int]\n    1\n");
    assert!(
        codes(&result).contains(&"PGS-E3008"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn function_as_value_without_type_uses_e7007() {
    let result = check("f = () -> Int\n    1\ng = () -> Unit\n    bind h = f\n    return\n");
    assert!(
        codes(&result).contains(&"PGS-E7007"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn try_outside_result_uses_e1405() {
    let result = check("f = () -> Int\n    some(1)?\n");
    assert!(
        codes(&result).contains(&"PGS-E1405"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn result_without_error_uses_e1505() {
    let result = check("f = () -> Result[Int]\n    1\n");
    assert!(
        codes(&result).contains(&"PGS-E1505"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn assert_eq_type_mismatch_uses_e1704() {
    let result = check("f = () -> Unit\n    assert_eq(1, \"x\")\n");
    assert!(
        codes(&result).contains(&"PGS-E1704"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unknown_method_uses_e3001() {
    let result = check("rune P\n    x: Int\nf = (p: P) -> Unit\n    p.nope()\n");
    assert!(
        codes(&result).contains(&"PGS-E3001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn unsatisfied_bound_also_uses_e3005() {
    let result = check(
        "pact MyBound\n    holds = (@) -> Bool\n\nneeds = [T: MyBound](value: T) -> T\n    value\n\ngrimoire\n    bind n = needs(1)\n    print(n)\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E3005"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn generic_operator_without_bound_uses_e3004() {
    let result = check("same = [T](a: T, b: T) -> Bool\n    a == b\n");
    assert!(
        codes(&result).contains(&"PGS-E3004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn generic_operator_with_bound_is_clean() {
    let result = check(
        "pact Eq\n    eq = (@, other: &Self) -> Bool\n\nsame = [T: Eq](a: T, b: T) -> Bool\n    a == b\n",
    );
    assert!(
        !codes(&result).contains(&"PGS-E3004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn generic_return_only_cannot_infer_e1305() {
    let result = check("make = [T]() -> ?T\n    none\n\ngrimoire\n    bind value = make()\n");
    assert!(
        codes(&result).contains(&"PGS-E1305"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn cstring_new_without_try_uses_e1608() {
    let result = check("f = () -> Unit\n    CString.new(\"x\")\n");
    assert!(
        codes(&result).contains(&"PGS-E1608"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn borrowed_generic_field_requires_own_receiver() {
    let result = check(
        "rune Wrap[T]\n    value: T\n\nritual[T] Wrap[T]\n    get = (@) -> T\n        @.value\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E4105"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn own_receiver_can_return_generic_field() {
    let result = check(
        "rune Wrap[T]\n    value: T\n\nritual[T] Wrap[T]\n    get = (@own) -> T\n        @.value\n\ngrimoire\n    bind b = Wrap(value: 1)\n    bind x: Int = b.get()\n    print(x)\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn match_on_generic_sum_binds_instantiated_fields() {
    let result = check(
        "enchanting Maybe[T]\n    Just(T)\n    Nothing\n\nunwrap_or = [T](m: Maybe[T], fallback: T) -> T\n    match m\n        when Just(v)\n            v\n        when Nothing\n            fallback\n\ngrimoire\n    bind m: Maybe[Int] = Just(41)\n    print(unwrap_or(m, 0))\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn positional_pattern_matches_named_variant() {
    let result = check(
        "enchanting Shape\n    Circle(radius: Float)\n    Point\n\nmeasure = (s: Shape) -> Float\n    match s\n        when Circle(radius)\n            radius * radius\n        when Point\n            0.0\n\ngrimoire\n    bind c = Circle(radius: 2.0)\n    print(measure(c))\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn generic_sum_string_field_accepts_coercion() {
    let result = check(
        "enchanting Maybe[T]\n    Just(T)\n    Nothing\n\nunwrap_or = [T](m: Maybe[T], fallback: T) -> T\n    match m\n        when Just(v)\n            v\n        when Nothing\n            fallback\n\ngrimoire\n    bind m: Maybe[String] = Just(\"hi\")\n    print(unwrap_or(m, \"no\"))\n",
    );
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}
