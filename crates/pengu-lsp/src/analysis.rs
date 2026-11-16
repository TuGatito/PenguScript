//! Análisis de un documento: sintaxis → HIR → tipos → ownership.

use pengu_check::check_ownership_with;
use pengu_diag::Diagnostic;
use pengu_hir::HirCrate;
use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::ast::Program;
use pengu_syntax::parse_program;
use pengu_types::{CheckResult, check_crate};

/// Resultado del análisis semántico de un documento.
#[derive(Clone, Debug, Default)]
pub struct Analysis {
    /// Diagnósticos de todas las etapas, en orden de pipeline.
    pub diagnostics: Vec<Diagnostic>,
    /// Programa sintáctico (faltará si hubo error de sintaxis).
    pub program: Option<Program>,
    /// Crate HIR (incluye la stdlib fusionada).
    pub krate: Option<HirCrate>,
    /// Tipos calculados.
    pub check: Option<CheckResult>,
    /// Árbol de sintaxis concreta, si el parser lo produjo.
    pub tree: Option<pengu_syntax::SyntaxTree>,
}

impl Analysis {
    /// `true` si algún diagnóstico de error impide seguir.
    #[must_use]
    pub fn has_errors(&self) -> bool {
        self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Analiza `text` como el archivo `file`.
#[must_use]
pub fn analyze(file: FileId, text: &str) -> Analysis {
    let parsed = parse_program(file, text);
    let mut analysis = Analysis {
        diagnostics: parsed.diagnostics,
        program: None,
        krate: None,
        check: None,
        tree: parsed.tree,
    };
    if analysis.has_errors() {
        return analysis;
    }
    let Some(program) = parsed.program else {
        return analysis;
    };
    let lowered = lower_program(&program);
    let lower_failed = lowered.diagnostics.iter().any(Diagnostic::is_error);
    analysis.diagnostics.extend(lowered.diagnostics);
    analysis.program = Some(program);
    analysis.krate = Some(lowered.krate);
    if lower_failed {
        return analysis;
    }
    let Some(krate) = analysis.krate.as_ref() else {
        return analysis;
    };
    let checked = check_crate(krate);
    let type_failed = checked.diagnostics.iter().any(Diagnostic::is_error);
    analysis
        .diagnostics
        .extend(checked.diagnostics.iter().cloned());
    if !type_failed {
        let ownership = check_ownership_with(krate, &checked);
        analysis.diagnostics.extend(ownership.diagnostics);
    }
    analysis.check = Some(checked);
    analysis
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn analiza_un_programa_valido_sin_diagnosticos() {
        let analysis = analyze(FileId::new(1), "grimoire\n    print(\"hola\")\n");
        assert!(
            analysis.diagnostics.is_empty(),
            "{:#?}",
            analysis.diagnostics
        );
        assert!(analysis.program.is_some());
        assert!(analysis.krate.is_some());
        assert!(analysis.check.is_some());
    }

    #[test]
    fn detecta_un_error_de_sintaxis_y_para() {
        let analysis = analyze(FileId::new(1), "grimoire\n  print(\n");
        assert!(analysis.has_errors());
        assert!(analysis.program.is_none());
        assert!(analysis.krate.is_none());
        assert!(analysis.check.is_none());
    }

    #[test]
    fn detecta_un_error_de_tipos() {
        let analysis = analyze(FileId::new(1), "f = () -> Int\n    \"texto\"\n");
        assert!(
            analysis
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code.starts_with("PGS-E7")),
            "{:#?}",
            analysis.diagnostics
        );
    }

    #[test]
    fn usa_la_stdlib_fusionada() {
        let analysis = analyze(FileId::new(1), "f = () -> Bool\n    (7).is_even()\n");
        assert!(
            analysis.diagnostics.is_empty(),
            "{:#?}",
            analysis.diagnostics
        );
    }
}
