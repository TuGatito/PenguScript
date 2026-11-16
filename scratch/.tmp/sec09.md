<a id="sec-09-primitivos"></a>
## 9. Tipos primitivos

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | `()`, `!`, `bool`, enteros, `f32`, `f64`, `char`, `str` |
| Palabras mágicas | — |
| Depende de | §4, §10 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec09_primitives.pengu` |

PenguScript no inventa una representación numérica: usa exactamente los tipos
primitivos de Rust y les da nombres legibles. La regla de oro es **no ocultar el
ancho**. `Int` y `Float` son cómodos para el código diario; los tipos con ancho
explícito se usan cuando el tamaño importa (ABI, archivos, protocolos, FFI).

### 9.1 Unit y Never

| PenguScript | Rust | Valores | Uso |
|---|---|---|---|
| `Unit` | `()` | uno: `()` | funciones y bloques sin valor |
| `Never` | `!` | ninguno | divergencia: `panic`, `return`, `break` |

`Unit` es el tipo de las funciones que no devuelven nada, de `while`/`for` y de
un bloque cuya última línea es una sentencia. `Never` es el tipo de las
expresiones que no terminan normalmente; se coacciona a cualquier tipo (§8).

```pengu
noop = () -> Unit
    ()

fail = (message: &Str) -> Never
    panic(message)
```

Rust generado:

```rust
fn noop() -> () {
    ()
}

fn fail(message: &str) -> ! {
    panic!("{}", message)
}
```

`Never` no se puede construir con un valor. Un `match` sin brazos, un `loop` sin
`break` o una llamada a `panic` producen `Never`.

### 9.2 Booleanos

`Bool` tiene exactamente dos valores: `true` y `false`. No hay truthiness: `0`,
`""`, `none` y los punteros nulos **no** son `Bool` (§12).

```pengu
bind enabled: Bool = true
bind visible = enabled and not false
```

`Bool` ocupa un byte en Rust; su tamaño no se especifica en la spec, pero el
codegen usa `bool`. Las operaciones permitidas se detallan en §12.

### 9.3 Enteros con signo

| Tipo | Rust | Rango |
|---|---|---|
| `I8` | `i8` | −128 a 127 |
| `I16` | `i16` | −32 768 a 32 767 |
| `I32` | `i32` | −2 147 483 648 a 2 147 483 647 |
| `I64` | `i64` | −2⁶³ a 2⁶³ − 1 |
| `I128` | `i128` | −2¹²⁷ a 2¹²⁷ − 1 |
| `Isize` | `isize` | depende del ancho del puntero del target |

`Isize` es el tipo con signo del tamaño de un puntero. No se garantiza que sea
de 64 bits: en un target de 32 bits es de 32 bits. Para índices se prefiere
`Usize`; para valores de dominio se prefieren tipos de ancho fijo.

### 9.4 Enteros sin signo

| Tipo | Rust | Rango |
|---|---|---|
| `U8` | `u8` | 0 a 255 |
| `U16` | `u16` | 0 a 65 535 |
| `U32` | `u32` | 0 a 4 294 967 295 |
| `U64` | `u64` | 0 a 2⁶⁴ − 1 |
| `U128` | `u128` | 0 a 2¹²⁸ − 1 |
| `Usize` | `usize` | depende del ancho del puntero del target |

`Usize` es el tipo de índices y longitudes de Rust. Un `Int` **no** se convierte
implícitamente en `Usize`: para indexar se usa `Usize` o una conversión explícita
(§9.13).

### 9.5 Alias cómodos: `Int`, `UInt`, `Float`

| Alias | Tipo real | Cuándo usarlo |
|---|---|---|
| `Int` | `I32` | enteros corrientes, contadores, valores pequeños |
| `UInt` | `U32` | cantidades no negativas corrientes |
| `Float` | `F64` | cálculo en coma flotante de doble precisión |

Los alias son **transparentes**: `Int` y `I32` son el mismo tipo. La anotación
`bind x: Int` genera `let x: i32`. La ventaja de `Int` es la legibilidad; la
ventaja de `I8`/`U64` es la precisión del contrato.

Regla: si un valor cruza una frontera de ABI, se serializa o se pasa a Rust, se
usa el tipo de ancho explícito. `Int` no promete 32 bits en una ABI; solo es un
alias de `I32` dentro del lenguaje.

### 9.6 Flotantes

| Tipo | Rust | Precisión |
|---|---|---|
| `F32` | `f32` | IEEE 754 binario32 |
| `F64` | `f64` | IEEE 754 binario64 |

`Float` es alias de `F64`. Los flotantes siguen IEEE 754: `NaN` no es igual a sí
mismo, `0.0` y `-0.0` se comparan iguales, y `inf`/`-inf` son valores válidos.
No se usa `==` para comparar flotantes con tolerancia; para eso se define una
función de épsilon en la biblioteca.

No hay `f16`, `f128` ni `Decimal` en el núcleo. Esos tipos, si existen, vienen de
un `tome` y se documentan en §26.

### 9.7 `Char`

`Char` es un **escalar Unicode** válido: un número en `0..=0x10FFFF` que no sea
un surrogate (`0xD800..=0xDFFF`). Ocupa 4 bytes en Rust.

```pengu
bind penguin: Char = '🐧'
bind newline: Char = '\n'
bind letter: U8 = b'P'
```

- Las comillas simples delimitan un `Char`: `'a'`, `'\n'`, `'\u{1F427}'`.
- `b'P'` es un **byte** (`U8`), no un `Char`.
- Un literal con más de un escalar es error (`PGS-E9004`).
- `Char` no es un string de longitud uno; para eso se usa `&Str`.

### 9.8 `Str`

`Str` es el tipo de los strings UTF-8 **no sizeados**. En la práctica aparece
siempre detrás de una referencia o dentro de un contenedor:

| Forma | Rust | Dueño |
|---|---|---|
| `&Str` | `&str` | no; préstamo |
| `String` | `String` | sí |
| `Cow[Str]` | `Cow<'_, str>` | a veces |

No se puede declarar un `bind x: Str = ...` por valor: `Str` no tiene tamaño
conocido y el compilador lo rechaza (`PGS-E9005`). Se usa `&Str`, `String` o
`Cow[Str]`. §10 cubre literales, métodos y conversiones.

### 9.9 Literales y sufijos

| Forma | Ejemplos | Tipo por defecto |
|---|---|---|
| Entero decimal | `0`, `42`, `1_000_000` | `Int` (`I32`) |
| Entero hexadecimal | `0xFF`, `0xdead_beef` | `Int` |
| Entero octal | `0o755` | `Int` |
| Entero binario | `0b1010_0101` | `Int` |
| Entero con sufijo | `42_i32`, `255_u8`, `1_000_usize` | el del sufijo |
| Flotante | `1.0`, `3.141_592`, `1.5e-3` | `Float` (`F64`) |
| Flotante con sufijo | `1.0_f32`, `2.5_f64` | el del sufijo |
| Booleano | `true`, `false` | `Bool` |
| Carácter | `'a'`, `'\n'`, `'🐧'` | `Char` |
| Byte | `b'a'`, `b'\n'` | `U8` |
| String | `"pengu"`, `"hola #{name}"` | `&Str` |

Reglas:

1. El sufijo es obligatorio para un ancho distinto del alias por defecto. `42_u8`
   es un `U8`; `42` es un `Int`.
2. El sufijo debe ser un tipo entero o flotante conocido (`i8`…`u128`, `isize`,
   `usize`, `f32`, `f64`). Un sufijo incompatible es error (`PGS-E9002`).
3. Los guiones bajos son separadores visuales; no cambian el valor. No pueden
   aparecer al inicio ni al final, ni duplicarse (`PGS-E9003`).
4. Un literal entero fuera del rango de su tipo es error de compilación
   (`PGS-E9001`).
5. No hay literales octales con signo ni literales binarios con prefijo `0B`.
6. El signo `-` es un operador unario, no parte del literal. `-128_i8` es válido;
   `128_i8` no lo es.

```pengu
bind decimal = 42
bind hex = 0x2A
bind octal = 0o52
bind binary = 0b10_1010
bind small: U8 = 42_u8
bind ratio: F32 = 1.5_f32
bind penguin: Char = '🐧'
bind flag: Bool = true
```

### 9.10 Inferencia y defaults

La inferencia es local y bidireccional (§4.5). Para literales numéricos:

1. Si hay una anotación o un contexto que fija el tipo, se usa ese tipo.
2. Si no hay contexto, un entero sin sufijo es `Int` (`I32`) y un flotante es
   `Float` (`F64`).
3. Un sufijo siempre gana sobre el default, pero no sobre una anotación
   incompatible.
4. No se elige un tipo menor por el valor. `bind x = 1` es `Int`, no `U8`.

```pengu
bind a = 1              -- Int
bind b: U8 = 1          -- U8
bind c = 1_u8           -- U8
bind d = 1.0            -- Float
bind e: F32 = 1.0       -- F32
```

Un literal no se convierte implícitamente a otro tipo:

```pengu
bind a: U8 = 1
bind b: U16 = a         -- error: U8 no es U16
bind c = a as U16       -- conversión explícita
```

### 9.11 Overflow, división y shifts

El codegen activa `overflow-checks = true` en todos los perfiles. Por eso las
operaciones aritméticas **panican** al desbordar, en debug y en release. Esto es
deliberado: un desbordamiento silencioso es un error de seguridad, no una
optimización.

| Operación | Comportamiento |
|---|---|
| `a + b`, `a - b`, `a * b` | panic si el resultado no cabe |
| `a / b` | panic si `b == 0` |
| `a % b` | panic si `b == 0` |
| `MIN / -1` | panic por overflow |
| `a << b`, `a >> b` | panic si `b >=` ancho de `a` |
| `a.abs()` | panic si `a` es el mínimo con signo |
| `a.pow(n)` | panic si el resultado no cabe |

Los literales constantes se comprueban en compilación. Una expresión que puede
desbordar en runtime se detecta con las operaciones explícitas de §9.12.

### 9.12 Operaciones checked, wrapping y saturating

Para cada tipo entero, la prelude expone los mismos métodos que Rust:

| Familia | Resultado | Uso |
|---|---|---|
| `checked_add`, `checked_sub`, `checked_mul`, `checked_div`, `checked_rem`, `checked_neg`, `checked_shl`, `checked_shr` | `?T` | el llamador decide |
| `wrapping_add`, `wrapping_sub`, `wrapping_mul`, `wrapping_div`, `wrapping_rem`, `wrapping_neg`, `wrapping_shl`, `wrapping_shr` | `T` | aritmética modular explícita |
| `saturating_add`, `saturating_sub`, `saturating_mul`, `saturating_div`, `saturating_pow` | `T` | se queda en el mínimo/máximo |
| `overflowing_add`, `overflowing_sub`, `overflowing_mul` | `(T, Bool)` | valor + indicador |

```pengu
bind a: U8 = 250
bind checked = a.checked_add(10)      -- none
bind wrapped = a.wrapping_add(10)     -- 4
bind saturated = a.saturating_add(10) -- 255
```

`checked_*` devuelve `?T`, no un `Bool` ni un valor centinela. Para usar el
resultado hay que desenvolverlo (§48):

```pengu
bind next = a.checked_add(1)?
```

El `?` solo es válido dentro de una función que devuelve `?T`/`!T` o en un
contexto que lo permita; §48 lo formaliza.

### 9.13 Casts numéricos con `as`

`as` es una conversión **explícita** y puede perder información. No hay casts
implícitos entre tipos numéricos.

| Origen | Destino | Semántica |
|---|---|---|
| entero | entero | trunca o extiende según Rust |
| entero | flotante | redondeo al más cercano representable |
| flotante | entero | satura a `MIN`/`MAX` y `NaN` a `0` (Rust) |
| `Char` | `U32` | valor escalar |
| `U8` | `Char` | byte ASCII; otros valores son error en runtime |
| `Bool` | entero | **no permitido** |
| `&Str` | `Str`/`String` | **no** con `as`; usar §10 |

```pengu
bind big: I64 = 300
bind small = big as U8        -- 44 (truncado)
bind back = small as I64      -- 44
bind code = 'A' as U32        -- 65
```

`as` no comprueba el rango. Para una conversión segura se usa `try_into()`:

```pengu
bind small = big.try_into()?  -- !U8
```

`try_into` devuelve `!T`; el `?` propaga el error. La conversión segura es la
forma recomendada cuando el valor viene de fuera del programa.

### 9.14 `NonZero`

Los tipos `NonZeroI8`…`NonZeroI128`, `NonZeroIsize`, `NonZeroU8`…`NonZeroU128` y
`NonZeroUsize` garantizan que el valor no es cero. Rust los usa para niche
optimization: `?NonZeroU32` ocupa el mismo espacio que `U32`.

```pengu
bind id = NonZeroU32.new(7)          -- ?NonZeroU32
bind raw = id.unwrap().get()         -- U32
bind checked = NonZeroU32.new(0)     -- none
```

Reglas:

1. `new` devuelve `?T`; no panica.
2. `get()` devuelve el entero subyacente.
3. `new_unchecked` solo existe dentro de `curse` (§52) y es responsabilidad del
   llamador.
4. `NonZero` no cambia el ancho; `NonZeroU8` sigue siendo un byte.

### 9.15 Ejemplo completo

```pengu
grimoire
    bind count: Int = 42
    bind mask: UInt = 0xFF
    bind ratio: Float = 1.5
    bind letter: Char = 'P'
    bind name: &Str = "pengu"

    bind total = count + 1
    bind wrapped = mask.wrapping_add(1)
    bind checked = count.checked_add(1)

    print(total)
    print(wrapped)
    print(checked.unwrap_or(0))
    print(ratio)
    print(letter)
    print(name)
```

Rust generado:

```rust
fn main() {
    let count: i32 = 42;
    let mask: u32 = 0xFF;
    let ratio: f64 = 1.5;
    let letter: char = 'P';
    let name: &str = "pengu";

    let total = count + 1;
    let wrapped = mask.wrapping_add(1);
    let checked = count.checked_add(1);

    println!("{}", total);
    println!("{}", wrapped);
    println!("{}", checked.unwrap_or(0));
    println!("{}", ratio);
    println!("{}", letter);
    println!("{}", name);
}
```

La salida es `43`, `0`, `43`, `1.5`, `P`, `pengu`.

### 9.16 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9001` | literal entero fuera de rango | usar un tipo más ancho o corregir el valor |
| `PGS-E9002` | sufijo incompatible con el tipo | cambiar sufijo o anotación |
| `PGS-E9003` | separador `_` mal colocado | quitar o recolocar el separador |
| `PGS-E9004` | literal `Char` con más de un escalar | usar un string o un solo carácter |
| `PGS-E9005` | `Str` por valor | usar `&Str`, `String` o `Cow[Str]` |
| `PGS-E9006` | overflow aritmético | usar `checked_*`, `wrapping_*` o `saturating_*` |
| `PGS-E9007` | división o resto por cero | comprobar el divisor o usar `checked_div` |
| `PGS-E9008` | shift mayor o igual que el ancho | comprobar el shift o usar `checked_shl` |
| `PGS-E9009` | cast `as` no permitido | usar una conversión explícita de §10/§32 |
| `PGS-E9010` | `NonZero.new(0)` usado como valor | desenvolver el `?` o comprobar `none` |
| `PGS-W9001` | cast que puede perder información | usar `try_into()` si el rango no es fijo |

### 9.17 Criterios de aceptación

- [x] Todos los tipos primitivos tienen mapeo a Rust y ejemplo.
- [x] `Int`, `UInt` y `Float` están definidos como alias, no como tipos nuevos.
- [x] La inferencia por defecto y los sufijos están especificados.
- [x] El comportamiento de overflow es explícito y seguro por defecto.
- [x] `Char`, `Str` y `String` se distinguen sin ambigüedad.
- [x] `NonZero` y los casts tienen reglas y diagnósticos.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

