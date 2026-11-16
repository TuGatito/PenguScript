---

<a id="sec-05"></a>
## 5. Bindings, mutabilidad y constantes

### 5.1 `bind` y `morph`

```pengu
bind name = "pengu"
bind answer = 42
morph count = 0
count = count + 1
```

- `bind` crea un binding inmutable.
- `morph` crea un binding mutable.
- `=` reasigna un binding `morph`; nunca crea uno nuevo.
- La mutabilidad se declara en el binding, no en el tipo.

No hay `let`, `var`, `const`, `final` ni `mut`.

### 5.2 Sin variables globales

Un módulo no puede declarar `bind` ni `morph` en su nivel superior:

```pengu
-- ERROR PGS-E1101
bind counter = 0
```

El estado global mutable no existe. Para constantes se usa `sigil`; para datos
inmutables compartidos, `relic`.

### 5.3 Scope y sombreado

Un binding vive desde su declaración hasta el final del bloque. Se puede
sombear con otro `bind`/`morph` en un bloque interno, pero no en el mismo
bloque:

```pengu
bind x = 1
if true then
    bind x = 2
    print(x) -- 2
print(x) -- 1
```

```pengu
-- ERROR PGS-E1102
bind x = 1
bind x = 2
```

No hay elevación de declaraciones. Un binding no existe antes de su línea.

### 5.4 Destructuring

```pengu
bind (a, b) = (1, 2)
bind Point(x, y) = Point(x: 3.0, y: 4.0)
bind Point(x: px, y: py) = Point(x: 5.0, y: 6.0)
```

El patrón debe ser irrefutable. Para patrones refutables se usa `match`,
`if ... then` o `bind ... else`:

```pengu
bind some(value) = maybe else
    return
```

### 5.5 Asignación

```pengu
morph point = Point(x: 1.0, y: 2.0)
point.x = 3.0
point.y = point.y + 1.0
```

Solo se puede asignar a:

- un binding `morph`;
- un campo de un binding `morph`;
- un elemento de un `Vec`/`Map` a través de un binding `morph`;
- un `&mut T` local.

La asignación es una sentencia, no una expresión. No devuelve valor.

### 5.6 Constantes

`sigil` declara una constante de módulo, evaluada en compilación:

```pengu
sigil MAX_POINTS: Int = 1024
sigil GREETING: &Str = "hola"
sigil ORIGIN: Point = Point(x: 0.0, y: 0.0)
```

Debe tener tipo explícito y una expresión constante. No puede depender de
`bind`/`morph` locales ni de estado en tiempo de ejecución.

### 5.7 `relic`

`relic` declara un valor inmutable de módulo, inicializado una vez:

```pengu
relic TABLE: [Int; 4] = [1, 2, 3, 4]
```

No hay `relic mut` ni `static mut`. Un `relic` no se reasigna. Si se necesita
estado compartido mutable, se importa de `std.concurrent` de forma explícita;
no es parte del núcleo.

### 5.8 Nombres

- `bind`/`morph`: `snake_case`.
- `sigil`: `SCREAMING_SNAKE_CASE`.
- `relic`: `SCREAMING_SNAKE_CASE`.

Un `sigil` o `relic` privado se puede usar en todo el módulo. `unveil` lo
expone fuera.

### 5.9 Diagnósticos de bindings

| Código | Situación |
|---|---|
| `PGS-E1101` | `bind`/`morph` en nivel de módulo. |
| `PGS-E1102` | Redeclaración en el mismo bloque. |
| `PGS-E1103` | Asignación a un binding inmutable. |
| `PGS-E1104` | Asignación a un campo privado. |
| `PGS-E1105` | Patrón refutable sin `else`. |
| `PGS-E1106` | `sigil` sin tipo explícito. |
| `PGS-E1107` | `sigil` con expresión no constante. |
| `PGS-E1108` | `relic` reasignado. |

[↑ Volver al índice](#indice)
