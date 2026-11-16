//! Parser de argumentos de `pengu` (sin dependencias externas).
//!
//! Acepta un subcomando, flags globales (`--offline`, `--locked`, `--force`,
//! `--verbose`) y los argumentos propios de `add`, `remove` y `update`. Los argumentos
//! desconocidos son un error de uso (código 2).

/// Subcomando a ejecutar.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Command {
    /// Crear un proyecto desde un template.
    New(NewArgs),
    /// Descargar y fijar el lock.
    Fetch,
    /// Mostrar el árbol de dependencias.
    Tree,
    /// Compilar el proyecto.
    Build,
    /// Analizar el proyecto sin invocar Cargo.
    Check,
    /// Re-ejecutar un comando al cambiar los fuentes.
    Watch(WatchArgs),
    /// Compilar y ejecutar el binario.
    Run,
    /// Ejecutar los tests.
    Test,
    /// Añadir una dependencia y actualizar el lock.
    Add(AddArgs),
    /// Quitar una dependencia.
    Remove(RemoveArgs),
    /// Re-resolver las referencias móviles.
    Update(UpdateArgs),
    /// Copiar las dependencias del lock a `vendor/`.
    Vendor,
    /// Mostrar el tamaño en bytes de los tipos y funciones del programa.
    Size,
    /// Formatear archivos.
    Fmt(FmtArgs),
    /// Analizar avisos de estilo y errores probables.
    Lint(LintArgs),
    /// Explicar un código de diagnóstico.
    Explain(ExplainArgs),
    /// Aplicar correcciones seguras.
    Fix(FixArgs),
    /// Generar documentación Markdown.
    Doc(DocArgs),
    /// Medir el pipeline del compilador.
    Bench(BenchArgs),
    /// Generar un `.d.pengu` desde una cabecera C.
    Bindgen(BindgenArgs),
    /// Servidor de lenguaje por stdio.
    Lsp,
    /// Comprobar la instalación.
    Doctor,
    /// Emitir un script de completado de shell.
    Completions(CompletionsArgs),
    /// Emitir la página de manual.
    Man,
    /// Mostrar la versión.
    Version,
    /// Mostrar la ayuda.
    Help,
}

/// Argumentos de `pengu bindgen`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct BindgenArgs {
    /// Cabecera C de entrada.
    pub header: String,
    /// Archivo de salida (por defecto `<nombre>.d.pengu` junto a la cabecera).
    pub output: Option<String>,
    /// Directorios de inclusión (`-I`).
    pub include_dirs: Vec<String>,
    /// Macros (`-D`).
    pub defines: Vec<String>,
    /// Patrones permitidos (`--allow`); vacío = todos.
    pub allowlist: Vec<String>,
    /// Patrones bloqueados (`--block`).
    pub blocklist: Vec<String>,
    /// Comprobar que el archivo existe y coincide, sin escribir.
    pub check: bool,
}

/// Shells con completado.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Shell {
    /// Bash.
    Bash,
    /// Zsh.
    Zsh,
    /// Fish.
    Fish,
}

impl Shell {
    /// Nombre canónico.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Bash => "bash",
            Self::Zsh => "zsh",
            Self::Fish => "fish",
        }
    }

    fn parse(name: &str) -> Result<Self, String> {
        match name {
            "bash" => Ok(Self::Bash),
            "zsh" => Ok(Self::Zsh),
            "fish" => Ok(Self::Fish),
            other => Err(format!(
                "shell desconocido `{other}` (usa bash, zsh o fish)"
            )),
        }
    }
}

/// Argumentos de `pengu completions`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompletionsArgs {
    /// Shell de destino.
    pub shell: Shell,
}

/// Argumentos de `pengu watch`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct WatchArgs {
    /// Comando a repetir en cada cambio.
    pub action: WatchAction,
}

/// Comando que `pengu watch` repite.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WatchAction {
    /// `check`.
    Check,
    /// `build`.
    Build,
    /// `run`.
    Run,
    /// `test`.
    Test,
}

impl WatchAction {
    /// Nombre del comando equivalente.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Check => "check",
            Self::Build => "build",
            Self::Run => "run",
            Self::Test => "test",
        }
    }
}

/// Argumentos de `pengu add`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct AddArgs {
    /// Nombre con el que se importa (por defecto, el del repositorio).
    pub name: Option<String>,
    /// URL git de origen.
    pub git: Option<String>,
    /// Ruta local de origen.
    pub path: Option<String>,
    /// Etiqueta a seguir.
    pub tag: Option<String>,
    /// Rama a seguir.
    pub branch: Option<String>,
    /// Revisión inmóvil.
    pub rev: Option<String>,
}

/// Argumentos de `pengu remove`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RemoveArgs {
    /// Dependencia a quitar.
    pub name: String,
}

/// Argumentos de `pengu new`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NewArgs {
    /// Nombre del proyecto (y del directorio).
    pub name: String,
    /// Template embebido; `None` usa `bin`.
    pub template: Option<String>,
}

/// Argumentos de `pengu update`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct UpdateArgs {
    /// Dependencia concreta; sin nombre se actualizan todas.
    pub name: Option<String>,
}

/// Argumentos de `pengu fmt`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct FmtArgs {
    /// Archivos a formatear; vacío usa el programa del proyecto.
    pub files: Vec<String>,
}

/// Argumentos de `pengu lint`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LintArgs {
    /// Archivos a analizar; vacío usa el programa del proyecto.
    pub files: Vec<String>,
    /// Códigos o nombres en nivel `allow`.
    pub allow: Vec<String>,
    /// Códigos o nombres en nivel `warn`.
    pub warn: Vec<String>,
    /// Códigos o nombres en nivel `deny` (falla la ejecución).
    pub deny: Vec<String>,
    /// Mostrar el catálogo de lints y salir.
    pub list: bool,
    /// Analizar los archivos como stdlib (omite los lints de estilo de std).
    pub std: bool,
}

/// Argumentos de `pengu explain`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ExplainArgs {
    /// Código a explicar, por ejemplo `PGS-E3001`.
    pub code: String,
}

/// Argumentos de `pengu fix`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct FixArgs {
    /// Solo mostrar los cambios, sin escribir.
    pub dry_run: bool,
    /// Archivos a corregir; vacío usa el programa del proyecto.
    pub files: Vec<String>,
}

/// Argumentos de `pengu doc`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DocArgs {
    /// Abrir el resultado con el visor del sistema.
    pub open: bool,
    /// Archivos a documentar; vacío usa el programa del proyecto.
    pub files: Vec<String>,
}

/// Argumentos de `pengu bench`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BenchArgs {
    /// Repeticiones por etapa.
    pub iterations: usize,
}

impl Default for BenchArgs {
    fn default() -> Self {
        Self { iterations: 5 }
    }
}

/// Argumentos ya validados.
#[derive(Clone, Debug, Eq, PartialEq)]
#[allow(clippy::struct_excessive_bools)]
pub struct Cli {
    /// Subcomando.
    pub command: Command,
    /// No tocar la red.
    pub offline: bool,
    /// Fallar si el lock no coincide.
    pub locked: bool,
    /// Re-resolver aunque el lock coincida.
    pub refresh: bool,
    /// Volver a clonar la caché de git.
    pub force: bool,
    /// Salida detallada.
    pub verbose: bool,
    /// Solo verificar (`pengu vendor --check`, `pengu fmt --check`).
    pub check: bool,
    /// Incluir doc tests en `pengu test`.
    pub doc: bool,
    /// Repetir al cambiar los fuentes (`pengu check --watch`).
    pub watch: bool,
    /// Salida en JSON (`pengu version --json`, `pengu doctor --json`).
    pub json: bool,
}

/// Ayuda de la CLI.
pub const USAGE: &str = "\
pengu — gestor de paquetes de PenguScript

USO:
    pengu <comando> [opciones]

COMANDOS:
    fetch              descarga las dependencias y escribe `Tome.lock`
    tree               muestra el árbol de dependencias
    build              compila el proyecto
    check              analiza el proyecto sin invocar Cargo (`--watch` lo repite)
    watch <comando>    repite `check|build|run|test` al cambiar los fuentes
    run                compila y ejecuta el binario
    test               ejecuta los tests del proyecto
    vendor             copia las dependencias del lock a `vendor/`
    size               muestra el tamaño en bytes de tipos y funciones
    fmt [archivos…]    formatea el código (`--check` solo verifica)
    lint [archivos…]   avisa de estilo y errores probables (`--allow/--warn/--deny`, `--std`)
    explain <código>   explica un diagnóstico con la especificación
    fix                aplica correcciones seguras (`--dry-run` solo muestra)
    doc                genera la documentación Markdown (`--open` la abre)
    bench              mide las etapas del compilador (`--iterations N`)
    bindgen <cabecera> genera un `.d.pengu` desde una cabecera C (`-o`, `-I`, `-D`,
                       `--allow`, `--block`, `--check`)
    lsp                servidor de lenguaje por stdio (editores)
    doctor             comprueba la instalación (binario, PATH, stdlib, editores)
    completions <shell> emite el completado para bash, zsh o fish
    man                emite la página de manual en formato roff
    add <fuente>       añade una dependencia (`--git URL` o `--path RUTA`)
    remove <nombre>    quita una dependencia
    new <nombre>       crea un proyecto (`--template bin|lib|with-dependency`)
    update [nombre]    re-resuelve etiquetas y ramas
    version            muestra la versión
    help               muestra esta ayuda

OPCIONES:
    --offline          no usa la red (falla si falta algo en la caché)
    --check            con `vendor`/`fmt`, solo verifica sin escribir
    --doc              con `test`, ejecuta también los doc tests
    --watch            con `check`, repite al cambiar los fuentes
    --locked           exige que `Tome.lock` coincida con `Tome.toml`
    --refresh          re-resuelve aunque el lock coincida
    --force            además re-clona la caché de git
    -v, --verbose      salida detallada
    -h, --help         ayuda
    -V, --version      versión
    --json             con `version` y `doctor`, salida JSON

AÑADIR:
    --git URL          origen git
    --path RUTA        origen local
    --tag ETIQUETA     sigue una etiqueta (por defecto, la versión más alta)
    --branch RAMA      sigue una rama
    --rev REVISION     fija una revisión inmóvil
";

#[derive(Default)]
#[allow(clippy::struct_excessive_bools)]
struct Flags {
    doc: bool,
    watch: bool,
    json: bool,
    offline: bool,
    locked: bool,
    refresh: bool,
    force: bool,
    verbose: bool,
    check: bool,
}

/// Parsea los argumentos (sin el nombre del programa).
///
/// # Errors
/// Devuelve un mensaje de uso si falta un comando, hay opciones incompatibles o se
/// desconocen argumentos.
pub fn parse(args: &[String]) -> Result<Cli, String> {
    let mut flags = Flags::default();
    let mut rest: Vec<String> = Vec::new();
    for arg in args {
        match arg.as_str() {
            "--offline" => flags.offline = true,
            "--locked" => flags.locked = true,
            "--refresh" => flags.refresh = true,
            "--force" => {
                flags.force = true;
                flags.refresh = true;
            }
            "--check" => flags.check = true,
            "--doc" => flags.doc = true,
            "--json" => flags.json = true,
            "--watch" => flags.watch = true,
            "-v" | "--verbose" => flags.verbose = true,
            "-h" | "--help" => return Ok(cli(Command::Help, &flags)),
            "-V" | "--version" => return Ok(cli(Command::Version, &flags)),
            value => rest.push(value.to_owned()),
        }
    }
    if let Some(first) = rest.first().filter(|arg| arg.starts_with('-')) {
        return Err(format!("opción desconocida `{first}`"));
    }
    let Some(name) = rest.first() else {
        return Ok(cli(Command::Help, &flags));
    };
    let tail = &rest[1..];
    let command = match name.as_str() {
        "fetch" => no_args(Command::Fetch, tail)?,
        "tree" => no_args(Command::Tree, tail)?,
        "build" => no_args(Command::Build, tail)?,
        "check" => no_args(Command::Check, tail)?,
        "watch" => Command::Watch(parse_watch(tail)?),
        "run" => no_args(Command::Run, tail)?,
        "test" => no_args(Command::Test, tail)?,
        "vendor" => no_args(Command::Vendor, tail)?,
        "size" => no_args(Command::Size, tail)?,
        "fmt" => Command::Fmt(parse_fmt(tail)?),
        "lint" => Command::Lint(parse_lint(tail)?),
        "explain" => Command::Explain(ExplainArgs {
            code: required_name(tail, "explain")?,
        }),
        "fix" => Command::Fix(parse_fix(tail)?),
        "doc" => Command::Doc(parse_doc(tail)?),
        "bench" => Command::Bench(parse_bench(tail)?),
        "bindgen" => Command::Bindgen(parse_bindgen(tail, flags.check)?),
        "lsp" => no_args(Command::Lsp, tail)?,
        "doctor" => no_args(Command::Doctor, tail)?,
        "completions" => Command::Completions(CompletionsArgs {
            shell: Shell::parse(&required_name(tail, "completions")?)?,
        }),
        "man" => no_args(Command::Man, tail)?,
        "version" => no_args(Command::Version, tail)?,
        "help" => no_args(Command::Help, tail)?,
        "new" => Command::New(parse_new(tail)?),
        "add" => Command::Add(parse_add(tail)?),
        "remove" => Command::Remove(RemoveArgs {
            name: required_name(tail, "remove")?,
        }),
        "update" => Command::Update(UpdateArgs {
            name: tail.first().cloned(),
        }),
        other => return Err(format!("comando desconocido `{other}`")),
    };
    if flags.watch && !matches!(&command, Command::Check) {
        return Err(
            "`--watch` solo se admite con `pengu check` (o usa `pengu watch <comando>`)".to_owned(),
        );
    }
    if flags.locked && flags.refresh {
        return Err("`--locked` y `--force` no se pueden combinar".to_owned());
    }
    Ok(cli(command, &flags))
}

fn parse_bindgen(tail: &[String], check: bool) -> Result<BindgenArgs, String> {
    let mut args = BindgenArgs {
        check,
        ..BindgenArgs::default()
    };
    let mut index = 0;
    while index < tail.len() {
        let value = tail[index].as_str();
        let take = |slot: &mut Vec<String>, index: &mut usize| -> Result<(), String> {
            let next = tail
                .get(*index + 1)
                .ok_or_else(|| format!("`{value}` necesita un valor"))?;
            slot.push(next.clone());
            *index += 2;
            Ok(())
        };
        match value {
            "-I" | "--include" => take(&mut args.include_dirs, &mut index)?,
            "-D" | "--define" => take(&mut args.defines, &mut index)?,
            "--allow" => take(&mut args.allowlist, &mut index)?,
            "--block" => take(&mut args.blocklist, &mut index)?,
            "-o" | "--output" => {
                let next = tail
                    .get(index + 1)
                    .ok_or_else(|| "`--output` necesita un valor".to_owned())?;
                args.output = Some(next.clone());
                index += 2;
            }
            other if other.starts_with("--output=") => {
                args.output = Some(other["--output=".len()..].to_owned());
                index += 1;
            }
            other if other.starts_with("-I") && other.len() > 2 => {
                args.include_dirs.push(other[2..].to_owned());
                index += 1;
            }
            other if other.starts_with("-D") && other.len() > 2 => {
                args.defines.push(other[2..].to_owned());
                index += 1;
            }
            other if other.starts_with('-') => {
                return Err(format!("opción desconocida `{other}`"));
            }
            other => {
                if !args.header.is_empty() {
                    return Err("`bindgen` admite una sola cabecera".to_owned());
                }
                other.clone_into(&mut args.header);
                index += 1;
            }
        }
    }
    if args.header.is_empty() {
        return Err("`bindgen` necesita una cabecera C".to_owned());
    }
    Ok(args)
}

fn cli(command: Command, flags: &Flags) -> Cli {
    Cli {
        command,
        offline: flags.offline,
        locked: flags.locked,
        refresh: flags.refresh,
        force: flags.force,
        verbose: flags.verbose,
        check: flags.check,
        doc: flags.doc,
        watch: flags.watch,
        json: flags.json,
    }
}

fn no_args(command: Command, rest: &[String]) -> Result<Command, String> {
    if rest.is_empty() {
        Ok(command)
    } else {
        Err(format!("argumento inesperado `{}`", rest[0]))
    }
}

fn required_name(rest: &[String], command: &str) -> Result<String, String> {
    if rest.len() == 1 {
        Ok(rest[0].clone())
    } else if rest.is_empty() {
        Err(format!("`pengu {command}` necesita un nombre"))
    } else {
        Err(format!("`pengu {command}` acepta un solo nombre"))
    }
}

fn parse_watch(args: &[String]) -> Result<WatchArgs, String> {
    let Some(name) = args.first() else {
        return Err("`pengu watch` necesita un comando: check, build, run o test".to_owned());
    };
    if args.len() > 1 {
        return Err(format!("argumento inesperado `{}`", args[1]));
    }
    let action = match name.as_str() {
        "check" => WatchAction::Check,
        "build" => WatchAction::Build,
        "run" => WatchAction::Run,
        "test" => WatchAction::Test,
        other => {
            return Err(format!(
                "`pengu watch` no reconoce `{other}` (usa check, build, run o test)"
            ));
        }
    };
    Ok(WatchArgs { action })
}

fn parse_new(args: &[String]) -> Result<NewArgs, String> {
    let mut name = None;
    let mut template = None;
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        let (flag, inline) = match arg.split_once('=') {
            Some((flag, value)) => (flag, Some(value.to_owned())),
            None => (arg.as_str(), None),
        };
        match flag {
            "--template" => {
                let value = if let Some(value) = inline {
                    value
                } else if index < args.len() {
                    index += 1;
                    args[index - 1].clone()
                } else {
                    return Err("`--template` necesita un valor".to_owned());
                };
                template = Some(value);
            }
            other if other.starts_with('-') => {
                return Err(format!("opción desconocida `{other}`"));
            }
            positional => {
                if name.is_some() {
                    return Err("`pengu new` acepta un solo nombre".to_owned());
                }
                name = Some(positional.to_owned());
            }
        }
    }
    if name.is_none() && template.as_deref() == Some("list") {
        return Ok(NewArgs {
            name: "list".to_owned(),
            template,
        });
    }
    let Some(name) = name else {
        return Err("`pengu new` necesita un nombre".to_owned());
    };
    Ok(NewArgs { name, template })
}

fn parse_fix(args: &[String]) -> Result<FixArgs, String> {
    let mut fix = FixArgs::default();
    for arg in args {
        match arg.as_str() {
            "--dry-run" => fix.dry_run = true,
            other if other.starts_with('-') => {
                return Err(format!("opción desconocida `{other}`"));
            }
            other => fix.files.push(other.to_owned()),
        }
    }
    Ok(fix)
}

fn parse_doc(args: &[String]) -> Result<DocArgs, String> {
    let mut doc = DocArgs::default();
    for arg in args {
        match arg.as_str() {
            "--open" => doc.open = true,
            other if other.starts_with('-') => {
                return Err(format!("opción desconocida `{other}`"));
            }
            other => doc.files.push(other.to_owned()),
        }
    }
    Ok(doc)
}

fn parse_bench(args: &[String]) -> Result<BenchArgs, String> {
    let mut bench = BenchArgs::default();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        let value = match arg.split_once('=') {
            Some(("--iterations", value)) => value.to_owned(),
            Some((flag, _)) => return Err(format!("opción desconocida `{flag}`")),
            None if arg == "--iterations" => {
                if index < args.len() {
                    index += 1;
                    args[index - 1].clone()
                } else {
                    return Err("`--iterations` necesita un valor".to_owned());
                }
            }
            None => return Err(format!("argumento inesperado `{arg}`")),
        };
        bench.iterations = value
            .parse::<usize>()
            .map_err(|_| format!("`{value}` no es un número de repeticiones"))?;
        if bench.iterations == 0 {
            return Err("`--iterations` debe ser mayor que cero".to_owned());
        }
    }
    Ok(bench)
}

fn parse_fmt(args: &[String]) -> Result<FmtArgs, String> {
    let mut files = Vec::new();
    for arg in args {
        if arg.starts_with('-') {
            return Err(format!("opción desconocida `{arg}`"));
        }
        files.push(arg.clone());
    }
    Ok(FmtArgs { files })
}

fn parse_lint(args: &[String]) -> Result<LintArgs, String> {
    let mut lint = LintArgs::default();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        if arg == "--list" {
            lint.list = true;
            continue;
        }
        if arg == "--std" {
            lint.std = true;
            continue;
        }
        let (flag, inline) = match arg.split_once('=') {
            Some((flag, value)) => (flag, Some(value.to_owned())),
            None => (arg.as_str(), None),
        };
        let value = |inline: &Option<String>, index: &mut usize| -> Result<String, String> {
            if let Some(value) = inline.clone() {
                return Ok(value);
            }
            if *index < args.len() {
                *index += 1;
                Ok(args[*index - 1].clone())
            } else {
                Err(format!("`{flag}` necesita un valor"))
            }
        };
        match flag {
            "--allow" => lint.allow.push(value(&inline, &mut index)?),
            "--warn" => lint.warn.push(value(&inline, &mut index)?),
            "--deny" => lint.deny.push(value(&inline, &mut index)?),
            other if other.starts_with('-') && inline.is_none() => {
                return Err(format!("opción desconocida `{other}`"));
            }
            other => {
                if inline.is_some() {
                    return Err(format!("opción desconocida `{other}`"));
                }
                lint.files.push(other.to_owned());
            }
        }
    }
    Ok(lint)
}

fn parse_add(args: &[String]) -> Result<AddArgs, String> {
    let mut add = AddArgs::default();
    let mut index = 0;
    while index < args.len() {
        let arg = &args[index];
        index += 1;
        let (flag, inline) = match arg.split_once('=') {
            Some((flag, value)) => (flag, Some(value.to_owned())),
            None => (arg.as_str(), None),
        };
        let value = |inline: &Option<String>, index: &mut usize| -> Result<String, String> {
            if let Some(value) = inline.clone() {
                return Ok(value);
            }
            if *index < args.len() {
                *index += 1;
                Ok(args[*index - 1].clone())
            } else {
                Err(format!("`{flag}` necesita un valor"))
            }
        };
        match flag {
            "--git" => add.git = Some(value(&inline, &mut index)?),
            "--path" => add.path = Some(value(&inline, &mut index)?),
            "--tag" => add.tag = Some(value(&inline, &mut index)?),
            "--branch" => add.branch = Some(value(&inline, &mut index)?),
            "--rev" => add.rev = Some(value(&inline, &mut index)?),
            "--offline" | "--locked" | "--force" | "--refresh" | "-v" | "--verbose" => {}
            other if other.starts_with('-') && inline.is_none() => {
                return Err(format!("opción desconocida `{other}`"));
            }
            positional => {
                if add.name.is_some() {
                    return Err(format!("argumento inesperado `{positional}`"));
                }
                add.name = Some(positional.to_owned());
            }
        }
    }
    match (&add.git, &add.path) {
        (Some(_), Some(_)) => Err("`--git` y `--path` son incompatibles".to_owned()),
        (None, None) => Err("`pengu add` necesita `--git URL` o `--path RUTA`".to_owned()),
        _ => Ok(()),
    }?;
    let references = [&add.tag, &add.branch, &add.rev]
        .iter()
        .filter(|value| value.is_some())
        .count();
    if references > 1 {
        return Err("elige solo una de `--tag`, `--branch` o `--rev`".to_owned());
    }
    if add.path.is_some() && references > 0 {
        return Err("`--path` no admite `--tag`, `--branch` ni `--rev`".to_owned());
    }
    Ok(add)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_ok(args: &[&str]) -> Cli {
        let owned: Vec<String> = args.iter().map(|arg| (*arg).to_owned()).collect();
        parse(&owned).expect("parse")
    }

    fn parse_err(args: &[&str]) -> String {
        let owned: Vec<String> = args.iter().map(|arg| (*arg).to_owned()).collect();
        parse(&owned).expect_err("error")
    }

    #[test]
    fn comandos_simples() {
        assert_eq!(parse_ok(&["fetch"]).command, Command::Fetch);
        assert!(parse_ok(&["build", "--locked", "-v"]).locked);
        assert_eq!(parse_ok(&[]).command, Command::Help);
        assert_eq!(parse_ok(&["--version"]).command, Command::Version);
        assert_eq!(parse_ok(&["--help"]).command, Command::Help);
    }

    #[test]
    fn add_con_git_y_tag() {
        let cli = parse_ok(&["add", "--git", "https://x/y", "--tag", "v1"]);
        match cli.command {
            Command::Add(add) => {
                assert_eq!(add.git.as_deref(), Some("https://x/y"));
                assert_eq!(add.tag.as_deref(), Some("v1"));
                assert_eq!(add.name, None);
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn add_acepta_igual_y_nombre() {
        let cli = parse_ok(&["add", "text", "--git=https://x/text"]);
        match cli.command {
            Command::Add(add) => {
                assert_eq!(add.name.as_deref(), Some("text"));
                assert_eq!(add.git.as_deref(), Some("https://x/text"));
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn add_rechaza_fuentes_incompatibles() {
        assert!(parse_err(&["add", "--git", "u", "--path", "p"]).contains("incompatibles"));
        assert!(parse_err(&["add"]).contains("--git URL"));
        assert!(
            parse_err(&["add", "--git", "u", "--tag", "a", "--branch", "b"]).contains("solo una")
        );
        assert!(parse_err(&["add", "--path", "p", "--tag", "v1"]).contains("no admite"));
    }

    #[test]
    fn remove_y_update() {
        assert_eq!(
            parse_ok(&["remove", "text"]).command,
            Command::Remove(RemoveArgs {
                name: "text".to_owned()
            })
        );
        assert!(parse_err(&["remove"]).contains("necesita un nombre"));
        assert_eq!(
            parse_ok(&["update", "text"]).command,
            Command::Update(UpdateArgs {
                name: Some("text".to_owned())
            })
        );
        assert_eq!(
            parse_ok(&["update"]).command,
            Command::Update(UpdateArgs { name: None })
        );
    }

    #[test]
    fn rechaza_combinaciones_y_desconocidos() {
        assert!(parse_err(&["fetch", "--locked", "--force"]).contains("no se pueden combinar"));
        assert!(parse_err(&["frobnicate"]).contains("comando desconocido"));
        assert!(parse_err(&["build", "extra"]).contains("inesperado"));
    }
}
