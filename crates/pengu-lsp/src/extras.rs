//! Ayuda de firma, lentes de código, acciones y plegado: el resto de la
//! superficie de la Fase 7 que no necesita un grafo de llamadas.

use crate::docs::Document;
use crate::index::{Entry, Index};
use crate::json::Value;
use crate::position::{Encoding, Position, Range};

/// `textDocument/signatureHelp`: firma de la llamada que contiene el cursor.
#[must_use]
pub fn signature_help(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let text = document.text();
    let open = text[..offset as usize].rfind('(')?;
    // El nombre de la función está justo antes del paréntesis.
    let (name, _, _) = crate::features::word_at(text, u32::try_from(open).ok()?.saturating_sub(1))?;
    let entries = index.lookup(&name);
    let entry = entries.first()?;
    let signature = entry.signature.as_ref()?;
    let label = crate::render::signature_text(&name, signature);
    let mut active = 0i64;
    let mut depth = 0i32;
    for byte in text[open + 1..offset as usize].bytes() {
        match byte {
            b'(' | b'[' | b'{' => depth += 1,
            b')' | b']' | b'}' => depth -= 1,
            b',' if depth == 0 => active += 1,
            _ => {}
        }
    }
    let mut parameters = Vec::new();
    if signature.receiver.is_some() {
        parameters.push(Value::object([("label", Value::from("@"))]));
    }
    for param in &signature.params {
        parameters.push(Value::object([(
            "label",
            Value::from(crate::render::type_text(param)),
        )]));
    }
    Some(Value::object([
        (
            "signatures",
            Value::Array(vec![Value::object([
                ("label", Value::from(label)),
                ("parameters", Value::Array(parameters)),
            ])]),
        ),
        ("activeSignature", Value::Int(0)),
        ("activeParameter", Value::Int(active)),
    ]))
}

/// `textDocument/codeLens`: un lente por cada test del archivo.
#[must_use]
pub fn code_lens(document: &Document, index: &Index, encoding: Encoding) -> Value {
    let mut lenses = Vec::new();
    for entry in index.in_file(document.file_id()) {
        if entry.kind != pengu_hir::DefKind::Function || !entry.is_test {
            continue;
        }
        let Some(range) = crate::diag::span_range(document, entry.span, encoding) else {
            continue;
        };
        lenses.push(Value::object([
            ("range", range.to_json()),
            (
                "command",
                Value::object([
                    ("title", Value::from("ejecutar test")),
                    ("command", Value::from("pengu.runTest")),
                    (
                        "arguments",
                        Value::Array(vec![
                            Value::from(document.uri().as_str()),
                            Value::from(entry.name.as_str()),
                        ]),
                    ),
                ]),
            ),
        ]));
    }
    // Lente de ejecución sobre el bloque `grimoire`, como rust-analyzer con `main`.
    for (number, line) in document.text().lines().enumerate() {
        if !line.trim_start().starts_with("grimoire") {
            continue;
        }
        let number = u32::try_from(number).unwrap_or(u32::MAX);
        lenses.push(Value::object([
            (
                "range",
                Range {
                    start: Position {
                        line: number,
                        character: 0,
                    },
                    end: Position {
                        line: number,
                        character: u32::try_from(line.len()).unwrap_or(u32::MAX),
                    },
                }
                .to_json(),
            ),
            (
                "command",
                Value::object([
                    ("title", Value::from("▶ Ejecutar programa")),
                    ("command", Value::from("pengu.run")),
                    (
                        "arguments",
                        Value::Array(vec![Value::from(document.uri().as_str())]),
                    ),
                ]),
            ),
        ]));
    }
    Value::Array(lenses)
}

/// `textDocument/foldingRange`: bloques por indentación y comentarios seguidos.
#[must_use]
pub fn folding_ranges(document: &Document) -> Value {
    let lines = document.text().lines().collect::<Vec<_>>();
    let mut ranges = Vec::new();
    let mut comment_start: Option<u32> = None;
    let mut last_comment = 0u32;
    for (number, line) in lines.iter().enumerate() {
        let trimmed = line.trim_start();
        let line_number = u32::try_from(number).unwrap_or(u32::MAX);
        if trimmed.starts_with("--") {
            if comment_start.is_none() {
                comment_start = Some(line_number);
            }
            last_comment = line_number;
        } else if let Some(start) = comment_start.take() {
            if last_comment > start {
                ranges.push(folding(start, last_comment));
            }
        }
    }
    if let Some(start) = comment_start {
        if last_comment > start {
            ranges.push(folding(start, last_comment));
        }
    }
    let mut stack: Vec<(usize, u32)> = Vec::new();
    for (number, line) in lines.iter().enumerate() {
        if line.trim().is_empty() || line.trim_start().starts_with("--") {
            continue;
        }
        let indent = line.len() - line.trim_start().len();
        let line_number = u32::try_from(number).unwrap_or(u32::MAX);
        while let Some((current, start)) = stack.last().copied() {
            if current < indent {
                break;
            }
            stack.pop();
            if line_number > start + 1 {
                ranges.push(folding(start, line_number - 1));
            }
        }
        if !line.trim_end().ends_with("then") {
            stack.push((indent, line_number));
        }
    }
    while let Some((_, start)) = stack.pop() {
        let end = u32::try_from(lines.len().saturating_sub(1)).unwrap_or(u32::MAX);
        if end > start + 1 {
            ranges.push(folding(start, end));
        }
    }
    Value::Array(ranges)
}

fn folding(start: u32, end: u32) -> Value {
    Value::object([
        ("startLine", Value::Int(i64::from(start))),
        ("endLine", Value::Int(i64::from(end))),
    ])
}

/// `textDocument/selectionRange`: línea, bloque y archivo.
#[must_use]
pub fn selection_ranges(document: &Document, positions: &[Position], encoding: Encoding) -> Value {
    let lines = document.text().lines().collect::<Vec<_>>();
    let line_len = |line: u32| -> u32 {
        lines.get(line as usize).map_or(0, |text| {
            u32::try_from(text.chars().count()).unwrap_or(u32::MAX)
        })
    };
    let mut result = Vec::new();
    for position in positions {
        let line_range = Range::new(
            Position {
                line: position.line,
                character: 0,
            },
            Position {
                line: position.line,
                character: line_len(position.line),
            },
        );
        let mut node = Value::object([
            ("range", line_range.to_json()),
            ("selectionRange", line_range.to_json()),
        ]);
        if let Some(block) = enclosing_block(&lines, position.line) {
            let block_range = Range::new(
                Position {
                    line: block.0,
                    character: 0,
                },
                Position {
                    line: block.1,
                    character: line_len(block.1),
                },
            );
            node = Value::object([
                ("range", block_range.to_json()),
                ("selectionRange", block_range.to_json()),
                ("parent", node),
            ]);
        }
        let _ = encoding;
        result.push(node);
    }
    Value::Array(result)
}

/// Bloque que contiene la línea: la cabecera con menor indentación previa y su
/// última línea con indentación mayor.
fn enclosing_block(lines: &[&str], line: u32) -> Option<(u32, u32)> {
    let indent = |number: u32| -> Option<usize> {
        let text = lines.get(number as usize)?;
        if text.trim().is_empty() {
            return None;
        }
        Some(text.len() - text.trim_start().len())
    };
    let mut current = indent(line)?;
    let mut start = line;
    for number in (0..line).rev() {
        let Some(candidate) = indent(number) else {
            continue;
        };
        if candidate < current {
            current = candidate;
            start = number;
            break;
        }
    }
    if start == line {
        return None;
    }
    let mut end = line;
    for number in (line + 1)..u32::try_from(lines.len()).unwrap_or(u32::MAX) {
        match indent(number) {
            Some(candidate) if candidate <= current => break,
            Some(_) => end = number,
            None => {}
        }
    }
    Some((start, end))
}

/// `workspace/symbol`: símbolos de los documentos abiertos.
#[must_use]
pub fn workspace_symbols(documents: &[(Document, Index)], query: &str) -> Value {
    let needle = query.to_lowercase();
    let mut symbols = Vec::new();
    for (document, index) in documents {
        for entry in index.in_file(document.file_id()) {
            if entry.kind == pengu_hir::DefKind::Local {
                continue;
            }
            if !needle.is_empty() && !entry.name.to_lowercase().contains(&needle) {
                continue;
            }
            let Some(range) = crate::diag::span_range(document, entry.span, Encoding::Utf16) else {
                continue;
            };
            symbols.push(Value::object([
                ("name", Value::from(entry.name.as_str())),
                ("kind", Value::Int(entry.symbol_kind())),
                (
                    "location",
                    Value::object([
                        ("uri", Value::from(document.uri().as_str())),
                        ("range", range.to_json()),
                    ]),
                ),
            ]));
            if symbols.len() >= 200 {
                return Value::Array(symbols);
            }
        }
    }
    Value::Array(symbols)
}

/// Entrada `Entry` del índice para una posición: usada por varias features.
#[must_use]
pub fn entry_at(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Entry> {
    let offset = document.offset(position, encoding);
    let (word, _, _) = crate::features::word_at(document.text(), offset)?;
    index.lookup(&word).first().map(|entry| (*entry).clone())
}
