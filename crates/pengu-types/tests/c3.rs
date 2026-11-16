//! Pruebas C3: records, sums y patrones.

use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::{CheckResult, check_crate};

fn check(source: &str) -> CheckResult {
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
    check_crate(&lowered.krate)
}

fn codes(result: &CheckResult) -> Vec<&'static str> {
    result.diagnostics.iter().map(|d| d.code).collect()
}

const POINT: &str = "rune Point\n    x: Float\n    y: Float\n";

#[test]
fn record_construction_and_field_access() {
    let source = format!(
        "{POINT}\nmake = () -> Point\n    Point(x: 1.0, y: 2.0)\n\narea = (p: Point) -> Float\n    p.x * p.y\n"
    );
    let result = check(&source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn record_update_keeps_type() {
    let source = format!("{POINT}\nmove = (p: Point) -> Point\n    Point(x: p.x + 1.0, ..p)\n");
    let result = check(&source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn missing_and_unknown_fields_are_reported() {
    let source = format!(
        "{POINT}\nbad = () -> Point\n    Point(x: 1.0)\n\nworse = () -> Point\n    Point(z: 1.0)\n"
    );
    let result = check(&source);
    let got = codes(&result);
    assert!(got.contains(&"PGS-E8002"), "{:?}", result.diagnostics);
    assert!(got.contains(&"PGS-E8003"), "{:?}", result.diagnostics);
}

const SHAPE: &str = "enchanting Shape\n    Circle(Float)\n    Rect(Float, Float)\n";

#[test]
fn sum_variants_and_match() {
    let source = format!(
        "{SHAPE}\narea = (s: Shape) -> Float\n    match s\n        when Circle(r) then 3.14 * r * r\n        when Rect(w, h) then w * h\n"
    );
    let result = check(&source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn named_variant_construction_and_pattern() {
    let source = "enchanting Shape\n    Circle(radius: Float)\n    Dot\n\narea = (s: Shape) -> Float\n    match s\n        when Circle(radius: r) then r\n        when Dot then 0.0\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn option_pattern_binds_inner() {
    let source = "get = (o: ?Int) -> Int\n    match o\n        when some(v) then v\n        when none then 0\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn record_pattern_and_named_fields() {
    let source = "rune Point\n    x: Float\n    y: Float\n\nsum = (p: Point) -> Float\n    match p\n        when Point(x, y) then x + y\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn record_pattern_named_fields() {
    let source = "rune Point\n    x: Float\n    y: Float\n\nsum = (p: Point) -> Float\n    match p\n        when Point(x: a, y: b) then a + b\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn non_exhaustive_match_is_reported() {
    let source =
        format!("{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when Circle(_) then 1\n");
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn guard_does_not_make_match_exhaustive() {
    let source = format!(
        "{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when Circle(_) if true then 1\n        when Rect(_, _) then 2\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn else_after_exhaustive_match_is_reported() {
    let source = format!(
        "{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when Circle(_) then 1\n        when Rect(_, _) then 2\n        else 3\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9008"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn bool_match_is_exhaustive_with_both_values() {
    let source =
        "f = (b: Bool) -> Int\n    match b\n        when true then 1\n        when false then 0\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn unreachable_arm_warns() {
    let source = format!(
        "{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when _ then 1\n        when Circle(_) then 2\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-W9001"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn refutable_bind_requires_else() {
    let source = "f = (o: ?Int) -> Int\n    bind some(x) = o\n    x\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E1105"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn for_pattern_must_be_irrefutable() {
    let source = "f = (items: Vec[?Int]) -> Unit\n    for some(x) in items\n        print(x)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E1105"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn duplicate_named_pattern_field_is_reported() {
    let source = format!(
        "{POINT}\nf = (p: Point) -> Float\n    match p\n        when Point(x: a, x: b) then a + b\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9007"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn rest_outside_aggregate_is_reported() {
    let source =
        format!("{POINT}\nf = (p: Point) -> Float\n    match p\n        when .. then 0.0\n");
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9006"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn pattern_type_mismatch_is_reported() {
    let source = format!(
        "{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when 1 then 1\n        when _ then 0\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9003"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn non_bool_guard_is_reported() {
    let source = format!(
        "{SHAPE}\nf = (s: Shape) -> Int\n    match s\n        when _ if 1 then 1\n        else 0\n"
    );
    let result = check(&source);
    assert!(
        codes(&result).contains(&"PGS-E9004"),
        "{:?}",
        result.diagnostics
    );
}

#[test]
fn refutable_bind_with_diverging_else_is_clean() {
    let source = "f = (o: ?Int) -> Int\n    bind some(x) = o else\n        return 0\n    x\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn irrefutable_for_pattern_is_clean() {
    let source = "f = (items: Vec[Int]) -> Unit\n    for x in items\n        print(x)\n";
    let result = check(source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn rest_in_record_pattern_is_clean() {
    let source = format!(
        "{POINT}\nf = (p: Point) -> Float\n    match p\n        when Point(x, ..) then x\n"
    );
    let result = check(&source);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
}

#[test]
fn bind_else_must_diverge_uses_e9005() {
    let source = "f = (o: ?Int) -> Unit\n    bind some(x) = o else\n        0\n    print(x)\n";
    let result = check(source);
    assert!(
        codes(&result).contains(&"PGS-E9005"),
        "{:?}",
        result.diagnostics
    );
}
