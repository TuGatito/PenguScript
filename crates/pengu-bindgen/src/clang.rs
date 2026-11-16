//! Invocación de `clang` para volcar el AST en JSON.

use std::path::Path;
use std::process::Command;

use crate::{BindgenError, Options};

/// Ejecutable de clang usado por el generador.
pub const CLANG: &str = "clang";

/// Vuelca el AST JSON de una cabecera C.
///
/// # Errors
///
/// Falla si `clang` no existe, si la cabecera no compila o si devuelve error.
pub fn dump(header: &Path, options: &Options) -> Result<String, BindgenError> {
    let mut command = Command::new(CLANG);
    command
        .arg("-Xclang")
        .arg("-ast-dump=json")
        .arg("-fsyntax-only")
        .arg("-x")
        .arg("c");
    for directory in &options.include_dirs {
        command.arg(format!("-I{directory}"));
    }
    for define in &options.defines {
        command.arg(format!("-D{define}"));
    }
    command.arg(header);
    let output = command.output().map_err(|error| {
        BindgenError::new(
            "PGS-E2101",
            format!("no se pudo ejecutar `{CLANG}`: {error}"),
        )
        .with_help("instala clang o pasa `--clang <ruta>`")
    })?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let detail = stderr.lines().next().unwrap_or("sin detalle").to_owned();
        return Err(BindgenError::new(
            "PGS-E2102",
            format!("clang no pudo analizar `{}`: {detail}", header.display()),
        ));
    }
    String::from_utf8(output.stdout)
        .map_err(|_| BindgenError::new("PGS-E2101", "la salida de clang no es UTF-8"))
}
