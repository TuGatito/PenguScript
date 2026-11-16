use pengu_span::DUMMY_FILE;
use pengu_syntax::{parse_expression, parse_program};

#[test]
fn malformed_inputs_do_not_panic() {
    for source in [
        "",
        "(",
        "if",
        "if true then",
        "match x",
        "match x\n    when",
        "bind",
        "bind x =",
        "foo(",
        "[1,",
        "{1:",
        "do\n",
        "curse",
        "a as",
        "when 1",
        "Set[",
        "(x: ) =>",
        "a < b < c",
    ] {
        let parsed = parse_expression(DUMMY_FILE, source);
        assert!(
            parsed.expr.is_some() || !parsed.diagnostics.is_empty(),
            "no result for {source:?}"
        );
    }
}

#[test]
fn negative_literal_patterns_parse_cleanly() {
    let parsed = parse_expression(
        DUMMY_FILE,
        "match x\n    when -1 then 0\n    when -1.5 then 1\n    else 2",
    );
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
}

#[test]
fn semicolon_outside_array_is_rejected() {
    let parsed = parse_expression(DUMMY_FILE, "a; b");
    assert!(!parsed.diagnostics.is_empty());
}

#[test]
fn missing_function_return_type_uses_e7001() {
    let parsed = parse_program(DUMMY_FILE, "f = (x: Int)\n    x\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E7001"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn missing_parameter_type_uses_e7003() {
    let parsed = parse_program(DUMMY_FILE, "f = (x) -> Int\n    x\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E7003"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn sigil_without_type_uses_e1106() {
    let parsed = parse_program(DUMMY_FILE, "sigil X = 1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1106"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn map_entry_without_value_uses_e3105() {
    let parsed = parse_expression(DUMMY_FILE, "Map[1]");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E3105"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn item_inside_block_uses_e6003() {
    let parsed = parse_program(DUMMY_FILE, "grimoire\n    rune X\n        x: Int\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E6003"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn derive_on_function_uses_e8008() {
    let parsed = parse_program(DUMMY_FILE, "@@derive(Debug)\nf = () -> Int\n    1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E8008"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn global_binding_uses_e1101() {
    let parsed = parse_program(DUMMY_FILE, "bind x = 1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1101"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn multiple_superpacts_use_e1203() {
    let parsed = parse_program(
        DUMMY_FILE,
        "pact A\n    f = (@) -> Int\npact B\n    g = (@) -> Int\npact P: A, B\n    h = (@) -> Int\n",
    );
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1203"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn associated_sigil_in_pact_uses_e1204() {
    let parsed = parse_program(DUMMY_FILE, "pact P\n    sigil X: Int\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1204"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn associated_essence_in_pact_uses_e1307() {
    let parsed = parse_program(DUMMY_FILE, "pact P\n    essence Item\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1307"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn dyn_type_uses_e1208() {
    let parsed = parse_program(DUMMY_FILE, "f = (x: dyn Show) -> Int\n    1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1208"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn test_returning_int_uses_e1702() {
    let parsed = parse_program(DUMMY_FILE, "@@test\nt = () -> Int\n    1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1702"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn test_with_parameters_uses_e1701() {
    let parsed = parse_program(DUMMY_FILE, "@@test\nt = (x: Int) -> Unit\n    print(x)\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1701"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn where_clause_uses_e1306() {
    let parsed = parse_program(DUMMY_FILE, "f = () -> Int where T: Eq\n    1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1306"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn const_generic_uses_e1308() {
    let parsed = parse_program(DUMMY_FILE, "f = [const N: Int](x: Int) -> Int\n    x\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1308"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn unveil_scroll_uses_e2007() {
    let parsed = parse_program(DUMMY_FILE, "unveil scroll a\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2007"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn foreign_body_uses_e1601() {
    let parsed = parse_program(DUMMY_FILE, "foreign \"C\"\n    f = () -> Int\n        1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1601"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn should_panic_without_message_uses_e1703() {
    let parsed = parse_program(
        DUMMY_FILE,
        "@@test(should_panic)\nt = () -> Unit\n    return\n",
    );
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1703"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn empty_rune_uses_e3010() {
    let parsed = parse_program(DUMMY_FILE, "rune Empty\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E3010"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn exported_foreign_uses_e1606() {
    let parsed = parse_program(DUMMY_FILE, "unveil foreign \"C\"\n    f = () -> Unit\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E1606"),
        "{:?}",
        parsed.diagnostics
    );
}
