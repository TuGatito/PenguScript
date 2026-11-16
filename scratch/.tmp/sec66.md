<a id="sec-66-no-soportado"></a>
## 66. No soportado y diferido

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 estable |
| Palabras mágicas | — |
| Depende de | §1, §63 |
| Ejemplos ejecutables | `no` |

Esta sección separa lo que **no existe por diseño** de lo que está **diferido**
a una fase futura. Un lector no debe asumir que una feature de Rust ausente
es un olvido: cada fila tiene una razón y una alternativa.

### 66.1 No soportado por diseño

| Feature | Por qué no | Alternativa |
|---|---|---|
| Variables globales mutables | Rompen el análisis de ownership y la inicialización estática (§5, §6). | `sigil`, `relic`, `@@shared` + `Mutex`, paso explícito de estado. |
| `static mut` | Acceso sin sincronización; Rust lo está retirando. | `@@shared` + `Mutex`/`RwLock`/atomics, o `UnsafeCell` en `curse`. |
| Herencia de clases | Composición y traits son más predecibles; evita diamonds. | `rune` + `pact` + `ritual`; campos y delegación. |
| `this`/`self` como palabra | `@` es el receptor; `self` se reserva a Rust generado. | `@`, `@mut`, `@own`. |
| `null`/`nil`/`undefined` | Elimina una clase de errores; `Option` es explícito. | `?T`, `none`, `some`. |
| Truthiness | Un `if` solo acepta `Bool`; evita conversiones implícitas. | Comparar explícitamente; `if x != 0 then`. |
| Conversiones implícitas | Dificultan la inferencia y el codegen. | `as` para casts, `From`/`Into` explícitos. |
| Excepciones (`try`/`catch`) | `Result` es parte del tipo; no hay flujo invisible. | `!T`, `?`, `match`, `panic` para bugs. |
| `switch` | `match` cubre y verifica exhaustividad. | `match`/`when`/`else`. |
| `do`/`while` | `loop` + `break` es más general. | `loop` con condición y `break`. |
| `goto` | Rompe estructuras y drop scopes. | `loop`/`break`, funciones, máquinas de estado. |
| `++`/`--` | Mutación oculta y precedence confusa. | `x += 1`, `x -= 1`. |
| `===`/`!==` | No hay coerción; `==` ya es estricto. | `is`/`isnt`. |
| `typeof`/`instanceof` | No hay reflexión de runtime. | `match` sobre enums, traits, tipos estáticos. |
| `eval` | No hay compilación en runtime; seguridad. | Macros, `rust` block auditado, generación externa. |
| Metatablas/prototipos | Modelo nominal y estático. | `rune`, `pact`, `ritual`. |
| GC/ARC implícito | Coste e imprevisibilidad; ownership explícito. | `Rc`/`Arc` cuando se necesiten. |
| Reflexión de tipos | No hay metadata de runtime. | Traits, enums, macros declarativas. |
| Herencia múltiple/mixins | Ambigüedad de métodos y estado. | Composición + traits. |
| Operadores definidos por el usuario | Se limitan a los traits de §40. | `Add`, `Index`, `PartialEq`, etc. |
| `default` en parámetros | Variantes y sobrecargas complican el ABI. | Funciones con nombre, structs de opciones, `Option`. |
| Varargs | ABI y tipos variables. | Slice `&[T]`, tuplas, macros. |
| Sobrecarga por firma | Resolución ambigua y codegen complejo. | Nombres distintos, traits, genéricos. |
| `macro_rules!` con expansión AST | Las macros expanden tokens, no AST tipado. | `incantation` + macros declarativas; proc macros en Rust. |
| Proc macros definidas en PenguScript | Requieren un crate compilado por rustc. | Consumir proc macros de crates Rust (§45). |
| `static` con destructor | Rust no lo permite; orden de drop incierto. | `OnceLock`/`LazyLock`, `@@thread_local`, `sigil`. |
| `become`/tail calls garantizados | No es estable ni portable. | `loop`/retorno explícito. |
| `dyn*`/`async` trait objects arbitrary | Inestable. | `dyn Future`, `Pin<Box<dyn Future>>`. |
| `#[global_allocator]` múltiple | Rust permite uno; el lenguaje no elige por ti. | Uno explícito en `no_std`/binario. |
| `no_std` con `std` implícito | Debe ser explícito. | `@@no_std`, `core`/`alloc`. |

### 66.2 Diferido

| Feature | Estado | Fase/ADR | Alternativa actual |
|---|---|---|---|
| Especialización de traits | Diferido | §69 D21 | Traits + dispatch explícito. |
| `generic_const_exprs` | Diferido | §69 D22 | Const generics simples; arrays fijos. |
| Tipos dependientes | Diferido | §69 D23 | Genéricos + validación runtime. |
| `async` closures con `for<'a>` complejo | Parcial | §38, §50 | `dream (…) => …`; `Box::pin`. |
| `try` blocks | Diferido | §48 | Función/closures que retornan `!T`. |
| Generadores/`yield` | Diferido | §49 | `Iterator` manual o `impl Iterator`. |
| `c_variadic` | Diferido | §53 | `foreign` con firma fija; wrappers Rust. |
| `extern type` | Diferido | §53 | Puntero opaco + `size_of` conocido. |
| Allocator API | Diferido | §55 | `@@global_allocator` + `alloc`. |
| SIMD portable (`std::simd`) | Diferido | §51 | Intrínsecos/`rust` block; autovectorización. |
| `#[target_feature]` dinámico | Parcial | §52 | `rust` block auditado; funciones específicas. |
| Inline asm complejo | Parcial | §52 | `asm!`/`global_asm!` en `rust` block auditado. |
| `#[naked]` functions | Diferido | §55 | `global_asm!` + `extern "C"`. |
| `#[coverage]`/instrumentación fina | Parcial | §58 | `pengu test --coverage` con herramientas Rust. |
| Miri/valgrind integrados | Parcial | §58 | Ejecutar sobre Rust generado. |
| `cargo expand` nativo | Parcial | §58 | Expandir el Rust generado. |
| Proc macro attributes definidos en Pengu | No soportado | §45 | Crate Rust + `@@attr`. |
| Macros 2.0 (`decl macro`) | Diferido | §45 | `macro_rules!` estable. |
| `macro_metavar_expr` | Diferido | §45 | `macro_rules!` sin metavariables extra. |
| `const` traits | Diferido | §54 | `const fn` + `sigil`. |
| `const` closures | Diferido | §54 | `eternal` fn + `sigil`. |
| `const` allocation/`Vec` en const | Parcial | §54 | Arrays fijos, `MaybeUninit` en `curse`. |
| `no_std` async executor | Parcial | §50, §55 | Executor externo (`embassy`). |
| WASM con JS glue automático | Parcial | §55 | `wasm-bindgen` externo; `rust` block. |
| Cross-compilation automática | Parcial | §55 | `rustup target add` + linker. |
| `cargo` publish a registro propio | Parcial | §58 | `pengu publish` + configuración. |
| Formatter/linter 100% paridad Rust | Parcial | §58 | `pengu fmt`/`lint` + rustfmt/clippy. |
| LSP con todas las refactorizaciones | Parcial | §58 | `pengu lsp` básico; edits textuales. |
| REPL | No soportado | §58 | `pengu run` con archivo; sin JIT. |
| Hot reload | No soportado | §58 | Recompilar y reiniciar. |
| `goto`/etiquetas arbitrarias | No soportado | §14 | `loop` etiquetado. |

### 66.3 Reglas

1. Una feature `No soportado` no se acepta ni con `@@allow`; el parser la rechaza.
2. Una feature `Diferido` se rechaza con `PGS-E6601` y un enlace a esta tabla.
3. Una feature `Parcial` se acepta con la limitación documentada; si el usuario
   necesita más, usa un `rust` block auditado (§52) o una crate Rust.
4. No se añade una feature a la tabla sin sección, alternativa y estado.
5. Las features inestables de Rust no se exponen como si fueran estables.
6. `rust` block no es una feature del lenguaje: es un escape hatch auditado;
   su contenido no está garantizado por la especificación.
7. La tabla se revisa en cada release candidate; un cambio de estado requiere
   ADR (§69).

### 66.4 Criterios de aceptación

- [x] Cada fila tiene motivo/estado y alternativa.
- [x] No se confunde “no soportado” con “aún no implementado”.
- [x] Las features inestables están fuera del núcleo.
- [x] Las alternativas son expresables en el lenguaje.
- [x] El escape hatch `rust` está acotado y auditado.

[↑ Volver al índice](#indice)
