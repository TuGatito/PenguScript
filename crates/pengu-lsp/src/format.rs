//! Formateo para el LSP, delegado en `pengu-fmt`.
//!
//! Una sola implementación para el editor y la CLI: lo que `pengu fmt`
//! escribiría es exactamente lo que devuelve `textDocument/formatting`.

use crate::docs::Document;
use crate::json::Value;

/// Texto formateado; si no se puede, se devuelve el original.
#[must_use]
pub fn formatted(text: &str) -> String {
    pengu_fmt::format_source(text).unwrap_or_else(|_| text.to_owned())
}

/// Ediciones para reemplazar el documento entero, si hace falta.
#[must_use]
pub fn formatting_edits(document: &Document) -> Value {
    let formatted = formatted(document.text());
    if formatted == document.text() {
        return Value::Array(Vec::new());
    }
    let end = document.position(
        u32::try_from(document.text().len()).unwrap_or(u32::MAX),
        crate::position::Encoding::Utf16,
    );
    let edit = Value::object([
        (
            "range",
            crate::position::Range::new(
                crate::position::Position {
                    line: 0,
                    character: 0,
                },
                end,
            )
            .to_json(),
        ),
        ("newText", Value::from(formatted)),
    ]);
    Value::Array(vec![edit])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::uri::Uri;
    use pengu_span::FileId;

    #[test]
    fn normaliza_espacios_finales_y_lineas_en_blanco() {
        let text = "f = () -> Int\n    1   \n\n\n";
        assert_eq!(formatted(text), "f = () -> Int\n    1\n");
    }

    #[test]
    fn los_tabuladores_no_se_formatean() {
        // El lexer rechaza tabuladores (`PGS-E1002`), así que no hay nada que
        // formatear: se devuelve el texto tal cual en vez de inventar sangría.
        let text = "f = () -> Int\n\t1\n";
        assert_eq!(formatted(text), text);
    }

    #[test]
    fn deja_el_texto_ya_formateado_igual() {
        let text = "f = () -> Int\n    1\n";
        assert_eq!(formatted(text), text);
    }

    #[test]
    fn devuelve_una_edicion_solo_si_cambia() {
        let document = Document::new(
            Uri::parse("file:///tmp/f.pengu").expect("uri"),
            FileId::new(1),
            1,
            "f = () -> Int\n    1   \n".to_owned(),
            false,
        );
        let edits = formatting_edits(&document);
        assert_eq!(edits.as_array().map(<[Value]>::len), Some(1));
        let already = Document::new(
            Uri::parse("file:///tmp/f.pengu").expect("uri"),
            FileId::new(1),
            1,
            "f = () -> Int\n    1\n".to_owned(),
            false,
        );
        assert_eq!(
            formatting_edits(&already).as_array().map(<[Value]>::len),
            Some(0)
        );
    }
}
