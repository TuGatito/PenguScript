//! Remapeo de diagnósticos de `rustc` a spans de PenguScript.
//!
//! Cargo emite una línea JSON por evento. Solo interesan las de
//! `reason = "compiler-message"` con `level = "error"`; su `spans[0]` trae el
//! archivo, la línea y la columna del Rust generado, y `rendered` el texto con
//! el que `rustc` explica el error.

use pengu_codegen::SourceMap;
use pengu_diag::Diagnostic;
use pengu_json::Value;
use pengu_span::{FileId, Span};

/// Convierte la salida de Cargo en diagnósticos PenguScript.
///
/// Si un error no tiene span en el sourcemap (código de la stdlib o del
/// runtime que no viene de una sentencia), se conserva el texto real y se
/// anota el archivo y la línea generados: nunca se descarta el mensaje.
#[must_use]
pub fn remap(output: &str, sourcemap: &SourceMap) -> Vec<Diagnostic> {
    let mut diagnostics: Vec<Diagnostic> = Vec::new();
    for line in output.lines() {
        let Some((message, span)) = parse_message(line.trim(), sourcemap) else {
            continue;
        };
        if diagnostics
            .iter()
            .any(|existing| existing.message == message && existing.primary == span.span)
        {
            continue;
        }
        diagnostics.push(Diagnostic::error("PGS-E2014", message, span.span).with_note(span.note));
    }
    diagnostics
}

struct Located {
    span: Span,
    note: String,
}

fn parse_message(line: &str, sourcemap: &SourceMap) -> Option<(String, Located)> {
    if !line.starts_with('{') {
        return None;
    }
    let value = pengu_json::parse(line).ok()?;
    if value.get("reason").and_then(Value::as_str) != Some("compiler-message") {
        return None;
    }
    let message = value.get("message")?;
    if message.get("level").and_then(Value::as_str) != Some("error") {
        return None;
    }
    let text = message
        .get("message")
        .and_then(Value::as_str)
        .unwrap_or("error del backend Rust");
    let code = message
        .get("code")
        .and_then(|code| code.get("code"))
        .and_then(Value::as_str);
    let headline = code.map_or_else(|| text.to_owned(), |code| format!("{code}: {text}"));

    let span_json = message
        .get("spans")
        .and_then(Value::as_array)
        .and_then(|spans| spans.first());
    let generated = span_json.map(|span| {
        let file = span
            .get("file_name")
            .and_then(Value::as_str)
            .unwrap_or("src/main.rs");
        let line = span.get("line_start").and_then(Value::as_i64).unwrap_or(0);
        let column = span
            .get("column_start")
            .and_then(Value::as_i64)
            .unwrap_or(0);
        (file.to_owned(), line, column)
    });
    let rendered = message.get("rendered").and_then(Value::as_str);
    let note = match &generated {
        Some((file, line, column)) => format!("generado en `{file}:{line}:{column}`"),
        None => "sin ubicación en el código generado".to_owned(),
    };
    let note = match rendered {
        Some(rendered) => format!("{note}\n{}", rendered.trim_end()),
        None => note,
    };
    let line = generated.as_ref().map_or(0, |(_, line, _)| *line);
    let span = sourcemap
        .lookup(u32::try_from(line).unwrap_or(0))
        .unwrap_or_else(|| Span::empty(FileId::new(0), 0));
    Some((headline, Located { span, note }))
}
