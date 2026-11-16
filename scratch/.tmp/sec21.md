<a id="sec-21-memoria"></a>
## 21. Memoria, Drop y layout

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `size_of`, `align_of`, `repr`, `Drop`, `ManuallyDrop`, `MaybeUninit` |
| Palabras mágicas | `@@repr`, `drop`, `curse` |
| Depende de | §16, §19, §20 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec21_memory.pengu` |

PenguScript no tiene GC ni un runtime de memoria propio. El layout, el orden de
drop y la validez de un valor siguen las reglas de Rust; el front-end solo
traduce y comprueba lo que puede en tiempo de compilación.

### 21.1 Stack, heap y valores

| Zona | Qué contiene | Quién libera |
|---|---|---|
| stack | locales, parámetros, valores `Sized` | el frame al salir |
| heap | `Box`, `Vec`, `String`, `Rc`, `Arc` | el dueño, al hacer drop |
| static | `sigil`, `relic`, literales `'static` | el programa |
| arena | bloques de una API | la arena |

Un valor `Sized` tiene un tamaño conocido en compilación y vive en el stack si no
se boxea. `Str`, `[T]` y `dyn Trait` son **unsized**: solo se usan detrás de una
referencia o un puntero inteligente (`&Str`, `Box[Str]`, `&dyn Trait`).

### 21.2 `size_of`, `align_of` y `repr`

```pengu
@@repr(C)
rune Pair
    a: U8
    b: U32

grimoire
    print(size_of[Pair]())
    print(align_of[Pair]())
```

Rust generado:

```rust
#[repr(C)]
struct Pair {
    a: u8,
    b: u32,
}

fn main() {
    println!("{}", std::mem::size_of::<Pair>());
    println!("{}", std::mem::align_of::<Pair>());
}
```

En una plataforma típica de 64 bits, `size_of[Pair]()` es `8` y
`align_of[Pair]()` es `4`: hay 3 bytes de padding entre `a` y `b`.

Reglas:

1. `size_of[T]()` -> `std::mem::size_of::<T>()`; `align_of[T]()` ->
   `std::mem::align_of::<T>()`.
2. `@@repr(C)` usa el layout de C; es obligatorio en structs que cruzan FFI.
3. `@@repr(Rust)` es el layout por defecto; el compilador puede reordenar campos.
   No se usa en FFI.
4. `@@repr(transparent)` exige un único campo no-ZST; el layout es el de ese
   campo.
5. `@@repr(u8)`/`u16`/`u32`/`u64`/`i8`/… fija la representación de un enum.
6. `@@repr(packed)` elimina padding; crear una referencia a un campo puede ser
   UB por desalineación (`PGS-E2102`). Solo se usa con copias y `read_unaligned`.
7. `@@repr(align(N))` fuerza una alineación mayor; `N` debe ser potencia de dos.

### 21.3 Orden de drop

El drop de un valor ocurre:

1. al final del scope, en orden **inverso** al de declaración de los locales;
2. en un struct, en orden de **declaración de campos** (no al revés);
3. en una tupla, de izquierda a derecha;
4. en un array, de izquierda a derecha;
5. después del cuerpo de `Drop::drop`, se dropean los campos.

```pengu
rune Loud
    name: Str

-- Vista previa: la implementación de traits se define en §35.
ritual Drop for Loud
    drop = (@mut) -> Unit
        print(@.name)

grimoire
    do
        bind a = Loud(name: "a")
        bind b = Loud(name: "b")
        print("fin del bloque")
    print("fin de main")
```

Rust generado:

```rust
struct Loud {
    name: String,
}

impl Drop for Loud {
    fn drop(&mut self) {
        println!("{}", self.name);
    }
}

fn main() {
    {
        let a = Loud { name: String::from("a") };
        let b = Loud { name: String::from("b") };
        println!("fin del bloque");
    }
    println!("fin de main");
}
```

Salida:

```text
fin del bloque
b
a
fin de main
```

`b` se declara después de `a`, así que se dropea primero. El bloque interno se
dropea antes de `fin de main`.

Reglas:

1. Un tipo con `Drop` no puede moverse parcialmente: mover un campo dejaría el
   `Drop` con un valor incompleto (`PGS-E2103`).
2. `Drop::drop` recibe `@mut` (`&mut self`); no recibe `@own`.
3. `Drop` se ejecuta también durante un panic (unwind); si el panic ocurre en un
   `drop`, el programa aborta.
4. `mem::forget(value)` evita el drop; es seguro, pero puede filtrar memoria
   (`PGS-W2102`). No se usa para “liberar” antes.
5. `ManuallyDrop[T]` envuelve un valor y no lo dropea; el programador debe
   llamar `ManuallyDrop.drop` o `ManuallyDrop.take` en `curse`.
6. Los `Rc`/`Arc` pueden cambiar el momento del drop: el valor vive hasta el
   último dueño.

### 21.4 `ManuallyDrop`

```pengu
bind value = ManuallyDrop.new(String.from("pengu"))
print(*value)
```

Rust generado:

```rust
use std::mem::ManuallyDrop;

fn main() {
    let value = ManuallyDrop::new(String::from("pengu"));
    println!("{}", *value);
}
```

`ManuallyDrop` no libera el `String`; el ejemplo filtra memoria a propósito. La
forma correcta de liberarlo es `ManuallyDrop.drop(value)` dentro de `curse`.

### 21.5 `MaybeUninit`

`MaybeUninit[T]` representa memoria que puede no estar inicializada. Leerla sin
inicializar es UB; escribirla y luego llamar `assume_init` es la forma de
construir un valor manualmente:

```pengu
curse make = () -> Int
    morph slot: MaybeUninit[Int] = MaybeUninit.uninit()
    slot.write(42)
    slot.assume_init()
```

Rust generado:

```rust
use std::mem::MaybeUninit;

unsafe fn make() -> i32 {
    unsafe {
        let mut slot: MaybeUninit<i32> = MaybeUninit::uninit();
        slot.write(42);
        slot.assume_init()
    }
}
```

Reglas:

1. `MaybeUninit.uninit()` no inicializa; no se puede leer todavía.
2. `slot.write(value)` escribe sin dropear el contenido anterior.
3. `slot.assume_init()` promete que el valor está inicializado; si no, UB.
4. `MaybeUninit` se usa en `curse`, FFI, buffers y arrays grandes; no en código
   normal.
5. Un `MaybeUninit[T]` no dropea `T` automáticamente; hay que hacerlo a mano.

### 21.6 Zero-sized types y nichos

Un **ZST** ocupa 0 bytes (`struct Marker;`, `()`), pero puede tener alineación 1.
Los ZST no se reservan en el heap y un `Vec[ZST]` no asigna capacidad real.

Un **niche** es un valor inválido que el compilador usa para representar `None`
sin coste extra: `Option<&T>` tiene el mismo tamaño que `&T` porque null es un
valor imposible para una referencia. `Option<Box<T>>`, `Option<NonNull<T>>` y
`Option<NonZeroU32>` también usan nichos. `Option<i32>` no puede: necesita un
discriminante.

Reglas:

1. No se depende del tamaño exacto de un tipo `repr(Rust)`; puede cambiar entre
   versiones y plataformas.
2. Para FFI, serialización o layout binario, se usa `@@repr(C)` y se comprueba
   con `size_of`/`align_of`.
3. Un `enum` sin `repr` puede reordenar variantes; no se asume su discriminante.
4. `Option<&T>` y `Option<Box<T>>` son “gratis” en tamaño, pero `Option<i32>` no.

### 21.7 Fugas de memoria

Una fuga es memoria que ya no es alcanzable pero no se libera. En Rust una fuga
es **safe** (no viola memoria), pero puede agotar el sistema:

- `mem::forget`;
- ciclos `Rc`/`Arc` sin `Weak`;
- `ManuallyDrop` sin drop;
- un `Vec` que crece sin límite;
- `Box::leak` (convierte en `&'static mut T`).

PenguScript no prohíbe fugas; el linter avisa en patrones obvios (`PGS-W2101`).
Un `Box::leak` es explícito y se usa para valores globales inmutables, no para
“evitar el borrow checker”.

### 21.8 Ejemplo completo

```pengu
@@repr(C)
rune Header
    tag: U8
    len: U32

grimoire
    bind header = Header(tag: 1, len: 42)
    print(size_of[Header]())
    print(header.tag)
    do
        bind temp = String.from("temporal")
        print(temp)
    print("fin")
```

Rust generado:

```rust
#[repr(C)]
struct Header {
    tag: u8,
    len: u32,
}

fn main() {
    let header = Header { tag: 1, len: 42 };
    println!("{}", std::mem::size_of::<Header>());
    println!("{}", header.tag);
    {
        let temp = String::from("temporal");
        println!("{}", temp);
    }
    println!("fin");
}
```

Salida: `8`, `1`, `temporal`, `fin`. `temp` se dropea al final del bloque interno.

### 21.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2101` | `repr` incompatible con el tipo | quitar `repr` o cambiar la representación |
| `PGS-E2102` | referencia a campo de `repr(packed)` | copiar con `read_unaligned` |
| `PGS-E2103` | move parcial de un tipo con `Drop` | mover el valor completo o usar `Option` |
| `PGS-E2104` | `MaybeUninit` leído sin inicializar | escribir antes de `assume_init` |
| `PGS-E2105` | `size_of`/`align_of` sobre unsized | usar `&T`/`Box[T]` |
| `PGS-E2106` | `repr(C)` con campos no FFI-safe | usar tipos FFI-safe |
| `PGS-W2101` | fuga probable | revisar ciclos/`forget` |
| `PGS-W2102` | `mem::forget` explícito | justificar o usar `ManuallyDrop` |
| `PGS-W2103` | `repr(Rust)` en FFI | usar `repr(C)` |

### 21.10 Criterios de aceptación

- [x] Stack, heap, static y arena están diferenciados.
- [x] `size_of`, `align_of` y `repr` tienen reglas y ejemplo.
- [x] El orden de drop está especificado para locales, structs, tuplas y arrays.
- [x] `Drop`, `ManuallyDrop` y `MaybeUninit` están cubiertos.
- [x] ZST, nichos y fugas están explicados.
- [x] Los ejemplos Rust compilan.
- [x] Los diagnósticos enlazan con §16, §19 y §20.

[↑ Volver al índice](#indice)

