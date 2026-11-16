#![forbid(unsafe_code)]
//! Diagnósticos estructurados de `PenguScript`.
//!
//! Un [`Diagnostic`] tiene un código `PGS-*`, una severidad, un span primario,
//! etiquetas secundarias, notas y una ayuda. `pengu-diag` no formatea contra el
//! código fuente: el CLI/LSP añaden el texto y el renderizado final.

use std::fmt;

use pengu_span::Span;

/// Severidad de un diagnóstico.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub enum Severity {
    /// Error que impide compilar.
    Error,
    /// Advertencia: compila, pero conviene corregir.
    Warning,
    /// Nota informativa.
    Note,
    /// Ayuda o sugerencia.
    Help,
}

impl Severity {
    /// Nombre corto y estable.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Error => "error",
            Self::Warning => "warning",
            Self::Note => "note",
            Self::Help => "help",
        }
    }

    /// `true` para errores.
    #[must_use]
    pub const fn is_error(self) -> bool {
        matches!(self, Self::Error)
    }
}

impl fmt::Display for Severity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Etiqueta secundaria dentro de un diagnóstico.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Label {
    /// Rango señalado.
    pub span: Span,
    /// Mensaje opcional.
    pub message: Option<String>,
}

impl Label {
    /// Etiqueta sin mensaje.
    #[must_use]
    pub const fn at(span: Span) -> Self {
        Self {
            span,
            message: None,
        }
    }

    /// Etiqueta con mensaje.
    #[must_use]
    pub fn new(span: Span, message: impl Into<String>) -> Self {
        Self {
            span,
            message: Some(message.into()),
        }
    }
}

/// Diagnóstico completo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Diagnostic {
    /// Código estable, por ejemplo `PGS-E1001`.
    pub code: &'static str,
    /// Severidad.
    pub severity: Severity,
    /// Mensaje principal.
    pub message: String,
    /// Span principal.
    pub primary: Span,
    /// Etiquetas adicionales.
    pub labels: Vec<Label>,
    /// Notas de contexto.
    pub notes: Vec<String>,
    /// Ayuda accionable.
    pub help: Option<String>,
}

impl Diagnostic {
    /// Crea un diagnóstico con el span y la severidad dados.
    #[must_use]
    pub fn new(
        code: &'static str,
        severity: Severity,
        message: impl Into<String>,
        primary: Span,
    ) -> Self {
        Self {
            code,
            severity,
            message: message.into(),
            primary,
            labels: Vec::new(),
            notes: Vec::new(),
            help: None,
        }
    }

    /// Error.
    #[must_use]
    pub fn error(code: &'static str, message: impl Into<String>, primary: Span) -> Self {
        Self::new(code, Severity::Error, message, primary)
    }

    /// Advertencia.
    #[must_use]
    pub fn warning(code: &'static str, message: impl Into<String>, primary: Span) -> Self {
        Self::new(code, Severity::Warning, message, primary)
    }

    /// Añade una etiqueta.
    #[must_use]
    pub fn with_label(mut self, label: Label) -> Self {
        self.labels.push(label);
        self
    }

    /// Añade una etiqueta con mensaje.
    #[must_use]
    pub fn with_label_at(mut self, span: Span, message: impl Into<String>) -> Self {
        self.labels.push(Label::new(span, message));
        self
    }

    /// Añade una nota.
    #[must_use]
    pub fn with_note(mut self, note: impl Into<String>) -> Self {
        self.notes.push(note.into());
        self
    }

    /// Añade una ayuda.
    #[must_use]
    pub fn with_help(mut self, help: impl Into<String>) -> Self {
        self.help = Some(help.into());
        self
    }

    /// `true` si es un error.
    #[must_use]
    pub const fn is_error(&self) -> bool {
        self.severity.is_error()
    }

    /// Render compacto sin código fuente: `error[PGS-E1001]: mensaje`.
    #[must_use]
    pub fn render_compact(&self) -> String {
        format!("{}[{}]: {}", self.severity, self.code, self.message)
    }
}

/// Contenedor de diagnósticos de una sesión.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DiagnosticBag {
    diagnostics: Vec<Diagnostic>,
}

impl DiagnosticBag {
    /// Bolsa vacía.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Añade un diagnóstico.
    pub fn push(&mut self, diagnostic: Diagnostic) {
        self.diagnostics.push(diagnostic);
    }

    /// Añade un error.
    pub fn error(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        self.push(Diagnostic::error(code, message, span));
    }

    /// Añade una advertencia.
    pub fn warning(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        self.push(Diagnostic::warning(code, message, span));
    }

    /// Añade varios diagnósticos.
    pub fn extend(&mut self, diagnostics: impl IntoIterator<Item = Diagnostic>) {
        self.diagnostics.extend(diagnostics);
    }

    /// `true` si hay al menos un error.
    #[must_use]
    pub fn has_errors(&self) -> bool {
        self.diagnostics.iter().any(Diagnostic::is_error)
    }

    /// Número de diagnósticos.
    #[must_use]
    pub fn len(&self) -> usize {
        self.diagnostics.len()
    }

    /// `true` si está vacía.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.diagnostics.is_empty()
    }

    /// Itera sobre los diagnósticos.
    pub fn iter(&self) -> impl Iterator<Item = &Diagnostic> {
        self.diagnostics.iter()
    }

    /// Consume la bolsa y devuelve el vector.
    #[must_use]
    pub fn into_vec(self) -> Vec<Diagnostic> {
        self.diagnostics
    }

    /// Vacía la bolsa.
    pub fn clear(&mut self) {
        self.diagnostics.clear();
    }

    /// Ordena por archivo, offset y severidad, sin perder estabilidad.
    pub fn sort(&mut self) {
        self.diagnostics.sort_by_key(|diagnostic| {
            (
                diagnostic.primary.file.raw(),
                diagnostic.primary.start,
                diagnostic.primary.end,
                diagnostic.severity,
                diagnostic.code,
            )
        });
    }
}

impl IntoIterator for DiagnosticBag {
    type Item = Diagnostic;
    type IntoIter = std::vec::IntoIter<Diagnostic>;

    fn into_iter(self) -> Self::IntoIter {
        self.diagnostics.into_iter()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pengu_span::{DUMMY_SPAN, FileId, Span};

    fn span(start: u32, end: u32) -> Span {
        Span::new(FileId::new(1), start, end)
    }

    #[test]
    fn severity_names() {
        assert_eq!(Severity::Error.as_str(), "error");
        assert_eq!(Severity::Warning.as_str(), "warning");
        assert_eq!(Severity::Note.as_str(), "note");
        assert_eq!(Severity::Help.as_str(), "help");
        assert!(Severity::Error.is_error());
        assert!(!Severity::Warning.is_error());
    }

    #[test]
    fn diagnostic_builder() {
        let diagnostic = Diagnostic::error("PGS-E1001", "BOM inesperado", span(0, 3))
            .with_label(Label::at(span(0, 3)))
            .with_label_at(span(3, 5), "aquí")
            .with_note("el archivo debe ser UTF-8 sin BOM")
            .with_help("guarda el archivo sin BOM");
        assert!(diagnostic.is_error());
        assert_eq!(diagnostic.labels.len(), 2);
        assert_eq!(diagnostic.notes.len(), 1);
        assert_eq!(
            diagnostic.help.as_deref(),
            Some("guarda el archivo sin BOM")
        );
        assert_eq!(
            diagnostic.render_compact(),
            "error[PGS-E1001]: BOM inesperado"
        );
    }

    #[test]
    fn bag_tracks_errors() {
        let mut bag = DiagnosticBag::new();
        assert!(bag.is_empty());
        assert!(!bag.has_errors());
        bag.warning("PGS-W1001", "aviso", span(0, 1));
        assert!(!bag.has_errors());
        bag.error("PGS-E1002", "error", span(1, 2));
        assert!(bag.has_errors());
        assert_eq!(bag.len(), 2);
        assert_eq!(bag.into_vec().len(), 2);
    }

    #[test]
    fn bag_sorts_by_span() {
        let mut bag = DiagnosticBag::new();
        bag.error("PGS-E1001", "b", span(10, 12));
        bag.error("PGS-E1001", "a", span(2, 4));
        bag.error("PGS-E1001", "c", span(10, 11));
        bag.sort();
        let starts: Vec<u32> = bag
            .iter()
            .map(|diagnostic| diagnostic.primary.start)
            .collect();
        assert_eq!(starts, vec![2, 10, 10]);
        assert_eq!(bag.iter().next().unwrap().message, "a");
    }

    #[test]
    fn dummy_span_is_usable() {
        let diagnostic = Diagnostic::warning("PGS-W0000", "sintético", DUMMY_SPAN);
        assert_eq!(diagnostic.primary, DUMMY_SPAN);
    }

    #[test]
    fn into_iterator() {
        let mut bag = DiagnosticBag::new();
        bag.error("PGS-E1001", "x", span(0, 1));
        let messages: Vec<String> = bag
            .into_iter()
            .map(|diagnostic| diagnostic.message)
            .collect();
        assert_eq!(messages, vec!["x"]);
    }
}
