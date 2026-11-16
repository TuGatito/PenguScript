---

<a id="sec-04"></a>
## 4. Tipos

### 4.1 Reglas

- El tipado es estático, fuerte y nominal.
- Las firmas de items son explícitas; las variables locales y las expresiones
  tienen inferencia local.
- No hay `null`, truthiness, coerción implícita ni conversiones automáticas.
- No hay tipos asociados, objetos de trait ni `impl Trait` en la superficie.
- Un tipo se escribe con `PascalCase`.

### 4.2 Primitivos

| Tipo | Representación | Literal |
|---|---|---|
| `Bool` | booleano | `true`, `false` |
| `Int` | entero con signo de 32 bits | `42` |
| `I8`, `I16`, `I32`, `I64`, `Isize` | enteros con signo | `42_i64` |
| `U8`, `U16`, `U32`, `U64`, `Usize` | enteros sin signo | `42_usize` |
| `Float` | 64 bits | `1.5` |
| `F32`, `F64` | flotantes | `1.5_f32` |
| `Char` | escalar Unicode | `'P'` |
| `String` | string owned | `String.from("pengu")` |
| `Str` | vista de string | `"pengu"` |
| `Unit` | ausencia de valor | `()` |
| `Never` | expresión que no retorna | `return`, `panic` |

`Int` es el entero por defecto; `Float` es el flotante por defecto. `I128` y
`U128` no están en el núcleo.

### 4.3 Tuplas

```pengu
bind pair = (1, "uno")
bind one = (1,)
bind empty = ()
```

`()` es `Unit`. `(T,)` es una tupla de un elemento. Los campos se leen con
`.0`, `.1`, etc.

### 4.4 Arrays y slices

```pengu
bind numbers: [Int; 3] = [1, 2, 3]
bind zeros = [0; 4]
bind view: &[Int] = &numbers
```

Un array `[T; N]` tiene tamaño fijo. Un slice `&[T]` es una vista con longitud
en tiempo de ejecución. `&mut [T]` permite modificarlo.

### 4.5 Referencias

`&T` y `&mut T` solo pueden aparecer:

- en parámetros de función;
- en variables locales;
- en el tipo de un binding local.

No pueden aparecer en campos de `rune`, variantes de `enchanting`, tipos de
retorno, alias que se guarden ni colecciones que se almacenen.

```pengu
length = (s: &Str) -> Usize
    s.len()
```

El compilador infiere cuánto vive la referencia. Si no puede, emite
`PGS-E1801` y sugiere mover el valor, usar `Rc[T]`/`Arc[T]` o reestructurar.

### 4.6 Strings

`Str` es una vista prestada de bytes UTF-8. `String` es la versión owned.

```pengu
bind literal: &Str = "pengu"
bind owned = String.from(literal)
bind joined = owned + "script"
```

No se indexa un string por entero. Para recorrer caracteres se usan
`chars()`, `bytes()` o `char_indices()`; para cortar, `get(a..b)` devuelve
`Option[&Str]` y falla si el rango no cae en un límite de carácter.

### 4.7 Colecciones

| Tipo | Uso |
|---|---|
| `Vec[T]` | secuencia dinámica |
| `Map[K, V]` | diccionario hash |
| `Set[T]` | conjunto hash |
| `[T; N]` | array fijo |
| `&[T]` | vista de secuencia |

`Map` y `Set` requieren claves `Eq + Hash`. No hay `BTreeMap` en la prelude;
se importa de `std.collections` si hace falta.

### 4.8 Opcionales y errores

```pengu
bind maybe: Option[Int] = some(3)
bind nothing: Option[Int] = none
bind result: Result[Int, String] = ok(3)
bind failure: Result[Int, String] = err("no")
```

`?T` es azúcar para `Option[T]`:

```pengu
bind maybe: ?Int = some(3)
```

`!T` no existe. Para errores se escribe `Result[T, E]` explícito.

### 4.9 Alias y newtypes

```pengu
essence Meters = Float

rune UserId
    value: UInt
```

Un alias no crea un tipo nuevo. Un `rune` de un solo campo sí: `UserId` no es
`UInt` y no se convierte solo.

### 4.10 Tipos genéricos

```pengu
rune Box[T]
    value: T

rune Pair[A, B]
    first: A
    second: B
```

Los parámetros van entre `[]`. Los bounds simples van en la cabecera:

```pengu
rune Sorted[T: Ord]
    items: Vec[T]
```

No hay `where`. No hay parámetros de tipo con valores (`const N`); los arrays
de tamaño fijo usan `[T; N]` con `N` literal o `sigil`.

### 4.11 Nunca y Unit

`Unit` es el tipo de `()`, de un `if` sin `else` y de un `while`.

`Never` es el tipo de una expresión que no produce un valor: `return`,
`break`, `continue` y `panic(...)`. `Never` se puede usar en cualquier rama.

### 4.12 Diagnósticos de tipos

| Código | Situación |
|---|---|
| `PGS-E3001` | Tipos incompatibles. |
| `PGS-E3002` | No se puede inferir el tipo. |
| `PGS-E3003` | El tipo no existe. |
| `PGS-E3004` | Genérico sin bound requerido. |
| `PGS-E3005` | Bound no satisfecho. |
| `PGS-E3006` | Referencia en posición prohibida. |
| `PGS-E3007` | `?T` usado con un tipo que no es `Option`. |
| `PGS-E3008` | `Result` con error no concreto. |
| `PGS-E3009` | Alias recursivo. |
| `PGS-E3010` | Newtype sin campo. |

[↑ Volver al índice](#indice)
