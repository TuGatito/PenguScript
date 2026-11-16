<a id="sec-27-rangos"></a>
## 27. Rangos e indexación

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `Range<T>`, `RangeInclusive<T>`, `RangeFrom`, `RangeTo`, `..` |
| Palabras mágicas | `..`, `..=` |
| Depende de | §22–§26 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec27_ranges.pengu` |

Un **rango** representa un intervalo de valores. No es una colección: es un
valor de primera clase que se puede iterar, usar como índice de slice, comparar
o pasar a una función. Hay rangos exhaustivos (`a..b`, `a..=b`) y abiertos
(`a..`, `..b`, `..=b`, `..`).

### 27.1 Formas

| Forma | Tipo Rust | Incluye |
|---|---|---|
| `a..b` | `Range<T>` | `a <= x < b` |
| `a..=b` | `RangeInclusive<T>` | `a <= x <= b` |
| `a..` | `RangeFrom<T>` | `x >= a` |
| `..b` | `RangeTo<T>` | `x < b` |
| `..=b` | `RangeToInclusive<T>` | `x <= b` |
| `..` | `RangeFull` | todo |

```pengu
bind exclusive = 1..5
bind inclusive = 1..=5
bind from = 3..
bind to = ..3
bind values = [10, 20, 30]
bind all = &values[..]

print(exclusive.contains(&3))
print(inclusive.contains(&5))
print(from.contains(&4))
print(to.contains(&2))
print(all.len())
```

Rust generado:

```rust
fn main() {
    let exclusive = 1..5;
    let inclusive = 1..=5;
    let from = 3..;
    let to = ..3;
    let values = [10, 20, 30];
    let all = &values[..];

    println!("{}", exclusive.contains(&3));
    println!("{}", inclusive.contains(&5));
    println!("{}", from.contains(&4));
    println!("{}", to.contains(&2));
    println!("{}", all.len());
}
```

`RangeFull` (`..`) se usa como índice (`&values[..]`), no como valor con
`contains`; para comprobar pertenencia se usa un rango concreto.

### 27.2 Rangos como iteradores

```pengu
morph total = 0
for i in 0..5
    total += i
print(total)

for i in (0..6).step_by(2)
    print(i)

for i in (0..3).rev()
    print(i)
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    for i in 0..5 {
        total += i;
    }
    println!("{}", total);

    for i in (0..6).step_by(2) {
        println!("{}", i);
    }

    for i in (0..3).rev() {
        println!("{}", i);
    }
}
```

Reglas:

1. `a..b` e `a..=b` son iterables si `T` implementa `Step` (enteros, `char`).
2. `step_by(n)` requiere `n > 0`; si `n == 0`, panic.
3. `rev()` requiere un iterador de doble extremo; los rangos lo son.
4. `for i in 0..n` no incluye `n`; `0..=n` sí.
5. Un rango vacío (`5..5`, `5..=4`) no produce elementos; no es un error.

### 27.3 Rangos como índices

```pengu
bind values = [10, 20, 30, 40]
bind middle = &values[1..3]
print(middle.len())
print(values.get(1..9).is_none())
```

Rust generado:

```rust
fn main() {
    let values = [10, 20, 30, 40];
    let middle = &values[1..3];
    println!("{}", middle.len());
    println!("{}", values.get(1..9).is_none());
}
```

Reglas:

1. `&slice[a..b]` y `&slice[a..=b]` producen `&[T]`; con `mut`, `&mut [T]`.
2. El rango debe estar en bounds y en orden; si no, panic (`PGS-R2701`).
3. `get(a..b)` devuelve `?&[T]` y no hace panic; es la forma segura para rangos
   calculados.
4. `get_mut(a..b)` devuelve `?&mut [T]`.
5. `..` como índice significa el slice completo: `&values[..]`.

### 27.4 Rangos en patterns

```pengu
classify = (n: Int) -> Str
    match n
        0..=9 then "digit"
        10..=99 then "two digits"
        _ then "many"

print(classify(7))
print(classify(42))
```

Rust generado:

```rust
fn classify(n: i32) -> &'static str {
    match n {
        0..=9 => "digit",
        10..=99 => "two digits",
        _ => "many",
    }
}

fn main() {
    println!("{}", classify(7));
    println!("{}", classify(42));
}
```

En un pattern, `a..=b` es inclusivo y `a..b` exclusivo; `..` ignora el resto de
los campos de un `rune`/tupla. Los rangos de patterns deben ser exhaustivos o
tener un caso `_`.

### 27.5 Rangos indentados

La forma indentada es opcional y equivalente:

```pengu
bind r = 1..
    10

for i in r
    print(i)
```

Rust generado:

```rust
fn main() {
    let r = 1..10;

    for i in r {
        println!("{}", i);
    }
}
```

Reglas:

1. El operador `..`/`..=` queda al final de la línea; el endpoint va en la línea
   siguiente, indentado un nivel.
2. El cierre no lleva delimitador; el rango termina en el endpoint.
3. `1..` con endpoint indentado es `1..10`; no confundir con `1..` abierto.
4. Para un rango abierto se escribe `1..` sin línea de endpoint.
5. La forma indentada no cambia el tipo ni la semántica.

### 27.6 `contains`, `split_at` y búsqueda

```pengu
bind r = 10..20
print(r.contains(&15))
print(r.contains(&20))

bind values = [1, 2, 3, 4, 5]
bind (left, right) = values.split_at(2)
print(left.len(), right.len())
```

Rust generado:

```rust
fn main() {
    let r = 10..20;
    println!("{}", r.contains(&15));
    println!("{}", r.contains(&20));

    let values = [1, 2, 3, 4, 5];
    let (left, right) = values.split_at(2);
    println!("{} {}", left.len(), right.len());
}
```

`r.contains(&20)` es `false` porque `10..20` es exclusivo. `split_at` no es un
rango, pero comparte la idea de partir una secuencia en dos mitades.

### 27.7 Rangos y préstamos

Un rango de índices no presta nada por sí mismo; el préstamo ocurre al indexar:

```pengu
bind values = [1, 2, 3]
bind r = 1..3
bind part = &values[r]
print(part.len())
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3];
    let r = 1..3;
    let part = &values[r];
    println!("{}", part.len());
}
```

Mientras `part` vive, `values` no puede modificarse. El rango `r` es `Copy` si
`T: Copy`; no retiene el préstamo.

### 27.8 Ejemplo completo

```pengu
bind values = [10, 20, 30, 40, 50]
bind window = &values[1..4]
print(window.len())

morph total = 0
for value in window
    total += value
print(total)

for i in 0..3
    print(i)
```

Rust generado:

```rust
fn main() {
    let values = [10, 20, 30, 40, 50];
    let window = &values[1..4];
    println!("{}", window.len());

    let mut total = 0;
    for value in window {
        total += value;
    }
    println!("{}", total);

    for i in 0..3 {
        println!("{}", i);
    }
}
```

### 27.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2701` | rango invertido | corregir `a..b` |
| `PGS-E2702` | rango fuera de bounds en índice | usar `get` o comprobar `len` |
| `PGS-E2703` | `step_by(0)` | usar un paso positivo |
| `PGS-E2704` | rango no iterable | usar un tipo `Step` o un iterador |
| `PGS-E2705` | pattern de rango no exhaustivo | añadir `_` |
| `PGS-W2701` | índice con rango calculado sin comprobar | usar `get` |
| `PGS-W2702` | `..` en una API pública | acotar el rango |

### 27.10 Criterios de aceptación

- [x] Las seis formas de rango están diferenciadas.
- [x] Rangos como iteradores, índices y patterns están cubiertos.
- [x] La forma indentada está definida y ejemplificada.
- [x] `contains`, `split_at` y préstamos están explicados.
- [x] Los diagnósticos incluyen rangos invertidos y fuera de bounds.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

