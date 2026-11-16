use pengu_span::DUMMY_FILE;
use pengu_syntax::ast::{BinOp, Expr, ExprKind, PatternKind, StmtKind, TypeKind, UnOp};
use pengu_syntax::parse_expression;

fn parse(source: &str) -> pengu_syntax::ast::Expr {
    let parsed = parse_expression(DUMMY_FILE, source);
    assert!(
        parsed.diagnostics.is_empty(),
        "diagnostics: {:?}",
        parsed.diagnostics
    );
    parsed.expr.expect("expression")
}

#[test]
fn precedence_multiplication_before_addition() {
    let expr = parse("1 + 2 * 3");
    let ExprKind::Binary {
        op: BinOp::Add,
        rhs,
        ..
    } = expr.kind
    else {
        panic!("expected add, got {:?}", expr.kind);
    };
    assert!(matches!(rhs.kind, ExprKind::Binary { op: BinOp::Mul, .. }));
}

#[test]
fn precedence_and_before_or() {
    let expr = parse("a or b and c");
    let ExprKind::Binary {
        op: BinOp::Or, rhs, ..
    } = expr.kind
    else {
        panic!("expected or, got {:?}", expr.kind);
    };
    assert!(matches!(rhs.kind, ExprKind::Binary { op: BinOp::And, .. }));
}

#[test]
fn postfix_chain() {
    let expr = parse("foo.bar(1)[0]?");
    assert!(matches!(expr.kind, ExprKind::Try(_)));
}

#[test]
fn casts_and_ranges() {
    let expr = parse("x as Int");
    assert!(matches!(expr.kind, ExprKind::Cast { .. }));
    let expr = parse("0..=10");
    assert!(matches!(
        expr.kind,
        ExprKind::Range {
            inclusive: true,
            ..
        }
    ));
}

#[test]
fn array_repeat_and_collection_literals() {
    let expr = parse("[0; 4]");
    assert!(matches!(expr.kind, ExprKind::ArrayRepeat { .. }));
    let expr = parse("Vec[1, 2, 3]");
    assert!(matches!(expr.kind, ExprKind::Vector(v) if v.len() == 3));
    let expr = parse("Map[\"a\": 1, \"b\": 2]");
    assert!(matches!(expr.kind, ExprKind::Map(m) if m.len() == 2));
    let expr = parse("Set[\"a\", \"b\"]");
    assert!(matches!(expr.kind, ExprKind::Set(s) if s.len() == 2));
}

#[test]
fn tuples_and_lambdas() {
    let expr = parse("(1,)");
    assert!(matches!(expr.kind, ExprKind::Tuple(t) if t.len() == 1));
    let expr = parse("(x: Int, y: Int) => x + y");
    assert!(matches!(expr.kind, ExprKind::Lambda { params, .. } if params.len() == 2));
    let expr = parse("(1 + 2) * 3");
    assert!(matches!(expr.kind, ExprKind::Binary { op: BinOp::Mul, .. }));
}

#[test]
fn inline_if_and_match() {
    let expr = parse("if ready then 1");
    assert!(matches!(
        expr.kind,
        ExprKind::If {
            else_branch: None,
            ..
        }
    ));
    let expr = parse("if ready then 1 else 0");
    assert!(matches!(
        expr.kind,
        ExprKind::If {
            else_branch: Some(_),
            ..
        }
    ));
    let expr = parse(
        "match value\n    when 0 then \"zero\"\n    when n if n > 0 then \"positive\"\n    else \"negative\"",
    );
    let ExprKind::Match { arms, .. } = expr.kind else {
        panic!("expected match");
    };
    assert_eq!(arms.len(), 3);
    assert!(matches!(
        arms[1].pattern.as_ref().map(|p| &p.kind),
        Some(PatternKind::Path(_))
    ));
    assert!(arms[1].guard.is_some());
}

#[test]
fn references_and_tuple_fields() {
    assert!(matches!(
        parse("&values").kind,
        ExprKind::Ref { mutable: false, .. }
    ));
    assert!(matches!(
        parse("&mut values").kind,
        ExprKind::Ref { mutable: true, .. }
    ));
    assert!(matches!(
        parse("&numbers[1..3]").kind,
        ExprKind::Ref { mutable: false, .. }
    ));
    let field = parse("pair.0");
    assert!(matches!(field.kind, ExprKind::Field { name, .. } if name == "0"));
}

#[test]
fn receivers_self_and_control_forms() {
    assert!(matches!(parse("@").kind, ExprKind::SelfValue));
    assert!(matches!(parse("Self").kind, ExprKind::SelfValue));
    let call = parse("@.len()");
    let ExprKind::Call { callee, .. } = call.kind else {
        panic!("expected call");
    };
    assert!(matches!(callee.kind, ExprKind::Field { .. }));
    assert!(matches!(parse("loop\n    break 5").kind, ExprKind::Loop(_)));
    assert!(matches!(
        parse("curse\n    read(p)").kind,
        ExprKind::Curse(_)
    ));
    assert!(matches!(
        parse("do\n    if ready then\n        1").kind,
        ExprKind::Do(_)
    ));
}

#[test]
fn block_bind_and_loop() {
    let expr = parse("do\n    bind x = 1\n    morph y = 2\n    x + y");
    let ExprKind::Do(block) = expr.kind else {
        panic!("expected block");
    };
    assert_eq!(block.stmts.len(), 3);
    assert!(matches!(
        block.stmts[0].kind,
        StmtKind::Bind { mutable: false, .. }
    ));
    assert!(matches!(
        block.stmts[1].kind,
        StmtKind::Bind { mutable: true, .. }
    ));
}

#[test]
fn while_for_and_break() {
    let expr = parse("do\n    while ready\n        break 1\n    for x in 0..10\n        continue");
    let ExprKind::Do(block) = expr.kind else {
        panic!("expected block");
    };
    assert_eq!(block.stmts.len(), 2);
    assert!(matches!(block.stmts[0].kind, StmtKind::While { .. }));
    assert!(matches!(block.stmts[1].kind, StmtKind::For { .. }));
}

#[test]
fn patterns_and_types() {
    let expr = parse(
        "match point\n    when Point(x: 0, y: 1) then y\n    when [first, .., last] then first",
    );
    let ExprKind::Match { arms, .. } = expr.kind else {
        panic!("expected match");
    };
    assert!(
        matches!(&arms[0].pattern.as_ref().unwrap().kind, PatternKind::Variant { named, .. } if named.len() == 2)
    );
    assert!(
        matches!(&arms[1].pattern.as_ref().unwrap().kind, PatternKind::Slice(items) if items.len() == 3)
    );

    let expr = parse("(x: [Int; 3], y: ?&Str) => x");
    let ExprKind::Lambda { params, .. } = expr.kind else {
        panic!("expected lambda");
    };
    assert!(matches!(params[0].ty.kind, TypeKind::Array { .. }));
    assert!(matches!(params[1].ty.kind, TypeKind::Option(_)));
}

#[test]
fn unary_and_boolean_ops() {
    let expr = parse("-1");
    assert!(matches!(expr.kind, ExprKind::Unary { op: UnOp::Neg, .. }));
    let expr = parse("not ready and ok");
    assert!(matches!(expr.kind, ExprKind::Binary { op: BinOp::And, .. }));
}

#[test]
fn comments_are_ignored() {
    let expr = parse("-- leading\n1 -- trailing\n");
    assert!(matches!(expr.kind, ExprKind::Int(_)));
}

#[test]
fn syntax_error_has_code() {
    let parsed = parse_expression(DUMMY_FILE, "1 +");
    assert!(!parsed.diagnostics.is_empty());
    assert_eq!(parsed.diagnostics[0].code, "PGS-E1901");
}

#[test]
fn if_block_with_elseif_and_else() {
    let expr = parse("if a then\n    1\nelseif b then\n    2\nelse\n    3");
    let ExprKind::If { else_branch, .. } = expr.kind else {
        panic!("expected if");
    };
    let else_block = else_branch.expect("else");
    assert!(matches!(
        else_block.stmts[0].kind,
        StmtKind::Expr(Expr {
            kind: ExprKind::If { .. },
            ..
        })
    ));
}

#[test]
fn loop_curse_and_bind_else() {
    let expr = parse(
        "do\n    loop\n        break 1\n    curse\n        outer()\n    bind ok(value) = action() else\n        return none",
    );
    let ExprKind::Do(block) = expr.kind else {
        panic!("expected do");
    };
    assert!(matches!(
        block.stmts[0].kind,
        StmtKind::Expr(Expr {
            kind: ExprKind::Loop(_),
            ..
        })
    ));
    assert!(matches!(
        block.stmts[1].kind,
        StmtKind::Expr(Expr {
            kind: ExprKind::Curse(_),
            ..
        })
    ));
    assert!(matches!(
        block.stmts[2].kind,
        StmtKind::Bind {
            else_block: Some(_),
            ..
        }
    ));
}

#[test]
fn interpolation_and_self() {
    let expr = parse("\"hello #{name} #{@.count}\"");
    let ExprKind::String(lit) = expr.kind else {
        panic!("expected string");
    };
    assert!(
        lit.parts
            .iter()
            .any(|part| matches!(part, pengu_syntax::ast::StringPart::Expr(_)))
    );

    let expr = parse("@");
    assert!(matches!(expr.kind, ExprKind::SelfValue));
}

#[test]
fn calls_index_field_and_assignment() {
    let expr = parse("do\n    items[0] = make(1).value\n    obj.field");
    let ExprKind::Do(block) = expr.kind else {
        panic!("expected do");
    };
    assert!(matches!(block.stmts[0].kind, StmtKind::Assign { .. }));
    assert!(matches!(
        block.stmts[1].kind,
        StmtKind::Expr(Expr {
            kind: ExprKind::Field { .. },
            ..
        })
    ));
}

#[test]
fn set_and_brace_map() {
    let expr = parse("Set[1, 2]");
    assert!(matches!(expr.kind, ExprKind::Set(items) if items.len() == 2));
    let expr = parse("{1: \"one\", 2: \"two\"}");
    assert!(matches!(expr.kind, ExprKind::Map(entries) if entries.len() == 2));
}

#[test]
fn comments_between_if_branches() {
    let expr = parse("if a then\n    1\n-- between\nelseif b then\n    2\n-- else\nelse\n    3");
    let ExprKind::If { else_branch, .. } = expr.kind else {
        panic!("expected if");
    };
    assert!(else_branch.is_some());
}

#[test]
fn match_arms_accept_thenless_blocks() {
    let expr = parse(
        "match shape\n    when Circle(r)\n        r\n    when Point\n        y\n    else\n        z",
    );
    let ExprKind::Match { arms, .. } = expr.kind else {
        panic!("expected match");
    };
    assert_eq!(arms.len(), 3);
    assert_eq!(arms[0].body.stmts.len(), 1);
    assert_eq!(arms[1].body.stmts.len(), 1);
    assert!(arms[2].pattern.is_none());
}

#[test]
fn lambda_block_and_unless() {
    let expr = parse("(x: Int) =>\n    if x < 0 then\n        -x\n    else\n        x");
    let ExprKind::Lambda { body, .. } = expr.kind else {
        panic!("expected lambda");
    };
    assert_eq!(body.stmts.len(), 1);
    let expr = parse("unless ready then 0 else 1");
    assert!(matches!(expr.kind, ExprKind::If { unless: true, .. }));
}

#[test]
fn empty_collections_and_open_range() {
    assert!(matches!(parse("[]").kind, ExprKind::Array(v) if v.is_empty()));
    assert!(matches!(parse("Vec[]").kind, ExprKind::Vector(v) if v.is_empty()));
    assert!(matches!(parse("Set[]").kind, ExprKind::Set(v) if v.is_empty()));
    assert!(matches!(parse("{}").kind, ExprKind::Map(m) if m.is_empty()));
    assert!(matches!(parse("Map[]").kind, ExprKind::Map(m) if m.is_empty()));
    let ExprKind::Range { end, .. } = parse("1..").kind else {
        panic!("expected open range");
    };
    assert!(end.is_none());
}
