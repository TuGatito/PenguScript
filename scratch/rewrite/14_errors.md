---

<a id="sec-15"></a>
## 15. Errores, `Option` y `Result`

### 15.1 Ausencia

`Option[T]` representa un valor que puede faltar:

```pengu
bind maybe: Option[Int] = some(3)
bind nothing: Option[Int] = none
```

Formas cortas:

```pengu
bind maybe: ?Int = some(3)
bind nothing: ?Int = none
```

`?T` es exactamente `Option[T]`. No hay `!T`.

### 15.2 Resultado

`Result[T, E]` representa un éxito o un error:

```pengu
bind ok_value: Result[Int, String] = ok(3)
bind error_value: Result[Int, String] = err("no")
```

`E` es un tipo concreto: un `enchanting`, un `rune` o un primitivo. No hay
errores boxed ni `Box[dyn Error]`.

### 15.3 `?`

```pengu
read_number = (text: &Str) -> Result[Int, ParseError]
    bind n = text.parse[Int]()?
    ok(n + 1)
```

`?`:

- en `Option`, devuelve `none` si el valor es `none`;
- en `Result`, devuelve `err(e)` si el valor es `err(e)`;
- exige que el error del caller sea el mismo tipo, o que se convierta con
  `map_err` antes.

No hay conversión automática de errores.

### 15.4 Métodos de `Option`

| Método | Firma |
|---|---|
| `is_some` | `(@) -> Bool` |
| `is_none` | `(@) -> Bool` |
| `unwrap_or` | `(@own, T) -> T` |
| `map` | `(@own, (T) -> U) -> Option[U]` |
| `and_then` | `(@own, (T) -> Option[U]) -> Option[U]` |
| `ok_or` | `(@own, E) -> Result[T, E]` |

### 15.5 Métodos de `Result`

| Método | Firma |
|---|---|
| `is_ok` | `(@) -> Bool` |
| `is_err` | `(@) -> Bool` |
| `unwrap_or` | `(@own, T) -> T` |
| `map` | `(@own, (T) -> U) -> Result[U, E]` |
| `map_err` | `(@own, (E) -> F) -> Result[T, F]` |
| `and_then` | `(@own, (T) -> Result[U, E]) -> Result[U, E]` |
| `ok` | `(@own) -> Option[T]` |

`unwrap()` y `expect()` existen solo en tests y en código de prototipo; el
linter los marca en producción.

### 15.6 Errores como sums

```pengu
enchanting ConfigError
    MissingFile(path: String)
    InvalidLine(line: Int)
    Empty

read_config = (path: &Str) -> Result[Config, ConfigError]
    bind text = read(path) else
        return err(MissingFile(path: String.from(path)))
    parse_config(text)
```

La suma de errores es el mecanismo normal. No hay jerarquía de excepciones.

### 15.7 `panic`

`panic(message)` aborta el programa. Se usa para bugs, no para errores
esperables.

```pengu
assert = (condition: Bool, message: &Str) -> Unit
    if not condition then
        panic(message)
```

`panic` es `Never`. No hay `try`, `catch`, `throw` ni `raise`.

### 15.8 Entrada fallible

```pengu
grimoire: Result[Unit, ConfigError]
    bind config = read_config("app.toml")?
    print(config.name)
    ok(())
```

El backend imprime el error y devuelve código 1.

### 15.9 Diagnósticos de errores

| Código | Situación |
|---|---|
| `PGS-E1501` | `?` en función que no devuelve `Option`/`Result`. |
| `PGS-E1502` | Error de `?` incompatible. |
| `PGS-E1503` | `unwrap` en producción. |
| `PGS-E1504` | `Option`/`Result` usado como valor directo. |
| `PGS-E1505` | `Result` sin tipo de error concreto. |
| `PGS-E1506` | `panic` en una rama que debía devolver valor. |
| `PGS-E1507` | `err` sin tipo de éxito. |
| `PGS-E1508` | `none` sin tipo. |

[↑ Volver al índice](#indice)
