//! Operaciones de alto nivel: resolver, verificar y materializar el lock.
//!
//! `fetch` es la única operación que puede tocar la red (y solo si no se pidió
//! `--offline`); `verify` comprueba el lock contra el manifiesto sin resolver nada.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use pengu_project::Manifest;

use crate::PkgError;
use crate::cache::Cache;
use crate::git::{Fetcher, Git, ShellGit};
use crate::lock::Lockfile;
use crate::source::Source;

/// Opciones de red y de verificación.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
#[allow(clippy::struct_excessive_bools)]
pub struct Options {
    /// No tocar la red: usar solo la caché.
    pub offline: bool,
    /// Exigir que `Tome.lock` exista y coincida con el manifiesto.
    pub locked: bool,
    /// Volver a resolver aunque el lock ya coincida (mueve `tag`/`branch`).
    pub refresh: bool,
    /// Re-clonar la caché de git antes de resolver.
    pub force: bool,
}

/// Fuentes declaradas en el manifiesto, con las rutas relativas a `root`.
///
/// # Errors
/// Devuelve `PGS-E1806` si una dependencia no declara fuente o declara varias.
pub fn declared_sources(
    root: &Path,
    manifest: &Manifest,
) -> Result<BTreeMap<String, Source>, PkgError> {
    let mut declared = BTreeMap::new();
    for dependency in &manifest.dependencies {
        let source = match crate::resolver::dependency_source(dependency)? {
            Source::Path { path } if Path::new(&path).is_relative() => {
                Source::path(&root.join(&path).display().to_string())?
            }
            other => other,
        };
        if declared.insert(dependency.name.clone(), source).is_some() {
            return Err(PkgError::plain(
                "PGS-E1807",
                format!("`{}` está declarada dos veces", dependency.name),
            )
            .with_help("deja una sola entrada en `[dependencies]`"));
        }
    }
    Ok(declared)
}

/// Resuelve, verifica y escribe el lock, dejando los árboles en la caché.
///
/// Con `locked` no se resuelve: se exige que el lock exista y coincida. Sin `refresh`
/// y con un lock que coincide, se reutiliza tal cual (comportamiento de `build`).
///
/// # Errors
/// Devuelve `PGS-E1804` (lock ausente o desactualizado con `--locked`), `PGS-E1803`,
/// `PGS-E1803`, `PGS-E1806`, `PGS-E1807` o `PGS-E1808` según la causa.
pub fn fetch(
    root: &Path,
    cache: &Cache,
    manifest: &Manifest,
    options: Options,
) -> Result<Lockfile, PkgError> {
    let declared = declared_sources(root, manifest)?;
    if options.force {
        // `--force` re-clona: la caché podría estar corrupta y es lo que pide el usuario.
        for source in declared.values() {
            if let Source::Git { url, .. } = source {
                let bare = cache.git_dir(url);
                if bare.exists() {
                    std::fs::remove_dir_all(&bare).map_err(|error| {
                        crate::io_error(
                            "PGS-E1803",
                            &format!("no se puede limpiar `{}`", bare.display()),
                            &error,
                        )
                    })?;
                }
            }
        }
    }
    let existing = Lockfile::read(root)?;
    if options.locked {
        let lock = existing.ok_or_else(|| {
            PkgError::stale_lock(
                "se pidió `--locked` y no existe `Tome.lock`",
                "ejecuta `pengu fetch` y repite",
            )
        })?;
        lock.matches(&declared)?;
        materialize(root, &lock, cache, options.offline)?;
        return Ok(lock);
    }
    if let Some(lock) = &existing {
        if !options.refresh && lock.matches(&declared).is_ok() {
            materialize(root, lock, cache, options.offline)?;
            return Ok(lock.clone());
        }
    }
    let git = ShellGit;
    let fetcher = Fetcher::new(&git, cache, options.offline);
    let lock = crate::resolver::resolve(root, manifest, &fetcher)?;
    if existing.as_ref() != Some(&lock) {
        lock.write(root)?;
    }
    Ok(lock)
}

/// Deja disponible el código de cada paquete: usa el vendor si existe (verificándolo) o
/// materializa los checkouts de la caché.
fn materialize(root: &Path, lock: &Lockfile, cache: &Cache, offline: bool) -> Result<(), PkgError> {
    if crate::vendor::exists(root) {
        return crate::vendor::verify(root, lock);
    }
    ensure_checkouts(lock, cache, offline)
}

/// Comprueba que el lock existe y coincide con el manifiesto (sin red).
///
/// # Errors
/// Devuelve `PGS-E1804` si falta el lock o no coincide.
pub fn verify(root: &Path, manifest: &Manifest) -> Result<Lockfile, PkgError> {
    let declared = declared_sources(root, manifest)?;
    let lock = Lockfile::read(root)?.ok_or_else(|| {
        PkgError::stale_lock(
            "no existe `Tome.lock`",
            "ejecuta `pengu fetch` para generarlo",
        )
    })?;
    lock.matches(&declared)?;
    Ok(lock)
}

/// Materializa en la caché los árboles de los paquetes git del lock.
///
/// # Errors
/// Devuelve `PGS-E1808` si `--offline` y falta la caché, o `PGS-E1806` si git falla.
pub fn ensure_checkouts(lock: &Lockfile, cache: &Cache, offline: bool) -> Result<(), PkgError> {
    let git = ShellGit;
    for package in &lock.packages {
        let source = Source::parse(&package.source)?;
        let Source::Git { url, .. } = source else {
            continue;
        };
        if package.commit.is_empty() {
            continue;
        }
        let checkout = cache.checkout_dir(&url, &package.commit);
        if checkout.is_dir() {
            continue;
        }
        let bare = cache.git_dir(&url);
        if !bare.is_dir() {
            if offline {
                return Err(PkgError::invalid_lock(
                    format!(
                        "`{}` no está en la caché y se pidió `--offline`",
                        package.name
                    ),
                    "ejecuta `pengu fetch` con red",
                ));
            }
            cache.ensure_dirs()?;
            git.clone_bare(&url, &bare)?;
        }
        git.checkout(&bare, &package.commit, &checkout)?;
    }
    Ok(())
}

/// Directorio donde build busca las fuentes de un paquete del lock.
///
/// Prefiere `vendor/<name>` (si existe) y cae a la caché.
#[must_use]
pub fn package_source_dir(
    root: &Path,
    cache: &Cache,
    package: &crate::lock::LockedPackage,
) -> PathBuf {
    let vendored = root.join("vendor").join(&package.name);
    if vendored.is_dir() {
        return vendored;
    }
    match Source::parse(&package.source) {
        Ok(Source::Git { url, .. }) if !package.commit.is_empty() => {
            cache.checkout_dir(&url, &package.commit)
        }
        Ok(Source::Path { path }) => PathBuf::from(path),
        _ => vendored,
    }
}

/// Añade o actualiza una dependencia en `Tome.toml` y re-resuelve el lock.
///
/// La escritura es transaccional: si la resolución falla, el manifiesto vuelve a su
/// contenido anterior.
///
/// # Errors
/// Devuelve el error del manifiesto (`PGS-E1803`) o el de la resolución.
pub fn add(
    root: &Path,
    cache: &Cache,
    options: Options,
    name: &str,
    spec: &str,
) -> Result<Lockfile, PkgError> {
    let path = root.join("Tome.toml");
    let original = std::fs::read_to_string(&path)
        .map_err(|error| crate::io_error("PGS-E1801", "no se puede leer `Tome.toml`", &error))?;
    let edited = crate::manifest::set_dependency(&original, name, spec)?;
    std::fs::write(&path, &edited).map_err(|error| {
        crate::io_error("PGS-E1801", "no se puede escribir `Tome.toml`", &error)
    })?;
    let manifest = pengu_project::parse_manifest(&edited).map_err(|diagnostic| {
        PkgError::plain(
            "PGS-E1803",
            format!("`Tome.toml` inválido: {}", diagnostic.render_compact()),
        )
    })?;
    let options = Options {
        refresh: true,
        ..options
    };
    match fetch(root, cache, &manifest, options) {
        Ok(lock) => Ok(lock),
        Err(error) => {
            let _ = std::fs::write(&path, original);
            Err(error)
        }
    }
}

/// Quita una dependencia de `Tome.toml` y re-resuelve el lock (podando huérfanos).
///
/// # Errors
/// `PGS-E1803` si la dependencia no existe, o el error de la resolución.
pub fn remove(
    root: &Path,
    cache: &Cache,
    options: Options,
    name: &str,
) -> Result<Lockfile, PkgError> {
    let path = root.join("Tome.toml");
    let original = std::fs::read_to_string(&path)
        .map_err(|error| crate::io_error("PGS-E1801", "no se puede leer `Tome.toml`", &error))?;
    let edited = crate::manifest::remove_dependency(&original, name)?;
    std::fs::write(&path, &edited).map_err(|error| {
        crate::io_error("PGS-E1801", "no se puede escribir `Tome.toml`", &error)
    })?;
    let manifest = pengu_project::parse_manifest(&edited).map_err(|diagnostic| {
        PkgError::plain(
            "PGS-E1803",
            format!("`Tome.toml` inválido: {}", diagnostic.render_compact()),
        )
    })?;
    let options = Options {
        refresh: true,
        ..options
    };
    match fetch(root, cache, &manifest, options) {
        Ok(lock) => Ok(lock),
        Err(error) => {
            let _ = std::fs::write(&path, original);
            Err(error)
        }
    }
}

/// Re-resuelve el grafo conservando los commits actuales salvo los que se actualizan.
///
/// `only` limita el movimiento a una dependencia; sin nombre se re-resuelven todas las
/// referencias móviles (`tag`/`branch`) y los `rev` se quedan fijos.
///
/// # Errors
/// `PGS-E1803` si el nombre no está en el manifiesto; el resto, como [`fetch`].
pub fn update(
    root: &Path,
    cache: &Cache,
    manifest: &Manifest,
    options: Options,
    only: Option<&str>,
) -> Result<Lockfile, PkgError> {
    if let Some(name) = only {
        if !manifest.dependencies.iter().any(|dep| dep.name == name) {
            return Err(PkgError::dependency_not_found(name));
        }
    }
    // Sin nombre se re-resuelve todo; con nombre se congelan los demás commits.
    let pins = if only.is_some() {
        match Lockfile::read(root)? {
            Some(lock) => lock.packages,
            None => Vec::new(),
        }
    } else {
        Vec::new()
    };
    let offline = options.offline;
    let git = ShellGit;
    let fetcher = Fetcher::new(&git, cache, offline);
    let lock = crate::resolver::resolve_keeping(root, manifest, &fetcher, &pins, only)?;
    lock.write(root)?;
    Ok(lock)
}

/// Nombre declarado por el `Tome.toml` de un directorio de paquete.
#[must_use]
pub fn package_name(dir: &Path) -> Option<String> {
    let text = std::fs::read_to_string(dir.join("Tome.toml")).ok()?;
    pengu_project::parse_manifest(&text)
        .ok()
        .map(|manifest| manifest.name)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    static COUNTER: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(name: &str) -> Self {
            let unique = COUNTER.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            let path = std::env::temp_dir()
                .join(format!("pengu-ops-{name}-{}-{unique}", std::process::id()));
            let _ = std::fs::remove_dir_all(&path);
            std::fs::create_dir_all(&path).expect("temp");
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn git(dir: &Path, args: &[&str]) {
        let output = Command::new("git")
            .args(args)
            .current_dir(dir)
            .env("GIT_TERMINAL_PROMPT", "0")
            .output()
            .expect("git");
        assert!(
            output.status.success(),
            "git {args:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    fn repo(dir: &Path, name: &str) {
        git(dir, &["init", "--quiet", "-b", "main"]);
        std::fs::write(
            dir.join("Tome.toml"),
            format!("[tome]\nname = \"{name}\"\nversion = \"1.0.0\"\npengu = \"0.6\"\n"),
        )
        .expect("manifiesto");
        std::fs::write(dir.join("lib.pengu"), "scroll demo\n").expect("fuente");
        git(dir, &["add", "."]);
        git(
            dir,
            &[
                "-c",
                "user.email=test@example.com",
                "-c",
                "user.name=Test",
                "commit",
                "--quiet",
                "-m",
                "inicial",
            ],
        );
        git(dir, &["tag", "v1"]);
    }

    fn root_manifest(dep_path: &Path) -> Manifest {
        pengu_project::parse_manifest(&format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n\
             [dependencies]\ntext = {{ git = \"{}\", tag = \"v1\" }}\n",
            dep_path.display()
        ))
        .expect("manifiesto")
    }

    #[test]
    fn force_reclona_la_cache() {
        let repo_dir = TempDir::new("repo-force");
        repo(repo_dir.path(), "text");
        let root = TempDir::new("root-force");
        let manifest = root_manifest(repo_dir.path());
        let cache = Cache::at(root.path().join("cache"));
        let options = Options::default();
        fetch(root.path(), &cache, &manifest, options).expect("fetch");
        let bare = cache.git_dir(&repo_dir.path().display().to_string());
        let marker = bare.join("marca");
        std::fs::write(&marker, "x").expect("marca");
        fetch(
            root.path(),
            &cache,
            &manifest,
            Options {
                refresh: true,
                force: true,
                ..options
            },
        )
        .expect("fetch forzado");
        assert!(!marker.exists(), "la caché se re-clona con --force");
        assert!(bare.exists(), "queda una caché limpia");
    }

    #[test]
    fn fetch_escribe_lock_y_lo_reutiliza() {
        let repo_dir = TempDir::new("repo");
        repo(repo_dir.path(), "text");
        let root = TempDir::new("root");
        let manifest = root_manifest(repo_dir.path());
        let cache = Cache::at(root.path().join("cache"));
        let lock = fetch(root.path(), &cache, &manifest, Options::default()).expect("fetch");
        assert_eq!(lock.packages.len(), 1);
        assert!(root.path().join("Tome.lock").is_file());
        let again = fetch(root.path(), &cache, &manifest, Options::default()).expect("fetch 2");
        assert_eq!(again, lock);
        let verified = verify(root.path(), &manifest).expect("verify");
        assert_eq!(verified, lock);
    }

    #[test]
    fn locked_sin_lock_falla_y_offline_sin_cache_falla() {
        let root = TempDir::new("root-malo");
        let manifest = pengu_project::parse_manifest(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n",
        )
        .expect("manifiesto");
        let cache = Cache::at(root.path().join("cache"));
        let options = Options {
            locked: true,
            ..Options::default()
        };
        let error = fetch(root.path(), &cache, &manifest, options).expect_err("locked");
        assert_eq!(error.code(), "PGS-E1804");

        let repo_dir = TempDir::new("repo-offline");
        repo(repo_dir.path(), "text");
        let manifest = root_manifest(repo_dir.path());
        let options = Options {
            offline: true,
            ..Options::default()
        };
        let error = fetch(root.path(), &cache, &manifest, options).expect_err("offline");
        assert_eq!(error.code(), "PGS-E1803");
    }

    #[test]
    fn package_source_dir_prefiere_vendor() {
        let root = TempDir::new("root-vendor");
        let cache = Cache::at(root.path().join("cache"));
        let package = crate::lock::LockedPackage {
            name: "text".into(),
            version: "1.0.0".into(),
            source: "path+../text".into(),
            commit: String::new(),
            checksum: format!("sha256-{}", "00".repeat(32)),
            features: Vec::new(),
            dependencies: Vec::new(),
        };
        std::fs::create_dir_all(root.path().join("vendor/text")).expect("vendor");
        assert_eq!(
            package_source_dir(root.path(), &cache, &package),
            root.path().join("vendor/text")
        );
    }
}
