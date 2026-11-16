//! URIs de LSP sin dependencias: `file://` y el esquema propio `pengu-std://`.

use std::fmt;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

/// Esquema de las fuentes de la biblioteca estándar.
pub const STD_SCHEME: &str = "pengu-std";

/// URI validada.
#[derive(Clone, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub struct Uri {
    text: String,
}

impl Uri {
    /// Valida y normaliza una URI.
    ///
    /// # Errors
    /// Devuelve un mensaje si el esquema no es `file` o `pengu-std`, la ruta no
    /// es absoluta o el porcentaje está mal formado.
    pub fn parse(text: &str) -> Result<Self, String> {
        let Some(scheme) = text.split_once(':').map(|(scheme, _)| scheme) else {
            return Err(format!("URI sin esquema: `{text}`"));
        };
        if scheme != "file" && scheme != STD_SCHEME {
            return Err(format!("esquema no soportado `{scheme}` en `{text}`"));
        }
        if scheme == "file" {
            let path = file_path(text)?;
            if !path.is_absolute() {
                return Err(format!("la ruta de `{text}` no es absoluta"));
            }
        }
        Ok(Self {
            text: text.to_owned(),
        })
    }

    /// URI de un archivo del disco.
    #[must_use]
    pub fn from_path(path: &Path) -> Self {
        let mut text = String::from("file://");
        let bytes = path.to_string_lossy();
        if !bytes.starts_with('/') {
            text.push('/');
        }
        for byte in bytes.bytes() {
            match byte {
                b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~' | b'/' => {
                    text.push(char::from(byte));
                }
                other => {
                    text.push('%');
                    let _ = write!(text, "{other:02X}");
                }
            }
        }
        Self { text }
    }

    /// URI de un archivo de la stdlib embebida.
    #[must_use]
    pub fn std_file(module: &str) -> Self {
        Self {
            text: format!("{STD_SCHEME}:///std/{module}.pengu"),
        }
    }

    /// Texto de la URI.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.text
    }

    /// `true` si apunta a la stdlib.
    #[must_use]
    pub fn is_std(&self) -> bool {
        self.text.starts_with(STD_SCHEME)
    }

    /// Ruta en disco, si es una URI `file:`.
    #[must_use]
    pub fn to_path(&self) -> Option<PathBuf> {
        if self.is_std() {
            return None;
        }
        file_path(&self.text).ok()
    }

    /// Nombre de módulo de la stdlib, si aplica.
    #[must_use]
    pub fn std_module(&self) -> Option<&str> {
        let rest = self.text.strip_prefix("pengu-std:///std/")?;
        rest.strip_suffix(".pengu")
    }
}

impl fmt::Display for Uri {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.text)
    }
}

fn file_path(text: &str) -> Result<PathBuf, String> {
    let rest = text
        .strip_prefix("file://")
        .ok_or_else(|| format!("se esperaba `file://` en `{text}`"))?;
    // Autoridad: se acepta vacía o `localhost`.
    let (authority, path) = if let Some(path) = rest.strip_prefix('/') {
        (String::new(), format!("/{path}"))
    } else {
        let (authority, path) = rest
            .split_once('/')
            .ok_or_else(|| format!("falta la ruta en `{text}`"))?;
        (authority.to_owned(), format!("/{path}"))
    };
    if !authority.is_empty() && authority != "localhost" {
        return Err(format!("autoridad no soportada `{authority}`"));
    }
    let decoded = percent_decode(&path)?;
    Ok(PathBuf::from(decoded))
}

fn percent_decode(text: &str) -> Result<String, String> {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'%' {
            if index + 2 >= bytes.len() {
                return Err(format!("porcentaje incompleto en `{text}`"));
            }
            let high =
                hex(bytes[index + 1]).ok_or_else(|| format!("porcentaje inválido en `{text}`"))?;
            let low =
                hex(bytes[index + 2]).ok_or_else(|| format!("porcentaje inválido en `{text}`"))?;
            out.push(high * 16 + low);
            index += 3;
        } else {
            out.push(bytes[index]);
            index += 1;
        }
    }
    String::from_utf8(out).map_err(|_| format!("la ruta no es UTF-8: `{text}`"))
}

fn hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ida_y_vuelta_de_archivo() {
        let uri = Uri::from_path(Path::new("/tmp/uno dos/ñ.pengu"));
        assert_eq!(uri.as_str(), "file:///tmp/uno%20dos/%C3%B1.pengu");
        assert_eq!(
            uri.to_path().as_deref(),
            Some(Path::new("/tmp/uno dos/ñ.pengu"))
        );
    }

    #[test]
    fn acepta_localhost_y_rechaza_autoridad() {
        assert!(Uri::parse("file://localhost/tmp/x.pengu").is_ok());
        assert!(Uri::parse("file://otrohost/tmp/x.pengu").is_err());
    }

    #[test]
    fn reconoce_la_stdlib() {
        let uri = Uri::std_file("integrum");
        assert_eq!(uri.as_str(), "pengu-std:///std/integrum.pengu");
        assert!(uri.is_std());
        assert_eq!(uri.std_module(), Some("integrum"));
        assert!(uri.to_path().is_none());
    }

    #[test]
    fn rechaza_esquemas_y_rutas_invalidas() {
        assert!(Uri::parse("http://x/y").is_err());
        assert!(Uri::parse("file://relative").is_err());
        assert!(Uri::parse("file:///tmp/%zz").is_err());
    }
}
