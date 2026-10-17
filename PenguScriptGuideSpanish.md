# Guía de Estilo Pengunic

> **Versión cubierta:** PenguScript **2.0.0**
> **Política de idioma.** El inglés es canónico: la guía normativa es
> [`PenguScriptGuideEnglish.md`](PenguScriptGuideEnglish.md). Esta traducción al
> español es **no normativa**; donde discrepen, gana la guía inglesa.
> `tests/test_language_policy.py` comprueba que las dos avanzan en paralelo.
>
> Este documento define las convenciones de nomenclatura, organización e idioma que rigen la biblioteca estándar (`std.*`) y que deberían seguir todos los módulos de usuario. Es el complemento normativo de [`LANGUAGE.md`](LANGUAGE.md): dónde el *Language Reference* describe qué *se puede* escribir, este documento prescribe qué *se debe* escribir.
> Léelo como se lee [PEP 8](https://peps.python.org/pep-0008/) + [PEP 20](https://peps.python.org/pep-0020/) para Python, o el [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) para Rust.

---

## Tabla de contenidos

1.  [Filosofía del código Pengunic](#1-filosofía-del-código-pengunic)
2.  [Nomenclatura](#2-nomenclatura)
3.  [Organización de módulos y archivos](#3-organización-de-módulos-y-archivos)
4.  [Expresiones sobre sentencias](#4-expresiones-sobre-sentencias)
5.  [Optionals, resultados y errores](#5-optionals-resultados-y-errores)
6.  [Enchantments, rituals y concepts](#6-enchantments-rituals-y-concepts)
7.  [Genéricos y bounds](#7-genéricos-y-bounds)
8.  [Gestión manual de memoria](#8-gestión-manual-de-memoria)
9.  [Interoperabilidad con C](#9-interoperabilidad-con-c)
10. [Diseño de APIs](#10-diseño-de-apis)
11. [Documentación (`##`)](#11-documentación-)
12. [Pruebas (`test`)](#12-pruebas-test)
13. [Tabla de traducción C → Pengunic](#13-tabla-de-traducción-c--pengunic)
14. [Anti-patrones](#14-anti-patrones)
15. [Excepciones documentadas](#15-excepciones-documentadas)
16. [Cadenas de métodos](#16-cadenas-de-métodos)
17. [Múltiples valores de retorno (tuplas)](#17-múltiples-valores-de-retorno-tuplas)
18. [Inicializadores cortos de struct](#18-inicializadores-cortos-de-struct)
19. [Atributos de declaración](#19-atributos-de-declaración)
20. [Bloques C embebidos (`antiquus`)](#20-bloques-c-embebidos-antiquus)
21. [`cyclus` y tipos recursivos](#21-cyclus-y-tipos-recursivos)

---

## 1. Filosofía del código Pengunic

PenguScript no es "C con azúcar sintáctico". El lenguaje ofrece construcciones de alto nivel —comprehensions, bloques de valor, `judge`, `with:`, `or:`, `enchanting`, `concept`— y **no usarlas cuando corresponde es un defecto de estilo**, igual que en Python no usar list comprehensions cuando son naturales.

Los seis principios Pengunic:

| # | Principio | En una frase |
|---|---|---|
| 1 | **Explicit over hidden** | Cada acción tiene una sola ortografía obvia. `+` es numérico, la interpolación `"{x}"` es la única composición de strings. |
| 2 | **Expressions over statements** | Si el lenguaje te da `do:`, `if`-valor, `for ... then ...`, úsalos. Un `var tmp` seguido de `if` para asignar es anti-Pengunic. |
| 3 | **Compose over inherit** | Los `concept` son contratos estáticos. Prefiere `shard T where T: Num` a duplicar la misma función por tipo. |
| 4 | **Types carry meaning** | Usa `seal` para newtypes, `maybe T` para "puede faltar", `result of T to E` para "puede fallar". No codifiques el fallo en un centinela. |
| 5 | **Zero-cost abstractions** | Todo lo que el compilador resuelve en compile-time (`enchanting`, `concept`, `shard`, `when`, `derive`) es gratis. Prefiérelo a despacho dinámico manual. |
| 6 | **C is the boundary, not the model** | El código Pengunic se lee como PenguScript. Solo se vuelve explícitamente C cuando se cruza la frontera FFI (`declare`, `ref to`, `bytes of`, `frozen`). |

> **Regla mnemotécnica:** Si tu módulo `std.*` podría compilarse tal cual a C sin reescritura, probablemente estás escribiendo C en la sintaxis de PenguScript. **Reescríbelo Pengunic.**

---

## 2. Nomenclatura

El lenguaje impone estilos por convención (`snake_case` para valores, `PascalCase` para tipos). Esta sección los formaliza y añade reglas para APIs.

### 2.1 Archivos y módulos

| Elemento | Regla | Ejemplos |
|---|---|---|
| Archivo fuente | `snake_case.pengu` | `scrolls.pengu`, `archivum.pengu` |
| Archivo de declaración | `snake_case.d.pengu` | `uuid.d.pengu`, `raylib.d.pengu` (bindings satélite) |
| Módulo (import) | `snake_case`, sustantivo o adjetivo | `std.scrolls`, `std.atlas`, `std.rites` |
| Módulo de colecciones | sustantivo en **plural** | `std.rites`, `std.scrolls` (no `rite`, `scroll`) |
| Módulo de capacidad | sustantivo **singular abstracto** | `std.cipher`, `std.loom` |

**Reglas:**
- Los módulos estándar viven bajo `std.` y su nombre es un **sustantivo latino o inglés**: `spark`, `scrolls`, `oracle`, `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `arithmancy`, `rites`, `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `filum`, `integrum`, `numerus`, `loom`, `invoke`, `ffi`, `ledger`.
- Los bindings C externos (`raylib`, `sqlite3`, `yaml`, …) **no** son módulos `std.*`: se extrajeron a repositorios satélite y se instalan con `pengu add <url>` (catálogo: [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)). El runtime solo enlaza `libc`/`libm`/`pthreads`, y los 26 módulos anteriores son toda la biblioteca estándar pura.
- Nunca uses `utils`, `helpers`, `common`, `misc`. Si no puedes nombrarlo con un sustantivo concreto, **el módulo no tiene una responsabilidad clara**.
- Las siglas se escriben en `snake_case` minúsculo como módulo: `std.ffi`.

### 2.2 Tipos

| Constructo | Estilo | Ejemplo |
|---|---|---|
| `rune` | `PascalCase`, **singular**, sustantivo concreto | `Player`, `Address`, `CsvTable`, `Stopwatch` |
| `omen` | `PascalCase`, **singular**, categoría | `Phase`, `Direction`, `JsonKind`, `Color` |
| `echo` | `PascalCase`, **singular** | `Number`, `Value` |
| `seal` | `PascalCase`, **singular** | `UserId`, `Meters`, `Sha256` |
| `alias` | `PascalCase` | `Buffer`, `Handler`, `Callback` |
| `concept` | `PascalCase`, **adjetivo o rol** | `Formatter`, `Measurable`, `Iterabilis`, `Nexus` |
| Parámetro `shard` | Letra única **o** `PascalCase` descriptivo | `T`, `U`, `K`, `V`, `E`, `Item`, `Key` |

**Reglas adicionales:**
- Un `rune` que envuelve recursos del sistema lleva nombre del **recurso**, no de la operación: `Mutex`, `WaitGroup`, `ChanInt` —no `LockHelper`, `Syncer`.
- Un `seal` describe **qué mide**, no su tipo subyacente: `UserId as int` ✅, `IntWrapper` ❌.
- Los `concept` que reflejan habilidades latinas ya existentes en el compilador (`Num`, `Ordo`, `Par`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum`) deben respetarse con su nombre canónico cuando aplique. Un usuario no redefine `Num`.
- Un `concept` **siempre** describe una capacidad en singular. Nunca pluralices un concept (`Formatters` ❌).

### 2.3 Funciones (`weave`)

Toda `weave` usa **`snake_case`** con el verbo en forma base (sin `to`, sin `-ing`).

| Categoría | Prefijo/forma | Ejemplos |
|---|---|---|
| Acción pura | verbo transitivo | `parse`, `format`, `split`, `join`, `merge`, `filter`, `map_*` |
| Predicado booleano | `is_`, `has_`, `can_`, `should_` | `is_empty`, `has_key`, `can_parse`, `should_retry` |
| Conversión segura | `to_*` | `to_string`, `to_int`, `to_upper` |
| Conversión que puede fallar | `parse_*` (devuelve `maybe T`) | `parse_int`, `parse_float` |
| Constructor | `new`, `from_*`, `with_*` | `new`, `from_csv`, `with_capacity` |
| Mutador | verbo transitivo | `push`, `pop`, `set_volume`, `clear`, `remove` |
| Getter no-trivial | `get_*` | `get_or`, `get_flag_value`, `getenv_or` |
| Forma pura de un mutante `@mutates` | `get_<nombre>` | `get_clamp` (pura), `clamp` (muta); ver §6.7 |
| Getter trivial | sustantivo (sin prefijo) | `len`, `size`, `first`, `keys`, `values` |
| Formateador | `format_*`, `describe_*` | `format_duration`, `describe_result_int` |
| I/O de líneas | `read_*`, `write_*` | `read_file`, `write_lines`, `read_int` |
| Validación | `assert_*` (aborta), `check_*` (devuelve `bool`), `expect_*` (test) | `assert_eq_int`, `check_range`, `expect_eq` |
| Iteración/generación | `iter_*`, `each_*`, `range_*`, `gen_*` | `range_to`, `for_each_int`, `gen_digits` |
| Extracción con fallback | `_or` al final | `get_or`, `unwrap_or`, `at_or`, `arg_at_or` |

**Prohibiciones:**
- ❌ Verbos en `-ing`: `parsing`, `getting` → usa `parse`, `get_*`.
- ❌ Redundancia tipo-hablando: `parse_string_to_int` ✅ `parse_int` mejor.
- ❌ Prefijos húngaros: `str_name`, `int_count` ❌.
- ❌ Nombres de 1-2 letras salvo `i`, `j`, `k` para índices en loops `from ... to ...` **cortos**.

### 2.4 Métodos de instancia (`enchanting T:`)

| Forma | Regla | Ejemplos |
|---|---|---|
| Mutador | verbo transitivo, `self->` modificado | `heal`, `damage`, `push`, `set_volume` |
| Consulta pura | sustantivo o `is_*`/`has_*` | `len`, `first`, `is_empty`, `has_key` |
| Conversión | `to_*` | `to_string`, `to_list`, `to_uppercase` |
| Producción derivada | verbo `clone`, `copy`, `reverse`, `transpose` | `clone`, `reverse`, `transpose` |
| Predicado de contenido | `contains`, `starts_with`, `ends_with`, `matches` | idem |

**Reglas:**
- Un método **no lleva el nombre del tipo** dentro: `Player.heal` ✅ `Player.heal_player` ❌.
- Los métodos que devuelven otra instancia **no consumen `self`** (PenguScript no tiene move semantics en `enchanting`). El nombre nunca usa `consume_`, `take_` ni `into_*`.
- `self` es siempre `ref to T`; por lo tanto los mutadores usan `set self->field is ...`.

### 2.5 Métodos `ritual` (estáticos)

| Rol | Nombre | Ejemplo |
|---|---|---|
| Constructor principal | `new` | `calling Player.new with "Ada"` |
| Constructor alternativo | `from_*`, `with_*` | `from_json`, `with_capacity`, `from_file` |
| Constante asociada | `zero`, `one`, `identity`, `empty` | `Vec2.zero`, `Mat4.identity` |
| Constructor con defaults | `default`, `default_*` | `Logger.default`, `Color.default_red` |
| Factory condicional | `try_*` (si puede fallar) | `try_parse`, `try_open` |

- ❌ `create`, `make`, `build`, `init` como nombre principal → **usa `new`**.
- ✅ `init` solo se acepta cuando **realmente inicializa algo externo** y no devuelve el tipo (p. ej. `raylib.InitWindow` en el binding satélite de raylib; en `std.*` puro el idiomático es `new`).

### 2.6 Variables, locales y parámetros

| Elemento | Estilo | Ejemplo |
|---|---|---|
| Local `var` / `let` | `snake_case` descriptivo | `total_count`, `parsed_items` |
| Parámetro | `snake_case`, corto si es obvio | `x`, `y`, `item`, `key`, `fallback` |
| Booleano local | prefijo `is_`, `has_`, `can_` | `is_ready`, `has_key`, `can_retry` |
| Índice de loop | `i`, `j`, `k` solo en loops cortos; si no, `index`, `row`, `col` | |
| Etiqueta de bucle (`break label` / `continue label`) | `snake_case` descriptivo, nunca una letra | `outer`, `lines_loop`, `next_row` |
| Acumulador | `acc`, `sum`, `total`, `result` | |
| Discard | `_` | `for _, v in col:` |
| Temporal interno | `tmp`, `raw`, `staged` | Nunca expuesto en API |

Etiqueta un bucle solo cuando haya al menos dos bucles anidados y necesites salir
del externo desde dentro; una etiqueta en un único bucle es ruido (ver §14.27).

### 2.7 Constantes top-level

Dos casos, no confundir:

| Caso | Estilo | Ejemplo |
|---|---|---|
| Constante **exportada** de módulo (API pública) | `SCREAMING_SNAKE_CASE` | `const MAX_USERS as int is 1024` |
| Constante **interna** de módulo (privada) | `_SCREAMING_SNAKE_CASE` o `snake_case` con `_` | `const _DEFAULT_CAP as int is 16` |
| Constante usada **solo** dentro de una función | declárala como `const` local top-level del módulo o como `static var` con guard | |

> [!NOTE]
> PenguScript **prohíbe** `var`/`let` a nivel top-level (E0002). Para estado de módulo usa `static var` dentro de un `weave` accesor (ver §8.3). Para valores fijos usa `const`.

### 2.8 Campos de `rune` / `echo` / `omen`

| Elemento | Estilo | Ejemplo |
|---|---|---|
| Campo público | `snake_case` | `name`, `hp`, `session_id` |
| Campo privado | `_snake_case` | `_secret_id`, `_internal_ptr` |
| Variante de `omen` | `PascalCase` | `Disconnected`, `Connecting`, `Connected` |
| Variante con payload | `PascalCase` (nombre de la **forma**, no del dato) | `Connected`, no `ConnectedSession` |

### 2.9 Genéricos

| Rol | Nombre canónico |
|---|---|
| Elemento genérico | `T` |
| Segundo/tercero | `U`, `V` |
| Clave de mapa | `K` |
| Valor de mapa | `V` |
| Error en `result` | `E` |
| Elemento iterable | `Item` |
| Resultado de transformación | `Out` |
| Estado del reductor | `Acc` |

Cuando un genérico tiene rol semántico claro y no colisiona, se permite `PascalCase` descriptivo: `weave map shard In and Out with xs as list of In, f as weave with x as In into Out into list of Out`. **No** uses nombres de una letra para roles no convencionales.

### 2.10 Prefijos reservados

| Prefijo | Propietario | Uso |
|---|---|---|
| `pengu_`, `_pengu_` | Compilador / runtime | **Nunca** los declares a mano. |
| `_` | Módulo / rune | Privacidad estricta (E0043 al cruzar frontera). |
| `ASSET_<MODULE>_` | Sistema `arca` | Identificadores de assets embebidos. |

---

## 3. Organización de módulos y archivos

### 3.1 Orden canónico dentro de un `.pengu`

```pengu
## std/example.pengu
## Descripción de una línea del módulo.
##
## Documentación extendida: qué resuelve, qué NO resuelve, invariantes,
## notas de memoria, ejemplos de uso.
##
## ## Ejemplo
## ```pengu
## import std.example
## calling example.do_thing with 42
## ```

# --- Directivas de módulo -----------------------------------------------
insignia example_            # opcional, solo si necesitas prefijo C
include "some_c_header.h"    # si el módulo es binding
link "somelib"               # si el módulo enlaza una librería C

# --- Imports ------------------------------------------------------------
import std.spark
import std.scrolls
import std.tally as tl

# --- Constantes públicas ------------------------------------------------
const MAX_DEPTH as int is 64
const DEFAULT_SEPARATOR as string is ","

# --- Concepts -----------------------------------------------------------
concept Formatter:
    weave format with value as string into string

# --- Tipos --------------------------------------------------------------
rune Config:
    name as string
    depth as int

omen ParseState:
    Empty
    Partial with consumed as int
    Complete

# --- Binds --------------------------------------------------------------
bind Config with Formatter:
    weave format with value as string into string:
        return "[{value}]"

# --- Enchantings --------------------------------------------------------
enchanting Config:
    weave ritual new_default into Config:
        return with name is "default", depth is 0

    weave display into string:
        return "{self->name} (depth={self->depth})"

# --- Funciones de módulo ------------------------------------------------
weave parse_config with raw as string into maybe Config:
    ...

weave validate_config with cfg as Config into result of Config to string:
    ...

# --- Helpers privados ---------------------------------------------------
weave _split_pairs with raw as string into list of string:
    ...

# --- Tests --------------------------------------------------------------
test "parse_config handles empty input":
    ...
```

**Reglas de orden:**
1. El docstring del módulo **siempre** va arriba.
2. Directivas (`insignia`, `include`, `link`) antes de imports.
3. Imports agrupados: std primero, proyecto después, todos ordenados alfabéticamente.
4. Constantes → Concepts → Tipos → Binds → Enchantings → Funciones públicas → Helpers privados (`_`) → Tests.
5. Los helpers privados **van al final** del archivo, no intercalados.

### 3.2 Tamaño de módulo

- **Un módulo = una responsabilidad.** Si dudas, divide.
- Bajo 800 líneas es cómodo. Sobre 1500 líneas es señal de que hay dos módulos escondidos.
- Un módulo puede exponer 1 tipo principal + sus enchantments, o N funciones relacionadas por un tema.

### 3.3 Imports

- Siempre explícitos, siempre ordenados.
- Alias solo cuando el nombre real colisiona o es muy largo: `import std.tally as tl`. **No** alias por pereza.
- Prohibido `import std.math as _` (E0036).

---

## 4. Expresiones sobre sentencias

Este es el eje del estilo Pengunic. **El lenguaje te da bloques de valor; úsalos.**

### 4.1 Regla general

> Si una operación computa un valor, **exprésala como expresión**, no como una secuencia de sentencias que mutan un temporal.

### 4.2 Comprehensions sobre loops con `push`

**Anti-Pengunic:**
```pengu
var squares as list of int is list of int
for x in nums:
    calling squares.push with x * x
```

**Pengunic:**
```pengu
let squares is for x in nums then x * x
```

Con filtro:
```pengu
let evens is for x in nums when x % 2 == 0 then x
```

### 4.3 `if`-valor sobre `var` + `if`/`else`

**Anti-Pengunic:**
```pengu
var label as string is ""
if score >= 100:
    set label is "winner"
else:
    set label is "keep going"
```

**Pengunic (una línea):**
```pengu
let label is if score >= 100 then "winner" else "keep going"
```

**Pengunic (bloques si hay lógica):**
```pengu
let label is if score >= 100:
    "winner"
else:
    "keep going"
```

### 4.4 `do:` para aislar cómputo

Cuando necesitas varios pasos para producir un valor, **no contamines el scope**:

**Anti-Pengunic:**
```pengu
var tmp as int is a * b
set tmp is tmp + c
set tmp is tmp * d
let result as int is tmp
```

**Pengunic:**
```pengu
let result is do:
    var acc is a * b
    set acc is acc + c
    acc * d
```

### 4.5 `judge` sobre cadenas de `if`/`else`

**Anti-Pengunic:**
```pengu
var desc as string is "?"
if state == Phase.Idle:
    set desc is "idle"
else if state == Phase.Fighting:
    set desc is "fighting"
```

**Pengunic:**
```pengu
let desc is judge state:
    when Phase.Idle -> "idle"
    when Phase.Fighting -> "fighting"
    else -> "?"
```

### 4.5.1 Cuándo usar `judge over rune`

`judge` puede casar dos formas distintas, y elegir entre ellas es una decisión de modelado de datos, no de sintaxis:

- **`omen` algebraico — lo predeterminado.** Cada variante lleva solo sus propios campos, el compilador guarda la representación más compacta y la cláusula liga el payload de la variante por posición. Prefiérelo siempre que las variantes sean cosas genuinamente distintas.
- **`rune` con un discriminante — cuando las variantes comparten campos.** Declara los campos compartidos (`line`, `col`, `type`) una sola vez en el rune y casa la etiqueta con `judge <rune> over <field>:`. Úsalo también cuando necesites un **layout estable** para FFI o para un struct C externo, y siempre que el valor se entregue a C.

Lado a lado:

`omen` algebraico:
```pengu
omen Shape:
    Circle with radius as f64
    Rect with width as f64, height as f64

weave area with s as Shape into f64:
    judge s:
        when Circle with radius -> 3.14159 * radius * radius
        when Rect with width, height -> width * height
```

`rune` con un discriminante:
```pengu
rune Expr:
    kind as ExprKind
    int_value as int
    bin_op as BinOp
    left as ref to Expr
    right as ref to Expr

omen ExprKind:
    Literal
    Binary
    Neg

omen BinOp:
    Add
    Sub
    Mul

weave eval with e as ref to Expr into int:
    judge e over kind:
        when Literal with int_value -> int_value
        when Binary with bin_op, left, right ->
            let l is calling eval with left
            let r is calling eval with right
            judge bin_op:
                when Add -> l + r
                when Sub -> l - r
                when Mul -> l * r
        when Neg with left -> 0 - (calling eval with left)
```

**Anti-Pengunic:** un rune con discriminante donde bastaría un `omen` algebraico:
```pengu
# ❌ Anti-Pengunic: ninguna variante comparte un campo; el rune solo añade una
# etiqueta a una unión que siempre ocupa el tamaño de la unión
rune Shape:
    kind as ShapeKind
    radius as f64
    width as f64
    height as f64

omen ShapeKind:
    Circle
    Rect

# ✅ Pengunic: el `omen` algebraico lleva solo los campos de cada variante
omen Shape:
    Circle with radius as f64
    Rect with width as f64, height as f64
```

**Anti-Pengunic:** un `omen` algebraico cuando las variantes comparten campos:
```pengu
# ❌ Anti-Pengunic: `line` y `col` se repiten en cada variante, y la unión se
# rellena hasta el tamaño de la variante mayor
omen Token:
    Ident with text as string, line as int, col as int
    Number with value as f64, line as int, col as int

# ✅ Pengunic: los campos compartidos viven una sola vez, en el rune
rune Token:
    kind as TokenKind
    text as string
    value as f64
    line as int
    col as int

omen TokenKind:
    Ident
    Number
```

**Reglas de nombres:**
- Llama al discriminante `kind` (Pengunic), o dale un sustantivo concreto como `op_kind` o `node_type`. **No** inventes nombres genéricos como `type`, `tag` o `which`.
- Los bindings de `with` son los nombres de campo del rune **literalmente**; no los renombres. Escribe `when Rect with width, height ->`, no `with w, h`.

### 4.6 `with:` builder sobre asignaciones campo a campo

**Anti-Pengunic:**
```pengu
var p as Point is with x is 0, y is 0
set p.x is 10
set p.y is 20
```

**Pengunic:**
```pengu
var p as Point with:
    set .x is 10
    set .y is 20
```

Anidado:
```pengu
var person as Person with:
    set .name is "Ada"
    set .age is 30
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
        set .zip is "12345"
```

### 4.6.1 `with:` en posición de valor

Un constructor `with:` es una expresión solo donde el compilador ya conoce el
tipo destino. Úsalo cuando el valor sea un struct construido en el sitio: en una
anotación de `var`/`let`/`static var`, un `return`, un campo, el tipo de elemento
de un bucle, una rama en posición de valor o la cola de un `do:`. **No** es una
expresión general: un argumento de llamada necesita un valor con nombre o el
literal en una línea `with x is …`, y un operando aritmético necesita primero una
variable tipada (la tabla de posiciones verificada está en `LANGUAGE.md` §18).

**✅ Pengunic: construye en el hueco que aporta el tipo**

```pengu
var p as Point with:              # la anotación aporta Point
    set .x is 1
    set .y is 2

weave origin into Point:
    return with:                  # 'into Point' aporta Point
        set .x is 0
        set .y is 0
```

**❌ Anti-Pengunic: construir un struct desechable solo para copiarlo en un valor existente**

```pengu
var p as Point is calling default_point     # p ya existe

var fresh as Point with:                    # ❌ construido solo para copiarlo
    set .x is 3
    set .y is 4
with p:
    set .x is fresh.x
    set .y is fresh.y

# ✅ Pengunic: una sola mutación 'with target:', sin valor desechable
with p:
    set .x is 3
    set .y is 4
```

**Cuándo no usar un constructor.** Un único valor trivial se lee mejor como el
literal de struct en una línea; y `with:` (construcción de un valor nuevo) no es
`with target:` (mutación de uno existente):

```pengu
# ✅ una línea, sin constructor
var q as Point is with x is 5, y is 6

# ✅ 'with:' construye un valor nuevo; 'with target:' muta uno existente
var fresh as Point with:
    set .x is 1
    set .y is 2
with fresh:
    set .x is 3
```

### 4.7 `with target:` para mutar colecciones o structs existentes

**Anti-Pengunic:**
```pengu
calling scores.push with 10
calling scores.push with 20
calling scores.clear
```

**Pengunic:**
```pengu
with scores:
    calling .push with 10
    calling .push with 20
    calling .clear
```

### 4.8 `if v as T is m:` para desempacar `maybe`

**Anti-Pengunic:**
```pengu
if m.is_present:
    let v is m.value
    calling process with v
```

**Pengunic:**
```pengu
if v as Config is m:
    calling process with v
```

También en valor:
```pengu
let label is if v as User is u: u.name else: "anonymous"
```

### 4.9 `some`, `maybe none` con contexto

Siempre **anota el tipo** cuando el valor es `maybe none` o `null` (E0014):

```pengu
var m as maybe int is some 42       # OK: tipo inferido del valor
var n as maybe int is maybe none    # OK: anotación requerida
var p as ref to int is null         # OK: anotación requerida
```

### 4.10 Recursión sobre acumuladores

Los helpers recursivos siguen siendo expresiones en su rama final:

```pengu
weave _factorial with n as int into int:
    if n <= 1:
        return 1
    return n * (calling _factorial with n - 1)
```

No hagas `var acc` + `while` si la recursión de cola (o expresión directa) se lee mejor. PenguScript no garantiza TCO, pero para profundidades pequeñas es idiomático.

### 4.11 `return` implícito al final

Si la última sentencia del `weave` es una expresión, **no escribas `return`**:

```pengu
weave double with x as int into int:
    x * 2                     # return implícito
```

Esto aplica a bloques de valor también:
```pengu
let x is do:
    var a is 10
    a * 2                     # valor del bloque
```

---

## 5. Optionals, resultados y errores

### 5.1 Elegir el tipo correcto

| Situación | Tipo | Ejemplo |
|---|---|---|
| Puede faltar, sin razón de fallo | `maybe T` | `find_user → maybe User` |
| Puede fallar con detalle | `result of T to E` | `parse_config → result of Config to string` |
| Fallo irrecuperable (bug, invariante roto) | `panic` | `weave divide with a, b: if b == 0: panic "division by zero"` |
| Pointer que puede no apuntar a nada | `ref to T` + `null` | `ref to Buffer is null` |

**Regla:** Nunca uses un valor centinela (`-1`, `""`, `0`) para "no encontrado". Usa `maybe T`.

### 5.2 `or else` para fallback

```pengu
let name is user_name or else "Guest"
let port is env_port or else 8080
```

En argumentos y struct-lits va **sin paréntesis** (por `list_value_expr`):

```pengu
calling connect with host, (port or else 8080)
var cfg as Config is with retries is (retries or else 3)
```

En aritmética sí requiere paréntesis (por precedencia):

```pengu
let total is base + (bonus or else 0)     # ✅
# let total is base + bonus or else 0     # ❌ parsea como ((base+bonus) or else 0)
```

### 5.3 `or return` para salida temprana

```pengu
weave greet with m as maybe User into string:
    let u is m or return "no user"
    return "Hi {u.name}"
```

### 5.4 `try` para propagación

Cuando la función **también** devuelve `maybe` o `result` compatible:

```pengu
weave load_config into result of Config to string:
    let raw is try calling read_file with "config.txt"
    let cfg is try calling parse_config with raw
    return cfg
```

### 5.5 `or:` para manejo rico

Cuando necesitas usar `error` con lógica:

```pengu
let cfg is calling parse_config with raw or:
    calling spark.eprintln with "Parse failed: {error}"
    return default_config
```

**Depuración:** cuando un pipeline genérico hace que el tipo estático de un
opcional no sea obvio, imprime `type of value` (`"maybe int"`, `"result of int to
string"`). Es una cadena de tiempo de compilación con cero coste en runtime —
úsala para diagnósticos y aserciones, nunca como comprobación de tipos en
runtime para ramificar (§14.28).

**Solo un `or:` por cadena de operaciones** — si necesitas dos, divide en funciones.

### 5.6 `panic` **no** es control de flujo

`panic` aborta el proceso. Solo se usa para:
- Invariantes internas violadas (nunca alcanzable desde API pública sin bug).
- Precondiciones documentadas que el caller **debe** cumplir.

Nunca en una ruta esperada:

```pengu
# ❌ Anti-Pengunic
weave divide with a as int, b as int into int:
    if b == 0:
        panic "div by zero"
    return a / b

# ✅ Pengunic
weave divide with a as int, b as int into maybe int:
    if b == 0:
        return maybe none
    return some (a / b)
```

### 5.7 Nombres para operaciones que pueden fallar

| Patrón | Convención |
|---|---|
| Devuelve `maybe T` | verbo base: `find`, `first_or_none`, `at_safe` |
| Devuelve `result of T to E` | verbo base: `parse`, `try_open` |
| Devuelve `T` o **panickea** | verbo + `_or_panic` / `_unwrap` | `read_or_panic`, `unwrap` |
| Devuelve `T` con fallback | `_or` al final | `get_or`, `at_or`, `arg_at_or` |

Nunca mezcles: un `weave` llamado `get_int` **no** debe panickear; uno llamado `get_int_or_panic` sí.

### 5.8 Anti-patrón: el bool + out-param

❌ **Nunca:**
```pengu
# Finge un maybe con bool + pointer a out
weave try_get with m as map of string to int, k as string, out as ref to int into bool:
    ...
```

✅ **Pengunic:**
```pengu
weave get_or with m as map of string to int, k as string, fallback as int into int:
    ...
weave get_safe with m as map of string to int, k as string into maybe int:
    ...
```

---

## 6. Enchantments, rituals y concepts

### 6.1 ¿Método o función de módulo?

Regla de decisión:

```
¿El primer argumento "es" el sujeto natural de la operación?
    SÍ  → método (enchanting T)
    NO  → función de módulo
```

| Caso | Elección | Ejemplo |
|---|---|---|
| `s.trim()` transforma **s** | método | `enchanting string: weave trim into string` |
| `m.keys()` accede a **m** | método | `enchanting map of ...: weave keys into list of K` |
| `tally.sum(xs)` reduce **xs** | ambas (método preferido) | `calling xs.sum` o `calling tally.sum with xs` |
| `scrolls.substring(s, i, j)` — s no es "el sujeto" | función de módulo | `calling scrolls.substring with s, 0, 4` |
| `archivum.copy(src, dst)` — ninguno es "el sujeto" | función de módulo | `calling archivum.copy with src, dst` |
| `chronicle.now()` — no hay sujeto | función de módulo | `calling chronicle.now` |
| `Player.new(...)` — constructor | `ritual` | `calling Player.new with "Ada"` |
| `Vec2.zero` — constante de tipo | `ritual` sin args | `var v is calling Vec2.zero` |

**Ambas exposiciones son válidas y frecuentes** (`std.tally` ofrece `calling xs.sum` **y** `calling tally.sum with xs`). Cuando existan las dos, el módulo delega en el método:

```pengu
enchanting list of int:
    weave sum into int:
        var acc is 0
        for x in essence of self:
            set acc is acc + x
        acc

weave sum with xs as list of int into int:
    return calling xs.sum
```

### 6.2 Nomenclatura de `ritual`

- `new` es el constructor canónico. Sin argumentos o con defaults.
- `from_*` cuando la fuente es otro tipo/serialización: `from_csv`, `from_json`, `from_file`.
- `with_*` cuando configura **capacidad/parámetros opcionales**: `with_capacity`, `with_retries`.
- `zero`, `one`, `identity`, `empty`, `default` para constantes canónicas.

### 6.3 Cuándo `concept` + `bind`

Usa `concept` cuando:

1. **Una función genérica necesita garantizar operaciones** sobre `T`.
2. **Varios tipos distintos comparten contrato** y quieres que una `weave shard T where T: C` los acepte.
3. **Quieres documentar la interfaz requerida** por una API de módulo.

❌ **No uses `concept` cuando:**
- Solo un tipo lo implementará **nunca más**. Es ruido.
- Necesitas polimorfismo en runtime. **PenguScript no lo tiene.** Usa `judge` sobre un `omen` con payloads.

Ejemplo correcto:

```pengu
concept Formatter:
    weave format_entry with title as string into string

weave print_all shard T where T: Formatter with items as list of T into void:
    for item in items:
        calling spark.println with calling item.format_entry with "LOG"
```

### 6.4 `derive` cuando corresponde

Si tu `rune` va a usarse como **clave de mapa**, en **comparaciones**, o cuando necesitas una copia en profundidad explícita:

```pengu
rune Point derive Par, Ordo, Vinculum, Imago, Nexus:
    x as int
    y as int
```

| Concept | Cuándo derivarlo |
|---|---|
| `Par` | Siempre que `==` tenga sentido semántico |
| `Ordo` | Cuando tiene orden total natural (números, strings, fechas) |
| `Vinculum` | Cuando va a usarse como **clave de `map`** |
| `Imago` | Cuando quieras copiar la rune en profundidad explícitamente antes de almacenarla |
| `Nexus` | Junto con `Imago` (el compilador los implica mutuamente) |

### 6.5 Cuándo **no** derivar `Par`/`Ordo`

- Si tu `rune` contiene **puntos flotantes** y el orden total no es trivial (NaN).
- Si tu `rune` contiene un **buffer C** y la igualdad estructural sería misleading.
- Si la igualdad debe comparar por **contenido lógico**, no por campos (implementa `bind` explícito).

### 6.6 Enchanting genérico de contenedores

Cuando quieras métodos para **todos los `map of K to V`**:

```pengu
enchanting map of shard K to shard V:
    weave is_empty into bool:
        return (calling self.len) == 0

    weave get_or with k as K, fallback as V into V:
        if calling self.contains with k:
            return self at k
        return fallback
```

- El bloque **concreto** (`enchanting map of string to int:`) **anula** el genérico para ese tipo. Úsalo para especializaciones de rendimiento.
- Los métodos genéricos se monomorfizan solo para las instancias realmente usadas.

### 6.7 Enchanting de primitivos (`shard T where T: …`)

Un primitivo (`int`, `float`, `char`, `bool`, …) es un objetivo válido de `enchanting`. A diferencia de las runes, `self` es **un valor**, no una referencia: `set self` se rechaza con `E0006` y `self->field` con `E0003`.

Cuando el método aplica a **varios** tipos primitivos, acota con `shard T where T: …`:

```pengu
# ✅ Pengunic: una definición, N tipos
enchanting shard T where T: Num and T: Ordo and T: Par:
    weave abs into T:
        if self < donum T:
            return -self
        return self

# ❌ Anti-Pengunic: N definiciones idénticas
enchanting int:   weave abs into int: ...
enchanting i64:   weave abs into i64: ...
enchanting float: weave abs into float: ...
enchanting f64:   weave abs into f64: ...
```

Reglas:

1. **Un módulo por capacidad, no por tipo.** `numerus` (`Num`), `integrum` (`Integrum`), `fractio` (`Real`), `littera` (`char`), `logica` (`bool`).
2. **El bound decide qué tipos tienen el método.** El compilador lo verifica en el punto de llamada: `(1.5).is_even` es `E0005` porque `float` no satisface `Integrum`.
3. **Monomorfización por tipo concreto.** El C emitido es `int_abs`, `f64_abs`, etc. Cero sobrecoste.
4. **`Num` no concede orden ni igualdad.** Ésos son los conceptos ortogonales `Ordo` (`<`, `<=`, `>`, `>=`) y `Par` (`==`, `!=`). Los refinamientos `Integrum` y `Real` conceden ambos: todo tipo que satisface uno de ellos es un primitivo numérico, y todo primitivo numérico es ordenable y comparable. Por eso `std.integrum` puede escribir `where T: Integrum:` y usar `<`, `<=`, `==`. Un genérico que solo necesita `+ - * /` y compara a mano escribe `where T: Num and T: Ordo and T: Par:` — es lo que hace `std.numerus`.
5. **Nunca `antiquus` para lógica trivial.** `declare` a `libm` cuando haga falta C (`sqrt`, `sin`).
6. **Predicados con `is_*`.** Consultas puras con el nombre base (`abs`, `floor`).
7. **Un método por bound correcto.** Si un método no puede funcionar en todos los tipos de un bound, muévelo al bound más estricto que encaje. `sqrt` no funciona en `int`; vive en `fractio` (`Real`), no en `numerus` (`Num`).
8. **`@mutates` para el par mutante/puro.** Un método que devuelve el propio tipo del receptor puede marcarse con `@mutates`: `calling x.clamp with …` **muta `x`** (solo como sentencia) y `calling x.get_clamp with …` devuelve el valor sin tocarlo. Se emite **una sola** función C y el cuerpo sigue siendo puro (`self` es un valor, `E0006` intacto): la asignación la hace el punto de llamada. Fuera de un bloque `enchanting`, con un `into` distinto del tipo del receptor, o con un cuerpo que asigna a `self`, es `E0067`; declarar además `get_<name>` es `E0068`; usar la forma mutante donde se espera un valor es `E0066`. Ver `LANGUAGE.md` §10.1.

**`Donum` es automático para las runes.** Una `rune` o un `echo` cuyos campos son todos
defaultables implementa `Donum` — `donum Point` simplemente funciona,
sin `derive Donum` ni `bind` (ver `LANGUAGE.md` §11.4). Un campo contenedor
(`list`, `map`, `slice`, `maybe`, `result`) lo elimina, porque un contenedor a
cero sería corrupto en vez de vacío; `derive Donum` es `E0005` (§14.29).

| Módulo | Bound | Cubre | Muta (sentencia) | Forma pura |
|---|---|---|---|---|
| `std.numerus` | `T: Num and T: Ordo and T: Par` | todos los primitivos numéricos | `abs`, `clamp`, `pow_int`, `round` | `get_abs`, `get_clamp`, … |
| `std.integrum` | `T: Integrum` | solo enteros | `gcd`, `lcm`, `next_prime`, `factorial` | `get_gcd`, `get_lcm`, … |
| `std.fractio` | `T: Real` | `float`, `f32`, `f64`, `double` | `sqrt`, `sin`, `exp`, `reciprocal` | `get_sqrt`, `get_sin`, … |
| `std.littera` | `char` | `char` | `to_upper`, `to_lower` | `get_to_upper`, `get_to_lower` |
| `std.logica` | `bool` | `bool` | `implies`, `xor`, `iff`, `toggle` | `get_implies`, `get_xor`, … |

Desde la versión 2.1.0 de estos módulos, todo método que devolvía el propio tipo
del receptor está marcado `@mutates`: `calling x.abs` **reescribe `x`** y solo
vale como sentencia, mientras que `calling x.get_abs` devuelve el valor sin tocar
`x`. Se emite **una sola** función C por receptor. Los predicados (`is_even`,
`is_nan`, `approx_eq`) y las conversiones (`to_int`, `to_hex`, `div_rem`) siguen
devolviendo su valor y no participan del desdoblamiento. Ver `LANGUAGE.md` §10.1
y `MIGRATION.md`.

Los transcendentales que llaman a `libm` viven en dos bloques **concretos** (`enchanting float:` y `enchanting f64:`) en lugar de en el shard, porque C expone símbolos distintos por ancho (`sqrtf` frente a `sqrt`). Los predicados y utilidades puras se quedan en el único bloque `enchanting shard T where T: Real:`. Declara solo los nombres canónicos (`float`, `f64`): `f32` y `double` son alias del mismo tipo C, y declarar ambas grafías es `E0047`.

Los cinco módulos cubren **todos** los primitivos del lenguaje. Importa el módulo cuyo bound encaje con el receptor y los métodos aparecen sin coste en runtime: el compilador monomorfiza cada llamada a una función C plana (`int_abs`, `f64_sqrt`, `char_to_upper`, `bool_to_int`, …). Un programa que no importa ninguno no paga nada por ellos; uno que importa uno solo paga por los métodos que realmente llama.

`std.arithmancy` conserva sus funciones escalares (`abs_i`, `clamp_f`, `sqrt_f`, …) por compatibilidad, pero su implementación son **wrappers de una línea** sobre los métodos de los cinco módulos. El algoritmo vive en un único lugar: el módulo del bound que lo soporta. Los tipos `Vec2`/`Vec3`/`Mat4`/`Quat` y las constantes `PI`/`TAU`/`E`/`EPSILON` siguen siendo responsabilidad de `arithmancy`.

### 6.8 Memoria manual con `std.memoria`

`std.memoria` es la API canónica para reservar y manipular bloques del heap. **No** reemplaza los operadores del lenguaje: los complementa. `banish` sigue liberando, `size of T` sigue midiendo, `sigil of x` sigue tomando una dirección y `essence of p` sigue desreferenciando.

| Necesitas | Usa |
|---|---|
| Reservar un valor | `calling memoria.alloc of T` |
| Reservar N elementos | `calling memoria.alloc_array of T with n` |
| Crecer/encoger un bloque | `calling memoria.resize_array of T with p, old_n, new_n` |
| Copiar bloques (con posible solape) | `calling memoria.copy of T with dst, src, n` |
| Rellenar / resetear | `calling memoria.fill of T with p, value, n` · `calling memoria.zero of T with p, n` |
| Liberar | `banish p` (¡no hay `memoria.free`!) |
| Tamaño de `T` | `size of T` (¡no hay `memoria.sizeof`!) |

Cada método es `shard T`: el compilador monomorfiza la llamada a una función C plana (`memoria_alloc_int`, `memoria_alloc_array_byte`, `memoria_resize_array_float`, …). Sin boxing, sin vtables.

**Regla**: pon `defer banish` (o `errdefer banish`) inmediatamente después de asignar:

```pengu
import std.memoria

weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 16
    defer banish buf
    calling memoria.fill of int with buf, 7, 16
    calling memoria.zero of int with buf, 16
    return 0
    # 'defer banish buf' lee la *variable* al salir del ámbito: si 'buf' fue
    # reasignado por 'resize_array', libera el puntero vigente, no una copia.
```

`resize_array` pide `old_n` explícito porque el `realloc` de C no sabe cuántos elementos tiene el bloque, y además puede moverlo: **tras un resize con éxito el puntero antiguo queda inválido — usa solo el retorno**. El patrón seguro es `defer banish buf` + `set buf is calling memoria.resize_array …`.

> ⚠️ Un `defer banish` en el **mismo** ámbito que un `return` del mismo puntero es un bug: el defer se ejecuta, libera el bloque y el llamador recibe un puntero colgante. Devuelve la propiedad moviendo la liberación al llamador.

**OOM**: `alloc`, `alloc_array` y `resize_array` abortan con `[PENGU] out of memory`. Si prefieres manejar el fallo, usa las variantes `try_*`, que devuelven `maybe`:

```pengu
var mp as maybe ref to int is calling memoria.try_alloc of int
if p as ref to int is mp:
    set essence of p is 1
    banish p        # libera el bloque
banish mp           # libera la caja del maybe (un 'maybe ref to T' posee la caja, no el puntero)
```

**Zeroed por defecto**: `alloc` y `alloc_array` devuelven memoria a cero. No existe `alloc_uninit`; si de verdad necesitas un bloque sin inicializar (rendimiento medido, código de arranque), usa un bloque `antiquus` con `malloc` y documenta el motivo.

---

## 7. Genéricos y bounds

### 7.1 Declaración

```pengu
weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if calling xs.len == 0:
        return fallback
    return xs at 0
```

- `shard T` para un tipo, `shard T and U` para varios.
- `where T: Concept` para bounds. Múltiples: `where T: Num and T: Ordo` o `where T: Num, T: Ordo`.
- El bound va **inmediatamente después** de `shard`.

### 7.2 Cuándo añadir bound vs dejarlo libre

| Necesitas en el cuerpo… | Bound requerido |
|---|---|
| `a + b`, `a - b`, `a * b`, `a / b` | `T: Num` |
| `a % b`, `a & b`, `a << b`, `~a` | `T: Integrum` |
| `sqrt`, `is_nan`, `floor`, `ceil` (operaciones solo de flotantes) | `T: Real` |
| `a == b`, `a != b` | `T: Par` |
| `a < b`, `a <= b`, `a > b`, `a >= b` | `T: Ordo` |
| `donum T` | `T: Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Forma` o `Donum` |
| `map of T to U` (T como clave) | `T: Vinculum` |
| Copiar en profundidad un `T` con un clon explícito | `T: Imago` (que implica `Nexus`) |
| Iterar `for x in xs` con `xs as list of T` | Ninguno (la lista ya da el elemento) |
| Imprimir con `"{x}"` | `T: Forma` |

### 7.3 Regla de mínima restricción

Añade **solo los bounds que realmente usas**. Un `shard T where T: Num` que nunca suma es ruido y limita al caller.

**Mal:**
```pengu
weave length_of shard T where T: Num with xs as list of T into int:
    return calling xs.len         # 'Num' no se usa
```

**Bien:**
```pengu
weave length_of shard T with xs as list of T into int:
    return calling xs.len
```

### 7.4 Bounds transitivos

Si tu `weave` llama a otro `weave` genérico, **propaga los bounds**:

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    ...

weave sum_then_double shard T where T: Num with xs as list of T into T:
    return (calling sum with xs) * 2     # 'Num' se usa aquí también
```

### 7.5 Asociados (futuro)

Cuando el lenguaje soporte `concept Iterator shard Self: alias Item`, los usaremos para iteradores genéricos. **Hoy** el idiomático es:

```pengu
concept Container shard T:
    weave push with item as T into void
    weave len into int
```

---

## 8. Gestión manual de memoria

### 8.1 Qué libera `banish`

PenguScript no tiene recolector de basura ni liberación automática: tú asignas, tú liberas.
`banish x` libera lo que `x` posee según su tipo estático, y es una operación segura que
no hace nada sobre literales y vistas sin posesión.

| Tipo | Qué libera `banish x` | Notas |
|---|---|---|
| `string` (interpolación, `chr`, `to string`) | su búfer del heap | `is_owned == 1` |
| `string` (literal `"x"`, `from_cstr`) | nada | `is_owned == 0`, no-op seguro |
| `list of T` | el búfer de elementos propio de la lista | nunca los elementos |
| `map of K to V` | la tabla de entradas y las celdas por entrada | nunca los búferes de claves/valores |
| `slice of T` | nada (siempre una vista) | rechazado con `E0008` |
| `ref to T` | la asignación apuntada (`free`) | gestionada por el llamador |
| `rune` con campos heap | `_pengu_cleanup_T` | solo con `derive Nexus` |
| elementos de `list of string` | nada | usa `pengu_banish_string_list` para esos |

### 8.2 Regla de oro

> **`banish x` libera ahora. `defer banish x` libera al salir del ámbito (LIFO). `errdefer banish x` libera solo en un retorno de error. Nada se libera a tus espaldas.**

### 8.3 Estado de módulo (patrón canónico)

**Nunca** declares `var` top-level (E0002). Usa `static var` en un accesor:

```pengu
weave next_id into int:
    static var counter as int is 0
    set counter is counter + 1
    counter
```

Para estado complejo, expon un `rune` + funciones que reciban `ref to Context`:

```pengu
rune Registry:
    items as list of string

weave registry_add with r as ref to Registry, item as string into void:
    calling r->items.push with item
```

### 8.4 Vistas sin posesión (nunca aplicarles banish)

Un valor que solo **ve** memoria de otro no debe recibir `banish`: un `slice of T`, un
`ref to T`, `bytes of s`, o cualquier cadena con `is_owned == 0`.

```pengu
let view is nums at 1 to 3        # un slice es solo una ventana sobre 'nums'
let raw is bytes of s             # una vista de bytes sin posesión sobre 's'
# Ninguna posee almacenamiento: libera 'nums' / 's', nunca las vistas.
```

### 8.5 `defer banish` para recursos que cruzan ámbitos

**No hay liberación automática al salir del ámbito.** Usa `defer banish` para liberar
cuando termina el ámbito, o `banish` para liberar en un momento concreto. Los recursos
que vienen de C siguen la rutina de limpieza de su biblioteca, no `banish`:

```pengu
weave process into result of int to string:
    var buf as ref to byte is calling c_alloc_buffer with 1024
    defer banish buf                       # libera cuando retorna 'process'
    ...
```

Para un `rune` con campos heap, opta por `derive Nexus` y libéralo explícitamente:

```pengu
var doc as Doc with:
    set .title is "spec"
    set .tags is ["a", "b"]
defer banish doc                           # invoca _pengu_cleanup_Doc
```

### 8.6 Nombres para el tiempo de vida

| Prefijo | Significado |
|---|---|
| sin prefijo | Lo asignaste tú: libéralo con `banish` / `defer banish` |
| sufijo `_view` | Una vista: nunca le apliques banish |
| sufijo `_owned` | Posee explícitamente un búfer del heap: libéralo explícitamente |

### 8.7 Nunca `banish` un `slice`

Un `slice of T` es **siempre** una ventana. Nunca libera. El docstring del módulo debe decirlo explícitamente cuando devuelve slices. Devolver un `slice of` de un array de pila se rechaza (`E0051`) porque el slice quedaría colgando al retornar el weave.

---

## 9. Interoperabilidad con C

### 9.1 `.d.pengu` para bindings

**Nunca** declares `declare foo...` en un `.pengu` de lógica pura. Los bindings van en su `.d.pengu`:

```pengu
# binding satélite de sqlite3 — instalado con `pengu add <url>`
include "sqlite3.h"
link "sqlite3"

rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to ref to opaque into int
declare sqlite3_close with db as ref to opaque into int
```

Los bindings C externos ya no viven en `std/`: `sqlite3` se extrajo a un repositorio satélite instalado con `pengu add <url>` (catálogo: [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)). Lo mismo vale para `raylib`, `yaml`, `uuid`, `xlsx` y el resto; las reglas de `.d.pengu` de abajo se aplican a todos ellos.

### 9.2 `declare` con tipos C exactos

- Usa `ref to char` para `char*`.
- Usa `ref to frozen char` para `const char*`.
- Usa `ref to void` / `ref to frozen void` para `void*` y `const void*` (wildcard).
- Usa `usize` para `size_t`.
- Usa `...` para variádicos C (`printf`), **no** `many T`.

### 9.3 `frozen` = `const` de C

`frozen` describe **pointee const**, no puntero const:

| Pengu | C |
|---|---|
| `frozen int` | `const int` |
| `ref to frozen int` | `const int*` |
| `ref to void` | `void*` |
| `ref to frozen void` | `const void*` |
| `frozen ref to int` | (normaliza a `ref to frozen int`) |

Usa `frozen` siempre que el C header tenga `const`.

### 9.4 Conversiones C

| Necesitas | Función |
|---|---|
| `PenguString` → `char*` | `ffi.cstr_from_string` (sin posesión) |
| `char*` → `PenguString` | `ffi.string_from_cstr` (asignada en el heap; libérala con `banish`) |
| Buffer C como bytes | `ffi.slice_from_ptr` (sin posesión, no aplicar banish) |
| `T*` → `void*` | `transmute p to ref to void` |
| Reinterpretar `T*` como `U*` | `transmute p to ref to U` (advertencia W0001) |

**Nunca** uses `+` para concatenar un `char*` con un string. Interpola:

```pengu
calling printf with (transmute "Hello, %s\n" to ref to frozen char), name_cstr
```

### 9.5 Liberar memoria de C con **su** cleanup, no con `banish`

Si el header dice "call `FreeX`", el código Pengunic lo llama:

```pengu
var tex as raylib.Texture2D is calling raylib.LoadTexture with path
defer calling raylib.UnloadTexture with tex
```

(`raylib` es un binding satélite: instálalo con `pengu add <url>` — consulta [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).)

`banish` es **solo** para memoria del runtime PenguScript (`pengu_sigil_alloc`, `PenguString` dinámico, `PenguList`, `PenguMap`).

---

## 10. Diseño de APIs

### 10.1 Las 12 reglas de una buena API `std.*`

1. **Cada función pública tiene un único propósito claro**, reflejado en su nombre.
2. **Los parámetros tienen defaults** cuando es posible (`times as int is 1`).
3. **Los errores esperables devuelven `maybe` o `result`**, no panickean.
4. **Los panics son bugs del caller** (precondiciones documentadas).
5. **Los strings se componen con `"{expr}"`**, jamás con `+`.
6. **Los `rune` y `omen` derivan `Par`/`Ordo`/`Vinculum`/`Imago`/`Nexus`** cuando aplica.
7. **Las funciones puras no tienen efectos colaterales** documentados como tales.
8. **Los mutadores se marcan como tales** (verbo transitivo, `self->`).
9. **Los helpers privados empiezan por `_`**.
10. **El módulo no expone estado global mutable** salvo `static var` encapsulado.
11. **Los ejemplos del docstring compilan tal cual.**
12. **Cada función pública tiene al menos un `test`.**

### 10.2 Módulos espejo de Python/Rust/Go

Cada módulo debe **competir con** su equivalente en otros lenguajes:

| Módulo | Compite con |
|---|---|
| `std.spark` | `fmt`, `io`, `os` de Go; `print()` de Python |
| `std.scrolls` | `strings` de Go; `str` methods de Python; `str` de Rust |
| `std.tally` | `itertools`, `statistics`, `functools` de Python |
| `std.atlas` | `dict` de Python; `map` de Go |
| `std.oracle` | `Optional`, `Result` de Rust |
| `std.loom` | `itertools` de Python; `Iterator` de Rust |
| `std.coven` | `set` de Python; `HashSet` de Rust |
| `std.archivum` | `os.path`, `shutil`, `pathlib` de Python; `os` de Go |
| `std.arithmancy` | `math` de Python; métodos de `f64` de Rust |
| `std.cipher` | `base64`, `json` de Python; `serde_json` de Rust |
| `std.filum` | `threading`, `sync` de Go; `std::thread` de Rust |
| `std.lot` | `random` de Python; `rand` de Rust |

Si al leer tu API un usuario de Python/Rust/Go dice *"esto lo haría en dos líneas con `X`"*, **tu API necesita ese `X`**. Las regex (`regulus`) y HTTP (`precis`) ya no son `std.*`: son bindings satélite (`pengu add <url>`, catálogo en [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)).

### 10.3 Nombres y compatibilidad

- **Nunca cambies la firma de una función pública sin bump de versión mayor.**
- Los alias de compatibilidad (`deprecated_new`) se eliminan tras dos versiones.
- Los nombres nuevos van en `snake_case`, en inglés, con los prefijos de §2.3.

### 10.4 Defaults y overloads

PenguScript no tiene overloads. Para "dos versiones":

```pengu
# Variante simple
weave get_or with m as map of string to int, k as string, fallback as int into int:
    ...

# Variante con contexto extra
weave get_or_with_logger with m as map of string to int, k as string, fallback as int, logger as ref to Logger into int:
    ...
```

O usa **parámetros con defaults** (que deben ser constantes de compile-time):

```pengu
weave retry with f as weave into bool, times as int is 3, delay_ms as int is 100 into bool:
    ...
```

### 10.5 Composición sobre duplicación

**Anti-Pengunic:**
```pengu
weave sum_int_list with xs as list of int into int:
    var acc is 0
    for x in xs: set acc is acc + x
    acc

weave sum_float_list with xs as list of float into float:
    var acc is 0.0
    for x in xs: set acc is acc + x
    acc
```

**Pengunic:**
```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    acc
```

Una sola `weave` sirve para `int`, `float`, `i64`, `f32`... y para cualquier tipo de usuario con `derive` de un concept `Num`.

Lo mismo vale para una función que solo envuelve un método. No copies el algoritmo; delega:

```pengu
# ✅ Pengunic: el algoritmo vive en std.numerus
weave abs_i with x as int into int:
    return calling x.abs
```


---

## 11. Documentación (`##`)

### 11.1 Docstring de módulo

Obligatorio. Va **antes de cualquier directiva**:

```pengu
## std/example.pengu
## Operaciones sobre cadenas con gestión manual de memoria.
##
## Este módulo NO libera memoria por ti: cada función devuelve un valor nuevo
## que tú liberas con `banish` (o `defer banish`). Las vistas (slices, `ref to`)
## no poseen memoria y nunca deben recibir `banish`.
##
## ## Ejemplo
## ```pengu
## import std.example
## let parts is calling example.split_once with "a=b", "="
## ```
```

### 11.2 Docstring de función/tipo

Estructura fija:

```pengu
## Convierte un entero a su representación hexadecimal en minúsculas.
##
## ## Parámetros
## - `n`: valor a convertir. Acepta negativos (se prefija con `-`).
## - `width`: ancho mínimo. Si el resultado es más corto, se rellena con `0`.
##
## ## Retorno
## Un `string` nuevo con la representación `0x…` (o `-0x…`); libéralo con `banish`.
##
## ## Ejemplo
## ```pengu
## calling to_hex with 255, 4       # "00ff"
## calling to_hex with -1, 2        # "-01"
## ```
weave to_hex with n as int, width as int is 0 into string:
    ...
```

### 11.3 Reglas

- **Una línea de resumen**, seguida de línea en blanco y detalles.
- Secciones en `## ## Nombre` (H2 dentro del docstring).
- Ejemplos en bloques ` ```pengu `.
- Los invariantes y la semántica de liberación se documentan **explícitamente**:
  - "El `list` retornado es nuevo; libéralo con `banish`."
  - "El `slice` retornado apunta a `self`; no lo banishes."
  - "Panickea si `n < 0`."
- Los `##` **preceden inmediatamente** al símbolo, sin línea en blanco intermedia.
- Nunca documentes lo obvio (`## Retorna un int`). Documenta **qué significa**.

### 11.4 Docstring de tipo

```pengu
## Configuración inmutable de una conexión HTTP.
##
## ## Invariantes
## - `retries >= 0`.
## - `timeout_ms > 0`.
##
## ## Memoria
## Los campos `headers` y `body` son propiedad del `rune`; usar
## `defer banish cfg` para liberarlos (requiere `derive Nexus`).
rune HttpConfig derive Par, Nexus:
    url as string
    retries as int
    timeout_ms as int
    headers as map of string to string
```

---

## 12. Pruebas (`test`)

### 12.1 Nombres

`test <descripción>` donde la descripción es una **oración declarativa** en inglés o español, en `snake_case` o string:

```pengu
test "split returns empty list for empty input":
    ...

test "parse_int rejects trailing garbage":
    ...
```

Nunca `test_1`, `test_foo`, `test_works`.

### 12.2 Cobertura mínima por función pública

- 1 test de **caso feliz**.
- 1 test por **caso borde** (vacío, cero, máximo, mínimo).
- 1 test por **caso de error** documentado.

### 12.3 Ubicación

Los `test` viven **en el mismo `.pengu`** que la función probada, al final del archivo, agrupados bajo un comentario `# --- Tests ---`.

### 12.4 Estilo

```pengu
test "split returns the original string when separator is empty":
    let parts is calling _split with "abc", ""
    calling ward.assert_eq_int with (calling parts.len), 1
    calling ward.assert_eq_string with (parts at 0), "abc"

test "split handles consecutive separators":
    let parts is calling _split with "a,,b", ","
    calling ward.assert_eq_int with (calling parts.len), 3
```

- Usa `std.ward` (`assert_eq_int`, `assert_eq_string`, `assert_true`, etc.).
- No uses `spark.println` dentro de tests salvo depuración temporal.
- Cada `test` debe poder ejecutarse **aislado** (sin estado global compartido).

---

## 13. Tabla de traducción C → Pengunic

| Patrón C | Anti-Pengunic en Pengu | Pengunic correcto |
|---|---|---|
| `if (x) return a; else return b;` | `var r as int is 0; if x: set r is a else: set r is b; return r` | `return if x then a else b` |
| `for (i=0;i<n;i++) arr[i] = f(i);` | `var i is 0; while i < n: set arr at i is f(i); set i is i + 1` | `let arr is for i from 0 to n then f(i)` |
| `acc = 0; for(...) acc += x;` | `var acc is 0; for x in xs: set acc is acc + x` | (concept) `weave sum shard T where T: Num` |
| `char buf[256]; sprintf(buf, "%d", n);` | `var buf as array of byte with size 256 is ...` | `let s is "{n}"` |
| `strcat(a, b)` | `var r is a` `set r is "{r}{b}"` | `let r is "{a}{b}"` |
| `switch (e) { case A: ...; case B: ...; }` | `if e == A: ... else if e == B: ...` | `judge e: when A -> ... when B -> ...` |
| `struct P p; p.x=1; p.y=2;` | `var p is with x is 0, y is 0; set p.x is 1; set p.y is 2` | `var p as P with: set .x is 1; set .y is 2` |
| `int* out; if (!try(&out)) return;` | (bool + out-param) | `let v is f() or return` |
| `if (p == NULL) return -1;` | `if p == null: return -1` | `let v is f() or else fallback` |
| `malloc` + `free` | `var p as ref to T is ...; banish p` | `defer banish p` si cruza un ámbito, si no `banish p` en el momento adecuado |
| `T** vtable` | (vtable manual) | `concept` + `shard T where T: C` |
| `void* user_data` | `ref to void` | `ref to frozen void` con `frozen` cuando aplique |
| `#define MAX 100` | `const MAX as int is 100` | igual |
| `typedef int UserId;` | `alias UserId as int` | `seal UserId as int` si es nominal |
| `enum { A, B };` | `omen X: A B` | igual con valores explícitos |
| `strlen(s)` | `calling scrolls.len with s` | `s.length` (postfix) |
| `strcmp(a,b) < 0` | `calling scrolls.compare with a, b < 0` | igual (¡`<` no existe en strings!) |
| `x.a(); x.b(); x.c();` | `calling x.a` `calling x.b` `calling x.c` | `calling x.a.b.c` |
| `x.a().b()` con línea larga | `let y is calling x.a.b` en una línea | cadena multilínea `.a` / `.b` |
| `struct { int q; bool ok; }` de retorno | `var out as ref to ...` out-param + `bool` | `into (int, bool)` + desestructurar |
| `r->x = a; r->y = b;` con `a`/`b` locales | `set r->x is a` `set r->y is b` | `with r: set .x is a; set .y is b` |
| `#define X(a) ...` (macro inline) | (función normal) | `@noreturn` / `@export` / `@packed` / `@align` según el caso |
| `__attribute__((noreturn))` | (no expresable) | `@noreturn weave … into void` |
| `__attribute__((packed))` | (no expresable) | `@packed rune …` |
| `__attribute__((aligned(N)))` | (no expresable) | `@align(N)` |
| `struct { struct T next; }` (recursivo) | (no compila, `E0050`) | `rune T cyclus:` + `maybe ref to T` |
| `static inline` con C manual para hot path | `antiquus` sin justificar | `weave inline` primero; `antiquus` solo con benchmark documentado |

---

## 14. Anti-patrones

### 14.1 Concatenar strings con `+`

```pengu
# ❌ E0005
let msg is "Hello, " + name

# ✅
let msg is "Hello, {name}"
```

`+` **nunca** concatena strings. La única composición es la interpolación.

### 14.2 Acumular strings en un loop con `+=`

```pengu
# ❌ O(n²) además de anti-Pengunic
var acc as string is ""
for x in xs:
    set acc is "{acc}{x}"

# ✅ O(n)
let parts is for x in xs then "{x}"
let acc is calling scrolls.join with parts, ""
```

### 14.3 Usar `let` para lo que debería ser `const` top-level

```pengu
# ❌ E0002
let MAX as int is 100

# ✅
const MAX as int is 100
```

### 14.4 `if x is present` seguido de `x.value`

```pengu
# ❌ Anti-Pengunic
if m.is_present:
    let v is m.value
    calling process with v

# ✅
if v as Config is m:
    calling process with v
```

### 14.5 `var tmp` seguido de un solo `if`

```pengu
# ❌
var r as int is 0
if cond:
    set r is a
else:
    set r is b

# ✅
let r is if cond then a else b
```

### 14.6 Llamar `calling x.foo` sin `calling` cuando es una llamada

```pengu
# ❌ ambiguo
x.foo

# ✅ explícito
calling x.foo
```

PenguScript **siempre** requiere `calling` para invocar. No hay azúcar de "método sin paréntesis".

### 14.7 Escribir `self.` en un método

```pengu
# ❌ E0003
weave heal with amount as int into void:
    set self.hp is self.hp + amount

# ✅
weave heal with amount as int into void:
    set self->hp is self->hp + amount
```

### 14.8 Devolver `bool` como "éxito/fallo" sin `maybe`/`result`

```pengu
# ❌ (¿dónde quedó el valor?)
weave find_user with id as int, out as ref to User into bool:
    ...

# ✅
weave find_user with id as int into maybe User:
    ...
```

### 14.9 Redefinir concepts del compilador

```pengu
# ❌ No lo hagas nunca
concept Num:
    weave add with other as int into int
```

`Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum` son **globales del compilador** y no se redefinen.

### 14.10 Duplicar código por tipo

```pengu
# ❌
weave sum_ints with xs as list of int into int: ...
weave sum_floats with xs as list of float into float: ...

# ✅
weave sum shard T where T: Num with xs as list of T into T: ...
```

### 14.11 Usar `banish` sobre vistas o literales

```pengu
# ❌ E0008
banish "literal"
banish (calling ffi.slice_from_ptr with p, n)

# ✅ (nada: los slices no poseen memoria)
```

### 14.12 Liberar un parámetro que no posees

```pengu
# ❌ el callee libera un string que el caller todavía posee
weave log with s as string into void:
    banish s

# ✅ un parámetro no posee memoria: documéntalo y deja la liberación al caller
weave log with s as string into void: ...
```

Los parámetros no poseen memoria en PenguScript. La regla es: **no apliques banish a un
parámetro**; si necesitas poseer una copia, cópiala explícitamente (`pengu_string_copy`,
o `derive Imago` en una rune y clónala).

### 14.13 `while` con acumulador cuando hay comprehension

```pengu
# ❌
var i is 0
var evens as list of int is list of int
while i < 10:
    if i % 2 == 0:
        calling evens.push with i
    set i is i + 1

# ✅
let evens is for i from 0 to 10 when i % 2 == 0 then i
```

### 14.14 Devolver `void` cuando el caller necesita el valor

```pengu
# ❌
weave push_if_new with xs as ref to list of int, v as int into void:
    if not calling xs->contains with v:
        calling xs->push with v

# ✅ (devuelve si lo insertó)
weave push_if_new with xs as ref to list of int, v as int into bool:
    if calling xs->contains with v:
        return false
    calling xs->push with v
    return true
```

### 14.15 Encadenar mutación y lectura

```pengu
# ❌ Anti-Pengunic
calling xs.push with 10.reverse.sort_asc

# ✅ Pengunic
calling xs.push with 10
calling xs.reverse
calling xs.sort_asc
```

### 14.16 Desempaquetar tuplas a mano

```pengu
# ❌
var pair as (int, bool) is calling divide with 10, 2
if pair.v1:
    return pair.v0

# ✅
let (q, ok) is calling divide with 10, 2
if ok:
    return q
```

### 14.17 `antiquus` para lógica expresable en PenguScript

```pengu
# ❌ Anti-Pengunic: C innecesario
antiquus max_of with a as int, b as int into int:
    r"""return a > b ? a : b;"""

# ✅ Pengunic
weave max_of with a as int, b as int into int:
    if a > b:
        return a
    return b
```

### 14.18 `@noreturn` sin garantía

```pengu
# ❌ Anti-Pengunic: puede retornar
@noreturn
weave maybe_fail into void:
    if cond:
        calling spark.exit with 1

# ✅ Pengunic: retorno garantizado
@noreturn
weave fail_hard with msg as string into void:
    calling spark.eprintln with msg
    calling spark.exit with 1
```

### 14.19 `@export` sin prefijo de proyecto

```pengu
# ❌ Anti-Pengunic: colisiona con 'process' de libc
@export("process")
weave do_process into void: ...

# ✅ Pengunic: prefijo de proyecto
@export("pengu_myapp_process")
weave do_process into void: ...
```

### 14.20 `@packed` fuera de la frontera binaria

```pengu
# ❌ Anti-Pengunic
@packed
rune Player:
    name as string
    hp as int

# ✅ Pengunic: solo cuando el layout importa
@packed
rune NetHeader:
    magic as u16
    version as u8
```

### 14.21 `cyclus` decorativo

```pengu
# ❌ Anti-Pengunic
rune Point cyclus:
    x as int
    y as int

# ✅ Pengunic: solo cuando hay recursión real
rune TreeNode cyclus:
    value as int
    left as maybe ref to TreeNode
```

### 14.22 Cuerpo C indentado en `antiquus`

```pengu
# ❌ Anti-Pengunic: el C va indentado dentro del string
antiquus fast_abs with x as int into int:
    """
        return x < 0 ? -x : x;
    """

# ✅ Pengunic: el C a columna 0
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

### 14.23 Cuerpo C sin documentar el motivo

```pengu
# ❌ Anti-Pengunic: ¿por qué C?
antiquus fast_abs with x as int into int:
    r"""return x < 0 ? -x : x;"""

# ✅ Pengunic: motivo medible
## Devuelve |x| sin ramas; el ternario provoca branch misprediction
## de ~8 ns/llamada en el bucle interno (bench/scanline.md).
antiquus fast_abs with x as int into int:
    r"""return x < 0 ? -x : x;"""
```

### 14.24 Inicializador corto en struct grande o heterogéneo

```pengu
# ❌ Anti-Pengunic: ¿qué campos son cortos y cuáles no?
return with host, port, timeout_ms is 30000, retries is 3

# ✅ Pengunic: explícito cuando los campos no son triviales
return with
    host is host,
    port is 8080,
    timeout_ms is 30000,
    retries is 3
```

### 14.25 Usar la forma mutante de `@mutates` donde se espera un valor

```pengu
# ❌ E0066: 'clamp' muta el receptor y no devuelve nada
var capped as int is calling hp.clamp with 0, 100

# ✅ Pengunic: la forma pura devuelve el valor
var capped as int is calling hp.get_clamp with 0, 100
```

Un método `@mutates` (y las formas in-place de `std.scrolls`) es una **sentencia**:
muta el receptor y no produce ningún valor. Dentro de una cadena o de una
expresión hay que usar `get_<name>`. Ver §6.7 y `LANGUAGE.md` §10.1.

### 14.26 Rune con discriminante cuando bastaría un `omen`

```pengu
# ❌ Anti-Pengunic: el discriminante añade una etiqueta que la unión no necesita
rune Event:
    kind as EventKind
    key as string
    x as int
    y as int

omen EventKind:
    Key
    Click

# ✅ Pengunic: el `omen` algebraico dice exactamente qué lleva cada variante
omen Event:
    Key with key as string
    Click with x as int, y as int
```

### 14.27 Etiqueta innecesaria en un único bucle

```pengu
# ❌ Anti-Pengunic: una etiqueta que ningún 'break'/'continue' apunta
outer: for x in xs:
    calling process with x

# ✅ Pengunic: el único bucle no necesita etiqueta
for x in xs:
    calling process with x
```

Una etiqueta sirve para abandonar un bucle **externo** desde dentro de uno
interno (`LANGUAGE.md` §7.5). En un único bucle añade un nombre, riesgo de
`E0069` (las etiquetas son locales a la función y únicas) y ninguna capacidad.

### 14.28 `type of` usado como comprobación de tipos en runtime

```pengu
# ❌ Anti-Pengunic: 'type of' es una constante de compilación, no una comprobación en runtime
if type of value == "int":
    calling handle_int with value
else:
    calling handle_other with value

# ✅ Pengunic: ramifica en tiempo de compilación con un genérico (o una sobrecarga)
weave handle shard T with value as T into void:
    calling print with "{value}"
```

`type of expr` produce un literal de cadena prestado elegido al compilar; la rama
`else` de arriba está muerta antes de emitir C. Úsalo para diagnósticos y
aserciones de tests, y usa un genérico/sobrecarga para el comportamiento.

### 14.29 `derive Donum`

```pengu
# ❌ E0005: 'Donum' is automatic for rune 'Point'; no 'derive' is needed
rune Point derive Donum:
    x as int

# ✅ Pengunic: todos los campos son defaultables, así que 'donum Point' funciona
rune Point:
    x as int
```

`Donum` **no** es uno de los cinco conceptos derivables (`Par`, `Ordo`,
`Vinculum`, `Imago`, `Nexus`). Una rune o un echo lo obtiene automáticamente
cuando todos sus campos son defaultables (`LANGUAGE.md` §11.4).

---

## 15. Excepciones documentadas

Una regla de estilo que la biblioteca estándar no puede cumplir es peor que no
tener regla: enseña a los contribuidores a ignorar la guía. La Fase 7 del roadmap
midió cada regla que la auditoría de 1.0 marcó como incumplible y registra aquí el
resultado — *exigida*, *acotada* o *relajada con una excepción con nombre*. Los
números se pueden volver a medir con el comando de la última columna; la
derivación completa está en [`AUDIT_1.0_FASE7.md`](AUDIT_1.0_FASE7.md) §7.7.

| Regla (§) | Estado | Medición | Cómo re-medir |
|---|---|---|---|
| Un `weave` público lleva docstring `##` (§11.2) | **Exigida** | `weave` 1314/1315. La única excepción es `std/cipher.pengu:375 weave _b32_val`, un helper **privado** — así que la cobertura de funciones *públicas* es del 100 % | `python -m pytest tests/test_std_docs_completeness.py -q` |
| Todo `declare` / `const` / `alias` / `omen` está documentado (§11.3) | **Acotada fuera** | `declare` 630/1862 (33,8 %), `const` 123/593 (20,7 %), `alias` 50/153 (32,7 %), `omen` 4/66 (6,1 %). La mayoría son **bindings generados** cuyo texto de documentación es el comentario de la cabecera C de origen; exigir el 100 % obligaría a inventar prosa para superficie de terceros | `python -m pytest tests/test_std_docs_completeness.py -q` |
| Indentar con 4 espacios, nunca tabuladores (§3.1) | **Exigida** | `.pengufmt.toml` y `std/.pengufmt.toml` fijan `tab_size = 4`, `pengu_project._resolve_indent` devuelve 4 por defecto, y el formateador es idempotente en toda la stdlib | `python pengu_project.py fmt --check std/` |
| Un local no puede ensombrecer un `weave` global (§2.6) | **Exigida** | `0 W0005` en los 27 módulos escritos a mano de `std/` | `python pengu_project.py check --entry std/<módulo>.pengu` |
| Sin conversiones inseguras (§9.4) | **Exigida** | `0 W0001` en los 27 módulos y **cero** llamadas a `transmute` en `std/` — la única aparición es un comentario explicativo en `std/ffi.pengu:67`. Si alguna vez hiciera falta, queda confinada a `std/ffi` y `std/filum` y debe ser del mismo tamaño | `python pengu_project.py check --entry std/<módulo>.pengu` |
| Los nombres y las firmas son consistentes entre módulos (§10.3) | **Relajada — excepción con nombre** | `std.loom` y `std.tally` comparten deliberadamente 15 nombres con contratos *distintos* (`loom.mean([1,2]) == 1.5` frente a `tally.mean([1,2]) == 1`; `loom.mode([])` → `none` frente a `tally.mode([])` → `0`). Son contratos documentados, no deriva | ver [`LANGUAGE.md` §19.1.1](LANGUAGE.md#1911-choosing-between-stdloom-and-stdtally) |
| Los `antiquus` públicos documentan motivo medible (§20.6) | **En observación** | Sin corpus todavía; primera medición en la próxima fase | `python -m pytest tests/test_antiquus_docs.py -q` (pendiente) |
| Los `@export` usan prefijo `pengu_<módulo>_` (§19.2) | **En observación** | Sin corpus todavía | `python pengu_project.py check --entry std/<módulo>.pengu` |
| Las cadenas de métodos no mezclan mutación y lectura (§16.1) | **En observación** | Sin corpus todavía | `pengu fmt --check std/` (regla heurística, no automática) |
| Los `rune` con `cyclus` documentan la indirección (§21.3) | **En observación** | Sin corpus todavía | `python -m pytest tests/test_std_docs_completeness.py -q` |

Dos consecuencias que conviene decir claramente, porque auditorías anteriores
afirmaban lo contrario:

1. **La regla de indentación nunca fue el problema.** Una auditoría anterior
   registró que "`pengu fmt` impone 2 espacios y `--indent 4` corrompe el
   archivo". Es falso desde `c42776c`: la configuración fija 4, el valor por
   defecto es 4 y `fmt --check std/` sale limpio. La prosa obsoleta que decía
   "2 espacios" en `LANGUAGE.md` §20.7 y `CHEATSHEET.md` se corrigió en la Fase 7.
2. **"Docstring en el 100 % de las declaraciones" no es una regla que valga la
   pena.** Acotada a *funciones públicas* se cumple exactamente; extendida a la
   superficie generada de `declare` exigiría documentar código que este proyecto
   no escribe.

Una regla sólo entra en esta tabla con una medición y un comando. Si un cambio
futuro rompe una fila *Exigida*, eso es una regresión, no una excepción nueva.

> Cuando el corpus exista, estas filas se miden con el mismo estándar que las demás: o pasan a **Exigida** con número, o se acotan, o se relajan con excepción con nombre.

---

## 16. Cadenas de métodos

La sintaxis `calling x.a.b.c` permite encadenar varias llamadas a método sobre un solo receptor. Cada eslabón `.nombre` se resuelve contra el tipo que produce el eslabón anterior. Es **azúcar de composición**, no llamada con paréntesis: el bloque `with` pertenece al **último** eslabón.

### 16.1 Cuándo encadenar

**Encadena cuando la cadena lee como una transformación lineal**, sin ramas ni efectos laterales intermedios:

```pengu
# ✅ Pengunic: cada paso transforma el valor anterior
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"

# ✅ Pengunic: cadena de transformaciones puras sobre colecciones
let top5 is calling scores.filter_positive.sort_desc.take with 5
```

**No encadenes cuando:**

| Situación | Qué hacer |
|---|---|
| Un eslabón intermedio necesita un nombre propio | Rompe la cadena y nómbralo |
| La cadena supera 4–5 eslabones | Divide en funciones |
| Un eslabón muta el receptor (`push`, `set_*`, `clear`) | Separa mutación de lectura |
| Un eslabón requiere argumentos y no es el último | Rompe la cadena |
| Un eslabón resuelve a un **campo**, no a un método | No es cadena, es acceso a campo |

```pengu
# ❌ Anti-Pengunic: mezcla lectura y mutación
calling xs.push with 10.reverse.sort_asc

# ✅ Pengunic: separa la mutación de la lectura
calling xs.push with 10
calling xs.reverse
calling xs.sort_asc
```

### 16.2 Cadenas multilínea

Para cadenas largas, una línea de continuación empieza por `.` (o `->`) y se pliega en la línea anterior antes del lexer. El plegado **preserva la numeración de líneas**: un diagnóstico sobre una expresión encadenada señala la línea donde *empieza* la cadena.

```pengu
# ✅ Pengunic: multilínea, un eslabón por línea
let slug is calling raw
    .trim
    .lower
    .replace with " ", "-"

# ❌ Anti-Pengunic: línea larga ilegible
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"
```

**Reglas de formato:**

- Un eslabón por línea.
- Indentación: **un nivel** (4 espacios) respecto a la línea que abre la cadena.
- El primer eslabón (`.trim`) va en la línea siguiente al receptor.
- No mezcles `.` y `->` en la misma cadena.
- Las líneas dentro de un string con comillas triples **nunca** se pliegan.

### 16.3 El bloque `with` pertenece al último eslabón

```pengu
# ✅ 'with " ", "-"' se aplica a '.replace', no a '.lower'
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"
```

Si un eslabón intermedio necesita argumentos y no es el último, la cadena no se puede escribir; pártela:

```pengu
# ❌ Anti-Pengunic: no hay forma de dar 'with 0, 4' al 'substring' intermedio
# let slug is calling raw.get_trim.get_substring with 0, 4.lower

# ✅ Pengunic: dos expresiones, nombres explícitos
let head is calling raw.get_trim.get_substring with 0, 4
let slug is calling head.lower
```

### 16.4 Cadenas y genéricos

La resolución de cada eslabón es monomorfización bajo demanda: el compilador instancia el método genérico solo para el tipo concreto del eslabón anterior. **No hay sobrecoste en runtime.**

```pengu
# ✅ Un solo 'calling' encadena métodos genéricos sobre 'map of shard K to shard V'
let short is calling registry
    .keys_sorted
    .first_or with "none"

# ✅ En una cadena, el receptor puede ser un 'ref to T':
calling self
    .remove with old_key
    .put with new_key, val
```

Cuando el receptor es `self` dentro de un `enchanting`, la cadena funciona igual y es la forma idiomática de aplicar varias mutaciones coordinadas:

```pengu
enchanting Registry:
    weave rename_key with old_key as K, new_key as K into bool:
        if not (calling self.contains with old_key):
            return false
        var val as V is self at old_key
        calling self
            .remove with old_key
            .put with new_key, val
        return true
```

### 16.5 Anti-patrones

```pengu
# ❌ Cadena de campos (no es cadena de métodos)
calling p.address.city.zip_code

# ❌ Cadena con un mutador en medio
calling xs.push with 10.reverse

# ❌ Cadena de más de 5 eslabones
calling raw.get_trim.get_lower.get_replace(" ", "-").split("-").filter_nonempty.first_or("none")

# ❌ Mezclar '.' y '->'
calling self.method1->method2

# ✅ Pengunic equivalente
let slug is calling raw
    .trim
    .lower
    .replace with " ", "-"
let first is calling slug.split with "-" . first_or with "none"
```

---

## 17. Múltiples valores de retorno (tuplas)

Cuando una operación produce varios valores relacionados, **declara una tupla** en lugar de forzar al caller a usar `maybe` + out-params o un `rune` de un solo uso.

### 17.1 Cuándo usar tuplas (y cuándo no)

| Situación | Tipo | Ejemplo |
|---|---|---|
| Un valor **y** un indicador de éxito | `(T, bool)` | `divide → (int, bool)` |
| Un valor **y** metadatos calculados juntos | `(T, U)` | `parse_header → (string, usize)` |
| Varios valores **con nombre propio** en el dominio | `rune` dedicado | `Point → rune` |
| Un valor o un fallo detallado | `result of T to E` | §5 |
| Un valor o nada | `maybe T` | §5 |

**Regla de decisión:**

> Si los valores tienen nombres independientes en el dominio (un `Point` tiene `x` e `y` **como conceptos**), usa un `rune`. Si solo tienen sentido juntos y son efímeros (se desempaquetan inmediatamente), usa una tupla.

### 17.2 Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| `weave` que devuelve tupla | verbo base, sin sufijo | `divide`, `split_first`, `parse_pair` |
| Nombres en la desestructuración | `snake_case` descriptivo | `let (q, ok) is …` |
| Acceso por campo en tuplas anónimas | `v0`, `v1`, … (rara vez) | `pair.v0` |

**Nunca** mezcles tuplas con los prefijos de §2.3:

- Una función que devuelve `(T, bool)` **no** debe llamarse `try_*` ni `parse_*`: esos prefijos implican `maybe`/`result`.
- Una función que devuelve `(T, bool)` **no** debe llamarse `find_*`: ese prefijo implica `maybe`.

### 17.3 Desestructuración canónica

```pengu
# ✅ Pengunic: desestructura al recibir, usa los nombres directamente
weave compute into int:
    let (q, ok) is calling divide with 10, 2
    if not ok:
        return 0
    return q

# ❌ Anti-Pengunic: desempaquetar a mano
weave compute into int:
    var pair as (int, bool) is calling divide with 10, 2
    if not pair.v1:
        return 0
    return pair.v0
```

- El número de nombres debe coincidir con el número de elementos (`E0017`).
- Se prefieren las formas **con paréntesis** `let (x, y) is p` en código nuevo; `let x, y is p` es equivalente pero menos visible.
- Los nombres van en `snake_case` descriptivo, **no** en `v0`/`v1`.

### 17.4 Tuplas y `try` / `or else` / `or:`

Las tuplas **no** componen con `try`, `or else` ni bloques `or:`. Si el resultado puede fallar, usa `result of T to E`:

```pengu
# ❌ Anti-Pengunic: mezclar tupla y 'try'
# let (v, ok) is try calling parse_pair with s

# ✅ Pengunic: 'result' cuando puede fallar
weave parse_pair with s as string into result of (int, int) to string:
    ...
```

### 17.5 Anti-patrones

```pengu
# ❌ Tupla para dos valores con nombre propio
weave make_point with x as int, y as int into (int, int):
    return x, y
# ✅ Esto es un 'rune Point'.

# ❌ Tupla + 'try'
# let (v, ok) is try calling f with x

# ❌ Nombres v0/v1 en la desestructuración
let (v0, v1) is calling divide with 10, 2
```

---

## 18. Inicializadores cortos de struct

Dentro de un literal `with`, un campo puede omitir `is <valor>` y tomar el binding del mismo nombre. La reescritura ocurre **antes de parsear** y nunca añade ni quita líneas, así que `#line` y las posiciones de diagnóstico siguen exactas.

### 18.1 Cuándo usar la forma corta

```pengu
# ✅ Pengunic: nombre de campo y binding coinciden exactamente
weave make with name as string, hp as int into Player:
    return with name, hp

# ✅ equivalente explícito (a veces preferible por claridad)
weave make with name as string, hp as int into Player:
    return with name is name, hp is hp
```

| Situación | ¿Forma corta? |
|---|---|
| Campo `name`, binding `name`, mismo tipo | ✅ Sí |
| Campo `name`, binding `n` (distinto nombre) | ❌ No — `with name is n` |
| Campo `name`, binding `name` pero tipo convertible (`seal`) | ❌ No — convierte explícitamente |
| Campo privado `_secret`, binding `_s` | ❌ No — la privacidad y el binding son cosas distintas |
| Campo `name`, binding local que ensombrece un `weave` global | ❌ No — evita `W0005` |

### 18.2 Mezcla con la forma explícita

```pengu
var p as Player with:
    name,                       # forma corta
    hp is 100,                  # forma explícita
    _secret_id is 0
```

Se pueden mezclar sin problema. La única restricción es que cada miembro sea **o** un nombre desnudo **o** `campo is <expr>`; no se admiten nombres con `as` ni expresiones sueltas.

### 18.3 La forma corta **no** convierte tipos

```pengu
# ❌ Anti-Pengunic: 'name' es 'string' pero el campo espera un 'seal Name'
weave make with name as string into User:
    return with name                # E0005

# ✅ Pengunic: convierte explícitamente
weave make with name as string into User:
    return with name is (name to Name)
```

La forma corta es azúcar sintáctico para `campo is campo`; no inserta conversiones.

### 18.4 Anti-patrón: forma corta en structs grandes

```pengu
# ❌ Anti-Pengunic: ¿qué campos son cortos y cuáles explícitos?
rune Config:
    host as string
    port as int
    timeout_ms as int
    retries as int

weave make_default with host as string into Config:
    let port is 8080
    return with host, port, timeout_ms is 30000, retries is 3

# ✅ Pengunic: explícito si los campos no son triviales
weave make_default with host as string into Config:
    return with
        host is host,
        port is 8080,
        timeout_ms is 30000,
        retries is 3
```

**Regla:** la forma corta es aceptable solo cuando **todos los campos del literal son o cortos o explícitos pero simples**, y el struct tiene ≤ 4 campos. En structs grandes o con campos de distinto origen, la forma explícita gana en legibilidad.

---

## 19. Atributos de declaración

PenguScript expone cuatro atributos a nivel de declaración. Cada uno tiene reglas de estilo propias y una justificación concreta.

### 19.1 `@noreturn`

Marca un `weave` que **nunca retorna** a quien lo llamó. El weave debe declararse `into void` (`E0056`).

```pengu
# ✅ Pengunic: aborto garantizado
@noreturn
weave fail_hard with msg as string into void:
    calling spark.eprintln with msg
    calling spark.exit with 1
```

**Reglas:**

- Solo se aplica a `weave`; nunca a `rune`, `omen` ni `declare`.
- El cuerpo **debe** terminar en una ruta que no retorne (`exit`, `panic`, `abort`, un `antiquus` con `_Noreturn`).
- **No** marques `@noreturn` una función que solo *probablemente* no retorna; el compilador no lo verifica más allá del contrato de tipo.
- El C generado lleva `_Noreturn` tanto en el prototipo como en la definición (`__declspec(noreturn)` en MSVC).

### 19.2 `@export("c_name")`

Fija el símbolo C emitido. Es el punto de entrada FFI para consumidores C.

```pengu
# ✅ Pengunic: nombre C estable con prefijo de proyecto
@export("pengu_myapp_add")
weave add with a as int, b as int into int:
    return a + b
```

**Reglas de estilo:**

- **Nunca** exportes con el nombre C por defecto (el que emitiría el compilador). Si exportas, **siempre** pasa un nombre C explícito.
- El nombre C debe empezar por `pengu_<módulo>_` (o el namespace del proyecto). Nunca uses un nombre "desnudo" (`process`, `add`, `read`): colisiona con libc.
- El nombre C debe ser **estable**: cambiarlo es un **breaking change de ABI**, no de API.
- Un `weave` exportado es **raíz de DCE**: sobrevive aunque nadie lo llame desde PenguScript. No exportes funciones internas "por si acaso".
- El nombre en PenguScript **no cambia**: `calling add with 1, 2` sigue siendo el call site.

### 19.3 `@packed`

Elimina el relleno entre campos de un `rune`. Solo debe usarse cuando **el layout binario importa**.

```pengu
# ✅ Pengunic: struct que mapea un formato en disco o red
@packed
rune NetHeader:
    magic as u16
    version as u8
    flags as u8
    length as u32
```

**Reglas:**

- **Solo** en `rune` que cruzan una frontera binaria (archivo, red, FFI con `memcpy`).
- **Nunca** en `rune` de uso general: rompe la alineación natural y penaliza el acceso.
- Si un `rune` tiene `@packed`, **documéntalo** en el docstring del tipo: es un contrato de layout.
- `@packed` **no se aplica a `echo`**: una unión de C tiene sus propias reglas.

### 19.4 `@align(N)`

Fija la alineación de un `rune` o de un campo. `N` debe ser potencia de dos entre 1 y 128 (`E0056`).

```pengu
# ✅ Pengunic: alinear un buffer para SIMD
@align(32)
rune AlignedBlock:
    _data as array of f32 with size 8

# ✅ alinear un campo concreto dentro de su struct
rune Mixed:
    a as u8
    @align(4) b as u32
    c as u8
```

**Reglas:**

- **Úsalo** cuando una API C exige una alineación concreta (SIMD, DMA, instrucciones atómicas).
- **No lo uses** para "optimizar" sin medir: la alineación natural suele ser la correcta.
- Documenta en el docstring **por qué** se necesita esa alineación, no solo cuál es.

### 19.5 Anti-patrones

```pengu
# ❌ @noreturn sin garantía de no-retorno
@noreturn
weave maybe_fail into void:
    if cond:
        calling spark.exit with 1
    # si 'cond' es falsa, retorna → E0056

# ❌ @export sin prefijo de proyecto
@export("process")             # colisiona con 'process' de libc
weave do_process into void: ...

# ❌ @packed en un rune de uso general
@packed
rune Player:                   # no cruza ninguna frontera binaria
    name as string
    hp as int

# ❌ @align sin documentar el motivo
@align(64)
rune Foo:                      # ¿por qué 64? nadie lo sabe
    x as int
```

---

## 20. Bloques C embebidos (`antiquus`)

Un `antiquus` declara una función cuyo cuerpo es **C literal**. Es la vía de escape del lenguaje, y por eso mismo **la regla de estilo más importante del documento**: cada `antiquus` es deuda técnica explícita y debe justificarse.

### 20.1 Cuándo **sí** usar `antiquus`

Solo en cuatro casos, en este orden de preferencia:

1. **Primitivas del sistema** que no tienen binding en `std.*`: syscalls, instrucciones de CPU, contadores de hardware.
2. **Código crítico para el rendimiento ya medido**, donde la diferencia es real y verificable.
3. **Glue FFI** para una API C que no se puede expresar como `declare` (por ejemplo, callbacks con contexto que exigen macros C).
4. **Reimplementar helpers del runtime** en el módulo `std` que los usa, para que DCE pueda podarlos.

### 20.2 Cuándo **no** usar `antiquus`

- **Nunca** para lógica que PenguScript ya expresa (bucles, condicionales, manejo de errores, colecciones). Reescribir eso en C pierde type checking y ownership tracking sin ganar nada.
- **Nunca** para FFI a una biblioteca existente: usa `declare` + `include` + `link`.
- **Nunca** para "saltarse" el sistema de tipos.

> **Regla mnemotécnica:** si tu `antiquus` tiene un `if` o un `for`, probablemente debería ser un `weave`.

### 20.3 Nomenclatura

| Rol | Nombre | Ejemplo |
|---|---|---|
| Primitiva de sistema | verbo + sufijo del sistema | `read_tsc`, `cpu_relax`, `syscall_write` |
| Helper de bajo nivel | `fast_*`, `raw_*` | `fast_abs`, `raw_memcpy` |
| Reimplementación de runtime | mismo nombre que el helper | `print_int`, `list_push` |
| Glue FFI | nombre del símbolo C con prefijo | `cb_register_signal` |

- **Prefijo `pengu_` prohibido** para `antiquus` de usuario (lo usa el compilador).
- **Prefijo `_`** si es privado del módulo.

### 20.4 `@export` y DCE

Un `antiquus` en un módulo `std/` o `lib/` es **podado por DCE** si nadie lo referencia. Para que sobreviva como punto de entrada FFI:

```pengu
# ✅ Pengunic: 'antiquus' que debe sobrevivir como símbolo C
@export("pengu_fast_double")
antiquus fast_double with x as int into int:
    r"""
    return x * 2;
    """
```

**Regla:** todo `antiquus` en `std/` o `lib/` que sea punto de entrada FFI **debe** llevar `@export("...")` con prefijo `pengu_<módulo>_`.

### 20.5 El cuerpo C: reglas de estilo

```pengu
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

- **Usa `r"""..."""`** cuando el C contiene barras invertidas (`printf`, regex, rutas): evita escapes dobles.
- **Usa `"""..."""`** cuando no las contiene; es más legible.
- **Indentación del C:** el cuerpo se emite con `#line 1 "antiquus:<nombre>"`, así que la indentación del C dentro del string es **literal**. Mantén el C a columna 0 dentro del string.

```pengu
# ❌ Anti-Pengunic: el C queda indentado, ofusca el diagnóstico
antiquus fast_abs with x as int into int:
    """
        return x < 0 ? -x : x;
    """

# ✅ Pengunic: el C a columna 0
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

- **Una sola responsabilidad por `antiquus`:** si el C tiene más de ~10 líneas, divídelo.
- **Parámetros con nombres C válidos:** `if`, `int`, `while` como parámetros son `E0035`; usa `condition`, `value`, `running`.
- **`many T` prohibido:** usa `slice of T` y lee `.data` / `.len`.

### 20.6 Documentación obligatoria

Todo `antiquus` público **debe** documentar:

```pengu
## Devuelve el valor absoluto de `x` sin ramas usando la instrucción de CPU.
##
## ## Motivo
## Se usa en el bucle interno de `render_scanline`, donde la rama del
## ternario provoca un `branch misprediction` medido de ~8 ns/llamada
## (ver benchmarks/scanline.md). Un `weave` equivalente es 3× más lento
## en el mismo perfil.
##
## ## Precondiciones
## - `x` debe ser un `int` de 32 bits.
##
## ## Memoria
## No asigna memoria. No hay nada que liberar.
antiquus fast_abs with x as int into int:
    r"""
    return x < 0 ? -x : x;
    """
```

**Secciones obligatorias:**

1. **Resumen** de una línea.
2. **Motivo:** por qué C y no PenguScript. Debe ser **medible** (benchmark, limitación del lenguaje, contrato de C).
3. **Precondiciones** si las hay (ownership, alineación, rango de valores).
4. **Memoria:** quién libera, o "no asigna".

### 20.7 Anti-patrones

```pengu
# ❌ Anti-Pengunic: lógica que PenguScript ya expresa
antiquus sum_list with xs as list of int into int:
    r"""
    int acc = 0;
    for (int i = 0; i < xs.len; i++) acc += ((int*)xs.data)[i];
    return acc;
    """
# ✅ Debería ser: weave sum shard T where T: Num ...

# ❌ Anti-Pengunic: sin @export en std/
antiquus fast_double with x as int into int:
    r"""return x * 2;"""
# Será podado por DCE si nadie lo llama.

# ❌ Anti-Pengunic: nombre C de parámetro inválido
antiquus check with int as int into bool:    # E0035
    r"""return int > 0;"""

# ❌ Anti-Pengunic: cuerpo con 'many T'
antiquus count with xs as many int into int: # E0005
    r"""return xs.len;"""
```

---

## 21. `cyclus` y tipos recursivos

`cyclus` declara explícitamente que un `rune` es autorreferencial. **No** hace legal el ciclo por valor: el ciclo debe romperse con indirección (`ref to`, `maybe ref to`, `slice`, `list`, `map`).

### 21.1 Cuándo usar `cyclus`

Solo cuando el tipo **realmente se contiene a sí mismo** de forma intencional:

```pengu
# ✅ Pengunic: árbol recursivo con indirección explícita
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T     # 'maybe ref' rompe el ciclo
    children as list of Node of T      # 'list' rompe el ciclo
```

### 21.2 Cuándo **no** usar `cyclus`

- **Nunca** en un `rune` sin recursión, ni siquiera "por si acaso". Es ruido.
- **Nunca** en un `rune` que se contiene **por valor** (`next as Bad`): eso es `E0050` y `cyclus` no lo arregla.
- **Nunca** en `echo` ni `omen`.

### 21.3 Documentación

Un `rune` con `cyclus` **debe** documentar **dónde** está la indirección:

```pengu
## Nodo de un árbol binario de enteros.
##
## ## Recursión
## El ciclo se rompe en `left` y `right` mediante `maybe ref to`; el nodo
## nunca se contiene por valor. Un árbol vacío se representa con
## `maybe none` en los hijos.
rune TreeNode cyclus:
    value as int
    left as maybe ref to TreeNode
    right as maybe ref to TreeNode
```

### 21.4 Anti-patrón: `cyclus` decorativo

```pengu
# ❌ Anti-Pengunic: 'cyclus' sin recursión real
rune Point cyclus:
    x as int
    y as int

# ❌ Anti-Pengunic: 'cyclus' sin documentar dónde está la indirección
rune Node cyclus:
    value as int
    next as maybe ref to Node
```
