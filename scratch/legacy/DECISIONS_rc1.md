# Decisiones de Fase 0 — PenguScript

**Estado:** cerrado para Fase 0
**Fecha:** 2026-11-12
**Alcance:** D0–D24, preguntas abiertas Q1–Q16, esquema de `Tome.toml` y contrato de codegen.
**Documento normativo:** `docs/LANGUAGE.md` (esqueleto + §5 piloto en Fase 0).

> Este archivo es el registro de trabajo. Se foldeará en el ADR §69 y en §3/§43/§58 cuando esas secciones se escriban. Si una decisión cambia, se agrega una entrada nueva; no se reescribe la historia.
> D25 (colecciones indentadas sin delimitadores) se añadió en Fase 4A y vive en §69; este archivo conserva el registro de Fase 0 para D0–D24.

---

## 1. Decisiones fundacionales D0–D24

Todas quedan **cerradas** para la Fase 0. La columna “Estado” indica si la decisión es normativa o si tiene una dependencia que se resolverá en una sección posterior.

| ID | Decisión | Elección | Motivo | Alternativa descartada | Estado |
|---|---|---|---|---|---|
| D0 | Idioma de la spec | Prosa en español; keywords, código y términos técnicos en inglés | El usuario escribe y revisa en español; el código se lee como Rust | Todo en inglés | Cerrada |
| D1 | Rust objetivo | Rust 2024 estable; MSRV 1.85.0; probado con rustc 1.99.1 | 2024 es la edición que usa el codegen; 1.85 es el primer estable con esa edición | Rust 2021; nightly por defecto | Cerrada |
| D2 | Modelo de compilación | Transpilador a Rust + Cargo; front-end propio; `rustc` es la autoridad final de tipos y borrow | Menos backend, semántica real de Rust, buena interop | Backend propio; intérprete | Cerrada |
| D3 | Indentación | 4 espacios; tabs prohibidos; bloques por indentación; `{}` solo para mapas/token trees | MoonScript/CoffeeScript sin ambigüedad de tabs | Tabs; llaves obligatorias | Cerrada |
| D4 | Léxico | Sustantivos mágicos para ítems; verbos familiares para control | Identidad del lenguaje sin curvas innecesarias | Renombrar todos los keywords | Cerrada |
| D5 | Variables | `bind` inmutable; `morph` mutable; `=` reasigna; prohibidos en módulo | La mutabilidad explícita es una ayuda de seguridad; `morph` no se olvida como `mut` | `bind`/`bind mut`; mutable por defecto | Cerrada |
| D6 | Constantes y statics | `sigil` = `const`; `relic` = `static` inmutable; `static mut` no existe | Conserva la regla de no globales mutables | `const`/`static`; `static mut` | Cerrada |
| D7 | Tipos base | `Int` = `i32`; `UInt` = `u32`; `Float` = `f64`; `Str` = `str`; `String` = `String` | Defaults predecibles y alineados con Rust | `Int` = `isize`; `Str` = `String` | Cerrada |
| D8 | Option/Result | `?T` = `Option<T>`; `!T` = `Result<T, Error>`; también `Option[T]`/`Result[T, E]`; `none`/`some`/`ok`/`err`; `?` postfijo | Azúcar legible sin esconder el tipo real | Solo `Option`/`Result`; `T?`/`T!E` | Cerrada |
| D9 | Todo es expresión | Bloques, `if`, `match`, `loop`, funciones; `bind`/asignación son sentencias; `return`/`break`/`continue` son `Never` | Conserva la ventaja de MoonScript sin romper move semantics | Asignación como expresión | Cerrada |
| D10 | Funciones | `name = (params) -> Tipo`; retorno obligatorio; cuerpo indentado; `(params) => expr` para lambdas; `->` en tipos de función | `->` identifica la función; el retorno explícito evita ambigüedad de parser | `spell`/`fn`; retorno inferido en funciones nombradas | Cerrada |
| D11 | Structs/enums | `rune` = struct; `enchanting` = enum; sin herencia | Palabras mágicas y composición en lugar de clases | `class`/`extends` | Cerrada |
| D12 | Traits/impls | `pact` = trait; `ritual` = impl; receptores `@`, `@mut`, `@own` | `@` es familiar para MoonScript/CoffeeScript | `trait`/`impl`; `self` | Cerrada |
| D13 | Genéricos | `[T]` para parámetros/argumentos; `[const N: Usize]`; lifetimes `'a`; turbofish `foo[Int](x)`; HRTB `for<'a>` | Evita el ruido de `<>` y conserva la sintaxis de índices | `<>` para genéricos | Cerrada |
| D14 | Módulos | Archivo = `scroll`; `summon` = `use`; `unveil` = `pub`; `Tome.toml` = manifiesto | Manifiesto propio con passthrough a Cargo | `mod`/`use`/`pub`; solo `Cargo.toml` | Cerrada |
| D15 | Atributos | `@@attr(...)`; inner `@@!attr(...)`; `@@derive`, `@@cfg`, `@@test`, etc. | `@` ya es el receptor | `#[...]` | Cerrada |
| D16 | Macros | `incantation` = `macro_rules!`; invocación `name!(...)`; token trees con `{}`/`()`/`[]` | Metaprogramación sin proc macros en PenguScript | Macros solo desde Rust | Cerrada |
| D17 | Strings | `Str` no sizeado; `String` owned; interpolación `#{expr}`; raw/byte/C strings; sin indexación por bytes | UTF-8 seguro y explícito | `Str` owned; single quotes para strings | Cerrada |
| D18 | Async/unsafe/FFI | `dream` = async; `awaken` = await; `curse` = unsafe; `foreign` = extern; `chimera` = union; bloque `rust` auditado | Nombres mágicos consistentes | `async`/`await`/`unsafe`/`extern` | Cerrada |
| D19 | Biblioteca estándar | `std`/`core`/`alloc` vía `summon`; sin runtime propio; crates externos vía `tome`; `print`/`format` en el prelude | No reimplementar la std | Biblioteca propia | Cerrada |
| D20 | Documento | Un solo `docs/LANGUAGE.md`; anclas ASCII; plantilla; ejemplos compilables | Requisito explícito del usuario | Varios archivos por tema | Cerrada |
| D21 | Testing/docs/tooling | `@@test`; doc comments `---`; CLI `pengu`; rustfmt/clippy/rustdoc; source maps | Un solo toolchain coherente | Herramientas externas sin integración | Cerrada |
| D22 | Versionado | Semver para la spec; versión de compilador; edición Rust; MSRV; changelog | Reproducibilidad | Sin versionado | Cerrada |
| D23 | Proc macros/build scripts | Proc macros en crates Rust, consumidas vía `tome`; `build.pengu` → `build.rs`; bloque `rust` para casos extremos | Rust no permite definir proc macros en otro lenguaje de forma estable | Proc macros en PenguScript desde el día 1 | Cerrada |
| D24 | Features inestables | Fuera del núcleo; opt-in con `@@feature` + nightly | La spec se mantiene estable | Incluirlas en el núcleo | Cerrada |

### 1.1 Reglas derivadas

1. Ninguna sección puede usar `let`, `fn`, `struct`, `enum`, `trait`, `mod`, `use`, `pub`, `const`, `static`, `self`, `class`, `extends` o `new` como keyword de PenguScript. Solo aparecen en bloques `rust` o en la lista de palabras prohibidas.
2. Todo ítem de nivel superior es una declaración (`rune`, `enchanting`, `pact`, `ritual`, `sigil`, `relic`, `essence`, `scroll`, `summon`, `unveil`, `incantation`, `foreign`), una definición de función `name = (params) -> ...` o un atributo.
3. `grimoire` es el único bloque ejecutable de nivel superior; compila a `fn main`.
4. El Rust generado usa edición 2024: `#[unsafe(no_mangle)]`, `#[unsafe(export_name)]`, `#[unsafe(link_section)]`.
5. Los ejemplos declaran los tipos que la spec promete explícitos.
6. Toda azúcar tiene desugaring documentado o enlace a §64.
7. Todo error tiene código, mensaje, causa y solución.

---

## 2. Preguntas Q1–Q16

Todas quedan resueltas por una decisión D. No hay preguntas bloqueantes para la Fase 1.

| ID | Pregunta | Resolución | Decisión |
|---|---|---|---|
| Q1 | ¿Prosa en español? | Sí; keywords y código en inglés | D0 |
| Q2 | ¿`bind`/`bind mut` o dos palabras? | `bind` inmutable; `morph` mutable | D5 |
| Q3 | ¿`Int` = `i32` y `Float` = `f64`? | Sí | D7 |
| Q4 | ¿`Str` = `str` y `String` = `String`? | Sí | D17 |
| Q5 | ¿Azúcar `?T`/`!T`? | Sí, además de `Option[T]`/`Result[T, E]` | D8 |
| Q6 | ¿Asignación como expresión? | No; es sentencia | D9 |
| Q7 | ¿Receptores `@`/`@mut`/`@own`? | Sí | D12 |
| Q8 | ¿`relic` + `@@shared`? | Sí; `static mut` no existe | D6 |
| Q9 | ¿`Tome.toml` o `Cargo.toml`? | `Tome.toml` con `[cargo]` passthrough | D14 |
| Q10 | ¿Bloque `rust` auditado? | Sí, como último recurso | D18 |
| Q11 | ¿Genéricos `[T]`? | Sí; HRTB `for<'a>` | D13 |
| Q12 | ¿Proc macros en PenguScript? | No; se definen en crates Rust | D23 |
| Q13 | ¿`print`/`format` built-ins? | Sí, en el prelude | D19 |
| Q14 | ¿Conservar `unless`/`then`/`is`/`isnt`? | Sí | D4/D9 |
| Q15 | ¿`print` para salida? | Sí; `format` para construir strings | D19 |
| Q16 | ¿Retorno obligatorio en funciones nombradas? | Sí; las lambdas infieren | D10 |

---

## 3. Esquema de `Tome.toml` (v0.1)

`Tome.toml` es el manifiesto de un paquete PenguScript. El compilador lo traduce a un `Cargo.toml` generado; no se edita el Cargo generado a mano.

### 3.1 Ejemplo completo

```toml
[tome]
name = "hello_pengu"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"
description = "Ejemplo mínimo de PenguScript"
authors = ["PenguScript contributors"]
license = "MIT"
repository = "https://example.invalid/hello_pengu"
readme = "README.md"

[dependencies]
serde = { version = "1", features = ["derive"] }
geometry = { path = "../geometry" }

[dev-dependencies]
pretty_assertions = "1"

[features]
default = ["std"]
std = []

[lib]
path = "src/lib.pengu"

[[bin]]
name = "hello_pengu"
path = "src/main.pengu"

[[test]]
name = "integration"
path = "tests/integration.pengu"

[[bench]]
name = "throughput"
path = "benches/throughput.pengu"
harness = false

[profile.release]
lto = true
codegen-units = 1

[cargo]
# Claves de Cargo que Tome no modela todavía.
# Se fusionan al final; no pueden sobrescribir package.name/version/edition
# ni los paths de lib/bin/test/bench.
```

### 3.2 Reglas

- `[tome]` es obligatorio. `name`, `version`, `pengu`, `edition` y `rust-version` son obligatorios.
- `name` usa `snake_case`; `version` es SemVer; `edition` es una edición de Rust; `rust-version` es la MSRV.
- `pengu` es la versión de la spec que el paquete requiere. El compilador rechaza una versión incompatible.
- `[dependencies]`, `[dev-dependencies]` y `[build-dependencies]` aceptan:
  - versión: `serde = "1"`;
  - tabla: `{ version, path, git, branch, tag, rev, features, default-features, optional }`;
  - path a un directorio con `Tome.toml` para dependencias PenguScript.
- `[features]` es idéntico a Cargo; `default` es una lista.
- `[lib]`, `[[bin]]`, `[[test]]`, `[[bench]]`, `[[example]]` usan `path` con extensión `.pengu`; el codegen genera el `.rs` correspondiente.
- `[workspace]` acepta `members` y `exclude`; los miembros son directorios con `Tome.toml`.
- `[profile.*]` se pasa a Cargo.
- `[cargo]` es el escape para claves de Cargo no modeladas. Se prohíbe sobrescribir `package.name`, `package.version`, `package.edition`, `lib.path`, `bin.path`, `test.path`, `bench.path` y `example.path`.
- `Tome.lock` no forma parte de v0.1. El lock real es `Cargo.lock`, generado en `target/pengu/`. Se reserva `Tome.lock` para §58.

### 3.3 Mapeo a Cargo

| `Tome.toml` | `Cargo.toml` generado |
|---|---|
| `tome.name` | `package.name` |
| `tome.version` | `package.version` |
| `tome.edition` | `package.edition` |
| `tome.rust-version` | `package.rust-version` |
| `tome.description/authors/license/repository/readme` | mismos campos de `package` |
| `dependencies` | `dependencies` |
| `dev-dependencies` | `dev-dependencies` |
| `build-dependencies` | `build-dependencies` |
| `features` | `features` |
| `lib` | `lib` (con `path` reescrito) |
| `[[bin]]` | `[[bin]]` (con `path` reescrito) |
| `[[test]]` | `[[test]]` |
| `[[bench]]` | `[[bench]]` |
| `[[example]]` | `[[example]]` |
| `profile.*` | `profile.*` |
| `cargo.*` | se fusiona al final, con las claves protegidas |

---

## 4. Contrato de codegen (v0.1)

### 4.1 Entradas y salidas

**Entrada:** árbol de fuentes `.pengu`, `Tome.toml`, `build.pengu` opcional.

**Salida:** `target/pengu/` con:

```text
target/pengu/
  Cargo.toml
  Cargo.lock
  build.rs                 # si existe build.pengu
  src/
    main.rs
    lib.rs
    <modulos>.rs
  sourcemap.json
```

- El compilador no escribe `.rs` junto a los `.pengu`; `target/pengu/` es descartable.
- `pengu build` ejecuta `cargo build --manifest-path target/pengu/Cargo.toml`.
- `pengu run` ejecuta el binario; `pengu check` ejecuta `cargo check`.
- Los archivos generados llevan `// @generated by pengu <version>; do not edit`.

### 4.2 Nombres y módulos

- Funciones, métodos, variables y módulos: `snake_case`.
- Tipos, enums, traits y aliases: `PascalCase`.
- Constantes y statics: `SCREAMING_SNAKE_CASE`.
- Archivo `foo.pengu` → módulo `foo` y archivo `src/foo.rs`.
- `src/main.pengu` → `src/main.rs`; `src/lib.pengu` → `src/lib.rs`.
- `scroll foo` inline → `mod foo { ... }` en el mismo archivo.
- Si un nombre coincide con una keyword de Rust, se genera con sufijo `_` (`type_`, `match_`). Nunca se usa `r#` para `self`, `Self`, `super` o `crate`; esos nombres se manglean con sufijo.
- Colisiones: se agrega `_2`, `_3`, … en orden determinista.
- El codegen no renombra nombres públicos sin documentarlo en el source map.

### 4.3 Atributos y `allow`

- `#[unsafe(no_mangle)]`, `#[unsafe(export_name = "...")]`, `#[unsafe(link_section = "...")]` para FFI/2024.
- No se emiten `#![allow(...)]` globales.
- `#[allow(non_snake_case)]` solo en símbolos `foreign` que lo requieran, con comentario `// FFI`.
- `#[allow(unused_mut)]` no se usa para tapar un `morph` no mutado; si el binding no se muta, el linter de PenguScript sugiere `bind`.
- `#[allow(dead_code)]` no se emite por defecto; el usuario puede pedirlo con `@@allow(dead_code)`.

### 4.4 Formato y determinismo

- `rustfmt --edition 2024` sobre todos los `.rs`.
- Orden de módulos, imports y mappings determinista; sin timestamps ni rutas absolutas.
- Los comentarios generados son estables y no contienen información de sesión.
- `sourcemap.json` se escribe con claves ordenadas y saltos de línea `\n`.

### 4.5 Source maps y diagnósticos

`sourcemap.json`:

```json
{
  "version": 1,
  "mappings": [
    {
      "generated": { "file": "src/main.rs", "line": 5, "column": 5 },
      "original": { "file": "src/main.pengu", "line": 2, "column": 5 }
    }
  ]
}
```

- `generated.file` es una ruta relativa a `target/pengu/`; un crate multiarchivo
  puede tener mappings a varios `.rs`.
- Líneas y columnas son 1-based.
- Cada sentencia y cada ítem generado tiene al menos un mapping.
- `pengu check` ejecuta `cargo check --message-format=json` y remapea el span primario con el mapping más cercano.
- Si un diagnóstico de Rust no tiene mapping, se muestra el span generado y se agrega la nota `origen PenguScript no disponible`.
- Los diagnósticos de PenguScript tienen código `PGS-E####`/`PGS-W####`; los de Rust se muestran con prefijo `rustc` y el archivo original cuando se puede mapear.

### 4.6 Reglas de Rust 2024

| Tema | Regla |
|---|---|
| Atributos unsafe | `#[unsafe(no_mangle)]`, `#[unsafe(export_name)]`, `#[unsafe(link_section)]` |
| `unsafe_op_in_unsafe_fn` | Toda operación unsafe dentro de `curse` se envuelve en `unsafe { ... }` |
| `gen` reservado | Se manglea si aparece como identificador |
| `impl Trait` con lifetimes | Se emite `+ use<'a, T>` cuando sea necesario |
| `if let`/temporales | Se insertan bloques para preservar el drop de 2024 |
| Tail expression | Se preserva el orden de drop con temporales explícitos si hace falta |
| `static mut` | Nunca se genera |
| Formato | `rustfmt --edition 2024` |

### 4.7 Invariantes

1. El Rust generado compila con `rustc --edition 2024` y la MSRV 1.85.
2. Cada ejemplo `rust` completo del documento compila.
3. Cada `bind` genera `let`; cada `morph` genera `let mut`; nunca al revés.
4. Ningún `bind`/`morph` de módulo llega al codegen.
5. Ningún `static mut` llega al codegen.
6. Todo `unsafe` de PenguScript está dentro de `curse` o de un bloque `rust` auditado.

---

## 5. Ejemplo de norte validado

### 5.1 PenguScript

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

### 5.2 Rust generado

```rust
// @generated by pengu 0.1.0; do not edit
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

### 5.3 Validación

- Compilado con `rustc 1.99.1 --edition 2024`.
- Ejecutado: imprime `length = 5`.
- La versión PenguScript usa 4 espacios y la sintaxis v0.2 (`->`, `@`, `bind`).
- El ejemplo no usa variables globales; `Point` y `main` son ítems.

---

## 6. Consecuencias y pendientes

- **§5** queda como sección piloto; su revisión externa es la aprobación del usuario.
- **§3, §43 y §58** deben absorber este contrato sin contradecirlo.
- **§65** debe incluir los códigos `PGS-E1001`–`PGS-E1008` definidos en §5.
- **§69** debe enlazar este archivo como registro histórico.
- **§70** debe reflejar la versión `0.1.0-dev` de la spec y la MSRV 1.85.0.
- No hay decisiones D0–D24 abiertas. Cualquier cambio posterior requiere una nueva entrada y revisión de las secciones afectadas.
