//! Comandos de distribución: `doctor`, `completions`, `man` y `version --json`.
//!
//! No usan dependencias externas: comprueban lo que pueden comprobar de verdad y
//! emiten texto generado a partir de una tabla única de comandos.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::args::{CompletionsArgs, Shell, USAGE};

/// Target de compilación con el que se construyó el binario.
#[must_use]
pub const fn target() -> &'static str {
    if cfg!(all(target_arch = "x86_64", target_os = "linux")) {
        "x86_64-unknown-linux-gnu"
    } else if cfg!(all(target_arch = "aarch64", target_os = "linux")) {
        "aarch64-unknown-linux-gnu"
    } else if cfg!(all(target_arch = "x86_64", target_os = "macos")) {
        "x86_64-apple-darwin"
    } else if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        "aarch64-apple-darwin"
    } else if cfg!(all(target_arch = "x86_64", target_os = "windows")) {
        "x86_64-pc-windows-msvc"
    } else {
        "unknown-unknown-unknown"
    }
}

/// Commit con el que se construyó el binario, si se conoce.
#[must_use]
pub fn commit() -> &'static str {
    option_env!("PENGU_COMMIT").unwrap_or("unknown")
}

/// Versión del compilador.
#[must_use]
pub const fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// `pengu version` en texto.
#[must_use]
pub fn version_text() -> String {
    format!("pengu {} ({})", version(), target())
}

/// `pengu version --json`.
#[must_use]
pub fn version_json() -> String {
    format!(
        "{{\"name\":\"pengu\",\"version\":\"{}\",\"target\":\"{}\",\"commit\":\"{}\"}}",
        version(),
        target(),
        commit()
    )
}

/// Tabla de comandos usada por `man` y los completados.
pub const COMMANDS: &[(&str, &str)] = &[
    ("fetch", "descarga las dependencias y escribe Tome.lock"),
    ("tree", "muestra el árbol de dependencias"),
    ("build", "compila el proyecto"),
    ("check", "analiza el proyecto sin invocar Cargo"),
    (
        "watch",
        "repite check|build|run|test al cambiar los fuentes",
    ),
    ("run", "compila y ejecuta el binario"),
    ("test", "ejecuta los tests del proyecto"),
    ("vendor", "copia las dependencias del lock a vendor/"),
    ("size", "muestra el tamaño en bytes de tipos y funciones"),
    ("fmt", "formatea el código"),
    ("lint", "avisa de estilo y errores probables"),
    ("explain", "explica un diagnóstico con la especificación"),
    ("fix", "aplica correcciones seguras"),
    ("doc", "genera la documentación Markdown"),
    ("bench", "mide las etapas del compilador"),
    ("bindgen", "genera un .d.pengu desde una cabecera C"),
    ("lsp", "servidor de lenguaje por stdio"),
    ("doctor", "comprueba la instalación"),
    ("completions", "emite el completado de shell"),
    ("man", "emite la página de manual"),
    ("add", "añade una dependencia"),
    ("remove", "quita una dependencia"),
    ("new", "crea un proyecto desde un template"),
    ("update", "re-resuelve etiquetas y ramas"),
    ("version", "muestra la versión"),
    ("help", "muestra la ayuda"),
];

/// Opciones globales usadas por los completados.
pub const GLOBAL_OPTIONS: &[(&str, &str)] = &[
    ("--offline", "no usa la red"),
    ("--locked", "exige que Tome.lock coincida"),
    ("--refresh", "re-resuelve aunque el lock coincida"),
    ("--force", "además re-clona la caché de git"),
    ("--check", "solo verifica"),
    ("--doc", "incluye doc tests en test"),
    ("--watch", "repite check al cambiar"),
    ("--json", "salida JSON"),
    ("--verbose", "salida detallada"),
    ("--help", "ayuda"),
    ("--version", "versión"),
];

/// `pengu completions <shell>`.
#[must_use]
pub fn completions(args: &CompletionsArgs) -> String {
    match args.shell {
        Shell::Bash => completions_bash(),
        Shell::Zsh => completions_zsh(),
        Shell::Fish => completions_fish(),
    }
}

fn words() -> String {
    COMMANDS
        .iter()
        .map(|(name, _)| *name)
        .collect::<Vec<_>>()
        .join(" ")
}

fn completions_bash() -> String {
    format!(
        r#"# completado de bash para pengu
_pengu() {{
    local cur prev commands options
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    commands="{}"
    options="{}"
    case "$prev" in
        completions) COMPREPLY=( $(compgen -W "bash zsh fish" -- "$cur") ); return 0 ;;
        watch) COMPREPLY=( $(compgen -W "check build run test" -- "$cur") ); return 0 ;;
        explain) COMPREPLY=( $(compgen -W "PGS-E1805 PGS-E2023 PGS-E3001 PGS-W1101" -- "$cur") ); return 0 ;;
    esac
    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$commands $options" -- "$cur") )
        return 0
    fi
    COMPREPLY=( $(compgen -W "$options" -- "$cur") )
    return 0
}}
complete -F _pengu pengu
"#,
        words(),
        GLOBAL_OPTIONS
            .iter()
            .map(|(name, _)| *name)
            .collect::<Vec<_>>()
            .join(" ")
    )
}

fn completions_zsh() -> String {
    let commands = COMMANDS
        .iter()
        .map(|(name, description)| format!("        '{}:{}'", name, description.replace('\'', "")))
        .collect::<Vec<_>>()
        .join("\n");
    let options = GLOBAL_OPTIONS
        .iter()
        .map(|(name, description)| format!("        '{}[{}]'", name, description.replace('\'', "")))
        .collect::<Vec<_>>()
        .join("\n");
    format!(
        r#"#compdef pengu
# completado de zsh para pengu
_pengu() {{
    _arguments -C \
{options} \
        '1:comando:({commands})' \
        '*::argumento:->args'
}}
_pengu "$@"
"#
    )
}

fn completions_fish() -> String {
    use std::fmt::Write as _;
    let mut out = String::from("# completado de fish para pengu\n");
    for (name, description) in COMMANDS {
        let _ = writeln!(
            out,
            "complete -c pengu -f -n '__fish_use_subcommand' -a '{name}' -d '{description}'"
        );
    }
    for (name, description) in GLOBAL_OPTIONS {
        let _ = writeln!(
            out,
            "complete -c pengu -l '{}' -d '{description}'",
            name.trim_start_matches("--")
        );
    }
    out.push_str(
        "complete -c pengu -f -n '__fish_seen_subcommand_from completions' -a 'bash zsh fish'\n",
    );
    out.push_str(
        "complete -c pengu -f -n '__fish_seen_subcommand_from watch' -a 'check build run test'\n",
    );
    out
}

/// `pengu man`: página de manual en roff.
#[must_use]
pub fn man_page() -> String {
    use std::fmt::Write as _;
    let mut out = String::new();
    out.push_str(".TH PENGU 1\n");
    out.push_str(".SH NOMBRE\n");
    out.push_str("pengu \\- gestor de paquetes y compilador de PenguScript\n");
    out.push_str(".SH SINOPSIS\n");
    out.push_str(".B pengu\n<comando> [opciones]\n");
    out.push_str(".SH DESCRIPCIÓN\n");
    out.push_str("Compila, ejecuta y prueba proyectos PenguScript, gestiona dependencias git y vendorizadas, y habla el protocolo de servidor de lenguaje por stdio con ");
    out.push_str(".B pengu lsp\n.\n");
    out.push_str(".SH COMANDOS\n");
    for (name, description) in COMMANDS {
        let _ = writeln!(out, ".TP\n.B {name}\n{description}.\n");
    }
    out.push_str(".SH OPCIONES GLOBALES\n");
    for (name, description) in GLOBAL_OPTIONS {
        let _ = writeln!(out, ".TP\n.B {name}\n{description}.\n");
    }
    out.push_str(".SH ARCHIVOS\n");
    out.push_str(".TP\n.I Tome.toml\nmanifiesto del proyecto\n");
    out.push_str(".TP\n.I Tome.lock\nlock con commits y checksums\n");
    out.push_str(".TP\n.I vendor/\ndependencias vendorizadas\n");
    out.push_str(".SH VÉASE TAMBIÉN\n");
    out.push_str("La especificación del lenguaje en docs/LANGUAGE.md y la guía de instalación en docs/INSTALL.md.\n");
    out
}

/// Ayuda corta (la misma de `pengu help`).
#[must_use]
pub const fn usage() -> &'static str {
    USAGE
}

/// Comprobación de instalación.
pub struct Doctor {
    checks: Vec<Check>,
}

struct Check {
    required: bool,
    ok: bool,
    name: &'static str,
    detail: String,
}

impl Doctor {
    /// Ejecuta todas las comprobaciones.
    #[must_use]
    pub fn run() -> Self {
        let mut checks = vec![check_binary(), check_path(), check_stdlib()];
        checks.push(check_compiler());
        checks.push(optional_check(
            "rustc",
            &["--version"],
            "compilador de Rust (necesario para build/run)",
        ));
        checks.push(optional_check(
            "cargo",
            &["--version"],
            "gestor de paquetes de Rust (necesario para build/run)",
        ));
        checks.push(optional_check(
            "clang",
            &["--version"],
            "solo para `pengu bindgen`",
        ));
        checks.push(optional_check(
            "git",
            &["--version"],
            "solo para dependencias git",
        ));
        checks.push(check_extension());
        Self { checks }
    }

    /// Código de salida: 1 si alguna comprobación requerida falla.
    #[must_use]
    pub fn code(&self) -> i32 {
        i32::from(u8::from(
            self.checks.iter().any(|check| check.required && !check.ok),
        ))
    }

    /// Informe legible.
    pub fn print(&self) {
        println!("pengu {} ({})", version(), target());
        for check in &self.checks {
            let mark = if check.ok {
                "ok"
            } else if check.required {
                "FALLA"
            } else {
                "aviso"
            };
            println!("{mark:>5}  {:<12} {}", check.name, check.detail);
        }
        if self.code() == 0 {
            println!("\ntodo listo: `pengu build` y `pengu lsp` deberían funcionar.");
        } else {
            println!("\nrevisa las comprobaciones marcadas como FALLA.");
        }
    }

    /// Informe JSON.
    #[must_use]
    pub fn json(&self) -> String {
        let items = self
            .checks
            .iter()
            .map(|check| {
                format!(
                    "{{\"name\":\"{}\",\"ok\":{},\"required\":{},\"detail\":\"{}\"}}",
                    check.name,
                    check.ok,
                    check.required,
                    escape(&check.detail)
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        format!(
            "{{\"version\":\"{}\",\"target\":\"{}\",\"ok\":{},\"checks\":[{}]}}",
            version(),
            target(),
            self.code() == 0,
            items
        )
    }
}

fn check_binary() -> Check {
    match std::env::current_exe() {
        Ok(path) => Check {
            required: true,
            ok: true,
            name: "binario",
            detail: path.display().to_string(),
        },
        Err(error) => Check {
            required: true,
            ok: false,
            name: "binario",
            detail: format!("no se pudo localizar: {error}"),
        },
    }
}

fn check_path() -> Check {
    let Some(current) = std::env::current_exe()
        .ok()
        .and_then(|path| path.canonicalize().ok())
    else {
        return Check {
            required: false,
            ok: false,
            name: "PATH",
            detail: "no se pudo resolver el binario".to_owned(),
        };
    };
    let found = find_in_path("pengu");
    match found {
        Some(path) if same_executable(&path, &current) => Check {
            required: true,
            ok: true,
            name: "PATH",
            detail: path.display().to_string(),
        },
        Some(path) => Check {
            required: true,
            ok: false,
            name: "PATH",
            detail: format!(
                "`pengu` resuelve a {} y este binario es {}; revisa el orden del PATH",
                path.display(),
                current.display()
            ),
        },
        None => Check {
            required: true,
            ok: false,
            name: "PATH",
            detail: "`pengu` no está en el PATH (añade <prefijo>/bin o reinicia la terminal)"
                .to_owned(),
        },
    }
}

fn same_executable(left: &Path, right: &Path) -> bool {
    match (left.canonicalize(), right.canonicalize()) {
        (Ok(left), Ok(right)) => left == right,
        _ => left == right,
    }
}

fn find_in_path(name: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    for directory in std::env::split_paths(&path) {
        for candidate in [directory.join(name), directory.join(format!("{name}.exe"))] {
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }
    None
}

fn check_stdlib() -> Check {
    let files = pengu_std::files();
    Check {
        required: true,
        ok: !files.is_empty(),
        name: "stdlib",
        detail: format!("{} módulos embebidos", files.len()),
    }
}

fn check_compiler() -> Check {
    let root = match temp_project() {
        Ok(root) => root,
        Err(error) => {
            return Check {
                required: true,
                ok: false,
                name: "compilador",
                detail: format!("no se pudo crear el proyecto temporal: {error}"),
            };
        }
    };
    let report = pengu_build::check(&root);
    let errors: Vec<String> = report
        .diagnostics
        .iter()
        .filter(|diagnostic| diagnostic.is_error())
        .map(|diagnostic| format!("{}: {}", diagnostic.code, diagnostic.message))
        .collect();
    let _ = std::fs::remove_dir_all(&root);
    match errors.first() {
        Some(error) => Check {
            required: true,
            ok: false,
            name: "compilador",
            detail: error.clone(),
        },
        None => Check {
            required: true,
            ok: true,
            name: "compilador",
            detail: "analiza un proyecto temporal".to_owned(),
        },
    }
}

fn temp_project() -> std::io::Result<PathBuf> {
    let base = std::env::temp_dir().join(format!(
        "pengu-doctor-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default()
    ));
    std::fs::create_dir_all(&base)?;
    std::fs::write(
        base.join("Tome.toml"),
        "[tome]\nname = \"doctor\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"doctor\"\n",
    )?;
    std::fs::write(base.join("main.pengu"), "grimoire\n    print(1)\n")?;
    Ok(base)
}

fn optional_check(program: &'static str, args: &[&str], purpose: &'static str) -> Check {
    let output = Command::new(program).args(args).output();
    match output {
        Ok(output) if output.status.success() => {
            let text = String::from_utf8_lossy(&output.stdout);
            let first = text.lines().next().unwrap_or(program);
            Check {
                required: false,
                ok: true,
                name: program,
                detail: first.trim().to_owned(),
            }
        }
        Ok(_) => Check {
            required: false,
            ok: false,
            name: program,
            detail: format!("responde con error; {purpose}"),
        },
        Err(_) => Check {
            required: false,
            ok: false,
            name: program,
            detail: format!("no encontrado; {purpose}"),
        },
    }
}

fn check_extension() -> Check {
    let output = Command::new("code").args(["--list-extensions"]).output();
    match output {
        Ok(output) if output.status.success() => {
            let text = String::from_utf8_lossy(&output.stdout);
            let found = text
                .lines()
                .any(|line| line.trim().eq_ignore_ascii_case(EXTENSION_ID));
            Check {
                required: false,
                ok: found,
                name: "extensión",
                detail: if found {
                    format!("{EXTENSION_ID} instalada")
                } else {
                    format!("{EXTENSION_ID} no instalada; ejecuta scripts/install-extension.sh")
                },
            }
        }
        _ => Check {
            required: false,
            ok: false,
            name: "extensión",
            detail: "`code` no está en el PATH; instala el .vsix a mano".to_owned(),
        },
    }
}

/// Identificador de la extensión de VS Code.
pub const EXTENSION_ID: &str = "penguscript.pengu-lsp";

fn escape(text: &str) -> String {
    text.replace('\\', "\\\\").replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn la_version_json_tiene_los_campos() {
        let json = version_json();
        assert!(json.contains("\"name\":\"pengu\""));
        assert!(json.contains(&format!("\"version\":\"{}\"", version())));
        assert!(json.contains("\"target\":\""));
    }

    #[test]
    fn los_completados_mencionan_los_comandos() {
        for shell in [Shell::Bash, Shell::Zsh, Shell::Fish] {
            let text = completions(&CompletionsArgs { shell });
            assert!(text.contains("doctor"), "{shell:?}");
            assert!(text.contains("bindgen"));
        }
    }

    #[test]
    fn el_manual_tiene_secciones() {
        let man = man_page();
        assert!(man.starts_with(".TH PENGU 1"));
        assert!(man.contains(".SH COMANDOS"));
        assert!(man.contains("bindgen"));
    }

    #[test]
    fn el_doctor_encuentra_la_stdlib() {
        let doctor = Doctor::run();
        assert!(
            doctor
                .checks
                .iter()
                .any(|check| check.name == "stdlib" && check.ok)
        );
    }
}
