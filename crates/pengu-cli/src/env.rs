//! Entorno del proyecto: raíz, manifiesto y detección de terminal.

use std::path::{Path, PathBuf};

use pengu_project::Manifest;

/// Sube por los directorios hasta encontrar `Tome.toml`.
#[must_use]
pub fn project_root(start: &Path) -> Option<PathBuf> {
    let mut current = start.to_path_buf();
    loop {
        if current.join("Tome.toml").is_file() {
            return Some(current);
        }
        if !current.pop() {
            return None;
        }
    }
}

/// Lee y valida el manifiesto de `root`.
///
/// # Errors
/// Devuelve el diagnóstico del manifiesto como texto legible.
pub fn read_manifest(root: &Path) -> Result<Manifest, String> {
    let path = root.join("Tome.toml");
    let text = std::fs::read_to_string(&path)
        .map_err(|error| format!("no se puede leer `{}`: {error}", path.display()))?;
    pengu_project::parse_manifest(&text)
        .map_err(|diagnostic| format!("`Tome.toml` inválido: {}", diagnostic.render_compact()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encuentra_la_raiz_hacia_arriba() {
        let base = std::env::temp_dir().join(format!("pengu-env-{}", std::process::id()));
        let nested = base.join("a").join("b");
        std::fs::create_dir_all(&nested).expect("dirs");
        std::fs::write(base.join("Tome.toml"), "[tome]\nname = \"x\"\n").expect("manifiesto");
        assert_eq!(project_root(&nested), Some(base.clone()));
        let _ = std::fs::remove_dir_all(&base);
    }
}
