<a id="sec-50-async"></a>
## 50. Async/await

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 7 |
| Rust | `async fn`, `.await`, `Future`, `Pin` |
| Palabras mágicas | `dream`, `awaken` |
| Depende de | §15, §35, §36, §48, §49 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec50_async.pengu` |

Una función asíncrona no bloquea el hilo mientras espera. Devuelve un **future**:
un valor que representa un cálculo que aún no terminó. El future se ejecuta
cuando un executor lo sondea; `awaken` espera su resultado dentro de otro
contexto asíncrono.

### 50.1 `dream` y `awaken`

```pengu
dream fetch = (url: &Str) -> !String
    bind response = http.get(url)?
    ok(response.text)

dream load = (url: &Str) -> !Usize
    bind text = awaken fetch(url)?
    ok(text.len())
```

Rust generado:

```rust
use std::error::Error;

async fn fetch(url: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    let response = http_get(url)?;
    Ok(response)
}

async fn load(url: &str) -> Result<usize, Box<dyn Error + Send + Sync>> {
    let text = fetch(url).await?;
    Ok(text.len())
}

fn http_get(_url: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    Ok(String::from("pengu"))
}

fn main() {
    let future = load("https://example.com");
    println!("future creado: {}", std::mem::size_of_val(&future) > 0);
}
```

Reglas:

1. `dream` es un modificador de función; el tipo de retorno es el **output** del
   future, no `Future<T>`.
2. Una llamada a una función `dream` devuelve un future; no se ejecuta hasta
   que se espera o se lanza en un executor.
3. `awaken expr` genera `expr.await`; solo es válido dentro de `dream`, de un
   bloque `dream do` o de una closure `dream`.
4. `awaken` es un operador prefijo; se aplica a la expresión que le sigue.
5. `?` después de `awaken` se aplica al resultado: `awaken f()?` es
   `(awaken f())?`.
6. Una función `dream` puede usar `?` si devuelve `Result`/`Option`.
7. Una función normal no puede usar `awaken` (`PGS-E5001`).

### 50.2 Bloques y closures async

```pengu
bind future = dream do
    bind value = awaken ready(21)
    value * 2

bind make = dream (x: Int) => x + 1
```

Rust generado:

```rust
fn main() {
    let future = async {
        let value = ready(21).await;
        value * 2
    };

    let make = |x: i32| async move { x + 1 };

    drop(future);
    drop(make);
}

async fn ready(value: i32) -> i32 {
    value
}
```

1. `dream do` crea un bloque asíncrono; el bloque puede capturar el entorno.
2. `dream (params) => expr` crea una closure asíncrona; captura como una
   closure normal.
3. `move` antes de la closure fuerza captura por valor:
   `move dream (x: Int) => ...` no es la forma canónica; se escribe
   `dream move (x: Int) => ...`? La forma soportada es
   `dream (x: Int) => ...` y `move` se aplica al bloque interno si hace falta.
4. Una closure async devuelve un future por llamada; no se reutiliza el future.
5. Un bloque async no se ejecuta al crearse; se ejecuta al esperarlo.
6. El tipo del future es anónimo; se usa `impl Future[Output = T]` para
   devolverlo.

### 50.3 `Future`, `Pin` y `Unpin`

| Concepto | Significado | Rust |
|---|---|---|
| `Future` | cálculo que produce `Output` | `Future<Output = T>` |
| `poll` | intenta avanzar el future | `Future::poll` |
| `Pin` | garantiza que el future no se mueve | `Pin<&mut F>` |
| `Unpin` | el future puede moverse | `Unpin` |
| executor | sondea y despierta futures | tokio, async-std, smol |

1. Un future se compone de estados; `poll` devuelve `Pending` o `Ready`.
2. `Pin` es necesario porque un future puede guardar referencias a sí mismo.
3. La mayoría de los futures de `async fn` son `!Unpin`; se usa `Box.pin`.
4. No se implementa `Future` a mano salvo para adaptadores avanzados.
5. `awaken` no bloquea el hilo; el executor decide cuándo reanudar.
6. Un future que no se espera ni se lanza no hace nada; el compilador avisa si
   es `must_use`.

### 50.4 Executors y runtime

PenguScript no incluye un runtime. El tome elige uno:

```toml
[dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

1. `tokio`, `async-std` y `smol` son executors externos.
2. El lenguaje no fija un runtime; el codegen no lo importa por defecto.
3. `dream grimoire` declara una entrada asíncrona; necesita un atributo de
   runtime (`@@tokio::main`) o un `main` que llame a `block_on`.
4. `@@tokio::main` sobre `dream grimoire` genera `#[tokio::main] async fn main()`.
5. Sin runtime, un future se puede construir pero no ejecutar.
6. Un runtime de un solo hilo no requiere `Send`; uno multi-hilo sí.

```pengu
@@tokio::main
dream grimoire
    bind text = awaken fetch("https://example.com")?
    print(text)
```

Rust conceptual:

```text
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let text = fetch("https://example.com").await?;
    println!("{}", text);
    Ok(())
}
```

El bloque anterior no se compila sin la crate `tokio`; es una muestra de codegen,
no un ejemplo aislado.

### 50.5 `Send` y `'static`

1. `spawn` requiere `F: Future + Send + 'static` y `F::Output: Send + 'static`.
2. Un future que presta datos locales no es `'static`; no se puede lanzar.
3. `Rc`/`RefCell` no son `Send`; `Arc`/`Mutex` sí.
4. Un `awaken` conserva el future en el estado; los préstamos deben vivir lo
   suficiente.
5. `async move` mueve las capturas al future; evita préstamos que no viven.
6. `Send` no se deriva; se comprueba estructuralmente.

```rust
fn require_send<T: Send>(_: T) {}

fn main() {
    let value = 1;
    let future = async move { value + 1 };
    require_send(future);
}
```

### 50.6 Cancelación y `select!`

1. Un future se cancela al dropearlo; no hay un `cancel()` universal.
2. `select!` espera el primero de varios futures; los demás se cancelan.
3. `select!` es una macro de un runtime/crate (`tokio::select!`,
   `futures::select!`), no una construcción del lenguaje.
4. La cancelación en un `awaken` puede dejar un recurso a medias; se usan
   guardas/RAII.
5. Un timeout se implementa con `timeout` del runtime o con `select!`.
6. No se cancela un future ya completado.

```rust
fn main() {
    let first = async { 1 };
    let second = async { 2 };
    drop(first);
    drop(second);
    println!("futures cancelados al dropear");
}
```

### 50.7 Streams

1. Un `Stream` produce una secuencia asíncrona; es el análogo async de
   `Iterator`.
2. El trait `Stream` vive en `futures-core`; no en `std`.
3. Se consume con `while let some(item) = stream.next().await`.
4. Los adaptadores (`map`, `filter`, `take`) son de `futures-util`.
5. Un stream no es un iterador; no se usa `for` directamente.
6. Backpressure: el consumidor controla el ritmo con `next().await`.

```rust
fn main() {
    let values = vec![1, 2, 3];
    let mut iter = values.into_iter();
    while let Some(value) = iter.next() {
        println!("{}", value);
    }
}
```

El bloque anterior es síncrono; un `Stream` real requiere `futures-core` y un
executor.

### 50.8 `async fn` en traits

```pengu
pact Fetch
    dream fetch = (@, url: &Str) -> String

ritual Client for Fetch
    dream fetch = (@, url: &Str) -> String
        "ok"
```

Rust generado (Rust 2024, `async fn` en traits):

```rust
trait Fetch {
    async fn fetch(&self, url: &str) -> String;
}

struct Client;

impl Fetch for Client {
    async fn fetch(&self, _url: &str) -> String {
        String::from("ok")
    }
}

fn main() {
    let _client = Client;
}
```

1. `async fn` en traits es estable en Rust 2024 para métodos no genéricos.
2. El future de retorno no se puede nombrar; se usa `impl Future`.
3. Un trait con `async fn` no es object-safe por defecto.
4. Para `dyn`, se usa un método que devuelve `Pin<Box<dyn Future + Send>>` o un
   trait auxiliar.
5. Los bounds `Send` no se añaden automáticamente; se declaran si el executor
   los necesita.

### 50.9 `no_std` y async

1. `core::future::Future` existe en `no_std`.
2. Un executor `no_std` requiere `alloc` para tareas y `Waker`.
3. `async` sin executor solo construye futures; no progresa.
4. `tokio` no es `no_std`; para embebidos se usan `embassy` o `smol`.
5. `Pin` y `Waker` están en `core`.
6. La sección §55 detalla `no_std`.

### 50.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5001` | `awaken` fuera de contexto async | marcar con `dream` |
| `PGS-E5002` | `dream` sin runtime en `grimoire` | añadir `@@tokio::main` o `block_on` |
| `PGS-E5003` | future no `Send` en `spawn` | usar `async move`/`Arc` |
| `PGS-E5004` | `awaken` en closure normal | usar `dream (..) =>` |
| `PGS-E5005` | `async fn` en trait no object-safe | usar `Pin<Box<dyn Future>>` |
| `PGS-E5006` | future no consumido | `awaken`, `spawn` o `drop` |
| `PGS-W5001` | `select!` sin cancelación segura | revisar recursos |
| `PGS-W5002` | runtime no especificado | declarar dependencia |

### 50.11 Criterios de aceptación

- [x] `dream`/`awaken` tienen sintaxis y semántica.
- [x] Futures, `Pin` y `Unpin` están explicados.
- [x] El runtime es explícito y sustituible.
- [x] `Send`/`'static` y cancelación están cubiertos.
- [x] Los ejemplos Rust compilan sin runtime externo.

[↑ Volver al índice](#indice)
