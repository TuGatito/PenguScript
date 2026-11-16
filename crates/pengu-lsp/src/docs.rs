//! Documentos abiertos: texto, versión, índice de líneas y cambios incrementales.

use std::collections::BTreeMap;

use pengu_span::FileId;
use pengu_vfs::{ContentHash, hash_text};

use crate::position::{Encoding, LineIndex, Position, Range};
use crate::uri::Uri;

/// Cambio de contenido enviado por el cliente.
#[derive(Clone, Debug)]
pub struct ContentChange {
    /// Rango reemplazado; `None` significa reemplazo total.
    pub range: Option<Range>,
    /// Texto nuevo.
    pub text: String,
}

/// Documento abierto.
#[derive(Clone, Debug)]
pub struct Document {
    uri: Uri,
    file_id: FileId,
    version: i32,
    text: String,
    index: LineIndex,
    hash: ContentHash,
    read_only: bool,
    dirty: bool,
}

impl Document {
    /// Crea un documento.
    #[must_use]
    pub fn new(uri: Uri, file_id: FileId, version: i32, text: String, read_only: bool) -> Self {
        let index = LineIndex::new(&text);
        let hash = hash_text(&text);
        Self {
            uri,
            file_id,
            version,
            text,
            index,
            hash,
            read_only,
            dirty: !read_only,
        }
    }

    /// URI.
    #[must_use]
    pub fn uri(&self) -> &Uri {
        &self.uri
    }

    /// `FileId` del documento.
    #[must_use]
    pub fn file_id(&self) -> FileId {
        self.file_id
    }

    /// Versión anunciada por el cliente.
    #[must_use]
    pub fn version(&self) -> i32 {
        self.version
    }

    /// Texto actual.
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Índice de líneas.
    #[must_use]
    pub fn index(&self) -> &LineIndex {
        &self.index
    }

    /// Hash del contenido (clave de caché).
    #[must_use]
    pub fn hash(&self) -> ContentHash {
        self.hash
    }

    /// `true` si es la stdlib embebida (solo lectura).
    #[must_use]
    pub fn read_only(&self) -> bool {
        self.read_only
    }

    /// `true` si cambió desde el último análisis.
    #[must_use]
    pub fn dirty(&self) -> bool {
        self.dirty
    }

    /// Marca el documento como analizado.
    pub fn mark_clean(&mut self) {
        self.dirty = false;
    }

    /// Posición LSP de un desplazamiento.
    #[must_use]
    pub fn position(&self, offset: u32, encoding: Encoding) -> Position {
        self.index.position_with(&self.text, offset, encoding)
    }

    /// Desplazamiento de una posición LSP.
    #[must_use]
    pub fn offset(&self, position: Position, encoding: Encoding) -> u32 {
        self.index.offset(&self.text, position, encoding)
    }

    /// Aplica un cambio completo (sincronización `Full` o `range: null`).
    pub fn apply_full(&mut self, text: String, version: i32) {
        self.text = text;
        self.index = LineIndex::new(&self.text);
        self.hash = hash_text(&self.text);
        self.version = version;
        self.dirty = true;
    }

    /// Aplica un cambio de rango.
    ///
    /// Devuelve `false` si el rango es inválido y el documento queda intacto.
    pub fn apply_range(
        &mut self,
        range: Range,
        replacement: &str,
        version: i32,
        encoding: Encoding,
    ) -> bool {
        let start = self.offset(range.start, encoding);
        let end = self.offset(range.end, encoding);
        if start > end {
            return false;
        }
        let start = usize::try_from(start).unwrap_or(usize::MAX);
        let end = usize::try_from(end).unwrap_or(usize::MAX);
        if start > self.text.len() || end > self.text.len() {
            return false;
        }
        if !self.text.is_char_boundary(start) || !self.text.is_char_boundary(end) {
            return false;
        }
        self.text.replace_range(start..end, replacement);
        self.index = LineIndex::new(&self.text);
        self.hash = hash_text(&self.text);
        self.version = version;
        self.dirty = true;
        true
    }
}

/// Conjunto de documentos abiertos, incluidos los de la stdlib.
#[derive(Debug, Default)]
pub struct Documents {
    open: BTreeMap<String, Document>,
    next_file: u32,
}

impl Documents {
    /// Crea el almacén con las fuentes de la stdlib cargadas como solo lectura.
    #[must_use]
    pub fn new() -> Self {
        let mut store = Self {
            open: BTreeMap::new(),
            next_file: 1,
        };
        for (index, file) in pengu_std::files().iter().enumerate() {
            let uri = Uri::std_file(file.name);
            let document = Document::new(
                uri.clone(),
                pengu_std::file_id(index),
                0,
                file.text.to_owned(),
                true,
            );
            store.open.insert(uri.as_str().to_owned(), document);
        }
        store
    }

    fn allocate_file(&mut self) -> FileId {
        let id = FileId::new(self.next_file);
        self.next_file = self.next_file.saturating_add(1);
        id
    }

    /// Abre (o reabre) un documento.
    ///
    /// # Panics
    ///
    /// Solo si el documento se acaba de insertar y no aparece, lo que sería un
    /// error de programación.
    pub fn open(&mut self, uri: Uri, version: i32, text: String) -> &mut Document {
        let key = uri.as_str().to_owned();
        if self.open.contains_key(&key) {
            let document = self.open.get_mut(&key).expect("documento existente");
            if !document.read_only {
                document.apply_full(text, version);
            }
            return document;
        }
        let file_id = self.allocate_file();
        self.open.insert(
            key.clone(),
            Document::new(uri, file_id, version, text, false),
        );
        self.open.get_mut(&key).expect("documento insertado")
    }

    /// Aplica cambios incrementales.
    ///
    /// Devuelve `None` si el documento no existe, es de solo lectura o algún
    /// rango es inválido (en ese caso no se aplica ninguno).
    pub fn change(
        &mut self,
        uri: &Uri,
        version: i32,
        changes: &[ContentChange],
        encoding: Encoding,
    ) -> Option<&mut Document> {
        let document = self.open.get_mut(uri.as_str())?;
        if document.read_only {
            return None;
        }
        let mut text = document.text.clone();
        let mut index = LineIndex::new(&text);
        for change in changes {
            match change.range {
                None => {
                    text.clone_from(&change.text);
                    index = LineIndex::new(&text);
                }
                Some(range) => {
                    let start = usize::try_from(index.offset(&text, range.start, encoding)).ok()?;
                    let end = usize::try_from(index.offset(&text, range.end, encoding)).ok()?;
                    if start > end
                        || end > text.len()
                        || !text.is_char_boundary(start)
                        || !text.is_char_boundary(end)
                    {
                        return None;
                    }
                    text.replace_range(start..end, &change.text);
                    index = LineIndex::new(&text);
                }
            }
        }
        document.text = text;
        document.index = index;
        document.hash = hash_text(&document.text);
        document.version = version;
        document.dirty = true;
        Some(document)
    }

    /// Cierra un documento (los de std no se cierran).
    pub fn close(&mut self, uri: &Uri) {
        if let Some(document) = self.open.get(uri.as_str()) {
            if document.read_only {
                return;
            }
        }
        self.open.remove(uri.as_str());
    }

    /// Documento por URI.
    #[must_use]
    pub fn get(&self, uri: &Uri) -> Option<&Document> {
        self.open.get(uri.as_str())
    }

    /// Documento por `FileId`.
    #[must_use]
    pub fn by_file(&self, file_id: FileId) -> Option<&Document> {
        self.open
            .values()
            .find(|document| document.file_id == file_id)
    }

    /// Documento mutable por URI.
    pub fn get_mut(&mut self, uri: &Uri) -> Option<&mut Document> {
        self.open.get_mut(uri.as_str())
    }

    /// Itera los documentos.
    pub fn iter(&self) -> impl Iterator<Item = &Document> {
        self.open.values()
    }

    /// Documentos sucios, ordenados por URI.
    #[must_use]
    pub fn dirty(&self) -> Vec<&Document> {
        self.open
            .values()
            .filter(|document| document.dirty)
            .collect()
    }

    /// Número de documentos.
    #[must_use]
    pub fn len(&self) -> usize {
        self.open.len()
    }

    /// `true` si no hay documentos (nunca: la stdlib está siempre).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.open.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn doc(text: &str) -> Document {
        Document::new(
            Uri::parse("file:///tmp/x.pengu").expect("uri"),
            FileId::new(1),
            1,
            text.to_owned(),
            false,
        )
    }

    #[test]
    fn aplica_cambios_incrementales() {
        let mut document = doc("hola mundo");
        let range = Range::new(
            Position {
                line: 0,
                character: 5,
            },
            Position {
                line: 0,
                character: 10,
            },
        );
        assert!(document.apply_range(range, "pengu", 2, Encoding::Utf16));
        assert_eq!(document.text(), "hola pengu");
        assert_eq!(document.version(), 2);
        assert!(document.dirty());
    }

    #[test]
    fn rechaza_rangos_invertidos_o_fuera_del_texto() {
        let mut document = doc("abc");
        let inverted = Range::new(
            Position {
                line: 0,
                character: 3,
            },
            Position {
                line: 0,
                character: 1,
            },
        );
        assert!(!document.apply_range(inverted, "x", 2, Encoding::Utf16));
        assert_eq!(document.text(), "abc");
    }

    #[test]
    fn aplica_varios_cambios_en_orden() {
        let mut documents = Documents::new();
        let uri = Uri::parse("file:///tmp/y.pengu").expect("uri");
        documents.open(uri.clone(), 1, "uno dos".to_owned());
        let changes = vec![
            ContentChange {
                range: Some(Range::new(
                    Position {
                        line: 0,
                        character: 0,
                    },
                    Position {
                        line: 0,
                        character: 3,
                    },
                )),
                text: "1".to_owned(),
            },
            ContentChange {
                range: Some(Range::new(
                    Position {
                        line: 0,
                        character: 2,
                    },
                    Position {
                        line: 0,
                        character: 5,
                    },
                )),
                text: "2".to_owned(),
            },
        ];
        let document = documents
            .change(&uri, 3, &changes, Encoding::Utf16)
            .expect("cambio");
        assert_eq!(document.text(), "1 2");
    }

    #[test]
    fn reemplazo_total_cuando_no_hay_rango() {
        let mut documents = Documents::new();
        let uri = Uri::parse("file:///tmp/z.pengu").expect("uri");
        documents.open(uri.clone(), 1, "viejo".to_owned());
        let changes = vec![ContentChange {
            range: None,
            text: "nuevo".to_owned(),
        }];
        let document = documents
            .change(&uri, 2, &changes, Encoding::Utf16)
            .expect("cambio");
        assert_eq!(document.text(), "nuevo");
    }

    #[test]
    fn la_stdlib_es_solo_lectura_y_esta_indexada() {
        let mut documents = Documents::new();
        let uri = Uri::std_file("integrum");
        let document = documents.get(&uri).expect("std");
        assert!(document.read_only());
        assert!(document.text().contains("scroll integrum"));
        let file_id = document.file_id();
        assert!(pengu_std::is_std_file(file_id));
        assert_eq!(pengu_std::file_index(file_id), Some(0));
        assert!(documents.change(&uri, 2, &[], Encoding::Utf16).is_none());
        documents.close(&uri);
        assert!(documents.get(&uri).is_some());
    }

    #[test]
    fn ids_de_archivo_no_chocan_con_los_de_std() {
        let mut documents = Documents::new();
        let uri = Uri::parse("file:///tmp/a.pengu").expect("uri");
        let document = documents.open(uri, 1, "x".to_owned());
        assert!(!pengu_std::is_std_file(document.file_id()));
    }
}
