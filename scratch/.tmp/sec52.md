<a id="sec-52-unsafe"></a>
## 52. Unsafe (`curse`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 8 |
| Rust | `unsafe`, raw pointers, unions, `transmute` |
| Palabras mágicas | `curse`, `chimera`, `transmute` |
| Depende de | §16–§21, §28, §31, §53 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec52_unsafe.pengu` |

`curse` es la palabra para `unsafe`. No es un modo global ni una puerta
trasera: es un contrato local que el programador firma y justifica. Todo
`curse` debe tener un comentario `-- SAFETY:` que explique por qué se cumple el
invariante.

### 52.1 `curse` en funciones y bloques

```pengu
curse read = (p: *const Int) -> Int
    -- SAFETY: el llamador garantiza que `p` apunta a un Int válido.
    *p

grimoire
    bind x = 42
    bind p = &raw const x
    bind value = curse
        -- SAFETY: `p` apunta a `x`, que sigue vivo.
        *p
    print(value)
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    // SAFETY: el llamador garantiza que `p` apunta a un Int válido.
    unsafe { *p }
}

fn main() {
    let x = 42;
    let p = &raw const x;
    let value = unsafe {
        // SAFETY: `p` apunta a `x`, que sigue vivo.
        *p
    };
    println!("{}", value);
}
```

1. `curse name = (...) -> T` genera `unsafe fn`.
2. Un bloque `curse` genera `unsafe { ... }` y puede contener varias
   operaciones.
3. Llamar a una función `curse` requiere un contexto `curse`.
4. Un bloque `curse` no cambia el tipo de su última expresión.
5. `curse` no silencia el borrow checker; solo habilita operaciones marcadas
   como unsafe.
6. Un `curse` sin `-- SAFETY:` es warning (`PGS-W5201`).
7. `@@deny(unsafe_op_in_unsafe_fn)` obliga a envolver cada operación unsafe
   dentro de una función unsafe; es la política recomendada.

### 52.2 Punteros raw

| Operación | Rust | Seguridad |
|---|---|---|
| `&raw const x` | `&raw const x` | crear el puntero es seguro |
| `&raw mut x` | `&raw mut x` | crear el puntero es seguro |
| `*p` (lectura) | `*p` | requiere `curse` |
| `*p = v` (escritura) | `*p = v` | requiere `curse` y exclusividad |
| `p.is_null()` | `is_null()` | seguro |
| `p.add(n)` | `add(n)` | requiere provenance y bounds |
| `p.cast[T]()` | `cast::<T>()` | requiere alineación y tamaño |

1. Un puntero raw no tiene lifetime ni garantía de validez.
2. `&raw` evita crear una referencia temporal; es la forma recomendada.
3. `*const T`/`*mut T` no son `Send` ni `Sync`.
4. La aritmética de punteros debe quedar dentro del mismo allocation.
5. Un puntero nulo no se dereferencia; se comprueba con `is_null`.
6. La provenance (de qué allocation proviene) importa; no se inventa un
   puntero a partir de un entero salvo en FFI/OS con contrato explícito.
7. Un `&mut T` y un `*mut T` al mismo dato no pueden usarse a la vez sin un
   protocolo.

### 52.3 `chimera` (uniones)

```pengu
@@repr(C)
chimera IntOrFloat
    i: Int
    f: Float

grimoire
    bind value = IntOrFloat(i: 42)
    bind as_int = curse
        -- SAFETY: se escribió el campo `i`, se lee `i`.
        value.i
    print(as_int)
```

Rust generado:

```rust
#[repr(C)]
union IntOrFloat {
    i: i32,
    f: f32,
}

fn main() {
    let value = IntOrFloat { i: 42 };
    let as_int = unsafe {
        // SAFETY: se escribió el campo `i`, se lee `i`.
        value.i
    };
    println!("{}", as_int);
}
```

1. `chimera` genera `union`; todos los campos deben ser `Copy` o
   `ManuallyDrop`.
2. Escribir un campo es seguro; leerlo requiere `curse`.
3. Leer un campo distinto del último escrito es comportamiento indefinido
   salvo que el tipo lo permita (`#[repr(C)]` y tipos compatibles).
4. Una unión no sabe qué variante está activa; se necesita una etiqueta
   externa.
5. `chimera` no reemplaza a `enchanting`; se usa para layout/FFI.
6. `MaybeUninit` es preferible para inicialización diferida.

### 52.4 `transmute`

```pengu
curse bits = (value: Float) -> U64
    -- SAFETY: `Float` y `U64` miden 8 bytes y la representación es estable.
    transmute(value)
```

Rust generado:

```rust
fn bits(value: f64) -> u64 {
    // SAFETY: `f64` y `u64` miden 8 bytes y la representación es estable.
    unsafe { std::mem::transmute(value) }
}
```

1. `transmute` exige que origen y destino tengan el mismo tamaño.
2. No comprueba validez: un `u32` convertido en `bool` puede ser inválido.
3. Para números, se prefieren `to_bits`/`from_bits`.
4. Para punteros, se prefiere `cast` y un contrato de provenance.
5. `transmute` entre tipos con drop puede filtrar recursos; se usa
   `ManuallyDrop`.
6. `transmute` no es una conversión de negocio; es una operación de bits.
7. `transmute` en genéricos puede fallar en compilación si los tamaños no
   coinciden.

### 52.5 `MaybeUninit`, `ManuallyDrop` y `UnsafeCell`

```rust
use std::mem::MaybeUninit;

fn main() {
    let mut value = MaybeUninit::<i32>::uninit();
    value.write(42);
    let value = unsafe { value.assume_init() };
    println!("{}", value);
}
```

1. `MaybeUninit[T]` representa un `T` que puede no estar inicializado.
2. `write` inicializa; `assume_init` es `curse` y exige que esté inicializado.
3. `assume_init_read` mueve el valor; `assume_init_drop` lo dropea.
4. `ManuallyDrop[T]` evita el drop automático; se usa para controlar el
   momento exacto.
5. `ManuallyDrop` no filtra por sí solo: hay que llamar a `drop` manualmente.
6. `UnsafeCell[T]` es la única forma legal de mutar a través de `&T`; la
   seguridad la aporta el envoltorio (`Cell`, `Mutex`, etc.).
7. `UnsafeCell` no es `Sync`; compartirlo sin sincronización es data race.

```rust
use std::cell::UnsafeCell;

struct Cell {
    value: UnsafeCell<i32>,
}

fn main() {
    let cell = Cell { value: UnsafeCell::new(1) };
    unsafe {
        *cell.value.get() += 1;
    }
    println!("{}", unsafe { *cell.value.get() });
}
```

### 52.6 Aliasing y soundness

1. Un `&mut T` es exclusivo mientras vive; no puede coexistir con otro acceso.
2. Un `&T` permite lecturas concurrentes; no escrituras.
3. Dos `&mut T` al mismo dato son UB aunque no se usen a la vez.
4. Un `&T` y un `*mut T` pueden coexistir solo si no se escribe mientras el
   `&T` está vivo.
5. `UnsafeCell` suspende la garantía de inmutabilidad, no la de exclusividad
   lógica.
6. Un `curse` no puede crear una referencia inválida, desalineada o nula.
7. La soundness es responsabilidad del código seguro que envuelve al `curse`;
   la API pública debe ser segura.

Checklist de soundness:

- [ ] El puntero apunta a un objeto vivo y alineado.
- [ ] El tamaño y el tipo coinciden.
- [ ] No hay aliasing mutable incompatible.
- [ ] El lifetime del préstamo cubre el uso.
- [ ] La inicialización está completa antes de leer.
- [ ] El drop se ejecuta exactamente una vez.
- [ ] El tipo no contiene valores inválidos.
- [ ] La concurrencia está sincronizada.

### 52.7 `curse` en traits

```pengu
curse pact UnsafeRead
    read = (@, p: *const Int) -> Int
```

Rust generado:

```rust
unsafe trait UnsafeRead {
    fn read(&self, p: *const i32) -> i32;
}
```

1. `curse pact` genera `unsafe trait`.
2. Un `ritual` de un trait unsafe debe ser `curse ritual`.
3. Un trait unsafe no hace unsafe a sus métodos por sí solo; cada método
   declara su propio contrato.
4. La implementación debe documentar por qué cumple el contrato.
5. Un trait unsafe no se puede implementar en código seguro.

### 52.8 Inline assembly

```rust
fn main() {
    unsafe {
        core::arch::asm!("nop");
    }
    println!("asm ok");
}
```

1. `asm!` y `global_asm!` son macros de Rust; se usan dentro de `curse`.
2. La sintaxis es específica de la arquitectura; no es portable.
3. Los registros, clobbers y opciones deben declararse.
4. `asm!` no es una optimización mágica; puede impedir optimizaciones.
5. Para código portátil, se usan intrínsecos o FFI.
6. `global_asm!` se usa a nivel de módulo; requiere `curse` y una sección
   explícita.

### 52.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5201` | operación unsafe fuera de `curse` | envolver en `curse` |
| `PGS-E5202` | `curse` sin justificación | añadir `-- SAFETY:` |
| `PGS-E5203` | `transmute` con tamaños distintos | usar una conversión válida |
| `PGS-E5204` | `chimera` con campo no `Copy` | usar `ManuallyDrop` |
| `PGS-E5205` | `assume_init` sin inicializar | escribir antes |
| `PGS-E5206` | `&mut` aliasado | separar los préstamos |
| `PGS-W5201` | `curse` sin comentario SAFETY | documentar |
| `PGS-W5202` | `curse` innecesario | usar código seguro |

### 52.10 Criterios de aceptación

- [x] `curse` cubre funciones, bloques y traits.
- [x] Punteros raw, uniones, `transmute` y `MaybeUninit` están definidos.
- [x] El checklist de soundness es explícito.
- [x] La asm está limitada a `curse`.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
