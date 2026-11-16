//! Type definition, implementaciones, acciones de código y jerarquía de
//! llamadas.
//!
//! La jerarquía de llamadas es textual dentro del archivo abierto: `PenguScript`
//! no tiene sobrecarga ni sombreado de funciones entre módulos, así que el
//! nombre resuelve de forma única con el índice. Se documenta el límite en
//! `docs/LSP.md`.

use pengu_hir::{DefKind, HirCrate};
use pengu_types::Ty;

use crate::analysis::Analysis;
use crate::docs::Document;
use crate::index::Index;
use crate::json::Value;
use crate::position::{Encoding, Position};

/// `textDocument/typeDefinition`: la definición del tipo de la expresión.
#[must_use]
pub fn type_definition(
    document: &Document,
    analysis: &Analysis,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let mut best: Option<(u32, &Ty)> = None;
    for (span, ty) in &analysis.check.as_ref()?.types {
        if span.file != document.file_id() || span.start > offset || offset >= span.end {
            continue;
        }
        let width = span.end - span.start;
        if best.is_none_or(|(current, _)| width < current) {
            best = Some((width, ty));
        }
    }
    let (_, ty) = best?;
    let Ty::Adt(def, _) = ty else {
        return None;
    };
    let entry = index.lookup_def(*def)?;
    crate::features::location(document, entry.span.file, entry.span)
}

/// `textDocument/implementation`: los `ritual … for Pact` de un pacto.
#[must_use]
pub fn implementation(
    document: &Document,
    krate: &HirCrate,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let entry = crate::extras::entry_at(document, index, position, encoding)?;
    let _ = offset;
    let mut locations = Vec::new();
    for implementation in &krate.impls {
        if implementation.pact != Some(entry.def) {
            continue;
        }
        let Some(def) = krate.defs.iter().find(|def| def.id == implementation.def) else {
            continue;
        };
        if let Some(location) = crate::features::location(document, def.span.file, def.span) {
            locations.push(location);
        }
    }
    if locations.is_empty() {
        return None;
    }
    Some(Value::Array(locations))
}

/// `textDocument/codeAction`: arreglos seguros que no cambian la intención.
#[must_use]
pub fn code_actions(document: &Document, analysis: &Analysis, params: &Value) -> Value {
    let diagnostics = params
        .get("context")
        .and_then(|context| context.get("diagnostics"))
        .and_then(Value::as_array)
        .map(<[Value]>::to_vec)
        .unwrap_or_default();
    let mut actions = Vec::new();
    for diagnostic in diagnostics {
        let code = diagnostic.get("code").and_then(Value::as_str).unwrap_or("");
        let message = diagnostic
            .get("message")
            .and_then(Value::as_str)
            .unwrap_or("");
        if code == "PGS-E1104" && message.contains("es privado") {
            let Some(line) = diagnostic
                .get("range")
                .and_then(|range| range.get("start"))
                .and_then(|start| start.get("line"))
                .and_then(Value::as_i64)
            else {
                continue;
            };
            let Some(text) = document
                .text()
                .lines()
                .nth(usize::try_from(line).unwrap_or(0))
            else {
                continue;
            };
            let indent = text.len() - text.trim_start().len();
            actions.push(Value::object([
                ("title", Value::from("Añadir `unveil` al campo")),
                ("kind", Value::from("quickfix")),
                ("isPreferred", Value::Bool(true)),
                (
                    "edit",
                    Value::object([(
                        "changes",
                        Value::object([(
                            document.uri().as_str(),
                            Value::Array(vec![Value::object([
                                (
                                    "range",
                                    Value::object([
                                        (
                                            "start",
                                            position_json(line, i64::try_from(indent).unwrap_or(0)),
                                        ),
                                        (
                                            "end",
                                            position_json(line, i64::try_from(indent).unwrap_or(0)),
                                        ),
                                    ]),
                                ),
                                ("newText", Value::from("unveil ")),
                            ])]),
                        )]),
                    )]),
                ),
            ]));
        }
    }
    let _ = analysis;
    Value::Array(actions)
}

fn position_json(line: i64, character: i64) -> Value {
    Value::object([
        ("line", Value::Int(line)),
        ("character", Value::Int(character)),
    ])
}

/// `callHierarchy/prepare`: elemento para la función bajo el cursor.
#[must_use]
pub fn prepare_call_hierarchy(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Value {
    let Ok(offset) = usize::try_from(document.offset(position, encoding)) else {
        return Value::Array(Vec::new());
    };
    let text = document.text();
    let mut start = offset.min(text.len());
    while start > 0 && is_word(text.as_bytes()[start - 1]) {
        start -= 1;
    }
    let mut end = offset.min(text.len());
    while end < text.len() && is_word(text.as_bytes()[end]) {
        end += 1;
    }
    let Some(word) = text.get(start..end) else {
        return Value::Array(Vec::new());
    };
    let entries = index.lookup(word);
    let Some(entry) = entries.iter().find(|entry| entry.kind == DefKind::Function) else {
        return Value::Array(Vec::new());
    };
    Value::Array(vec![call_item(document, entry, encoding)])
}

fn is_word(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

fn call_item(document: &Document, entry: &crate::index::Entry, encoding: Encoding) -> Value {
    let from = crate::diag::span_range(document, entry.span, encoding);
    let kind = 12;
    let detail = entry.detail.clone();
    Value::object([
        ("name", Value::from(entry.name.as_str())),
        ("kind", Value::Int(kind)),
        ("detail", Value::from(detail)),
        ("uri", Value::from(document.uri().as_str())),
        (
            "range",
            from.map_or(Value::Null, crate::position::Range::to_json),
        ),
        (
            "selectionRange",
            from.map_or(Value::Null, crate::position::Range::to_json),
        ),
    ])
}

/// `callHierarchy/incomingCalls`: llamadas a la función en el archivo.
#[must_use]
pub fn incoming_calls(
    document: &Document,
    index: &Index,
    item: &Value,
    encoding: Encoding,
) -> Value {
    let Some(name) = item.get("name").and_then(Value::as_str) else {
        return Value::Array(Vec::new());
    };
    let mut calls = Vec::new();
    for (start, end) in crate::refs::occurrences(document.text(), name) {
        let next = document.text().as_bytes().get(end as usize).copied();
        if next != Some(b'(') {
            continue;
        }
        let Some(caller) = caller_of(document, index, start) else {
            continue;
        };
        if caller.name == name {
            continue;
        }
        let Some(from) = crate::diag::span_range(document, caller.span, encoding) else {
            continue;
        };
        calls.push(Value::object([
            ("from", call_item(document, &caller, encoding)),
            ("fromRanges", Value::Array(vec![from.to_json()])),
        ]));
    }
    Value::Array(calls)
}

fn caller_of(document: &Document, index: &Index, offset: u32) -> Option<crate::index::Entry> {
    let entry = index.containing(document.file_id(), offset)?;
    if entry.kind != DefKind::Function {
        return None;
    }
    Some(entry.clone())
}

/// `callHierarchy/outgoingCalls`: llamadas que hace la función.
#[must_use]
pub fn outgoing_calls(
    document: &Document,
    index: &Index,
    item: &Value,
    encoding: Encoding,
) -> Value {
    let Some(name) = item.get("name").and_then(Value::as_str) else {
        return Value::Array(Vec::new());
    };
    let entries = index.lookup(name);
    let Some(entry) = entries.iter().find(|entry| entry.kind == DefKind::Function) else {
        return Value::Array(Vec::new());
    };
    let body = body_span(document, index, entry.span.end);
    let mut calls = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    let text = document.text();
    let slice = text
        .get(body.0 as usize..body.1 as usize)
        .unwrap_or_default();
    for entry in index.in_file(document.file_id()) {
        if entry.kind != DefKind::Function || entry.name == name {
            continue;
        }
        for (start, end) in crate::refs::occurrences(slice, &entry.name) {
            if slice.as_bytes().get(end as usize) != Some(&b'(') {
                continue;
            }
            if !seen.insert(entry.name.clone()) {
                continue;
            }
            let from = document.position(body.0 + start, encoding);
            let to = document.position(body.0 + end, encoding);
            calls.push(Value::object([
                ("to", call_item(document, entry, encoding)),
                (
                    "fromRanges",
                    Value::Array(vec![crate::position::Range::new(from, to).to_json()]),
                ),
            ]));
        }
    }
    Value::Array(calls)
}

/// Rango del cuerpo: desde el final de la firma hasta la siguiente definición
/// del mismo archivo.
fn body_span(document: &Document, index: &Index, after: u32) -> (u32, u32) {
    let text_len = u32::try_from(document.text().len()).unwrap_or(u32::MAX);
    let next = index
        .in_file(document.file_id())
        .into_iter()
        .map(|entry| entry.span.start)
        .filter(|start| *start > after)
        .min()
        .unwrap_or(text_len);
    (after, next)
}

/// `pengu size` necesita el nombre de la definición que contiene un offset.
#[must_use]
pub fn definition_at_offset(
    index: &Index,
    file: pengu_span::FileId,
    offset: u32,
) -> Option<crate::index::Entry> {
    index.containing(file, offset).cloned()
}
