<a id="sec-13-condicionales"></a>
## 13. Condicionales

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | `if`, `else if`, `else`, `!` |
| Palabras mágicas | `unless`, `then`, `elseif` |
| Depende de | §8, §12 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec13_conditionals.pengu` |

`if` es una expresión: produce el valor de la rama ejecutada. También se puede
usar como sentencia, en cuyo caso el valor se descarta. La condición debe ser
`Bool`; no hay truthiness (§12.6).

### 13.1 Forma multilínea

```pengu
if score >= 90
    "excelente"
elseif score >= 60
    "aprobado"
else
    "reprobado"
```

Reglas:

1. La condición va en la misma línea que `if`, sin `then`.
2. El cuerpo es un bloque indentado; no se usan llaves.
3. `elseif` encadena condiciones; puede haber cero o más.
4. `else` es la rama final; es opcional.
5. `elseif` y `else` deben estar al mismo nivel de indentación que el `if`.
6. Un `elseif` después de `else` es error (`PGS-E9404`).
7. No se usa `else if`; la forma canónica es `elseif` (`PGS-E9405`).

La forma anterior es equivalente a:

```pengu
bind category = if score >= 90
    "excelente"
elseif score >= 60
    "aprobado"
else
    "reprobado"
```

Rust generado:

```rust
let category = if score >= 90 {
    "excelente"
} else if score >= 60 {
    "aprobado"
} else {
    "reprobado"
};
```

### 13.2 Forma inline con `then`

Cuando cada rama cabe en una línea se usa `then`:

```pengu
bind parity = if n % 2 == 0 then "par" else "impar"
bind max = if a > b then a else b
```

Reglas:

1. `then` es obligatorio en la forma inline; sin él, el parser espera un bloque
   indentado (`PGS-E9403`).
2. La rama del `then` es una expresión; el `else` también.
3. `then` no se usa en la forma multilínea.
4. Una forma inline sin `else` produce `Unit` y solo se permite como sentencia:
   `if debug then print("debug")`.
5. No se mezcla `then` con un bloque indentado en la misma rama.

Rust generado para `parity`:

```rust
let parity = if n % 2 == 0 { "par" } else { "impar" };
```

### 13.3 `unless`

`unless cond` es azúcar de `if not cond`:

```pengu
unless logged_in
    print("inicia sesión")
```

Rust generado:

```rust
if !logged_in {
    println!("inicia sesión");
}
```

Reglas:

1. `unless` acepta `else`, pero no `elseif` (`PGS-E9406`). Para varias ramas se
   usa `if`.
2. `unless cond then expr` es la forma inline.
3. `unless` no invierte el tipo de las ramas; solo niega la condición.
4. `unless not cond` es válido pero se simplifica a `if cond` con un warning
   (`PGS-W9401`).

### 13.4 `if` como expresión

`if` produce un valor si todas las ramas que pueden ejecutarse producen un valor
compatible.

| Forma | Tipo | Ejemplo |
|---|---|---|
| `if c then a else b` | unificación de `a` y `b` | `if ok then 1 else 0` |
| `if c ... else ...` | unificación de ramas | `if c` … `else` … |
| `if c then a` | `Unit` | solo sentencia |
| `if c` … (sin `else`) | `Unit` | solo sentencia |
| rama `Never` | no participa | `if c then 1 else return 0` |

Reglas de unificación:

1. Si todas las ramas tienen el mismo tipo `T`, el `if` tiene tipo `T`.
2. Una rama `Never` se coacciona a `T`; no obliga a unificar con las demás.
3. Si una rama es `Unit` y otra `T ≠ Unit`, el `if` es error (`PGS-E9402`),
   salvo que el contexto exija `Unit`.
4. Sin `else`, el tipo es `Unit`; usar el `if` como valor es error
   (`PGS-E9408`).
5. Los valores de las ramas no se mezclan: solo se evalúa una.

```pengu
bind label = if count == 0
    "vacío"
else
    "con elementos"

bind next = if index + 1 < length then index + 1 else return index
```

Rust generado:

```rust
let label = if count == 0 {
    "vacío"
} else {
    "con elementos"
};

let next = if index + 1 < length {
    index + 1
} else {
    return index;
};
```

### 13.5 `if` como sentencia

Un `if` en posición de sentencia descarta su valor:

```pengu
if debug
    print("modo debug")

if cache_hit
    use_cache()
else
    recompute()
```

No es necesario `then` en la forma multilínea. Si la rama produce un valor no
`Unit`, el compilador emite un warning (`PGS-W9402`) y el codegen descarta el
valor; no se convierte en una expresión.

### 13.6 Anidamiento y `else` colgante

La indentación resuelve el `else` colgante: un `else` pertenece al `if` más
cercano que esté abierto en el mismo nivel.

```pengu
if outer
    if inner
        print("ambos")
    else
        print("solo outer")
```

El `else` pertenece al `if inner`. Para que pertenezca a `outer`, se indenta el
`if inner` dentro de un `do` o se reestructura el código. No hay ambigüedad de
parser porque el `else` se alinea con su `if`.

### 13.7 `if` y `match`

`if` sirve para condiciones booleanas; `match` para elegir por forma o valor
(§30). Para comprobar una `Option` sin desenvolverla se puede usar `match`:

```pengu
match value
    when some(x)
        print(x)
    when none
        print("sin valor")
```

La forma abreviada de Rust `if let` se especifica en §30 como una forma de
`match`; en Fase 2 se usa `match` o `is_some()`/`is_none()`.

### 13.8 Ejemplo completo

```pengu
grimoire
    bind score = 75
    bind category = if score >= 90
        "excelente"
    elseif score >= 60
        "aprobado"
    else
        "reprobado"

    bind parity = if score % 2 == 0 then "par" else "impar"
    bind max = if score > 100 then score else 100

    unless score < 0
        print("puntaje válido")

    print(category)
    print(parity)
    print(max)
```

Rust generado:

```rust
fn main() {
    let score = 75;
    let category = if score >= 90 {
        "excelente"
    } else if score >= 60 {
        "aprobado"
    } else {
        "reprobado"
    };

    let parity = if score % 2 == 0 { "par" } else { "impar" };
    let max = if score > 100 { score } else { 100 };

    if !(score < 0) {
        println!("puntaje válido");
    }

    println!("{}", category);
    println!("{}", parity);
    println!("{}", max);
}
```

La salida es `puntaje válido`, `aprobado`, `impar`, `100`.

### 13.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9401` | condición que no es `Bool` | usar una comparación |
| `PGS-E9402` | ramas de `if` con tipos incompatibles | convertir a un tipo común |
| `PGS-E9403` | forma inline sin `then` | añadir `then` o indentar el bloque |
| `PGS-E9404` | `elseif` después de `else` | mover `else` al final |
| `PGS-E9405` | `else if` usado | usar `elseif` |
| `PGS-E9406` | `elseif` dentro de `unless` | usar `if` |
| `PGS-E9407` | `if` sin cuerpo | añadir un bloque o `then` |
| `PGS-E9408` | `if` sin `else` usado como valor | añadir `else` o descartar el valor |
| `PGS-W9401` | `unless not` redundante | simplificar a `if` |
| `PGS-W9402` | valor de `if` descartado como sentencia | usar `bind _ =` o consumir el valor |

### 13.10 Criterios de aceptación

- [x] `if`/`elseif`/`else` y `unless` están definidos.
- [x] `then` inline y bloque indentado no se mezclan.
- [x] `if` sin `else` produce `Unit`; con `else`, las ramas unifican.
- [x] Una rama `Never` no participa en la unificación.
- [x] La condición solo acepta `Bool`.
- [x] El `else` colgante se resuelve por indentación.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

