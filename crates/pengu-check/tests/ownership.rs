//! Pruebas C4: ownership, moves y préstamos.

use pengu_check::{OwnershipResult, check_ownership_with};
use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn check(source: &str) -> OwnershipResult {
    let parsed = parse_program(FileId::new(0), source);
    assert!(
        parsed.diagnostics.is_empty(),
        "parser: {:?}",
        parsed.diagnostics
    );
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(
        lowered.diagnostics.is_empty(),
        "HIR: {:?}",
        lowered.diagnostics
    );
    let types = check_crate(&lowered.krate);
    check_ownership_with(&lowered.krate, &types)
}

fn codes(result: &OwnershipResult) -> Vec<&'static str> {
    result.diagnostics.iter().map(|d| d.code).collect()
}

#[test]
fn copy_values_can_be_used_after_assignment() {
    let source = "main = () -> Unit\n    bind a = 1\n    bind b = a\n    print(a)\n    print(b)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn moving_a_string_then_using_it_is_rejected() {
    let source = "rune P\n    name: String\n\nmain = () -> Unit\n    bind p = P(name: \"pengu\")\n    bind q = p\n    print(p)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4101"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn moving_a_borrowed_value_is_rejected() {
    let source = "rune P\n    name: String\n\nmain = () -> Unit\n    morph v = P(name: \"pengu\")\n    bind r = &v\n    bind w = v\n    print(r)\n    print(w)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4106"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn mutable_and_shared_borrows_conflict() {
    let source = "main = () -> Unit\n    morph v = 1\n    bind a = &v\n    bind b = &mut v\n    print(a)\n    print(b)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4102"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn assigning_to_an_immutable_binding_is_rejected() {
    let source = "main = () -> Unit\n    bind x = 1\n    x = 2\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn assigning_to_a_borrowed_value_is_rejected() {
    let source = "main = () -> Unit\n    morph x = 1\n    bind r = &x\n    x = 2\n    print(r)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4108"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn free_function_cannot_return_a_reference() {
    let source = "first = (text: &Str) -> &Str\n    text\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4109"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn borrowing_a_local_is_allowed() {
    let source = "main = () -> Unit\n    bind v = 1\n    bind r = &v\n    print(r)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn match_that_moves_a_field_poisons_the_record() {
    let source = "rune P\n    name: String\n\nmain = () -> Unit\n    bind p = P(name: \"pengu\")\n    match p\n        when P(name) then print(name)\n    print(p)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4101"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn mutating_a_collection_requires_morph() {
    let source = "main = () -> Unit\n    bind v: Vec[Int] = Vec[]\n    v.push(1)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E3106"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn mutable_borrow_of_immutable_binding_is_rejected() {
    let source = "main = () -> Unit\n    bind v = 1\n    bind r = &mut v\n    print(r)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn matching_copy_fields_does_not_move_the_record() {
    let source = "rune P\n    x: Float\n\nmain = () -> Unit\n    bind p = P(x: 1.0)\n    match p\n        when P(x) then print(x)\n    print(p)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn copy_record_can_be_used_after_binding() {
    let source = "@@derive(Copy, Clone)\nrune P\n    x: Int\n\nmain = () -> Unit\n    bind p = P(x: 1)\n    bind q = p\n    print(p)\n    print(q)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn mutable_collection_can_be_modified() {
    let source = "main = () -> Unit\n    morph v: Vec[Int] = Vec[]\n    v.push(1)\n    print(v)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn moving_one_field_leaves_other_fields_usable() {
    let source = "rune P\n    name: String\n    age: Int\n\nmain = () -> Unit\n    bind p = P(name: \"pengu\", age: 3)\n    match p\n        when P(name) then print(name)\n    print(p.age)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn nll_allows_mutation_after_last_use() {
    let diagnostics =
        check("grimoire\n    morph v = Vec[1]\n    bind r = &v\n    print(r)\n    v.push(2)\n");
    assert!(
        diagnostics.diagnostics.is_empty(),
        "{:?}",
        diagnostics.diagnostics
    );
}

#[test]
fn nll_loan_without_use_does_not_block_mutation() {
    let diagnostics = check("grimoire\n    morph v = Vec[1]\n    bind r = &v\n    v.push(2)\n");
    assert!(
        diagnostics.diagnostics.is_empty(),
        "{:?}",
        diagnostics.diagnostics
    );
}

#[test]
fn method_mut_receiver_requires_morph() {
    let result = check(
        "rune Point\n    x: Float\n\nritual Point\n    set = (@mut) -> Unit\n        @.x\n\ngrimoire\n    bind p = Point(x: 1.0)\n    p.set()\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn own_method_consumes_receiver() {
    let result = check(
        "rune Point\n    x: Float\n\nritual Point\n    take = (@own) -> Float\n        @.x\n\ngrimoire\n    bind p = Point(x: 1.0)\n    bind n = p.take()\n    print(p)\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E4101"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn closure_can_read_capture_twice() {
    let result = check(
        "grimoire\n    bind base = 10\n    bind add = (x: Int) => x + base\n    bind a = add(1)\n    bind b = add(2)\n",
    );
    assert!(
        !codes(&result).contains(&"PGS-E7004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn closure_cannot_consume_capture() {
    let result = check("grimoire\n    bind s = \"x\"\n    bind f = () =>\n        bind t = s\n");
    assert!(
        codes(&result).contains(&"PGS-E7004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn closure_cannot_return() {
    let result = check("grimoire\n    bind f = () =>\n        return 1\n");
    assert!(
        codes(&result).contains(&"PGS-E7004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn closure_borrow_ends_at_last_call() {
    let result = check(
        "grimoire\n    morph v = Vec[1]\n    bind f = () => print(v)\n    f()\n    f()\n    v.push(2)\n",
    );
    assert!(
        !codes(&result).contains(&"PGS-E4102"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn closure_borrow_blocks_mutation_before_last_call() {
    let result = check(
        "grimoire\n    morph v = Vec[1]\n    bind f = () => print(v)\n    v.push(2)\n    f()\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E4102"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn method_mut_receiver_accepts_morph() {
    let result = check(
        "rune Point\n    x: Float\n\nritual Point\n    set = (@mut) -> Unit\n        @.x\n\ngrimoire\n    morph p = Point(x: 1.0)\n    p.set()\n",
    );
    assert!(
        !codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn temporary_borrow_ends_after_statement() {
    let result = check("grimoire\n    morph v = Vec[1]\n    print(&v)\n    v.push(2)\n");
    assert!(
        !codes(&result).contains(&"PGS-E4102"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn immutable_self_cannot_assign_a_field() {
    let result = check(
        "rune Point\n    x: Float\n\nritual Point\n    set = (@) -> Unit\n        @.x = 2.0\n\ngrimoire\n    morph p = Point(x: 1.0)\n    p.set()\n",
    );
    assert!(
        codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn mutable_self_can_assign_a_field() {
    let result = check(
        "rune Point\n    x: Float\n\nritual Point\n    set = (@mut) -> Unit\n        @.x = 2.0\n\ngrimoire\n    morph p = Point(x: 1.0)\n    p.set()\n",
    );
    assert!(
        !codes(&result).contains(&"PGS-E4103"),
        "{:?}",
        result.diagnostics
    );
}
