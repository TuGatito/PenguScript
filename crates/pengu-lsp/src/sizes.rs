//! Tamaños reales en bytes para el editor.
//!
//! Usa `pengu-layout` (el mismo motor que el verificador de `rustc`) y lo
//! reduce a una línea de hover. Un tipo sin tamaño (por ejemplo un slice) no
//! produce texto: mejor no decir nada que decir una mentira.

use std::fmt::Write as _;

use pengu_hir::{DefId, HirCrate};
use pengu_layout::{format_size, layout_of, layout_of_adt};
use pengu_types::Ty;

/// Texto breve con tamaño y alineación: `12 B (alineación 4)`.
#[must_use]
pub fn describe(ty: &Ty, krate: &HirCrate) -> Option<String> {
    let layout = layout_of(ty, krate)?;
    let mut text = format_size(layout.size);
    if layout.align > 1 {
        let _ = write!(text, " (alineación {})", format_size(layout.align));
    }
    Some(text)
}

/// Tamaño de un ADT con sus argumentos ya sustituidos.
#[must_use]
pub fn describe_adt(def: DefId, krate: &HirCrate) -> Option<String> {
    let adt = krate.adt(def)?;
    let args: Vec<Ty> = adt.generics.iter().map(|_| Ty::Error).collect();
    let layout = layout_of_adt(def, &args, krate)?;
    let mut text = format!("tamaño {}", format_size(layout.size));
    if layout.align > 1 {
        let _ = write!(text, ", alineación {}", format_size(layout.align));
    }
    if adt.kind == pengu_hir::AdtKind::Record {
        text.push_str(", campos en orden de declaración (repr C)");
    }
    Some(text)
}

/// Huella de una función: suma de parámetros y retorno.
#[must_use]
pub fn footprint(def: DefId, krate: &HirCrate) -> Option<String> {
    pengu_layout::footprint(def, krate).map(|total| format!("huella {}", format_size(total)))
}

/// Traduce el AST de un tipo a `Ty`, resolviendo tipos del programa.
pub use pengu_layout::{ast_ty, typed};

/// Línea de hover para un tipo: `tamaño 8 B, alineación 4 B`.
#[must_use]
pub fn type_line(ty: &Ty, krate: &HirCrate) -> Option<String> {
    describe(ty, krate).map(|text| format!("tamaño {text}"))
}
