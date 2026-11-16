<a id="sec-20-smart-pointers"></a>
## 20. Smart pointers e interior mutability

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `Box`, `Rc`, `Arc`, `Cell`, `RefCell`, `Mutex`, `RwLock`, `Cow`, `Weak` |
| Palabras mágicas | `bind`, `morph`, `@mut`, `@@shared` |
| Depende de | §16, §17, §19 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec20_smart_pointers.pengu` |

Un **smart pointer** es un tipo que posee o comparte un valor y además ofrece
operaciones adicionales (contar referencias, comprobar préstamos en runtime,
sincronizar hilos). PenguScript no inventa una jerarquía nueva: expone los
smart pointers de Rust con nombres y reglas propias.

### 20.1 Guía de selección

| Necesidad | Tipo | Coste | `Send`/`Sync` | Se usa con |
|---|---|---|---|---|
| valor en el heap, un dueño | `Box[T]` | asignación | según `T` | recursión, `dyn Trait`, tamaños grandes |
| varios dueños, un hilo | `Rc[T]` | conteo no atómico | no | grafos, listas compartidas |
| varios dueños, varios hilos | `Arc[T]` | conteo atómico | sí, si `T` lo es | concurrencia |
| mutar a través de `&T`, un hilo | `Cell[T]` / `RefCell[T]` | préstamo runtime | no | interior mutability |
| mutar a través de `&T`, varios hilos | `Mutex[T]` / `RwLock[T]` | lock | sí, si `T` lo es | estado compartido |
| evitar copias de strings/slices | `Cow[Str]` | enum prestado/poseído | según `T` | APIs que a veces poseen |
| referencia débil | `Weak[T]` | conteo no propietario | según `T` | romper ciclos `Rc`/`Arc` |
| valor fijo en memoria | `Pin[P]` | sin coste | según `P` | `async`, self-references |

Regla: si no necesitas compartir, usa `Box[T]` o el valor directo. `Rc`/`Arc`
no son “el tipo por defecto para todo”; añaden conteo y pueden crear ciclos.

### 20.2 `Box[T]`

`Box[T]` guarda `T` en el heap y es el único dueño:

```pengu
rune Node
    value: Int
    next: ?Box[Node]

grimoire
    bind leaf = Node(value: 1, next: none)
    bind root = Box.new(Node(value: 2, next: some(Box.new(leaf))))
    print(root.value)
```

Rust generado:

```rust
struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

fn main() {
    let leaf = Node { value: 1, next: None };
    let root = Box::new(Node {
        value: 2,
        next: Some(Box::new(leaf)),
    });
    println!("{}", root.value);
}
```

Reglas:

1. `Box.new(value)` -> `Box::new(value)`.
2. `Box[T]` implementa `Deref<Target = T>`; `box.field` y `*box` acceden al valor.
3. Mover el `Box` mueve el valor; clonar el `Box` requiere `T: Clone` y produce
   una copia profunda (`Box.clone(&b)`).
4. `Box[T]` permite tipos recursivos porque el tamaño del `Box` es un puntero.
5. `Box[Str]` es el tipo de un string poseído en el heap; `String` ya lo es, así
   que `Box[String]` solo se usa si necesitas indirección adicional.

### 20.3 `Rc[T]` y `Arc[T]`

`Rc[T]` comparte ownership dentro de un hilo; `Arc[T]` lo comparte entre hilos:

```pengu
grimoire
    bind a = Rc.new(String.from("pengu"))
    bind b = Rc.clone(&a)
    print(a)
    print(b)
    print(Rc.strong_count(&a))
```

Rust generado:

```rust
use std::rc::Rc;

fn main() {
    let a = Rc::new(String::from("pengu"));
    let b = Rc::clone(&a);
    println!("{}", a);
    println!("{}", b);
    println!("{}", Rc::strong_count(&a));
}
```

Reglas:

1. `Rc.new(value)`/`Arc.new(value)` crean el puntero con conteo 1.
2. `Rc.clone(&a)` incrementa el conteo; no copia `T`. Se escribe explícito para
   que el lector vea que no es un `Clone` profundo.
3. `Rc.strong_count(&a)`/`Arc.strong_count(&a)` devuelven el número de dueños.
4. El valor se libera cuando el último `Rc`/`Arc` se destruye.
5. `Rc[T]` no es `Send`; `Arc[T]` es `Send + Sync` solo si `T: Send + Sync`.
6. `Weak[T]` se crea con `Rc.downgrade(&a)`/`Arc.downgrade(&a)`; `weak.upgrade()`
   devuelve `?Rc[T]`/`?Arc[T]`. Un ciclo de `Rc`/`Arc` sin `Weak` nunca se libera.

```pengu
bind a = Arc.new(42)
bind weak = Arc.downgrade(&a)
bind restored = weak.upgrade()
```

Rust generado:

```rust
use std::sync::Arc;

fn main() {
    let a = Arc::new(42);
    let weak = Arc::downgrade(&a);
    let restored = weak.upgrade();
    println!("{:?}", restored);
}
```

`restored` es `Option<Arc<i32>>`; `print("{:?}")` es válido para `Option`.

### 20.4 `Cell[T]` y `RefCell[T]`

`Cell[T]` permite reemplazar el valor con `&self`; `RefCell[T]` permite
préstamos mutables comprobados en runtime:

```pengu
grimoire
    bind cell = RefCell.new(1)
    *cell.borrow_mut() += 1
    print(*cell.borrow())
```

Rust generado:

```rust
use std::cell::RefCell;

fn main() {
    let cell = RefCell::new(1);
    *cell.borrow_mut() += 1;
    println!("{}", *cell.borrow());
}
```

Reglas:

1. `RefCell.new(value)` -> `RefCell::new(value)`; `Cell.new(value)` ->
   `Cell::new(value)`.
2. `cell.borrow()` devuelve `Ref[T]`; `cell.borrow_mut()` devuelve `RefMut[T]`.
3. Dos `borrow_mut()` simultáneos, o `borrow()` + `borrow_mut()` solapados,
   hacen **panic** en runtime (`PGS-R2001`); no es un error de compilación.
4. `Cell[T]` solo funciona con `T: Copy` para leer (`cell.get()`); para tipos no
   `Copy` se usa `RefCell[T]` o `Cell.replace`.
5. `Cell`/`RefCell` no son `Sync`; no se comparten entre hilos. Para eso se usa
   `Mutex`/`RwLock`.
6. `RefCell` no evita ciclos ni fugas; solo mueve la comprobación de aliasing al
   runtime.

### 20.5 `Mutex[T]` y `RwLock[T]`

```pengu
summon std::sync::Arc
summon std::sync::Mutex
summon std::thread

grimoire
    bind counter = Arc.new(Mutex.new(0))
    bind c = Arc.clone(&counter)
    bind handle = thread.spawn(move () =>
        morph guard = c.lock().unwrap()
        *guard += 1
    )
    handle.join().unwrap()
    print(*counter.lock().unwrap())
```

Rust generado:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let c = Arc::clone(&counter);
    let handle = thread::spawn(move || {
        let mut guard = c.lock().unwrap();
        *guard += 1;
    });
    handle.join().unwrap();
    println!("{}", *counter.lock().unwrap());
}
```

Reglas:

1. `Mutex.new(value)` -> `Mutex::new(value)`; `lock()` devuelve
   `LockResult<MutexGuard[T>>`.
2. `lock().unwrap()` es el patrón por defecto; si el lock está envenenado
   (panic mientras se tenía), `unwrap()` propaga el panic. Una API puede usar
   `match` para recuperar el guard (`PGS-W2001`).
3. El `MutexGuard` libera el lock al salir de scope; no se puede mover fuera.
4. `RwLock` permite muchos lectores o un escritor; `read()`/`write()` siguen el
   mismo patrón.
5. Para compartir entre hilos: `Arc[Mutex[T]]` o `Arc[RwLock[T]]`. `Rc`/`RefCell`
   no cruzan hilos.
6. Un lock retenido mientras se hace I/O o se llama código desconocido puede
   bloquear el programa; mantener la sección crítica corta.

### 20.6 `Cow[Str]`

`Cow` (“clone on write”) guarda un préstamo o un valor poseído:

```pengu
bind borrowed: Cow[Str] = Cow.borrowed("pengu")
bind owned: Cow[Str] = Cow.owned(String.from("pengu"))
print(borrowed)
print(owned)
```

Rust generado:

```rust
use std::borrow::Cow;

fn main() {
    let borrowed: Cow<str> = Cow::Borrowed("pengu");
    let owned: Cow<str> = Cow::Owned(String::from("pengu"));
    println!("{}", borrowed);
    println!("{}", owned);
}
```

Reglas:

1. `Cow.borrowed(&str)` no copia; `Cow.owned(String)` posee.
2. `cow.to_mut()` clona solo si está prestado; devuelve `&mut String`.
3. `Cow[Str]` es útil en APIs que aceptan `&Str` y a veces necesitan poseer.
4. `Cow` no es un smart pointer de ownership compartido; no cuenta referencias.

### 20.7 `Pin[P]`

`Pin[P]` garantiza que el valor apuntado no se mueva. Se usa en `async` y en
estructuras auto-referenciales:

```pengu
bind pinned: Pin[Box[Int]] = Pin.new(Box.new(42))
```

Rust generado:

```rust
use std::pin::Pin;

fn main() {
    let pinned: Pin<Box<i32>> = Pin::new(Box::new(42));
    println!("{}", *pinned);
}
```

Reglas:

1. `Pin.new(pointer)` fija el valor; `Pin` no añade heap por sí mismo.
2. Un `Pin[&mut T]` no permite mover `T`; para extraerlo se necesita `T: Unpin`
   o `curse`.
3. `Pin` no es magia: si el tipo no es `Unpin`, el compilador impide moverlo.
4. §50 (async) y §51 (concurrencia) usan `Pin`; no se necesita en código normal.

### 20.8 Orden de drop con smart pointers

| Valor | Qué se libera al salir de scope |
|---|---|
| `Box[T]` | `T` y luego la allocation |
| `Rc[T]` | decrementa; si llega a 0, `T` y el bloque |
| `Arc[T]` | igual que `Rc`, con operación atómica |
| `RefCell[T]` | `T`; los `Ref`/`RefMut` vivos impiden el drop |
| `Mutex[T]` | `T` después de liberar el lock |
| `Cow[Str]` | nada si es prestado; el `String` si es poseído |

Un `Rc`/`Arc` puede mantener vivo un valor más allá del scope donde se creó; eso
es intencional, pero un ciclo sin `Weak` es una fuga de memoria lógica.

### 20.9 Ejemplo completo

```pengu
rune Node
    value: Int
    next: ?Box[Node]

grimoire
    bind list = Box.new(Node(
        value: 1,
        next: some(Box.new(Node(value: 2, next: none)))
    ))
    morph current = &list
    while current.next.is_some()
        current = current.next.as_ref().unwrap()
    print(current.value)
```

Rust generado:

```rust
struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

fn main() {
    let list = Box::new(Node {
        value: 1,
        next: Some(Box::new(Node { value: 2, next: None })),
    });
    let mut current = &list;
    while current.next.is_some() {
        current = current.next.as_ref().unwrap();
    }
    println!("{}", current.value);
}
```

Este ejemplo recorre una lista enlazada sin copiar los nodos. `current` es un
`&Box<Node>`; `current.next.as_ref()` produce `Option<&Box<Node>>`.

### 20.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2001` | `Rc`/`RefCell` usado donde se exige `Send`/`Sync` | usar `Arc`/`Mutex` |
| `PGS-E2002` | `Box.clone` sin `T: Clone` | implementar `Clone` o mover |
| `PGS-E2003` | `RefCell` con préstamo mutable solapado | acortar el scope del `Ref`/`RefMut` |
| `PGS-E2004` | `Mutex` bloqueado dos veces en el mismo hilo | soltar el primer guard |
| `PGS-E2005` | `Pin` de un tipo que no se puede fijar | usar `Box::pin` o `Unpin` |
| `PGS-E2006` | `Cow` mutado sin `to_mut` | llamar `to_mut()` |
| `PGS-W2001` | `Mutex` envenenado recuperado con `unwrap` | usar `match`/`PoisonError` |
| `PGS-W2002` | ciclo `Rc`/`Arc` sin `Weak` | añadir `Weak` |

### 20.11 Criterios de aceptación

- [x] La guía de selección cubre `Box`, `Rc`, `Arc`, `Cell`, `RefCell`,
      `Mutex`, `RwLock`, `Cow` y `Pin`.
- [x] `Rc`/`Arc` distinguen conteo no atómico y atómico.
- [x] `RefCell` documenta el panic por préstamo solapado.
- [x] `Mutex`/`RwLock` enlazan con concurrencia (§51).
- [x] `Cow` y `Pin` tienen ejemplo y reglas.
- [x] El orden de drop con smart pointers está especificado.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

