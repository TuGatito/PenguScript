---

<a id="sec-14"></a>
## 14. Operadores

### 14.1 Precedencia

De mayor a menor:

| Nivel | Operadores | Asociatividad |
|---|---|---|
| 1 | `.`, `()`, `[]`, `?` | izquierda |
| 2 | unario `-`, `not` | derecha |
| 3 | `as` | izquierda |
| 4 | `*`, `/`, `%` | izquierda |
| 5 | `+`, `-` | izquierda |
| 6 | `..`, `..=` | izquierda |
| 7 | `<`, `<=`, `>`, `>=` | izquierda |
| 8 | `is`, `isnt`, `==`, `!=` | izquierda |
| 9 | `in` | izquierda |
| 10 | `and` | izquierda |
| 11 | `or` | izquierda |
| 12 | `=` (asignación) | sentencia |

No hay `&&`, `||`, `++`, `--` ni comparaciones encadenadas (`a < b < c` es
error).

### 14.2 Aritméticos

```pengu
bind a = 1 + 2
bind b = 10 - 3
bind c = 4 * 5
bind d = 9 / 2
bind e = 9 % 2
bind f = -a
```

`/` entre enteros trunca hacia cero. La división por cero hace panic. La
suma, resta y multiplicación de enteros comprueban desbordamiento en debug y
en release; para aritmética envolvente se usan métodos explícitos de `std.int`.

### 14.3 Comparación

```pengu
a == b
a != b
a < b
a <= b
a > b
a >= b
a is b
a isnt b
```

`is`/`isnt` son alias legibles de `==`/`!=` para tipos que implementan `Eq`.
No comparan identidad de referencia.

No se pueden comparar tipos distintos sin conversión explícita.

### 14.4 Booleanos

```pengu
ready and not cancelled
ready or fallback
```

`and` y `or` hacen cortocircuito. `not` es el único operador de negación
booleana. No hay `!` para `Bool`.

### 14.5 Rangos y pertenencia

```pengu
0..10
0..=10
value in 0..10
```

`in` comprueba pertenencia en un rango, en un `Set` o en un `Map` (clave).

### 14.6 Casts

```pengu
bind small = 300 as U8
bind code = 'P' as U32
bind ratio = 2 as Float
```

`as` solo convierte entre primitivos numéricos y entre `Char` y enteros. No
convierte records, sums ni strings. Para strings se usa `.parse[T]()`; para
números a string, `.to_string()`.

### 14.7 `?`

El operador postfix `?` propaga `Option`/`Result`:

```pengu
read_config = (path: &Str) -> Result[Config, ReadError]
    bind text = read(path)?
    parse_config(text)
```

- En una función que devuelve `Option[T]`, `?` propaga `none`.
- En una función que devuelve `Result[T, E]`, `?` propaga `err`.
- El error debe convertirse explícitamente si el tipo no coincide.

### 14.8 Sobrecarga

La sobrecarga de operadores es explícita y chica. Los pacts viven en
`std.ops` y se importan:

```pengu
summon std::ops::Add

rune Point
    x: Float
    y: Float

ritual Point for Add
    add = (@own, other: Point) -> Point
        Point(x: @.x + other.x, y: @.y + other.y)

bind p = Point(x: 1.0, y: 2.0) + Point(x: 3.0, y: 4.0)
```

Solo se sobrecargan:

| Operador | Pact | Método |
|---|---|---|
| `+` | `Add` | `add` |
| `-` | `Sub` | `sub` |
| `*` | `Mul` | `mul` |
| `/` | `Div` | `div` |
| `%` | `Rem` | `rem` |
| `-` unario | `Neg` | `neg` |
| `==`, `!=` | `Eq` | `eq` |
| `<`, `<=`, `>`, `>=` | `Ord` | `cmp` |

La firma es siempre `(@own, other: Self) -> Self` (o `(@, other: &Self) ->
Bool` para `Eq`/`Ord`). No hay tipo de salida asociado.

No se sobrecargan `[]`, `()`, `.`, `=`, `&`, `*` de desreferencia, `?`, `!`,
`..` ni `as`. No hay `+=` para tipos de usuario; se escribe `p = p + q`.

### 14.9 Diagnósticos de operadores

| Código | Situación |
|---|---|
| `PGS-E1401` | Tipos incompatibles en un operador. |
| `PGS-E1402` | Operador no definido para el tipo. |
| `PGS-E1403` | División por cero constante. |
| `PGS-E1404` | Cast inválido. |
| `PGS-E1405` | `?` fuera de una función que devuelve `Option`/`Result`. |
| `PGS-E1406` | Sobrecarga de un operador no permitido. |
| `PGS-E1407` | Firma de sobrecarga incorrecta. |
| `PGS-E1408` | Comparación encadenada. |

[↑ Volver al índice](#indice)
