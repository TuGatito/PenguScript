<a id="sec-14-bucles"></a>
## 14. Bucles

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | `while`, `loop`, `for`, `break`, `continue`, labels |
| Palabras mágicas | `while`, `loop`, `for`, `by`, `break`, `continue` |
| Depende de | §8, §11, §13 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec14_loops.pengu` |

PenguScript tiene tres bucles: `while` para repetir mientras una condición sea
`Bool`, `loop` para repetir hasta un `break`, y `for` para recorrer un iterable o
un rango. `loop` puede producir un valor con `break value`; `while` y `for`
producen `Unit`.

### 14.1 `while`

```pengu
morph n = 3
while n > 0
    print(n)
    n -= 1
```

Rust generado:

```rust
let mut n = 3;
while n > 0 {
    println!("{}", n);
    n -= 1;
}
```

Reglas:

1. La condición debe ser `Bool`; no hay truthiness (`PGS-E9501`).
2. La condición se evalúa antes de cada iteración; si es `false` al inicio, el
   cuerpo no se ejecuta.
3. `while` produce `Unit`; no se puede `bind` su resultado.
4. `break` sale del bucle; `continue` salta a la siguiente comprobación.
5. `break value` **no** es válido en `while` (`PGS-E9504`); para producir un
   valor se usa `loop`.

### 14.2 `loop`

```pengu
morph attempts = 0
loop
    attempts += 1
    if attempts >= 3
        break
```

Rust generado:

```rust
let mut attempts = 0;
loop {
    attempts += 1;
    if attempts >= 3 {
        break;
    }
}
```

`loop` sin `break` tiene tipo `Never`; un `loop` con `break value` tiene el tipo
del valor:

```pengu
bind answer = loop
    break 42
```

Rust generado:

```rust
let answer = loop {
    break 42;
};
```

Reglas:

1. `break` sin valor produce `Unit`; `break value` produce el tipo del valor.
2. Todos los `break value` de un mismo `loop` deben unificar (`PGS-E9510`).
3. Un `loop` sin `break` es `Never` y no termina normalmente.
4. `continue` vuelve al inicio del `loop` sin producir valor.
5. `loop` es una expresión; se puede usar en `bind`, `return` o como rama.

### 14.3 `for` sobre iterables

```pengu
for item in items
    print(item)

for (key, value) in table
    print(key)
    print(value)
```

Rust generado:

```rust
for item in items {
    println!("{}", item);
}

for (key, value) in table {
    println!("{}", key);
    println!("{}", value);
}
```

Reglas:

1. `for` llama a `IntoIterator` sobre el iterable. Un array, `Vec`, slice, mapa,
   set o rango implementan `IntoIterator`; un tipo de usuario puede implementarlo
   en §49.
2. El patrón del `for` puede ser un identificador, una tupla, un `rune` o un
   patrón de §30.
3. El binding del patrón es inmutable. Para mutar el valor dentro del cuerpo se
   usa un `morph` local o se recorre por referencia mutable.
4. `for` produce `Unit`; no se puede `bind` su resultado.
5. El iterable se evalúa una vez, antes de la primera iteración.
6. Si el iterable se mueve, queda movido después del bucle (§16).

### 14.4 Rangos numéricos y `by`

```pengu
for i in 0..5
    print(i)

for i in 0..=10 by 2
    print(i)
```

Rust generado:

```rust
for i in 0..5 {
    println!("{}", i);
}

for i in (0..=10).step_by(2) {
    println!("{}", i);
}
```

Reglas:

1. `a..b` es exclusivo; `a..=b` es inclusivo.
2. `by n` es opcional y solo se aplica a rangos numéricos. `n` debe ser un entero
   positivo (`PGS-E9505`); `by 0` es error.
3. `by` no cambia el tipo del rango; el codegen usa `step_by`.
4. No hay `by` negativo. Para recorrer en orden inverso se usa `.rev()` sobre el
   rango (adelanto de §49).
5. `by` solo es válido en `for`, no en una expresión de rango general
   (`PGS-E9506`).

### 14.5 `break` y `continue`

| Forma | Dónde | Efecto |
|---|---|---|
| `break` | cualquier bucle | sale del bucle |
| `break value` | solo `loop` | sale y produce `value` |
| `continue` | cualquier bucle | salta a la siguiente iteración |
| `break label` | bucle etiquetado | sale del bucle con esa etiqueta |
| `continue label` | bucle etiquetado | continúa el bucle con esa etiqueta |

`break value` en `while` o `for` es error (`PGS-E9504`). `break` fuera de un
bucle es error (`PGS-E9502`); `continue` fuera de un bucle también
(`PGS-E9503`).

### 14.6 Etiquetas

Una etiqueta se escribe antes del bucle:

```pengu
outer: for i in 0..3
    inner: while true
        if i == 1
            break outer
        break
```

Rust generado:

```rust
'outer: for i in 0..3 {
    'inner: while true {
        if i == 1 {
            break 'outer;
        }
        break;
    }
}
```

Reglas:

1. La etiqueta es un identificador seguido de `:` al inicio de la línea del
   bucle; no es un tipo ni un campo.
2. `break outer` y `continue outer` deben referirse a un bucle etiquetado
   envolvente (`PGS-E9509`).
3. Las etiquetas no crean scope de variables; solo nombran el bucle.
4. No se puede etiquetar un `if` o un bloque, solo `while`/`loop`/`for`.

### 14.7 `loop` como expresión

```pengu
bind first_even = loop
    bind n = next()
    if n % 2 == 0
        break n
```

Rust generado:

```rust
let first_even = loop {
    let n = next();
    if n % 2 == 0 {
        break n;
    }
};
```

El tipo de `first_even` es el tipo de `n`. Un `loop` con varios `break` debe
unificar sus valores; un `break` sin valor en un `loop` que produce valor es
error (`PGS-E9510`).

### 14.8 Comprehensions

Una comprehension es azúcar para construir una colección:

```pengu
bind squares = [x * x for x in 0..5]
bind evens = [x for x in 0..10 if x % 2 == 0]
bind lengths = { name: name.len() for name in ["a", "bb"] }
```

Rust generado:

```rust
let squares: Vec<i32> = (0..5).map(|x| x * x).collect();
let evens: Vec<i32> = (0..10).filter(|x| x % 2 == 0).collect();
let lengths: std::collections::HashMap<&str, usize> =
    ["a", "bb"].into_iter().map(|name| (name, name.len())).collect();
```

Reglas:

1. `[expr for pattern in iterable]` produce un `Vec[T]`.
2. `[expr for pattern in iterable if cond]` filtra con `cond`, que debe ser
   `Bool`.
3. `{ key: value for pattern in iterable }` produce un `HashMap[K, V]`; las
   claves deben implementar `Eq + Hash`.
4. No hay `break`/`continue` dentro de una comprehension; usar un `for`
   explícito (`PGS-E9508`).
5. El orden de los elementos de un `HashMap` no se garantiza.
6. Una comprehension es una expresión; se puede usar en `bind`, `return` o como
   argumento.

### 14.9 `while let` e iteradores

La forma `while let` de Rust se expresará con `match`/patrones en §30; en Fase 2
se usa un `loop` con `match` o `while cond`. Los adaptadores de iterador
(`map`, `filter`, `enumerate`, `zip`, `take`, `skip`, `chain`, `rev`) se
documentan en §49.

### 14.10 Ejemplo completo

```pengu
grimoire
    morph total = 0
    for i in 0..5
        total += i

    for i in 0..=10 by 2
        total += i

    outer: for i in 0..3
        for j in 0..3
            if i == 1 and j == 1
                break outer

    bind squares = [x * x for x in 0..5]
    bind evens = [x for x in 0..10 if x % 2 == 0]

    print(total)
    print(squares.len())
    print(evens.len())
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    for i in 0..5 {
        total += i;
    }

    for i in (0..=10).step_by(2) {
        total += i;
    }

    'outer: for i in 0..3 {
        for j in 0..3 {
            if i == 1 && j == 1 {
                break 'outer;
            }
        }
    }

    let squares: Vec<i32> = (0..5).map(|x| x * x).collect();
    let evens: Vec<i32> = (0..10).filter(|x| x % 2 == 0).collect();

    println!("{}", total);
    println!("{}", squares.len());
    println!("{}", evens.len());
}
```

La salida es `40`, `5`, `5`.

### 14.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9501` | condición de `while` que no es `Bool` | usar una comparación |
| `PGS-E9502` | `break` fuera de un bucle | moverlo dentro o eliminarlo |
| `PGS-E9503` | `continue` fuera de un bucle | moverlo dentro o eliminarlo |
| `PGS-E9504` | `break value` en `while`/`for` | usar `loop` o `break` sin valor |
| `PGS-E9505` | `by` no positivo | usar un entero positivo |
| `PGS-E9506` | `by` fuera de un `for` | moverlo al `for` |
| `PGS-E9507` | `loop` sin `break` usado como valor | añadir `break` o cambiar el contexto |
| `PGS-E9508` | `break`/`continue` en comprehension | usar un `for` explícito |
| `PGS-E9509` | etiqueta no encontrada | etiquetar el bucle envolvente |
| `PGS-E9510` | `break` con tipos incompatibles | unificar los valores |
| `PGS-W9501` | `loop` que nunca termina | añadir una condición de salida |

### 14.12 Criterios de aceptación

- [x] `while`, `loop` y `for` tienen sintaxis y semántica.
- [x] `loop` puede producir valor con `break value`.
- [x] `while`/`for` producen `Unit`; `break value` en ellos es error.
- [x] Los rangos inclusivos y `by` están definidos.
- [x] Las etiquetas y `break`/`continue` etiquetados están definidos.
- [x] Las comprehensions son expresiones y no contienen `break`.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

