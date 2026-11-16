//! Features de la fase L3: hover, definición, completion y símbolos.

use std::fmt::Write as _;

use pengu_hir::{DefKind, HirCrate, ModuleId};

use crate::analysis::Analysis;
use crate::docs::Document;
use crate::index::{Entry, Index};
use crate::json::Value;
use crate::position::{Encoding, Position, Range};
use crate::uri::Uri;

/// Palabras clave y constructos del lenguaje, para completion.
const KEYWORDS: &[&str] = &[
    "bind",
    "morph",
    "if",
    "then",
    "else",
    "elseif",
    "match",
    "when",
    "while",
    "do",
    "for",
    "in",
    "loop",
    "break",
    "continue",
    "return",
    "rune",
    "enchanting",
    "essence",
    "pact",
    "ritual",
    "scroll",
    "summon",
    "unveil",
    "sigil",
    "relic",
    "foreign",
    "curse",
    "grimoire",
    "textus",
    "own",
    "mut",
    "Self",
    "true",
    "false",
    "none",
];

/// Identificador que contiene la posición.
#[must_use]
pub fn word_at(text: &str, offset: u32) -> Option<(String, u32, u32)> {
    let offset = usize::try_from(offset).ok()?;
    if offset > text.len() {
        return None;
    }
    let bytes = text.as_bytes();
    let is_word = |byte: u8| byte.is_ascii_alphanumeric() || byte == b'_';
    let mut start = offset;
    while start > 0 && is_word(bytes[start - 1]) {
        start -= 1;
    }
    let mut end = offset;
    while end < bytes.len() && is_word(bytes[end]) {
        end += 1;
    }
    if start == end {
        return None;
    }
    let word = text.get(start..end)?;
    Some((
        word.to_owned(),
        u32::try_from(start).ok()?,
        u32::try_from(end).ok()?,
    ))
}

fn uri_for(document: &Document, file: pengu_span::FileId) -> Option<Uri> {
    if file == document.file_id() {
        return Some(document.uri().clone());
    }
    let index = pengu_std::file_index(file)?;
    let files = pengu_std::files();
    files.get(index).map(|file| Uri::std_file(file.name))
}

#[must_use]
pub fn location(
    document: &Document,
    file: pengu_span::FileId,
    span: pengu_span::Span,
) -> Option<Value> {
    let uri = uri_for(document, file)?;
    let range = if file == document.file_id() {
        crate::diag::span_range(document, span, Encoding::Utf16)?
    } else {
        crate::position::Range::new(
            crate::position::Position {
                line: 0,
                character: 0,
            },
            crate::position::Position {
                line: 0,
                character: 0,
            },
        )
    };
    Some(Value::object([
        ("uri", Value::from(uri.as_str())),
        ("range", range.to_json()),
    ]))
}

/// Hover: firma de la definición bajo el cursor, su tamaño y el tipo de la
/// expresión.
#[must_use]
pub fn hover(
    document: &Document,
    analysis: &Analysis,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let krate = analysis.krate.as_ref();
    let mut contents: Option<String> = None;
    let mut range: Option<Range> = None;
    let mut size: Option<String> = None;
    if let Some((word, start, end)) = word_at(document.text(), offset) {
        if let Some(entry) = index.lookup(&word).first() {
            contents = Some(entry.detail.clone());
            range = crate::diag::span_range(
                document,
                pengu_span::Span::new(document.file_id(), start, end),
                encoding,
            );
            if let Some(krate) = krate {
                size = size_for_entry(entry, krate);
            }
        }
    }
    if contents.is_none() {
        if let Some(entry) = index.containing(document.file_id(), offset) {
            contents = Some(entry.detail.clone());
            range = crate::diag::span_range(document, entry.span, encoding);
        }
    }
    if contents.is_none() {
        if let Some(check) = &analysis.check {
            let mut best: Option<(u32, &pengu_types::Ty)> = None;
            for (span, ty) in &check.types {
                if span.file == document.file_id() && span.start <= offset && offset < span.end {
                    let width = span.end - span.start;
                    if best.is_none_or(|(current, _)| width < current) {
                        best = Some((width, ty));
                    }
                }
            }
            if let Some((_, ty)) = best {
                size = krate.and_then(|krate| crate::sizes::describe(ty, krate));
                contents = Some(format!("tipo: `{ty}`"));
            }
        }
    }
    let mut contents = contents?;
    if let Some(size) = size {
        let _ = write!(contents, "\n\ntamaño: {size}");
    }
    let mut hover = vec![(
        "contents".to_owned(),
        Value::object([
            ("kind", Value::from("markdown")),
            ("value", Value::from(format!("```pengu\n{contents}\n```"))),
        ]),
    )];
    if let Some(range) = range {
        hover.push(("range".to_owned(), range.to_json()));
    }
    Some(Value::object(hover))
}

fn size_for_entry(entry: &Entry, krate: &pengu_hir::HirCrate) -> Option<String> {
    use pengu_hir::DefKind;
    match entry.kind {
        DefKind::Type => {
            if krate.adt(entry.def).is_some() {
                crate::sizes::describe_adt(entry.def, krate)
            } else {
                None
            }
        }
        DefKind::Function => crate::sizes::footprint(entry.def, krate),
        DefKind::Const | DefKind::Static => {
            let constant = krate.consts.get(&entry.def)?;
            let ty = crate::sizes::typed(&constant.ty, krate)?;
            crate::sizes::describe(&ty, krate)
        }
        _ => None,
    }
}

/// Definición: ubicación de la definición bajo el cursor.
#[must_use]
pub fn definition(
    document: &Document,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Option<Value> {
    let offset = document.offset(position, encoding);
    let entry = word_at(document.text(), offset)
        .and_then(|(word, _, _)| index.lookup(&word).first().copied())
        .or_else(|| index.containing(document.file_id(), offset))?;
    location(document, entry.span.file, entry.span)
}

fn completion_item(entry: &Entry, sort: &str) -> Value {
    Value::object([
        ("label", Value::from(entry.name.as_str())),
        ("kind", Value::Int(entry.completion_kind())),
        ("detail", Value::from(entry.detail.as_str())),
        ("sortText", Value::from(sort)),
        ("filterText", Value::from(entry.name.as_str())),
    ])
}

fn keyword_item(keyword: &str) -> Value {
    Value::object([
        ("label", Value::from(keyword)),
        ("kind", Value::Int(14)),
        ("sortText", Value::from("3")),
    ])
}

fn module_item(label: &str, detail: String) -> Value {
    Value::object([
        ("label", Value::from(label)),
        ("kind", Value::Int(9)),
        ("detail", Value::from(detail)),
        ("sortText", Value::from("2")),
        ("filterText", Value::from(label)),
    ])
}

/// Resto de la línea si empieza por `summon` como palabra completa.
fn summon_context(line: &str) -> Option<String> {
    let rest = line.strip_prefix("summon")?;
    if rest.starts_with(|character: char| character.is_ascii_alphanumeric() || character == '_') {
        return None;
    }
    Some(rest.trim_start().to_owned())
}

/// Ruta escrita antes de `::` y prefijo del último segmento.
fn double_colon_context(line: &str) -> Option<(Vec<String>, String)> {
    let separator = line.rfind("::")?;
    let tail = &line[separator + 2..];
    if !tail
        .chars()
        .all(|character| character.is_alphanumeric() || character == '_')
    {
        return None;
    }
    let mut start = separator;
    for (position, character) in line[..separator].char_indices().rev() {
        if character.is_alphanumeric() || character == '_' || character == ':' {
            start = position;
        } else {
            break;
        }
    }
    let path = &line[start..separator];
    if path.is_empty() {
        return None;
    }
    let segments: Vec<String> = path
        .split("::")
        .filter(|segment| !segment.is_empty())
        .map(str::to_owned)
        .collect();
    if segments.is_empty() {
        return None;
    }
    Some((segments, tail.to_owned()))
}

fn child_module(krate: &HirCrate, parent: ModuleId, name: &str) -> Option<ModuleId> {
    let module = krate.module(parent);
    for item in &module.items {
        let def = krate.def(*item);
        if def.kind == DefKind::Module && def.name == name {
            return krate
                .modules
                .iter()
                .find(|module| module.def == Some(def.id))
                .map(|module| module.id);
        }
    }
    None
}

fn resolve_module(krate: &HirCrate, segments: &[String]) -> Option<ModuleId> {
    let mut current = krate.root;
    for segment in segments {
        current = child_module(krate, current, segment)?;
    }
    Some(current)
}

/// Resuelve un módulo desde la raíz o, si no existe, dentro de `std`.
fn resolve_module_any(krate: &HirCrate, segments: &[String]) -> Option<ModuleId> {
    if let Some(module) = resolve_module(krate, segments) {
        return Some(module);
    }
    let mut path = vec!["std".to_owned()];
    path.extend_from_slice(segments);
    resolve_module(krate, &path)
}

/// Módulos del proyecto y de la biblioteca estándar.
fn module_list(krate: &HirCrate, filter: &str) -> Vec<Value> {
    let mut items = Vec::new();
    let root = krate.module(krate.root);
    for item in &root.items {
        let def = krate.def(*item);
        if def.kind != DefKind::Module {
            continue;
        }
        if def.name == "std" {
            if let Some(std) = child_module(krate, krate.root, "std") {
                for inner in &krate.module(std).items {
                    let inner_def = krate.def(*inner);
                    if inner_def.kind != DefKind::Module {
                        continue;
                    }
                    let label = format!("std::{}", inner_def.name);
                    if label.starts_with(filter) {
                        items.push(module_item(
                            &label,
                            "módulo de la biblioteca estándar".to_owned(),
                        ));
                    }
                }
            }
            continue;
        }
        if def.name.starts_with(filter) {
            items.push(module_item(&def.name, "módulo del proyecto".to_owned()));
        }
    }
    items
}

/// Módulos de la biblioteca estándar por nombre, sin necesidad de HIR.
///
/// Sirve para completar mientras el documento aún no compila (por ejemplo al
/// escribir `summon ` a medias), que es justo cuando más falta hace.
fn std_module_items(filter: &str) -> Vec<Value> {
    let mut items = Vec::new();
    for file in pengu_std::files() {
        let label = format!("std::{}", file.name);
        if label.starts_with(filter) {
            items.push(module_item(
                &label,
                "módulo de la biblioteca estándar".to_owned(),
            ));
        }
    }
    items
}

/// Items (funciones, tipos, constantes y submódulos) de un módulo.
fn module_items(krate: &HirCrate, index: &Index, segments: &[String], filter: &str) -> Vec<Value> {
    let Some(module) = resolve_module_any(krate, segments) else {
        return Vec::new();
    };
    let mut items = Vec::new();
    for item in &krate.module(module).items {
        let def = krate.def(*item);
        if matches!(def.kind, DefKind::Local | DefKind::Generic) {
            continue;
        }
        if !def.name.starts_with(filter) {
            continue;
        }
        match index.lookup_def(def.id) {
            Some(entry) => items.push(completion_item(entry, "1")),
            None => items.push(module_item(&def.name, String::new())),
        }
    }
    items
}

fn completion_response(items: Vec<Value>) -> Value {
    let mut items = items;
    items.truncate(500);
    Value::object([
        ("isIncomplete", Value::Bool(false)),
        ("items", Value::Array(items)),
    ])
}

/// Completion por contexto: módulos tras `summon`, miembros tras `mod::`,
/// métodos tras `.`, y palabras clave y símbolos del archivo en el resto.
#[must_use]
pub fn completion(
    document: &Document,
    analysis: &Analysis,
    index: &Index,
    position: Position,
    encoding: Encoding,
) -> Value {
    let offset = usize::try_from(document.offset(position, encoding)).unwrap_or(0);
    let text = document.text();
    let offset = offset.min(text.len());
    let line_start = text
        .get(..offset)
        .and_then(|prefix| prefix.rfind('\n'))
        .map_or(0, |index| index + 1);
    let line = text
        .get(line_start..offset)
        .unwrap_or_default()
        .trim_start();
    let krate = analysis.krate.as_ref();

    // `summon std::` y `summon `: módulos.
    if let Some(rest) = summon_context(line) {
        if let Some(krate) = krate {
            if let Some(separator) = rest.rfind("::") {
                let path: Vec<String> = rest[..separator]
                    .split("::")
                    .filter(|segment| !segment.is_empty())
                    .map(str::to_owned)
                    .collect();
                let filter = &rest[separator + 2..];
                return completion_response(module_items(krate, index, &path, filter));
            }
            return completion_response(module_list(krate, &rest));
        }
        // Mientras se escribe, el documento suele tener un error de sintaxis y
        // no hay HIR: los módulos de la std se listan igual, por sus nombres.
        let filter = match rest.rfind("::") {
            Some(separator) => format!("std::{}", &rest[separator + 2..]),
            None => rest.clone(),
        };
        return completion_response(std_module_items(&filter));
    }

    // `modulo::item` en cualquier expresión.
    if let Some((path, filter)) = double_colon_context(line) {
        if let Some(krate) = krate {
            let items = module_items(krate, index, &path, &filter);
            if !items.is_empty() {
                return completion_response(items);
            }
        } else if path == ["std"] {
            return completion_response(std_module_items(&format!("std::{filter}")));
        }
    }

    // Métodos tras `.`.
    let receiver =
        line.trim_end_matches(|character: char| character.is_alphanumeric() || character == '_');
    if receiver.ends_with('.') {
        let mut items = Vec::new();
        for entry in index.entries() {
            let method = entry
                .signature
                .as_ref()
                .is_some_and(|signature| signature.receiver.is_some())
                || entry.detail.contains("(@");
            if method {
                items.push(completion_item(entry, "1"));
            }
        }
        return completion_response(items);
    }

    let mut items = Vec::new();
    for entry in index.in_file(document.file_id()) {
        items.push(completion_item(entry, "1"));
    }
    for keyword in KEYWORDS {
        items.push(keyword_item(keyword));
    }
    completion_response(items)
}

/// Símbolos del documento.
#[must_use]
pub fn document_symbols(document: &Document, index: &Index) -> Value {
    let mut symbols = Vec::new();
    for entry in index.in_file(document.file_id()) {
        let Some(range) = crate::diag::span_range(document, entry.span, Encoding::Utf16) else {
            continue;
        };
        symbols.push(Value::object([
            ("name", Value::from(entry.name.as_str())),
            ("detail", Value::from(entry.detail.as_str())),
            ("kind", Value::Int(entry.symbol_kind())),
            ("range", range.to_json()),
            ("selectionRange", range.to_json()),
        ]));
    }
    Value::Array(symbols)
}

/// `true` si el nombre es una palabra reservada del lenguaje.
#[must_use]
pub fn is_keyword(name: &str) -> bool {
    KEYWORDS.contains(&name)
}

#[cfg(test)]
mod tests {
    use super::*;
    use pengu_span::FileId;

    fn document(text: &str) -> Document {
        Document::new(
            Uri::parse("file:///tmp/features.pengu").expect("uri"),
            FileId::new(1),
            1,
            text.to_owned(),
            false,
        )
    }

    fn analyzed(text: &str) -> (Document, Analysis, Index) {
        let document = document(text);
        let analysis = crate::analysis::analyze(document.file_id(), document.text());
        let index = analysis
            .krate
            .as_ref()
            .map_or_else(Index::default, Index::build);
        (document, analysis, index)
    }

    #[test]
    fn encuentra_la_palabra_bajo_el_cursor() {
        let text = "hola = () -> Int\n    1\n";
        let (word, start, end) = word_at(text, 2).expect("palabra");
        assert_eq!(word, "hola");
        assert_eq!((start, end), (0, 4));
    }

    #[test]
    fn hover_muestra_la_firma() {
        let (document, analysis, index) = analyzed("suma = (a: Int, b: Int) -> Int\n    a + b\n");
        let hover = hover(
            &document,
            &analysis,
            &index,
            Position {
                line: 0,
                character: 1,
            },
            Encoding::Utf16,
        )
        .expect("hover");
        let value = hover
            .get("contents")
            .and_then(|contents| contents.get("value"))
            .and_then(Value::as_str)
            .expect("valor");
        assert!(value.contains("fn suma(Int, Int) -> Int"), "{value}");
    }

    #[test]
    fn definicion_apunta_al_archivo_y_rango() {
        let (document, _analysis, index) = analyzed("suma = (a: Int) -> Int\n    a\n");
        let definition = definition(
            &document,
            &index,
            Position {
                line: 0,
                character: 2,
            },
            Encoding::Utf16,
        )
        .expect("definición");
        assert_eq!(
            definition.get("uri").and_then(Value::as_str),
            Some("file:///tmp/features.pengu")
        );
    }

    #[test]
    fn completion_incluye_keywords_y_definiciones() {
        let (document, analysis, index) = analyzed("suma = (a: Int) -> Int\n    a\n");
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 1,
                character: 5,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("suma"))
        );
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("bind"))
        );
    }

    #[test]
    fn simbolos_del_documento_respetan_el_orden() {
        let (document, _analysis, index) =
            analyzed("primera = () -> Int\n    1\n\nsegunda = () -> Int\n    2\n");
        let symbols = document_symbols(&document, &index);
        let items = symbols.as_array().expect("símbolos");
        assert!(items.len() >= 2);
        assert_eq!(
            items[0].get("name").and_then(Value::as_str),
            Some("primera")
        );
        assert_eq!(
            items[1].get("name").and_then(Value::as_str),
            Some("segunda")
        );
    }
    #[test]
    fn completion_tras_summon_lista_modulos() {
        let (document, analysis, index) = analyzed("summon std::libra\n");
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 0,
                character: 17,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("libra")),
            "{items:?}"
        );
    }

    #[test]
    fn completion_tras_dos_puntos_lista_items_del_modulo() {
        let (document, analysis, index) =
            analyzed("summon std::libra\n\nleer = () -> Int\n    libra::parse(\"a = 1\")\n");
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 3,
                character: 11,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("parse")),
            "{items:?}"
        );
    }

    #[test]
    fn completion_tras_punto_ofrece_metodos() {
        let (document, analysis, index) = analyzed("texto = () -> Usize\n    \"hola\".len()\n");
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 1,
                character: 11,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert_ne!(items.len(), 0);
        assert!(
            items
                .iter()
                .all(|item| item.get("kind").and_then(Value::as_i64) == Some(3))
        );
    }

    #[test]
    fn completion_funciona_con_el_documento_a_medias() {
        // Al escribir `summon ` el documento todavía no compila; aun así hay
        // que listar los módulos de la std.
        let (document, analysis, index) = analyzed("summon \n");
        assert!(
            analysis.krate.is_none(),
            "el documento debería ser inválido"
        );
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 0,
                character: 7,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("std::libra")),
            "{items:?}"
        );
    }

    #[test]
    fn completion_tras_std_dos_puntos_sin_hir() {
        let (document, analysis, index) = analyzed("summon std::\n");
        let completion = completion(
            &document,
            &analysis,
            &index,
            Position {
                line: 0,
                character: 12,
            },
            Encoding::Utf16,
        );
        let items = completion
            .get("items")
            .and_then(Value::as_array)
            .expect("items");
        assert!(
            items
                .iter()
                .any(|item| item.get("label").and_then(Value::as_str) == Some("std::iason")),
            "{items:?}"
        );
    }
}
