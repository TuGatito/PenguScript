<a id="sec-19-referencias"></a>
## 19. Referencias y punteros

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `&T`, `&mut T`, `*const T`, `*mut T`, `&raw`, `NonNull` |
| Palabras mágicas | `&`, `&mut`, `&raw`, `curse` |
| Depende de | §17, §18 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec19_pointers.pengu` |

PenguScript distingue tres familias:

| Forma | Tipo | Seguridad | Null |
|---|---|---|---|
| referencia compartida | `&T` | segura | no |
| referencia mutable | `&mut T` | segura | no |
| puntero raw | `*const T` / `*mut T` | solo en `curse` | puede ser null |

Las referencias son la forma normal de prestar. Los punteros raw existen para
FFI, estructuras de datos de bajo nivel y código `curse`; no son un reemplazo de
`&`/`&mut`.

### 19.1 Referencias

```pengu
grimoire
    bind value = 42
    bind shared = &value
    print(*shared)

    morph text = String.from("pengu")
    bind mutable = &mut text
    mutable.push_str("!")
    print(text)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let shared = &value;
    println!("{}", *shared);

    let mut text = String::from("pengu");
    let mutable = &mut text;
    mutable.push_str("!");
    println!("{}", text);
}
```

Reglas:

1. `&value` produce `&T`; `*r` lee el valor apuntado.
2. `&mut value` produce `&mut T`; requiere `morph`.
3. `*r = value` escribe a través de `&mut T`.
4. Las referencias nunca son null y siempre apuntan a un valor válido.
5. Un `&T` no permite mover el valor; un `&mut T` tampoco.

### 19.2 Punteros raw

```pengu
grimoire
    bind value = 42
    bind p = &raw const value
    print(p as Usize)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let p = &raw const value;
    println!("{}", p as usize);
}
```

Reglas:

1. `&raw const place` crea `*const T` sin crear una referencia intermedia.
2. `&raw mut place` crea `*mut T`; requiere `morph`.
3. Un puntero raw puede ser null, dangling o apuntar a memoria no inicializada;
   el compilador no lo comprueba.
4. Crear un puntero raw es seguro; **desreferenciarlo** requiere `curse`.
5. `p as Usize` convierte la dirección; `p as *const U` cambia el tipo.
6. `*const T` y `*mut T` no implementan `Send`/`Sync` por defecto; §52 lo trata.

### 19.3 Desreferenciar y `curse`

```pengu
curse read = (p: *const Int) -> Int
    *p
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    unsafe { *p }
}
```

Una función `curse` es `unsafe fn`; su cuerpo se trata como un bloque
`unsafe`. En el call site se necesita un bloque `curse`:

```pengu
grimoire
    bind value = 42
    bind p = &raw const value
    curse
        bind read = *p
        print(read)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let p = &raw const value;
    unsafe {
        let read = *p;
        println!("{}", read);
    }
}
```

Reglas:

1. `curse` como modificador declara una función `unsafe fn`.
2. `curse` como bloque introduce un contexto `unsafe` y produce el valor de su
   última expresión.
3. `*p` sobre `*const T`/`*mut T` solo es válido dentro de `curse`
   (`PGS-E1901`).
4. Escribir `*p = value` requiere `*mut T` y `curse`.
5. Llamar a una función `curse` requiere un bloque `curse` (`PGS-E1902`).
6. El bloque `curse` no relaja las reglas de aliasing ni de lifetimes; solo
   permite operaciones que Rust marca como unsafe.

### 19.4 `NonNull`

`NonNull[T]` es un puntero no nulo, pero no garantiza que sea válido:

```pengu
bind value = 42
bind ptr: NonNull[Int] = NonNull.from(&mut value)
```

Rust generado:

```rust
use std::ptr::NonNull;

fn main() {
    let mut value = 42;
    let ptr: NonNull<i32> = NonNull::from(&mut value);
    println!("{}", ptr.as_ptr() as usize);
}
```

Reglas:

1. `NonNull[T]` no puede ser null; es la opción para “puntero no nulo”.
2. `NonNull::from(&mut value)` crea un `NonNull` a partir de una referencia.
3. `ptr.as_ptr()` devuelve `*mut T`; para leer se necesita `curse`.
4. Un `NonNull` puede quedar dangling si el valor se libera; el tipo no lo evita.
5. Para un puntero que puede ser null se usa `?NonNull[T]` (`Option<NonNull<T>>`),
   no un `NonNull` “null”.

### 19.5 Aritmética de punteros

```pengu
curse offset = (p: *const Int, n: Usize) -> *const Int
    p.add(n)
```

Rust generado:

```rust
unsafe fn offset(p: *const i32, n: usize) -> *const i32 {
    unsafe { p.add(n) }
}
```

Reglas:

1. `p.add(n)` avanza `n` elementos, no `n` bytes; `n` se multiplica por
   `size_of::<T>()`.
2. El puntero resultante debe quedar dentro de la misma allocation o uno pasado
   el final; si no, la operación es UB.
3. `p.offset(n)` acepta enteros con signo; `p.add(n)`/`p.sub(n)` usan `Usize`.
4. `p.wrapping_add(n)` no exige estar dentro de la allocation, pero desreferenciar
   fuera de ella sigue siendo UB.
5. No se hace aritmética sobre `&T`; se convierte a `*const T` primero.

### 19.6 Null, dangling y provenance

| Concepto | Qué es | Cómo se evita |
|---|---|---|
| null | dirección 0 | usar `?NonNull[T]` o `Option<*const T>` |
| dangling | apunta a memoria liberada | mantener vivo el dueño |
| uninitialized | memoria sin inicializar | `MaybeUninit`/`MaybeUninit::assume_init` en `curse` |
| provenance | permiso de acceso que acompaña al puntero | no fabricar punteros con enteros; usar `&raw` |
| aliasing | dos accesos incompatibles | respetar `&T`/`&mut T` también en `curse` |

Rust usa **provenance**: un puntero no es solo una dirección, también lleva el
permiso sobre una allocation. Convertir un `Usize` arbitrario a puntero y
desreferenciarlo es UB aunque la dirección “exista”. La única forma portable de
obtener un puntero es `&raw`, un `NonNull` derivado de una referencia, o una
API de FFI documentada.

### 19.7 `curse` y FFI

Las funciones `foreign` con punteros se declaran en §54. Una función `curse`
puede recibir punteros de C, pero debe documentar:

- si el puntero puede ser null;
- quién es el dueño de la memoria;
- cuánto vive;
- si la función libera o no;
- si el puntero debe estar alineado.

Sin ese contrato, el código `curse` es una fuente de UB. La regla de PenguScript
es: **todo `curse` tiene un comentario de seguridad** (`-- SAFETY: ...`) o un
`@@safety` que lo sustituya. El linter lo comprueba (`PGS-W1901`).

### 19.8 Ejemplo completo

```pengu
curse read = (p: *const Int) -> Int
    *p

grimoire
    bind value = 42
    bind p = &raw const value
    bind copy = curse
        *p
    print(copy)
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    unsafe { *p }
}

fn main() {
    let value = 42;
    let p = &raw const value;
    let copy = unsafe { *p };
    println!("{}", copy);
}
```

`read` no se usa en este ejemplo; existe para mostrar la firma. El bloque
`curse` de `main` sí lee `p`.

### 19.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1901` | deref de raw pointer fuera de `curse` | envolver en `curse` |
| `PGS-E1902` | llamada a función `curse` sin bloque `curse` | añadir `curse` |
| `PGS-E1903` | `&raw mut` sobre binding inmutable | usar `morph` |
| `PGS-E1904` | `NonNull` construido desde null | usar un valor válido |
| `PGS-E1905` | aritmética fuera de la allocation | rediseñar el offset |
| `PGS-E1906` | escritura con `*const T` | usar `*mut T` |
| `PGS-W1901` | `curse` sin comentario `SAFETY` | documentar el contrato |

### 19.10 Criterios de aceptación

- [x] Referencias y punteros raw están diferenciados.
- [x] `&raw const`/`&raw mut` y `*p` están definidos.
- [x] `curse` como modificador y como bloque está definido.
- [x] `NonNull`, null, dangling y provenance están cubiertos.
- [x] La aritmética de punteros y sus límites están explicados.
- [x] FFI y el contrato de seguridad se enlazan a §52/§54.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

