#![forbid(unsafe_code)]
//! Generación de Rust a partir de HIR y LIR (B3).

mod codegen;
mod ssa;

pub use codegen::{Generated, SourceMap, generate};
