---

<a id="sec-09"></a>
## 9. Pattern matching

### 9.1 `match`

```pengu
bind area = match shape
    when Circle(radius) then
        3.141592653589793 * radius * radius
    when Rectangle(width, height) then
        width * height
    when Point then
        0.0
```

Cada brazo empieza con `when`, sigue un patrón y termina en `then` o en un
bloque indentado.

`else` cubre el resto:

```pengu
bind label = match n
    when 0 then "cero"
    when 1 then "uno"
    else "muchos"
```

### 9.2 Patrones

| Patrón | Ejemplo |
|---|---|
| Literal | `when 0`, `when "ok"`, `when true` |
| Binding | `when x` |
| Wildcard | `when _` |
| Tupla | `when (a, b)` |
| Record | `when Point(x, y)` |
| Record con nombres | `when Point(x: px, y: py)` |
| Variante unitaria | `when None` |
| Variante con campos | `when Some(value)` |
| Variante con nombres | `when Circle(radius: r)` |
| Rango | `when 0..=9` |
| Alternativa | `when 0 | 1 | 2` |
| Binding de patrón | `when whole @ Some(_)` |
| Resto | `when Point(x, ..)` |
| Slice | `when [first, .., last]` |

No hay `ref`, `ref mut`, `box`, `dyn` ni patrones de tipo.

### 9.3 Guards

```pengu
bind kind = match n
    when x if x < 0 then "negativo"
    when 0 then "cero"
    else "positivo"
```

Un guard es una expresión `Bool`. Si falla, se prueba el siguiente brazo.

### 9.4 `bind ... else`

Un binding refutable necesita `else`:

```pengu
bind some(value) = maybe else
    return none

bind ok(number) = result else
    return err("no era un número")
```

El `else` debe divergir: `return`, `break`, `continue` o `panic`.

### 9.5 Alternativas y anidamiento

```pengu
bind sign = match n
    when -1 | 0 | 1 then "pequeño"
    when x if x < 0 then "negativo"
    else "grande"
```

Los patrones se evalúan de arriba a abajo. El primero que coincide gana.

### 9.6 Exhaustividad

Un `match` sobre un `enchanting` debe cubrir todas las variantes o tener
`else`. Un `match` sobre `Bool` debe cubrir `true` y `false` o tener `else`.
Un `match` sobre un rango de enteros necesita `else`.

```pengu
-- ERROR PGS-E6008
bind bad = match shape
    when Circle(_) then 1.0
```

### 9.7 `match` como expresión

El tipo del `match` es la unificación de todos los brazos. Un brazo `Never`
no participa.

```pengu
bind message = match result
    when ok(value) then "valor: #{value}"
    when err(reason) then
        panic(reason)
```

### 9.8 Diagnósticos de patrones

| Código | Situación |
|---|---|
| `PGS-E9001` | Patrón no exhaustivo. |
| `PGS-E9002` | Brazo inalcanzable. |
| `PGS-E9003` | Patrón incompatible con el tipo. |
| `PGS-E9004` | Guard que no es `Bool`. |
| `PGS-E9005` | `bind ... else` sin divergencia. |
| `PGS-E9006` | `..` en posición inválida. |
| `PGS-E9007` | Binding duplicado en un patrón. |
| `PGS-E9008` | `else` después de un brazo exhaustivo. |

[↑ Volver al índice](#indice)
