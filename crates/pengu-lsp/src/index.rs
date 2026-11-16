//! Índice de definiciones para hover, completion, definición y símbolos.

use std::collections::BTreeMap;

use pengu_hir::{DefKind, HirCrate};
use pengu_span::{FileId, Span};

use crate::render;

/// Definición indexada.
#[derive(Clone, Debug)]
pub struct Entry {
    /// Nombre.
    pub name: String,
    /// Clase de definición.
    pub kind: DefKind,
    /// Span de la definición (nombre incluido).
    pub span: Span,
    /// Texto corto para hover/completion.
    pub detail: String,
    /// Definición del HIR a la que apunta.
    pub def: pengu_hir::DefId,
    /// Firma, si la definición es una función.
    pub signature: Option<pengu_hir::Signature>,
    /// `true` si la función lleva `@@test`.
    pub is_test: bool,
}

impl Entry {
    /// Etiqueta del `CompletionItemKind` de LSP.
    #[must_use]
    pub fn completion_kind(&self) -> i64 {
        match self.kind {
            DefKind::Function => 3,
            DefKind::Module => 9,
            DefKind::Const | DefKind::Static => 21,
            DefKind::Type | DefKind::Pact | DefKind::Impl => 22,
            DefKind::Variant => 20,
            DefKind::Field => 5,
            DefKind::Generic | DefKind::Local => 6,
        }
    }

    /// Etiqueta del `SymbolKind` de LSP.
    #[must_use]
    pub fn symbol_kind(&self) -> i64 {
        match self.kind {
            DefKind::Function => 12,
            DefKind::Module => 2,
            DefKind::Const | DefKind::Static => 14,
            DefKind::Type | DefKind::Pact | DefKind::Impl => 23,
            DefKind::Variant | DefKind::Field => 8,
            DefKind::Generic | DefKind::Local => 13,
        }
    }
}

/// Índice de definiciones del crate (incluida la stdlib).
#[derive(Debug, Default)]
pub struct Index {
    entries: Vec<Entry>,
    by_name: BTreeMap<String, Vec<usize>>,
}

impl Index {
    /// Construye el índice a partir del HIR.
    #[must_use]
    pub fn build(krate: &HirCrate) -> Self {
        let mut index = Self::default();
        for def in &krate.defs {
            if matches!(def.kind, DefKind::Local | DefKind::Generic) {
                continue;
            }
            let detail = detail_for(krate, def);
            index
                .by_name
                .entry(def.name.clone())
                .or_default()
                .push(index.entries.len());
            index.entries.push(Entry {
                name: def.name.clone(),
                kind: def.kind,
                span: def.span,
                signature: krate.signature(def.id).cloned(),
                is_test: krate.tests.contains_key(&def.id),
                def: def.id,
                detail,
            });
        }
        index
    }

    /// Entrada de una definición concreta.
    #[must_use]
    pub fn lookup_def(&self, def: pengu_hir::DefId) -> Option<&Entry> {
        self.entries.iter().find(|entry| entry.def == def)
    }

    /// Entradas con ese nombre.
    #[must_use]
    pub fn lookup(&self, name: &str) -> Vec<&Entry> {
        self.by_name
            .get(name)
            .map(|indices| indices.iter().map(|index| &self.entries[*index]).collect())
            .unwrap_or_default()
    }

    /// Entrada que contiene el desplazamiento (la más pequeña).
    #[must_use]
    pub fn containing(&self, file: FileId, offset: u32) -> Option<&Entry> {
        self.entries
            .iter()
            .filter(|entry| {
                entry.span.file == file && entry.span.start <= offset && offset < entry.span.end
            })
            .min_by_key(|entry| entry.span.end - entry.span.start)
    }

    /// Entradas de un archivo, ordenadas por posición.
    #[must_use]
    /// Todas las entradas del índice.
    pub fn entries(&self) -> &[Entry] {
        &self.entries
    }

    #[must_use]
    pub fn in_file(&self, file: FileId) -> Vec<&Entry> {
        let mut entries: Vec<&Entry> = self
            .entries
            .iter()
            .filter(|entry| entry.span.file == file)
            .collect();
        entries.sort_by_key(|entry| entry.span.start);
        entries
    }

    /// Número de entradas.
    #[must_use]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// `true` si está vacío.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

fn detail_for(krate: &HirCrate, def: &pengu_hir::Def) -> String {
    match def.kind {
        DefKind::Function => krate.signature(def.id).map_or_else(
            || format!("fn {}", def.name),
            |signature| render::signature_text(&def.name, signature),
        ),
        DefKind::Const | DefKind::Static => krate.consts.get(&def.id).map_or_else(
            || format!("sigil {}", def.name),
            |constant| format!("sigil {}: {}", def.name, render::type_text(&constant.ty)),
        ),
        DefKind::Module => format!("scroll {}", def.name),
        DefKind::Type => format!("tipo {}", def.name),
        DefKind::Pact => format!("pact {}", def.name),
        DefKind::Variant => format!("variante {}", def.name),
        DefKind::Field => format!("campo {}", def.name),
        DefKind::Impl | DefKind::Generic | DefKind::Local => def.name.clone(),
    }
}

/// `true` si el nombre es un tipo integrado del lenguaje.
#[must_use]
pub fn is_type_name(name: &str) -> bool {
    matches!(
        name,
        "Bool"
            | "Int"
            | "I8"
            | "I16"
            | "I32"
            | "I64"
            | "Isize"
            | "U8"
            | "U16"
            | "U32"
            | "UInt"
            | "U64"
            | "Usize"
            | "Float"
            | "F32"
            | "F64"
            | "Char"
            | "Str"
            | "String"
            | "Unit"
            | "Never"
            | "Ordering"
            | "Option"
            | "Result"
            | "Vec"
            | "Map"
            | "Set"
            | "Box"
            | "Rc"
            | "Arc"
            | "CStr"
            | "CString"
            | "Self"
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use pengu_hir::lower_program;
    use pengu_syntax::parse_program;

    fn crate_of(source: &str) -> HirCrate {
        let parsed = parse_program(FileId::new(1), source);
        let program = parsed.program.expect("programa");
        lower_program(&program).krate
    }

    #[test]
    fn indexa_definiciones_del_usuario_y_de_la_stdlib() {
        let krate = crate_of("hola = (nombre: &Str) -> Str\n    nombre\n");
        let index = Index::build(&krate);
        let hola = index.lookup("hola");
        assert_eq!(hola.len(), 1);
        assert_eq!(hola[0].detail, "fn hola(&Str) -> Str");
        assert!(!index.lookup("trim").is_empty());
    }

    #[test]
    fn encuentra_la_definicion_bajo_el_cursor() {
        let source = "hola = (nombre: &Str) -> Str\n    nombre\n";
        let krate = crate_of(source);
        let index = Index::build(&krate);
        let offset = u32::try_from(source.find("hola").expect("hola")).expect("u32");
        let entry = index.containing(FileId::new(1), offset).expect("entrada");
        assert_eq!(entry.name, "hola");
        assert_eq!(entry.symbol_kind(), 12);
    }

    #[test]
    fn las_constantes_llevan_su_tipo() {
        let krate = crate_of("sigil LIMITE: Int = 10\n");
        let index = Index::build(&krate);
        let entries = index.lookup("LIMITE");
        let entry = entries.first().expect("constante");
        assert_eq!(entry.detail, "sigil LIMITE: Int");
    }
}
