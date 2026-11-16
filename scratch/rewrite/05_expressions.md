---

<a id="sec-06"></a>
## 6. Expresiones y control

### 6.1 Todo lo que produce un valor es una expresión

Un bloque, un `if`, un `match`, un `loop` y una función producen un valor.
`bind`, la asignación y la declaración de items son sentencias.

```pengu
bind label = if ready then "listo" else "esperando"
```

La última expresión de un bloque es su valor:

```pengu
bind area =
    bind side = 4.0
    side * side
```

No se usa `;`. Una línea nueva separa sentencias.

### 6.2 `if`

```pengu
if condition then
    do_one()
elseif other then
    do_two()
else
    do_three()
```

La forma en una línea usa `then` y `else`:

```pengu
bind status = if score >= 60 then "ok" else "fail"
```

Reglas:

- La condición debe ser `Bool`; no hay truthiness.
- Sin `else`, el `if` es `Unit`.
- Con `else`, las dos ramas deben unificar en un tipo.
- Una rama `Never` no participa en la unificación.

### 6.3 `unless`

```pengu
unless ready then
    wait()
```

`unless` es `if not condition`. No tiene `elseif`; puede tener `else`.

### 6.4 `do`

`do` introduce un bloque explícito como expresión:

```pengu
bind value = do
    bind x = 10
    x * 2
```

Se usa cuando hace falta un bloque donde la indentación sola no basta.

### 6.5 `for`

```pengu
for item in items do
    print(item)

for i in 0..10 do
    print(i)

for (key, value) in map do
    print("#{key}: #{value}")
```

`for` recorre un iterable. El cuerpo es `Unit`. No hay `for` estilo C ni
`for` con índice implícito.

### 6.6 `while`

```pengu
morph n = 3
while n > 0 do
    n = n - 1
```

La condición es `Bool`. El resultado es `Unit`.

### 6.7 `loop`

```pengu
bind result = loop
    if done() then
        break 42
    work()
```

`loop` se repite hasta un `break`. Un `break` con valor convierte el `loop` en
una expresión de ese tipo. Un `loop` sin `break` es `Never`.

### 6.8 `break`, `continue`, `return`

```pengu
for x in items do
    if x < 0 then
        continue
    if x > 100 then
        break
    print(x)
```

- `break` sale del `loop`/`while`/`for` más cercano.
- `continue` salta a la siguiente iteración.
- `return expr` sale de la función.
- `return` sin expresión devuelve `Unit`.
- Los tres son `Never`.

No hay labels de bucle en el núcleo.

### 6.9 `match` en una línea

El pattern matching completo está en §9. La forma básica es:

```pengu
bind kind = match shape
    when Circle(_) then "redondo"
    when Square(_) then "cuadrado"
    else "otro"
```

### 6.10 Diagnósticos de control

| Código | Situación |
|---|---|
| `PGS-E6001` | Condición que no es `Bool`. |
| `PGS-E6002` | Ramas de `if` con tipos incompatibles. |
| `PGS-E6003` | `else` sin `if`. |
| `PGS-E6004` | `break`/`continue` fuera de un bucle. |
| `PGS-E6005` | `break` con valor fuera de `loop`. |
| `PGS-E6006` | `return` con valor en función `Unit`. |
| `PGS-E6007` | `loop` sin `break` usado como valor. |
| `PGS-E6008` | `match` no exhaustivo. |

[↑ Volver al índice](#indice)
