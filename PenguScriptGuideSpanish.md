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

1. [Filosofía del código Pengunic](#1-filosofía-del-código-pengunic)
2. [Nomenclatura](#2-nomenclatura)
3. [Organización de módulos y archivos](#3-organización-de-módulos-y-archivos)
4. [Expresiones sobre sentencias](#4-expresiones-sobre-sentencias)
5. [Optionals, resultados y errores](#5-optionals-resultados-y-errores)
6. [Enchantments, rituals y concepts](#6-enchantments-rituals-y-concepts)
7. [Genéricos y bounds](#7-genéricos-y-bounds)
8. [Gestión manual de memoria](#8-gestión-manual-de-memoria)
9. [Interoperabilidad con C](#9-interoperabilidad-con-c)
10. [Diseño de APIs](#10-diseño-de-apis)
11. [Documentación (`##`)](#11-documentación-)
12. [Pruebas (`test`)](#12-pruebas-test)
13. [Tabla de traducción C → Pengunic](#13-tabla-de-traducción-c--pengunic)
14. [Anti-patrones](#14-anti-patrones)
15. [Excepciones documentadas](#15-excepciones-documentadas)

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
| Archivo fuente | `snake_case.pengu` | `scrolls.pengu`, `precis.pengu` |
| Archivo de declaración | `snake_case.d.pengu` | `sqlite3.d.pengu`, `raylib.d.pengu` |
| Módulo (import) | `snake_case`, sustantivo o adjetivo | `std.scrolls`, `std.atlas`, `std.rites` |
| Módulo de colecciones | sustantivo en **plural** | `std.rites`, `std.scrolls` (no `rite`, `scroll`) |
| Módulo de capacidad | sustantivo **singular abstracto** | `std.cipher`, `std.loom` |

**Reglas:**
- Los módulos estándar viven bajo `std.` y su nombre es un **sustantivo latino o inglés**: `spark`, `scrolls`, `oracle`, `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `rites`, `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `regulus`, `parchment`, `seal`, `precis`, `filum`, `loom`, `invoke`, `ffi`, `celeris`, `arithmancy`.
- Nunca uses `utils`, `helpers`, `common`, `misc`. Si no puedes nombrarlo con un sustantivo concreto, **el módulo no tiene una responsabilidad clara**.
- Las siglas se escriben en `snake_case` minúsculo como módulo: `std.ffi`, `std.uuid`, `std.xxhash`.

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
- ✅ `init` solo se acepta cuando **realmente inicializa algo externo** y no devuelve el tipo (p. ej. `raylib.InitWindow` como binding C; en `std.*` puro el idiomático es `new`).

### 2.6 Variables, locales y parámetros

| Elemento | Estilo | Ejemplo |
|---|---|---|
| Local `var` / `let` | `snake_case` descriptivo | `total_count`, `parsed_items` |
| Parámetro | `snake_case`, corto si es obvio | `x`, `y`, `item`, `key`, `fallback` |
| Booleano local | prefijo `is_`, `has_`, `can_` | `is_ready`, `has_key`, `can_retry` |
| Índice de loop | `i`, `j`, `k` solo en loops cortos; si no, `index`, `row`, `col` | |
| Acumulador | `acc`, `sum`, `total`, `result` | |
| Discard | `_` | `for _, v in col:` |
| Temporal interno | `tmp`, `raw`, `staged` | Nunca expuesto en API |

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
| `precis.get(url, headers)` — ninguno es "el sujeto" | función de módulo | `calling precis.get with url` |
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
| `a == b`, `a != b` | `T: Par` |
| `a < b`, `a <= b`, `a > b`, `a >= b` | `T: Ordo` |
| `donum T` | `T: Num`, `Integrum`, `Par`, `Ordo`, `Forma` o `Donum` |
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
# std/sqlite3.d.pengu
include "sqlite3.h"
link "sqlite3"

rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to ref to opaque into int
declare sqlite3_close with db as ref to opaque into int
```

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
| `std.regulus` | `re` de Python; `regex` de Rust |
| `std.precis` | `net/http` de Go; `requests` de Python |
| `std.filum` | `threading`, `sync` de Go; `std::thread` de Rust |

Si al leer tu API un usuario de Python/Rust/Go dice *"esto lo haría en dos líneas con `X`"*, **tu API necesita ese `X`**.

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

`Num`, `Integrum`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum` son **globales del compilador** y no se redefinen.

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
