# Plan maestro de tooling — CLI, compilador y LSP

**Proyecto:** PenguScript-Rust  
**Documento:** plan de implementación del toolchain completo  
**Versión:** `0.1`  
**Fecha:** 2026-11-12  
**Estado:** planificación; no hay implementación todavía  
**Alcance:** `pengu` CLI, compilador/checker, LSP, extensión de VS Code, bindgen, paquetes git, templates, ejemplos, scripts de instalación y release.

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Producto y principios](#2-producto-y-principios)
3. [Arquitectura del toolchain](#3-arquitectura-del-toolchain)
4. [Flujo de compilación](#4-flujo-de-compilación)
5. [CLI `pengu`](#5-cli-pengu)
6. [Templates y `pengu new`](#6-templates-y-pengu-new)
7. [Paquetes git y `pengu add`](#7-paquetes-git-y-pengu-add)
8. [Bindgen de cabeceras](#8-bindgen-de-cabeceras)
9. [LSP](#9-lsp)
10. [Extensión de VS Code](#10-extensión-de-vs-code)
11. [Ejemplos, conformidad y QA](#11-ejemplos-conformidad-y-qa)
12. [Instalación, scripts y release](#12-instalación-scripts-y-release)
13. [Fases de implementación](#13-fases-de-implementación)
14. [Documentos detallados por área](#14-documentos-detallados-por-área)
15. [Riesgos y decisiones abiertas](#15-riesgos-y-decisiones-abiertas)
16. [Criterios de aceptación globales](#16-criterios-de-aceptación-globales)
17. [Anexos](#17-anexos)

---

<a id="1-resumen-ejecutivo"></a>
## 1. Resumen ejecutivo

PenguScript necesita una experiencia de desarrollo que no obligue al usuario a pensar en Rust. El compilador es el producto principal: si `pengu check` acepta un programa, ese programa debe compilar y ejecutarse; si hay un error, el usuario debe ver un diagnóstico de PenguScript con código, causa y solución, nunca un error crudo de `rustc`.

El toolchain se construye en cuatro capas:

1. **CLI `pengu`**: la puerta de entrada. Debe ser rápida, predecible, bonita y completa: crear, añadir dependencias, compilar, ejecutar, testear, formatear, documentar, generar bindings y lanzar el LSP.
2. **Compilador/checker**: front-end propio (léxico, parser, resolución, tipos, ownership) y backend Rust invisible. El checker es la autoridad de aceptación; Rust es el verificador final y el generador de código máquina.
3. **LSP**: servidor semántico incremental con la calidad de rust-analyzer/clangd/pyright: diagnósticos, autocompletado, hover, definición, referencias, rename, acciones, hints, semantic tokens y navegación.
4. **Ecosistema**: templates, paquetes git (sin registry propio), bindgen de C, extensión de VS Code, ejemplos ejecutables y scripts de instalación/release.

La regla de oro:

> El usuario escribe PenguScript, piensa en PenguScript y depura en PenguScript. Rust es un detalle de implementación del backend.

El plan se ejecuta en **12 fases** (0–11). Cada fase termina con un entregable ejecutable, tests y un documento detallado propio.

---

<a id="2-producto-y-principios"></a>
## 2. Producto y principios

### 2.1 Promesa al usuario

- Un único binario, `pengu`, para todo el ciclo de vida.
- Un proyecto se crea con `pengu new` y se ejecuta con `pengu run`.
- `pengu check` es rápido y exhaustivo; `pengu build` no muestra errores de Rust no mapeados.
- El LSP funciona en un proyecto abierto y en un archivo `.pengu` suelto.
- Las dependencias se declaran por Git; no hay registry central ni cuentas.
- Los templates hacen que `new` produzca algo que compila y se ejecuta desde el primer minuto.

### 2.2 Principios de diseño

1. **Checker primero, backend después.** Ningún error de tipos, ownership o FFI debe llegar a `rustc` sin diagnóstico PenguScript.
2. **Un solo camino de compilación.** `check`, la CLI, el LSP y los tests usan el mismo driver y el mismo checker; no hay dos interpretaciones de la semántica.
3. **Diagnósticos accionables.** Todo error tiene código estable (`PGS-Exxxx`), span, mensaje, causa y, cuando aplica, sugerencia automática.
4. **Incrementalidad real.** El LSP y `pengu check --watch` reanalizan solo lo afectado; la caché se comparte entre CLI y LSP.
5. **Determinismo.** Mismo código, mismas dependencias, mismo lock y misma versión de `pengu` producen el mismo Rust y el mismo binario lógico.
6. **Offline-first.** `--offline` y `--locked` deben funcionar; la red solo se usa para resolver o actualizar.
7. **Cross-platform.** Linux, macOS y Windows son ciudadanos de primera clase; no hay rutas POSIX asumidas.
8. **Seguridad por defecto.** Dependencias git fijadas por commit/checksum; bindgen no ejecuta código de la cabecera; FFI explícita y auditada.
9. **Extensible sin magia oculta.** Templates, bindgen y paquetes tienen formatos documentados y validables.
10. **Rendimiento visible.** Tiempos de arranque, check y LSP medidos y publicados; no se acepta una regresión silenciosa.

### 2.3 No objetivos de la primera versión

- Registry propio de paquetes.
- Publicación automática a un marketplace.
- Debugger gráfico completo (se planifica como fase posterior).
- Soporte de todos los targets exóticos de Rust.
- Compatibilidad con Cargo como interfaz de usuario.
- Extensión para todos los editores; VS Code primero, protocolo LSP estándar después.

---

<a id="3-arquitectura-del-toolchain"></a>
## 3. Arquitectura del toolchain

### 3.1 Workspace propuesto

```text
PenguScript-Rust/
├── Cargo.toml                 # workspace
├── crates/
│   ├── pengu-cli/             # binario `pengu`, parsing de comandos, UX
│   ├── pengu-driver/          # orquestación: check/build/run/test
│   ├── pengu-syntax/          # lexer, tokens, parser, AST, spans
│   ├── pengu-hir/             # resolución, módulos, items, scopes
│   ├── pengu-types/           # tipos, inferencia, pacts, constraints
│   ├── pengu-check/           # checker semántico y de ownership
│   ├── pengu-lower/           # HIR -> IR de bajo nivel y desugaring
│   ├── pengu-codegen/         # IR -> Rust + Cargo + sourcemap
│   ├── pengu-diag/            # diagnóstico, códigos, render, JSON
│   ├── pengu-pkg/             # Tome.toml, Tome.lock, git deps
│   ├── pengu-bindgen/         # cabeceras C -> .d.pengu
│   ├── pengu-lsp/             # servidor LSP
│   ├── pengu-fmt/             # formatter
│   ├── pengu-lint/            # lints y code actions
│   ├── pengu-doc/             # documentación y doc tests
│   ├── pengu-test/            # runner de tests y ejemplos
│   └── pengu-vfs/             # VFS compartida CLI/LSP
├── editors/
│   └── vscode/
├── templates/
├── examples/
├── scripts/
├── docs/
└── scratch/
```

No es obligatorio crear todos los crates el día uno. La separación existe para que el LSP pueda depender del análisis sin arrastrar la CLI, y para que el checker sea testeable sin invocar `cargo`.

### 3.2 Capas

```text
                 ┌─────────────────────────────┐
                 │ pengu-cli / pengu-lsp / API │
                 └──────────────┬──────────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │        pengu-driver         │
                 │  load → parse → resolve →   │
                 │  check → lower → codegen    │
                 └──────────────┬──────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
│  front-end  │          │   checker   │          │   backend   │
│ syntax/HIR  │          │ types/own   │          │ lower/rust  │
└─────────────┘          └─────────────┘          └─────────────┘
```

### 3.3 Decisiones técnicas recomendadas

| Área | Recomendación | Motivo |
|---|---|---|
| CLI | `clap` derive + `miette`/`ariadne` | ayuda consistente, errores bonitos, completions |
| Git | `gix` (o `git2` si `gix` no cubre) | Sin shell-out, portable, cacheable |
| TOML | `toml` + `toml_edit` | leer y preservar formato al editar `Tome.toml` |
| LSP | `tower-lsp` o `async-lsp` | JSON-RPC, cancellation, lifecycle |
| Incremental | Salsa-like propio o `salsa` | consultas memoizadas para LSP |
| Bindgen | `clang` CLI + AST JSON | sin enlazar libclang; portable y auto-hospedable |
| Formatter | `prettyplease` conceptual + reglas propias | preservar indentación PenguScript |
| Tests | `insta` (snapshots) + `proptest`/`arbitrary` | diagnósticos y parser |
| Benchmarks | `criterion` | medir check/LSP/build |
| VS Code | TypeScript + `vscode-languageclient` | estándar y mantenible |

> **Revisión de auto-hospedaje:** [`CLI_PLAN.md`](CLI_PLAN.md) §3–§4 revisa estas recomendaciones. Para el núcleo se descartan `clap`, `miette`, `tower-lsp`, `salsa` y `gix`; se usan parser, diagnósticos, LSP síncrono y cache propios, y `git`/`clang` como procesos externos. Las razones son licencias, portabilidad a PenguScript y ausencia de macros/async en el lenguaje.

### 3.4 Cache y artefactos

```text
target/pengu/
├── analysis/          # caché incremental del checker
├── gen/               # Rust generado por crate
├── build/             # Cargo target del proyecto
├── bindgen/           # salidas de bindgen
└── metadata.json      # versión, hashes, targets
```

La caché debe ser segura ante cambios de versión del compilador: una versión distinta invalida la caché.

---

<a id="4-flujo-de-compilación"></a>
## 4. Flujo de compilación

### 4.1 Pipeline

1. **Cargar proyecto.** Leer `Tome.toml`, resolver `Tome.lock`, construir el grafo de módulos y el VFS.
2. **Lexer.** UTF-8, indentación, comentarios, literales, tokens; errores léxicos recuperables.
3. **Parser.** AST con spans; recuperación de errores para que el LSP siga funcionando.
4. **Resolución.** Módulos, imports, namespaces de tipos/valores, `scroll`, `summon`, `unveil`, `.d.pengu`.
5. **Checker.** Tipos, inferencia local, pacts, genéricos, patrones, retornos, exhaustividad, ownership/borrowing, FFI, const eval.
6. **Lowering.** HIR -> IR explícito: moves, drops, préstamos, monomorfización, desugaring de expresiones.
7. **Codegen.** Rust + `Cargo.toml` + `sourcemap.json`; nombres estables; rustfmt.
8. **Backend.** `cargo build`/`cargo test`; mapear diagnósticos de `rustc` a spans PenguScript.
9. **Empaquetado.** Ejecutable, librería o artefacto solicitado; reporte de tiempos y artefactos.

### 4.2 Regla de aceptación

`pengu check` debe ejecutar 1–6 sin invocar `cargo`. `pengu build` ejecuta 1–8. Si `check` acepta y `build` falla por un error no mapeado, es un bug de prioridad alta del compilador.

### 4.3 Diagnósticos

- Códigos estables por familia: `PGS-E1xxx` léxico, `E2xxx` programa, `E3xxx` tipos, `E4xxx` ownership, `E5xxx` FFI, etc.
- Severidad: error, warning, hint.
- Sugerencias con edits de texto (para `pengu fix` y code actions).
- Salida humana y `--message-format=json`.
- `pengu explain E4109` muestra la regla completa.
- Nunca mostrar rutas internas de `target/pengu` salvo en `--verbose`.

### 4.4 Source maps

`sourcemap.json` asocia cada span Rust generado con:

- archivo `.pengu`, línea y columna;
- item lógico (rune, función, expresión);
- rango original;
- tipo de mapeo (`item`, `expr`, `type`, `ffi`).

Los diagnósticos de `rustc` se remapean por span; si no hay mapeo, se asocian al item contenedor y se marca `PGS-E2014`.

### 4.5 Incrementalidad

- El driver expone consultas puras: `parse(file)`, `resolve(module)`, `check(item)`, `lower(item)`, `codegen(item)`.
- El LSP usa un `AnalysisHost` con snapshots inmutables y cancelación por request.
- `pengu check --watch` reutiliza la misma caché en disco.
- Cambios en `Tome.toml` invalidan el grafo de módulos completo.

---

<a id="5-cli-pengu"></a>
## 5. CLI `pengu`

### 5.1 Principios de UX

- **Descubrible:** `pengu --help` agrupado por tareas, no una lista alfabética.
- **Seguro:** comandos destructivos piden confirmación salvo `--yes`.
- **Consistente:** todos los comandos aceptan `--json`, `--quiet`, `--verbose`, `--color`, `--offline`, `--locked` cuando aplica.
- **Rápido:** arranque < 50 ms; `pengu check` incremental < 100 ms para cambios pequeños.
- **Bonito:** progreso con `indicatif`, colores solo en TTY, resumen final claro.
- **Scriptable:** códigos de salida estables y JSON documentado.

### 5.2 Flags globales

```text
pengu [GLOBAL] <COMMAND>

GLOBAL:
  -v, --verbose              más detalle (repetible)
  -q, --quiet                solo errores
      --color <auto|always|never>
      --no-color
      --json                 salida machine-readable
      --offline              no acceder a la red
      --locked               fallar si Tome.lock no está al día
      --config <PATH>        configuración de usuario
  -h, --help
  -V, --version
```

### 5.3 Comandos completos

#### Proyecto

| Comando | Descripción | Fase |
|---|---|---|
| `pengu new <name>` | Crea proyecto ejecutable. | 1 |
| `pengu new <name> --lib` | Crea librería. | 1 |
| `pengu new <name> --template <t>` | Usa template embebido o git. | 1 |
| `pengu init` | Inicializa en directorio existente. | 1 |
| `pengu templates` | Lista templates disponibles. | 1 |
| `pengu metadata` | Información del proyecto en JSON. | 1 |

#### Dependencias

| Comando | Descripción | Fase |
|---|---|---|
| `pengu add <spec>` | Añade dependencia git. | 5 |
| `pengu remove <name>` | Quita dependencia. | 5 |
| `pengu update [name]` | Actualiza lock/dependencias. | 5 |
| `pengu tree` | Árbol de dependencias. | 5 |
| `pengu fetch` | Descarga sin compilar. | 5 |
| `pengu vendor` | Copia dependencias a `vendor/`. | 5 |
| `pengu outdated` | Compara con tags remotos (opcional, red). | 5 |

Specs de `add`:

```text
gh:owner/repo
gh:owner/repo@v1.2.3
gh:owner/repo#<commit>
git+https://host/repo.git@v1.2.3
git+ssh://git@host/repo.git#<rev>
./local/path
```

Flags: `--rev`, `--tag`, `--branch`, `--name`, `--subdir`, `--features`, `--no-default-features`, `--optional`.

#### Build y ejecución

| Comando | Descripción | Fase |
|---|---|---|
| `pengu check [path]` | Solo checker; rápido. | 3 |
| `pengu build` | Compila ejecutable/librería. | 4 |
| `pengu run [-- args]` | Compila y ejecuta. | 4 |
| `pengu run script.pengu` | Ejecuta un archivo suelto. | 4 |
| `pengu test` | Tests del proyecto. | 4/8 |
| `pengu bench` | Benchmarks. | 8 |
| `pengu clean` | Limpia artefactos. | 1 |
| `pengu watch` | Re-ejecuta check/test/run al cambiar. | 4 |

Flags de build: `--release`, `--target`, `--lib`, `--bin`, `--all-targets`, `--jobs`, `--timings`, `--emit`, `--message-format`, `--target-dir`, `--deny warnings`, `--allow warnings`.

#### Calidad

| Comando | Descripción | Fase |
|---|---|---|
| `pengu fmt` | Formatea. | 8 |
| `pengu fmt --check` | Verifica formato. | 8 |
| `pengu lint` | Lints. | 8 |
| `pengu fix` | Aplica sugerencias seguras. | 8 |
| `pengu doc` | Genera documentación. | 8 |
| `pengu doc --open` | Abre docs. | 8 |
| `pengu explain <code>` | Explica un diagnóstico. | 8 |

#### FFI y bindgen

| Comando | Descripción | Fase |
|---|---|---|
| `pengu bindgen <header>` | Genera `.d.pengu`. | 9 |
| `pengu bindgen --check` | Verifica que el binding está al día. | 9 |
| `pengu bindgen --allow <regex>` | Allowlist. | 9 |
| `pengu bindgen --link <lib>` | Añade `[link]`. | 9 |

#### LSP y editor

| Comando | Descripción | Fase |
|---|---|---|
| `pengu lsp` | Servidor LSP por stdio. | 6 |
| `pengu lsp --tcp <addr>` | Servidor TCP (debug). | 6 |
| `pengu lsp --log <file>` | Log de protocolo. | 6 |
| `pengu completions <shell>` | Completions. | 1 |
| `pengu man` | Man page. | 11 |

#### Diagnóstico y mantenimiento

| Comando | Descripción | Fase |
|---|---|---|
| `pengu doctor` | Chequea toolchain, Rust, git, clang, PATH. | 1 |
| `pengu self update` | Actualiza `pengu` (si hay release). | 11 |
| `pengu version` | Versión + commit + rustc. | 1 |
| `pengu debug` | DAP/debugger (futuro). | 11+ |
| `pengu repl` | REPL (futuro). | 11+ |

### 5.4 Códigos de salida

| Código | Significado |
|---|---|
| 0 | Éxito. |
| 1 | Error de compilación/check. |
| 2 | Uso inválido de CLI. |
| 3 | Error de configuración/manifest. |
| 4 | Error de red/git. |
| 5 | Error de toolchain externo (rustc/cargo/clang). |
| 6 | Fallo de test/bench. |
| 7 | Cancelado por el usuario. |

### 5.5 Configuración

Precedencia: flags > variables `PENGU_*` > `Tome.toml` > `~/.config/pengu/config.toml` > defaults.

Configuración de usuario:

```toml
[cli]
color = "auto"
jobs = 0
telemetry = false

[lsp]
inlay_hints = true
semantic_tokens = true

[build]
target_dir = "target/pengu"
```

No hay telemetría por defecto.

---

<a id="6-templates-y-pengu-new"></a>
## 6. Templates y `pengu new`

### 6.1 Templates embebidos

| Template | Uso | Contenido |
|---|---|---|
| `bin` | Ejecutable mínimo | `Tome.toml`, `src/main.pengu`, `grimoire`. |
| `lib` | Librería | `src/lib.pengu`, un `rune` y un test. |
| `cli` | CLI de ejemplo | parseo simple de args, `Result`, tests. |
| `ffi` | FFI C | `.d.pengu`, `foreign`, ejemplo `curse`. |
| `wasm` | WASM | target wasm, export mínimo. |
| `test` | Solo tests | `src/lib.pengu`, `tests/`. |

`pengu new --template list` o `pengu templates` muestra la tabla.

### 6.2 Template remoto

```text
pengu new myapp --template gh:owner/pengu-template-cli@v1
```

Reglas:

- El template debe tener `template.toml` con `name`, `version`, `description`, `variables`.
- Variables: `{{name}}`, `{{crate_name}}`, `{{author}}`, `{{year}}`, `{{description}}`.
- Archivos binarios se copian tal cual; no se ejecuta código del template.
- `--no-git` evita `git init`; por defecto se inicializa repo si está disponible.
- `pengu new` falla si el directorio no está vacío, salvo `--force`.

### 6.3 `pengu init`

- Detecta si ya hay `Tome.toml`; no lo sobrescribe.
- Pregunta template si es interactivo; en CI usa `--template`.
- Crea `.gitignore`, `README.md`, `src/`, `examples/`, `tests/`.

---

<a id="7-paquetes-git-y-pengu-add"></a>
## 7. Paquetes git y `pengu add`

### 7.1 Modelo

No hay registry. Una dependencia es un repositorio Git con un `Tome.toml` válido. La identidad es `name` del manifest; el origen es la URL/commit.

```toml
[dependencies]
geom = { git = "https://github.com/acme/geom", tag = "v1.2.0" }
texto = { git = "https://gitlab.com/acme/texto", rev = "9f3c2a1" }
local = { path = "../local" }
```

Forma compacta aceptada por la CLI:

```text
gh:acme/geom@v1.2.0
```

Se normaliza a la forma larga al escribir `Tome.toml`.

### 7.2 Resolución

1. Leer dependencias directas.
2. Resolver cada git spec a un commit concreto (tag/rev/branch).
3. Leer el `Tome.toml` de esa revisión.
4. Resolver dependencias transitivas.
5. Fijar **un commit por nombre**; si dos fuentes o features chocan, error `PGS-E1807`.
6. Escribir `Tome.lock` ordenado con commit, checksum del árbol y features.
7. Cachear en `~/.cache/pengu/git/<host>/<owner>/<repo>/<commit>/`.

No se implementa SAT ni rangos SemVer de dependencias: un commit por paquete y un ref explícito. Es predecible y suficiente para v1.

### 7.3 `Tome.lock`

```toml
version = 1

[[package]]
name = "geom"
version = "1.2.0"
source = "git+https://github.com/acme/geom?rev=9f3c2a1"
checksum = "sha256:..."
features = ["std"]
dependencies = ["vector"]
```

- Ordenado por nombre.
- `checksum` es el hash del árbol/contenido, no del commit solamente.
- `--locked` falla si el lock no coincide.
- `--offline` usa solo la caché; si falta, error claro.

### 7.4 Comandos

- `pengu add` valida que el repo tenga `Tome.toml` y que el nombre no colisione.
- `pengu remove` limpia del manifest, lock y caché opcional.
- `pengu update` re-resuelve; `update <name>` solo esa dependencia.
- `pengu tree` muestra el grafo y las features activas.
- `pengu vendor` copia a `vendor/` y reescribe el lock para builds offline/herméticos.

### 7.5 Seguridad

- No se ejecuta `build.pengu` de una dependencia sin consentimiento explícito.
- Los builds de dependencias no tienen scripts por defecto.
- `pengu add` muestra commit y URL antes de escribir.
- `pengu audit` (fase posterior) puede comparar contra avisos, pero no hay registry.

---

<a id="8-bindgen-de-cabeceras"></a>
## 8. Bindgen de cabeceras

### 8.1 Objetivo

Convertir una cabecera C en un `.d.pengu` seguro y compilable, sin que el usuario escriba `extern "C"` ni traduzca tipos a mano.

```text
pengu bindgen include/foo.h \
  --out src/foo.d.pengu \
  --abi C \
  --allow 'foo_.*' \
  --block 'foo_internal_.*' \
  --link m
```

### 8.2 Pipeline

1. Parsear flags y validar que `clang` existe.
2. Ejecutar clang con `-Xclang -ast-dump=json`; no enlazar `clang-sys` en el núcleo.
3. Recoger funciones, structs, enums, typedefs, constantes y variables.
4. Filtrar por allowlist/blocklist.
5. Mapear tipos C -> tipos PenguScript (`Int`, `UInt`, `Float`, `Ptr[T]`, `CStr`, `rune` con `@@repr(C)`).
6. Emitir `.d.pengu` con `abi "C"`, comentarios de origen y `[link]` si aplica.
7. Validar con el checker (`pengu check` sobre un proyecto temporal).
8. Reportar símbolos omitidos y por qué.

### 8.3 Reglas

- `Ptr[T]` solo en la frontera; nunca se guarda en un `rune` normal.
- Structs por valor: `@@repr(C)` y campos públicos.
- Unions: se omiten o se marcan como opacas; el lenguaje no tiene `union` de usuario.
- Function pointers: se mapean solo si el lenguaje los soporta en ese punto; si no, se omite con diagnóstico.
- Macros: solo constantes numéricas/string simples; el resto se reporta como no soportado.
- `--check` compara el archivo generado con el actual y falla si difiere.
- El binding generado no se edita a mano; se regenera.

### 8.4 Calidad

- Corpus con cabeceras reales: `zlib`, `libpng`, `sqlite3`, `raylib`, `ncurses`.
- Tests de layout (`size_of`/`align_of`) contra C.
- Tests de llamada FFI en Linux/macOS/Windows.
- Mensajes claros para tipos no soportados.

---

<a id="9-lsp"></a>
## 9. LSP

### 9.1 Objetivo de calidad

Un servidor que se sienta como rust-analyzer/clangd/pyright:

- diagnósticos al escribir, sin guardar;
- autocompletado contextual y rápido;
- hover con tipos y docs;
- go to definition/type/implementation;
- find references y rename seguro;
- code actions y quick fixes;
- inlay hints de tipos y parámetros;
- semantic tokens;
- signature help;
- document/workspace symbols;
- call hierarchy;
- folding/selection ranges;
- code lens para tests;
- formatting;
- organización de imports.

### 9.2 Arquitectura

```text
VS Code / editor
      │ JSON-RPC (stdio)
      ▼
pengu-lsp
  ├── lifecycle / capabilities
  ├── document sync (incremental)
  ├── VFS + AnalysisHost (snapshots)
  ├── request handlers con cancelación
  ├── diagnósticos push/pull
  └── formatting / code actions
      │
      ▼
pengu-driver (mismas consultas que la CLI)
```

- `AnalysisHost` mantiene el estado mutable; cada request toma un snapshot inmutable.
- La cancelación de `$/cancelRequest` se propaga al checker.
- Los diagnósticos se debouncean (p. ej. 150 ms) y se publican por documento.
- El servidor funciona con un archivo suelto: crea un proyecto virtual en memoria.
- Multi-root workspace: un `AnalysisHost` por carpeta, con cache compartida.

### 9.3 Matriz de capabilities por fase

| Capability | Fase 6 | Fase 7 |
|---|---|---|
| `textDocument/publishDiagnostics` | ✅ | ✅ |
| `textDocument/hover` | ✅ | ✅ |
| `textDocument/completion` | ✅ | ✅ |
| `textDocument/definition` | ✅ | ✅ |
| `textDocument/documentSymbol` | ✅ | ✅ |
| `textDocument/formatting` | ✅ | ✅ |
| `textDocument/references` | — | ✅ |
| `textDocument/rename` | — | ✅ |
| `textDocument/codeAction` | — | ✅ |
| `textDocument/inlayHint` | — | ✅ |
| `textDocument/semanticTokens` | — | ✅ |
| `textDocument/signatureHelp` | — | ✅ |
| `textDocument/implementation` | — | ✅ |
| `textDocument/typeDefinition` | — | ✅ |
| `workspace/symbol` | — | ✅ |
| `callHierarchy` | — | ✅ |
| `textDocument/codeLens` | — | ✅ |
| `textDocument/foldingRange` | — | ✅ |
| `textDocument/selectionRange` | — | ✅ |
| `textDocument/documentLink` | — | ✅ |
| `workspace/didChangeWatchedFiles` | — | ✅ |

### 9.4 Rendimiento

Objetivos en una laptop media, proyecto de 50k LOC:

- diagnóstico incremental p50 < 100 ms, p95 < 300 ms;
- completion p50 < 150 ms;
- hover/definition p50 < 50 ms;
- indexación inicial < 2 s;
- memoria < 500 MB para 50k LOC;
- sin bloquear el event loop; todo request pesado en `spawn_blocking` o pool.

### 9.5 Testing

- Tests de protocolo con `lsp-types` y un cliente fake.
- Snapshots de respuestas (`insta`).
- Tests de cancelación y concurrencia.
- Fuzzing de documentos incompletos.
- Corpus de proyectos reales.
- Medición continua con `criterion` y perfiles.

---

<a id="10-extensión-de-vs-code"></a>
## 10. Extensión de VS Code

### 10.1 Estructura

```text
editors/vscode/
├── package.json
├── src/extension.ts
├── syntaxes/pengu.tmLanguage.json
├── snippets/pengu.json
├── language-configuration.json
├── tasks.json
└── test/
```

### 10.2 Funciones

- Resaltado TextMate + semantic tokens del LSP.
- Autocompletado, hover, diagnósticos, go to definition, rename, references, code actions.
- Comandos: `Pengu: Build`, `Pengu: Run`, `Pengu: Check`, `Pengu: Test`, `Pengu: Format`, `Pengu: Restart LSP`.
- Tasks de build/run/test con problem matcher.
- Status bar: versión de `pengu`, estado del LSP, target.
- Configuración: ruta de `pengu`, args del LSP, inlay hints, formatting on save.
- Snippets: `rune`, `enchanting`, `pact`, `ritual`, `match`, `grimoire`, `foreign`, `@@test`.
- `pengu lsp` se lanza automáticamente; si falta, muestra acción de instalación.

### 10.3 Empaquetado

- `vsce package` produce `.vsix`.
- Publicación en Marketplace solo cuando el LSP esté estable.
- Tests de extensión con `@vscode/test-electron`.
- CI en Linux/macOS/Windows.

---

<a id="11-ejemplos-conformidad-y-qa"></a>
## 11. Ejemplos, conformidad y QA

### 11.1 `examples/`

Cada ejemplo es un proyecto real:

```text
examples/
├── hello/
│   ├── Tome.toml
│   ├── src/main.pengu
│   └── expected.txt
├── cli/
├── library/
├── ffi/
├── wasm/
└── errors/
```

- `pengu test --examples` compila y ejecuta todos.
- Ejemplos con salida esperada se comparan con `expected.txt`.
- Ejemplos de error verifican códigos de diagnóstico (`expected.stderr`).
- Los ejemplos son tests de regresión del compilador y del CLI.

### 11.2 Conformidad con la spec

- Extraer bloques `pengu` de `docs/LANGUAGE.md` y compilarlos.
- Todo bloque normativo debe compilar o estar marcado como fragmento.
- Tests de gramática: cada producción EBNF tiene al menos un caso.
- Tests de diagnósticos: cada código tiene un caso que lo dispara y una corrección.

### 11.3 Pirámide de tests

| Nivel | Qué prueba |
|---|---|
| Unit | lexer, parser, tipos, utils |
| Snapshot | AST, diagnósticos, formatter, LSP |
| Integration | `pengu` end-to-end sobre fixtures |
| Conformance | ejemplos de la spec |
| FFI | bindgen + llamadas reales |
| LSP | protocolo y características |
| CLI | snapshots de ayuda/salida/exit codes |
| Cross-platform | Linux/macOS/Windows |
| Fuzz | parser, lexer, LSP con input inválido |

### 11.4 CI

- `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`.
- `pengu check` sobre todos los ejemplos.
- `pengu test --examples`.
- Benchmarks sin regresión > 10%.
- Nightly con Rust beta y stable; MSRV 1.85.
- Matriz de SO.

---

<a id="12-instalación-scripts-y-release"></a>
## 12. Instalación, scripts y release

### 12.1 Scripts

```text
scripts/
├── build.sh          # build release del workspace
├── install.sh        # instala pengu en ~/.local/bin o /usr/local/bin
├── uninstall.sh
├── install.ps1       # Windows
└── release.sh        # empaqueta artefactos
```

`scripts/install.sh`:

- Detecta SO/arquitectura.
- Prefiere binario precompilado del release; si no, compila con `cargo build --release`.
- Copia `pengu` a `$PENGU_INSTALL_DIR` o `~/.local/bin`.
- Añade al PATH solo con `--modify-path` (no edita dotfiles sin permiso).
- Instala completions y man page.
- Verifica con `pengu doctor`.

`scripts/install.ps1` equivalente para Windows.

### 12.2 `pengu self update`

- Consulta el release más reciente (si hay red).
- Descarga el artefacto de la plataforma, verifica checksum y reemplaza el binario.
- `--version <v>` para fijar; `--dry-run`.

### 12.3 Release

- GitHub Actions: Linux x86_64/aarch64, macOS x86_64/aarch64, Windows x86_64.
- Checksums SHA-256 y SBOM.
- `pengu --version` incluye versión, commit y `rustc`.
- Versionado SemVer; pre-releases `-rc.N`.
- Notas de release generadas desde `CHANGELOG.md`.

---

<a id="13-fases-de-implementación"></a>
## 13. Fases de implementación

Cada fase termina con código ejecutable, tests y un documento detallado. Las fases 0–5 construyen la base; 6–11 completan la experiencia.

### Fase 0 — Fundaciones y esqueleto del CLI

**Objetivo:** que `pengu` exista, sea instalable y tenga una UX base.

Entregables:

- Workspace Cargo y crates vacíos con límites claros.
- `pengu` con `clap`: `version`, `doctor`, `completions`, `help` agrupada.
- `pengu-diag` con códigos, spans y render humano/JSON.
- Configuración y flags globales.
- CI mínimo (fmt, clippy, test).
- `scripts/build.sh` y `scripts/install.sh` iniciales.

Salida: `pengu doctor` funciona; `pengu --help` es presentable; tests de CLI.

### Fase 1 — Proyecto, templates y ciclo de vida

**Objetivo:** crear un proyecto y ejecutar `build/run` con un backend mínimo.

Entregables:

- `pengu new`, `pengu init`, `pengu templates`.
- Templates `bin`, `lib`, `cli`, `ffi`, `wasm`, `test`.
- `Tome.toml` parseado y validado.
- `pengu build/run/clean` con pipeline mínimo (hello world).
- `pengu metadata`.
- `.gitignore`, README y estructura de proyecto.

Salida: `pengu new hola && cd hola && pengu run` imprime `hola`.

### Fase 2 — Front-end del compilador

**Objetivo:** lexer, parser, AST, módulos y diagnósticos recuperables.

Entregables:

- Lexer con indentación, comentarios, literales y errores.
- Parser con spans y recuperación.
- AST completa de la spec 0.6.0.
- Resolución de módulos, `scroll`, `summon`, `unveil`, `.d.pengu`.
- `pengu check` sintáctico y de resolución.
- Snapshot tests de AST y diagnósticos.

Salida: todos los ejemplos de la spec parsean; errores con span correcto.

### Fase 3 — Checker semántico y de ownership

**Objetivo:** el corazón de la promesa “no pienses en Rust”.

Entregables:

- Tipos, inferencia local, pacts, genéricos, patrones, retornos.
- Ownership/borrowing/moves/drops según la spec.
- Exhaustividad, `?`, errores, const eval.
- Diagnósticos con códigos, sugerencias y `pengu explain`.
- Corpus de conformidad y tests negativos.

Salida: `pengu check` acepta los ejemplos válidos y rechaza los inválidos con códigos correctos; `cargo` no se invoca.

### Fase 4 — Lowering, codegen y build/run reales

**Objetivo:** generar Rust correcto y compilarlo.

Entregables:

- Lowering a IR con moves/drops explícitos.
- Codegen de Rust + `Cargo.toml` + `sourcemap.json`.
- `pengu build/run/test` con `cargo`.
- Remapeo de errores de `rustc`.
- Caché incremental.
- Ejemplos end-to-end.

Salida: los ejemplos compilan y corren; ningún error de Rust sin mapear en programas aceptados.

**Estado: ✅ cerrada.** `pengu check` (+`--watch`) comparte el análisis con
`build`; remapeo real de `rustc` con span y nota; caché por fingerprint SHA-256
(segundo build en 18 ms sin Cargo); `emit` idempotente; `examples/` compilados y
ejecutados en tests; `docs/BUILD.md`. Ver `scratch/PHASE4_PLAN.md`.

### Fase 5 — Paquetes git, lock y vendor ✅ (2026-11-15)

**Objetivo:** dependencias sin registry.

Entregables (todos ✅):

- `pengu add/remove/update/tree/fetch/vendor` — `crates/pengu-cli`.
- Resolución de git, tags/revs/branches — `crates/pengu-pkg/src/{git,source,spec,tags}.rs`.
- `Tome.lock`, checksums, caché, offline/locked — `crates/pengu-pkg/src/{lock,sha256,tree_hash,cache,ops}.rs`.
- Detección de ciclos y conflictos — `crates/pengu-pkg/src/resolver.rs` (`PGS-E1807` con camino).
- Features aditivas y dependencias `optional` — `resolver::expand_features`.
- Vendor verificado y build desde vendor — `crates/pengu-pkg/src/vendor.rs`.
- Dependencias integradas en el build como módulos (`scroll <paquete>`, decisión D2 de
  `scratch/PHASE5_PLAN.md`).
- `pengu new` con templates embebidos `bin`, `lib` y `with-dependency` (este último crea
  un proyecto que usa una dependencia `path` y resuelve el lock sin red). La parte de
  templates remotos (`gh:…`) y `pengu init` sigue siendo de la Fase 1.

Salida: un proyecto con dos dependencias git compila reproduciblemente; `--offline`
funciona con `vendor/` y sin caché. 643 tests, clippy/fmt limpios. Detalle en
`scratch/STATUS.md` §11 y `scratch/PHASE5_PLAN.md`.

### Fase 6 — LSP base ✅

**Objetivo:** editor con diagnósticos, hover, completion y navegación básica.

Entregables:

- Servidor LSP stdio con lifecycle y VFS.
- `publishDiagnostics`, `hover`, `completion`, `definition`, `documentSymbol`, `formatting`.
- `pengu lsp`, logging y configuración.
- Cliente de prueba y snapshots.

Salida: VS Code muestra diagnósticos y autocompletado en un proyecto real.

**Estado:** cerrada (crate `pengu-lsp`, `docs/LSP.md`, clientes en `editors/`;
614 tests de workspace antes de la fase → 714 al cerrarla).

### Fase 7 — LSP avanzado ✅

**Objetivo:** calidad rust-analyzer/clangd/pyright.

Entregables:

- references, rename, code actions, inlay hints, semantic tokens.
- signature help, type definition, implementation, workspace symbols.
- call hierarchy, code lens de tests, folding, selection ranges.
- performance y cancelación.

Salida: suite de protocolo y benchmarks; uso diario sin caídas.

**Estado:** cerrada. `pengu-layout` mide el layout real (verificado contra
`rustc`), `hover`/inlay hints/`pengu size` muestran bytes, y el servidor cubre
references, rename, semantic tokens, inlay hints, signature help, code lens,
folding, selection ranges, type definition, implementation, code actions,
workspace symbols y call hierarchy. Detalle en `scratch/PHASE7_PLAN.md`,
`docs/LSP.md` y `scratch/STATUS.md` §13.

### Fase 8 — Formatter, linter, docs, tests y fix ✅

**Objetivo:** completar el ciclo de calidad.

Entregables:

- `pengu fmt`/`--check` idempotente.
- `pengu lint`, lints configurables.
- `pengu fix` con sugerencias seguras.
- `pengu doc`, doc tests.
- `pengu test`, `pengu bench`, `--watch`.
- Integración con CI.

Salida: un proyecto se formatea, lintea, testea y documenta solo con `pengu`.

### Fase 9 — Bindgen

**Objetivo:** consumir C sin escribir bindings a mano.

Entregables:

- `pengu bindgen` con clang CLI (AST JSON).
- Mapeo de tipos, `Ptr`, `@@repr(C)`, `[link]`.
- Allow/blocklist, reporte de omitidos.
- Corpus de cabeceras reales.
- `--check` y validación con el checker.

Salida: `pengu bindgen zlib.h` genera un `.d.pengu` que compila y se usa en un ejemplo.

**Estado (2026-11-15): ✅ cerrada.** `pengu bindgen` genera declarados desde
`clang -ast-dump=json` para `zlib.h`, `sqlite3.h` y `stdio.h`; el manifiesto
gana `[declarations]` y el build carga los declarados como módulos (`PGS-E2013`,
`PGS-E2020`, `PGS-E2023`); `.d.pengu` admite constantes con valor; `curse`
funciona en posición de valor; y la ABI de `CStr` en `foreign "C"` viaja como
`*const c_char` con conversión en el call site. `docs/BINDGEN.md` documenta
mapeo, omisiones y opciones.

### Fase 10 — Extensión de VS Code y ecosistema

**Objetivo:** experiencia integrada.

Entregables:

- Extensión VS Code con LSP, syntax, snippets, tasks, comandos.
- `examples/` completo y ejecutable como tests.
- Documentación de usuario y guías.
- Snapshots de CLI y LSP.

Salida: instalar el `.vsix`, abrir un proyecto y tener la experiencia completa.

### Fase 11 — Release, instaladores y extras

**Objetivo:** distribución real.

Entregables:

- Instaladores Linux/macOS/Windows.
- `pengu self update`, completions, man page.
- Checksums, SBOM, CI de release.
- `pengu debug` (DAP) y `pengu repl` como extras si el tiempo lo permite.
- Documento de release y migración.

Salida: `curl ... | sh` instala `pengu` y `pengu doctor` pasa en las tres plataformas.

**Estado: ✅ cerrada (2026-11-15).** `scripts/install.sh`, `install.ps1`,
`install.bat`, `package.sh`, `vsix.mjs`, `test-release.sh`, workflow `Release`
(matriz linux/macOS/Windows), `pengu doctor`/`version --json`/`completions`/`man`,
`docs/INSTALL.md` y `docs/RELEASE.md`. `pengu self update` no se implementa:
actualizar es re-ejecutar el instalador (decisión D10), y `pengu debug`/`repl`
quedan fuera del alcance de la fase.

---

<a id="14-documentos-detallados-por-área"></a>
## 14. Documentos detallados por área

Este plan es el mapa. La implementación se planifica después en documentos separados:

| Documento | Contenido |
|---|---|
| `scratch/CLI_PLAN.md` | Todos los comandos, flags, UX, exit codes, config, tests de CLI. |
| `scratch/COMPILER_PLAN.md` | Lexer, parser, HIR, tipos, ownership, lowering, codegen, source maps. |
| `scratch/LSP_PLAN.md` | Capabilities, arquitectura, rendimiento, testing, integración VS Code. |
| `scratch/PKG_PLAN.md` | Git deps, lock, resolución, cache, vendor, seguridad. |
| `scratch/BINDGEN_PLAN.md` | clang CLI/AST JSON, mapeo de tipos, ABI, corpus, generación. |
| `scratch/TEMPLATES_PLAN.md` | Formato de template, variables, templates embebidos/remotos. |
| `scratch/QA_PLAN.md` | Conformidad, fuzz, benchmarks, CI, ejemplos. |
| `scratch/phases/FASE_00.md` … `FASE_11.md` | Plan superdetallado de cada fase. |

Orden recomendado de escritura:

1. `CLI_PLAN.md` (es la interfaz de todo).
2. `COMPILER_PLAN.md`.
3. `LSP_PLAN.md`.
4. `PKG_PLAN.md`, `BINDGEN_PLAN.md`, `TEMPLATES_PLAN.md`.
5. `QA_PLAN.md`.
6. Documentos de fase.

---

<a id="15-riesgos-y-decisiones-abiertas"></a>
## 15. Riesgos y decisiones abiertas

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Implementar un borrow checker completo | Muy alto | Empezar por el subconjunto de la spec (sin lifetimes escritos); usar `rustc` como red de seguridad y mapear. |
| LSP lento por recompilar | Alto | Salsa/cache, snapshots, debounce, cancelación, medición continua. |
| `clang` difícil de distribuir | Medio | Detectar y dar instrucciones; bindgen opcional; fallback a bindings manuales. |
| Git deps sin registry | Medio | Lock, checksum, cache, vendor; documentar que no hay resolución SAT. |
| Windows paths/CRLF | Medio | CI Windows desde fase 0; VFS normaliza. |
| Formatter y parser divergen | Medio | Formatter sobre AST, tests de round-trip. |
| Errores de `rustc` no mapeados | Alto | Tests de “cero fugas”; source maps; fallback con span de item. |
| Features de Rust no soportadas | Medio | Matriz de paridad y diagnósticos `PGS-E66xx`. |

Decisiones abiertas:

1. Cache incremental propio (sin `salsa`): resuelto en `CLI_PLAN.md` §3–§4 y §11.
2. LSP síncrono propio (sin `tower-lsp`/async): resuelto en `CLI_PLAN.md` §3–§4 y §12.
3. ¿Un crate por capa o menos? Recomendación: empezar con 6 crates y separar cuando duela.
4. ¿El formatter es estable desde fase 1 o fase 8? Recomendación: fase 8, pero el parser debe preservar comentarios desde fase 2.
5. ¿`pengu run script.pengu` usa un proyecto temporal o `rustc` directo? Recomendación: proyecto temporal cacheado para reutilizar dependencias.
6. ¿La extensión se publica en Marketplace? Solo tras fase 10 y revisión.

---

<a id="16-criterios-de-aceptación-globales"></a>
## 16. Criterios de aceptación globales

El toolchain se considera “completo” cuando:

- `pengu new`, `add`, `build`, `run`, `test`, `check`, `fmt`, `doc` y `lsp` funcionan en Linux/macOS/Windows.
- Todos los ejemplos de `docs/LANGUAGE.md` y `examples/` compilan.
- `pengu check` no invoca `cargo` y detecta todos los errores normativos de la spec.
- Un programa aceptado por `check` no produce errores crudos de `rustc`; si los produce, hay un test que lo cubre.
- El LSP responde las capabilities de la fase 7 con los objetivos de latencia.
- `pengu add` instala una dependencia git y `--locked --offline` reproduce el build.
- `pengu bindgen` genera un binding usable para al menos 3 cabeceras reales.
- La extensión de VS Code instala, lanza el LSP y muestra diagnósticos.
- `scripts/install.sh` y `install.ps1` dejan `pengu` en PATH y `pengu doctor` pasa.
- CI verde en la matriz de SO y Rust estable/MSRV.

---

<a id="17-anexos"></a>
## 17. Anexos

### A. Matriz de comandos por fase

| Fase | Comandos que deben funcionar |
|---|---|
| 0 | `version`, `doctor`, `completions`, `--help` |
| 1 | `new`, `init`, `templates`, `metadata`, `build`, `run`, `clean` |
| 2 | `check` (sintáctico/resolución) |
| 3 | `check` (semántico) |
| 4 | `build`, `run`, `test`, `check --watch` |
| 5 | `add`, `remove`, `update`, `tree`, `fetch`, `vendor` |
| 6 | `lsp` |
| 7 | `lsp` avanzado |
| 8 | `fmt`, `lint`, `fix`, `doc`, `bench` |
| 9 | `bindgen` |
| 10 | Extensión VS Code + `examples` |
| 11 | `self update`, `man`, instaladores, `debug`/`repl` |

### B. Layout de un proyecto

```text
mi-app/
├── Tome.toml
├── Tome.lock
├── README.md
├── .gitignore
├── src/
│   ├── main.pengu
│   └── lib.pengu
├── tests/
│   └── integracion.pengu
├── examples/
│   └── basico.pengu
└── target/pengu/       # generado, no se commitea
```

### C. Variables de entorno

| Variable | Uso |
|---|---|
| `PENGU_HOME` | Directorio de configuración/caché. |
| `PENGU_LOG` | Nivel de log (`error`, `warn`, `info`, `debug`, `trace`). |
| `PENGU_TARGET_DIR` | Target dir alternativo. |
| `PENGU_OFFLINE` | Fuerza offline. |
| `PENGU_NO_COLOR` | Desactiva color. |
| `PENGU_RUSTC` | `rustc` alternativo. |
| `PENGU_CARGO` | `cargo` alternativo. |
| `PENGU_CLANG` | Ruta a `clang`. |

### D. Glosario de tooling

- **Checker:** análisis semántico que acepta/rechaza el programa antes de Rust.
- **Driver:** orquestador compartido por CLI y LSP.
- **HIR:** representación intermedia con nombres resueltos.
- **Lowering:** conversión a IR explícito para codegen.
- **Source map:** mapa de spans PenguScript ↔ Rust.
- **VFS:** sistema de archivos virtual con overlays del editor.
- **Snapshot:** vista inmutable del análisis para un request LSP.
- **Tome:** manifest de un proyecto/dependencia.
- **Template:** esqueleto de proyecto con variables.
- **Bindgen:** generación de `.d.pengu` desde C.

---

**Fin del plan maestro.** `scratch/CLI_PLAN.md` desarrolla la interfaz completa. El siguiente entregable es `scratch/COMPILER_PLAN.md`.
