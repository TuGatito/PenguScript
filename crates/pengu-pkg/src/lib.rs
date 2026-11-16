//! Gestión de paquetes de `PenguScript`: fuentes git/path, caché, `Tome.lock` y vendor.
//!
//! La norma está en `docs/LANGUAGE.md` §18. Este crate no usa dependencias externas
//! (igual que el resto del workspace) y no toca la red en sus tests: git se invoca por
//! `Command` y las pruebas usan repositorios locales.

pub mod cache;
pub mod git;
pub mod lock;
pub mod manifest;
pub mod ops;
pub mod resolver;
pub use pengu_sha256 as sha256;
pub mod source;
pub mod spec;
pub mod tags;
pub mod toml;
pub mod tree;
pub mod tree_hash;
pub mod vendor;

use std::fmt;

/// Error con el código de diagnóstico de la norma y una acción sugerida.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PkgError {
    /// Código `PGS-Exxxx`.
    pub code: &'static str,
    /// Mensaje para el usuario.
    pub message: String,
    /// Acción sugerida, si la hay.
    pub help: Option<String>,
}

impl PkgError {
    /// Error con ayuda.
    #[must_use]
    pub fn new(code: &'static str, message: impl Into<String>, help: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            help: Some(help.into()),
        }
    }

    /// Error sin ayuda adicional.
    #[must_use]
    pub fn plain(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            help: None,
        }
    }

    /// `PGS-E1808`: lock inválido o checksum incorrecto.
    #[must_use]
    pub fn invalid_lock(message: impl Into<String>, help: impl Into<String>) -> Self {
        Self::new("PGS-E1808", message, help)
    }

    /// Código del diagnóstico.
    #[must_use]
    pub fn code(&self) -> &'static str {
        self.code
    }

    /// Añade o reemplaza la acción sugerida.
    #[must_use]
    pub fn with_help(mut self, help: impl Into<String>) -> Self {
        self.help = Some(help.into());
        self
    }

    /// `PGS-E1803`: la dependencia pedida no está en el manifiesto.
    #[must_use]
    pub fn dependency_not_found(name: &str) -> Self {
        Self::new(
            "PGS-E1803",
            format!("la dependencia `{name}` no está en `Tome.toml`"),
            "revisa `[dependencies]` o usa `pengu add`",
        )
    }

    /// `PGS-E1804`: lock ausente o desactualizado.
    #[must_use]
    pub fn stale_lock(message: impl Into<String>, help: impl Into<String>) -> Self {
        Self::new("PGS-E1804", message, help)
    }
}

impl fmt::Display for PkgError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.code, self.message)?;
        if let Some(help) = &self.help {
            write!(f, " ({help})")?;
        }
        Ok(())
    }
}

impl std::error::Error for PkgError {}

/// Convierte un error de E/S en un `PkgError` con contexto y el código indicado.
#[must_use]
pub fn io_error(code: &'static str, context: &str, error: &std::io::Error) -> PkgError {
    PkgError::plain(code, format!("{context}: {error}"))
}
