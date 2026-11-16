use pengu_hir::lower_program;
use pengu_lir::{LStmt, LTerm, lower_crate};
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn lower(source: &str) -> pengu_lir::LProgram {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    let mut lir = lower_crate(&lowered.krate, &types);
    lir.functions.retain(|function| {
        !lowered
            .krate
            .is_std_module(lowered.krate.def(function.def).module)
    });
    lir
}

#[test]
fn lowers_if_else_to_three_blocks() {
    let program = lower(
        "grimoire\n    morph x = 1\n    if x > 0 then\n        x = 2\n    else\n        x = 3\n    return\n",
    );
    let function = &program.functions[0];
    assert_eq!(function.blocks.len(), 4); // entry, then, else, join
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::If(_, _, _)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Return(None)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| b.stmts.iter().any(|s| matches!(s, LStmt::Assign(_, _, _))))
    );
}

#[test]
fn lowers_while_with_break_and_continue() {
    let program = lower(
        "grimoire\n    morph x = 0\n    while x < 3\n        x = x + 1\n        if x == 2 then\n            continue\n        if x == 3 then\n            break\n    return\n",
    );
    let function = &program.functions[0];
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::If(_, _, _)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Goto(_)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Return(None)))
    );
}

#[test]
fn lowers_loop_with_value_break() {
    let program = lower("grimoire\n    loop\n        break 7\n    return\n");
    let function = &program.functions[0];
    assert!(function.blocks.len() >= 3);
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Goto(_)))
    );
}

#[test]
fn lowers_return_value() {
    let program = lower("f = () -> Int\n    return 42\n");
    let function = program.functions.iter().find(|f| f.name == "f").expect("f");
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Return(Some(_))))
    );
}

#[test]
fn lowers_for_over_array() {
    let parsed = parse_program(
        FileId::new(0),
        "grimoire\n    for x in [1, 2]\n        print(x)\n",
    );
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    let types = check_crate(&lowered.krate);
    let mut lir = lower_crate(&lowered.krate, &types);
    assert!(
        lir.diagnostics.is_empty(),
        "for sobre array debe bajar: {:?}",
        lir.diagnostics
    );
    lir.functions.retain(|function| {
        !lowered
            .krate
            .is_std_module(lowered.krate.def(function.def).module)
    });
    let function = &lir.functions[0];
    assert!(function.blocks.len() >= 5);
}

#[test]
fn lowers_for_over_range() {
    let program = lower(
        "grimoire\n    morph sum = 0\n    for i in 0..3\n        sum = sum + i\n    return\n",
    );
    let function = &program.functions[0];
    assert!(function.blocks.len() >= 5);
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::If(_, _, _)))
    );
}

#[test]
fn lowers_match_statement() {
    let program = lower(
        "grimoire\n    morph x = 1\n    match x\n        when 1 then\n            x = 2\n        else\n            x = 3\n    return\n",
    );
    let function = &program.functions[0];
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::If(_, _, _)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::Return(None)))
    );
}

#[test]
fn lowers_if_expression_value() {
    let program = lower("grimoire\n    bind x = if true then 1 else 2\n    return\n");
    let function = &program.functions[0];
    assert!(
        function
            .blocks
            .iter()
            .any(|b| matches!(b.term, LTerm::If(_, _, _)))
    );
    assert!(
        function
            .blocks
            .iter()
            .any(|b| b.stmts.iter().any(|s| matches!(s, LStmt::Let(_, _, _))))
    );
}
