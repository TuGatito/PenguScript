#![forbid(unsafe_code)]
//! Spans y localización básica de `PenguScript`.
//!
//! Un [`Span`] identifica un rango de bytes `[start, end)` dentro de un
//! [`FileId`]. Los offsets son bytes UTF-8, no caracteres, para que el lexer
//! pueda operar sin asignaciones. La conversión a línea/columna vive en
//! `pengu-vfs`, que es quien conoce el texto.
//!
//! Los spans son valores ligeros y `Copy`; se usan en tokens, AST, HIR y
//! diagnósticos.

use std::fmt;

/// Identificador estable de un archivo dentro de una sesión.
///
/// El valor `u32::MAX` está reservado para [`DUMMY_FILE`].
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub struct FileId(u32);

impl FileId {
    /// Crea un `FileId` a partir de su valor crudo.
    #[must_use]
    pub const fn new(raw: u32) -> Self {
        Self(raw)
    }

    /// Devuelve el valor crudo.
    #[must_use]
    pub const fn raw(self) -> u32 {
        self.0
    }

    /// Devuelve el índice para usar en vectores.
    #[must_use]
    pub const fn index(self) -> usize {
        self.0 as usize
    }

    /// `true` si es el archivo sintético.
    #[must_use]
    pub const fn is_dummy(self) -> bool {
        self.0 == u32::MAX
    }
}

impl fmt::Display for FileId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.is_dummy() {
            f.write_str("<dummy>")
        } else {
            write!(f, "file#{}", self.0)
        }
    }
}

/// Archivo sintético para nodos generados por el compilador.
pub const DUMMY_FILE: FileId = FileId::new(u32::MAX);

/// Rango de bytes `[start, end)` dentro de un archivo.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub struct Span {
    /// Archivo que contiene el rango.
    pub file: FileId,
    /// Offset inicial, inclusivo.
    pub start: u32,
    /// Offset final, exclusivo.
    pub end: u32,
}

impl Span {
    /// Crea un span.
    ///
    /// # Panics
    ///
    /// Entra en pánico si `start > end`.
    #[must_use]
    pub const fn new(file: FileId, start: u32, end: u32) -> Self {
        assert!(start <= end);
        Self { file, start, end }
    }

    /// Crea un span vacío en `offset`.
    #[must_use]
    pub const fn empty(file: FileId, offset: u32) -> Self {
        Self {
            file,
            start: offset,
            end: offset,
        }
    }

    /// Crea un span de longitud `len` desde `start`.
    #[must_use]
    pub const fn with_len(file: FileId, start: u32, len: u32) -> Self {
        Self::new(file, start, start + len)
    }

    /// Longitud en bytes.
    #[must_use]
    pub const fn len(self) -> u32 {
        self.end - self.start
    }

    /// `true` si el rango está vacío.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.start == self.end
    }

    /// `true` si el offset cae dentro de `[start, end)`.
    #[must_use]
    pub const fn contains(self, offset: u32) -> bool {
        self.start <= offset && offset < self.end
    }

    /// `true` si el span cae completamente dentro de `[start, end)`.
    #[must_use]
    pub const fn contains_span(self, other: Self) -> bool {
        self.file.raw() == other.file.raw() && self.start <= other.start && other.end <= self.end
    }

    /// Une dos spans del mismo archivo.
    ///
    /// # Panics
    ///
    /// Entra en pánico si los spans pertenecen a archivos distintos.
    #[must_use]
    pub fn merge(self, other: Self) -> Self {
        assert_eq!(
            self.file, other.file,
            "no se pueden unir spans de archivos distintos"
        );
        Self {
            file: self.file,
            start: self.start.min(other.start),
            end: self.end.max(other.end),
        }
    }

    /// Convierte a un `Range<usize>` para indexar texto.
    #[must_use]
    pub const fn range(self) -> std::ops::Range<usize> {
        self.start as usize..self.end as usize
    }
}

impl fmt::Display for Span {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}..{}", self.file, self.start, self.end)
    }
}

/// Span sintético sin archivo real.
pub const DUMMY_SPAN: Span = Span::empty(DUMMY_FILE, 0);

/// Un valor acompañado de su span.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct Spanned<T> {
    /// Span del valor.
    pub span: Span,
    /// Valor.
    pub value: T,
}

impl<T> Spanned<T> {
    /// Crea un valor con span.
    #[must_use]
    pub const fn new(span: Span, value: T) -> Self {
        Self { span, value }
    }

    /// Transforma el valor conservando el span.
    #[must_use]
    pub fn map<U>(self, f: impl FnOnce(T) -> U) -> Spanned<U> {
        Spanned {
            span: self.span,
            value: f(self.value),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn file() -> FileId {
        FileId::new(3)
    }

    #[test]
    fn file_id_basics() {
        assert_eq!(file().raw(), 3);
        assert_eq!(file().index(), 3);
        assert!(!file().is_dummy());
        assert!(DUMMY_FILE.is_dummy());
        assert_eq!(file().to_string(), "file#3");
        assert_eq!(DUMMY_FILE.to_string(), "<dummy>");
    }

    #[test]
    fn span_basics() {
        let span = Span::new(file(), 10, 20);
        assert_eq!(span.len(), 10);
        assert!(!span.is_empty());
        assert!(span.contains(10));
        assert!(span.contains(19));
        assert!(!span.contains(20));
        assert_eq!(span.range(), 10..20);
    }

    #[test]
    fn empty_span_does_not_contain() {
        let span = Span::empty(file(), 7);
        assert!(span.is_empty());
        assert_eq!(span.len(), 0);
        assert!(!span.contains(7));
    }

    #[test]
    fn merge_spans() {
        let a = Span::new(file(), 10, 20);
        let b = Span::new(file(), 15, 30);
        let merged = a.merge(b);
        assert_eq!(merged, Span::new(file(), 10, 30));
        assert_eq!(a.merge(a), a);
    }

    #[test]
    fn contains_span_requires_same_file() {
        let a = Span::new(file(), 10, 20);
        let b = Span::new(FileId::new(4), 12, 15);
        assert!(!a.contains_span(b));
    }

    #[test]
    fn spanned_map_keeps_span() {
        let span = Span::new(file(), 0, 3);
        let value = Spanned::new(span, 41);
        let mapped = value.map(|n| n + 1);
        assert_eq!(mapped.span, span);
        assert_eq!(mapped.value, 42);
    }

    #[test]
    #[should_panic(expected = "start <= end")]
    fn inverted_span_panics() {
        let _ = Span::new(file(), 20, 10);
    }
}
