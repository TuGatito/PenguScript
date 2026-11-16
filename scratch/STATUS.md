# Estado del proyecto tras la auditoría de limitaciones (2026-11-14)

Este documento es el cierre de la tanda pedida en la sesión anterior: auditoría de las
limitaciones documentadas, plan por fases, ejecución de cada fase y actualización de la
STDLIB para usar lo que antes eran limitaciones. El plan detallado vive en
`scratch/LIMITATIONS_AUDIT.md` (§2 diseño de cada arreglo, §3 tabla de fases, §4 registro
de limitaciones nuevas).

## 1. Commits

| Commit | Contenido |
|---|---|
| `00994d1` | Base heredada S0–S4 (12 módulos, runtime de intrínsecos) |
| `f27d210` | A0: auditoría + plan |
| `e743e85` | A1: constantes asociadas en `ritual` |
| `0c49e9a` | A2: variantes calificadas, `Ordering` como valor, literales negativos |
| `82bed8c` | A3: lambdas con cuerpo de bloque y `elseif` inline |
| `7d37c7c` | A6: `Range[T]`, APIs de rango y destructuring desde expresión |
| `d04d2a2` | S5a: codegen de módulos `std` (visibilidad, asociadas de `rune`, sufijos) |
| `8e7cee4` | S5: `via` (FS) completo |
| `aeb3683` | S5b: `exsecutor`, `ambitus`, `tempus`, `optio` |
| `7ee841f` | S7: adaptadores de iterador (`funis` sobre `Iterator`) |
| `48e979b` | S6: `nexus` (`CString` seguro) |
| `e333cb0` | S8: `versio`, `digestum`, `iason` |
| `89bd31a` | S9: `terminus`, `globus`, `cellula` |
| `ea32956` | S10: `rete` (TCP) |
| `4270a25` | Cierre: `STATUS.md`, tabla de aliases y limpieza de lints |
| `db9fe7f` | S8b/S9b: `libra` (TOML aplanado) y `archivum` (tar) |
| `a431b26` | S11: `match` anidado como expresión (N48) |
| `10874a3` | WIP heredado: alias `std::*`, llamadas cualificadas y Gate B |
| `f4420c6` | T1: `via` con `Path`/`PathBuf`, `WalkOptions`, `FileType`, `Permissions` |
| `130bc73` | T2: `via` con `OpenOptions` y E/S por cantidad |
| `ecfe0ea` | T3: `exsecutor` con `Stdio`, pipes y estado del comando |
| `f854c50` | T4: `tempus` con duraciones `f64` y `ambitus.var_os` |
| `ffdd412` | T5: coerción `Str` ↔ `String` (A4) |

## 2. STDLIB actual

28 módulos en `std/` (4.047 líneas de PenguScript), todos registrados en
`crates/pengu-std/src/lib.rs` y con runtime en `crates/pengu-codegen/src/std_rt.rs`
(4.126 líneas).

- **Primitivos y texto:** `integrum`, `floatem`, `littera`, `verbum`, `numerus`, `opera`,
  `veritas`.
- **Colecciones:** `capsa`, `tabula`, `fasciculus`, `structura` (pila/cola/cola
  doble), `optio`.
- **Sistema:** `via` (FS), `exsecutor` (procesos), `ambitus` (entorno), `tempus` (tiempo),
  `terminus` (terminal), `globus` (glob), `cellula` (celdas).
- **Datos:** `iason` (JSON), `libra` (TOML aplanado), `digestum`
  (SHA-256/SHA-1/CRC-32/FNV-1a), `versio` (SemVer), `archivum` (tar).
- **Red y FFI:** `rete` (TCP), `nexus` (`CString`).

Todos los módulos nuevos implementan `Show` con `unveil ritual X for Show`, se resuelven
entre módulos por ruta (`std::via::read_to_string`) y usan el runtime como paso directo
(`foreign "pengu"` + `panic("passthrough")`).

## 3. Limitaciones resueltas (resumen)

El detalle con evidencia está en `scratch/LIMITATIONS_AUDIT.md` §4. Las más importantes:

- Constantes asociadas (`Int.MAX`, `Float.NAN`, `Int.from_str`) — A1.
- Variantes calificadas en expresión y patrón (`FloatClass.NaN`, `when FloatClass.Zero`) y
  `Less`/`Equal`/`Greater` como valores de `Ordering` — A2.
- Lambdas con cuerpo de bloque y `elseif` inline (comparadores multilínea en `sort_by`) — A3.
- `Range[T]` y `get(range)`/`split_at`/`replace_range`; destructuring desde expresión — A6.
- Resolución de tipos por módulo en LIR (antes un `rune` homónimo de otro módulo ganaba la
  firma) y `Show` de runes; variantes `some`/`ok`/`err` en patrones; `x == none` sin
  `PartialEq`; `for` sobre elementos no `Copy`; sufijos numéricos (`41_u64`); funciones
  asociadas de `rune`; visibilidad `pub` en módulos `std`; literales `Str` en `sigil`.
- Adaptadores de `Iterator` sobre `Vec` (20 métodos) — S7.
- `libra` aplana el TOML en vez de compartir el árbol de `iason` — S8b (cierra N42).
- `archivum` escribe tar ustar compatible con `tar -tf` del sistema — S9b.
- `match` anidado como expresión ya no revienta con `unreachable!()` — S11 (cierra N48).

## 3.1 Segunda tanda (T1–T6)

La tanda pedida tras crear `via`, `exsecutor`, `ambitus` y `tempus` vive en
`scratch/AUDIT_VIA_EXSECUTOR.md`: auditoría de V1–V12, plan T0–T6 y las limitaciones
nuevas N55–N61. Resumen de lo ganado:

- `via`: rutas tipadas (`Path`/`PathBuf`), `WalkOptions` con `follow_links`,
  `include_hidden`, `max_depth` y detección de ciclos, `FileType`, `Permissions`,
  `Metadata` por campos, `OpenOptions` encadenable, E/S por cantidad, `sync_all`,
  `sync_data`, `try_clone` y marcas de tiempo en milisegundos (`I64`).
- `exsecutor`: `Stdio` (`stdio_piped`/`stdio_inherit`/`stdio_discard`), redirección de los
  tres flujos, `Child.process_id`, `write_stdin`, `close_stdin`, `read_stdout`,
  `read_stderr`, `wait_with_output`, y getters de `Command` más `env_remove`.
- `tempus`: `Duration` acepta y expone segundos fraccionarios (`from_secs_f64`,
  `as_secs_f64`, `mul_f64`, `div_f64`), `subsec_micros`/`subsec_nanos`, y
  `SystemTimeError.duration`.
- `ambitus`: `var_os`.
- Lenguaje: A4, conversión `Str` ↔ `String` (argumentos, retorno, `return` y `bind`
  anotado; `String` → `&Str` solo para *places*), e interpolación con partes tipada
  `String`. Gate B pasa a `58/4/12/67/5`.

## 4. Pendiente (con motivo)

| Tema | Motivo | Dónde continuar |
|---|---|---|
| A4: coerción `Str` → `String` | diseño de coerción implícita; hoy se usa `String.from(&s)` | auditoría §2.6 |
| A5: slices `&[T]` | requiere tipos de vista y coerción array→slice | auditoría §2.7 |
| A7: move checking | soundness; hoy el checker no marca uso tras mover | auditoría §2.8 |
| `vinculum` / `frenum` | el lenguaje no tiene hilos ni tipos opacos; `Rc`/`Mutex` no son expresables | S9b |
| `rune Iter[T]` | generaliza los adaptadores a colecciones propias (N36) | S7b |
| `structura` ordenados | `==`/`Copy` sobre `T` genérico: hace falta `Clone`/`Copy` en bounds (N67) | tanda C |
| N62: asociadas de `ritual` genérico | la plantilla `impl<T>` choca con el `enum __State`; hoy se usa una función libre | tanda C |
| TLS/HTTP (`rete`) | requiere capa de transporte genérica y certificados | S10b |
| `nexus` con punteros | `unsafe_code = "forbid"` en el workspace; FFI cruda fuera de v1 (N38) | — |

## 4.1 Tercera tanda (C1–C5, 2026-11-15)

Auditoría y plan en `scratch/AUDIT_FUNIS_STRUCTURA.md`. Commits:

| Commit | Fase |
|---|---|
| `C1` | arreglos del checker: `Ord` sin recursión, inferencia genérica en llamadas cualificadas, `instantiations`, `builtin_pact`, coerción en campos de record, `PGS-E1305` (N58/N60/N62/N66) |
| `C2` | `std/structura.pengu` con pila, cola y cola doble genéricas + docs §23 + test de codegen |
| `C3` | `funis`: sección §22 revisada (adaptadores en el checker, N36) |
| `C4` | `libra`/`iason`/`digestum`/`versio`: sin diferidos pendientes en sus tablas |
| `C5` | `STATUS.md`, auditoría y corpus al día |

Gate B tras la tanda: **62 compilados / 4 declaraciones / 12 fragmentos / 63
fallos / 5 errores** (antes 59/4/12/66/5).

## 5. Cómo verificar

```bash
cargo test --workspace          # 558 tests; la suite compila y ejecuta Rust real
cargo clippy --workspace --all-targets   # sin warnings
```

La sonda de desarrollo (`scratch/tools/probe`) sigue disponible para probar fragmentos:

```bash
cargo build --manifest-path scratch/tools/probe/Cargo.toml
./scratch/tools/probe/target/debug/pengu-probe programa.pengu --run
```

Ojo: hay que recompilar la sonda tras tocar `std/*.pengu` (el `include_str!` se congela) y
en los commits con identificadores usar `git commit -F archivo` (las comillas invertidas de
`-m` ejecutan sustitución de comandos).

## 4. Trabajo posterior: alias de módulo y Gate B (2026-11-14)

Cierre de los dos huecos que quedaban entre la std implementada y el corpus de la spec.
Working tree sobre `c82b149` (sin commit todavía).

### Alias de módulo (`docs/STDLIB.md` §32.1)

`install_module_aliases` (`crates/pengu-hir/src/lower.rs`) instala, en el ámbito del módulo
`std` y **antes** de resolver los `summon`, un binding por alias: `int`, `string`, `math`,
`io`, `fs`, `process`, `env`, `time`, `ffi`, `cell`, `test`, `ops`, `iter`, `toml`, `json`,
`digest`, `semver`, `term`, `glob`, `archive`, `net`/`tls`/`http`. Así `summon std::env`
resuelve a `ambitus` sin casos especiales en `find_module_path`.

### Llamadas cualificadas por módulo

`env.args()`, `fs.read_to_string(path)`, `ffi.cstring_new(text)` no resolvían: el `Field`
trataba la base como valor y fallaba con `PGS-E2004 no se encuentra \`env\``. Ahora:

- **HIR** (`ExprKind::Field`): si la base es un `Path` que resuelve a un módulo, se busca el
  ítem en ese módulo, se comprueba visibilidad (`PGS-E2006`) y se registra la `Resolution`
  del `Field` sin bajar la base como valor.
- **Checker**: un `Field` resuelto a función se tipa como `Ty::Fn(params, ret)` y `call_ty`
  acepta el callee `Field` (genérico o no) sin caer en la rama de métodos.
- **LIR**: el `Call` cuyo callee es `Field` con `Res::Def` de función sin receptor se baja a
  `LExpr::Call`.
- **Importación de tipos integrados**: `summon std::ffi::CString` / `CStr` resuelve al
  primitivo (`bind_import` con `Res::Primitive`).

### FFI del corpus (§16.5)

- `CString.new(text)`: nuevo `LExpr::CStringNew` que emite
  `::std::ffi::CString::new(x).map_err(|_| ())`; el `else` del `bind` cuenta como manejo de
  `NulError`.
- `curse`: se baja a LIR (antes `PGS-E1901 "expresión no soportada en LIR B1"`) y el cuerpo
  se emite dentro de `unsafe` (`LFunction::has_curse`). El valor de un `curse` final se
  descarta cuando la función devuelve `Unit`.
- `&CString` → `&CStr`: coerción en `unify` (el checker ya no rechaza `puts(&message)`).

### Verificación

- `cargo test --workspace`: **562 tests**, 0 fallos.
- Gate B: `(55, 4, 12, 70, 5)` y **4 bloqueos completos** (53/1/12/75/5 y 7 al empezar).
- Limitaciones nuevas y abiertas (CStr unsized, A4, alias múltiple, `bind ok`, `NulError`):
  `scratch/LIMITATIONS_AUDIT.md` §3.1.

## 5. S6 cerrado: `nexus`/FFI completo (2026-11-14, esta sesión)

`std/nexus.pengu` tenía 7 funciones (`CString`); ahora tiene **17**, con la superficie
segura completa de `CString` y `CStr`, y la FFI está verificada de punta a punta contra
libc (`strlen`, `toupper`), no solo en el corpus.

Arreglos de compilador necesarios (todos con test):

1. **`curse` como sentencia** ya no convierte su última expresión en `return` de la
   función ni se come las sentencias siguientes (`crates/pengu-lir/src/lower.rs`,
   `lower_block_to` / `lower_stmt`).
2. **`match` exhaustivo**: el fallthrough tras el último brazo se marca
   `LTerm::Unreachable`. Antes obligaba a inicializar con `unreachable!()` locales
   definidos solo en un brazo cuando el tipo no tiene `Default` (panic al arrancar, p. ej.
   un `CString`).
3. **`CStr` por valor era *unsized*** (N49): `Ty::CStr` se emite como `&::std::ffi::CStr`,
   `&CStr` se normaliza a `CStr` y `ast_type` no duplica la referencia; `ty_has_ref` /
   `ty_rust_state` lo tratan como préstamo.
4. **Llamar a una función `curse` en código seguro** ahora da `PGS-E1602` (antes se
   permitía, contra `docs/LANGUAGE.md` §16.2).

Limitación nueva (N55): una vista `CStr` no puede guardarse en un `bind` y usarse después
(el state machine mueve la `CString` dueña; `error[E0597]`). Se usa como temporal; las
conversiones que copian (`cstring_to_str`, `cstring_to_string_lossy`, `cstr_to_cstring`) no
tienen el problema. N58: falta la coerción `Str` → `String` en **campos de record**.

Gate B: **59 compilados / 4 declaraciones / 12 fragmentos / 66 fallos / 5 errores**
(antes 58/4/12/67/5). Los 3 bloqueos completos restantes son de los ejemplos, no de la
stdlib: 504 (campos privados + N58), 2576 y 3874 (fragmentos con `ConfigError`/`AppError`).
El bloque 326 de §2.7 estaba mal tipado (`Map` con valores `Str` e `Int`) y se corrigió en
`docs/LANGUAGE.md`.

## 7. S7 cerrado: `funis` completo (2026-11-14)

`std/funis.pengu` no existía: los adaptadores estaban codificados a mano en la tabla de
`Ty::Iterator` y `summon std::iter` fallaba. S7a los completa:

- **13 adaptadores nuevos**: `filter_map`, `flat_map`, `flatten`, `chain`, `take_while`,
  `skip_while`, `reduce`, `product`, `for_each`, `inspect`, `fuse`, `max_by`, `min_by`.
  Tres capas: `VecAdapterKind` (`crates/pengu-lir/src/lir.rs`), el mapa nombre→kind y el
  filtro "solo sobre `Iterator`" (`crates/pengu-lir/src/lower.rs`), las firmas de
  `method_signature` (`crates/pengu-types/src/check.rs`) y la emisión
  (`crates/pengu-codegen/src/codegen.rs`).
- **Un iterador se puede guardar en un `bind`**: `take`/`skip`/`step_by`/`rev` ahora
  envuelven en `Box::new(…)`. `rev` materializa (O(n) de memoria) porque
  `Box<dyn Iterator>` no implementa `DoubleEndedIterator`.
- **`Str.chars()`/`bytes()`/`char_indices()`**: `VecAdapterKind::StrChars/StrBytes/StrCharIndices`;
  cierran tres diferidos de S2.
- **Cuerpos de lambda**: se renderizan desde el AST (`lower_ast_expr`), no por LIR. Se
  añadieron `none`, `some`/`ok`/`err`, `print`/`format`, `Vec[…]`/`[…]`, interpolación y
  records; sigue siendo un subconjunto (N59).
- `std/funis.pengu` queda como módulo de documentación (`scroll funis` sin items): la
  superficie no se puede declarar en Pengu hasta que `Iter[T]` sea un tipo nominal (N36).

Tests: `std_funis_adapters_compile_and_run`, `std_funis_str_chars_compile_and_run`,
`std_funis_bind_adapted_iterator`. Suite: **573 tests**.

**S7b (`structura`) no se implementó**: `VecDeque`/`BTreeMap`/`BTreeSet`/`BinaryHeap`/
`LinkedList` no existen como tipos del lenguaje y un `rune` que los imite necesita comparar
`K` (`[T: Ord]` da `PGS-E2004`; con el pacto importado, el compilador desborda la pila). Ver
N60 en `scratch/LIMITATIONS_AUDIT.md`. Rutas posibles: (a) 5 tipos integrados nuevos con
paso directo a Rust (≈150 sitios de `match` sobre `Ty`), o (b) arreglar los bounds genéricos
y escribirlos en Pengu.

## 8. S8 cerrado: `libra`, `iason`, `digestum` y `versio` completos (2026-11-15)

- **`digestum`**: SHA-512 (`sha512`, `sha512_hex`, `sha512_text`), `hmac_sha256`,
  `hmac_sha256_text` y `constant_time_eq`. Todo en Rust puro; verificado contra
  `sha512("abc")` y los vectores de RFC 4231.
- **`iason`**: `equals` (comparación estructural), `get_path("a.b.0")` y mutadores
  `push`/`insert`/`set`/`remove` sobre `@mut Json`. Los parámetros `&Json` se pasan con `&`.
- **`libra`**: tablas en línea aplanadas, arrays de tablas `[[x]]` con índice (`x.0.campo`),
  fechas/horas clasificadas como `date`/`time`/`datetime` y `get_array` (separador interno,
  admite comas dentro de los elementos).
- **`versio`**: `satisfies` acepta uniones `||`, conjunciones por espacios, comodines
  (`1.x`, `1.2.x`, `*`) y versiones incompletas que se rellenan con ceros.

Suite: **577 tests**. Tests nuevos: `std_digestum_sha512_and_hmac`,
`std_iason_mutators_and_paths`, `std_libra_inline_tables_and_dates`,
`std_versio_requirement_grammar`.

Limitación nueva (N61): asignar a un local dentro del brazo de un `match` cuya condición lo
presta (`current = next` tras `match current.get(k)`) da `PGS-E4108`; se evita sacando el
resultado a un `morph` y asignando en un `match` aparte. Relacionado: un préstamo de
`Vec.get(i)` guardado en un `bind` no sobrevive entre estados del state machine (E0597).

## 9. S9 cerrado: `terminus`, `globus` y `archivum`

- **`terminus`**: `clear_screen`, `move_cursor`, `hide_cursor`/`show_cursor`,
  `cursor_up`/`down`/`left`/`right`, `progress_bar` y `read_key` (sin modo crudo: se
  documenta como N63).
- **`globus`**: `find_with(pattern, root, max_depth, include_hidden, follow_links)`.
- **`archivum`**: `create_targz`/`entries_targz`/`extract_targz`, `create_zip`/`entries_zip`/
  `extract_zip` y `compress_gz`/`decompress_gz`. El escritor usa deflate *stored*; el lector
  implementa inflate completo (fijo y dinámico) y valida CRC/longitud de gzip.
- Verificado contra herramientas del sistema: `unzip -t`, `gzip -t`, `tar -tzf`.
- Tests: `std_archivum_zip_and_targz_roundtrip`, `std_s9_terminus_and_glob_helpers`.

## 10. B8 y Gate B cerrados

`crates/pengu-build/tests/gate_b_corpus.rs` clasifica los 146 bloques de
`docs/LANGUAGE.md` en cinco categorías y **no deja ningún fallo sin declarar**:
`unclassified.is_empty()` rompe la suite si aparece uno nuevo, y
`declared_hits == DECLARED_NON_EXECUTABLE.len()` obliga a retirar entradas que ya
compilan.

| Categoría | Bloques |
|---|---:|
| Compilados a Rust | 68 |
| Declaraciones `.d.pengu`/`foreign` | 4 |
| Fragmentos parseables / citas con nombres indefinidos | 56 |
| No ejecutables declarados con motivo | 13 |
| Ejemplos de error (`-- ERROR PGS-`) | 5 |
| **Bloqueos sin declarar** | **0** |

Arreglos de conformidad de la sesión: alias `UInt` ≡ `U32` en HIR/checker/codegen,
`&String` → `Str` en `coerce_strings`, `&[T]` normalizado a `Ty::Slice` (sin doble
préstamo), unificación `[T]` ↔ `&[T; N]`, `for` e índice sobre préstamos, y el ejemplo
§3.6 de `docs/LANGUAGE.md` con `unveil` en el `rune` y sus campos.

Los 13 declarados son fragmentos de la especificación (expresiones sueltas, citas que
dependen de la prosa, fuentes de `std`) o límites del lenguaje ya anotados: N71
(expresión de bloque en `bind`), N72 (`ritual[T]` sobre `rune` genérico), N73 (literal
`Str` en constructor de variante con `E = String`). Ningún bloqueo es de la stdlib.

`scratch/COMPILER_PLAN.md` §7.3/§7.4 marcan **B8 ✅** y **Gate B ✅**; el siguiente hito
es la Fase 5 de `scratch/TOOLING_PLAN.md` (paquetes git, lock y vendor).

## 11. Fase 5 cerrada: paquetes git, lock y vendor (2026-11-15)

La Fase 5 de `scratch/TOOLING_PLAN.md` está implementada y verificada. El plan de
detalle vive en `scratch/PHASE5_PLAN.md`; dos crates nuevos, sin dependencias externas:

- `crates/pengu-pkg` (16 módulos): `sha256`, `toml`, `source`, `tree_hash`, `cache`,
  `git`, `lock`, `manifest`, `tags`, `spec`, `resolver`, `ops`, `vendor`, `tree`.
- `crates/pengu-cli`: binario `pengu` con `fetch`, `tree`, `vendor`, `build`, `run`,
  `test`, `add`, `remove`, `update`, `version` y `help`.

Lo que hace hoy, con paridad Cargo/Go en lo que la norma pide:

| Capacidad | Implementación |
|---|---|
| Añadir por git | `pengu add --git URL [--tag\|--branch\|--rev]`; sin referencia elige la etiqueta más alta y, si no hay, la rama por defecto con aviso |
| Añadir local | `pengu add --path ../x` (el nombre se lee del `Tome.toml` del paquete) |
| Quitar / actualizar | `pengu remove`, `pengu update [dep]` (mueve tags y ramas; los `rev` nunca) |
| Lock determinista | `Tome.lock` versión 1, ordenado, con `commit`, `checksum` del árbol y `features` |
| Integridad | checksum canónico SHA-256 del árbol (ignora `.git`, `target`, `vendor`, `.pengu`, `Tome.lock`, `.pengu-checksum`) |
| Offline y `--locked` | `--offline` no toca la red; `--locked` falla con `PGS-E1804` si el lock no coincide; `--force` re-clona la caché |
| Vendor | `pengu vendor` copia y verifica; `--check` solo verifica; el build prefiere `vendor/` y detecta copias editadas (`PGS-E1808`) |
| Grafo | `pengu tree` con jerarquía, fuente y marca de ciclo/ausente |
| Plantillas | `pengu new <nombre> --template bin\|lib\|with-dependency`; `--template list`; el template con dependencia resuelve el lock sin red |
| Features | aditivas y unidas entre consumidores; una dependencia `optional` solo entra si su feature se activa |
| Ciclos y conflictos | `PGS-E1807` con el camino del ciclo, o conflicto de fuente/versión |

El build integra los paquetes **fusionándolos como módulos**: cada `lib.pengu` del lock se
envuelve en `scroll <nombre>` y se antepone al programa raíz, así que `summon <paquete>::item`
funciona sin compilación separada (decisión D2 del plan).

Verificación: **646 tests** en el workspace (incluye `48` de `pengu-pkg` y `7` unitarios +
`4` de integración de extremo a extremo de `pengu-cli`), `cargo fmt --all -- --check` limpio y
`cargo clippy --workspace --all-targets -- -D warnings` sin avisos.

## 12. Fase 6 cerrada: LSP base (2026-11-15)

- **Crate nuevo `pengu-lsp`** (sin dependencias externas): JSON-RPC con framing
  `Content-Length`, posiciones UTF-8/UTF-16, URIs `file:`/`pengu-std:`, log a
  archivo y servidor stdio con hilo lector, debounce de 120 ms y cancelación
  cooperativa.
- **Diagnósticos completos**: léxicos, sintácticos, de tipos y de ownership, con
  `source = "pengu"`, `code`, `relatedInformation` y versión del documento.
- **Features**: hover, definición (incluida la stdlib como documentos virtuales),
  completion (keywords, símbolos y métodos tras `.`), documentSymbol y formato
  conservador idempotente.
- **`pengu lsp`** en la CLI, con `PENGU_LSP_LOG` para depurar.
- **Editores**: `editors/vscode` (cliente JS propio, sin `npm install`),
  `editors/nvim/lua/pengu.lua` (Neovim 0.10+/LazyVim) e instrucciones para Vim
  y `coc.nvim` en `docs/LSP.md`; `editors/smoke.mjs` valida el protocolo real.
- **Rendimiento**: se corrigieron tres comportamientos cuadráticos — dos del CST
  (`Collector::add` y `token_owner`) y uno del parser JSON (validaba UTF-8 sobre
  el resto del mensaje en cada carácter). 9 000 líneas tardaban 85 s en parsear;
  ahora `didOpen` de 14 004 líneas tarda ~0,5 s y el de 40 004 líneas ~1,8 s en
  `release`. Presupuestos en `crates/pengu-lsp/tests/performance.rs` y
  `editors/bench.mjs`.
- **Límites**: `MAX_LINES` sube de 10 000 a 200 000 (el guardia real es
  `MAX_SOURCE_BYTES = 10 MiB`), documentado en `docs/FRONTEND.md`.
- **Verificación**: 715 tests de workspace, `cargo fmt --check` y
  `clippy -D warnings` limpios; Neovim 0.12 muestra los diagnósticos del
  servidor real y `editors/smoke.mjs` valida el protocolo de punta a punta.

## 13. Fase 7 cerrada: LSP avanzado y tamaños reales (2026-11-15)

- **Crate nuevo `pengu-layout`**: motor de layout propio con `#[repr(C)]` y
  `#[repr(C, u32)]` emitidos por el backend (`repr(u32)` en enums sin campos) y
  verificado contra `std::mem::size_of`/`align_of` de `rustc` en
  `crates/pengu-codegen/tests/layout.rs`.
- **Tamaños en el editor**: `hover` de ADT (`tamaño`, `alineación` y orden de
  campos), de función (`huella`), de `sigil` y de expresión; inlay hints
  `: Tipo · N B` en locales sin anotación; `pengu size` imprime la tabla del
  programa.
- **Features nuevas de LSP**: references, documentHighlight, prepareRename y
  rename (stdlib de solo lectura), semantic tokens full/range, inlay hints,
  signature help, code lens de `@@test`, folding, selection ranges,
  typeDefinition, implementation (pacto → `ritual … for`), code actions
  (`unveil` en campos privados), workspace symbols y call hierarchy por nombre
  dentro del archivo.
- **Descartado con motivo** (en `scratch/PHASE7_PLAN.md`): `documentLink` (los
  módulos no son archivos) y `workspace/didChangeWatchedFiles` (el overlay del
  editor es la fuente de verdad).
- Verificación: 728 tests, `fmt` y `clippy -D warnings` limpios.

## 14. Fase 8 cerrada: formatter, linter, docs, tests y fix (2026-11-15)

- **`pengu-fmt`** (crate nuevo): formateador de **tokens** con verificación
  semántica (relexa y compara `(kind, lexema)`), idempotente y con
  `PGS-E1805` cuando algo no cuadra. `pengu fmt [--check]` sobre archivos o
  directorios; la stdlib está formateada (`pengu fmt --check std`).
- **`pengu-lint`** (crate nuevo): 10 lints (`W1001`, `W1101`, `W1102`, `W1201`,
  `W1301`, `W1501`, `W2001`, `W6001`, `W6002`, `W9001`) con `--allow/--warn/
  --deny`, `--list` y `--std`; la stdlib no tiene avisos.
- **`pengu fix`**: solo correcciones seguras (import muerto, sentencia
  inalcanzable, `while true do` → `loop`), con `--dry-run`.
- **`pengu doc`** genera Markdown desde `---`/`--!` en `target/pengu/doc/`, y
  **`pengu test --doc`** convierte los bloques `pengu` de la documentación en
  `@@test` ejecutados en `target/pengu/doc-tests`.
- **`pengu bench`** mide lex/parse/lower/check/LIR/codegen y el total;
  **`pengu explain <código>`** lee `docs/LANGUAGE.md` embebido.
- **LSP**: `textDocument/formatting` delega en `pengu-fmt` (una sola
  implementación); se retiró el formateador conservador de `pengu-lsp`.
- **CI**: `.github/workflows/ci.yml` con `cargo fmt --check`, `clippy -D
  warnings`, `cargo test --workspace`, `pengu fmt --check std` y
  `pengu lint --std std`.
- Documentación de usuario en `docs/QUALITY.md`; plan y desviaciones en
  `scratch/PHASE8_PLAN.md` (`--watch` queda para la Fase 4).
- Verificación: **760 tests**, `fmt` y `clippy -D warnings` limpios.

## 15. Fase 4 cerrada: lowering, codegen y build/run reales (2026-11-15)

- **`pengu check`** (nuevo): `parse → lower_program → check_crate →
  check_ownership_with`, sin LIR, codegen ni Cargo; `--watch` repite al cambiar
  `*.pengu`/`Tome.toml` (polling 250 ms, sin dependencias). `build` y `check`
  comparten `analyze_with_packages`, así no divergen.
- **Ownership en el build**: `pengu-build` ahora ejecuta `pengu-check`; se
  corrigió el diagnóstico duplicado de "uso de un valor movido".
- **`pengu-json`** y **`pengu-sha256`** extraídos como crates compartidos
  (`pengu-lsp`/`pengu-build` y `pengu-pkg`/`pengu-build`).
- **Remapeo real de `rustc`** (`pengu-build/src/remap.rs`): `E0308: mismatched
  types` con span Pengu, nota `generado en \`src/main.rs:L:C\`` y el `rendered`
  completo; sin span se informa como `PGS-E2014` con nota.
- **Caché incremental** (`pengu-build/src/cache.rs`): fingerprint SHA-256 de
  manifiesto, fuentes propias, paquetes y stdlib en `target/pengu/cache.json`;
  `build` cacheado en 18 ms sin invocar a Cargo y `run` en 16 ms ejecutando el
  binario directamente. `emit` es idempotente (no cambia mtimes).
- **`examples/`**: `hola`, `numeros`, `config` y `archivos`, compilados y
  ejecutados por `crates/pengu-build/tests/examples.rs`, que además exige
  formato y cero avisos del linter.
- **Docs**: `docs/BUILD.md` (pipeline, `check`, caché, fingerprint, `watch`,
  remapeo, ejemplos); CI añade `pengu fmt --check examples` y
  `pengu lint examples`.
- Verificación: **773 tests**, `fmt` y `clippy -D warnings` limpios; Gate B
  sigue en 68 compilados / 13 declarados.

## 16. Fase 9 cerrada: bindgen (2026-11-15)

- **`crates/pengu-bindgen`**: `clang -Xclang -ast-dump=json -fsyntax-only` →
  IR (`records`, `enums`, `functions`, `constants`, `omitted`) → `.d.pengu`
  determinista. Mapeo de escalares con clave canónica (`unsigned long` ==
  `long unsigned`), `size_t`/`ssize_t`, tipos de `stdint.h`, punteros
  (`const char *` → `CStr`, `void *` → `Ptr[U8]`, estructuras opacas →
  `Ptr[U8]`), enums a `Int`. Se omiten con motivo variádicas, punteros a
  función, uniones, bitfields, campos anónimos y `long double`.
- **Declaraciones en el manifiesto**: `[declarations] nombre = "ruta.d.pengu"`;
  el build las baja como módulos (`lower_program_with_declarations`), valida
  nombre/extensión/existencia (`PGS-E2010`, `PGS-E2020`, `PGS-E2003`) y exige
  `[link]` para `abi "C"` (`PGS-E2023`).
- **Lenguaje**: `.d.pengu` admite constantes con valor (`MODO: Int = 1`) y
  `curse` funciona en posición de valor (rama de `match`).
- **ABI de `CStr`**: en `foreign "C"` se declara `*const c_char` y el call site
  convierte argumentos con `.as_ptr()` y el retorno con `CStr::from_ptr`.
  Sin esto, `&CStr` y su puntero gordo (16 B) corrompían la pila.
- **CLI**: `pengu bindgen` con `-I`, `-D`, `-o`, `--allow`, `--block`,
  `--check` y `-v` (lista omitidos).
- **Corpus**: `zlib.h` (37 funciones), `sqlite3.h` (191) y `stdio.h` generan
  declarados que `pengu check` acepta; `examples/zlib.pengu` llama a la
  biblioteca real y comprueba `zlibVersion()`.
- **Docs**: `docs/BINDGEN.md`; `TOOLING_PLAN.md` Fase 9 ✅.
- Verificación: **799 tests**, `fmt` y `clippy -D warnings` limpios.

## 17. Fase 11 cerrada: release, instaladores y extras (2026-11-15)

- **CLI de release** (`crates/pengu-cli/src/release.rs`): `pengu version --json`
  (`name`, `version`, `target`, `commit`), `pengu doctor` (binario, PATH,
  stdlib, compilador, `rustc`, `cargo`, `clang`, `git` y extensión de VS Code;
  `--json`, exit 1 solo si falla algo requerido), `pengu completions
  bash|zsh|fish` y `pengu man`.
- **Instaladores**: `scripts/install.sh` (POSIX; release con `SHA256SUMS` o
  `--from-source`; prefijo `~/.pengu`; PATH idempotente con bloque marcado en
  `~/.profile`/`~/.bashrc`/`~/.zshrc` y `fish_add_path`; completions y manual en
  `share/`; `--uninstall`), `scripts/install.ps1` (PATH de usuario, `.zip`,
  `Expand-Archive`, `Get-FileHash`; ASCII puro por PowerShell 5.1) y
  `scripts/install.bat` (mapea `--x` a `-X` y delega en PowerShell).
- **Empaquetado**: `scripts/package.sh` (tar.gz o zip, `SHA256SUMS`
  determinista, `VERSION`, `sbom.json` con los crates del workspace),
  `.github/workflows/release.yml` (matriz linux x86_64, macos x86_64/arm64,
  windows x86_64; valida que el tag coincida con la versión del crate; publica
  con `gh release create`).
- **Extensión de VS Code**: `scripts/vsix.mjs` sin `npm` (valida manifiesto,
  exige versión igual a `pengu version`, arma `[Content_Types].xml` +
  `extension.vsixmanifest` + `extension/`, comprime con `zip` o
  `Compress-Archive`, `--install` con `code --install-extension`);
  `scripts/install-extension.sh`/`.bat` como atajos. Publisher alineado a
  `penguscript`.
- **Pruebas**: `scripts/test-release.sh` hace el ciclo completo con un
  repositorio `file://` (empaquetar → instalar → `pengu run` → `doctor` →
  `.vsix` → desinstalar) y pasa; CI añade `sh -n`, `node --check`,
  `vsix --check`, instalación desde fuente y empaquetado.
- **Documentación**: `docs/INSTALL.md`, `docs/RELEASE.md`, `CHANGELOG.md`
  (entrada `Compiler 0.1.0`) y `README.md` con instalación y estado real.
- **Renuncias declaradas**: `pengu self update` (actualizar es re-ejecutar el
  instalador, D10) y `pengu debug`/`repl` (fuera del alcance de la fase).
- Verificación: **803 tests**, `fmt` y `clippy -D warnings` limpios;
  instalación desde release local y `doctor` en verde.

## 18. Editor: LSP y extensión de VS Code reparados (cierre del tramo)

La extensión de VS Code y el servidor no se entendían. Auditoría y arreglos,
con `scratch/EDITOR_PLAN.md` como plan:

- **Causa raíz**: la extensión solo mandaba `didOpen` desde
  `onDidOpenTextDocument`, evento que ya había ocurrido cuando la extensión se
  activa con el archivo abierto. El servidor nunca recibía el documento y
  respondía vacío a todo. Ahora, después de `initialize`, se manda `didOpen` de
  todos los `workspace.textDocuments` de tipo `pengu`, y las peticiones se
  encolan hasta que llega la respuesta de `initialize`.
- **Providers**: se registran los 19 que el servidor anuncia (antes 5): hover,
  completion, definition, typeDefinition, implementation, references,
  highlight, rename, signature help, folding, selection, documentSymbol,
  workspaceSymbol, formatting, inlay hints, code lens, semantic tokens, code
  actions y call hierarchy. Comandos `pengu.run`, `pengu.test`, `pengu.check`,
  `pengu.runTest`, `pengu.restartServer`, `pengu.showOutput`; atajos `F5`,
  `Ctrl+F5`, `Ctrl+Shift+B` con `editorLangId == pengu`.
- **Ejecutar**: lente «▶ Ejecutar programa» sobre `grimoire` (la emite el
  servidor, así la ven todos los editores) y lente «ejecutar test» sobre cada
  `@@test`; ambas guardan el documento y usan `pengu run`/`pengu test` en la
  raíz del proyecto, en un terminal reutilizado.
- **Autocompletado por contexto** (`crates/pengu-lsp/src/features.rs`): tras
  `summon ` se listan módulos del proyecto y `std::…`; tras `modulo::` los
  items del módulo (resolviendo también dentro de `std`); tras `.` los métodos
  (con receptor); en el resto, símbolos del archivo y palabras clave. Con
  `sortText`/`filterText` y `snippetSupport`.
- **Snippets**: `editors/vscode/snippets/pengu.json`, 24 plantillas.
- **Gramática**: la interpolación `#{…}` ahora es una región con
  `contentName` y patrones (números, palabras clave, operadores, funciones,
  variables, accesos), así que se colorea el contenido.
- **Robustez**: si `pengu` no está en PATH la extensión lo dice con acciones
  (instalar, configurar ruta, ver registro); barra de estado con el proceso.
- **Verificación**: `editors/smoke.mjs` (protocolo real: diagnósticos, hover,
  completion de módulos, hints, lente de ejecución, tokens) y
  `editors/check-extension.mjs` (activa la extensión con un `vscode` simulado,
  comprueba los 25 registros y que lanza `pengu lsp`); ambos en CI.
  `docs/EDITOR.md` documenta capacidades, atajos y depuración.
- Suite: **807 tests**, `fmt` y `clippy -D warnings` limpios; `.vsix`
  regenerado e instalado (`penguscript.pengu-lsp`).

