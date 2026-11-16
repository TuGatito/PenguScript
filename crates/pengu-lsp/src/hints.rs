//! Inlay hints: el tipo y el tamaño de cada local, en la línea donde se declara.

use pengu_hir::HirCrate;
use pengu_types::Ty;

use crate::analysis::Analysis;
use crate::docs::Document;
use crate::json::Value;
use crate::position::{Encoding, Position, Range};

/// Hints de tipo para los locales del documento.
#[must_use]
pub fn inlay_hints(
    document: &Document,
    analysis: &Analysis,
    range: Range,
    encoding: Encoding,
) -> Value {
    let (Some(krate), Some(check)) = (analysis.krate.as_ref(), analysis.check.as_ref()) else {
        return Value::Array(Vec::new());
    };
    let mut hints = Vec::new();
    for body in &krate.bodies {
        let Some(locals) = check.locals.get(&body.id) else {
            continue;
        };
        for local in &body.locals {
            if Some(local.id) == body.self_local {
                continue;
            }
            let Some(ty) = locals.get(&local.id) else {
                continue;
            };
            if local.span.file != document.file_id() {
                continue;
            }
            // Si la declaración ya lleva anotación, el hint sería repetirla.
            let after = &document.text()[local.span.end as usize..];
            if after.trim_start().starts_with(':') {
                continue;
            }
            let position = document.position(local.span.end, encoding);
            if !within(position, range) {
                continue;
            }
            hints.push(Value::object([
                ("position", position.to_json()),
                ("label", Value::from(label(ty, krate))),
                ("kind", Value::Int(1)),
                ("paddingRight", Value::Bool(true)),
            ]));
        }
    }
    Value::Array(hints)
}

fn label(ty: &Ty, krate: &HirCrate) -> String {
    match crate::sizes::describe(ty, krate) {
        Some(size) => format!(": {ty} · {size}"),
        None => format!(": {ty}"),
    }
}

fn within(position: Position, range: Range) -> bool {
    let after_start = position.line > range.start.line
        || (position.line == range.start.line && position.character >= range.start.character);
    let before_end = position.line < range.end.line
        || (position.line == range.end.line && position.character <= range.end.character);
    after_start && before_end
}
