//! Reconstrucción de fuente desde el CST.
//!
//! El formateador inicial es deliberadamente conservador: reconstruye el
//! archivo exactamente como fue escrito. La fase de CLI puede añadir reglas de
//! estilo sin perder texto, porque el CST conserva todo el trivia.

use pengu_diag::Diagnostic;
use pengu_span::FileId;

use crate::{parse_declaration_file, parse_program};

/// Resultado de una operación de formato.
#[derive(Debug)]
pub struct Formatted {
    /// Texto reconstruido.
    pub text: String,
    /// Diagnósticos estructurales encontrados al parsear.
    pub diagnostics: Vec<Diagnostic>,
}

/// Reconstruye el archivo desde su CST. Si el CST no puede construirse,
/// devuelve el texto original junto con los diagnósticos.
#[must_use]
pub fn format_source(file: FileId, source: &str) -> Formatted {
    let parsed = parse_program(file, source);
    let tree = parsed.tree;
    match tree {
        Some(tree) => Formatted {
            text: tree.reconstruct(),
            diagnostics: parsed.diagnostics,
        },
        None => {
            let mut diagnostics = parsed.diagnostics;
            diagnostics.push(pengu_diag::Diagnostic::error(
                "PGS-E1805",
                "`pengu fmt` no puede formatear una fuente con errores estructurales",
                pengu_span::Span::new(file, 0, 0),
            ));
            Formatted {
                text: source.to_owned(),
                diagnostics,
            }
        }
    }
}

/// Igual que [`format_source`], pero para archivos `.d.pengu`.
#[must_use]
pub fn format_declaration(file: FileId, source: &str) -> Formatted {
    let parsed = parse_declaration_file(file, source);
    let tree = parsed.tree;
    match tree {
        Some(tree) => Formatted {
            text: tree.reconstruct(),
            diagnostics: parsed.diagnostics,
        },
        None => Formatted {
            text: source.to_owned(),
            diagnostics: parsed.diagnostics,
        },
    }
}

/// Comprueba que el CST de un programa reconstruye el fuente exacto.
#[must_use]
pub fn reconstructs(file: FileId, source: &str) -> bool {
    let parsed: crate::ParsedProgram = parse_program(file, source);
    parsed.tree.is_some_and(|tree| tree.reconstruct() == source)
}
