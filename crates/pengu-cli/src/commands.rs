//! Implementación de los subcomandos.

use std::path::{Path, PathBuf};

use pengu_pkg::PkgError;
use pengu_pkg::cache::Cache;
use pengu_pkg::git::{Fetcher, ShellGit};
use pengu_pkg::lock::Lockfile;
use pengu_pkg::ops::{self, Options};
use pengu_pkg::spec::{self, Requested};
use pengu_pkg::tree;
use pengu_project::Manifest;

use crate::args::{self, Cli, Command, FmtArgs, LintArgs, WatchAction};
use std::fmt::Write as _;

use crate::env;

/// Ejecuta un subcomando y devuelve el código de salida.
#[must_use]
pub fn dispatch(cli: &Cli) -> i32 {
    match cli.command {
        Command::Help => {
            print!("{}", args::USAGE);
            0
        }
        Command::Version => {
            if cli.json {
                println!("{}", crate::release::version_json());
            } else {
                println!("{}", crate::release::version_text());
            }
            0
        }
        Command::Doctor => {
            let doctor = crate::release::Doctor::run();
            if cli.json {
                println!("{}", doctor.json());
            } else {
                doctor.print();
            }
            doctor.code()
        }
        Command::Completions(ref completions) => {
            print!("{}", crate::release::completions(completions));
            0
        }
        Command::Man => {
            print!("{}", crate::release::man_page());
            0
        }
        Command::New(ref new) => match new_project(new) {
            Ok(code) => code,
            Err(ProjectError::Usage(message)) => {
                eprintln!("error: {message}");
                2
            }
            Err(ProjectError::Pkg(error)) => {
                eprintln!("{error}");
                1
            }
            Err(ProjectError::Io(message)) => {
                eprintln!("error: {message}");
                1
            }
        },
        Command::Fmt(ref fmt) => format_files(fmt, cli.check),
        Command::Fix(ref fix) => fix_project(fix),
        Command::Doc(ref doc) => generate_docs(doc),
        Command::Bench(ref bench) => benchmark(bench),
        Command::Lint(ref lint) => lint_files(lint),
        Command::Explain(ref explain) => explain_code(&explain.code),
        Command::Bindgen(ref bindgen) => bindgen_header(bindgen, cli.verbose),
        Command::Lsp => pengu_lsp::run_stdio(pengu_lsp::Config {
            log_path: std::env::var_os("PENGU_LSP_LOG").map(std::path::PathBuf::from),
            ..pengu_lsp::Config::default()
        }),
        Command::Fetch
        | Command::Tree
        | Command::Build
        | Command::Check
        | Command::Watch(_)
        | Command::Run
        | Command::Test
        | Command::Add(_)
        | Command::Remove(_)
        | Command::Update(_)
        | Command::Vendor
        | Command::Size => match project_command(cli) {
            Ok(code) => code,
            Err(ProjectError::Usage(message)) => {
                eprintln!("error: {message}");
                2
            }
            Err(ProjectError::Pkg(error)) => {
                eprintln!("{error}");
                1
            }
            Err(ProjectError::Io(message)) => {
                eprintln!("error: {message}");
                1
            }
        },
    }
}

enum ProjectError {
    Usage(String),
    Pkg(PkgError),
    Io(String),
}

impl From<PkgError> for ProjectError {
    fn from(error: PkgError) -> Self {
        Self::Pkg(error)
    }
}

fn project_command(cli: &Cli) -> Result<i32, ProjectError> {
    let cwd = std::env::current_dir().map_err(|error| {
        ProjectError::Io(format!("no se puede leer el directorio actual: {error}"))
    })?;
    let root = env::project_root(&cwd).ok_or_else(|| {
        ProjectError::Usage(format!(
            "no se encontró `Tome.toml` en `{}` ni en sus padres",
            cwd.display()
        ))
    })?;
    let manifest = env::read_manifest(&root).map_err(ProjectError::Io)?;
    match &cli.command {
        Command::Fetch => fetch(cli, &root, &manifest),
        Command::Tree => show_tree(&root, &manifest),
        Command::Build | Command::Run | Command::Test => build_like(cli, &root, &manifest),
        Command::Check => {
            if cli.watch {
                watch_project(cli, &root, &manifest, WatchAction::Check)
            } else {
                check_project(cli, &root, &manifest)
            }
        }
        Command::Watch(watch) => watch_project(cli, &root, &manifest, watch.action),
        Command::Vendor => vendor_project(cli, &root, &manifest),
        Command::Size => sizes(&root, &manifest),
        Command::Add(add) => add_dependency(cli, &root, add),
        Command::Remove(remove) => remove_dependency(cli, &root, &remove.name),
        Command::Update(update) => {
            update_dependencies(cli, &root, &manifest, update.name.as_deref())
        }
        Command::Bindgen(_)
        | Command::New(_)
        | Command::Version
        | Command::Help
        | Command::Lsp
        | Command::Fmt(_)
        | Command::Lint(_)
        | Command::Explain(_)
        | Command::Fix(_)
        | Command::Doc(_)
        | Command::Bench(_)
        | Command::Doctor
        | Command::Completions(_)
        | Command::Man => Ok(0),
    }
}

/// `pengu size`: tamaños reales del programa, medidos con `pengu-layout`.
fn sizes(root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    let program_path = ["main.pengu", "lib.pengu"]
        .iter()
        .map(|name| root.join(name))
        .find(|path| path.is_file())
        .ok_or_else(|| {
            ProjectError::Io(format!(
                "el proyecto `{}` no tiene `main.pengu` ni `lib.pengu`",
                manifest.name
            ))
        })?;
    let source = std::fs::read_to_string(&program_path)
        .map_err(|error| ProjectError::Io(error.to_string()))?;
    let parsed = pengu_syntax::parse_program(pengu_span::FileId::new(0), &source);
    let program = parsed.program.ok_or_else(|| {
        ProjectError::Io("el programa no parsea; no hay tamaños que mostrar".to_owned())
    })?;
    let lowered = pengu_hir::lower_program(&program);
    let checked = pengu_types::check_crate(&lowered.krate);
    if checked
        .diagnostics
        .iter()
        .any(pengu_diag::Diagnostic::is_error)
    {
        for diagnostic in &checked.diagnostics {
            if diagnostic.is_error() {
                eprintln!("{}", diagnostic.render_compact());
            }
        }
        return Ok(1);
    }
    let krate = &lowered.krate;
    let mut rows = Vec::new();
    for def in &krate.defs {
        if def.module != krate.root {
            continue;
        }
        match def.kind {
            pengu_hir::DefKind::Type => {
                if let Some(size) = pengu_layout::layout_of_adt(def.id, &[], krate) {
                    rows.push(format!("tipo {} · {}", def.name, describe(&size)));
                } else if krate
                    .adt(def.id)
                    .is_some_and(|adt| !adt.generics.is_empty())
                {
                    rows.push(format!(
                        "tipo {} · genérico (el tamaño depende de sus argumentos)",
                        def.name
                    ));
                }
            }
            pengu_hir::DefKind::Function => {
                if let Some(size) = footprint(def.id, krate) {
                    rows.push(format!(
                        "fn {} · huella {}",
                        def.name,
                        pengu_layout::format_size(size)
                    ));
                }
            }
            pengu_hir::DefKind::Const | pengu_hir::DefKind::Static => {
                if let Some(signature) = krate.signature(def.id) {
                    if let Some(size) = pengu_layout::typed(&signature.ret, krate)
                        .and_then(|ty| pengu_layout::layout_of(&ty, krate))
                    {
                        rows.push(format!("sigil {} · {}", def.name, describe(&size)));
                    }
                }
            }
            _ => {}
        }
    }
    rows.sort();
    for row in rows {
        println!("{row}");
    }
    Ok(0)
}

fn describe(layout: &pengu_layout::Layout) -> String {
    let mut text = pengu_layout::format_size(layout.size);
    if layout.align > 1 {
        let _ = write!(
            text,
            ", alineación {}",
            pengu_layout::format_size(layout.align)
        );
    }
    text
}

fn footprint(def: pengu_hir::DefId, krate: &pengu_hir::HirCrate) -> Option<usize> {
    pengu_layout::footprint(def, krate)
}

fn fetch(cli: &Cli, root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    let cache = Cache::from_env()?;
    let options = Options {
        offline: cli.offline,
        locked: cli.locked,
        refresh: true,
        force: cli.force,
    };
    let lock = ops::fetch(root, &cache, manifest, options)?;
    if cli.verbose {
        println!(
            "lock: {} paquete(s) en `{}`",
            lock.packages.len(),
            root.join("Tome.lock").display()
        );
    }
    Ok(0)
}

fn show_tree(root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    let lock = ops::verify(root, manifest)?;
    print!("{}", tree::render(manifest, &lock));
    Ok(0)
}

fn build_like(cli: &Cli, root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    use std::io::Write as _;

    let (lock, packages) = ensure_lock(cli, root, manifest)?;
    if cli.verbose {
        println!(
            "lock verificado: {} paquete(s), {} fusionado(s)",
            lock.packages.len(),
            packages.len()
        );
    }
    let doc_root;
    let build_root = if cli.doc && cli.command == Command::Test {
        doc_root = match doc_tests_root(root, manifest, &packages) {
            Ok(path) => path,
            Err(message) => return Err(ProjectError::Io(message)),
        };
        doc_root.as_path()
    } else {
        root
    };
    let report = match cli.command {
        Command::Build => pengu_build::build_report_with_packages(build_root, &packages),
        Command::Run => pengu_build::run_report_with_packages(build_root, &packages),
        _ => pengu_build::test_report_with_packages(build_root, &packages),
    }
    .map_err(|error| ProjectError::Io(format!("no se pudo compilar: {error}")))?;
    if report.cached && cli.verbose {
        eprintln!("sin cambios");
    }
    for diagnostic in &report.diagnostics {
        eprintln!("{}", diagnostic.render_compact());
    }
    if cli.command == Command::Run {
        if let Some(output) = &report.output {
            let _ = std::io::stdout().write_all(&output.stdout);
            let _ = std::io::stdout().flush();
            let _ = std::io::stderr().write_all(&output.stderr);
        }
    } else if cli.command == Command::Test {
        if let Some(output) = &report.output {
            print_human(&output.stdout);
            let _ = std::io::stderr().write_all(&output.stderr);
        }
    } else if !report.success() {
        if let Some(output) = &report.output {
            let _ = std::io::stderr().write_all(&output.stderr);
        }
    }
    if report.success() { Ok(0) } else { Ok(1) }
}

/// `pengu check`: front-end completo, sin Cargo.
fn check_project(cli: &Cli, root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    let (_, packages) = ensure_lock(cli, root, manifest)?;
    let report = pengu_build::check_with_packages(root, &packages);
    for diagnostic in &report.diagnostics {
        eprintln!("{}", diagnostic.render_compact());
    }
    if report.is_clean() {
        println!("check: sin errores");
        Ok(0)
    } else {
        Ok(1)
    }
}

/// Intervalo de sondeo de `--watch`.
const WATCH_INTERVAL: std::time::Duration = std::time::Duration::from_millis(250);

/// `pengu check --watch` / `pengu watch <comando>`: repite al cambiar los fuentes.
fn watch_project(
    cli: &Cli,
    root: &Path,
    manifest: &Manifest,
    action: WatchAction,
) -> Result<i32, ProjectError> {
    let mut current = crate::watch::snapshot(root);
    loop {
        println!("── {} ──", action.name());
        let _ = run_watch_action(cli, root, manifest, action);
        loop {
            std::thread::sleep(WATCH_INTERVAL);
            let next = crate::watch::snapshot(root);
            if crate::watch::changed(&current, &next) {
                current = next;
                break;
            }
        }
    }
}

fn run_watch_action(
    cli: &Cli,
    root: &Path,
    manifest: &Manifest,
    action: WatchAction,
) -> Result<i32, ProjectError> {
    let mut cli = cli.clone();
    cli.watch = false;
    cli.command = match action {
        WatchAction::Check => Command::Check,
        WatchAction::Build => Command::Build,
        WatchAction::Run => Command::Run,
        WatchAction::Test => Command::Test,
    };
    if action == WatchAction::Check {
        check_project(&cli, root, manifest)
    } else {
        build_like(&cli, root, manifest)
    }
}

/// Imprime solo las líneas legibles: `cargo` emite JSON por `--message-format=json`.
fn print_human(bytes: &[u8]) {
    use std::io::Write as _;

    let text = String::from_utf8_lossy(bytes);
    for line in text.lines() {
        if !line.starts_with('{') {
            println!("{line}");
        }
    }
    let _ = std::io::stdout().flush();
}

fn ensure_lock(
    cli: &Cli,
    root: &Path,
    manifest: &Manifest,
) -> Result<(Lockfile, Vec<(String, std::path::PathBuf)>), ProjectError> {
    if manifest.dependencies.is_empty() {
        return Ok((
            Lockfile {
                version: pengu_pkg::lock::LOCK_VERSION,
                packages: Vec::new(),
            },
            Vec::new(),
        ));
    }
    let cache = Cache::from_env()?;
    let options = Options {
        offline: cli.offline,
        locked: cli.locked,
        refresh: false,
        force: false,
    };
    let lock = ops::fetch(root, &cache, manifest, options)?;
    // Si hay vendor, se usa y se verifica: una copia editada a mano es un error.
    if pengu_pkg::vendor::exists(root) {
        pengu_pkg::vendor::verify(root, &lock)?;
    }
    let packages = lock
        .packages
        .iter()
        .map(|package| {
            (
                package.name.clone(),
                ops::package_source_dir(root, &cache, package),
            )
        })
        .collect();
    Ok((lock, packages))
}

fn add_dependency(cli: &Cli, root: &Path, add: &args::AddArgs) -> Result<i32, ProjectError> {
    let cache = Cache::from_env()?;
    let source = add
        .git
        .clone()
        .or_else(|| add.path.clone())
        .ok_or_else(|| ProjectError::Usage("`pengu add` necesita una fuente".to_owned()))?;
    let (spec, warning) = if let Some(url) = &add.git {
        let requested = if let Some(tag) = &add.tag {
            Requested::Tag(tag)
        } else if let Some(branch) = &add.branch {
            Requested::Branch(branch)
        } else if let Some(rev) = &add.rev {
            Requested::Rev(rev)
        } else {
            Requested::Auto
        };
        let shell = ShellGit;
        let fetcher = Fetcher::new(&shell, &cache, cli.offline);
        spec::git_spec(&fetcher, url, requested)?
    } else {
        (
            spec::path_spec(add.path.as_deref().unwrap_or_default()),
            None,
        )
    };
    if let Some(warning) = &warning {
        eprintln!("aviso: {warning}");
    }
    let name = match &add.name {
        Some(name) => name.clone(),
        None => infer_package_name(cli, root, &cache, add, &spec)
            .or_else(|| spec::infer_name(&source))
            .ok_or_else(|| {
                ProjectError::Usage(format!("no se puede derivar un nombre de `{source}`"))
            })?,
    };
    let options = Options {
        offline: cli.offline,
        locked: false,
        refresh: true,
        force: false,
    };
    let lock = ops::add(root, &cache, options, &name, &spec.text)?;
    println!("añadido {name} = {}", spec.text);
    if cli.verbose {
        println!("lock: {} paquete(s)", lock.packages.len());
    }
    Ok(0)
}

fn remove_dependency(cli: &Cli, root: &Path, name: &str) -> Result<i32, ProjectError> {
    let cache = Cache::from_env()?;
    let options = Options {
        offline: cli.offline,
        locked: false,
        refresh: true,
        force: false,
    };
    let lock = ops::remove(root, &cache, options, name)?;
    println!("quitado {name}");
    if cli.verbose {
        println!("lock: {} paquete(s)", lock.packages.len());
    }
    Ok(0)
}

fn update_dependencies(
    cli: &Cli,
    root: &Path,
    manifest: &Manifest,
    only: Option<&str>,
) -> Result<i32, ProjectError> {
    let cache = Cache::from_env()?;
    let options = Options {
        offline: cli.offline,
        locked: false,
        refresh: true,
        force: false,
    };
    let before = Lockfile::read(root)?
        .map(|lock| lock.packages)
        .unwrap_or_default();
    let lock = ops::update(root, &cache, manifest, options, only)?;
    let mut moved = 0_usize;
    for package in &lock.packages {
        let previous = before.iter().find(|old| old.name == package.name);
        let changed = previous.is_none_or(|old| old.commit != package.commit);
        if changed {
            moved += 1;
            if cli.verbose {
                let short = package.commit.get(..8).unwrap_or(&package.commit);
                println!("{} -> {}", package.name, short);
            }
        }
    }
    println!("actualizados {moved} paquete(s)");
    Ok(0)
}

/// Nombre real del paquete cuando se puede leer su `Tome.toml`.
fn infer_package_name(
    cli: &Cli,
    root: &Path,
    cache: &Cache,
    add: &args::AddArgs,
    spec: &spec::Spec,
) -> Option<String> {
    if let Some(path) = &add.path {
        let dir = root.join(path);
        return ops::package_name(&dir);
    }
    let url = add.git.as_deref()?;
    let reference = spec.reference.clone()?;
    let source = pengu_pkg::source::Source::git(url, reference).ok()?;
    let shell = ShellGit;
    let fetcher = Fetcher::new(&shell, cache, cli.offline);
    let resolved = fetcher.prepare(&source).ok()?;
    ops::package_name(&resolved.path)
}

/// `pengu vendor`: copia las dependencias del lock a `vendor/` (o solo las verifica).
fn vendor_project(cli: &Cli, root: &Path, manifest: &Manifest) -> Result<i32, ProjectError> {
    let cache = Cache::from_env()?;
    let (lock, _) = ensure_lock(cli, root, manifest)?;
    if cli.check {
        pengu_pkg::vendor::verify(root, &lock)?;
        if cli.verbose {
            eprintln!("vendor: {} paquete(s) verificados", lock.packages.len());
        }
        return Ok(0);
    }
    let vendored = pengu_pkg::vendor::vendor(root, &cache, &lock)?;
    if cli.verbose {
        println!("vendor: {vendored:?}");
    } else {
        println!("vendor: {} paquete(s)", vendored.len());
    }
    Ok(0)
}

/// Crea un proyecto nuevo desde un template embebido.
fn new_project(new: &crate::args::NewArgs) -> Result<i32, ProjectError> {
    use crate::templates;

    if new.template.as_deref() == Some("list") {
        print!("{}", templates::names());
        return Ok(0);
    }
    if !is_project_name(&new.name) {
        return Err(ProjectError::Usage(format!(
            "`{}` no es un nombre de proyecto válido (letras, dígitos, `_` y `-`, sin empezar por dígito)",
            new.name
        )));
    }
    let target = std::env::current_dir()
        .map_err(|error| {
            ProjectError::Io(format!("no se puede leer el directorio actual: {error}"))
        })?
        .join(&new.name);
    if target.exists() {
        return Err(ProjectError::Usage(format!(
            "`{}` ya existe",
            target.display()
        )));
    }
    let template = templates::find(new.template.as_deref().unwrap_or("bin")).ok_or_else(|| {
        ProjectError::Usage(format!(
            "template desconocido `{}`; usa `pengu new x --template list`",
            new.template.as_deref().unwrap_or("bin")
        ))
    })?;
    for (path, content) in templates::render(template, &new.name) {
        let full = target.join(&path);
        if let Some(parent) = full.parent() {
            std::fs::create_dir_all(parent).map_err(|error| {
                ProjectError::Io(format!("no se puede crear `{}`: {error}", parent.display()))
            })?;
        }
        std::fs::write(&full, content).map_err(|error| {
            ProjectError::Io(format!(
                "no se puede escribir `{}`: {error}",
                full.display()
            ))
        })?;
    }
    println!("creado {} ({})", target.display(), template.name);

    let manifest = env::read_manifest(&target).map_err(ProjectError::Io)?;
    if !manifest.dependencies.is_empty() {
        let cache = Cache::from_env()?;
        let options = Options {
            offline: false,
            locked: false,
            refresh: true,
            force: false,
        };
        ops::fetch(&target, &cache, &manifest, options)?;
        println!(
            "lock: {} paquete(s)",
            Lockfile::read(&target)?.map_or(0, |lock| lock.packages.len())
        );
    }
    println!("siguiente: cd {} && pengu run", new.name);
    Ok(0)
}

fn is_project_name(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with(|ch: char| ch.is_ascii_digit())
        && name
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-')
}

/// `pengu fmt [archivos…]` / `pengu fmt --check`.
fn format_files(args: &FmtArgs, check: bool) -> i32 {
    let files = match target_files(&args.files) {
        Ok(files) => files,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let mut failed = false;
    for path in files {
        let source = match std::fs::read_to_string(&path) {
            Ok(source) => source,
            Err(error) => {
                eprintln!("error: no se puede leer {}: {error}", path.display());
                failed = true;
                continue;
            }
        };
        match pengu_fmt::format_source(&source) {
            Ok(formatted) if formatted == source => {
                if cli_verbose() {
                    println!("sin cambios {}", path.display());
                }
            }
            Ok(formatted) => {
                if check {
                    failed = true;
                    match pengu_fmt::differences(&source) {
                        Ok(differences) => {
                            for difference in differences {
                                println!(
                                    "{}:{}: {}",
                                    path.display(),
                                    difference.line,
                                    difference.formatted
                                );
                            }
                        }
                        Err(error) => eprintln!("{}: {error}", path.display()),
                    }
                } else if let Err(error) = std::fs::write(&path, formatted) {
                    eprintln!("error: no se puede escribir {}: {error}", path.display());
                    failed = true;
                } else {
                    println!("formateado {}", path.display());
                }
            }
            Err(error) => {
                eprintln!("{}: {error}", path.display());
                failed = true;
            }
        }
    }
    i32::from(failed)
}

fn cli_verbose() -> bool {
    std::env::var_os("PENGU_VERBOSE").is_some()
}

/// `pengu lint [archivos…]`.
fn lint_files(args: &LintArgs) -> i32 {
    if args.list {
        for info in pengu_lint::lints() {
            println!("{}  {} — {}", info.code, info.name, info.description);
        }
        return 0;
    }
    let mut config = pengu_lint::LintConfig::new();
    for (keys, level) in [
        (&args.allow, pengu_lint::Level::Allow),
        (&args.warn, pengu_lint::Level::Warn),
        (&args.deny, pengu_lint::Level::Deny),
    ] {
        for key in keys {
            if !config.set(key, level) {
                eprintln!("error: no existe el lint `{key}` (prueba `pengu lint --list`)");
                return 2;
            }
        }
    }
    let files = match target_files(&args.files) {
        Ok(files) => files,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let mut errors = false;
    for path in files {
        let source = match std::fs::read_to_string(&path) {
            Ok(source) => source,
            Err(error) => {
                eprintln!("error: no se puede leer {}: {error}", path.display());
                return 2;
            }
        };
        let report = pengu_lint::lint_with(&source, pengu_span::FileId::new(0), &config, args.std);
        errors |= report.has_errors();
        for diagnostic in &report.diagnostics {
            let (line, column) = line_column(&source, diagnostic.primary.start);
            let severity = match diagnostic.severity {
                pengu_diag::Severity::Error => "error",
                _ => "aviso",
            };
            println!(
                "{}:{line}:{column}: {severity} {}: {}",
                path.display(),
                diagnostic.code,
                diagnostic.message
            );
            if let Some(help) = &diagnostic.help {
                println!("    ayuda: {help}");
            }
        }
    }
    i32::from(errors)
}

/// `pengu explain <código>`.
fn explain_code(code: &str) -> i32 {
    let spec = include_str!("../../../docs/LANGUAGE.md");
    let needle = code.trim().to_uppercase();
    let Some(position) = spec.find(&needle) else {
        eprintln!("error: `{code}` no aparece en docs/LANGUAGE.md");
        return 1;
    };
    let line_start = spec[..position].rfind('\n').map_or(0, |index| index + 1);
    let line_end = spec[position..]
        .find('\n')
        .map_or(spec.len(), |index| position + index);
    let line = spec[line_start..line_end].trim();
    if line.starts_with('|') {
        let cells: Vec<&str> = line.trim_matches('|').split('|').map(str::trim).collect();
        if cells.len() >= 2 {
            println!("{} — {}", cells[0].trim_matches('`'), cells[1]);
            return 0;
        }
    }
    let start = spec[..line_start]
        .rfind("\n\n")
        .map_or(0, |index| index + 2);
    let end = spec[line_end..]
        .find("\n\n")
        .map_or(spec.len(), |index| line_end + index);
    println!("{}", spec[start..end].trim());
    0
}

fn line_column(source: &str, offset: u32) -> (usize, usize) {
    let mut line = 1usize;
    let mut column = 1usize;
    for (index, character) in source.char_indices() {
        if index >= offset as usize {
            break;
        }
        if character == '\n' {
            line += 1;
            column = 1;
        } else {
            column += 1;
        }
    }
    (line, column)
}

fn target_files(explicit: &[String]) -> Result<Vec<std::path::PathBuf>, String> {
    if !explicit.is_empty() {
        let mut files = Vec::new();
        for entry in explicit {
            let path = std::path::PathBuf::from(entry);
            if path.is_dir() {
                let mut found: Vec<_> = std::fs::read_dir(&path)
                    .map_err(|error| format!("no se puede leer {}: {error}", path.display()))?
                    .filter_map(Result::ok)
                    .map(|entry| entry.path())
                    .filter(|path| {
                        path.extension()
                            .is_some_and(|extension| extension == "pengu")
                            || path
                                .file_name()
                                .is_some_and(|name| name.to_string_lossy().ends_with(".d.pengu"))
                    })
                    .collect();
                found.sort();
                if found.is_empty() {
                    return Err(format!("{} no contiene archivos `.pengu`", path.display()));
                }
                files.extend(found);
            } else {
                files.push(path);
            }
        }
        return Ok(files);
    }
    let cwd = std::env::current_dir().map_err(|error| error.to_string())?;
    let root = env::project_root(&cwd)
        .ok_or_else(|| "no se encontró `Tome.toml` ni `main.pengu`/`lib.pengu`".to_owned())?;
    let program = ["main.pengu", "lib.pengu"]
        .iter()
        .map(|name| root.join(name))
        .find(|path| path.is_file())
        .ok_or_else(|| format!("{} no tiene `main.pengu` ni `lib.pengu`", root.display()))?;
    Ok(vec![program])
}

/// Crea un proyecto temporal con los doc tests anexados al programa.
fn doc_tests_root(
    root: &Path,
    manifest: &Manifest,
    packages: &[(String, PathBuf)],
) -> Result<PathBuf, String> {
    let program = ["main.pengu", "lib.pengu"]
        .iter()
        .map(|name| root.join(name))
        .find(|path| path.is_file())
        .ok_or_else(|| "el proyecto no tiene `main.pengu` ni `lib.pengu`".to_owned())?;
    let source = std::fs::read_to_string(&program)
        .map_err(|error| format!("no se puede leer {}: {error}", program.display()))?;
    let blocks = doc_test_blocks(&source);
    let dir = root.join("target/pengu/doc-tests");
    std::fs::create_dir_all(&dir).map_err(|error| error.to_string())?;
    let mut augmented = source;
    if !blocks.is_empty() {
        augmented.push('\n');
    }
    for block in &blocks {
        augmented.push_str(block);
    }
    std::fs::write(dir.join("main.pengu"), augmented).map_err(|error| error.to_string())?;
    let manifest = format!(
        "[tome]\nname = \"doc_tests\"\nversion = \"0.0.0\"\npengu = \"{}\"\nedition = \"{}\"\n\n[[bin]]\nname = \"doc_tests\"\npath = \"main.pengu\"\n",
        manifest.pengu, manifest.edition
    );
    std::fs::write(dir.join("Tome.toml"), manifest).map_err(|error| error.to_string())?;
    let _ = packages;
    Ok(dir)
}

/// Elemento de nivel superior con su documentación.
struct DocItem<'a> {
    docs: Vec<&'a str>,
    signature: &'a str,
}

/// Recoge los pares (documentación `---`, línea del item).
fn doc_items(source: &str) -> Vec<DocItem<'_>> {
    let mut items = Vec::new();
    let mut pending: Vec<&str> = Vec::new();
    for line in source.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("---") {
            pending.push(rest.strip_prefix(' ').unwrap_or(rest));
            continue;
        }
        if pending.is_empty() {
            continue;
        }
        if line.trim().is_empty() || line.starts_with(' ') || line.starts_with('\t') {
            pending.clear();
            continue;
        }
        items.push(DocItem {
            docs: std::mem::take(&mut pending),
            signature: line,
        });
    }
    items
}

/// Extrae los bloques de código `pengu` de los comentarios `---` como tests.
fn doc_test_blocks(source: &str) -> Vec<String> {
    let mut blocks = Vec::new();
    for item in doc_items(source) {
        let mut code: Option<Vec<&str>> = None;
        for line in item.docs {
            let trimmed = line.trim_start();
            if let Some(info) = trimmed.strip_prefix("```") {
                if code.is_none() && info.trim() == "pengu" {
                    code = Some(Vec::new());
                    continue;
                }
                if let Some(lines) = code.take() {
                    blocks.push(render_doc_test(blocks.len() + 1, &lines));
                }
                continue;
            }
            if let Some(lines) = code.as_mut() {
                lines.push(line);
            }
        }
    }
    blocks
}

fn render_doc_test(number: usize, lines: &[&str]) -> String {
    let mut text = format!("@@test\ndoc_test_{number} = () -> Unit\n");
    for line in lines {
        text.push_str("    ");
        text.push_str(line);
        text.push('\n');
    }
    text.push('\n');
    text
}

/// `pengu fix`: aplica solo correcciones que no cambian la semántica.
fn fix_project(args: &args::FixArgs) -> i32 {
    let files = match target_files(&args.files) {
        Ok(files) => files,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let mut changed = 0usize;
    for path in files {
        let source = match std::fs::read_to_string(&path) {
            Ok(source) => source,
            Err(error) => {
                eprintln!("error: no se puede leer {}: {error}", path.display());
                return 2;
            }
        };
        let report = pengu_lint::lint(
            &source,
            pengu_span::FileId::new(0),
            &pengu_lint::LintConfig::new(),
        );
        let mut lines: Vec<String> = source.lines().map(str::to_owned).collect();
        let mut remove = std::collections::BTreeSet::new();
        let mut replace: Vec<(usize, String)> = Vec::new();
        for diagnostic in &report.diagnostics {
            let (line, _) = line_column(&source, diagnostic.primary.start);
            match diagnostic.code {
                "PGS-W2001" | "PGS-W6001" => {
                    remove.insert(line);
                }
                "PGS-W6002"
                    if lines
                        .get(line - 1)
                        .is_some_and(|text| text.contains("while true do")) =>
                {
                    if let Some(text) = lines.get(line - 1) {
                        replace.push((line, text.replacen("while true do", "loop", 1)));
                    }
                }
                _ => {}
            }
        }
        if remove.is_empty() && replace.is_empty() {
            continue;
        }
        for (line, text) in &replace {
            if *line >= 1 && *line <= lines.len() {
                lines[*line - 1].clone_from(text);
                changed += 1;
                println!(
                    "{}:{line}: corregido ({})",
                    path.display(),
                    if args.dry_run { "simulado" } else { "aplicado" }
                );
            }
        }
        for line in remove.iter().rev() {
            if *line >= 1 && *line <= lines.len() {
                lines.remove(*line - 1);
                changed += 1;
                println!(
                    "{}:{line}: corregido ({})",
                    path.display(),
                    if args.dry_run { "simulado" } else { "aplicado" }
                );
            }
        }
        let mut fixed = lines.join("\n");
        fixed.push('\n');
        if args.dry_run {
            print!("{fixed}");
        } else {
            match pengu_fmt::format_source(&fixed) {
                Ok(formatted) => {
                    if let Err(error) = std::fs::write(&path, formatted) {
                        eprintln!("error: no se puede escribir {}: {error}", path.display());
                        return 2;
                    }
                }
                Err(error) => {
                    eprintln!("{}: {error}", path.display());
                    return 2;
                }
            }
        }
    }
    if changed == 0 {
        println!("sin correcciones seguras");
    }
    i32::from(changed > 0 && args.dry_run)
}

/// `pengu doc`: genera Markdown a partir de los comentarios `---` y `--!`.
fn generate_docs(args: &args::DocArgs) -> i32 {
    let cwd = match std::env::current_dir() {
        Ok(cwd) => cwd,
        Err(error) => {
            eprintln!("error: {error}");
            return 2;
        }
    };
    let Some(root) = env::project_root(&cwd) else {
        eprintln!("error: no se encontró `Tome.toml`");
        return 2;
    };
    let manifest = match env::read_manifest(&root) {
        Ok(manifest) => manifest,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let files = match target_files(&args.files) {
        Ok(files) => files,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let Some(path) = files.first() else {
        eprintln!("error: no hay programa");
        return 2;
    };
    let source = match std::fs::read_to_string(path) {
        Ok(source) => source,
        Err(error) => {
            eprintln!("error: no se puede leer {}: {error}", path.display());
            return 2;
        }
    };
    let markdown = render_markdown(&manifest, &source);
    let out_dir = root.join("target/pengu/doc");
    if let Err(error) = std::fs::create_dir_all(&out_dir) {
        eprintln!("error: {error}");
        return 2;
    }
    let out = out_dir.join(format!("{}.md", manifest.name));
    if let Err(error) = std::fs::write(&out, &markdown) {
        eprintln!("error: no se puede escribir {}: {error}", out.display());
        return 2;
    }
    println!("{}", out.display());
    if args.open {
        let _ = std::process::Command::new("xdg-open").arg(&out).spawn();
    }
    0
}

fn render_markdown(manifest: &Manifest, source: &str) -> String {
    let mut out = String::new();
    let _ = writeln!(out, "# {} v{}\n", manifest.name, manifest.version);
    let mut module_docs: Vec<&str> = Vec::new();
    for line in source.lines() {
        let trimmed = line.trim_start();
        let Some(rest) = trimmed.strip_prefix("--!") else {
            if line.trim().is_empty() || trimmed.starts_with("--") {
                continue;
            }
            break;
        };
        module_docs.push(rest.strip_prefix(' ').unwrap_or(rest));
    }
    if !module_docs.is_empty() {
        for doc in &module_docs {
            let _ = writeln!(out, "{doc}");
        }
        out.push('\n');
    }
    for item in doc_items(source) {
        let name = item.signature.trim();
        let _ = writeln!(out, "## `{name}`\n");
        for doc in &item.docs {
            let _ = writeln!(out, "{doc}");
        }
        out.push('\n');
    }
    out
}

/// `pengu bench`: mide las etapas del compilador.
/// `pengu bindgen`: genera un `.d.pengu` desde una cabecera C.
fn bindgen_header(args: &args::BindgenArgs, verbose: bool) -> i32 {
    let header = std::path::Path::new(&args.header);
    let options = pengu_bindgen::Options {
        include_dirs: args.include_dirs.clone(),
        defines: args.defines.clone(),
        allowlist: args.allowlist.clone(),
        blocklist: args.blocklist.clone(),
    };
    let generated = match pengu_bindgen::generate(header, &options) {
        Ok(generated) => generated,
        Err(error) => {
            eprintln!("{error}");
            return 1;
        }
    };
    if verbose {
        for detail in &generated.report.details {
            eprintln!("omitido: {detail}");
        }
    }
    let output = args
        .output
        .clone()
        .map_or_else(|| default_output(header), std::path::PathBuf::from);
    if args.check {
        let current = std::fs::read_to_string(&output).unwrap_or_default();
        if current == generated.source {
            println!("bindgen: {}", output.display());
            return 0;
        }
        eprintln!(
            "error: `{}` no coincide con la cabecera; ejecuta `pengu bindgen {}`",
            output.display(),
            args.header
        );
        return 1;
    }
    if let Err(error) = write_atomic(&output, &generated.source) {
        eprintln!("error: no se pudo escribir `{}`: {error}", output.display());
        return 1;
    }
    let report = &generated.report;
    println!(
        "generado {}: {} función(es), {} estructura(s), {} constante(s), {} omitido(s)",
        output.display(),
        report.functions,
        report.records,
        report.constants,
        report.omitted_total()
    );
    0
}

/// `<cabecera>.d.pengu` junto al archivo de entrada.
fn default_output(header: &std::path::Path) -> std::path::PathBuf {
    let stem = header.file_stem().map_or_else(
        || "declaracion".to_owned(),
        |stem| stem.to_string_lossy().into_owned(),
    );
    header.with_file_name(format!("{stem}.d.pengu"))
}

fn write_atomic(path: &std::path::Path, contents: &str) -> std::io::Result<()> {
    let mut temporary = path.as_os_str().to_owned();
    temporary.push(".tmp");
    std::fs::write(&temporary, contents)?;
    std::fs::rename(&temporary, path)
}

fn benchmark(args: &args::BenchArgs) -> i32 {
    let files = match target_files(&[]) {
        Ok(files) => files,
        Err(message) => {
            eprintln!("error: {message}");
            return 2;
        }
    };
    let Some(path) = files.first() else {
        eprintln!("error: no hay programa");
        return 2;
    };
    let source = match std::fs::read_to_string(path) {
        Ok(source) => source,
        Err(error) => {
            eprintln!("error: no se puede leer {}: {error}", path.display());
            return 2;
        }
    };
    let mut stages = Stages::default();
    for _ in 0..args.iterations {
        stages.measure(&source);
    }
    let lines = source.lines().count();
    let tokens = pengu_syntax::lex(pengu_span::FileId::new(0), &source)
        .tokens
        .len();
    println!("programa: {lines} líneas, {tokens} tokens");
    println!("etapas (mínimo de {} repeticiones):", args.iterations);
    for (name, duration) in stages.report() {
        println!("  {name:<10} {duration:>8.3} ms");
    }
    0
}

#[derive(Default)]
struct Stages {
    lex: Option<std::time::Duration>,
    parse: Option<std::time::Duration>,
    lower: Option<std::time::Duration>,
    check: Option<std::time::Duration>,
    lir: Option<std::time::Duration>,
    codegen: Option<std::time::Duration>,
    total: Option<std::time::Duration>,
}

impl Stages {
    fn measure(&mut self, source: &str) {
        let start = std::time::Instant::now();
        let lex_start = std::time::Instant::now();
        let _ = pengu_syntax::lex(pengu_span::FileId::new(0), source);
        Self::keep(&mut self.lex, lex_start.elapsed());
        let parse_start = std::time::Instant::now();
        let parsed = pengu_syntax::parse_program(pengu_span::FileId::new(0), source);
        Self::keep(&mut self.parse, parse_start.elapsed());
        let Some(program) = parsed.program else {
            return;
        };
        let lower_start = std::time::Instant::now();
        let lowered = pengu_hir::lower_program(&program);
        Self::keep(&mut self.lower, lower_start.elapsed());
        let check_start = std::time::Instant::now();
        let checked = pengu_types::check_crate(&lowered.krate);
        Self::keep(&mut self.check, check_start.elapsed());
        let lir_start = std::time::Instant::now();
        let lir = pengu_lir::lower_crate(&lowered.krate, &checked);
        Self::keep(&mut self.lir, lir_start.elapsed());
        let codegen_start = std::time::Instant::now();
        let _ = pengu_codegen::generate(&lowered.krate, &lir);
        Self::keep(&mut self.codegen, codegen_start.elapsed());
        Self::keep(&mut self.total, start.elapsed());
    }

    fn keep(slot: &mut Option<std::time::Duration>, duration: std::time::Duration) {
        if slot.is_none_or(|current| duration < current) {
            *slot = Some(duration);
        }
    }

    fn report(&self) -> Vec<(&'static str, f64)> {
        [
            ("lex", self.lex),
            ("parse", self.parse),
            ("lower", self.lower),
            ("check", self.check),
            ("lir", self.lir),
            ("codegen", self.codegen),
            ("total", self.total),
        ]
        .into_iter()
        .map(|(name, duration)| (name, duration.unwrap_or_default().as_secs_f64() * 1_000.0))
        .collect()
    }
}
