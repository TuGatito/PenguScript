<a id="sec-68-cookbook"></a>
## 68. Cookbook

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | `grimoire`, `rune`, `dream`, `foreign`, `@@` |
| Depende de | §3, §15, §28, §48, §50, §53, §55 |
| Ejemplos ejecutables | `sí` |

Recetas mínimas, completas y compilables. Cada una muestra el PenguScript y
el Rust que genera el compilador. Los bloques `rust` se compilan con
`rustc --edition 2024`.

### 68.1 Hello world

```pengu
grimoire
    print("Hola, PenguScript")
```

```rust
fn main() {
    println!("Hola, PenguScript");
}
```

### 68.2 CLI con argumentos

```pengu
summon std::env

grimoire
    bind args = env.args().skip(1).collect::<Vec[String]>()
    if args.is_empty() then
        print("uso: saludo <nombre>")
        return 1
    print("Hola, #{args[0]}")
    0
```

```rust
use std::env;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        println!("uso: saludo <nombre>");
        std::process::exit(1);
    }
    println!("Hola, {}", args[0]);
}
```

### 68.3 Librería

```pengu
-- lib.pengu
unveil rune Point
    x: Float
    y: Float

unveil length = (@) -> Float
    Math.sqrt(@.x * @.x + @.y * @.y)
```

```rust
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}
```

### 68.4 Errores con `?`

```pengu
rune ParseError
    message: String

read_number = (text: Str) -> !Int
    bind value = text.parse::[Int]()?
    ok(value)
```

```rust
#[derive(Debug)]
struct ParseError {
    message: String,
}

fn read_number(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    let value: i32 = text.parse()?;
    Ok(value)
}

fn main() {
    match read_number("42") {
        Ok(v) => println!("{v}"),
        Err(e) => println!("error: {e}"),
    }
}
```

### 68.5 Async

```pengu
dream fetch = (url: Str) -> !String
    bind response = http.get(url).awaken?
    ok(response.text().awaken?)

dream main_async = () -> !Unit
    bind body = fetch("https://example.com").awaken?
    print(body.len())
    ok(())
```

El executor no forma parte del lenguaje; el Rust generado usa `.await` y el
runtime que elija el `Tome.toml` (Tokio, async-std, embassy, etc.).

```rust
async fn fetch(url: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    let _ = url;
    Ok(String::from("hola"))
}

async fn main_async() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let body = fetch("https://example.com").await?;
    println!("{}", body.len());
    Ok(())
}

fn main() {
    let _future = main_async();
}
```

### 68.6 FFI

```pengu
foreign "C"
    curse cos(x: Float) -> Float

grimoire
    curse
        print(cos(0.0))
```

```rust
#[link(name = "m")]
unsafe extern "C" {
    fn cos(x: f64) -> f64;
}

fn main() {
    unsafe {
        println!("{}", cos(0.0));
    }
}
```

### 68.7 Embebido (`no_std`)

```pengu
@@no_std

unveil rune Register
    value: UInt

unveil read = (ptr: *const UInt) -> UInt
    curse
        *ptr
```

```rust
#![no_std]

pub struct Register {
    pub value: u32,
}

pub unsafe fn read(ptr: *const u32) -> u32 {
    *ptr
}
```

### 68.8 WASM

```toml
[tome]
name = "hello-wasm"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"

[lib]
path = "lib.pengu"

[dependencies]
wasm-bindgen = "0.2"
```

```pengu
summon wasm_bindgen::prelude::*

@@wasm_bindgen
unveil greet = (name: Str) -> String
    format("Hola, #{name}")
```

El glue JS y `wasm-bindgen` son externos; el target es
`wasm32-unknown-unknown`.

### 68.9 Macros

```pengu
incantation square
    ($x:expr) => {
        $x * $x
    }

grimoire
    print(square!(5))
```

```rust
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

fn main() {
    println!("{}", square!(5));
}
```

### 68.10 Checklist de una receta

1. El `pengu` debe ser válido según §60.
2. El `rust` debe compilar con `rustc --edition 2024`.
3. Si hay `unsafe`, debe llevar `-- SAFETY:` en el Pengu y un comentario
   `// SAFETY:` en el Rust.
4. Si hay async, el executor se declara en `Tome.toml`.
5. Si hay FFI, el ABI y el linker se declaran.
6. Si es `no_std`, no se importa `std`.
7. Si es WASM, el target y el glue se documentan.

[↑ Volver al índice](#indice)
