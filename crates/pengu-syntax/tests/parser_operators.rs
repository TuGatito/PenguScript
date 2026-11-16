use pengu_span::DUMMY_FILE;
use pengu_syntax::ast::{BinOp, ExprKind};
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
fn every_binary_operator_parses() {
    for (source, op) in [
        ("a + b", BinOp::Add),
        ("a - b", BinOp::Sub),
        ("a * b", BinOp::Mul),
        ("a / b", BinOp::Div),
        ("a % b", BinOp::Rem),
        ("a < b", BinOp::Lt),
        ("a <= b", BinOp::Le),
        ("a > b", BinOp::Gt),
        ("a >= b", BinOp::Ge),
        ("a == b", BinOp::Eq),
        ("a != b", BinOp::Ne),
        ("a is b", BinOp::Is),
        ("a isnt b", BinOp::Isnt),
        ("a in b", BinOp::In),
        ("a and b", BinOp::And),
        ("a or b", BinOp::Or),
    ] {
        assert!(
            matches!(parse(source), ExprKind::Binary { op: got, .. } if got == op),
            "{source}"
        );
    }
}

#[test]
fn precedence_table_is_respected() {
    let ExprKind::Binary {
        op: BinOp::Add,
        rhs,
        ..
    } = parse("a * b + c")
    else {
        panic!("expected add");
    };
    assert!(matches!(rhs.kind, ExprKind::Path(_)));
    let ExprKind::Binary {
        op: BinOp::Add,
        rhs,
        ..
    } = parse("a + b * c")
    else {
        panic!("expected add");
    };
    assert!(matches!(rhs.kind, ExprKind::Binary { op: BinOp::Mul, .. }));
    let ExprKind::Binary {
        op: BinOp::Mul,
        lhs,
        ..
    } = parse("a as Int * b")
    else {
        panic!("expected mul");
    };
    assert!(matches!(lhs.kind, ExprKind::Cast { .. }));
}

#[test]
fn range_literals_are_ranges() {
    assert!(matches!(
        parse("a..b"),
        ExprKind::Range {
            inclusive: false,
            ..
        }
    ));
    assert!(matches!(
        parse("a..=b"),
        ExprKind::Range {
            inclusive: true,
            ..
        }
    ));
}

#[test]
fn range_binds_looser_than_additive() {
    let ExprKind::Range { start, .. } = parse("a + b..c") else {
        panic!("expected range");
    };
    assert!(matches!(
        start.kind,
        ExprKind::Binary { op: BinOp::Add, .. }
    ));
}

#[test]
fn chained_comparison_is_left_associative() {
    let parsed = parse_expression(DUMMY_FILE, "a < b < c");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1408"),
        "{:?}",
        parsed.diagnostics
    );
    let ExprKind::Binary {
        op: BinOp::Lt, lhs, ..
    } = parsed.expr.expect("expression").kind
    else {
        panic!("expected comparison");
    };
    assert!(matches!(lhs.kind, ExprKind::Binary { op: BinOp::Lt, .. }));
}

#[test]
fn lambda_and_if_are_expressions() {
    assert!(matches!(parse("() => 1"), ExprKind::Lambda { .. }));
    assert!(matches!(parse("(x: Int) => x"), ExprKind::Lambda { .. }));
    assert!(matches!(
        parse("if ready then 1 else 0"),
        ExprKind::If { .. }
    ));
    assert!(matches!(
        parse("unless ready then 1 else 0"),
        ExprKind::If { unless: true, .. }
    ));
}

#[test]
fn not_binds_tighter_than_comparison() {
    let ExprKind::Binary {
        op: BinOp::Eq, lhs, ..
    } = parse("not a == b")
    else {
        panic!("expected comparison");
    };
    assert!(matches!(
        lhs.kind,
        ExprKind::Unary {
            op: pengu_syntax::ast::UnOp::Not,
            ..
        }
    ));
}
