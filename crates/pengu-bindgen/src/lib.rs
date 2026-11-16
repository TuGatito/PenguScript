//! `pengu bindgen`: declara cabeceras C en `.d.pengu` a partir de clang.
//!
//! El flujo es `clang -Xclang -ast-dump=json` → [`ir::Ir`] → [`emit::render`].
//! El mapeo de tipos es explícito ([`types`]) y nunca adivina: lo que no sabe
//! representar se omite con un motivo, que se reporta al usuario.

pub mod clang;
pub mod emit;
pub mod ir;
pub mod report;
pub mod types;

use std::path::Path;

/// Error del generador.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BindgenError {
    /// Código `PGS-*`.
    pub code: &'static str,
    /// Mensaje.
    pub message: String,
    /// Ayuda opcional.
    pub help: Option<String>,
}

impl BindgenError {
    /// Construye un error con un código.
    #[must_use]
    pub fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            help: None,
        }
    }

    /// Añade una ayuda.
    #[must_use]
    pub fn with_help(mut self, help: impl Into<String>) -> Self {
        self.help = Some(help.into());
        self
    }
}

impl std::fmt::Display for BindgenError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)?;
        if let Some(help) = &self.help {
            write!(formatter, " (ayuda: {help})")?;
        }
        Ok(())
    }
}

impl std::error::Error for BindgenError {}

/// Opciones del generador.
#[derive(Clone, Debug, Default)]
pub struct Options {
    /// Directorios de inclusión (`-I`).
    pub include_dirs: Vec<String>,
    /// Definiciones (`-D`).
    pub defines: Vec<String>,
    /// Si no está vacía, solo se generan los nombres que encajan.
    pub allowlist: Vec<String>,
    /// Nombres que nunca se generan.
    pub blocklist: Vec<String>,
}

/// Resultado de generar un archivo.
#[derive(Clone, Debug)]
pub struct Generated {
    /// Contenido del `.d.pengu`.
    pub source: String,
    /// Resumen de lo generado y lo omitido.
    pub report: report::Report,
    /// Nombre de la cabecera de origen.
    pub header: String,
}

/// Genera la declaración de una cabecera C.
///
/// # Errors
///
/// Falla si `clang` no está disponible, si la cabecera no compila o si la salida
/// de clang no es JSON válido.
pub fn generate(header: &Path, options: &Options) -> Result<Generated, BindgenError> {
    let dump = clang::dump(header, options)?;
    let json = pengu_json::parse(&dump).map_err(|error| {
        BindgenError::new("PGS-E2101", format!("clang no devolvió JSON: {error}"))
    })?;
    let main_file = header.display().to_string();
    let ir = ir::Ir::from_json(&json, options, Some(&main_file))?;
    let source = emit::render(&ir, header);
    let report = report::Report::from_ir(&ir);
    Ok(Generated {
        source,
        report,
        header: main_file,
    })
}

/// Genera desde texto ya volcado por clang (útil para tests y `--ast`).
///
/// # Errors
///
/// Falla si el texto no es JSON válido.
pub fn generate_from_dump(
    header: &Path,
    dump: &str,
    options: &Options,
) -> Result<Generated, BindgenError> {
    let json = pengu_json::parse(dump).map_err(|error| {
        BindgenError::new("PGS-E2101", format!("clang no devolvió JSON: {error}"))
    })?;
    let main_file = header.display().to_string();
    let ir = ir::Ir::from_json(&json, options, Some(&main_file))?;
    let source = emit::render(&ir, header);
    let report = report::Report::from_ir(&ir);
    Ok(Generated {
        source,
        report,
        header: main_file,
    })
}
