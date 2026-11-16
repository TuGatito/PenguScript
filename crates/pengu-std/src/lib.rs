//! La biblioteca estándar de `PenguScript`, embebida en el compilador.
//!
//! `std` no vive en el sistema de archivos del usuario: sus fuentes se
//! compilan dentro del binario con `include_str!` para que el compilador sea
//! determinista y no dependa de una instalación (D7 de `scratch/STDLIB_PLAN.md`).
//!
//! Cada archivo de `std/` declara su propio `scroll`; este crate los envuelve
//! en el módulo raíz `std`, de modo que `std/integrum.pengu` se convierte en
//! `std::integrum`.

use std::sync::OnceLock;

use pengu_span::{DUMMY_SPAN, FileId};
use pengu_syntax::ast::{Item, ItemKind, Program, Scroll, Visibility};
use pengu_syntax::parse_program;

/// Nombre del módulo raíz de la stdlib.
pub const STD: &str = "std";

/// Fuentes de la stdlib, una por archivo.
///
/// El orden es fijo: la carga es determinista y no depende del sistema de
/// archivos.
const FILES: &[(&str, &str)] = &[
    ("integrum", include_str!("../../../std/integrum.pengu")),
    ("floatem", include_str!("../../../std/floatem.pengu")),
    ("littera", include_str!("../../../std/littera.pengu")),
    ("funis", include_str!("../../../std/funis.pengu")),
    ("capsa", include_str!("../../../std/capsa.pengu")),
    ("tabula", include_str!("../../../std/tabula.pengu")),
    ("fasciculus", include_str!("../../../std/fasciculus.pengu")),
    ("numerus", include_str!("../../../std/numerus.pengu")),
    ("proba", include_str!("../../../std/proba.pengu")),
    ("fluxus", include_str!("../../../std/fluxus.pengu")),
    ("opera", include_str!("../../../std/opera.pengu")),
    ("veritas", include_str!("../../../std/veritas.pengu")),
    ("verbum", include_str!("../../../std/verbum.pengu")),
    ("via", include_str!("../../../std/via.pengu")),
    ("exsecutor", include_str!("../../../std/exsecutor.pengu")),
    ("ambitus", include_str!("../../../std/ambitus.pengu")),
    ("tempus", include_str!("../../../std/tempus.pengu")),
    ("structura", include_str!("../../../std/structura.pengu")),
    ("optio", include_str!("../../../std/optio.pengu")),
    ("nexus", include_str!("../../../std/nexus.pengu")),
    ("versio", include_str!("../../../std/versio.pengu")),
    ("digestum", include_str!("../../../std/digestum.pengu")),
    ("iason", include_str!("../../../std/iason.pengu")),
    ("terminus", include_str!("../../../std/terminus.pengu")),
    ("globus", include_str!("../../../std/globus.pengu")),
    ("cellula", include_str!("../../../std/cellula.pengu")),
    ("rete", include_str!("../../../std/rete.pengu")),
    ("archivum", include_str!("../../../std/archivum.pengu")),
    ("libra", include_str!("../../../std/libra.pengu")),
];

/// Primer `FileId` reservado para los archivos de la stdlib.
///
/// Cada archivo tiene el suyo para que los diagnósticos, el hover y la
/// navegación apunten a la fuente correcta (Fase 6, D7).
pub const FIRST_FILE: u32 = 0x3F00_0000;

/// Archivo de la stdlib.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StdFile {
    /// Nombre del módulo (sin extensión).
    pub name: &'static str,
    /// Texto fuente.
    pub text: &'static str,
}

/// Devuelve los archivos de la stdlib en orden determinista.
#[must_use]
pub fn files() -> Vec<StdFile> {
    FILES
        .iter()
        .map(|(name, text)| StdFile { name, text })
        .collect()
}

/// `FileId` del archivo `index`-ésimo de [`files`].
#[must_use]
pub fn file_id(index: usize) -> FileId {
    let offset = u32::try_from(index).unwrap_or(u32::MAX);
    FileId::new(FIRST_FILE.saturating_add(offset))
}

/// `true` si el `FileId` pertenece a la stdlib.
#[must_use]
pub fn is_std_file(file: FileId) -> bool {
    file.raw() >= FIRST_FILE
}

/// Índice del archivo de la stdlib, si el `FileId` es suyo.
#[must_use]
pub fn file_index(file: FileId) -> Option<usize> {
    if is_std_file(file) {
        usize::try_from(file.raw() - FIRST_FILE).ok()
    } else {
        None
    }
}

/// Devuelve el programa de la stdlib ya parseado.
///
/// # Panics
///
/// Si la stdlib embebida no parsea. Es un fallo de construcción del
/// compilador, cubierto por los tests de este crate.
#[must_use]
pub fn std_program() -> &'static Program {
    static STD_PROGRAM: OnceLock<Program> = OnceLock::new();
    STD_PROGRAM.get_or_init(|| {
        let mut items = Vec::new();
        let mut diagnostics = Vec::new();
        for (index, (_, text)) in FILES.iter().enumerate() {
            let parsed = parse_program(file_id(index), text);
            diagnostics.extend(parsed.diagnostics);
            if let Some(mut program) = parsed.program {
                items.append(&mut program.items);
            }
        }
        assert!(
            diagnostics.is_empty(),
            "la stdlib embebida no parsea:\n{diagnostics:#?}"
        );
        let scroll = Item {
            kind: ItemKind::Scroll(Scroll {
                name: STD.to_owned(),
                items,
                span: DUMMY_SPAN,
            }),
            derives: Vec::new(),
            visibility: Visibility::Private,
            span: DUMMY_SPAN,
        };
        Program {
            items: vec![scroll],
            span: DUMMY_SPAN,
        }
    })
}

/// Compone un programa de usuario con la stdlib.
///
/// El `scroll std` va primero para que el módulo exista antes de cualquier
/// `summon std::...`. Si el programa ya trae un `scroll std` (es la propia
/// stdlib), se devuelve sin tocar.
#[must_use]
pub fn with_std(program: &Program) -> Program {
    if defines_std(program) {
        return program.clone();
    }
    let mut merged = std_program().clone();
    merged.items.extend(program.items.iter().cloned());
    merged.span = program.span;
    merged
}

/// Comprueba si un programa declara el módulo `std`.
#[must_use]
pub fn defines_std(program: &Program) -> bool {
    program
        .items
        .iter()
        .any(|item| matches!(&item.kind, ItemKind::Scroll(scroll) if scroll.name == STD))
}

/// Compone el texto fuente completo de la stdlib.
#[must_use]
pub fn source() -> String {
    let mut text = String::from("scroll std\n");
    for (_, body) in FILES {
        for line in body.lines() {
            if line.trim().is_empty() {
                text.push('\n');
            } else {
                text.push_str("    ");
                text.push_str(line);
                text.push('\n');
            }
        }
    }
    text
}

#[cfg(test)]
mod tests {
    use super::{defines_std, std_program, with_std};

    #[test]
    fn la_stdlib_parsea() {
        let program = std_program();
        assert!(defines_std(program));
    }

    fn metodo_counts() -> Vec<usize> {
        fn rituals(items: &[pengu_syntax::ast::Item], found: &mut Vec<usize>) {
            for item in items {
                match &item.kind {
                    pengu_syntax::ast::ItemKind::Ritual(ritual) => {
                        found.push(
                            ritual
                                .items
                                .iter()
                                .filter(|item| {
                                    matches!(item, pengu_syntax::ast::RitualItem::Method(_))
                                })
                                .count(),
                        );
                    }
                    pengu_syntax::ast::ItemKind::Scroll(scroll) => rituals(&scroll.items, found),
                    _ => {}
                }
            }
        }

        let mut found = Vec::new();
        rituals(&std_program().items, &mut found);
        found
    }

    #[test]
    fn integrum_expone_la_superficie_de_int() {
        let methods = *metodo_counts().first().expect("ritual de Int");
        assert!(
            methods >= 63,
            "la superficie de `Int` debe cubrir los 63 del documento, hay {methods}"
        );
    }

    #[test]
    fn floatem_expone_la_superficie_de_float() {
        let methods = *metodo_counts().get(1).expect("ritual de Float");
        assert!(
            methods >= 57,
            "la superficie de `Float` debe cubrir los 57 del documento, hay {methods}"
        );
    }

    #[test]
    fn el_programa_de_usuario_va_despues() {
        let parsed =
            pengu_syntax::parse_program(pengu_span::FileId::new(0), "grimoire\n    print(1)\n");
        let program = parsed.program.expect("el programa de prueba parsea");
        let fused = with_std(&program);
        assert_eq!(fused.items.len(), std_program().items.len() + 1);
        assert!(matches!(
            fused.items.first().map(|item| &item.kind),
            Some(pengu_syntax::ast::ItemKind::Scroll(_))
        ));
        assert!(matches!(
            fused.items.last().map(|item| &item.kind),
            Some(pengu_syntax::ast::ItemKind::Grimoire(_))
        ));
    }

    #[test]
    fn littera_expone_la_superficie_de_char() {
        let methods = *metodo_counts().get(2).expect("ritual de Char");
        assert!(
            methods >= 33,
            "la superficie de `Char` debe cubrir los 33 del documento, hay {methods}"
        );
    }
}
