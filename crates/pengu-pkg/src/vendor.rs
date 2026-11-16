//! Vendor: copia de las dependencias del lock dentro del repositorio.
//!
//! `vendor/<nombre>` contiene el árbol del paquete tal cual se publicó, más un archivo
//! `.pengu-checksum` con el checksum del lock. El build prefiere el vendor cuando existe
//! y verifica que el árbol sigue coincidiendo antes de usarlo: una copia editada a mano
//! es un error (`PGS-E1808`), no una compilación silenciosa con otro código.

use std::path::{Path, PathBuf};

use crate::PkgError;
use crate::cache::Cache;
use crate::lock::{LockedPackage, Lockfile};
use crate::ops;
use crate::tree_hash;

/// Nombre del archivo que guarda el checksum de una copia vendida.
pub const MARKER: &str = ".pengu-checksum";

/// Directorio del vendor.
#[must_use]
pub fn vendor_dir(root: &Path) -> PathBuf {
    root.join("vendor")
}

/// Directorio de un paquete vendido.
#[must_use]
pub fn package_dir(root: &Path, name: &str) -> PathBuf {
    vendor_dir(root).join(name)
}

/// Copia todos los paquetes del lock a `vendor/` y devuelve los nombres copiados.
///
/// # Errors
/// `PGS-E1808` si un paquete no se puede materializar o su árbol no coincide con el
/// checksum del lock; `PGS-E1803` si falta la fuente.
pub fn vendor(root: &Path, cache: &Cache, lock: &Lockfile) -> Result<Vec<String>, PkgError> {
    cache.ensure_dirs()?;
    let target_root = vendor_dir(root);
    std::fs::create_dir_all(&target_root).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede crear `{}`", target_root.display()),
            &error,
        )
    })?;
    let mut vendored = Vec::with_capacity(lock.packages.len());
    for package in &lock.packages {
        let source = ops::package_source_dir(root, cache, package);
        if !source.is_dir() {
            return Err(PkgError::invalid_lock(
                format!("no se encuentra la fuente de `{}`", package.name),
                "ejecuta `pengu fetch` y repite",
            ));
        }
        let destination = package_dir(root, &package.name);
        copy_verified(&source, &destination, package)?;
        vendored.push(package.name.clone());
    }
    Ok(vendored)
}

/// Verifica que cada paquete vendido sigue coincidiendo con el lock.
///
/// # Errors
/// `PGS-E1808` si falta una copia o su checksum no coincide.
pub fn verify(root: &Path, lock: &Lockfile) -> Result<(), PkgError> {
    for package in &lock.packages {
        let dir = package_dir(root, &package.name);
        if !dir.is_dir() {
            return Err(PkgError::invalid_lock(
                format!("falta la copia vendida de `{}`", package.name),
                "ejecuta `pengu vendor` para regenerarla",
            ));
        }
        let actual = tree_hash::tree_checksum(&dir)?;
        if actual != package.checksum {
            return Err(PkgError::invalid_lock(
                format!(
                    "la copia vendida de `{}` no coincide con Tome.lock",
                    package.name
                ),
                "restaura el vendor o ejecuta `pengu vendor` de nuevo",
            ));
        }
    }
    Ok(())
}

/// `true` si el proyecto tiene un vendor con al menos un paquete.
#[must_use]
pub fn exists(root: &Path) -> bool {
    vendor_dir(root).is_dir()
}

/// Copia un árbol a un directorio temporal y lo renombra al final (escritura atómica).
fn copy_verified(
    source: &Path,
    destination: &Path,
    package: &LockedPackage,
) -> Result<(), PkgError> {
    let checksum = tree_hash::tree_checksum(source)?;
    if checksum != package.checksum {
        return Err(PkgError::invalid_lock(
            format!(
                "el árbol de `{}` no coincide con el checksum de Tome.lock",
                package.name
            ),
            format!(
                "la fuente `{}` cambió; ejecuta `pengu fetch --force` para regenerar el lock",
                source.display()
            ),
        ));
    }
    let temporary = destination.with_extension("tmp");
    if temporary.exists() {
        remove_tree(&temporary)?;
    }
    copy_tree(source, &temporary)?;
    write_marker(&temporary, &package.checksum)?;
    if destination.exists() {
        remove_tree(destination)?;
    }
    std::fs::rename(&temporary, destination).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede publicar `{}`", destination.display()),
            &error,
        )
    })
}

fn write_marker(dir: &Path, checksum: &str) -> Result<(), PkgError> {
    std::fs::write(dir.join(MARKER), format!("{checksum}\n")).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede escribir `{}`", dir.join(MARKER).display()),
            &error,
        )
    })
}

fn copy_tree(source: &Path, destination: &Path) -> Result<(), PkgError> {
    std::fs::create_dir_all(destination).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede crear `{}`", destination.display()),
            &error,
        )
    })?;
    let mut entries: Vec<_> = std::fs::read_dir(source)
        .map_err(|error| {
            crate::io_error(
                "PGS-E1803",
                &format!("no se puede leer `{}`", source.display()),
                &error,
            )
        })?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| {
            crate::io_error(
                "PGS-E1803",
                &format!("no se puede leer `{}`", source.display()),
                &error,
            )
        })?;
    entries.sort_by_key(std::fs::DirEntry::file_name);
    for entry in entries {
        let name = entry.file_name();
        let text = name.to_string_lossy();
        match text.as_ref() {
            ".git" | "target" | ".pengu" => continue,
            _ => {}
        }
        let from = entry.path();
        let to = destination.join(&name);
        let file_type = entry.file_type().map_err(|error| {
            crate::io_error(
                "PGS-E1803",
                &format!("no se puede leer `{}`", from.display()),
                &error,
            )
        })?;
        if file_type.is_dir() {
            copy_tree(&from, &to)?;
        } else if file_type.is_symlink() {
            let target = std::fs::read_link(&from).map_err(|error| {
                crate::io_error(
                    "PGS-E1803",
                    &format!("no se puede leer `{}`", from.display()),
                    &error,
                )
            })?;
            make_symlink(&target, &to)?;
        } else {
            std::fs::copy(&from, &to).map_err(|error| {
                crate::io_error(
                    "PGS-E1803",
                    &format!("no se puede copiar `{}`", from.display()),
                    &error,
                )
            })?;
        }
    }
    Ok(())
}

#[cfg(unix)]
fn make_symlink(target: &Path, destination: &Path) -> Result<(), PkgError> {
    std::os::unix::fs::symlink(target, destination).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede enlazar `{}`", destination.display()),
            &error,
        )
    })
}

#[cfg(not(unix))]
fn make_symlink(_target: &Path, destination: &Path) -> Result<(), PkgError> {
    Err(PkgError::invalid_lock(
        format!(
            "no se puede copiar el enlace simbólico `{}` en esta plataforma",
            destination.display()
        ),
        "elimina el enlace del paquete o usa una copia sin enlaces",
    ))
}

fn remove_tree(path: &Path) -> Result<(), PkgError> {
    std::fs::remove_dir_all(path).map_err(|error| {
        crate::io_error(
            "PGS-E1808",
            &format!("no se puede limpiar `{}`", path.display()),
            &error,
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::source::{GitRef, Source};

    fn package(name: &str, checksum: String) -> LockedPackage {
        LockedPackage {
            name: name.to_owned(),
            version: "1.0.0".to_owned(),
            source: Source::git("/repo", GitRef::Tag("v1".to_owned()))
                .expect("source")
                .canonical(),
            commit: "abc".to_owned(),
            checksum,
            features: Vec::new(),
            dependencies: Vec::new(),
        }
    }

    #[test]
    fn vendor_copia_y_verifica() {
        let root = std::env::temp_dir().join(format!("pengu-vendor-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        // Fuente simulada: un directorio con el checksum esperado.
        let source = root.join("source");
        std::fs::create_dir_all(&source).expect("dir");
        std::fs::write(source.join("lib.pengu"), "unveil x = 1\n").expect("write");
        let source_checksum = tree_hash::tree_checksum(&source).expect("hash2");
        let target = root.join("vendor");
        std::fs::create_dir_all(&target).expect("vendor");
        let package = package("text", source_checksum.clone());
        copy_verified(&source, &target.join("text"), &package).expect("copia");
        let lock = Lockfile::new(vec![package]).expect("lock");
        verify(&root, &lock).expect("verifica");
        std::fs::write(target.join("text/lib.pengu"), "unveil x = 2\n").expect("edit");
        assert!(verify(&root, &lock).is_err(), "detecta la edición");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn vendor_detecta_checksum_incorrecto() {
        let root = std::env::temp_dir().join(format!("pengu-vendor-bad-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let source = root.join("source");
        std::fs::create_dir_all(&source).expect("dir");
        std::fs::write(source.join("lib.pengu"), "unveil x = 1\n").expect("write");
        let package = package("text", "sha256-0000".to_owned());
        let error = copy_verified(&source, &root.join("vendor/text"), &package).expect_err("error");
        assert_eq!(error.code, "PGS-E1808");
        let _ = std::fs::remove_dir_all(&root);
    }
}
