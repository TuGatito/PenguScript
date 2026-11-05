# Referencia del lenguaje PenguScript

PenguScript es un lenguaje pequeño y de tipado estático que compila a C. Esta
referencia documenta el lenguaje tal como lo implementa `psc` 0.31.0: cada
construcción, su semántica y el C al que se reduce.

Es el documento de *lenguaje* del conjunto de documentación:

| Documento | Responde |
| --- | --- |
| **LANGUAGE.es.md** (este archivo) | ¿Cómo escribo esta construcción y en qué se convierte en C? |
| [PENGUNIC.es.md](PENGUNIC.es.md) | ¿Cómo escribo PenguScript seguro, idiomático y rápido? |
| [STDLIB.es.md](STDLIB.es.md) | ¿Qué módulo estándar uso y dónde está su API? |

English: [LANGUAGE.md](LANGUAGE.md).

<!-- toc -->
- [0. Cómo leer esta referencia](#0-cómo-leer-esta-referencia)
- [1. Estructura léxica](#1-estructura-léxica)
  - [1.1 Archivos y módulos](#11-archivos-y-módulos)
  - [1.2 Comentarios](#12-comentarios)
  - [1.3 Identificadores y keywords](#13-identificadores-y-keywords)
  - [1.4 Disposición](#14-disposición)
  - [1.5 Literales](#15-literales)
- [2. Tipos](#2-tipos)
  - [2.1 Tipos primitivos y de runtime](#21-tipos-primitivos-y-de-runtime)
  - [2.2 Tipos compuestos](#22-tipos-compuestos)
  - [2.3 Valor frente a referencia](#23-valor-frente-a-referencia)
- [3. Variables y constantes](#3-variables-y-constantes)
  - [3.1 Declaraciones](#31-declaraciones)
  - [3.2 Asignación y `set`](#32-asignación-y-set)
  - [3.3 Scope y shadowing](#33-scope-y-shadowing)
  - [3.4 Garantías de seguridad y renuncias](#34-garantías-de-seguridad-y-renuncias)
- [4. Operadores](#4-operadores)
  - [4.1 Precedencia](#41-precedencia)
  - [4.2 Aritmética y bit a bit](#42-aritmética-y-bit-a-bit)
  - [4.3 Comparación, pertenencia y tests de palabras](#43-comparación-pertenencia-y-tests-de-palabras)
  - [4.4 Dirección, desreferencia, tamaño](#44-dirección-desreferencia-tamaño)
  - [4.5 Primitivas de carácter y byte](#45-primitivas-de-carácter-y-byte)
  - [4.6 Casts y conversiones](#46-casts-y-conversiones)
  - [4.7 `defined`, `size of` y valores de tiempo de compilación](#47-defined-size-of-y-valores-de-tiempo-de-compilación)
- [5. Control de flujo](#5-control-de-flujo)
  - [5.1 `if`, `unless` y bindings de `if`](#51-if-unless-y-bindings-de-if)
  - [5.2 `while`](#52-while)
  - [5.3 `for`](#53-for)
  - [5.4 `judge` — coincidencia de patrones](#54-judge-coincidencia-de-patrones)
  - [5.5 `break`, `continue`, `return`](#55-break-continue-return)
  - [5.6 Expresiones de bloque](#56-expresiones-de-bloque)
- [6. Funciones](#6-funciones)
  - [6.1 `weave`](#61-weave)
  - [6.2 Convenciones de llamada](#62-convenciones-de-llamada)
  - [6.3 Parámetros variádicos](#63-parámetros-variádicos)
  - [6.4 `declare`](#64-declare)
  - [6.5 Lambdas](#65-lambdas)
  - [6.6 Métodos `ritual`](#66-métodos-ritual)
  - [6.7 Punto de entrada](#67-punto-de-entrada)
- [7. Módulos e imports](#7-módulos-e-imports)
  - [7.1 Módulo = archivo](#71-módulo-archivo)
  - [7.2 `import`](#72-import)
  - [7.3 Estado a nivel de módulo](#73-estado-a-nivel-de-módulo)
- [8. Interop con C](#8-interop-con-c)
  - [8.1 `include`, `link`, `ldflag`, `insignia`](#81-include-link-ldflag-insignia)
  - [8.2 `declare`](#82-declare)
  - [8.3 `opaque`, `ref to`, `bytes of`](#83-opaque-ref-to-bytes-of)
  - [8.4 Archivos de declaración `.d.pengu`](#84-archivos-de-declaración-dpengu)
  - [8.5 `antiquus` — C incrustado](#85-antiquus-c-incrustado)
  - [8.6 `transmute`, `@packed`, `@align`](#86-transmute-packed-align)
- [9. Tipos compuestos](#9-tipos-compuestos)
  - [9.1 `rune` — structs](#91-rune-structs)
  - [9.2 `cyclus` — tipos recursivos](#92-cyclus-tipos-recursivos)
  - [9.3 `echo` — uniones](#93-echo-uniones)
  - [9.4 `omen` — enums y tipos suma](#94-omen-enums-y-tipos-suma)
  - [9.5 `seal`, `alias`, `opaque`](#95-seal-alias-opaque)
  - [9.6 `frozen`](#96-frozen)
  - [9.7 `derive`](#97-derive)
  - [9.8 Constructores `with:`](#98-constructores-with)
- [10. Métodos y conceptos](#10-métodos-y-conceptos)
  - [10.1 `enchanting` — métodos sobre un tipo](#101-enchanting-métodos-sobre-un-tipo)
  - [10.2 `@mutates`](#102-mutates)
  - [10.3 `concept` — contratos de tiempo de compilación](#103-concept-contratos-de-tiempo-de-compilación)
  - [10.4 `bind` — implementar un concepto](#104-bind-implementar-un-concepto)
  - [10.5 Resolución de métodos](#105-resolución-de-métodos)
  - [10.6 Conceptos integrados](#106-conceptos-integrados)
- [11. Genéricos](#11-genéricos)
  - [11.1 `shard`](#111-shard)
  - [11.2 Bounds](#112-bounds)
  - [11.3 `donum T`](#113-donum-t)
  - [11.4 Métodos genéricos y derivación](#114-métodos-genéricos-y-derivación)
  - [11.5 Límites](#115-límites)
- [12. Opcionales y errores](#12-opcionales-y-errores)
  - [12.1 `maybe T` y `result of T to E`](#121-maybe-t-y-result-of-t-to-e)
  - [12.2 Constructores](#122-constructores)
  - [12.3 Inspección y desenvolvimiento](#123-inspección-y-desenvolvimiento)
  - [12.4 `or else`, `or return`, `try`, `or:`](#124-or-else-or-return-try-or)
  - [12.5 `panic`](#125-panic)
  - [12.6 `defer` y `errdefer`](#126-defer-y-errdefer)
  - [12.7 Propiedad de los valores boxeados](#127-propiedad-de-los-valores-boxeados)
- [13. Memoria](#13-memoria)
  - [13.1 El modelo](#131-el-modelo)
  - [13.2 `banish`](#132-banish)
  - [13.3 `defer` y `errdefer`](#133-defer-y-errdefer)
  - [13.4 Lo que el compilador no hace](#134-lo-que-el-compilador-no-hace)
  - [13.5 Los valores boxeados se mueven](#135-los-valores-boxeados-se-mueven)
  - [13.6 Valores devueltos y parámetros](#136-valores-devueltos-y-parámetros)
  - [13.7 Depurar fugas](#137-depurar-fugas)
- [14. Atributos](#14-atributos)
  - [14.1 Hilos](#141-hilos)
  - [14.2 Corrutinas](#142-corrutinas)
- [15. Tests y herramientas](#15-tests-y-herramientas)
  - [15.1 Bloques `test`](#151-bloques-test)
  - [15.2 Comandos](#152-comandos)
  - [15.3 Opciones de build](#153-opciones-de-build)
  - [15.4 Manifiesto del proyecto](#154-manifiesto-del-proyecto)
  - [15.5 `psc doc`](#155-psc-doc)
- [16. Encadenamiento, pipes, tuplas y forma corta](#16-encadenamiento-pipes-tuplas-y-forma-corta)
  - [16.1 Cadenas de métodos](#161-cadenas-de-métodos)
  - [16.2 Pipes](#162-pipes)
  - [16.3 Tuplas y retornos múltiples](#163-tuplas-y-retornos-múltiples)
  - [16.4 Inicializadores abreviados de struct](#164-inicializadores-abreviados-de-struct)
- [17. Deprecación](#17-deprecación)
- [18. Diagnósticos](#18-diagnósticos)
- [19. Ejemplo completo](#19-ejemplo-completo)
- [Apéndice A. Keywords](#apéndice-a-keywords)
- [Apéndice B. Representaciones en runtime](#apéndice-b-representaciones-en-runtime)
- [Apéndice C. Esbozo de gramática](#apéndice-c-esbozo-de-gramática)
<!-- /toc -->

## 0. Cómo leer esta referencia

Cada construcción se documenta una sola vez, en el orden en que el compilador
la ve: léxico, tipos, declaraciones, expresiones, sentencias y, después, los
rasgos que necesitan su propia sección (genéricos, memoria, interop).

* Un bloque ```pengu es PenguScript válido. Los bloques marcados
  `pengu-fragment` son fragmentos: ilustran una forma y no pretenden compilar
  por sí solos.
* Un bloque ```c es el C *representativo* que produce `psc emit-c`, sin las
  marcas `#line` ni los `(void)` de variables sin usar. Los nombres de los
  helpers generados (`pengu_list_new`, `_pengu_clone_*`, …) son literales.
* Las listas de keywords, las correspondencias de tipos y los códigos de
  diagnóstico son exhaustivos; la prosa no lo es — [PENGUNIC.es.md](PENGUNIC.es.md)
  cubre *cómo usar* el lenguaje y [STDLIB.es.md](STDLIB.es.md) cubre la
  biblioteca estándar.
* Versión: `psc` 0.31.0. La versión de ABI que espera el C generado es 3.

## 1. Estructura léxica

### 1.1 Archivos y módulos

| Elemento | Regla |
| --- | --- |
| Archivo fuente | `*.pengu`, UTF-8, LF o CRLF |
| Archivo de declaración | `*.d.pengu` — solo `declare`/`include`/`link`/tipos; sin cuerpos por convención |
| Id de módulo | la ruta relativa a la raíz de fuentes, con `/` → `.`, sin extensión |
| Punto de entrada | `weave main into int` en el módulo que se compila como programa |
| Entrada de test | bloques declarados con `test` (§16) |

### 1.2 Comentarios

```pengu
# comentario de línea
## comentario de documentación (lo extraen `psc doc` y el LSP)

rune Point:
    x as int   # se admiten comentarios al final de línea
```

Una secuencia de líneas `##` al principio del archivo, antes de la primera
declaración, es el docstring del módulo. Una secuencia de líneas `##`
inmediatamente encima de una declaración documenta esa declaración. `psc doc`
renderiza ambas (§16.3).

### 1.3 Identificadores y keywords

Los identificadores empiezan por una letra o `_` y continúan con letras, dígitos
o `_`. `_` por sí solo es el binding de descarte (`for _, v in xs`). Los nombres
que chocan con palabras reservadas de C o con nombres de tipos de C se rechazan
(`E0035`); también `main` como constante (`E0040`).

El lenguaje tiene 71 palabras reservadas; el Apéndice A las enumera. No hay
keywords contextuales tipo `true`, salvo `over` (solo tiene sentido tras el
sujeto de un `judge`), `of` y `at`/`to` en sus posiciones de operador.

### 1.4 Disposición

Los bloques se delimitan por indentación. Un bloque son las sentencias
indentadas más que su cabecera; al desindentar, termina. El formateador
(`psc fmt`) usa cuatro espacios (`.pengufmt.toml`: `tab_size = 4`,
`insert_spaces = true`) y es la referencia de disposición.

```pengu
weave classify with n as int into string:
    if n < 0:
        return "negative"
    else if n == 0:
        return "zero"
    else:
        return "positive"
```

Una línea lógica puede continuar dentro de un `(`, `[` o `{` abiertos. Por lo
demás, una sentencia por línea; `,` separa elementos en listas de argumentos,
parámetros, campos y elementos — nunca termina una sentencia.

### 1.5 Literales

| Literal | Ejemplo | Tipo |
| --- | --- | --- |
| Entero decimal | `42`, `1_000_000` | `int` |
| Hexadecimal | `0xFF`, `0x1F_2E` | `int` |
| Binario | `0b1010` | `int` |
| Float | `3.5`, `1e-9` | `float` (32 bits) |
| Float de 64 bits | `3.5f64` no es un sufijo — anota: `var x as f64 is 3.5` | `f64` |
| Booleano | `true`, `false` | `bool` |
| Carácter | `'A'`, `'\n'` | `char` |
| String | `"hi"`, `"a\nb"` | `string` |
| String crudo | `r"a\nb"` (sin escapes) | `string` |
| String multilínea | `"""line 1\nline 2"""` | `string` |
| Interpolado | `"total: {total}"` | `string` |
| Lista | `[1, 2, 3]` | `list of int` |
| Mapa | `{"a": 1, "b": 2}` | `map of string to int` |
| Array fijo | `[3, 1, 2]` en un hueco `array of int with size 3` | `array of int with size 3` |
| Rango | `0 to 10` | rango entero — solo en `for`, `in` y comprensiones, no es un tipo escribible |
| Nulo | `null` | cualquier puntero, `opaque` o `maybe T` |

Escapes en strings normales: `\n \t \r \\ \" \' \0 \xNN \u{...}`. La
interpolación toma una expresión: `"{name} v{version}"`; `{{` y `}}` producen
llaves literales.

Un literal float es de precisión simple hasta que su tipo destino diga otra
cosa: en un hueco `f64` el mismo literal se emite como `double` de C con todos
sus dígitos.

## 2. Tipos

### 2.1 Tipos primitivos y de runtime

| PenguScript | Tipo C | Tamaño | Notas |
| --- | --- | --- | --- |
| `int` | `int32_t` | 4 | entero por defecto |
| `i64`, `long` | `int64_t` | 8 | |
| `i16`, `short` | `int16_t` | 2 | |
| `i8` | `int8_t` | 1 | |
| `u32`, `uint` | `uint32_t` | 4 | |
| `u64`, `ulong` | `uint64_t` | 8 | |
| `u16`, `ushort` | `uint16_t` | 2 | |
| `byte`, `u8` | `uint8_t` | 1 | bytes y 8 sin signo |
| `size_t`, `usize` | `size_t` | puntero | longitudes e índices |
| `isize` | `intptr_t` | puntero | con signo, tamaño de puntero |
| `float`, `f32` | `float` | 4 | IEEE-754 simple |
| `f64`, `double` | `double` | 8 | IEEE-754 doble |
| `char` | `char` | 1 | un byte |
| `bool` | `bool` | 1 | `true` / `false` |
| `void` | `void` | – | sin valor |
| `string` | `PenguString` | 16 | `{ char *data; int len; int32_t is_owned; }` |
| `opaque` | `void *` | puntero | handle de C, solo tras `ref to` |

Prefiere las formas cortas (`int`, `byte`, `size_t`, `float`, `f64`). Las formas
con ancho de C existen para que una firma copiada de una cabecera conserve su
ancho exacto y para que `psc bind` pueda emitirla tal cual.

Los tipos de runtime son structs de C normales (`build/include/pengu_runtime.h`):

```c
typedef struct { char *data; int len; int32_t is_owned; } PenguString;
typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;
typedef struct { bool is_present; void *value; } PenguMaybe;
```

`PenguString` guarda la longitud, así que puede contener bytes NUL;
`is_owned == 0` marca una vista prestada. `PenguList` guarda los elementos por
valor con un `elem_size` fijo y solo es dueño de su búfer de elementos.

### 2.2 Tipos compuestos

| Tipo | Escritura | Representación en C |
| --- | --- | --- |
| Lista | `list of T` | `PenguList` (vector de CC) |
| Mapa | `map of K to V` | `PenguMap` (mapa de CC) |
| Array fijo | `array of T with size N` | `T[N]`, anidado como `T[M][N]` |
| Slice | `slice of T` | `PenguSlice { void *data; int len; size_t elem_size; }` |
| Opcional | `maybe T` | caja etiquetada, payload en el heap |
| Resultado | `result of T to E` | caja etiquetada, payload en el heap |
| Puntero | `ref to T`, `ref to frozen T` | `T *` |
| Tupla | `(T, U)`, `(T, U, V)` | struct anónimo |
| Puntero a función | `weave with T into U` | `U (*)(T)` |
| Tipo de usuario | `rune`, `echo`, `omen`, `seal`, `alias` | struct / union / enum / envoltorio |

`string`, `list`, `map` y los valores boxeados `maybe`/`result` son *propiedad*
del que los tiene, salvo que una función devuelva una vista prestada (§14).
`slice`, los rangos, `ref to T`, las tuplas y los escalares son valores planos.

### 2.3 Valor frente a referencia

* `string`, `list`, `map`, un `rune` que contenga alguno de ellos, `maybe`,
  `result`: la asignación copia el valor, pero los strings y contenedores de
  dentro se comparten salvo que el lenguaje diga otra cosa — las funciones de
  limpieza del compilador asumen un solo dueño (§14.3).
* `slice of T` y `ref to T` son vistas que no poseen. Copiarlas nunca duplica
  el almacenamiento.
* `frozen T` es una cualificación de solo lectura; `ref to frozen T` es un
  puntero de solo lectura.

## 3. Variables y constantes

### 3.1 Declaraciones

Se aceptan ocho formas:

```pengu-fragment
var count as int is 0                 # tipado, mutable
let name as string is "Ada"           # tipado, inmutable
var total is 100                      # int inferido
let greeting is "Hello"               # string inferido
var buffer as array of byte with size 64 is array of byte with size 64

let (x, y) is point_value             # destructuring, inferido
var (id, label) as (int, string) is user_record
let (r, g, b, a) as Color is current_color

const MAX_USERS as int is 1024        # solo top level, en tiempo de compilación
const PI is 3.14159                   # float inferido

static var calls as int is 0          # dentro de un weave: persiste entre llamadas
```

Reglas:

* Un binding `var` es mutable; `let` no lo es (`E0006` al asignar).
* `var`/`let` están prohibidos en top level (`E0002`). El estado de nivel
  superior es `const`, o `static var` dentro de una función.
* `const` solo existe en top level (`E0001`) y debe ser una expresión de tiempo
  de compilación. Las constantes `list` y `map` se rechazan (`E0005`); usa
  `array of T`.
* `null` necesita tipo explícito: `const NIL as ref to int is null`.
* El destructuring funciona con runes (campos en orden de declaración), arrays
  fijos, slices y listas; cualquier otra cosa, o un número de bindings
  incorrecto, es `E0017`.

### 3.2 Asignación y `set`

La asignación es `set`; no existe `x = 1` a secas.

```pengu-fragment
set count is 42
set player.hp is 100
set self->hp is 80
set items at (i + 1) is new_item
set essence of ptr is 99            # *ptr = 99
set .x is 10                        # solo dentro de un constructor `with:`
```

Hay formas compuestas: `+= -= *= /= %= &= |= ^= <<= >>=`. `+=` sobre `string`
es `E0005`; compón strings con interpolación.

```pengu-fragment
set counter += 1
set flags |= 0x08
set text is "{text} suffix"
```

El destino debe ser mutable: asignar a un `let`, a un `const`, a un valor
`frozen` o a través de un `ref to frozen T` es `E0006`.

### 3.3 Scope y shadowing

Los scopes son bloques de indentación: cuerpos de weave, ramas de
`if`/`while`/`for`, constructores `with:`, bloques `or:` y expresiones `do:`.
La búsqueda es léxica y una declaración interna oculta a una externa.

A nivel de módulo, un nombre sin cualificar se resuelve primero en el módulo
actual, después en los módulos que este importa (transitivamente, en orden de
import) y nunca en un módulo ajeno. Un nombre cualificado sigue los alias
importados: `calling padre.hijo.fn` dentro de `padre` nombra `padre.hijo.fn`,
no una `fn` local de `padre`.

```pengu
weave main into int:
    let x is 1
    if x == 1:
        let x is "shadowed"      # otro x, el mismo nombre
        calling print with x
    return x                     # 1
```

`banish`, `defer` y `errdefer` solo son válidos dentro del cuerpo de una
función (`E0008`).

### 3.4 Garantías de seguridad y renuncias

Las comprobaciones de límites, de desbordamiento de enteros y de nulos están
activas por defecto. Se desactivan por build con `--release-unsafe` (perfil
release), nunca por sentencia. Consulta §16 para los perfiles de build y §14
para lo que sigue siendo manual incluso con las comprobaciones activas.

## 4. Operadores

### 4.1 Precedencia

De menor a mayor:

| Nivel | Operadores |
| --- | --- |
| 1 | `or else`, `or return`, `try`, `or:` |
| 2 | `or` |
| 3 | `and` |
| 4 | `not` |
| 5 | `is`, `is present`, `is not present`, `as`, `in`, `not in` |
| 6 | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| 7 | `&#124;` (or bit a bit) |
| 8 | `^` (xor bit a bit) |
| 9 | `&` (and bit a bit) |
| 10 | `<<`, `>>` |
| 11 | `+`, `-`, `+` para strings |
| 12 | `*`, `/`, `%` |
| 13 | unarios `-`, `~`, `not`, `sigil of`, `essence of`, `bytes of`, `size of`, `align of`, `transmute ... to`, `banish`, `some`, `ord`, `chr` |
| 14 | `.field`, `->field`, `at i`, `calling f with ...`, `(...)` |

`pipe` inicia un nuevo eslabón al principio de una línea de continuación
(§16.2); no es un operador infijo.

### 4.2 Aritmética y bit a bit

```pengu-fragment
var a as int is 7
var b as int is 2
var q as int is a / b        # 3, la división entera trunca hacia cero
var r as int is a % b        # 1
var f as float is 7.0 / 2.0  # 3.5
var m as int is a & 0x0F
var s as int is a << 2
```

`/` y `%` sobre enteros truncan; `%` con operando izquierdo negativo sigue a C
(el resto conserva el signo del dividendo). `%` sobre `float` es `E0005`. Usa
`std.fractio` para utilidades de coma flotante.

El desbordamiento entero se comprueba en debug y en release (aborta);
`--release-unsafe` desactiva la comprobación y deja el desbordamiento de C.

### 4.3 Comparación, pertenencia y tests de palabras

```pengu
weave classify with a as int, b as int, value as maybe int into string:
    if a == b and a < 10:
        return "small equal"
    if value is present:
        return "present"
    return "none"
```

`in` funciona con listas, arrays, slices, mapas (pertenencia de clave), strings
(substring) y rangos (`i in 0 to 10`). `is present` / `is not present` prueban un
`maybe`; `is` también prueba una variante de omen (`state is Ready`).

Los strings se comparan por contenido (`pengu_string_eq`); `==` entre dos
`list` compara elemento a elemento solo si el tipo de elemento tiene `Par`
(§12).

### 4.4 Dirección, desreferencia, tamaño

| Forma | Significado | C |
| --- | --- | --- |
| `sigil of x` | dirección de una variable/campo | `&x` |
| `essence of p` | desreferencia | `*p` |
| `p at i` | indexación de puntero/array | `p[i]` |
| `size of T` | tamaño en tiempo de compilación | `sizeof(T)` |
| `align of T` | alineación en tiempo de compilación | `_Alignof(T)` |
| `bytes of s` | vista de bytes de un string/array | `(uint8_t*)s.data` |

```pengu-fragment
var n as int is 5
var p as ref to int is sigil of n
set essence of p is 6
var raw as ref to frozen byte is bytes of "abc"
var dist as isize is p2 - p1     # distancia en elementos
```

`p++`, `p[i]` y `p + 1` no son PenguScript: usa `p at i` y `p + n` para
aritmética de punteros (escalada por elemento). La aritmética sobre
`ref to void` se rechaza.

### 4.5 Primitivas de carácter y byte

```pengu-fragment
var c as char is 'A'
var code as int is ord c        # 65
var back as char is chr 65      # 'A'
```

`ord` acepta `char`; `chr` acepta un entero entre 0 y 255.

### 4.6 Casts y conversiones

| Forma | Significado | Comprobación en runtime |
| --- | --- | --- |
| `x to T` | conversión numérica o nominal (estrecha en silencio) | no |
| `if v as T is n:` | estrecha un `maybe`/`result` y liga `n` | sí, test de presencia |
| `transmute x to T` | reinterpreta los bits | no, inseguro |

```pengu-fragment
var i as int is 65
var c as char is i to char
var f as float is 1 to float
var v as maybe int is some 3
if v as int is n:
    calling print with "{n}"
```

`as` solo es válido en una condición (`if`, `while`, guarda de `judge`), donde
estrecha el payload de un `maybe`/`result` y lo liga; no es un cast numérico
general. `to` convierte entre tipos numéricos (truncando: `300 to u8` es `44`) y
entre un `seal` y su representación. `transmute` está reservado para trucos de
layout en FFI y se cubre en §9.6.

### 4.7 `defined`, `size of` y valores de tiempo de compilación

`defined(NAME)` es verdadero cuando se pasó `-D NAME` o el nombre es un hecho
predefinido del entorno (`wasm`, `debug`, `main`). `size of`/`align of` se
pliegan en tiempo de compilación. Ambos sirven en `when` y en inicializadores
de `const`.

## 5. Control de flujo

### 5.1 `if`, `unless` y bindings de `if`

```pengu-fragment
if score >= 100:
    calling print with "winner"
else if score >= 60:
    calling print with "ok"
else:
    calling print with "keep going"

unless muted:
    calling play_sound with "beep"
```

La condición debe ser `bool` (`E0005`). Una rama puede llevar una sentencia en
la misma línea tras los dos puntos (`if x == 1: return 1`); declaraciones,
`defer` y `banish` no pueden.

Una condición `if` puede ligar el payload de un `maybe`:

```pengu-fragment
if u as User is user:
    calling print with user.name
else:
    calling print with "anonymous"
```

El nombre ligado queda en el scope de la rama `then` y se reduce a un único
test `pengu_maybe_is_present` más la extracción.

### 5.2 `while`

```pengu-fragment
var i as int is 0
while i < 10:
    calling tick with i
    set i is i + 1
```

Los bucles aceptan una etiqueta antes de la keyword (`outer: while ...`);
consulta §5.5.

### 5.3 `for`

```pengu-fragment
for i from 0 to 10:              # [0, 10), final exclusivo
    calling tick with i

for i from 10 to 0 step -1:      # descendente
    calling tick with i

for item in items:               # lista, array, slice, string, mapa
    calling handle with item

for i, item in indexed:          # índice + elemento
    calling handle with i

for _, v in values:              # descarta el índice
    calling handle with v
```

| Forma | Itera sobre | Tipo del elemento |
| --- | --- | --- |
| `for i from a to b` | rango entero `[a, b)` | `int` |
| `... step k` | rango con paso `k` (puede ser negativo) | `int` |
| `for x in list` | `list of T` | `T` |
| `for x in array` | `array of T with size N` | `T` |
| `for x in slice` | `slice of T` | `T` |
| `for ch in s` | `string` | `string` de un carácter |
| `for k in map` | claves de `map of K to V`, en orden de hash | `K` |

La forma con índice `for i, v in col` exige nombres distintos (`E0037`); `_`
descarta cualquiera de los dos bindings.

Las **comprensiones** construyen una lista a partir de una expresión:

```pengu-fragment
let squares as list of int is for x in nums then x * x
let evens as list of int is for x in nums when x % 2 == 0 then x
```

Las comprensiones aceptan solo la forma de elemento (sin binding de índice) y
se reducen a una statement-expression que asigna un `PenguList` y hace push de
cada valor.

```c
/* for i from 0 to 3 */
for (int32_t i = 0; i < 3; i++) { ... }

/* for item in xs: */
for (int _k = 0; _k < xs.len; _k++) {
    int32_t item = *(int32_t*)pengu_list_at(&xs, _k);
    ...
}
```

### 5.4 `judge` — coincidencia de patrones

```pengu-fragment
let desc as string is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
    else -> "unknown"
```

Sujetos: `omen`, `bool`, `int`, `string`, `char`.

| Patrón | Ejemplo |
| --- | --- |
| Variante desnuda | `when Ready ->` |
| Variante cualificada | `when Phase.Ready ->` |
| Nombre C completo | `when Phase_Ready ->` |
| Literal | `when 42 ->`, `when "admin" ->`, `when 'X' ->` |
| Alternativas | `when Ready &#124; Loading ->` |
| Binding de payload | `when Ok with value ->` |
| Guarda | `when Val with n if n > 0 ->` |
| Defecto | `else ->` |

La exhaustividad se exige para sujetos `omen` y `bool` (`E0044`); para `int`,
`string` y `char`, una coincidencia ausente produce el valor cero salvo que
haya un `else ->`. Los patrones con guarda no cuentan como cobertura.

**`judge ... over`** hace coincidir un rune cuyo discriminante es uno de sus
campos:

```pengu
rune Expr:
    kind as ExprKind
    value as int
    left as ref to Expr
    right as ref to Expr

omen ExprKind:
    Lit is 0
    Add is 1

weave eval with e as ref to Expr into int:
    return judge e over kind:
        when Lit with value -> value
        when Add with left, right ->
            (calling eval with left) + (calling eval with right)
```

`over` es una keyword blanda: `var over as int is 5` sigue compilando. La forma
`over` también admite payloads estrechados (`field as some`, `field as ok`,
`field as (a, b)`).

El codegen emite un `switch` de C cuando todas las ramas son constantes
enteras; si no, emite cadenas `if`/`else` con extracción de payload y
comprobación de guardas.

```c
switch (state.tag) {
  case Ready: return pengu_string_from_cstr("ready");
  case Loading: return pengu_string_from_cstr("loading");
  case Done: return pengu_string_from_cstr("done");
  default: return pengu_string_from_cstr("unknown");
}
```

### 5.5 `break`, `continue`, `return`

`break` y `continue` requieren un bucle que los contenga (`E0007`). `return`
debe coincidir con el tipo del `into` que lo envuelve (`E0020`); un `return`
desnudo solo es válido en un weave `void`.

Los bucles pueden etiquetarse para salir de más de uno:

```pengu-fragment
outer: for line in lines:
    for ch in line:
        if ch == ";":
            continue outer
        if ch == "}":
            break outer
```

Las etiquetas son locales a la función, únicas por función (`E0069`) y se
reducen a `goto _pengu_label_<name>_{continue,break}` conservando la limpieza
del bucle.

### 5.6 Expresiones de bloque

Una comprensión (`for x in xs then expr`), el condicional de una línea
(`if c then a else b`) y un **bloque indentado** en posición de valor son
valores. `do:` y un `if`/`unless` multilínea evalúan al valor de su última
expresión; las sentencias anteriores corren en el scope del bloque.

```pengu
weave main into int:
    let v as int is do:
        var a as int is 5
        a + 4
    let w as int is if v > 0:
        1
    else:
        0
    calling print with "{v} {w}"    # 9 1
    return 0
```

Los bloques bajan a sentencias-expresión de GNU (`__extension__(({ ... }))`),
así que el C generado necesita GCC o Clang, las toolchains soportadas.
`return`, `banish` y `defer` dentro del bloque conservan su significado. Un
bucle en posición de valor (`for x in xs then expr`) recoge el valor de cada
iteración en un nuevo `list of T`.

## 6. Funciones

### 6.1 `weave`

```pengu
weave greet with name as string, times as int is 1 into void:
    for i from 0 to times:
        calling print with "Hi {name}"

weave double with x as int into int:
    return x * 2
```

* `with` introduce los parámetros; `into`, el tipo de retorno. Un weave `void`
  puede omitir el valor de `return`.
* Los valores por defecto de los parámetros deben ser constantes de tiempo de
  compilación.
* Un cuerpo cuya última sentencia es una expresión la devuelve implícitamente.
* Las llamadas aceptan argumentos posicionales y nombrados:
  `calling greet with "Ada", times is 2`.
* La lista de argumentos tras `with` es voraz — pon paréntesis a una llamada
  usada dentro de una expresión mayor: `(calling get_count) > 0`.
* Los weaves pequeños (≤ 3 sentencias, sin bucles, sin `static`) se inlinean
  automáticamente; `inline weave ...` lo fuerza. El C recibe
  `static inline __attribute__((always_inline))`.

`psc emit-c` convierte cada weave en una función de C llamada `<módulo>_<nombre>`:

```c
int32_t d1_add(int32_t a, int32_t b) {
    return (a + b);
}
```

Un `string`, `list` o `map` devuelto se devuelve por valor; el llamado transfiere
la propiedad al llamador.

### 6.2 Convenciones de llamada

```pengu-fragment
calling greet with "Ada", 3        # función libre
calling spark.println with "hi"    # cualificada por módulo
calling player.heal with 25        # método sobre un valor
calling Player.new_hero with "Ada" # método ritual (estático), sobre el tipo
calling items.push with 4          # método integrado de contenedor
```

Los métodos integrados de contenedor (`list`: `push`, `pop`, `len`, `at`,
`clear`; `map`: `get`, `put`, `contains`, `remove`, `len`, `keys`, `values`) los
resuelve el compilador sin necesidad de un bloque `enchanting`.

### 6.3 Parámetros variádicos

`many T` está reservado en la gramática para weaves variádicos, pero ninguna
sintaxis de llamada lo satisface en 0.28.0: toda llamada se rechaza con
`E0005`. Mientras no se implemente, usa `slice of T` (o `list of T`):

```pengu
weave count_slice with xs as slice of int into int:
    return (xs.len to int)
```

`declare` no tiene forma `many` (`E0005`); allí se usa un `...` final para los
varargs crudos de C. Tampoco existe el spread en la llamada (`f(...xs)`).

### 6.4 `declare`

```pengu
declare pengu_print with s as string into void
declare strlen_c with s as ref to char into usize
declare printf with fmt as ref to frozen char, ... into int
```

`declare` liga una función externa de C; las llamadas se vuelven llamadas
directas de C. Los tipos deben coincidir exactamente con la cabecera. Un `...`
final son varargs crudos de C (válido solo en `declare`). Toda función externa
necesita un `declare`, o la llamada es `E0004`.

### 6.5 Lambdas

```pengu-fragment
let no_args as weave into int is lambda into 42
let double as weave with x as int into int is lambda x as int into x * 2
let add as weave with a as int, b as int into int is lambda a as int, b as int into a + b
```

Las lambdas son funciones estáticas de C (`_pengu_lambda_N`) **sin capturas**:
solo ven sus parámetros y las declaraciones de nivel de módulo. Los tipos de sus
parámetros son obligatorios; el tipo de retorno se infiere. El cuerpo de una
lambda es una frontera de función, así que `break`/`continue` no pueden apuntar
a un bucle del weave que la contiene.

### 6.6 Métodos `ritual`

Un `ritual` es una función asociada (estática) declarada dentro de `enchanting`
o de `bind`. No recibe `self` y se llama sobre el nombre del tipo:

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    weave ritual new with name as string into Player:
        return with name is name, hp is 100
```

Llamar a un ritual sobre una instancia, o a un método de instancia sobre el
nombre del tipo, es `E0034`; usar `self` dentro de un ritual es `E0033`.

### 6.7 Punto de entrada

La entrada del programa es `weave main into int` (o `into void`) en el módulo
de entrada. El compilador emite `pengu_main` y un `main` de C que llama a
`pengu_init(argc, argv)`, ejecuta `pengu_main`, vacía stdio y devuelve el
estado. El módulo de entrada ve `main` como `true` en las condiciones `when`;
los módulos importados lo ven como `false`.

## 7. Módulos e imports

### 7.1 Módulo = archivo

Un módulo es un archivo `.pengu`. Su id de módulo es su ruta bajo la raíz de
fuentes con `/` sustituido por `.` y sin extensión: `src/components/player.pengu`
es `components.player`. Los archivos de la biblioteca estándar son `std.*`.

### 7.2 `import`

```pengu-fragment
import std.spark                  # biblioteca estándar incluida
import std.scrolls as s           # alias
import components.player          # módulo del proyecto (src/components/player.pengu)
import utils                      # src/utils.pengu
```

| Regla | Comportamiento |
| --- | --- |
| Resolución | ruta con puntos → `src/<ruta>.pengu`, luego `<ruta>.d.pengu`, luego `__init__.pengu` |
| Orden | los módulos se comprueban y emiten en orden de dependencia (topológico) |
| Ciclos | `E0004`, con el ciclo impreso (`a -> b -> a`) |
| Duplicados | importar el mismo módulo dos veces es `E0004` |

### 7.3 Estado a nivel de módulo

`var` y `let` están prohibidos en top level (`E0002`). El estado persistente
tiene dos formas legales: `const` (valor de tiempo de compilación) y
`static var` dentro de un weave, que emite un `static` de C con inicialización
única protegida:

```pengu
weave next_id into int:
    static var counter as int is 0
    set counter += 1
    return counter
```

El estado `static` es por proceso y nunca se libera; prefiere pasar el estado
explícitamente.

## 8. Interop con C

### 8.1 `include`, `link`, `ldflag`, `insignia`

```pengu
include "mylib.h"        # añade la cabecera al C generado
link "mylib"             # añade -lmylib cuando una función viva lo necesita
link "m"
ldflag "-sUSE_GLFW=3"    # opción cruda del linker, para lo que un nombre de librería no expresa
insignia mylib_          # prefijo C de cada declaración de abajo
```

`link` es condicional: la opción llega al linker solo cuando el módulo tiene un
símbolo vivo que la necesita (release poda el código nativo sin usar). `ldflag`
se emite fuera del envoltorio `--start-group` y el proyecto puede sobrescribirlo
con sus propios `ldflags`.

`insignia` prefija los nombres C generados: con `insignia pengu_`, `weave
helper` pasa a `pengu_helper`, y un `omen Color` pasa a `pengu_Color` con
variantes `pengu_Color_Red`. Es la herramienta que evita que un binding choque
con libc.

### 8.2 `declare`

```pengu
declare strlen_c with s as ref to char into usize
declare printf with fmt as ref to frozen char, ... into int
declare qsort with base as ref to void, n as usize, size as usize, cmp as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void
```

Las listas de parámetros de `declare` deben escribirse en una sola línea: el
parser no continúa una lista de parámetros tras una coma final.

* Toda función externa debe declararse antes de usarse (`E0004`).
* Los tipos de parámetro y retorno deben coincidir exactamente con el prototipo
  de C; PenguScript no convierte en silencio en la frontera.
* Un `...` final significa varargs crudos de C (solo en `declare`).
* `declare` puede combinarse con `@noreturn` y con `inline`.

Strings de C: pasa `ref to char`; un literal de string de PenguScript se
convierte automáticamente donde se espera `ref to char`. Usa `bytes of s` para
una vista mutable de bytes y `std.ffi` para conversiones explícitas.

### 8.3 `opaque`, `ref to`, `bytes of`

```pengu
alias File as opaque

declare fopen with path as ref to char, mode as ref to char into ref to File
declare fclose with f as ref to File into int

weave main into int:
    var f as ref to File is calling fopen with "/tmp/x", "r"
    if f == null:
        return 1
    defer banish f          # solo si el módulo documenta que es dueño del handle
    var raw as ref to frozen byte is bytes of "abc"
    return 0
```

* `opaque` es un tipo de C incompleto: no se puede instanciar (`E0012`) y solo
  se usa tras `ref to`.
* `bytes of s` produce `ref to byte` para un string o un array fijo de bytes; la
  vista es prestada y no debe banishearse.
* `sigil of x` es `&x`; `essence of p` es `*p`.

### 8.4 Archivos de declaración `.d.pengu`

```pengu
# mylib.d.pengu
include "mylib.h"
link "mylib"

omen Mode:
    MODE_FAST is 1
    MODE_SAFE is 2

declare mylib_open with name as ref to char into ref to opaque
```

Un `.d.pengu` contiene `include`/`link`/`ldflag`/`insignia`/`declare` y
declaraciones de tipos; no es lugar para código ejecutable. Es el compañero de
una librería de C, escrito a mano o generado por `psc bind`, y el envoltorio con
nombre latino (`std/mylib.pengu`) es donde vive la API pública y segura. El
compilador no rechaza hoy un cuerpo en un `.d.pengu`, así que es una convención
que debes respetar.

`psc bind header.h --output=mylib.d.pengu` genera las declaraciones desde una
cabecera de C (consulta `docs/EXTERNAL_MODULES.md`).

### 8.5 `antiquus` — C incrustado

```pengu
antiquus add with a as int, b as int into int:
    """
    return a + b;
    """
```

El cuerpo es C literal en un string con triple comilla. Las reglas de cabecera
son las de `weave` (`shard`, `where`, valores por defecto, cualquier tipo de
parámetro); el cuerpo ve los nombres de los parámetros tal cual, así que deben
ser identificadores de C válidos (`E0035`). `many T` no se admite, y `main` no
puede ser un `antiquus` (`E0040`). Un `antiquus` es una definición, así que va
en un `.pengu`, no en un `.d.pengu`. Prefiere `r"""..."""` cuando el C contenga
barras invertidas.

`@export("sym")` fija el símbolo emitido y lo convierte en raíz del DCE.

### 8.6 `transmute`, `@packed`, `@align`

```pengu
@packed
rune Header:
    magic as u32
    version as u16

weave bits_of with f as float into u32:
    return transmute f to u32
```

`transmute x to T` reinterpreta los bits (sin comprobación). `@packed` elimina
el relleno del struct; `@align(N)` fija la alineación. Ambos cambian el layout
de C y están pensados para formatos en disco o de red — consulta §14.

## 9. Tipos compuestos

### 9.1 `rune` — structs

```pengu
rune Player:
    name as string
    hp as int
    is_alive as bool
    _secret_id as int          # privado del módulo (E0043 fuera)
```

Construcción:

```pengu-fragment
var p as Player is with name is "Hero", hp is 100, is_alive is true

var q as Player with:
    set .name is "Villain"
    set .hp is 50
```

Los constructores anidados infieren el tipo del campo:

```pengu-fragment
var person as Person with:
    set .name is "Ada"
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
```

Los campos se leen con `.` sobre un valor y con `->` sobre una referencia
(`self->hp`). Un rune es un `struct` de C; sus campos aparecen en orden de
declaración.

Un rune se reduce a un struct de C más un helper de clonado y otro de limpieza;
ambos se generan aunque sean triviales, para que los contenedores puedan copiar
y liberar cualquier rune de forma uniforme:

```c
struct Point { int32_t x; int32_t y; };

static inline void _pengu_clone_Point(Point* out, const Point* v) { *out = *v; }
static inline void _pengu_cleanup_Point(Point* p) { (void)p; }
```

Un rune cuyos campos poseen memoria genera una limpieza que los libera, y
`derive Nexus` es lo que hace que `banish` la llame.

### 9.2 `cyclus` — tipos recursivos

```pengu
rune Node cyclus:
    value as int
    next as maybe ref to Node
```

La recursión por valor es infinita y se rechaza (`E0050`). `cyclus` marca la
declaración como intencionadamente recursiva; el ciclo debe romperse igualmente
con indirección (`ref to`, `list`, `map`, `slice`).

Una autorreferencia *genérica* (`rune Node shard T:` con `ref to Node of T`
dentro) se rechaza con `E0021` en 0.28.0: el parámetro de tipo no está en scope
dentro de su propio cuerpo. Envuelve el payload (`value as ref to void`, o un
nodo no genérico que guarde `slice of T`).

### 9.3 `echo` — uniones

```pengu
echo Number:
    i as int
    f as float
```

Un `echo` es una `union` de C: todos los campos comparten almacenamiento y el
registro mide lo que su campo mayor. El acceso a campos no se comprueba —
escribir uno sobrescribe los demás. Para un tipo suma etiquetado usa `omen`.

### 9.4 `omen` — enums y tipos suma

```pengu
omen Direction:              # enum numérico
    North is 0
    South is 1

omen Color with string:      # con valores de string
    Red
    Green

omen Event:                  # tipo suma algebraico
    Disconnected
    Connecting with attempt as int
    Connected with session_id as string, latency_ms as float
```

| Variante | Escritura | C |
| --- | --- | --- |
| Numérica | `omen X:` con `is N` | `typedef enum { X_A = 0, ... } X;` |
| De string | `omen X with string:` | `#define X_A pengu_string_from_cstr("A")` |
| Algebraica | variantes con payload `with` | struct con `int32_t tag` + `union` de payload |

Las variantes son accesibles sin cualificar (`Red`), cualificadas
(`Color.Red`) o por nombre C completo (`Color_Red`). Los valores duplicados son
`E0027`, los no constantes `E0029`, los payloads en un omen de strings `E0028`
y los nombres sin cualificar ambiguos `E0046`.

```c
typedef struct {
    int32_t tag;
    union {
        struct { int32_t attempt; } Connecting;
        struct { PenguString session_id; float latency_ms; } Connected;
    } data;
} Event;
```

### 9.5 `seal`, `alias`, `opaque`

```pengu
seal UserId as int          # nominal: sin conversión implícita
alias Inches as int         # sinónimo transparente
alias Buffer as opaque      # handle de C incompleto
```

Un `seal` es un tipo distinto: asignarle un `int` exige `raw to UserId`. Un
`alias` es intercambiable con su destino. `opaque` no se puede instanciar
(`E0012`) y vive tras `ref to`.

### 9.6 `frozen`

```pengu-fragment
frozen int              # const int
ref to frozen int       # const int *
frozen Player           # const Player
```

`frozen` cualifica lo apuntado; la forma canónica es `ref to frozen T`. Es
ortogonal a `let`: `let` congela el nombre, `frozen` congela el valor. Un valor
mutable fluye hacia `frozen`; lo contrario no compila.

### 9.7 `derive`

```pengu
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int
```

| Concepto | Derivable | Genera |
| --- | --- | --- |
| `Par` | sí | `==`, `!=` |
| `Ordo` | sí | `<`, `<=`, `>`, `>=` |
| `Vinculum` | sí | hash, usable como clave de mapa |
| `Imago` | sí | `_pengu_clone_<T>` (e implica `Nexus`) |
| `Nexus` | sí | `_pengu_cleanup_<T>` |
| `Forma`, `Iterabilis` | no (`E0005`) | — |
| `Donum` | automático | implícito cuando todos los campos son inicializables por defecto; `derive Donum` es `E0005` |

Derivar un concepto de comparación sobre un rune genérico acota sus parámetros;
la comprobación ocurre en cada punto de sustitución.

### 9.8 Constructores `with:`

```pengu-fragment
var p as Point with:
    set .x is 10
    set .y is 20
    calling .shift with 5, 3
```

Un constructor asigna un temporal a cero, aplica `set .field` y llamadas, y
evalúa al valor. Solo se permiten `set .field is ...` y llamadas sobre el
destino (`E0014`); `if`, `var`, `defer` y `banish` se rechazan. La mutabilidad
sigue al binding: `let p with:` construye una vez y congela el nombre; `with
let_ptr:` donde `let_ptr as ref to T` sigue siendo mutable porque lo apuntado lo
es.

## 10. Métodos y conceptos

### 10.1 `enchanting` — métodos sobre un tipo

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100
```

* `self` es implícito y tiene tipo `ref to Player`, así que los campos se
  escriben `self->hp`. `self.hp` es `E0003`.
* Un método declarado con `ritual` es estático: no tiene `self` y se llama sobre
  el nombre del tipo (`calling Player.new_hero with "Ada"`). Usar `self` ahí es
  `E0033`.
* Llamar a un ritual sobre una instancia, o a un método de instancia sobre un
  tipo, es `E0034`.
* `enchanting` funciona con tipos de usuario y con contenedores integrados,
  incluidas las formas genéricas: `enchanting list of shard T:`.

Un método se convierte en una función libre de C cuyo primer parámetro es el
puntero al receptor, llamada `<Tipo>_<método>`:

```c
void Player_heal(Player* self, int32_t amount) {
    self->hp = (self->hp + amount);
}

/* punto de llamada */
Player_heal(&p, 2);
```

No hay vtable: `bind` y los conceptos se resuelven en tiempo de compilación, así
que una llamada a un método de concepto es una llamada directa de C a la
implementación concreta.

### 10.2 `@mutates`

`@mutates` declara un método cuyo resultado se asigna de vuelta al receptor. El
cuerpo se escribe como si fuera puro — `self` no se muta y el cuerpo devuelve el
valor nuevo — y la asignación ocurre en el punto de llamada.

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    @mutates
    weave grown with by as int into Player:
        return with name is self->name, hp is self->hp + by
```

Solo es válido dentro de `enchanting`, el tipo de retorno debe ser el del
receptor, y una sola función de C sirve tanto a la forma pura como a la forma
en sitio.

### 10.3 `concept` — contratos de tiempo de compilación

```pengu
concept Speaker:
    weave greet with target as string into string
```

Un concepto solo enumera firmas de métodos — sin cuerpos, sin campos, sin
estado. Puede tomar parámetros de tipo (`concept Container shard T:`). Los
métodos `ritual` dentro de un concepto no están soportados en 0.28.0 (el checker
registra el modificador como nombre del método); declara los rituales en
`enchanting`.

### 10.4 `bind` — implementar un concepto

```pengu
concept Speaker:
    weave greet with target as string into string

rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with target as string into string:
        return "Woof, {target}!"
```

| Regla | Diagnóstico |
| --- | --- |
| Todo método requerido debe implementarse | `E0031` |
| El número y tipos de parámetros y el retorno deben coincidir exactamente | `E0030` |
| El tipo y el concepto deben existir antes del `bind` | `E0004` |
| Un tipo puede ligar cualquier número de conceptos | — |
| No hay métodos por defecto: cada `bind` escribe todos los cuerpos | — |

### 10.5 Resolución de métodos

`calling x.m with ...` se resuelve en este orden:

1. Desenvuelve `ref to`, `alias`, `seal` y `frozen` hasta el tipo base.
2. Si `x` es un parámetro de tipo, usa sus bounds `where`.
3. Busca `(tipo base, método)` en la tabla de métodos que llenan `enchanting`
   y `bind`.
4. Busca el nombre monomorfizado (`Box_int` → `Box`).
5. Busca en la tabla de bindings de conceptos.
6. Cae a los métodos integrados de contenedor (`push`, `pop`, `len`, `get`, …).
7. Si no, `E0004`.

La resolución es estática; no hay vtable ni despacho dinámico.

### 10.6 Conceptos integrados

| Concepto | Habilita |
| --- | --- |
| `Num` | `+`, `-`, `*`, `/`, `-` unario |
| `Integrum` | `%`, `&`, `&#124;`, `^`, `<<`, `>>`, `~`, comparaciones |
| `Real` | aritmética y comparaciones de coma flotante |
| `Par` | `==`, `!=` |
| `Ordo` | `<`, `<=`, `>`, `>=` |
| `Vinculum` | usable como clave de `map` (hashing) |
| `Imago` | copia profunda (`_pengu_clone_<T>`) |
| `Nexus` | destrucción (`_pengu_cleanup_<T>`, invocada por `banish`) |
| `Forma` | interpolación de strings (`"{x}"`) |
| `Iterabilis` | `for x in col` |
| `Donum` | valor por defecto de `donum T` |

`Integrum` y `Real` son refinamientos disjuntos de `Num`; un tipo satisface `Num`
a través de uno u otro. Un genérico que solo necesita `+ - * /` debe acotarse
con `Num`.

## 11. Genéricos

### 11.1 `shard`

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x
```

Un parámetro `shard` está en scope desde la lista `with` hasta el final de la
declaración, incluido el tipo de retorno y el cuerpo. Cada uso concreto
instancia una función o un struct de C especializado (`identity_int`,
`Box_of_string`). El anidamiento está soportado: `Box of (Box of int)`.

Los argumentos explícitos están disponibles cuando la inferencia no puede verlos:

```pengu-fragment
var a as int is calling identity of int with 5
var b as string is calling identity of string with "hi"
```

Cada instanciación es una función de C distinta, con sufijo de número de
instanciación:

```c
int32_t d2_identity_inst3(int32_t x) { return x; }
```

El sufijo es interno; el nombre en PenguScript sigue siendo `identity`. Un rune
genérico instancia un struct por argumento de tipo, y solo se emiten las
instanciaciones que el programa usa (DCE).

### 11.2 Bounds

```pengu
weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if xs.len == 0:
        return fallback
    return xs at 0
```

Los bounds se escriben con `where`; varios se unen con `and`
(`where T: Num and T: Ordo`). Un bound es lo que permite que un cuerpo genérico
use un operador o método sobre `T`; sin él, el operador es `E0005`.

### 11.3 `donum T`

`donum T` es el valor por defecto de un tipo inicializable por defecto: `0` para
números, `false`, `""`, un struct a cero, un contenedor vacío.

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

Un rune o un echo implementan `Donum` automáticamente cuando todos sus campos lo
hacen. Un contenedor genérico necesita el bound:
`rune Box shard T where T: Donum:`.

### 11.4 Métodos genéricos y derivación

```pengu
rune Point shard T derive Par, Ordo:
    x as T
    y as T
```

Los conceptos derivados sobre un genérico se convierten en bounds de sus
parámetros; la comprobación ocurre en cada sustitución. `derive Donum` no se
escribe nunca (`E0005`).

### 11.5 Límites

* Los tipos asociados no están implementados (aplazados).
* No hay parámetros comodín ni de tipo superior.
* Los tipos genéricos y los tipos con métodos no son de scope de módulo: dos
  módulos que declaren el mismo nombre genérico producen `E0070`.

## 12. Opcionales y errores

### 12.1 `maybe T` y `result of T to E`

* `maybe T` responde *¿hay un valor?* — búsquedas, campos opcionales, "find".
* `result of T to E` responde *¿qué falló?* — E/S, parsing, red.

```pengu
omen IoError:
    NotFound
    Permission
    Unknown

weave find_user with id as int into maybe string:
    if id == 1:
        return some "Admin"
    return maybe none

weave load with path as string into result of string to IoError:
    if path == "":
        return calling err_of with IoError.NotFound
    return calling ok_of with "data"
```

`maybe T` es un `PenguMaybe` — un flag más un payload boxeado. `some x` asigna el
payload y mueve el valor dentro:

```c
PenguMaybe m = __extension__(({ int32_t _p = 3;
    int32_t* _h = malloc(sizeof(int32_t)); if (!_h) abort();
    *_h = _p; PenguMaybe _r = pengu_maybe_some(_h); _r; }));
```

Leer un valor presente lo desreferencia y lo copia; `banish` libera la caja. El
payload boxeado es la razón de que `some x` mueva un valor con propiedad en vez
de copiarlo.

### 12.2 Constructores

| Constructor | Produce |
| --- | --- |
| `some x` | `maybe T` presente |
| `maybe none` | `maybe T` vacío |
| `calling ok_of with v` | lado `ok` de un `result` |
| `calling err_of with e` | lado `err` de un `result` |

`ok` y `err` **no** son keywords ni constructores: `ok 1` es
`E0004: Undefined identifier 'ok'`. `result of T` sin `to E` hace que `E` sea
`error` (un `const char *`); prefiere nombrar el tipo de error.

### 12.3 Inspección y desenvolvimiento

```pengu-fragment
var user as maybe string is calling find_user with 1

if user is present:
    calling print with user.value

if user is not present:
    calling print with "missing"

if user as string is u:
    calling print with u

let fallback as string is user or else "Guest"
let u2 as string is user or return 0
let data as string is try calling load with "x"
```

`maybe` expone `.is_present` y `.value`; `result` expone `.is_ok`, `.value` y
`.error` (alias `.err`). Leer `.value` cuando está ausente es indefinido —
comprueba antes, o usa `as`, `or else`, `or return`, `try` u `or:`.

### 12.4 `or else`, `or return`, `try`, `or:`

* `x or else fallback` — evalúa `fallback` solo cuando no hay valor o hay error.
* `x or return expr` — ejecuta las limpiezas pendientes `defer`/`errdefer` y
  devuelve `expr` desde el weave que lo envuelve.
* `try x` — propaga un `maybe` vacío o un `result` con error desde la función
  que lo envuelve; el tipo de retorno debe ser compatible (`E0045`). La función
  debe devolver un `maybe` o un `result` compatible.
* `x or:` — un bloque que maneja el fallo; dentro, `error` queda ligado al
  payload del fallo (tipo `string` para `maybe`, el tipo de error para `result`)
  y es su dueño.

```pengu-fragment
var parsed as JsonValue is calling json.parse with text or:
    calling spark.println with "invalid: {error}"
    return 1
```

`error` solo es visible dentro del bloque `or:` (`E0015` fuera). En posición
aritmética, las expresiones de desenvolvimiento necesitan paréntesis:
`10 + (bonus or else 0)`.

### 12.5 `panic`

`panic` aborta el proceso tras imprimir el mensaje y una traza de pila
(`std.spark.panic`). Es para bugs y estados imposibles, nunca para fallos
esperados — un fallo esperado es un `result`.

### 12.6 `defer` y `errdefer`

```pengu-fragment
weave copy_file with src as string, dst as string into result of void to IoError:
    var in as string is try calling archivum.read_file_result with src
    defer banish in
    var out as string is calling transform with in
    errdefer banish out          # solo se ejecuta si el weave devuelve un error
    if out.len == 0:
        return calling err_of with IoError.Unknown
    return calling ok_of with 0
```

`defer` se ejecuta al salir del scope por cualquier camino; `errdefer` solo
cuando el scope sale mediante un `return` de error (un `result` con error).
Ambos se ejecutan en orden LIFO y antes de que un `or return`/`try` propague.

### 12.7 Propiedad de los valores boxeados

`some`, `ok_of` y `err_of` boxean el payload con un `memcpy`. Cuando el operando
es un hueco vivo con propiedad (una variable, un campo, `essence of`), el
constructor lo **mueve**: la fuente queda vacía y la caja pasa a ser la única
dueña. No uses ni banishees la fuente después. Un rvalue se copia directamente
en la caja, y un parámetro prestado se clona, así que el llamador conserva su
búfer.

`banish m` libera primero el payload que posee la caja y después la caja.

## 13. Memoria

### 13.1 El modelo

Sin GC, sin borrow checker, sin liberación al salir del scope. Tú asignas, tú
liberas. El compilador comprueba tipos y, con una excepción sintáctica (los
movimientos al boxear), no rastrea tiempos de vida.

```pengu
weave main into int:
    var s as string is "hello"
    defer banish s
    calling print with s
    return 0
```

### 13.2 `banish`

`banish target` acepta un lvalue mutable de tipo `ref to T`, `string`,
`list of T`, `map of K to V`, `maybe T`, `result of T to E`, o un rune con
`derive Nexus` (o con un helper de limpieza).

| Destino | C emitido |
| --- | --- |
| `string` | `pengu_banish_string(&s)` |
| `list of T` | `pengu_banish_list(&l)` |
| `map of K to V` | `pengu_banish_map(&m)` |
| `ref to T` | `pengu_banish((void*)p)` |
| `maybe` / `result` | payload + caja |
| rune con `Nexus` | `_pengu_cleanup_T(&v)` |
| elemento (`xs at 0`, `m at "k"`) | libera ese elemento en sitio |

Banishear un string o un contenedor lo deja vacío. Un string prestado
(`is_owned == 0`) es un no-op seguro. Banishear un `list of string` libera el
búfer propio de la lista pero **no** los strings de dentro: libera cada string,
o usa `pengu_banish_string_list`.

Destinos rechazados (`E0008`): literales, temporales (asigna antes a una
variable), newtypes `seal` (convierte explícitamente), valores `frozen` y
constantes.

### 13.3 `defer` y `errdefer`

Programa una liberación en vez de ejecutarla ahora. `defer` se ejecuta al salir
del scope por cualquier camino; `errdefer`, solo en un retorno de error. Ambos
son LIFO.

```pengu-fragment
var buf as list of int is [1, 2, 3]
defer banish buf
```

### 13.4 Lo que el compilador no hace

* No libera nada al salir del scope salvo que hayas escrito `defer`.
* No detecta doble liberación, uso tras liberación ni fugas.
* No rastrea la propiedad a través de fronteras de función: quien asigna decide
  quién libera, y la API debe documentarlo.
* No libera los elementos de un `list`/`map` cuando se banishea el contenedor.

### 13.5 Los valores boxeados se mueven

`some x`, `ok_of x`, `err_of x` vacían un hueco vivo con propiedad (ver §12.7).
Tras boxear, la fuente queda vacía; banishearla es un no-op, usarla es un bug.

### 13.6 Valores devueltos y parámetros

* Un weave que devuelve un `string`, `list` o `map` transfiere la propiedad al
  llamador; el llamador lo banishea.
* Un parámetro de tipo string/contenedor es **prestado** por el llamado, salvo
  que la firma diga otra cosa. El llamado no debe banishearlo.
* Un `ref to T` devuelto es una vista prestada salvo que el módulo documente una
  transferencia de propiedad.
* Cruzar una frontera de tarea es una transferencia: `filum.start` mueve los
  valores con dueño y exige `@shared` para los `ref`; `coro.start` los mueve
  igual, pero acepta `ref to T` sin `@shared` porque la corrutina nunca cambia
  de hilo. En ambos casos el binding original queda inutilizable (`E0008`).

### 13.7 Depurar fugas

* Compila en debug y ejecuta bajo `valgrind --leak-check=full` o ASan
  (`cc -fsanitize=address`); el C generado es C normal.
* El runtime mantiene un búfer circular de 64 marcos para las trazas de pánico,
  así que un `panic` señala la línea que lo lanzó.
* `std.arena` es la vía de escape para un grupo de asignaciones con un solo
  tiempo de vida: asigna desde la arena y luego `banish arena` libera todo de
  una vez.

## 14. Atributos

Los atributos se escriben en la línea encima de la declaración que modifican.

| Atributo | Se aplica a | Efecto | C |
| --- | --- | --- | --- |
| `@inline` | `weave` | fuerza el inlining | `static inline __attribute__((always_inline))` |
| `@cold` | `weave` | marca un camino raro | `__attribute__((cold))` |
| `@deprecated("msg")` | cualquier declaración | avisa al usarla (`W0006`) | `__attribute__((deprecated("msg")))` |
| `@noreturn` | `weave`, `declare`, `antiquus` | la llamada nunca retorna | `__attribute__((noreturn))` |
| `@export("symbol")` | `weave`, `antiquus` | fija el símbolo C y lo mantiene vivo (raíz del DCE) | función C exportada |
| `@packed` | `rune` | elimina el relleno del struct | `__attribute__((packed))` |
| `@align(N)` | `rune` | fija la alineación | `__attribute__((aligned(N)))` |
| `@mutates` | método en `enchanting` | asigna el resultado de vuelta al receptor | una función C, dos formas de llamada |
| `@shared` | `rune`, `omen` | permite que `ref to T` cruce `filum.start` | sin cambio de código; flag de compilación |
| `@spawn` | `weave` | marca la función que arranca un hilo; valida worker y propiedad en cada llamada | sin cambio de código; contrato del compilador |
| `@coroutine` | `weave` | marca la función que arranca una corrutina; valida worker y propiedad | sin cambio de código; contrato del compilador |

```pengu
@deprecated("use read_file_result to distinguish the failure cause")
weave read_file with path as string into maybe string:
    return maybe none

@noreturn
declare abort_now into void

@packed
rune WireHeader:
    magic as u32
    version as u16
```

`@export` sin un prefijo propio del proyecto puede chocar con símbolos de libc;
prefíjalo (`@export("mylib_fast_double")`). `@packed` y `@align(N)` cambian el
ABI del struct: úsalos solo para formatos de red o de disco, y replica el layout
en el lado C exactamente. `@shared` es una promesa de que los métodos del rune
sincronizan; el compilador comprueba la frontera, no la implementación.

### 14.1 Hilos

```pengu
import std.filum

weave worker with value as string into void:
    calling print with value

weave main into int:
    let h as Thread is calling filum.start with worker, "hello"
    var r as result of void to ThreadError is calling h.join
    calling h.free
    return 0
```

`start` mueve los argumentos con dueño al worker; un local movido no puede
volver a leerse (`E0008`). `start0`, `start2` y `start3` cubren workers de cero,
dos y tres argumentos. Un `ref to T` exige `@shared` en `T`; los escalares se
copian. `join` espera y devuelve `result of void to ThreadError`; `detach` es
fire-and-forget; `free` libera el handle. `Thread` es un id copiable, así que un
supervisor puede guardarlo. TLS, `Pool` y `parallel_for` también están en
`std.filum`.

### 14.2 Corrutinas

Una corrutina es una tarea cooperativa, explícita y *stackful*: se suspende en
`coro.yield` y solo avanza cuando su dueño llama `resume`. Vive en el hilo que
la creó, así que no hay carreras ni migración; para paralelismo se usa
`std.filum`.

```pengu
import std.coro

weave worker with out as ref to int into void:
    set essence of out is 1
    calling coro.yield
    set essence of out is 2

weave main into int:
    var n as int is 0
    var co as coro.Coroutine is calling coro.start with worker, (sigil of n)
    var first as coro.CoroutineState is calling co.resume
    var second as coro.CoroutineState is calling co.resume
    calling co.free
    if first != coro.CoroutineState.suspended or second != coro.CoroutineState.finished:
        return 1
    return n
```

`start` crea la corrutina suspendida y mueve el argumento con dueño; `start0`
cubre un worker sin argumentos. `resume` la ejecuta hasta el siguiente `yield` o
hasta que retorne, y devuelve `suspended` o `finished`; `status` lee el estado
sin ejecutarla. `free` solo libera una corrutina terminada; `abandon` descarta
una suspendida (y no ejecuta sus `defer`). `yield` fuera de una corrutina, o
`resume` sobre una terminada, es un panic: son bugs del programa, no errores
recuperables.

La pila por defecto es de 64 KiB (arena compartida y reciclada); un `ref to T`
no requiere `@shared` porque no cruza hilos, y un `string`/`list`/`map` se mueve
al worker. No hay planificador, `async`/`await`, cancelación ni valores de
retorno por `yield`: el control es explícito y los datos viajan por `ref to` o
por el estado compartido del dueño. En wasm `std.coro` no está disponible.

`@coroutine` marca la función que arranca la tarea (la implementación de
`std.coro.start`); si escribes tu propio arrancador, replica el contrato:
primer argumento worker, resto argumentos del worker, retorno del worker `void`.

## 15. Tests y herramientas

### 15.1 Bloques `test`

```pengu
import std.ward

test "arithmetic":
    calling ward.assert_eq_int with 1 + 1, 2

test string_formatting:
    calling ward.assert_eq_string with "abc", "abc"
```

Un test es `test <nombre>:` donde el nombre es un literal de string o un
identificador. Los cuerpos se comprueban en todos los modos (`check`, `build`,
`run`, `test`), pero el arnés de C solo se emite para `psc test`. Los bloques
`test` van en archivos `.pengu`, no en `.d.pengu`.

```console
$ psc test              # ejecuta todos los bloques test del proyecto
$ psc test --watch      # reejecuta al cambiar
$ psc test --json       # eventos JSON Lines para CI
```

### 15.2 Comandos

| Comando | Propósito |
| --- | --- |
| `psc build [TARGET]` | compila a C y enlaza |
| `psc run FILE [-- args]` | compila y ejecuta un programa o un archivo suelto |
| `psc check [TARGET]` | solo comprueba tipos |
| `psc emit-c FILE` | imprime el C generado |
| `psc test` | ejecuta los bloques `test` |
| `psc fmt [PATHS]` | formatea (`--check`, `--diff`, `--stdin`, `--indent=N`, `--tabs`) |
| `psc doc` | genera `docs/api` desde los comentarios `##` (`--include-std`, `--html`, `--output=DIR`) |
| `psc bind HEADER` | genera un `.d.pengu` desde una cabecera C (`--prefix`, `--links`, `--ignore`, `--output`) |
| `psc init` / `psc new` | crea el esqueleto de un proyecto |
| `psc add` / `psc remove` / `psc update` | dependencias |
| `psc lsp` | arranca el servidor de lenguaje (stdio) |
| `psc doctor` | diagnostica el toolchain |
| `psc assets` | incrusta assets del proyecto |
| `psc gc` | elimina artefactos de build obsoletos |
| `psc tree` | imprime el grafo de módulos |
| `psc time` | mide las fases de compilación |
| `psc watch` | recompila al cambiar |
| `psc eval` | evalúa una expresión |
| `psc version` / `--version` / `-V` | imprime la versión del compilador |

### 15.3 Opciones de build

| Flag | Significado |
| --- | --- |
| `--profile=debug` &#124; `--profile=release` | optimización y comprobaciones |
| `--target=TRIPLE` &#124; `--target=wasm` | compilación cruzada |
| `--cc=NAME` | compilador de C |
| `--out=PATH` | ruta del artefacto |
| `--exe` | enlaza un ejecutable incluso en un proyecto de librería |
| `--strict-c99` | C99 portable (sin statement expressions) |
| `--release-unsafe` | desactiva comprobaciones de límites/desbordamiento |
| `--verbose` | imprime el comando del compilador |

`--json` en `check`/`build`/`test` emite diagnósticos legibles por máquina.
Códigos de salida: `0` éxito, `1` fallo de compilación o de test, `2` error de
uso.

### 15.4 Manifiesto del proyecto

`pengu.toml` (preferido) o `pengu.yaml` en la raíz del proyecto declaran `name`,
`version`, `src_dir`, `lib_dir`, `std_dirs`, `dependencies`, `output`, `cc`,
`ldflags`, `cflags`. `psc init` escribe uno mínimo.

### 15.5 `psc doc`

`psc doc` renderiza una página por módulo a partir de los comentarios `##`. Con
`--include-std` documenta también la biblioteca estándar, que es como se produce
[docs/api](api/README.md):

```console
$ psc doc --include-std --html --output docs/api
Generated 182 module(s) in docs/api
```

Cada página empieza con `# <módulo>`, una línea `> Source:` y el docstring del
módulo, y después una sección `###` por símbolo exportado con su firma y su
texto `##`. El índice es `docs/api/README.md`, y `--html` añade
`docs/api/index.html` con filtro.

## 16. Encadenamiento, pipes, tuplas y forma corta

### 16.1 Cadenas de métodos

Una cadena empieza con una expresión `calling` y continúa con eslabones
`.método`. Cada eslabón puede llevar su propia lista `with`:

```pengu
rune Counter:
    value as int

enchanting Counter:
    weave plus with n as int into Counter:
        return with value is self.value + n

weave main into int:
    var c as Counter is with value is 1
    var d as Counter is calling c.plus with 2
        .plus with 3          # 6
    return d.value
```

La cadena de arriba es la forma multilínea; es la que hay que usar cuando un
eslabón lleva argumentos. Un eslabón siempre es una llamada a método, nunca una
lectura de campo. Todos los eslabones salvo el último deben producir un valor;
un método `@mutates` solo puede ser el último.

Una línea de continuación empieza por `.` (o `->` para un receptor de
referencia) y se pliega en la línea anterior antes del lexado.

### 16.2 Pipes

`pipe` encadena **funciones libres**: el valor anterior se convierte en el
primer argumento de la llamada siguiente.

```pengu-fragment
var text as string is 42
    pipe spark.str_int

weave editar with value as int, delta as int into int:
    return value + delta

var total as int is calling base
    pipe editar with 2
    pipe editar with 3
```

`pipe` es contextual (un identificador válido) y solo se reconoce al principio
de una línea de continuación. Los pasos deben ser funciones libres, no métodos
(`E0053`). El último paso puede devolver `void`, en cuyo caso el pipe conserva
el valor anterior.

### 16.3 Tuplas y retornos múltiples

```pengu
weave divmod with a as int, b as int into (int, int):
    return a / b, a % b

weave main into int:
    let (q, r) is calling divmod with 7, 2
    return q + r
```

Un tipo tupla es `(T, U)`; un valor tupla es `(a, b)`. El destructuring funciona
con tuplas y con runes. Las tuplas son structs anónimos de C y no se asignan en
el heap.

Un tipo tupla se reduce a un struct nombrado por sus tipos componentes, con
campos `first`, `second`, `third`, …:

```c
typedef struct { int32_t first; int32_t second; } PenguTuple_int32_t_int32_t;

PenguTuple_int32_t_int32_t _pengu_tup0 = d2_divmod(7, 2);
int32_t q = _pengu_tup0.first;
int32_t r = _pengu_tup0.second;
```

Un `let a, b is expr` guarda `expr` primero en un temporal, así que la expresión
se ejecuta exactamente una vez; los dos bindings leen de ese temporal.

### 16.4 Inicializadores abreviados de struct

Dentro de un literal `with`, un campo puede omitir `is valor` y tomar el binding
del mismo nombre:

```pengu-fragment
weave make into Player:
    let name is "Ada"
    var hp is 100
    return with name, hp        # igual que: with name is name, hp is hp
```

Ambas formas pueden mezclarse; un campo cuyo valor no sea un nombre simple
necesita la forma explícita con `is`.

## 17. Deprecación

Marca una declaración con `@deprecated("motivo")`; cada uso emite `W0006` con
ese motivo, y `psc doc` muestra una insignia de deprecado.

```pengu
## @deprecated use read_file_result to distinguish the failure cause
@deprecated("use read_file_result to distinguish the failure cause")
weave read_file with path as string into maybe string:
    return maybe none
```

Política: un símbolo deprecado sigue funcionando al menos una release menor y
solo se elimina en una release mayor; el changelog nombra el reemplazo. No
depreques sin nombrar la alternativa.

## 18. Diagnósticos

Cada diagnóstico tiene un código estable. Los errores detienen la compilación;
los avisos no.

| Código | Significado |
| --- | --- |
| `E0000` | error de sintaxis |
| `E0001` | `const` dentro de un weave |
| `E0002` | `var`/`let` en top level |
| `E0003` | `self.` en vez de `self->` |
| `E0004` | nombre, miembro, módulo o etiqueta indefinidos |
| `E0005` | discrepancia de tipos |
| `E0006` | violación de mutabilidad |
| `E0007` | `break`/`continue` fuera de un bucle, o etiqueta que no lo envuelve |
| `E0008` | operación de memoria inválida (`banish` de un temporal, literal, `frozen`, …) |
| `E0009` | destino `with` inválido |
| `E0014` | sentencia inválida dentro de un constructor `with:` |
| `E0015` | dimensión de array desconocida |
| `E0019` | expresión de interpolación inválida |
| `E0020` | discrepancia en el tipo de `return` |
| `E0021` | número incorrecto de argumentos genéricos |
| `E0022` | parámetro de tipo usado fuera de su declaración |
| `E0023` | más de un parámetro `many` |
| `E0024` | `many` no es el último parámetro |
| `E0026` | más de un `insignia` |
| `E0027` | valor de variante de omen duplicado |
| `E0028` | payload en un omen de strings |
| `E0029` | valor de variante de omen no constante |
| `E0030` | firma de método de concepto incorrecta |
| `E0031` | método de concepto no implementado |
| `E0032` | bound no satisfecho |
| `E0033` | `self` dentro de un `ritual` |
| `E0034` | ritual llamado sobre una instancia, o método sobre un tipo |
| `E0035` | nombre que no es un identificador C válido |
| `E0036` | alias de import inválido |
| `E0037` | nombre de binding duplicado (índice/elemento de bucle) |
| `E0038` | nombre reservado de C |
| `E0039` | nombre de campo que choca con un nombre de C |
| `E0041` | tamaño de array inválido |
| `E0042` | rango inválido |
| `E0043` | símbolo privado accedido desde otro módulo |
| `E0044` | `judge` no exhaustivo |
| `E0047` | método no disponible sobre un primitivo |
| `E0049` | operador no permitido por el bound |
| `E0050` | tipo de tamaño infinito |
| `E0051` | referencia colgante |
| `E0052` | concepto duplicado |
| `E0053` | forma de composición incorrecta (`.` frente a `pipe`) |
| `E0056` | atributo no permitido aquí |
| `E0057` | carácter fuera de rango |
| `E0059` | `antiquus` sin cuerpo |
| `E0063` | `static` en la posición incorrecta |
| `E0064` | nombre de test inválido |
| `E0065` | colisión de nombre de campo en C |
| `E0066` | `@mutates` usado en posición de valor |
| `E0067` | `@mutates` sobre algo que no es método |
| `E0068` | el retorno de `@mutates` no es el receptor |
| `E0069` | etiqueta de bucle duplicada |
| `E0070` | nombre de tipo duplicado en un módulo |
| `W0001` | se usó `transmute` |
| `W0002` | acceso a campo de `echo` (unión sin comprobar) |
| `W0004` | código inalcanzable |
| `W0005` | binding ocultado |
| `W0006` | símbolo deprecado usado |
| `W0007` | operación insegura |
| `W0013` | rango vacío o invertido |

`psc check --json` y `psc build --json` emiten cada diagnóstico como un objeto
JSON con `code`, `severity`, `message`, `file`, `line`, `column` y `help`
opcional.

## 19. Ejemplo completo

Una lista de tareas que ejercita `omen`, `rune`, `enchanting`, `judge`, `with`,
`maybe`, `for`, `defer` e interpolación de strings:

```pengu
import std.spark

omen Priority:
    Low is 0
    Normal is 1
    High is 2

weave priority_name with p as Priority into string:
    return judge p:
        when Priority.Low -> "low"
        when Priority.Normal -> "normal"
        when Priority.High -> "high"

rune Task:
    title as string
    priority as Priority
    done as bool

enchanting Task:
    weave label into string:
        return "{self->title} [{calling priority_name with self->priority}]"

weave make_task with title as string, priority as Priority into Task:
    return with title is title, priority is priority, done is false

weave first_high with tasks as list of Task into maybe Task:
    for t in tasks:
        if t.priority == Priority.High:
            return some t
    return maybe none

weave main into int:
    var tasks as list of Task is list of Task
    defer banish tasks

    calling tasks.push with (calling make_task with "write docs", Priority.High)
    calling tasks.push with (calling make_task with "review PR", Priority.Low)

    var top as maybe Task is calling first_high with tasks
    if top is present:
        var t as Task is top.value
        calling spark.println with (calling t.label)
    else:
        calling spark.println with "nothing urgent"

    calling spark.println with "{tasks.len} task(s)"
    return 0
```

Salida:

```text
write docs [high]
2 task(s)
```

Lo interesante del lowering: `Task` se convierte en un struct de C, `Priority`
en un enum, `judge p:` en un `switch`, el literal `with` en un literal
compuesto, el `maybe` en un `PenguMaybe` cuyo payload se boxea en el heap, y
`defer banish tasks` en una llamada de limpieza emitida en cada camino de
retorno.

## Apéndice A. Keywords

| Keyword | Significado |
| --- | --- |
| `alias` | sinónimo de tipo transparente |
| `and` | y lógico (también une bounds) |
| `antiquus` | función cuyo cuerpo es C literal |
| `as` | cast comprobado / estrechamiento |
| `banish` | libera almacenamiento con propiedad |
| `bind` | implementa un concepto para un tipo |
| `break` | sale de un bucle |
| `bytes` | operador de vista de bytes (`bytes of`) |
| `calling` | prefijo de llamada |
| `chr` | entero a carácter |
| `concept` | contrato en tiempo de compilación |
| `const` | valor de compilación en top level |
| `continue` | siguiente iteración |
| `cyclus` | marca un tipo intencionadamente recursivo |
| `declare` | función C externa |
| `defer` | se ejecuta al salir del scope |
| `defined` | comprobación de nombre en tiempo de compilación |
| `derive` | genera implementaciones de conceptos |
| `donum` | valor por defecto de un tipo |
| `echo` | unión de C |
| `else` | rama de reserva |
| `enchanting` | métodos de un tipo |
| `errdefer` | se ejecuta al retornar un error |
| `error` | payload del fallo dentro de `or:` |
| `essence` | desreferencia (`essence of`) |
| `false` | booleano falso |
| `for` | bucle |
| `from` | inicio del rango / forma de bucle |
| `if` | condicional |
| `import` | importación de módulo |
| `in` | pertenencia / iteración |
| `include` | añade una cabecera C |
| `insignia` | prefijo de nombres C |
| `into` | separador del tipo de retorno |
| `is` | predicado / forma de nombrado |
| `judge` | coincidencia de patrones |
| `lambda` | función estática anónima |
| `ldflag` | opción cruda del enlazador |
| `let` | binding inmutable |
| `link` | enlaza una librería |
| `many` | marcador variádico (reservado; ver §6.3) |
| `maybe` | tipo opcional / constructor vacío |
| `none` | `maybe` vacío (`maybe none`) |
| `not` | negación lógica / `not in` |
| `null` | valor de puntero nulo |
| `of` | constructor de tipo (`list of T`) |
| `omen` | enum / tipo suma |
| `or` | o lógico / formas de reserva |
| `ord` | carácter a entero |
| `return` | retorno de un weave |
| `rune` | struct |
| `seal` | newtype nominal |
| `set` | asignación |
| `shard` | parámetro de tipo genérico |
| `sigil` | dirección de (`sigil of`) |
| `some` | `maybe` presente |
| `static` | local persistente |
| `step` | paso del bucle |
| `test` | bloque de test |
| `to` | conversión / fin del rango |
| `transmute` | reinterpreta bits |
| `true` | booleano verdadero |
| `try` | propaga el fallo |
| `unless` | `if` negado |
| `var` | binding mutable |
| `weave` | función |
| `when` | rama de match / rama de compilación |
| `where` | bounds genéricos |
| `while` | bucle |
| `with` | lista de parámetros / literal / constructor |

## Apéndice B. Representaciones en runtime

| PenguScript | C |
| --- | --- |
| `string` | `typedef struct { char *data; int len; int32_t is_owned; } PenguString;` |
| `list of T` | `typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;` |
| `map of K to V` | `typedef struct { void *state; int len; int cap; size_t key_size; size_t val_size; } PenguMap;` |
| `slice of T` | `typedef struct { void *data; int len; size_t elem_size; } PenguSlice;` |
| `maybe T` | `PenguMaybe` — flag de presencia + payload boxeado |
| `result of T to E` | `PenguResult` — flag ok + payload/error boxeados |
| `ref to T` | `T *` |
| `rune` | `struct` con los campos en orden |
| `echo` | `union` |
| `omen` (numérico) | `enum` |
| `omen` (algebraico) | `struct { int32_t tag; union { ... } data; }` |
| `weave ... into ...` | tipo puntero a función |
| tupla `(T, U)` | `struct PenguTuple_<mangled>` con campos `first`, `second`, … |

Helpers generados: `pengu_string_from_cstr`, `pengu_string_format_ex`,
`pengu_string_copy`, `pengu_banish_string`, `pengu_list_new`, `pengu_list_push`,
`pengu_list_at`, `pengu_banish_list`, `pengu_map_new`, `pengu_map_put`,
`pengu_map_get`, `pengu_banish_map`, `pengu_maybe_some`, `pengu_maybe_none`,
`pengu_maybe_is_present`, `pengu_sigil_alloc`, `_pengu_clone_<T>`,
`_pengu_cleanup_<T>`, `_pengu_lambda_<N>`.

## Apéndice C. Esbozo de gramática

Una EBNF compacta del lenguaje implementado; omite la precedencia de expresiones
(§4.1) y las keywords contextuales (`over`, `pipe`, `frozen`).

```text
program        = { top_decl } ;
top_decl       = const_decl | rune_decl | echo_decl | omen_decl | seal_decl
               | alias_decl | weave_decl | declare_decl | antiquus_decl
               | enchanting_decl | concept_decl | bind_decl | test_decl
               | import_decl | directive | when_top ;

directive      = "include" string | "link" string | "ldflag" string
               | "insignia" ident ;

import_decl    = "import" dotted [ "as" ident ] ;
const_decl     = "const" ident [ "as" type ] "is" expr ;
rune_decl      = "rune" ident [ "cyclus" ] [ "shard" ident { "," ident } ]
                 [ "where" bounds ] [ "derive" ident { "," ident } ] ":"
                 { field } ;
field          = ident "as" type ;
echo_decl      = "echo" ident ":" { field } ;
omen_decl      = "omen" ident [ "with" "string" ] ":"
                 { ident [ "is" expr ] [ "with" field { "," field } ] } ;
seal_decl      = "seal" ident "as" type ;
alias_decl     = "alias" ident "as" type ;
weave_decl     = [ "@" attr ] { "@" attr } [ "inline" ] "weave" ident
                 [ "shard" ident { "," ident } ] [ "where" bounds ]
                 [ "ritual" ] [ "with" params ] "into" type ":" block ;
declare_decl   = "declare" ident [ "with" params ] "into" type ;
antiquus_decl  = "antiquus" ident [ "with" params ] "into" type ":"
                 ( '"""' { any } '"""' | 'r"""' { any } '"""' ) ;
enchanting_decl= "enchanting" type ":" { weave_decl } ;
concept_decl   = "concept" ident [ "shard" ident ] [ "where" bounds ] ":"
                 { weave_sig } ;
bind_decl      = "bind" ident "with" ident ":" { weave_decl } ;
test_decl      = "test" ( string | ident ) ":" block ;
when_top       = "when" expr ":" { top_decl } [ "else" ":" { top_decl } ] ;

block          = INDENT { stmt } DEDENT ;
stmt           = var_decl | const_decl | set_stmt | if_stmt | while_stmt
               | for_stmt | judge_stmt | return_stmt | break_stmt
               | continue_stmt | defer_stmt | banish_stmt | expr_stmt
               | "do" ":" block ;
var_decl       = ( "var" | "let" ) [ "static" ] pattern [ "as" type ]
                 "is" expr ;
set_stmt       = "set" lvalue ( "is" expr | op "=" expr ) ;
if_stmt        = ( "if" | "unless" ) expr ":" block
                 { "else" "if" expr ":" block } [ "else" ":" block ] ;
while_stmt     = [ ident ":" ] "while" expr ":" block ;
for_stmt       = [ ident ":" ] "for" ident [ "," ident ] "in" expr ":" block
               | [ ident ":" ] "for" ident "from" expr "to" expr
                 [ "step" expr ] ":" block ;
judge_stmt     = "judge" expr [ "over" ident ] ":"
                 { "when" pattern [ "with" ident { "," ident } ] [ "if" expr ]
                   "->" ( expr | block ) }
                 [ "else" "->" ( expr | block ) ] ;
return_stmt    = "return" [ expr ] ;
defer_stmt     = ( "defer" | "errdefer" ) stmt ;
banish_stmt    = "banish" expr ;

type           = "int" | "float" | "bool" | "char" | "string" | "void"
               | "ref" "to" [ "frozen" ] type
               | "frozen" type
               | "list" "of" type | "slice" "of" type
               | "array" "of" type "with" "size" expr
               | "map" "of" type "to" type
               | "maybe" type | "result" "of" type [ "to" type ]
               | "(" type { "," type } ")"
               | "weave" [ "with" params ] "into" type
               | ident [ "of" type ] ;
```
