---

<a id="sec-13"></a>
## 13. Genéricos y bounds

### 13.1 Declaración

```pengu
identity = [T](value: T) -> T
    value

first = [T](values: &[T]) -> Option[&T]
    values.first()

rune Pair[A, B]
    first: A
    second: B
```

Los parámetros de tipo van entre `[]`, antes de los parámetros de valor.

### 13.2 Bounds

```pengu
maximum = [T: Ord](a: T, b: T) -> T
    if a > b then a else b
```

Un bound es un `pact`. Se pueden pedir varios con `+`:

```pengu
unique = [T: Eq + Hash](values: Vec[T]) -> Set[T]
    morph out = Set.new()
    for value in values do
        out.insert(value)
    out
```

No hay cláusulas `where`. No hay bounds de tipo asociado, de vida ni de
constantes.

### 13.3 Llamada

```pengu
bind n = identity[Int](42)
bind s = identity[String](String.from("pengu"))
```

El tipo se puede inferir:

```pengu
bind n = identity(42)
```

Si la inferencia no alcanza, se usa el turbofish `[T]` después del nombre.

### 13.4 Tipos genéricos

```pengu
rune Box[T]
    value: T

enchanting Maybe[T]
    some(T)
    none

pact Container[T]
    first = (@) -> Option[&T]
```

Un tipo genérico se instancia con `Box[Int]`, `Maybe[String]`,
`Container[Point]`.

### 13.5 Genéricos en rituals

```pengu
ritual[T] Box[T]
    get = (@) -> &T
        &@.value
```

Los parámetros del `ritual` deben coincidir con los del tipo o con un
subconjunto.

### 13.6 Monomorfización

Cada instancia concreta genera una versión especializada en el backend. No hay
despacho dinámico. El costo es código, no indirección.

### 13.7 Límites

- No hay parámetros de tipo con valores (`const N`).
- No hay tipos asociados.
- No hay `impl Trait`.
- No hay genéricos de rango superior.
- No hay especialización.
- No hay defaults de tipo.

### 13.8 Diagnósticos de genéricos

| Código | Situación |
|---|---|
| `PGS-E1301` | Parámetro de tipo no usado. |
| `PGS-E1302` | Bound no satisfecho. |
| `PGS-E1303` | Bound desconocido. |
| `PGS-E1304` | Turbofish con número incorrecto de tipos. |
| `PGS-E1305` | No se puede inferir el parámetro. |
| `PGS-E1306` | `where` en la superficie. |
| `PGS-E1307` | Tipo asociado en un `pact`. |
| `PGS-E1308` | Genérico en un contexto no permitido. |

[↑ Volver al índice](#indice)
