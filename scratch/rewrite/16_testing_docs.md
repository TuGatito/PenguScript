---

<a id="sec-17"></a>
## 17. Testing y documentación

### 17.1 `@@test`

El único atributo de testing es `@@test`:

```pengu
@@test
adds = () -> Unit
    assert_eq(1 + 1, 2)
```

Una función de test:

- no recibe parámetros;
- devuelve `Unit` o `Result[Unit, E]`;
- se ejecuta con `pengu test`;
- puede estar en cualquier módulo.

### 17.2 Variantes

```pengu
@@test(should_panic: "división por cero")
divide_by_zero = () -> Unit
    _ = 1 / 0

@@test(ignore: "pendiente de implementar")
future_test = () -> Unit
    assert(false)
```

No hay `@@bench`, `@@should_panic` separado, property testing ni fuzzing en el
núcleo. Viven en `std.test` o en crates externos.

### 17.3 Aserciones

```pengu
assert(condition, "mensaje")
assert_eq(actual, expected)
assert_ne(actual, unexpected)
```

`assert` hace panic con el mensaje si la condición es falsa. `assert_eq` y
`assert_ne` requieren `Debug + PartialEq` y muestran ambos valores.

### 17.4 Tests de integración

`[[test]]` en `Tome.toml`:

```toml
[[test]]
name = "integration"
path = "tests/integration.pengu"
```

El archivo se compila como un binario de test independiente. No hay
`#[cfg(test)]`: `@@test` marca la función.

### 17.5 Documentación

```pengu
--- Suma dos enteros.
---
--- ```pengu
--- assert_eq(add(1, 2), 3)
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

- `---` documenta el item siguiente.
- `--!` documenta el módulo.
- El contenido es Markdown.
- Los bloques ```pengu se ejecutan como doc tests con `pengu test --doc`.

### 17.6 `@@deprecated` no existe

No hay atributos generales. Para marcar algo como obsoleto se usa la
documentación y el changelog; el linter puede emitir un warning si el nombre
aparece en una lista de migración.

### 17.7 Cobertura

`pengu test --coverage` produce un reporte de líneas y ramas. La cobertura no
es parte de la semántica del lenguaje.

### 17.8 Diagnósticos de testing

| Código | Situación |
|---|---|
| `PGS-E1701` | `@@test` con parámetros. |
| `PGS-E1702` | `@@test` con retorno inválido. |
| `PGS-E1703` | `should_panic` sin mensaje. |
| `PGS-E1704` | `assert_eq` con tipos incompatibles. |
| `PGS-E1705` | Doc test que no compila. |
| `PGS-E1706` | `@@test` duplicado. |

[↑ Volver al índice](#indice)
