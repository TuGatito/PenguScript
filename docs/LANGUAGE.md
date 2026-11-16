# PenguScript

**El lenguaje chico con backend filoso.**

| Campo | Valor |
|---|---|
| Lenguaje | PenguScript |
| Versión de la spec | `0.6.0` |
| Estado | `0.6.0` en revisión editorial; implementación pendiente |
| Fecha | 2026-11-12 |
| Backend | Rust 2024, único backend en 0.6.0; invisible para el usuario |
| MSRV del backend | 1.85.0 |
| Archivo | `docs/LANGUAGE.md` |

PenguScript es un lenguaje de sistemas pequeño y directo. Usa un backend filoso
para producir código máquina, pero **el usuario nunca escribe ni ve el
backend**. No es un transpilador, no es azúcar sobre otro lenguaje y no busca
retrocompatibilidad con las decisiones de Rust. Es un lenguaje propio.

La personalidad del lenguaje se resume así:

> Records, sums, pattern matching y ownership, sin lifetimes escritos, sin
> traits complejos, sin macros y sin unsafe general. ~15 conceptos. Se lee en
> una tarde. Se usa durante años.

La metáfora operativa es un cuchillo karambit: chico, curvo, filoso, capaz. No
es una navaja suiza. La regla que gobierna el diseño es:

> **Cada concepto que el usuario debe aprender debe justificar su existencia
> con potencia, no con paridad.** Si una feature no da potencia para el 95% del
> código, no entra. Si entra, se simplifica hasta que quepa en una línea.

<a id="indice"></a>
## Índice

1. [Misión y los ~15 conceptos](#sec-01)
2. [Léxico](#sec-02)
3. [Programa, módulos y entrada](#sec-03)
4. [Tipos](#sec-04)
5. [Bindings, mutabilidad y constantes](#sec-05)
6. [Expresiones y control](#sec-06)
7. [Funciones y closures](#sec-07)
8. [Records y sums](#sec-08)
9. [Pattern matching](#sec-09)
10. [Colecciones](#sec-10)
11. [Ownership y referencias](#sec-11)
12. [Pacts y rituals](#sec-12)
13. [Genéricos y bounds](#sec-13)
14. [Operadores](#sec-14)
15. [Errores, `Option` y `Result`](#sec-15)
16. [FFI: `foreign` y `curse`](#sec-16)
17. [Testing y documentación](#sec-17)
18. [Herramientas y tomes](#sec-18)
19. [Gramática](#sec-19)
20. [Diagnósticos](#sec-20)
21. [Garantías del lenguaje](#sec-21)
22. [Diferido y no soportado](#sec-22)
23. [Glosario](#sec-23)
24. [Cookbook](#sec-24)
25. [Decisiones de diseño (ADR)](#sec-25)
26. [Changelog](#sec-26)
27. [Referencias](#sec-27)
28. [Apéndice Z: qué se eliminó y por qué](#sec-28)

---

<a id="sec-01"></a>
## 1. Misión y los ~15 conceptos

### 1.1 Qué es

PenguScript es un lenguaje:

- **estático**, con inferencia local y firmas explícitas en items;
- **de sistemas**, con ownership y movimiento, pero sin lifetimes escritos;
- **propio**, con un backend que el usuario no ve ni edita;
- **chico**, con una superficie que cabe en una tarde de lectura;
- **explícito**, sin coerción implícita, sin excepciones y sin control oculto.

### 1.2 Qué no es

- No es un transpilador de Rust.
- No es un subconjunto de Rust con otro nombre.
- No es un lenguaje de macros.
- No es un lenguaje de concurrencia en el núcleo.
- No es un lenguaje de traits con tipos asociados.
- No es una navaja suiza.

### 1.3 Los 17 conceptos del núcleo

| # | Concepto | Sintaxis |
|---|---|---|
| 1 | Primitivos: `Bool`, `Int`, `Float`, `Char`, `String`, `Unit`, `Never` | — |
| 2 | Tuplas | `(A, B)` |
| 3 | Arrays y slices | `[T; N]`, `&[T]` |
| 4 | Colecciones | `Vec[T]`, `Map[K, V]`, `Set[T]` |
| 5 | Records | `rune` |
| 6 | Sums | `enchanting` |
| 7 | Funciones nombradas | `->` |
| 8 | Closures | `=>` |
| 9 | Genéricos con bounds simples | `[T: Pact]` |
| 10 | Contratos e implementaciones | `pact` / `ritual` |
| 11 | Pattern matching | `match` / `when` / `then` |
| 12 | Errores, ausencia y orden | `Option[T]`, `Result[T, E]`, `Ordering`, `?T`, `?` |
| 13 | Módulos, imports y visibilidad | `scroll` / `summon` / `unveil` |
| 14 | Bindings, mutabilidad y constantes | `bind` / `morph` / `sigil` / `relic` |
| 15 | Control de flujo | `if` / `elseif` / `else`, `for`, `while`, `loop`, `return`, `break`, `continue` |
| 16 | FFI auditada | `foreign` / `curse` |
| 17 | Punto de entrada | `grimoire` |

Estos 17 conceptos son el núcleo. `Show` no es uno adicional: es el pact de
prelude que usan `print` y `format`. Ningún otro keyword entra al núcleo. Si una
sección introduce un concepto que no está en esta tabla, se elimina, se difiere
a §22 o se mueve a la librería estándar.

### 1.4 Valores por defecto, referencias explícitas

Los valores se mueven o se copian; no hay recolección de basura y no hay
lifetimes que el usuario deba escribir. Las referencias `&T` y `&mut T` solo
viven en parámetros y variables locales. Para compartir datos que sobreviven a
una función se usa `Rc[T]` o `Arc[T]`, importados explícitamente.

### 1.5 Ejemplo mínimo

```pengu
rune Point
    x: Float
    y: Float

length = (p: Point) -> Float
    (p.x * p.x + p.y * p.y).sqrt()

grimoire
    bind p = Point(x: 3.0, y: 4.0)
    print(length(p))
```

El programa imprime `5.0`. No hay `main`, no hay `#[...]` y no hay Rust a la
vista: `grimoire` es la entrada.

### 1.6 Criterio de admisión

Una feature entra solo si cumple las cuatro condiciones:

1. Resuelve un problema del 95% del código de sistemas.
2. Se puede explicar en una tabla o en una frase.
3. No duplica otro concepto del núcleo.
4. El backend puede implementarla sin filtraciones en la superficie.

[↑ Volver al índice](#indice)
---

<a id="sec-02"></a>
## 2. Léxico

### 2.1 Archivo y codificación

- Fuente UTF-8 sin BOM. Un BOM es `PGS-E1001`.
- Se aceptan LF y CRLF; CRLF se normaliza a LF.
- La indentación significativa usa **cuatro espacios** por nivel.
- Un tabulador fuera de un string o comentario es `PGS-E1002`.
- Un aumento de indentación que no sea múltiplo de cuatro es `PGS-E1003`.
- Un `DEDENT` que no coincide con ningún nivel abierto es `PGS-E1004`.

### 2.2 Comentarios

```pengu
-- comentario de línea
--[[ comentario de bloque ]]
--- documentación del siguiente item
--! documentación interna del módulo
```

`---` y `--!` son documentación, no comentarios libres. Se procesan en §17.

### 2.3 Identificadores

Un identificador empieza con `XID_Start` o `_` y continúa con `XID_Continue`.
Se permiten letras Unicode, pero no emojis ni marcas de control. Los
identificadores distinguen mayúsculas y minúsculas.

Convenciones:

- `snake_case` para funciones, bindings y campos.
- `PascalCase` para tipos, records, sums, pacts y variantes.
- `SCREAMING_SNAKE_CASE` para `sigil`.

### 2.4 Keywords

La lista completa es corta y cerrada:

| Familia | Keywords |
|---|---|
| Declaraciones | `rune`, `enchanting`, `pact`, `ritual`, `essence`, `scroll`, `summon`, `unveil`, `grimoire`, `foreign`, `curse` |
| Archivos de declaración | `abi` (solo en `.d.pengu`) |
| Tipos de borde | `Ptr` (solo en `.d.pengu`, `foreign` y `curse`) |
| Bindings | `bind`, `morph`, `sigil`, `relic` |
| Control | `if`, `elseif`, `else`, `unless`, `match`, `when`, `then`, `for`, `while`, `loop`, `break`, `continue`, `return`, `do` |
| Operadores | `and`, `or`, `not`, `is`, `isnt`, `in`, `as` |
| Literales | `true`, `false`, `none`, `some`, `ok`, `err` |
| Contextuales | `@`, `@mut`, `@own`, `Self` |

`Vec`, `Map`, `Set`, `Option`, `Result` y `String` son tipos de la prelude, no
keywords. `Self` solo se usa dentro de `pact` y `ritual`.

El lexer rechaza como identificadores estas palabras históricas: `spell`,
`spirit`, `fn`, `def`, `function`, `class`, `this`, `self`, `null`, `nil`,
`try`, `catch`, `throw`, `macro`, `impl`, `trait` y `where` (`PGS-E1010`).
Otros nombres de features eliminadas, como `new` o `switch`, siguen siendo
identificadores válidos; §28.1 describe features, no una lista de palabras
reservadas.

### 2.5 Literales

#### Booleanos y ausencia

```pengu
true
false
none
```

`none` es el único literal de ausencia. No hay `null` ni `nil`.

#### Enteros

```pengu
42
0xFF
0o755
0b1010
1_000_000
42_i64
42_usize
```

Los sufijos son `I8`, `I16`, `I32`, `I64`, `Isize`, `U8`, `U16`, `U32`, `U64`
y `Usize`. Sin sufijo, el contexto decide; si no hay contexto, `Int`.

No hay `I128` ni `U128` en el núcleo. Se importan de `std.int` si hacen falta.

Un literal entero con un dígito inválido para su base, o un prefijo sin
dígitos (`0x`, `0b`, `0o`), es `PGS-E1011`.

#### Flotantes

```pengu
1.5
1.0e10
2.5_f32
```

Sin sufijo, el contexto decide; si no hay contexto, `Float`. No hay `NaN`
literal; se usa `Float.nan()` de la prelude.

Un `.` seguido de un identificador después de un literal entero es acceso a
método, no parte del número: `42.is_even()` es válido. Para un flotante se
escribe `42.0` o `42.0e0`.

#### Char y strings

```pengu
'a'
'\n'
b'P'
"hola"
"hola, #{name}"
"""texto
con varias líneas"""
r"sin \escapes"
b"bytes"
c"cadena C"
```

Un `Char` es un escalar Unicode. Un `byte char` es `U8`; el carácter directo
debe ser ASCII y `\xNN` admite `0x00`–`0xFF`.

`String` es owned; `&Str` es una vista prestada. Un literal de string sin
contexto es `&Str`; donde se espera `String` (retorno, argumento o binding
anotado) el literal se convierte solo, sin `String.from`. En sentido
contrario, un `String` que ya vive en una variable puede pasarse a un
parámetro `&Str`. Esta conversión es la única del lenguaje y no alcanza a los
temporales: prestar el resultado de una llamada exige `as_str`.

La interpolación `#{expr}` solo existe en strings normales y triples. Un
string con partes es `String` (se construye en propiedad); sin partes es
`&Str`. Para escribir `#{` literal se usa `\#{`.

#### Colecciones

```pengu
[1, 2, 3]
[0; 4]
Vec[1, 2, 3]
Map["a": 1, "b": 2]
Set["a", "b"]
(1, "uno")
()
```

Los arrays son de tamaño fijo; `Vec`, `Map` y `Set` son colecciones owned.
La forma indentada con `[]`/`{}` no forma parte del núcleo: la indentación se
reserva para bloques. El `;` de `[0; 4]` y `[T; N]` solo separa la expresión
del tamaño; no es un separador de sentencias.

#### Rangos

```pengu
0..10
0..=10
```

Un rango no es una colección; se usa en `for` y en slices.

### 2.6 Separadores

- `NEWLINE` separa sentencias y elementos de un bloque.
- Dentro de `()`, `[]` y `{}` se permiten saltos de línea; las comas son
  opcionales antes del cierre.
- No se usa `;` como separador.
- La continuación de una expresión después de un operador binario es
  automática si la línea siguiente está más indentada.

### 2.7 Ejemplo

```pengu
grimoire
    bind name = "pengu"
    bind answer = 42
    bind ratio = 1.5
    bind letter = 'P'
    bind bytes = [1, 2, 3]
    bind words = Vec["magic", "static"]
    bind config = Map["name": name, "version": "0.6"]
    print("#{name}: #{answer} / #{ratio} / #{letter}")
```

### 2.8 Diagnósticos del léxico

| Código | Situación |
|---|---|
| `PGS-E1001` | BOM al inicio. |
| `PGS-E1002` | Tabulador en indentación. |
| `PGS-E1003` | Indentación no múltiplo de cuatro. |
| `PGS-E1004` | `DEDENT` sin nivel correspondiente. |
| `PGS-E1005` | String sin cerrar. |
| `PGS-E1006` | Char o byte char sin cerrar. |
| `PGS-E1007` | Escape desconocido. |
| `PGS-E1008` | Byte char no ASCII. |
| `PGS-E1009` | Comentario de bloque sin cerrar. |
| `PGS-E1010` | Término retirado. |
| `PGS-E1011` | Carácter no reconocido o literal numérico inválido. |

[↑ Volver al índice](#indice)
---

<a id="sec-03"></a>
## 3. Programa, módulos y entrada

### 3.1 Archivos y raíces

Un programa PenguScript se compone de archivos `.pengu`.

- La raíz de un binario es `main.pengu`.
- La raíz de una librería es `lib.pengu`.
- Un módulo llamado `geometry` se busca en `geometry.pengu` o en
  `geometry/scroll.pengu`. Si existen ambos, es `PGS-E2013`; no hay orden de
  precedencia.
- Un archivo `geometry.d.pengu` es una **declaración**: aporta tipos y firmas,
  no código. Se resuelve después de las dos formas anteriores y solo si está
  listado en `[declarations]` de `Tome.toml` o es adyacente a la raíz.
- No hay `mod`, `use`, `pub` ni `crate`: esos nombres pertenecen al backend.

### 3.2 Módulos

```pengu
scroll geometry
    rune Point
        x: Float
        y: Float

    unveil norm = (p: Point) -> Float
        (p.x * p.x + p.y * p.y).sqrt()
```

`scroll` declara un módulo en el mismo archivo. También puede declarar un módulo de archivo:

```pengu
scroll geometry
```

En ese caso se carga `geometry.pengu` o `geometry/scroll.pengu`.

Un módulo puede contener records, sums, funciones, constantes, pacts, rituals y
submódulos. No puede contener `bind` ni `morph` en su nivel superior: el estado
global mutable no existe.

La ruta de un módulo es única dentro del tome. `scroll geometry` con cuerpo y
un archivo `geometry.pengu` son el mismo módulo: no hay precedencia, es un
error `PGS-E2013`. Lo mismo pasa si existen `geometry.pengu` y
`geometry/scroll.pengu` a la vez. Las rutas anidadas sí son distintas:
`app::geometry` y `geometry` pueden coexistir.

Resolución de nombres:

- módulos y tipos comparten el espacio de nombres de tipos;
- bindings, funciones, constantes y variantes viven en el espacio de valores;
- un `bind`/`morph` local puede sombrear un valor importado, pero no un módulo
  ni un tipo;
- un `summon` que choca con otro nombre del mismo espacio es `PGS-E2005`;
- `geometry::Point` siempre resuelve el módulo `geometry`, nunca un valor
  local llamado `geometry`.

### 3.3 Imports

```pengu
summon geometry::Point
summon geometry::norm as length
```

`summon` importa un item o un módulo. No hay imports glob. Un nombre importado
puede renombrarse con `as`.

Los items del mismo módulo se ven sin importación. Los items de un submódulo se
importan con su ruta.

Si `summon nombre` no encuentra un `.pengu`, busca un `.d.pengu` declarado en
`[declarations]` o un `nombre.d.pengu` adyacente. Un `.d.pengu` no genera
código: solo contribuye nombres y tipos (§16.7).

### 3.4 Visibilidad

Por defecto todo es privado al módulo.

| Forma | Alcance |
|---|---|
| `unveil` | público |
| `unveil(tome)` | visible en el tome actual |
| `unveil(scroll)` | visible en el módulo padre |

`unveil` se escribe antes del item o del campo de un `rune`; las formas
`unveil(tome)` y `unveil(scroll)` solo se aplican a items. No existe `pub`,
`pub(crate)` ni `pub(in ...)`. Las variantes de un `enchanting` no
tienen visibilidad propia: si el `enchanting` es `unveil`, todas las variantes
son públicas; si no, ninguna. Un campo de variante tampoco lleva `unveil`; un
`unveil` en esa posición es `PGS-E2007`.

```pengu
scroll geometry
    unveil rune Point
        unveil x: Float
        unveil y: Float

    unveil(tome) origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Un campo sin `unveil` solo se lee y se escribe dentro del módulo que declara el
record. Un campo `unveil` puede leerse desde fuera; para escribirlo se usa un
método `@mut`, no una asignación directa.

### 3.5 Entrada

`grimoire` es el punto de entrada del binario. No recibe argumentos y devuelve
`Unit` o `Result[Unit, E]`.

```pengu
rune Args
    program: String
    rest: Vec[String]

grimoire
    print("hola, pengu")
```

Si el `grimoire` declara `Result[Unit, E]`, un `err` se imprime en stderr y el
proceso termina con código 1. Un `return` dentro de `grimoire` es válido y se
tipa contra el retorno declarado, igual que en cualquier función:

- `grimoire` con `Unit`: `return` sin valor;
- `grimoire: Result[Unit, E]`: `return ok(())` o `return err(e)`;
- `return` con un valor incompatible es `PGS-E6006` o `PGS-E7002`.

`return` no es una producción especial de `grimoire`: es una sentencia normal
de `block` (§19.9).

```pengu
enchanting StartError
    MissingName

grimoire: Result[Unit, StartError]
    bind name = "pengu"
    if name.len() == 0 then
        return err(MissingName)
    print(name)
    ok(())
```

No hay `main`, `argc`, `argv` ni `std::env::args` en la superficie: la librería
`std.env` expone `args()` cuando hace falta.

### 3.6 Un programa completo

```pengu
scroll app
    unveil rune Config
        unveil name: String
        unveil verbose: Bool

    unveil load = () -> Config
        Config(name: "pengu", verbose: false)

summon app::load

grimoire
    bind config = load()
    if config.verbose then
        print("modo verboso")
    print(config.name)
```

### 3.7 Tome

Un **tome** es la unidad de compilación. Su manifiesto es `Tome.toml`:

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "0.6"
edition = "2024"

[dependencies]
text = "1.2"

[link]
m = { lib = "m", kind = "shared" }
foo = { lib = "foo", kind = "static" }

[declarations]
libc = "vendor/libc.d.pengu"

[features]
default = []
json = []

[[bin]]
name = "hello"
path = "main.pengu"
```

Solo se aceptan las claves `[tome]`, `[dependencies]`, `[link]`, `[declarations]`,
`[features]`, `[[bin]]`, `[[lib]]`, `[[test]]` y `[[example]]`. No hay `[cargo]`, `[profile]` ni tablas
de tooling: el backend decide esos detalles.

### 3.8 Pipeline

El compilador:

1. lee `Tome.toml`;
2. carga la raíz;
3. lexea, parsea y resuelve nombres;
4. verifica tipos, ownership y visibilidad;
5. baja a su representación interna;
6. emite código al backend;
7. produce el binario o la librería.

Los errores del backend se traducen a diagnósticos PenguScript. El usuario no
edita archivos generados y no ve el código del backend.

Mapeo de errores del backend:

1. Cada fragmento generado tiene un rango en `sourcemap.json` que apunta a un
   rango de PenguScript.
2. El compilador toma el span generado más interno y lo remapea al span de
   PenguScript correspondiente.
3. Si no hay mapeo, usa el item PenguScript que encerró la generación; si
   tampoco existe, reporta `PGS-E2014` con la ubicación generada y el código
   de backend como nota.
4. El mensaje principal siempre es un diagnóstico PenguScript; el código de
   rustc, si existe, aparece solo en la nota, nunca como diagnóstico primario.
5. Un error interno del backend que no se pueda atribuir a un span es
   `PGS-E2014`; no se muestra el código generado salvo con `pengu explain`.

### 3.9 Diagnósticos del programa

| Código | Situación |
|---|---|
| `PGS-E2001` | No se encuentra `Tome.toml`. |
| `PGS-E2002` | Falta `main.pengu` o `lib.pengu`. |
| `PGS-E2003` | Módulo no encontrado. |
| `PGS-E2004` | `summon` de un nombre inexistente. |
| `PGS-E2005` | Import duplicado. |
| `PGS-E2006` | Item privado usado fuera del módulo. |
| `PGS-E2007` | `unveil` inválido en este contexto. |
| `PGS-E2008` | `grimoire` duplicado. |
| `PGS-E2009` | `grimoire` ausente en un binario. |
| `PGS-E2010` | `Tome.toml` inválido. |
| `PGS-E2011` | Dependencia no declarada. |
| `PGS-E2012` | Ciclo de módulos. |
| `PGS-E2013` | Módulo duplicado o ambiguo. |
| `PGS-E2014` | Error del backend sin mapeo a PenguScript. |

[↑ Volver al índice](#indice)
---

<a id="sec-04"></a>
## 4. Tipos

### 4.1 Reglas

- El tipado es estático, fuerte y nominal.
- Las firmas de items son explícitas; las variables locales y las expresiones
  tienen inferencia local.
- No hay `null`, truthiness, coerción implícita ni conversiones automáticas.
- No hay tipos asociados ni tipos de retorno opacos en la superficie.
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

`CStr`, `CString`, `Ptr[T]`, `Option`, `Result` y `Ordering` no son
primitivos:

| Tipo | Dónde vive |
|---|---|
| `CStr`, `CString` | `std.ffi` (§16.3) |
| `Ptr[T]` | tipo de borde de FFI (§4.7) |
| `Option[T]`, `Result[T, E]` | sums de la prelude |
| `Ordering` | sum de la prelude (`Less`, `Equal`, `Greater` son valores) |
| `Range[T]` | rango `inicio..fin` / `inicio..=fin`; `Range[Usize]` para índices |

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
`PGS-E4109` y sugiere mover el valor, usar `Rc[T]`/`Arc[T]` o reestructurar.

### 4.6 Strings

`Str` es una vista prestada de bytes UTF-8. `String` es la versión owned.

```pengu
bind literal: &Str = "pengu"
bind owned: String = "pengu"
bind titulo = "hola #{owned}"
bind vista: &Str = owned
bind joined = owned + "script"
bind copia = String.from(literal)
```

`bind owned: String = "pengu"` convierte el literal porque la anotación pide
`String`; `titulo` es `String` porque la interpolación construye un valor en
propiedad; `vista` presta un `String` que ya es un lugar; `String.from(literal)`
sigue siendo la forma explícita y nunca sobra.

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

`Ordering` es un sum de la prelude con `Less`, `Equal` y `Greater`. Es el
resultado de `Ord.cmp` y no se escribe a mano salvo para implementar `Ord`.

`CStr` y `CString` pertenecen a `std.ffi`, no al núcleo. `CStr` es la vista
prestada de un string C y solo se usa en la frontera FFI; se importa con
`summon std::ffi::CStr`. `CString` es la versión owned y puede fallar con
`NulError`.

`Ptr[T]` es un tipo de borde para punteros opacos de FFI. Solo puede aparecer
en un `.d.pengu`, en una firma `foreign` o en una función `curse`; no se
guarda, no se compara y no se pasa a código PenguScript normal.

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

No hay cláusulas adicionales de bounds. No hay parámetros de tipo con valores; los arrays
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
---

<a id="sec-05"></a>
## 5. Bindings, mutabilidad y constantes

### 5.1 `bind` y `morph`

```pengu
bind name = "pengu"
bind answer = 42
bind typed: Int = 42
morph count = 0
count = count + 1
```

- `bind` crea un binding inmutable. El tipo es opcional (`bind answer: Int = 42`); si se escribe, el checker lo comprueba.
- `morph` crea un binding mutable.
- `=` reasigna un binding `morph`; nunca crea uno nuevo.
- La mutabilidad se declara en el binding, no en el tipo.

No hay `let`, `var`, `const`, `final` ni `mut`.

### 5.2 Sin variables globales

Un módulo no puede declarar `bind` ni `morph` en su nivel superior:

```pengu
-- ERROR PGS-E1101
bind counter = 0
```

El estado global mutable no existe. Para constantes se usa `sigil`; para datos
inmutables compartidos, `relic`.

### 5.3 Scope y sombreado

Un binding vive desde su declaración hasta el final del bloque. Se puede
sombear con otro `bind`/`morph` en un bloque interno, pero no en el mismo
bloque:

```pengu
bind x = 1
if true then
    bind x = 2
    print(x) -- 2
print(x) -- 1
```

```pengu
-- ERROR PGS-E1102
bind x = 1
bind x = 2
```

No hay elevación de declaraciones. Un binding no existe antes de su línea.

### 5.4 Destructuring

```pengu
bind (a, b) = (1, 2)
bind (head, tail) = text.split_at(4_usize)
bind Point(x, y) = Point(x: 3.0, y: 4.0)
bind Point(x: px, y: py) = Point(x: 5.0, y: 6.0)
```

El valor puede ser cualquier expresión: se evalúa una sola vez y se
desestructura el resultado. El patrón debe ser irrefutable. Para patrones refutables se usa `match`,
`if ... then` o `bind ... else`:

```pengu
bind some(value) = maybe else
    return
```

### 5.5 Asignación

```pengu
morph point = Point(x: 1.0, y: 2.0)
point.x = 3.0
point.y = point.y + 1.0
```

Solo se puede asignar a:

- un binding `morph`;
- un campo de un binding `morph`;
- un elemento de un `Vec`/`Map` a través de un binding `morph`;
- un `&mut T` local.

La asignación a un campo `unveil` desde fuera del módulo requiere un método
`@mut`; dentro del módulo, un binding `morph` puede asignarlo. La asignación es
una sentencia, no una expresión. No devuelve valor.

### 5.6 Constantes

`sigil` declara una constante de módulo, evaluada en compilación:

```pengu
sigil MAX_POINTS: Int = 1024
sigil GREETING: &Str = "hola"
sigil ORIGIN: Point = Point(x: 0.0, y: 0.0)
```

Debe tener tipo explícito y una **expresión constante**. Una expresión
constante es una de estas formas, y nada más:

- un literal;
- un cast `as` entre primitivos constantes;
- un operador aritmético, de comparación o booleano entre constantes, con la
  semántica de §14;
- un constructor de `rune` o `enchanting` con campos constantes;
- un array o una tupla de constantes;
- `some`, `none`, `ok` o `err` sobre constantes;
- una referencia a otro `sigil` del mismo módulo.

No hay llamadas a funciones ni a métodos, aunque sean de `std`. Por eso
`sigil X: String = String.from("hi")` no es constante; `sigil X: &Str = "hi"`
sí. Tampoco se permiten `Vec`, `Map` ni `Set` literales, porque asignan en
runtime. No puede depender de `bind`/`morph` locales ni de estado en tiempo de
ejecución.

### 5.7 `relic`

`relic` declara un valor inmutable de módulo, inicializado una vez:

```pengu
relic TABLE: [Int; 4] = [1, 2, 3, 4]
```

No hay `relic mut` ni `static mut`. Un `relic` no se reasigna. Si se necesita
estado compartido mutable, se importa de `std.concurrent` de forma explícita;
no es parte del núcleo.

### 5.8 Nombres

- `bind`/`morph`: `snake_case`.
- `sigil`: `SCREAMING_SNAKE_CASE`.
- `relic`: `SCREAMING_SNAKE_CASE`.

Un `sigil` o `relic` privado se puede usar en todo el módulo. `unveil` lo
expone fuera.

### 5.9 Diagnósticos de bindings

| Código | Situación |
|---|---|
| `PGS-E1101` | `bind`/`morph` en nivel de módulo. |
| `PGS-E1102` | Redeclaración en el mismo bloque. |
| `PGS-E1103` | Asignación a un binding inmutable. |
| `PGS-E1104` | Asignación a un campo privado. |
| `PGS-E1105` | Patrón refutable sin `else`. |
| `PGS-E1106` | `sigil` sin tipo explícito. |
| `PGS-E1107` | `sigil` con expresión no constante. |
| `PGS-E1108` | `relic` reasignado. |
| `PGS-W1101` | Binding local no usado. |
| `PGS-W1102` | Sombreado de un binding. |

[↑ Volver al índice](#indice)
---

<a id="sec-06"></a>
## 6. Expresiones y control

### 6.1 Todo lo que produce un valor es una expresión

Un bloque, un `if`, un `match`, un `loop` y una función producen un valor.
`bind` y la asignación son sentencias. Los items solo se declaran en módulos, `pact` o `ritual`.

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
- `elseif` también funciona en la forma de una línea:
  `if a < b then Less elseif a > b then Greater else Equal`. Dentro de
  paréntesis (por ejemplo como argumento de una llamada) las líneas se
  consideran continuación, así que la forma de una línea es la que se usa en
  lambdas y comparadores.
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
| `PGS-W6001` | Código inalcanzable. |
| `PGS-W6002` | Condición de bucle constante. |
| `PGS-E6007` | `loop` sin `break` usado como valor. |
| `PGS-E6008` | `match` no exhaustivo. |

[↑ Volver al índice](#indice)
---

<a id="sec-07"></a>
## 7. Funciones y closures

### 7.1 Función nombrada

```pengu
add = (a: Int, b: Int) -> Int
    a + b
```

Una función nombrada:

- es un item, no un binding;
- puede estar en el nivel de módulo;
- no captura variables;
- tiene tipo de retorno explícito;
- devuelve la última expresión.

No hay `spell`, `fn`, `def` ni `function`.

### 7.2 Llamada

```pengu
bind total = add(2, 3)
bind inc = add(1, _)
```

No hay aplicación parcial en el núcleo: `_` no es un placeholder. La segunda
línea es un error.

### 7.3 Retorno

```pengu
absolute = (n: Int) -> Int
    if n < 0 then
        return -n
    n
```

`return` sale inmediatamente. La última expresión también es el valor de
retorno; no hace falta escribir `return` al final.

### 7.4 Parámetros

```pengu
repeat = (text: &Str, times: Int) -> String
    bind out = String.new()
    for _ in 0..times do
        out.push_str(text)
    out
```

- Los parámetros se separan con comas.
- Cada parámetro tiene nombre y tipo.
- No hay parámetros opcionales, valores por defecto, varargs ni sobrecarga.
- No hay `morph` en parámetros: un parámetro es inmutable. Para mutar una copia,
  se crea un `morph` local.

### 7.5 Funciones que no retornan

```pengu
fail = (message: &Str) -> Never
    panic(message)
```

`Never` se usa para funciones que siempre fallan o divergen.

### 7.6 Closures

```pengu
bind inc = (x: Int) => x + 1

bind add = (a: Int, b: Int) =>
    a + b
```

Una closure:

- usa `=>`;
- puede capturar variables del scope;
- infiere el tipo de retorno;
- no puede usar `return` ni `?`;
- no puede consumir una captura: solo leerla o mutarla;
- se guarda en un `bind`/`morph` o se pasa como argumento.

La captura es por referencia cuando es posible y por movimiento cuando la
closure escapa o cuando el valor no se puede prestar. No se escribe `move` ni
`ref`; el compilador decide.

Una closure capturada por movimiento sigue siendo invocable varias veces:
puede leer o mutar la captura, pero no moverla fuera. Pasar una captura
no-`Copy` por valor, retornarla o guardarla en otra estructura es
`PGS-E7004`. Si necesitas consumir el valor, pásalo como parámetro o usa
`Rc`/`Arc`.

La inmutabilidad de `bind` impide reasignar la variable que guarda la closure,
no impide que la closure mute sus capturas. El backend puede usar `let mut`
interno para una closure `bind` sin exponer reasignación en PenguScript.

### 7.7 Tipo de función

```pengu
bind op: (Int, Int) -> Int = add
make = (n: Int) -> (Int) -> Int
    (x: Int) => x + n
```

El tipo `(A, B) -> C` describe una función o closure. No hay `Fn`, `FnMut` ni
`FnOnce` en la superficie. Toda función o closure de este tipo se puede llamar
cualquier número de veces; una closure nunca es `FnOnce`. El backend usa
`FnMut` en los parámetros genéricos y `impl FnMut` en los retornos.

### 7.8 Pasar funciones

```pengu
apply = (f: (Int) -> Int, value: Int) -> Int
    f(value)

bind doubled = apply((x: Int) => x * 2, 21)
```

No hay closures genéricas ni polimorfismo de rango superior. Si una función
necesita un tipo distinto, se usa un genérico en la función contenedora.

### 7.9 `grimoire`

`grimoire` no es una función normal: no recibe parámetros y no se llama desde
PenguScript. Se define en §3.

### 7.10 Diagnósticos de funciones

| Código | Situación |
|---|---|
| `PGS-E7001` | Falta el tipo de retorno. |
| `PGS-E7002` | Retorno incompatible con la firma. |
| `PGS-E7003` | Parámetro sin tipo. |
| `PGS-E7004` | `return`, `?` o consumo de una captura en una closure. |
| `PGS-E7005` | Llamada con número de argumentos incorrecto. |
| `PGS-E7006` | Tipo de argumento incorrecto. |
| `PGS-E7007` | Función usada como valor sin tipo. |
| `PGS-E7008` | `Never` en una posición que requiere valor. |

[↑ Volver al índice](#indice)
---

<a id="sec-08"></a>
## 8. Records y sums

### 8.1 Records

```pengu
rune Point
    x: Float
    y: Float

bind p = Point(x: 1.0, y: 2.0)
```

Un `rune` agrupa campos con nombre. Es un tipo nominal: `Point` no es
intercambiable con otro record de la misma forma.

Los campos son privados por defecto. `unveil` los expone:

```pengu
unveil rune Point
    unveil x: Float
    unveil y: Float
```

Un campo `unveil` se lee desde fuera; se modifica a través de un método `@mut`
o de un binding `morph` dentro del módulo.

### 8.2 Records de un campo

```pengu
rune UserId
    value: UInt

bind id = UserId(value: 7)
```

Un record de un campo es un newtype: no se convierte automáticamente en
`UInt`.

### 8.3 Records genéricos

```pengu
rune Box[T]
    value: T

rune Pair[A, B]
    first: A
    second: B

bind pair = Pair(first: 1, second: "uno")
```

Los parámetros de tipo se declaran entre `[]`. Los bounds van en la cabecera:

```pengu
rune Sorted[T: Ord]
    items: Vec[T]
```

### 8.4 Shorthand y actualización

```pengu
bind x = 3.0
bind p = Point(x: x, y: 4.0)
bind q = Point(y: 5.0, ..p)
```

`..p` copia los campos restantes de `p`. El tipo de `q` es el mismo que el de
`p`. Los campos sobrescritos se evalúan una sola vez.

### 8.5 Sums

```pengu
enchanting Shape
    Circle(radius: Float)
    Rectangle(width: Float, height: Float)
    Point
```

Un `enchanting` tiene variantes:

- unitarias (`Point`);
- con campos nombrados (`Circle(radius: Float)`);
- con campos posicionales (`Rectangle(Float, Float)`).

No hay discriminantes numéricos ni representación explícita. El backend elige la representación.

### 8.6 Construcción y match

```pengu
bind c = Circle(radius: 2.0)
bind r = Rectangle(3.0, 4.0)

bind name = match c
    when Circle(radius) then "círculo"
    when Rectangle(width, height) then "rectángulo"
    when Point then "punto"
```

El `match` debe ser exhaustivo o tener `else`. Los detalles están en §9.

### 8.7 `Option` y `Result`

`Option[T]` y `Result[T, E]` son sums de la prelude:

```pengu
enchanting Option[T]
    some(T)
    none

enchanting Result[T, E]
    ok(T)
    err(E)
```

No se pueden redeclarar. `?T` es azúcar para `Option[T]`.

### 8.8 `@@derive`

El único atributo general es `@@derive(...)`, y solo acepta:

`Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`,
`Default`.

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Float
    y: Float
```

Reglas:

- `Copy` exige `Clone` y que todos los campos sean `Copy`.
- `PartialEq` y `PartialOrd` sí se pueden derivar con `Float`.
- `Eq`, `Ord` y `Hash` no se pueden derivar si hay `Float`: `NaN` rompe la
  reflexividad de `Eq`.
- `Float` no puede ser clave de `Map` ni elemento de `Set`, porque ambos exigen
  `Eq + Hash`.
- Para ordenar floats se usa `total_cmp`; `sort` normal no acepta `Float`.
- En un `rune`, `Default` exige que todos los campos tengan valor por defecto.
- En un `enchanting`, `@@derive` se aplica a todas las variantes y campos.
  Se permiten `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`
  y `Hash` si todos los campos lo permiten; `Copy` exige `Clone` y todos los
  campos `Copy`. `Default` no se permite en `enchanting` en 0.6.0.
- Un derive imposible es `PGS-E8007`.
- No hay derives externos en v1.

### 8.9 Diagnósticos de records y sums

| Código | Situación |
|---|---|
| `PGS-E8001` | Campo duplicado. |
| `PGS-E8002` | Campo faltante en la construcción. |
| `PGS-E8003` | Campo desconocido. |
| `PGS-E8004` | Variante duplicada. |
| `PGS-E8005` | `..base` con tipo incompatible. |
| `PGS-E8006` | `@@derive` desconocido. |
| `PGS-E8007` | `@@derive` imposible para un campo. |
| `PGS-E8008` | `Option`/`Result` redeclarados. |

[↑ Volver al índice](#indice)
---

<a id="sec-09"></a>
## 9. Pattern matching

### 9.1 `match`

```pengu
bind area = match shape
    when Circle(radius) then
        3.141592653589793 * radius * radius
    when Rectangle(width, height) then
        width * height
    when Point then
        0.0
```

Cada brazo empieza con `when`, sigue un patrón y termina en `then` o en un
bloque indentado.

`else` cubre el resto:

```pengu
bind label = match n
    when 0 then "cero"
    when 1 then "uno"
    else "muchos"
```

### 9.2 Patrones

| Patrón | Ejemplo |
|---|---|
| Literal | `when 0`, `when "ok"`, `when true` |
| Binding | `when x` |
| Wildcard | `when _` |
| Tupla | `when (a, b)` |
| Record | `when Point(x, y)` |
| Record con nombres | `when Point(x: px, y: py)` |
| Variante unitaria | `when None`, `when FloatClass.NaN` |
| Variante con campos | `when Some(value)` |
| Variante con nombres | `when Circle(radius: r)` |
| Rango | `when 0..=9` |
| Alternativa | `when 0 | 1 | 2` |
| Binding de patrón | `when whole @ Some(_)` |
| Resto | `when Point(x, ..)` |
| Slice | `when [first, .., last]` |

Los literales numéricos de un patrón pueden ser negativos (`when -1`). No hay
patrones de referencia, caja ni tipo.

Las variantes unitarias se pueden nombrar sin calificar (`when Zero`) si el
nombre es único entre las sumas visibles, o calificadas con su tipo
(`when FloatClass.Zero`). `Less`, `Equal` y `Greater` son valores de `Ordering`
utilizables en expresiones y patrones.

### 9.3 Guards

```pengu
bind kind = match n
    when x if x < 0 then "negativo"
    when 0 then "cero"
    else "positivo"
```

Un guard es una expresión `Bool`. Si falla, se prueba el siguiente brazo.

### 9.4 `bind ... else`

Un binding refutable necesita `else`:

```pengu
bind some(value) = maybe else
    return none

bind ok(number) = result else
    return err("no era un número")
```

El `else` debe divergir: `return`, `break`, `continue` o `panic`.

`bind ... else` es una sentencia; no se admite en la cabecera de un `for`
(§19.9). El patrón de `for` es irrefutable. Para filtrar dentro de un bucle,
se usa el cuerpo:

```pengu
for value in values
    bind ok(n) = parse(value) else
        continue
    print(n)
```

### 9.5 Alternativas y anidamiento

```pengu
bind sign = match n
    when -1 | 0 | 1 then "pequeño"
    when x if x < 0 then "negativo"
    else "grande"
```

Los patrones se evalúan de arriba a abajo. El primero que coincide gana.

### 9.6 Exhaustividad

Un `match` sobre un `enchanting` debe cubrir todas las variantes o tener
`else`. Un `match` sobre `Bool` debe cubrir `true` y `false` (o `_`) o tener
`else`; por tanto, esto es válido y exhaustivo:

```pengu
bind label = match flag
    when true then "on"
    when false then "off"
```

Con un solo brazo (`when true`) hace falta `else`. Un `match` sobre un rango de
enteros necesita `else`.

```pengu
-- ERROR PGS-E6008
bind bad = match shape
    when Circle(_) then 1.0
```

### 9.7 `match` como expresión

El tipo del `match` es la unificación de todos los brazos. Un brazo `Never`
no participa.

```pengu
bind message = match result
    when ok(value) then "valor: #{value}"
    when err(reason) then
        panic(reason)
```

### 9.8 Diagnósticos de patrones

| Código | Situación |
|---|---|
| `PGS-E9001` | Patrón no exhaustivo. |
| `PGS-W9001` | Brazo de `match` inalcanzable. |
| `PGS-E9003` | Patrón incompatible con el tipo. |
| `PGS-E9004` | Guard que no es `Bool`. |
| `PGS-E9005` | `bind ... else` sin divergencia. |
| `PGS-E9006` | `..` en posición inválida. |
| `PGS-E9007` | Binding duplicado en un patrón. |
| `PGS-E9008` | `else` después de un brazo exhaustivo. |

[↑ Volver al índice](#indice)
---

<a id="sec-10"></a>
## 10. Colecciones

### 10.1 Arrays

```pengu
bind numbers: [Int; 3] = [1, 2, 3]
bind zeros = [0; 4]
```

Un array tiene tamaño fijo. `[expr; N]` repite `expr` `N` veces. `N` debe ser
un literal o un `sigil` entero.

```pengu
bind first = numbers[0]
bind last = numbers[2]
```

El índice debe ser `Usize`. Un índice fuera de rango hace panic. Para evitar el
panic se usa `numbers.get(i)`, que devuelve `Option[Int]`.

### 10.2 Slices

```pengu
bind view: &[Int] = &numbers
bind middle = &numbers[1..3]
```

Un slice es una vista. No se copia el contenido. `&mut [T]` permite modificar
la vista, no el tamaño.

```pengu
sum = (values: &[Int]) -> Int
    morph total = 0
    for value in values do
        total = total + value
    total
```

### 10.3 `Vec`

```pengu
morph values = Vec[1, 2, 3]
values.push(4)
bind last = values.pop()
```

| Operación | Firma |
|---|---|
| `Vec.new()` | `() -> Vec[T]` |
| `Vec.with_capacity(n)` | `(Usize) -> Vec[T]` |
| `push` | `(@mut, T) -> Unit` |
| `pop` | `(@mut) -> Option[T]` |
| `insert` | `(@mut, Usize, T) -> Unit` |
| `remove` | `(@mut, Usize) -> T` |
| `retain` | `(@mut, (T) -> Bool) -> Unit` |
| `len` | `(@) -> Usize` |
| `is_empty` | `(@) -> Bool` |
| `get` | `(@, Usize) -> Option[&T]` |
| `sort` | `(@mut) -> Unit` |
| `contains` | `(@, &T) -> Bool` |

`Vec[T]` es el tipo de secuencia dinámica del núcleo. `VecDeque`, `LinkedList`
y `BinaryHeap` viven en `std.collections`.

### 10.4 `Map`

```pengu
morph ages = { "ana": 30, "pengu": 2 }
ages.insert("lua", 5)
bind ana = ages.get("ana") -- Option[&Int]
bind removed = ages.remove("lua") -- Option[Int]
```

Las claves deben ser `Eq + Hash`. El orden de iteración no se garantiza.

| Operación | Firma |
|---|---|
| `Map.new()` | `() -> Map[K, V]` |
| `insert` | `(@mut, K, V) -> Option[V]` |
| `get` | `(@, &K) -> Option[&V]` |
| `get_mut` | `(@mut, &K) -> Option[&mut V]` |
| `remove` | `(@mut, &K) -> Option[V]` |
| `contains_key` | `(@, &K) -> Bool` |
| `len` | `(@) -> Usize` |

No hay `map[key]` en el núcleo. Se usa `get`/`insert` para hacer explícita la
ausencia.

### 10.5 `Set`

```pengu
morph tags = Set["magic", "static"]
tags.insert("sharp")
bind has = tags.contains("magic")
```

`Set[T]` requiere `T: Eq + Hash`. No conserva orden.

### 10.6 Literales

```pengu
bind a = [1, 2, 3]
bind b = Vec[1, 2, 3]
bind c = { "a": 1, "b": 2 }
bind d = Set["a", "b"]
```

Las comas finales están permitidas. Un `{` sin `clave: valor` es un error.

### 10.7 Iteración

```pengu
for value in values do
    print(value)

for (key, value) in ages do
    print("#{key}: #{value}")

for tag in tags do
    print(tag)
```

`for` es la única forma de recorrer una colección en el núcleo. No hay métodos
de iterador en la prelude; `std.iter` los provee (incluidos `map`, `filter` y
`collect`) cuando se importan.

### 10.8 Capacidad y movimiento

`Vec`, `Map`, `Set` y `String` son owned. Al pasarlos a una función se mueven,
salvo que se preste una vista (`&[T]`, `&Str`, `&Map[K, V]`).

```pengu
print_all = (values: &[Int]) -> Unit
    for value in values do
        print(value)

morph values = Vec[1, 2]
print_all(&values)
values.push(3) -- sigue siendo dueño
```

### 10.9 Diagnósticos de colecciones

| Código | Situación |
|---|---|
| `PGS-E3101` | Índice fuera de rango en tiempo de compilación. |
| `PGS-E3102` | `Map` con clave sin `Eq`/`Hash`. |
| `PGS-E3103` | `Set` con elemento sin `Eq`/`Hash`. |
| `PGS-E3104` | `Vec` con tipo no inferido. |
| `PGS-E3105` | Literal de mapa con entrada inválida. |
| `PGS-E3106` | `push` sobre un binding inmutable. |

[↑ Volver al índice](#indice)
---

<a id="sec-11"></a>
## 11. Ownership y referencias

### 11.1 Move

Asignar o pasar un valor owned lo **mueve**. Después del movimiento, el binding
original no se puede usar.

```pengu
bind a = String.from("pengu")
bind b = a
-- ERROR PGS-E1103: `a` fue movido
print(a)
```

Para conservar el original se presta (`&a`) o se clona explícitamente
(`a.clone()`).

### 11.2 `Copy`

Los tipos simples se copian en lugar de moverse:

`Bool`, `Int`, `I8`–`I64`, `U8`–`U64`, `Isize`, `Usize`, `Float`, `F32`,
`F64`, `Char`, `Unit`, tuplas de `Copy` y arrays de `Copy`.

```pengu
bind x = 1
bind y = x
print(x) -- válido: Int es Copy
```

Un record puede ser `Copy` solo si todos sus campos lo son y si se deriva con
`@@derive(Copy, Clone)`. `String`, `Vec`, `Map` y `Set` nunca son `Copy`.

### 11.3 `Clone`

`clone()` crea una copia profunda explícita:

```pengu
bind a = Vec[1, 2, 3]
bind b = a.clone()
```

No hay clonado implícito. Pasar un `Vec` a una función que no lo necesita
consume el original; si la función solo lee, recibe `&[T]`.

### 11.4 Referencias

```pengu
length = (s: &Str) -> Usize
    s.len()

append = (values: &mut Vec[Int], value: Int) -> Unit
    values.push(value)
```

Reglas:

- `&T` presta de forma inmutable; `&mut T` presta de forma mutable.
- No puede haber a la vez un `&T` y un `&mut T` al mismo valor.
- Una referencia local no puede escapar de la función que la crea. Un método
  puede devolver una vista ligada al receptor (§11.6).
- No se guardan referencias en campos, variantes, retornos de funciones libres,
  alias ni colecciones.
- No se escribe ninguna anotación de vida. El compilador la infiere.

### 11.5 Referencias en locales

```pengu
bind text = String.from("pengu")
bind view: &Str = &text
print(view)
```

La referencia vive mientras `text` viva y no se mueva. El compilador rechaza
usar `view` después de mover `text`.

### 11.6 Retornos

Una función libre no puede devolver `&T` ni `&mut T`:

```pengu
-- ERROR PGS-E4109
first_word = (text: &Str) -> &Str
    text
```

Para devolver una vista se devuelve el valor owned (`String`), un `Box[String]`
o un `Rc[String]`/`Arc[String]`.

Un método sí puede devolver una referencia si deriva del receptor `@`/`@mut`,
como `Str.get(a..b) -> Option[&Str]`. No puede devolver una referencia a un
local del método.

### 11.7 `Box`, `Rc`, `Arc`

- `Box[T]` es propiedad única en el heap.
- `Rc[T]` comparte dentro de un hilo.
- `Arc[T]` comparte entre hilos.

`Box` está en la prelude. `Rc` y `Arc` se importan:

```pengu
summon std::rc::Rc

bind shared = Rc.new(String.from("pengu"))
bind copy = shared.clone()
print(shared.len())
```

`Rc` y `Arc` no son `Copy`; clonarlos incrementa el contador. No hay
mutabilidad interior en el núcleo: si se necesita, se importa de
`std.cell`/`std.concurrent` y se hace explícita.

### 11.8 Destrucción

El valor se destruye automáticamente al final de su scope. No hay `Drop`
visible ni `defer` en el núcleo. El orden es el inverso al de declaración.

### 11.9 Préstamos y métodos

Un método `@` toma `&self`; `@mut` toma `&mut self`; `@own` toma `self`.
Si un método `@`/`@mut` devuelve un campo cuyo tipo no es `Copy`, debe usar
`@own` (`PGS-E4105`); devolver el campo desde un préstamo exigiría moverlo.

```pengu
rune Counter
    value: Int

ritual Counter
    get = (@) -> Int
        @.value

    bump = (@mut) -> Unit
        @.value = @.value + 1

    into_value = (@own) -> Int
        @.value
```

### 11.10 Diagnósticos de ownership

| Código | Situación |
|---|---|
| `PGS-E4101` | Uso de un valor movido. |
| `PGS-E4102` | Préstamo inmutable y mutable simultáneos. |
| `PGS-E4103` | Asignación a un binding inmutable. |
| `PGS-E4104` | Referencia que escapa del scope. |
| `PGS-E4105` | Referencia en campo/variante/alias/retorno, o método `@`/`@mut` que devuelve un campo no-`Copy` sin `@own`. |
| `PGS-E4106` | Movimiento de un valor prestado. |
| `PGS-E4107` | `Rc`/`Arc` usado sin importar. |
| `PGS-E4108` | Destrucción de un valor todavía prestado. |
| `PGS-E4109` | No se puede inferir la vida de una referencia. |

[↑ Volver al índice](#indice)
---

<a id="sec-12"></a>
## 12. Pacts y rituals

### 12.1 `pact`

Un `pact` declara un contrato de métodos:

```pengu
pact Shape
    area = (@) -> Float
    name = (@) -> String
        "shape"
```

Reglas:

- Solo declara métodos con receptor `@`, `@mut` o `@own`.
- Puede dar una implementación por defecto.
- Puede tener como máximo un superpact.
- No declara tipos asociados, constantes asociadas, métodos genéricos,
  métodos de concurrencia ni cláusulas adicionales de bounds. Un `sigil` o
  `relic` dentro de un `pact` o `ritual` es `PGS-E1204`.
- No se usa como tipo dinámico: no hay despacho dinámico.

### 12.2 Superpact

```pengu
pact Named
    name = (@) -> String

pact Shape: Named
    area = (@) -> Float
```

`Shape` exige que el tipo implemente también `Named`. No hay herencia múltiple.

### 12.3 `Show`

`Show` es el único pact de la prelude:

```pengu
pact Show
    show = (@) -> String
```

`print(x)` y `format("#{x}")` requieren `x: Show` o un primitivo. No hay
`Display` ni `Debug` en la superficie; `@@derive(Debug)` sigue existiendo para
depuración del backend, pero el usuario no lo usa para imprimir.

### 12.4 `ritual` inherente

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Un `ritual` inherente agrega métodos y funciones asociadas al tipo.

- `@` recibe `&self`.
- `@mut` recibe `&mut self`.
- `@own` recibe `self`.
- Una función sin receptor se llama como `Point.origin()`.
- `Self` se refiere al tipo del `ritual`.

### 12.5 `ritual ... for`

```pengu
ritual Point for Shape
    area = (@) -> Float
        0.0

    name = (@) -> String
        "point"
```

Un `ritual Tipo for Pact` implementa el contrato. Deben estar todos los
métodos sin default.

### 12.6 Reglas de coherencia

- Se puede implementar un `pact` propio para un tipo propio.
- Se puede implementar un `pact` de la librería para un tipo propio.
- No se puede implementar un `pact` ajeno para un tipo ajeno.
- No hay impls solapadas.
- No hay blanket impls (`ritual[T] Pact for T`).
- Un tipo puede tener varios `ritual` inherentes, pero no dos métodos con el
  mismo nombre.

### 12.7 Genéricos en rituals

```pengu
rune Box[T]
    value: T

ritual[T] Box[T]
    into_inner = (@own) -> T
        @.value

    replace = (@mut, value: T) -> T
        bind old = @.value
        @.value = value
        old
```

El parámetro `[T]` se declara en el `ritual`. Los bounds van en la cabecera.

### 12.8 Sin despacho dinámico

No hay despacho dinámico ni tablas virtuales. Si se necesita
elegir entre variantes, se usa un `enchanting`:

```pengu
enchanting AnyShape
    Circle(Circle)
    Square(Square)

area = (shape: AnyShape) -> Float
    match shape
        when Circle(c) then c.area()
        when Square(s) then s.area()
```

### 12.9 Diagnósticos de pacts

| Código | Situación |
|---|---|
| `PGS-E1201` | Método faltante en el `ritual`. |
| `PGS-E1202` | Firma incompatible con el `pact`. |
| `PGS-E1203` | `pact` con más de un superpact. |
| `PGS-E1204` | `pact`/`ritual` con asociado no soportado (tipo, `sigil` o `relic`). |
| `PGS-E1205` | `ritual` para tipo ajeno y pact ajeno. |
| `PGS-E1206` | Implementaciones solapadas. |
| `PGS-E1207` | Blanket impl. |
| `PGS-E1208` | Despacho dinámico en la superficie. |
| `PGS-E1209` | `Self` fuera de un `pact`/`ritual`. |
| `PGS-E1210` | `ritual` inherente sobre primitivo fuera de `std`. |
| `PGS-W1210` | Método inherente y de pact con el mismo nombre en un primitivo. |

### 12.10 Rituales sobre primitivos

Los primitivos (`Int`, `I8`–`I64`, `U8`–`U64`, `Isize`, `Usize`, `Float`,
`F32`, `F64`, `Bool`, `Char`, `String`, `Str`) pueden recibir métodos, pero con
una restricción de coherencia:

```pengu
-- inherente: tipo local, o primitivo solo dentro de std
ritual Point
    inherent = (@) -> Float
        0.0

-- pact: tipo local o pact local
ritual Point for Shape
    area = (@) -> Float
        0.0
```

- Un `ritual` **inherente** sobre un primitivo solo se permite dentro de `std`.
  Fuera, es `PGS-E1210`.
- Un `ritual Primitivo for MiPact` se permite en cualquier parte si `MiPact` es
  local. Es la regla huérfana aplicada a primitivos.
- Los métodos inherentes de primitivos son **públicos siempre**; no se escribe
  `unveil`.
- Para tipos `Copy`, el receptor natural es `@own`; para `String`, `@` o `@mut`
  según el método. El autor de `std` elige.
- Si un método inherente y uno de pact comparten nombre en un primitivo, gana el
  inherente y se emite `PGS-W1210`.
- No hay extension methods de usuario. Fuera de `std`, `ritual Int { ... }` es
  error; esto evita ambigüedades de coherencia.

Ejemplos de `std`:

```pengu
-- std/bool.pengu
ritual Bool
    switch = (@own) -> Bool
        not @

-- std/string.pengu
ritual Str
    split = (@, sep: &Str) -> Vec[&Str]
        Vec[]
    trim = (@) -> &Str
        @

-- std/int.pengu
ritual Int
    abs = (@own) -> Int
        if @ < 0 then -@ else @

    is_even = (@own) -> Bool
        @ % 2 == 0
```

Uso:

```pengu
grimoire
    print("  hola  ".trim())
    bind parts = "a,b,c".split(",")
    print(parts.len())
    print(parts[0])
    print(true.switch())
    print((-5).abs())
    print(42.is_even())
```

[↑ Volver al índice](#indice)
---

<a id="sec-13"></a>
## 13. Genéricos y bounds

### 13.1 Declaración

```pengu
identity = [T](value: T) -> T
    value

contains = [T: Eq](values: &[T], target: &T) -> Bool
    for value in values do
        if value == target then
            return true
    false

rune Pair[A, B]
    first: A
    second: B
```

Los parámetros de tipo van entre `[]`, antes de los parámetros de valor.

### 13.2 Bounds

```pengu
maximum = [T: Ord](a: T, b: T) -> T
    if a > b then a else b
```

Un bound es un `pact`. Se pueden pedir varios con `+`:

```pengu
unique = [T: Eq + Hash](values: Vec[T]) -> Set[T]
    morph out = Set.new()
    for value in values do
        out.insert(value)
    out
```

No hay cláusulas adicionales de bounds. No hay bounds de tipo asociado, de vida ni de
constantes.

### 13.3 Llamada

```pengu
bind n = identity[Int](42)
bind s = identity[String](String.from("pengu"))
```

El tipo se puede inferir:

```pengu
bind n = identity(42)
```

Si la inferencia no alcanza, se usa el turbofish `[T]` después del nombre.

### 13.4 Tipos genéricos

```pengu
rune Box[T]
    value: T

enchanting Maybe[T]
    some(T)
    none

pact Container[T]
    contains = (@, target: &T) -> Bool
```

Un tipo genérico se instancia con `Box[Int]`, `Maybe[String]`,
`Container[Point]`.

### 13.5 Genéricos en rituals

```pengu
ritual[T] Box[T]
    into_inner = (@own) -> T
        @.value
```

Los parámetros del `ritual` deben coincidir con los del tipo o con un
subconjunto.

### 13.6 Monomorfización

Cada instancia concreta genera una versión especializada en el backend. No hay
despacho dinámico. El costo es código, no indirección.

### 13.7 Límites

- No hay parámetros de tipo con valores (`const N`).
- No hay tipos asociados.
- No hay tipos de retorno opacos.
- No hay genéricos de rango superior.
- No hay especialización.
- No hay defaults de tipo.

### 13.8 Diagnósticos de genéricos

| Código | Situación |
|---|---|
| `PGS-E1301` | Parámetro de tipo no usado. |
| `PGS-E1302` | Bound no satisfecho. |
| `PGS-E1303` | Bound desconocido. |
| `PGS-E1304` | Turbofish con número incorrecto de tipos. |
| `PGS-E1305` | No se puede inferir el parámetro. |
| `PGS-E1306` | Cláusula de bounds no permitida. |
| `PGS-E1307` | Tipo asociado en un `pact`. |
| `PGS-E1308` | Genérico en un contexto no permitido. |

[↑ Volver al índice](#indice)
---

<a id="sec-14"></a>
## 14. Operadores

### 14.1 Precedencia

De mayor a menor:

| Nivel | Operadores | Asociatividad |
|---|---|---|
| 1 | `.`, `()`, `[]`, `?` | izquierda |
| 2 | unario `-`, `not` | derecha |
| 3 | `as` | izquierda |
| 4 | `*`, `/`, `%` | izquierda |
| 5 | `+`, `-` | izquierda |
| 6 | `..`, `..=` | izquierda |
| 7 | `<`, `<=`, `>`, `>=` | izquierda |
| 8 | `is`, `isnt`, `==`, `!=`, `in` | izquierda |
| 9 | `and` | izquierda |
| 10 | `or` | izquierda |
| 11 | `=` (asignación) | sentencia |

No hay `&&`, `||`, `++`, `--` ni comparaciones encadenadas (`a < b < c` es
error).

### 14.2 Aritméticos

```pengu
bind a = 1 + 2
bind b = 10 - 3
bind c = 4 * 5
bind d = 9 / 2
bind e = 9 % 2
bind f = -a
```

`/` entre enteros trunca hacia cero. La división por cero hace panic, igual
que `MIN / -1` y `MIN % -1` para enteros con signo.

La suma, resta y multiplicación de enteros usan **aritmética comprobada en
todas las builds**, debug y release. Un desbordamiento hace panic; no hay
wrapping silencioso en release. Para aritmética explícita se usan métodos de
`std.int`:

| Método | Resultado |
|---|---|
| `wrapping_add`/`wrapping_sub`/`wrapping_mul` | envuelve, sin panic |
| `checked_add`/`checked_sub`/`checked_mul` | `Option[T]`; `none` si desborda |
| `saturating_add`/`saturating_sub`/`saturating_mul` | satura al mínimo/máximo |
| `overflowing_add`/`overflowing_sub`/`overflowing_mul` | `(T, Bool)` |

Un desbordamiento en una expresión constante es error de compilación. La
excepción son los casts `as`: no son aritmética comprobada, tienen su propia
semántica de truncado o saturación (§14.6) y se aplican igual en `sigil`. El
backend configura `overflow-checks = true` también en release.

`Float` sigue IEEE 754 y no hace panic por overflow: produce `inf`, `-inf` o
`NaN` según el caso.

### 14.3 Comparación

```pengu
a == b
a != b
a < b
a <= b
a > b
a >= b
a is b
a isnt b
```

`is`/`isnt` son alias legibles de `==`/`!=` para tipos que implementan `Eq`.
No comparan identidad de referencia.

`Float` usa IEEE 754:

- `NaN == NaN` es `false`; `NaN != NaN` es `true`;
- `0.0 == -0.0` es `true`;
- cualquier comparación ordenada con `NaN` es `false`;
- `is`/`isnt` exigen `Eq`, así que no se usan con `Float`;
- para ordenar con `NaN` se usa `total_cmp`, no `<`.

No se pueden comparar tipos distintos sin conversión explícita.

### 14.4 Booleanos

```pengu
ready and not cancelled
ready or fallback
```

`and` y `or` hacen cortocircuito. `not` es el único operador de negación
booleana. No hay `!` para `Bool`.

### 14.5 Rangos y pertenencia

```pengu
0..10
0..=10
value in 0..10
```

`in` comprueba pertenencia en un rango, en un `Set` o en un `Map` (clave).

### 14.6 Casts

```pengu
bind small = 300 as U8      -- 44
bind wrapped = -1 as U8     -- 255
bind code = 'P' as U32      -- 80
bind ratio = 2 as Float     -- 2.0
```

`as` solo convierte entre primitivos numéricos y entre `Char` y enteros. No
convierte records, sums, `Bool` ni strings. Para strings se usa `.parse[T]()`;
para números a string, `.to_string()`.

La semántica es la de Rust, sin cambios en runtime ni en const eval:

| Desde | Hasta | Resultado |
|---|---|---|
| entero | entero | trunca al ancho destino (módulo 2^N); `300 as U8` = 44, `-1 as U8` = 255 |
| `Float` | entero | trunca hacia cero y satura al rango; `NaN` -> 0; `inf`/`-inf` -> máximo/mínimo |
| entero | `Float` | redondeo al más cercano; puede perder precisión |
| `Float` | `Float` | redondeo al más cercano; `F64` -> `F32` puede perder precisión |
| `Char` | entero | valor escalar Unicode, truncado al ancho destino |
| `U8` | `Char` | válido para 0..=255 |
| otro entero | `Char` | error de compilación (`PGS-E1404`); usar `Char.from_u32` de `std` |

Un cast nunca hace panic por rango. `300 as U8` es válido y vale 44; un
`sigil X: U8 = 300` sin cast sí es error de compilación. En const eval se
aplica exactamente la misma tabla que en runtime.

### 14.7 `?`

El operador postfix `?` propaga `Option`/`Result`:

```pengu
summon std::fs

read_config = (path: &Str) -> Result[Config, ReadError]
    bind text = fs.read_to_string(path)?
    parse_config(text)
```

- En una función que devuelve `Option[T]`, `?` propaga `none`.
- En una función que devuelve `Result[T, E]`, `?` propaga `err`.
- El error debe convertirse explícitamente si el tipo no coincide.
- `?` no se permite dentro de una closure: no tiene un tipo de retorno
  declarado del cual inferir la propagación. Es `PGS-E7004`; se usa `match` o
  se propaga en la función contenedora.

### 14.8 Sobrecarga

La sobrecarga de operadores es explícita y chica. Los pacts viven en
`std.ops` y se importan:

```pengu
summon std::ops::Add

rune Point
    x: Float
    y: Float

ritual Point for Add
    add = (@own, other: Point) -> Point
        Point(x: @.x + other.x, y: @.y + other.y)

bind p = Point(x: 1.0, y: 2.0) + Point(x: 3.0, y: 4.0)
```

`Ordering` es un sum de la prelude:

```pengu
enchanting Ordering
    Less
    Equal
    Greater
```

Solo se sobrecargan:

| Operador | Pact | Método |
|---|---|---|
| `+` | `Add` | `add` |
| `-` | `Sub` | `sub` |
| `*` | `Mul` | `mul` |
| `/` | `Div` | `div` |
| `%` | `Rem` | `rem` |
| `-` unario | `Neg` | `neg` |
| `==`, `!=` | `Eq` | `eq` |
| `<`, `<=`, `>`, `>=` | `Ord` | `cmp` |

Las firmas son:

- aritméticos: `(@own, other: Self) -> Self`;
- `Eq`: `(@, other: &Self) -> Bool`;
- `Ord`: `(@, other: &Self) -> Ordering`.

`Ord` requiere `Eq`. No hay tipo de salida asociado.

No se sobrecargan `[]`, `()`, `.`, `=`, `&`, `*` de desreferencia, `?`, `!`,
`..` ni `as`. No hay `+=` para tipos de usuario; se escribe `p = p + q`.

### 14.9 Diagnósticos de operadores

| Código | Situación |
|---|---|
| `PGS-E1401` | Tipos incompatibles en un operador. |
| `PGS-E1402` | Operador no definido para el tipo. |
| `PGS-E1403` | División por cero constante. |
| `PGS-E1404` | Cast inválido. |
| `PGS-E1405` | `?` fuera de una función que devuelve `Option`/`Result`. |
| `PGS-E1406` | Sobrecarga de un operador no permitido. |
| `PGS-E1407` | Firma de sobrecarga incorrecta. |
| `PGS-E1408` | Comparación encadenada. |

[↑ Volver al índice](#indice)
---

<a id="sec-15"></a>
## 15. Errores, `Option` y `Result`

### 15.1 Ausencia

`Option[T]` representa un valor que puede faltar:

```pengu
bind maybe: Option[Int] = some(3)
bind nothing: Option[Int] = none
```

Formas cortas:

```pengu
bind maybe: ?Int = some(3)
bind nothing: ?Int = none
```

`?T` es exactamente `Option[T]`. No hay `!T`.

### 15.2 Resultado

`Result[T, E]` representa un éxito o un error:

```pengu
bind ok_value: Result[Int, String] = ok(3)
bind error_value: Result[Int, String] = err("no")
```

`E` es un tipo concreto: un `enchanting`, un `rune` o un primitivo. No hay
errores boxed ni jerarquías de errores.

### 15.3 `?`

```pengu
read_number = (text: &Str) -> Result[Int, ParseError]
    bind n = text.parse[Int]()?
    ok(n + 1)
```

`?`:

- en `Option`, devuelve `none` si el valor es `none`;
- en `Result`, devuelve `err(e)` si el valor es `err(e)`;
- exige que el error del caller sea el mismo tipo, o que se convierta con
  `map_err` antes.

No hay conversión automática de errores.

### 15.4 Métodos de `Option`

| Método | Firma | Nota |
|---|---|---|
| `is_some` | `(@) -> Bool` | no consume |
| `is_none` | `(@) -> Bool` | no consume |
| `unwrap` | `(@own) -> T` | panic si es `none`; solo tests/prototipo |
| `expect` | `(@own, message: &Str) -> T` | panic con mensaje; solo tests/prototipo |
| `unwrap_or` | `(@own, default: T) -> T` | evalúa `default` siempre |
| `unwrap_or_else` | `(@own, f: () -> T) -> T` | evalúa `f` solo si es `none` |
| `map` | `(@own, f: (T) -> U) -> Option[U]` | transforma el valor |
| `and_then` | `(@own, f: (T) -> Option[U]) -> Option[U]` | encadena |
| `filter` | `(@own, f: (T) -> Bool) -> Option[T]` | conserva o descarta |
| `ok_or` | `(@own, err: E) -> Result[T, E]` | convierte a `Result` |
| `take` | `(@mut) -> Option[T]` | deja `none` en el receptor |
| `replace` | `(@mut, value: T) -> Option[T]` | reemplaza y devuelve el anterior |

### 15.5 Métodos de `Result`

| Método | Firma | Nota |
|---|---|---|
| `is_ok` | `(@) -> Bool` | no consume |
| `is_err` | `(@) -> Bool` | no consume |
| `unwrap` | `(@own) -> T` | panic si es `err`; solo tests/prototipo |
| `expect` | `(@own, message: &Str) -> T` | panic con mensaje; solo tests/prototipo |
| `unwrap_or` | `(@own, default: T) -> T` | evalúa `default` siempre |
| `unwrap_or_else` | `(@own, f: (E) -> T) -> T` | evalúa `f` solo si es `err` |
| `map` | `(@own, f: (T) -> U) -> Result[U, E]` | transforma el éxito |
| `map_err` | `(@own, f: (E) -> F) -> Result[T, F]` | transforma el error |
| `and_then` | `(@own, f: (T) -> Result[U, E]) -> Result[U, E]` | encadena |
| `ok` | `(@own) -> Option[T]` | descarta el error |
| `err` | `(@own) -> Option[E]` | descarta el éxito |

`unwrap()` y `expect()` existen solo en tests y en código de prototipo; el
linter los marca en producción. `unwrap_or_else` recibe una closure sin
parámetros y no evalúa el valor por defecto si no hace falta.

### 15.6 Errores como sums

```pengu
summon std::fs

enchanting ConfigError
    MissingFile(path: String)
    InvalidLine(line: Int)
    Empty

read_config = (path: &Str) -> Result[Config, ConfigError]
    bind ok(text) = fs.read_to_string(path) else
        return err(MissingFile(path: String.from(path)))
    parse_config(text)
```

La suma de errores es el mecanismo normal. No hay jerarquía de excepciones.

### 15.7 `panic`

`panic(message)` desenrolla la pila, ejecuta los `Drop` de los valores vivos y
termina el proceso con código 1. Se usa para bugs, no para errores esperables.

```pengu
assert = (condition: Bool, message: &Str) -> Unit
    if not condition then
        panic(message)
```

`panic` es `Never`. No hay `try`, `catch`, `throw` ni `raise`, y no hay forma
de recuperarse de un panic. El backend compila con `panic = "unwind"`; los
`Drop` corren, pero el proceso no continúa. Un panic que alcanza una frontera
`curse`/`foreign` se convierte en abort y nunca cruza a C. `std.concurrent` no
se reutiliza después de un panic: el proceso ya terminó.

### 15.8 Entrada fallible

```pengu
grimoire: Result[Unit, ConfigError]
    bind config = read_config("app.toml")?
    print(config.name)
    ok(())
```

El backend imprime el error y devuelve código 1.

### 15.9 Diagnósticos de errores

| Código | Situación |
|---|---|
| `PGS-E1501` | `?` en función que no devuelve `Option`/`Result`. |
| `PGS-E1502` | Error de `?` incompatible. |
| `PGS-W1501` | `unwrap`/`expect` en producción. |
| `PGS-E1504` | `Option`/`Result` usado como valor directo. |
| `PGS-E1505` | `Result` sin tipo de error concreto. |
| `PGS-E1506` | `panic` en una rama que debía devolver valor. |
| `PGS-E1507` | `err` sin tipo de éxito. |
| `PGS-E1508` | `none` sin tipo. |

[↑ Volver al índice](#indice)
---

<a id="sec-16"></a>
## 16. FFI: `foreign` y `curse`

### 16.1 `foreign`

`foreign "C"` declara funciones externas. No tiene cuerpo y no exporta nada:

```pengu
summon std::ffi::CStr

foreign "C"
    puts = (text: &CStr) -> Int
    strlen = (text: &CStr) -> Usize
```

Un bloque `foreign` solo contiene firmas. No puede contener records, sums ni
funciones con cuerpo.

### 16.2 `curse`

Llamar a una función `foreign` requiere un bloque `curse`:

```pengu
summon std::ffi::CString

say = (text: &Str) -> Unit
    bind ok(c_text) = CString.new(text) else
        return
    curse
        -- SAFETY: `c_text` vive hasta el final del bloque y `puts` no la guarda.
        puts(&c_text)
```

Reglas:

- `curse` es la única puerta a FFI.
- Cada bloque `curse` debe tener un comentario `-- SAFETY:` que explique por
  qué la llamada es válida.
- No hay punteros crudos, conversiones de representación, uniones, asm ni acceso directo a
  memoria.
- No se puede exportar una función PenguScript a C en v1.
- El bloque `curse` no se puede usar para saltarse ownership, tipos ni
  visibilidad.

Una función que siempre requiere `curse` se declara con el modificador:

```pengu
foreign "C"
    read = (fd: Int) -> Int

-- SAFETY: el descriptor lo valida el llamador
curse read_raw = (fd: Int) -> Int
    read(fd)
```

Llamar a `read_raw` también requiere `curse`.

### 16.3 Tipos de FFI

| Penguin | C |
|---|---|
| `Int` | `int32_t` |
| `I64` | `int64_t` |
| `U8` | `uint8_t` |
| `Usize` | `size_t` |
| `Float` | `double` |
| `Bool` | `bool` (solo si el header lo garantiza) |
| `&CStr` | `const char *` |
| `Ptr[T]` | puntero opaco; solo borde FFI |
| `*` | no disponible |

`CStr` y `CString` viven en `std.ffi`. `CString.new` puede fallar si el string
contiene un byte nulo; devuelve `Result[CString, NulError]`.

### 16.4 ABI

- El ABI de `foreign` en un archivo normal es `"C"`.
- `.d.pengu` puede declarar `"C"`, `"system"`, `"js"` o `"pengu"`.
- No hay variádicas.
- Una función `foreign` que puede hacer panic debe documentarlo; el backend
  no deja que un panic cruce la frontera C.
- Los errores de C se convierten en `Result` explícito.

### 16.4.1 Declaraciones desde C

Un archivo `.d.pengu` generado por `pengu bindgen` se registra en `Tome.toml`
y se importa como un módulo:

```toml
[link]
z

[declarations]
zlib = "zlib.d.pengu"
```

`summon zlib::zlibVersion` queda disponible y, como toda firma `foreign "C"`,
solo se puede llamar desde `curse`. Usar una declaración `abi "C"` sin `[link]`
es `PGS-E2023`; el nombre debe ser un identificador (`PGS-E2010`), el archivo
tiene que existir (`PGS-E2003`) y terminar en `.d.pengu` (`PGS-E2020`).

Los punteros `CStr` cruzan la frontera como `*const c_char`: el backend los
convierte con `.as_ptr()` al llamar y con `CStr::from_ptr` al volver, porque
`CStr` no tiene tamaño y una referencia sería un puntero gordo.

### 16.5 Ejemplo completo

```pengu
summon std::ffi::CStr
summon std::ffi::CString

foreign "C"
    puts = (text: &CStr) -> Int

grimoire
    bind ok(message) = CString.new("hola desde PenguScript") else
        panic("string con NUL")
    curse
        -- SAFETY: el CString vive hasta después de la llamada y puts no retiene el puntero.
        puts(&message)
```

### 16.6 Diagnósticos de FFI

| Código | Situación |
|---|---|
| `PGS-E1601` | `foreign` con cuerpo. |
| `PGS-E1602` | Llamada a `foreign` fuera de `curse`. |
| `PGS-E1603` | `curse` sin comentario `-- SAFETY:`. |
| `PGS-E1604` | Tipo no representable en C. |
| `PGS-E1605` | ABI desconocido. |
| `PGS-E1606` | Exportación de función PenguScript a C. |
| `PGS-E1607` | `curse` usado fuera de FFI. |
| `PGS-E1608` | `CString` sin manejo de `NulError`. |

### 16.7 Archivos de declaración y `Ptr[T]`

Un archivo `.d.pengu` distribuye declaraciones sin implementación. Sirve para
FFI nativa, bindings JS y headers de librerías PenguScript.

```pengu
-- libc.d.pengu
abi "C"

summon std::ffi::CStr

rune FILE
    _private: [U8; 0]

puts = (text: &CStr) -> Int
fopen = (path: &CStr, mode: &CStr) -> Ptr[FILE]
fclose = (file: Ptr[FILE]) -> Int
```

La primera línea debe ser `abi "..."`:

| `abi` | Uso | Validación |
|---|---|---|
| `"C"` | FFI nativa (`.dll`, `.so`, `.dylib`) | siempre |
| `"system"` | FFI del sistema | siempre |
| `"js"` | Backend JS, **diferido** | en 0.6.0 siempre `PGS-E2022` |
| `"pengu"` | Librería PenguScript | siempre; requiere implementación |

`abi "C"` y `abi "system"` requieren una entrada en `[link]` de `Tome.toml`
(§18.2), o una dependencia que declare `link`. Sin esa entrada, el build falla
con `PGS-E2023`. `abi "pengu"` y `abi "js"` no usan `[link]`; `abi "js"` no
existe en 0.6.0.

Contenido permitido:

- `rune`, `enchanting` y `pact` con campos, variantes y métodos **sin cuerpo**;
  en un `rune` de `.d.pengu` también se permiten métodos declarados.
- `nombre = (params) -> ret` sin cuerpo.
- `nombre: Type` como constante declarada sin valor.
- `summon`.

Contenido prohibido:

- `grimoire`, `bind`, `morph`, `sigil`, `relic`, `foreign` y cuerpos de
  función.
- Valores por defecto en métodos de `pact`.
- `unveil`: todos los items son públicos implícitamente. `unveil` produce
  `PGS-E2027`.

`Ptr[T]` es un puntero opaco de FFI. Solo se acepta en `.d.pengu`, en firmas
`foreign` y en funciones `curse`; no se guarda, no se compara y no cruza a
código normal.

Dos `.d.pengu` pueden declarar el mismo nombre (`puts`) si pertenecen a módulos
distintos: `libc::puts` y `mylib::puts` son símbolos distintos. El conflicto
solo existe si dos archivos declaran el mismo módulo (`PGS-E2013`) o si se
importan los dos sin alias con `summon` (`PGS-E2005`). Con alias
(`summon libc::puts as c_puts`) no hay conflicto.

Ejemplo de header PenguScript:

```pengu
-- mylib.d.pengu
abi "pengu"

rune Config
    name: String
    verbose: Bool

enchanting LoadError
    Missing
    Invalid(line: Int)

load = (path: &Str) -> Result[Config, LoadError]
```

En `Tome.toml`:

```toml
[declarations]
libc = "vendor/libc.d.pengu"
```

El compilador también busca `nombre.d.pengu` junto a `nombre.pengu`. Una
dependencia puede declarar `declarations = "vendor/mylib.d.pengu"`.

Reglas:

1. Un `.d.pengu` no genera código; solo aporta tipos y nombres.
2. Todos sus items son públicos implícitos.
3. Un método o función sin cuerpo solo es válido en `.d.pengu`.
4. Una constante `nombre: Type` sin valor solo es válida en `.d.pengu`.
5. `abi "js"` siempre es `PGS-E2022` en 0.6.0; el backend JS está diferido.
6. `abi "C"`/`"system"` requiere una entrada en `[link]`; si falta, `PGS-E2023`.
7. `abi "pengu"` requiere una implementación en la misma crate o dependencia.
8. `Ptr[T]` solo se acepta en `.d.pengu`, `foreign` y `curse`.

`foreign "C"` directo y `.d.pengu` con `abi "C"` coexisten: el primero sirve
para casos chicos; el segundo para distribuir una superficie.

| Código | Situación |
|---|---|
| `PGS-E2020` | `.d.pengu` sin cabecera `abi`. |
| `PGS-E2021` | `.d.pengu` con cuerpo, `sigil` o `relic`. |
| `PGS-E2022` | `abi "js"` en 0.6.0; backend JS diferido. |
| `PGS-E2023` | `abi "C"`/`"system"` sin entrada `[link]` o librería no enlazada. |
| `PGS-E2024` | `abi "pengu"` sin implementación. |
| `PGS-E2025` | `Ptr[T]` fuera de `.d.pengu`/`foreign`/`curse`. |
| `PGS-E2026` | `grimoire` en `.d.pengu`. |
| `PGS-E2027` | `unveil` en `.d.pengu`. |

[↑ Volver al índice](#indice)
---

<a id="sec-17"></a>
## 17. Testing y documentación

### 17.1 `@@test`

El único atributo de testing es `@@test`:

```pengu
@@test
adds = () -> Unit
    assert_eq(1 + 1, 2)
```

Una función de test:

- no recibe parámetros;
- devuelve `Unit`; los tests que devuelven `Result[Unit, E]` se difieren a una
  versión futura;
- se ejecuta con `pengu test`;
- puede estar en cualquier módulo.

### 17.2 Variantes

```pengu
@@test(should_panic: "división por cero")
divide_by_zero = () -> Unit
    panic("división por cero")

@@test(ignore: "pendiente de implementar")
future_test = () -> Unit
    assert(false, "pendiente")
```

No hay `@@bench`, `@@should_panic` separado, property testing ni fuzzing en el
núcleo. Viven en `std.test` o en crates externos.

### 17.3 Aserciones

```pengu
assert(condition, "mensaje")
assert_eq(actual, expected)
assert_ne(actual, unexpected)
```

`assert` hace panic con el mensaje si la condición es falsa. `assert_eq` y
`assert_ne` requieren `Debug + PartialEq` y muestran ambos valores.

### 17.4 Tests de integración

`[[test]]` en `Tome.toml`:

```toml
[[test]]
name = "integration"
path = "tests/integration.pengu"
```

El archivo se compila como un binario de test independiente. No hay
No hay compilación condicional de tests: `@@test` marca la función.

### 17.5 Documentación

```pengu
--- Suma dos enteros.
---
--- ```pengu
--- assert_eq(add(1, 2), 3)
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

- `---` documenta el item siguiente.
- `--!` documenta el módulo.
- El contenido es Markdown.
- Los bloques ```pengu se ejecutan como doc tests con `pengu test --doc`.

### 17.6 `@@deprecated` no existe

No hay atributos generales. Para marcar algo como obsoleto se usa la
documentación y el changelog; el linter puede emitir un warning si el nombre
aparece en una lista de migración.

### 17.7 Cobertura

`pengu test --coverage` produce un reporte de líneas y ramas. La cobertura no
es parte de la semántica del lenguaje.

### 17.8 Diagnósticos de testing

| Código | Situación |
|---|---|
| `PGS-E1701` | `@@test` con parámetros. |
| `PGS-E1702` | `@@test` con retorno distinto de `Unit`. |
| `PGS-E1703` | `should_panic` sin mensaje. |
| `PGS-E1704` | `assert_eq` con tipos incompatibles. |
| `PGS-E1705` | Doc test que no compila. |
| `PGS-E1706` | `@@test` duplicado. |

[↑ Volver al índice](#indice)
---

<a id="sec-18"></a>
## 18. Herramientas y tomes

### 18.1 CLI

```text
pengu new <name> | init | templates
pengu add | remove | update | tree | fetch | vendor | outdated
pengu check | build | run | clean | watch
pengu test [--doc] [--coverage]
pengu bench
pengu fmt [--check] | lint | fix | doc [--open]
pengu bindgen | lsp | doctor | explain <code>
pengu metadata | completions <shell> | man
pengu self update
```

No hay `fuzz`, `audit` ni `deny` en el núcleo. Se instalan como herramientas
externas. `debug` y `repl` están reservados.

### 18.2 `Tome.toml`

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "0.6"
edition = "2024"

[dependencies]
json = { git = "https://github.com/pengu/json", tag = "v1.2.0" }
local = { path = "../local" }

[link]
m = { lib = "m", kind = "shared" }
foo = { lib = "foo", kind = "static" }

[declarations]
libc = "vendor/libc.d.pengu"

[features]
default = []
json = []

[[bin]]
name = "hello"
path = "main.pengu"

[[lib]]
name = "hello"
path = "lib.pengu"

[[test]]
name = "integration"
path = "tests/integration.pengu"
```

Reglas:

- `name`, `version`, `pengu` y `edition` son obligatorios.
- `pengu` declara la versión mínima del compilador.
- Las dependencias son **git o path**; no hay registry central ni crates.
- Una dependencia git declara `git` y exactamente uno de `tag`, `branch` o
  `rev`; `pengu add` elige un tag si existe y, si no, `branch = "main"` con
  advertencia.
- Una dependencia path declara `path`, relativo a la raíz del paquete.
- Una dependencia acepta `features` (lista), `default-features` (bool,
  por defecto `true`) y `optional` (bool, por defecto `false`); una dependencia
  opcional se activa con una feature del mismo nombre. Las features se unen.
- `[link]` declara librerías nativas para `foreign` y `.d.pengu` con
  `abi "C"`/`"system"`. Cada entrada exige `lib` y acepta `kind = "shared"`
  (por defecto) o `kind = "static"`.
- Una dependencia puede declarar su propio `link = { lib = "...", kind = "..." }`;
  se une al `[link]` del paquete.
- `[declarations]` lista archivos `.d.pengu` que se cargan como módulos de
  declaraciones; no generan código.
- Una dependencia puede declarar `declarations = "ruta.d.pengu"`.
- `features` del paquete son aditivas.
- No hay `[cargo]`, `[profile]`, `[tool.*]` ni scripts de build.

### 18.3 Lockfile

`Tome.lock` registra los commits y checksums exactos. Se genera con
`pengu build` y se versiona en la aplicación. `pengu update` lo actualiza. Es
TOML, igual que `Tome.toml`:

```toml
version = 1

[[package]]
name = "json"
version = "0.3.1"
source = "git+https://github.com/pengu/json?tag=v1.2.0"
commit = "9f1c..."
checksum = "sha256-..."
features = ["std"]
dependencies = ["text"]

[[package]]
name = "text"
version = "1.2.3"
source = "git+https://github.com/pengu/text?rev=4a7d..."
commit = "4a7d..."
checksum = "sha256-..."
features = []
dependencies = []
```

Reglas:

- `version` es la versión del formato del lockfile; en `0.6.0` es `1`.
- Cada `[[package]]` tiene `name`, `version`, `source`, `checksum`, `features`
  y `dependencies`.
- `source` es canónico: `git+URL?tag=...`, `?branch=...`, `?rev=...`, o
  `path+../local`.
- `commit` es obligatorio para git; no se emite para path.
- `checksum` es SHA-256 del árbol empaquetado y es obligatorio.
- `dependencies` son nombres exactos, no rangos; solo hay una versión por
  nombre en el grafo.
- Las entradas se ordenan por `name`.
- El lockfile no se edita a mano; `pengu` lo reescribe.
- Un lockfile con formato desconocido, campos faltantes o checksum inválido es
  `PGS-E1808`; uno válido pero incompatible con `Tome.toml` es `PGS-E1804`.

#### 18.3.1 Resolución de dependencias

No hay registry, rangos SemVer de dependencias ni solver SAT en `0.6.0`. El
resolver es determinista y simple:

1. Lee `[dependencies]`; cada nombre aparece una sola vez.
2. Resuelve git: `tag` o `branch` a su commit actual, o usa `rev`; `path` lee
   el `Tome.toml` local.
3. Un commit/versión por nombre; si dos entradas piden fuentes o features
   incompatibles, emite `PGS-E1807`.
4. Une las features pedidas por todos los consumidores (son aditivas).
5. Si `Tome.lock` existe, usa commits/checksums exactos; si no coincide con
   `Tome.toml`, emite `PGS-E1804`.
6. `pengu update` re-resuelve `branch`/`tag` a su commit actual e ignora el
   lock; `pengu build` respeta el lock. Un `rev` no se mueve.

No se permiten dos versiones del mismo paquete en el grafo. Las dependencias
path se tratan como locales y su checksum se calcula del árbol.

### 18.4 Formatter

`pengu fmt` aplica:

- cuatro espacios por nivel;
- un espacio después de `:` en tipos;
- sin espacios dentro de `[]` y `()`;
- una coma por elemento, con coma final permitida;
- líneas de hasta 100 columnas.

No hay configuración por proyecto en v1. Las diferencias se reportan con
`pengu fmt --check`.

### 18.5 Linter

`pengu lint` detecta:

- bindings no usados (`PGS-W1101`);
- sombreado de bindings (`PGS-W1102`);
- imports no usados (`PGS-W2001`);
- `unwrap`/`expect` en producción (`PGS-W1501`);
- comparaciones redundantes;
- `if` que puede ser `match`;
- código inalcanzable (`PGS-W6001`);
- condiciones de bucle constantes (`PGS-W6002`);
- brazos de `match` inalcanzables (`PGS-W9001`);
- nombres que no siguen la convención.

Los warnings se pueden silenciar con `pengu lint --allow <code>`; no hay
atributos de lint en el código.

### 18.6 LSP

`pengu lsp` ofrece:

- diagnóstico al guardar;
- autocompletado de nombres y campos;
- ir a definición;
- buscar referencias;
- renombrar;
- formato.

No hay refactors avanzados ni generación de código.

### 18.7 Reproducibilidad

Un build es reproducible si:

- `Tome.lock` está presente;
- la versión de `pengu` coincide con `pengu` del manifiesto;
- no se usan rutas absolutas;
- no se lee el entorno durante la compilación.

El backend puede producir artefactos idénticos con `--remap-path-prefix`.

### 18.8 Diagnósticos de tooling

| Código | Situación |
|---|---|
| `PGS-E1802` | Versión de `pengu` incompatible. |
| `PGS-E1803` | Dependencia o librería de `[link]` no encontrada. |
| `PGS-E1804` | Lockfile desactualizado. |
| `PGS-E1805` | `pengu fmt` no puede formatear. |
| `PGS-E1806` | Dependencia git sin `tag`/`branch`/`rev` o ref inválido. |
| `PGS-E1807` | Conflicto de dependencias por nombre, fuente o features. |
| `PGS-E1808` | `Tome.lock` inválido o con checksum incorrecto. |
| `PGS-W2001` | Import no usado. |

[↑ Volver al índice](#indice)
---

<a id="sec-19"></a>
## 19. Gramática

La gramática usa `NEWLINE`, `INDENT` y `DEDENT` producidos por el lexer. Los
terminales léxicos se definen en §2.

### 19.1 Programa

```ebnf
program        ::= item*
item           ::= scroll_def | summon_def | rune_def | enchanting_def
                 | pact_def | ritual_def | essence_def | foreign_def
                 | function_def | const_def | static_def | grimoire_def
                 | test_def
visibility     ::= "unveil" ("(" ("tome" | "scroll") ")")?

scroll_def     ::= "scroll" IDENT (NEWLINE INDENT item* DEDENT)?
summon_def     ::= "summon" path ("as" IDENT)?
path           ::= IDENT ("::" IDENT)*
```

### 19.2 Records y sums

```ebnf
rune_def       ::= derive_attr? visibility? "rune" IDENT type_params? NEWLINE INDENT field+ DEDENT
field          ::= "unveil"? IDENT ":" type

enchanting_def ::= derive_attr? visibility? "enchanting" IDENT type_params? NEWLINE INDENT variant+ DEDENT
variant        ::= variant_name (variant_fields)?
variant_name   ::= IDENT | "some" | "none" | "ok" | "err"
variant_fields ::= "(" (named_field ("," named_field)* | type ("," type)* ","?)? ")"
named_field    ::= IDENT ":" type
```

### 19.2.1 Alias de tipo

```ebnf
essence_def    ::= visibility? "essence" IDENT type_params? "=" type
```

`essence` no crea un tipo nominal; el checker la sustituye por el tipo de la
derecha.

### 19.3 Pacts y rituals

```ebnf
pact_def       ::= visibility? "pact" IDENT type_params? (":" path)? NEWLINE INDENT pact_item+ DEDENT
pact_item      ::= method_sig | method_def

ritual_def     ::= visibility? "ritual" type_params? type ("for" path)? NEWLINE INDENT ritual_item+ DEDENT
ritual_item    ::= method_def | function_def | const_def

method_sig     ::= IDENT "=" receiver "(" params? ")" "->" type
method_def     ::= IDENT "=" receiver "(" params? ")" "->" type NEWLINE INDENT block DEDENT
receiver       ::= "@" | "@mut" | "@own"
const_def      ::= ("sigil" | "relic") IDENT ":" type "=" const_expr
```

Un `ritual` puede declarar métodos, funciones asociadas (`Tipo.metodo(args)`) y
constantes asociadas (`Tipo.NOMBRE`, con `sigil` o `relic`). El lenguaje ya
define `Int.MIN/MAX/BITS`, `Float.EPSILON/MIN/MAX/MIN_POSITIVE/NAN/INFINITY/
NEG_INFINITY` y `Char.from_u32/from_digit` en la stdlib; las constantes
asociadas se leen con la misma sintaxis `Tipo.NOMBRE` en cualquier expresión
constante.

### 19.4 Tipos

```ebnf
type           ::= "?" type
                 | "&" "mut"? type
                 | "[" type ";" expr "]"
                 | "(" ")"
                 | "(" type "," ")"
                 | "(" type ("," type)+ ","? ")"
                 | path type_args?
                 | "[" type ("," type)* ","? "]"
                 | function_type
                 | "Self"
                 | ptr_type

function_type  ::= "(" (type ("," type)* ","?)? ")" "->" type
ptr_type       ::= "Ptr" "[" type "]"

type_args      ::= "[" type ("," type)* ","? "]"
type_params    ::= "[" type_param ("," type_param)* ","? "]"
type_param     ::= IDENT (":" bound ("+" bound)*)?
bound          ::= path
```

`Self` solo es válido dentro de `pact` y `ritual`. No hay despacho dinámico ni anotaciones de vida. `Ptr[T]` es la única
construcción de borde para FFI; se reconoce por el nombre `Ptr` y no puede
usarse como identificador de usuario.

### 19.5 Funciones

```ebnf
function_def   ::= visibility? "curse"? IDENT "=" type_params? "(" params? ")" "->" type
                   NEWLINE INDENT block DEDENT
params         ::= param ("," param)* ","?
param          ::= IDENT ":" type

grimoire_def   ::= "grimoire" (":" type)? NEWLINE INDENT block DEDENT
```

`grimoire` usa un `block` normal, así que `return` ya está permitido como
`return_stmt`; no hay una producción especial. El tipo del `return` se compara
con el tipo declarado de `grimoire`.

### 19.6 Constantes y estáticos

```ebnf
const_def      ::= visibility? "sigil" IDENT ":" type "=" expr
static_def     ::= visibility? "relic" IDENT ":" type "=" expr
```

### 19.7 FFI

```ebnf
foreign_def    ::= "foreign" STRING NEWLINE INDENT foreign_item+ DEDENT
foreign_item   ::= IDENT "=" "(" params? ")" "->" type
```

`foreign` no tiene cuerpos. `curse` aparece en `function_def` y en bloques.

### 19.8 Expresiones

```ebnf
expr           ::= or_expr
or_expr        ::= and_expr ("or" and_expr)*
and_expr       ::= comparison ("and" comparison)*
comparison     ::= range (comp_op range)?
comp_op        ::= "==" | "!=" | "<" | "<=" | ">" | ">=" | "is" | "isnt" | "in"
range          ::= additive (".." "="? additive)?
additive       ::= multiplicative (("+" | "-") multiplicative)*
multiplicative ::= cast (("*" | "/" | "%") cast)*
cast           ::= unary ("as" type)*
unary          ::= ("-" | "not" | "&" "mut"?) unary | postfix
postfix        ::= primary (("." (IDENT ("(" args? ")")? | INT)) | "(" args? ")" | "[" expr "]" | "?")*
primary        ::= literal | path | "(" expr ")" | tuple | array | vector
                 | map | map_lit | set | record
                 | if_expr | match_expr | do_expr | loop_expr | curse_expr | lambda

record         ::= path "(" record_field ("," record_field)* ","? ")"
record_field   ::= IDENT ":" expr | ".." expr

if_expr        ::= "if" expr "then" expr
                 | "if" expr "then" expr "else" expr
                 | "if" expr "then" expr ("elseif" expr "then" expr)*
                   ("else" expr)?
                 | "if" expr "then" NEWLINE INDENT block DEDENT
                   ("elseif" expr "then" NEWLINE INDENT block DEDENT)*
                   ("else" NEWLINE INDENT block DEDENT)?
                 | "unless" expr "then" expr
                 | "unless" expr "then" expr "else" expr
                 | "unless" expr "then" NEWLINE INDENT block DEDENT
                   ("else" NEWLINE INDENT block DEDENT)?
match_expr     ::= "match" expr NEWLINE INDENT match_arm+ DEDENT
do_expr        ::= "do" NEWLINE INDENT block DEDENT
loop_expr      ::= "loop" NEWLINE INDENT block DEDENT
curse_expr     ::= "curse" NEWLINE INDENT block DEDENT
lambda         ::= "(" params? ")" "=>" expr
                 | "(" params? ")" "=>" NEWLINE INDENT block DEDENT

tuple          ::= "(" ")" | "(" expr "," ")" | "(" expr ("," expr)+ ","? ")"
array          ::= "[" "]" | "[" expr ("," expr)* ","? "]"
                 | "[" expr ";" expr "]"
vector         ::= "Vec" "[" "]" | "Vec" "[" expr ("," expr)* ","? "]"
map            ::= "{" "}" | "{" map_entry ("," map_entry)* ","? "}"
map_lit        ::= "Map" "[" "]" | "Map" "[" map_entry ("," map_entry)* ","? "]"
map_entry      ::= expr ":" expr
set            ::= "Set" "[" "]" | "Set" "[" expr ("," expr)* ","? "]"
```

`Vec`, `Map` y `Set` no son keywords. En expresión, un `IDENT` exacto
`Vec`/`Map`/`Set` seguido de `[` se parsea como literal; en tipo,
`Vec[T]`/`Map[K, V]`/`Set[T]` es `path` + `type_args`.

### 19.9 Sentencias

```ebnf
block          ::= statement+
statement      ::= binding | assignment | expr | while_stmt
                 | for_stmt | return_stmt | break_stmt | continue_stmt

binding        ::= ("bind" | "morph") pattern (":" type)? "=" binding_value
                   ("else" NEWLINE INDENT block DEDENT)?
binding_value  ::= expr | NEWLINE INDENT block DEDENT
assignment     ::= expr "=" expr

while_stmt     ::= "while" expr "do"? NEWLINE INDENT block DEDENT
for_stmt       ::= "for" pattern "in" expr "do"? NEWLINE INDENT block DEDENT
return_stmt    ::= "return" expr?
break_stmt     ::= "break" expr?
continue_stmt  ::= "continue"
```

### 19.10 Patrones

```ebnf
pattern        ::= literal
                 | "_"
                 | IDENT
                 | IDENT "@" pattern
                 | "(" pattern ("," pattern)* ","? ")"
                 | path "(" pattern ("," pattern)* ","? ")"
                 | path "(" named_pattern ("," named_pattern)* ","? ")"
                 | path
                 | pattern "|" pattern
                 | pattern ".." pattern?
                 | "[" pattern ("," pattern)* ","? "]"

named_pattern  ::= IDENT ":" pattern
```

### 19.11 Atributos y tests

```ebnf
test_def       ::= "@@test" ("(" test_opt ("," test_opt)* ")")? NEWLINE
                   IDENT "=" "(" ")" "->" type NEWLINE INDENT block DEDENT
test_opt       ::= "should_panic" ":" STRING | "ignore" ":" STRING

derive_attr    ::= "@@derive" "(" IDENT ("," IDENT)* ")"
```

Solo existen `@@test` y `@@derive`. No hay otros atributos.

### 19.12 Match

```ebnf
match_arm      ::= "when" pattern ("if" expr)? "then" expr
                 | "when" pattern ("if" expr)? "then"? NEWLINE INDENT block DEDENT
                 | "else" expr
                 | "else" NEWLINE INDENT block DEDENT
```

### 19.13 Restricciones

- `else` es obligatorio si el `match` no es exhaustivo.
- Un `break` con valor solo es válido dentro de `loop`.
- `?` solo es válido en funciones que devuelven `Option` o `Result`.
- `@`, `@mut` y `@own` solo son válidos como receptores de métodos o en patrones de binding.
- `Self` solo es válido dentro de `pact` y `ritual`.
- `bind ... else` solo es una sentencia; no se admite en la cabecera de `for`.
- Las variantes de `enchanting` no llevan `unveil`; heredan la visibilidad del
  `enchanting`.
- Un módulo y un tipo no pueden compartir nombre en el mismo ámbito.

### 19.14 Archivos de declaración

```ebnf
decl_file      ::= abi_decl item_decl*
abi_decl       ::= "abi" STRING NEWLINE
item_decl      ::= rune_decl | enchanting_decl | pact_decl
                 | function_decl | const_decl | summon_def

rune_decl      ::= "rune" IDENT type_params? NEWLINE (INDENT decl_member+ DEDENT)?
decl_member    ::= field_decl | method_decl

field_decl     ::= IDENT ":" type

enchanting_decl ::= "enchanting" IDENT type_params? NEWLINE INDENT decl_variant+ DEDENT
decl_variant   ::= IDENT variant_fields?

pact_decl      ::= "pact" IDENT type_params? (":" path)? NEWLINE INDENT method_decl+ DEDENT
method_decl    ::= IDENT "=" receiver "(" params? ")" "->" type
function_decl  ::= IDENT "=" "(" params? ")" "->" type
const_decl     ::= IDENT ":" type
```

Un `rune` de `.d.pengu` puede declarar métodos; en un `.pengu` normal los
métodos van en un `ritual`. `method_decl` no lleva cuerpo y `pact_decl` no
admite defaults. `const_decl` no lleva `=`.

[↑ Volver al índice](#indice)
---

<a id="sec-20"></a>
## 20. Diagnósticos

El compilador emite códigos estables. Un error impide compilar; un warning no.

El catálogo tiene **160 códigos** (152 errores, 8 warnings), en el límite de 160 del núcleo.

### 20.1 Formato

```text
PGS-E3001: tipos incompatibles
  --> src/main.pengu:12:9
   |
12 |     bind x: Int = "pengu"
   |                   ^^^^^^^ se esperaba `Int`
```

Cada diagnóstico incluye: código, mensaje, archivo, línea, columna, fragmento y una solución cuando existe.

### 20.2 Catálogo

| Código | Situación |
|---|---|
| `PGS-E1001` | BOM al inicio. |
| `PGS-E1002` | Tabulador en indentación. |
| `PGS-E1003` | Indentación no múltiplo de cuatro. |
| `PGS-E1004` | `DEDENT` sin nivel correspondiente. |
| `PGS-E1005` | String sin cerrar. |
| `PGS-E1006` | Char o byte char sin cerrar. |
| `PGS-E1007` | Escape desconocido. |
| `PGS-E1008` | Byte char no ASCII. |
| `PGS-E1009` | Comentario de bloque sin cerrar. |
| `PGS-E1010` | Término retirado. |
| `PGS-E1011` | Carácter no reconocido o literal numérico inválido. |
| `PGS-E1101` | `bind`/`morph` en nivel de módulo. |
| `PGS-E1102` | Redeclaración en el mismo bloque. |
| `PGS-E1103` | Asignación a un binding inmutable. |
| `PGS-E1104` | Asignación a un campo privado. |
| `PGS-E1105` | Patrón refutable sin `else`. |
| `PGS-E1106` | `sigil` sin tipo explícito. |
| `PGS-E1107` | `sigil` con expresión no constante. |
| `PGS-E1108` | `relic` reasignado. |
| `PGS-E1201` | Método faltante en el `ritual`. |
| `PGS-E1202` | Firma incompatible con el `pact`. |
| `PGS-E1203` | `pact` con más de un superpact. |
| `PGS-E1204` | `pact`/`ritual` con asociado no soportado (tipo, `sigil` o `relic`). |
| `PGS-E1205` | `ritual` para tipo ajeno y pact ajeno. |
| `PGS-E1206` | Implementaciones solapadas. |
| `PGS-E1207` | Blanket impl. |
| `PGS-E1208` | Despacho dinámico en la superficie. |
| `PGS-E1209` | `Self` fuera de un `pact`/`ritual`. |
| `PGS-E1210` | `ritual` inherente sobre primitivo fuera de `std`. |
| `PGS-W1210` | Método inherente y de pact con el mismo nombre en un primitivo. |
| `PGS-E1301` | Parámetro de tipo no usado. |
| `PGS-E1302` | Bound no satisfecho. |
| `PGS-E1303` | Bound desconocido. |
| `PGS-E1304` | Turbofish con número incorrecto de tipos. |
| `PGS-E1305` | No se puede inferir el parámetro. |
| `PGS-E1306` | Cláusula de bounds no permitida. |
| `PGS-E1307` | Tipo asociado en un `pact`. |
| `PGS-E1308` | Genérico en un contexto no permitido. |
| `PGS-E1401` | Tipos incompatibles en un operador. |
| `PGS-E1402` | Operador no definido para el tipo. |
| `PGS-E1403` | División por cero constante. |
| `PGS-E1404` | Cast inválido. |
| `PGS-E1405` | `?` fuera de una función que devuelve `Option`/`Result`. |
| `PGS-E1406` | Sobrecarga de un operador no permitido. |
| `PGS-E1407` | Firma de sobrecarga incorrecta. |
| `PGS-E1408` | Comparación encadenada. |
| `PGS-E1501` | `?` en función que no devuelve `Option`/`Result`. |
| `PGS-E1502` | Error de `?` incompatible. |
| `PGS-W1501` | `unwrap`/`expect` en producción. |
| `PGS-E1504` | `Option`/`Result` usado como valor directo. |
| `PGS-E1505` | `Result` sin tipo de error concreto. |
| `PGS-E1506` | `panic` en una rama que debía devolver valor. |
| `PGS-E1507` | `err` sin tipo de éxito. |
| `PGS-E1508` | `none` sin tipo. |
| `PGS-E1601` | `foreign` con cuerpo. |
| `PGS-E1602` | Llamada a `foreign` fuera de `curse`. |
| `PGS-E1603` | `curse` sin comentario `-- SAFETY:`. |
| `PGS-E1604` | Tipo no representable en C. |
| `PGS-E1605` | ABI desconocido. |
| `PGS-E1606` | Exportación de función PenguScript a C. |
| `PGS-E1607` | `curse` usado fuera de FFI. |
| `PGS-E1608` | `CString` sin manejo de `NulError`. |
| `PGS-E1701` | `@@test` con parámetros. |
| `PGS-E1702` | `@@test` con retorno distinto de `Unit`. |
| `PGS-E1703` | `should_panic` sin mensaje. |
| `PGS-E1704` | `assert_eq` con tipos incompatibles. |
| `PGS-E1705` | Doc test que no compila. |
| `PGS-E1706` | `@@test` duplicado. |
| `PGS-E1802` | Versión de `pengu` incompatible. |
| `PGS-E1803` | Dependencia o librería de `[link]` no encontrada. |
| `PGS-E1804` | Lockfile desactualizado. |
| `PGS-E1805` | `pengu fmt` no puede formatear. |
| `PGS-E1806` | Dependencia git sin `tag`/`branch`/`rev` o ref inválido. |
| `PGS-E1807` | Conflicto de dependencias por nombre, fuente o features. |
| `PGS-E1808` | `Tome.lock` inválido o con checksum incorrecto. |
| `PGS-E1901` | Error de sintaxis. |
| `PGS-E2001` | No se encuentra `Tome.toml`. |
| `PGS-E2002` | Falta `main.pengu` o `lib.pengu`. |
| `PGS-E2003` | Módulo no encontrado. |
| `PGS-E2004` | `summon` de un nombre inexistente. |
| `PGS-E2005` | Import duplicado. |
| `PGS-E2006` | Item privado usado fuera del módulo. |
| `PGS-E2007` | `unveil` inválido en este contexto. |
| `PGS-E2008` | `grimoire` duplicado. |
| `PGS-E2009` | `grimoire` ausente en un binario. |
| `PGS-E2010` | `Tome.toml` inválido. |
| `PGS-E2011` | Dependencia no declarada. |
| `PGS-E2012` | Ciclo de módulos. |
| `PGS-E2013` | Módulo duplicado o ambiguo. |
| `PGS-E2014` | Error del backend sin mapeo a PenguScript. |
| `PGS-E2020` | `.d.pengu` sin cabecera `abi`. |
| `PGS-E2021` | `.d.pengu` con cuerpo, `sigil` o `relic`. |
| `PGS-E2022` | `abi "js"` en 0.6.0; backend JS diferido. |
| `PGS-E2023` | `abi "C"`/`"system"` sin entrada `[link]` o librería no enlazada. |
| `PGS-E2024` | `abi "pengu"` sin implementación. |
| `PGS-E2025` | `Ptr[T]` fuera de `.d.pengu`/`foreign`/`curse`. |
| `PGS-E2026` | `grimoire` en `.d.pengu`. |
| `PGS-E2027` | `unveil` en `.d.pengu`. |
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
| `PGS-E3101` | Índice fuera de rango en tiempo de compilación. |
| `PGS-E3102` | `Map` con clave sin `Eq`/`Hash`. |
| `PGS-E3103` | `Set` con elemento sin `Eq`/`Hash`. |
| `PGS-E3104` | `Vec` con tipo no inferido. |
| `PGS-E3105` | Literal de mapa con entrada inválida. |
| `PGS-E3106` | `push` sobre un binding inmutable. |
| `PGS-E4101` | Uso de un valor movido. |
| `PGS-E4102` | Préstamo inmutable y mutable simultáneos. |
| `PGS-E4103` | Asignación a un binding inmutable. |
| `PGS-E4104` | Referencia que escapa del scope. |
| `PGS-E4105` | Referencia en campo/variante/retorno, o método `@`/`@mut` que devuelve un campo no-`Copy` sin `@own`. |
| `PGS-E4106` | Movimiento de un valor prestado. |
| `PGS-E4107` | `Rc`/`Arc` usado sin importar. |
| `PGS-E4108` | Destrucción de un valor todavía prestado. |
| `PGS-E4109` | No se puede inferir la vida de una referencia. |
| `PGS-W1101` | Binding local no usado. |
| `PGS-W1102` | Sombreado de un binding. |
| `PGS-W2001` | Import no usado. |
| `PGS-W6001` | Código inalcanzable. |
| `PGS-W6002` | Condición de bucle constante. |
| `PGS-E6001` | Condición que no es `Bool`. |
| `PGS-E6002` | Ramas de `if` con tipos incompatibles. |
| `PGS-E6003` | `else` sin `if`. |
| `PGS-E6004` | `break`/`continue` fuera de un bucle. |
| `PGS-E6005` | `break` con valor fuera de `loop`. |
| `PGS-E6006` | `return` con valor en función `Unit`. |
| `PGS-E6007` | `loop` sin `break` usado como valor. |
| `PGS-E6008` | `match` no exhaustivo. |
| `PGS-E7001` | Falta el tipo de retorno. |
| `PGS-E7002` | Retorno incompatible con la firma. |
| `PGS-E7003` | Parámetro sin tipo. |
| `PGS-E7004` | `return`, `?` o consumo de una captura en una closure. |
| `PGS-E7005` | Llamada con número de argumentos incorrecto. |
| `PGS-E7006` | Tipo de argumento incorrecto. |
| `PGS-E7007` | Función usada como valor sin tipo. |
| `PGS-E7008` | `Never` en una posición que requiere valor. |
| `PGS-E8001` | Campo duplicado. |
| `PGS-E8002` | Campo faltante en la construcción. |
| `PGS-E8003` | Campo desconocido. |
| `PGS-E8004` | Variante duplicada. |
| `PGS-E8005` | `..base` con tipo incompatible. |
| `PGS-E8006` | `@@derive` desconocido. |
| `PGS-E8007` | `@@derive` imposible para un campo. |
| `PGS-E8008` | `Option`/`Result` redeclarados. |
| `PGS-E9001` | Patrón no exhaustivo. |
| `PGS-W9001` | Brazo de `match` inalcanzable. |
| `PGS-E9003` | Patrón incompatible con el tipo. |
| `PGS-E9004` | Guard que no es `Bool`. |
| `PGS-E9005` | `bind ... else` sin divergencia. |
| `PGS-E9006` | `..` en posición inválida. |
| `PGS-E9007` | Binding duplicado en un patrón. |
| `PGS-E9008` | `else` después de un brazo exhaustivo. |

### 20.3 Reglas

- Un código no cambia de significado entre versiones menores.
- Un código retirado no se reutiliza.
- `pengu explain <código>` muestra la explicación y un ejemplo.
- Los warnings se pueden silenciar con `pengu lint --allow <código>`.

[↑ Volver al índice](#indice)
---

<a id="sec-21"></a>
## 21. Garantías del lenguaje

### 21.1 Qué garantiza PenguScript

| Aspecto | Estado | Nota |
|---|---|---|
| Sin `null` | Core | La ausencia se modela con `Option[T]`. |
| Sin lectura de memoria liberada | Core | Ownership y préstamos. |
| Sin carreras de datos en código seguro | Core | Sin hilos en el núcleo; `std.concurrent` expone concurrencia segura. |
| Sin recolección de basura | Core | Destrucción determinista al final del scope. |
| Sin conversiones implícitas | Core | `as`, `.parse[T]()` y `.to_string()` son explícitos. |
| Sin excepciones | Core | `Result[T, E]` y `?`. |
| Sin truthiness | Core | Las condiciones son `Bool`. |
| Sin `switch` con fallthrough | Core | `match` exhaustivo. |
| Sin macros de usuario | Core | Solo `@@derive` y `@@test`. |
| Sin despacho dinámico | Core | Sums + `match`. |
| Sin anotaciones de vida | Core | El compilador infiere y prohíbe escapes. |
| Sin `unsafe` general | Core | `curse` solo para FFI. |
| Sin estado global mutable | Core | `sigil` y `relic` son inmutables. |
| Sin imports globales | Core | `summon` explícito. |
| Sin dependencias ocultas | Core | `Tome.toml` declara todo. |
| Sin código generado editable | Core | El backend es invisible. |
| Sin hilos/atomics en el núcleo | Diferido | `std.concurrent`. |
| Sin `Rc`/`Arc` en la prelude | Std | Se importan. |
| `Box` en la prelude | Core | `Box[T]` está disponible. |
| `Vec`/`Map`/`Set` en la prelude | Core | Están disponibles por defecto. |
| Sin `CStr`/`CString` en la prelude | Std | Se importan para FFI. |
| Sin `BTreeMap`/`BTreeSet` | Std | `std.collections`. |
| Sin `VecDeque`/`LinkedList`/`BinaryHeap` | Std | `std.collections`. |
| Sin `Cell`/`RefCell`/`Mutex`/`RwLock` | Std | `std.cell`/`std.concurrent`. |
| Sin `format!`/`print!` visibles | Core | `print`/`format` son funciones del compilador. |
| Sin `assert!`/`panic!` visibles | Core | `assert`/`panic` son funciones. |
| Sin `derive` externos | Core | Solo los nueve built-in. |
| Sin tests por atributos múltiples | Core | `@@test` con opciones. |
| Sin ABI estable de PenguScript | No soportado | Solo `foreign "C"` de entrada. |
| Sin exportación a C | No soportado | v1. |
| Sin genéricos de rango superior | No soportado | Fuera del núcleo. |
| Sin `const` genéricos | No soportado | Arrays con `N` literal. |
| Sin especialización | No soportado | Fuera del núcleo. |

### 21.2 Límites

- PenguScript no garantiza un layout de memoria estable.
- No garantiza un ABI estable entre versiones.
- No garantiza que el backend produzca el mismo código máquina entre
  versiones; sí garantiza el mismo comportamiento observable.
- La cobertura de tests no es una garantía de corrección.

### 21.3 Lo que el usuario puede asumir

1. Un programa que compila no tiene lecturas de memoria liberada, carreras de
   datos en código seguro ni `null`.
2. Los errores esperables se modelan con `Result`; los bugs con `panic`.
3. Un `match` sin `else` es exhaustivo.
4. Un binding `bind` no cambia; uno `morph` sí.
5. Un valor se mueve o se copia de forma predecible.
6. El backend no filtra tipos, atributos ni sintaxis a la superficie.

[↑ Volver al índice](#indice)
---

<a id="sec-22"></a>
## 22. Diferido y no soportado

Esta sección **no es normativa para el código de usuario**. Lista lo que queda
fuera del núcleo y su alternativa.

### 22.1 Fuera del núcleo

| Área | Estado | Alternativa |
|---|---|---|
| Anotaciones de vida (`'a`, `'static`) | No soportado | Referencias solo en parámetros/locales; el compilador infiere. |
| `for<'a>` / rango superior | No soportado | Usar funciones concretas o sums. |
| `where` | No soportado | Bounds en la cabecera `[T: Pact]`. |
| Tipos asociados | No soportado | Usar un parámetro de tipo o un `enchanting`. |
| GATs | No soportado | Usar `Vec`/`String` owned. |
| `dyn` / objetos de trait | No soportado | `enchanting` + `match`. |
| `impl Trait` | No soportado | Tipo concreto, `Box[T]` o `enchanting`. |
| `async` / `await` | Diferido | `std.async` con runtime externo. |
| Backend JS / `abi "js"` | Diferido | En 0.6.0 solo existe el backend Rust. |
| Hilos, canales, atomics | Diferido | `std.concurrent`. |
| `Rc` / `Arc` en la prelude | Std | `summon std::rc::Rc` / `std::sync::Arc`. |
| `Cell` / `RefCell` | Std | `std.cell`, explícito. |
| `Mutex` / `RwLock` | Std | `std.concurrent`, explícito. |
| `Box` en la prelude | Core | Disponible. |
| `Pin` / `Future` | Diferido | `std.async`. |
| `unsafe` general | No soportado | `curse` solo para FFI. |
| Punteros crudos | No soportado | Sin acceso directo a memoria. |
| `transmute` / uniones / asm | No soportado | Reestructurar el código. |
| Macros de usuario | No soportado | Funciones y `std.meta` no existe en v1. |
| Atributos generales | No soportado | Solo `@@derive` y `@@test`. |
| `repr` / layout estable | No soportado | El backend decide. |
| Build scripts | Diferido | `std.build` o un crate externo. |
| `I128` / `U128` | Std | `std.int`. |
| `BTreeMap` / `BTreeSet` | Std | `std.collections`. |
| `VecDeque` / `LinkedList` / `BinaryHeap` | Std | `std.collections`. |
| `Cow` | Std | `std.borrow`. |
| `Weak` | Std | `std.rc`/`std.sync`. |
| `Index` / `IndexMut` sobrecargables | No soportado | Método `.at(i)` o `get`. |
| `Deref` / `DerefMut` | No soportado | Acceso explícito a campos. |
| `From` / `Into` implícitos | No soportado | `.to_string()`, `.parse[T]()`, `as`. |
| `Display` / `Debug` sobrecargables | No soportado | `Show` y `@@derive(Debug)`. |
| `Drop` visible | No soportado | Destrucción automática. |
| Exportar funciones a C | No soportado | v1. |
| Variádicas C | No soportado | Funciones C concretas. |
| Bench/fuzz/property testing | Std | Herramientas externas. |
| `cfg` / `test` / `inline` / `must_use` | No soportado | El backend decide. |

### 22.2 Por qué

El criterio es siempre el mismo: si una feature no da potencia para el 95% del
código, no entra. Las que sí entran se simplifican hasta caber en una línea.

### 22.3 Lo que se puede importar

La librería estándar es chica:

`std.io`, `std.fs`, `std.process`, `std.env`, `std.time`, `std.math`,
`std.string`, `std.collections`, `std.iter`, `std.ffi`, `std.rc`, `std.sync`,
`std.cell`, `std.async`, `std.test`, `std.ops`.

Todo lo demás es un crate externo.

[↑ Volver al índice](#indice)
---

<a id="sec-23"></a>
## 23. Glosario

**Backend filoso.** El compilador que traduce PenguScript a código máquina.
Es invisible para el usuario; no se edita ni se ve.

**Karambit.** Metáfora del lenguaje: chico, curvo, filoso, capaz. No una navaja
suiza.

**Núcleo.** Los ~15 conceptos de §1. Todo lo demás es `std` o no existe.

**Prelude.** Nombres disponibles sin `summon`: tipos primitivos, `Option`,
`Result`, `Vec`, `Map`, `Set`, `String`, `Box`, `print`, `format`, `panic`,
`assert`, `Show`, `Ordering`, `none`, `some`, `ok`, `err`.

**Binding.** Nombre que posee un valor. `bind` es inmutable; `morph` es mutable.

**Record.** Tipo producto con campos con nombre. Se declara con `rune`.

**Sum.** Tipo con variantes. Se declara con `enchanting`.

**Newtype.** Record de un solo campo; no se convierte solo en su campo.

**Pact.** Contrato de métodos con receptor. Se declara con `pact`.

**Ritual.** Implementación de métodos o de un pact. Se declara con `ritual`.

**`Show`.** Único pact de la prelude; lo usan `print` y `format`.

**`Ordering`.** Sum de la prelude con `Less`, `Equal` y `Greater`; resultado de
`Ord.cmp`.

**Tome.** Unidad de compilación; su manifiesto es `Tome.toml`.

**Scroll.** Módulo. Puede ser inline o un archivo.

**Summon.** Import explícito de un nombre o módulo.

**Unveil.** Visibilidad pública (o acotada con `(tome)`/`(scroll)`).

**Grimoire.** Punto de entrada del binario.

**Ownership.** Regla de un único dueño para los valores owned.

**Préstamo.** Referencia temporal `&T`/`&mut T`; no escapa del scope.

**Move.** Transferencia de propiedad; el origen deja de ser usable.

**Copy.** Copia implícita de tipos simples.

**Clone.** Copia profunda explícita con `.clone()`.

**Option.** Tipo que representa ausencia: `some(T)` o `none`.

**Result.** Tipo que representa éxito o error: `ok(T)` o `err(E)`.

**`?`.** Operador que propaga `none`/`err` al caller.

**Patrón.** Forma que se compara con un valor en `match` o `bind ... else`.

**Exhaustivo.** Un `match` que cubre todos los casos sin `else`.

**FFI.** Frontera con C. Se declara con `foreign` o un `.d.pengu` y se llama
dentro de `curse`.

**Curse.** Bloque auditado que permite llamar a FFI.

**`.d.pengu`.** Archivo de declaraciones sin implementación; distribuye tipos y
firmas para FFI, JS o headers PenguScript.

**`abi`.** Cabecera obligatoria de un `.d.pengu`: `"C"`, `"system"`, `"js"` o
`"pengu"`.

**`Ptr[T]`.** Puntero opaco de FFI; solo existe en `.d.pengu`, `foreign` y
`curse`.

**Diferido.** Fuera del núcleo por ahora; puede volver en una versión mayor.

[↑ Volver al índice](#indice)
---

<a id="sec-24"></a>
## 24. Cookbook

### 24.1 Hola

```pengu
grimoire
    print("hola, pengu")
```

### 24.2 Argumentos

```pengu
summon std::env

grimoire
    bind args = env.args()
    if args.len() > 1 then
        print(args[1])
    else
        print("sin argumentos")
```

### 24.3 Leer un archivo

```pengu
summon std::fs

enchanting ReadError
    Missing(path: String)
    Invalid

read_config = (path: &Str) -> Result[String, ReadError]
    bind ok(text) = fs.read_to_string(path) else
        return err(Missing(String.from(path)))
    ok(text)
```

### 24.4 Propagar errores

```pengu
enchanting AppError
    Read(ReadError)
    Parse

load = (path: &Str) -> Result[String, AppError]
    bind text = read_config(path).map_err((e: ReadError) => Read(e))?
    ok(text)
```

### 24.5 CLI con código de salida

```pengu
grimoire: Result[Unit, AppError]
    bind text = load("app.toml")?
    print(text)
    ok(())
```

Si el `Result` es `err`, el backend imprime el error y sale con código 1.

### 24.6 Records y sums

```pengu
rune User
    name: String
    age: Int

enchanting Role
    Admin
    Member
    Guest

describe = (user: User, role: Role) -> String
    match role
        when Admin then "#{user.name} (admin)"
        when Member then "#{user.name} (member)"
        when Guest then "#{user.name} (invitado)"
```

### 24.7 Colecciones

```pengu
morph counts = { "a": 1, "b": 2 }
counts.insert("c", 3)

morph names = Vec["ana", "pengu"]
names.push("lua")

morph tags = Set["magic", "static"]
tags.insert("sharp")

for (key, value) in counts do
    print("#{key} = #{value}")
```

### 24.8 Patrones

```pengu
bind (x, y) = (1, 2)
bind Point(px, py) = Point(x: 3.0, y: 4.0)

bind status = match result
    when ok(value) then "ok: #{value}"
    when err(reason) then "error: #{reason}"
```

### 24.9 Un método

```pengu
rune Counter
    value: Int

ritual Counter
    bump = (@mut) -> Unit
        @.value = @.value + 1

    get = (@) -> Int
        @.value

morph counter = Counter(value: 0)
counter.bump()
print(counter.get())
```

### 24.10 FFI

```pengu
summon std::ffi::CString

foreign "C"
    puts = (text: &CStr) -> Int

grimoire
    bind ok(message) = CString.new("hola") else
        panic("NUL")
    curse
        -- SAFETY: el CString vive hasta después de puts y puts no retiene el puntero.
        puts(&message)
```

### 24.11 Test

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@test
adds = () -> Unit
    assert_eq(add(1, 2), 3)
```

### 24.12 Librería

```pengu
-- lib.pengu
unveil rune Greeting
    unveil text: String

unveil greet = (name: &Str) -> Greeting
    Greeting(text: "hola, #{name}")
```

### 24.13 Métodos sobre primitivos

```pengu
grimoire
    bind name = "  pengu  ".trim()
    bind parts = "a,b,c".split(",")
    print(name)
    print(parts.len())
```

### 24.14 `.d.pengu`

```pengu
-- libc.d.pengu
abi "C"

rune FILE
    _private: [U8; 0]

puts = (text: &CStr) -> Int
fopen = (path: &CStr, mode: &CStr) -> Ptr[FILE]
fclose = (file: Ptr[FILE]) -> Int
```

[↑ Volver al índice](#indice)
---

<a id="sec-25"></a>
## 25. Decisiones de diseño (ADR)

### 25.1 ADR anteriores

Las decisiones D0–D25 de la spec `1.0.0-rc.1` quedan **superadas** por el nuevo
rumbo. Se conservan en `scratch/legacy/LANGUAGE_rc1.md` como historia, no como
norma. Ninguna se cita en las secciones normativas de este documento.

### D26. Lenguaje propio con backend invisible

**Contexto:** la spec anterior se presentaba como un lenguaje que compilaba a
otro lenguaje y exponía sus tipos.

**Decisión:** PenguScript es un lenguaje propio. El backend es un detalle de
implementación; el usuario no escribe ni ve su código.

**Alternativas:** seguir siendo un transpilador; generar código directamente.

**Consecuencias:** la superficie se juzga por sí misma, no por paridad. Los
errores del backend se traducen a diagnósticos propios.

### D27. Minimalismo de ~15 conceptos

**Contexto:** la spec anterior tenía 71 secciones y más de 400 diagnósticos.

**Decisión:** el núcleo tiene los conceptos de §1. Todo lo demás es `std`, una
herramienta externa o no existe.

**Consecuencias:** se eliminan familias enteras de features y se recorta el
catálogo a 160 códigos como máximo.

### D28. Referencias sin anotaciones de vida

**Contexto:** el usuario no debe aprender un sistema de vidas para escribir
código de sistemas.

**Decisión:** `&T`/`&mut T` solo en parámetros y locales. El compilador infiere;
si la referencia escapa, error `PGS-E4109`. No se guardan referencias en
records, sums, retornos ni alias.

**Alternativas:** exigir anotaciones; copiar siempre; usar solo valores owned.

**Consecuencias:** se pierden vistas persistentes; se ganan reglas simples y
un backend que puede inferir el resto.

### D29. Operadores minimalistas

**Contexto:** la sobrecarga de operadores puede volverse un lenguaje dentro del
lenguaje.

**Decisión:** solo `Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Eq` y `Ord`, con
`Self` contra `Self`, en `std.ops`. Sin tipos asociados. `[]`, `Deref`, `From`
y `Display` no se sobrecargan.

**Consecuencias:** menos magia; los tipos que necesitan indexación usan
métodos con nombre.

### D30. FFI de entrada

**Contexto:** exportar funciones a C obliga a estabilizar ABI y tipos.

**Decisión:** v1 solo importa funciones C con `foreign "C"`. No exporta
funciones PenguScript. `curse` es la frontera auditada.

**Consecuencias:** FFI como puerta, no como grieta. La exportación se difiere.

### D31. Sin macros ni atributos generales

**Contexto:** las macros y los atributos son una superficie enorme.

**Decisión:** no hay macros de usuario. Solo `@@derive` y `@@test`. El resto de
los atributos son detalles del backend.

**Consecuencias:** se pierde metaprogramación; se gana un lenguaje que se lee
completo.

### D32. `?T` sí, `!T` no

**Contexto:** dos azúcares para `Option` y `Result` duplican conceptos.

**Decisión:** `?T` es `Option[T]`. Los errores se escriben `Result[T, E]`
explícito.

**Consecuencias:** una sola forma corta; el error siempre tiene tipo concreto.

### D33. `Rc`/`Arc` fuera de la prelude

**Contexto:** compartir con contadores es una decisión de costo visible.

**Decisión:** `Rc` y `Arc` se importan de `std`. La prelude solo tiene `Box`,
`Vec`, `String`, `Map`, `Set` y `Option`/`Result`. `Box` se queda porque es
propiedad única, no compartición: no introduce contadores ni ciclos.

**Consecuencias:** el costo de compartir se ve en el import.

### D34. Karambit

**Contexto:** la tentación de agregar features “porque el backend puede”.

**Decisión:** la ausencia de features es una feature. Cada adición debe pagar
su costo en superficie, diagnóstico y documentación.

**Consecuencias:** el documento se mantiene corto; las features dudosas van a
§22.

### D35. Rituales inherentes sobre primitivos solo en `std`

**Contexto:** los métodos sobre primitivos mejoran la ergonomía, pero las
extension methods de usuario rompen la coherencia y la predictibilidad.

**Decisión:** `ritual Primitivo` inherente solo se permite en `std`. Un
`ritual Primitivo for PactoLocal` se permite en cualquier parte porque el pacto
es local. Fuera de `std`, el inherente es `PGS-E1210`; una colisión de nombres
emite `PGS-W1210`.

**Consecuencias:** `std` gana métodos naturales; el usuario no puede agregar
métodos a tipos ajenos.

### D36. `.d.pengu` y `Ptr[T]`

**Contexto:** hace falta distribuir declaraciones de FFI, JS y librerías sin
implementación, sin abrir raw pointers en el lenguaje.

**Decisión:** `.d.pengu` declara tipos y firmas con una cabecera `abi`; no
genera código y todo es público implícito. Los opacos de C usan `Ptr[T]`, un
tipo de borde permitido solo en `.d.pengu`, `foreign` y `curse`.

**Consecuencias:** FFI y headers se distribuyen; `Ptr[T]` no contamina el
código normal.

### D37. Dependencias git/path, sin registry

**Contexto.** El lenguaje no tiene un registry central y el usuario pidió
dependencias por git. Un registry añade infraestructura, versionado y
publicación que no existen en 0.6.0.

**Decisión.** `[dependencies]` solo acepta entradas git (`tag`, `branch` o
`rev`) o `path`. `Tome.lock` fija commit y checksum. No hay `pengu publish`.
La resolución no usa rangos SemVer ni SAT: un ref/commit por nombre.

**Alternativas.** Registry propio (descartado por infraestructura y
publicación); libgit2 (descartado por licencia y portabilidad); rangos
SemVer sobre tags (diferido, no necesario para v1).

**Consecuencias.** `pengu update` mueve branches/tags; los tags deberían ser
inmutables. La reproducibilidad depende de commit + checksum. El costo es
que no hay un índice central de paquetes.

[↑ Volver al índice](#indice)
---

<a id="sec-26"></a>
## 26. Changelog

### 26.1 Versión

| Componente | Versión |
|---|---|
| Spec | `0.6.0` |
| Compilador | `0.6.0` |
| Edición | `2024` |
| Backend mínimo | `1.85.0` |

`0.5.0` fue una reescritura mayor, no un release candidate. `0.6.0` agrega
features y cambia el modelo de paquetes; ver §26.4.

### 26.2 `0.6.0` — métodos en primitivos y `.d.pengu`

- `ritual` inherente sobre primitivos solo dentro de `std`; un pact local
  sobre un primitivo se permite en cualquier parte. Códigos `PGS-E1210` y
  `PGS-W1210`.
- `.d.pengu` para distribuir declaraciones con cabecera `abi "C"`, `"system"`,
  `"js"` o `"pengu"`; sin cuerpos, sin `grimoire`, sin `sigil`/`relic`, sin
  `unveil`.
- `Ptr[T]` como puntero opaco de FFI, solo en `.d.pengu`, `foreign` y `curse`.
- `[declarations]` y `[link]` en `Tome.toml`; `abi "C"`/`"system"` exige
  entrada de enlace (`PGS-E2023`).
- Casts `as` con tabla explícita (truncado entero, saturación flotante,
  `NaN` -> 0) y misma semántica en const eval.
- `?` prohibido en closures; `PGS-E7004` cubre `return`, `?` y consumo de
  capturas.
- `abi "js"` diferido; en 0.6.0 siempre `PGS-E2022`. Solo backend Rust.
- `sigil`/`relic` no se permiten en `pact`/`ritual`; `PGS-E1204`.
- `panic` desenrolla, ejecuta `Drop` y termina; cruzar FFI aborta.
- `sigil` solo acepta literales, casts, operadores, constructores, arrays,
  tuplas, `some`/`none`/`ok`/`err` y otros `sigil`; sin llamadas.
- `.d.pengu` de módulos distintos pueden repetir nombres; conflicto solo por
  módulo duplicado (`PGS-E2013`) o import sin alias (`PGS-E2005`).
- Dependencias **git o path**, sin registry ni crates; `Tome.lock` registra
  commit y checksum; `pengu publish` se retira y `PGS-E1806` pasa a ref git
  inválido.
- Cierre de huecos semánticos: overflow comprobado siempre, comparaciones
  IEEE de `Float`, formato y resolución de `Tome.lock`, mapeo de errores del
  backend, módulos duplicados, `CStr` en `std.ffi`, firmas completas de
  `Option`/`Result`, `match` sobre `Bool`, `return` en `grimoire`,
  `bind ... else` en cuerpos de bucle y visibilidad de variantes.
- Cierre de parser/checker: `Vec[...]`/`Map[...]` en la gramática; closures
  nunca `FnOnce` y sin consumo de capturas (`PGS-E7004`); `@@derive` en
  `enchanting` sin `Default`; `@@test` solo devuelve `Unit`.
- Catálogo de 160 códigos (152 errores, 8 warnings); límite de 160.
- ADR D35, D36 y D37.

### 26.3 `0.5.0` — reescritura de misión

- PenguScript deja de presentarse como un transpilador y pasa a ser un lenguaje
  propio con backend invisible.
- Núcleo reducido a ~15 conceptos.
- Referencias sin anotaciones de vida; prohibidas en records, sums, retornos y
  alias.
- Pacts minimalistas: solo métodos con receptor, un superpact como máximo, sin
  tipos asociados.
- Operadores limitados a `std.ops`; sin `Index`, `Deref`, `From` ni `Display`
  sobrecargables.
- `?T` se mantiene; `!T` se elimina.
- Sin macros de usuario; solo `@@derive` y `@@test`.
- FFI solo de entrada; sin exportación a C.
- Sin build scripts.
- Catálogo de diagnósticos reducido a 150 códigos como máximo.
- Matriz de garantías reducida a 50 filas como máximo.
- Nuevas ADR D26–D34.
- Apéndice Z con las features eliminadas.

### 26.4 Compatibilidad

- Un programa `1.0.0-rc.1` no compila en `0.5.0` si usa lifetimes escritos,
  `where`, tipos asociados, GATs, `dyn`, `impl Trait`, async, macros, atributos
  generales, `rust` blocks o exportación FFI.
- El compilador `0.5.x` rechaza la sintaxis retirada con `PGS-E1010` o con el
  diagnóstico de la sección correspondiente.
- Las versiones `0.5.x` son compatibles entre sí en el núcleo; una feature
  nueva solo entra en una versión menor si no rompe programas existentes.
- `0.6.0` conserva la semántica de `0.5.0`; agrega métodos de primitivos en
  `std`, archivos `.d.pengu` y cambia el modelo de paquetes de registry a
  git/path. Un `Tome.toml` con dependencias de registry debe migrarse.

### 26.5 Política

- `0.x`: cambios mayores permitidos; se documentan en este changelog.
- `1.x`: solo adiciones compatibles; las eliminaciones requieren `2.0`.
- Un diagnóstico retirado no se reutiliza.
- Una feature diferida puede volver en una versión mayor, nunca en un parche.

[↑ Volver al índice](#indice)
---

<a id="sec-27"></a>
## 27. Referencias

### 27.1 Especificaciones

- The Rust Reference — semántica del backend, tipos y préstamos.
- The Rustonomicon — solo para implementar el backend, no para el usuario.
- The Cargo Book — formato de manifiesto y resolución de dependencias.
- The rustc Book — edición 2024 y MSRV.
- Rust Standard Library — documentación de `std` que se reexporta.
- MoonScript — inspiración de indentación y sintaxis.
- CoffeeScript — inspiración de funciones y expresiones.
- V — inspiración de simplicidad y ausencia de globales.
- Kotlin — inspiración de inferencia local.
- Gleam — inspiración de sums y ausencia de `null`.
- Zig — inspiración de disciplina y FFI.
- Lua — inspiración de embebibilidad y stdlib chica.
- Go — inspiración de módulos y compilación rápida.

### 27.2 Normas

- RFC 2119 / RFC 8174 — niveles de exigencia (`DEBE`, `DEBERÍA`, `PUEDE`).
- Unicode Standard Annex #31 — identificadores XID.
- Unicode Standard — escalares y UTF-8.
- Semantic Versioning 2.0.0 — versiones del lenguaje y de los paquetes.
- TOML 1.0.0 — `Tome.toml`.
- IEEE 754 — `Float`/`F32`/`F64`.
- System V ABI / C ABI — `foreign "C"`.

### 27.3 Herramientas

- `pengu` — compilador, formatter, linter, LSP y gestor de paquetes.
- `git` — control de versiones.
- `pengu explain` — explicación de diagnósticos.

[↑ Volver al índice](#indice)
<a id="sec-28"></a>
## 28. Apéndice Z: qué se eliminó y por qué

Este apéndice es histórico y no normativo. Explica las features que la spec
`1.0.0-rc.1` tenía y que `0.5.0` deja fuera.

| Feature eliminada | Por qué |
|---|---|
| Anotaciones `'a`, `'static` | El usuario no debe aprender vidas; el compilador infiere y prohíbe escapes. |
| `for<'a>` / rango superior | No da potencia para el 95% del código; fuera del núcleo. |
| `where` | Los bounds caben en la cabecera `[T: Pact]`. |
| Tipos asociados | Duplican los parámetros de tipo y complican los pacts. |
| GATs | Superficie enorme para casos raros. |
| `dyn` / objetos de trait | Un `enchanting` + `match` es más explícito. |
| `impl Trait` | El tipo de retorno debe ser visible. |
| `Pin` / `Future` | Async no es del núcleo. |
| `async` / `await` | Diferido a `std.async`; el núcleo es síncrono. |
| `dream` / `awaken` | Nombres de la etapa async, eliminada. |
| Hilos / canales / atomics | `std.concurrent`, no el lenguaje. |
| `Send` / `Sync` visibles | Detalle del backend; el usuario no los escribe. |
| `Rc` / `Arc` en la prelude | Compartir debe ser explícito; van a `std`. |
| `Cell` / `RefCell` / `Mutex` / `RwLock` | Mutabilidad interior fuera del núcleo. |
| `Cow` / `Weak` | Casos avanzados; `std`. |
| Punteros crudos | Sin acceso directo a memoria en código seguro. |
| `transmute` / uniones / asm | Sin `unsafe` general; `curse` solo para FFI. |
| `MaybeUninit` / `ManuallyDrop` / `UnsafeCell` | Detalles que el usuario no debe tocar. |
| `PhantomData` / ZST / DST | Detalles de representación; el backend decide. |
| `repr` / layout estable | No se garantiza; no es parte del contrato. |
| `cfg` / `inline` / `must_use` | Atributos del backend, no del usuario. |
| Macros (`macro_rules!`, `incantation`) | Superficie enorme; no hay metaprogramación. |
| Atributos generales | Solo `@@derive` y `@@test`. |
| `rust` block | El backend es invisible; no hay escape de código. |
| Exportar funciones a C | v1 solo importa FFI; exportar exige ABI estable. |
| Build scripts | El 99% no los necesita; diferidos a `std.build`. |
| `I128` / `U128` | Rango raro; `std.int`. |
| `BTreeMap` / `BTreeSet` | `std.collections`. |
| `VecDeque` / `LinkedList` / `BinaryHeap` | `std.collections`. |
| `Index` / `IndexMut` sobrecargables | Requieren tipo asociado; se usa `.at(i)`/`get`. |
| `Deref` / `DerefMut` | Coerción automática; se accede de forma explícita. |
| `From` / `Into` | Conversiones implícitas; se usan métodos explícitos. |
| `Display` / `Debug` sobrecargables | Solo `Show` para imprimir. |
| `Drop` visible | La destrucción es automática. |
| `spell` | La función se declara con `->`. |
| `spirit` | El receptor es `@`. |
| `class` / `this` | No hay clases; records y métodos. |
| `null` / `nil` | `Option[T]` y `none`. |
| `try` / `catch` / `throw` | `Result[T, E]` y `?`. |
| `switch` con fallthrough | `match` exhaustivo. |
| Bench / fuzz / property testing | Herramientas externas; no el núcleo. |

### 28.1 Regla de eliminación

Una feature se elimina si:

1. no resuelve el 95% de los casos;
2. se puede reemplazar por un concepto del núcleo;
3. su costo de superficie supera su potencia.

Si una feature eliminada vuelve, vuelve en una versión mayor y con una ADR
nueva.

[↑ Volver al índice](#indice)
---

