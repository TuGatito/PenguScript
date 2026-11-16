//! Límites duros del frontend: tamaño, líneas y profundidad.

use pengu_span::FileId;
use pengu_syntax::{
    MAX_DEPTH, MAX_LINES, MAX_SOURCE_BYTES, parse_declaration_file, parse_expression, parse_program,
};

#[test]
fn source_larger_than_limit_is_reported_without_parsing() {
    let source = "a".repeat(MAX_SOURCE_BYTES + 1);
    let parsed = parse_program(FileId::new(0), &source);

    assert_eq!(parsed.diagnostics.len(), 1);
    assert_eq!(parsed.diagnostics[0].code, "PGS-E1901");
    assert!(parsed.tree.is_some());
}

#[test]
fn too_many_lines_are_reported() {
    let source = "a\n".repeat(MAX_LINES + 1);
    let parsed = parse_program(FileId::new(0), &source);

    assert_eq!(parsed.diagnostics.len(), 1);
    assert_eq!(parsed.diagnostics[0].code, "PGS-E1901");
}

#[test]
fn excessive_delimiter_depth_is_reported() {
    let source = "(".repeat(MAX_DEPTH + 1);
    let parsed = parse_expression(FileId::new(0), &source);

    assert_eq!(parsed.diagnostics.len(), 1);
    assert_eq!(parsed.diagnostics[0].code, "PGS-E1901");
    assert!(parsed.tree.is_some());
}

#[test]
fn excessive_indentation_depth_is_reported() {
    let mut source = String::new();
    for level in 0..=MAX_DEPTH + 1 {
        source.push_str(&"    ".repeat(level));
        source.push_str("scroll s\n");
    }
    let parsed = parse_program(FileId::new(0), &source);

    assert!(parsed.diagnostics.iter().any(|d| d.code == "PGS-E1901"));
}

#[test]
fn declaration_and_expression_paths_apply_limits() {
    let source = "a".repeat(MAX_SOURCE_BYTES + 1);
    assert_eq!(
        parse_declaration_file(FileId::new(0), &source).diagnostics[0].code,
        "PGS-E1901"
    );
    assert_eq!(
        parse_expression(FileId::new(0), &source).diagnostics[0].code,
        "PGS-E1901"
    );
}
