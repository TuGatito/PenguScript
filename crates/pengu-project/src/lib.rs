//! Descubrimiento y validación básica de proyectos PenguScript.

use std::path::{Path, PathBuf};

use pengu_diag::Diagnostic;
use pengu_span::{FileId, Span};

/// Dependencia declarada en `Tome.toml`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Dependency {
    /// Nombre.
    pub name: String,
    /// Fuente git, si existe.
    pub git: Option<String>,
    /// Ruta local, si existe.
    pub path: Option<String>,
    /// Tag git.
    pub tag: Option<String>,
    /// Rama git.
    pub branch: Option<String>,
    /// Revisión git.
    pub rev: Option<String>,
    /// Features de Cargo.
    pub features: Vec<String>,
    /// `default-features` de Cargo.
    pub default_features: bool,
    /// Dependencia opcional.
    pub optional: bool,
}

impl Default for Dependency {
    fn default() -> Self {
        Self {
            name: String::new(),
            git: None,
            path: None,
            tag: None,
            branch: None,
            rev: None,
            features: Vec::new(),
            default_features: true,
            optional: false,
        }
    }
}

/// Feature declarada en `Tome.toml`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Feature {
    /// Nombre.
    pub name: String,
    /// Features que activa.
    pub enables: Vec<String>,
}

/// Declaración `.d.pengu` del manifiesto (`[declarations]`).
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Declaration {
    /// Nombre del módulo con el que se importa (`summon <nombre>::item`).
    pub name: String,
    /// Ruta relativa al manifiesto.
    pub path: PathBuf,
}

/// Manifiesto mínimo de `Tome.toml`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Manifest {
    /// Nombre del proyecto.
    pub name: String,
    /// Versión.
    pub version: String,
    /// Versión de PenguScript requerida.
    pub pengu: String,
    /// Edición.
    pub edition: String,
    /// Versión mínima de Rust.
    pub rust_version: String,
    /// Features.
    pub features: Vec<Feature>,
    /// Dependencias.
    pub dependencies: Vec<Dependency>,
    /// Binarios declarados.
    pub bins: Vec<String>,
    /// Librería declarada.
    pub lib: Option<String>,
    /// Librerías de `[link]`.
    pub links: Vec<String>,
    /// Declaraciones `.d.pengu` de `[declarations]`.
    pub declarations: Vec<Declaration>,
    /// Nombres de dependencias duplicadas detectadas al parsear.
    pub duplicate_dependencies: Vec<String>,
}

/// Resultado de cargar un proyecto.
#[derive(Clone, Debug, Default)]
pub struct LoadedProject {
    /// Manifiesto, si se pudo parsear.
    pub manifest: Option<Manifest>,
    /// Ruta del manifiesto.
    pub manifest_path: Option<PathBuf>,
    /// Diagnósticos.
    pub diagnostics: Vec<Diagnostic>,
}

fn span(source: &str) -> Span {
    Span::new(FileId::new(0), 0, source.len() as u32)
}

/// Carga y valida un proyecto en `root`.
#[must_use]
pub fn load(root: &Path) -> LoadedProject {
    let manifest_path = root.join("Tome.toml");
    let mut loaded = LoadedProject::default();
    let Ok(source) = std::fs::read_to_string(&manifest_path) else {
        loaded.diagnostics.push(Diagnostic::error(
            "PGS-E2001",
            "no se encuentra `Tome.toml`",
            span(""),
        ));
        return loaded;
    };
    let manifest = match parse_manifest(&source) {
        Ok(manifest) => manifest,
        Err(diagnostic) => {
            loaded.diagnostics.push(*diagnostic);
            return loaded;
        }
    };
    loaded
        .diagnostics
        .extend(validate_manifest(&manifest, root));
    let has_bin = !manifest.bins.is_empty() && root.join("main.pengu").is_file();
    let has_lib = manifest.lib.is_some() && root.join("lib.pengu").is_file();
    if !has_bin && !has_lib {
        loaded.diagnostics.push(Diagnostic::error(
            "PGS-E2002",
            "el proyecto necesita `main.pengu` o `lib.pengu`",
            span(&source),
        ));
    }
    loaded.manifest = Some(manifest);
    loaded.manifest_path = Some(manifest_path);
    loaded
}

fn parse_array(value: &str) -> Vec<String> {
    value
        .trim()
        .trim_matches(|c| c == '[' || c == ']')
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .map(|part| part.trim_matches('"').to_owned())
        .collect()
}

/// Parsea un `Tome.toml` mínimo.
pub fn parse_manifest(source: &str) -> Result<Manifest, Box<Diagnostic>> {
    let full_span = span(source);
    let mut manifest = Manifest::default();
    let mut section = String::new();
    let mut saw_tome = false;
    for line in source.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            let inner = line[1..line.len() - 1].trim();
            section = inner
                .trim_start_matches('[')
                .trim_end_matches(']')
                .trim()
                .to_owned();
            if section == "tome" {
                saw_tome = true;
            }
            continue;
        }
        if section == "link" && !line.contains('=') {
            manifest.links.push(line.trim_matches('"').to_owned());
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            return Err(Box::new(Diagnostic::error(
                "PGS-E2010",
                "`Tome.toml` inválido: se esperaba `clave = valor`",
                full_span,
            )));
        };
        let key = key.trim();
        let value = value.trim();
        match section.as_str() {
            "tome" => {
                let value = value.trim_matches('"').to_owned();
                match key {
                    "name" => manifest.name = value,
                    "version" => manifest.version = value,
                    "pengu" => manifest.pengu = value,
                    "edition" => manifest.edition = value,
                    "rust-version" => manifest.rust_version = value,
                    "lib" => manifest.lib = Some(value),
                    _ => {}
                }
            }
            "bin" => {
                if key == "name" {
                    manifest.bins.push(value.trim_matches('"').to_owned());
                }
            }
            "lib" => {
                if key == "name" || key == "path" {
                    manifest.lib = Some(value.trim_matches('"').to_owned());
                }
            }
            "dependencies" => {
                let mut dep = Dependency {
                    name: key.to_owned(),
                    ..Dependency::default()
                };
                if value.starts_with('{') {
                    for part in value.trim_matches(|c| c == '{' || c == '}').split(',') {
                        let Some((k, v)) = part.split_once('=') else {
                            continue;
                        };
                        let v = v.trim().trim_matches('"').to_owned();
                        match k.trim() {
                            "git" => dep.git = Some(v),
                            "path" => dep.path = Some(v),
                            "tag" => dep.tag = Some(v),
                            "branch" => dep.branch = Some(v),
                            "rev" => dep.rev = Some(v),
                            "features" => dep.features = parse_array(&v),
                            "default-features" => dep.default_features = v != "false",
                            "optional" => dep.optional = v == "true",
                            _ => {}
                        }
                    }
                } else {
                    dep.path = Some(value.trim_matches('"').to_owned());
                }
                if manifest
                    .dependencies
                    .iter()
                    .any(|other| other.name == dep.name)
                {
                    manifest.duplicate_dependencies.push(dep.name.clone());
                }
                manifest.dependencies.push(dep);
            }
            "features" => {
                manifest.features.push(Feature {
                    name: key.to_owned(),
                    enables: parse_array(value),
                });
            }
            "link" => manifest.links.push(value.trim_matches('"').to_owned()),
            "declarations" => {
                if manifest.declarations.iter().any(|other| other.name == key) {
                    return Err(Box::new(Diagnostic::error(
                        "PGS-E2013",
                        format!("el módulo `{key}` está declarado más de una vez"),
                        full_span,
                    )));
                }
                manifest.declarations.push(Declaration {
                    name: key.to_owned(),
                    path: PathBuf::from(value.trim_matches('"')),
                });
            }
            _ => {}
        }
    }
    if !saw_tome {
        return Err(Box::new(Diagnostic::error(
            "PGS-E2010",
            "`Tome.toml` inválido: falta `[tome]`",
            full_span,
        )));
    }
    Ok(manifest)
}

fn is_identifier(name: &str) -> bool {
    let mut chars = name.chars();
    chars
        .next()
        .is_some_and(|first| first.is_ascii_alphabetic() || first == '_')
        && chars.all(|ch| ch.is_ascii_alphanumeric() || ch == '_')
}

/// Valida las reglas del manifiesto que no requieren lockfile.
#[must_use]
pub fn validate_manifest(manifest: &Manifest, root: &Path) -> Vec<Diagnostic> {
    let mut diagnostics = Vec::new();
    let at = span("");
    if manifest.pengu != "0.6" {
        diagnostics.push(Diagnostic::error(
            "PGS-E1802",
            format!("se requiere PenguScript 0.6, no `{}`", manifest.pengu),
            at,
        ));
    }
    for name in &manifest.duplicate_dependencies {
        diagnostics.push(Diagnostic::error(
            "PGS-E1807",
            format!("la dependencia `{name}` está declarada más de una vez"),
            at,
        ));
    }
    for declaration in &manifest.declarations {
        if !is_identifier(&declaration.name) {
            diagnostics.push(Diagnostic::error(
                "PGS-E2010",
                format!(
                    "el nombre de declaración `{}` no es un identificador válido",
                    declaration.name
                ),
                at,
            ));
        }
        let extension_ok = declaration
            .path
            .extension()
            .is_some_and(|extension| extension == "d.pengu")
            || declaration.path.to_string_lossy().ends_with(".d.pengu");
        if !extension_ok {
            diagnostics.push(Diagnostic::error(
                "PGS-E2020",
                format!(
                    "la declaración `{}` debe apuntar a un archivo `.d.pengu`",
                    declaration.name
                ),
                at,
            ));
        }
        if !root.join(&declaration.path).is_file() {
            diagnostics.push(Diagnostic::error(
                "PGS-E2003",
                format!(
                    "no se encuentra la declaración `{}` en `{}`",
                    declaration.name,
                    declaration.path.display()
                ),
                at,
            ));
        }
    }
    for dep in &manifest.dependencies {
        if dep.git.is_some() && dep.tag.is_none() && dep.branch.is_none() && dep.rev.is_none() {
            diagnostics.push(Diagnostic::error(
                "PGS-E1806",
                format!(
                    "la dependencia git `{}` no fija tag, branch ni rev",
                    dep.name
                ),
                at,
            ));
        }
        if let Some(path) = &dep.path {
            if !root.join(path).exists() {
                diagnostics.push(Diagnostic::error(
                    "PGS-E1803",
                    format!("no se encuentra la dependencia `{}`", dep.name),
                    at,
                ));
            }
        }
    }
    diagnostics
}

/// Valida un `Tome.lock` contra el manifiesto.
#[must_use]
pub fn validate_lock(manifest: &Manifest, lock: &str) -> Vec<Diagnostic> {
    let at = span(lock);
    let mut diagnostics = Vec::new();
    if !lock.lines().any(|line| line.trim() == "version = 1") {
        diagnostics.push(Diagnostic::error(
            "PGS-E1808",
            "`Tome.lock` inválido: falta `version = 1`",
            at,
        ));
        return diagnostics;
    }
    let version = lock.lines().find_map(|line| {
        let (key, value) = line.split_once('=')?;
        (key.trim() == "version" && value.trim() != "1").then(|| value.trim().to_owned())
    });
    if let Some(version) = version {
        if !version.is_empty() && manifest.version != version {
            diagnostics.push(Diagnostic::error(
                "PGS-E1804",
                "`Tome.lock` está desactualizado respecto a `Tome.toml`",
                at,
            ));
        }
    }
    diagnostics
}

/// Valida que una ABI que enlaza bibliotecas tenga una entrada `[link]`.
#[must_use]
pub fn validate_link(abi: &str, manifest: &Manifest) -> Option<Diagnostic> {
    if matches!(abi, "C" | "system") && manifest.links.is_empty() {
        Some(Diagnostic::error(
            "PGS-E2023",
            "`abi \"C\"`/`\"system\"` requiere una entrada en `[link]`",
            span(""),
        ))
    } else {
        None
    }
}

/// Comprueba que una dependencia esté declarada.
#[must_use]
pub fn require_dependency(manifest: &Manifest, name: &str) -> Option<Diagnostic> {
    if manifest.dependencies.iter().any(|dep| dep.name == name) {
        None
    } else {
        Some(Diagnostic::error(
            "PGS-E2011",
            format!("la dependencia `{name}` no está declarada en `Tome.toml`"),
            span(""),
        ))
    }
}

/// Comprueba que un error del backend tenga un span PenguScript asociado.
#[must_use]
pub fn map_backend_error(has_mapping: bool) -> Option<Diagnostic> {
    if has_mapping {
        None
    } else {
        Some(Diagnostic::error(
            "PGS-E2014",
            "error del backend sin mapeo a PenguScript",
            span(""),
        ))
    }
}

impl Manifest {
    /// Genera el `Cargo.toml` equivalente para el backend Rust.
    #[must_use]
    pub fn to_cargo_toml(&self) -> String {
        self.to_cargo_toml_with_base(Path::new("."))
    }

    /// Genera el `Cargo.toml` resolviendo dependencias `path` relativas a `base`.
    #[must_use]
    pub fn to_cargo_toml_with_base(&self, base: &Path) -> String {
        let mut out = String::new();
        out.push_str("[package]\n");
        out.push_str(&format!("name = \"{}\"\n", self.name));
        out.push_str(&format!("version = \"{}\"\n", self.version));
        out.push_str(&format!("edition = \"{}\"\n", self.edition));
        let rust_version = if self.rust_version.is_empty() {
            "1.85.0"
        } else {
            &self.rust_version
        };
        out.push_str(&format!("rust-version = \"{rust_version}\"\n"));
        out.push_str("build = \"build.rs\"\n\n");
        out.push_str("[profile.dev]\noverflow-checks = true\n\n");
        out.push_str("[profile.release]\noverflow-checks = true\n");
        if !self.features.is_empty() {
            out.push_str("\n[features]\n");
            for feature in &self.features {
                let values = feature
                    .enables
                    .iter()
                    .map(|value| format!("\"{value}\""))
                    .collect::<Vec<_>>()
                    .join(", ");
                out.push_str(&format!("{} = [{}]\n", feature.name, values));
            }
        }
        out.push_str("\n[dependencies]\n");
        for dependency in &self.dependencies {
            out.push_str(&format!("{} = ", dependency.name));
            let mut fields = Vec::new();
            if let Some(path) = &dependency.path {
                let resolved = if Path::new(path).is_absolute() {
                    PathBuf::from(path)
                } else {
                    base.join(path)
                };
                fields.push(format!("path = \"{}\"", resolved.display()));
            } else if let Some(git) = &dependency.git {
                fields.push(format!("git = \"{git}\""));
                if let Some(tag) = &dependency.tag {
                    fields.push(format!("tag = \"{tag}\""));
                }
                if let Some(branch) = &dependency.branch {
                    fields.push(format!("branch = \"{branch}\""));
                }
                if let Some(rev) = &dependency.rev {
                    fields.push(format!("rev = \"{rev}\""));
                }
            }
            if !dependency.features.is_empty() {
                let values = dependency
                    .features
                    .iter()
                    .map(|value| format!("\"{value}\""))
                    .collect::<Vec<_>>()
                    .join(", ");
                fields.push(format!("features = [{values}]"));
            }
            if !dependency.default_features {
                fields.push("default-features = false".to_owned());
            }
            if dependency.optional {
                fields.push("optional = true".to_owned());
            }
            out.push_str(&format!("{{ {} }}\n", fields.join(", ")));
        }
        if self.lib.is_some() {
            out.push_str("\n[lib]\npath = \"src/lib.rs\"\n");
        }
        for bin in &self.bins {
            out.push_str("\n[[bin]]\n");
            out.push_str(&format!("name = \"{bin}\"\npath = \"src/main.rs\"\n"));
        }
        out
    }

    /// Genera el `build.rs` que enlaza las librerías de `[link]`.
    #[must_use]
    pub fn build_rs(&self) -> String {
        let mut out = String::from("fn main() {\n");
        for link in &self.links {
            out.push_str(&format!("    println!(\"cargo:rustc-link-lib={link}\");\n"));
        }
        out.push_str("}\n");
        out
    }
}

#[cfg(test)]
mod cargo_tests {
    use super::*;

    #[test]
    fn renders_cargo_toml_and_build_rs() {
        let manifest = Manifest {
            name: "demo".to_owned(),
            version: "0.1.0".to_owned(),
            pengu: "1.85.0".to_owned(),
            edition: "2024".to_owned(),
            dependencies: vec![Dependency {
                name: "util".to_owned(),
                git: Some("https://example.com/util".to_owned()),
                tag: Some("v1".to_owned()),
                ..Dependency::default()
            }],
            bins: vec!["demo".to_owned()],
            lib: Some("demo".to_owned()),
            links: vec!["m".to_owned()],
            ..Manifest::default()
        };
        let cargo = manifest.to_cargo_toml();
        assert!(cargo.contains("name = \"demo\""));
        assert!(cargo.contains("git = \"https://example.com/util\""));
        assert!(cargo.contains("tag = \"v1\""));
        assert!(cargo.contains("[[bin]]"));
        assert!(cargo.contains("build = \"build.rs\""));
        assert!(cargo.contains("rust-version = \"1.85.0\""));
        assert!(cargo.contains("[profile.dev]"));
        assert!(cargo.contains("overflow-checks = true"));
        assert!(manifest.build_rs().contains("rustc-link-lib=m"));
    }
}
