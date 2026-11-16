//! `Tome.lock`: lectura, validación y escritura determinista.
//!
//! El formato lo fija `docs/LANGUAGE.md` §18.3: `version = 1` y una entrada
//! `[[package]]` por paquete con `name`, `version`, `source`, `commit`, `checksum`,
//! `features` y `dependencies`, ordenadas por `name` y sin repeticiones.

use std::collections::BTreeMap;
use std::path::Path;

use crate::PkgError;
use crate::source::Source;
use crate::toml::{self, Value};

/// Versión del formato del lock.
pub const LOCK_VERSION: u32 = 1;

/// Nombre del archivo.
pub const LOCK_FILE: &str = "Tome.lock";

/// Entrada del lock.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LockedPackage {
    /// Nombre del paquete.
    pub name: String,
    /// Versión declarada en su `Tome.toml`.
    pub version: String,
    /// Fuente canónica (`git+…`/`path+…`).
    pub source: String,
    /// Commit completo (vacío para `path`).
    pub commit: String,
    /// Checksum canónico del árbol (`sha256-<hex>`).
    pub checksum: String,
    /// Features activadas.
    pub features: Vec<String>,
    /// Nombres de dependencias directas.
    pub dependencies: Vec<String>,
}

/// Contenido completo de `Tome.lock`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Lockfile {
    /// Versión del formato.
    pub version: u32,
    /// Paquetes ordenados por nombre.
    pub packages: Vec<LockedPackage>,
}

impl Lockfile {
    /// Crea un lock normalizando orden y comprobando que no haya nombres repetidos.
    ///
    /// # Errors
    /// Devuelve `PGS-E1807` si dos paquetes comparten nombre.
    pub fn new(mut packages: Vec<LockedPackage>) -> Result<Self, PkgError> {
        packages.sort_by(|left, right| left.name.cmp(&right.name));
        for pair in packages.windows(2) {
            if pair[0].name == pair[1].name {
                return Err(PkgError::plain(
                    "PGS-E1807",
                    format!(
                        "`{}` aparece dos veces en el lock con fuentes distintas",
                        pair[0].name
                    ),
                )
                .with_help("elimina `Tome.lock` y ejecuta `pengu fetch`"));
            }
        }
        Ok(Self {
            version: LOCK_VERSION,
            packages,
        })
    }

    /// Busca un paquete por nombre.
    #[must_use]
    pub fn package(&self, name: &str) -> Option<&LockedPackage> {
        self.packages.iter().find(|package| package.name == name)
    }

    /// Parsea y valida un lock.
    ///
    /// # Errors
    /// Devuelve `PGS-E1808` si el TOML es inválido, falta un campo, el checksum no
    /// tiene el formato canónico o las dependencias referencian paquetes ausentes.
    pub fn parse(text: &str) -> Result<Self, PkgError> {
        let table = toml::parse(text).map_err(|error| {
            PkgError::invalid_lock(
                format!("Tome.lock inválido: {error}"),
                "revisa el archivo o bórralo para regenerarlo",
            )
        })?;
        let version = table
            .get("version")
            .and_then(Value::as_integer)
            .ok_or_else(|| missing("version"))?;
        let version = u32::try_from(version).map_err(|_| {
            PkgError::invalid_lock(
                format!("`version = {version}` no es válido en Tome.lock"),
                "el formato actual es `version = 1`",
            )
        })?;
        if version != LOCK_VERSION {
            return Err(PkgError::invalid_lock(
                format!("Tome.lock usa la versión {version} y se esperaba {LOCK_VERSION}"),
                "bórralo y ejecuta `pengu fetch` para regenerarlo",
            ));
        }
        // Un lock sin paquetes es válido: un proyecto sin dependencias lo escribe así.
        let raw = match table.get("package") {
            Some(value) => value.as_array().ok_or_else(|| missing("[[package]]"))?,
            None => &Vec::new(),
        };
        let mut packages = Vec::with_capacity(raw.len());
        for value in raw {
            let entry = value
                .as_table()
                .ok_or_else(|| missing("[[package]] como tabla"))?;
            packages.push(parse_package(entry)?);
        }
        let lock = Self::new(packages)?;
        for package in &lock.packages {
            for dependency in &package.dependencies {
                if lock.package(dependency).is_none() {
                    return Err(PkgError::invalid_lock(
                        format!(
                            "`{}` depende de `{dependency}`, que no está en el lock",
                            package.name
                        ),
                        "bórralo y ejecuta `pengu fetch`",
                    ));
                }
            }
            Source::parse(&package.source)?;
            if crate::sha256::parse_checksum(&package.checksum).is_none() {
                return Err(PkgError::invalid_lock(
                    format!(
                        "checksum de `{}` con formato inválido: `{}`",
                        package.name, package.checksum
                    ),
                    "bórralo y ejecuta `pengu fetch`",
                ));
            }
        }
        Ok(lock)
    }

    /// Serializa el lock de forma determinista.
    #[must_use]
    pub fn render(&self) -> String {
        use std::fmt::Write as _;
        let mut out = String::from("# Generado por `pengu`. No editar a mano.\n");
        writeln!(out, "version = {}", self.version).expect("escribir en String");
        for package in &self.packages {
            out.push_str("\n[[package]]\n");
            writeln!(out, "name = \"{}\"", package.name).expect("escribir");
            writeln!(out, "version = \"{}\"", package.version).expect("escribir");
            writeln!(out, "source = \"{}\"", package.source).expect("escribir");
            writeln!(out, "commit = \"{}\"", package.commit).expect("escribir");
            writeln!(out, "checksum = \"{}\"", package.checksum).expect("escribir");
            writeln!(out, "features = {}", render_list(&package.features)).expect("escribir");
            writeln!(out, "dependencies = {}", render_list(&package.dependencies))
                .expect("escribir");
        }
        out
    }

    /// Lee el lock de `directory`, si existe.
    ///
    /// # Errors
    /// Devuelve `PGS-E1808` si el archivo existe pero no es válido.
    pub fn read(directory: &Path) -> Result<Option<Self>, PkgError> {
        let path = directory.join(LOCK_FILE);
        if !path.exists() {
            return Ok(None);
        }
        let text = std::fs::read_to_string(&path).map_err(|error| {
            crate::io_error(
                "PGS-E1808",
                &format!("no se puede leer `{}`", path.display()),
                &error,
            )
        })?;
        Self::parse(&text).map(Some)
    }

    /// Escribe el lock con escritura atómica (`<archivo>.tmp` + rename).
    ///
    /// # Errors
    /// Devuelve `PGS-E1808` si no se puede escribir.
    pub fn write(&self, directory: &Path) -> Result<(), PkgError> {
        let path = directory.join(LOCK_FILE);
        let temp = directory.join(format!("{LOCK_FILE}.tmp"));
        std::fs::write(&temp, self.render()).map_err(|error| {
            crate::io_error(
                "PGS-E1808",
                &format!("no se puede escribir `{}`", temp.display()),
                &error,
            )
        })?;
        std::fs::rename(&temp, &path).map_err(|error| {
            crate::io_error(
                "PGS-E1808",
                &format!("no se puede renombrar `{}`", temp.display()),
                &error,
            )
        })
    }

    /// Comprueba que las dependencias declaradas siguen coincidiendo con el lock.
    ///
    /// # Errors
    /// Devuelve `PGS-E1804` si falta un paquete o cambió su fuente.
    pub fn matches(&self, declared: &BTreeMap<String, Source>) -> Result<(), PkgError> {
        for (name, source) in declared {
            let Some(package) = self.package(name) else {
                return Err(stale(format!(
                    "`{name}` está en `Tome.toml` y no en `Tome.lock`"
                )));
            };
            if package.source != source.canonical() {
                return Err(stale(format!(
                    "la fuente de `{name}` cambió: el lock tiene `{}` y el manifiesto `{}`",
                    package.source,
                    source.canonical()
                )));
            }
        }
        Ok(())
    }
}

fn parse_package(table: &toml::Table) -> Result<LockedPackage, PkgError> {
    Ok(LockedPackage {
        name: string(table, "name")?,
        version: string(table, "version")?,
        source: string(table, "source")?,
        commit: string(table, "commit")?,
        checksum: string(table, "checksum")?,
        features: list(table, "features")?,
        dependencies: list(table, "dependencies")?,
    })
}

fn string(table: &toml::Table, key: &str) -> Result<String, PkgError> {
    table
        .get(key)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| missing(key))
}

fn list(table: &toml::Table, key: &str) -> Result<Vec<String>, PkgError> {
    let values = table
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| missing(key))?;
    let mut out = Vec::with_capacity(values.len());
    for value in values {
        let text = value
            .as_str()
            .ok_or_else(|| missing(&format!("`{key}` de tipo cadena")))?;
        out.push(text.to_owned());
    }
    out.sort();
    out.dedup();
    Ok(out)
}

fn render_list(values: &[String]) -> String {
    let mut sorted = values.to_vec();
    sorted.sort();
    sorted.dedup();
    let items: Vec<String> = sorted.iter().map(|value| format!("\"{value}\"")).collect();
    format!("[{}]", items.join(", "))
}

fn missing(key: &str) -> PkgError {
    PkgError::invalid_lock(
        format!("Tome.lock no tiene `{key}`"),
        "bórralo y ejecuta `pengu fetch` para regenerarlo",
    )
}

fn stale(message: String) -> PkgError {
    PkgError::stale_lock(message, "ejecuta `pengu fetch` para actualizar `Tome.lock`")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Lockfile {
        Lockfile::new(vec![
            LockedPackage {
                name: "text".into(),
                version: "1.2.3".into(),
                source: "git+https://example.com/text?tag=v1".into(),
                commit: "aaaa".into(),
                checksum: format!("sha256-{}", "ab".repeat(32)),
                features: vec!["std".into()],
                dependencies: Vec::new(),
            },
            LockedPackage {
                name: "json".into(),
                version: "0.3.1".into(),
                source: "git+https://example.com/json?tag=v1".into(),
                commit: "bbbb".into(),
                checksum: format!("sha256-{}", "cd".repeat(32)),
                features: Vec::new(),
                dependencies: vec!["text".into()],
            },
        ])
        .expect("lock")
    }

    #[test]
    fn ida_y_vuelta_con_orden() {
        let lock = sample();
        assert_eq!(lock.packages[0].name, "json");
        let text = lock.render();
        let parsed = Lockfile::parse(&text).expect("parse");
        assert_eq!(parsed, lock);
        assert!(text.contains("dependencies = [\"text\"]"));
    }

    #[test]
    fn rechaza_duplicados() {
        let package = LockedPackage {
            name: "a".into(),
            version: "1.0.0".into(),
            source: "git+https://example.com/a?rev=1".into(),
            commit: "1".into(),
            checksum: format!("sha256-{}", "00".repeat(32)),
            features: Vec::new(),
            dependencies: Vec::new(),
        };
        let error = Lockfile::new(vec![package.clone(), package]).expect_err("dup");
        assert_eq!(error.code(), "PGS-E1807");
    }

    #[test]
    fn rechaza_checksum_malo_y_version() {
        let mut text = sample().render();
        text = text.replace(&format!("sha256-{}", "ab".repeat(32)), "sha256-corto");
        assert_eq!(
            Lockfile::parse(&text).expect_err("checksum").code(),
            "PGS-E1808"
        );
        let bad_version = sample().render().replace("version = 1", "version = 2");
        assert_eq!(
            Lockfile::parse(&bad_version).expect_err("version").code(),
            "PGS-E1808"
        );
    }

    #[test]
    fn detecta_lock_desactualizado() {
        let lock = sample();
        let mut declared = BTreeMap::new();
        declared.insert(
            "json".to_owned(),
            Source::git(
                "https://example.com/json",
                crate::source::GitRef::Tag("v1".into()),
            )
            .expect("source"),
        );
        assert!(lock.matches(&declared).is_ok());
        declared.insert(
            "json".to_owned(),
            Source::git(
                "https://example.com/json",
                crate::source::GitRef::Tag("v2".into()),
            )
            .expect("source"),
        );
        assert_eq!(
            lock.matches(&declared).expect_err("stale").code(),
            "PGS-E1804"
        );
    }
}
