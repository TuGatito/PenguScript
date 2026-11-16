//! Caché incremental por contenido.
//!
//! El build es determinista: mismas fuentes, mismo manifiesto y misma stdlib
//! producen el mismo Rust. Por eso basta con un fingerprint SHA-256 de todas
//! las entradas para saber si el árbol emitido sigue siendo válido y ahorrarse
//! tanto la generación como la invocación de Cargo.
//!
//! El fingerprint se escribe **después** de un build correcto: si el proceso
//! muere a medias, el siguiente build vuelve a compilar.

use std::path::{Path, PathBuf};

use pengu_json::{Value, render};
use pengu_sha256::{Sha256, hex};

/// Versión del formato de caché; se sube cuando cambia lo que se emite.
pub const CACHE_VERSION: u32 = 1;

/// Nombre del archivo de caché dentro de `target/pengu`.
const CACHE_FILE: &str = "cache.json";

/// Datos guardados tras un build correcto.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Cache {
    /// Fingerprint de las entradas.
    pub fingerprint: String,
    /// Nombre del binario emitido, si el proyecto es un binario.
    pub bin_name: Option<String>,
}

impl Cache {
    /// Lee la caché del proyecto, si existe y es válida.
    #[must_use]
    pub fn read(root: &Path) -> Option<Self> {
        let text = std::fs::read_to_string(cache_path(root)).ok()?;
        let value = pengu_json::parse(&text).ok()?;
        if value.get("version").and_then(Value::as_i64) != Some(i64::from(CACHE_VERSION)) {
            return None;
        }
        let fingerprint = value.get("fingerprint").and_then(Value::as_str)?.to_owned();
        let bin_name = value
            .get("bin_name")
            .and_then(Value::as_str)
            .map(str::to_owned);
        Some(Self {
            fingerprint,
            bin_name,
        })
    }

    /// Escribe la caché de forma atómica.
    ///
    /// # Errors
    /// Devuelve el error de E/S si no se puede escribir.
    pub fn write(&self, root: &Path) -> std::io::Result<()> {
        let path = cache_path(root);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let bin_name = self
            .bin_name
            .as_deref()
            .map_or(Value::Null, |name| Value::Str(name.to_owned()));
        let value = Value::object([
            ("version", Value::Int(i64::from(CACHE_VERSION))),
            ("fingerprint", Value::Str(self.fingerprint.clone())),
            ("bin_name", bin_name),
        ]);
        let temporary = path.with_extension("tmp");
        std::fs::write(&temporary, render(&value))?;
        std::fs::rename(temporary, path)
    }

    /// `true` si la caché corresponde al fingerprint actual.
    #[must_use]
    pub fn matches(&self, fingerprint: &str) -> bool {
        self.fingerprint == fingerprint
    }
}

/// Ruta del archivo de caché.
#[must_use]
pub fn cache_path(root: &Path) -> PathBuf {
    root.join("target").join("pengu").join(CACHE_FILE)
}

/// Ruta del binario emitido (dentro del `target` de la crate generada).
#[must_use]
pub fn binary_path(root: &Path, bin_name: &str) -> PathBuf {
    root.join("target")
        .join("pengu")
        .join("target")
        .join("debug")
        .join(bin_name)
}

/// Calcula el fingerprint de todas las entradas del build.
#[must_use]
pub fn fingerprint(root: &Path, packages: &[(String, PathBuf)]) -> String {
    let mut hasher = Sha256::new();
    let mut feed = |label: &str, bytes: &[u8]| {
        hasher.update(label.as_bytes());
        hasher.update(&[0]);
        hasher.update(&(bytes.len() as u64).to_le_bytes());
        hasher.update(bytes);
    };
    feed("cache", &CACHE_VERSION.to_le_bytes());
    feed("driver", env!("CARGO_PKG_VERSION").as_bytes());
    if let Ok(manifest) = std::fs::read(root.join("Tome.toml")) {
        feed("manifest", &manifest);
    }
    for name in ["main.pengu", "lib.pengu"] {
        if let Ok(source) = std::fs::read(root.join(name)) {
            feed(name, &source);
        }
    }
    for (name, dir) in packages {
        feed("package", name.as_bytes());
        for file in ["lib.pengu", "main.pengu"] {
            if let Ok(source) = std::fs::read(dir.join(file)) {
                feed(file, &source);
                break;
            }
        }
    }
    for file in pengu_std::files() {
        feed(file.name, file.text.as_bytes());
    }
    hex(&hasher.finish())
}
