#![forbid(unsafe_code)]
//! HIR de `PenguScript`: módulos, definiciones, scopes y cuerpos.
//!
//! C1 resuelve nombres y construye el grafo de módulos. El checker de tipos y
//! ownership se añade en fases posteriores.

pub mod hir;
pub mod ids;
mod lower;

pub use hir::{
    AdtDef, AdtField, AdtKind, AdtVariant, Binding, Body, ConstDef, Def, DefKind, GenericParam,
    HirCrate, Local, Module, Namespace, Primitive, Res, Resolution, Scope, ScopeKind, Signature,
    Symbol, TestInfo, check_binary,
};
pub use ids::{BodyId, DefId, ItemId, LocalId, ModuleId, ScopeId};
pub use lower::{Lowered, lower_declaration, lower_program, lower_program_with_declarations};
