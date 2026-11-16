//! Fuzz determinista de F6. No usa `cargo-fuzz`: es un smoke test reproducible
//! que recorre 10M tokens léxicos y fuentes pseudoaleatorias del parser.

use pengu_span::FileId;
use pengu_syntax::{MAX_DEPTH, lex, parse_expression, parse_program};

fn next(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

fn random_source(seed: u64, pieces: usize) -> String {
    let atoms = [
        "a",
        "b",
        "x",
        "1",
        "0",
        "42",
        "1.5",
        "true",
        "none",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        "+",
        "-",
        "*",
        "/",
        "%",
        "==",
        "!=",
        "<",
        ">",
        "..",
        "..=",
        "::",
        ",",
        ".",
        "?",
        "if",
        "then",
        "else",
        "unless",
        "match",
        "when",
        "for",
        "while",
        "loop",
        "do",
        "return",
        "break",
        "continue",
        "bind",
        "morph",
        "rune",
        "enchanting",
        "scroll",
        "summon",
        "pact",
        "ritual",
        "essence",
        "foreign",
        "curse",
        "grimoire",
        "@",
        "@mut",
        "@own",
        "Self",
        "Vec",
        "Map",
        "Set",
        "Str",
        "&",
        "&mut",
        "\"s\"",
        "'c'",
        "b'P'",
        "r\"raw\"",
        "\n",
        "    ",
        "        ",
        "-- c\n",
        "--[[ b ]]\n",
        "--- d\n",
    ];
    let mut state = seed;
    let mut out = String::new();
    for _ in 0..pieces {
        let index = (next(&mut state) as usize) % atoms.len();
        out.push_str(atoms[index]);
        out.push(' ');
    }
    out
}

#[test]
fn ten_million_lexer_tokens_do_not_panic() {
    let file = FileId::new(0);
    let chunk = "a ".repeat(1_000_000);
    for _ in 0..10 {
        let lexed = lex(file, &chunk);
        assert!(lexed.diagnostics.is_empty());
        assert!(!lexed.tokens.is_empty());
    }
}

#[test]
fn random_sources_do_not_panic() {
    let file = FileId::new(1);
    for seed in 0..128u64 {
        let source = random_source(seed.wrapping_mul(0x9e37_79b9_7f4a_7c15), 200);
        let _ = parse_program(file, &source);
        let _ = parse_expression(file, &source);
    }
}

#[test]
fn extreme_nesting_is_rejected_without_panic() {
    let file = FileId::new(2);
    let source = format!("{}1{}", "(".repeat(MAX_DEPTH), ")".repeat(MAX_DEPTH));
    let parsed = parse_expression(file, &source);
    assert!(parsed.diagnostics.iter().any(|d| d.code == "PGS-E1901"));
}
