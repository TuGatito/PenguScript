//! Pruebas de las garantías de §21 que no dependen de ownership.

use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn check(source: &str) -> Vec<&'static str> {
    let parsed = parse_program(FileId::new(0), source);
    if !parsed.diagnostics.is_empty() {
        return parsed.diagnostics.iter().map(|d| d.code).collect();
    }
    let lowered = lower_program(&parsed.program.expect("programa"));
    if !lowered.diagnostics.is_empty() {
        return lowered.diagnostics.iter().map(|d| d.code).collect();
    }
    check_crate(&lowered.krate)
        .diagnostics
        .iter()
        .map(|d| d.code)
        .collect()
}

#[test]
fn truthiness_is_rejected() {
    let codes = check("grimoire\n    if 1 then 2 else 3\n");
    assert!(
        codes.iter().any(|code| code.starts_with("PGS-E")),
        "{codes:?}"
    );
}

#[test]
fn module_globals_are_rejected() {
    let codes = check("bind x = 1\n");
    assert!(!codes.is_empty(), "bind de módulo debe fallar");
}

#[test]
fn null_is_rejected() {
    let codes = check("grimoire\n    bind x = null\n");
    assert!(!codes.is_empty(), "`null` no existe");
}

#[test]
fn macros_are_rejected() {
    let codes = check("grimoire\n    foo!()\n");
    assert!(!codes.is_empty(), "no hay macros de usuario");
}

#[test]
fn lifetime_annotations_are_rejected() {
    let codes = check("rune R<'a>\n    x: &'a Str\n");
    assert!(!codes.is_empty(), "no hay lifetimes escritos");
}

#[test]
fn non_exhaustive_match_is_rejected() {
    let codes = check(
        "enchanting E\n    A\n    B\n\ngrimoire\n    bind e = A\n    match e\n        when A then 1\n",
    );
    assert!(codes.contains(&"PGS-E9001"), "{codes:?}");
}

#[test]
fn dynamic_trait_is_rejected() {
    let codes = check("grimoire\n    bind x: dyn Show = 1\n");
    assert!(!codes.is_empty(), "`dyn` no existe");
}
