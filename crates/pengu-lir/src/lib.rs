//! Bajada de HIR tipado a LIR explícito.

pub mod lir;
pub mod lower;
pub mod mono;

pub use lir::{
    BlockId, BuiltinVariant, DestructureTarget, LBinOp, LBlock, LExpr, LFunction, LLocal, LParam,
    LProgram, LStmt, LStringPart, LTerm, LUnOp, LocalIndex, VecAdapterKind,
};
pub use lower::lower_crate;
pub use mono::{MonoInstance, MonoPlan, plan_monomorphization};
