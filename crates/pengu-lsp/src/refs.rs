//! Referencias, resaltado y renombrado.
//!
//! La resolución del compilador es por nombre dentro de un archivo: el índice
//! guarda una entrada por definición y aquí se cruzan las apariciones textuales
//! del mismo identificador. Renombrar exige que el identificador no sea de la
//! biblioteca estándar (esos documentos son de solo lectura).

use crate::docs::Document;
use crate::index::Index;
use crate::json::Value;
use crate::position::{Encoding, Position, Range};
use crate::uri::Uri;

/// Nombre bajo el cursor, sus apariciones y si está declarado en el archivo.
type Occurrences = (String, Vec<(u32, u32)>, bool);

/// Apariciones de un identificador en un texto, como `(inicio, fin)`.
#[must_use]
pub fn occurrences(text: &str, name: &str) -> Vec<(u32, u32)> {
    let is_word = |byte: u8| byte.is_ascii_alphanumeric() || byte == b'_';
    let bytes = text.as_bytes();
    let needle = name.as_bytes();
    let mut found = Vec::new();
    let mut index = 0;
    while let Some(offset) = text[index..].find(name) {
        let start = index + offset;
        let end = start + needle.len();
        let before_ok = start == 0 || !is_word(bytes[start - 1]);
        let after_ok = end >= bytes.len() || !is_word(bytes[end]);
        if before_ok && after_ok {
            found.push((
                u32::try_from(start).unwrap_or(u32::MAX),
                u32::try_from(end).unwrap_or(u32::MAX),
            ));
        }
        index = end;
    }
    found
}

fn target(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Occurrences> {
    let offset = document.offset(position, encoding);
    let (word, _, _) = crate::features::word_at(document.text(), offset)?;
    let declared = index
        .lookup(&word)
        .iter()
        .any(|entry| entry.span.file == document.file_id());
    let spans = occurrences(document.text(), &word);
    Some((word, spans, declared))
}

fn range(document: &Document, start: u32, end: u32, encoding: Encoding) -> Option<Range> {
    crate::diag::span_range(
        document,
        pengu_span::Span::new(document.file_id(), start, end),
        encoding,
    )
}

/// `textDocument/references`.
#[must_use]
pub fn references(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
    include_declaration: bool,
) -> Option<Value> {
    let (word, spans, _) = target(document, index, position, encoding)?;
    let declared = index
        .lookup(&word)
        .iter()
        .filter(|entry| entry.span.file == document.file_id())
        .map(|entry| entry.span)
        .collect::<Vec<_>>();
    let mut locations = Vec::new();
    for (start, end) in spans {
        let is_declaration = declared
            .iter()
            .any(|span| span.start == start && span.end == end);
        if is_declaration && !include_declaration {
            continue;
        }
        let Some(range) = range(document, start, end, encoding) else {
            continue;
        };
        locations.push(Value::object([
            ("uri", Value::from(document.uri().as_str())),
            ("range", range.to_json()),
        ]));
    }
    Some(Value::Array(locations))
}

/// `textDocument/documentHighlight`.
#[must_use]
pub fn highlights(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let (_, spans, _) = target(document, index, position, encoding)?;
    let mut highlights = Vec::new();
    for (start, end) in spans {
        let Some(range) = range(document, start, end, encoding) else {
            continue;
        };
        highlights.push(Value::object([("range", range.to_json())]));
    }
    Some(Value::Array(highlights))
}

/// `textDocument/prepareRename`: rango del identificador y su texto actual.
#[must_use]
pub fn prepare_rename(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let (word, start, end) = crate::features::word_at(document.text(), offset)?;
    if index
        .lookup(&word)
        .iter()
        .any(|entry| entry.span.file != document.file_id())
    {
        // Renombrar la biblioteca estándar no tiene sentido: es de solo lectura.
        return None;
    }
    let range = range(document, start, end, encoding)?;
    Some(Value::object([
        ("range", range.to_json()),
        ("placeholder", Value::from(word)),
    ]))
}

/// `textDocument/rename`.
#[must_use]
pub fn rename(
    document: &Document,
    index: &Index,
    position: Position,
    new_name: &str,
    encoding: Encoding,
) -> Option<Value> {
    if !is_identifier(new_name) {
        return None;
    }
    let offset = document.offset(position, encoding);
    let (word, _, _) = crate::features::word_at(document.text(), offset)?;
    if index
        .lookup(&word)
        .iter()
        .any(|entry| entry.span.file != document.file_id())
    {
        return None;
    }
    let mut edits = Vec::new();
    for (start, end) in occurrences(document.text(), &word) {
        let Some(range) = range(document, start, end, encoding) else {
            continue;
        };
        edits.push(Value::object([
            ("range", range.to_json()),
            ("newText", Value::from(new_name)),
        ]));
    }
    if edits.is_empty() {
        return None;
    }
    let mut changes = std::collections::BTreeMap::new();
    changes.insert(document.uri().as_str().to_owned(), Value::Array(edits));
    Some(Value::object([("changes", Value::Object(changes))]))
}

/// Identificador válido de `PenguScript` (ASCII, sin palabra reservada).
#[must_use]
pub fn is_identifier(name: &str) -> bool {
    let mut chars = name.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !(first.is_ascii_alphabetic() || first == '_') {
        return false;
    }
    if !chars.all(|ch| ch.is_ascii_alphanumeric() || ch == '_') {
        return false;
    }
    !crate::features::is_keyword(name) && !crate::index::is_type_name(name)
}

/// Ubicación de la URI del propio documento (por claridad de los llamadores).
#[must_use]
pub fn document_uri(document: &Document) -> &Uri {
    document.uri()
}
