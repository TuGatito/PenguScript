<a id="sec-44-atributos"></a>
## 44. Atributos (@@)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | `#[...]`, `#![...]` |
| Palabras mágicas | `@@`, `@@!` |
| Depende de | §28, §35, §45, §46 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec44_attributes.pengu` |

Un **atributo** es metadato de compilación. En PenguScript se escribe con `@@`
para no confundirlo con `@` (receptor). Los atributos internos, que aplican al
item que los contiene, usan `@@!`.

### 44.1 Sintaxis

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Int
    y: Int

@@inline
add = (a: Int, b: Int) -> Int
    a + b

@@must_use
important = () -> Int
    42
```

Rust generado:

```rust
#[derive(Debug, Clone, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

#[inline]
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[must_use]
fn important() -> i32 {
    42
}
```

Reglas:

1. `@@nombre` sin argumentos; `@@nombre(args)` con argumentos.
2. Varios atributos van en líneas consecutivas antes del item.
3. El orden se conserva en el Rust generado.
4. `@@!` es un atributo interno y debe ir al inicio del archivo o del bloque
   `scroll`, antes de cualquier item.
5. Los argumentos son literales, identificadores o listas; no expresiones
   arbitrarias.
6. Un atributo desconocido es error (`PGS-E4410`), salvo que venga de una proc
   macro importada.
7. Los atributos no cambian la semántica del lenguaje; solo el codegen o el
   compilador de Rust.

### 44.2 Atributos internos

```pengu
@@!allow(dead_code)
@@!doc("Crate de ejemplo")

print("pengu")
```

Rust generado:

```rust
#![allow(dead_code)]
#![doc = "Crate de ejemplo"]

fn main() {
    println!("pengu");
}
```

1. `@@!` solo es válido al inicio de la raíz o de un `scroll`.
2. Un atributo interno después de un item es error (`PGS-E4411`).
3. `@@!allow`/`deny`/`warn` afectan a todo el módulo.
4. `@@!doc` documenta el crate o módulo.
5. `@@!no_std` convierte el crate en `no_std`; se detalla en §55.

### 44.3 Tabla de atributos

| PenguScript | Rust | Efecto |
|---|---|---|
| `@@derive(T1, T2)` | `#[derive(T1, T2)]` | genera impls |
| `@@repr(C)` / `@@repr(u8)` | `#[repr(...)]` | layout/discriminante |
| `@@cfg(cond)` | `#[cfg(cond)]` | compilación condicional |
| `@@cfg_attr(cond, attr)` | `#[cfg_attr(...)]` | atributo condicional |
| `@@test` | `#[test]` | test unitario |
| `@@bench` | `#[bench]` | benchmark (nightly) |
| `@@ignore` | `#[ignore]` | test ignorado |
| `@@should_panic` | `#[should_panic]` | test que debe fallar |
| `@@inline` / `@@inline(always)` | `#[inline]` | inline hint |
| `@@cold` | `#[cold]` | ruta fría |
| `@@track_caller` | `#[track_caller]` | ubicación del llamador |
| `@@must_use` | `#[must_use]` | valor que no se debe ignorar |
| `@@deprecated("msg")` | `#[deprecated(note = "msg")]` | aviso de uso |
| `@@non_exhaustive` | `#[non_exhaustive]` | obliga a `_` fuera del crate |
| `@@doc("texto")` | `#[doc = "texto"]` | documentación |
| `@@allow(lint)` | `#[allow(lint)]` | permite lint |
| `@@deny(lint)` | `#[deny(lint)]` | prohíbe lint |
| `@@warn(lint)` | `#[warn(lint)]` | avisa lint |
| `@@no_mangle` | `#[unsafe(no_mangle)]` | símbolo sin mangling |
| `@@link(...)` | `#[link(...)]` | biblioteca nativa |
| `@@link_name("x")` | `#[link_name = "x"]` | nombre de símbolo |
| `@@link_section("x")` | `#[link_section = "x"]` | sección del binario |
| `@@export_name("x")` | `#[export_name = "x"]` | símbolo exportado |
| `@@used` | `#[used]` | conservar símbolo |
| `@@path("ruta")` | `#[path = "ruta"]` | ruta de módulo |
| `@@macro_use` | `#[macro_use]` | importar macros |
| `@@panic_handler` | `#[panic_handler]` | handler de pánico |
| `@@global_allocator` | `#[global_allocator]` | allocator global |
| `@@no_std` | `#![no_std]` | crate sin std |
| `@@feature(...)` | `#![feature(...)]` | feature nightly |
| `@@target_feature(...)` | `#[target_feature(...)]` | instrucciones |
| `@@non_exhaustive` | `#[non_exhaustive]` | variantes futuras |

1. Los atributos de nightly (`@@bench`, `@@feature`) requieren un toolchain
   nightly; el compilador lo comprueba.
2. `@@no_mangle`, `@@link_section`, `@@export_name` y `@@target_feature` son
   `unsafe` en Rust 2024; el codegen emite `#[unsafe(...)]`.
3. `@@repr` solo se aplica a structs/enums; en otro item es error.
4. `@@derive` solo se aplica a structs/enums; en una función es error.
5. `@@cfg` se puede aplicar a cualquier item.

### 44.4 `@@cfg` y `@@cfg_attr`

```pengu
@@cfg(debug_assertions)
debug_only = () -> Int
    1

@@cfg_attr(debug_assertions, derive(Debug))
rune Config
    name: String
```

Rust generado:

```rust
#[cfg(debug_assertions)]
fn debug_only() -> i32 {
    1
}

#[cfg_attr(debug_assertions, derive(Debug))]
struct Config {
    name: String,
}
```

1. `@@cfg` elimina el item si la condición es falsa; no es un `if` de runtime.
2. `@@cfg_attr` aplica el atributo solo si la condición se cumple; en el ejemplo,
   solo en builds con `debug_assertions`.
3. Las condiciones usan la sintaxis de `cfg` de Rust: `feature = "x"`,
   `target_os = "linux"`, `debug_assertions`, `all(...)`, `any(...)`, `not(...)`.
4. Una feature no declarada en `Tome.toml` produce `PGS-W4410`.
5. `@@cfg` no puede depender de valores de runtime.

### 44.5 Atributos de documentación

```pengu
@@doc("Punto en el plano.")
@@derive(Debug, Clone, Copy)
rune Point
    @@doc("Coordenada horizontal.")
    x: Int
    y: Int
```

Rust generado:

```rust
#[doc = "Punto en el plano."]
#[derive(Debug, Clone, Copy)]
struct Point {
    #[doc = "Coordenada horizontal."]
    x: i32,
    y: i32,
}
```

1. `---` es el comentario de documentación idiomático; `@@doc("...")` es la
   forma explícita cuando se genera desde una herramienta.
2. `@@doc` acepta un string; no acepta Markdown como bloque.
3. `@@doc(hidden)` oculta el item de la documentación.
4. La documentación de un campo debe ir antes del campo.
5. `@@doc` en un `scroll` documenta el módulo.

### 44.6 Atributos de proc macro

```pengu
summon serde::Serialize
summon serde::Deserialize

@@derive(Serialize, Deserialize)]
rune User
    name: String
```

1. Un atributo de proc macro solo existe si la crate que lo define está en
   `Tome.toml` y el nombre está en scope.
2. PenguScript no define proc macros; las consume (§45).
3. `@@derive` con un nombre no importado es error (`PGS-E4412`).
4. Un atributo de función (`@@my_attr(...)`) se aplica al item siguiente.
5. El orden importa: `@@derive` antes de `@@repr` es lo habitual, pero el
   codegen conserva el orden escrito.

### 44.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4410` | atributo desconocido | importar la proc macro o corregir el nombre |
| `PGS-E4411` | `@@!` después de un item | moverlo al inicio |
| `PGS-E4412` | derive no importado | `summon` la crate |
| `PGS-E4413` | `@@repr` en un item no válido | aplicarlo a struct/enum |
| `PGS-E4414` | `@@derive` en una función | quitarlo |
| `PGS-W4410` | `cfg` con feature no declarada | declararla en `Tome.toml` |
| `PGS-W4411` | atributo redundante | simplificar |

### 44.8 Criterios de aceptación

- [x] `@@` y `@@!` tienen sintaxis y posición definidas.
- [x] La tabla cubre los atributos built-in.
- [x] `cfg`, `cfg_attr` y documentación tienen ejemplo.
- [x] La relación con proc macros está explícita.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
