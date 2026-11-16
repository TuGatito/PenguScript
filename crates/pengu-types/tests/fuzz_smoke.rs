//! Entradas pseudoaleatorias: parser, HIR y checker no deben paniquear.

use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

const ATOMS: &[&str] = &[
    "grimoire",
    "bind",
    "morph",
    "rune",
    "enchanting",
    "match",
    "when",
    "then",
    "else",
    "if",
    "unless",
    "for",
    "while",
    "loop",
    "return",
    "break",
    "continue",
    "print",
    "Int",
    "Str",
    "String",
    "Bool",
    "Float",
    "Vec",
    "Map",
    "Set",
    "Option",
    "Result",
    "x",
    "y",
    "foo",
    "Bar",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    ",",
    ":",
    "=",
    "->",
    "=>",
    "+",
    "-",
    "*",
    "/",
    "==",
    "!=",
    "<",
    ">",
    "and",
    "or",
    "not",
    "?",
    "@",
    "&",
    "\n",
    "    ",
    "--",
    "\"s\"",
    "1",
    "1.5",
    "true",
    "false",
    "none",
    "some",
    "ok",
    "err",
];

fn lcg(state: &mut u64) -> u64 {
    *state = state
        .wrapping_mul(6364136223846793005)
        .wrapping_add(1442695040888963407);
    *state
}

#[test]
fn malformed_inputs_do_not_panic() {
    let mut state = 0x5eed_u64;
    for _ in 0..300 {
        let len = (lcg(&mut state) % 80) as usize;
        let mut source = String::new();
        for _ in 0..len {
            let atom = ATOMS[(lcg(&mut state) as usize) % ATOMS.len()];
            source.push_str(atom);
        }
        let parsed = parse_program(FileId::new(0), &source);
        if let Some(program) = parsed.program {
            let lowered = lower_program(&program);
            let _ = check_crate(&lowered.krate);
        }
    }
}
