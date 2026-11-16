//! Límites del frontend.
//!
//! Los límites son deliberadamente conservadores: el frontend debe responder
//! con un diagnóstico, nunca con un pánico ni con un consumo de memoria
//! descontrolado.

use pengu_diag::Diagnostic;
use pengu_span::{FileId, Span};

use crate::{Token, TokenKind};

/// Tamaño máximo de un archivo fuente: 10 MiB.
pub const MAX_SOURCE_BYTES: usize = 10 * 1024 * 1024;

/// Número máximo de líneas de un archivo fuente.
///
/// Es un guardia secundario: el límite real es `MAX_SOURCE_BYTES`. Con líneas
/// cortas (código normal) 200 000 líneas caben de sobra en 10 MiB; el límite
/// existe para rechazar entradas con millones de líneas vacías.
pub const MAX_LINES: usize = 200_000;

/// Profundidad máxima de anidamiento de delimitadores e indentación.
pub const MAX_DEPTH: usize = 1_000;

/// Comprueba tamaño y número de líneas.
#[must_use]
pub fn source_diagnostic(file: FileId, source: &str) -> Option<Diagnostic> {
    if source.len() > MAX_SOURCE_BYTES {
        return Some(Diagnostic::error(
            "PGS-E1901",
            format!(
                "el archivo excede el límite de {} MiB",
                MAX_SOURCE_BYTES / (1024 * 1024)
            ),
            Span::new(file, 0, 0),
        ));
    }
    let lines = source.bytes().filter(|byte| *byte == b'\n').count() + 1;
    if lines > MAX_LINES {
        return Some(Diagnostic::error(
            "PGS-E1901",
            format!("el archivo excede el límite de {MAX_LINES} líneas"),
            Span::new(file, 0, 0),
        ));
    }
    None
}

/// Comprueba la profundidad de delimitadores e indentación de una secuencia
/// de tokens. Se ejecuta antes del parser para evitar recursión descontrolada.
#[must_use]
pub fn token_depth_diagnostic(tokens: &[Token]) -> Option<Diagnostic> {
    let mut delimiters = 0usize;
    let mut indentation = 0usize;
    for token in tokens {
        match token.kind {
            TokenKind::LParen | TokenKind::LBracket | TokenKind::LBrace => {
                delimiters += 1;
            }
            TokenKind::RParen | TokenKind::RBracket | TokenKind::RBrace => {
                delimiters = delimiters.saturating_sub(1);
            }
            TokenKind::Indent => indentation += 1,
            TokenKind::Dedent => indentation = indentation.saturating_sub(1),
            _ => {}
        }
        if delimiters >= MAX_DEPTH || indentation >= MAX_DEPTH {
            return Some(Diagnostic::error(
                "PGS-E1901",
                format!("la profundidad de anidamiento excede {MAX_DEPTH}"),
                token.span,
            ));
        }
    }
    None
}
