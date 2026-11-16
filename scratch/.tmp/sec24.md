<a id="sec-24-tuplas"></a>
## 24. Tuplas

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `()`, `(A, B)`, tuplas de hasta 12 |
| Palabras mágicas | `(`, `)`, `,` |
| Depende de | §2.6, §4 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec24_tuples.pengu` |

Una **tupla** agrupa valores de tipos posiblemente distintos con una longitud
fija. Es un producto cartesiano: `(A, B)` contiene un `A` y un `B`. No es una
colección homogénea; para eso se usa un array o un `Vec`.

### 24.1 Tipo y valores

```pengu
bind unit: Unit = ()
bind one = (42,)
bind pair = (42, "pengu")
bind triple = (1, 2.5, true)
```

Rust generado:

```rust
fn main() {
    let unit: () = ();
    let one = (42,);
    let pair = (42, "pengu");
    let triple = (1, 2.5, true);
    println!("{} {} {} {}", unit == (), one.0, pair.0, triple.2);
}
```

Reglas:

1. `()` es el único valor de `Unit`; no confundir con `none`.
2. `(x,)` es una tupla de un elemento; la coma es obligatoria.
3. `(x)` es agrupación, no una tupla.
4. `(a, b)` tiene tipo `(A, B)`; el orden importa.
5. Los elementos pueden ser de tipos distintos; no hay coerción entre ellos.
6. La longitud es parte del tipo: `(Int, Int)` y `(Int, Int, Int)` son distintos.

### 24.2 Acceso

```pengu
bind pair = (42, "pengu")
print(pair.0)
print(pair.1)
```

Rust generado:

```rust
fn main() {
    let pair = (42, "pengu");
    println!("{}", pair.0);
    println!("{}", pair.1);
}
```

Reglas:

1. `tuple.0`, `tuple.1`, … acceden por índice; el índice es un literal, no un
   valor de runtime.
2. No se puede escribir `tuple[i]` con `i` variable; para eso se usa un array.
3. `tuple.0` se puede asignar si la tupla es `morph` y el campo es mutable.
4. Acceder a un índice inexistente es error de compilación (`PGS-E2401`).

### 24.3 Destructuring

```pengu
bind (id, name) = (7, "pengu")
print(id)
print(name)
```

Rust generado:

```rust
fn main() {
    let (id, name) = (7, "pengu");
    println!("{}", id);
    println!("{}", name);
}
```

Reglas:

1. `bind (a, b) = expr` desestructura una tupla; `a` y `b` son bindings nuevos.
2. `morph (a, b) = expr` permite reasignar `a`/`b` después.
3. `_` ignora un elemento: `bind (id, _) = pair`.
4. La aridad debe coincidir; no hay “resto” en una tupla (`..` no aplica).
5. El destructuring de tuplas se usa también en `for`, `match` y parámetros
   (§30).

### 24.4 Retorno de tuplas

```pengu
make_pair = () -> (Int, Str)
    (1, "one")

bind (n, s) = make_pair()
print(n)
print(s)
```

Rust generado:

```rust
fn make_pair() -> (i32, &'static str) {
    (1, "one")
}

fn main() {
    let (n, s) = make_pair();
    println!("{}", n);
    println!("{}", s);
}
```

Las tuplas permiten devolver varios valores sin definir un `rune`. Si el
resultado tiene semántica propia o se usa en una API pública, se prefiere un
`rune` con nombres; una tupla es más frágil porque el orden es posicional.

### 24.5 Anidación

```pengu
bind nested = ((1, 2), (3, 4))
print(nested.0.1)
print(nested.1.0)
```

Rust generado:

```rust
fn main() {
    let nested = ((1, 2), (3, 4));
    println!("{}", nested.0.1);
    println!("{}", nested.1.0);
}
```

Una tupla puede contener tuplas, arrays, `Vec`, `Option`, etc. El tipo se infiere
de los elementos; no hay tuplas heterogéneas “dinámicas”.

### 24.6 Tuple structs (adelanto de §28)

Un **tuple struct** es un `rune` con campos posicionales:

```pengu
rune Point(Int, Int)
bind p = Point(1, 2)
print(p.0)
```

Rust generado:

```rust
struct Point(i32, i32);

fn main() {
    let p = Point(1, 2);
    println!("{}", p.0);
}
```

A diferencia de una tupla, `Point` es un tipo nominal: `Point(1, 2)` no es
intercambiable con `(1, 2)`. §28 define la sintaxis completa y la visibilidad.

### 24.7 Traits en tuplas

Rust implementa automáticamente estos traits para tuplas hasta 12 elementos si
todos sus elementos los implementan:

| Trait | Requisito |
|---|---|
| `Clone` | todos los elementos `Clone` |
| `Copy` | todos los elementos `Copy` |
| `Debug` | todos los elementos `Debug` |
| `PartialEq`/`Eq` | todos los elementos correspondientes |
| `PartialOrd`/`Ord` | todos los elementos correspondientes |
| `Hash` | todos los elementos `Hash` |
| `Default` | todos los elementos `Default` |

Las tuplas de 13 o más elementos no implementan estos traits automáticamente; si
se necesitan, se usa un `rune`.

### 24.8 Coste y layout

Una tupla se layouta como sus campos en orden de declaración, con padding para
alinear cada campo. `size_of::<(u8, u32)>()` suele ser `8`, no `5`, por el
padding. El orden de drop es de izquierda a derecha (§21).

### 24.9 Ejemplo completo

```pengu
min_max = (a: Int, b: Int) -> (Int, Int)
    if a <= b then (a, b) else (b, a)

bind (low, high) = min_max(7, 3)
print(low)
print(high)
```

Rust generado:

```rust
fn min_max(a: i32, b: i32) -> (i32, i32) {
    if a <= b { (a, b) } else { (b, a) }
}

fn main() {
    let (low, high) = min_max(7, 3);
    println!("{}", low);
    println!("{}", high);
}
```

### 24.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2401` | índice de tupla inexistente | usar un índice válido o un `rune` |
| `PGS-E2402` | aridad distinta en destructuring | ajustar el patrón |
| `PGS-E2403` | tupla de 13+ elementos con `Debug` | usar un `rune` |
| `PGS-E2404` | `tuple[i]` con índice variable | usar un array |
| `PGS-W2401` | tupla usada como API pública | preferir un `rune` con nombres |

### 24.11 Criterios de aceptación

- [x] `Unit`, tupla de un elemento y tuplas múltiples están diferenciadas.
- [x] Acceso `.0` y destructuring están definidos.
- [x] Retorno de tuplas y anidación tienen ejemplo.
- [x] Los tuple structs se distinguen de las tuplas.
- [x] Los traits automáticos y el límite de 12 están documentados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

