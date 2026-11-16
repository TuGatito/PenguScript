//! Layout de los tipos de `PenguScript`: tamaño y alineación reales en bytes.
//!
//! El backend emite `#[repr(C)]` para los `rune` y `#[repr(C, u32)]` para los
//! `enchanting`, así que el layout de los tipos nominales es el de C más un
//! discriminante `u32`. Los tipos integrados (`Vec`, `Map`, `String`, …) miden
//! lo que sus equivalentes de Rust. Los tests de `pengu-codegen` comparan este
//! motor con `std::mem::size_of` de `rustc`.
//!
//! El motor trabaja sobre [`Ty`] ya resuelto (HIR + checker) y devuelve `None`
//! cuando no puede garantizar el número (tipos sin tamaño, genéricos sin
//! instanciar, recursión infinita). La UI nunca inventa un tamaño.

use std::collections::HashMap;

use pengu_hir::{AdtKind, DefId, HirCrate};
use pengu_syntax::ast::{Type, TypeKind};
use pengu_types::Ty;

/// Tamaño y alineación de un valor, en bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Layout {
    /// Bytes que ocupa un valor.
    pub size: usize,
    /// Alineación exigida.
    pub align: usize,
    /// `true` si el tipo deja valores inválidos que `Option` puede reutilizar.
    pub niche: bool,
}

impl Layout {
    const fn new(size: usize, align: usize, niche: bool) -> Self {
        Self { size, align, niche }
    }
}

/// Alinea `offset` al siguiente múltiplo de `align` (potencia de dos).
#[must_use]
pub const fn align_to(offset: usize, align: usize) -> usize {
    if align <= 1 {
        offset
    } else {
        offset.div_ceil(align) * align
    }
}

/// Layout de `ty` dentro de `krate`.
#[must_use]
pub fn layout_of(ty: &Ty, krate: &HirCrate) -> Option<Layout> {
    layout_at(ty, krate, 0)
}

/// Size/align de un ADT ya instanciado (`Adt(def, args)`).
#[must_use]
pub fn layout_of_adt(def: DefId, args: &[Ty], krate: &HirCrate) -> Option<Layout> {
    adt_layout(def, args, krate, 0)
}

// La tabla está agrupada por familia de tipos, no por tamaño: dos familias con
// el mismo layout se quedan separadas para que el mapa siga siendo legible.
#[allow(clippy::match_same_arms)]
fn layout_at(ty: &Ty, krate: &HirCrate, depth: u32) -> Option<Layout> {
    if depth > 24 {
        return None;
    }
    Some(match ty {
        Ty::Bool => Layout::new(1, 1, true),
        Ty::Int | Ty::I32 | Ty::U32 | Ty::F32 => Layout::new(4, 4, false),
        Ty::I8 | Ty::U8 => Layout::new(1, 1, false),
        Ty::I16 | Ty::U16 => Layout::new(2, 2, false),
        Ty::I64 | Ty::Isize | Ty::U64 | Ty::Usize | Ty::Float | Ty::F64 => Layout::new(8, 8, false),
        Ty::Char => Layout::new(4, 4, true),
        Ty::String => Layout::new(24, 8, true),
        Ty::Str => Layout::new(16, 8, true),
        Ty::Unit | Ty::Never => Layout::new(0, 1, false),
        Ty::Tuple(items) => tuple_layout(items, krate, depth)?,
        Ty::Array(elem, len) => {
            let inner = layout_at(elem, krate, depth + 1)?;
            let stride = align_to(inner.size, inner.align);
            let len = usize::try_from(*len).ok()?;
            Layout::new(stride.saturating_mul(len), inner.align, false)
        }
        Ty::Slice(..) => return None,
        Ty::Ref(inner, _) => match &**inner {
            Ty::Str | Ty::CStr | Ty::Slice(..) => Layout::new(16, 8, true),
            _ => Layout::new(8, 8, true),
        },
        Ty::Ptr(_) => Layout::new(8, 8, false),
        Ty::Vec(_) => Layout::new(24, 8, true),
        Ty::Map(..) => Layout::new(48, 8, true),
        Ty::Set(_) => Layout::new(48, 8, true),
        Ty::Option(inner) => option_layout(layout_at(inner, krate, depth + 1)?),
        Ty::Result(ok, err) => enum_layout(
            &[
                layout_at(ok, krate, depth + 1)?,
                layout_at(err, krate, depth + 1)?,
            ],
            true,
        ),
        Ty::Box(_) | Ty::Rc(_) | Ty::Arc(_) => Layout::new(8, 8, true),
        Ty::Adt(def, args) => adt_layout(*def, args, krate, depth + 1)?,
        Ty::Generic(_) | Ty::Infer(_) | Ty::IntVar(_) | Ty::FloatVar(_) | Ty::Error => return None,
        Ty::CStr => Layout::new(16, 8, true),
        Ty::CString => Layout::new(8, 8, true),
        Ty::Ordering => Layout::new(1, 1, true),
        Ty::Fn(..) => Layout::new(8, 8, true),
        Ty::Range(elem) => {
            let inner = layout_at(elem, krate, depth + 1)?;
            c_layout(&[inner, inner], false)
        }
        Ty::Iterator(_) => Layout::new(16, 8, true),
    })
}

fn tuple_layout(items: &[Ty], krate: &HirCrate, depth: u32) -> Option<Layout> {
    let mut layouts = Vec::with_capacity(items.len());
    for item in items {
        layouts.push(layout_at(item, krate, depth + 1)?);
    }
    // Rust ordena los campos de una tupla por alineación descendente (estable).
    layouts.sort_by_key(|layout| std::cmp::Reverse(layout.align));
    Some(c_layout(&layouts, false))
}

fn option_layout(inner: Layout) -> Layout {
    if inner.niche {
        Layout::new(inner.size, inner.align.max(1), true)
    } else {
        let align = inner.align.max(1);
        let offset = align_to(1, align);
        Layout::new(align_to(offset + inner.size, align), align, true)
    }
}

/// Layout de un enum de Rust con `#[repr(C)]` y el discriminante más pequeño
/// que quepa: `tag` primero, luego la unión de los payloads.
fn enum_layout(variants: &[Layout], niche: bool) -> Layout {
    let payload_size = variants.iter().map(|layout| layout.size).max().unwrap_or(0);
    let payload_align = variants
        .iter()
        .map(|layout| layout.align)
        .max()
        .unwrap_or(1)
        .max(1);
    let tag_align = if variants.len() <= 256 { 1 } else { 4 };
    let align = payload_align.max(tag_align);
    let offset = align_to(tag_align, payload_align);
    Layout::new(align_to(offset + payload_size, align), align, niche)
}

/// Layout secuencial de campos (reglas de C), opcionalmente con nicho.
fn c_layout(fields: &[Layout], niche: bool) -> Layout {
    let mut offset = 0usize;
    let mut align = 1usize;
    for field in fields {
        let field_align = field.align.max(1);
        align = align.max(field_align);
        offset = align_to(offset, field_align) + field.size;
    }
    Layout::new(align_to(offset, align), align, niche)
}

fn adt_layout(def: DefId, args: &[Ty], krate: &HirCrate, depth: u32) -> Option<Layout> {
    if depth > 24 {
        return None;
    }
    let adt = krate.adt(def)?;
    let mut env: HashMap<DefId, Ty> = HashMap::new();
    for (index, generic) in adt.generics.iter().enumerate() {
        let value = args.get(index).cloned().unwrap_or(Ty::Error);
        env.insert(generic.def, value);
    }
    match adt.kind {
        AdtKind::Record => {
            let mut fields = Vec::with_capacity(adt.fields.len());
            for field in &adt.fields {
                let ty = resolve_type(&field.ty, &field.resolutions, &env, krate)?;
                fields.push(layout_at(&ty, krate, depth + 1)?);
            }
            let niche = fields.iter().any(|field| field.niche);
            Some(c_layout(&fields, niche))
        }
        AdtKind::Sum => {
            let mut variants = Vec::with_capacity(adt.variants.len());
            for variant in &adt.variants {
                let mut fields = Vec::with_capacity(variant.fields.len());
                for field in &variant.fields {
                    let ty = resolve_type(&field.ty, &field.resolutions, &env, krate)?;
                    fields.push(layout_at(&ty, krate, depth + 1)?);
                }
                variants.push(c_layout(&fields, false));
            }
            let payload = variants
                .iter()
                .map(|variant| variant.size)
                .max()
                .unwrap_or(0);
            if payload == 0 {
                // Sin payload el backend emite `#[repr(u32)]`: solo el
                // discriminante, y sus valores sobrantes dan nicho.
                Some(Layout::new(4, 4, true))
            } else {
                Some(enum_layout(&variants, true))
            }
        }
    }
}

/// Convierte el tipo declarado de un campo (AST) al tipo semántico.
fn resolve_type(
    ty: &Type,
    resolutions: &[pengu_hir::Resolution],
    env: &HashMap<DefId, Ty>,
    krate: &HirCrate,
) -> Option<Ty> {
    match &ty.kind {
        TypeKind::Unit => Some(Ty::Unit),
        TypeKind::SelfType => None,
        TypeKind::Option(inner) => Some(Ty::Option(Box::new(resolve_type(
            inner,
            resolutions,
            env,
            krate,
        )?))),
        TypeKind::Ref { mutable, inner } => {
            if let TypeKind::Path { segments, args } = &inner.kind {
                if args.is_empty() {
                    match segments.last().map(String::as_str) {
                        Some("Str") => return Some(Ty::Str),
                        Some("CStr") => return Some(Ty::CStr),
                        _ => {}
                    }
                }
            }
            if let TypeKind::Slice(elem) = &inner.kind {
                return Some(Ty::Slice(
                    Box::new(resolve_type(elem, resolutions, env, krate)?),
                    *mutable,
                ));
            }
            Some(Ty::Ref(
                Box::new(resolve_type(inner, resolutions, env, krate)?),
                *mutable,
            ))
        }
        TypeKind::Array { elem, len } => {
            let elem = resolve_type(elem, resolutions, env, krate)?;
            let text = match &len.kind {
                pengu_syntax::ast::ExprKind::Int(value) => value.clone(),
                _ => return None,
            };
            Some(Ty::Array(Box::new(elem), text.parse().ok()?))
        }
        TypeKind::Slice(inner) => Some(Ty::Slice(
            Box::new(resolve_type(inner, resolutions, env, krate)?),
            false,
        )),
        TypeKind::Tuple(items) => {
            let mut types = Vec::with_capacity(items.len());
            for item in items {
                types.push(resolve_type(item, resolutions, env, krate)?);
            }
            Some(Ty::Tuple(types))
        }
        TypeKind::Ptr(inner) => Some(Ty::Ptr(Box::new(resolve_type(
            inner,
            resolutions,
            env,
            krate,
        )?))),
        TypeKind::Fn { params, ret } => {
            let mut types = Vec::with_capacity(params.len());
            for param in params {
                types.push(resolve_type(param, resolutions, env, krate)?);
            }
            Some(Ty::Fn(
                types,
                Box::new(resolve_type(ret, resolutions, env, krate)?),
            ))
        }
        TypeKind::Path { segments, args } => {
            let name = segments.last()?;
            if args.is_empty() {
                if let Some((def, value)) =
                    env.iter().find(|(def, _)| krate.def(**def).name == *name)
                {
                    // Genérico ya instanciado: se sustituye por su argumento.
                    if !matches!(value, Ty::Error) {
                        return Some(value.clone());
                    }
                    return Some(Ty::Generic(*def));
                }
            }
            let mut types = Vec::with_capacity(args.len());
            for arg in args {
                types.push(resolve_type(arg, resolutions, env, krate)?);
            }
            resolve_path(name, &types, ty, resolutions, krate)
        }
    }
}

fn resolve_path(
    name: &str,
    args: &[Ty],
    ty: &Type,
    resolutions: &[pengu_hir::Resolution],
    krate: &HirCrate,
) -> Option<Ty> {
    // Un tipo con argumentos (`Option[Point]`) acumula una resolución por cada
    // nombre del interior. La del tipo es la que cubre exactamente su span; si
    // no hay coincidencia, la más pequeña (la del nombre propio) es la buena.
    let mut best: Option<&pengu_hir::Resolution> = None;
    for resolution in resolutions {
        let inside = resolution.span.start >= ty.span.start && resolution.span.end <= ty.span.end;
        if !inside {
            continue;
        }
        let key = |candidate: &pengu_hir::Resolution| {
            (
                candidate.span.start == ty.span.start && candidate.span.end == ty.span.end,
                std::cmp::Reverse(candidate.span.end - candidate.span.start),
            )
        };
        if best.is_none_or(|current| key(resolution) > key(current)) {
            best = Some(resolution);
        }
    }
    if let Some(resolution) = best {
        match resolution.res {
            pengu_hir::Res::Primitive(primitive) => {
                // `Option`, `Vec`… se resuelven como primitivo del HIR pero no
                // son tipos con tamaño propio: caen al nombre estructural.
                if let Some(ty) = primitive_ty(primitive) {
                    return Some(ty);
                }
            }
            pengu_hir::Res::Def(def) => {
                if let Some(_adt) = krate.adt(def) {
                    return Some(Ty::Adt(def, args.to_vec()));
                }
                if krate.def(def).name == name {
                    return Some(Ty::Generic(def));
                }
            }
            pengu_hir::Res::Local(_) | pengu_hir::Res::Error => {}
        }
    }
    named_ty(name, args)
}

fn primitive_ty(primitive: pengu_hir::Primitive) -> Option<Ty> {
    use pengu_hir::Primitive;
    Some(match primitive {
        Primitive::Bool => Ty::Bool,
        Primitive::Int => Ty::Int,
        Primitive::I8 => Ty::I8,
        Primitive::I16 => Ty::I16,
        Primitive::I32 => Ty::I32,
        Primitive::I64 => Ty::I64,
        Primitive::Isize => Ty::Isize,
        Primitive::U8 => Ty::U8,
        Primitive::U16 => Ty::U16,
        Primitive::U32 => Ty::U32,
        Primitive::U64 => Ty::U64,
        Primitive::Usize => Ty::Usize,
        Primitive::Float => Ty::Float,
        Primitive::F32 => Ty::F32,
        Primitive::F64 => Ty::F64,
        Primitive::Char => Ty::Char,
        Primitive::String => Ty::String,
        Primitive::Str => Ty::Str,
        Primitive::Unit => Ty::Unit,
        Primitive::Ordering => Ty::Ordering,
        Primitive::CStr => Ty::CStr,
        Primitive::CString => Ty::CString,
        _ => return None,
    })
}

fn named_ty(name: &str, args: &[Ty]) -> Option<Ty> {
    let arg = |index: usize| args.get(index).cloned();
    Some(match name {
        "Bool" => Ty::Bool,
        "Int" => Ty::Int,
        "I8" => Ty::I8,
        "I16" => Ty::I16,
        "I32" => Ty::I32,
        "I64" => Ty::I64,
        "Isize" => Ty::Isize,
        "U8" => Ty::U8,
        "U16" => Ty::U16,
        "U32" | "UInt" => Ty::U32,
        "U64" => Ty::U64,
        "Usize" => Ty::Usize,
        "Float" => Ty::Float,
        "F32" => Ty::F32,
        "F64" => Ty::F64,
        "Char" => Ty::Char,
        "String" => Ty::String,
        "Str" => Ty::Str,
        "Unit" => Ty::Unit,
        "CStr" => Ty::CStr,
        "CString" => Ty::CString,
        "Ordering" => Ty::Ordering,
        "Vec" => Ty::Vec(Box::new(arg(0)?)),
        "Option" => Ty::Option(Box::new(arg(0)?)),
        "Box" => Ty::Box(Box::new(arg(0)?)),
        "Rc" => Ty::Rc(Box::new(arg(0)?)),
        "Arc" => Ty::Arc(Box::new(arg(0)?)),
        "Set" => Ty::Set(Box::new(arg(0)?)),
        "Map" => Ty::Map(Box::new(arg(0)?), Box::new(arg(1)?)),
        "Result" => Ty::Result(Box::new(arg(0)?), Box::new(arg(1)?)),
        "Iter" => Ty::Iterator(Box::new(arg(0)?)),
        "Range" => Ty::Range(Box::new(arg(0)?)),
        _ => return None,
    })
}

/// Formatea un tamaño para mostrarlo en el editor.
///
/// Los valores pequeños se muestran en bytes (`12 B`) y los grandes en KiB/MiB
/// con un decimal.
#[must_use]
pub fn format_size(size: usize) -> String {
    const KIB: f64 = 1024.0;
    if size < 1024 {
        return format!("{size} B");
    }
    #[allow(clippy::cast_precision_loss)] // tamaños muy por debajo de 2^52
    let value = size as f64;
    if value < KIB * KIB {
        return format!("{:.1} KiB", value / KIB);
    }
    format!("{:.1} MiB", value / (KIB * KIB))
}

/// Traduce el AST de un tipo a `Ty` (sin resolver nombres del programa).
#[must_use]
pub fn ast_ty(ty: &pengu_syntax::ast::Type) -> Option<Ty> {
    use pengu_syntax::ast::{ExprKind, TypeKind};

    fn boxed(ty: &pengu_syntax::ast::Type) -> Option<Box<Ty>> {
        ast_ty(ty).map(Box::new)
    }

    Some(match &ty.kind {
        TypeKind::Path { segments, args } => {
            let name = segments.last()?;
            let arg = args.first().and_then(ast_ty);
            match name.as_str() {
                "Bool" => Ty::Bool,
                "Int" => Ty::Int,
                "I8" => Ty::I8,
                "I16" => Ty::I16,
                "I32" => Ty::I32,
                "I64" => Ty::I64,
                "Isize" => Ty::Isize,
                "U8" => Ty::U8,
                "U16" => Ty::U16,
                "U32" | "UInt" => Ty::U32,
                "U64" => Ty::U64,
                "Usize" => Ty::Usize,
                "Float" => Ty::Float,
                "F32" => Ty::F32,
                "F64" => Ty::F64,
                "Char" => Ty::Char,
                "String" => Ty::String,
                "Str" => Ty::Str,
                "Unit" => Ty::Unit,
                "Ordering" => Ty::Ordering,
                "Option" => Ty::Option(Box::new(arg?)),
                "Vec" => Ty::Vec(Box::new(arg?)),
                "Box" => Ty::Box(Box::new(arg?)),
                "Rc" => Ty::Rc(Box::new(arg?)),
                "Arc" => Ty::Arc(Box::new(arg?)),
                _ => return None,
            }
        }
        TypeKind::Ref { inner: target, .. } => Ty::Ref(boxed(target)?, false),
        TypeKind::Tuple(items) => Ty::Tuple(items.iter().map(ast_ty).collect::<Option<Vec<Ty>>>()?),
        TypeKind::Array { elem, len } => {
            let ExprKind::Int(value) = &len.kind else {
                return None;
            };
            Ty::Array(boxed(elem)?, value.parse::<u64>().ok()?)
        }
        _ => return None,
    })
}

/// Como [`ast_ty`], pero resolviendo los tipos nominales del propio programa.
#[must_use]
pub fn typed(ty: &pengu_syntax::ast::Type, krate: &HirCrate) -> Option<Ty> {
    if let Some(resolved) = ast_ty(ty) {
        return Some(resolved);
    }
    let pengu_syntax::ast::TypeKind::Path { segments, args } = &ty.kind else {
        return None;
    };
    let name = segments.last()?;
    let def = krate
        .defs
        .iter()
        .find(|def| def.name == *name && krate.adt(def.id).is_some())?;
    let args = args
        .iter()
        .map(|arg| typed(arg, krate))
        .collect::<Option<Vec<Ty>>>()?;
    Some(Ty::Adt(def.id, args))
}

/// Huella de una función: tamaño de parámetros y retorno sumados.
#[must_use]
pub fn footprint(def: pengu_hir::DefId, krate: &HirCrate) -> Option<usize> {
    let signature = krate.signature(def)?;
    let mut total = layout_of(&typed(&signature.ret, krate)?, krate)?.size;
    for param in &signature.params {
        total = total.saturating_add(layout_of(&typed(param, krate)?, krate)?.size);
    }
    Some(total)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn size(ty: &Ty) -> Option<usize> {
        layout_of(ty, &empty_krate()).map(|layout| layout.size)
    }

    fn empty_krate() -> HirCrate {
        let program =
            pengu_syntax::parse_program(pengu_span::FileId::new(0), "grimoire\n    print(1)\n")
                .program
                .expect("programa");
        pengu_hir::lower_program(&program).krate
    }

    #[test]
    fn primitivos() {
        assert_eq!(size(&Ty::Bool), Some(1));
        assert_eq!(size(&Ty::Int), Some(4));
        assert_eq!(size(&Ty::I64), Some(8));
        assert_eq!(size(&Ty::Usize), Some(8));
        assert_eq!(size(&Ty::Float), Some(8));
        assert_eq!(size(&Ty::Char), Some(4));
        assert_eq!(size(&Ty::String), Some(24));
        assert_eq!(size(&Ty::Str), Some(16));
        assert_eq!(size(&Ty::Vec(Box::new(Ty::Int))), Some(24));
        assert_eq!(
            size(&Ty::Map(Box::new(Ty::Int), Box::new(Ty::Int))),
            Some(48)
        );
        assert_eq!(size(&Ty::Set(Box::new(Ty::Int))), Some(48));
        assert_eq!(size(&Ty::Box(Box::new(Ty::Bool))), Some(8));
        assert_eq!(size(&Ty::Iterator(Box::new(Ty::Int))), Some(16));
        assert_eq!(size(&Ty::Range(Box::new(Ty::Int))), Some(8));
        assert_eq!(size(&Ty::Unit), Some(0));
    }

    #[test]
    fn opcionales_con_y_sin_nicho() {
        // Sin nicho: enumeración de dos variantes.
        assert_eq!(size(&Ty::Option(Box::new(Ty::Int))), Some(8));
        assert_eq!(size(&Ty::Option(Box::new(Ty::I64))), Some(16));
        // Con nicho: mismo tamaño que el tipo.
        assert_eq!(size(&Ty::Option(Box::new(Ty::Bool))), Some(1));
        assert_eq!(size(&Ty::Option(Box::new(Ty::Char))), Some(4));
        assert_eq!(size(&Ty::Option(Box::new(Ty::String))), Some(24));
        assert_eq!(size(&Ty::Option(Box::new(Ty::Str))), Some(16));
        assert_eq!(
            size(&Ty::Option(Box::new(Ty::Box(Box::new(Ty::Int))))),
            Some(8)
        );
    }

    #[test]
    fn tuplas_ordenadas_por_alineacion() {
        assert_eq!(
            size(&Ty::Tuple(vec![Ty::Bool, Ty::Int, Ty::Char])),
            Some(12)
        );
        assert_eq!(size(&Ty::Tuple(vec![Ty::Bool, Ty::I64, Ty::U32])), Some(16));
        assert_eq!(size(&Ty::Tuple(vec![Ty::Int, Ty::Bool])), Some(8));
    }

    #[test]
    fn arrays_y_referencias() {
        assert_eq!(size(&Ty::Array(Box::new(Ty::Bool), 3)), Some(3));
        assert_eq!(size(&Ty::Array(Box::new(Ty::Int), 4)), Some(16));
        assert_eq!(size(&Ty::Slice(Box::new(Ty::Int), false)), None);
        assert_eq!(size(&Ty::Ref(Box::new(Ty::Int), false)), Some(8));
    }

    #[test]
    fn formatos_legibles() {
        assert_eq!(format_size(0), "0 B");
        assert_eq!(format_size(12), "12 B");
        assert_eq!(format_size(1024), "1.0 KiB");
        assert_eq!(format_size(1536), "1.5 KiB");
        assert_eq!(format_size(2 * 1024 * 1024), "2.0 MiB");
    }
}
