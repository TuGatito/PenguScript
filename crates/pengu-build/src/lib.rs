#![forbid(unsafe_code)]
//! Driver de build/run/test del backend Rust (B5–B7).

use std::path::{Path, PathBuf};
use std::process::Command;

use pengu_codegen::{SourceMap, generate};
use pengu_diag::Diagnostic;
use pengu_hir::{HirCrate, lower_program_with_declarations};
use pengu_lir::lower_crate;
use pengu_span::{FileId, Span};
use pengu_syntax::{parse_declaration_file, parse_program};
use pengu_types::{CheckResult, check_crate};

mod cache;
mod check;
mod remap;

pub use cache::Cache as BuildCache;
pub use check::{CheckReport, check, check_with_packages};
pub use remap::remap as remap_rustc_diagnostics;

/// Resultado de compilar un proyecto a Rust.
#[derive(Clone, Debug, Default)]
pub struct BuildResult {
    /// Fuente Rust.
    pub rust: String,
    /// Manifiesto Cargo equivalente.
    pub cargo_toml: String,
    /// `build.rs` con `[link]`.
    pub build_rs: String,
    /// Sourcemap.
    pub sourcemap: SourceMap,
    /// `true` si el proyecto produce un binario.
    pub is_bin: bool,
    /// Nombre del binario.
    pub bin_name: String,
    /// Nombre del paquete Cargo.
    pub package_name: String,
    /// Diagnósticos.
    pub diagnostics: Vec<Diagnostic>,
}

impl BuildResult {
    /// `true` si no hay errores.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Resultado del front-end de un proyecto: todo lo que se sabe antes del LIR.
///
/// `build` y `check` comparten esta función para no divergir: la única
/// diferencia es que `build` sigue con LIR y codegen cuando el análisis está
/// limpio.
pub(crate) struct Analysis {
    pub cargo_toml: String,
    pub build_rs: String,
    pub package_name: String,
    pub bin_name: String,
    pub is_bin: bool,
    pub diagnostics: Vec<Diagnostic>,
    pub program: Option<pengu_syntax::ast::Program>,
    pub krate: Option<HirCrate>,
    pub types: Option<CheckResult>,
}

impl Analysis {
    fn is_clean(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
    }
}

/// Ejecuta sintaxis → HIR → tipos → ownership, parando en la primera etapa con errores.
pub(crate) fn analyze_with_packages(root: &Path, packages: &[(String, PathBuf)]) -> Analysis {
    let mut analysis = Analysis {
        cargo_toml: String::new(),
        build_rs: String::new(),
        package_name: String::new(),
        bin_name: String::new(),
        is_bin: false,
        diagnostics: Vec::new(),
        program: None,
        krate: None,
        types: None,
    };
    let project = pengu_project::load(root);
    analysis.diagnostics.extend(project.diagnostics.clone());
    let Some(manifest) = project.manifest.as_ref() else {
        return analysis;
    };
    // Las dependencias Pengu se compilan dentro de esta misma crate: no se declaran como
    // dependencias Cargo (si no, Cargo intentaría construir crates Rust que no existen).
    let mut cargo_manifest = manifest.clone();
    cargo_manifest.dependencies.clear();
    analysis.cargo_toml = cargo_manifest.to_cargo_toml_with_base(root);
    analysis.build_rs = manifest.build_rs();
    analysis.package_name.clone_from(&manifest.name);

    let source_path = root.join("main.pengu");
    let is_bin = source_path.is_file();
    analysis.is_bin = is_bin;
    analysis.bin_name = manifest
        .bins
        .first()
        .cloned()
        .unwrap_or_else(|| manifest.name.clone());
    let source_path = if is_bin {
        source_path
    } else {
        root.join("lib.pengu")
    };
    let Ok(source) = std::fs::read_to_string(&source_path) else {
        analysis.diagnostics.push(Diagnostic::error(
            "PGS-E2002",
            "no se encuentra `main.pengu` o `lib.pengu`",
            Span::new(FileId::new(0), 0, 0),
        ));
        return analysis;
    };

    let parsed = parse_program(FileId::new(0), &source);
    analysis.diagnostics.extend(parsed.diagnostics.clone());
    if !analysis.is_clean() {
        return analysis;
    }
    let Some(program) = parsed.program else {
        return analysis;
    };
    let program = match merge_packages(program, packages, &mut analysis.diagnostics) {
        Some(program) => program,
        None => return analysis,
    };
    analysis.program = Some(program.clone());
    let declarations = load_declarations(root, manifest, &mut analysis.diagnostics);
    if !analysis.is_clean() {
        return analysis;
    }
    let lowered = lower_program_with_declarations(&program, &declarations);
    analysis.diagnostics.extend(lowered.diagnostics.clone());
    if !analysis.is_clean() {
        return analysis;
    }
    let types = check_crate(&lowered.krate);
    analysis.diagnostics.extend(types.diagnostics.clone());
    if !types.is_clean() {
        return analysis;
    }
    let ownership = pengu_check::check_ownership_with(&lowered.krate, &types);
    analysis.diagnostics.extend(ownership.diagnostics);
    if !analysis.is_clean() {
        return analysis;
    }
    analysis.krate = Some(lowered.krate);
    analysis.types = Some(types);
    analysis
}

/// Primer `FileId` reservado a los archivos `.d.pengu` de `[declarations]`.
const DECLARATION_FILE_BASE: u32 = 0x3E00_0000;

/// Carga y valida las declaraciones `.d.pengu` del manifiesto.
fn load_declarations(
    root: &Path,
    manifest: &pengu_project::Manifest,
    diagnostics: &mut Vec<Diagnostic>,
) -> Vec<(String, pengu_syntax::ast::DeclarationFile)> {
    let mut declarations = Vec::new();
    for (index, declaration) in manifest.declarations.iter().enumerate() {
        let path = root.join(&declaration.path);
        let Ok(source) = std::fs::read_to_string(&path) else {
            diagnostics.push(Diagnostic::error(
                "PGS-E2003",
                format!(
                    "no se encuentra la declaración `{}` en `{}`",
                    declaration.name,
                    declaration.path.display()
                ),
                Span::new(FileId::new(0), 0, 0),
            ));
            continue;
        };
        let file_id = FileId::new(DECLARATION_FILE_BASE + u32::try_from(index).unwrap_or(0));
        let parsed = parse_declaration_file(file_id, &source);
        diagnostics.extend(parsed.diagnostics);
        let Some(file) = parsed.file else {
            continue;
        };
        if matches!(file.abi.as_str(), "C" | "system") && manifest.links.is_empty() {
            diagnostics.push(Diagnostic::error(
                "PGS-E2023",
                format!(
                    "la declaración `{}` usa `abi \"C\"`; añade la librería a `[link]` de `Tome.toml`",
                    declaration.name
                ),
                Span::new(file_id, 0, 1),
            ));
        }
        declarations.push((declaration.name.clone(), file));
    }
    declarations
}

/// Compila `root/main.pengu` o `root/lib.pengu` sin invocar Cargo.
#[must_use]
pub fn compile(root: &Path) -> BuildResult {
    compile_with_packages(root, &[])
}

/// Compila fusionando paquetes como módulos del mismo programa.
///
/// Cada entrada de `packages` es `(nombre del paquete, directorio)`; se lee su
/// `lib.pengu` (o `main.pengu` si no hay librería) y se envuelve en un `scroll` con el
/// nombre del paquete, de modo que el código raíz puede importarlo con
/// `summon <paquete>::<item>`. Las dependencias se compilan en una sola crate, así que
/// no hace falta que sean crates Rust.
///
/// # Panics
/// No entra en pánico; los errores de lectura se reportan como diagnósticos `PGS-E2003`.
#[must_use]
pub fn compile_with_packages(root: &Path, packages: &[(String, PathBuf)]) -> BuildResult {
    let analysis = analyze_with_packages(root, packages);
    let mut result = BuildResult {
        cargo_toml: analysis.cargo_toml,
        build_rs: analysis.build_rs,
        package_name: analysis.package_name,
        bin_name: analysis.bin_name,
        is_bin: analysis.is_bin,
        diagnostics: analysis.diagnostics,
        ..BuildResult::default()
    };
    if !result.is_clean() {
        return result;
    }
    let (Some(krate), Some(types)) = (analysis.krate.as_ref(), analysis.types.as_ref()) else {
        return result;
    };
    let lir = lower_crate(krate, types);
    result.diagnostics.extend(lir.diagnostics.clone());
    if !result.is_clean() {
        return result;
    }
    let generated = generate(krate, &lir);
    result.diagnostics.extend(generated.diagnostics);
    result.rust = generated.source;
    result.sourcemap = generated.sourcemap;
    result
}

/// Envuelve el paquete como `scroll <nombre>` y lo antepone al programa raíz.
fn merge_packages(
    program: pengu_syntax::ast::Program,
    packages: &[(String, PathBuf)],
    diagnostics: &mut Vec<Diagnostic>,
) -> Option<pengu_syntax::ast::Program> {
    let mut items = Vec::new();
    for (index, (name, dir)) in packages.iter().enumerate() {
        let module = package_module_name(name);
        let file = FileId::new(u32::MAX - 1 - index as u32);
        let source_path = if dir.join("lib.pengu").is_file() {
            dir.join("lib.pengu")
        } else {
            dir.join("main.pengu")
        };
        let Ok(source) = std::fs::read_to_string(&source_path) else {
            diagnostics.push(Diagnostic::error(
                "PGS-E2003",
                format!(
                    "no se encuentra la fuente del paquete `{name}` en `{}`",
                    source_path.display()
                ),
                Span::empty(FileId::new(0), 0),
            ));
            return None;
        };
        let mut wrapped = String::new();
        wrapped.push_str("scroll ");
        wrapped.push_str(&module);
        wrapped.push('\n');
        for line in source.lines() {
            if line.is_empty() {
                wrapped.push('\n');
            } else {
                wrapped.push_str("    ");
                wrapped.push_str(line);
                wrapped.push('\n');
            }
        }
        let parsed = parse_program(file, &wrapped);
        diagnostics.extend(parsed.diagnostics);
        if diagnostics.iter().any(Diagnostic::is_error) {
            return None;
        }
        let package_program = parsed.program?;
        items.extend(package_program.items);
    }
    items.extend(program.items);
    Some(pengu_syntax::ast::Program {
        items,
        span: program.span,
    })
}

/// Convierte el nombre de un paquete en un nombre de módulo válido.
fn package_module_name(name: &str) -> String {
    let mut module = String::with_capacity(name.len());
    for (index, ch) in name.chars().enumerate() {
        if ch.is_ascii_alphanumeric() || ch == '_' {
            if index == 0 && ch.is_ascii_digit() {
                module.push('_');
            }
            module.push(ch);
        } else {
            module.push('_');
        }
    }
    module
}

/// Escribe `target/pengu/` con Rust, Cargo.toml, build.rs y sourcemap.
///
/// Solo toca los archivos cuyo contenido cambió: reescribirlos siempre
/// invalidaría el fingerprint de Cargo y forzaría una recompilación completa.
pub fn emit(root: &Path, result: &BuildResult) -> std::io::Result<PathBuf> {
    let out = root.join("target").join("pengu");
    std::fs::create_dir_all(out.join("src"))?;
    let source_name = if result.is_bin { "main.rs" } else { "lib.rs" };
    write_if_changed(&out.join("src").join(source_name), &result.rust)?;
    write_if_changed(&out.join("Cargo.toml"), &result.cargo_toml)?;
    write_if_changed(&out.join("build.rs"), &result.build_rs)?;
    write_if_changed(&out.join("sourcemap.json"), &result.sourcemap.to_json())?;
    Ok(out)
}

fn write_if_changed(path: &Path, contents: &str) -> std::io::Result<()> {
    if std::fs::read_to_string(path).ok().as_deref() == Some(contents) {
        return Ok(());
    }
    std::fs::write(path, contents)
}

/// Resultado de una operación de Cargo, con errores remapeados.
#[derive(Debug)]
pub struct BuildReport {
    /// Salida de Cargo, si se llegó a ejecutar.
    pub output: Option<std::process::Output>,
    /// Diagnósticos PenguScript, incluidos los errores de rustc/Cargo.
    pub diagnostics: Vec<Diagnostic>,
    /// `true` si se reutilizó el build anterior sin invocar a Cargo.
    pub cached: bool,
}

impl BuildReport {
    /// `true` si Cargo terminó con éxito.
    #[must_use]
    pub fn success(&self) -> bool {
        !self.diagnostics.iter().any(Diagnostic::is_error)
            && (self.cached
                || self
                    .output
                    .as_ref()
                    .is_some_and(|output| output.status.success()))
    }
}

fn cargo_report(output: std::process::Output, sourcemap: &SourceMap) -> BuildReport {
    if output.status.success() {
        return BuildReport {
            output: Some(output),
            diagnostics: Vec::new(),
            cached: false,
        };
    }
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));
    let mut diagnostics = remap_rustc_diagnostics(&text, sourcemap);
    if diagnostics.is_empty() {
        diagnostics.push(Diagnostic::error(
            "PGS-E2014",
            "Cargo falló sin un diagnóstico JSON reconocible",
            Span::empty(FileId::new(0), 0),
        ));
    }
    BuildReport {
        output: Some(output),
        diagnostics,
        cached: false,
    }
}

/// Compila el proyecto y devuelve salida + diagnósticos remapeados.
pub fn build_report(root: &Path) -> std::io::Result<BuildReport> {
    build_report_with_packages(root, &[])
}

/// Como [`build_report`], fusionando paquetes como módulos.
pub fn build_report_with_packages(
    root: &Path,
    packages: &[(String, PathBuf)],
) -> std::io::Result<BuildReport> {
    let fingerprint = cache::fingerprint(root, packages);
    if let Some(cache) = reusable(root, &fingerprint) {
        debug_assert!(cache.matches(&fingerprint));
        return Ok(BuildReport {
            output: None,
            diagnostics: Vec::new(),
            cached: true,
        });
    }
    let result = compile_with_packages(root, packages);
    if !result.is_clean() {
        return Ok(BuildReport {
            output: None,
            diagnostics: result.diagnostics,
            cached: false,
        });
    }
    let out = emit(root, &result)?;
    let output = Command::new("cargo")
        .args([
            "build",
            "--quiet",
            "--message-format=json",
            "--manifest-path",
        ])
        .arg(out.join("Cargo.toml"))
        .output()?;
    let report = cargo_report(output, &result.sourcemap);
    if report.success() {
        remember(root, &fingerprint, &result)?;
    }
    Ok(report)
}

/// Caché válida y artefacto presente: no hace falta ni generar ni llamar a Cargo.
fn reusable(root: &Path, fingerprint: &str) -> Option<cache::Cache> {
    let cache = cache::Cache::read(root)?;
    if !cache.matches(fingerprint) {
        return None;
    }
    let bin = cache.bin_name.as_deref()?;
    cache::binary_path(root, bin).is_file().then_some(cache)
}

fn remember(root: &Path, fingerprint: &str, result: &BuildResult) -> std::io::Result<()> {
    if !result.is_bin {
        return Ok(());
    }
    cache::Cache {
        fingerprint: fingerprint.to_owned(),
        bin_name: Some(result.bin_name.clone()),
    }
    .write(root)
}

/// Compila y ejecuta, devolviendo salida + diagnósticos remapeados.
pub fn run_report(root: &Path) -> std::io::Result<BuildReport> {
    run_report_with_packages(root, &[])
}

/// Como [`run_report`], fusionando paquetes como módulos.
pub fn run_report_with_packages(
    root: &Path,
    packages: &[(String, PathBuf)],
) -> std::io::Result<BuildReport> {
    let fingerprint = cache::fingerprint(root, packages);
    let cached = reusable(root, &fingerprint);
    if let Some(cache) = &cached {
        let bin_name = cache.bin_name.clone().unwrap_or_default();
        let output = run_binary(root, &bin_name)?;
        return Ok(BuildReport {
            output: Some(output),
            diagnostics: Vec::new(),
            cached: true,
        });
    }
    let result = compile_with_packages(root, packages);
    if !result.is_clean() {
        return Ok(BuildReport {
            output: None,
            diagnostics: result.diagnostics,
            cached: false,
        });
    }
    if !result.is_bin {
        return Err(std::io::Error::other(
            "el proyecto no declara un binario `main.pengu`",
        ));
    }
    let out = emit(root, &result)?;
    let bin_name = result.bin_name.clone();
    let sourcemap = result.sourcemap.clone();
    let build = Command::new("cargo")
        .args([
            "build",
            "--quiet",
            "--message-format=json",
            "--manifest-path",
        ])
        .arg(out.join("Cargo.toml"))
        .args(["--bin", &bin_name])
        .output()?;
    let build_report = cargo_report(build, &sourcemap);
    if !build_report.success() {
        return Ok(build_report);
    }
    remember(root, &fingerprint, &result)?;
    let output = run_binary(root, &bin_name)?;
    let mut diagnostics = Vec::new();
    if !output.status.success() {
        diagnostics.push(Diagnostic::error(
            "PGS-E2014",
            "el binario terminó con error; revisa stderr",
            Span::empty(FileId::new(0), 0),
        ));
    }
    Ok(BuildReport {
        output: Some(output),
        diagnostics,
        cached: false,
    })
}

fn run_binary(root: &Path, bin_name: &str) -> std::io::Result<std::process::Output> {
    Command::new(cache::binary_path(root, bin_name)).output()
}

/// Ejecuta la suite de tests generada (`@@test`).
pub fn test_report(root: &Path) -> std::io::Result<BuildReport> {
    test_report_with_packages(root, &[])
}

/// Como [`test_report`], fusionando paquetes como módulos.
pub fn test_report_with_packages(
    root: &Path,
    packages: &[(String, PathBuf)],
) -> std::io::Result<BuildReport> {
    let result = compile_with_packages(root, packages);
    if !result.is_clean() {
        return Ok(BuildReport {
            output: None,
            diagnostics: result.diagnostics,
            cached: false,
        });
    }
    let out = emit(root, &result)?;
    let output = Command::new("cargo")
        .args([
            "test",
            "--quiet",
            "--message-format=json",
            "--manifest-path",
        ])
        .arg(out.join("Cargo.toml"))
        .output()?;
    Ok(cargo_report(output, &result.sourcemap))
}

/// Compila el proyecto generado con Cargo.
///
/// # Errors
/// Devuelve el error de E/S de Cargo o el de la generación.
pub fn build(root: &Path) -> std::io::Result<BuildReport> {
    build_report(root)
}

/// Compila y ejecuta el binario del proyecto generado.
///
/// # Errors
/// Devuelve el error de E/S de Cargo o de la ejecución del binario.
pub fn run(root: &Path) -> std::io::Result<BuildReport> {
    run_report(root)
}

/// Ejecuta la suite de tests generada.
///
/// # Errors
/// Devuelve el error de E/S de Cargo.
pub fn test(root: &Path) -> std::io::Result<BuildReport> {
    test_report(root)
}
