---

<a id="sec-16"></a>
## 16. FFI: `foreign` y `curse`

### 16.1 `foreign`

`foreign "C"` declara funciones externas. No tiene cuerpo y no exporta nada:

```pengu
foreign "C"
    puts = (text: &CStr) -> Int
    strlen = (text: &CStr) -> Usize
```

Un bloque `foreign` solo contiene firmas. No puede contener records, sums ni
funciones con cuerpo.

### 16.2 `curse`

Llamar a una función `foreign` requiere un bloque `curse`:

```pengu
summon std::ffi::CString

say = (text: &Str) -> Unit
    bind c_text = CString.new(text) else
        return
    curse
        -- SAFETY: `c_text` vive hasta el final del bloque y `puts` no la guarda.
        _ = puts(&c_text)
```

Reglas:

- `curse` es la única puerta a FFI.
- Cada bloque `curse` debe tener un comentario `-- SAFETY:` que explique por
  qué la llamada es válida.
- No hay punteros crudos, `transmute`, uniones, asm ni acceso directo a
  memoria.
- No se puede exportar una función PenguScript a C en v1.
- El bloque `curse` no se puede usar para saltarse ownership, tipos ni
  visibilidad.

Una función que siempre requiere `curse` se declara con el modificador:

```pengu
curse read_raw = (fd: Int) -> Int
    foreign_read(fd)
```

Llamar a `read_raw` también requiere `curse`.

### 16.3 Tipos de FFI

| Penguin | C |
|---|---|
| `Int` | `int32_t` |
| `I64` | `int64_t` |
| `U8` | `uint8_t` |
| `Usize` | `size_t` |
| `Float` | `double` |
| `Bool` | `bool` (solo si el header lo garantiza) |
| `&CStr` | `const char *` |
| `*` | no disponible |

`CStr` y `CString` viven en `std.ffi`. `CString.new` puede fallar si el string
contiene un byte nulo; devuelve `Result[CString, NulError]`.

### 16.4 ABI

- El único ABI del núcleo es `"C"`.
- No hay variádicas.
- Una función `foreign` que puede hacer panic debe documentarlo; el backend
  no deja que un panic cruce la frontera C.
- Los errores de C se convierten en `Result` explícito.

### 16.5 Ejemplo completo

```pengu
summon std::ffi::CString

foreign "C"
    puts = (text: &CStr) -> Int

grimoire
    bind message = CString.new("hola desde PenguScript") else
        panic("string con NUL")
    curse
        -- SAFETY: el CString vive hasta después de la llamada y puts no retiene el puntero.
        _ = puts(&message)
```

### 16.6 Diagnósticos de FFI

| Código | Situación |
|---|---|
| `PGS-E1601` | `foreign` con cuerpo. |
| `PGS-E1602` | Llamada a `foreign` fuera de `curse`. |
| `PGS-E1603` | `curse` sin comentario `-- SAFETY:`. |
| `PGS-E1604` | Tipo no representable en C. |
| `PGS-E1605` | ABI desconocido. |
| `PGS-E1606` | Exportación de función PenguScript a C. |
| `PGS-E1607` | `curse` usado fuera de FFI. |
| `PGS-E1608` | `CString` sin manejo de `NulError`. |

[↑ Volver al índice](#indice)
