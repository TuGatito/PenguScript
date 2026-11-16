---

<a id="sec-08"></a>
## 8. Records y sums

### 8.1 Records

```pengu
rune Point
    x: Float
    y: Float

bind p = Point(x: 1.0, y: 2.0)
```

Un `rune` agrupa campos con nombre. Es un tipo nominal: `Point` no es
intercambiable con otro record de la misma forma.

Los campos son privados por defecto. `unveil` los expone:

```pengu
unveil rune Point
    unveil x: Float
    unveil y: Float
```

Un campo `unveil` se lee desde fuera; se modifica a través de un método `@mut`
o de un binding `morph` dentro del módulo.

### 8.2 Records de un campo

```pengu
rune UserId
    value: UInt

bind id = UserId(value: 7)
```

Un record de un campo es un newtype: no se convierte automáticamente en
`UInt`.

### 8.3 Records genéricos

```pengu
rune Box[T]
    value: T

rune Pair[A, B]
    first: A
    second: B

bind pair = Pair(first: 1, second: "uno")
```

Los parámetros de tipo se declaran entre `[]`. Los bounds van en la cabecera:

```pengu
rune Sorted[T: Ord]
    items: Vec[T]
```

### 8.4 Shorthand y actualización

```pengu
bind x = 3.0
bind p = Point(x: x, y: 4.0)
bind q = Point(y: 5.0, ..p)
```

`..p` copia los campos restantes de `p`. El tipo de `q` es el mismo que el de
`p`. Los campos sobrescritos se evalúan una sola vez.

### 8.5 Sums

```pengu
enchanting Shape
    Circle(radius: Float)
    Rectangle(width: Float, height: Float)
    Point
```

Un `enchanting` tiene variantes:

- unitarias (`Point`);
- con campos nombrados (`Circle(radius: Float)`);
- con campos posicionales (`Rectangle(Float, Float)`).

No hay discriminantes numéricos ni `repr`. El backend elige la representación.

### 8.6 Construcción y match

```pengu
bind c = Circle(radius: 2.0)
bind r = Rectangle(3.0, 4.0)

bind name = match c
    when Circle(radius) then "círculo"
    when Rectangle(width, height) then "rectángulo"
    when Point then "punto"
```

El `match` debe ser exhaustivo o tener `else`. Los detalles están en §9.

### 8.7 `Option` y `Result`

`Option[T]` y `Result[T, E]` son sums de la prelude:

```pengu
enchanting Option[T]
    some(T)
    none

enchanting Result[T, E]
    ok(T)
    err(E)
```

No se pueden redeclarar. `?T` es azúcar para `Option[T]`.

### 8.8 `@@derive`

El único atributo general es `@@derive(...)`, y solo acepta:

`Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`,
`Default`.

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Float
    y: Float
```

Reglas:

- `Copy` exige `Clone` y ningún campo con `String`, `Vec`, `Map` o `Set`.
- `Eq`, `Ord` y `Hash` no se pueden derivar si hay `Float`.
- `Default` exige que todos los campos tengan valor por defecto.
- No hay derives externos en v1.

### 8.9 Diagnósticos de records y sums

| Código | Situación |
|---|---|
| `PGS-E8001` | Campo duplicado. |
| `PGS-E8002` | Campo faltante en la construcción. |
| `PGS-E8003` | Campo desconocido. |
| `PGS-E8004` | Variante duplicada. |
| `PGS-E8005` | `..base` con tipo incompatible. |
| `PGS-E8006` | `@@derive` desconocido. |
| `PGS-E8007` | `@@derive` imposible para un campo. |
| `PGS-E8008` | `Option`/`Result` redeclarados. |

[↑ Volver al índice](#indice)
