//! Fuentes de dependencia: git (con `tag`/`branch`/`rev`) y path.
//!
//! El formato canónico lo fija `docs/LANGUAGE.md` §18.3:
//! `git+URL?tag=...`, `git+URL?branch=...`, `git+URL?rev=...` y `path+../local`.

use crate::PkgError;

/// Referencia de una dependencia git: exactamente una de las tres.
#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub enum GitRef {
    /// Etiqueta.
    Tag(String),
    /// Rama.
    Branch(String),
    /// Revisión (commit o prefijo).
    Rev(String),
}

impl GitRef {
    /// Clave canónica (`tag=`, `branch=`, `rev=`).
    #[must_use]
    pub fn key(&self) -> &'static str {
        match self {
            Self::Tag(_) => "tag",
            Self::Branch(_) => "branch",
            Self::Rev(_) => "rev",
        }
    }

    /// Valor.
    #[must_use]
    pub fn value(&self) -> &str {
        match self {
            Self::Tag(value) | Self::Branch(value) | Self::Rev(value) => value,
        }
    }

    /// `true` si es una revisión fija (no se mueve con `update`).
    #[must_use]
    pub fn is_rev(&self) -> bool {
        matches!(self, Self::Rev(_))
    }
}

/// Origen de un paquete.
#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub enum Source {
    /// Repositorio git con una referencia.
    Git {
        /// URL del repositorio.
        url: String,
        /// Referencia pedida en el manifiesto.
        reference: GitRef,
    },
    /// Ruta local, relativa a la raíz del paquete que la declara.
    Path {
        /// Ruta tal y como aparece en el manifiesto.
        path: String,
    },
}

impl Source {
    /// Construye una fuente git validando que la URL no esté vacía.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806` si la URL o la referencia están vacías.
    pub fn git(url: &str, reference: GitRef) -> Result<Self, PkgError> {
        let url = url.trim();
        if url.is_empty() {
            return Err(PkgError::plain(
                "PGS-E1806",
                "una dependencia git necesita `git = \"URL\"`",
            ));
        }
        if reference.value().trim().is_empty() {
            return Err(PkgError::plain(
                "PGS-E1806",
                format!(
                    "la dependencia git `{url}` declara `{}` vacío",
                    reference.key()
                ),
            ));
        }
        Ok(Self::Git {
            url: url.to_owned(),
            reference,
        })
    }

    /// Construye una fuente path.
    ///
    /// # Errors
    /// Devuelve `PGS-E1803` si la ruta está vacía.
    pub fn path(path: &str) -> Result<Self, PkgError> {
        let path = path.trim();
        if path.is_empty() {
            return Err(PkgError::plain(
                "PGS-E1803",
                "una dependencia path necesita una ruta",
            ));
        }
        Ok(Self::Path {
            path: path.to_owned(),
        })
    }

    /// Forma canónica que se escribe en el lock.
    #[must_use]
    pub fn canonical(&self) -> String {
        match self {
            Self::Git { url, reference } => {
                format!("git+{url}?{}={}", reference.key(), reference.value())
            }
            Self::Path { path } => format!("path+{path}"),
        }
    }

    /// Interpreta una forma canónica.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806`/`PGS-E1803` si el texto no es una fuente válida.
    pub fn parse(text: &str) -> Result<Self, PkgError> {
        if let Some(rest) = text.strip_prefix("git+") {
            let (url, query) = rest.rsplit_once('?').ok_or_else(|| {
                PkgError::invalid_lock(
                    format!("fuente git sin referencia: `{text}`"),
                    "usa `git+URL?tag=`, `?branch=` o `?rev=`",
                )
            })?;
            let (key, value) = query.split_once('=').ok_or_else(|| {
                PkgError::invalid_lock(
                    format!("referencia git malformada: `{query}`"),
                    "usa `tag=`, `branch=` o `rev=`",
                )
            })?;
            let reference = match key {
                "tag" => GitRef::Tag(value.to_owned()),
                "branch" => GitRef::Branch(value.to_owned()),
                "rev" => GitRef::Rev(value.to_owned()),
                other => {
                    return Err(PkgError::invalid_lock(
                        format!("referencia git desconocida: `{other}`"),
                        "usa `tag=`, `branch=` o `rev=`",
                    ));
                }
            };
            return Self::git(url, reference);
        }
        if let Some(path) = text.strip_prefix("path+") {
            return Self::path(path);
        }
        Err(PkgError::invalid_lock(
            format!("fuente desconocida: `{text}`"),
            "las fuentes empiezan por `git+` o `path+`",
        ))
    }

    /// URL, si es git.
    #[must_use]
    pub fn url(&self) -> Option<&str> {
        match self {
            Self::Git { url, .. } => Some(url),
            Self::Path { .. } => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonico_ida_y_vuelta() {
        for source in [
            Source::git("https://example.com/x", GitRef::Tag("v1".into())).expect("git"),
            Source::git("https://example.com/x", GitRef::Branch("main".into())).expect("git"),
            Source::git("https://example.com/x", GitRef::Rev("abc".into())).expect("git"),
            Source::path("../local").expect("path"),
        ] {
            let text = source.canonical();
            assert_eq!(Source::parse(&text), Ok(source));
        }
    }

    #[test]
    fn rechaza_git_sin_referencia() {
        assert!(Source::parse("git+https://example.com/x").is_err());
        assert!(Source::git("", GitRef::Tag("v1".into())).is_err());
        assert!(Source::git("https://example.com/x", GitRef::Tag(" ".into())).is_err());
    }

    #[test]
    fn rev_es_inmovil() {
        assert!(GitRef::Rev("abc".into()).is_rev());
        assert!(!GitRef::Tag("v1".into()).is_rev());
        assert!(!GitRef::Branch("main".into()).is_rev());
    }
}
