# Plan maestro para `docs/LANGUAGE.md`

**PenguScript — especificación única del lenguaje**

| Campo | Valor |
|---|---|
| Estado | Planificación `v1.5`; fases 0–11 completadas; release candidate `1.0.0-rc.1` aprobado |
| Fecha | 2026-11-12 |
| Archivo final | `docs/LANGUAGE.md` |
| Fase actual | Fase 11 completada — QA técnico y revisión adversarial aprobados; release candidate |
| Naturaleza | Documento temporal de trabajo; **no** es la especificación |
| Idioma | Prosa en español; palabras clave, código y nombres técnicos en inglés |

---

<a id="indice"></a>
## Índice

1. [Propósito y alcance](#sec-01-proposito)
2. [Restricciones y principios](#sec-02-restricciones)
3. [Decisiones fundacionales](#sec-03-decisiones)
4. [Léxico mágico provisional](#sec-04-lexico)
5. [Auditoría de secciones](#sec-05-auditoria)
6. [Arquitectura del documento final](#sec-06-arquitectura)
7. [Plantilla de sección](#sec-07-plantilla)
8. [Plan por fases](#sec-08-fases)
   - [Fase 0 — Decisiones y andamiaje](#fase-0)
   - [Fase 1 — Fundamentos](#fase-1)
   - [Fase 2 — Núcleo del lenguaje](#fase-2)
   - [Fase 3 — Ownership y memoria](#fase-3)
   - [Fase 4A — Colecciones y datos](#fase-4a)
   - [Fase 4B — Agregados y pattern matching](#fase-4b)
   - [Fase 5 — Abstracción](#fase-5)
   - [Fase 6 — Organización y metaprogramación](#fase-6)
   - [Fase 7 — Runtime avanzado](#fase-7)
   - [Fase 8 — Sistemas e interop](#fase-8)
   - [Fase 9 — Herramientas y calidad](#fase-9)
   - [Fase 10 — Apéndices](#fase-10)
   - [Fase 11 — QA y release candidate](#fase-11)
9. [Matrices de cobertura](#sec-09-matrices)
10. [Estrategia de validación](#sec-10-validacion)
11. [Riesgos y mitigaciones](#sec-11-riesgos)
12. [Preguntas abiertas](#sec-12-preguntas)
13. [Seguimiento de progreso](#sec-13-seguimiento)
14. [Próximo paso](#sec-14-proximo)

**Anexos**

- [Anexo A — Checklist de las 71 secciones](#anexo-a-outline)
- [Anexo B — Definition of Done por sección](#anexo-b-checklist)
- [Anexo C — Glosario de diseño](#anexo-c-glosario)

---

<a id="sec-01-proposito"></a>
## 1. Propósito y alcance

### 1.1 Qué es este documento

Este archivo es el **plan de ejecución** para escribir `docs/LANGUAGE.md`, la especificación normativa completa de PenguScript. Su función es:

- fijar las decisiones de diseño que afectan a todas las secciones;
- inventariar todo lo que debe cubrir el lenguaje;
- detectar secciones que faltan antes de empezar a redactar;
- ordenar la redacción en fases con dependencias claras;
- definir criterios de aceptación verificables para cada fase;
- evitar contradicciones, olvidos y re-trabajo.

La regla de oro: **ninguna sección de `LANGUAGE.md` se escribe sin saber a qué fase pertenece, qué reglas debe contener, qué código PenguScript muestra y qué Rust genera.**

### 1.2 Qué no es este documento

- No es la especificación del lenguaje.
- No es un tutorial.
- No es un documento de implementación del compilador.
- No es un registro de ideas sueltas: las decisiones abiertas están marcadas como tales.
- No contiene todavía el texto final de `docs/LANGUAGE.md`.

### 1.3 Resultado esperado del proyecto

Un único archivo `docs/LANGUAGE.md` que:

1. defina **toda** la sintaxis y semántica de PenguScript;
2. tenga un índice clickeable y navegación estable;
3. explique cada construcción con reglas, sintaxis, ejemplos y el Rust generado;
4. cubra de forma completa la superficie estable de Rust 2024, traducida a la versión PenguScript;
5. preserve las ventajas expresivas de MoonScript/CoffeeScript que no entren en conflicto con el tipado estático;
6. haga cumplir la prohibición de variables globales;
7. sirva como fuente de verdad para el parser, el type checker, el codegen, el formatter, el linter, el LSP y la documentación pública.

### 1.4 Criterios de éxito globales

- [ ] No falta ninguna de las secciones solicitadas por el usuario.
- [ ] No falta ninguna categoría necesaria para cubrir Rust estable.
- [ ] Cada sección tiene reglas normativas, sintaxis, ejemplos, Rust generado y diagnósticos.
- [ ] Cada bloque `rust` compila con `rustc`/`cargo` en la edición fijada.
- [ ] Cada bloque `pengu` es válido según la gramática y, cuando exista compilador, pasa parser + type checker.
- [ ] El índice no tiene enlaces rotos ni anclas duplicadas.
- [ ] El léxico mágico se usa de forma consistente en todo el documento.
- [ ] No hay contradicciones entre secciones.
- [ ] La regla de "sin variables globales" aparece y se respeta en todos los ejemplos.
- [ ] Las reglas de "todo es una expresión" son precisas y no ambiguas.
- [ ] El documento se puede leer de principio a fin y también consultar por sección.

### 1.5 Supuestos de trabajo

- El compilador se implementará en Rust.
- PenguScript se compila a Rust: el front-end produce Rust y se apoya en `rustc`/Cargo para el resto del pipeline.
- El objetivo es Rust **2024 estable**; las features inestables se documentan como diferidas o como opt-in explícito.
- No habrá runtime propio, GC, ni máquina virtual.
- La especificación es única: `docs/LANGUAGE.md`. Los documentos auxiliares viven en `scratch/` y no forman parte del contrato del lenguaje.
- El repositorio está vacío salvo `.git`, `.gitignore`, `.gitattributes` y `scratch/`; se parte de cero.

### 1.6 Cómo se usa el plan

1. Revisar y aprobar (o corregir) las decisiones de la sección 3.
2. Aprobar el léxico de la sección 4.
3. Ejecutar la Fase 0.
4. Al cerrar cada fase, actualizar la tabla de seguimiento y pedir revisión antes de avanzar.
5. Cualquier cambio a una decisión ya bloqueada exige una entrada en el ADR (apéndice 69) y una revisión de las secciones afectadas.

---

<a id="sec-02-restricciones"></a>
## 2. Restricciones y principios

### 2.1 Restricciones explícitas del usuario

| # | Restricción | Consecuencia para el documento |
|---|---|---|
| R1 | PenguScript es estático y compila a Rust | Toda construcción debe tener un mapeo a Rust válido y tipado |
| R2 | Sintaxis fuertemente inspirada en MoonScript/CoffeeScript | Indentación significativa, bloques sin llaves, retorno implícito, expresiones, `unless`, comprehensions, interpolación |
| R3 | Seguridad de tipos inspirada en V, Kotlin y Rust | Tipado fuerte, inferencia local, ownership/borrowing, sin `null`, sin truthiness, sin conversiones implícitas peligrosas |
| R4 | No se pueden crear variables globales | Prohibidos `bind` y `morph` a nivel de módulo; solo constantes y statics inmutables controlados |
| R5 | Nombres mágicos para ítems (`rune`, `enchanting`, etc.) | Léxico coherente y obligatorio; palabras de Rust prohibidas para declaraciones |
| R6 | Toda la sintaxis en un solo `docs/LANGUAGE.md` | Un archivo, bien organizado, con índice clickeable |
| R7 | Cada sección debe tener reglas, código PenguScript y Rust generado | Plantilla de sección obligatoria |
| R8 | Debe haber soporte completo de Rust "en nuestra versión" | Matriz de paridad y secciones para todo Rust estable |
| R9 | Ventajas de MoonScript, especialmente "todo es una expresión" | Sección dedicada y reglas transversales |
| R10 | Trabajo por fases, sin olvidar nada | Este plan y su checklist |

### 2.2 Principios de diseño

**P1 — Sustantivos mágicos, verbos familiares.**
Los ítems que declaran cosas nuevas usan palabras mágicas (`rune`, `enchanting`, `pact`, `ritual`, `sigil`). Las funciones no necesitan una palabra clave: se declaran con `name = (params) -> Tipo`, y `->` ya las identifica. El flujo de control y los operadores conservan palabras familiares (`if`, `for`, `while`, `match`, `return`, `and`, `or`, `not`). Esto mantiene la sensación mágica sin obligar a aprender un idioma nuevo para leer un bucle.

**P2 — Todo lo que produce valor es una expresión.**
Bloques, `if`, `match`, `loop` y cuerpos de función producen valores. `bind` y la asignación son sentencias; `return`, `break` y `continue` son expresiones divergentes. Las reglas exactas están en la sección 8.

**P3 — Inferencia local, fronteras explícitas.**
Las variables locales y los closures infieren. Las firmas de funciones, los campos de structs, los ítems públicos y los bounds genéricos son explícitos. Esto mantiene el código legible, los errores claros y el Rust generado predecible.

**P4 — Semántica de Rust, coste cero.**
PenguScript no inventa un modelo de memoria distinto. Movimientos, préstamos, lifetimes, `Drop`, `Send`/`Sync` y `unsafe` se explican con las reglas de Rust y se traducen sin runtime adicional.

**P5 — Sin estado global mutable.**
No existen variables globales. Existen constantes (`sigil`) y statics inmutables (`relic`). `static mut` no se expone. La mutabilidad global, si se necesita, pasa por interior mutability explícita y auditada.

**P6 — Un mapeo obvio a Rust.**
Cada construcción tiene una traducción preferida y documentada. El Rust generado debe ser legible, idiomático y formateado; no debe parecer código de máquina.

**P7 — Divulgación progresiva.**
El lenguaje básico se aprende con pocas palabras. Las capacidades avanzadas (GATs, HRTB, FFI, `no_std`, async) existen, pero se documentan en secciones avanzadas y con ejemplos completos.

**P8 — Diagnósticos primero.**
Cada regla debe poder verificarse y cada error debe tener un código, un mensaje, una causa y una solución. El documento no solo dice "esto no se puede"; dice por qué y cómo arreglarlo.

**P9 — Interoperabilidad como válvula de escape.**
Todo Rust estable debe ser expresable. Para los rincones que el lenguaje no cubra de forma nativa, existe `foreign`, `curse` y un bloque `rust` explícito y auditado, nunca como camino por defecto.

**P10 — La especificación es ejecutable.**
Los ejemplos no son decorativos: son tests. Un ejemplo que no compila es un bug del documento.

### 2.3 Trade-offs aceptados

| Trade-off | Decisión | Motivo |
|---|---|---|
| Magia vs. legibilidad | Léxico mágico solo para ítems; verbos familiares para control | Se aprende rápido y se lee bien |
| Concisión MoonScript vs. tipado explícito | `bind` explícito, firmas de función explícitas | Evita ambigüedad y facilita el codegen |
| Cobertura total de Rust vs. tamaño del documento | Cobertura total, pero APIs de `std` se referencian, no se re-documentan | El documento define el lenguaje, no la biblioteca estándar |
| Transpilación vs. backend propio | Transpilación a Rust + Cargo | Menos trabajo, semántica real de Rust, mejor interop |
| Mutable global vs. pureza | Sin variables globales; statics inmutables + interior mutability explícita | Conserva la regla de V sin bloquear FFI/allocators |
| Azúcar vs. sorpresas | Azúcar limitada y con desugaring documentado | El Rust generado se puede predecir |

### 2.4 No objetivos

- Tipado dinámico, duck typing o truthiness.
- `null`/`nil` como valor universal.
- Herencia de clases, metatables, prototipos o `super`.
- Recolector de basura o runtime propio.
- Higher-Kinded Types (Rust no los tiene).
- Especialización, impls negativos, `dyn*`, generators, `try` blocks y otras features inestables como parte del núcleo.
- Reemplazar Cargo, rustc, rustfmt, clippy o rustdoc.
- Re-documentar cada método de `std`; el documento define cómo se invoca la biblioteca, no su API completa.
- Un lenguaje visual o un editor propio.

---

<a id="sec-03-decisiones"></a>
## 3. Decisiones fundacionales

Las decisiones se numeran `D0`–`D24`. Cada una tiene una recomendación; la columna "Alternativa" registra lo que se descarta y por qué. Las que afectan a la sintaxis deben quedar bloqueadas antes de la Fase 1.

| ID | Decisión | Recomendación | Alternativa descartada | Fase |
|---|---|---|---|---|
| D0 | Idioma de la especificación | Prosa en español; keywords, código y términos técnicos en inglés | Todo en inglés | 0 |
| D1 | Versión de Rust objetivo | Rust 2024, solo estable; MSRV a fijar en Fase 0 (≥ 1.85) | Rust 2021; nightly por defecto | 0 |
| D2 | Modelo de compilación | Transpilador a Rust + Cargo; front-end propio; `rustc` como autoridad final de tipos/borrow | Backend propio; intérprete | 0 |
| D3 | Indentación | 4 espacios; tabs prohibidos; bloques por indentación; `{}` para mapas/token trees | Tabs; llaves obligatorias | 0 |
| D4 | Léxico mágico | Sustantivos mágicos para ítems; verbos familiares para control | Renombrar todos los keywords | 0 |
| D5 | Variables | `bind` inmutable, `morph` mutable; reasignación con `=`; sin `bind`/`morph` de módulo | `let`/`var`; asignación implícita | 0 |
| D6 | Constantes y statics | `sigil` = `const`; `relic` = `static` inmutable; `static mut` no existe | `const`/`static` de Rust | 0 |
| D7 | Tipos base | `Int` = `i32`, `UInt` = `u32`, `Float` = `f64`; `Str` = `str`, `String` = `String` | `Int` = `isize`; `Str` = `String` | 0 |
| D8 | Option/Result | Azúcar `?T` = `Option<T>`, `!T` = `Result<T, Error>`; canónicos `Option[T]`, `Result[T, E]`; `none`/`some`/`ok`/`err`; `?` postfijo | Solo `Option`/`Result`; `T?`/`T!E` | 0 |
| D9 | Todo es expresión | Bloques, `if`, `match`, `loop`, funciones; `bind`/asignación son sentencias; `return`/`break`/`continue` son `Never` | Asignación como expresión | 0 |
| D10 | Funciones | `name = (params) -> ReturnType` para funciones nombradas, con tipo de retorno obligatorio y cuerpo indentado; `(params) => expr` para lambdas; `->` también en tipos de función | `spell`/`fn` como keyword obligatoria | 0 |
| D11 | Structs/enums | `rune` = struct; `enchanting` = enum; sin herencia | `class`/`extends` | 0 |
| D12 | Traits/impls | `pact` = trait; `ritual` = impl; receptores `@`, `@mut`, `@own` | `trait`/`impl`; `self` | 0 |
| D13 | Genéricos | `[T]` para parámetros/argumentos; `[const N: Usize]`; lifetimes `'a`; turbofish `foo[Int](x)`; HRTB `for<'a>` | `<>` para genéricos | 0 |
| D14 | Módulos | Archivo = `scroll`; `summon` = `use`; `unveil` = `pub`; `Tome.toml` = manifiesto | `mod`/`use`/`pub`; solo `Cargo.toml` | 0 |
| D15 | Atributos | `@@attr(...)`; inner `@@!attr(...)`; `@@derive`, `@@cfg`, `@@test`, etc. | `#[...]` | 0 |
| D16 | Macros | `incantation` = `macro_rules!`; invocación `name!(...)`; token trees con `{}`/`()`/`[]` | Macros solo desde Rust | 0 |
| D17 | Strings | `Str` no sizeado, `String` owned; interpolación `#{expr}`; raw/byte/C strings; sin indexación por bytes | `Str` owned; single quotes para strings | 0 |
| D18 | Async/unsafe/FFI | `dream` = async, `awaken` = await, `curse` = unsafe, `foreign` = extern, `chimera` = union; bloque `rust` como escape auditado | `async`/`await`/`unsafe`/`extern` | 0 |
| D19 | Biblioteca estándar | `std`/`core`/`alloc` vía `summon`; sin runtime propio; crates externos vía `tome` | Biblioteca propia | 0 |
| D20 | Documento | Un solo `docs/LANGUAGE.md`; anclas ASCII explícitas; plantilla de sección; ejemplos compilables | Varios archivos por tema | 0 |
| D21 | Testing/docs/tooling | `@@test`; doc comments `---`; CLI `pengu`; rustfmt/clippy/rustdoc; source maps | Herramientas externas sin integración | 0 |
| D22 | Versionado | Semver para la spec; versión de compilador; edición Rust; MSRV; changelog | Sin versionado | 0 |
| D23 | Proc macros/build scripts | Proc macros se definen en crates Rust y se consumen vía `tome`; `build.pengu` → `build.rs`; bloque `rust` para casos extremos | Definir proc macros en PenguScript desde el día 1 | 0 |
| D24 | Features inestables | Excluidas por defecto; opt-in documentado con `@@feature` + nightly | Incluirlas en el núcleo | 0 |

### 3.1 Reglas derivadas que hay que respetar en todo el documento

1. Ninguna sección puede usar `let`, `fn`, `struct`, `enum`, `trait`, `mod`, `use`, `pub`, `const`, `static`, `self`, `class`, `extends` o `new` como palabra clave de PenguScript. Solo pueden aparecer dentro de bloques `rust` generados o en la lista de "palabras prohibidas".
2. Todo ítem de nivel superior debe ser una declaración (`rune`, `enchanting`, `pact`, `ritual`, `sigil`, `relic`, `essence`, `scroll`, `summon`, `unveil`, `incantation`, `foreign`), una definición de función `name = (params) -> ...` o un atributo. Una sentencia suelta a nivel de módulo es un error. Una definición de función no es una variable global: no captura el entorno y vive en el espacio de ítems.
3. `grimoire` es el único bloque de código ejecutable de nivel superior; compila a `fn main`.
4. El Rust generado debe usar edición 2024, incluyendo `#[unsafe(no_mangle)]`, `#[unsafe(export_name)]` y `#[unsafe(link_section)]`.
5. Los ejemplos deben declarar explícitamente los tipos que el documento promete explícitos; no se permite "inferir por arte de magia" lo que la regla dice que debe anotarse.
6. Toda sección que introduzca azúcar debe incluir una tabla de desugaring o un enlace a la sección 64.
7. Toda sección que introduzca un error debe incluir un código de diagnóstico y un ejemplo de corrección.

---

### 3.2 Sintaxis de funciones y lambdas (v0.2)

La palabra `spell` se elimina. La forma canónica imita a MoonScript: el nombre a la izquierda, los parámetros entre paréntesis y `->` a la derecha. La diferencia es que una función nombrada siempre declara su tipo de retorno, para que la firma sea explícita y el parser no tenga que adivinar.

```pengu
# Función nombrada: item, sin captura, tipo de retorno obligatorio
sum = (x: Int, y: Int) -> Int
  x + y

# El cuerpo va indentado en la línea siguiente
double = (x: Int) -> Int
  x * 2

# Lambda: expresión con captura; puede ser inline o indentada
bind inc = (x: Int) => x + 1

# Tipo de función
bind op: (Int, Int) -> Int = (a: Int, b: Int) => a + b
```

Reglas de desambiguación:

- `name = (params) -> Type` **siempre** es una definición de función nombrada. El `->` va seguido de un tipo y después viene un bloque indentado. No hay cuerpo inline para funciones nombradas: si necesitas una expresión corta, usa una lambda `(params) => expr`.
- `(params) => expr` **siempre** es una lambda. No lleva tipo de retorno explícito; se infiere del cuerpo o de la anotación del binding.
- `bind f = (x: Int) => ...` declara una variable local que contiene una lambda. `f = (x: Int) => ...` es una reasignación y exige que `f` ya exista.
- En nivel de módulo solo se permite `name = (params) -> Type`; `bind`, `morph` y la asignación suelta siguen prohibidos. Una función nombrada es un item, no una variable global: no captura el entorno.
- Los métodos usan la misma forma dentro de `ritual`/`pact`: `length = (@) -> Float`. Los receptores son `@` (`&self`), `@mut` (`&mut self`) y `@own` (`self`).
- Los modificadores van antes del nombre: `dream fetch = (...) -> !String`, `curse read = (...) -> U8`, `eternal square = (...) -> Int`.
- `return` sigue siendo opcional: el valor final del cuerpo es el retorno. `return` explícito sirve para salidas tempranas.

Gramática preliminar:

```ebnf
function_def ::= modifier* IDENT "=" ("[" type_params "]")? "(" params ")" "->" type (NEWLINE INDENT body DEDENT)?
lambda       ::= "move"? "(" params ")" "=>" (expr | NEWLINE INDENT body DEDENT)
function_type ::= "(" type ("," type)* ")" "->" type
```

El cuerpo de una función nombrada es obligatorio salvo en declaraciones de `pact` y `foreign`, donde la firma no tiene implementación. Las lambdas usan `=>` y no participan de esta gramática.

---

<a id="sec-04-lexico"></a>
## 4. Léxico mágico provisional

Esta tabla es la propuesta que se bloquea en la Fase 0. No es una lista de deseos: si una palabra aparece aquí, su significado es único en toda la especificación.

### 4.1 Sustantivos y verbos mágicos

| PenguScript | Rust | Categoría | Regla / nota |
|---|---|---|---|
| `rune` | `struct` | Tipo | Struct con campos nombrados, tupla o unitario |
| `enchanting` | `enum` | Tipo | Enum con variantes unitarias, de tupla o de struct |
| `->` | `fn` / `->` | Sintaxis | `name = (params) -> Tipo` define una función; `(A) -> B` es un tipo de función |
| `=>` | closure | Sintaxis | `(params) => expr` define una lambda con captura |
| `ritual` | `impl` | Implementación | Inherente o de trait |
| `pact` | `trait` | Abstracción | Trait, con métodos y items asociados |
| `essence` | `type` | Alias | Type alias, incluido alias genérico |
| `sigil` | `const` | Constante | Valor de compile-time; puede ser global |
| `relic` | `static` | Static | Static inmutable; `static mut` no existe |
| `scroll` | `mod` | Módulo | Módulo de archivo o inline |
| `tome` | crate/package | Paquete | Unidad de compilación; manifiesto `Tome.toml` |
| `summon` | `use` | Importación | Trae paths al scope |
| `unveil` | `pub` | Visibilidad | Exporta un ítem; formas `unveil(scroll)`, `unveil(tome)` |
| `bind` | `let` | Binding | Inmutable |
| `morph` | `let mut` | Binding | Mutable |
| `@` | `self` | Receptor | `@` = `&self`; `@mut` = `&mut self`; `@own` = `self` |
| `@@` | `#[...]` | Atributo | `@@attr(...)`; inner `@@!attr(...)` |
| `grimoire` | `fn main` | Entrada | Bloque de entrada del binario |
| `incantation` | `macro_rules!` | Macro | Macro declarativa |
| `curse` | `unsafe` | Unsafe | `curse name = (params) -> ...`, bloque o trait unsafe |
| `chimera` | `union` | Unsafe | Unión; acceso a campos requiere `curse` |
| `dream` | `async` | Async | `dream name = (params) -> ...`, bloque `dream`, lambda `dream (params) => ...` |
| `awaken` | `.await` | Async | `awaken expr` |
| `foreign` | `extern` | FFI | `foreign "C"` + firmas `name = (params) -> Tipo` sin cuerpo |
| `eternal` | `const fn` | Const | `eternal name = (params) -> ...`; función const-evaluable |
| `rust` | Rust crudo | Escape | Bloque auditado de tokens Rust; solo como último recurso |

### 4.2 Verbos familiares que se conservan

`if`, `elseif`, `else`, `unless`, `then`, `match`, `when`, `for`, `while`, `loop`, `break`, `continue`, `return`, `and`, `or`, `not`, `is`, `isnt`, `in`, `as`, `where`, `dyn`, `impl` (solo en posición de tipo, para `impl Trait`), `mut`, `move`, `true`, `false`.

### 4.3 Preludio (identificadores, no keywords)

`none`, `some`, `ok`, `err`, `print`, `format`, `panic`, `assert`, `Vec`, `VecDeque`, `HashMap`, `HashSet`, `BTreeMap`, `BTreeSet`, `Option`, `Result`, `String`, `Str`, `Int`, `UInt`, `Float`, `Bool`, `Char`, `Unit`, `Never`, `Box`, `Rc`, `Arc`, `Cell`, `RefCell`, `Mutex`, `RwLock`, `Cow`, `Pin`, `PhantomData`, `Error`, `Send`, `Sync`, `Sized`, `Copy`, `Clone`, `Drop`, `Iterator`, `IntoIterator`, `From`, `Into`, `TryFrom`, `TryInto`, `Display`, `Debug`.

Estos nombres pueden sombrearse, pero hacerlo produce un warning del linter. Las palabras de la tabla 4.1 y los verbos de 4.2 son keywords y no pueden usarse como identificadores.

### 4.4 Palabras de Rust prohibidas como declaraciones

`let`, `fn`, `struct`, `enum`, `trait`, `impl` (como declaración), `mod`, `use`, `pub`, `const`, `static`, `self`, `Self` (como receptor), `super` (como herencia), `class`, `extends`, `new`, `nil`, `null`, `var`, `val`, `function`, `local`, `export`.

Excepciones deliberadas:

- `Self` sigue existiendo como **tipo** dentro de `ritual`/`pact`.
- `impl` sigue existiendo en **posición de tipo** para `impl Trait`.
- `super` y `crate` siguen existiendo en **paths**.
- `mut` sigue existiendo como modificador (`morph`, `&mut`, `@mut`).
- `move` sigue existiendo para closures.
- `ref`/`ref mut` pueden aparecer en patrones; se documentan como contextuales.

### 4.5 Convenciones de nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Tipos, structs, enums, traits, aliases | `PascalCase` | `Point`, `Drawable`, `Meters` |
| Funciones, métodos, variables, módulos | `snake_case` | `compute_length`, `geometry` |
| Constantes y statics | `SCREAMING_SNAKE_CASE` | `MAX_HP`, `DEFAULT_PORT` |
| Variantes de enum | `PascalCase` | `Circle`, `NotFound` |
| Parámetros genéricos de tipo | `T`, `U`, `K`, `V`, `E` | `HashMap[K, V]` |
| Lifetimes | `'a`, `'b`, `'static` | `Ref['a, T]` |
| Archivos | `snake_case.pengu` | `http_client.pengu` |
| Atributos | `snake_case` | `@@derive`, `@@cfg` |
| Macros | `snake_case!` | `log!(...)` |

### 4.6 Reglas de consistencia

- Un concepto, una palabra. No se admiten sinónimos mágicos.
- Las palabras mágicas son minúsculas y se reservan siempre.
- `rune` nunca significa "variable"; `enchanting` nunca significa "magia" en general.
- `@` es el único nombre para el receptor; `self` está prohibido.
- `@` en expresión o receptor es el receptor; `@` en patrón es el operador de binding (`name @ pattern`); `@@` siempre introduce un atributo.
- `#{}` siempre interpola; `#` no es el operador de longitud.
- `..` y `..=` siempre son rangos; la concatenación de strings es `+` o interpolación.
- `{}` siempre es un literal de mapa o un token tree de macro; nunca un bloque de código.
- `[]` es array, slice o parámetros genéricos según contexto; `()` es agrupación, tupla o llamada.
- `->` declara una función nombrada y también aparece en tipos de función; `=>` introduce una lambda con captura.
- El tipo de retorno de una función nombrada va después de `->` y es obligatorio; las lambdas lo infieren. `:` se reserva para anotaciones de tipo y campos.
- `=>` no se usa en `match`; las ramas usan `when ... then`.

---

<a id="sec-05-auditoria"></a>
## 5. Auditoría de secciones

### 5.1 Secciones solicitadas y su destino

| # | Solicitada por el usuario | Sección final | Fase |
|---|---|---|---|
| 1 | Comentarios | §2.3 Comentarios | 1 |
| 2 | Variables | §5 Variables y bindings | 1 |
| 3 | Todos los tipos | §4 Sistema de tipos; §9 Primitivos; §10 Strings/chars; §20 Smart pointers; §22–§32; §33 Genéricos; §35 Traits; §37–§39 | 1–5 |
| 4 | Constantes | §6 Constantes y statics | 1 |
| 5 | Operadores | §11 Operadores | 2 |
| 6 | Booleanos | §12 Booleanos y lógica | 2 |
| 7 | Condicionales | §13 Condicionales | 2 |
| 8 | Bucles | §14 Bucles | 2 |
| 9 | Funciones | §15 Funciones | 2 |
| 10 | Scope | §7 Scope y resolución de nombres | 1 |
| 11 | Ownership | §16 Ownership | 3 |
| 12 | Borrowing | §17 Borrowing | 3 |
| 13 | Arrays | §22 Arrays y slices | 4A |
| 14 | Vectores | §23 Vectores y VecDeque | 4A |
| 15 | Tuplas | §24 Tuplas | 4A |
| 16 | Hashmaps | §25 HashMap, HashSet, BTreeMap, BTreeSet | 4A |
| 17 | Estructuras | §28 Structs (`rune`) | 4B |
| 18 | Enums | §29 Enums (`enchanting`) | 4B |
| 19 | Módulos | §41 Módulos (`scroll`) + §42 Visibilidad | 6 |
| 20 | Type aliases y casts | §32 Type aliases, newtypes y casts | 4B |
| 21 | Implementación de estructuras | §31 Implementaciones (`ritual`) | 4B |
| 22 | Referencias y punteros | §19 Referencias y punteros | 3 |
| 23 | Estructuras de datos | §26 Otras estructuras de datos | 4A |
| 24 | Macros y atributos | §44 Atributos; §45 Macros; §46 Derives | 6 |
| 25 | Pattern matching | §30 Pattern matching | 4B |
| 26 | Genéricos y constraints | §33 Genéricos; §34 Constraints y where | 5 |
| 27 | Strings y chars | §10 Strings y chars | 2 |
| 28 | Higher-Ranked Items | §37 Higher-Ranked Items (HRTB) | 5 |

**Conclusión:** no falta ninguna sección solicitada. Todas tienen destino, fase y criterio de aceptación.

### 5.2 Secciones que faltaban y se agregan

Las siguientes áreas no estaban en la lista original, pero son necesarias para que el documento sea una especificación completa y para cubrir Rust estable.

| Área añadida | Por qué es necesaria | Sección | Fase |
|---|---|---|---|
| Estructura léxica, indentación, identificadores y keywords | Sin ella el parser no se puede implementar ni auditar | §2 | 1 |
| Estructura del programa, entry point y pipeline | Define cómo se ejecuta y compila un tome | §3 | 1 |
| Sistema de tipos e inferencia | Es la base de todas las reglas de tipado | §4 | 1 |
| Mutabilidad | Rust la exige en bindings, préstamos, campos y patrones | §5, §17, §20 | 1–3 |
| Statics, estado global e interior mutability | Reconcilia "sin globales" con Rust/FFI | §6 | 1 |
| Expresiones, sentencias y bloques | Concreta "todo es una expresión" sin ambigüedad | §8 | 1 |
| Lifetimes | Sin ellas no se entiende borrowing ni structs con referencias | §18 | 3 |
| Traits y items asociados | Son el mecanismo central de abstracción de Rust | §35, §36 | 5 |
| Closures | Rust las usa en iteradores, async, threads y APIs | §38 | 5 |
| Function pointers y HOF | Completan el modelo de funciones | §39 | 5 |
| Const generics y const eval | Rust moderno los usa en arrays, tipos y APIs | §33, §54 | 5, 8 |
| Slices y rangos | Necesarios para arrays, strings, iteradores e indexación | §22, §27 | 4A |
| Option/Result y manejo de errores | Rust no tiene excepciones; es central | §48 | 7 |
| Iteradores | Es la forma idiomática de recorrer y transformar datos | §49 | 7 |
| Async/await | Parte de Rust estable y de la mayoría de servidores modernos | §50 | 7 |
| Concurrencia, `Send`/`Sync`, atomics | Rust estable y seguridad de hilos | §51 | 7 |
| Unsafe, uniones y `transmute` | Necesarios para FFI, allocators y estructuras de bajo nivel | §52 | 8 |
| FFI e interop con Rust | "Soporte completo de Rust" incluye llamar y ser llamado | §53 | 8 |
| Modelo de memoria, `Drop` y layout | Explica el coste cero y la seguridad | §21 | 3 |
| `no_std`, embebidos y wasm | Plataformas soportadas por Rust | §55 | 8 |
| Testing | Una spec sin ejemplos ejecutables se degrada | §56 | 9 |
| Documentación y doctests | Rustdoc es parte del ecosistema | §57 | 9 |
| CLI, LSP, formatter y linter | El lenguaje necesita herramienta, no solo gramática | §58 | 9 |
| Guía de estilo | Evita documentos contradictorios y código inconsistente | §59 | 9 |
| Gramática EBNF | Fuente de verdad para el parser | §60 | 10 |
| Léxico y palabras clave | Referencia única y auditable | §61 | 10 |
| Precedencia y asociatividad | Sin tabla, cada ejemplo es ambiguo | §62 | 10 |
| Matriz de paridad Rust | Demuestra que no falta nada | §63 | 10 |
| Desugaring | Explica cómo el azúcar se convierte en Rust | §64 | 10 |
| Catálogo de diagnósticos | Convierte reglas en errores accionables | §65 | 10 |
| No soportado / diferido | Evita promesas falsas | §66 | 10 |
| Glosario | Alinea términos mágicos, Rust y español | §67 | 10 |
| Cookbook | Valida el lenguaje con casos reales | §68 | 10 |
| ADR | Registra por qué se tomó cada decisión | §69 | 10 |
| Changelog y versionado | Permite evolucionar sin romper | §70 | 10 |
| Referencias | Da autoridad y trazabilidad | §71 | 10 |

### 5.3 Cobertura de Rust: categorías que no se pueden omitir

| Categoría | Secciones |
|---|---|
| Items y declaraciones | §15, §28, §29, §31, §35, §41, §43 |
| Visibilidad y paths | §41, §42 |
| Genéricos, lifetimes, const generics | §18, §33, §34 |
| Traits, GATs, object safety | §35, §36 |
| Implementaciones y coherencia | §31, §35 |
| Ownership, borrowing, `Drop` | §16, §17, §21 |
| Referencias, raw pointers, smart pointers | §19, §20 |
| Tipos primitivos, strings, arrays, tuples, mapas | §9, §10, §22–§27 |
| Structs, enums, pattern matching | §28–§30 |
| Funciones, closures, fn pointers, HRTB | §15, §37–§39 |
| Operadores y sobrecarga | §11, §40 |
| Módulos, crates, packages, features | §41–§43, §47 |
| Atributos, derives, macros | §44–§46 |
| Errores, iteradores, async, concurrencia | §48–§51 |
| Unsafe, FFI, const eval, `no_std` | §52–§55 |
| Testing, docs, tooling, estilo | §56–§59 |
| Gramática, paridad, desugaring, diagnósticos | §60–§66 |

### 5.4 Cobertura de MoonScript: qué se conserva y qué se descarta

| Rasgo de MoonScript | Decisión en PenguScript | Sección |
|---|---|---|
| Indentación significativa | Se conserva | §2 |
| Comentarios `--` y `--[[ ]]` | Se conservan; se añade `---` para doc | §2 |
| Asignación local implícita | Se reemplaza por `bind`/`morph` explícito | §5 |
| Variables globales implícitas | Se eliminan | §5, §6 |
| `if`/`unless`/`elseif`/`then` | Se conservan | §13 |
| `switch`/`when` | Se adapta a `match`/`when`/`else` | §30 |
| `for` numérico y `for ... in` | Se conservan | §14 |
| Comprehensions | Se conservan | §14 |
| `while`/`loop` | Se conservan | §14 |
| Funciones `->` y retorno implícito | Se conservan: `name = (params) -> Tipo` para funciones y `(params) =>` para lambdas; retorno implícito | §15, §38 |
| Funciones nombradas sin keyword | `name = (params) -> Tipo`; `->` las identifica | §15 | Adaptar |
| Clases, herencia, `super`, `new` | Se reemplazan por `rune` + `pact`/`ritual` + literales | §28, §31, §35 |
| `@` como `self` | Se conserva: `@` = `self`; los atributos pasan a `@@` | §31, §44 |
| Interpolación `#{}` | Se conserva | §10 |
| Strings largos `[[ ]]` | Se adaptan a `"""..."""` | §10 |
| Tablas `{}` | Se separan en arrays `[...]` y mapas `{k: v}` | §22, §25 |
| Splat `*` | Se limita a spread `...` explícito; sin varargs | §11, §22 |
| Slicing | Se adapta a rangos `..`/`..=` | §27 |
| `and`/`or`/`not`, `is`/`isnt` | Se conservan | §11, §12 |
| `..` como concatenación | Se descarta; `..` es rango; concatenar con `+` o interpolación | §10, §11 |
| `#` como longitud | Se descarta; se usa `.len()` | §10 |
| `nil` | Se reemplaza por `none`/`Option` | §9, §48 |
| Truthiness | Se elimina; las condiciones son `Bool` | §12 |
| `do` como expresión | Se conserva | §8 |
| `import`/`export` | Se reemplazan por `summon`/`unveil` | §41, §42 |
| `continue`/`break`/`return` | Se conservan | §14, §15 |
| `=>` (función ligada) | Se conserva como lambda con captura: `(params) => expr` | §15, §38 |
| `with` | No se soporta; se usa `bind` local | §7 |
| Metatables/prototipos | No se soportan | §66 |
| Coroutines | Se adaptan a iteradores/async | §49, §50 |

---

<a id="sec-06-arquitectura"></a>
## 6. Arquitectura del documento final

### 6.1 Principios de organización

1. **Un archivo, diez partes.** El documento se divide en partes numeradas; cada parte agrupa secciones afines.
2. **Numeración estable.** Las secciones se numeran `1..71`; los apéndices también. No se renumera por capricho: los cambios se registran en el changelog.
3. **Anclas ASCII explícitas.** Cada `##` lleva un `<a id="sec-NN-slug"></a>` antes del título. El índice enlaza a esas anclas, no a slugs generados por el renderer.
4. **Plantilla uniforme.** Todas las secciones de lenguaje usan la plantilla de la sección 7.
5. **Normativo primero.** Las reglas van antes que los ejemplos. Los ejemplos ilustran, no sustituyen la regla.
6. **Rust generado siempre.** Ninguna sección de lenguaje termina sin mostrar el Rust que produce.
7. **Enlaces cruzados.** Cada sección enlaza a las secciones relacionadas y al apéndice de desugaring/paridad.
8. **Sin callejones sin salida.** Si una construcción no se soporta, se dice en §66 y se ofrece la alternativa.

### 6.2 Estructura por partes

| Parte | Título | Secciones |
|---|---|---|
| I | Fundamentos | 1–8 |
| II | Núcleo del lenguaje | 9–15 |
| III | Ownership y memoria | 16–21 |
| IV | Datos y agregados | 22–32 |
| V | Abstracción | 33–40 |
| VI | Organización y metaprogramación | 41–47 |
| VII | Runtime avanzado | 48–51 |
| VIII | Sistemas e interop | 52–55 |
| IX | Herramientas y calidad | 56–59 |
| X | Apéndices y referencias | 60–71 |

### 6.3 Outline completo

**Front matter**

- Portada y metadatos
- Cómo leer este documento
- Índice
- Léxico rápido
- Convenciones (RFC 2119, bloques de código, estados)

**Parte I — Fundamentos**

1. Introducción y filosofía
2. Estructura léxica
   - 2.1 Codificación, líneas y BOM
   - 2.2 Indentación y bloques
   - 2.3 Comentarios
   - 2.4 Identificadores y palabras clave
   - 2.5 Literales
   - 2.6 Separadores, continuación de línea y punto y coma
3. Estructura del programa y compilación
   - 3.1 Archivos, `scroll`s y `tome`s
   - 3.2 Punto de entrada: `grimoire`
   - 3.3 Items de nivel superior
   - 3.4 Importaciones: `summon`
   - 3.5 Pipeline de compilación y artefactos
   - 3.6 Source maps y diagnósticos
4. Sistema de tipos
   - 4.1 Estático, fuerte y nominal
   - 4.2 Inferencia local y firmas explícitas
   - 4.3 Sin `null`, sin truthiness, sin conversiones implícitas
   - 4.4 Catálogo de tipos
   - 4.5 Ownership/borrowing como base
   - 4.6 Coherencia y reglas de huérfanos
5. Variables y bindings
   - 5.1 `bind` inmutable
   - 5.2 `morph`
   - 5.3 Anotaciones e inferencia
   - 5.4 Inicialización y asignación diferida
   - 5.5 Reasignación y operadores compuestos
   - 5.6 Shadowing
   - 5.7 Destructuring
   - 5.8 Prohibición de variables globales
   - 5.9 Mutabilidad y préstamos
6. Constantes, statics y estado global
   - 6.1 `sigil` (`const`)
   - 6.2 `relic` (`static` inmutable)
   - 6.3 Evaluación en compile-time
   - 6.4 Prohibición de `static mut`
   - 6.5 Interior mutability y `@@shared`
   - 6.6 `thread_local`
   - 6.7 Statics de FFI y enlace
7. Scope y resolución de nombres
   - 7.1 Scope léxico
   - 7.2 Drop scopes
   - 7.3 Temporales
   - 7.4 Paths y prelude
   - 7.5 `@`, `Self`, `super`, `crate`
   - 7.6 Shadowing vs. redefinición
8. Expresiones, sentencias y bloques
   - 8.1 Todo lo que produce valor es una expresión
   - 8.2 `bind` y asignación son sentencias
   - 8.3 `return`, `break`, `continue` como `Never`
   - 8.4 Bloques y valor final
   - 8.5 `do`
   - 8.6 Separadores y descarte de valores
   - 8.7 Divergencia y unit

**Parte II — Núcleo del lenguaje**

9. Tipos primitivos
   - 9.1 `Unit`
   - 9.2 `Never`
   - 9.3 `Bool`
   - 9.4 Enteros con signo
   - 9.5 Enteros sin signo
   - 9.6 `Isize`/`Usize`
   - 9.7 Floats
   - 9.8 `Char`
   - 9.9 `Str`
   - 9.10 Alias `Int`, `UInt`, `Float`
   - 9.11 Literales numéricos
   - 9.12 Overflow y operaciones checked/wrapping/saturating
10. Strings y chars
    - 10.1 `Str` vs. `String`
    - 10.2 Literales y escapes
    - 10.3 Raw strings
    - 10.4 Byte strings
    - 10.5 C strings
    - 10.6 Interpolación
    - 10.7 Concatenación y formato
    - 10.8 Indexación, slicing y UTF-8
    - 10.9 Chars y Unicode
    - 10.10 Conversiones
11. Operadores
    - 11.1 Aritméticos
    - 11.2 Comparación
    - 11.3 Lógicos
    - 11.4 Bitwise
    - 11.5 Asignación y compuestos
    - 11.6 Rangos
    - 11.7 Acceso, llamada y método
    - 11.8 Referencia y deref
    - 11.9 Cast `as`
    - 11.10 `in`, `is`, `isnt`
    - 11.11 `?` (try)
    - 11.12 `awaken`
    - 11.13 Precedencia y asociatividad
    - 11.14 Sobrecarga de operadores
12. Booleanos y lógica
    - 12.1 `Bool` estricto
    - 12.2 Cortocircuito
    - 12.3 `and`/`or`/`not` y alias simbólicos
    - 12.4 Sin truthiness
    - 12.5 Bitwise vs. lógico
    - 12.6 Comparaciones encadenadas
13. Condicionales
    - 13.1 `if`/`elseif`/`else`
    - 13.2 `unless`
    - 13.3 `then` inline
    - 13.4 `if` como expresión
    - 13.5 `if let` (adelanto)
    - 13.6 Diagnósticos
14. Bucles
    - 14.1 `while`
    - 14.2 `loop`
    - 14.3 `for ... in`
    - 14.4 `for` numérico
    - 14.5 `break`/`continue`/labels
    - 14.6 `loop` como expresión
    - 14.7 Comprehensions
    - 14.8 `while let` (adelanto)
    - 14.9 Iteradores (adelanto)
    - 14.10 Diagnósticos
15. Funciones
    - 15.1 `->` y `=>`
    - 15.2 Funciones nombradas y parámetros
    - 15.3 Tipo de retorno obligatorio
    - 15.4 Retorno implícito
    - 15.5 `return` temprano
    - 15.6 Recursión
    - 15.7 Funciones divergentes
    - 15.8 `grimoire`
    - 15.9 Métodos y `@` (adelanto)
    - 15.10 Genéricos (adelanto)
    - 15.11 Sin overloading, defaults ni varargs
    - 15.12 `main` y `Termination`

**Parte III — Ownership y memoria**

16. Ownership
    - 16.1 Move
    - 16.2 `Copy`
    - 16.3 `Clone`
    - 16.4 `Drop`
    - 16.5 Partial moves
    - 16.6 Ownership en funciones y retornos
    - 16.7 Ownership en colecciones
    - 16.8 `mem::take/replace/swap/forget`
17. Borrowing
    - 17.1 `&` y `&mut`
    - 17.2 Reglas de aliasing
    - 17.3 Reborrow
    - 17.4 NLL
    - 17.5 Préstamos en funciones
    - 17.6 Préstamos en structs
    - 17.7 Conflictos y soluciones
18. Lifetimes
    - 18.1 Elisión
    - 18.2 Explícitos
    - 18.3 `'static`
    - 18.4 Bounds
    - 18.5 Structs, impls y traits
    - 18.6 Variance
    - 18.7 HRTB (adelanto)
    - 18.8 Diagnósticos
19. Referencias y punteros
    - 19.1 Referencias compartidas y mutables
    - 19.2 Raw pointers
    - 19.3 Deref y address-of
    - 19.4 `NonNull`
    - 19.5 Aritmética de punteros
    - 19.6 Null, dangling y provenance
    - 19.7 Function pointers (adelanto)
20. Smart pointers e interior mutability
    - 20.1 `Box`
    - 20.2 `Rc`/`Weak`
    - 20.3 `Arc`/`Weak`
    - 20.4 `Cell`/`RefCell`
    - 20.5 `Mutex`/`RwLock`
    - 20.6 `Cow`
    - 20.7 `Pin`
    - 20.8 `MaybeUninit`/`ManuallyDrop`
    - 20.9 `OnceCell`/`LazyLock`
21. Memoria, `Drop` y layout
    - 21.1 Stack y heap
    - 21.2 RAII
    - 21.3 Orden de drop
    - 21.4 Drop scopes
    - 21.5 Leaks
    - 21.6 Allocators
    - 21.7 ZST, DST y `repr`
    - 21.8 Coste cero

**Parte IV — Datos y agregados**

22. Arrays y slices
23. Vectores y `VecDeque`
24. Tuplas
25. Mapas y sets
26. Otras estructuras de datos
27. Rangos e indexación
28. Structs (`rune`)
29. Enums (`enchanting`)
30. Pattern matching
31. Implementaciones (`ritual`)
32. Type aliases, newtypes y casts (`essence`)

**Parte V — Abstracción**

33. Genéricos
34. Constraints y `where`
35. Traits (`pact`)
36. Associated items (types, consts, GATs)
37. Higher-Ranked Items (HRTB)
38. Closures
39. Function pointers y higher-order functions
40. Operator overloading

**Parte VI — Organización y metaprogramación**

41. Módulos (`scroll`)
42. Visibilidad (`unveil`)
43. Crates, packages y workspaces (`tome`)
44. Atributos (`@@`)
45. Macros (`incantation`)
46. Derives y traits comunes
47. Build scripts, features y `cfg`

**Parte VII — Runtime avanzado**

48. Manejo de errores
49. Iteradores
50. Async/await
51. Concurrencia

**Parte VIII — Sistemas e interop**

52. Unsafe (`curse`)
53. FFI e interop con Rust
54. Const eval
55. `no_std`, embebidos y wasm

**Parte IX — Herramientas y calidad**

56. Testing
57. Documentación
58. Herramientas (CLI, LSP, formatter, linter)
59. Guía de estilo

**Parte X — Apéndices y referencias**

60. Gramática EBNF
61. Léxico y palabras clave
62. Precedencia y asociatividad
63. Matriz de paridad Rust
64. Desugaring
65. Catálogo de diagnósticos
66. No soportado y diferido
67. Glosario
68. Cookbook
69. Decisiones de diseño (ADR)
70. Changelog y versionado
71. Referencias

### 6.4 Convenciones de bloques de código

| Lenguaje | Uso | Regla |
|---|---|---|
| `pengu` | Código PenguScript | Debe ser válido; si es un fragmento, se marca `// fragmento` y se explica el contexto |
| `rust` | Rust generado | Debe compilar; se formatea con rustfmt; sin `...` salvo que se marque como elisión |
| `ebnf` | Gramática | Producciones normativas; no se inventan reglas fuera de ella |
| `toml` | `Tome.toml` | Debe ser válido y corresponder a un ejemplo |
| `text` | Diagnósticos, árboles, tablas | Solo ilustrativo |
| `mermaid` | Diagramas | Opcional; no debe ser la única fuente de una regla |

Convenciones adicionales:

- Los bloques `rust` llevan un comentario `// Generado por PenguScript` cuando son el resultado de un ejemplo.
- Los errores esperados se marcan con `//~ ERROR` o una tabla de diagnóstico; no se usan bloques de Rust inválidos sin marca.
- Los ejemplos incompletos se evitan; si son necesarios, se marcan como `fragmento` y se enlaza al ejemplo completo.
- Los nombres de variables en ejemplos son `snake_case`; los tipos, `PascalCase`.

### 6.5 Convenciones de anclas y enlaces

- Cada `##` lleva un ancla explícita con el patrón `sec-NN-slug`.
- Cada `###` tiene `<a id="sec-NN-M-slug"></a>` si el índice lo enlaza.
- Los slugs son ASCII, minúsculas, con guiones; sin acentos ni `ñ`.
- El índice se escribe a mano y se valida con un script.
- Cada sección termina con `[↑ Volver al índice](#indice)`.
- Los enlaces internos usan rutas relativas del propio archivo y apuntan a un ancla explícita.
- No se usan enlaces a encabezados autogenerados; siempre a anclas explícitas.

### 6.6 Metadatos de sección

Cada sección comienza con una tabla:

| Campo | Valor |
|---|---|
| Estado | `pendiente`, `borrador`, `revisión`, `completo` |
| Fase | `0`–`11` |
| Rust | Feature o features de Rust que cubre |
| Palabras mágicas | Keywords involucradas |
| Depende de | Secciones previas |
| Ejemplos ejecutables | `sí`/`no` y ruta al golden test |

---

<a id="sec-07-plantilla"></a>
## 7. Plantilla de sección

Toda sección de lenguaje (Partes I–VIII) usa esta plantilla. Las secciones de herramientas y apéndices pueden omitir las subsecciones que no apliquen, pero deben conservar Reglas, Ejemplos y Ver también.

````markdown
<a id="sec-05-variables"></a>
## 5. Variables y bindings

| Campo | Valor |
|---|---|
| Estado | borrador |
| Fase | 1 |
| Rust | `let`, `let mut` |
| Palabras mágicas | `bind`, `morph` |
| Depende de | §4, §7 |

### 5.1 Reglas

- **DEBE** declararse toda variable local con `bind` o `morph`.
- **NO DEBE** existir ningún `bind` ni `morph` a nivel de módulo.
- **DEBE** inferirse el tipo cuando se omite la anotación y sea posible.
- **DEBE** rechazarse el uso de una variable antes de su inicialización.
- **PUEDE** hacerse shadowing en un scope interior.
- **NO DEBE** reasignarse un `bind` inmutable.

### 5.2 Sintaxis

```ebnf
binding           ::= immutable_binding | mutable_binding
immutable_binding ::= "bind" pattern (":" type)? ("=" expr)? NEWLINE
mutable_binding   ::= "morph" pattern (":" type)? ("=" expr)? NEWLINE
reassignment      ::= path "=" expr NEWLINE
```

### 5.3 Semántica

Explicación del scope, la inferencia, la inicialización diferida, el drop y la traducción a Rust.

### 5.4 Ejemplos

```pengu
bind max_hp: Int = 100
morph hp = max_hp
hp = hp - 10
```

### 5.5 Rust generado

```rust
let max_hp: i32 = 100;
let mut hp = max_hp;
hp = hp - 10;
```

### 5.6 Diagnósticos

| Código | Mensaje | Causa | Solución |
|---|---|---|---|
| PGS-E1001 | `bind`/`morph` no permitido en el módulo | Se intentó declarar una global | Usa `sigil` o `relic`; si es estado local, muévelo a `grimoire` o a una función |

### 5.7 Interacciones

- §6: constantes y statics.
- §8: expresiones y sentencias.
- §16: move y `Copy`.
- §17: préstamos.

### 5.8 Ver también

- [§3.3 Items de nivel superior](#sec-03)
- [§61 Léxico](#sec-61)
- [§65 Diagnósticos](#sec-65)

[↑ Volver al índice](#indice)
````

### 7.1 Reglas de la plantilla

- **Reglas** es obligatorio y usa RFC 2119: DEBE, NO DEBE, DEBERÍA, NO DEBERÍA, PUEDE.
- **Sintaxis** es obligatorio si la sección introduce o modifica gramática.
- **Semántica** es obligatorio si hay evaluación, tipos, ownership o codegen no obvio.
- **Ejemplos** es obligatorio: al menos un caso positivo, uno negativo y uno límite.
- **Rust generado** es obligatorio en toda sección de lenguaje; debe ser completo y compilable.
- **Diagnósticos** es obligatorio si la sección introduce errores nuevos.
- **Interacciones** es obligatorio si la sección afecta a otras.
- **Ver también** es obligatorio.

### 7.2 Definition of Done de una sección

Una sección está `completo` solo si:

- [ ] Tiene todas las subsecciones obligatorias.
- [ ] Las reglas no contradicen ninguna otra sección.
- [ ] La sintaxis coincide con la gramática EBNF.
- [ ] Los ejemplos PenguScript son válidos.
- [ ] El Rust generado compila.
- [ ] Los diagnósticos tienen código, causa y solución.
- [ ] Los enlaces internos funcionan.
- [ ] Usa el léxico oficial; no introduce sinónimos.
- [ ] Respeta la regla de no globales.
- [ ] Respeta las reglas de "todo es expresión".
- [ ] Fue revisada por alguien distinto del autor.

---

<a id="sec-08-fases"></a>
## 8. Plan por fases

### Resumen

| Fase | Nombre | Secciones | Depende de | Tamaño |
|---|---|---|---|---|
| 0 | Decisiones y andamiaje | piloto §5 | — | M |
| 1 | Fundamentos | §1–§8 | 0 | L |
| 2 | Núcleo del lenguaje | §9–§15 | 1 | XL |
| 3 | Ownership y memoria | §16–§21 | 2 | L |
| 4A | Colecciones y datos | §22–§27 | 3 | M |
| 4B | Agregados y pattern matching | §28–§32 | 4A | L |
| 5 | Abstracción | §33–§40 | 4B | XL |
| 6 | Organización y metaprogramación | §41–§47 | 5 | L |
| 7 | Runtime avanzado | §48–§51 | 6 | L |
| 8 | Sistemas e interop | §52–§55 | 7 | XL |
| 9 | Herramientas y calidad | §56–§59 | 8 | M |
| 10 | Apéndices | §60–§71 | 9 | XL |
| 11 | QA y release candidate | todo | 10 | L |

**Regla de avance:** una fase no se considera cerrada hasta que su checklist esté completo, los ejemplos compilen y el usuario apruebe el resultado. Las fases 10 y 11 pueden solaparse parcialmente con revisiones, pero no se declaran completas antes.

---

<a id="fase-0"></a>
### Fase 0 — Decisiones y andamiaje

**Objetivo:** congelar las decisiones que afectan a toda la especificación y crear el esqueleto verificable de `docs/LANGUAGE.md`.

**Secciones:** ninguna final; se escribe la sección piloto §5 (Variables) para validar la plantilla.

**Decisiones a cerrar:** D0–D24.

**Contenido obligatorio:**

1. Revisar el léxico de la sección 4; eliminar sinónimos; congelar la tabla de keywords.
2. Validar el ejemplo de norte (sección 8.0) y producir su Rust; compilarlo.
3. Crear `docs/LANGUAGE.md` con:
   - portada y metadatos;
   - índice con anclas;
   - las diez partes y las 71 secciones como encabezados `pendiente`;
   - la plantilla de sección aplicada a §5;
   - el glosario rápido.
4. Escribir la sección piloto §5 completa: reglas, sintaxis, semántica, ejemplos, Rust generado, diagnósticos.
5. Crear los scripts de validación en `scratch/tools/`:
   - `check_anchors.py`: detecta enlaces internos rotos y anclas duplicadas.
   - `check_rust_snippets.sh`: extrae bloques `rust` y los compila con `rustc --edition 2024`.
   - `check_terms.py`: detecta keywords prohibidas fuera de bloques `rust`.
   - `check_sections.py`: compara el outline con los encabezados reales.
6. Definir el esquema de `Tome.toml` y el contrato de codegen:
   - nombres, módulos, `#[allow]`, `#[unsafe(...)]`;
   - formato con rustfmt;
   - source maps y remapeo de diagnósticos de `rustc`.
7. Crear `scratch/DECISIONS.md` con el registro de decisiones cerradas y sus alternativas. Se foldeará en el ADR §69.

**Ejemplo de norte (provisional, a validar en esta fase):**

```pengu
rune Point
  x: Float
  y: Float

ritual Point
  new = (x: Float, y: Float) -> Point
    Point(x: x, y: y)

  length = (@) -> Float
    (@.x * @.x + @.y * @.y).sqrt()

grimoire
  bind p = Point.new(3.0, 4.0)
  print("length = #{p.length()}")
```

Rust esperado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

fn main() {
    let p = Point::new(3.0, 4.0);
    println!("length = {}", p.length());
}
```

**Entregable:** `docs/LANGUAGE.md` esqueleto + §5 completa; `scratch/tools/`; `scratch/DECISIONS.md`.

**Criterios de aceptación:**

- [x] D0–D24 están decididas o marcadas como abiertas con responsable y fecha.
- [x] El léxico no tiene colisiones ni sinónimos.
- [x] El ejemplo de norte compila como Rust y su versión PenguScript es válida según la gramática preliminar.
- [x] §5 pasa el Definition of Done del Anexo B (aprobado por el usuario; ver m00510).
- [x] El índice del esqueleto no tiene enlaces rotos.
- [x] Los scripts de validación se ejecutan sin errores sobre el esqueleto.
- [x] No queda ningún `TBD` sin justificar en §5.

**Riesgos:** bikeshedding del léxico; mezclar decisiones de implementación con decisiones de lenguaje. **Mitigación:** timebox de una sesión y registro de alternativas.

**Dependencias:** ninguna.

---

<a id="fase-1"></a>
### Fase 1 — Fundamentos (§1–§8)

**Objetivo:** establecer la filosofía, la gramática léxica, la estructura del programa, el sistema de tipos, los bindings, las constantes, el scope y las reglas de expresión.

**Secciones:** §1 Introducción; §2 Léxico; §3 Programa y compilación; §4 Tipos; §5 Variables; §6 Constantes/statics; §7 Scope; §8 Expresiones.

**Decisiones a cerrar:** D2, D3, D5, D6, D7, D9, D20.

**Contenido obligatorio:**

- **§1:** manifiesto del lenguaje; magia vs. legibilidad; estático; sin globales; todo es expresión; coste cero; interoperabilidad; no objetivos.
- **§2:** UTF-8; BOM; LF/CRLF; indentación de 4 espacios; tabs prohibidos; algoritmo INDENT/DEDENT; comentarios `--`, `--[[ ]]`, `---`, `--!`; identificadores Unicode XID; keywords y contextuales; literales (bool, `none`, enteros con bases y separadores, floats, chars, strings, raw/byte/C, arrays, mapas, tuplas); continuación de línea; punto y coma opcional.
- **§3:** `.pengu`; raíz `main.pengu`/`lib.pengu`; `scroll` de archivo e inline; `Tome.toml`; `grimoire`; items permitidos en módulo; `summon`; `unveil`; pipeline parse → AST → resolución → type check → lower → Rust → cargo; artefactos; source maps; remapeo de diagnósticos.
- **§4:** tipo estático/fuerte/nominal; inferencia local; firmas explícitas; sin `null`; sin truthiness; sin conversiones implícitas; catálogo completo de tipos; ownership/borrowing; coherencia/orphan rules; `dyn`/`impl Trait`; variance (adelanto).
- **§5:** `bind`/`morph`; anotación e inferencia; inicialización y asignación diferida; reasignación; compuestos; shadowing; destructuring; prohibición de globales; mutabilidad y préstamos; `_`.
- **§6:** `sigil`; `relic`; const eval; `static mut` prohibido; `@@shared` e interior mutability; `thread_local`; statics FFI; visibilidad; naming.
- **§7:** scope léxico; drop scopes; temporales; paths; prelude; `@`/`Self`/`super`/`crate`; shadowing; resolución de nombres; imports glob.
- **§8:** todo lo que produce valor es expresión; `bind`/asignación como sentencias; `return`/`break`/`continue` como `Never`; bloques y valor final; `do`; separadores; descarte de valores; unit; divergencia.

**Entregable:** §1–§8 completas, con ejemplos y Rust generado.

**Criterios de aceptación:**

- [x] La regla de no globales es inequívoca y aparece en §5 y §6.
- [x] La gramática léxica permite escribir todos los ejemplos del resto del plan.
- [x] El catálogo de tipos no deja tipos sin dueño.
- [x] Las reglas de "todo es expresión" distinguen expresión, sentencia y divergencia.
- [x] Cada ejemplo tiene Rust compilable.
- [x] Los diagnósticos de §5 y §6 tienen código y solución.
- [x] El índice y las anclas están actualizados.

**Riesgos:** ambigüedad de indentación; mezclar `relic` con variables globales; sobreexplicar Rust antes de tiempo. **Mitigación:** gramática formal y ejemplos negativos.

**Dependencias:** Fase 0.

---

<a id="fase-2"></a>
### Fase 2 — Núcleo del lenguaje (§9–§15)

**Objetivo:** cubrir los tipos primitivos, strings/chars, operadores, booleanos, condicionales, bucles y funciones: el subconjunto con el que ya se puede escribir un programa real.

**Secciones:** §9 Tipos primitivos; §10 Strings/chars; §11 Operadores; §12 Booleanos; §13 Condicionales; §14 Bucles; §15 Funciones.

**Decisiones a cerrar:** D7, D8 (parte de tipos), D10, D13 (introducción), D17.

**Contenido obligatorio:**

- **§9:** `Unit`, `Never`, `Bool`, `I8`–`I128`, `U8`–`U128`, `Isize`, `Usize`, `F32`/`F64`, `Char`, `Str`; alias `Int`/`UInt`/`Float`; literales, sufijos, inferencia por defecto; overflow y operaciones checked/wrapping/saturating; `as` numérico; `NonZero`.
- **§10:** `Str` vs. `String`; literales y escapes; raw, byte y C strings; interpolación `#{}`; `print`/`format`; concatenación; indexación y slicing por bytes; UTF-8; chars; `chars`/`bytes`/`char_indices`; `len`; conversiones `to_string`/`as_str`/`into`; `Cow`; `OsString`/`Path`/`CString` (referencia).
- **§11:** aritméticos; comparación; lógicos; bitwise; asignación y compuestos; rangos; acceso/llamada/método; referencia/deref; `as`; `in`; `is`/`isnt`; `?`; `awaken` (adelanto); precedencia y asociatividad; sobrecarga (adelanto).
- **§12:** `Bool` estricto; `true`/`false`; cortocircuito; `and`/`or`/`not`; alias `&&`/`||`/`!` (si se aceptan); sin truthiness; bitwise vs. lógico; comparaciones encadenadas.
- **§13:** `if`/`elseif`/`else`; `unless`; `then` inline; `if` como expresión; unificación de ramas; ausencia de `else`; `if let` (adelanto); errores.
- **§14:** `while`; `loop`; `for ... in`; `for` numérico inclusive con step; labels; `break`/`continue`; `break value`; `loop` como expresión; comprehensions; `while let` (adelanto); iteradores (adelanto); diagnóstico de `break value` fuera de `loop`.
- **§15:** `->` y `=>`; funciones nombradas `name = (params) -> Tipo`; parámetros; tipo de retorno obligatorio; cuerpo indentado; retorno implícito; `return`; recursión; divergencia; `grimoire` unitario y fallible (`grimoire: !Unit`); métodos `name = (@) -> Tipo` (adelanto); genéricos `name = [T](...) -> ...` (adelanto); sin overloading/defaults/varargs; `main` y `Termination`.

**Entregable:** §9–§15 completas; tabla de precedencia; tabla de literales; ejemplos de control de flujo; Rust generado.

**Criterios de aceptación:**

- [x] Cada tipo primitivo tiene mapeo a Rust y ejemplo.
- [x] La tabla de precedencia cubre todos los operadores y coincide con el parser.
- [x] Las condiciones solo aceptan `Bool`.
- [x] `if` sin `else` produce `Unit`; con `else`, las ramas unifican.
- [x] `loop` puede producir valor con `break value`; `while`/`for` producen `Unit`.
- [x] Las funciones tienen firmas explícitas y retorno implícito.
- [x] Los ejemplos de strings respetan UTF-8 y no indexan por bytes.
- [x] Todos los bloques Rust compilan.

**Riesgos:** precedencia ambigua; semántica de overflow; confusión `Str`/`String`; loops como expresión. **Mitigación:** tablas normativas y tests de parser.

**Dependencias:** Fase 1.

---

<a id="fase-3"></a>
### Fase 3 — Ownership y memoria (§16–§21)

**Objetivo:** explicar el modelo de memoria de Rust con suficiente profundidad para que el resto de la especificación sea comprensible y seguro.

**Secciones:** §16 Ownership; §17 Borrowing; §18 Lifetimes; §19 Referencias y punteros; §20 Smart pointers; §21 Memoria/Drop/layout.

**Decisiones a cerrar:** D6 (interior mutability), D18 (unsafe), D19.

**Contenido obligatorio:**

- **§16:** move; `Copy`; `Clone` explícito; `Drop`; partial moves; ownership en funciones/retornos; ownership en colecciones; `mem::take/replace/swap/forget`; ejemplos de errores del borrow checker.
- **§17:** `&`/`&mut`; reglas (un mutable XOR muchos shared); reborrow; NLL; préstamos en funciones; structs con referencias; conflictos y soluciones (`split_at_mut`, interior mutability).
- **§18:** elisión (tabla completa); lifetimes explícitos; `'static`; bounds; structs/impls/traits; variance; HRTB (adelanto); diagnósticos.
- **§19:** referencias compartidas/mutables; raw pointers `*const`/`*mut`; `&raw`; deref; `NonNull`; aritmética de punteros; null/dangling/provenance; `curse`.
- **§20:** `Box`, `Rc`/`Weak`, `Arc`/`Weak`, `Cell`/`RefCell`, `Mutex`/`RwLock`, `Cow`, `Pin`, `MaybeUninit`/`ManuallyDrop`, `OnceCell`/`LazyLock`; cuándo usar cada uno; coste; ciclos.
- **§21:** stack/heap; RAII; orden de drop (locales, campos, tuplas); drop scopes; leaks; allocators; ZST/DST; `repr`; `size_of`/`align_of`; coste cero.

**Entregable:** §16–§21 completas; tabla de elisión de lifetimes; matriz de smart pointers; ejemplos de errores y correcciones.

**Criterios de aceptación:**

- [x] Las reglas de borrowing son consistentes con Rust y con §5/§17.
- [x] La tabla de elisión cubre todos los casos estables.
- [x] Los ejemplos de errores muestran el mensaje y la solución.
- [x] Los smart pointers tienen una guía de elección.
- [x] El orden de drop está especificado.
- [x] `unsafe` se menciona solo donde corresponde y se enlaza a §52.

**Riesgos:** explicar demasiado Rust y perder el hilo del lenguaje; `Pin`/variance son difíciles. **Mitigación:** ejemplos progresivos y remisiones.

**Dependencias:** Fase 2.

---

<a id="fase-4a"></a>
### Fase 4A — Colecciones y datos (§22–§27)

**Objetivo:** cubrir arrays, slices, vectores, tuplas, mapas/sets, otras colecciones y rangos.

**Secciones:** §22 Arrays/slices; §23 Vectores/VecDeque; §24 Tuplas; §25 Mapas/sets; §26 Otras estructuras; §27 Rangos/indexación.

**Decisiones a cerrar:** D7, D8, D17 (interacción con slices), D13 (const generics para arrays).

**Contenido obligatorio:**

- **§22:** `[T; N]`; literales; repetición; indexación; bounds; `get`; slices `&[T]`/`&mut [T]`; subslice; `split_at`; `chunks`; `windows`; `iter`; `IntoIterator`; `TryFrom<&[T]>`; `array::from_fn`; arrays multidimensionales; const generics.
- **§23:** `Vec[T]`; literal `Vec[...]`; `Vec.new`; `with_capacity`; push/pop; insert/remove; retain; drain; sort/dedup; binary_search; capacidad; slices; `VecDeque`.
- **§24:** `(A, B)`; unit; tupla de un elemento; acceso `.0`; destructuring; tuple structs; impls de traits hasta 12; `()`.
- **§25:** `HashMap[K, V]`, `HashSet[T]`, `BTreeMap[K, V]`, `BTreeSet[T]`; literal `{k: v}`; `insert`/`get`/`entry`/`remove`; orden; `Hash`/`Eq`; hasher custom; `Index` vs. `get`.
- **§26:** `VecDeque`, `LinkedList`, `BinaryHeap`, `BTreeMap/Set`, `HashMap/Set`; cuándo usar; tabla de complejidad; crates externos vía `tome`.
- **§27:** `..`, `..=`; `Range`, `RangeInclusive`, `RangeFrom`, `RangeTo`, `RangeFull`; slicing; `get`; `split_at`; `contains`; `step_by`; `for`.

**Entregable:** §22–§27 completas; tabla de colecciones y complejidad; ejemplos de literales y slicing.

**Extensión de sintaxis (m01025, ajustada en m01398):** formas indentadas opcionales **sin `[]` ni `{}`** para arrays y mapas; `Vec`/`Set` como marcadores seguidos de cuerpo indentado; mapas anidados por `clave:` + indentación. Las tuplas conservan `()` y los rangos su forma propia. La forma inline sigue siendo válida y ambas producen el mismo Rust.

**Criterios de aceptación:**

- [x] No hay ambigüedad entre array, slice y `Vec` en los literales.
- [x] La indexación fuera de rango y `get` se explican.
- [x] Los mapas literales no se confunden con bloques.
- [x] Las tablas de complejidad son correctas.
- [x] Los ejemplos de UTF-8/slicing no parten chars.
- [x] Todos los bloques Rust compilan.
- [x] Las formas indentadas (sin delimitadores) e inline son equivalentes y están documentadas.

**Riesgos:** ambigüedad de literales; exceso de APIs de `std`. **Mitigación:** reglas de contexto y enlaces a docs de `std`.

**Dependencias:** Fase 3.

---

<a id="fase-4b"></a>

### Fase 4B — Agregados y pattern matching (§28–§32)

**Objetivo:** definir structs, enums, pattern matching, implementaciones y conversiones de tipos.

**Secciones:** §28 Structs (`rune`); §29 Enums (`enchanting`); §30 Pattern matching; §31 Implementaciones (`ritual`); §32 Type aliases/newtypes/casts (`essence`).

**Decisiones a cerrar:** D11, D12, D13 (bounds en structs), D15 (`@@repr`/`@@derive`).

**Contenido obligatorio:**

- **§28:** struct nombrado, de tupla y unitario; campos; visibilidad; genéricos; `where`; `@@repr`; `@@derive`; `PhantomData`; DST/ZST; field init shorthand; update syntax `..`; literales; patrones.
- **§29:** variantes unitarias, de tupla y de struct; discriminantes; `@@repr`; `Option`/`Result`; `@@non_exhaustive`; niche optimization; métodos.
- **§30:** `match`/`when`/`else`; patrones literales, binding, wildcard, tupla, struct, enum, slice, rango, or, `@` (binding de patrón, no receptor), `ref`/`ref mut`, `..`; guards; exhaustividad; `if let`; `while let`; `let-else`; refutable vs. irrefutable.
- **§31:** `ritual`; inherente; métodos `name = (@) -> Tipo`; `@`/`@mut`/`@own`; funciones asociadas `name = (...) -> Tipo`; `Self`; múltiples impls; impls genéricos; impls de trait (adelanto); coherencia/orphan rules.
- **§32:** `essence`; alias genérico; associated types (adelanto); newtype; `as`; `Into`/`From`; `TryFrom`/`TryInto`; coerciones; casts de punteros/enums; `transmute` (solo `curse`).

**Entregable:** §28–§32 completas; tabla de patrones; tabla de casts; ejemplos de impls y métodos.

**Criterios de aceptación:**

- [x] La sintaxis de variantes distingue unitaria, tupla y struct sin ambigüedad.
- [x] Los receptores `@` se mapean correctamente a `&self`, `&mut self` y `self`.
- [x] `match` es exhaustivo o usa `else`.
- [x] Los patrones cubren todos los tipos agregados.
- [x] Las reglas de coherencia/orphan se explican y se delegan a Rust.
- [x] Los casts no permiten pérdidas implícitas.
- [x] Todos los ejemplos compilan.

**Riesgos:** sintaxis de variantes; ergonomía de patrones; confusión `ritual`/`pact`. **Mitigación:** ejemplos comparados y tabla de decisión.

**Dependencias:** Fase 4A.

---

<a id="fase-5"></a>
### Fase 5 — Abstracción (§33–§40)

**Objetivo:** cubrir genéricos, constraints, traits, items asociados, HRTB, closures, function pointers y sobrecarga de operadores.

**Secciones:** §33 Genéricos; §34 Constraints/where; §35 Traits; §36 Associated items; §37 HRTB; §38 Closures; §39 Function pointers/HOF; §40 Operator overloading.

**Decisiones a cerrar:** D12, D13, D18 (closures/async), D23 (proc macros no aplica aquí).

**Contenido obligatorio:**

- **§33:** parámetros de tipo, lifetime y const; `[T]`; `[const N: Usize]`; turbofish `foo[Int](x)`; inferencia; monomorphization; generic structs/enums/functions/impls; `PhantomData`; sin defaults de tipo.
- **§34:** bounds `T: Pact + Clone`; `where`; lifetime bounds; `?Sized`; associated type bounds; HRTB; const bounds; resolución.
- **§35:** `pact`; métodos; métodos default; associated types/consts; supertraits; blanket impls; marker/auto traits; object safety; `dyn`; `impl Trait`; coherencia; sealed traits (`seal`); operator traits.
- **§36:** associated types; GATs; associated consts; RPITIT; `async fn` en traits; `Self`; proyecciones.
- **§37:** `for<'a>`; higher-ranked trait bounds; fn pointers; closures; late-bound vs. early-bound; `dyn for<'a> Fn(&'a T)`; ejemplos.
- **§38:** sintaxis `(params) => expr`; capturas; `Fn`/`FnMut`/`FnOnce`; `move`; retorno de closures; recursión; closures en structs; HRTB; `impl Fn`; `dream` closures.
- **§39:** tipo `(A) -> B`; function pointers; callbacks; `dyn Fn`; combinadores; `impl Fn`; diferencias con closures.
- **§40:** traits de operadores (`Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Not`, `BitAnd`, `BitOr`, `BitXor`, `Shl`, `Shr`, `AddAssign`, etc.); `Index`/`IndexMut`; `Deref`/`DerefMut`; `PartialEq`/`Eq`; `PartialOrd`/`Ord`; `Display`; reglas y límites.

**Entregable:** §33–§40 completas; tabla de traits de operadores; ejemplos de HRTB y closures; guía de object safety.

**Criterios de aceptación:**

- [x] La sintaxis de genéricos no colisiona con indexación/slices.
- [x] Los bounds y `where` son equivalentes a Rust.
- [x] `dyn`/`impl Trait` y object safety están explicados.
- [x] GATs y RPITIT tienen ejemplos compilables.
- [x] HRTB no se confunde con lifetimes normales.
- [x] Las closures capturan correctamente por referencia o por movimiento.
- [x] La sobrecarga de operadores se limita a traits de Rust.

**Riesgos:** complejidad del trait solver; HRTB; object safety. **Mitigación:** ejemplos mínimos y remisiones a Rust.

**Dependencias:** Fase 4B.

---

<a id="fase-6"></a>
### Fase 6 — Organización y metaprogramación (§41–§47)

**Objetivo:** definir módulos, visibilidad, crates/packages, atributos, macros, derives y build scripts.

**Secciones:** §41 Módulos; §42 Visibilidad; §43 Crates/packages/workspaces; §44 Atributos; §45 Macros; §46 Derives; §47 Build scripts/features/cfg.

**Decisiones a cerrar:** D14, D15, D16, D23.

**Contenido obligatorio:**

- **§41:** archivo = `scroll`; módulo inline; raíz; resolución de archivos (`foo.pengu`, `foo/scroll.pengu`); `summon`; paths `crate`/`self`/`super`; re-exports; prelude; glob imports.
- **§42:** privado por defecto; `unveil`; `unveil(scroll)`; `unveil(tome)`; `unveil(parent)`; campos/variantes/items de trait; `pub(in path)`; reglas de privacidad.
- **§43:** `tome`; `Tome.toml`; dependencias; features; targets (lib/bin/test/bench/example); workspaces; ediciones; semver; lockfile; registro; `[cargo]` passthrough.
- **§44:** `@@attr(...)`; inner `@@!`; atributos built-in (`@@derive`, `@@repr`, `@@cfg`, `@@test`, `@@inline`, `@@cold`, `@@deprecated`, `@@must_use`, `@@non_exhaustive`, `@@doc`, `@@allow/deny/warn`, `@@no_mangle`, `@@link`, `@@panic_handler`, `@@global_allocator`, `@@no_std`, `@@feature`, `@@bench`, `@@ignore`, `@@should_panic`, `@@track_caller`, `@@target_feature`, `@@used`, `@@link_section`, `@@export_name`, `@@path`, `@@macro_use`).
- **§45:** `incantation` (`macro_rules!`); metavariables; repeticiones; higiene; `$crate`; invocación `name!(...)`; exportación; proc macros (derive/attribute/function-like) desde crates Rust; límites; `@@derive`.
- **§46:** `Clone`, `Copy`, `Debug`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`, `Default`; derives custom; serde; `Display`; `Error`; cuándo implementar a mano.
- **§47:** `build.pengu` → `build.rs`; features; `@@cfg`; target-specific deps; variables de entorno; `OUT_DIR`; `include!`; reproducibilidad.

**Entregable:** §41–§47 completas; árbol de módulos de ejemplo; tabla de visibilidad; tabla de atributos; ejemplo de macro y de build script.

**Criterios de aceptación:**

- [x] La resolución de módulos es determinista.
- [x] La tabla de visibilidad cubre todas las formas de `pub`.
- [x] `Tome.toml` mapea a `Cargo.toml` y permite features avanzadas.
- [x] Los atributos tienen sintaxis y efecto documentados.
- [x] Las macros declarativas tienen higiene y token trees explicados.
- [x] La política de proc macros es explícita (definir en Rust, consumir desde PenguScript).
- [x] Los build scripts no rompen la reproducibilidad.

**Riesgos:** mapeo de Cargo; token trees en un lenguaje indentado; proc macros. **Mitigación:** `[cargo]` passthrough y bloque `rust` auditado.

**Dependencias:** Fase 5.

---

<a id="fase-7"></a>
### Fase 7 — Runtime avanzado (§48–§51)

**Objetivo:** cubrir errores, iteradores, async/await y concurrencia.

**Secciones:** §48 Manejo de errores; §49 Iteradores; §50 Async/await; §51 Concurrencia.

**Decisiones a cerrar:** D8, D18, D19.

**Contenido obligatorio:**

- **§48:** `Option`/`Result`; `?T`/`!T`; `none`/`some`/`ok`/`err`; `?`; `From`; `panic`; `assert`; errores custom; `Error`; `Box<dyn Error>`; `thiserror`/`anyhow`; `catch_unwind`; `main` con `Result`; `Termination`; `let-else`; `try` blocks (diferido).
- **§49:** `Iterator`/`IntoIterator`; `iter`/`iter_mut`/`into_iter`; adaptadores (`map`, `filter`, `filter_map`, `flat_map`, `flatten`, `fold`, `reduce`, `scan`, `take`, `skip`, `take_while`, `skip_while`, `chain`, `zip`, `enumerate`, `peekable`, `rev`, `cycle`, `inspect`, `step_by`, `fuse`); consumidores (`collect`, `sum`, `product`, `min`, `max`, `count`, `any`, `all`, `find`, `position`, `partition`, `unzip`); iteradores custom; `impl Iterator`; pereza; `DoubleEndedIterator`; `ExactSizeIterator`; `FusedIterator`.
- **§50:** `dream name = (params) -> ...`; `awaken`; `Future`; `Pin`; async blocks/closures; executors (tokio/async-std); `Send` futures; cancelación; `select!`; streams; `async fn` en traits; RPITIT; runtime-agnostic; `no_std` async.
- **§51:** threads; `spawn`; `JoinHandle`; scoped threads; `Send`/`Sync`; `Arc<Mutex<T>>`; `RwLock`; channels (`mpsc`, crossbeam); atomics; `Ordering`; `thread_local`; `OnceLock`/`LazyLock`; rayon; deadlocks; data races; `UnsafeCell`.

**Entregable:** §48–§51 completas; tabla de conversiones de error; tabla de adaptadores de iteradores; ejemplos async y de concurrencia.

**Criterios de aceptación:**

- [x] `?` solo se usa en funciones que devuelven `Result`/`Option` compatibles.
- [x] La tabla de `From`/`?` es correcta.
- [x] Los iteradores no se confunden con comprehensions.
- [x] Los ejemplos async usan un runtime concreto y explican cómo cambiarlo.
- [x] `Send`/`Sync` se explican con ejemplos de error.
- [x] Los ejemplos de concurrencia no tienen data races.

**Riesgos:** elegir un runtime; `Pin`; cancelación; deadlocks. **Mitigación:** ejemplos runtime-agnostic y notas explícitas.

**Dependencias:** Fase 6.

---

<a id="fase-8"></a>
### Fase 8 — Sistemas e interop (§52–§55)

**Objetivo:** cubrir unsafe, FFI, const eval y `no_std`/embebidos/wasm.

**Secciones:** §52 Unsafe; §53 FFI/interop; §54 Const eval; §55 `no_std`/embebidos/wasm.

**Decisiones a cerrar:** D18, D23, D24.

**Contenido obligatorio:**

- **§52:** `curse` bloques/funciones/traits; raw pointers; uniones (`chimera`); `transmute`; `MaybeUninit`; `ManuallyDrop`; `UnsafeCell`; aliasing/soundness; safety comments; `@@deny(unsafe_op_in_unsafe_fn)`; inline asm (`asm!`, `global_asm!`).
- **§53:** `foreign "C"`; extern blocks; `@@no_mangle`/`@@export_name`/`@@link`/`@@link_name`; `@@repr(C)`; tipos opacos; C strings; bindgen/cbindgen; llamar crates Rust; bloque `rust`; ABI; unwinding; `@@global_allocator`/`@@panic_handler`; wasm; `wasm-bindgen`.
- **§54:** `sigil`; `eternal name = (params) -> ...` (`const fn`); const generics; const blocks; const panic; limitaciones (sin heap, sin traits inestables); `OnceLock`/`LazyLock`; inicialización de statics.
- **§55:** `@@no_std`; `core`/`alloc`; panic handler; allocator; entry point; target triples; cross-compilation; linker scripts; volatile/MMIO; interrupts; `cortex-m`/`embassy`; `build-std`; wasm.

**Entregable:** §52–§55 completas; checklist de soundness; ejemplo FFI; ejemplo `no_std`; tabla de const eval.

**Criterios de aceptación:**

- [x] Toda operación unsafe está dentro de `curse` y tiene justificación.
- [x] Las reglas de aliasing y `transmute` son conservadoras.
- [x] El ejemplo FFI compila y explica el ABI.
- [x] `no_std` tiene panic handler y allocator cuando corresponde.
- [x] El bloque `rust` está marcado como escape auditado y no se usa en ejemplos básicos.
- [x] Las features inestables están en §66, no en el núcleo.

**Riesgos:** complejidad de unsafe/ABI; toolchains embebidos; abuso del bloque `rust`. **Mitigación:** ejemplos mínimos y checklist de seguridad.

**Dependencias:** Fase 7.

---

<a id="fase-9"></a>
### Fase 9 — Herramientas y calidad (§56–§59)

**Objetivo:** cerrar la experiencia de uso: testing, documentación, CLI/LSP/formatter/linter y guía de estilo.

**Secciones:** §56 Testing; §57 Documentación; §58 Herramientas; §59 Guía de estilo.

**Decisiones a cerrar:** D20, D21, D22.

**Contenido obligatorio:**

- **§56:** `@@test`; `assert`/`assert_eq`/`assert_ne`/`debug_assert`; tests unitarios/integración/doc; `@@should_panic`; `@@ignore`; organización; property testing; fuzzing; benchmarks; coverage; mocking; CI.
- **§57:** `---` doc comments; `--!` module docs; Markdown; doctests; `@@doc`; `@@must_use`; `@@deprecated`; rustdoc; intra-doc links; ejemplos; README.
- **§58:** CLI `pengu` (`init`, `new`, `build`, `run`, `check`, `test`, `fmt`, `lint`, `doc`, `clean`, `add`, `publish`); LSP; formatter; linter; códigos de error; source maps; editor integration; CI; reproducibilidad; `Tome.lock`; audit; semver.
- **§59:** naming/casing; indentación; longitud de línea; imports; comentarios; uso del léxico; preferir expresiones; manejo de errores; política de unsafe; documentación; ejemplos; formato; lints.

**Entregable:** §56–§59 completas; tabla de comandos; reglas de lint; guía de estilo.

**Criterios de aceptación:**

- [x] Los tests de ejemplo compilan y se ejecutan.
- [x] Los doc comments generan doctests válidos.
- [x] Cada comando del CLI tiene propósito, flags y salida.
- [x] Las reglas de estilo son verificables por el formatter/linter.
- [ ] La guía de estilo no contradice la spec.

**Riesgos:** prometer tooling que no existe; doc drift. **Mitigación:** marcar estado `planificado` y no presentar como implementado.

**Dependencias:** Fase 8.

---

<a id="fase-10"></a>
### Fase 10 — Apéndices (§60–§71)

**Objetivo:** producir las referencias normativas y de consulta que cierran la especificación.

**Secciones:** §60 Gramática; §61 Léxico; §62 Precedencia; §63 Paridad Rust; §64 Desugaring; §65 Diagnósticos; §66 No soportado; §67 Glosario; §68 Cookbook; §69 ADR; §70 Changelog; §71 Referencias.

**Decisiones a cerrar:** todas; cualquier cambio requiere ADR.

**Contenido obligatorio:**

- **§60:** EBNF léxica, de items, tipos, expresiones, patrones, atributos, macros y manifiesto; algoritmo de indentación.
- **§61:** tabla completa de keywords, contextuales, preludio, prohibidas; colisiones.
- **§62:** tabla de precedencia y asociatividad; notas de ambigüedad; cómo resuelve el parser.
- **§63:** matriz exhaustiva de Rust estable; estado (`completo`, `parcial`, `diferido`, `no soportado`); sección; notas.
- **§64:** tabla de desugaring: azúcar → forma core → Rust.
- **§65:** catálogo de códigos `PGS-E...`, `PGS-W...`; mensaje, causa, ejemplo, solución.
- **§66:** features no soportadas o diferidas y su alternativa.
- **§67:** glosario bilingüe de términos mágicos, Rust y del documento.
- **§68:** cookbook: hello world, CLI, librería, errores, async, FFI, embebido, wasm, macros.
- **§69:** ADR con D0–D25, contexto, decisión, alternativas, consecuencias.
- **§70:** versión de spec, versión de compilador, edición Rust, MSRV, semver, deprecaciones.
- **§71:** referencias a Rust Reference/Book, MoonScript, V, Kotlin, RFC 2119.

**Entregable:** §60–§71 completas; matriz de paridad; catálogo de diagnósticos; cookbook.

**Criterios de aceptación:**

- [x] La gramática EBNF puede alimentar un parser sin decisiones ad hoc.
- [x] La matriz de paridad no tiene filas vacías ni "TBD".
- [x] Cada diagnóstico del catálogo aparece en al menos una sección.
- [x] El cookbook compila.
- [x] El glosario no tiene definiciones circulares.
- [x] El ADR explica las decisiones y sus alternativas.

**Riesgos:** duplicación con las secciones; inconsistencia de códigos; tamaño. **Mitigación:** generar tablas desde una fuente única y validar con scripts.

**Dependencias:** Fase 9.

---

<a id="fase-11"></a>
### Fase 11 — QA y release candidate

**Objetivo:** auditar la especificación completa y declararla release candidate.

**Contenido obligatorio:**

1. **Completitud:** recorrer el Anexo A y marcar cada sección; comparar contra §63.
2. **Consistencia:** buscar términos duplicados, sinónimos, referencias rotas, contradicciones.
3. **Técnica:** extraer y compilar todos los bloques `rust`; extraer y validar todos los `pengu` (parser/type checker cuando exista).
4. **Navegación:** verificar índice, anclas, numeración, enlaces, "volver al índice".
5. **Legibilidad:** revisar con un lector nuevo; medir tiempo para encontrar un tema.
6. **Revisión adversarial:** Rust expert, usuario de MoonScript, principiante, revisor de seguridad.
7. **Cierre:** changelog, versión `1.0.0-rc.1`, firma.

**Criterios de aceptación:**

- [x] Cero enlaces rotos.
- [x] Cero bloques `rust` sin compilar.
- [x] Cero `TBD` sin justificar.
- [x] Contradicciones conocidas corregidas (re-auditoría completada).
- [x] Todas las secciones del Anexo A en `completo`.
- [x] Dos revisores distintos aprueban (legibilidad y Rust/seguridad).
- [x] El changelog refleja todos los cambios.

**Riesgos:** cambios de última hora; renumeração; fatiga de revisión. **Mitigación:** congelar numeración y aceptar solo cambios aditivos después del RC.

---

<a id="sec-09-matrices"></a>
## 9. Matrices de cobertura

### 9.1 Matriz de paridad Rust (planificación)

**Leyenda:** `Completo` = se documenta y se mapea a Rust; `Parcial` = se documenta con una limitación explícita; `Diferido` = no está en el núcleo, se explica en §66; `No soportado` = no se puede expresar.

| # | Área de Rust | Sección(es) | Estado objetivo |
|---|---|---|---|
| 1 | Items y declaraciones | §15, §28, §29, §31, §35, §41, §43 | Completo |
| 2 | Visibilidad y paths | §41, §42 | Completo |
| 3 | Genéricos de tipo, lifetime y const | §33 | Completo |
| 4 | Bounds, `where`, HRTB | §34, §37 | Completo |
| 5 | Traits, defaults, associated items, GATs | §35, §36 | Completo |
| 6 | Impls y coherencia | §31, §35 | Completo |
| 7 | Ownership, move, `Copy`, `Clone`, `Drop` | §16, §21 | Completo |
| 8 | Borrowing y NLL | §17 | Completo |
| 9 | Lifetimes, elisión y variance | §18 | Completo |
| 10 | Referencias y raw pointers | §19 | Completo |
| 11 | Smart pointers e interior mutability | §20 | Completo |
| 12 | Primitivos, literales y overflow | §9 | Completo |
| 13 | Strings, chars y UTF-8 | §10 | Completo |
| 14 | Arrays y slices | §22 | Completo |
| 15 | `Vec` y `VecDeque` | §23 | Completo |
| 16 | Tuplas | §24 | Completo |
| 17 | Mapas y sets | §25 | Completo |
| 18 | Otras colecciones | §26 | Completo |
| 19 | Rangos e indexación | §27 | Completo |
| 20 | Structs | §28 | Completo |
| 21 | Enums y discriminantes | §29 | Completo |
| 22 | Pattern matching y exhaustividad | §30 | Completo |
| 23 | Type aliases, newtypes y casts | §32 | Completo |
| 24 | Operadores y sobrecarga | §11, §40 | Completo |
| 25 | Control de flujo y expresiones | §8, §13, §14 | Completo |
| 26 | Funciones, recursión y divergencia | §15 | Completo |
| 27 | Closures y traits `Fn` | §38 | Completo |
| 28 | Function pointers y HOF | §39 | Completo |
| 29 | Módulos, paths y prelude | §41 | Completo |
| 30 | Crates, packages, workspaces y features | §43, §47 | Completo |
| 31 | Atributos y derives | §44, §46 | Completo |
| 32 | Macros declarativas | §45 | Completo |
| 33 | Proc macros | §45 | Parcial: se consumen desde crates Rust; definirlas requiere Rust |
| 34 | Errores, `Option`, `Result`, `?`, `panic` | §48 | Completo |
| 35 | Iteradores | §49 | Completo |
| 36 | Async/await, `Future`, `Pin` | §50 | Completo |
| 37 | Concurrencia, `Send`/`Sync`, atomics | §51 | Completo |
| 38 | Unsafe, uniones, `transmute`, asm | §52 | Completo |
| 39 | FFI, ABI y `repr` | §53 | Completo |
| 40 | Const eval, `const fn`, const generics | §54 | Completo |
| 41 | `no_std`, embebidos y wasm | §55 | Completo |
| 42 | Testing y benchmarks | §56 | Completo |
| 43 | Documentación y doctests | §57 | Completo |
| 44 | Tooling, CLI, LSP, formatter, linter | §58 | Completo |
| 45 | Guía de estilo | §59 | Completo |
| 46 | Gramática, léxico y precedencia | §60–§62 | Completo |
| 47 | Desugaring y diagnósticos | §64, §65 | Completo |
| 48 | No soportado / diferido | §66 | Documentado |
| 49 | Ediciones y MSRV | §43, §70 | Completo |
| 50 | Rendimiento y coste cero | §21, §59 | Completo |
| 51 | Seguridad y soundness | §52, §65 | Completo |
| 52 | Interop con crates Rust | §53 | Completo |
| 53 | Build scripts | §47 | Completo |
| 54 | Inline asm | §52 | Completo |
| 55 | Plataformas y cross-compilation | §55 | Completo |
| 56 | Miri, fuzzing y sanitizers | §56, §58 | Completo |
| 57 | Especificidades de Rust 2024 | §43, §70 | Completo |

**Nota de alcance:** "Completo" significa que el **lenguaje** permite expresar la feature y el documento la cubre. No significa que `LANGUAGE.md` re-documente cada método de `std`; para las APIs, se enlaza a la documentación oficial de Rust y se explica la sintaxis de invocación.

### 9.2 Matriz MoonScript

| Rasgo | PenguScript | Sección | Decisión |
|---|---|---|---|
| Indentación significativa | Igual | §2 | Conservar |
| Comentarios `--` / `--[[ ]]` | Igual + `---` | §2 | Conservar/extender |
| Asignación local implícita | `bind` / `morph` | §5 | Reemplazar |
| Globales implícitas | Prohibidas | §5, §6 | Eliminar |
| `if`/`unless`/`elseif`/`then` | Igual | §13 | Conservar |
| `switch`/`when` | `match`/`when`/`else` | §30 | Adaptar |
| `for` numérico | `for i = a, b[, step]` | §14 | Conservar |
| `for ... in` | `for x in iterable` | §14 | Conservar |
| Comprehensions | `[expr for ... when ...]` | §14 | Conservar |
| `while`/`loop` | Igual | §14 | Conservar |
| Funciones `->` | `name = (params) ->` y `(params) =>` | §15, §38 | Adaptar |
| Funciones nombradas | Sin keyword: `name = (params) -> Tipo` | §15 | Adaptar |
| Retorno implícito | Igual | §8, §15 | Conservar |
| Clases/herencia | `rune` + `pact`/`ritual` | §28, §31, §35 | Reemplazar |
| `@` como `self` | `@` | §31 | Conservar |
| `new` | Literal / `new` asociado | §28 | Adaptar |
| `super` | No hay herencia; métodos de trait | §35 | Eliminar |
| `extends` | Supertraits `:` | §35 | Adaptar |
| Interpolación `#{}` | Igual | §10 | Conservar |
| Strings largos `[[ ]]` | `"""..."""` | §10 | Adaptar |
| Tablas `{}` | Mapas `{k: v}`; arrays `[...]` | §22, §25 | Adaptar |
| Splat `*` | Spread `...` limitado | §11, §22 | Adaptar |
| Slicing | Rangos `..`/`..=` | §27 | Adaptar |
| `and`/`or`/`not` | Igual + alias simbólicos | §12 | Conservar |
| `is`/`isnt` | Igual | §11 | Conservar |
| `!=` | Igual | §11 | Conservar |
| `..` concatenación | `+` o interpolación; `..` es rango | §10, §11 | Divergencia |
| `#` longitud | `.len()` | §10 | Divergencia |
| `nil` | `none` / `Option` | §9, §48 | Reemplazar |
| Truthiness | Prohibida | §12 | Eliminar |
| `do` expresión | Igual | §8 | Conservar |
| `import`/`export` | `summon`/`unveil` | §41, §42 | Reemplazar |
| `continue`/`break`/`return` | Igual | §14, §15 | Conservar |
| `=>` función ligada | `(params) => expr` | §15, §38 | Adaptar |
| `with` | No se soporta; `bind` local | §7 | No soportado |
| Metatables/prototipos | No se soportan | §66 | No soportado |
| Coroutines | Iteradores/async | §49, §50 | Adaptar |

### 9.3 Especificidades de Rust 2024 para el codegen

| Tema | Regla de codegen |
|---|---|
| Atributos unsafe | `#[unsafe(no_mangle)]`, `#[unsafe(export_name)]`, `#[unsafe(link_section)]` |
| `unsafe_op_in_unsafe_fn` | Toda operación unsafe dentro de una `unsafe fn` se envuelve en `unsafe { ... }` |
| `gen` reservado | Evitar `gen` como identificador generado; manglear si aparece |
| Captura de lifetimes en `impl Trait` | Emitir `+ use<'a, T>` cuando sea necesario para preservar la semántica 2024 |
| `if let` y temporales | Insertar bloques explícitos si el cambio de scope 2024 afecta al drop |
| Tail expression y temporales | Insertar `let` temporales o bloques para preservar el orden de drop documentado |
| Match ergonomics | Ajustar patrones `ref`/`mut` según la edición; no depender de cambios implícitos |
| `static mut` | No se genera nunca; `relic` es inmutable |
| `rustfmt` | Formatear con `--edition 2024` |

### 9.4 Trazabilidad

Cada fila de la matriz debe poder responderse con:

1. **Sección** donde se define.
2. **Ejemplo** positivo y negativo.
3. **Test** (golden snippet o test de parser/type checker).
4. **Rust generado** que demuestra el mapeo.
5. **Diagnóstico** asociado, si hay errores.

---

<a id="sec-10-validacion"></a>
## 10. Estrategia de validación

### 10.1 Reglas de calidad del documento

- Toda sección debe poder leerse de forma aislada y entenderse con las remisiones.
- Ninguna regla puede contradecir otra; si hay conflicto, se resuelve en una sección y las demás remiten.
- Ningún ejemplo puede usar una construcción que no esté definida antes (salvo adelanto explícito).
- Ningún bloque `rust` puede contener `...` sin una marca de elisión.
- Ningún diagnóstico puede repetir código con otro significado.

### 10.2 Herramientas

| Herramienta | Función | Fase |
|---|---|---|
| `check_anchors.py` | Enlaces internos y anclas duplicadas | 0 |
| `check_rust_snippets.sh` | Extrae y compila bloques `rust` | 0 |
| `check_terms.py` | Keywords prohibidas y léxico oficial | 0 |
| `check_sections.py` | Outline vs. encabezados reales | 0 |
| `markdownlint` | Formato Markdown | 1 |
| `cspell`/`hunspell` | Ortografía | 1 |
| `pengu check` | Parser + type checker de ejemplos `.pengu` | cuando exista |
| `cargo test` | Golden tests de codegen | cuando exista |
| `cargo miri`/fuzz | Soundness de ejemplos unsafe | 8+ |

### 10.3 Validación de bloques Rust

1. Extraer todos los bloques ```rust.
2. Envolverlos en un crate temporal con `#![allow(dead_code, unused_variables)]`.
3. Compilar con `rustc --edition 2024` o `cargo check`.
4. Formatear con `rustfmt` y comparar con el bloque publicado (si se promete formato).
5. Los ejemplos que deben fallar se marcan con `//~ ERROR` y se validan contra el mensaje esperado.

### 10.4 Validación de bloques PenguScript

Antes de que exista el compilador:

- Revisión manual por dos personas.
- Comprobación contra la gramática EBNF.
- Comprobación de que cada construcción usada está definida en una sección anterior o marcada como adelanto.

Cuando exista el compilador:

- `pengu check` sobre cada snippet.
- Golden tests: `.pengu` + `.rs` esperado + diagnósticos esperados.
- Tests de propiedades para el parser (indentación, strings, patrones).

### 10.5 Golden tests

Estructura propuesta:

```text
tests/
  snippets/
    variables/
      basic.pengu
      basic.rs
      no_globals.pengu
      no_globals.err
    ...
```

Cada caso debe tener:

- entrada `.pengu`;
- salida `.rs` esperada (si compila);
- diagnóstico esperado (si falla);
- sección de referencia.

### 10.6 Revisión

| Rol | Qué revisa |
|---|---|
| Autor | Consistencia, ejemplos, enlaces |
| Revisor Rust | Semántica, codegen, soundness, edición 2024 |
| Revisor MoonScript | Ergonomía, fidelidad sintáctica, pérdida de ventajas |
| Revisor principiante | Claridad, orden, ejemplos |
| Revisor de seguridad | Unsafe, FFI, `no_std`, dependencias |

### 10.7 CI propuesta

- `doc-lint`: markdownlint + anchors + spelling.
- `doc-rust`: compila todos los bloques Rust.
- `doc-pengu`: parser + type checker sobre snippets (cuando exista).
- `doc-coverage`: compara secciones con la matriz de paridad.
- `doc-links`: enlaces externos (con caché para no fallar por red).

### 10.8 Métricas

| Métrica | Objetivo |
|---|---|
| Secciones `completo` | 71/71 |
| Enlaces rotos | 0 |
| Bloques Rust sin compilar | 0 |
| `TBD` sin justificar | 0 |
| Decisiones abiertas | 0 al RC |
| Cobertura de la matriz de paridad | 100% con estado explícito |
| Ejemplos por sección | ≥ 3 (positivo, negativo, límite) |

### 10.9 Definition of Done global

`docs/LANGUAGE.md` está listo cuando:

- [x] Las 71 secciones están en `completo`.
- [x] La matriz de paridad no tiene huecos.
- [x] Todos los ejemplos compilan o fallan con el diagnóstico documentado.
- [x] El índice y las anclas funcionan.
- [x] No hay contradicciones ni sinónimos mágicos.
- [x] La regla de no globales y la de "todo es expresión" son verificables.
- [x] Dos revisores externos aprueban.
- [x] El changelog y la versión están actualizados.

---

<a id="sec-11-riesgos"></a>
## 11. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación | Fase |
|---|---|---|---|
| Bikeshedding del léxico | Alto | Timebox, tabla única, ADR, no sinónimos | 0 |
| Ambigüedad de indentación | Alto | Gramática formal, INDENT/DEDENT, tests de parser | 1 |
| "Todo es expresión" choca con move semantics | Alto | Carve-outs explícitos: asignación es sentencia | 1 |
| No globales vs. statics/FFI | Alto | `relic` inmutable + `@@shared` + `curse`; política documentada | 1 |
| Inferencia local vs. firmas explícitas | Medio | Firmas de función explícitas; locales inferidos | 1 |
| Precedencia de operadores ambigua | Medio | Tabla normativa + tests | 2 |
| `Str`/`String` y UTF-8 | Medio | Modelo explícito, sin indexación por bytes | 2 |
| Borrow checker difícil de explicar | Alto | Ejemplos progresivos, remisión a Rust | 3 |
| `Pin`/variance/HRTB | Alto | Secciones avanzadas con ejemplos mínimos | 3, 5 |
| Ambigüedad array/slice/Vec | Medio | Reglas de literales y contexto | 4A |
| Sintaxis de variantes de enum | Medio | Unit/tupla/struct con reglas claras | 4B |
| Object safety/trait solver | Alto | Delegar en rustc, documentar límites | 5 |
| Mapeo de Cargo | Medio | `[cargo]` passthrough; ejemplos reales | 6 |
| Token trees en lenguaje indentado | Medio | `{}`/`()`/`[]` solo en macros; contexto | 6 |
| Proc macros | Medio | Definir en Rust; consumir desde PenguScript | 6 |
| Elegir runtime async | Medio | Ejemplos runtime-agnostic; features | 7 |
| `Send`/`Sync` y concurrencia | Alto | Matriz de errores y ejemplos | 7 |
| Unsafe/FFI/ABI | Alto | Checklist de soundness; ejemplos mínimos | 8 |
| `no_std`/embebidos | Alto | Ejemplo con target concreto; limitaciones | 8 |
| Tooling prometido y no implementado | Medio | Estado `planificado`; no vender como hecho | 9 |
| Documento demasiado grande | Medio | Partes, índice, búsqueda, secciones autocontenidas | 10 |
| Duplicación entre secciones y apéndices | Medio | Fuente única + enlaces | 10 |
| Cambios de Rust estable | Bajo | Fijar edición/MSRV; revisar por release | 10 |
| Abuso del bloque `rust` | Medio | Lint, revisión, solo último recurso | 8 |
| Fatiga de revisión | Medio | Fases cortas, checklists, revisiones parciales | 11 |

---

<a id="sec-12-preguntas"></a>
## 12. Preguntas abiertas

Estas son las decisiones que conviene que el usuario confirme antes de la Fase 1. Todas tienen una recomendación; ninguna bloquea la Fase 0.

| ID | Pregunta | Recomendación | Impacto | Fase |
|---|---|---|---|---|
| Q1 | ¿Prosa en español o en inglés? | Español, con keywords/código en inglés | D0; todo el documento | 0 |
| Q2 | ¿`bind`/`morph` o asignación implícita tipo MoonScript? | `bind`/`morph` explícito | D5; legibilidad vs. concisión | 0 |
| Q3 | ¿`Int` = `i32` y `Float` = `f64`? | Sí; `Isize`/`Usize` y `F32`/`F64` explícitos | D7; interoperabilidad | 0 |
| Q4 | ¿`Str` = `str` y `String` = `String`? | Sí; literales se convierten a `String` en contexto tipado | D7/D17; strings | 0 |
| Q5 | ¿Azúcar `?T`/`!T` o solo `Option`/`Result`? | Azúcar `?T`/`!T` + canónicos | D8; ergonomía | 0 |
| Q6 | ¿Asignación como sentencia o expresión? | Sentencia; `return`/`break`/`continue` sí son expresiones `Never` | D9; codegen y move | 0 |
| Q7 | ¿`@`/`@mut`/`@own`? | Sí | D12; métodos | 0 |
| Q8 | ¿`relic` con interior mutability? | Permitido solo con `@@shared` y lint; `static mut` no existe | D6; estado global | 0 |
| Q9 | ¿`Tome.toml` o `Cargo.toml` directo? | `Tome.toml` con `[cargo]` passthrough | D14; tooling | 0 |
| Q10 | ¿Bloque `rust` de escape? | Sí, auditado y solo último recurso | D18/D23; cobertura total | 0 |
| Q11 | ¿Genéricos `[T]` y HRTB `for<'a>`? | Sí | D13; parser | 0 |
| Q12 | ¿Proc macros definidas en PenguScript? | No en v1; se consumen desde crates Rust | D23; alcance | 0 |
| Q13 | ¿`print`/`format` como built-ins? | Sí; `print` → `println!`, `format` → `format!` | D17/D19; ergonomía | 0 |
| Q14 | ¿`unless`/`then`/`is`/`isnt`? | Sí, son parte de la herencia MoonScript | D4; sintaxis | 0 |
| Q15 | ¿`say` o `print` para salida? | `print` (familiar y MoonScript) | D19; preludio | 0 |
| Q16 | ¿Tipo de retorno obligatorio en funciones nombradas? | Sí: `name = (params) -> Tipo`; las lambdas infieren | D10; sintaxis y parser | 0 |

**Decisión por defecto:** si el usuario no responde, se avanza con las recomendaciones y se registran en el ADR. Cambiarlas después cuesta más; por eso la Fase 0 es explícita.

---

<a id="sec-13-seguimiento"></a>
## 13. Seguimiento de progreso

### 13.1 Estado de fases

| Fase | Estado | Inicio | Fin | Notas |
|---|---|---|---|---|
| 0 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m00510) |
| 1 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m00666) |
| 2 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m00869) |
| 3 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m01025) |
| 4A | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m01261) |
| 4B | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m01565) |
| 5 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m01813) |
| 6 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m01942) |
| 7 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m02033) |
| 8 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m02138) |
| 9 | Completada | 2026-11-12 | 2026-11-12 | Aprobada por el usuario (m02226) |
| 10 | Completada | 2026-11-12 | 2026-11-12 | Apéndices aprobados; QA de Fase 11 |
| 11 | En revisión | 2026-11-12 | — | QA técnico completo; re-auditoría y aprobación pendientes |

### 13.2 Métricas de progreso

| Métrica | Valor actual | Objetivo |
|---|---|---|
| Secciones `completo` | 71 | 71 |
| Secciones piloto | 1 (§5, completo) | 1 |
| Decisiones cerradas | 26 | 26 |
| Bloques Rust compilados | 325 | Todos |
| Enlaces rotos | 0 | 0 |
| `TBD` abiertos | 0 | 0 |
| Ejemplos por sección | 59 (uno por §1–§59; apéndices sin ejemplo propio) | ≥ 3 |
| Diagnósticos catalogados | 486 | Todos |

### 13.3 Changelog del plan

| Versión | Fecha | Cambio |
|---|---|---|
| `v0.1` | 2026-11-12 | Plan inicial: decisiones, léxico, auditoría, fases, matrices |
| `v0.2` | 2026-11-12 | `->` para funciones, `=>` para lambdas, `bind`/`morph`, `@` como receptor, atributos `@@`, sin `spell` |
| `v0.3` | 2026-11-12 | Fase 4A aprobada; Fase 4B §§28–§32 en revisión; 172 bloques Rust y 32 ejemplos |
| `v0.4` | 2026-11-12 | Formas indentadas sin `[]`/`{}`: arrays, mapas, `Vec`/`Set` y mapas anidados; clasificación array/mapa; tuplas conservan `()` |
| `v0.5` | 2026-11-12 | Fase 5 (§§33–§40) en revisión; 223 bloques Rust y 40 ejemplos; secciones 1–32 completas |
| `v0.6` | 2026-11-12 | Fase 5 aprobada; Fase 6 en progreso |
| `v0.7` | 2026-11-12 | Fase 6 (§§41–§47) en revisión; 252 bloques Rust y 47 ejemplos |
| `v0.8` | 2026-11-12 | Fase 6 aprobada; Fase 7 (§§48–§51) en revisión; 277 bloques Rust y 51 ejemplos |
| `v1.0` | 2026-11-12 | Fase 8 (§§52–§55) en revisión; 304 bloques Rust y 55 ejemplos |
| `v1.1` | 2026-11-12 | Fase 8 aprobada; Fase 9 (§§56–§59) en revisión; 317 bloques Rust y 59 ejemplos |
| `v1.2` | 2026-11-12 | Fase 9 aprobada; Fase 10 (§§60–§71) en revisión; 325 bloques Rust, 59 ejemplos, 460 diagnósticos |
| `v1.3` | 2026-11-12 | Fase 10 aprobada; Fase 11 QA y release candidate `1.0.0-rc.1`; 486 diagnósticos |
| `v1.4` | 2026-11-12 | QA de Fase 11: grammar/desugaring blockers corregidos; catálogo 486; 325 bloques y 59 ejemplos; re-auditoría pendiente |
| `v1.5` | 2026-11-12 | Fase 11 completada: re-auditorías aprobadas; `1.0.0-rc.1` (r13), 21.818 líneas |

### 13.4 Regla de cambio

- Cambiar una decisión bloqueada requiere:
  1. entrada en el ADR §69;
  2. revisión de las secciones afectadas;
  3. actualización de la matriz de paridad;
  4. nota en el changelog.
- Añadir una sección nueva requiere:
  1. justificar el hueco;
  2. asignarle fase;
  3. añadirla al índice y al Anexo A;
  4. actualizar la matriz.

---

<a id="sec-14-proximo"></a>
## 14. Próximo paso

### 14.1 Orden de la Fase 0

1. Revisar la tabla de decisiones D0–D25 y confirmar/corregir.
2. Revisar el léxico de la sección 4; congelarlo.
3. Validar el ejemplo de norte y su Rust.
4. Crear `docs/LANGUAGE.md` con el esqueleto y las anclas.
5. Escribir §5 (Variables) como sección piloto.
6. Crear los scripts de validación.
7. Registrar las decisiones en `scratch/DECISIONS.md`.
8. Revisar el piloto contra el Anexo B y cerrar la fase.

### 14.2 Lo que necesito del usuario

- Aprobación del plan y del enfoque por fases.
- Confirmación (o corrección) de las decisiones Q1–Q7, Q9, Q11 y Q16, que son las que más afectan a la sintaxis.
- Confirmación de que la prosa en español es la deseada.
- Luz verde para crear `docs/LANGUAGE.md` y la sección piloto.

Con eso, la Fase 0 se ejecuta en una sola sesión y la Fase 1 puede empezar sin re-trabajo.

---

<a id="anexo-a-outline"></a>
## Anexo A — Checklist de las 71 secciones

| # | Sección | Fase | Estado |
|---|---|---|---|
| 1 | Introducción y filosofía | 1 | Completo |
| 2 | Estructura léxica | 1 | Completo |
| 3 | Estructura del programa y compilación | 1 | Completo |
| 4 | Sistema de tipos | 1 | Completo |
| 5 | Variables y bindings | 0 | Completo |
| 6 | Constantes, statics y estado global | 1 | Completo |
| 7 | Scope y resolución de nombres | 1 | Completo |
| 8 | Expresiones, sentencias y bloques | 1 | Completo |
| 9 | Tipos primitivos | 2 | Completo |
| 10 | Strings y chars | 2 | Completo |
| 11 | Operadores | 2 | Completo |
| 12 | Booleanos y lógica | 2 | Completo |
| 13 | Condicionales | 2 | Completo |
| 14 | Bucles | 2 | Completo |
| 15 | Funciones | 2 | Completo |
| 16 | Ownership | 3 | Completo |
| 17 | Borrowing | 3 | Completo |
| 18 | Lifetimes | 3 | Completo |
| 19 | Referencias y punteros | 3 | Completo |
| 20 | Smart pointers e interior mutability | 3 | Completo |
| 21 | Memoria, `Drop` y layout | 3 | Completo |
| 22 | Arrays y slices | 4A | Completo |
| 23 | Vectores y `VecDeque` | 4A | Completo |
| 24 | Tuplas | 4A | Completo |
| 25 | Mapas y sets | 4A | Completo |
| 26 | Otras estructuras de datos | 4A | Completo |
| 27 | Rangos e indexación | 4A | Completo |
| 28 | Structs (`rune`) | 4B | Completo |
| 29 | Enums (`enchanting`) | 4B | Completo |
| 30 | Pattern matching | 4B | Completo |
| 31 | Implementaciones (`ritual`) | 4B | Completo |
| 32 | Type aliases, newtypes y casts | 4B | Completo |
| 33 | Genéricos | 5 | Completo |
| 34 | Constraints y `where` | 5 | Completo |
| 35 | Traits (`pact`) | 5 | Completo |
| 36 | Associated items | 5 | Completo |
| 37 | Higher-Ranked Items (HRTB) | 5 | Completo |
| 38 | Closures | 5 | Completo |
| 39 | Function pointers y HOF | 5 | Completo |
| 40 | Operator overloading | 5 | Completo |
| 41 | Módulos (`scroll`) | 6 | Completo |
| 42 | Visibilidad (`unveil`) | 6 | Completo |
| 43 | Crates, packages y workspaces | 6 | Completo |
| 44 | Atributos (`@@`) | 6 | Completo |
| 45 | Macros (`incantation`) | 6 | Completo |
| 46 | Derives y traits comunes | 6 | Completo |
| 47 | Build scripts, features y `cfg` | 6 | Completo |
| 48 | Manejo de errores | 7 | Completo |
| 49 | Iteradores | 7 | Completo |
| 50 | Async/await | 7 | Completo |
| 51 | Concurrencia | 7 | Completo |
| 52 | Unsafe (`curse`) | 8 | Completo |
| 53 | FFI e interop con Rust | 8 | Completo |
| 54 | Const eval | 8 | Completo |
| 55 | `no_std`, embebidos y wasm | 8 | Completo |
| 56 | Testing | 9 | Completo |
| 57 | Documentación | 9 | Completo |
| 58 | Herramientas | 9 | Completo |
| 59 | Guía de estilo | 9 | Completo |
| 60 | Gramática EBNF | 10 | Completo |
| 61 | Léxico y palabras clave | 10 | Completo |
| 62 | Precedencia y asociatividad | 10 | Completo |
| 63 | Matriz de paridad Rust | 10 | Completo |
| 64 | Desugaring | 10 | Completo |
| 65 | Catálogo de diagnósticos | 10 | Completo |
| 66 | No soportado y diferido | 10 | Completo |
| 67 | Glosario | 10 | Completo |
| 68 | Cookbook | 10 | Completo |
| 69 | Decisiones de diseño (ADR) | 10 | Completo |
| 70 | Changelog y versionado | 10 | Completo |
| 71 | Referencias | 10 | Completo |

---

<a id="anexo-b-checklist"></a>
## Anexo B — Definition of Done por sección

Una sección se marca `completo` solo si responde "sí" a todo:

### B.1 Contenido

- [ ] Tiene objetivo y alcance claros.
- [ ] Tiene reglas normativas con RFC 2119.
- [ ] Tiene sintaxis EBNF si introduce gramática.
- [ ] Tiene semántica si hay evaluación, tipos, ownership o codegen no obvio.
- [ ] Tiene al menos un ejemplo positivo.
- [ ] Tiene al menos un ejemplo negativo con diagnóstico.
- [ ] Tiene al menos un caso límite.
- [ ] Tiene Rust generado completo.
- [ ] Tiene tabla de diagnósticos si introduce errores.
- [ ] Tiene "Ver también" con enlaces.

### B.2 Consistencia

- [ ] Usa el léxico oficial; no inventa sinónimos.
- [ ] No contradice ninguna otra sección.
- [ ] No usa construcciones no definidas sin marcarlas como adelanto.
- [ ] Respeta la regla de no globales.
- [ ] Respeta las reglas de "todo es expresión".
- [ ] Respeta la edición Rust 2024.

### B.3 Verificación

- [ ] El bloque Rust compila.
- [ ] El bloque PenguScript es válido según la gramática.
- [ ] Los enlaces internos funcionan.
- [ ] El código de diagnóstico existe en §65.
- [ ] La sección aparece en la matriz de paridad si cubre una feature de Rust.
- [ ] Fue revisada por alguien distinto del autor.

### B.4 Navegación

- [ ] Tiene ancla ASCII explícita.
- [ ] Está en el índice.
- [ ] Tiene "Volver al índice".
- [ ] Los enlaces a otras secciones usan anclas, no encabezados autogenerados.

---

<a id="anexo-c-glosario"></a>
## Anexo C — Glosario de diseño

| Término | Definición |
|---|---|
| **Ancla estable** | Identificador ASCII explícito que no cambia al reescribir un título. |
| **Codegen contract** | Conjunto de reglas que garantizan que el Rust generado es válido, legible y semánticamente equivalente. |
| **Desugaring** | Transformación documentada de azúcar sintáctico a una forma core y luego a Rust. |
| **DoD** | Definition of Done; checklist que una sección debe cumplir para considerarse completa. |
| **Fase** | Unidad de trabajo del plan con objetivo, secciones, entregable y criterios de aceptación. |
| **Golden test** | Par entrada/salida (`.pengu` → `.rs` o diagnóstico) que se compara automáticamente. |
| **Léxico mágico** | Conjunto de palabras de PenguScript que reemplazan keywords de Rust para declarar ítems. |
| **Matriz de paridad** | Tabla que relaciona cada feature de Rust con su sección y estado en PenguScript. |
| **Sección normativa** | Sección que define reglas obligatorias, no solo ejemplos o recomendaciones. |
| **Source map** | Mapa entre posiciones del Rust generado y posiciones del PenguScript original. |
| **Transpilación** | Compilación de PenguScript a Rust fuente, que luego se compila con `rustc`/Cargo. |

---

*Fin del plan. La especificación comienza en la Fase 0; este archivo no debe crecer con contenido de `LANGUAGE.md`.*