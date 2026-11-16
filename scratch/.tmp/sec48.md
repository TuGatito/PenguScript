<a id="sec-48-errores"></a>
## 48. Manejo de errores

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 7 |
| Rust | `Option<T>`, `Result<T, E>`, `?`, `panic!`, `Termination` |
| Palabras mágicas | `?T`, `!T`, `none`, `some`, `ok`, `err`, `panic` |
| Depende de | §4, §8, §29, §30, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec48_errors.pengu` |

PenguScript no tiene `null`, excepciones ni errores implícitos. Un valor que
puede faltar se representa con `?T` (`Option<T>`); una operación que puede fallar,
con `!T` (`Result<T, Error>`). El operador `?` propaga el fallo sin `try`/`catch`.

### 48.1 `Option` y `Result`

| PenguScript | Rust | Constructor | Éxito | Fallo |
|---|---|---|---|---|
| `?T` | `Option<T>` | `some(v)` | `some(v)` | `none` |
| `!T` | `Result<T, Error>` | `ok(v)` | `ok(v)` | `err(e)` |
| `!T` con error custom | `Result<T, E>` | `ok(v)` | `ok(v)` | `err(e)` |

1. `?T` y `!T` son azúcar; no son tipos distintos de `Option`/`Result`.
2. `some`, `ok` y `err` son funciones; `none` es un valor constante.
3. `Option` no contiene un mensaje de error; para eso se usa `Result`.
4. `Result` no se puede ignorar silenciosamente: o se consume, o se propaga con
   `?`, o se convierte explícitamente.
5. `Option`/`Result` se pueden anidar: `? !T` es `Option<Result<T, E>>`.

```pengu
find = (items: &[Int], target: Int) -> ?Usize
    for (i, item) in items.iter().enumerate()
        if *item == target
            return some(i)
    none

parse = (text: &Str) -> !Int
    bind n = text.parse[Int]()?
    ok(n)
```

Rust generado:

```rust
fn find(items: &[i32], target: i32) -> Option<usize> {
    for (i, item) in items.iter().enumerate() {
        if *item == target {
            return Some(i);
        }
    }
    None
}

fn parse(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    let n = text.parse::<i32>()?;
    Ok(n)
}
```

`Error` es el alias de `Box<dyn std::error::Error + Send + Sync>` (§4.8).

### 48.2 El operador `?`

`expr?` hace:

1. Si `expr` es `some(v)`/`ok(v)`, se evalúa a `v`.
2. Si es `none`/`err(e)`, retorna temprano con ese valor.
3. En `Result`, el error se convierte con `From` al tipo de error de la función.
4. En `Option`, no hay conversión: el fallo es `none`.

```pengu
read_config = (path: &Str) -> !String
    bind text = std.fs.read_to_string(path)?
    ok(text)

first_line = (path: &Str) -> ?String
    bind text = std.fs.read_to_string(path).ok()?
    text.lines().next().map(String.from)
```

Rust generado:

```rust
fn read_config(path: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    let text = std::fs::read_to_string(path)?;
    Ok(text)
}

fn first_line(path: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    text.lines().next().map(String::from)
}
```

Reglas:

1. `?` solo se usa en una función que devuelve `Result`/`Option` compatible
   (`PGS-E4801`).
2. `?` sobre `Result` en una función `Option` es error; y viceversa
   (`PGS-E4802`).
3. `?` sobre `Result` requiere `E: Into<Efun>`, donde `Efun` es el error de la
   función (`PGS-E4803`).
4. `?` no se usa en `grimoire` con retorno `Unit`; se declara `grimoire: !Unit`.
5. `?` no se usa en un bloque que no sea el cuerpo de una función compatible.
6. `?` no convierte `none` en `err`; son dominios distintos.
7. `?` se asocia al postfix más cercano: `foo()?.bar()` es
   `(foo()?).bar()`.
8. `?` no oculta el error: el tipo de retorno lo hace visible.

### 48.3 `panic`, `assert` y `unwrap`

```pengu
check = (n: Int) -> Int
    assert(n > 0, "n debe ser positivo")
    n

read_port = (text: &Str) -> UInt
    text.parse[UInt]().expect("puerto inválido")
```

Rust generado:

```rust
fn check(n: i32) -> i32 {
    assert!(n > 0, "n debe ser positivo");
    n
}

fn read_port(text: &str) -> u32 {
    text.parse::<u32>().expect("puerto inválido")
}
```

1. `panic("msg")` genera `panic!("msg")`; su tipo es `Never`.
2. `assert(cond, "msg")` genera `assert!(cond, "msg")`.
3. `assert_eq(a, b)` y `assert_ne(a, b)` están disponibles en tests.
4. `unwrap()`/`expect()` son para invariantes comprobadas; en código de
   biblioteca se prefiere `?`.
5. Un `panic` no es un error recuperable; no se usa para validación de entrada.
6. `panic` en `no_std` requiere `@@panic_handler` (§55).
7. `panic = "abort"` elimina el unwind; `catch_unwind` deja de capturar.

### 48.4 Errores custom

```pengu
@@derive(Debug)]
enchanting ParseError
    Empty
    Invalid(String)

ritual Display for ParseError
    fmt = (@, f: &mut fmt::Formatter) -> fmt::Result
        match @
            when ParseError.Empty then write(f, "vacío")
            when ParseError.Invalid(msg) then write(f, "inválido: #{msg}")

ritual Error for ParseError
```

Rust generado:

```rust
use std::fmt;

#[derive(Debug)]
enum ParseError {
    Empty,
    Invalid(String),
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Empty => write!(f, "vacío"),
            ParseError::Invalid(msg) => write!(f, "inválido: {}", msg),
        }
    }
}

impl std::error::Error for ParseError {}
```

1. Un error custom implementa `Debug`, `Display` y `Error`.
2. `Error` no requiere métodos; `source()` es opcional.
3. `Display` es el mensaje para el usuario; `Debug` es para diagnóstico.
4. Un `enchanting` es la forma natural de modelar variantes de error.
5. Un `rune` sirve para un error con campos comunes.
6. No se usa `String` como error en APIs públicas; se define un tipo.

### 48.5 Conversión con `From`

```pengu
@@derive(Debug)]
rune ConfigError
    message: String

ritual Display for ConfigError
    fmt = (@, f: &mut fmt::Formatter) -> fmt::Result
        write(f, "config: #{@.message}")

ritual Error for ConfigError

ritual From[ParseError] for ConfigError
    from = (e: ParseError) -> ConfigError
        ConfigError(message: "#{e}")
```

Rust generado:

```rust
use std::fmt;

#[derive(Debug)]
struct ConfigError {
    message: String,
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "config: {}", self.message)
    }
}

impl std::error::Error for ConfigError {}

#[derive(Debug)]
enum ParseError {
    Empty,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Empty => write!(f, "vacío"),
        }
    }
}

impl std::error::Error for ParseError {}

impl From<ParseError> for ConfigError {
    fn from(e: ParseError) -> ConfigError {
        ConfigError { message: format!("{}", e) }
    }
}
```

Con `From`, `?` convierte automáticamente:

```pengu
load = (text: &Str) -> !Int
    bind n = parse(text)?
    ok(n)
```

1. `?` usa `From`, no `Into` directamente.
2. La implementación de `From` debe ser coherente y no perder información.
3. Un error de bajo nivel se envuelve en uno de dominio.
4. No se implementa `From<String>` para todo; se pierde el tipo.
5. `thiserror` y `anyhow` son crates externas; se consumen, no se integran al
   lenguaje.

### 48.6 `main` fallible

```pengu
grimoire: !Unit
    bind config = read_config("Tome.toml")?
    print(config)
```

Rust generado:

```rust
fn read_config(_path: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    Ok(String::new())
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let config = read_config("Tome.toml")?;
    println!("{}", config);
    Ok(())
}
```

1. `grimoire: !Unit` genera `fn main() -> Result<(), E>`.
2. El `E` por defecto es `Box<dyn Error + Send + Sync>`.
3. `?` funciona en `main` solo con esta forma.
4. Un `main` fallible imprime el error y devuelve código de salida distinto de
   cero.
5. `Termination` permite personalizar el código de salida (§48.8).
6. Un `grimoire` normal no puede usar `?` (`PGS-E4804`).

### 48.7 `catch_unwind`

```pengu
bind result = std.panic.catch_unwind(() => panic("boom"))
match result
    when ok(_) then print("sin panic")
    when err(_) then print("panic capturado")
```

Rust generado:

```rust
fn main() {
    let result = std::panic::catch_unwind(|| panic!("boom"));
    match result {
        Ok(_) => println!("sin panic"),
        Err(_) => println!("panic capturado"),
    }
}
```

1. `catch_unwind` captura un panic de unwind, no un abort.
2. El closure debe ser `UnwindSafe`; si no, se usa `AssertUnwindSafe`.
3. No se usa para control de flujo normal.
4. Un panic puede dejar invariantes rotas; el estado compartido debe revisarse.
5. `panic = "abort"` hace que `catch_unwind` no capture.

### 48.8 `Termination` y códigos de salida

Rust permite que `main` devuelva cualquier `T: Termination`. PenguScript expone
solo dos formas:

1. `grimoire` -> `fn main()` con salida 0.
2. `grimoire: !Unit` -> `fn main() -> Result<(), Error>` con salida 1 en error.

Para un código distinto, se usa `std.process.exit(code)` explícitamente. No hay
un `main` con `ExitCode` en la superficie del lenguaje; el codegen puede
añadirlo en el futuro sin romper la sintaxis.

### 48.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4801` | `?` fuera de función compatible | devolver `Result`/`Option` o usar `match` |
| `PGS-E4802` | `?` de `Option` en función `Result` | convertir con `ok_or`/`ok_or_else` |
| `PGS-E4803` | error sin `From` al error de retorno | implementar `From` o mapear |
| `PGS-E4804` | `?` en `grimoire` no fallible | declarar `grimoire: !Unit` |
| `PGS-E4805` | `unwrap` en código de biblioteca | usar `?` o `expect` con invariante |
| `PGS-E4806` | `panic` para entrada inválida | devolver `Result` |
| `PGS-E4807` | `Error` sin `Display`/`Debug` | implementar ambos |
| `PGS-W4801` | `Box<dyn Error>` en API pública | definir un error de dominio |
| `PGS-W4802` | `catch_unwind` para flujo normal | usar `Result` |

### 48.10 Criterios de aceptación

- [x] `Option`/`Result` y sus constructores están definidos.
- [x] `?` tiene reglas de compatibilidad y conversión.
- [x] `panic`, `assert`, `unwrap` y `catch_unwind` están diferenciados.
- [x] Los errores custom implementan `Error`.
- [x] `grimoire: !Unit` está conectado con `Termination`.

[↑ Volver al índice](#indice)
