//! Checker de ownership y préstamos (C4).
//!
//! C4 cubre move/Copy/Clone, préstamos, inicialización, mutabilidad y
//! escapes básicos. La inferencia NLL fina y las closures quedan para C5.

mod ownership;

pub use ownership::{OwnershipResult, check_ownership, check_ownership_with};
