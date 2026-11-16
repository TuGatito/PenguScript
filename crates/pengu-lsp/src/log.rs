//! Logging del servidor: a un archivo (`--log` o `PENGU_LSP_LOG`) o a stderr.

use std::fmt;
use std::fs::File;
use std::io::Write as _;
use std::path::Path;
use std::sync::{Mutex, OnceLock};

static SINK: OnceLock<Option<Mutex<File>>> = OnceLock::new();

/// Inicializa el destino del log. Sin ruta, todo va a stderr.
///
/// # Errors
/// Devuelve el error de E/S si no se puede abrir el archivo.
pub fn init(path: Option<&Path>) -> std::io::Result<()> {
    let sink = match path {
        Some(path) => {
            if let Some(parent) = path
                .parent()
                .filter(|parent| !parent.as_os_str().is_empty())
            {
                std::fs::create_dir_all(parent)?;
            }
            Some(Mutex::new(
                std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(path)?,
            ))
        }
        None => None,
    };
    SINK.get_or_init(|| sink);
    Ok(())
}

/// Escribe una línea de log.
pub fn write(level: &str, arguments: fmt::Arguments<'_>) {
    let line = format!("[pengu-lsp] {level} {arguments}");
    match SINK.get().and_then(Option::as_ref) {
        Some(file) => {
            if let Ok(mut file) = file.lock() {
                let _ = writeln!(file, "{line}");
                let _ = file.flush();
            }
        }
        None => eprintln!("{line}"),
    }
}

/// Log de depuración.
#[macro_export]
macro_rules! debug_log {
    ($($arg:tt)*) => {
        $crate::log::write("debug", format_args!($($arg)*))
    };
}

/// Log informativo.
#[macro_export]
macro_rules! info_log {
    ($($arg:tt)*) => {
        $crate::log::write("info", format_args!($($arg)*))
    };
}

/// Log de error.
#[macro_export]
macro_rules! error_log {
    ($($arg:tt)*) => {
        $crate::log::write("error", format_args!($($arg)*))
    };
}
