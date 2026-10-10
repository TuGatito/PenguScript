# Pengunic Style Guide

> **Covered version:** PenguScript **2.0.0**
> **Language policy.** English is canonical: this guide is normative. The Spanish
> translation [`PenguScriptGuideSpanish.md`](PenguScriptGuideSpanish.md) is
> **non-normative**; where they disagree, this file wins. `tests/test_language_policy.py`
> checks that the two stay structurally in step.
>
> This document defines the naming, organization and language conventions that govern the standard library (`std.*`) and that every user module should follow. It is the normative companion of [`LANGUAGE.md`](LANGUAGE.md): where the *Language Reference* describes what *can* be written, this document prescribes what *should* be written.
> Read it the way you read [PEP 8](https://peps.python.org/pep-0008/) + [PEP 20](https://peps.python.org/pep-0020/) for Python, or the [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) for Rust.

---

## Table of contents

1.  [Pengunic code philosophy](#1-pengunic-code-philosophy)
2.  [Naming](#2-naming)
3.  [Module and file organization](#3-module-and-file-organization)
4.  [Expressions over statements](#4-expressions-over-statements)
5.  [Optionals, results and errors](#5-optionals-results-and-errors)
6.  [Enchantments, rituals and concepts](#6-enchantments-rituals-and-concepts)
7.  [Generics and bounds](#7-generics-and-bounds)
8.  [Manual memory management](#8-manual-memory-management)
9.  [C interoperability](#9-c-interoperability)
10. [API design](#10-api-design)
11. [Documentation (`##`)](#11-documentation-)
12. [Tests (`test`)](#12-tests-test)
13. [C → Pengunic translation table](#13-c--pengunic-translation-table)
14. [Anti-patterns](#14-anti-patterns)
15. [Documented exceptions](#15-documented-exceptions)
16. [Method chaining](#16-method-chaining)
17. [Multiple return values (tuples)](#17-multiple-return-values-tuples)
18. [Shorthand struct initializers](#18-shorthand-struct-initializers)
19. [Declaration attributes](#19-declaration-attributes)
20. [Embedded C blocks (`antiquus`)](#20-embedded-c-blocks-antiquus)
21. [`cyclus` and recursive types](#21-cyclus-and-recursive-types)

---

## 1. Pengunic code philosophy

PenguScript is not "C with syntactic sugar". The language offers high-level constructs —comprehensions, value blocks, `judge`, `with:`, `or:`, `enchanting`, `concept`— and **not using them when they are called for is a style defect**, just as not using list comprehensions in Python when they are natural is a defect.

The six Pengunic principles:

| # | Principle | In one sentence |
|---|---|---|
| 1 | **Explicit over hidden** | Every action has a single obvious spelling. `+` is numeric, interpolation `"{x}"` is the only string composition. |
| 2 | **Expressions over statements** | If the language gives you `do:`, `if`-value, `for ... then ...`, use them. A `var tmp` followed by an `if` to assign is anti-Pengunic. |
| 3 | **Compose over inherit** | `concept`s are static contracts. Prefer `shard T where T: Num` to duplicating the same function per type. |
| 4 | **Types carry meaning** | Use `seal` for newtypes, `maybe T` for "may be missing", `result of T to E` for "may fail". Do not encode failure in a sentinel. |
| 5 | **Zero-cost abstractions** | Everything the compiler resolves at compile time (`enchanting`, `concept`, `shard`, `when`, `derive`) is free. Prefer it to manual dynamic dispatch. |
| 6 | **C is the boundary, not the model** | Pengunic code reads like PenguScript. It only becomes explicitly C when the FFI boundary is crossed (`declare`, `ref to`, `bytes of`, `frozen`). |

> **Mnemonic rule:** If your `std.*` module could be compiled as-is to C without a rewrite, you are probably writing C in PenguScript syntax. **Rewrite it the Pengunic way.**

---

## 2. Naming

The language imposes styles by convention (`snake_case` for values, `PascalCase` for types). This section formalizes them and adds rules for APIs.

### 2.1 Files and modules

| Element | Rule | Examples |
|---|---|---|
| Source file | `snake_case.pengu` | `scrolls.pengu`, `precis.pengu` |
| Declaration file | `snake_case.d.pengu` | `sqlite3.d.pengu`, `raylib.d.pengu` |
| Module (import) | `snake_case`, noun or adjective | `std.scrolls`, `std.atlas`, `std.rites` |
| Collection module | noun in the **plural** | `std.rites`, `std.scrolls` (not `rite`, `scroll`) |
| Capability module | **abstract singular** noun | `std.cipher`, `std.loom` |

**Rules:**
- Standard modules live under `std.` and their name is a **Latin or English noun**: `spark`, `scrolls`, `oracle`, `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `rites`, `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `regulus`, `parchment`, `seal`, `precis`, `filum`, `loom`, `invoke`, `ffi`, `celeris`, `arithmancy`.
- Never use `utils`, `helpers`, `common`, `misc`. If you cannot name it with a concrete noun, **the module does not have a clear responsibility**.
- Acronyms are written in lowercase `snake_case` as a module name: `std.ffi`, `std.uuid`, `std.xxhash`.

### 2.2 Types

| Construct | Style | Example |
|---|---|---|
| `rune` | `PascalCase`, **singular**, concrete noun | `Player`, `Address`, `CsvTable`, `Stopwatch` |
| `omen` | `PascalCase`, **singular**, category | `Phase`, `Direction`, `JsonKind`, `Color` |
| `echo` | `PascalCase`, **singular** | `Number`, `Value` |
| `seal` | `PascalCase`, **singular** | `UserId`, `Meters`, `Sha256` |
| `alias` | `PascalCase` | `Buffer`, `Handler`, `Callback` |
| `concept` | `PascalCase`, **adjective or role** | `Formatter`, `Measurable`, `Iterabilis`, `Nexus` |
| `shard` parameter | Single letter **or** descriptive `PascalCase` | `T`, `U`, `K`, `V`, `E`, `Item`, `Key` |

**Additional rules:**
- A `rune` that wraps system resources carries the name of the **resource**, not of the operation: `Mutex`, `WaitGroup`, `ChanInt` —not `LockHelper`, `Syncer`.
- A `seal` describes **what it measures**, not its underlying type: `UserId as int` ✅, `IntWrapper` ❌.
- The `concept`s that mirror Latin capabilities already present in the compiler (`Num`, `Ordo`, `Par`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum`) must be respected with their canonical name where applicable. A user does not redefine `Num`.
- A `concept` **always** describes a capability in the singular. Never pluralize a concept (`Formatters` ❌).

### 2.3 Functions (`weave`)

Every `weave` uses **`snake_case`** with the verb in base form (no `to`, no `-ing`).

| Category | Prefix/form | Examples |
|---|---|---|
| Pure action | transitive verb | `parse`, `format`, `split`, `join`, `merge`, `filter`, `map_*` |
| Boolean predicate | `is_`, `has_`, `can_`, `should_` | `is_empty`, `has_key`, `can_parse`, `should_retry` |
| Safe conversion | `to_*` | `to_string`, `to_int`, `to_upper` |
| Conversion that may fail | `parse_*` (returns `maybe T`) | `parse_int`, `parse_float` |
| Constructor | `new`, `from_*`, `with_*` | `new`, `from_csv`, `with_capacity` |
| Mutator | transitive verb | `push`, `pop`, `set_volume`, `clear`, `remove` |
| Non-trivial getter | `get_*` | `get_or`, `get_flag_value`, `getenv_or` |
| Trivial getter | noun (no prefix) | `len`, `size`, `first`, `keys`, `values` |
| Formatter | `format_*`, `describe_*` | `format_duration`, `describe_result_int` |
| Line I/O | `read_*`, `write_*` | `read_file`, `write_lines`, `read_int` |
| Validation | `assert_*` (aborts), `check_*` (returns `bool`), `expect_*` (test) | `assert_eq_int`, `check_range`, `expect_eq` |
| Iteration/generation | `iter_*`, `each_*`, `range_*`, `gen_*` | `range_to`, `for_each_int`, `gen_digits` |
| Extraction with fallback | trailing `_or` | `get_or`, `unwrap_or`, `at_or`, `arg_at_or` |

**Prohibitions:**
- ❌ `-ing` verbs: `parsing`, `getting` → use `parse`, `get_*`.
- ❌ Type-speaking redundancy: `parse_string_to_int` ✅ `parse_int` is better.
- ❌ Hungarian prefixes: `str_name`, `int_count` ❌.
- ❌ 1–2 letter names except `i`, `j`, `k` for indices in **short** `from ... to ...` loops.

### 2.4 Instance methods (`enchanting T:`)

| Form | Rule | Examples |
|---|---|---|
| Mutator | transitive verb, `self->` modified | `heal`, `damage`, `push`, `set_volume` |
| Pure query | noun or `is_*`/`has_*` | `len`, `first`, `is_empty`, `has_key` |
| Conversion | `to_*` | `to_string`, `to_list`, `to_uppercase` |
| Derived production | verb `clone`, `copy`, `reverse`, `transpose` | `clone`, `reverse`, `transpose` |
| Content predicate | `contains`, `starts_with`, `ends_with`, `matches` | idem |

**Rules:**
- A method **does not carry the type name inside it**: `Player.heal` ✅ `Player.heal_player` ❌.
- Methods that return another instance **do not consume `self`** (PenguScript has no move semantics in `enchanting`). The name never uses `consume_`, `take_` or `into_*`.
- `self` is always `ref to T`; therefore mutators use `set self->field is ...`.

### 2.5 `ritual` methods (static)

| Role | Name | Example |
|---|---|---|
| Main constructor | `new` | `calling Player.new with "Ada"` |
| Alternative constructor | `from_*`, `with_*` | `from_json`, `with_capacity`, `from_file` |
| Associated constant | `zero`, `one`, `identity`, `empty` | `Vec2.zero`, `Mat4.identity` |
| Constructor with defaults | `default`, `default_*` | `Logger.default`, `Color.default_red` |
| Conditional factory | `try_*` (if it may fail) | `try_parse`, `try_open` |

- ❌ `create`, `make`, `build`, `init` as the main name → **use `new`**.
- ✅ `init` is only accepted when it **really initializes something external** and does not return the type (e.g. `raylib.InitWindow` as a C binding; in pure `std.*` the idiomatic choice is `new`).

### 2.6 Variables, locals and parameters

| Element | Style | Example |
|---|---|---|
| Local `var` / `let` | descriptive `snake_case` | `total_count`, `parsed_items` |
| Parameter | `snake_case`, short if obvious | `x`, `y`, `item`, `key`, `fallback` |
| Boolean local | prefix `is_`, `has_`, `can_` | `is_ready`, `has_key`, `can_retry` |
| Loop index | `i`, `j`, `k` only in short loops; otherwise `index`, `row`, `col` | |
| Accumulator | `acc`, `sum`, `total`, `result` | |
| Discard | `_` | `for _, v in col:` |
| Internal temporary | `tmp`, `raw`, `staged` | Never exposed in an API |

### 2.7 Top-level constants

Two cases, do not confuse them:

| Case | Style | Example |
|---|---|---|
| Constant **exported** from a module (public API) | `SCREAMING_SNAKE_CASE` | `const MAX_USERS as int is 1024` |
| Constant **internal** to a module (private) | `_SCREAMING_SNAKE_CASE` or `snake_case` with `_` | `const _DEFAULT_CAP as int is 16` |
| Constant used **only** inside a function | declare it as a module top-level local `const` or as a `static var` with a guard | |

> [!NOTE]
> PenguScript **forbids** top-level `var`/`let` (E0002). For module state use `static var` inside an accessor `weave` (see §8.3). For fixed values use `const`.

### 2.8 Fields of `rune` / `echo` / `omen`

| Element | Style | Example |
|---|---|---|
| Public field | `snake_case` | `name`, `hp`, `session_id` |
| Private field | `_snake_case` | `_secret_id`, `_internal_ptr` |
| `omen` variant | `PascalCase` | `Disconnected`, `Connecting`, `Connected` |
| Variant with payload | `PascalCase` (name of the **shape**, not of the data) | `Connected`, not `ConnectedSession` |

### 2.9 Generics

| Role | Canonical name |
|---|---|
| Generic element | `T` |
| Second/third | `U`, `V` |
| Map key | `K` |
| Map value | `V` |
| Error in `result` | `E` |
| Iterable element | `Item` |
| Transformation result | `Out` |
| Reducer state | `Acc` |

When a generic has a clear semantic role and does not collide, a descriptive `PascalCase` is allowed: `weave map shard In and Out with xs as list of In, f as weave with x as In into Out into list of Out`. **Do not** use one-letter names for unconventional roles.

### 2.10 Reserved prefixes

| Prefix | Owner | Use |
|---|---|---|
| `pengu_`, `_pengu_` | Compiler / runtime | **Never** declare them by hand. |
| `_` | Module / rune | Strict privacy (E0043 when crossing a boundary). |
| `ASSET_<MODULE>_` | `arca` system | Embedded asset identifiers. |

---

## 3. Module and file organization

### 3.1 Canonical order inside a `.pengu`

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

**Order rules:**
1. The module docstring **always** goes at the top.
2. Directives (`insignia`, `include`, `link`) before imports.
3. Imports grouped: std first, project afterwards, all sorted alphabetically.
4. Constants → Concepts → Types → Binds → Enchantings → Public functions → Private helpers (`_`) → Tests.
5. Private helpers **go at the end** of the file, not interleaved.

### 3.2 Module size

- **One module = one responsibility.** If in doubt, split.
- Under 800 lines is comfortable. Over 1500 lines is a sign that two modules are hidden in one.
- A module may expose 1 main type + its enchantments, or N functions related by a topic.

### 3.3 Imports

- Always explicit, always sorted.
- Alias only when the real name collides or is very long: `import std.tally as tl`. **Do not** alias out of laziness.
- `import std.math as _` is forbidden (E0036).

---

## 4. Expressions over statements

This is the axis of Pengunic style. **The language gives you value blocks; use them.**

### 4.1 General rule

> If an operation computes a value, **express it as an expression**, not as a sequence of statements that mutate a temporary.

### 4.2 Comprehensions over loops with `push`

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

With a filter:
```pengu
let evens is for x in nums when x % 2 == 0 then x
```

### 4.3 `if`-value over `var` + `if`/`else`

**Anti-Pengunic:**
```pengu
var label as string is ""
if score >= 100:
    set label is "winner"
else:
    set label is "keep going"
```

**Pengunic (one line):**
```pengu
let label is if score >= 100 then "winner" else "keep going"
```

**Pengunic (blocks if there is logic):**
```pengu
let label is if score >= 100:
    "winner"
else:
    "keep going"
```

### 4.4 `do:` to isolate a computation

When you need several steps to produce a value, **do not pollute the scope**:

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

### 4.5 `judge` over `if`/`else` chains

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

### 4.6 `with:` builder over field-by-field assignments

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

Nested:
```pengu
var person as Person with:
    set .name is "Ada"
    set .age is 30
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
        set .zip is "12345"
```

### 4.7 `with target:` to mutate existing collections or structs

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

### 4.8 `if v as T is m:` to unpack `maybe`

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

Also in value position:
```pengu
let label is if v as User is u: u.name else: "anonymous"
```

### 4.9 `some`, `maybe none` with context

Always **annotate the type** when the value is `maybe none` or `null` (E0014):

```pengu
var m as maybe int is some 42       # OK: tipo inferido del valor
var n as maybe int is maybe none    # OK: anotación requerida
var p as ref to int is null         # OK: anotación requerida
```

### 4.10 Recursion over accumulators

Recursive helpers are still expressions in their final branch:

```pengu
weave _factorial with n as int into int:
    if n <= 1:
        return 1
    return n * (calling _factorial with n - 1)
```

Do not do `var acc` + `while` if tail recursion (or a direct expression) reads better. PenguScript does not guarantee TCO, but for small depths it is idiomatic.

### 4.11 Implicit `return` at the end

If the last statement of the `weave` is an expression, **do not write `return`**:

```pengu
weave double with x as int into int:
    x * 2                     # return implícito
```

This applies to value blocks too:
```pengu
let x is do:
    var a is 10
    a * 2                     # valor del bloque
```

---

## 5. Optionals, results and errors

### 5.1 Choosing the right type

| Situation | Type | Example |
|---|---|---|
| May be missing, with no reason for failure | `maybe T` | `find_user → maybe User` |
| May fail with detail | `result of T to E` | `parse_config → result of Config to string` |
| Unrecoverable failure (bug, broken invariant) | `panic` | `weave divide with a, b: if b == 0: panic "division by zero"` |
| Pointer that may point to nothing | `ref to T` + `null` | `ref to Buffer is null` |

**Rule:** Never use a sentinel value (`-1`, `""`, `0`) for "not found". Use `maybe T`.

### 5.2 `or else` for fallback

```pengu
let name is user_name or else "Guest"
let port is env_port or else 8080
```

In arguments and struct literals it goes **without parentheses** (because of `list_value_expr`):

```pengu
calling connect with host, (port or else 8080)
var cfg as Config is with retries is (retries or else 3)
```

In arithmetic it does require parentheses (because of precedence):

```pengu
let total is base + (bonus or else 0)     # ✅
# let total is base + bonus or else 0     # ❌ parsea como ((base+bonus) or else 0)
```

### 5.3 `or return` for early exit

```pengu
weave greet with m as maybe User into string:
    let u is m or return "no user"
    return "Hi {u.name}"
```

### 5.4 `try` for propagation

When the function **also** returns a compatible `maybe` or `result`:

```pengu
weave load_config into result of Config to string:
    let raw is try calling read_file with "config.txt"
    let cfg is try calling parse_config with raw
    return cfg
```

### 5.5 `or:` for rich handling

When you need to use `error` with logic:

```pengu
let cfg is calling parse_config with raw or:
    calling spark.eprintln with "Parse failed: {error}"
    return default_config
```

**Only one `or:` per operation chain** — if you need two, split into functions.

### 5.6 `panic` is **not** control flow

`panic` aborts the process. It is used only for:
- Internal invariants violated (never reachable from a public API without a bug).
- Documented preconditions that the caller **must** satisfy.

Never on an expected path:

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

### 5.7 Names for operations that may fail

| Pattern | Convention |
|---|---|
| Returns `maybe T` | base verb: `find`, `first_or_none`, `at_safe` |
| Returns `result of T to E` | base verb: `parse`, `try_open` |
| Returns `T` or **panics** | verb + `_or_panic` / `_unwrap` | `read_or_panic`, `unwrap` |
| Returns `T` with fallback | trailing `_or` | `get_or`, `at_or`, `arg_at_or` |

Never mix them: a `weave` called `get_int` **must not** panic; one called `get_int_or_panic` does.

### 5.8 Anti-pattern: the bool + out-param

❌ **Never:**
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

## 6. Enchantments, rituals and concepts

### 6.1 Method or module function?

Decision rule:

```
¿El primer argumento "es" el sujeto natural de la operación?
    SÍ  → método (enchanting T)
    NO  → función de módulo
```

| Case | Choice | Example |
|---|---|---|
| `s.trim()` transforms **s** | method | `enchanting string: weave trim into string` |
| `m.keys()` accesses **m** | method | `enchanting map of ...: weave keys into list of K` |
| `tally.sum(xs)` reduces **xs** | both (method preferred) | `calling xs.sum` or `calling tally.sum with xs` |
| `scrolls.substring(s, i, j)` — s is not "the subject" | module function | `calling scrolls.substring with s, 0, 4` |
| `precis.get(url, headers)` — neither is "the subject" | module function | `calling precis.get with url` |
| `chronicle.now()` — there is no subject | module function | `calling chronicle.now` |
| `Player.new(...)` — constructor | `ritual` | `calling Player.new with "Ada"` |
| `Vec2.zero` — type constant | `ritual` with no args | `var v is calling Vec2.zero` |

**Both exposures are valid and common** (`std.tally` offers `calling xs.sum` **and** `calling tally.sum with xs`). When both exist, the module delegates to the method:

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

### 6.2 `ritual` naming

- `new` is the canonical constructor. With no arguments or with defaults.
- `from_*` when the source is another type/serialization: `from_csv`, `from_json`, `from_file`.
- `with_*` when it configures **capacity/optional parameters**: `with_capacity`, `with_retries`.
- `zero`, `one`, `identity`, `empty`, `default` for canonical constants.

### 6.3 When to use `concept` + `bind`

Use `concept` when:

1. **A generic function needs to guarantee operations** on `T`.
2. **Several distinct types share a contract** and you want a `weave shard T where T: C` to accept them.
3. **You want to document the interface required** by a module API.

❌ **Do not use `concept` when:**
- Only one type will **ever** implement it. It is noise.
- You need runtime polymorphism. **PenguScript does not have it.** Use `judge` over an `omen` with payloads.

Correct example:

```pengu
concept Formatter:
    weave format_entry with title as string into string

weave print_all shard T where T: Formatter with items as list of T into void:
    for item in items:
        calling spark.println with calling item.format_entry with "LOG"
```

### 6.4 `derive` when appropriate

If your `rune` is going to be used as a **map key**, in **comparisons**, or when you need an explicit deep copy:

```pengu
rune Point derive Par, Ordo, Vinculum, Imago, Nexus:
    x as int
    y as int
```

| Concept | When to derive it |
|---|---|
| `Par` | Whenever `==` makes semantic sense |
| `Ordo` | When it has a natural total order (numbers, strings, dates) |
| `Vinculum` | When it is going to be used as a **`map` key** |
| `Imago` | When you want to deep-copy the rune explicitly before storing it |
| `Nexus` | Together with `Imago` (the compiler implies them mutually) |

### 6.5 When **not** to derive `Par`/`Ordo`

- If your `rune` contains **floating point** values and the total order is not trivial (NaN).
- If your `rune` contains a **C buffer** and structural equality would be misleading.
- If equality must compare by **logical content**, not by fields (implement an explicit `bind`).

### 6.6 Generic enchanting of containers

When you want methods for **all `map of K to V`**:

```pengu
enchanting map of shard K to shard V:
    weave is_empty into bool:
        return (calling self.len) == 0

    weave get_or with k as K, fallback as V into V:
        if calling self.contains with k:
            return self at k
        return fallback
```

- The **concrete** block (`enchanting map of string to int:`) **overrides** the generic one for that type. Use it for performance specializations.
- Generic methods are monomorphized only for the instances actually used.

---

## 7. Generics and bounds

### 7.1 Declaration

```pengu
weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if calling xs.len == 0:
        return fallback
    return xs at 0
```

- `shard T` for one type, `shard T and U` for several.
- `where T: Concept` for bounds. Multiple: `where T: Num and T: Ordo` or `where T: Num, T: Ordo`.
- The bound goes **immediately after** `shard`.

### 7.2 When to add a bound vs leave it free

| What you need in the body… | Required bound |
|---|---|
| `a + b`, `a - b`, `a * b`, `a / b` | `T: Num` |
| `a % b`, `a & b`, `a << b`, `~a` | `T: Integrum` |
| `a == b`, `a != b` | `T: Par` |
| `a < b`, `a <= b`, `a > b`, `a >= b` | `T: Ordo` |
| `donum T` | `T: Num`, `Integrum`, `Par`, `Ordo`, `Forma` or `Donum` |
| `map of T to U` (T as key) | `T: Vinculum` |
| Deep-copying a `T` with an explicit clone | `T: Imago` (which implies `Nexus`) |
| Iterating `for x in xs` with `xs as list of T` | None (the list already yields the element) |
| Printing with `"{x}"` | `T: Forma` |

### 7.3 Minimal restriction rule

Add **only the bounds you actually use**. A `shard T where T: Num` that never adds is noise and limits the caller.

**Bad:**
```pengu
weave length_of shard T where T: Num with xs as list of T into int:
    return calling xs.len         # 'Num' no se usa
```

**Good:**
```pengu
weave length_of shard T with xs as list of T into int:
    return calling xs.len
```

### 7.4 Transitive bounds

If your `weave` calls another generic `weave`, **propagate the bounds**:

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    ...

weave sum_then_double shard T where T: Num with xs as list of T into T:
    return (calling sum with xs) * 2     # 'Num' se usa aquí también
```

### 7.5 Associated types (future)

When the language supports `concept Iterator shard Self: alias Item`, we will use them for generic iterators. **Today** the idiomatic form is:

```pengu
concept Container shard T:
    weave push with item as T into void
    weave len into int
```

---

## 8. Manual memory management

### 8.1 What `banish` releases

PenguScript has no garbage collector and no automatic release: you allocate, you release.
`banish x` frees what `x` owns according to its static type, and is a safe no-op on
literals and non-owning views.

| Type | `banish x` frees | Notes |
|---|---|---|
| `string` (interpolation, `chr`, `to string`) | its heap buffer | `is_owned == 1` |
| `string` (literal `"x"`, `from_cstr`) | nothing | `is_owned == 0`, safe no-op |
| `list of T` | the list's own element buffer | never the elements |
| `map of K to V` | the entries table and per-entry cells | never the keys'/values' buffers |
| `slice of T` | nothing (always a view) | rejected with `E0008` |
| `ref to T` | the pointed-to allocation (`free`) | caller-managed |
| `rune` with heap fields | `_pengu_cleanup_T` | only with `derive Nexus` |
| `list of string` elements | nothing | use `pengu_banish_string_list` for those |

### 8.2 Golden rule

> **`banish x` frees now. `defer banish x` frees at scope exit (LIFO). `errdefer banish x` frees only on an error return. Nothing is released behind your back.**

### 8.3 Module state (canonical pattern)

**Never** declare a top-level `var` (E0002). Use `static var` in an accessor:

```pengu
weave next_id into int:
    static var counter as int is 0
    set counter is counter + 1
    counter
```

For complex state, expose a `rune` + functions that take `ref to Context`:

```pengu
rune Registry:
    items as list of string

weave registry_add with r as ref to Registry, item as string into void:
    calling r->items.push with item
```

### 8.4 Non-owning views (never banish them)

A value that only **views** another's memory must not be banished: a `slice of T`, a
`ref to T`, `bytes of s`, or any string with `is_owned == 0`.

```pengu
let view is nums at 1 to 3        # a slice is only a window over 'nums'
let raw is bytes of s             # a non-owning byte view over 's'
# Neither owns storage: release 'nums' / 's' themselves, never the views.
```

### 8.5 `defer banish` for resources crossing scopes

**There is no automatic release at scope exit.** Use `defer banish` to free when the
scope ends, or `banish` to free at a specific moment. Resources that come from C follow
their library's cleanup routine, not `banish`:

```pengu
weave process into result of int to string:
    var buf as ref to byte is calling c_alloc_buffer with 1024
    defer banish buf                       # frees when 'process' returns
    ...
```

For a `rune` with heap fields, opt in with `derive Nexus` and banish it explicitly:

```pengu
var doc as Doc with:
    set .title is "spec"
    set .tags is ["a", "b"]
defer banish doc                           # invokes _pengu_cleanup_Doc
```

### 8.6 Naming for lifetime

| Prefix | Meaning |
|---|---|
| no prefix | You allocated it: release it with `banish` / `defer banish` |
| `_view` suffix | A view: never banish it |
| `_owned` suffix | Explicitly owning a heap buffer: release it explicitly |

### 8.7 Never `banish` a `slice`

A `slice of T` is **always** a window. It never frees. The module docstring must say so explicitly when it returns slices. Returning a `slice of` a stack array is itself rejected (`E0051`) because the slice would dangle once the weave returns.

---

## 9. C interoperability

### 9.1 `.d.pengu` for bindings

**Never** declare `declare foo...` in a pure-logic `.pengu`. Bindings go in their `.d.pengu`:

```pengu
# std/sqlite3.d.pengu
include "sqlite3.h"
link "sqlite3"

rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to ref to opaque into int
declare sqlite3_close with db as ref to opaque into int
```

### 9.2 `declare` with exact C types

- Use `ref to char` for `char*`.
- Use `ref to frozen char` for `const char*`.
- Use `ref to void` / `ref to frozen void` for `void*` and `const void*` (wildcard).
- Use `usize` for `size_t`.
- Use `...` for C varargs (`printf`), **not** `many T`.

### 9.3 `frozen` = C `const`

`frozen` describes a **const pointee**, not a const pointer:

| Pengu | C |
|---|---|
| `frozen int` | `const int` |
| `ref to frozen int` | `const int*` |
| `ref to void` | `void*` |
| `ref to frozen void` | `const void*` |
| `frozen ref to int` | (normalizes to `ref to frozen int`) |

Use `frozen` whenever the C header has `const`.

### 9.4 C conversions

| You need | Function |
|---|---|
| `PenguString` → `char*` | `ffi.cstr_from_string` (non-owning) |
| `char*` → `PenguString` | `ffi.string_from_cstr` (heap-allocated; release with `banish`) |
| C buffer as bytes | `ffi.slice_from_ptr` (non-owning, do not banish) |
| `T*` → `void*` | `transmute p to ref to void` |
| Reinterpreting `T*` as `U*` | `transmute p to ref to U` (W0001 warning) |

**Never** use `+` to concatenate a `char*` with a string. Interpolate:

```pengu
calling printf with (transmute "Hello, %s\n" to ref to frozen char), name_cstr
```

### 9.5 Free C memory with **its** cleanup, not with `banish`

If the header says "call `FreeX`", Pengunic code calls it:

```pengu
var tex as raylib.Texture2D is calling raylib.LoadTexture with path
defer calling raylib.UnloadTexture with tex
```

`banish` is **only** for PenguScript runtime memory (`pengu_sigil_alloc`, dynamic `PenguString`, `PenguList`, `PenguMap`).

---

## 10. API design

### 10.1 The 12 rules of a good `std.*` API

1. **Every public function has a single clear purpose**, reflected in its name.
2. **Parameters have defaults** whenever possible (`times as int is 1`).
3. **Expectable errors return `maybe` or `result`**, they do not panic.
4. **Panics are caller bugs** (documented preconditions).
5. **Strings are composed with `"{expr}"`**, never with `+`.
6. **`rune`s and `omen`s derive `Par`/`Ordo`/`Vinculum`/`Imago`/`Nexus`** when applicable.
7. **Pure functions have no side effects** documented as such.
8. **Mutators are marked as such** (transitive verb, `self->`).
9. **Private helpers start with `_`**.
10. **The module does not expose mutable global state** except encapsulated `static var`.
11. **Docstring examples compile as-is.**
12. **Every public function has at least one `test`.**

### 10.2 Modules mirroring Python/Rust/Go

Every module should **compete with** its equivalent in other languages:

| Module | Competes with |
|---|---|
| `std.spark` | Go's `fmt`, `io`, `os`; Python's `print()` |
| `std.scrolls` | Go's `strings`; Python's `str` methods; Rust's `str` |
| `std.tally` | Python's `itertools`, `statistics`, `functools` |
| `std.atlas` | Python's `dict`; Go's `map` |
| `std.oracle` | Rust's `Optional`, `Result` |
| `std.loom` | Python's `itertools`; Rust's `Iterator` |
| `std.coven` | Python's `set`; Rust's `HashSet` |
| `std.archivum` | Python's `os.path`, `shutil`, `pathlib`; Go's `os` |
| `std.regulus` | Python's `re`; Rust's `regex` |
| `std.precis` | Go's `net/http`; Python's `requests` |
| `std.filum` | Python's `threading`, Go's `sync`; Rust's `std::thread` |

If, on reading your API, a Python/Rust/Go user says *"I would do this in two lines with `X`"*, **your API needs that `X`**.

### 10.3 Names and compatibility

- **Never change the signature of a public function without a major version bump.**
- Compatibility aliases (`deprecated_new`) are removed after two versions.
- New names use `snake_case`, in English, with the prefixes from §2.3.

### 10.4 Defaults and overloads

PenguScript has no overloads. For "two versions":

```pengu
# Variante simple
weave get_or with m as map of string to int, k as string, fallback as int into int:
    ...

# Variante con contexto extra
weave get_or_with_logger with m as map of string to int, k as string, fallback as int, logger as ref to Logger into int:
    ...
```

Or use **parameters with defaults** (which must be compile-time constants):

```pengu
weave retry with f as weave into bool, times as int is 3, delay_ms as int is 100 into bool:
    ...
```

### 10.5 Composition over duplication

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

A single `weave` serves `int`, `float`, `i64`, `f32`... and any user type with a `derive` of a `Num` concept.

---

## 11. Documentation (`##`)

### 11.1 Module docstring

Mandatory. It goes **before any directive**:

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

### 11.2 Function/type docstring

Fixed structure:

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

### 11.3 Rules

- **A one-line summary**, followed by a blank line and the details.
- Sections in `## ## Name` (H2 inside the docstring).
- Examples in ` ```pengu ` blocks.
- Invariants and release semantics are documented **explicitly**:
  - "The returned `list` is new; release it with `banish`."
  - "The returned `slice` points into `self`; do not banish it."
  - "Panics if `n < 0`."
- `##` **immediately precede** the symbol, with no blank line in between.
- Never document the obvious (`## Returns an int`). Document **what it means**.

### 11.4 Type docstring

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

## 12. Tests (`test`)

### 12.1 Names

`test <description>` where the description is a **declarative sentence** in English or Spanish, in `snake_case` or a string:

```pengu
test "split returns empty list for empty input":
    ...

test "parse_int rejects trailing garbage":
    ...
```

Never `test_1`, `test_foo`, `test_works`.

### 12.2 Minimum coverage per public function

- 1 **happy path** test.
- 1 test per **edge case** (empty, zero, maximum, minimum).
- 1 test per documented **error case**.

### 12.3 Location

`test`s live **in the same `.pengu`** as the function under test, at the end of the file, grouped under a `# --- Tests ---` comment.

### 12.4 Style

```pengu
test "split returns the original string when separator is empty":
    let parts is calling _split with "abc", ""
    calling ward.assert_eq_int with (calling parts.len), 1
    calling ward.assert_eq_string with (parts at 0), "abc"

test "split handles consecutive separators":
    let parts is calling _split with "a,,b", ","
    calling ward.assert_eq_int with (calling parts.len), 3
```

- Use `std.ward` (`assert_eq_int`, `assert_eq_string`, `assert_true`, etc.).
- Do not use `spark.println` inside tests except for temporary debugging.
- Every `test` must be able to run **in isolation** (without shared global state).

---

## 13. C → Pengunic translation table

| C pattern | Anti-Pengunic in Pengu | Correct Pengunic |
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
| `malloc` + `free` | `var p as ref to T is ...; banish p` | `defer banish p` if it crosses a scope, otherwise `banish p` at the right point |
| `T** vtable` | (manual vtable) | `concept` + `shard T where T: C` |
| `void* user_data` | `ref to void` | `ref to frozen void` with `frozen` when applicable |
| `#define MAX 100` | `const MAX as int is 100` | same |
| `typedef int UserId;` | `alias UserId as int` | `seal UserId as int` if nominal |
| `enum { A, B };` | `omen X: A B` | same with explicit values |
| `strlen(s)` | `calling scrolls.len with s` | `s.length` (postfix) |
| `strcmp(a,b) < 0` | `calling scrolls.compare with a, b < 0` | same (`<` does not exist on strings!) |
| `x.a(); x.b(); x.c();` | `calling x.a` `calling x.b` `calling x.c` | `calling x.a.b.c` |
| `x.a().b()` on a long line | `let y is calling x.a.b` on one line | multi-line chain `.a` / `.b` |
| `struct { int q; bool ok; }` returned | `var out as ref to ...` out-param + `bool` | `into (int, bool)` + destructure |
| `r->x = a; r->y = b;` with local `a`/`b` | `set r->x is a` `set r->y is b` | `with r: set .x is a; set .y is b` |
| `#define X(a) ...` (inline macro) | (a normal function) | `@noreturn` / `@export` / `@packed` / `@align` as applicable |
| `__attribute__((noreturn))` | (not expressible) | `@noreturn weave … into void` |
| `__attribute__((packed))` | (not expressible) | `@packed rune …` |
| `__attribute__((aligned(N)))` | (not expressible) | `@align(N)` |
| `struct { struct T next; }` (recursive) | (does not compile, `E0050`) | `rune T cyclus:` + `maybe ref to T` |
| `static inline` with hand-written C for a hot path | unjustified `antiquus` | `weave inline` first; `antiquus` only with a documented benchmark |

---

## 14. Anti-patterns

### 14.1 Concatenating strings with `+`

```pengu
# ❌ E0005
let msg is "Hello, " + name

# ✅
let msg is "Hello, {name}"
```

`+` **never** concatenates strings. The only composition is interpolation.

### 14.2 Accumulating strings in a loop with `+=`

```pengu
# ❌ O(n²) además de anti-Pengunic
var acc as string is ""
for x in xs:
    set acc is "{acc}{x}"

# ✅ O(n)
let parts is for x in xs then "{x}"
let acc is calling scrolls.join with parts, ""
```

### 14.3 Using `let` for what should be a top-level `const`

```pengu
# ❌ E0002
let MAX as int is 100

# ✅
const MAX as int is 100
```

### 14.4 `if x is present` followed by `x.value`

```pengu
# ❌ Anti-Pengunic
if m.is_present:
    let v is m.value
    calling process with v

# ✅
if v as Config is m:
    calling process with v
```

### 14.5 `var tmp` followed by a single `if`

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

### 14.6 Calling `calling x.foo` without `calling` when it is a call

```pengu
# ❌ ambiguo
x.foo

# ✅ explícito
calling x.foo
```

PenguScript **always** requires `calling` to invoke. There is no "method without parentheses" sugar.

### 14.7 Writing `self.` in a method

```pengu
# ❌ E0003
weave heal with amount as int into void:
    set self.hp is self.hp + amount

# ✅
weave heal with amount as int into void:
    set self->hp is self->hp + amount
```

### 14.8 Returning `bool` as "success/failure" without `maybe`/`result`

```pengu
# ❌ (¿dónde quedó el valor?)
weave find_user with id as int, out as ref to User into bool:
    ...

# ✅
weave find_user with id as int into maybe User:
    ...
```

### 14.9 Redefining compiler concepts

```pengu
# ❌ No lo hagas nunca
concept Num:
    weave add with other as int into int
```

`Num`, `Integrum`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum` are **compiler globals** and are not redefined.

### 14.10 Duplicating code per type

```pengu
# ❌
weave sum_ints with xs as list of int into int: ...
weave sum_floats with xs as list of float into float: ...

# ✅
weave sum shard T where T: Num with xs as list of T into T: ...
```

### 14.11 Using `banish` on views or literals

```pengu
# ❌ E0008
banish "literal"
banish (calling ffi.slice_from_ptr with p, n)

# ✅ (nothing: slices are non-owning)
```

### 14.12 Releasing a parameter you do not own

```pengu
# ❌ the callee banishes a string the caller still owns
weave log with s as string into void:
    banish s

# ✅ a parameter is non-owning: document it and leave the release to the caller
weave log with s as string into void: ...
```

Parameters are non-owning in PenguScript. The rule is: **do not banish a parameter**;
if you need to own a copy, copy it explicitly (`pengu_string_copy`, or `derive Imago` on
a rune and clone it).

### 14.13 `while` with an accumulator when there is a comprehension

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

### 14.14 Returning `void` when the caller needs the value

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

### 14.15 Chaining mutation and reading

```pengu
# ❌ Anti-Pengunic
calling xs.push with 10.reverse.sort_asc

# ✅ Pengunic
calling xs.push with 10
calling xs.reverse
calling xs.sort_asc
```

### 14.16 Unpacking tuples by hand

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

### 14.17 `antiquus` for logic PenguScript can express

```pengu
# ❌ Anti-Pengunic: unnecessary C
antiquus max_of with a as int, b as int into int:
    r"""return a > b ? a : b;"""

# ✅ Pengunic
weave max_of with a as int, b as int into int:
    if a > b:
        return a
    return b
```

### 14.18 `@noreturn` without a guarantee

```pengu
# ❌ Anti-Pengunic: it can return
@noreturn
weave maybe_fail into void:
    if cond:
        calling spark.exit with 1

# ✅ Pengunic: guaranteed non-return
@noreturn
weave fail_hard with msg as string into void:
    calling spark.eprintln with msg
    calling spark.exit with 1
```

### 14.19 `@export` without a project prefix

```pengu
# ❌ Anti-Pengunic: collides with libc's 'process'
@export("process")
weave do_process into void: ...

# ✅ Pengunic: project prefix
@export("pengu_myapp_process")
weave do_process into void: ...
```

### 14.20 `@packed` outside the binary boundary

```pengu
# ❌ Anti-Pengunic
@packed
rune Player:
    name as string
    hp as int

# ✅ Pengunic: only when the layout matters
@packed
rune NetHeader:
    magic as u16
    version as u8
```

### 14.21 Decorative `cyclus`

```pengu
# ❌ Anti-Pengunic
rune Point cyclus:
    x as int
    y as int

# ✅ Pengunic: only with real recursion
rune TreeNode cyclus:
    value as int
    left as maybe ref to TreeNode
```

### 14.22 Indented C body in `antiquus`

```pengu
# ❌ Anti-Pengunic: the C is indented inside the string
antiquus fast_abs with x as int into int:
    """
        return x < 0 ? -x : x;
    """

# ✅ Pengunic: the C at column 0
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

### 14.23 C body without a documented reason

```pengu
# ❌ Anti-Pengunic: why C?
antiquus fast_abs with x as int into int:
    r"""return x < 0 ? -x : x;"""

# ✅ Pengunic: measurable reason
## Returns |x| without branches; the ternary causes a branch misprediction
## of ~8 ns/call in the inner loop (bench/scanline.md).
antiquus fast_abs with x as int into int:
    r"""return x < 0 ? -x : x;"""
```

### 14.24 Shorthand initializer in a large or heterogeneous struct

```pengu
# ❌ Anti-Pengunic: which fields are shorthand and which are not?
return with host, port, timeout_ms is 30000, retries is 3

# ✅ Pengunic: explicit when the fields are not trivial
return with
    host is host,
    port is 8080,
    timeout_ms is 30000,
    retries is 3
```

---

## 15. Documented exceptions

A style rule that the standard library cannot satisfy is worse than no rule: it
teaches contributors to ignore the guide. Roadmap Phase 7 measured every rule the
1.0 audit had flagged as unenforceable and recorded the outcome here — *enforced*,
*scoped*, or *relaxed with a named exception*. The numbers are re-measurable with
the command in the last column; the full derivation is in
[`AUDIT_1.0_FASE7.md`](AUDIT_1.0_FASE7.md) §7.7.

| Rule (§) | Status | Measurement | How to re-measure |
|---|---|---|---|
| A public `weave` carries a `##` docstring (§11.2) | **Enforced** | `weave` 1314/1315. The single exception is `std/cipher.pengu:375 weave _b32_val`, a **private** helper — so coverage of *public* functions is 100 % | `python -m pytest tests/test_std_docs_completeness.py -q` |
| Every `declare` / `const` / `alias` / `omen` is documented (§11.3) | **Scoped out** | `declare` 630/1862 (33.8 %), `const` 123/593 (20.7 %), `alias` 50/153 (32.7 %), `omen` 4/66 (6.1 %). Most are **generated bindings** whose doc text is the upstream C header comment; demanding 100 % would mean inventing prose for third-party API surface | `python -m pytest tests/test_std_docs_completeness.py -q` |
| Indent with 4 spaces, never tabs (§3.1) | **Enforced** | `.pengufmt.toml` and `std/.pengufmt.toml` pin `tab_size = 4`, `pengu_project._resolve_indent` defaults to 4, and the formatter is idempotent on the whole stdlib | `python pengu_project.py fmt --check std/` |
| A local may not shadow a global `weave` (§2.6) | **Enforced** | `0 W0005` across all 27 hand-written `std/` modules | `python pengu_project.py check --entry std/<module>.pengu` |
| No unsafe conversion (§9.4) | **Enforced** | `0 W0001` across all 27 modules, and **zero** `transmute` calls in `std/` — the only occurrence is an explanatory comment in `std/ffi.pengu:67`. Should one ever be needed, it is confined to `std/ffi` and `std/filum` and must be same-size | `python pengu_project.py check --entry std/<module>.pengu` |
| Names and signatures are consistent across modules (§10.3) | **Relaxed — named exception** | `std.loom` and `std.tally` deliberately share 15 names with *different* contracts (`loom.mean([1,2]) == 1.5` vs `tally.mean([1,2]) == 1`; `loom.mode([])` → `none` vs `tally.mode([])` → `0`). Both are documented contracts, not drift | see [`LANGUAGE.md` §19.1.1](LANGUAGE.md#1911-choosing-between-stdloom-and-stdtally) |
| Public `antiquus` documents a measurable reason (§20.6) | **Under observation** | No corpus yet; first measurement next phase | `python -m pytest tests/test_antiquus_docs.py -q` (pending) |
| `@export` uses the `pengu_<module>_` prefix (§19.2) | **Under observation** | No corpus yet | `python pengu_project.py check --entry std/<module>.pengu` |
| Method chains do not mix mutation and reading (§16.1) | **Under observation** | No corpus yet | `pengu fmt --check std/` (heuristic rule, not automatic) |
| `rune`s with `cyclus` document the indirection (§21.3) | **Under observation** | No corpus yet | `python -m pytest tests/test_std_docs_completeness.py -q` |

Two consequences worth stating plainly, because earlier audits reported the
opposite:

1. **The indentation rule was never the problem.** An earlier audit recorded that
   "`pengu fmt` imposes 2 spaces and `--indent 4` corrupts the file". That is
   false as of `c42776c`: the config pins 4, the default is 4, and
   `fmt --check std/` is clean. The stale "2-space" prose that survived in
   `LANGUAGE.md` §20.7 and `CHEATSHEET.md` was corrected in Phase 7.
2. **"Docstring on 100 % of declarations" is not a rule worth having.** Scoped to
   *public functions* it is met exactly; extended to generated `declare`
   surfaces it would require writing documentation for code this project does not
   author.

A rule is only added to this table with a measurement and a command. If a future
change makes an *Enforced* row fail, that is a regression, not a new exception.

> When the corpus exists, these rows are measured by the same standard as the rest: they either become **Enforced** with a number, or get scoped, or are relaxed with a named exception.

---

## 16. Method chaining

The syntax `calling x.a.b.c` chains several method calls on a single receiver. Each `.name` link is resolved against the type produced by the previous link. It is **composition sugar**, not a parenthesised call: the `with` block belongs to the **last** link.

### 16.1 When to chain

**Chain when the chain reads as a linear transformation**, with no branches and no intermediate side effects:

```pengu
# ✅ Pengunic: each step transforms the previous value
let slug is calling raw.trim.lower.replace with " ", "-"

# ✅ Pengunic: chain of pure transformations over collections
let top5 is calling scores.filter_positive.sort_desc.take with 5
```

**Do not chain when:**

| Situation | What to do |
|---|---|
| An intermediate link needs a name of its own | Break the chain and name it |
| The chain exceeds 4–5 links | Split it into functions |
| A link mutates the receiver (`push`, `set_*`, `clear`) | Separate mutation from reading |
| A link requires arguments and is not the last one | Break the chain |
| A link resolves to a **field**, not a method | It is not a chain, it is field access |

```pengu
# ❌ Anti-Pengunic: mixes reading and mutation
calling xs.push with 10.reverse.sort_asc

# ✅ Pengunic: separate mutation from reading
calling xs.push with 10
calling xs.reverse
calling xs.sort_asc
```

### 16.2 Multi-line chains

For long chains, a continuation line starts with `.` (or `->`) and is folded into the previous line before the lexer. The folding **preserves line numbering**: a diagnostic on a chained expression points at the line where the chain *starts*.

```pengu
# ✅ Pengunic: multi-line, one link per line
let slug is calling raw
    .trim
    .lower
    .replace with " ", "-"

# ❌ Anti-Pengunic: unreadable long line
let slug is calling raw.trim.lower.replace with " ", "-"
```

**Formatting rules:**

- One link per line.
- Indentation: **one level** (4 spaces) relative to the line that opens the chain.
- The first link (`.trim`) goes on the line after the receiver.
- Do not mix `.` and `->` in the same chain.
- Lines inside a triple-quoted string are **never** folded.

### 16.3 The `with` block belongs to the last link

```pengu
# ✅ 'with " ", "-"' applies to '.replace', not to '.lower'
let slug is calling raw.trim.lower.replace with " ", "-"
```

If an intermediate link needs arguments and is not the last one, the chain cannot be written; split it:

```pengu
# ❌ Anti-Pengunic: there is no way to pass 'with 0, 4' to the intermediate 'substring'
# let slug is calling raw.trim.substring with 0, 4.lower

# ✅ Pengunic: two expressions, explicit names
let head is calling raw.trim.substring with 0, 4
let slug is calling head.lower
```

### 16.4 Chains and generics

Each link is resolved by on-demand monomorphization: the compiler instantiates the generic method only for the concrete type of the previous link. **There is no runtime overhead.**

```pengu
# ✅ A single 'calling' chains generic methods over 'map of shard K to shard V'
let short is calling registry
    .keys_sorted
    .first_or with "none"

# ✅ In a chain, the receiver may be a 'ref to T':
calling self
    .remove with old_key
    .put with new_key, val
```

When the receiver is `self` inside an `enchanting`, the chain works the same way and is the idiomatic way to apply several coordinated mutations:

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

### 16.5 Anti-patterns

```pengu
# ❌ Field chain (not a method chain)
calling p.address.city.zip_code

# ❌ Chain with a mutator in the middle
calling xs.push with 10.reverse

# ❌ Chain of more than 5 links
calling raw.trim.lower.replace(" ", "-").split("-").filter_nonempty.first_or("none")

# ❌ Mixing '.' and '->'
calling self.method1->method2

# ✅ Equivalent Pengunic
let slug is calling raw
    .trim
    .lower
    .replace with " ", "-"
let first is calling slug.split with "-" . first_or with "none"
```

---

## 17. Multiple return values (tuples)

When an operation produces several related values, **declare a tuple** instead of forcing the caller to use `maybe` + out-params or a single-use `rune`.

### 17.1 When to use tuples (and when not to)

| Situation | Type | Example |
|---|---|---|
| A value **and** a success flag | `(T, bool)` | `divide → (int, bool)` |
| A value **and** metadata computed together | `(T, U)` | `parse_header → (string, usize)` |
| Several values **with a name of their own** in the domain | dedicated `rune` | `Point → rune` |
| A value or a detailed failure | `result of T to E` | §5 |
| A value or nothing | `maybe T` | §5 |

**Decision rule:**

> If the values have independent names in the domain (a `Point` has `x` and `y` **as concepts**), use a `rune`. If they only make sense together and are ephemeral (they are unpacked immediately), use a tuple.

### 17.2 Naming

| Element | Convention | Example |
|---|---|---|
| `weave` returning a tuple | base verb, no suffix | `divide`, `split_first`, `parse_pair` |
| Names in the destructuring | descriptive `snake_case` | `let (q, ok) is …` |
| Field access on anonymous tuples | `v0`, `v1`, … (rarely) | `pair.v0` |

**Never** mix tuples with the prefixes from §2.3:

- A function returning `(T, bool)` **must not** be called `try_*` or `parse_*`: those prefixes imply `maybe`/`result`.
- A function returning `(T, bool)` **must not** be called `find_*`: that prefix implies `maybe`.

### 17.3 Canonical destructuring

```pengu
# ✅ Pengunic: destructure on receipt, use the names directly
weave compute into int:
    let (q, ok) is calling divide with 10, 2
    if not ok:
        return 0
    return q

# ❌ Anti-Pengunic: unpacking by hand
weave compute into int:
    var pair as (int, bool) is calling divide with 10, 2
    if not pair.v1:
        return 0
    return pair.v0
```

- The number of names must match the number of elements (`E0017`).
- Prefer the **parenthesised** form `let (x, y) is p` in new code; `let x, y is p` is equivalent but less visible.
- Names go in descriptive `snake_case`, **not** in `v0`/`v1`.

### 17.4 Tuples and `try` / `or else` / `or:`

Tuples **do not** compose with `try`, `or else` or `or:` blocks. If the result can fail, use `result of T to E`:

```pengu
# ❌ Anti-Pengunic: mixing a tuple and 'try'
# let (v, ok) is try calling parse_pair with s

# ✅ Pengunic: 'result' when it can fail
weave parse_pair with s as string into result of (int, int) to string:
    ...
```

### 17.5 Anti-patterns

```pengu
# ❌ Tuple for two values with a name of their own
weave make_point with x as int, y as int into (int, int):
    return x, y
# ✅ This is a 'rune Point'.

# ❌ Tuple + 'try'
# let (v, ok) is try calling f with x

# ❌ v0/v1 names in the destructuring
let (v0, v1) is calling divide with 10, 2
```

---

## 18. Shorthand struct initializers

Inside a `with` literal, a field may omit `is <value>` and take the binding of the same name. The rewrite happens **before parsing** and never adds or removes lines, so `#line` and diagnostic positions stay exact.

### 18.1 When to use the shorthand form

```pengu
# ✅ Pengunic: field name and binding match exactly
weave make with name as string, hp as int into Player:
    return with name, hp

# ✅ explicit equivalent (sometimes preferable for clarity)
weave make with name as string, hp as int into Player:
    return with name is name, hp is hp
```

| Situation | Shorthand form? |
|---|---|
| Field `name`, binding `name`, same type | ✅ Yes |
| Field `name`, binding `n` (different name) | ❌ No — `with name is n` |
| Field `name`, binding `name` but a convertible type (`seal`) | ❌ No — convert explicitly |
| Private field `_secret`, binding `_s` | ❌ No — privacy and the binding are different things |
| Field `name`, local binding that shadows a global `weave` | ❌ No — avoid `W0005` |

### 18.2 Mixing with the explicit form

```pengu
var p as Player with:
    name,                       # shorthand form
    hp is 100,                  # explicit form
    _secret_id is 0
```

They can be mixed without a problem. The only restriction is that each member is **either** a bare name **or** `field is <expr>`; names with `as` and bare expressions are not allowed.

### 18.3 The shorthand form does **not** convert types

```pengu
# ❌ Anti-Pengunic: 'name' is 'string' but the field expects a 'seal Name'
weave make with name as string into User:
    return with name                # E0005

# ✅ Pengunic: convert explicitly
weave make with name as string into User:
    return with name is (name to Name)
```

The shorthand form is syntactic sugar for `field is field`; it does not insert conversions.

### 18.4 Anti-pattern: shorthand in large structs

```pengu
# ❌ Anti-Pengunic: which fields are shorthand and which are explicit?
rune Config:
    host as string
    port as int
    timeout_ms as int
    retries as int

weave make_default with host as string into Config:
    let port is 8080
    return with host, port, timeout_ms is 30000, retries is 3

# ✅ Pengunic: explicit if the fields are not trivial
weave make_default with host as string into Config:
    return with
        host is host,
        port is 8080,
        timeout_ms is 30000,
        retries is 3
```

**Rule:** the shorthand form is acceptable only when **every field of the literal is either shorthand or explicit but simple**, and the struct has ≤ 4 fields. In large structs, or structs with fields of different origins, the explicit form wins on readability.

---

## 19. Declaration attributes

PenguScript exposes four declaration-level attributes. Each has its own style rules and a concrete justification.

### 19.1 `@noreturn`

Marks a `weave` that **never returns** to its caller. The weave must be declared `into void` (`E0056`).

```pengu
# ✅ Pengunic: guaranteed abort
@noreturn
weave fail_hard with msg as string into void:
    calling spark.eprintln with msg
    calling spark.exit with 1
```

**Rules:**

- It applies only to `weave`; never to `rune`, `omen` or `declare`.
- The body **must** end on a path that does not return (`exit`, `panic`, `abort`, an `antiquus` with `_Noreturn`).
- **Do not** mark a function `@noreturn` just because it *probably* does not return; the compiler does not verify it beyond the type contract.
- The generated C carries `_Noreturn` in both the prototype and the definition (`__declspec(noreturn)` on MSVC).

### 19.2 `@export("c_name")`

Sets the emitted C symbol. It is the FFI entry point for C consumers.

```pengu
# ✅ Pengunic: stable C name with a project prefix
@export("pengu_myapp_add")
weave add with a as int, b as int into int:
    return a + b
```

**Style rules:**

- **Never** export under the default C name (the one the compiler would emit). If you export, **always** pass an explicit C name.
- The C name must start with `pengu_<module>_` (or the project namespace). Never use a "bare" name (`process`, `add`, `read`): it collides with libc.
- The C name must be **stable**: changing it is an **ABI breaking change**, not an API change.
- An exported `weave` is a **DCE root**: it survives even if nobody calls it from PenguScript. Do not export internal functions "just in case".
- The PenguScript name **does not change**: `calling add with 1, 2` is still the call site.

### 19.3 `@packed`

Removes the padding between the fields of a `rune`. It should only be used when **the binary layout matters**.

```pengu
# ✅ Pengunic: struct that maps an on-disk or on-wire format
@packed
rune NetHeader:
    magic as u16
    version as u8
    flags as u8
    length as u32
```

**Rules:**

- **Only** on `rune`s that cross a binary boundary (file, network, FFI with `memcpy`).
- **Never** on general-purpose `rune`s: it breaks natural alignment and penalises access.
- If a `rune` has `@packed`, **document it** in the type docstring: it is a layout contract.
- `@packed` **does not apply to `echo`**: a C union has rules of its own.

### 19.4 `@align(N)`

Sets the alignment of a `rune` or of a field. `N` must be a power of two between 1 and 128 (`E0056`).

```pengu
# ✅ Pengunic: align a buffer for SIMD
@align(32)
rune AlignedBlock:
    _data as array of f32 with size 8

# ✅ align a specific field within its struct
rune Mixed:
    a as u8
    @align(4) b as u32
    c as u8
```

**Rules:**

- **Use it** when a C API requires a specific alignment (SIMD, DMA, atomic instructions).
- **Do not use it** to "optimise" without measuring: natural alignment is usually the right one.
- Document in the docstring **why** that alignment is needed, not just what it is.

### 19.5 Anti-patterns

```pengu
# ❌ @noreturn without a guarantee of non-return
@noreturn
weave maybe_fail into void:
    if cond:
        calling spark.exit with 1
    # if 'cond' is false, it returns → E0056

# ❌ @export without a project prefix
@export("process")             # collides with libc's 'process'
weave do_process into void: ...

# ❌ @packed on a general-purpose rune
@packed
rune Player:                   # crosses no binary boundary
    name as string
    hp as int

# ❌ @align without documenting the reason
@align(64)
rune Foo:                      # why 64? nobody knows
    x as int
```

---

## 20. Embedded C blocks (`antiquus`)

An `antiquus` declares a function whose body is **literal C**. It is the language's escape hatch, and for that very reason **the most important style rule in this document**: every `antiquus` is explicit technical debt and must be justified.

### 20.1 When **to** use `antiquus`

Only in four cases, in this order of preference:

1. **System primitives** that have no binding in `std.*`: syscalls, CPU instructions, hardware counters.
2. **Performance-critical code already measured**, where the difference is real and verifiable.
3. **FFI glue** for a C API that cannot be expressed as `declare` (for example, callbacks with context that require C macros).
4. **Reimplementing runtime helpers** in the `std` module that uses them, so that DCE can prune them.

### 20.2 When **not** to use `antiquus`

- **Never** for logic PenguScript already expresses (loops, conditionals, error handling, collections). Rewriting that in C loses type checking and ownership tracking without gaining anything.
- **Never** for FFI to an existing library: use `declare` + `include` + `link`.
- **Never** to "bypass" the type system.

> **Mnemonic rule:** if your `antiquus` has an `if` or a `for`, it should probably be a `weave`.

### 20.3 Naming

| Role | Name | Example |
|---|---|---|
| System primitive | verb + system suffix | `read_tsc`, `cpu_relax`, `syscall_write` |
| Low-level helper | `fast_*`, `raw_*` | `fast_abs`, `raw_memcpy` |
| Runtime reimplementation | the same name as the helper | `print_int`, `list_push` |
| FFI glue | the C symbol name with a prefix | `cb_register_signal` |

- **`pengu_` prefix forbidden** for user `antiquus` (the compiler uses it).
- **`_` prefix** if it is private to the module.

### 20.4 `@export` and DCE

An `antiquus` in a `std/` or `lib/` module is **pruned by DCE** if nobody references it. For it to survive as an FFI entry point:

```pengu
# ✅ Pengunic: an 'antiquus' that must survive as a C symbol
@export("pengu_fast_double")
antiquus fast_double with x as int into int:
    r"""
    return x * 2;
    """
```

**Rule:** every `antiquus` in `std/` or `lib/` that is an FFI entry point **must** carry `@export("...")` with the `pengu_<module>_` prefix.

### 20.5 The C body: style rules

```pengu
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

- **Use `r"""..."""`** when the C contains backslashes (`printf`, regex, paths): it avoids double escaping.
- **Use `"""..."""`** when it does not; it is more readable.
- **C indentation:** the body is emitted with `#line 1 "antiquus:<name>"`, so the indentation of the C inside the string is **literal**. Keep the C at column 0 inside the string.

```pengu
# ❌ Anti-Pengunic: the C ends up indented, obscuring diagnostics
antiquus fast_abs with x as int into int:
    """
        return x < 0 ? -x : x;
    """

# ✅ Pengunic: the C at column 0
antiquus fast_abs with x as int into int:
    r"""
return x < 0 ? -x : x;
"""
```

- **One responsibility per `antiquus`:** if the C is longer than ~10 lines, split it.
- **Parameters with valid C names:** `if`, `int`, `while` as parameters are `E0035`; use `condition`, `value`, `running`.
- **`many T` forbidden:** use `slice of T` and read `.data` / `.len`.

### 20.6 Mandatory documentation

Every public `antiquus` **must** document:

```pengu
## Returns the absolute value of `x` without branches, using the CPU instruction.
##
## ## Reason
## Used in the inner loop of `render_scanline`, where the ternary branch
## causes a measured `branch misprediction` of ~8 ns/call
## (see benchmarks/scanline.md). An equivalent `weave` is 3× slower
## on the same profile.
##
## ## Preconditions
## - `x` must be a 32-bit `int`.
##
## ## Memory
## Allocates nothing. There is nothing to release.
antiquus fast_abs with x as int into int:
    r"""
    return x < 0 ? -x : x;
    """
```

**Mandatory sections:**

1. **Summary** of one line.
2. **Reason:** why C and not PenguScript. It must be **measurable** (benchmark, language limitation, C contract).
3. **Preconditions** if any (ownership, alignment, value range).
4. **Memory:** who releases, or "allocates nothing".

### 20.7 Anti-patterns

```pengu
# ❌ Anti-Pengunic: logic PenguScript already expresses
antiquus sum_list with xs as list of int into int:
    r"""
    int acc = 0;
    for (int i = 0; i < xs.len; i++) acc += ((int*)xs.data)[i];
    return acc;
    """
# ✅ It should be: weave sum shard T where T: Num ...

# ❌ Anti-Pengunic: no @export in std/
antiquus fast_double with x as int into int:
    r"""return x * 2;"""
# It will be pruned by DCE if nobody calls it.

# ❌ Anti-Pengunic: invalid C parameter name
antiquus check with int as int into bool:    # E0035
    r"""return int > 0;"""

# ❌ Anti-Pengunic: body with 'many T'
antiquus count with xs as many int into int: # E0005
    r"""return xs.len;"""
```

---

## 21. `cyclus` and recursive types

`cyclus` explicitly declares that a `rune` is self-referential. It does **not** make a by-value cycle legal: the cycle must be broken with indirection (`ref to`, `maybe ref to`, `slice`, `list`, `map`).

### 21.1 When to use `cyclus`

Only when the type **really does contain itself** intentionally:

```pengu
# ✅ Pengunic: recursive tree with explicit indirection
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T     # 'maybe ref' breaks the cycle
    children as list of Node of T      # 'list' breaks the cycle
```

### 21.2 When **not** to use `cyclus`

- **Never** on a `rune` without recursion, not even "just in case". It is noise.
- **Never** on a `rune` that contains itself **by value** (`next as Bad`): that is `E0050` and `cyclus` does not fix it.
- **Never** on `echo` or `omen`.

### 21.3 Documentation

A `rune` with `cyclus` **must** document **where** the indirection is:

```pengu
## Node of a binary tree of integers.
##
## ## Recursion
## The cycle is broken in `left` and `right` by `maybe ref to`; the node
## never contains itself by value. An empty tree is represented with
## `maybe none` in the children.
rune TreeNode cyclus:
    value as int
    left as maybe ref to TreeNode
    right as maybe ref to TreeNode
```

### 21.4 Anti-pattern: decorative `cyclus`

```pengu
# ❌ Anti-Pengunic: 'cyclus' with no real recursion
rune Point cyclus:
    x as int
    y as int

# ❌ Anti-Pengunic: 'cyclus' without documenting where the indirection is
rune Node cyclus:
    value as int
    next as maybe ref to Node
```
