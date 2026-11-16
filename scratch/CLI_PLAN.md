# CLI_PLAN.md — CLI de PenguScript

**Versión del plan:** `0.1.0`
**Estado:** planificación detallada; sin implementación
**Documento padre:** [`TOOLING_PLAN.md`](TOOLING_PLAN.md)
**Objetivo del producto:** un CLI `pengu` completo, rápido, predecible y auto-hospedable.

---

## Índice

1. [Resumen ejecutivo](#resumen)
2. [Alcance y principios](#alcance)
3. [Auto-hospedaje: la restricción que manda](#auto-hospedaje)
4. [Política de licencias y auditoría de dependencias](#licencias)
5. [Arquitectura del CLI](#arquitectura)
6. [Modelo de comandos y parser](#modelo)
7. [UX, salida y errores](#ux)
8. [Referencia de comandos](#comandos)
9. [Manifiesto, lock y configuración](#manifiesto)
10. [Paquetes git](#paquetes)
11. [Check, build, run y driver](#driver)
12. [LSP](#lsp)
13. [Bindgen](#bindgen)
14. [fmt, lint, fix, doc, test y bench](#calidad)
15. [Templates](#templates)
16. [Instalación y self-update](#instalacion)
17. [Diagnósticos y explain](#diagnosticos)
18. [Testing del CLI](#testing)
19. [Fases de implementación](#fases)
20. [Ruta de auto-hospedaje](#autohospedaje-ruta)
21. [Riesgos y mitigaciones](#riesgos)
22. [Criterios de aceptación](#aceptacion)
23. [Decisiones abiertas](#decisiones-abiertas)

Apéndices:

- [A. Matriz de comandos](#apendice-a)
- [B. Códigos de salida](#apendice-b)
- [C. Esquema JSON de salida](#apendice-c)
- [D. Huecos de stdlib para auto-hospedaje](#apendice-d)
- [E. Fuentes de licencias](#apendice-e)

---

<a id="resumen"></a>
## 1. Resumen ejecutivo

`pengu` es el único punto de entrada del ecosistema. No es un wrapper de Cargo ni un conjunto de scripts: es un **driver de compilación y proyecto** con contrato propio.

Decisiones centrales:

| # | Decisión | Razón |
|---|---|---|
| C1 | CLI escrito primero en Rust, pero diseñado como si ya fuera PenguScript | El auto-hospedaje no se improvisa al final |
| C2 | Sin `clap`, sin `miette`, sin `tower-lsp`, sin `salsa` en el núcleo | Frameworks con macros/async/proc-macros son difíciles de portar |
| C3 | Parser de argumentos propio, dirigido por una `CommandSpec` | Una sola fuente para ayuda, parseo, completions y man |
| C4 | Diagnósticos propios con span + código + ayuda | Control total del UX y del remapeo desde Rust |
| C5 | LSP síncrono sobre stdio con JSON-RPC propio | El lenguaje no tiene async; no queremos un runtime async en el compilador |
| C6 | Paquetes por git usando el ejecutable `git` como transporte | Evita enlazar libgit2/GPL; el protocolo se delega a una herramienta estándar |
| C7 | Bindgen contra `clang` como proceso, no contra libclang en el núcleo | Menos FFI, más portable, mismo resultado práctico |
| C8 | Formatos TOML/JSON con librerías pequeñas durante el bootstrap | Se sustituyen por `std.toml` y `std.json` cuando existan |
| C9 | `--json`/NDJSON como contrato estable para editores y CI | Automatización sin parsear texto humano |
| C10 | `pengu check` nunca invoca Cargo; `pengu build` es el único que compila Rust | Separación clara y errores de Rust siempre remapeados |

El CLI se implementa en 12 fases (C0–C11). La fase C0 no necesita compilador: entrega `pengu --help`, `pengu doctor`, `pengu new/init`, `pengu metadata` y el esqueleto de errores. Las fases C3–C5 conectan el compilador. C7–C8 conectan el LSP. C11 es el puente de auto-hospedaje.

---

<a id="alcance"></a>
## 2. Alcance y principios

### 2.1. Qué incluye

- Crear, inicializar, inspeccionar y mantener proyectos.
- Añadir/quitar/actualizar dependencias git y producir un lock reproducible.
- Ejecutar el checker semántico sin compilar Rust.
- Ejecutar el pipeline completo y llamar a `cargo`/`rustc` de forma controlada.
- Ejecutar tests, benchmarks, ejemplos y doc-tests.
- Formatear, lintar, aplicar fixes seguros y generar documentación.
- Generar bindings `.d.pengu` desde cabeceras C.
- Arrancar y mantener el servidor LSP.
- Diagnosticar el entorno, explicar códigos, generar completions y man pages.
- Actualizarse a sí mismo de forma verificable.

### 2.2. Qué no incluye (v1)

- Registry central propio; los paquetes son git.
- Publicación en un índice tipo crates.io.
- Build scripts de usuario.
- Macros de usuario.
- Async/await.
- Debugger DAP y REPL (fases posteriores; `debug`/`repl` reservados).
- Cross-compilación exótica más allá de lo que Cargo soporte.
- Empaquetado para todas las distros; sí scripts de instalación y binarios release.

### 2.3. Principios

1. **Un comando, una responsabilidad.** `check` no compila; `build` no adivina; `run` no reformatea.
2. **El proyecto es la fuente de verdad.** Flags > entorno > `Tome.toml` > config global.
3. **Nada de errores crudos del backend.** Todo error de `rustc` se mapea o se convierte en error interno con contexto.
4. **Salida humana por defecto, JSON cuando se pide.** El JSON no cambia entre versiones menores sin deprecación.
5. **Determinismo.** Misma entrada, mismo lock, mismo resultado; `--locked` debe fallar si algo cambió.
6. **Seguridad por defecto.** Sin hooks, sin build scripts, sin binarios precompilados, sin credenciales en logs.
7. **Rápido en el caso común.** `pengu check` incremental; arranque < 100 ms; sin red si no hace falta.
8. **Portable.** Linux, macOS y Windows; rutas y procesos encapsulados en `pengu-os`.
9. **Auto-hospedable.** Cada dependencia tiene un plan de reemplazo o un motivo documentado.
10. **El CLI es una API.** Scripts, CI y editores dependen de códigos, JSON y archivos, no de mensajes.

---

<a id="auto-hospedaje"></a>
## 3. Auto-hospedaje: la restricción que manda

### 3.1. Definición

Auto-hospedaje significa que una versión de PenguScript pueda compilar el compilador, el CLI, el LSP, el formatter y el package manager escritos en PenguScript, usando una versión anterior como bootstrap. Rust queda como backend de codegen y como `cargo`/`rustc` externos; no como lenguaje del producto.

No significa “que el código Rust se traduzca automáticamente”. Significa que el código nuevo se escribe en PenguScript y que las dependencias Rust del bootstrap tienen reemplazo.

### 3.2. Etapas

| Etapa | Compilador | CLI/LSP | Backend | Estado |
|---|---|---|---|---|
| H0 | Rust | Rust | `rustc` | Implementación inicial |
| H1 | Rust + stdlib PenguScript estable | Rust | `rustc` | Programas reales en PenguScript |
| H2 | Front-end en PenguScript, codegen en Rust | Rust | `rustc` | Hito de auto-hospedaje parcial |
| H3 | Compilador en PenguScript | PenguScript | `rustc` | Compilador auto-hospedado |
| H4 | Compilador en PenguScript | PenguScript | `rustc` | CLI/LSP auto-hospedados |
| H5 | Compilador en PenguScript | PenguScript | `rustc` | Bootstrap reproducible de dos etapas |

La meta del proyecto es H4; H5 es release de calidad.

### 3.3. Regla de dependencia

Toda dependencia del núcleo debe clasificarse en una de estas categorías:

| Clase | Significado | Permitida en núcleo |
|---|---|---|
| **P0 — portable directa** | Lógica pequeña, sin macros, sin C, sin async; se puede reescribir en PenguScript | Sí |
| **P1 — portable con esfuerzo** | API de datos, sin macros; requiere parser/estructura propia | Sí, con plan de reemplazo |
| **P2 — bootstrap temporal** | Útil ahora; se sustituye por stdlib o módulo propio antes de H3 | Sí, con issue y fecha límite |
| **P3 — externa opcional** | Se invoca como proceso, no se enlaza | Sí, si es opcional y está detrás de una interfaz |
| **P4 — no portable** | Macros pesadas, async runtime, C++ enorme, GPL/AGPL enlazada | No |

Regla práctica: si una librería obliga a usar `derive`, `async`, un runtime, o una API C++ en el núcleo, se rechaza o se aísla.

### 3.4. Implicaciones concretas

- **Sin `clap`:** parser propio. `clap` es excelente, pero su modelo derive y su superficie no se portan de forma razonable.
- **Sin `miette`/`ariadne`:** renderer propio. Los spans y el layout son parte del lenguaje, no de una librería.
- **Sin `tower-lsp`:** LSP síncrono. `tower-lsp` arrastra Tokio y `async-trait`; PenguScript no tiene async.
- **Sin hilos en el núcleo:** el lenguaje no expone hilos/atomics. El LSP se diseña como bucle de eventos cooperativo; si hace falta concurrencia, se usa un proceso worker, no `std::thread` en el código portable.
- **Sin `salsa`:** cache incremental propio con hashes y revisiones; menos magia y más control.
- **Sin `gix` en el núcleo:** se usa `git` como proceso para fetch/clone; el lock y la resolución son propios.
- **Sin `libclang` enlazado en el núcleo:** bindgen usa `clang` como proceso y JSON de AST; libclang queda como opción experimental.
- **Sin `regex`:** allowlists de bindgen con globs simples; el lenguaje no necesita regex en el compilador.
- **Con `toml` y `serde_json`:** son bootstrap P2; se reemplazan por `std.toml`/`std.json`.

### 3.5. Contrato de portabilidad

Cada crate del workspace debe declarar en `PORTABILITY.toml` (o en `Cargo.toml` metadata):

```toml
[portability]
tier = "P1"
self_host_blocker = false
replacement = "pengu-json"
notes = "Usa serde solo como runtime; sin derive en el core."
```

El CI falla si una dependencia nueva no tiene clasificación.

---

<a id="licencias"></a>
## 4. Política de licencias y auditoría de dependencias

### 4.1. Licencia del proyecto

La licencia de PenguScript aún no está fijada. Este plan asume **MIT OR Apache-2.0** para el código del compilador y del CLI, que es la combinación más interoperable con el ecosistema Rust. Si se elige otra, la allowlist se ajusta antes de la fase C0.

### 4.2. Allowlist

Aceptadas para código enlazado en el núcleo:

- MIT
- Apache-2.0
- BSD-2-Clause
- BSD-3-Clause
- ISC
- Zlib
- Unicode-3.0 (solo tablas de datos)
- CC0-1.0 / Unlicense (solo datos)

Rechazadas o requieren revisión legal explícita:

- GPL-2.0/3.0, AGPL, SSPL: no enlazadas.
- LGPL: solo enlace dinámico opcional, nunca en el núcleo.
- MPL-2.0: permitida solo si no se modifica el archivo cubierto; evitar en núcleo.
- Licencias custom o “source available”: prohibidas.
- Dependencias sin licencia declarada: prohibidas.

### 4.3. Dependencias enlazadas (bootstrap)

| Dependencia | Uso | Licencia esperada | Tier | Reemplazo / nota |
|---|---|---|---|---|
| `toml` | Leer `Tome.toml`, lock | MIT OR Apache-2.0 | P2 | `std.toml` |
| `serde_json` | LSP, metadata, JSON | MIT OR Apache-2.0 | P2 | `std.json` |
| `sha2` | Checksums del lock | MIT OR Apache-2.0 | P2 | `std.digest` (SHA-256) |
| `semver` | Versiones y resolución | MIT OR Apache-2.0 | P2 | `std.semver` |
| `tempfile` | Directorios temporales | MIT OR Apache-2.0 | P0 | `std.fs` |
| `walkdir` | Recorrido de árboles | MIT OR Unlicense | P0 | `std.fs.walk` |
| `dirs` | Config/cache del usuario | MIT OR Apache-2.0 | P0 | `std.env` |
| `which` | Descubrir `git`/`clang` | MIT | P0 | `std.process.which` |
| `unicode-width` | Ancho de diagnóstico | MIT OR Apache-2.0 | P0 | tablas UTF-8 |
| `libc` | FFI de SO puntual | MIT OR Apache-2.0 | P3 | `foreign "C"` |
| `windows-sys` | FFI Windows puntual | MIT OR Apache-2.0 | P3 | `foreign` |
| `ureq` | `self update` HTTP | MIT OR Apache-2.0 | P3 | `rete` (`std.net`) o `curl`/`git` |
| `zip` | Paquetes de release | MIT | P3 | `archivum` (`std.archive`) |
| `tar` | Paquetes de release | MIT OR Apache-2.0 | P3 | `archivum` (`std.archive`) |
| `flate2` | Compresión | MIT OR Apache-2.0 | P3 | `archivum` (`std.archive`, gzip nativo) |

### 4.4. Herramientas externas (no enlazadas)

| Herramienta | Uso | Licencia | Nota |
|---|---|---|---|
| `git` | transporte de paquetes | GPL-2.0 | proceso externo; no se distribuye con `pengu` |
| `rustc` | backend | MIT OR Apache-2.0 | toolchain externa |
| `cargo` | build backend | MIT OR Apache-2.0 | toolchain externa |
| `clang` | bindgen | Apache-2.0 WITH LLVM-exception | proceso externo; opcional |
| `libclang` | bindgen alternativo | Apache-2.0 WITH LLVM-exception | solo experimental, P4 |

Invocar un programa GPL no obliga a licenciar `pengu` bajo GPL; enlazar una librería GPL sí. Esta distinción se documenta y se prueba: el binario `pengu` no debe enlazar libgit2.

### 4.5. Rechazadas explícitamente

| Dependencia | Motivo |
|---|---|
| `clap` | parser/derive no auto-hospedable; reemplazo propio |
| `miette` / `ariadne` | renderer propio; menos dependencias y control de spans |
| `tower-lsp` | Tokio + async; el lenguaje no tiene async |
| `salsa` | macros y modelo incremental difícil de portar |
| `gix` | enorme; se usa `git` como proceso |
| `libgit2` | C + GPL con linking exception; evitar |
| `regex` | superficie innecesaria; globs propios |
| `serde_derive` | macros en el núcleo; solo `serde` runtime si hace falta |
| `thiserror` | derive; errores propios |
| `anyhow` | acceptable en CLI, pero no en el núcleo del compilador |

### 4.6. Gate de CI

- `cargo deny check licenses` con allowlist.
- `cargo deny check advisories`.
- `cargo about generate` para atribuciones.
- `cargo tree --duplicates` con revisión.
- `PORTABILITY.toml` obligatorio por crate.
- Revisión manual de toda dependencia nueva que use `build.rs`, `proc-macro`, C o async.

---

<a id="arquitectura"></a>
## 5. Arquitectura del CLI

### 5.1. Capas

```text
pengu (bin)
  └── pengu-cli          parser, help, completions, dispatch, output
        ├── pengu-driver    orquesta check/build/run/test
        ├── pengu-pkg       manifiesto, lock, git, cache
        ├── pengu-lsp       servidor LSP
        ├── pengu-bindgen   cabeceras C -> .d.pengu
        ├── pengu-fmt       formatter
        ├── pengu-lint      lints
        ├── pengu-doc       documentación
        ├── pengu-test     runner de tests
        └── pengu-diag      diagnóstico + render
              └── pengu-syntax / pengu-hir / pengu-types / pengu-check / pengu-lower / pengu-codegen
```

### 5.2. Crates y responsabilidades

| Crate | Responsabilidad | Depende de |
|---|---|---|
| `pengu-cli` | parser, spec, help, dispatch, exit codes | `pengu-driver`, `pengu-pkg` |
| `pengu-driver` | pipeline, perfiles, cache, invocación de Cargo | syntax/hir/types/check/lower/codegen |
| `pengu-syntax` | lexer, parser, AST, spans | `pengu-diag` |
| `pengu-hir` | resolución, nombres, scopes | syntax, diag |
| `pengu-types` | tipos, inferencia, checks | hir, diag |
| `pengu-check` | ownership, préstamos, exhaustividad | types, diag |
| `pengu-lower` | HIR -> IR de bajo nivel | check |
| `pengu-codegen` | IR -> Rust + sourcemap | lower, diag |
| `pengu-diag` | diagnósticos, spans, render, JSON | syntax (spans) |
| `pengu-pkg` | Tome, lock, git, cache, vendor | diag, fs |
| `pengu-lsp` | JSON-RPC, documentos, capabilities | driver, diag |
| `pengu-fmt` | formato determinista | syntax |
| `pengu-lint` | reglas y fixes | hir/types |
| `pengu-doc` | doc comments, HTML/Markdown | hir |
| `pengu-test` | discovery y ejecución | driver |
| `pengu-bindgen` | clang -> `.d.pengu` | pkg, diag |
| `pengu-vfs` | snapshots de archivos | — |
| `pengu-os` | paths, procesos, terminal | — |

### 5.3. Regla de dependencias

- `pengu-cli` no habla con `rustc` directamente; llama a `pengu-driver`.
- `pengu-check` no conoce Cargo.
- `pengu-codegen` no conoce el filesystem del proyecto; recibe un `BuildPlan`.
- `pengu-lsp` no renderiza diagnósticos humanos; usa JSON/diag.
- `pengu-pkg` no ejecuta builds.
- `pengu-fmt` y `pengu-lint` no modifican archivos sin `--write`/`fix`.

### 5.4. Flujo de un comando

```text
argv
  -> parser (CommandSpec)
  -> contexto global (cwd, config, color, offline)
  -> descubrir Tome.toml
  -> dispatch
  -> resultado (OutputEvent)
  -> render humano o JSON
  -> exit code
```

Todo comando devuelve un `CommandOutcome`:

```rust
struct CommandOutcome {
    code: ExitCode,
    events: Vec<OutputEvent>,
    artifacts: Vec<Artifact>,
    diagnostics: Vec<Diagnostic>,
}
```

---

<a id="modelo"></a>
## 6. Modelo de comandos y parser

### 6.1. `CommandSpec`

Una sola estructura describe el CLI. De ella salen el parser, la ayuda, las completions y el man.

```rust
struct CommandSpec {
    name: &'static str,
    about: &'static str,
    aliases: &'static [&'static str],
    subcommands: &'static [CommandSpec],
    args: &'static [ArgSpec],
    flags: &'static [FlagSpec],
    examples: &'static [&'static str],
    hidden: bool,
}

struct ArgSpec {
    name: &'static str,
    value_name: &'static str,
    required: bool,
    variadic: bool,
    default: Option<&'static str>,
    value_parser: ValueParser,
}

struct FlagSpec {
    long: &'static str,
    short: Option<char>,
    value: Option<ValueParser>,
    repeatable: bool,
    global: bool,
    conflicts: &'static [&'static str],
}
```

No hay `derive`; la spec es código Rust normal y se puede traducir a una tabla PenguScript.

### 6.2. Gramática de argumentos

```text
pengu [global-flags] <command> [command-flags] [positionals]
pengu help [command]
pengu <command> --help
```

Reglas:

- `--flag=value` y `--flag value` son equivalentes.
- `-v` repetible: `-vv`, `-vvv`.
- `--` termina el parseo; lo siguiente son argumentos posicionales/`run`.
- Un flag global puede ir antes o después del subcomando.
- Los subcomandos son la primera posición no-flag.
- `help` sin argumento muestra la ayuda raíz; `help build` muestra la de build.
- Sugerencia de comando/flags con distancia de edición ≤ 2.
- Error de uso: exit 2, mensaje breve, `pengu help` como salida.

### 6.3. Prioridad de configuración

```text
flags de línea de comandos
  > variables de entorno PENGU_*
  > [cli] de Tome.toml
  > config global (~/.config/pengu/config.toml)
  > defaults
```

### 6.4. Completions y man

- `pengu completions bash|zsh|fish|powershell|elvish` genera desde `CommandSpec`.
- `pengu man --out <dir>` genera `pengu.1` y `pengu-<cmd>.1`.
- Los nombres/valores se escapan; nada de scripts manuales duplicados.

### 6.5. Versionado del contrato

- `pengu --version` imprime `pengu 0.x.y (spec 0.6.0, rustc ...)`.
- `metadata.cli_schema = "pengu.cli.v1"`.
- Cambios incompatibles en JSON/flags suben `cli_schema` y requieren deprecación.

---

<a id="ux"></a>
## 7. UX, salida y errores

### 7.1. Salida humana

Ejemplo de `pengu check`:

```text
pengu check

  ✓ Tome.toml
  ✓ 12 archivos, 4 módulos
  ✓ tipos y préstamos

  error[PGS-E4105]: no se puede devolver una referencia a un valor local
    --> src/main.pengu:18:12
     |
  18 |     return &total
     |            ^^^^^^ el valor `total` vive en este frame
     |
     = ayuda: devuelve `total` por valor, o acepta `&mut` como parámetro
     = código: PGS-E4105 · pengu explain PGS-E4105

  1 error; 0 warnings
```

Reglas:

- Cabecera con comando y contexto, no ruido.
- Un bloque por diagnóstico; código siempre visible.
- Colores solo si TTY y `--color auto` (default).
- `--color never` y `NO_COLOR` respetados.
- Progreso solo en TTY; `--no-progress` lo apaga.
- `--quiet` muestra solo errores y resultado final.
- `--verbose` añade tiempos, rutas y comandos internos.
- Nunca imprimir rutas absolutas si `--relative-paths`.

### 7.2. Salida JSON

`--json` produce un único objeto al final:

```json
{
  "schema": "pengu.cli.v1",
  "command": "check",
  "ok": false,
  "exit_code": 3,
  "duration_ms": 412,
  "diagnostics": [
    {
      "code": "PGS-E4105",
      "severity": "error",
      "message": "no se puede devolver una referencia a un valor local",
      "file": "src/main.pengu",
      "span": { "start": 210, "end": 216, "line": 18, "column": 12 },
      "labels": [],
      "notes": [],
      "help": "devuelve `total` por valor"
    }
  ],
  "artifacts": []
}
```

`--message-format=ndjson` emite eventos:

```json
{"event":"start","command":"build"}
{"event":"diagnostic","code":"PGS-E4105", "...": "..."}
{"event":"artifact","kind":"binary","path":"target/pengu/debug/app"}
{"event":"end","ok":true,"exit_code":0}
```

### 7.3. Códigos de salida

| Código | Significado |
|---|---|
| 0 | Éxito |
| 1 | Fallo general |
| 2 | Uso incorrecto / flag inválido |
| 3 | Error de check (tipos, ownership, sintaxis) |
| 4 | Error de build (codegen/cargo/rustc remapeado) |
| 5 | Tests fallaron |
| 6 | Error de paquete/resolución/lock |
| 7 | Error de red/git |
| 8 | Error interno (panic controlado) |
| 9 | LSP no pudo arrancar |
| 10 | Bindgen falló |
| 130 | Interrumpido por SIGINT |

### 7.4. Errores del CLI

- `pengu` sin args: ayuda raíz + exit 0 (decisión amigable).
- Subcomando desconocido: sugerencia + exit 2.
- Flag desconocido: sugerencia + exit 2.
- Falta valor: muestra firma + exit 2.
- `--json` en error de uso: JSON con `ok:false`, no texto humano.
- Panic: el núcleo usa `Result` y evita panics; no se depende de `catch_unwind` (no es portable). En el bootstrap Rust puede existir un guard de último recurso que imprima `error interno` + ruta de log; el CLI auto-hospedado no lo necesita. Exit 8. En `--verbose`, backtrace solo en bootstrap.

### 7.5. Accesibilidad y CI

- `--no-color`, `NO_COLOR`, `CLICOLOR=0`.
- `--no-progress` automático si `CI=true`.
- `--yes` para no interactivo.
- Ningún prompt si `--json` o stdin no es TTY.
- Salida estable para snapshots.

### 7.6. Códigos propios del CLI

Además de los códigos del lenguaje (`PGS-E*`/`PGS-W*`), el CLI usa un namespace propio para errores de herramienta:

| Código | Significado |
|---|---|
| `PGS-CLI-001` | No se encontró `Tome.toml`. |
| `PGS-CLI-002` | El proyecto ya está inicializado. |
| `PGS-CLI-003` | Dependencia inexistente, duplicada o en conflicto. |
| `PGS-CLI-004` | No hay un target ejecutable. |
| `PGS-CLI-005` | Herramienta externa requerida no disponible (`git`, `clang`). |
| `PGS-CLI-006` | `Tome.toml` inválido para la operación. |
| `PGS-CLI-007` | `Tome.lock` desactualizado o inconsistente. |
| `PGS-CLI-008` | Error interno recuperable del CLI. |

Estos códigos se documentan en `pengu explain` y no sustituyen a los del compilador.

---

<a id="comandos"></a>
## 8. Referencia de comandos

Convenciones:

- `pengu <cmd> --help` es la fuente de verdad de flags.
- Todos aceptan `--json` salvo `lsp`.
- Todos aceptan `--manifest-path <path>`.
- `<path>` por defecto es `.`.

### 8.1. `pengu new`

Crea un proyecto nuevo.

```text
pengu new <path> [--name <name>] [--template <tpl>] [--vcs git|none]
                  [--no-git] [--force] [--yes]
```

- Falla si el directorio existe y no está vacío, salvo `--force`.
- `--name` debe ser un identificador válido; default: basename.
- `--template` default `bin`; valores `bin`, `lib`, `cli`, `ffi`, `wasm`, `test`.
- `--vcs git` inicializa repo y `.gitignore`; `none` no.
- No ejecuta hooks ni instala dependencias.
- Salida: árbol creado + `cd` sugerido.

### 8.2. `pengu init`

Inicializa un proyecto en un directorio existente.

```text
pengu init [path] [--name <name>] [--template <tpl>] [--vcs git|none] [--yes]
```

- No sobrescribe archivos existentes sin `--force`.
- Detecta si ya hay `Tome.toml`; error `PGS-CLI-002` si ya está inicializado.
- Crea `Tome.toml`, `src/main.pengu` o `src/lib.pengu`, `README.md`, `.gitignore`.
- `--template lib` crea `src/lib.pengu` y un test mínimo.

### 8.3. `pengu templates`

```text
pengu templates list [--json]
pengu templates show <name>
pengu templates apply <name> [--path <dir>] [--force]
```

- Lista templates locales y remotos.
- `show` imprime el árbol y los archivos.
- `apply` copia; no ejecuta código.
- Templates remotos: `gh:owner/repo@tag`, `git+https://...#rev`; siempre pinneados.

### 8.4. `pengu add`

Añade una dependencia git o local.

```text
pengu add <name> --git <url> [--tag <tag>|--branch <branch>|--rev <rev>]
                    [--subdir <dir>] [--features <a,b>]
                    [--no-default-features] [--optional]
pengu add <name> --path <dir>
```

- Actualiza `Tome.toml` y `Tome.lock`.
- Verifica que el repo tenga `Tome.toml` en la raíz o en `--subdir`.
- No ejecuta build scripts (no existen).
- Si no se da `tag`/`branch`/`rev`, elige el tag SemVer más alto; si no hay tags, `branch = "main"` con advertencia.
- Falla si el nombre ya existe con otra fuente; `PGS-CLI-003`.
- Salida: versión/commit resueltos y cambios.

### 8.5. `pengu remove`

```text
pengu remove <name>
```

- Elimina la entrada del manifiesto y actualiza lock.
- Si hay dependencias transitivas huérfanas, las elimina.
- Error si el nombre no existe (`PGS-CLI-003`).

### 8.6. `pengu update`

```text
pengu update [name...] [--precise <rev>] [--dry-run]
```

- Sin args: re-resuelve `tag`/`branch` al commit actual; no mueve `rev` ni dependencias path.
- `--precise`: fija un commit exacto.
- `--dry-run`: muestra cambios sin escribir.
- Nunca actualiza una dependencia fijada por `rev` salvo `--precise`.
- `--locked` en `build/check` no actualiza.

### 8.7. `pengu tree`

```text
pengu tree [--depth <n>] [--invert] [--duplicates] [--json]
```

- Árbol de dependencias resuelto.
- `--duplicates` lista nombres/fuentes duplicados en el grafo.
- No ejecuta red; usa lock.

### 8.8. `pengu fetch`

```text
pengu fetch [--offline] [--locked]
```

- Descarga las fuentes del lock a la caché.
- Idempotente.
- `--offline` falla si falta algo.

### 8.9. `pengu vendor`

```text
pengu vendor [--output <dir>] [--no-delete]
```

- Copia las fuentes del lock a `vendor/`.
- Escribe `vendor/.pengu-vendor.toml` con hashes.
- `--no-delete` no borra archivos existentes.
- Build/check usan vendor si existe y `--offline`.

### 8.10. `pengu outdated`

```text
pengu outdated [--json]
```

- Compara lock con tags/ramas permitidas.
- No modifica nada.
- Requiere red; `--offline` error.

### 8.11. `pengu check`

```text
pengu check [paths...] [--all-targets] [--features <a,b>]
                   [--no-default-features] [--deny <warn|all>]
                   [--message-format human|short|json|ndjson]
                   [--timings] [--json]
```

- Carga manifiesto, resuelve features, parsea, resuelve nombres, infiere tipos, verifica ownership, lints.
- **No invoca Cargo.**
- No escribe binarios; sí cache de check.
- `--all-targets`: lib, bins, tests, examples.
- `--deny warnings`: warnings -> error (exit 3).
- `--timings`: tabla por fase.
- Códigos: 0 ok, 3 diagnóstico, 6 manifiesto/lock.
- Si no hay `Tome.toml`: `PGS-CLI-001`.

### 8.12. `pengu build`

```text
pengu build [--release] [--target <triple>] [--features <a,b>]
                   [--no-default-features] [--bin <name>] [--lib]
                   [--examples] [--workspace] [--jobs <n>]
                   [--keep-rust] [--timings] [--json]
```

- Ejecuta check; si falla, no llama a Cargo.
- Genera Rust en `target/pengu/rust/` (o `--keep-rust`).
- Invoca `cargo build` con `Cargo.toml` generado.
- Remapea diagnósticos de rustc a spans PenguScript.
- `--release` usa perfil release.
- `--target` pasa el triple; cross según toolchain.
- Artefactos en `target/pengu/<profile>/`.
- Nunca muestra errores crudos de Rust; si no hay span, `PGS-E2014` + nota interna.

### 8.13. `pengu run`

```text
pengu run [--release] [--bin <name>] [--example <name>]
                 [--features <a,b>] [--] [args...]
```

- Build del binario y ejecución con args, env y cwd actual.
- `--` separa args de PenguScript.
- Exit code del programa, salvo error de build (4).
- `--bin` y `--example` excluyentes.
- Sin binario: `PGS-CLI-004`.

### 8.14. `pengu test`

```text
pengu test [filter] [--doc] [--no-run] [--ignored] [--include-ignored]
                  [--nocapture] [--test-threads <n>]
                  [--features <a,b>] [--coverage] [--json]
```

- Descubre `@@test` y tests de integración.
- `--doc` ejecuta doc-tests.
- `--no-run` compila sin ejecutar.
- `--ignored` solo ignorados; `--include-ignored` ambos.
- `--coverage` requiere `llvm-cov` (fase posterior).
- Exit 5 si falla un test.
- Salida humana: `ok/FAILED`, duración, resumen.

### 8.15. `pengu bench`

```text
pengu bench [filter] [--no-run] [--features <a,b>] [--json]
```

- Benchmarks nativos; no usa Criterion en runtime.
- `--no-run` compila.
- Reporte estable; comparación con baseline en fase posterior.

### 8.16. `pengu clean`

```text
pengu clean [--target] [--cache] [--all] [--dry-run]
```

- `--target`: `target/pengu/`.
- `--cache`: caché de check/build.
- `--all`: ambos + caché de paquetes.
- Nunca borra `~/.cache/pengu/git` sin `--all` explícito.

### 8.17. `pengu watch`

```text
pengu watch [--clear] [--exec <cmd>] [--check|--test|--run]
```

- Observa `src/`, `tests/`, `examples/`, `Tome.toml`.
- Debounce 150 ms.
- `--clear` limpia pantalla.
- `--exec` ejecuta un comando tras éxito.
- Fase C9; no en v1 mínima.

### 8.18. `pengu fmt`

```text
pengu fmt [paths...] [--check] [--diff] [--all] [--stdin]
```

- Formato determinista; sin configuración por proyecto en v1.
- `--check` no escribe; exit 1 si hay cambios.
- `--diff` muestra diff unificado.
- `--stdin` lee de stdin y escribe a stdout.
- No formatea `target/` ni `vendor/`.

### 8.19. `pengu lint`

```text
pengu lint [paths...] [--deny <warn|all>] [--json]
```

- Lints semánticos y de estilo.
- `--deny warnings` convierte warnings en errores.
- No aplica fixes; eso es `pengu fix`.
- Códigos `PGS-Wxxxx`.

### 8.20. `pengu fix`

```text
pengu fix [paths...] [--allow-dirty] [--dry-run] [--check]
```

- Solo fixes seguros y marcados.
- `--dry-run` muestra diff.
- `--check` exit 1 si quedarían cambios.
- Rechaza si el árbol git está sucio sin `--allow-dirty`.

### 8.21. `pengu doc`

```text
pengu doc [--open] [--no-deps] [--private] [--out <dir>]
```

- Genera HTML estático desde `---`.
- `--open` abre el índice.
- No ejecuta doc-tests; eso es `pengu test --doc`.

### 8.22. `pengu bindgen`

```text
pengu bindgen <header.h> [--output <file.d.pengu>]
                         [--abi C|system]
                         [--allowlist <glob>] [--blocklist <glob>]
                         [--link <name>] [--clang-arg <arg>]
                         [--no-default-includes] [--json]
```

- Requiere `clang` en PATH o `--clang`.
- Genera `.d.pengu` con `abi "C"` / `abi "system"`.
- Mapea tipos C a primitivos, `Ptr[T]`, `Str`, `CStr`.
- No genera exports.
- `--allowlist`/`--blocklist` con globs.
- `--link` añade `[link]` al manifiesto.
- Falla con `PGS-CLI-005` si clang no está.

### 8.23. `pengu lsp`

```text
pengu lsp [--stdio] [--socket <addr>] [--log <file>]
                 [--log-level <error|warn|info|debug|trace>]
                 [--worker]   # interno; modo proceso de análisis
```

- Default `--stdio`.
- Nunca escribe logs a stdout.
- `--socket` para debugging; no producción.
- Exit 9 si no puede iniciar.

### 8.24. `pengu doctor`

```text
pengu doctor [--json]
```

Comprueba:

- versión de `pengu`, `rustc`, `cargo`, `git`, `clang`.
- `Tome.toml` válido.
- lock consistente.
- cache escribible.
- PATH.
- targets instalados.
- conectividad git (opcional; `--offline` no).

Salida con `✓/! /✗` y remedios.

### 8.25. `pengu explain`

```text
pengu explain <code>
```

- Explica un código (`PGS-E4105`) con causa, ejemplo y solución.
- Fuente: catálogo §20 de `LANGUAGE.md`; se genera `explanations.json` en build.
- Código desconocido: exit 2.

### 8.26. `pengu metadata`

```text
pengu metadata [--format json|toml] [--no-deps]
```

- Salida estable para herramientas: nombre, versión, targets, features, deps, lock, root.
- No ejecuta red.

### 8.27. `pengu completions` y `pengu man`

```text
pengu completions <bash|zsh|fish|powershell|elvish>
pengu man [--out <dir>]
```

- Generados desde `CommandSpec`.
- Incluyen subcomandos, flags y valores enumerados.

### 8.28. `pengu self update`

```text
pengu self update [--check] [--version <v>] [--force] [--channel stable|beta]
```

- Verifica checksum y firma si está disponible.
- No actualiza si el binario es de un package manager del sistema (`PENGU_MANAGED=1`).
- `--check` solo informa.
- Rollback: conserva el binario anterior.

### 8.29. `pengu debug` y `pengu repl` (reservados)

- No en v1.
- `debug` será DAP; `repl` evaluará con el mismo checker.
- No se anuncian como estables.

---

<a id="manifiesto"></a>
## 9. Manifiesto, lock y configuración

### 9.1. `Tome.toml`

```toml
[tome]
name = "app"
version = "0.1.0"
pengu = "0.6"
edition = "2024"

[dependencies]
json = { git = "https://github.com/pengu/json", tag = "v1.2.0" }
local = { path = "../local" }

[features]
default = ["json"]
http = []

[[bin]]
name = "app"
path = "src/main.pengu"

[[lib]]
name = "app"
path = "src/lib.pengu"

[link]
m = { lib = "m", kind = "system" }

[declarations]
libc = "libc.d.pengu"
```

Reglas:

- `[tome]` obligatorio: `name`, `version`, `pengu`, `edition`.
- `pengu` es un rango compatible con el compilador.
- No hay `[build-dependencies]` en v1.
- `path` siempre relativo a la raíz.
- Nombres en snake_case; binarios pueden tener guiones.
- `[[lib]]` máximo uno.
- `[link]` solo para `foreign`/`.d.pengu` con `abi "C"`/`"system"`.
- `[declarations]` lista `.d.pengu` que no generan código.

### 9.2. `Tome.lock`

```toml
version = 1

[[package]]
name = "json"
version = "0.3.1"
source = "git+https://github.com/pengu/json?tag=v1.2.0"
commit = "9f1c..."
checksum = "sha256-..."
features = ["std"]
dependencies = ["text"]
```

- Ordenado por nombre.
- `commit` obligatorio para git.
- `checksum` SHA-256 del árbol empaquetado.
- `source` canónico.
- El lock no se edita a mano; `pengu update` lo reescribe.

### 9.3. Configuración global

`~/.config/pengu/config.toml`:

```toml
[cli]
color = "auto"
jobs = 0
progress = "auto"

[git]
protocol = "https"

[build]
target-dir = "target/pengu"
```

- `PENGU_COLOR`, `PENGU_JOBS`, `PENGU_OFFLINE`, `PENGU_LOG`.
- `PENGU_MANAGED=1` bloquea `self update`.
- `NO_COLOR` y `CI` respetados.

---

<a id="paquetes"></a>
## 10. Paquetes git

### 10.1. Specs

```text
gh:owner/repo
gh:owner/repo@v1.2.0
git+https://example.com/repo.git#rev
ssh://git@example.com/repo.git@main
file:///srv/repo
```

- `gh:` se expande a `https://github.com/owner/repo.git`.
- `@tag`/`#rev` son excluyentes.
- `?path=sub/dir` selecciona subdirectorio.
- Sin registry central.

### 10.2. Resolución

- Un commit por paquete; no hay rangos SemVer de dependencias ni SAT.
- `tag`/`branch` se resuelven a su commit actual; `rev` queda fijo.
- Features se unen (unión).
- Conflicto por nombre, fuente o features -> `PGS-E1807`.
- Ref git ausente/inválido -> `PGS-E1806`.
- Lock inválido -> `PGS-E1808`.
- `--locked` falla si el lock no coincide.
- `--offline` no toca red.

### 10.3. Caché

```text
~/.cache/pengu/
  git/db/<hash>.git      # bare
  git/checkouts/<hash>/  # árbol de trabajo
  pkg/<name>-<commit>/   # extraído verificado
```

- Lock por archivo para concurrencia.
- Limpieza por LRU; `pengu clean --cache`.
- Nunca se confía en el checkout para checksum; se verifica el árbol.

### 10.4. Seguridad

- Sin hooks, sin submódulos automáticos, sin LFS automático.
- `git` se invoca con `--no-prompt` si no hay TTY; credenciales vía helper.
- URLs con credenciales se rechazan en `Tome.toml`.
- Warn si branch móvil; error en `--locked` si el commit cambió.
- Vendor con hashes; build offline.

### 10.5. `git` como dependencia externa

- `pengu` no enlaza libgit2.
- `pengu doctor` verifica `git >= 2.30`.
- Si falta `git`, `pengu add/fetch/update` fallan con remedio; `build` con vendor/lock puede seguir.
- Windows: Git for Windows; se detecta `git.exe`.

---

<a id="driver"></a>
## 11. Check, build, run y driver

### 11.1. Pipeline

```text
manifest -> resolve -> features -> load VFS
  -> lex -> parse -> HIR -> resolve -> types -> ownership -> lints
  -> [check termina aquí]
  -> lower -> Rust -> Cargo.toml -> cargo -> rustc
  -> remap diagnostics -> artifacts
```

### 11.2. Incrementalidad

- Cache por archivo y por query.
- Claves: hash de contenido, versión del compilador, features, target.
- Sin `salsa`: `QueryKey` + `Revision` + `DashMap`-like propia.
- `pengu check` reutiliza cache entre runs.
- `pengu clean --cache` invalida.

### 11.3. Codegen

- Un archivo `.pengu` -> un `.rs` con `//@ sourcemap`.
- `sourcemap.json` mapea spans generados a PenguScript.
- `Cargo.toml` generado en `target/pengu/rust/`.
- `Cargo.lock` generado; no se versiona.
- `rustfmt` sobre Rust generado.
- `--keep-rust` conserva el árbol.

### 11.4. Remapeo

- rustc JSON (`--message-format=json`) -> `Diagnostic`.
- Si hay span mapeado: diagnóstico PenguScript con código original.
- Si no: `PGS-E2014` con nota “error interno del backend” y archivo Rust.
- Nunca mostrar `error[E0xxx]` de Rust como diagnóstico principal.

### 11.5. Perfiles

- `dev`: opt-level 0, debug true, overflow checks true.
- `release`: opt-level 3, lto thin, panic unwind.
- `test`: como dev.
- `bench`: release + debug false.
- `--profile` custom en `Tome.toml`? v1 solo los cuatro.

### 11.6. Variables de entorno

- `PENGU_TARGET_DIR`, `PENGU_OFFLINE`, `PENGU_LOCKED`, `PENGU_LOG`.
- `RUSTC`, `CARGO` respetados pero validados.
- `PENGU_KEEP_RUST=1`.

---

<a id="lsp"></a>
## 12. LSP

### 12.1. Arquitectura

```text
stdin/stdout
  <-> JSON-RPC framing (Content-Length) en un solo hilo
  <-> cola de requests/notificaciones
  <-> scheduler cooperativo de análisis
  <-> VFS + compiler queries
  <-> writer (mismo hilo) -> responses/notifications
```

- Sin Tokio, sin async, **sin hilos en el núcleo**.
- El bucle lee, encola, procesa un paso acotado y escribe; las operaciones largas se dividen en incrementos.
- Cancelación por `$/cancelRequest`: se marca la request y el scheduler la abandona entre pasos.
- Si la latencia no alcanza, se usa un **proceso worker** (`pengu lsp --worker`) con pipes JSON; el proceso principal sigue siendo single-threaded. No se usan hilos del lenguaje.
- Un documento se analiza con snapshot inmutable.
- Diagnósticos push tras cambios (debounce 250 ms).

### 12.2. Capabilities v1

- `textDocumentSync`: incremental.
- `publishDiagnostics`.
- `hover`.
- `completion` + `resolve`.
- `signatureHelp`.
- `definition`.
- `references`.
- `documentSymbol`.
- `workspaceSymbol`.
- `rename` + `prepareRename`.
- `formatting` + `rangeFormatting`.
- `codeAction` (fixes seguros).
- `semanticTokens` (fase posterior).
- `inlayHint` (fase posterior).
- `foldingRange`, `selectionRange`.
- `callHierarchy` (fase posterior).

### 12.3. Rendimiento

| Operación | Objetivo |
|---|---|
| arranque | < 150 ms |
| keystroke (warm) | < 50 ms |
| diagnóstico full | < 2 s / 100k LOC |
| completion | < 100 ms |
| hover | < 50 ms |
| rename | < 500 ms / 100 archivos |

### 12.4. Protocolo

- `initialize` devuelve `serverInfo` con versión de `pengu` y `spec`.
- `shutdown`/`exit` correctos.
- `workspace/didChangeConfiguration` recarga config.
- `window/logMessage` para logs; nunca stdout crudo.
- `--log` escribe a archivo; `--log-level`.

### 12.5. Testing LSP

- Golden tests de JSON-RPC.
- `lsp-server`-style harness propio.
- Corpus de proyectos; snapshots de diagnostics/hover/completion.
- Test de cancelación y de cierre limpio.
- Fuzz de framing.

---

<a id="bindgen"></a>
## 13. Bindgen

### 13.1. Flujo

```text
header.h
  -> clang -Xclang -ast-dump=json -fsyntax-only
  -> filtro allow/block
  -> modelo C
  -> mapeo a tipos PenguScript
  -> .d.pengu + [link]
```

- `clang` externo; no libclang enlazado.
- Si `clang` no está: `PGS-CLI-005`.
- `--abi C` default; `--abi system` para libs del sistema.

### 13.2. Mapeo

| C | PenguScript |
|---|---|
| `int` | `I32` |
| `unsigned` | `U32` |
| `long` | `Isize`/`I64` según target |
| `char*` | `Ptr[U8]` o `CStr` en contexto |
| `void*` | `Ptr[Unit]` |
| `struct` opaco | `rune Name` + `Ptr[Name]` |
| `enum` | `enchanting` con `@@repr` |
| función | `foreign "C"` |

- Sin exports.
- Sin callbacks automáticos en v1; función puntero -> `Ptr`.
- `--allowlist`/`--blocklist` globs.
- `--link` escribe `[link]`.
- `--json` reporta símbolos y omisiones.

### 13.3. Testing

- Corpus: libc, zlib, sqlite3 (solo cabeceras), una lib propia.
- Snapshot `.d.pengu`.
- Compilar el `.d.pengu` con `pengu check`.
- Test de ABI/layout con `sizeof` verificado por C.

---

<a id="calidad"></a>
## 14. fmt, lint, fix, doc, test y bench

### 14.1. fmt

- 4 espacios, sin tabs.
- Ancho 100; una expresión por línea si excede.
- Comentarios preservados.
- `--check` para CI.
- Idempotente: `fmt(fmt(x)) == fmt(x)`.

### 14.2. lint

- Reglas con código `PGS-Wxxxx`.
- Niveles: allow/warn/deny.
- `@@allow`/`@@deny` no existen como atributos generales; la configuración va en `Tome.toml`:

```toml
[lint]
deny = ["unused_binding"]
allow = ["shadowing"]
```

- `pengu lint --deny warnings`.

### 14.3. fix

- Solo fixes marcados `safe`.
- No toca archivos fuera del proyecto.
- `--dry-run`, `--check`.
- Rechaza árbol sucio sin `--allow-dirty`.

### 14.4. doc

- `---` y `--!`.
- HTML estático + búsqueda.
- `--private` incluye items privados.
- Enlaces cruzados validados.

### 14.5. test

- `@@test`.
- `@@test(should_panic: "...")`.
- `@@test(ignore: "...")`.
- Tests de integración en `tests/*.pengu`.
- Doc-tests.
- `--coverage` fase posterior.

### 14.6. bench

- Ejecuta `@@test` en release con warmup y repeticiones; mide tiempo, no es un benchmark estadístico.
- No hay `@@bench` en 0.6.0 (solo `@@test`).
- Runner propio; no Criterion en runtime.
- Reporte JSON estable.

---

<a id="templates"></a>
## 15. Templates

### 15.1. Built-in

| Template | Contenido |
|---|---|
| `bin` | `Tome.toml`, `src/main.pengu`, `tests/smoke.pengu`, `.gitignore` |
| `lib` | `Tome.toml`, `src/lib.pengu`, `tests/lib.pengu` |
| `cli` | `bin` + `src/cli.pengu` + parseo de args mínimo |
| `ffi` | `Tome.toml` con `[link]`, `src/lib.pengu`, `.d.pengu` de ejemplo |
| `wasm` | `Tome.toml`, target wasm, `src/lib.pengu` |
| `test` | proyecto mínimo con un test |

### 15.2. Contrato

- Sin hooks.
- Sin dependencias por defecto.
- `README.md` con comandos.
- `.gitignore` con `target/`, `vendor/` opcional.
- `pengu new` no ejecuta `git commit`.

### 15.3. Remotos

- `gh:owner/repo@tag`.
- Se descarga a temp, se valida `Tome.toml` y se copia.
- Nunca se ejecuta código del template.
- `--force` requerido para sobrescribir.

---

<a id="instalacion"></a>
## 16. Instalación y self-update

### 16.1. Instalación

- `scripts/install.sh` (Linux/macOS): detecta target, descarga release, verifica SHA-256, instala en `~/.local/bin` o `/usr/local/bin` con `--prefix`.
- `scripts/install.ps1` (Windows): descarga zip, verifica, añade al PATH de usuario.
- `scripts/build.sh`: build release + tests + empaquetado.
- `pengu doctor` comprueba PATH.

### 16.2. PATH

- `install.sh --add-path` escribe el bloque en shell rc solo con confirmación.
- Windows: `setx PATH` o registro de usuario; nunca sistema sin admin.
- `pengu doctor` detecta si el binario no está en PATH.

### 16.3. Releases

- Targets: `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu`, `x86_64-apple-darwin`, `aarch64-apple-darwin`, `x86_64-pc-windows-msvc`.
- Artefactos: `pengu-<version>-<target>.tar.gz`/`.zip`, `.sha256`, `.sig` (minisign).
- SBOM CycloneDX.
- `pengu --version` incluye commit.

### 16.4. self update

- `pengu self update --check`.
- Descarga, verifica checksum/firma, reemplaza atómicamente, conserva `.old`.
- Si `PENGU_MANAGED=1`, no actualiza.
- Rollback manual: `pengu self update --rollback` (fase posterior).

---

<a id="diagnosticos"></a>
## 17. Diagnósticos y explain

### 17.1. Modelo

```rust
struct Diagnostic {
    code: &'static str,       // PGS-E4105
    severity: Severity,
    message: String,
    span: Option<Span>,
    labels: Vec<Label>,
    notes: Vec<String>,
    help: Option<String>,
}
```

- Código siempre presente.
- Span con archivo, línea, columna, offset.
- Labels múltiples.
- `help` accionable, no genérico.
- `notes` para contexto.

### 17.2. Render

- Cabecera `error[PGS-E4105]: ...`.
- Línea de código con `^` y labels.
- `= ayuda: ...`
- `= código: ... · pengu explain ...`
- Ancho de terminal; `unicode-width`.
- Sin tabs; expandir a 4 espacios.

### 17.3. JSON

- Mismo esquema que §7.2.
- `severity`: `error|warning|note|help`.
- Offsets en bytes UTF-8.

### 17.4. explain

- `pengu explain PGS-E4105`.
- Salida:

```text
PGS-E4105 — referencia a valor local

Causa: ...
Ejemplo: ...
Solución: ...
Ver: LANGUAGE.md §11.6
```

- Generado desde `LANGUAGE.md` §20; no duplicar a mano.

---

<a id="testing"></a>
## 18. Testing del CLI

### 18.1. Unitarios

- Parser: cada flag, alias, conflicto, `--`, valores repetidos.
- Spec: ayuda generada, completions, man.
- Config: precedencia.
- Output: JSON schema, colores, quiet.
- Errores: exit codes.

### 18.2. Integración

- Proyectos fixture en `tests/fixtures/`.
- `assert_cmd` + `predicates` + `insta` (solo dev).
- Cada comando: éxito, error, JSON, `--help`.
- `pengu new` -> `check` -> `build` -> `run` en CI.
- Git local con `file://`; sin red.
- `self update` con servidor local.

### 18.3. Snapshot

- `insta` para ayuda, diagnósticos, JSON.
- Nombres estables; no incluir rutas absolutas.
- Revisión humana de cada snapshot.

### 18.4. Matriz

| Nivel | Qué prueba |
|---|---|
| unit | parser, config, render |
| integration | comandos contra fixtures |
| e2e | proyecto real + git local + cargo |
| lsp | JSON-RPC golden |
| bindgen | cabeceras + snapshot |
| cross | Linux/macOS/Windows |

### 18.5. CI

- Linux, macOS, Windows.
- `cargo fmt --check`, `clippy -D warnings`, `cargo deny`, `cargo test`.
- `pengu` build propio (dogfood) cuando exista.
- Bench de arranque.

---

<a id="fases"></a>
## 19. Fases de implementación

### C0 — Esqueleto y contrato

- `pengu-cli` con `CommandSpec`, parser, help, `--version`, `doctor`, `metadata`.
- Render humano/JSON base.
- Exit codes.
- Tests de parser y snapshots.
- Sin compilador.

**Salida:** `pengu --help` funciona; `doctor` detecta toolchain; `metadata` lee un `Tome.toml` mínimo.

### C1 — Proyectos y templates

- `new`, `init`, `templates`.
- Escritura segura de archivos.
- `Tome.toml` mínimo.
- `doctor` valida proyecto.

**Salida:** proyecto creado, `pengu check` da “compilador no instalado” controlado.

### C2 — Paquetes git

- `add`, `remove`, `update`, `tree`, `fetch`, `vendor`, `outdated`.
- Lock, cache, resolución.
- Git local `file://` en tests.

**Salida:** dependencia git añadida y lock reproducible.

### C3 — Checker

- `check` conectado a syntax/hir/types/check.
- Diagnósticos, JSON, `--deny`.
- Cache incremental.

**Salida:** proyecto real chequeado sin Cargo.

### C4 — Build/run/clean

- `build`, `run`, `clean`.
- Codegen + Cargo + remapeo.
- Perfiles.

**Salida:** binario ejecutable.

### C5 — Tests/bench/watch

- `test`, `bench`, `watch`.
- Discovery `@@test`.
- Runner.

**Salida:** suite de tests ejecutada.

### C6 — Calidad

- `fmt`, `lint`, `fix`, `doc`.
- Config de lint.
- Snapshots.

**Salida:** CI de formato/lint/docs.

### C7 — Bindgen

- `bindgen` con clang.
- Corpus libc.
- `.d.pengu` + `[link]`.

**Salida:** binding de libc compila.

### C8 — LSP base

- `lsp` stdio, framing, diagnostics, hover, completion, definition.
- Harness de tests.

**Salida:** VS Code muestra diagnósticos.

### C9 — LSP avanzado

- references, rename, formatting, code actions, symbols.
- Cancelación, performance.

**Salida:** experiencia comparable a rust-analyzer en el subconjunto.

### C10 — Distribución

- `completions`, `man`, `self update`, instaladores.
- Releases multiplataforma.

**Salida:** instalación en máquina limpia.

### C11 — Puente de auto-hospedaje

- Extraer `CommandSpec` a formato portátil.
- Reemplazar `toml`/`serde_json` por `std.toml`/`std.json`.
- Portar parser y `doctor` a PenguScript.
- Bootstrap de dos etapas.

**Salida:** `pengu` compilado por PenguScript ejecuta `--help` y `check`.

---

<a id="autohospedaje-ruta"></a>
## 20. Ruta de auto-hospedaje

### 20.1. Orden de port

1. `pengu-diag` (render + JSON) — no depende del compilador.
2. `pengu-cli-spec`/parser.
3. `pengu-pkg` (TOML, git process).
4. `pengu-check` (front-end).
5. `pengu-codegen` (emite Rust).
6. `pengu-lsp` (JSON-RPC).
7. `pengu-fmt`/`lint`.
8. `pengu-bindgen`.

### 20.2. Superficie de stdlib requerida

Antes de H3, PenguScript necesita estas APIs; todas están mapeadas en `docs/STDLIB.md` `0.3.0`:

- `std.toml` (`libra`): parser/encoder.
- `std.json` (`iason`): parser/encoder.
- `std.digest` (`digestum`): SHA-256/512 y checksums.
- `std.semver` (`versio`): versiones y requisitos.
- `std.fs.walk` (`via.walk`): recorrido recursivo.
- `std.process` (`exsecutor`): spawn, pipes, exit, `which`.
- `std.term` (`terminus`): color, ancho, raw mode.
- `std.glob` (`globus`): patrones.
- `std.archive` (`archivum`): tar/tar.gz/zip para self-update.
- `std.net`/TLS (`rete`): TCP/UDP/TLS/HTTP/1.1, o delegación a `curl`/`git`.

### 20.3. Reglas de código

- Sin `derive` en el núcleo.
- Sin `async`.
- Sin hilos/atomics/canales en el núcleo; proceso worker si hace falta concurrencia.
- Sin `dyn` en APIs públicas del CLI.
- Sin `Rc`/`Arc` en el parser.
- Sin `regex`.
- Sin `clap`.
- Errores como enums propios.
- Strings UTF-8; paths como `PathBuf`.

### 20.4. Bootstrap

```text
pengu-rust (N) -> compila pengu.pengu (N+1) -> compila pengu.pengu (N+2)
```

- H5 exige que N+1 y N+2 sean idénticos byte a byte.
- Se guarda el binario N para reproducibilidad.
- `scripts/bootstrap.sh` automatiza.

### 20.5. Criterio de “no bloqueante”

Una dependencia es no bloqueante si:

- tiene reemplazo en stdlib o módulo propio;
- su API usada es pequeña y documentada;
- no obliga a macros/async en el núcleo;
- su licencia está en allowlist.

Si no cumple, no entra al núcleo.

---

<a id="riesgos"></a>
## 21. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Parser propio incompleto | UX pobre | Spec + tests + completions desde el día 1 |
| LSP síncrono lento | Mala experiencia | Snapshots, cache, worker, debounce |
| `git` externo falta | Paquetes no funcionan | `doctor`, vendor, mensaje claro |
| `clang` falta | Bindgen no funciona | `doctor`, `--clang`, error accionable |
| Formatos TOML/JSON propios incompletos | Bloqueo H3 | Empezar `std.toml`/`std.json` en H2 |
| Deriva Rust/PenguScript | Dos CLIs | `CommandSpec` única; tests de contrato |
| Errores de rustc sin span | Mala UX | `PGS-E2014` + `--keep-rust` + nota |
| Licencias | Bloqueo legal | `cargo deny`, allowlist, revisión |
| Complejidad de bindgen | Retraso | clang JSON + allowlist; no libclang |
| Windows paths/procesos | Bugs | `pengu-os`, CI Windows |

---

<a id="aceptacion"></a>
## 22. Criterios de aceptación

### 22.1. CLI

- Todos los comandos de §8 existen con `--help`.
- Parser acepta flags antes/después del subcomando, `--`, `-vv`, `--flag=value`.
- `pengu --json` cumple `pengu.cli.v1`.
- Exit codes de §7.3.
- `pengu doctor` en máquina limpia da remedios correctos.
- `pengu new` + `pengu check` + `pengu build` + `pengu run` funcionan en Linux/macOS/Windows.

### 22.2. Auto-hospedaje

- `PORTABILITY.toml` por crate.
- `cargo deny` verde.
- Ningún crate del núcleo usa `clap`, `tower-lsp`, `salsa`, `miette`, `regex` o `libgit2`.
- `std.toml`, `std.json`, `std.digest`, `std.semver` existen antes de H3.
- Bootstrap H5 reproducible.

### 22.3. UX

- Diagnóstico con código, span, ayuda y `explain`.
- Colores solo TTY; `NO_COLOR`.
- Progreso solo TTY; CI silencioso.
- Sin errores crudos de Rust.

### 22.4. Testing

- Cobertura de parser > 90%.
- Snapshot de ayuda/comandos.
- E2E de proyecto + git local.
- LSP golden tests.
- Bindgen corpus.

---

<a id="decisiones-abiertas"></a>
## 23. Decisiones abiertas

| # | Pregunta | Recomendación |
|---|---|---|
| D1 | ¿Licencia del proyecto MIT/Apache-2.0? | Sí, antes de C0 |
| D2 | ¿Parser propio o `clap` bootstrap? | Propio; `CommandSpec` desde el inicio |
| D3 | ¿`toml`/`serde_json` bootstrap o propios ya? | Bootstrap P2; stdlib en H2 |
| D4 | ¿LSP síncrono o async? | Síncrono; el lenguaje no tiene async |
| D5 | ¿Bindgen con libclang o clang CLI? | clang CLI/JSON |
| D6 | ¿`git` CLI o `gix`? | git CLI; `gix` opcional futuro |
| D7 | ¿`self update` con `ureq` o downloader externo? | `ureq` P3; fallback `curl`/PowerShell |
| D8 | ¿`debug`/`repl` en v1? | No; reservados |
| D9 | ¿Workspaces en v1? | Sí, lectura; escritura fase posterior |
| D10 | ¿Registry central? | No; git |

---

<a id="apendice-a"></a>
## Apéndice A — Matriz de comandos

| Comando | Fase | Código |
|---|---|---|
| `new` | C1 | 0/2 |
| `init` | C1 | 0/2 |
| `templates` | C1 | 0/2 |
| `add` | C2 | 0/6/7 |
| `remove` | C2 | 0/6 |
| `update` | C2 | 0/6/7 |
| `tree` | C2 | 0/6 |
| `fetch` | C2 | 0/6/7 |
| `vendor` | C2 | 0/6 |
| `outdated` | C2 | 0/6/7 |
| `check` | C3 | 0/3/6 |
| `build` | C4 | 0/3/4/6 |
| `run` | C4 | 0/3/4 |
| `clean` | C4 | 0 |
| `test` | C5 | 0/3/5 |
| `bench` | C5 | 0/3/5 |
| `watch` | C5 | 0/3/4 |
| `fmt` | C6 | 0/1 |
| `lint` | C6 | 0/3 |
| `fix` | C6 | 0/1/3 |
| `doc` | C6 | 0/3 |
| `bindgen` | C7 | 0/10 |
| `lsp` | C8 | 0/9 |
| `doctor` | C0 | 0/1 |
| `explain` | C0 | 0/2 |
| `metadata` | C0 | 0/6 |
| `completions` | C10 | 0/2 |
| `man` | C10 | 0/2 |
| `self update` | C10 | 0/1/7 |

---

<a id="apendice-b"></a>
## Apéndice B — Códigos de salida

Ver §7.3. Regla: un comando solo usa los códigos de su fila; no inventa códigos nuevos sin actualizar este apéndice.

---

<a id="apendice-c"></a>
## Apéndice C — Esquema JSON de salida

```json
{
  "$schema": "https://penguscript.dev/schemas/cli-v1.json",
  "schema": "pengu.cli.v1",
  "command": "string",
  "ok": true,
  "exit_code": 0,
  "duration_ms": 0,
  "diagnostics": [],
  "artifacts": [],
  "data": {}
}
```

Reglas:

- `diagnostics` siempre array.
- `artifacts` con `kind` (`binary`, `lib`, `doc`, `binding`, `lock`), `path`.
- `data` específico del comando; no rompe el esquema base.
- NDJSON: un evento por línea, `event` obligatorio.

---

<a id="apendice-d"></a>
## Apéndice D — Cobertura de stdlib para auto-hospedaje

La superficie está especificada en [`docs/STDLIB.md`](../docs/STDLIB.md) `0.3.0`; la implementación sigue el orden H1–H4.

| Módulo | Uso | Módulo de STDLIB | Estado |
|---|---|---|---|
| `std.toml` | Tome/lock/config | `libra` | Superficie completa |
| `std.json` | LSP, metadata, JSON | `iason` | Superficie completa |
| `std.digest` | checksums | `digestum` | Superficie completa (SHA-256/512, HMAC) |
| `std.semver` | versiones | `versio` | Superficie completa |
| `std.fs.walk` | discovery | `via.walk` | Superficie completa |
| `std.process` | git/clang/cargo | `exsecutor` | Superficie completa |
| `std.term` | color, ancho | `terminus` | Superficie completa (ANSI + plataforma) |
| `std.glob` | allowlist bindgen | `globus` | Superficie completa |
| `std.archive` | releases/self-update | `archivum` | Superficie completa (tar/tar.gz/zip) |
| `std.net`/TLS | self-update | `rete` | Superficie completa (TCP/UDP/TLS/HTTP/1.1) |

Mientras la implementación no exista, el bootstrap puede usar las dependencias P2/P3 de §4.

---

<a id="apendice-e"></a>
## Apéndice E — Fuentes de licencias

- crates.io metadata: <https://crates.io/>
- SPDX License List: <https://spdx.org/licenses/>
- `cargo-deny`: <https://github.com/EmbarkStudios/cargo-deny>
- `cargo-about`: <https://github.com/EmbarkStudios/cargo-about>
- LLVM license: <https://llvm.org/LICENSE.txt>
- Git license: <https://git-scm.com/about/free-and-open-source>

La tabla de §4.3 es una auditoría inicial; la versión exacta se fija en `Cargo.lock` y se revalida con `cargo deny` en cada PR.

---

## Nota final

Este documento es el contrato del CLI, no una implementación. La regla que decide cualquier discusión futura es simple:

> Si una librería o diseño no puede ser reemplazado o portado sin reescribir el producto, no pertenece al núcleo.

El siguiente paso es implementar C0: `CommandSpec`, parser, `doctor`, `metadata`, salida JSON y tests. Después C1 (proyectos/templates) y C2 (paquetes git), antes de tocar el compilador.
