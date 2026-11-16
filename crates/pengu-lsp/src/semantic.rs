//! Semantic tokens: coloreado por significado sin depender del editor.
//!
//! Se recorre el texto una vez y se clasifica cada token con el índice del
//! compilador; es O(bytes) y no necesita el AST completo, así que funciona
//! incluso mientras el archivo no compila.

use crate::docs::Document;
use crate::index::Index;
use crate::json::Value;
use crate::position::Range;

/// Tipos de token, en el orden que declara la leyenda.
pub const TYPES: &[&str] = &[
    "namespace",
    "type",
    "function",
    "variable",
    "keyword",
    "string",
    "number",
    "comment",
    "operator",
];

const MODIFIERS: &[&str] = &["declaration", "readonly"];

const NAMESPACE: u32 = 0;
const TYPE: u32 = 1;
const FUNCTION: u32 = 2;
const VARIABLE: u32 = 3;
const KEYWORD: u32 = 4;
const STRING: u32 = 5;
const NUMBER: u32 = 6;
const COMMENT: u32 = 7;
const OPERATOR: u32 = 8;

/// Leyenda del servidor.
#[must_use]
pub fn legend() -> Value {
    Value::object([
        (
            "tokenTypes",
            Value::Array(TYPES.iter().map(|name| Value::from(*name)).collect()),
        ),
        (
            "tokenModifiers",
            Value::Array(MODIFIERS.iter().map(|name| Value::from(*name)).collect()),
        ),
    ])
}

struct Encoder<'a> {
    text: &'a str,
    data: Vec<u32>,
    line: u32,
    line_start: usize,
    previous_line: u32,
    previous_start: u32,
}

impl Encoder<'_> {
    fn push(&mut self, start: usize, end: usize, kind: u32, modifiers: u32) {
        let start_units = utf16_len(&self.text[self.line_start..start]);
        let length = utf16_len(&self.text[start..end]).max(1);
        self.data.push(self.line - self.previous_line);
        if self.line == self.previous_line {
            self.data.push(start_units - self.previous_start);
        } else {
            self.data.push(start_units);
        }
        self.data.push(length);
        self.data.push(kind);
        self.data.push(modifiers);
        self.previous_line = self.line;
        self.previous_start = start_units;
    }
}

/// Tokens del documento completo, ya codificados como enteros relativos.
#[must_use]
pub fn tokens(document: &Document, index: &Index) -> Value {
    tokens_in(document, index, None)
}

/// Tokens de un rango de líneas (o del documento si el rango es `None`).
#[must_use]
pub fn tokens_in(document: &Document, index: &Index, lines: Option<Range>) -> Value {
    let text = document.text();
    let mut encoder = Encoder {
        text,
        data: Vec::new(),
        line: 0,
        line_start: 0,
        previous_line: 0,
        previous_start: 0,
    };
    let mut cursor = 0usize;
    if let Some(range) = lines {
        // Los deltas son absolutos: se empieza en la primera línea del rango.
        encoder.line = range.start.line;
        encoder.previous_line = range.start.line;
        for _ in 0..range.start.line {
            match text[cursor..].find('\n') {
                Some(offset) => cursor += offset + 1,
                None => break,
            }
        }
        encoder.line_start = cursor;
    }
    let last_line = lines.map(|range| range.end.line);
    scan(&mut encoder, index, cursor, last_line);
    Value::Array(
        encoder
            .data
            .into_iter()
            .map(|value| Value::Int(i64::from(value)))
            .collect(),
    )
}

fn scan(encoder: &mut Encoder<'_>, index: &Index, from: usize, last_line: Option<u32>) {
    let text = encoder.text;
    let bytes = text.as_bytes();
    let mut cursor = from;
    while cursor < bytes.len() {
        if last_line.is_some_and(|end| encoder.line > end) {
            break;
        }
        if let Some(step) = scan_one(encoder, index, cursor) {
            cursor = step;
            continue;
        }
        cursor += 1;
    }
}

/// Reconoce el token que empieza en `cursor` y devuelve dónde sigue el escaneo.
fn scan_one(encoder: &mut Encoder<'_>, index: &Index, cursor: usize) -> Option<usize> {
    let text = encoder.text;
    let bytes = text.as_bytes();
    let byte = *bytes.get(cursor)?;
    if byte == b'\n' {
        encoder.line += 1;
        encoder.line_start = cursor + 1;
        return Some(cursor + 1);
    }
    if byte.is_ascii_whitespace() {
        return Some(cursor + 1);
    }
    if byte == b'-' && bytes.get(cursor + 1) == Some(&b'-') {
        let end = text[cursor..]
            .find('\n')
            .map_or(bytes.len(), |offset| cursor + offset);
        encoder.push(cursor, end, COMMENT, 0);
        return Some(end);
    }
    if byte == b'"' {
        let mut scan = cursor + 1;
        while scan < bytes.len() {
            match bytes[scan] {
                b'\\' => scan += 2,
                b'"' => {
                    scan += 1;
                    break;
                }
                b'\n' | b'\r' => break,
                _ => scan += 1,
            }
        }
        let end = scan.min(bytes.len());
        encoder.push(cursor, end, STRING, 0);
        return Some(end);
    }
    if byte.is_ascii_digit() {
        let mut scan = cursor;
        while scan < bytes.len() && (bytes[scan].is_ascii_alphanumeric() || bytes[scan] == b'.') {
            scan += 1;
        }
        encoder.push(cursor, scan, NUMBER, 0);
        return Some(scan);
    }
    if byte.is_ascii_alphabetic() || byte == b'_' || byte == b'@' {
        let mut scan = cursor;
        if byte == b'@' {
            scan += 1;
            if bytes.get(scan) == Some(&b'@') {
                scan += 1;
            }
        }
        while scan < bytes.len() && (bytes[scan].is_ascii_alphanumeric() || bytes[scan] == b'_') {
            scan += 1;
        }
        let (kind, modifiers) = classify(&text[cursor..scan], index);
        encoder.push(cursor, scan, kind, modifiers);
        return Some(scan);
    }
    if !byte.is_ascii() {
        // Carácter multibyte fuera de un identificador: token propio para no
        // cortar en medio de un `char` (los spans deben ser límites válidos).
        let width = text[cursor..].chars().next().map_or(1, char::len_utf8);
        encoder.push(cursor, cursor + width, OPERATOR, 0);
        return Some(cursor + width);
    }
    let mut scan = cursor + 1;
    while scan < bytes.len() && is_operator(bytes[scan]) {
        scan += 1;
    }
    encoder.push(cursor, scan, OPERATOR, 0);
    Some(scan)
}

fn classify(word: &str, index: &Index) -> (u32, u32) {
    let name = word.trim_start_matches('@');
    if crate::features::is_keyword(name) || name == "true" || name == "false" {
        return (KEYWORD, 1 << 1);
    }
    if crate::index::is_type_name(name) {
        return (TYPE, 0);
    }
    if let Some(entry) = index.lookup(name).first() {
        let modifiers = 1 << 1;
        return match entry.kind {
            pengu_hir::DefKind::Module => (NAMESPACE, modifiers),
            pengu_hir::DefKind::Type | pengu_hir::DefKind::Variant => (TYPE, modifiers),
            pengu_hir::DefKind::Function => (FUNCTION, modifiers),
            _ => (VARIABLE, modifiers),
        };
    }
    (VARIABLE, 0)
}

fn is_operator(byte: u8) -> bool {
    matches!(
        byte,
        b'+' | b'-'
            | b'*'
            | b'/'
            | b'%'
            | b'='
            | b'<'
            | b'>'
            | b'!'
            | b'&'
            | b'|'
            | b':'
            | b'.'
            | b','
            | b'('
            | b')'
            | b'['
            | b']'
            | b'{'
            | b'}'
    )
}

fn utf16_len(text: &str) -> u32 {
    text.chars()
        .map(|ch| u32::try_from(ch.len_utf16()).unwrap_or(1))
        .sum()
}
