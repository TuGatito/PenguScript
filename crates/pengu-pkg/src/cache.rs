//! Caché content-addressed de repositorios y checkouts.
//!
//! La caché vive en `$PENGU_HOME/cache` (o `~/.pengu/cache`). Los repositorios bare se
//! guardan por URL en `git/<slug>.git` y los árboles se materializan por commit en
//! `src/<hash>/<commit>/`, de modo que un mismo commit siempre produce el mismo
//! directorio y se puede compartir entre proyectos.

use std::path::{Path, PathBuf};

use crate::PkgError;

/// Caché local de dependencias.
#[derive(Clone, Debug)]
pub struct Cache {
    root: PathBuf,
}

impl Cache {
    /// Caché en una raíz explícita (pensada para tests).
    pub fn at(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// Caché del usuario: `$PENGU_HOME/cache` o `~/.pengu/cache`.
    ///
    /// # Errors
    /// Devuelve `PGS-E1803` si no se puede determinar el directorio del usuario.
    pub fn from_env() -> Result<Self, PkgError> {
        if let Some(home) = std::env::var_os("PENGU_HOME") {
            return Ok(Self::at(PathBuf::from(home).join("cache")));
        }
        if let Some(home) = std::env::var_os("HOME") {
            return Ok(Self::at(PathBuf::from(home).join(".pengu").join("cache")));
        }
        Err(PkgError::invalid_lock(
            "no se puede determinar la caché",
            "define `PENGU_HOME` o `HOME`",
        ))
    }

    /// Raíz de la caché.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Directorio del repositorio bare de una URL.
    #[must_use]
    pub fn git_dir(&self, url: &str) -> PathBuf {
        self.root.join("git").join(format!("{}.git", slug(url)))
    }

    /// Directorio del checkout de un commit.
    #[must_use]
    pub fn checkout_dir(&self, url: &str, commit: &str) -> PathBuf {
        self.root.join("src").join(slug(url)).join(commit)
    }

    /// Crea los directorios base de la caché.
    ///
    /// # Errors
    /// Devuelve `PGS-E1803` si el sistema de archivos no permite crear la caché.
    pub fn ensure_dirs(&self) -> Result<(), PkgError> {
        for dir in ["git", "src"] {
            let path = self.root.join(dir);
            std::fs::create_dir_all(&path).map_err(|error| {
                crate::io_error(
                    "PGS-E1803",
                    &format!("no se puede crear la caché `{}`", path.display()),
                    &error,
                )
            })?;
        }
        Ok(())
    }
}

/// Slug estable de una URL: nombre legible + prefijo del hash.
fn slug(url: &str) -> String {
    let name = url
        .trim_end_matches('/')
        .rsplit(['/', ':'])
        .next()
        .unwrap_or("repo")
        .trim_end_matches(".git");
    let mut clean = String::new();
    for byte in name.chars() {
        if byte.is_ascii_alphanumeric() || matches!(byte, '-' | '_' | '.') {
            clean.push(byte);
        } else {
            clean.push('-');
        }
    }
    if clean.is_empty() {
        clean.push_str("repo");
    }
    format!("{clean}-{}", &crate::sha256::hex(url.as_bytes())[..12])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slug_es_estable_y_legible() {
        let url = "https://example.com/org/mi-repo.git";
        let first = slug(url);
        assert_eq!(first, slug(url));
        assert!(first.starts_with("mi-repo-"), "{first}");
        assert!(!first.contains('/'));
        assert_ne!(first, slug("https://example.com/org/otro.git"));
    }

    #[test]
    fn rutas_por_url_y_commit() {
        let cache = Cache::at("/tmp/pengu-cache");
        let url = "https://example.com/x/y";
        let dir = cache.git_dir(url);
        assert!(dir.to_string_lossy().contains("/git/y-"), "{dir:?}");
        assert!(dir.to_string_lossy().ends_with(".git"));
        assert!(cache.checkout_dir(url, "abc").ends_with("abc"));
        assert_ne!(cache.git_dir(url), cache.git_dir("https://example.com/x/z"));
    }
}
