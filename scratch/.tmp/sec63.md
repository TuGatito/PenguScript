<a id="sec-63-paridad-rust"></a>
## 63. Matriz de paridad Rust

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 estable, MSRV 1.85.0 |
| Palabras mágicas | todas |
| Depende de | §1–§59 |
| Ejemplos ejecutables | `no` |

### 63.1 Leyenda

| Estado | Significado |
|---|---|
| `Completo` | La construcción se expresa en PenguScript y se mapea a Rust sin pérdida semántica. |
| `Parcial` | Se expresa con una limitación documentada; el generador puede emitir Rust o exigir un `rust` block auditado. |
| `Diferido` | No está en el núcleo actual; hay una sección/ADR y una alternativa. |
| `No soportado` | No se puede expresar por diseño; se documenta la razón y la alternativa. |

`Parcial` no significa “roto”: significa que el usuario debe conocer una
restricción (por ejemplo, proc macros definidas en Rust). `Diferido` tiene
una fase o una decisión pendiente; no hay filas “TBD”.

### 63.2 Matriz

| # | Área de Rust | Sección(es) | Estado | Notas |
|---:|---|---|---|---|
| 1 | Items y declaraciones | §15, §28, §29, §31, §35, §41, §43 | Completo | `rune`/`enchanting`/`pact`/`ritual`/`essence`/`scroll`. |
| 2 | Visibilidad y paths | §41, §42 | Completo | `unveil`, `crate::`, `super::`; no `self::`. |
| 3 | Genéricos de tipo | §33 | Completo | `[T]`, turbofish. |
| 4 | Genéricos de lifetime | §33, §37 | Completo | `['a]`, `for<'a>`. |
| 5 | Const generics | §33, §54 | Completo | `[const N: Usize]`. |
| 6 | Bounds y `where` | §34 | Completo | Incluye `?Sized`, associated bounds. |
| 7 | Traits y defaults | §35 | Completo | `pact`; sin herencia de clases. |
| 8 | Associated types/consts/GATs | §36 | Completo | GAT con `where Self: 'a`. |
| 9 | `impl Trait` y RPITIT | §35, §36 | Completo | Incluye `async fn` en trait. |
| 10 | Trait objects (`dyn`) | §35 | Completo | Object safety la valida rustc. |
| 11 | Impls y coherencia | §31, §35 | Completo | Reglas de orphan de Rust. |
| 12 | Ownership/move | §16 | Completo | Sin GC. |
| 13 | `Copy`/`Clone`/`Drop` | §16, §21, §46 | Completo | `Drop` explícito. |
| 14 | Borrowing/NLL | §17 | Completo | Mismas reglas que rustc. |
| 15 | Lifetimes/elisión/variance | §18 | Completo | Tabla de elisión propia. |
| 16 | Referencias y raw pointers | §19 | Completo | Raw solo en `curse`. |
| 17 | Smart pointers | §20 | Completo | `Box`, `Rc`, `Arc`, `Cow`, etc. |
| 18 | Interior mutability | §20, §51 | Completo | `Cell`, `RefCell`, `Mutex`, `RwLock`, `UnsafeCell` en `curse`. |
| 19 | Primitivos/literales/overflow | §9 | Completo | Overflow checks siempre. |
| 20 | Strings/chars/UTF-8 | §10 | Completo | Sin indexación por byte. |
| 21 | Arrays y slices | §22 | Completo | `[T; N]`, `&[T]`, `&mut [T]`. |
| 22 | `Vec`/`VecDeque` | §23 | Completo | Incluye `VecDeque`. |
| 23 | Tuplas | §24 | Completo | Hasta 12 traits estándar. |
| 24 | Mapas y sets | §25 | Completo | `HashMap`, `HashSet`, `BTreeMap`, `BTreeSet`. |
| 25 | Otras colecciones | §26 | Completo | `LinkedList`, `BinaryHeap`; crates externas. |
| 26 | Rangos e indexación | §27 | Completo | `..`, `..=`, slicing seguro. |
| 27 | Structs | §28 | Completo | Named/tuple/unit. |
| 28 | Enums/discriminantes | §29 | Completo | `@@repr`, niche. |
| 29 | Pattern matching | §30 | Completo | Exhaustividad. |
| 30 | Type aliases/newtypes/casts | §32 | Completo | `as`, `From`/`Into`, `TryFrom`. |
| 31 | Operadores | §11, §40 | Completo | Sobrecarga vía traits. |
| 32 | Control de flujo | §8, §13, §14 | Completo | `if`, `match`, `loop`, `while`, `for`. |
| 33 | Funciones/recursión | §15 | Completo | Retorno explícito, cuerpo implícito. |
| 34 | Closures | §38 | Completo | `=>`, `move`, `Fn*`. |
| 35 | Function pointers/HOF | §39 | Completo | `fn` tipos y valores. |
| 36 | Módulos y prelude | §41 | Completo | `scroll`, `summon`. |
| 37 | Crates/packages/workspaces | §43 | Completo | `Tome.toml`; `[cargo]` passthrough. |
| 38 | Features y cfg | §47 | Completo | Aditivas; `@@cfg`. |
| 39 | Atributos | §44 | Completo | `@@`, `@@!`. |
| 40 | Derives estándar | §46 | Completo | 9 derives + externos. |
| 41 | Macros declarativas | §45 | Completo | `incantation` -> `macro_rules!`. |
| 42 | Proc macros (definición) | §45 | Parcial | Se consumen; definirlas requiere Rust. |
| 43 | Proc macros (consumo) | §44, §45, §46 | Completo | `@@derive`, `@@attr`, `name!`. |
| 44 | `Option`/`Result`/`?` | §48 | Completo | `?T`, `!T`, `?`. |
| 45 | `panic`/unwinding | §48, §52 | Completo | `panic`, `catch_unwind` en `curse`. |
| 46 | Iteradores | §49 | Completo | Adaptadores/consumidores. |
| 47 | Async/await | §50 | Completo | `dream`/`awaken`; executor externo. |
| 48 | `Future`/`Pin`/`Unpin` | §50 | Completo | `Pin` explícito. |
| 49 | Threads | §51 | Completo | `std::thread`, scoped threads. |
| 50 | `Send`/`Sync` | §51 | Completo | Auto traits de Rust. |
| 51 | Channels | §51 | Completo | `mpsc`, `sync_channel`. |
| 52 | Atomics/ordering | §51 | Completo | `Atomic*`, `Ordering`. |
| 53 | `OnceLock`/`LazyLock`/TLS | §51 | Completo | `@@thread_local`. |
| 54 | Rayon/paralelismo | §51 | Parcial | Dependencia externa; feature. |
| 55 | Unsafe | §52 | Completo | `curse` + `-- SAFETY:`. |
| 56 | Unions | §52 | Completo | `chimera` + `@@repr(C)`. |
| 57 | `transmute` | §52 | Completo | Solo en `curse`. |
| 58 | `MaybeUninit`/`ManuallyDrop` | §52 | Completo | Requiere `curse`. |
| 59 | Inline asm | §52 | Parcial | `asm!`/`global_asm!` vía `rust` block auditado. |
| 60 | FFI | §53 | Completo | `foreign "C"`, `@@no_mangle`, `repr(C)`. |
| 61 | Bindgen/cbindgen | §53 | Parcial | Herramientas externas; flujo documentado. |
| 62 | Const eval/`const fn` | §54 | Completo | `sigil`, `eternal`. |
| 63 | `no_std` | §55 | Completo | `core`/`alloc`. |
| 64 | Embebido | §55 | Parcial | Targets/`cortex-m`/`embassy`; depende de toolchain. |
| 65 | WASM | §55, §53 | Parcial | `wasm32-unknown-unknown`; JS glue externo. |
| 66 | Testing | §56 | Completo | `@@test`, `@@should_panic`, `@@ignore`. |
| 67 | Doc tests | §57 | Completo | `pengu doc --test`. |
| 68 | Benchmarks | §56 | Parcial | Harness externo (`criterion`/`divan`). |
| 69 | Property testing/fuzzing | §56 | Parcial | Crates externas (`proptest`, `cargo-fuzz`). |
| 70 | Documentación | §57 | Completo | `---`, `--!`, intra-doc links. |
| 71 | Formatter/linter/LSP | §58 | Completo | `pengu fmt`, `pengu lint`, `pengu lsp`. |
| 72 | Source maps/diagnósticos | §3, §58 | Completo | `sourcemap.json`; remapeo. |
| 73 | Build scripts | §47 | Completo | `build.pengu` -> `build.rs`. |
| 74 | Reproducibilidad/audit | §58 | Completo | `Tome.lock`, `pengu audit`. |
| 75 | Cross-compilation | §55, §58 | Parcial | Requiere target Rust instalado. |
| 76 | Miri/valgrind/sanitizers | §52, §58 | Parcial | Herramientas externas sobre Rust generado. |
| 77 | `cargo` ecosystem | §43, §58 | Completo | Passthrough y comandos propios. |
| 78 | `rustfmt`/`clippy` | §58 | Completo | Se ejecutan sobre Rust generado. |
| 79 | `cargo doc`/`rustdoc` | §57 | Completo | `pengu doc`. |
| 80 | `cargo publish`/registro | §58 | Completo | `pengu publish`; registro compatible. |
| 81 | `cargo expand` | §58 | Parcial | Solo sobre Rust generado. |
| 82 | Reflection/runtime eval | — | No soportado | Sin runtime/GC; usar macros/código explícito. |
| 83 | Herencia de clases | — | No soportado | `pact` + composición. |
| 84 | Excepciones | — | No soportado | `!T` + `?`. |
| 85 | Null/truthiness | — | No soportado | `?T`; `Bool` estricto. |
| 86 | Globales mutables | — | No soportado | `sigil`/`relic`/`@@shared`. |
| 87 | `static mut` | — | No soportado | `@@shared` + `Mutex`/atomics. |
| 88 | GC/ARC implícito | — | No soportado | Ownership; `Rc`/`Arc` explícitos. |
| 89 | Metatablas/prototipos | — | No soportado | Tipos nominales. |
| 90 | `goto`/`switch`/`do-while` | — | No soportado | `loop`, `match`, `while`. |

### 63.3 Reglas de mantenimiento

1. Toda fila `Parcial` debe enlazar a una sección y explicar la limitación.
2. Toda fila `Diferido` debe tener una fase/ADR y una alternativa.
3. Toda fila `No soportado` debe explicar el motivo y la alternativa.
4. Si una feature de Rust no aparece, se añade antes de un release candidate.
5. La matriz se revisa en cada fase que añada una construcción nueva.
6. `Completo` no promete paridad de APIs de `std`; promete paridad de la
   construcción del lenguaje y su mapeo.
7. Las features inestables de Rust no se exponen; se documentan en §66.
8. Las herramientas externas se marcan `Parcial` aunque el flujo esté probado,
   porque su disponibilidad no la controla PenguScript.

### 63.4 Criterios de aceptación

- [x] No hay filas vacías ni `TBD`.
- [x] Cada fila tiene sección o “—”.
- [x] Cada `Parcial`/`Diferido`/`No soportado` tiene nota.
- [x] La matriz cubre lenguaje, std, toolchain y ecosistema.
- [x] Las limitaciones de proc macros y herramientas externas son explícitas.

[↑ Volver al índice](#indice)
