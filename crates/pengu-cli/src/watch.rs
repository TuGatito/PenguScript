//! Detección de cambios por polling de mtimes.
//!
//! Sin dependencias y portable: `inotify`/`FSEvents` no están disponibles en
//! todas las plataformas y añadirlos obligaría a una dependencia externa. Un
//! `read_dir` completo del proyecto cada 250 ms cuesta décimas de milisegundo
//! para un árbol de cientos de archivos.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

/// Estado de los fuentes que interesan al compilador.
pub type Snapshot = BTreeMap<PathBuf, (SystemTime, u64)>;

/// Directorios que nunca contienen fuentes (y que el propio build escribe).
const SKIPPED: &[&str] = &["target", ".git"];

/// Profundidad máxima del recorrido; un proyecto real no pasa de aquí.
const MAX_DEPTH: usize = 32;

/// Instantánea de `*.pengu` y `Tome.toml` bajo `root`.
#[must_use]
pub fn snapshot(root: &Path) -> Snapshot {
    let mut state = Snapshot::new();
    collect(root, &mut state, 0);
    state
}

fn collect(dir: &Path, state: &mut Snapshot, depth: usize) {
    if depth > MAX_DEPTH {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        let Ok(metadata) = entry.metadata() else {
            continue;
        };
        if metadata.is_dir() {
            if SKIPPED.contains(&name.as_ref()) {
                continue;
            }
            collect(&entry.path(), state, depth + 1);
        } else if name.ends_with(".pengu") || name == "Tome.toml" {
            let modified = metadata.modified().unwrap_or(SystemTime::UNIX_EPOCH);
            state.insert(entry.path(), (modified, metadata.len()));
        }
    }
}

/// `true` si algo cambió entre dos instantáneas.
#[must_use]
pub fn changed(before: &Snapshot, after: &Snapshot) -> bool {
    before != after
}
