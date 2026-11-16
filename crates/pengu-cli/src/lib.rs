//! CLI de `PenguScript`: `pengu fetch|tree|build|run|test`.
//!
//! La lógica vive aquí (no en `main.rs`) para poder probarla desde tests de integración
//! sin depender del proceso.

pub mod args;
pub mod commands;
pub mod env;
pub mod release;
pub mod templates;
pub mod watch;

/// Punto de entrada: parsea, ejecuta y devuelve el código de salida.
#[must_use]
pub fn run(args: &[String]) -> i32 {
    match args::parse(args) {
        Ok(cli) => commands::dispatch(&cli),
        Err(message) => {
            eprintln!("error: {message}");
            2
        }
    }
}
