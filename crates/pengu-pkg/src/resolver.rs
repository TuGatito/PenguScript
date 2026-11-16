//! Resolución del grafo de dependencias a un `Tome.lock` concreto.
//!
//! La resolución es en profundidad y determinista: recorre las dependencias en el orden
//! del manifiesto, resuelve cada fuente con la caché y devuelve el lock ordenado por
//! nombre. Detecta ciclos (`PGS-E1807` con el camino) y conflictos de fuente o versión.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use pengu_project::{Manifest, parse_manifest};

use crate::PkgError;
use crate::git::{Fetcher, Resolved};
use crate::lock::{LockedPackage, Lockfile};
use crate::source::{GitRef, Source};
use crate::tree_hash;

/// Resuelve el grafo completo de `manifest` (con raíz en `root`) a un lock.
///
/// # Errors
/// Devuelve `PGS-E1803` (path inexistente o manifiesto ilegible), `PGS-E1806`
/// (referencia git inválida) o `PGS-E1807` (ciclo, conflicto de fuente o de versión).
pub fn resolve(
    root: &Path,
    manifest: &Manifest,
    fetcher: &Fetcher<'_>,
) -> Result<Lockfile, PkgError> {
    resolve_keeping(root, manifest, fetcher, &[], None)
}

/// Resuelve conservando los commits ya fijados en `pins`.
///
/// Si `only` es `Some(nombre)`, el paquete indicado se vuelve a resolver (sus `tag` y
/// `branch` pueden moverse) y el resto se queda en el commit del pin. Si es `None`, se
/// re-resuelve todo el grafo salvo los `rev`, que nunca se mueven.
///
/// # Errors
/// Las mismas que [`resolve`].
pub fn resolve_keeping(
    root: &Path,
    manifest: &Manifest,
    fetcher: &Fetcher<'_>,
    pins: &[LockedPackage],
    only: Option<&str>,
) -> Result<Lockfile, PkgError> {
    let mut resolver = Resolver {
        fetcher,
        packages: BTreeMap::new(),
        stack: Vec::new(),
        pins,
        only,
        enabled: BTreeMap::new(),
    };
    for dependency in &manifest.dependencies {
        resolver.visit(
            dependency,
            root,
            &dependency.features,
            dependency.default_features,
        )?;
    }
    Lockfile::new(resolver.packages.into_values().collect())
}

/// Construye la fuente de una dependencia del manifiesto.
///
/// # Errors
/// Devuelve `PGS-E1806` si no declara `git` ni `path`, declara ambos, o le falta
/// exactamente una referencia git.
pub fn dependency_source(dependency: &pengu_project::Dependency) -> Result<Source, PkgError> {
    match (&dependency.git, &dependency.path) {
        (Some(_), Some(_)) => Err(PkgError::plain(
            "PGS-E1806",
            format!(
                "`{}` declara `git` y `path` a la vez; elige una fuente",
                dependency.name
            ),
        )
        .with_help("deja solo `git = …` o solo `path = …`")),
        (Some(url), None) => {
            let reference = match (&dependency.tag, &dependency.branch, &dependency.rev) {
                (Some(tag), None, None) => GitRef::Tag(tag.clone()),
                (None, Some(branch), None) => GitRef::Branch(branch.clone()),
                (None, None, Some(rev)) => GitRef::Rev(rev.clone()),
                _ => {
                    return Err(PkgError::plain(
                        "PGS-E1806",
                        format!(
                            "`{}` debe declarar exactamente una de `tag`, `branch` o `rev`",
                            dependency.name
                        ),
                    )
                    .with_help("añade la referencia que quieras seguir"));
                }
            };
            Source::git(url, reference)
        }
        (None, Some(path)) => Source::path(path),
        (None, None) => Err(PkgError::plain(
            "PGS-E1806",
            format!("`{}` no declara `git` ni `path`", dependency.name),
        )
        .with_help("añade `git = \"URL\"` con su referencia, o `path = \"…\"`")),
    }
}

struct Resolver<'a> {
    fetcher: &'a Fetcher<'a>,
    packages: BTreeMap<String, LockedPackage>,
    stack: Vec<String>,
    pins: &'a [LockedPackage],
    only: Option<&'a str>,
    /// Features efectivas de cada paquete ya visitado.
    enabled: BTreeMap<String, Vec<String>>,
}

impl Resolver<'_> {
    #[allow(clippy::too_many_lines)]
    /// Visita una dependencia con las features que pide su consumidor.
    ///
    /// Las features son aditivas: si el paquete ya estaba resuelto se unen las nuevas,
    /// se recalcula su cierre y, si el conjunto creció, se vuelve a bajar a sus hijos
    /// (una feature puede activar una dependencia opcional que antes se omitía).
    fn visit(
        &mut self,
        dependency: &pengu_project::Dependency,
        base: &Path,
        requested: &[String],
        default_features: bool,
    ) -> Result<(), PkgError> {
        let source = match dependency_source(dependency)? {
            Source::Path { path } if Path::new(&path).is_relative() => {
                Source::path(&base.join(&path).display().to_string())?
            }
            other => other,
        };
        if let Some(position) = self.stack.iter().position(|name| name == &dependency.name) {
            let mut path = self.stack[position..].to_vec();
            path.push(dependency.name.clone());
            return Err(PkgError::plain(
                "PGS-E1807",
                format!("ciclo de dependencias: {}", path.join(" -> ")),
            )
            .with_help("rompe el ciclo quitando una de las dependencias"));
        }
        let canonical = source.canonical();
        let pinned = self
            .pin_for(&dependency.name, &canonical)
            .map(|pin| (pin.commit.clone(), pin.checksum.clone()));
        let resolved = if let Some((commit, _)) = &pinned {
            let path = self.fetcher.prepare_pinned(&source, commit)?;
            Resolved {
                commit: commit.clone(),
                path,
            }
        } else {
            self.fetcher.prepare(&source)?
        };
        let package = read_package(&resolved, &dependency.name)?;
        if package.name != dependency.name {
            return Err(PkgError::plain(
                "PGS-E1807",
                format!(
                    "`{}` declara en su `Tome.toml` el nombre `{}`",
                    dependency.name, package.name
                ),
            )
            .with_help("los renombrados no están soportados: usa el nombre real"));
        }
        if let Some(existing) = self.packages.get(&dependency.name) {
            if existing.source != canonical {
                return Err(conflict(
                    &dependency.name,
                    &existing.source,
                    &canonical,
                    "fuente",
                ));
            }
            if existing.version != package.version {
                return Err(conflict(
                    &dependency.name,
                    &existing.version,
                    &package.version,
                    "versión",
                ));
            }
        }
        let mut wanted = requested.to_vec();
        if default_features {
            wanted.push("default".to_owned());
        }
        let (features, activated) = expand_features(&package, &wanted);
        let grew = self.enabled.get(&dependency.name).is_none_or(|previous| {
            features
                .iter()
                .chain(activated.iter())
                .any(|feature| !previous.contains(feature))
        });
        if !grew && self.packages.contains_key(&dependency.name) {
            return Ok(());
        }
        let mut tracked = features.clone();
        tracked.extend(activated.iter().cloned());
        tracked.sort();
        tracked.dedup();
        self.enabled.insert(dependency.name.clone(), tracked);
        let mut children = Vec::new();
        self.stack.push(dependency.name.clone());
        for child in &package.dependencies {
            if child.optional && !features.contains(&child.name) && !activated.contains(&child.name)
            {
                continue;
            }
            self.visit(
                child,
                &resolved.path,
                &child.features,
                child.default_features,
            )?;
            children.push(child.name.clone());
        }
        self.stack.pop();
        children.sort();
        children.dedup();
        let checksum = match &pinned {
            Some((_, checksum)) => checksum.clone(),
            None => tree_hash::tree_checksum(&resolved.path)?,
        };
        self.packages.insert(
            dependency.name.clone(),
            LockedPackage {
                name: dependency.name.clone(),
                version: package.version,
                source: canonical,
                commit: resolved.commit,
                checksum,
                features,
                dependencies: children,
            },
        );
        Ok(())
    }
}

/// Cierre transitivo de un conjunto de features sobre la tabla `[features]`.
///
/// Una feature puede activar otras features del mismo paquete; si el nombre que aparece
/// en `enables` es el de una dependencia opcional, esa dependencia se activa (no se
/// añade como feature). Una dependencia opcional también se activa con la feature de su
/// mismo nombre, como en Cargo.
fn expand_features(package: &Manifest, wanted: &[String]) -> (Vec<String>, Vec<String>) {
    let mut enabled: Vec<String> = Vec::new();
    let mut activated: Vec<String> = Vec::new();
    let mut queue: Vec<String> = wanted.to_vec();
    while let Some(feature) = queue.pop() {
        if enabled.contains(&feature) || activated.contains(&feature) {
            continue;
        }
        let entry = package.features.iter().find(|entry| entry.name == feature);
        if entry.is_none()
            && package
                .dependencies
                .iter()
                .any(|dep| dep.optional && dep.name == feature)
        {
            activated.push(feature);
            continue;
        }
        enabled.push(feature.clone());
        if let Some(entry) = entry {
            queue.extend(entry.enables.iter().cloned());
        }
    }
    enabled.sort();
    enabled.dedup();
    activated.sort();
    activated.dedup();
    (enabled, activated)
}

impl Resolver<'_> {
    /// Pin aplicable al paquete: mismo nombre y misma fuente, y no es el que se actualiza.
    fn pin_for(&self, name: &str, canonical: &str) -> Option<&LockedPackage> {
        if self.only == Some(name) {
            return None;
        }
        self.pins
            .iter()
            .find(|pin| pin.name == name && pin.source == canonical)
    }
}

fn read_package(resolved: &Resolved, name: &str) -> Result<Manifest, PkgError> {
    let manifest_path = resolved.path.join("Tome.toml");
    let text = std::fs::read_to_string(&manifest_path).map_err(|error| {
        crate::io_error(
            "PGS-E1803",
            &format!(
                "`{name}` no tiene un `Tome.toml` legible en `{}`",
                resolved.path.display()
            ),
            &error,
        )
    })?;
    parse_manifest(&text).map_err(|diagnostic| {
        PkgError::plain(
            "PGS-E1803",
            format!(
                "el `Tome.toml` de `{name}` no es válido: {}",
                diagnostic.render_compact()
            ),
        )
        .with_help("corrige el manifiesto del paquete o fija otra referencia")
    })
}

fn conflict(name: &str, first: &str, second: &str, what: &str) -> PkgError {
    PkgError::plain(
        "PGS-E1807",
        format!("conflicto de {what} para `{name}`: `{first}` y `{second}`"),
    )
    .with_help("unifica la fuente o la versión en `Tome.toml`")
}

/// Ruta de un paquete dentro de `vendor/`, si ya está vendoreado.
#[must_use]
pub fn vendored_path(root: &Path, name: &str) -> Option<PathBuf> {
    let path = root.join("vendor").join(name);
    path.is_dir().then_some(path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cache::Cache;
    use crate::git::ShellGit;
    use std::process::Command;

    static COUNTER: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(name: &str) -> Self {
            let unique = COUNTER.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            let path = std::env::temp_dir().join(format!(
                "pengu-resolver-{name}-{}-{unique}",
                std::process::id()
            ));
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

    fn make_repo(dir: &Path, manifest: &str) {
        git(dir, &["init", "--quiet", "-b", "main"]);
        std::fs::write(dir.join("Tome.toml"), manifest).expect("manifiesto");
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

    fn manifest(dependencies: &str) -> Manifest {
        parse_manifest(&format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n[dependencies]\n{dependencies}"
        ))
        .expect("manifiesto")
    }

    #[test]
    fn resuelve_git_y_produce_lock_ordenado() {
        let repo = TempDir::new("git");
        make_repo(
            repo.path(),
            "[tome]\nname = \"text\"\nversion = \"1.0.0\"\npengu = \"0.6\"\n",
        );
        let cache = TempDir::new("cache");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, false);
        let manifest = manifest(&format!(
            "text = {{ git = \"{}\", tag = \"v1\" }}\n",
            repo.path().display()
        ));
        let lock = resolve(repo.path(), &manifest, &fetcher).expect("resolver");
        assert_eq!(lock.packages.len(), 1);
        let package = &lock.packages[0];
        assert_eq!(package.name, "text");
        assert_eq!(package.version, "1.0.0");
        assert!(package.checksum.starts_with("sha256-"));
        assert_eq!(package.commit.len(), 40);
        assert!(package.source.starts_with("git+"));
    }

    #[test]
    fn las_features_activan_dependencias_opcionales() {
        let root = TempDir::new("root-features");
        let base = TempDir::new("base-features");
        let opt = TempDir::new("opt-features");
        std::fs::write(
            opt.path().join("Tome.toml"),
            "[tome]\nname = \"opt\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n",
        )
        .expect("opt");
        std::fs::write(
            base.path().join("Tome.toml"),
            format!(
                "[tome]\nname = \"base\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n                 [dependencies]\nopt = {{ path = \"{}\", optional = true }}\n                 [features]\ndefault = []\nextra = [\"opt\"]\n",
                opt.path().display()
            ),
        )
        .expect("base");
        let without = format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n[dependencies]\n\
             base = {{ path = \"{}\" }}\n",
            base.path().display()
        );
        let manifest = parse_manifest(&without).expect("manifiesto");
        let cache = TempDir::new("cache-features");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, true);
        let lock = resolve(root.path(), &manifest, &fetcher).expect("sin features");
        assert_eq!(lock.packages.len(), 1, "opt sigue inactiva");
        assert_eq!(lock.packages[0].features, vec!["default".to_owned()]);

        let with = without.replace(
            &format!("base = {{ path = \"{}\" }}", base.path().display()),
            &format!(
                "base = {{ path = \"{}\", features = [\"extra\"] }}",
                base.path().display()
            ),
        );
        let manifest = parse_manifest(&with).expect("manifiesto");
        let lock = resolve(root.path(), &manifest, &fetcher).expect("con features");
        let names: Vec<&str> = lock.packages.iter().map(|p| p.name.as_str()).collect();
        assert_eq!(names, vec!["base", "opt"]);
        let base_locked = lock.package("base").expect("base");
        assert_eq!(
            base_locked.features,
            vec!["default".to_owned(), "extra".to_owned()]
        );
        assert_eq!(
            base_locked.dependencies,
            vec!["opt".to_owned()],
            "la arista se materializa con la feature"
        );
    }

    #[test]
    fn une_las_features_de_varios_consumidores() {
        let root = TempDir::new("root-union");
        let first = TempDir::new("first-union");
        let second = TempDir::new("second-union");
        let base = TempDir::new("base-union");
        let opt = TempDir::new("opt-union");
        std::fs::write(
            opt.path().join("Tome.toml"),
            "[tome]\nname = \"opt\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n",
        )
        .expect("opt");
        std::fs::write(
            base.path().join("Tome.toml"),
            format!(
                "[tome]\nname = \"base\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n                 [dependencies]\nopt = {{ path = \"{}\", optional = true }}\n                 [features]\ndefault = []\nextra = [\"opt\"]\n",
                opt.path().display()
            ),
        )
        .expect("base");
        for (dir, name, features) in [
            (&first, "first", "features = [\"extra\"]"),
            (&second, "second", "features = [\"default\"]"),
        ] {
            std::fs::write(
                dir.path().join("Tome.toml"),
                format!(
                    "[tome]\nname = \"{name}\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n                     [dependencies]\nbase = {{ path = \"{}\", {features} }}\n",
                    base.path().display()
                ),
            )
            .expect("consumidor");
        }
        let text = format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n[dependencies]\n\
             first = {{ path = \"{}\" }}\nsecond = {{ path = \"{}\" }}\n",
            first.path().display(),
            second.path().display()
        );
        let manifest = parse_manifest(&text).expect("manifiesto");
        let cache = TempDir::new("cache-union");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, true);
        let lock = resolve(root.path(), &manifest, &fetcher).expect("union");
        let base_locked = lock.package("base").expect("base");
        assert_eq!(
            base_locked.features,
            vec!["default".to_owned(), "extra".to_owned()]
        );
        assert!(
            lock.package("opt").is_some(),
            "la feature de `first` la activa"
        );
    }

    #[test]
    fn detecta_conflicto_de_fuente_entre_consumidores() {
        let root = TempDir::new("root-conflicto");
        let first = TempDir::new("first-conflicto");
        let second = TempDir::new("second-conflicto");
        let left = TempDir::new("left-conflicto");
        let right = TempDir::new("right-conflicto");
        for (dir, version) in [(&left, "1.0.0"), (&right, "2.0.0")] {
            std::fs::write(
                dir.path().join("Tome.toml"),
                format!("[tome]\nname = \"shared\"\nversion = \"{version}\"\npengu = \"0.6\"\n"),
            )
            .expect("shared");
        }
        for (dir, name, target) in [
            (&first, "first", left.path()),
            (&second, "second", right.path()),
        ] {
            std::fs::write(
                dir.path().join("Tome.toml"),
                format!(
                    "[tome]\nname = \"{name}\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n\
                     [dependencies]\nshared = {{ path = \"{}\" }}\n",
                    target.display()
                ),
            )
            .expect("consumidor");
        }
        let text = format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n[dependencies]\n\
             first = {{ path = \"{}\" }}\nsecond = {{ path = \"{}\" }}\n",
            first.path().display(),
            second.path().display()
        );
        let manifest = parse_manifest(&text).expect("manifiesto");
        let cache = TempDir::new("cache-conflicto");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, true);
        let error = resolve(root.path(), &manifest, &fetcher).expect_err("conflicto");
        assert_eq!(error.code(), "PGS-E1807");
        assert!(error.message.contains("fuente"), "{}", error.message);
        assert!(error.message.contains("shared"), "{}", error.message);
    }

    #[test]
    fn resuelve_path_y_detecta_ciclo() {
        let root = TempDir::new("root");
        let dep = TempDir::new("dep");
        std::fs::write(
            dep.path().join("Tome.toml"),
            format!(
                "[tome]\nname = \"local\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n\
                 [dependencies]\nraiz = {{ path = \"{}\" }}\n",
                root.path().display()
            ),
        )
        .expect("manifiesto");
        let cache = TempDir::new("cache");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, true);
        let text = format!(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n[dependencies]\n\
             local = {{ path = \"{}\" }}\n",
            dep.path().display()
        );
        std::fs::write(root.path().join("Tome.toml"), &text).expect("raiz");
        let manifest = parse_manifest(&text).expect("manifiesto");
        let error = resolve(root.path(), &manifest, &fetcher).expect_err("ciclo");
        assert_eq!(error.code(), "PGS-E1807");
        assert!(error.message.contains("->"), "{}", error.message);
    }
}
