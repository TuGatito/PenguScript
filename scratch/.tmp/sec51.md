<a id="sec-51-concurrencia"></a>
## 51. Concurrencia

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 7 |
| Rust | `thread`, `Arc`, `Mutex`, `RwLock`, atomics, channels |
| Palabras mágicas | `spawn`, `move`, `Send`, `Sync` |
| Depende de | §16, §17, §20, §35, §49 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec51_concurrency.pengu` |

La concurrencia segura se apoya en dos traits: `Send` indica que un valor puede
moverse entre hilos; `Sync` indica que puede compartirse por referencia. El
compilador rechaza los usos que rompen esas garantías.

### 51.1 Hilos

```pengu
grimoire
    bind handle = std.thread.spawn(move () =>
        print("hola desde otro hilo")
    )
    handle.join().unwrap()
```

Rust generado:

```rust
fn main() {
    let handle = std::thread::spawn(move || {
        println!("hola desde otro hilo");
    });
    handle.join().unwrap();
}
```

1. `std.thread.spawn` recibe una closure `FnOnce + Send + 'static`.
2. El closure debe ser `move` si captura valores que no viven en `'static`.
3. `JoinHandle.join()` devuelve `Result<T, Box<dyn Any + Send>>`.
4. Un panic en el hilo se propaga como `Err` en `join`; no se ignora.
5. El hilo principal no espera automáticamente; sin `join`, el programa puede
   terminar antes.
6. `spawn` no comparte el stack; los datos se mueven o se comparten con `Arc`.

### 51.2 Hilos con scope

```pengu
grimoire
    morph total = 0
    std.thread.scope((scope) =>
        scope.spawn(() =>
            total += 1
        )
    )
    print(total)
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    std::thread::scope(|scope| {
        scope.spawn(|| {
            total += 1;
        });
    });
    println!("{}", total);
}
```

1. `thread::scope` garantiza que todos los hilos terminen antes de salir del
   bloque; permite prestar datos locales.
2. El closure de `scope` recibe un `Scope`; `scope.spawn` acepta préstamos no
   `'static`.
3. Al salir del scope, se hace `join` implícito; un panic se propaga.
4. No se puede devolver una referencia a un dato del scope.
5. `scope` no sustituye a `Arc` cuando los hilos deben sobrevivir al bloque.
6. Los préstamos mutables deben ser disjuntos; el borrow checker lo comprueba.

### 51.3 `Send` y `Sync`

| Tipo | `Send` | `Sync` | Nota |
|---|---|---|---|
| `i32`, `bool`, `f64` | sí | sí | `Copy` |
| `String`, `Vec[T]` | sí | sí | si `T` lo es |
| `Rc[T]` | no | no | conteo no atómico |
| `Arc[T]` | sí | sí | si `T: Send + Sync` |
| `RefCell[T]` | sí | no | mutabilidad interior no thread-safe |
| `Mutex[T]` | sí | sí | si `T: Send` |
| `RwLock[T]` | sí | sí | si `T: Send + Sync` |
| `*const T`/`*mut T` | no | no | raw pointers |
| `Cell[T]` | sí | no | no compartible por referencia |

1. `Send` se comprueba estructuralmente; un `rune` es `Send` si todos sus campos
   lo son.
2. `Sync` permite `&T` entre hilos; `T: Sync` no implica `T: Send`.
3. `Rc`/`RefCell` son de un solo hilo; para compartir se usa `Arc`/`Mutex`.
4. Un tipo con `UnsafeCell` no es `Sync` por defecto.
5. `PhantomData` puede cambiar auto-traits; se documenta.
6. No se implementan `Send`/`Sync` a mano salvo en `curse` con justificación.

### 51.4 `Arc<Mutex<T>>`

```pengu
grimoire
    bind counter = Arc.new(Mutex.new(0))
    morph handles = Vec.new()

    for _ in 0..4
        bind c = Arc.clone(&counter)
        handles.push(std.thread.spawn(move () =>
            morph guard = c.lock().unwrap()
            *guard += 1
        ))

    for handle in handles
        handle.join().unwrap()

    print(*counter.lock().unwrap())
```

Rust generado:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = Vec::new();

    for _ in 0..4 {
        let c = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            let mut guard = c.lock().unwrap();
            *guard += 1;
        }));
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("{}", *counter.lock().unwrap());
}
```

1. `Arc` comparte el dueño; `Mutex` serializa el acceso.
2. `Arc.clone(&counter)` incrementa el conteo; no copia el valor.
3. `lock()` devuelve `LockResult<MutexGuard<T>>`; `unwrap` propaga un lock
   envenenado.
4. El `MutexGuard` se libera al salir del scope.
5. No se mantiene un guard mientras se espera otro lock; riesgo de deadlock.
6. `RwLock` permite múltiples lectores o un escritor.

### 51.5 `RwLock`

```rust
use std::sync::RwLock;

fn main() {
    let lock = RwLock::new(1);

    {
        let read = lock.read().unwrap();
        println!("{}", *read);
    }

    {
        let mut write = lock.write().unwrap();
        *write += 1;
    }

    println!("{}", *lock.read().unwrap());
}
```

1. `read` permite varios lectores; `write` es exclusivo.
2. Un lector no puede coexistir con un escritor.
3. `RwLock` puede ser más lento que `Mutex` para secciones críticas pequeñas.
4. El lock se envenena si un hilo panica mientras lo tiene.
5. `try_read`/`try_write` no bloquean; se usan para evitar deadlocks.

### 51.6 Canales

```pengu
grimoire
    bind (tx, rx) = std.sync.mpsc.channel()

    std.thread.spawn(move () =>
        tx.send(42).unwrap()
    )

    print(rx.recv().unwrap())
```

Rust generado:

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        tx.send(42).unwrap();
    });

    println!("{}", rx.recv().unwrap());
}
```

1. `mpsc` es multi-productor, single-consumidor.
2. `send` falla si el receptor se cerró; `recv` falla si todos los emisores se
   cerraron.
3. El canal es una forma de transferir ownership sin locks.
4. `sync_channel` tiene capacidad limitada y aplica backpressure.
5. Para múltiples consumidores se usa `crossbeam-channel` o un `Mutex` sobre la
   cola.
6. Un canal no garantiza orden entre productores distintos; sí conserva el orden
   de cada productor.

### 51.7 Atómicos y `Ordering`

```pengu
grimoire
    bind count = Arc.new(AtomicUsize.new(0))
    morph handles = Vec.new()

    for _ in 0..4
        bind c = Arc.clone(&count)
        handles.push(std.thread.spawn(move () =>
            c.fetch_add(1, Ordering.SeqCst)
        ))

    for handle in handles
        handle.join().unwrap()

    print(count.load(Ordering::SeqCst))
```

Rust generado:

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

fn main() {
    let count = Arc::new(AtomicUsize::new(0));
    let mut handles = Vec::new();

    for _ in 0..4 {
        let c = Arc::clone(&count);
        handles.push(thread::spawn(move || {
            c.fetch_add(1, Ordering::SeqCst);
        }));
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("{}", count.load(Ordering::SeqCst));
}
```

| `Ordering` | Uso |
|---|---|
| `Relaxed` | contador sin sincronización adicional |
| `Acquire`/`Release` | publicar/consumir datos |
| `AcqRel` | lectura-escritura atómica |
| `SeqCst` | orden total, el más fácil de razonar |

1. `SeqCst` es el default seguro; los demás se usan con un argumento de
   rendimiento.
2. Un atómico no protege un `rune` completo; para eso se usa `Mutex`.
3. `fetch_add` devuelve el valor anterior.
4. Un `Ordering` más débil puede romper la relación happens-before.
5. Los atómicos no evitan ABA; para eso se usa una versión o un lock.

### 51.8 `OnceLock`, `LazyLock` y `thread_local`

```rust
use std::sync::{LazyLock, OnceLock};

static CONFIG: OnceLock<String> = OnceLock::new();
static DATA: LazyLock<Vec<i32>> = LazyLock::new(|| vec![1, 2, 3]);

fn main() {
    CONFIG.set(String::from("pengu")).unwrap();
    println!("{}", CONFIG.get().unwrap());
    println!("{:?}", *DATA);
}
```

1. `OnceLock` se inicializa una vez; `set` devuelve error si ya estaba.
2. `LazyLock` inicializa en el primer acceso; es thread-safe.
3. `thread_local` crea una copia por hilo; no se comparte.
4. `static mut` no se usa; §6 lo prohíbe.
5. `LazyLock` requiere Rust 1.80+; el MSRV es 1.85.

```rust
use std::cell::RefCell;

thread_local! {
    static COUNTER: RefCell<u32> = RefCell::new(0);
}

fn main() {
    COUNTER.with(|c| *c.borrow_mut() += 1);
    COUNTER.with(|c| println!("{}", c.borrow()));
}
```

### 51.9 Rayon y paralelismo de datos

Rayon es una crate externa para paralelismo de datos. No forma parte del
lenguaje:

```toml
[dependencies]
rayon = "1.10"
```

1. `par_iter` paraleliza un iterador; el resultado conserva el orden.
2. El closure debe ser `Send + Sync`.
3. No se usa Rayon para blocking I/O; para eso se usa async o un pool.
4. El coste de sincronización puede superar el beneficio en cargas pequeñas.
5. Un `Mutex` dentro de `par_iter` serializa y anula el paralelismo.

### 51.10 Deadlocks, data races y `UnsafeCell`

1. Un **data race** es un acceso concurrente no sincronizado con al menos una
   escritura; Rust lo impide en código seguro.
2. Un **deadlock** no es un data race: dos hilos esperan locks en orden circular.
3. Prevención: un orden global de locks, `try_lock`, timeouts y secciones
   críticas cortas.
4. `UnsafeCell` es la base de la mutabilidad interior; usarlo mal rompe
   `Sync`.
5. `UnsafeCell` no es `Sync`; envolverlo en `Mutex` lo hace seguro.
6. Un `MutexGuard` no se envía a otro hilo sin comprobar el tipo.
7. Un panic con un lock tomado lo envenena; se maneja con `unwrap_or_else`.

### 51.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5101` | `spawn` con closure no `Send` | usar `move`/`Arc` |
| `PGS-E5102` | `spawn` con préstamo no `'static` | usar `scope` o mover |
| `PGS-E5103` | `Rc`/`RefCell` compartido entre hilos | usar `Arc`/`Mutex` |
| `PGS-E5104` | `join` ignorado | manejar `Result` |
| `PGS-E5105` | lock mantenido entre `await` | reducir el scope |
| `PGS-E5106` | `Ordering` incompatible con la operación | revisar el protocolo |
| `PGS-W5101` | `Mutex` en sección crítica larga | reducir |
| `PGS-W5102` | `thread_local` con estado grande | revisar |

### 51.12 Criterios de aceptación

- [x] Hilos, `spawn`, `join` y scoped threads están definidos.
- [x] `Send`/`Sync` tienen tabla y ejemplo de error.
- [x] `Arc<Mutex<T>>`, `RwLock` y canales tienen ejemplo.
- [x] Atómicos y `Ordering` están cubiertos.
- [x] Deadlocks y data races se distinguen.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
