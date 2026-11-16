# Changelog

Todos los cambios relevantes de PenguScript. El formato sigue, en lo posible,
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado de
la especificación usa [SemVer](https://semver.org/lang/es/).

Las entradas de lenguaje describen la especificación; las de `Compiler`
describen el compilador en Rust.

## [Unreleased]

## [Compiler 0.1.0] - 2026-11-15

Primera release del compilador completo. `pengu` analiza, verifica, baja a LIR,
genera Rust y compila con Cargo; incluye la stdlib embebida y el servidor LSP.

### Añadido

- **STDLIB completa (S1–S9):** 29 módulos en `std/` — núcleo (`integrum`,
  `floatem`, `littera`, `opera`, `veritas`, `verbum`, `capsa`, `tabula`,
  `fasciculus`, `numerus`, `fluxus`, `proba`, `opera`, `optio`, `funis`,
  `structura`), sistema (`via`, `exsecutor`, `ambitus`, `tempus`, `terminus`,
  `globus`, `archivum`, `cellula`), FFI (`nexus`) y auto-hospedaje textual
  (`libra`, `iason`, `digestum`, `versio`, `rete`).
- **Gate B cerrado:** corpus de la especificación clasificado (68 programas
  compilan, 13 bloques declarados no ejecutables con motivo) y
  `scratch/GATE_B_CORPUS.md` como referencia.
- **Fase 4 — build real:** `pengu check` sin Cargo, `--watch`, caché
  incremental por `SHA-256`, `emit` idempotente, remapeo de errores de `rustc`
  a spans del fuente y `examples/` compilados en los tests.
- **Fase 5 — paquetes:** `crates/pengu-pkg` con lock `Tome.lock` v1, git por
  `Command`, caché de repositorios desnudos, `tree_hash` canónico, resolución
  con ciclos/features/opcionales, `vendor` verificado y comandos
  `fetch/tree/vendor/add/remove/update`.
- **Fase 6 — LSP base:** `crates/pengu-lsp` con JSON-RPC propio, posiciones
  UTF-8/16, diagnósticos, hover, completion, definición, símbolos y formato.
- **Fase 7 — LSP avanzado:** `crates/pengu-layout` (tamaños y alineación
  verificados contra `rustc`), references, rename, tokens semánticos, inlay
  hints, signature help, code lens, folding, selection, typeDefinition,
  implementation, code actions, workspace symbols, call hierarchy y
  `pengu size`.
- **Fase 8 — calidad:** `pengu fmt` (formateador de tokens con verificación de
  secuencia), `pengu lint` (10 lints), `pengu fix`, `pengu doc` con doc tests,
  `pengu bench`, `pengu explain` y CI.
- **Fase 9 — bindgen:** `pengu bindgen <cabecera>` con clang AST JSON,
  `[declarations]` en `Tome.toml`, `PGS-E2023` cuando falta `[link]` y corpus
  zlib/sqlite3/stdio con `examples/zlib.pengu`.
- **Fase 11 — release:** `scripts/install.sh`, `scripts/install.ps1`,
  `scripts/install.bat` (PATH idempotente, `--from-source`, `--uninstall`,
  completions y manual), `scripts/package.sh` (tar.gz/zip, `SHA256SUMS`,
  `VERSION`, `sbom.json`), `scripts/vsix.mjs` (`.vsix` sin npm, `--install`) y
  workflow `Release` para Linux/macOS/Windows.
- `pengu doctor`, `pengu version --json`, `pengu completions` y `pengu man`.

### Documentación

- Nuevas guías: `docs/INSTALL.md`, `docs/RELEASE.md`, `docs/BUILD.md`,
  `docs/QUALITY.md`, `docs/LSP.md` y `docs/BINDGEN.md`; `README.md` con
  instalación y estado real.


### Compiler

- **B7 (2026-11-13, completo):** build/run/test con Cargo.
  - `pengu-build::{build_report, run_report, test_report}` devuelven salida y
    diagnósticos remapeados; `build`/`run`/`test` son wrappers de error.
  - `cargo build/run/test --message-format=json`; errores del backend pasan
    por `remap_rustc_diagnostics`.
  - Tests: **518 workspace**, 43 codegen, 9 build.
- **Gate B (2026-11-13, PASA en suite representativa):** 15 programas backend compilan/ejecutan; `scratch/GATE_B_REPORT.md`.

- **B6 (2026-11-13, completo):** sourcemaps y errores JSON.
  - `SourceMap` registra líneas Rust y sus spans PenguScript mediante
    marcadores por sentencia; `lookup` y `to_json`.
  - `pengu-build::remap_rustc_diagnostics` convierte errores JSON de
    `rustc`/Cargo a diagnósticos `PGS-E2014`, con span PenguScript cuando
    hay mapeo y span vacío cuando no.
  - Tests: **514 workspace**, 43 codegen, 7 build.

- **B5 (2026-11-13, completo):** Cargo/Tome/link.
  - `Manifest::to_cargo_toml_with_base` emite `[package]` con `build.rs`,
    `rust-version`, features, dependencias git/path (absolutas) y `[[bin]]`/`[lib]`.
  - `build.rs` enlaza `[link]` con `cargo:rustc-link-lib`.
  - `pengu-build::{build, run, emit}` usan Cargo; soporte bin/lib.
  - Tests: 5 build, 13 project, **511 workspace**.

- **B4 (2026-11-13, completo):** runtime, `print`/`format` y `Show`.
  - `Show` para primitivos, strings, `&T`, `Box`/`Rc`/`Arc`, arrays/slices,
    `Vec`, `Map`, `Set`, `Option`, `Result`, tuplas 2–4 y `Ordering`.
  - Interpolación `#{}` en LIR y codegen; `print`, `format`, `panic` y `assert`.
  - `ritual T for Show` de usuario; el `Show` de prelude no se emite como item.
  - Tests: **506 workspace**, 42 codegen; incluye ejecución y panic.

- **B3 (2026-11-13, completo):** codegen SSA, iteradores e impls genéricos.
  - Locales generados como state machine SSA (`__State` + `loop/match`), sin
    `Option<T>` ni `expect` ocultos; locals con préstamos usan `enum __State<'a>`.
  - Closures, iteradores lazy (`Iterator`, `IntoIter`, `Next`), `for` sobre
    `Vec`/array/`Map`/`Set`, destructuring plano/anidado y adaptadores.
  - Impls genéricos monomorfizados; receptores `@`/`@mut`/`@own`.
  - `Show` runtime, sourcemaps, `pengu-build::{compile, emit, run}` y Cargo/Tome.
  - Tests: **499 workspace**, 35 codegen; clippy/fmt limpios.

- **B3d (2026-11-13, base):** closures y `for` sobre `Vec`.
  - `LExpr::Closure`/`ClosureCall`; closures sin captura y con captura.
  - `for x in vector`/array con índice `usize`, `len()` e indexación prestada.
  - Tests: 17 codegen; **489 workspace**.
  - Pendiente: adaptadores/iteradores, impls genéricos y runtime.

- **B3c (2026-11-13, parcial):** métodos y `Str` prestado.
  - LIR `Method` y `SelfValue` -> local `self`; codegen de `obj.metodo(...)`.
  - `Str` se emite como `&str` con elisión de lifetime.
  - Tests: 14 codegen; **474 workspace**.
  - B3d pendiente: closures/captura, iteradores/`for`, impls genéricos y runtime.

- **B3b (2026-11-13):** expresiones y locales en `pengu-codegen`.
  - LIR/codegen de campos, índices, arrays/repeat, `Vec`/`Map`/`Set`, records,
    variantes, primitivas, casts, `?`, refs, rangos y chars.
  - Expresión final de función, locales `Copy`/no `Copy` sin `clone()`,
    `grimoire: Result`.
  - Tests de compilación y ejecución; **473 workspace**, 13 codegen.
  - B3c pendiente: closures, iteradores/métodos, impls genéricos y runtime.

- **B3a (2026-11-13):** codegen de items en `pengu-codegen`.
  - `rune`/`enchanting`, `essence`, `sigil`/`relic`, `pact` (incluye defaults),
    `impl`/`ritual`, `foreign` agrupado por ABI, `@@test`, `grimoire`, `curse`
    y funciones LIR con CFG (`__pc` + `loop/match`).
  - Módulos `scroll` anidados, paths `crate::...`, visibilidad y metadata HIR
    (`TestInfo`, `grimoires`, `foreign_abis`).
  - `Generated.diagnostics` propaga HIR/LIR y no emite Rust si hay errores.
  - El Rust generado compila con `rustc --edition 2024 --crate-type lib`.
  - Limitaciones B3c: closures, iteradores/impls genéricos, runtime y enlaces
    FFI reales en B5.
  - Tests: 10 de codegen; **470 workspace**.

- **B2 (2026-11-13):** monomorfización materializada en `pengu-lir`.
  - `MonoPlan`/`MonoInstance` y recolección transitiva de instancias con turbofish.
  - Una `LFunction` por instancia, sin funciones genéricas base; sustitución de
    tipos en locales, parámetros, retorno, temporales y ADTs.
  - `LExpr::Call(DefId, Vec<Ty>, Vec<LExpr>)` conserva los argumentos de tipo.
  - Tests: 3 de monomorfización; **460 workspace**.

- **C4 (2026-11-13):** checker de ownership y préstamos en `pengu-check`.
  - Places con proyecciones, movimiento de owned, `Copy`/`Clone`, préstamos
    `&`/`&mut`, conflictos shared/mut, movimiento de prestados, asignación a
    prestados/inmutables y `push` sobre inmutable.
  - Escapes de referencias locales, retornos de referencias en funciones libres,
    movimientos de campos en `match` y merge de estados en ramas.
  - `CheckResult` expone tipos por `BodyId`/`LocalId`; `AdtDef.is_copy` sale de
    `@@derive(Copy)`.
  - Diagnósticos `PGS-E4101`–`E4108`, `E1103`, `E3106`.
  - 15 tests de C4 y **304 de workspace**; clippy/fmt limpios.
- **F0 (2026-11-12):** workspace Rust 2024/MSRV 1.85.0 con los crates
  `pengu-span`, `pengu-vfs` y `pengu-diag`. Sin dependencias externas.
  - `pengu-span`: `FileId`, `Span`, `Spanned<T>`, spans vacíos y fusión.
  - `pengu-vfs`: `SourceFile`, `Vfs` con overlays, `line_col`, `normalize_path`
    y fingerprint de contenido de 256 bits (no criptográfico).
  - `pengu-diag`: `Diagnostic`, `Label`, `DiagnosticBag`, severidades y
    códigos `PGS-*`.
  - `cargo test --workspace` verde.
- **F1 (2026-11-12):** crate `pengu-syntax` con el lexer completo del núcleo.
  - Tokens de §2, keywords, literales numéricos/char/string normal/triple/raw/
    byte/C, interpolación `#{}` y comentarios/doc comments.
  - Indentación significativa, `NEWLINE`/`INDENT`/`DEDENT`, continuación tras
    operador binario, CRLF y BOM.
  - Diagnósticos léxicos `PGS-E1001`–`PGS-E1011`; identificadores Unicode con
    `unicode-ident` (MIT OR Apache-2.0).
  - 39 tests del lexer (38 unitarios + corpus); 62 tests de workspace; clippy y fmt limpios.
- **F2 (2026-11-12):** parser Pratt de expresiones; tercera ronda cierra desviaciones de gramática inline/bloque, indentación tras comentarios de bloque y cubre referencias/campos de tupla.
  - AST de expresiones, tipos, patrones, sentencias y bloques.
  - Precedencia §14.1, postfix, llamadas, indexado, campos, `?`, `as`, rangos.
  - `if`/`unless`/`match`/`do`/`loop`/`curse`, lambdas, `bind`/`morph` y bloques.
  - `PGS-E1901` para errores sintácticos; catálogo 160 códigos.
  - Bindings con tipo explícito, tipos de función `(A, B) -> C` y tipo `Self`.
  - Referencias de expresión `&`/`&mut`, acceso a campos de tupla `.0`, y rechazo de bloques/`match` vacíos.
  - 84 tests de parser; 149 tests de workspace; clippy y fmt limpios.
- **F3 (2026-11-12):** parser de items, programa y `.d.pengu`.
  - `Program`, `Item`, `ItemKind` y AST de `scroll`, `summon`, `rune`,
    `enchanting`, `pact`, `ritual`, `essence`, `foreign`, funciones, `sigil`/
    `relic`, `grimoire` y `@@test`.
  - `parse_program` y `parse_declaration_file`; `DeclarationFile` con `abi`.
  - `rune`/`enchanting` con `@@derive`; `essence`; `.d.pengu` sin cuerpos.
  - 15 tests de programa, 3 de declaraciones; 105 tests de parser; 167 de
    workspace; clippy y fmt limpios.
- **F4 (2026-11-12):** CST lossless y recuperación de errores.
  - `SyntaxTree` con `SyntaxKind`, `SyntaxNode`, `SyntaxToken` y
    `SyntaxElement`; conserva comentarios, espacios, `NEWLINE`, `INDENT`,
    `DEDENT` y `EOF`.
  - `ParsedProgram.tree`, `ParsedDeclaration.tree` y `ParsedExpr.tree`; el
    árbol se construye incluso si el parser no puede producir el AST.
  - Diagnósticos combinados de lexer y parser, con tope de 100 por archivo,
    también en expresiones.
  - `reconstruct()` reconstruye el fuente exacto; los nodos tienen spans,
    jerarquía y `node_at()` para mapear spans del AST.
  - Nodos con el mismo span pero distinto kind se conservan (p. ej. raíz
    `Program` y su único `rune`); los tokens se asignan al nodo más profundo.
  - 15 tests de CST; 191 tests de workspace; clippy y fmt limpios.
- **F5 (2026-11-12):** corpus de sintaxis completo.
  - `crates/pengu-syntax/tests/spec_corpus.rs` extrae y parsea los 146 bloques
    `pengu` de `docs/LANGUAGE.md`: 141 válidos y 5 ejemplos marcados
    `-- ERROR PGS-` (semánticos).
  - Parser: `match` con `then` antes de bloque, actualización de records
    `Point(..base)`, nombres de variante `some`/`none`/`ok`/`err`, y `bind`
    con bloque implícito como valor.
  - Lexer: `=` ya no continúa una línea; así `bind x =` puede abrir bloque.
  - Spec: gramática de `record`, `variant_name`, `binding_value`,
    `match_arm` y `visibility`; `unveil(tome)`/`unveil(scroll)` implementados
    en AST/parser y documentados.
  - 1 test de corpus; 191 tests de workspace; clippy y fmt limpios.
- Auditoría F4/F5: el CST conserva la base de `Point(..p)`; el lexer
  distingue `42f32` como `Float`, diagnostica `1e`, `1e+`, `1.` y
  `1.0_i64` con `PGS-E1011`, y mantiene `1..2` como rango.
- **F6 / Gate F (2026-11-13):** fuzz, límites y documentación del frontend.
  - `pengu-syntax/src/limits.rs`: 10 MiB, 10 000 líneas y profundidad 1000;
    `PGS-E1901` antes de lexear/parsear.
  - `tests/fuzz_smoke.rs`: 10M tokens léxicos, 128 fuentes pseudoaleatorias y
    anidamiento extremo, sin pánicos.
  - `format_source`/`format_declaration` y reconstrucción exacta desde el CST.
  - `docs/FRONTEND.md` con pipeline, recuperación, límites, fuzz y evidencia.
  - Gate F cerrado: 146 bloques (141 válidos + 5 `ERROR PGS-`), todas las
    producciones §19 con parser+test, errores con span y tope 100.
  - 228 tests de workspace; clippy y fmt limpios.
- **C1 (2026-11-12):** crate `pengu-hir` con HIR de nombres, módulos,
  scopes, cuerpos e imports.
  - `HirCrate`/`Module`/`Def`/`Body`, IDs globales (`DefId`, `ModuleId`) y
    locales (`LocalId`, `ScopeId`, `BodyId`); namespaces separados.
  - `scroll` anidado, `summon` con alias/import de valores, tipos y módulos;
    duplicados `PGS-E2005`/`E2013`, no encontrado `PGS-E2004`, privado
    `PGS-E2006`.
  - Visibilidad `unveil`/`unveil(tome)`/`unveil(scroll)`.
  - `Self` en `pact`/`ritual`; fuera `PGS-E1209`; `@` no se resuelve como
    nombre.
  - Firmas de métodos sin cuerpo (`pact`, `rune` de `.d.pengu`) resueltas en
    un `Body` de firma; `Self` funciona sin falso `E1209`.
  - Tipos de prelude y valores `print`/`format`/`some`/`none`/`ok`/`err`;
    patrones prelude y `|` no duplican locales.
  - `unveil` de campo se refleja en `DefKind::Field`; módulo y tipo con el
    mismo nombre dan `PGS-E2005`; ciclos de imports dan `PGS-E2012`.
  - 26 tests de `pengu-hir`; **228 tests de workspace**; clippy y fmt limpios.
  - Limitaciones C1: no carga archivos ni resuelve `.d.pengu` desde disco, no
    comprueba tipos/ownership, y los cuerpos son HIR de nombres, no tipados.

- **C2 (2026-11-13):** crate `pengu-types` con tipos, inferencia y checker inicial.
  - `Ty` (primitivos, tuplas, arrays/slices, refs, `Ptr`, `Vec`/`Map`/`Set`,
    `Option`/`Result`, `Box`/`Rc`/`Arc`, `Adt`, `Generic`, `Fn`, `Range`),
    `Infer` union-find y `check_crate`.
  - Literales y sufijos, defaults `Int`/`Float`, rangos de enteros,
    firmas/aridad, arrays/`Vec`/`Map`/`Set`, tuplas, `bind`/`morph`, control,
    `loop`/`break`, `return`, `?`, `Option`/`Result`, `if`/`match`, `Never`,
    `in`, `as`, referencias, `print`/`format`.
  - `none` sin contexto `PGS-E1508`; `err` sin éxito `PGS-E1507`; `?` fuera de
    retorno Option/Result `PGS-E3007`; `if` sin `else` exige `Unit`.
  - 39 tests de `pengu-types`; 267 de workspace; clippy y fmt limpios.
  - Limitaciones: records/sums y patrones complejos son C3; ownership C4;
    genéricos/pacts C6; sin codegen.

- **C3 (2026-11-13):** records, sums, patrones y exhaustividad.
  - HIR `AdtDef`/`AdtField`/`AdtVariant`; variantes enlazadas en tipos y valores;
    `Self`/campos resueltos en el tipo del ADT.
  - Construcción de records, acceso/actualización `..base`, variantes
    unit/tuple/named y `Option`/`Result`.
  - Patrones de tupla, record posicional/nombrado, variante, slice, rango,
    `or`, `@` y `..`; bindings tipados; `bind ... else` y `for` irrefutable.
  - Exhaustividad de sums, `Bool`, `Option`/`Result` y records completos;
    `else` inalcanzable y brazos inalcanzables.
  - Diagnósticos `PGS-E8001`–`E8005`, `PGS-E9001`–`E9008`, `PGS-W9001`.
  - 22 tests de C3; 61 de `pengu-types`; **289 de workspace**; clippy y fmt limpios.
  - Limitaciones: genéricos de ADT y visibilidad profunda quedan para C6/C7;
    ownership es C4.

### Language

- **0.6.0:** rituales inherentes sobre primitivos solo en `std` y pactos
  locales; archivos de declaración `.d.pengu` con cabecera `abi`; `Ptr[T]`
  para opacos de FFI; `[declarations]` y `[link]` en `Tome.toml`.
- **0.6.0:** cierre de los cuatro huecos de parser/checker:
  `Vec[...]`/`Map[...]` en §19.8; closures que nunca son `FnOnce` y no
  consumen capturas (`PGS-E7004`); `@@derive` en `enchanting` sin `Default`;
  `@@test` solo devuelve `Unit` (`PGS-E1702`).
- **0.6.0:** dependencias git/path, sin registry; `Tome.lock` con commit y
  checksum; `pengu publish` retirado.
- **0.6.0:** overflow entero comprobado siempre, comparaciones IEEE de
  `Float`, resolución de dependencias git, mapeo de errores del backend,
  módulos duplicados, `CStr` en `std.ffi`, `Option`/`Result` completos,
  `match` sobre `Bool`, `return` en `grimoire`, `bind ... else` en bucles y
  visibilidad de variantes.
- **0.5.0:** reescritura de misión. PenguScript deja de ser un transpilador y
  pasa a ser un lenguaje de sistemas chico con backend Rust invisible.
  Núcleo de ~15 conceptos; sin lifetimes escritas, traits complejos, macros,
  async, hilos ni unsafe general en código de usuario; FFI solo de entrada.
  Diagnósticos ≤160 y garantías ≤50.
- **0.3.0:** mapa de `STDLIB.md` ampliado con módulos de auto-hospedaje
  (`std.toml`, `std.json`, `std.digest`, `std.semver`, `std.term`,
  `std.glob`, `std.archive`, `std.net`/TLS, `fs.walk`).

### Tooling

- `scratch/COMPILER_PLAN.md`: plan del compilador en tres fases (frontend,
  checker, lowering/codegen) con gates F/C/B, auditoría de licencias y ruta
  de auto-hospedaje H0–H5.
- `scratch/CLI_PLAN.md`: diseño del CLI `pengu`, 29 comandos, LSP, bindgen,
  paquetes git y auto-hospedaje.
- `scratch/TOOLING_PLAN.md`: plan maestro de tooling por fases.

### Validation

- `docs/LANGUAGE.md`: 28 secciones, 29 anchors, 56 enlaces internos, 160
  diagnósticos y 33 garantías; `check_rewrite.py` y `check_pengu_blocks.py`
  en verde.
- `docs/STDLIB.md`: 32 secciones, 1.929 líneas, versión 0.3.0.

## [Backend parcial] - 2026-11-13

### Added

- Receptores `@mut`/`@own` en llamadas a métodos.
- Runtime `Show` para `print`/`format`.
- `sourcemap.json` aproximado por item.
- `pengu-project`: Cargo.toml, build.rs, `[[bin]]`.
- `pengu-build`: compile/emit/run end-to-end.

### Known gaps

- `T` no-`Copy` desde `@` y locales `Option`/`expect` se corrigieron en B3. Gate B pasa en suite representativa; corpus completo queda B8.

## [0.1.0] - 2026-11-12

### Added

- Repositorio inicial y especificación de misión.
- `docs/LANGUAGE.md` (0.6.0).
- `docs/STDLIB.md` (0.3.0).
- Planes de compilador, CLI y tooling en `scratch/`.

