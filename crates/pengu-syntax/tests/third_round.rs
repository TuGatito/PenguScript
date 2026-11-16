use pengu_span::DUMMY_FILE;
use pengu_syntax::ast::ExprKind;
use pengu_syntax::{TokenKind, lex, parse_expression, parse_program};

fn clean(source: &str) -> bool {
    let parsed = parse_expression(DUMMY_FILE, source);
    if !parsed.is_clean() {
        eprintln!("source:\n{source}\ndiagnostics: {:#?}", parsed.diagnostics);
    }
    parsed.is_clean()
}

macro_rules! ok {
    ($name:ident, $src:expr) => {
        #[test]
        fn $name() {
            assert!(clean($src));
        }
    };
}

ok!(if_inline, "if true then 1 else 2");
ok!(unless_inline, "unless false then 1 else 2");
ok!(
    if_block,
    "if true then\n    1\nelseif false then\n    2\nelse\n    3\n"
);
ok!(
    if_block_comment_before_else,
    "if true then\n    1\n-- c\nelse\n    2\n"
);
ok!(match_inline, "match 1\n    when 1 then 2\n    else 3\n");
ok!(
    match_block,
    "match 1\n    when 1\n        2\n    else\n        3\n"
);
ok!(
    match_guard,
    "match 1\n    when x if x > 0 then x\n    else 0\n"
);
ok!(match_range, "match 1\n    when -1..=1 then 2\n    else 3\n");
ok!(do_block, "do\n    bind x = 1\n    x\n");
ok!(loop_break, "loop\n    break 1\n");
ok!(curse_block, "curse\n    1\n");
ok!(lambda_inline, "(x: Int) => x");
ok!(lambda_block, "(x: Int) =>\n    x\n");
ok!(vec_lit, "Vec[1, 2]");
ok!(map_lit, "Map[\"a\": 1]");
ok!(set_lit, "Set[\"a\"]");
ok!(map_brace, "{ \"a\": 1 }");
ok!(array_repeat, "[1; 2]");
ok!(tuple_one, "(1,)");
ok!(index_call, "foo[Int](1)");
ok!(ref_expr, "&x");
ok!(ref_mut_expr, "&mut x");
ok!(tuple_field, "pair.0");
ok!(try_expr, "x?");
ok!(cast_expr, "x as Int");
ok!(range_expr, "a..b");
ok!(range_open, "a..");
ok!(bool_expr, "true and not false");
ok!(some_expr, "some(1)");
ok!(ok_expr, "ok(1)");
ok!(err_expr, "err(\"e\")");
ok!(at_expr, "@");
ok!(self_expr, "Self");
ok!(while_do, "do\n    while true do\n        break\n");
ok!(for_do, "do\n    for x in 0..3 do\n        x\n");

fn bad(source: &str) -> bool {
    let parsed = parse_expression(DUMMY_FILE, source);
    !parsed.is_clean()
}

#[test]
fn inline_elseif_is_accepted() {
    assert!(!bad("if true then 1 elseif false then 2 else 3"));
}

#[test]
fn inline_if_with_block_else_is_rejected() {
    assert!(bad("if true then 1 else\n    2\n"));
}

#[test]
fn block_if_with_inline_else_is_rejected() {
    assert!(bad("if true then\n    1\nelse 2\n"));
}

#[test]
fn match_then_block_is_accepted() {
    let parsed = parse_expression(
        DUMMY_FILE,
        "match 1\n    when 1 then\n        2\n    else 3\n",
    );
    assert!(parsed.is_clean(), "{:?}", parsed.diagnostics);
    assert!(parsed.expr.is_some());
}

#[test]
fn match_without_then_needs_block() {
    assert!(bad("match 1\n    when 1 2\n    else 3\n"));
}

#[test]
fn indented_block_comment_then_code_emits_indent() {
    let lexed = lex(DUMMY_FILE, "if true\n    --[[ c ]] bind x = 1\n");
    let kinds: Vec<_> = lexed.tokens.iter().map(|t| t.kind).collect();
    assert!(kinds.contains(&TokenKind::Indent), "{kinds:#?}");
}

#[test]
fn block_comment_then_code_dedents() {
    let lexed = lex(DUMMY_FILE, "if true\n    x\n--[[ c ]] y\n");
    let kinds: Vec<_> = lexed.tokens.iter().map(|t| t.kind).collect();
    assert!(kinds.contains(&TokenKind::Dedent), "{kinds:#?}");
}

#[test]
fn comment_only_line_does_not_indent() {
    let lexed = lex(DUMMY_FILE, "if true\n    x\n        --[[ c ]]\n");
    let kinds: Vec<_> = lexed.tokens.iter().map(|t| t.kind).collect();
    assert_eq!(
        kinds
            .iter()
            .filter(|k| matches!(k, TokenKind::Indent))
            .count(),
        1,
        "{kinds:#?}"
    );
}

#[test]
fn parenthesized_type_without_comma_is_rejected() {
    assert!(bad("do\n    bind x: (Int) = 1\n    x\n"));
}

#[test]
fn continuation_skips_comment_only_lines() {
    assert!(clean(
        "do\n    bind x = 1 +\n        -- comentario\n        2\n    x\n"
    ));
    assert!(clean(
        "do\n    bind x = 1 +\n        --[[ comentario ]] 2\n    x\n"
    ));
}

#[test]
fn record_functional_update_parses() {
    let parsed = parse_expression(DUMMY_FILE, "Point(y: 5.0, ..p)");
    assert!(parsed.is_clean(), "{:?}", parsed.diagnostics);
    let expr = parsed.expr.expect("expression");
    match expr.kind {
        ExprKind::Record { base, .. } => assert!(base.is_some()),
        other => panic!("expected record, got {other:?}"),
    }
}

#[test]
fn prelude_variant_names_parse_in_enchanting() {
    let parsed = parse_program(
        DUMMY_FILE,
        "enchanting Maybe\n    some\n    none\n    ok\n    err\n",
    );
    assert!(parsed.is_clean(), "{:?}", parsed.diagnostics);
    assert!(parsed.program.is_some());
}

#[test]
fn bind_accepts_an_indented_block_rhs() {
    let parsed = parse_program(
        DUMMY_FILE,
        "grimoire\n    bind area =\n        bind side = 4.0\n        side * side\n",
    );
    assert!(parsed.is_clean(), "{:?}", parsed.diagnostics);
    assert!(parsed.program.is_some());
}
