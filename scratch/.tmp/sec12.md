<a id="sec-12-booleanos"></a>
## 12. Booleanos y lógica

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | `bool`, `&&`, `\|\|`, `!` |
| Palabras mágicas | `and`, `or`, `not`, `is`, `isnt` |
| Depende de | §9, §11 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec12_booleans.pengu` |

`Bool` tiene dos valores y ninguna conversión implícita. PenguScript no tiene
truthiness: una condición no es “cualquier cosa que no sea cero/vacía/nula”. Si
una rama necesita un `Bool`, se escribe un `Bool`.

### 12.1 El tipo `Bool`

| Propiedad | Valor |
|---|---|
| Valores | `true`, `false` |
| Tipo Rust | `bool` |
| Tamaño | 1 byte en el codegen actual; no es parte de la ABI |
| Conversión implícita | ninguna |
| `null`/`none` como falso | no |

```pengu
bind enabled: Bool = true
bind disabled = false
bind also_disabled: Bool = not enabled
```

No se puede usar un entero como condición:

```pengu
if 1
    print("no")
```

El error es `PGS-E9301`: la condición debe ser `Bool`, no `Int`. Tampoco se puede
usar `none`, un string vacío ni un puntero.

### 12.2 Operadores lógicos

| Operador | Aridad | Tipos | Rust | Cortocircuito |
|---|---|---|---|---|
| `and` | binario | `Bool`, `Bool` | `&&` | sí |
| `or` | binario | `Bool`, `Bool` | `\|\|` | sí |
| `not` | unario | `Bool` | `!` | — |
| `!` | unario | `Bool` o entero | `!` | — |

`and` y `or` **solo** aceptan `Bool`. No devuelven el operando como Python:
`true and 1` es error de tipo, no `1`.

```pengu
bind can_run = ready and not paused
bind either = ready or paused
bind neither = not (ready or paused)
```

Rust generado:

```rust
let can_run = ready && !paused;
let either = ready || paused;
let neither = !(ready || paused);
```

`!` es un alias de `not` para `Bool`; `not` es la forma recomendada. `!` también
es el complemento bit a bit de enteros (§11.5); el tipo del operando decide.

No se aceptan `&&` ni `||` (`PGS-E9303`). La forma canónica es `and`/`or`, para
que la lógica se lea como MoonScript y no se mezclen dos vocabularios.

### 12.3 Cortocircuito

`and` evalúa el lado derecho solo si el izquierdo es `true`. `or` lo evalúa solo
si el izquierdo es `false`.

```pengu
bind ok = has_permission(user) and audit(user)
bind fallback = cache.has(key) or compute(key)
```

Rust generado:

```rust
let ok = has_permission(user) && audit(user);
let fallback = cache.has(key) || compute(key);
```

Consecuencias:

1. El lado derecho puede tener efectos secundarios que no ocurren.
2. No se usa `and`/`or` para elegir un valor; para eso está `if`.
3. `and`/`or` no son funciones; no se pueden pasar como argumento.
4. `not` no cortocircuita porque es unario.

### 12.4 Comparaciones

Las comparaciones producen `Bool`:

| Operador | Requisito | Resultado |
|---|---|---|
| `==`, `!=` | `PartialEq` | `Bool` |
| `<`, `<=`, `>`, `>=` | `PartialOrd` | `Bool` |
| `is`, `isnt` | alias de `==`, `!=` | `Bool` |

`is`/`isnt` no son identidad de referencia; comparan valores. Dos `String` con el
mismo contenido son `is`. Para identidad de referencia se usa `ptr_eq` (§19).

Las comparaciones **no encadenan**. `a < b < c` es error (`PGS-E9203`); se
escribe:

```pengu
bind in_range = low <= value and value <= high
```

### 12.5 Lógica y bitwise

`and`/`or` son lógicos y cortocircuitan. `&`/`|`/`^` son bit a bit y evalúan
ambos lados. Sobre `Bool`, `&`/`|`/`^` existen pero **no** son la forma
recomendada:

```pengu
bind a = true & false       -- false, evalúa ambos
bind b = true and false     -- false, cortocircuita
```

Para lógica se usan `and`/`or`/`not`. Para máscaras de bits se usan `&`/`|`/`^`
sobre enteros.

### 12.6 Condiciones estrictas

Toda posición que espera un `Bool` exige exactamente `Bool`:

| Posición | Regla |
|---|---|
| `if`/`elseif`/`unless` | condición `Bool` |
| `while` | condición `Bool` |
| `for ... if` (comprehension) | condición `Bool` |
| guard de `match` | condición `Bool` |
| `assert(cond)` | condición `Bool` |

No hay conversión de `Int`, `Float`, `Char`, `Str`, `?T`, `!T` ni punteros a
`Bool`. Si se necesita “no vacío”, se escribe `s.is_empty()` o
`option.is_some()`.

### 12.7 `Bool` y `match`

`match` sobre `Bool` debe cubrir `true` y `false`:

```pengu
bind label = match enabled
    when true then "activo"
    when false then "inactivo"
```

Un `match` sin uno de los dos brazos es no exhaustivo (`PGS-E9306`). El
compilador no añade un brazo comodín para `Bool`.

### 12.8 Ejemplo completo

```pengu
grimoire
    bind ready = true
    bind paused = false
    bind can_run = ready and not paused
    bind either = ready or paused
    bind neither = not (ready or paused)
    bind in_range = 1 <= 2 and 2 <= 3

    print(can_run)
    print(either)
    print(neither)
    print(in_range)
```

Rust generado:

```rust
fn main() {
    let ready = true;
    let paused = false;
    let can_run = ready && !paused;
    let either = ready || paused;
    let neither = !(ready || paused);
    let in_range = 1 <= 2 && 2 <= 3;

    println!("{}", can_run);
    println!("{}", either);
    println!("{}", neither);
    println!("{}", in_range);
}
```

La salida es `true`, `true`, `false`, `true`.

### 12.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9301` | condición que no es `Bool` | usar una comparación o `is_empty`/`is_some` |
| `PGS-E9302` | `and`/`or` con un operando que no es `Bool` | convertir la condición explícitamente |
| `PGS-E9303` | `&&`/`\|\|` usados | usar `and`/`or` |
| `PGS-E9304` | `not` sobre un tipo que no es `Bool` | usar `!` para enteros o una comparación |
| `PGS-E9305` | conversión implícita a `Bool` | escribir la comparación |
| `PGS-E9306` | `match` de `Bool` no exhaustivo | cubrir `true` y `false` |
| `PGS-W9301` | `&`/`\|` sobre `Bool` en contexto lógico | usar `and`/`or` si se busca cortocircuito |

### 12.10 Criterios de aceptación

- [x] `Bool` es estricto y no hay truthiness.
- [x] `and`/`or` cortocircuitan y solo aceptan `Bool`.
- [x] `not` y `!` están definidos sin ambigüedad.
- [x] Las comparaciones producen `Bool` y no encadenan.
- [x] Las condiciones de `if`/`while`/`match` exigen `Bool`.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

