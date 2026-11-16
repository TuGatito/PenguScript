//! Servidor de lenguaje de `PenguScript` (Fase 6, LSP base).
//!
//! El crate no tiene dependencias externas: implementa el framing de LSP, JSON,
//! URIs y la conversión de posiciones, y usa el compilador (`pengu-syntax`,
//! `pengu-hir`, `pengu-types`, `pengu-check`, `pengu-vfs`) para el análisis.

#![forbid(unsafe_code)]

pub mod advanced;
pub mod analysis;
pub mod diag;
pub mod docs;
pub mod extras;
pub mod features;
pub mod format;
pub mod framing;
pub mod hints;
pub mod index;
pub use pengu_json as json;
pub mod log;
pub mod position;
pub mod project;
pub mod refs;
pub mod render;
pub mod rpc;
pub mod semantic;
pub mod server;
pub mod sizes;
pub mod uri;

pub use server::{Config, Server, run_stdio};
