//! Emisión del `.d.pengu`.

use std::fmt::Write as _;
use std::path::Path;

use crate::ir::{Ir, Omitted};

/// Genera el contenido del `.d.pengu`.
#[must_use]
pub fn render(ir: &Ir, header: &Path) -> String {
    let name = header.file_name().map_or_else(
        || header.display().to_string(),
        |name| name.to_string_lossy().into_owned(),
    );
    let mut out = String::new();
    let _ = writeln!(
        out,
        "-- Generado por `pengu bindgen` desde `{name}`. No editar a mano."
    );
    let _ = writeln!(
        out,
        "-- {} funcion(es), {} estructura(s), {} constante(s); {} omitido(s).",
        ir.functions.len(),
        ir.records.len(),
        ir.constants.len(),
        ir.omitted.len()
    );
    out.push('\n');
    out.push_str("abi \"C\"\n");
    for record in &ir.records {
        out.push('\n');
        let _ = writeln!(out, "rune {}", identifier(&record.name));
        for field in &record.fields {
            let _ = writeln!(out, "    {}: {}", identifier(&field.name), field.ty);
        }
    }
    if !ir.constants.is_empty() {
        out.push('\n');
        for constant in &ir.constants {
            let _ = writeln!(
                out,
                "{}: Int = {}",
                identifier(&constant.name),
                constant.value
            );
        }
    }
    for function in &ir.functions {
        out.push('\n');
        let params = function
            .params
            .iter()
            .map(|param| format!("{}: {}", identifier(&param.name), signature_type(&param.ty)))
            .collect::<Vec<_>>()
            .join(", ");
        let _ = writeln!(
            out,
            "{} = ({params}) -> {}",
            identifier(&function.name),
            signature_type(&function.ret)
        );
    }
    out
}

/// En una firma, `CStr` viaja como referencia (`&CStr`): el tipo es *unsized*.
fn signature_type(ty: &str) -> String {
    if ty == "CStr" {
        "&CStr".to_owned()
    } else {
        ty.to_owned()
    }
}

/// Convierte un identificador C en uno válido de `PenguScript`.
#[must_use]
pub fn identifier(name: &str) -> String {
    let mut clean = String::with_capacity(name.len() + 1);
    for (index, character) in name.chars().enumerate() {
        let valid = if index == 0 {
            character.is_ascii_alphabetic() || character == '_'
        } else {
            character.is_ascii_alphanumeric() || character == '_'
        };
        clean.push(if valid { character } else { '_' });
    }
    if clean.is_empty() {
        clean.push('_');
    }
    if pengu_syntax::is_reserved(&clean) {
        clean.push('_');
    }
    clean
}

/// Líneas del reporte de omisiones.
#[must_use]
pub fn omission_lines(omitted: &[Omitted]) -> Vec<String> {
    omitted
        .iter()
        .map(|item| format!("{} {}: {}", item.kind, item.name, item.reason))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::identifier;

    #[test]
    fn sanea_identificadores() {
        assert_eq!(identifier("size"), "size");
        assert_eq!(identifier("type"), "type");
        assert_eq!(identifier("match"), "match_");
        assert_eq!(identifier("self"), "self_");
        assert_eq!(identifier("2fast"), "_fast");
        assert_eq!(identifier("a-b"), "a_b");
    }
}
