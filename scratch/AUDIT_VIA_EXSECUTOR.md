# Auditoría 2: limitaciones documentadas al escribir `via`, `exsecutor`, `ambitus` y `tempus`

Fecha: 2026-11-14 (segunda tanda). Base: `10874a3`.
Método: igual que la auditoría 1 — cada punto se reproduce con
`scratch/tools/probe` (parse → HIR → tipos → LIR → codegen → `rustc` → ejecución)
antes de darlo por bueno. Los puntos marcados **(doc)** son huecos de la
especificación, no del lenguaje.

## 1. Limitaciones documentadas y veredicto

Fuente: las tablas «Diseño objetivo pendiente» de `docs/STDLIB.md` §11–§14, la
tabla §1 de `scratch/LIMITATIONS_AUDIT.md` (A4, A5, A7, N34–N36, N49–N54) y los
comentarios de cabecera de `std/{via,exsecutor,ambitus,tempus}.pengu`.

| # | Limitación | Estado verificado |
|---|---|---|
| V1 | `via` no tiene tipo de ruta: todo es `&Str`, así que no hay `Path`/`PathBuf` con métodos | **CONFIRMADA (doc)**: `std/via.pengu` solo expone `join/parent/file_name/extension/file_stem` como funciones sueltas sobre texto. `rune Path { text: String }` es viable (probado: un `rune` con campo `String` y `new(s: &Str)` con `String.from(s)` compila y ejecuta) |
| V2 | No hay `WalkOptions` (`follow_links`, `include_hidden`, `max_depth`); `walk_*` no parametriza el recorrido | **CONFIRMADA**: el runtime `via_walk_paths(root, files, dirs)` solo distingue ficheros/directorios |
| V3 | No hay `OpenOptions`: solo `File.open/create/append` | **CONFIRMADA**; el patrón builder sí funciona: `(@mut, allow: Bool) -> &mut Opts` con `@` como retorno se encadena (`o.lectura(true)`, probado) |
| V4 | No hay `Metadata`/`Permissions`/`FileType`: `FileInfo` aplana todo y `File.metadata` devuelve `FileInfo` | **CONFIRMADA (doc)**; los `rune` con campos `Bool` no tienen ningún problema |
| V5 | `Metadata.modified/created/accessed -> Result[SystemTime, IoError]` no existe: `FileInfo.modified_ms: Option[Int]` es la única marca de tiempo | **CONFIRMADA (doc)**: un módulo de `std` no puede importar el `SystemTime` de `tempus` (N42), así que la vía es exponer milisegundos (`Int`) y dejar el tipos ricos a `tempus` |
| V6 | `DirEntry` solo tiene `path` e `is_dir`: faltan `file_name`, `metadata`, `file_type` | **CONFIRMADA** |
| V7 | `File.read(buf)`/`File.write(buf)` con slices `&mut [U8]`/`&[U8]` no existen | **CONFIRMADA**: depende de A5 (slices). Alternativa sin A5: `read_bytes(count)`/`write_bytes(Vec[U8])` |
| V8 | `File.sync_all/sync_data/try_clone` no existen | **CONFIRMADA (doc)** |
| V9 | `exsecutor` no tiene `Stdio` ni redirección (`Command.stdin/stdout/stderr`, `Child.stdin/stdout/stderr`, `Child.id`, `wait_with_output`) | **CONFIRMADA**; el runtime solo guarda `std::process::Child` y captura con `output()` |
| V10 | `Command.get_args/get_envs/get_current_dir` y `env_remove/envs` no existen | **CONFIRMADA (doc)** |
| V11 | `tempus` no tiene duraciones fraccionarias (`from_secs_f64`, `as_secs_f64`, `mul_f64`, `div_f64`), `subsec_micros/nanos` ni `SystemTimeError.duration` | **CONFIRMADA (doc)**: `Duration` guarda `millis: Int` |
| V12 | `ambitus` está completo salvo `var_os` (lectura de variables no UTF-8) | **CONFIRMADA (doc)** |

Limitaciones del lenguaje que siguen abiertas y afectan a estos módulos (ya
documentadas en la auditoría 1): **A4** (`Str` → `String` implícito; bloquea
devolver literales como `String` y `String.from("… #{x}")`), **A5** (slices),
**A7** (move checking), **N34** (métodos con cuerpo sobre `Option`/`Result`),
**N36** (`rune Iter[T]`), **N49** (`CStr` unsized por valor) y **N53**
(`NulError` como `Ty::Error`).

## 2. Cómo reparar sin romper lo anterior

- **V1/V2/V4/V6/V8**: son huecos de superficie, no del compilador. Se resuelven
  añadiendo `rune`s y funciones a `std/via.pengu` con intrínsecos nuevos en
  `crates/pengu-codegen/src/std_rt.rs`. Los `rune` con campos `String`/`Bool`
  ya funcionan y los builders con `&mut` también, así que el riesgo es bajo.
- **V2**: el recorrido se parametriza en el runtime (`via_walk_with(root, mode,
  follow, hidden, depth)`), con detección de ciclos por conjunto de rutas
  canónicas y `max_depth` opcional.
- **V5**: `via` expone milisegundos (`Int`) en vez de `SystemTime`: evita
  importar `tempus` (N42) y no bloquea a nadie. `tempus` seguirá siendo el
  módulo para aritmética de tiempos.
- **V7**: sin A5 no se pueden escribir `&mut [U8]`; se ofrecen
  `read_bytes(count) -> Result[Vec[U8], IoError]` y
  `write_bytes(data: Vec[U8]) -> Result[Usize, IoError]`. Cuando llegue A5 se
  añadirán las variantes con slice.
- **V9/V10**: se añade `rune Stdio` (variantes `inherit`/`piped`/`null` como
  funciones asociadas), y el runtime guarda los pipes del hijo en registros
  (`EXSEC_CHILDREN` pasa a guardar `Child` + `Option<ChildStdin>` +
  `Option<ChildStdout>` + `Option<ChildStderr>`), con
  `Child.write_stdin/read_stdout/read_stderr/wait_with_output`.
- **V11**: `Duration` sigue guardando `millis: Int` y las nuevas funciones
  convierten en el runtime (`from_secs_f64` redondea a ms; `as_secs_f64`
  divide). `subsec_micros/nanos` se calculan con la parte fraccionaria de los
  milisegundos actuales (precisión documentada: ms).
- **V12**: `var_os` devuelve `Option[String]` con pérdida `lossy`, igual que
  `args_os`.
- **A4**: fase propia (T5) porque toca checker, LIR y codegen; se hace después de
  los módulos para no mezclar riesgo.

## 3. Plan por fases

| Fase | Contenido | Actualiza en `std/` |
|---|---|---|
| **T0** ✅ | Esta auditoría | — |
| **T1** ✅ | `via`: `Path`/`PathBuf`, `WalkOptions`, `FileType`, `Permissions`, `DirEntry` completo y marcas de tiempo en ms | `via` |
| **T2** ✅ | `via`: `OpenOptions`, `File.read_bytes/write_bytes/sync_all/sync_data/try_clone/modified_ms` | `via` |
| **T3** ✅ | `exsecutor`: `Stdio`, redirección, `Child.id/read_stdout/read_stderr/write_stdin/wait_with_output`, getters de `Command` y `env_remove` | `exsecutor` |
| **T4** ✅ | `tempus`: duraciones `f64`, `subsec_micros/nanos`, `SystemTimeError.duration`; `ambitus.var_os` | `tempus`, `ambitus` |
| **T5** ✅ | A4: coerción `Str` → `String` en bind/argumento/retorno/campo, y simplificación de las firmas de `std` | `iason`, `exsecutor` |
| **T6** | Documentación (`docs/STDLIB.md` §11–§14, auditoría, `STATUS.md`) y cierre | — |

Cada fase: implementación + test en `crates/pengu-codegen/tests/codegen.rs` +
`cargo test --workspace` verde + `cargo clippy` sin warnings + commit a `main`.

## 4. Criterios de aceptación

- `cargo test --workspace` verde en cada commit; ningún test previo cambia de
  resultado.
- `std/` no conserva notas «Diferido» que esta tanda haya cerrado.
- `docs/STDLIB.md` §11–§14 describe la superficie real (tabla de firmas) y
  `scratch/LIMITATIONS_AUDIT.md` marca V1–V12 con su estado final.

## 5. Limitaciones nuevas descubiertas en T1–T3 (N55–N59)

| # | Limitación | Estado |
|---|---|---|
| N55 | Una cadena `if/elseif/else` **en línea** como cuerpo completo de un método no parsea (`se esperaba una expresión` en la línea siguiente). Hay que usar la forma con bloque (`then` + línea indentada). | Documentada; usar forma con bloque |
| N56 | `for x in @.campo` y `match @.campo` movían el campo que vive detrás de `&self`/`&mut self` → `E0507` en el Rust emitido. | RESUELTA en T3 (`clone_place` en `crates/pengu-lir/src/lower.rs`) |
| N57 | Un binding `bind` de colección es inmutable: `v.push(x)` da `PGS-E3106`. Hay que declararlo con `morph`. | Documentada |
| N58 | `Vec.clone()` no existe: copiar un `Vec[String]` exige un bucle `for` + `push`. | Documentada |
| N59 | `Stdio` no puede usar `inherit` ni `null` como nombres de constructor (palabras reservadas) → `stdio_inherit`, `stdio_discard`. | Documentada |

También: `Child.id` colisionaba con el nombre materializado de las funciones genéricas en la
prueba de mono (`id__Int`/`id`) → se renombró a `Child.process_id`.

## 6. T5: coerción `Str` ↔ `String` (A4)

Implementada en tres piezas:

- `crates/pengu-types/src/check.rs`: `CheckResult.coercions: HashMap<Span, Coercion>` y el
  helper `coerce_strings(expected, actual, span, place)`. Acepta `Str → String` en
  argumentos, retorno del cuerpo, `return` explícito y `bind` anotado; acepta
  `String → Str`/`&Str` solo cuando la expresión es un *place* (`Path`, `Field` o
  `Index`), porque prestar un temporal produce `E0716`.
- `crates/pengu-lir/src/lower.rs`: `lower_expr` pasa por `apply_string_coercion`, que
  materializa la conversión anotada con `.to_string()` o `.as_str()`.
- `crates/pengu-types/src/check.rs` (`string_ty`): una interpolación **con partes** ahora
  se tipa `String` (es lo que el codegen construye con `[…].concat()`); un literal sin
  partes sigue siendo `Str`. Esto cierra tres huecos del corpus Gate B
  (`58/4/12/67/5`, antes `55/4/12/70/5`).

Límites conocidos de la conversión (documentados en `docs/LANGUAGE.md` §4.6):

- No hay `String → Str` para temporales: `toma_str(String.from("x"))` sigue siendo error;
  hay que ligar el `String` a un nombre o llamar `as_str`.
- Las ramas de un `if`/`match` no se convierten entre sí: si una rama es `String` y otra
  `Str`, el tipo común sigue fallando (se arregla con `String.from` en la rama `Str`).
