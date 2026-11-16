//! Descubrimiento del proyecto y del archivo raíz del programa.

use std::path::{Path, PathBuf};

use pengu_project::{Manifest, parse_manifest};

/// Proyecto detectado a partir de una ruta.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Project {
    /// Raíz (directorio con `Tome.toml`, o el ancestro con el programa).
    pub root: PathBuf,
    /// Archivo raíz del programa.
    pub program: PathBuf,
}

impl Project {
    /// Manifiesto del proyecto, si existe y parsea.
    #[must_use]
    pub fn manifest(&self) -> Option<Manifest> {
        let source = std::fs::read_to_string(self.root.join("Tome.toml")).ok()?;
        parse_manifest(&source).ok()
    }

    /// `true` si el archivo dado es el raíz del programa.
    #[must_use]
    pub fn is_program(&self, path: &Path) -> bool {
        same_file(&self.program, path)
    }
}

fn same_file(left: &Path, right: &Path) -> bool {
    if left == right {
        return true;
    }
    match (left.canonicalize(), right.canonicalize()) {
        (Ok(left), Ok(right)) => left == right,
        _ => false,
    }
}

fn program_in(directory: &Path) -> Option<PathBuf> {
    let bin = directory.join("main.pengu");
    if bin.is_file() {
        return Some(bin);
    }
    let lib = directory.join("lib.pengu");
    if lib.is_file() {
        return Some(lib);
    }
    None
}

/// Descubre el proyecto al que pertenece `from`.
///
/// Sube por los ancestros buscando `Tome.toml`; si no lo encuentra, usa el
/// primer directorio con `main.pengu` o `lib.pengu`.
#[must_use]
pub fn discover(from: &Path) -> Option<Project> {
    let start = if from.is_dir() {
        from
    } else {
        from.parent().unwrap_or(from)
    };
    let mut program_root = None;
    for directory in start.ancestors() {
        if directory.join("Tome.toml").is_file() {
            if let Some(program) = program_in(directory) {
                return Some(Project {
                    root: directory.to_path_buf(),
                    program,
                });
            }
        }
        if program_root.is_none() {
            if let Some(program) = program_in(directory) {
                program_root = Some(Project {
                    root: directory.to_path_buf(),
                    program,
                });
            }
        }
    }
    program_root
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp(name: &str) -> PathBuf {
        let path = std::env::temp_dir().join(format!("pengu-lsp-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).expect("dir");
        path
    }

    #[test]
    fn encuentra_el_proyecto_por_el_manifiesto() {
        let root = temp("project");
        std::fs::write(
            root.join("Tome.toml"),
            "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\n",
        )
        .expect("manifest");
        std::fs::write(root.join("main.pengu"), "grimoire\n").expect("main");
        let nested = root.join("sub");
        std::fs::create_dir_all(&nested).expect("nested");
        let project = discover(&nested).expect("proyecto");
        assert_eq!(project.root, root);
        assert_eq!(project.program, root.join("main.pengu"));
        assert!(project.is_program(&root.join("main.pengu")));
    }

    #[test]
    fn prefiere_main_y_luego_lib() {
        let root = temp("lib");
        std::fs::write(root.join("lib.pengu"), "grimoire\n").expect("lib");
        let project = discover(&root).expect("proyecto");
        assert_eq!(project.program, root.join("lib.pengu"));
        std::fs::write(root.join("main.pengu"), "grimoire\n").expect("main");
        let project = discover(&root).expect("proyecto");
        assert_eq!(project.program, root.join("main.pengu"));
    }

    #[test]
    fn sin_proyecto_no_hay_nada() {
        let root = temp("empty");
        assert!(discover(&root).is_none());
    }
}
