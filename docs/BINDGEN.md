# `pengu bindgen` — Bindings de C para PenguScript

`pengu bindgen` lee una cabecera de C con `clang` y genera un archivo de
declaraciones (`.d.pengu`) que el compilador carga como un módulo más.

```console
$ pengu bindgen /usr/include/zlib.h -o zlib.d.pengu
generado zlib.d.pengu: 37 función(es), 1 estructura(s), 0 constante(s), 49 omitido(s)
```

## Manifiesto

Un declarado se registra en `Tome.toml` y se enlaza con `[link]`:

```toml
[link]
z

[declarations]
zlib = "zlib.d.pengu"
```

Con eso, `summon zlib::zlibVersion` importa la función como cualquier otro
item. Las firmas declaradas son `foreign "C"`, así que **solo se pueden llamar
desde `curse`**:

```pengu
summon std::ffi
summon zlib::zlibVersion

--- Devuelve la versión de zlib copiada a un `String` propio.
version = () -> String
    -- SAFETY: la cadena la devuelve zlib, es estática y no se libera.
    bind raw = curse
        zlibVersion()
    ffi.cstr_to_string_lossy(raw)
```

Cada bloque `curse` exige un comentario `-- SAFETY:` (`PGS-E1603`), y usar una
declaración `abi "C"` sin `[link]` es `PGS-E2023`.

## Mapeo de tipos

| C | PenguScript |
| --- | --- |
| `bool` | `Bool` |
| `char`, `signed char` | `I8` |
| `short`, `int`, `long` | `I16`, `Int`, `Int` |
| `unsigned char` … `unsigned long long` | `U8` … `U64` |
| `size_t`, `ssize_t` | `Usize`, `Isize` |
| `int8_t` … `uint64_t` | `I8` … `U64` |
| `float`, `double` | `F32`, `Float` |
| `const char *` | `CStr` (en firmas viaja como puntero C) |
| `void *` | `Ptr[U8]` |
| `struct N *` (completo) | `Ptr[N]` |
| `struct N *` (opaco) | `Ptr[U8]` |
| `enum N` | `Int` |
| constantes de enum | `NOMBRE: Int = valor` |

Los `rune` generados llevan `#[repr(C)]`, el mismo layout que en C; el orden de
declaración respeta las dependencias por valor.

## Qué se omite y por qué

`--verbose` lista cada omisión:

- **Variádicas** (`printf`): no hay forma de construirlas en el lenguaje.
- **Punteros a función**: `Ptr[T]` no admite funciones todavía.
- **Uniones y bitfields**: no se adivina un layout distinto al de C.
- **Campos anónimos**: tampoco se adivinan.
- **Tipos opacos por valor**: si una estructura contiene un tipo que no se
  puede representar, se descarta la estructura y las firmas que la usan por
  valor; los punteros a esos tipos se emiten como `Ptr[U8]`.
- **`long double`**: no hay tipo equivalente.

La salida es determinista: orden por nombre y ninguna ruta absoluta ni marca de
tiempo, así que `pengu bindgen --check` sirve en CI.

## Opciones

| Opción | Efecto |
| --- | --- |
| `-o`, `--output` | Archivo de salida (por defecto `<cabecera>.d.pengu`) |
| `-I`, `--include` | Directorio de búsqueda para `#include` |
| `-D`, `--define` | Macro definida |
| `--allow`, `--block` | Allowlist y blocklist de nombres (`*` y `?`) |
| `--check` | Falla si el archivo no coincide con la cabecera |
| `-v`, `--verbose` | Lista los omitidos y su motivo |

## Corpus de pruebas

`crates/pengu-bindgen/tests/real_headers.rs` genera declarados de
`/usr/include/zlib.h`, `/usr/include/sqlite3.h` y `/usr/include/stdio.h`, y
verifica que el compilador los acepta. El ejemplo `examples/zlib.pengu` llama a
la biblioteca real y comprueba la versión.

Si `clang` no está instalado, el comando devuelve `PGS-E2101`; si la cabecera no
compila, `PGS-E2102` con la primera línea de `stderr` de `clang`.

## Limitaciones conocidas

- Solo C, sin C++ (name mangling y plantillas quedan fuera).
- Las macros no se expanden a constantes: solo los `enum`.
- Los `typedef` de punteros a función no se representan.
- `[link]` enlaza la biblioteca a nivel de programa; no hay carga dinámica.
