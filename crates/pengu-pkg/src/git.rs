//! Acceso a git a través del ejecutable del sistema.
//!
//! No hay dependencias externas: se invoca `git` con `LC_ALL=C`,
//! `GIT_TERMINAL_PROMPT=0` y `protocol.version=2`. El trait [`Git`] permite sustituir
//! la implementación en tests de la lógica de resolución sin tocar la red.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::PkgError;
use crate::cache::Cache;
use crate::source::{GitRef, Source};

/// Operaciones de git que necesita el gestor de paquetes.
pub trait Git {
    /// Clona `url` como repositorio bare en `dest`.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806` si el clonado falla.
    fn clone_bare(&self, url: &str, dest: &Path) -> Result<(), PkgError>;
    /// Actualiza refs y tags de un repositorio bare.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806` si la actualización falla.
    fn fetch(&self, bare: &Path) -> Result<(), PkgError>;
    /// Resuelve una referencia a un commit completo, si existe.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806` si `git` no se puede ejecutar.
    fn resolve(&self, bare: &Path, reference: &GitRef) -> Result<Option<String>, PkgError>;
    /// Materializa `commit` en `dest`.
    ///
    /// # Errors
    /// Devuelve `PGS-E1806` si no se puede materializar el árbol.
    fn checkout(&self, bare: &Path, commit: &str, dest: &Path) -> Result<(), PkgError>;
}

/// Implementación con el `git` del sistema.
#[derive(Clone, Copy, Debug, Default)]
pub struct ShellGit;

impl Git for ShellGit {
    fn clone_bare(&self, url: &str, dest: &Path) -> Result<(), PkgError> {
        run(
            &[
                "clone".to_owned(),
                "--bare".to_owned(),
                "--quiet".to_owned(),
                url.to_owned(),
                dest.display().to_string(),
            ],
            None,
        )
        .map(|_| ())
        .map_err(|error| {
            error.with_help(format!(
                "no se pudo clonar `{url}`; comprueba la URL y los permisos"
            ))
        })
    }

    fn fetch(&self, bare: &Path) -> Result<(), PkgError> {
        run(
            &[
                "-C".to_owned(),
                bare.display().to_string(),
                "fetch".to_owned(),
                "--prune".to_owned(),
                "--tags".to_owned(),
                "--quiet".to_owned(),
                "origin".to_owned(),
                // En un clon desnudo no hay refspec por defecto: sin esto `origin/main`
                // no se actualiza y `pengu update` no vería commits nuevos.
                "+refs/heads/*:refs/remotes/origin/*".to_owned(),
            ],
            None,
        )
        .map(|_| ())
        .map_err(|error| {
            error.with_help("no se pudo actualizar la caché; prueba `pengu fetch --force`")
        })
    }

    fn resolve(&self, bare: &Path, reference: &GitRef) -> Result<Option<String>, PkgError> {
        let value = reference.value();
        let candidates = match reference {
            GitRef::Tag(_) => vec![format!("refs/tags/{value}"), value.to_owned()],
            // Primero el remoto: en un clon desnudo `refs/heads/<rama>` se queda en el
            // commit del clon y no se actualiza con `fetch`.
            GitRef::Branch(_) => vec![
                format!("refs/remotes/origin/{value}"),
                format!("refs/heads/{value}"),
                value.to_owned(),
            ],
            GitRef::Rev(_) => vec![value.to_owned(), format!("refs/tags/{value}")],
        };
        for candidate in candidates {
            let spec = format!("{candidate}^{{commit}}");
            let output = Command::new("git")
                .args(["-C", &bare.display().to_string()])
                .args(["-c", "protocol.version=2"])
                .args(["rev-parse", "--verify", "--quiet", &spec])
                .env("LC_ALL", "C")
                .env("GIT_TERMINAL_PROMPT", "0")
                .output()
                .map_err(|error| git_missing(&error))?;
            if output.status.success() {
                let commit = String::from_utf8_lossy(&output.stdout).trim().to_owned();
                if !commit.is_empty() {
                    return Ok(Some(commit));
                }
            }
        }
        Ok(None)
    }

    fn checkout(&self, bare: &Path, commit: &str, dest: &Path) -> Result<(), PkgError> {
        if dest.exists() {
            std::fs::remove_dir_all(dest).map_err(|error| {
                crate::io_error(
                    "PGS-E1806",
                    &format!("no se puede limpiar `{}`", dest.display()),
                    &error,
                )
            })?;
        }
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent).map_err(|error| {
                crate::io_error(
                    "PGS-E1806",
                    &format!("no se puede crear `{}`", parent.display()),
                    &error,
                )
            })?;
        }
        run(
            &[
                "clone".to_owned(),
                "--quiet".to_owned(),
                "--no-checkout".to_owned(),
                bare.display().to_string(),
                dest.display().to_string(),
            ],
            None,
        )?;
        run(
            &[
                "-C".to_owned(),
                dest.display().to_string(),
                "checkout".to_owned(),
                "--quiet".to_owned(),
                "--detach".to_owned(),
                commit.to_owned(),
            ],
            None,
        )
        .map_err(|error| error.with_help("el commit no está en la caché; ejecuta `pengu fetch`"))?;
        std::fs::write(dest.join(".pengu-commit"), format!("{commit}\n")).map_err(|error| {
            crate::io_error(
                "PGS-E1806",
                &format!(
                    "no se puede escribir la marca de commit en `{}`",
                    dest.display()
                ),
                &error,
            )
        })?;
        Ok(())
    }
}

/// Paquete resuelto: commit (si es git) y directorio con el árbol.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Resolved {
    /// Commit completo, vacío para dependencias de tipo `path`.
    pub commit: String,
    /// Directorio con el árbol de la dependencia.
    pub path: PathBuf,
}

/// Resuelve y materializa una fuente usando la caché.
pub struct Fetcher<'a> {
    git: &'a dyn Git,
    cache: &'a Cache,
    offline: bool,
}

impl<'a> Fetcher<'a> {
    /// Crea un resolvedor con la caché y la política de red indicadas.
    pub fn new(git: &'a dyn Git, cache: &'a Cache, offline: bool) -> Self {
        Self {
            git,
            cache,
            offline,
        }
    }

    /// Resuelve `source` a un commit y un árbol listo para usar.
    ///
    /// # Errors
    /// Devuelve `PGS-E1803` (path inexistente o `--offline` sin caché) o `PGS-E1806`
    /// (referencia inválida o git no disponible).
    pub fn prepare(&self, source: &Source) -> Result<Resolved, PkgError> {
        match source {
            Source::Path { path } => {
                let path = PathBuf::from(path);
                if !path.is_dir() {
                    return Err(PkgError::plain(
                        "PGS-E1803",
                        format!("la dependencia local `{}` no existe", path.display()),
                    )
                    .with_help("revisa la ruta en `Tome.toml`"));
                }
                let path = path.canonicalize().map_err(|error| {
                    crate::io_error(
                        "PGS-E1803",
                        &format!("no se puede resolver `{}`", path.display()),
                        &error,
                    )
                })?;
                Ok(Resolved {
                    commit: String::new(),
                    path,
                })
            }
            Source::Git { url, reference } => {
                let bare = self.cache.git_dir(url);
                if !bare.exists() {
                    if self.offline {
                        return Err(PkgError::plain(
                            "PGS-E1803",
                            format!("`{url}` no está en la caché y se pidió `--offline`"),
                        )
                        .with_help("ejecuta `pengu fetch` con red"));
                    }
                    self.cache.ensure_dirs()?;
                    self.git.clone_bare(url, &bare)?;
                } else if !self.offline {
                    self.git.fetch(&bare)?;
                }
                let commit = self.git.resolve(&bare, reference)?.ok_or_else(|| {
                    PkgError::plain(
                        "PGS-E1806",
                        format!(
                            "no se encuentra la referencia `{}` en `{url}`",
                            reference.value()
                        ),
                    )
                    .with_help("revisa `tag`/`branch`/`rev` en `Tome.toml`")
                })?;
                let dest = self.cache.checkout_dir(url, &commit);
                if !dest.exists() {
                    self.git.checkout(&bare, &commit, &dest)?;
                }
                Ok(Resolved { commit, path: dest })
            }
        }
    }

    /// Materializa un commit ya fijado por el lock (sin volver a resolver la referencia).
    ///
    /// # Errors
    /// `PGS-E1803` si el commit no está y se pidió `--offline`.
    pub fn prepare_pinned(&self, source: &Source, commit: &str) -> Result<PathBuf, PkgError> {
        match source {
            Source::Path { path } => Ok(PathBuf::from(path).canonicalize().map_err(|error| {
                crate::io_error(
                    "PGS-E1803",
                    &format!("no se puede resolver `{path}`"),
                    &error,
                )
            })?),
            Source::Git { url, .. } => {
                let bare = self.cache.git_dir(url);
                if !bare.exists() {
                    if self.offline {
                        return Err(PkgError::plain(
                            "PGS-E1803",
                            format!("`{url}` no está en la caché y se pidió `--offline`"),
                        )
                        .with_help("ejecuta `pengu fetch` con red"));
                    }
                    self.cache.ensure_dirs()?;
                    self.git.clone_bare(url, &bare)?;
                }
                let dest = self.cache.checkout_dir(url, commit);
                if !dest.exists() {
                    self.git.checkout(&bare, commit, &dest)?;
                }
                Ok(dest)
            }
        }
    }

    /// Tags publicados en un remoto, sin descargar el repositorio.
    ///
    /// # Errors
    /// `PGS-E1806` si no se puede consultar el remoto.
    pub fn remote_tags(&self, url: &str) -> Result<Vec<String>, PkgError> {
        let args = ["ls-remote", "--tags", "--refs", url].map(str::to_owned);
        let output = run(&args, None)?;
        let mut tags = Vec::new();
        for line in output.lines() {
            if let Some((_, reference)) = line.split_once('\t') {
                if let Some(name) = reference.strip_prefix("refs/tags/") {
                    tags.push(name.to_owned());
                }
            }
        }
        tags.sort();
        tags.dedup();
        Ok(tags)
    }

    /// Rama por defecto del remoto (`HEAD` simbólico).
    ///
    /// # Errors
    /// `PGS-E1806` si no se puede consultar el remoto.
    pub fn remote_default_branch(&self, url: &str) -> Result<Option<String>, PkgError> {
        let args = ["ls-remote", "--symref", url, "HEAD"].map(str::to_owned);
        let output = run(&args, None)?;
        for line in output.lines() {
            if let Some(rest) = line.strip_prefix("ref: refs/heads/") {
                if let Some((name, _)) = rest.split_once('\t') {
                    return Ok(Some(name.to_owned()));
                }
            }
        }
        Ok(None)
    }
}

fn git_missing(error: &std::io::Error) -> PkgError {
    PkgError::plain("PGS-E1806", format!("no se puede ejecutar `git`: {error}"))
        .with_help("instala git y comprueba que está en el `PATH`")
}

fn run(args: &[String], cwd: Option<&Path>) -> Result<String, PkgError> {
    let mut command = Command::new("git");
    command
        .args(["-c", "protocol.version=2"])
        .args(args)
        .env("LC_ALL", "C")
        .env("GIT_TERMINAL_PROMPT", "0");
    if let Some(cwd) = cwd {
        command.current_dir(cwd);
    }
    let output = command.output().map_err(|error| git_missing(&error))?;
    if output.status.success() {
        return Ok(String::from_utf8_lossy(&output.stdout).into_owned());
    }
    let stderr = String::from_utf8_lossy(&output.stderr);
    let detail = stderr.lines().last().unwrap_or("sin detalle").trim();
    Err(PkgError::plain(
        "PGS-E1806",
        format!("`git {}` falló: {detail}", args.join(" ")),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    static COUNTER: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(name: &str) -> Self {
            let unique = COUNTER.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            let path = std::env::temp_dir()
                .join(format!("pengu-pkg-{name}-{}-{unique}", std::process::id()));
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

    fn repo_with_tag(dir: &Path) -> String {
        git(dir, &["init", "--quiet", "-b", "main"]);
        std::fs::write(dir.join("datos.txt"), "hola\n").expect("archivo");
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
        let output = Command::new("git")
            .args(["rev-parse", "HEAD"])
            .current_dir(dir)
            .output()
            .expect("rev-parse");
        String::from_utf8_lossy(&output.stdout).trim().to_owned()
    }

    #[test]
    fn resuelve_tag_y_materializa_el_arbol() {
        let repo = TempDir::new("repo");
        let commit = repo_with_tag(repo.path());
        let cache = TempDir::new("cache");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, false);
        let source = Source::git(&repo.path().display().to_string(), GitRef::Tag("v1".into()))
            .expect("source");
        let resolved = fetcher.prepare(&source).expect("prepare");
        assert_eq!(resolved.commit, commit);
        assert_eq!(
            std::fs::read_to_string(resolved.path.join("datos.txt")).expect("lee"),
            "hola\n"
        );
        assert!(cache.git_dir(&repo.path().display().to_string()).is_dir());
        // Segundo intento reutiliza el checkout existente.
        let again = fetcher.prepare(&source).expect("prepare otra vez");
        assert_eq!(again.path, resolved.path);
    }

    #[test]
    fn resuelve_rama_y_rev() {
        let repo = TempDir::new("repo-rama");
        let commit = repo_with_tag(repo.path());
        let cache = TempDir::new("cache-rama");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, false);
        let url = repo.path().display().to_string();
        let branch = fetcher
            .prepare(&Source::git(&url, GitRef::Branch("main".into())).expect("source"))
            .expect("rama");
        assert_eq!(branch.commit, commit);
        let rev = fetcher
            .prepare(&Source::git(&url, GitRef::Rev(commit.clone())).expect("source"))
            .expect("rev");
        assert_eq!(rev.commit, commit);
    }

    #[test]
    fn referencia_inexistente_da_e1806() {
        let repo = TempDir::new("repo-mala");
        repo_with_tag(repo.path());
        let cache = TempDir::new("cache-mala");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, false);
        let source = Source::git(
            &repo.path().display().to_string(),
            GitRef::Tag("no-existe".into()),
        )
        .expect("source");
        let error = fetcher.prepare(&source).expect_err("debe fallar");
        assert_eq!(error.code(), "PGS-E1806");
    }

    #[test]
    fn offline_sin_cache_da_e1808() {
        let cache = TempDir::new("cache-offline");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, true);
        let source = Source::git("https://example.com/inexistente", GitRef::Tag("v1".into()))
            .expect("source");
        let error = fetcher.prepare(&source).expect_err("debe fallar");
        assert_eq!(error.code(), "PGS-E1803");
    }

    #[test]
    fn path_inexistente_da_e1803() {
        let cache = TempDir::new("cache-path");
        let cache = Cache::at(cache.path());
        let git = ShellGit;
        let fetcher = Fetcher::new(&git, &cache, false);
        let source = Source::path("/ruta/que/no/existe").expect("source");
        let error = fetcher.prepare(&source).expect_err("debe fallar");
        assert_eq!(error.code(), "PGS-E1803");
    }
}
