---

<a id="sec-12"></a>
## 12. Pacts y rituals

### 12.1 `pact`

Un `pact` declara un contrato de métodos:

```pengu
pact Shape
    area = (@) -> Float
    name = (@) -> String
        "shape"
```

Reglas:

- Solo declara métodos con receptor `@`, `@mut` o `@own`.
- Puede dar una implementación por defecto.
- Puede tener como máximo un superpact.
- No declara tipos asociados, constantes asociadas, métodos genéricos,
  métodos async ni cláusulas `where`.
- No se usa como tipo dinámico: no hay `dyn` ni `Box[dyn Pact]`.

### 12.2 Superpact

```pengu
pact Named
    name = (@) -> String

pact Shape: Named
    area = (@) -> Float
```

`Shape` exige que el tipo implemente también `Named`. No hay herencia múltiple.

### 12.3 `Show`

`Show` es el único pact de la prelude:

```pengu
pact Show
    show = (@) -> String
```

`print(x)` y `format("#{x}")` requieren `x: Show` o un primitivo. No hay
`Display` ni `Debug` en la superficie; `@@derive(Debug)` sigue existiendo para
depuración del backend, pero el usuario no lo usa para imprimir.

### 12.4 `ritual` inherente

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Un `ritual` inherente agrega métodos y funciones asociadas al tipo.

- `@` recibe `&self`.
- `@mut` recibe `&mut self`.
- `@own` recibe `self`.
- Una función sin receptor se llama como `Point.origin()`.
- `Self` se refiere al tipo del `ritual`.

### 12.5 `ritual ... for`

```pengu
ritual Point for Shape
    area = (@) -> Float
        0.0

    name = (@) -> String
        "point"
```

Un `ritual Tipo for Pact` implementa el contrato. Deben estar todos los
métodos sin default.

### 12.6 Reglas de coherencia

- Se puede implementar un `pact` propio para un tipo propio.
- Se puede implementar un `pact` de la librería para un tipo propio.
- No se puede implementar un `pact` ajeno para un tipo ajeno.
- No hay impls solapadas.
- No hay blanket impls (`ritual[T] Pact for T`).
- Un tipo puede tener varios `ritual` inherentes, pero no dos métodos con el
  mismo nombre.

### 12.7 Genéricos en rituals

```pengu
rune Box[T]
    value: T

ritual[T] Box[T]
    get = (@) -> &T
        &@.value

    replace = (@mut, value: T) -> T
        bind old = @.value
        @.value = value
        old
```

El parámetro `[T]` se declara en el `ritual`. Los bounds van en la cabecera.

### 12.8 Sin despacho dinámico

No hay `dyn Pact`, `impl Pact` en retorno ni tablas virtuales. Si se necesita
elegir entre variantes, se usa un `enchanting`:

```pengu
enchanting AnyShape
    Circle(Circle)
    Square(Square)

bind area = (shape: AnyShape) -> Float
    match shape
        when Circle(c) then c.area()
        when Square(s) then s.area()
```

### 12.9 Diagnósticos de pacts

| Código | Situación |
|---|---|
| `PGS-E1201` | Método faltante en el `ritual`. |
| `PGS-E1202` | Firma incompatible con el `pact`. |
| `PGS-E1203` | `pact` con más de un superpact. |
| `PGS-E1204` | `pact` con tipo asociado. |
| `PGS-E1205` | `ritual` para tipo ajeno y pact ajeno. |
| `PGS-E1206` | Implementaciones solapadas. |
| `PGS-E1207` | Blanket impl. |
| `PGS-E1208` | `dyn`/`impl Pact` en la superficie. |
| `PGS-E1209` | `Self` fuera de un `pact`/`ritual`. |

[↑ Volver al índice](#indice)
