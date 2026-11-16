<a id="sec-53-ffi"></a>
## 53. FFI e interop con Rust

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 8 |
| Rust | `extern "C"`, `#[no_mangle]`, `#[repr(C)]`, `CStr`/`CString` |
| Palabras mágicas | `foreign`, `@@link`, `@@no_mangle` |
| Depende de | §28, §29, §32, §52 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec53_ffi.pengu` |

PenguScript compila a Rust, así que la interop tiene dos direcciones:

1. **Llamar código externo** (C, Rust, sistema) desde PenguScript.
2. **Exponer código PenguScript** a C u otros lenguajes.

La regla central es que el ABI no se adivina: se declara con `foreign`.

### 53.1 Bloques `foreign`

```pengu
foreign "C"
    abs = (x: Int) -> Int

grimoire
    bind value = curse
        -- SAFETY: `abs` recibe un i32 y no retiene el puntero.
        abs(-7)
    print(value)
```

Rust generado:

```rust
unsafe extern "C" {
    fn abs(x: i32) -> i32;
}

fn main() {
    let value = unsafe {
        // SAFETY: `abs` recibe un i32 y no retiene el puntero.
        abs(-7)
    };
    println!("{}", value);
}
```

1. `foreign "C"` abre un bloque de declaraciones sin cuerpo.
2. Cada línea `name = (params) -> Ret` genera una función `extern`.
3. El bloque completo genera `unsafe extern "C" { ... }` en Rust 2024.
4. Llamar una función `foreign` requiere `curse`.
5. El ABI se escribe como string: `"C"`, `"C-unwind"`, `"system"`,
   `"stdcall"`, `"fastcall"`, `"win64"`, `"sysv64"`.
6. `foreign` no implementa la función; solo declara su firma.
7. Una firma `foreign` no puede tener cuerpo.
8. Las funciones `foreign` no son `unsafe fn` por sí mismas en Rust; el
   bloque externo es unsafe y la llamada se envuelve en `curse`.

### 53.2 Exportar funciones PenguScript

```pengu
@@no_mangle
unveil foreign "C" add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#[unsafe(no_mangle)]
pub extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `foreign "C" name = (params) -> Ret` con cuerpo define una función
   exportada con ABI C.
2. `unveil` la hace `pub`; sin `unveil` el símbolo no se exporta.
3. `@@no_mangle` evita el mangling de Rust; el símbolo se llama `add`.
4. `@@export_name("...")` cambia el nombre del símbolo.
5. `@@link_name("...")` cambia el nombre que se busca al importar.
6. Una función exportada no puede entrar en pánico a través del borde FFI;
   se captura o se marca `"C-unwind"`.
7. Los tipos del borde deben ser `#[repr(C)]`.
8. Los strings no cruzan el borde como `String`; se usa `*const c_char`.

### 53.3 Tipos compatibles con C

```pengu
@@repr(C)
rune PointC
    x: Float
    y: Float
```

Rust generado:

```rust
#[repr(C)]
struct PointC {
    x: f64,
    y: f64,
}
```

| PenguScript | C | Rust |
|---|---|---|
| `I8`/`U8` | `int8_t`/`uint8_t` | `i8`/`u8` |
| `I16`/`U16` | `int16_t`/`uint16_t` | `i16`/`u16` |
| `I32`/`U32` | `int32_t`/`uint32_t` | `i32`/`u32` |
| `I64`/`U64` | `int64_t`/`uint64_t` | `i64`/`u64` |
| `Isize`/`Usize` | `intptr_t`/`uintptr_t` | `isize`/`usize` |
| `Float` | `double` | `f64` |
| `Bool` | `bool` | `bool` |
| `*const T`/`*mut T` | `const T*`/`T*` | `*const T`/`*mut T` |
| `chimera` | `union` | `union` |

1. `@@repr(C)` es obligatorio para structs, enums y uniones que cruzan el
   borde.
2. Un `enchanting` con `@@repr(C)` debe tener campos compatibles con C.
3. Un enum con datos no es un entero C; se usa una struct etiquetada.
4. `Bool` es `bool` de C99; si el header usa `int`, se declara `Int`.
5. `Str` no es `char*`; se usa `*const c_char` o `CStr`.

### 53.4 Tipos opacos

```pengu
@@repr(C)
rune FILE
    _private: [U8; 0]

foreign "C"
    fopen = (path: *const c_char, mode: *const c_char) -> *mut FILE
    fclose = (file: *mut FILE) -> Int
```

1. Un tipo opaco se declara con un campo privado de tamaño cero.
2. El código PenguScript nunca lee `_private`; solo pasa `*mut FILE`.
3. La definición real vive en C.
4. `fopen` puede devolver null; se comprueba antes de usar.
5. `fclose` consume el puntero; no se usa después.
6. Un tipo opaco no implementa `Drop` automático; el recurso se cierra con
   la función externa.

### 53.5 Strings C

```pengu
bind message = c"hello"

bind owned = CString.new("pengu")
bind ptr = owned.as_ptr()
```

Rust generado:

```rust
let message = c"hello";
let owned = std::ffi::CString::new("pengu").unwrap();
let ptr = owned.as_ptr();
```

1. `c"..."` produce `&CStr`; no copia ni asigna.
2. `CString.new(text)` produce un buffer con terminador `NUL`.
3. `CString.new` falla si el texto contiene `NUL`; devuelve `!CString`.
4. `CStr.from_ptr(p)` es `curse` y exige que `p` sea un C string válido.
5. `CStr.to_str()` devuelve `!&Str` por UTF-8 inválido.
6. Un `CString` debe vivir mientras se use su `as_ptr()`.
7. No se libera un `CString` con `free`; lo hace `Drop`.

```rust
use std::ffi::CStr;

fn main() {
    let message = c"hello";
    let len = unsafe { strlen(message.as_ptr()) };
    println!("{} {}", len, message.to_str().unwrap());
}

unsafe extern "C" {
    fn strlen(s: *const std::ffi::c_char) -> usize;
}
```

### 53.6 Llamar a Rust desde PenguScript

Un crate Rust puede exponer funciones `extern "C"` y PenguScript las declara
con `foreign`:

```pengu
foreign "C"
    pengu_add = (a: Int, b: Int) -> Int
```

1. El crate Rust debe exportar `#[unsafe(no_mangle)] pub extern "C" fn`.
2. El enlace se declara en `Tome.toml` con `[dependencies]`.
3. Si la función vive en una librería estática, se añade `@@link`.
4. Los tipos deben ser `#[repr(C)]` o primitivos C.
5. Los errores se convierten en códigos; no se propaga un `Result` Rust.
6. Las panics se capturan antes de cruzar el borde.

### 53.7 Enlace y símbolos

```pengu
@@link(name = "m")
foreign "C"
    cos = (x: Float) -> Float
```

Rust generado:

```rust
#[link(name = "m")]
unsafe extern "C" {
    fn cos(x: f64) -> f64;
}
```

1. `@@link(name = "...")` enlaza una librería nativa.
2. `@@link_name("...")` cambia el símbolo importado.
3. `@@export_name("...")` cambia el símbolo exportado.
4. `@@no_mangle` desactiva el mangling.
5. `@@link_section("...")` coloca el símbolo en una sección.
6. `@@used` evita que el linker elimine el símbolo.
7. Los nombres no pueden colisionar entre crates.

### 53.8 ABI y unwinding

1. `"C"` no permite unwinding a través del borde; una panic es UB.
2. `"C-unwind"` permite unwinding controlado; se usa solo si ambos lados lo
   soportan.
3. `"system"` usa el ABI del sistema (`stdcall` en Windows x86, `C` en el
   resto).
4. Los enteros deben tener tamaño explícito; `Int` es `i32`, no `long`.
5. Los punteros pueden ser nulos; se documenta si lo son.
6. Las callbacks deben ser `extern "C"` y no capturar estado no `Send` sin
   contrato.
7. Un `struct` con `Drop` no se pasa por valor a C sin `ManuallyDrop`.

### 53.9 bindgen y cbindgen

1. **bindgen** genera declaraciones PenguScript a partir de headers C; el
   resultado se revisa y se marca con `@@repr(C)`.
2. **cbindgen** genera headers C a partir de las funciones `foreign`
   exportadas.
3. Las herramientas no forman parte del compilador; son pasos de build.
4. El header generado es la fuente de verdad del ABI.
5. Los nombres generados se pueden ajustar con `@@export_name`.
6. No se confía en bindgen para tipos opacos; se revisan a mano.

### 53.10 Bloque `rust` como escape auditado

```pengu
rust
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
```

1. El bloque `rust` inserta tokens Rust sin traducir.
2. Se usa para bindings generados, no para lógica de negocio.
3. Todo bloque `rust` debe revisarse y marcarse en el source map.
4. No se permite en ejemplos básicos; es una herramienta de interop.
5. El código insertado sigue las reglas de Rust 2024, incluidos
   `#[unsafe(...)]`.
6. Un bloque `rust` no puede declarar globals PenguScript.

### 53.11 wasm

1. `wasm32-unknown-unknown` no tiene `std` completo; se usa `core`/`alloc`.
2. `wasm32-wasip1` tiene un sistema de archivos virtual y `std` parcial.
3. `wasm-bindgen` expone funciones con `@@wasm_bindgen`; el atributo lo
   aporta el proc macro, no el núcleo.
4. Los tipos JS (`JsValue`) se manejan como tipos opacos.
5. El tamaño y la alineación de `usize` cambian; se usan tipos explícitos.
6. Las funciones exportadas usan `foreign "C"` o `wasm-bindgen`.
7. El hilo único es el default; `wasm-bindgen-rayon` requiere features.

### 53.12 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5301` | `foreign` sin ABI | añadir `"C"` u otro ABI |
| `PGS-E5302` | tipo no `repr(C)` en el borde | añadir `@@repr(C)` |
| `PGS-E5303` | llamada a `foreign` sin `curse` | envolver en `curse` |
| `PGS-E5304` | `foreign` con cuerpo y sin `foreign "C"` | declarar el ABI |
| `PGS-E5305` | `CString` con `NUL` | validar el texto |
| `PGS-E5306` | `link_name` duplicado | usar un alias |
| `PGS-W5301` | puntero potencialmente nulo | comprobar `is_null` |
| `PGS-W5302` | panic a través de FFI | capturar o `"C-unwind"` |

### 53.13 Criterios de aceptación

- [x] `foreign` cubre importación y exportación.
- [x] Los tipos del borde tienen una tabla C/Rust.
- [x] Strings, tipos opacos y enlace están definidos.
- [x] El ABI y el unwinding están documentados.
- [x] El bloque `rust` queda como escape auditado.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
