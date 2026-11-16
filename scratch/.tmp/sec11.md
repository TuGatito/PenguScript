<a id="sec-11-operadores"></a>
## 11. Operadores

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | Operadores de Rust; `contains`, `as`, `?`, `.await` |
| Palabras mágicas | `and`, `or`, `not`, `is`, `isnt`, `in`, `as`, `awaken` |
| Depende de | §8, §9, §10 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec11_operators.pengu` |

Los operadores de PenguScript son los de Rust, con dos concesiones a
MoonScript: `and`/`or`/`not` en lugar de `&&`/`||`/`!` para lógica, e
`is`/`isnt` como alias legibles de `==`/`!=`. No hay sobrecarga definida por el
usuario en esta sección; §40 explica cómo un `ritual` implementa los traits de
operador.

### 11.1 Tabla de precedencia

De mayor a menor. Todos los operadores de un mismo nivel asocian a la izquierda
salvo los indicados.

| Nivel | Operadores | Asociatividad | Produce |
|---|---|---|---|
| 1 | `.` campo/método, `()` llamada, `[]` índice, `?` postfix | izquierda | según el operando |
| 2 | `-` `+` `!` `*` `&` `&mut` `awaken` (prefijos) | derecha | según el operando |
| 3 | `as` | izquierda | tipo destino |
| 4 | `*` `/` `%` | izquierda | numérico |
| 5 | `+` `-` | izquierda | numérico o string |
| 6 | `<<` `>>` | izquierda | entero |
| 7 | `&` | izquierda | entero o `Bool` |
| 8 | `^` | izquierda | entero o `Bool` |
| 9 | `\|` | izquierda | entero o `Bool` |
| 10 | `..` `..=` | no asociativo | rango |
| 11 | `==` `!=` `<` `<=` `>` `>=` `is` `isnt` `in` | no asociativo | `Bool` |
| 12 | `not` (prefijo) | derecha | `Bool` |
| 13 | `and` | izquierda, cortocircuito | `Bool` |
| 14 | `or` | izquierda, cortocircuito | `Bool` |
| 15 | `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` | no asociativo; sentencia | `Unit` |

Consecuencias que conviene memorizar:

- `2 + 3 * 4` es `2 + (3 * 4)`.
- `0..n + 1` es `0..(n + 1)`, porque `+` tiene más precedencia que `..`.
- `not a == b` es `not (a == b)`, porque `not` está por debajo de comparación.
- `a and b or c` es `(a and b) or c`.
- `x = y = z` no es válido: la asignación no es expresión y no asocia.
- `a < b < c` no es válido: las comparaciones no encadenan. Se escribe
  `a < b and b < c`.

### 11.2 Aritméticos

| Operador | Tipos | Rust | Notas |
|---|---|---|---|
| `+` | enteros, flotantes | `+` | también `String + &Str` |
| `-` | enteros, flotantes | `-` | binario y unario |
| `*` | enteros, flotantes | `*` | — |
| `/` | enteros, flotantes | `/` | división entera trunca hacia cero |
| `%` | enteros, flotantes | `%` | resto; signo del dividendo |
| `-` unario | enteros, flotantes | `-` | `-x` |

La aritmética entera panica al desbordar y al dividir por cero (§9.11). La
división entera trunca hacia cero: `-7 / 2 == -3`, `-7 % 2 == -1`. Para
aritmética modular explícita se usan `wrapping_*`; para saturación,
`saturating_*`; para detectar, `checked_*`.

`+` con strings solo existe como `String + &Str` (§10.4). `Str + Str` es error.

### 11.3 Comparación e igualdad

| Operador | Significado | Requisito |
|---|---|---|
| `==` | igualdad | `PartialEq` |
| `!=` | desigualdad | `PartialEq` |
| `<` `<=` `>` `>=` | orden | `PartialOrd` |
| `is` | alias de `==` | `PartialEq` |
| `isnt` | alias de `!=` | `PartialEq` |

`is` e `isnt` son **azúcar de igualdad**, no identidad de referencia. Dos
`String` con el mismo contenido son `is`; dos referencias al mismo valor también.
No hay `===` ni `!==`.

```pengu
bind same = "pengu" is "pengu"     -- true
bind different = 1 isnt 2          -- true
```

Rust generado:

```rust
let same = "pengu" == "pengu";
let different = 1 != 2;
```

Las comparaciones no encadenan. `a < b < c` es error de tipo
(`PGS-E9203`), porque `a < b` es `Bool` y `Bool < c` no existe.

### 11.4 Lógicos

| Operador | Tipos | Rust | Cortocircuito |
|---|---|---|---|
| `and` | `Bool` | `&&` | sí |
| `or` | `Bool` | `\|\|` | sí |
| `not` | `Bool` | `!` | — |
| `!` prefijo | `Bool` o entero | `!` | — |

`and` y `or` solo aceptan `Bool`; no hay truthiness. El lado derecho no se evalúa
si el izquierdo decide el resultado:

```pengu
bind ok = ready and side_effect()
bind fallback = ready or side_effect()
```

Rust generado:

```rust
let ok = ready && side_effect();
let fallback = ready || side_effect();
```

No se aceptan `&&` ni `||` como alias: la forma canónica es `and`/`or`. `!` sí
se acepta como negación lógica de `Bool` y como complemento bit a bit de enteros;
`not` es el nombre legible para `Bool`.

### 11.5 Bitwise

| Operador | Tipos | Rust | Notas |
|---|---|---|---|
| `&` | enteros, `Bool` | `&` | AND bit a bit |
| `\|` | enteros, `Bool` | `\|` | OR bit a bit |
| `^` | enteros, `Bool` | `^` | XOR bit a bit |
| `<<` | enteros | `<<` | panic si el shift es ≥ ancho |
| `>>` | enteros | `>>` | shift aritmético para signed |
| `!` prefijo | enteros | `!` | complemento a uno |

`&`, `|` y `^` sobre `Bool` **no** cortocircuitan; para lógica se usan
`and`/`or`. El shift con cantidad negativa es error de tipo; con cantidad mayor o
igual al ancho panica (`PGS-E9008`).

```pengu
bind flags = 0b1010 & 0b0110       -- 0b0010
bind mask = 0b0001 | 0b1000        -- 0b1001
bind toggle = 0b1010 ^ 0b0011      -- 0b1001
bind shift = 1 << 3                -- 8
```

### 11.6 Rangos

| Forma | Significado | Rust |
|---|---|---|
| `a..b` | `a` inclusive, `b` exclusivo | `a..b` |
| `a..=b` | ambos inclusive | `a..=b` |

`..` no asocia: `a..b..c` es error. `..` con `..=` mezclados también. Los rangos
se usan en `for`, en `in` y como valores de tipo `Range[T]`/`RangeInclusive[T]`
(§27).

```pengu
bind digits = 0..10
bind inclusive = 0..=9
bind has_five = 5 in 0..10
```

### 11.7 `in`

`x in collection` comprueba pertenencia y produce `Bool`.

| Colección | Rust |
|---|---|
| array, slice, `Vec[T]` | `collection.contains(&x)` |
| rango | `range.contains(&x)` |
| `HashMap` | `map.contains_key(&x)` |
| `HashSet` | `set.contains(&x)` |
| string | `s.contains(x)` (substring) |

`in` no itera; es una comprobación. Para recorrer se usa `for` (§14). La
pertenencia usa `PartialEq`; en mapas y sets usa `Eq`/`Hash`.

```pengu
bind present = 3 in [1, 2, 3]
bind inside = 'p' in "pengu"
```

Rust generado:

```rust
let present = [1, 2, 3].contains(&3);
let inside = "pengu".contains('p');
```

### 11.8 Referencia, deref y acceso

| Forma | Significado | Rust |
|---|---|---|
| `&expr` | préstamo compartido | `&expr` |
| `&mut expr` | préstamo mutable | `&mut expr` |
| `*expr` | deref | `*expr` |
| `expr.field` | campo | `expr.field` |
| `expr.method(args)` | método | `expr.method(args)` |
| `expr[index]` | índice | `expr[index]` |
| `expr(args)` | llamada | `expr(args)` |
| `expr?` | propagación | `expr?` |
| `awaken expr` | await | `expr.await` |

`&`/`&mut` y `*` se desarrollan en §17–§19. `?` se desarrolla en §48. `awaken`
se desarrolla en §50. Aquí solo se fija su precedencia.

`?` es postfix y se aplica a `?T`/`!T`; no es el operador ternario de C. No hay
`a ? b : c`; para eso se usa `if`.

### 11.9 Casts con `as`

`as` convierte explícitamente entre tipos numéricos y entre `Char` y enteros
(§9.13). No hay casts implícitos ni casts entre strings y números; para eso se
usa `parse`/`to_string` (§10.8).

```pengu
bind small = 300 as U8          -- 44
bind code = 'A' as U32          -- 65
bind rounded = 3.9 as Int       -- 3
```

`as` tiene más precedencia que `*` y menos que los prefijos. `-1 as U8` es
`(-1) as u8`; el resultado es `255`.

### 11.10 Asignación y compuestos

La asignación es una **sentencia**, no una expresión:

| Forma | Rust | Notas |
|---|---|---|
| `x = expr` | `x = expr` | requiere `morph` |
| `x += expr` | `x += expr` | equivalente a `x = x + expr` |
| `x -= expr` | `x -= expr` | — |
| `x *= expr` | `x *= expr` | — |
| `x /= expr` | `x /= expr` | — |
| `x %= expr` | `x %= expr` | — |
| `x &= expr` | `x &= expr` | bitwise |
| `x \|= expr` | `x \|= expr` | bitwise |
| `x ^= expr` | `x ^= expr` | bitwise |
| `x <<= expr` | `x <<= expr` | — |
| `x >>= expr` | `x >>= expr` | — |

No hay `++` ni `--`. La asignación compuesta evalúa el lugar una sola vez y
respeta las reglas de préstamo: si `x` está prestado, `x += 1` es error hasta que
el préstamo termine (§17).

```pengu
morph total = 0
total += 10
total *= 2
```

### 11.11 Ejemplo completo

```pengu
grimoire
    bind a = 2 + 3 * 4
    bind b = (2 + 3) * 4
    bind c = 1 << 3
    bind d = 0b1010 & 0b0110
    bind e = not false and true
    bind f = 2 in [1, 2, 3]
    bind g = 3.9 as Int

    print(a)
    print(b)
    print(c)
    print(d)
    print(e)
    print(f)
    print(g)
```

Rust generado:

```rust
fn main() {
    let a = 2 + 3 * 4;
    let b = (2 + 3) * 4;
    let c = 1 << 3;
    let d = 0b1010 & 0b0110;
    let e = !false && true;
    let f = [1, 2, 3].contains(&2);
    let g = 3.9 as i32;

    println!("{}", a);
    println!("{}", b);
    println!("{}", c);
    println!("{}", d);
    println!("{}", e);
    println!("{}", f);
    println!("{}", g);
}
```

La salida es `14`, `20`, `8`, `2`, `true`, `true`, `3`.

### 11.12 Sobrecarga

Los operadores de esta sección son los de los tipos primitivos. Un `rune` puede
implementar `Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Not`, `BitAnd`, `BitOr`,
`BitXor`, `Shl`, `Shr`, `PartialEq` y `PartialOrd` mediante `ritual` (§40). Esa
implementación no cambia la precedencia ni la asociatividad.

No se permite definir operadores nuevos ni cambiar la aridad. `a + b + c` siempre
se agrupa como `(a + b) + c`, aunque `+` esté sobrecargado.

### 11.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9201` | tipos incompatibles en operador | convertir explícitamente o implementar el trait |
| `PGS-E9202` | operador no definido para el tipo | usar otro operador o implementar §40 |
| `PGS-E9203` | comparación encadenada | separar con `and` |
| `PGS-E9204` | asignación usada como expresión | convertirla en sentencia |
| `PGS-E9205` | `&&` o `||` usados | usar `and`/`or` |
| `PGS-E9206` | `++`/`--` | usar `+= 1`/`-= 1` |
| `PGS-E9207` | shift negativo o demasiado grande | comprobar el valor o usar `checked_shl` |
| `PGS-E9208` | rango mal formado | usar `a..b` o `a..=b`, sin encadenar |
| `PGS-E9209` | `in` sobre un tipo sin pertenencia | usar un iterador o `contains` explícito |
| `PGS-E9210` | `?` fuera de función que devuelve `?T`/`!T` | cambiar el retorno o usar `match` |

### 11.14 Criterios de aceptación

- [x] La tabla de precedencia cubre todos los operadores y su asociatividad.
- [x] Los operadores aritméticos, lógicos, bitwise y de comparación están
      definidos.
- [x] `and`/`or` cortocircuitan y solo aceptan `Bool`.
- [x] `is`/`isnt` son alias de igualdad, no identidad.
- [x] La asignación es sentencia y no asocia.
- [x] `in`, `as`, `?` y `awaken` tienen precedencia y semántica inicial.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

