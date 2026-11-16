<a id="sec-69-adr"></a>
## 69. Decisiones de diseño (ADR)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | todas |
| Depende de | §1–§68 |
| Ejemplos ejecutables | `no` |

Cada decisión se registra una vez. “Alternativas” no es una lista de ideas
descartadas sin motivo: incluye por qué se rechazaron. Un cambio posterior
añade una ADR nueva; no reescribe la historia.

### 69.1 Formato

| Campo | Contenido |
|---|---|
| ID | `D0`–`D24` |
| Contexto | Fuerza o restricción que obliga a decidir. |
| Decisión | Regla normativa adoptada. |
| Alternativas | Opciones consideradas y razón de descarte. |
| Consecuencias | Efectos positivos, costes y deuda aceptada. |
| Estado | `cerrada`; un cambio crea `D25+`. |

### 69.2 Decisiones

| ID | Contexto | Decisión | Alternativas | Consecuencias |
|---|---|---|---|---|
| D0 | El usuario diseña y revisa en español; el código se lee como Rust. | Prosa en español; keywords, código y términos técnicos en inglés. | Todo en inglés. | Documento legible para el autor; mezcla deliberada de idiomas. |
| D1 | Rust 2024 es la edición estable objetivo y el codegen debe ser reproducible. | Rust 2024 estable; MSRV 1.85.0; probado con rustc 1.99.1. | Rust 2021; nightly por defecto. | Se pueden usar `let-else`, `async fn` en traits y `gen` no estable; sin nightly. |
| D2 | Un backend propio multiplica el trabajo y no garantiza la semántica de borrow. | Transpilador a Rust + Cargo; front-end propio; rustc es la autoridad final. | Backend propio; intérprete. | Reutiliza rustc; los errores de tipos/borrow se remapean; depende de Rust. |
| D3 | MoonScript/CoffeeScript usan indentación; los tabs son ambiguos. | 4 espacios; tabs prohibidos; `{}` solo para mapas/token trees. | Tabs; llaves obligatorias. | Parser determinista; editores deben configurar 4 espacios. |
| D4 | Se quiere una identidad mágica sin curvas innecesarias. | Sustantivos mágicos para ítems; verbos familiares para control. | Renombrar todos los keywords. | `rune`/`enchanting`/`pact`; `if`/`for`/`match` siguen siendo familiares. |
| D5 | La mutabilidad implícita es peligrosa con ownership. | `bind` inmutable; `morph` mutable; `=` reasigna; prohibidos en módulo. | `let`/`var`; mutable por defecto; `bind mut` (retirado). | No se olvida `mut`; no hay globales; más palabras que MoonScript. |
| D6 | `static mut` es una fuente de UB y el lenguaje no permite globales mutables. | `sigil` = `const`; `relic` = `static` inmutable; `static mut` no existe. | `const`/`static`; `static mut`. | Estado global solo con `@@shared` + sincronización. |
| D7 | Los defaults deben ser predecibles y alineados con Rust. | `Int` = `i32`; `UInt` = `u32`; `Float` = `f64`; `Str` = `str`; `String` = `String`. | `Int` = `isize`; `Str` = `String`. | Tipos explícitos; `Usize`/`Isize` para tamaños. |
| D8 | `Option`/`Result` son verbosos y el lenguaje quiere azúcar legible. | `?T` = `Option<T>`; `!T` = `Result<T, Error>`; `none`/`some`/`ok`/`err`; `?` postfijo. | Solo `Option`/`Result`; `T?`/`T!E`. | Azúcar sin ocultar el tipo; `!T` fija `Error`. |
| D9 | MoonScript presume “todo es expresión”; Rust tiene sentencias. | Bloques, `if`, `match`, `loop` y funciones son expresiones; `bind`/asignación son sentencias; `return`/`break`/`continue` son `Never`. | Asignación como expresión. | Se conserva la ventaja sin romper move semantics. |
| D10 | `spell` era verboso y `fn` es de Rust; `->` es característico. | `name = (params) -> Tipo`; retorno obligatorio; cuerpo indentado; `(params) => expr` para lambdas. | `spell` (retirado)/`fn`; retorno inferido en funciones. | `->` identifica funciones; lambdas capturan; parser sin ambigüedad. |
| D11 | La herencia de clases complica la composición y el layout. | `rune` = struct; `enchanting` = enum; sin herencia. | `class`/`extends`. | Composición + traits; no hay diamonds. |
| D12 | Se necesita dispatch estático y dinámico sin `self`. | `pact` = trait; `ritual` = impl; receptores `@`, `@mut`, `@own`. | `trait`/`impl`; `self`. | `@` es familiar para MoonScript; métodos explícitos. |
| D13 | `<>` choca visualmente con comparaciones y con la indentación. | `[T]` para genéricos; `[const N: Usize]`; lifetimes `'a`; turbofish `foo[Int](x)`; HRTB `for<'a>`. | `<>` para genéricos. | `[]` se comparte con indexación; el parser distingue por tipo. |
| D14 | Se quiere un manifiesto propio sin perder Cargo. | `Tome.toml` con `[cargo]` passthrough; archivo = `scroll`; `summon`/`unveil`. | Solo `Cargo.toml`; `mod`/`use`/`pub`. | Ecosistema Cargo accesible; una capa de validación propia. |
| D15 | `@` ya es el receptor; `#[...]` es de Rust. | `@@attr(...)`; inner `@@!attr(...)`; `@@derive`, `@@cfg`, `@@test`. | `#[...]`. | `@@` no se confunde con `@`; los atributos son explícitos. |
| D16 | Se necesita metaprogramación sin proc macros en PenguScript. | `incantation` = `macro_rules!`; invocación `name!(...)`; token trees `{}`/`()`/`[]`. | Macros solo desde Rust. | Macros declarativas; sin expansión AST tipada. |
| D17 | UTF-8 y ownership de strings deben ser explícitos. | `Str` no sizeado; `String` owned; interpolación `#{expr}`; raw/byte/C; sin indexación por bytes. | `Str` owned; single quotes para strings. | Sin corrupción UTF-8; `String` se construye explícitamente. |
| D18 | Los nombres de Rust para async/unsafe/FFI rompen la estética. | `dream`/`awaken`/`curse`/`foreign`/`chimera`; `rust` block auditado. | `async`/`await`/`unsafe`/`extern`. | Nombres mágicos consistentes; el escape hatch es visible. |
| D19 | Reimplementar la std es inviable y fragmenta el ecosistema. | `std`/`core`/`alloc` vía `summon`; sin runtime propio; crates vía `tome`; `print`/`format` en preludio. | Biblioteca propia. | Interop directa; el runtime es el de Rust. |
| D20 | El usuario exige un solo archivo con índice clickeable. | Un `docs/LANGUAGE.md`; anclas ASCII; plantilla; ejemplos compilables. | Varios archivos por tema. | Documento grande; navegación por índice y anclas. |
| D21 | Testing, docs y tooling deben ser parte del lenguaje, no un afterthought. | `@@test`; doc comments `---`; CLI `pengu`; rustfmt/clippy/rustdoc; source maps. | Herramientas externas sin integración. | Un solo toolchain; se apoya en herramientas Rust. |
| D22 | La spec y el compilador evolucionan por fases. | Semver para la spec; versión de compilador; edición Rust; MSRV; changelog. | Sin versionado. | Releases reproducibles; deprecaciones con ventana. |
| D23 | Rust no permite definir proc macros en otro lenguaje de forma estable. | Proc macros en crates Rust consumidas vía `tome`; `build.pengu` -> `build.rs`; `rust` block para casos extremos. | Proc macros en PenguScript desde el día 1. | Se acepta una dependencia de Rust para metaprogramación avanzada. |
| D24 | Las features inestables rompen la promesa de estabilidad. | Fuera del núcleo; opt-in con `@@feature` + nightly. | Incluirlas en el núcleo. | Núcleo estable; el usuario asume el riesgo del nightly. |
| D25 | El azúcar de colecciones indentadas necesitaba delimitadores y era ruidosa. | Las colecciones indentadas no llevan `[]`/`{}`; `Vec`/`Set` son marcadores; el cuerpo se clasifica por `clave: valor`. | Mantener delimitadores obligatorios. | Sintaxis MoonScript; requiere regla de clasificación y `do` para bloques. |

### 69.3 Consecuencias globales

1. El lenguaje no tiene runtime propio: hereda el de Rust y su modelo de
   memoria.
2. El compilador es un transpilador: la mayor parte de la semántica fina la
   decide rustc.
3. La sintaxis es más verbosa que MoonScript en bindings (`bind`/`morph`) y
   más estricta en tipos (retorno obligatorio, `Bool` estricto).
4. La magia está en los nombres y en la forma de declarar, no en efectos
   ocultos.
5. La compatibilidad con Rust es una prioridad: `rust` block y `foreign`
   existen para no bloquear casos límite.
6. La deuda principal es el parser de indentación y el sourcemap; se prueban
   con los ejemplos y validadores del repo.

### 69.4 Cómo cambiar una decisión

1. Abrir una ADR nueva (`D26+`) con contexto y alternativa.
2. Actualizar la sección afectada y §64/§65 si cambia el desugaring/código.
3. Actualizar §70 (changelog) y la matriz §63 si cambia la paridad.
4. Añadir/actualizar un ejemplo compilable.
5. No se reescribe una ADR cerrada; se marca como superada.

[↑ Volver al índice](#indice)
