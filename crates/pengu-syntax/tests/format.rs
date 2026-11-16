//! Gate F: el CST debe reconstruir el fuente exacto.

use pengu_span::FileId;
use pengu_syntax::{format_declaration, format_source};

#[test]
fn format_reconstructs_program_text() {
    let source = "-- comentario\nrune Point\n    x: Int\n    y: Int\n\ngrimoire\n    bind p = Point(x: 1, y: 2)\n";
    let file = FileId::new(0);
    let formatted = format_source(file, source);
    assert_eq!(formatted.text, source);
    assert!(formatted.diagnostics.is_empty());
}

#[test]
fn format_reconstructs_declaration_text() {
    let source = "abi \"C\"\n\nrune FILE\n\nputs = (s: &CStr) -> Int\n";
    let file = FileId::new(1);
    let formatted = format_declaration(file, source);
    assert_eq!(formatted.text, source);
    assert!(formatted.diagnostics.is_empty());
}

#[test]
fn format_preserves_crlf_bom_and_interpolation() {
    let source = "\u{feff}bind name = \"pengu\"\nbind msg = \"hola #{name}\"\n";
    let file = FileId::new(2);
    let formatted = format_source(file, source);
    assert_eq!(formatted.text, source);
}
