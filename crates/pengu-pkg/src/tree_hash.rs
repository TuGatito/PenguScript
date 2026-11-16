//! Checksum canónico del árbol empaquetado.
//!
//! La norma exige un `checksum` SHA-256 por paquete (`docs/LANGUAGE.md` §18.3). Para
//! que sea reproducible entre máquinas y sistemas operativos se define así:
//!
//! - Se recorren los archivos del paquete ordenados por **ruta relativa** (bytes UTF-8,
//!   separador `/`).
//! - Se omiten `.git/`, `target/`, `vendor/`, `.pengu/`, el propio `Tome.lock` y el
//!   marcador `.pengu-checksum` que escribe `pengu vendor`.
//! - Por entrada se alimenta al hash: `ruta`, un byte `\0`, un byte de modo
//!   (`-` archivo, `x` ejecutable, `l` enlace simbólico), la longitud en little-endian
//!   de 8 bytes y el contenido (para un enlace, su destino).
//! - No se incluyen mtime, permisos de lectura ni el orden del sistema de archivos.

use std::path::{Path, PathBuf};

use crate::PkgError;
use crate::sha256::{self, Sha256};

const IGNORED_DIRS: &[&str] = &[".git", "target", "vendor", ".pengu"];

/// Digest canónico del árbol `root`.
///
/// # Errors
/// Devuelve `PGS-E1803` si no se puede leer el árbol.
pub fn tree_digest(root: &Path) -> Result<[u8; 32], PkgError> {
    let mut entries = Vec::new();
    collect(root, root, &mut entries)?;
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    let mut hasher = Sha256::new();
    for entry in entries {
        hasher.update(entry.path.as_bytes());
        hasher.update(b"\0");
        hasher.update(&[entry.mode]);
        hasher.update(&(entry.data.len() as u64).to_le_bytes());
        hasher.update(&entry.data);
    }
    Ok(hasher.finish())
}

/// Checksum con el formato del lock (`sha256-<hex>`).
///
/// # Errors
/// Devuelve `PGS-E1803` si no se puede leer el árbol.
pub fn tree_checksum(root: &Path) -> Result<String, PkgError> {
    Ok(format!("sha256-{}", sha256::hex(&tree_digest(root)?)))
}

struct Entry {
    path: String,
    mode: u8,
    data: Vec<u8>,
}

fn collect(root: &Path, dir: &Path, out: &mut Vec<Entry>) -> Result<(), PkgError> {
    let reader = std::fs::read_dir(dir).map_err(|error| {
        crate::io_error(
            "PGS-E1803",
            &format!("no se pudo leer `{}`", dir.display()),
            &error,
        )
    })?;
    let mut children: Vec<PathBuf> = reader
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .collect();
    children.sort();
    for path in children {
        let relative = path.strip_prefix(root).unwrap_or(&path);
        let relative = relative
            .components()
            .map(|component| component.as_os_str().to_string_lossy().into_owned())
            .collect::<Vec<_>>()
            .join("/");
        let metadata = std::fs::symlink_metadata(&path).map_err(|error| {
            crate::io_error(
                "PGS-E1803",
                &format!("no se pudo leer `{}`", path.display()),
                &error,
            )
        })?;
        let name = path
            .file_name()
            .map(|value| value.to_string_lossy().into_owned())
            .unwrap_or_default();
        if metadata.is_dir() {
            if IGNORED_DIRS.contains(&name.as_str()) {
                continue;
            }
            collect(root, &path, out)?;
            continue;
        }
        if relative == "Tome.lock" || relative == crate::vendor::MARKER {
            continue;
        }
        if metadata.file_type().is_symlink() {
            let target = std::fs::read_link(&path).map_err(|error| {
                crate::io_error(
                    "PGS-E1803",
                    &format!("no se pudo leer el enlace `{}`", path.display()),
                    &error,
                )
            })?;
            out.push(Entry {
                path: relative,
                mode: b'l',
                data: target.to_string_lossy().into_owned().into_bytes(),
            });
            continue;
        }
        if std::path::Path::new(&relative)
            .extension()
            .is_some_and(|ext| ext.eq_ignore_ascii_case("tmp"))
        {
            continue;
        }
        let data = std::fs::read(&path).map_err(|error| {
            crate::io_error(
                "PGS-E1803",
                &format!("no se pudo leer `{}`", path.display()),
                &error,
            )
        })?;
        #[cfg(unix)]
        let mode = {
            use std::os::unix::fs::PermissionsExt;
            if metadata.permissions().mode() & 0o111 != 0 {
                b'x'
            } else {
                b'-'
            }
        };
        #[cfg(not(unix))]
        let mode = b'-';
        out.push(Entry {
            path: relative,
            mode,
            data,
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(path: &Path, contents: &str) {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).expect("dir");
        }
        std::fs::write(path, contents).expect("write");
    }

    #[test]
    fn checksum_estable_y_sensible_al_contenido() {
        let root = std::env::temp_dir().join(format!("pengu-tree-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        write(&root.join("a.txt"), "uno");
        write(&root.join("dir/b.txt"), "dos");
        let first = tree_checksum(&root).expect("checksum");
        let second = tree_checksum(&root).expect("checksum");
        assert_eq!(first, second);
        assert!(first.starts_with("sha256-"));

        write(&root.join("dir/b.txt"), "dos!");
        let changed = tree_checksum(&root).expect("checksum");
        assert_ne!(first, changed);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn ignora_git_target_y_lock() {
        let root = std::env::temp_dir().join(format!("pengu-tree-ign-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        write(&root.join("Tome.toml"), "name = \"x\"\n");
        let base = tree_checksum(&root).expect("checksum");
        write(&root.join(".git/HEAD"), "ref: refs/heads/main\n");
        write(&root.join("target/debug/x"), "binario");
        write(&root.join("vendor/dep/Tome.toml"), "name = \"dep\"\n");
        write(&root.join("Tome.lock"), "version = 1\n");
        assert_eq!(base, tree_checksum(&root).expect("checksum"));
        let _ = std::fs::remove_dir_all(&root);
    }
}
