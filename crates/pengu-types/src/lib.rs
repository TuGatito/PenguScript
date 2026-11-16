#![forbid(unsafe_code)]
//! Checker de tipos e inferencia (C2).
//!
//! C2 resuelve tipos del AST, infiere literales y expresiones locales y
//! comprueba firmas de funciones. No implementa ownership (C4) ni patrones
//! exhaustivos de records/sums (C3).

mod check;
mod ty;
mod unify;

pub use check::{CheckResult, Coercion, check_crate};
pub use ty::Ty;
pub use unify::Infer;
