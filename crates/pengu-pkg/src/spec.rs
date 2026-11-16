//! Construcción de la especificación de una dependencia para `pengu add`.

use crate::PkgError;
use crate::git::Fetcher;
use crate::source::GitRef;
use crate::tags;

/// Referencia pedida al añadir una dependencia.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Requested<'a> {
    /// Etiqueta concreta.
    Tag(&'a str),
    /// Rama concreta.
    Branch(&'a str),
    /// Revisión inmóvil.
    Rev(&'a str),
    /// Ninguna: se elige la mejor disponible.
    Auto,
}

/// Especificación de dependencia ya resuelta y aviso opcional para el usuario.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Spec {
    /// Texto a escribir en `Tome.toml`: `{ git = "…", tag = "…" }`.
    pub text: String,
    /// Referencia git elegida (para poder leer el paquete antes de fijarlo).
    pub reference: Option<GitRef>,
}

/// Deriva el nombre de importación de una URL o ruta.
///
/// Quita el sufijo `.git`, se queda con el último segmento y convierte los caracteres
/// no alfanuméricos en `_`.
#[must_use]
pub fn infer_name(source: &str) -> Option<String> {
    let trimmed = source.trim_end_matches('/');
    let last = trimmed.rsplit(['/', '\\', ':']).next()?;
    let last = last.strip_suffix(".git").unwrap_or(last);
    if last.is_empty() {
        return None;
    }
    let mut name = String::with_capacity(last.len());
    for (index, ch) in last.chars().enumerate() {
        if ch.is_ascii_alphanumeric() || ch == '_' {
            if index == 0 && ch.is_ascii_digit() {
                name.push('_');
            }
            name.push(ch);
        } else {
            name.push('_');
        }
    }
    Some(name)
}

/// Construye la especificación para una dependencia git.
///
/// Sin referencia explícita elige la etiqueta de versión más alta; si no hay etiquetas
/// versionadas, fija la rama por defecto y devuelve un aviso (la rama se moverá con
/// `pengu update`).
///
/// # Errors
/// `PGS-E1806` si no hay etiquetas ni rama por defecto.
pub fn git_spec(
    fetcher: &Fetcher<'_>,
    url: &str,
    requested: Requested<'_>,
) -> Result<(Spec, Option<String>), PkgError> {
    let (spec, warning, reference) = match requested {
        Requested::Tag(tag) => (
            format!("{{ git = \"{url}\", tag = \"{tag}\" }}"),
            None,
            GitRef::Tag(tag.to_owned()),
        ),
        Requested::Branch(branch) => (
            format!("{{ git = \"{url}\", branch = \"{branch}\" }}"),
            Some(format!(
                "seguirá la rama `{branch}`: `pengu update` puede moverla"
            )),
            GitRef::Branch(branch.to_owned()),
        ),
        Requested::Rev(rev) => (
            format!("{{ git = \"{url}\", rev = \"{rev}\" }}"),
            Some(format!(
                "la revisión `{rev}` no se moverá con `pengu update`"
            )),
            GitRef::Rev(rev.to_owned()),
        ),
        Requested::Auto => {
            let available = fetcher.remote_tags(url)?;
            if let Some(tag) = tags::best_tag(&available) {
                (
                    format!("{{ git = \"{url}\", tag = \"{tag}\" }}"),
                    None,
                    GitRef::Tag(tag),
                )
            } else {
                let branch = fetcher.remote_default_branch(url)?.ok_or_else(|| {
                    PkgError::plain(
                        "PGS-E1806",
                        format!("`{url}` no publica etiquetas de versión ni una rama por defecto"),
                    )
                    .with_help("indica `--tag`, `--branch` o `--rev`")
                })?;
                (
                    format!("{{ git = \"{url}\", branch = \"{branch}\" }}"),
                    Some(format!(
                        "`{url}` no publica etiquetas de versión: se fija la rama `{branch}`, \
                         que se moverá con `pengu update`"
                    )),
                    GitRef::Branch(branch),
                )
            }
        }
    };
    Ok((
        Spec {
            text: spec,
            reference: Some(reference),
        },
        warning,
    ))
}

/// Construye la especificación de una dependencia local.
#[must_use]
pub fn path_spec(path: &str) -> Spec {
    Spec {
        text: format!("{{ path = \"{path}\" }}"),
        reference: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn infiere_nombres() {
        assert_eq!(
            infer_name("https://github.com/pengu/json.git"),
            Some("json".to_owned())
        );
        assert_eq!(infer_name("../local/"), Some("local".to_owned()));
        assert_eq!(
            infer_name("git@host:team/my-lib.git"),
            Some("my_lib".to_owned())
        );
        assert_eq!(infer_name("/"), None);
    }

    #[test]
    fn especificaciones_simples() {
        assert_eq!(path_spec("../x").text, "{ path = \"../x\" }".to_owned());
    }
}
