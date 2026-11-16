//! `pengu check`: análisis completo sin invocar Cargo.
//!
//! Comparte el front-end con [`crate::compile`] (sintaxis → HIR → tipos →
//! ownership), así que lo que `check` acepta es exactamente lo que `build`
//! acepta antes de bajar a LIR.

use std::path::{Path, PathBuf};

use pengu_diag::Diagnostic;

use crate::analyze_with_packages;

/// Resultado de `pengu check`.
#[derive(Clone, Debug, Default)]
pub struct CheckReport {
    /// Diagnósticos de todas las etapas del front-end.
    pub diagnostics: Vec<Diagnostic>,
}

impl CheckReport {
    /// `true` si no hay errores.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Analiza `root` sin generar Rust ni llamar a Cargo.
#[must_use]
pub fn check(root: &Path) -> CheckReport {
    check_with_packages(root, &[])
}

/// Como [`check`], fusionando paquetes como módulos del mismo programa.
#[must_use]
pub fn check_with_packages(root: &Path, packages: &[(String, PathBuf)]) -> CheckReport {
    let analysis = analyze_with_packages(root, packages);
    CheckReport {
        diagnostics: analysis.diagnostics,
    }
}
