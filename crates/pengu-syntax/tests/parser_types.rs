use pengu_span::DUMMY_FILE;
use pengu_syntax::ast::{ExprKind, PatternKind, StmtKind, TypeKind};
use pengu_syntax::parse_expression;

fn parse(source: &str) -> ExprKind {
    let parsed = parse_expression(DUMMY_FILE, source);
    assert!(
        parsed.diagnostics.is_empty(),
        "{source}: {:?}",
        parsed.diagnostics
    );
    parsed.expr.expect("expression").kind
}

#[test]
fn all_type_forms_parse_in_lambda_params() {
    let ExprKind::Lambda { params, .. } =
        parse("(a: ?Int, b: &Str, c: &mut [Int; 3], d: (Int, Str), e: Ptr[U8], f: [U8]) => a")
    else {
        panic!("expected lambda");
    };
    assert!(matches!(params[0].ty.kind, TypeKind::Option(_)));
    assert!(matches!(
        params[1].ty.kind,
        TypeKind::Ref { mutable: false, .. }
    ));
    assert!(matches!(
        params[2].ty.kind,
        TypeKind::Ref { mutable: true, .. }
    ));
    assert!(matches!(params[3].ty.kind, TypeKind::Tuple(_)));
    assert!(matches!(params[4].ty.kind, TypeKind::Ptr(_)));
    assert!(matches!(params[5].ty.kind, TypeKind::Slice(_)));
}

#[test]
fn nested_type_arguments_and_unit() {
    let ExprKind::Lambda { params, .. } = parse("(m: Map[Str, Vec[Int]], u: ()) => u") else {
        panic!("expected lambda");
    };
    let TypeKind::Path { segments, args } = &params[0].ty.kind else {
        panic!("expected path");
    };
    assert_eq!(segments, &["Map"]);
    assert_eq!(args.len(), 2);
    assert!(matches!(params[1].ty.kind, TypeKind::Unit));
}

#[test]
fn pattern_ranges_or_and_bind() {
    let ExprKind::Match { arms, .. } = parse(
        "match n\n    when 0..=9 | 20 then 1\n    when whole @ Some(x) then x\n    when [first, .., last] then first",
    ) else {
        panic!("expected match");
    };
    assert!(matches!(
        arms[0].pattern.as_ref().unwrap().kind,
        PatternKind::Or(_)
    ));
    assert!(matches!(
        arms[1].pattern.as_ref().unwrap().kind,
        PatternKind::Bind { .. }
    ));
    assert!(matches!(
        arms[2].pattern.as_ref().unwrap().kind,
        PatternKind::Slice(_)
    ));
}

#[test]
fn cast_type_is_parsed() {
    let ExprKind::Cast { ty, .. } = parse("value as Vec[?Int]") else {
        panic!("expected cast");
    };
    let TypeKind::Path { args, .. } = ty.kind else {
        panic!("expected path");
    };
    assert!(matches!(args[0].kind, TypeKind::Option(_)));
}

#[test]
fn function_types_and_self_type_in_lambdas() {
    let ExprKind::Lambda { params, .. } =
        parse("(op: (Int, Int) -> Int, thunk: () -> Unit, s: Self) => op(1, 2)")
    else {
        panic!("expected lambda");
    };
    let TypeKind::Fn {
        params: fn_params,
        ret,
    } = &params[0].ty.kind
    else {
        panic!("expected function type");
    };
    assert_eq!(fn_params.len(), 2);
    assert!(matches!(ret.kind, TypeKind::Path { .. }));
    assert!(matches!(params[1].ty.kind, TypeKind::Fn { .. }));
    assert!(matches!(params[2].ty.kind, TypeKind::SelfType));
}

#[test]
fn typed_bindings_parse_in_blocks() {
    let ExprKind::Do(block) = parse(
        "do\n    bind op: (Int, Int) -> Int = add\n    bind pair: (Int, Int) = (1, 2)\n    op(1, 2)",
    ) else {
        panic!("expected do block");
    };
    let StmtKind::Bind { ty: Some(ty), .. } = &block.stmts[0].kind else {
        panic!("expected typed bind");
    };
    assert!(matches!(ty.kind, TypeKind::Fn { .. }));
    let StmtKind::Bind { ty: Some(ty), .. } = &block.stmts[1].kind else {
        panic!("expected typed bind");
    };
    assert!(matches!(ty.kind, TypeKind::Tuple(_)));
}

#[test]
fn one_element_tuple_type_parses() {
    let ExprKind::Lambda { params, .. } = parse("(pair: (Int,)) => pair") else {
        panic!("expected lambda");
    };
    let TypeKind::Tuple(items) = &params[0].ty.kind else {
        panic!("expected tuple type");
    };
    assert_eq!(items.len(), 1);
}

#[test]
fn nested_function_return_type_parses() {
    let ExprKind::Cast { ty, .. } = parse("value as (Int) -> (Int) -> Int") else {
        panic!("expected cast");
    };
    let TypeKind::Fn { ret, .. } = ty.kind else {
        panic!("expected function type");
    };
    assert!(matches!(ret.kind, TypeKind::Fn { .. }));
}
