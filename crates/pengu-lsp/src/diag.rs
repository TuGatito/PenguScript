//! Conversión de diagnósticos del compilador al formato LSP.

use crate::docs::Document;
use crate::json::Value;
use crate::position::{Encoding, Position, Range};
use pengu_diag::{Diagnostic, Severity};

/// Rango LSP de un span dentro de `document`.
///
/// Devuelve `None` si el span pertenece a otro archivo.
#[must_use]
pub fn span_range(
    document: &Document,
    span: pengu_span::Span,
    encoding: Encoding,
) -> Option<Range> {
    if span.file != document.file_id() {
        return None;
    }
    let start = document.position(span.start, encoding);
    let end = document.position(span.end, encoding);
    Some(Range::new(
        Position {
            line: start.line,
            character: start.character,
        },
        Position {
            line: end.line,
            character: end.character,
        },
    ))
}

fn severity_code(severity: Severity) -> i64 {
    match severity {
        Severity::Error => 1,
        Severity::Warning => 2,
        Severity::Note => 3,
        Severity::Help => 4,
    }
}

fn message(diagnostic: &Diagnostic) -> String {
    let mut text = diagnostic.message.clone();
    for note in &diagnostic.notes {
        text.push('\n');
        text.push_str(note);
    }
    if let Some(help) = &diagnostic.help {
        text.push_str("\nayuda: ");
        text.push_str(help);
    }
    text
}

/// Convierte un diagnóstico a la forma que espera `textDocument/publishDiagnostics`.
///
/// Devuelve `None` si el diagnóstico no está en `document`.
#[must_use]
pub fn to_lsp(document: &Document, diagnostic: &Diagnostic, encoding: Encoding) -> Option<Value> {
    let range = span_range(document, diagnostic.primary, encoding)?;
    let mut fields = vec![
        ("range".to_owned(), range.to_json()),
        (
            "severity".to_owned(),
            Value::Int(severity_code(diagnostic.severity)),
        ),
        ("code".to_owned(), Value::from(diagnostic.code)),
        ("source".to_owned(), Value::from("pengu")),
        ("message".to_owned(), Value::from(message(diagnostic))),
    ];

    let mut related = Vec::new();
    for label in &diagnostic.labels {
        let Some(label_range) = span_range(document, label.span, encoding) else {
            continue;
        };
        let location = Value::object([
            ("uri", Value::from(document.uri().as_str())),
            ("range", label_range.to_json()),
        ]);
        let item = Value::object([
            ("location", location),
            (
                "message",
                Value::from(label.message.clone().unwrap_or_default()),
            ),
        ]);
        related.push(item);
    }
    if !related.is_empty() {
        fields.push(("relatedInformation".to_owned(), Value::Array(related)));
    }
    Some(Value::object(fields))
}

#[cfg(test)]
mod tests {
    use super::*;
    use pengu_span::{FileId, Span};

    #[test]
    fn convierte_un_diagnostico_del_mismo_archivo() {
        let document = Document::new(
            crate::uri::Uri::parse("file:///tmp/a.pengu").expect("uri"),
            FileId::new(1),
            1,
            "uno\ndos\n".to_owned(),
            false,
        );
        let diagnostic = Diagnostic::error("PGS-E1001", "algo", Span::new(FileId::new(1), 4, 7));
        let value = to_lsp(&document, &diagnostic, Encoding::Utf16).expect("lsp");
        let object = value.as_object().expect("objeto");
        assert_eq!(
            object.get("code").and_then(Value::as_str),
            Some("PGS-E1001")
        );
        assert_eq!(object.get("severity").and_then(Value::as_i64), Some(1));
        let range = object
            .get("range")
            .and_then(Value::as_object)
            .expect("range");
        let start = range
            .get("start")
            .and_then(Value::as_object)
            .expect("start");
        assert_eq!(start.get("line").and_then(Value::as_i64), Some(1));
    }

    #[test]
    fn ignora_diagnosticos_de_otro_archivo() {
        let document = Document::new(
            crate::uri::Uri::parse("file:///tmp/a.pengu").expect("uri"),
            FileId::new(1),
            1,
            "uno\n".to_owned(),
            false,
        );
        let diagnostic = Diagnostic::error("PGS-E1001", "algo", Span::new(FileId::new(2), 0, 1));
        assert!(to_lsp(&document, &diagnostic, Encoding::Utf16).is_none());
    }
}
