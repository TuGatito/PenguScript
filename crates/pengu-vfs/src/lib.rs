#![forbid(unsafe_code)]
//! Sistema de archivos virtual y localización de `PenguScript`.
//!
//! `pengu-vfs` mantiene el texto base de cada archivo, sus overlays (cambios
//! sin guardar del LSP) y un índice de líneas para traducir offsets UTF-8 a
//! línea/columna. No toca el disco: la carga y el guardado son del driver.
//!
//! El fingerprint de contenido es un hash de 256 bits **no criptográfico**;
//! sirve para invalidar cachés, no para verificar integridad.

use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};
use std::sync::Arc;

use pengu_span::{FileId, Span};

/// Hash de contenido de 256 bits, no criptográfico.
pub type ContentHash = [u8; 32];

/// Línea y columna, ambas 1-based.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct LineCol {
    /// Línea, empezando en 1.
    pub line: u32,
    /// Columna en caracteres Unicode, empezando en 1.
    pub column: u32,
}

/// Archivo fuente con su texto actual y su índice de líneas.
#[derive(Clone, Debug)]
pub struct SourceFile {
    path: PathBuf,
    base_text: Arc<str>,
    text: Arc<str>,
    line_starts: Vec<u32>,
    hash: ContentHash,
    overlay: bool,
}

impl SourceFile {
    /// Crea un archivo a partir de su ruta y texto base.
    #[must_use]
    pub fn new(path: impl Into<PathBuf>, text: &str) -> Self {
        let path = normalize_path(path.into());
        let base_text: Arc<str> = Arc::from(text);
        let line_starts = compute_line_starts(&base_text);
        let hash = hash_text(&base_text);
        Self {
            path,
            base_text: base_text.clone(),
            text: base_text,
            line_starts,
            hash,
            overlay: false,
        }
    }

    /// Ruta normalizada.
    #[must_use]
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Texto efectivo (overlay si existe).
    #[must_use]
    pub fn text(&self) -> &str {
        &self.text
    }

    /// Texto base, sin overlay.
    #[must_use]
    pub fn base_text(&self) -> &str {
        &self.base_text
    }

    /// `true` si hay un overlay activo.
    #[must_use]
    pub const fn has_overlay(&self) -> bool {
        self.overlay
    }

    /// Fingerprint del texto efectivo.
    #[must_use]
    pub const fn hash(&self) -> ContentHash {
        self.hash
    }

    /// Número de líneas. Un archivo vacío tiene una línea.
    #[must_use]
    pub fn line_count(&self) -> u32 {
        u32::try_from(self.line_starts.len()).unwrap_or(u32::MAX)
    }

    /// Offset de inicio de `line` (1-based).
    #[must_use]
    pub fn line_start(&self, line: u32) -> Option<u32> {
        let index = usize::try_from(line.checked_sub(1)?).ok()?;
        self.line_starts.get(index).copied()
    }

    /// Texto de `line` (1-based), sin `\n` ni `\r` finales.
    #[must_use]
    pub fn line_text(&self, line: u32) -> Option<&str> {
        let index = usize::try_from(line.checked_sub(1)?).ok()?;
        let start = usize::try_from(*self.line_starts.get(index)?).ok()?;
        let end = self
            .line_starts
            .get(index + 1)
            .copied()
            .map_or(self.text.len(), |offset| offset as usize);
        let text = self.text.get(start..end)?;
        let text = text.strip_suffix('\n').unwrap_or(text);
        let text = text.strip_suffix('\r').unwrap_or(text);
        Some(text)
    }

    /// Convierte un offset UTF-8 en línea/columna.
    ///
    /// Si el offset cae en medio de un carácter, retrocede al límite anterior.
    /// Si cae fuera del texto, se limita al final.
    #[must_use]
    pub fn line_col(&self, offset: u32) -> LineCol {
        let offset = offset.min(saturating_len(&self.text));
        let index = match self.line_starts.binary_search(&offset) {
            Ok(index) => index,
            Err(0) => 0,
            Err(index) => index - 1,
        };
        let line_start = self.line_starts[index] as usize;
        let mut end = offset as usize;
        while end > line_start && !self.text.is_char_boundary(end) {
            end -= 1;
        }
        let column = self.text[line_start..end].chars().count();
        LineCol {
            line: u32::try_from(index + 1).unwrap_or(u32::MAX),
            column: u32::try_from(column + 1).unwrap_or(u32::MAX),
        }
    }

    /// Span que cubre todo el archivo.
    #[must_use]
    pub fn full_span(&self, file: FileId) -> Span {
        Span::new(file, 0, saturating_len(&self.text))
    }

    fn set_base(&mut self, text: &str) {
        self.base_text = Arc::from(text);
        if !self.overlay {
            self.text = self.base_text.clone();
            self.rebuild();
        }
    }

    fn set_overlay(&mut self, text: &str) {
        self.text = Arc::from(text);
        self.overlay = true;
        self.rebuild();
    }

    fn clear_overlay(&mut self) -> bool {
        if !self.overlay {
            return false;
        }
        self.text = self.base_text.clone();
        self.overlay = false;
        self.rebuild();
        true
    }

    fn rebuild(&mut self) {
        self.line_starts = compute_line_starts(&self.text);
        self.hash = hash_text(&self.text);
    }
}

fn saturating_len(text: &str) -> u32 {
    u32::try_from(text.len()).unwrap_or(u32::MAX)
}

fn compute_line_starts(text: &str) -> Vec<u32> {
    let mut starts = Vec::with_capacity(1 + text.bytes().filter(|byte| *byte == b'\n').count());
    starts.push(0);
    for (index, byte) in text.bytes().enumerate() {
        if byte == b'\n' {
            starts.push(u32::try_from(index + 1).unwrap_or(u32::MAX));
        }
    }
    starts
}

const FNV_OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const FNV_PRIME: u64 = 0x0000_0100_0000_01b3;

/// Hash de contenido de 256 bits, no criptográfico.
///
/// Cuatro carriles FNV-1a con semillas distintas. Es determinista entre
/// plataformas y versiones, suficiente para invalidar cachés.
#[must_use]
pub fn hash_text(text: &str) -> ContentHash {
    let mut lanes = [
        FNV_OFFSET,
        FNV_OFFSET ^ 0x9e37_79b9_7f4a_7c15,
        FNV_OFFSET ^ 0xbf58_476d_1ce4_e5b9,
        FNV_OFFSET ^ 0x94d0_49bb_1331_11eb,
    ];
    for byte in text.bytes() {
        let value = u64::from(byte);
        for (index, lane) in lanes.iter_mut().enumerate() {
            *lane ^= value.wrapping_add((index as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15));
            *lane = lane.wrapping_mul(FNV_PRIME);
        }
    }
    let len = text.len() as u64;
    for (index, lane) in lanes.iter_mut().enumerate() {
        *lane ^= len.wrapping_add(index as u64);
        *lane = lane.wrapping_mul(FNV_PRIME);
    }
    let mut out = [0_u8; 32];
    for (chunk, lane) in out.chunks_exact_mut(8).zip(lanes) {
        chunk.copy_from_slice(&lane.to_le_bytes());
    }
    out
}

/// Sistema de archivos virtual.
#[derive(Debug, Default)]
pub struct Vfs {
    files: Vec<SourceFile>,
    by_path: HashMap<PathBuf, FileId>,
}

impl Vfs {
    /// Crea un VFS vacío.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Inserta o actualiza el texto base de un archivo.
    ///
    /// Si el archivo tiene overlay, el overlay sigue siendo el texto efectivo.
    pub fn insert(&mut self, path: impl AsRef<Path>, text: &str) -> FileId {
        let path = normalize_path(path);
        let id = self.ensure_file(&path);
        self.files[id.index()].set_base(text);
        id
    }

    /// Instala un overlay (texto sin guardar).
    pub fn set_overlay(&mut self, path: impl AsRef<Path>, text: &str) -> FileId {
        let path = normalize_path(path);
        let id = self.ensure_file(&path);
        self.files[id.index()].set_overlay(text);
        id
    }

    /// Elimina el overlay y vuelve al texto base.
    pub fn remove_overlay(&mut self, path: impl AsRef<Path>) -> bool {
        let path = normalize_path(path);
        self.by_path
            .get(&path)
            .is_some_and(|id| self.files[id.index()].clear_overlay())
    }

    /// Devuelve el archivo por id.
    #[must_use]
    pub fn source(&self, file: FileId) -> Option<&SourceFile> {
        self.files.get(file.index())
    }

    /// Devuelve el archivo por ruta.
    #[must_use]
    pub fn source_by_path(&self, path: impl AsRef<Path>) -> Option<&SourceFile> {
        let path = normalize_path(path);
        self.by_path.get(&path).and_then(|id| self.source(*id))
    }

    /// Texto efectivo por id.
    #[must_use]
    pub fn text(&self, file: FileId) -> Option<&str> {
        self.source(file).map(SourceFile::text)
    }

    /// Ruta por id.
    #[must_use]
    pub fn path(&self, file: FileId) -> Option<&Path> {
        self.source(file).map(SourceFile::path)
    }

    /// Busca el id de una ruta.
    #[must_use]
    pub fn file_id(&self, path: impl AsRef<Path>) -> Option<FileId> {
        let path = normalize_path(path);
        self.by_path.get(&path).copied()
    }

    /// Itera sobre los archivos.
    pub fn iter(&self) -> impl Iterator<Item = &SourceFile> {
        self.files.iter()
    }

    /// Número de archivos.
    #[must_use]
    pub fn len(&self) -> usize {
        self.files.len()
    }

    /// `true` si no hay archivos.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.files.is_empty()
    }

    fn ensure_file(&mut self, path: &Path) -> FileId {
        if let Some(id) = self.by_path.get(path) {
            return *id;
        }
        let raw = u32::try_from(self.files.len()).expect("demasiados archivos en el VFS");
        let id = FileId::new(raw);
        self.files.push(SourceFile::new(path.to_path_buf(), ""));
        self.by_path.insert(path.to_path_buf(), id);
        id
    }
}

/// Normaliza una ruta sin tocar el sistema de archivos.
///
/// Elimina `.`, resuelve `..` cuando es posible y conserva mayúsculas,
/// prefijos de Windows y rutas relativas que empiezan por `..`.
#[must_use]
pub fn normalize_path(path: impl AsRef<Path>) -> PathBuf {
    let mut out = PathBuf::new();
    let mut rooted = false;
    for component in path.as_ref().components() {
        match component {
            Component::Prefix(prefix) => {
                out.push(prefix.as_os_str());
                rooted = true;
            }
            Component::RootDir => {
                out.push(Component::RootDir.as_os_str());
                rooted = true;
            }
            Component::CurDir => {}
            Component::ParentDir => {
                let can_pop = matches!(out.components().next_back(), Some(Component::Normal(_)));
                if can_pop {
                    out.pop();
                } else if !rooted {
                    out.push("..");
                }
            }
            Component::Normal(part) => out.push(part),
        }
    }
    if out.as_os_str().is_empty() {
        out.push(".");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn line_index_and_columns() {
        let file = SourceFile::new("test.pengu", "aé\nmundo\n");
        assert_eq!(file.line_count(), 3);
        assert_eq!(file.line_col(0), LineCol { line: 1, column: 1 });
        assert_eq!(file.line_col(2), LineCol { line: 1, column: 2 });
        assert_eq!(file.line_col(3), LineCol { line: 1, column: 3 });
        assert_eq!(file.line_col(4), LineCol { line: 2, column: 1 });
        assert_eq!(file.line_text(1), Some("aé"));
        assert_eq!(file.line_text(2), Some("mundo"));
        assert_eq!(file.line_text(3), Some(""));
    }

    #[test]
    fn line_col_clamps_and_rounds_to_boundary() {
        let file = SourceFile::new("test.pengu", "aé\nb");
        assert_eq!(file.line_col(1).column, 2);
        assert_eq!(file.line_col(2).column, 2);
        assert_eq!(file.line_col(3).column, 3);
        assert_eq!(file.line_col(99), LineCol { line: 2, column: 2 });
    }

    #[test]
    fn crlf_strips_carriage_return() {
        let file = SourceFile::new("test.pengu", "uno\r\ndos\r\n");
        assert_eq!(file.line_text(1), Some("uno"));
        assert_eq!(file.line_text(2), Some("dos"));
    }

    #[test]
    fn overlay_changes_text_and_hash() {
        let mut vfs = Vfs::new();
        let id = vfs.insert("src/main.pengu", "uno");
        let original = vfs.source(id).unwrap().hash();
        vfs.set_overlay("src/main.pengu", "dos");
        let source = vfs.source(id).unwrap();
        assert!(source.has_overlay());
        assert_eq!(source.text(), "dos");
        assert_eq!(source.base_text(), "uno");
        assert_ne!(source.hash(), original);
        assert!(vfs.remove_overlay("src/main.pengu"));
        let source = vfs.source(id).unwrap();
        assert!(!source.has_overlay());
        assert_eq!(source.text(), "uno");
        assert_eq!(source.hash(), original);
    }

    #[test]
    fn base_update_keeps_overlay() {
        let mut vfs = Vfs::new();
        let id = vfs.insert("a.pengu", "base1");
        vfs.set_overlay("a.pengu", "overlay");
        vfs.insert("a.pengu", "base2");
        assert_eq!(vfs.text(id), Some("overlay"));
        vfs.remove_overlay("a.pengu");
        assert_eq!(vfs.text(id), Some("base2"));
    }

    #[test]
    fn overlay_can_create_new_file() {
        let mut vfs = Vfs::new();
        let id = vfs.set_overlay("nuevo.pengu", "hola");
        assert_eq!(vfs.text(id), Some("hola"));
        assert!(vfs.file_id("nuevo.pengu").is_some());
    }

    #[test]
    fn file_ids_are_stable() {
        let mut vfs = Vfs::new();
        let a = vfs.insert("a.pengu", "");
        let b = vfs.insert("b.pengu", "");
        assert_ne!(a, b);
        assert_eq!(vfs.insert("a.pengu", "x"), a);
        assert_eq!(vfs.file_id("b.pengu"), Some(b));
    }

    #[test]
    fn normalize_paths() {
        assert_eq!(normalize_path("a/./b"), PathBuf::from("a/b"));
        assert_eq!(normalize_path("a/../b"), PathBuf::from("b"));
        assert_eq!(normalize_path("../a"), PathBuf::from("../a"));
        assert_eq!(normalize_path(""), PathBuf::from("."));
        assert_eq!(normalize_path("/a/../b"), PathBuf::from("/b"));
    }

    #[test]
    fn hash_is_stable_and_sensitive() {
        assert_eq!(hash_text("pengu"), hash_text("pengu"));
        assert_ne!(hash_text("pengu"), hash_text("pengu "));
        assert_ne!(hash_text(""), hash_text("a"));
    }

    #[test]
    fn full_span_matches_text() {
        let mut vfs = Vfs::new();
        let id = vfs.insert("a.pengu", "abc");
        let span = vfs.source(id).unwrap().full_span(id);
        assert_eq!(span.start, 0);
        assert_eq!(span.end, 3);
    }
}
