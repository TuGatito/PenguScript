# Pengunic Style Guide

> **Covered version:** PenguScript **3.0.1**
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
| Source file | `snake_case.pengu` | `scrolls.pengu`, `archivum.pengu` |
| Declaration file | `snake_case.d.pengu` | `uuid.d.pengu`, `raylib.d.pengu` (satellite bindings) |
| Module (import) | `snake_case`, noun or adjective | `std.scrolls`, `std.atlas`, `std.rites` |
| Collection module | noun in the **plural** | `std.rites`, `std.scrolls` (not `rite`, `scroll`) |
| Capability module | **abstract singular** noun | `std.cipher`, `std.loom` |

**Rules:**
- Standard modules live under `std.` and their name is a **Latin or English noun**: `spark`, `scrolls`, `oracle`, `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `arithmancy`, `rites`, `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `filum`, `integrum`, `numerus`, `loom`, `invoke`, `ffi`, `ledger`.
- External C bindings (`raylib`, `sqlite3`, `yaml`, …) are **not** `std.*` modules: they were extracted to satellite repositories and are installed with `pengu add <url>` (catalogue: [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)). The runtime links only `libc`/`libm`/`pthreads`, and the 26 modules above are the whole pure standard library.
- Never use `utils`, `helpers`, `common`, `misc`. If you cannot name it with a concrete noun, **the module does not have a clear responsibility**.
- Acronyms are written in lowercase `snake_case` as a module name: `std.ffi`.

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
| Pure form of a `@mutates` method | `get_<name>` | `get_clamp` (pure), `clamp` (mutates); see §6.7 |
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
- ✅ `init` is only accepted when it **really initializes something external** and does not return the type (e.g. `raylib.InitWindow` in the raylib satellite binding; in pure `std.*` the idiomatic choice is `new`).

### 2.6 Variables, locals and parameters

| Element | Style | Example |
|---|---|---|
| Local `var` / `let` | descriptive `snake_case` | `total_count`, `parsed_items` |
| Parameter | `snake_case`, short if obvious | `x`, `y`, `item`, `key`, `fallback` |
| Boolean local | prefix `is_`, `has_`, `can_` | `is_ready`, `has_key`, `can_retry` |
| Loop index | `i`, `j`, `k` only in short loops; otherwise `index`, `row`, `col` | |
| Loop label (`break label` / `continue label`) | descriptive `snake_case`, never one letter | `outer`, `lines_loop`, `next_row` |
| Accumulator | `acc`, `sum`, `total`, `result` | |
| Discard | `_` | `for _, v in col:` |
| Internal temporary | `tmp`, `raw`, `staged` | Never exposed in an API |

Label a loop only when at least two loops are nested and you must leave the
outer one from inside it; a label on a single loop is noise (see §14.27).

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

### 4.5.1 When to use `judge over rune`

`judge` can match two different shapes, and choosing between them is a data-modelling decision, not a syntax one:

- **Algebraic `omen` — the default.** Each variant carries only its own fields, the compiler stores the most compact representation, and the clause binds the variant's payload positionally. Prefer it whenever the variants are genuinely different things.
- **`rune` with a discriminant — when the variants share fields.** Declare the shared fields (`line`, `col`, `type`) once on the rune and match the tag with `judge <rune> over <field>:`. Reach for it as well when you need a **stable layout** for FFI or an external C struct, and whenever the value is handed to C.

Or-patterns (`when A | B ->`) let two variants share one clause; a *narrowed* pattern (`when Binary with left as Literal ->`) is a test, not coverage — the variant still needs a plain clause or an `else`.

Side by side:

Algebraic `omen`:
```pengu
omen Shape:
    Circle with radius as f64
    Rect with width as f64, height as f64

weave area with s as Shape into f64:
    judge s:
        when Circle with radius -> 3.14159 * radius * radius
        when Rect with width, height -> width * height
```

`rune` with a discriminant:
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

**Anti-Pengunic:** a rune with a discriminant where an algebraic `omen` would do:
```pengu
# ❌ Anti-Pengunic: no variant shares a field; the rune only adds a tag to a
# union that is always union-sized
rune Shape:
    kind as ShapeKind
    radius as f64
    width as f64
    height as f64

omen ShapeKind:
    Circle
    Rect

# ✅ Pengunic: the algebraic `omen` carries only each variant's fields
omen Shape:
    Circle with radius as f64
    Rect with width as f64, height as f64
```

**Anti-Pengunic:** an algebraic `omen` when the variants share fields:
```pengu
# ❌ Anti-Pengunic: `line` and `col` repeat in every variant, and the union is
# padded to the largest variant
omen Token:
    Ident with text as string, line as int, col as int
    Number with value as f64, line as int, col as int

# ✅ Pengunic: the shared fields live once, in the rune
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

**Naming rules:**
- Call the discriminant `kind` (Pengunic), or give it a concrete noun such as `op_kind` or `node_type`. Do **not** invent generic names like `type`, `tag` or `which`.
- The `with` bindings are the rune's field names **verbatim**; do not rename them. Write `when Rect with width, height ->`, not `with w, h`.

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

### 4.6.1 `with:` in value position

A `with:` builder is an expression only where the compiler already knows the
target type. Use it when the value is a struct built on the spot: in a
`var`/`let`/`static var` annotation, a `return`, a field, a loop element type, a
value-position branch or a `do:` tail. It is **not** a general expression: a call
argument needs a named value or the one-line `with x is …` literal, and an
arithmetic operand needs a typed variable first (`LANGUAGE.md` §18 has the
verified position table).

**✅ Pengunic: build in the slot that supplies the type**

```pengu
var p as Point with:              # the annotation supplies Point
    set .x is 1
    set .y is 2

weave origin into Point:
    return with:                  # 'into Point' supplies Point
        set .x is 0
        set .y is 0
```

**❌ Anti-Pengunic: build a throw-away struct only to copy it into an existing value**

```pengu
var p as Point is calling default_point     # p already exists

var fresh as Point with:                    # ❌ built only to be copied
    set .x is 3
    set .y is 4
with p:
    set .x is fresh.x
    set .y is fresh.y

# ✅ Pengunic: one 'with target:' mutation, no throw-away value
with p:
    set .x is 3
    set .y is 4
```

**When not to use a builder.** A single trivial value is clearer as the one-line
struct literal; and `with:` (construction of a new value) is not `with target:`
(mutation of an existing one):

```pengu
# ✅ one line, no builder
var q as Point is with x is 5, y is 6

# ✅ 'with:' constructs a new value; 'with target:' mutates an existing one
var fresh as Point with:
    set .x is 1
    set .y is 2
with fresh:
    set .x is 3
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

### 4.16 Parsing with `std.json`

`std.json` is a strict parser and a DOM with explicit ownership. The pattern is
**parse once, query with the typed accessors, free the copies**:

```pengu
import std.json
import std.spark

weave load_config with path as string into maybe JsonValue:
    var text as maybe string is calling archivum.read_file with path
    if t as string is text:
        var parsed as result of JsonValue to json.JsonError is calling json.parse with t
        if p as JsonValue is parsed:
            return some p
        banish parsed
    banish text
    return maybe none
```

- `parse` returns `result of JsonValue to JsonError`. Use `or:` or check
  `is_ok` and `banish` the result (which frees the tree).
- `get`, `at`, `first`, `last`, `pointer` and `find_key` return **owned deep
  copies**; `banish` them. `as_string` returns an owned copy inside a maybe:
  `json.take_string with (sigil of opt)` moves it out and frees the box.
- Prefer `json.get_or_null` when you want a plain value without a `maybe`.
- `validate` checks a document without building a DOM; `validate_schema`
  returns a list of human-readable errors.
- `parse_in_arena` is the one-shot mode: `banish arena` frees the whole tree.

**Anti-pattern:** walking the DOM with `if kind == ...` and hand-written string
building. Use `as_*`, `pointer` and `stringify`.

### 4.17 Reporting diagnostics

Build structured diagnostics, never concatenate error strings yourself:

```pengu
import std.diagnostic as diag

weave report_unused with name as string, span as Span into void:
    calling bag.error with "unused binding '{name}'", span

weave main into int:
    var bag as DiagnosticBag is calling DiagnosticBag.new
    defer banish bag
    calling bag.add_source with "src/main.pengu", source_text
    # ... add diagnostics ...
    if calling bag.has_errors:
        var human as string is calling bag.render_colored
        defer banish human
        calling spark.print with human
        return 1
    return 0
```

- `render_colored` for a terminal (honours `NO_COLOR` and TTY detection);
  `render_json` for CI and the LSP (an array of LSP `Diagnostic` objects with
  0-indexed positions).
- Register the source with `add_source` to get context lines; without it the
  renderer prints `file:line:col` and the label messages.
- `errors_only` / `warnings_and_errors` return deep copies; release them with
  `free_diagnostics`.

### 4.18 JSON-RPC with `std.jsonrpc`

For an LSP or any `Content-Length`-framed stream:

```pengu
import std.jsonrpc as rpc

weave reply with id as JsonRpcId, result as JsonValue into string:
    var msg as JsonRpcMessage is calling rpc.response_ok with id, result
    defer banish msg
    return calling rpc.encode_framed with msg
```

- Use `encode_framed`/`decode_framed_bytes` for LSP; use `encode_message` and
  `parse_message` for HTTP or a test harness.
- `decode_framed_bytes` returns `consumed == 0` when the buffer is incomplete;
  keep reading and retry with the enlarged buffer.
- A batch decodes with `parse_batch`; release it with `take_messages` +
  `free_messages`.
- Validate the `id` before responding: `null` and floats are invalid ids.


### 4.19 Text processing: `std.lingua` and `std.regulus`

`std.scrolls` works on **bytes**, which is right for ASCII, search/replace and
byte-exact protocols. The moment text can contain non-ASCII codepoints, bytes are
the wrong unit: `"ñ".length` is `2`, `"😀".length` is `4`, and iterating a
string yields encoding bytes, not characters.

**Rule 1 — operate on codepoints, not bytes, when the text may be non-ASCII.**
Use `lingua.decode`/`encode` at the boundary and keep byte offsets only for
positions, not for character decisions.

**Rule 2 — validate external input before processing it.** `lingua.is_valid` is
O(n) and allocates nothing; `validate` returns an error with the exact byte
offset. A parser that assumes UTF-8 and discovers otherwise halfway through has
already produced a partial result.

```pengu
import std.lingua
import std.spark

weave main into int:
    var checked as result of void to LinguaError is calling lingua.validate with "año"
    if not checked.is_ok:
        calling spark.eprintln with "input is not UTF-8"
        return 1
    banish checked
    var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with "año"
    if not decoded.is_ok:
        return 1
    var cps as list of Codepoint is decoded.value
    calling spark.println_int with cps.len          # 3 codepoints, 4 bytes
    banish decoded
    return 0
```

**Rule 3 — compile a regex once and reuse it.** `Regex.compile` copies the
pattern and owns one compiled block; compiling inside a loop repeats work and
allocation for no reason. Release the result, not the borrowed `rx`.

```pengu
import std.regulus
import std.spark

weave main into int:
    var compiled as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if not compiled.is_ok:
        return 1
    var rx as Regex is compiled.value
    calling spark.println_bool with (calling rx.is_match with "abc123")
    banish compiled
    return 0
```

**Rule 4 — escape user input before it becomes a pattern.** `regulus.escape`
quotes every metacharacter. Concatenating raw input into a pattern is how a
validator becomes a denial of service or, worse, matches something else.

**Rule 5 — use the smallest engine that fits.** `std.regulus` has a complete,
documented grammar: `. ^ $ * + ? [] \d \w \s`. No groups, no alternation, no
`{n,m}`, no lookaround, no backreferences. If the pattern needs any of those,
install a PCRE satellite explicitly rather than encoding a parser in a regex.

### 4.20 HTTP requests: `Request` → `send` → `Response`

`std.petitio` is the HTTP client. The shape is always the same: build a
`Request`, configure it with the builder methods, `send` it, and **check the
result** before touching the payload. Network failures are values, not
exceptions:

1. `Request.new(method, url)` gives you a request with sane defaults (follows 30
   redirects, verifies TLS, no timeout).
2. Configure it with `header`, `timeout`, `json_body`, `auth_bearer`, … — each
   builder mutates the request and returns nothing, so call them as statements.
3. `send` returns `result of Response to HttpError`. Check `r.is_ok` first.
4. Move the response out with `take_response` (or borrow it with `r.value`) and
   release it with `banish` / `defer banish`.
5. Parse JSON with `resp.json`, which is another `result` — handle it too.

```pengu
import std.json
import std.petitio
import std.spark

weave main into int:
    var req as Request is calling Request.new with "GET", "https://api.example.com/items"
    defer banish req
    calling req.header with "Accept", "application/json"
    calling req.timeout with 5.0

    var r as result of Response to HttpError is calling req.send
    defer banish r
    if not r.is_ok:
        var failure as HttpError is calling petitio.take_error with (sigil of r)
        var why as string is calling failure.message
        calling spark.eprintln with why
        banish why
        banish failure
        return 1
    var resp as Response is calling petitio.take_response with (sigil of r)
    defer banish resp

    var parsed as result of JsonValue to json.JsonError is calling resp.json
    defer banish parsed
    if not parsed.is_ok:
        return 1
    var root as JsonValue is parsed.value
    calling spark.println_int with (calling root.array_len)
    return 0
```

Use the one-shot helpers (`petitio.get`, `petitio.post_json`, …) when you do not
need to configure anything: they build, send and release the request themselves.
Use a `Session` when several requests share headers or cookies.

For bodies that must not be buffered, `send_to_file(path)` writes to disk and
`send_stream(cb, user)` forwards each chunk to a callback. The callback's
`chunk` is a **borrowed view** of libcurl's buffer: do not store it, release it,
or let it escape; returning `false` aborts with `HttpError.Cancelled`. For
several requests at once, `fetch_many(requests)` runs them on one thread with
libcurl-multi and returns results in input order (the input `Request`s remain
yours). Pick the protocol with `http_version(HttpVersion.Http2)` and read what
the server spoke from `resp.http_version`; authenticate with `auth_basic` /
`auth_digest` / `auth_any`, and use SOCKS proxies with `socks_proxy` (DNS on the
proxy, `socks5h`).

### 4.21 Compression: `gzip`, `zlib` or raw deflate

`std.compressus` is the compression module. The first decision is **whether to
compress at all**: compression trades CPU for bytes, and it only wins when the
payload is larger than a few hundred bytes and is not already compressed. JPEG,
PNG, MP4, ZIP, `.gz`, PDF (usually) and most modern protocol bodies are already
compressed; running them through gzip again spends CPU to make them *bigger*.

The second decision is the **format**:

| Use case | Format | Why |
|---|---|---|
| A file on disk (`.gz`, a tarball, a download) | `CompressionFormat.Gzip` | self-describing, `gzip -d` and every archive tool read it |
| HTTP `Content-Encoding: gzip` | `CompressionFormat.Gzip` | what browsers and servers negotiate |
| A protocol that says "zlib" (PNG `IDAT`, some HTTP) | `CompressionFormat.Zlib` | the smaller framing and the Adler-32 the spec asks for |
| A protocol that already frames and checksums (ZIP member, WebSocket `permessage-deflate`) | `CompressionFormat.RawDeflate` | no duplicated header or checksum |

Compression always returns a `result`: bad input is a value, never a panic. The
result owns the compressed bytes; borrow them with `.value` and release the whole
result with `banish`.

```pengu
import std.compressus
import std.spark

weave save_log with text as string, path as string into int:
    var packed as result of string to CompressError is calling compressus.gzip_compress with text, CompressionLevel.Best
    defer banish packed
    if not packed.is_ok:
        var failure as CompressError is packed.error
        var why as string is calling failure.message
        calling spark.eprintln with why
        banish why
        return 1
    var ok as bool is calling archivum.write_bytes with path, packed.value
    if not ok:
        return 1
    return 0
```

Use `CompressionLevel.Fastest` on a hot path (logs, telemetry, request bodies)
and `CompressionLevel.Best` when the file is written once and read many times.

**One-shot vs chunks.** The one-shot functions hold the whole input and the
whole output in memory. Below ~10 MB that is the right tool: one call, one
allocation, no state machine. Between 10 MB and ~100 MB it still works but the
peak memory is input + output; above ~100 MB, split the payload into independent
gzip **members** and concatenate them — `gzip_decompress` (and every reader)
accepts a multi-member file. A real streaming API lands in 2.14.1.

**Verify what you transport.** `crc32` and `adler32` return the same values as
Python's `zlib.crc32` / `zlib.adler32`, and the `*_continue` variants let a file
be checked chunk by chunk. A downloaded dependency is not trustworthy until its
checksum matches the one in the manifest.

---

## 5. Optionals, results and errors

### 5.1 Choosing the right type

| Situation | Type | Example |
|---|---|---|
| May be missing, with no reason for failure | `maybe T` | `find_user → maybe User` |
| May fail with detail | `result of T to E` | `parse_config → result of Config to ConfigError` |
| Unrecoverable failure (bug, broken invariant) | `panic` | `weave divide with a, b: if b == 0: panic "division by zero"` |
| Pointer that may point to nothing | `ref to T` + `null` | `ref to Buffer is null` |

**Rule:** Never use a sentinel value (`-1`, `""`, `0`) for "not found". Use `maybe T`.

### 5.1.1 The boundary: absence vs cause

`maybe` and `result` do not compete; they answer different questions:

| Question | Container | When |
|---|---|---|
| “Is it there or not?” | `maybe T` | Absence is a normal outcome and there is nothing else to report |
| “Did it fail? Why?” | `result of T to E` | The caller must distinguish causes and react differently |
| “Yes or no?” | `bool` | There are only two answers and no cause to report |
| “This cannot happen” | `panic` | Broken invariant or programmer bug |

**Do not use `maybe` to hide a failure with a cause.** `read_file → maybe string`
cannot tell “missing” from “permission denied”; if the caller needs that
distinction, the API must be `result of string to IoError`.

**Do not use `result` for an ordinary lookup.** `find_user → result of User to
NotFound` forces an invented error and makes “not found” look exceptional. If
absence is the answer, `maybe User` is more honest.

**Do not use `result of T to string` as a catch-all.** Define one `omen` per
module (`IoError`, `JsonError`, `LinguaError`, `HttpError`, …); the caller can
then `judge` the variants and the compiler checks exhaustiveness.

### 5.1.2 Constructors and ownership

```pengu
# maybe: presence
var user as maybe User is some found
var nobody as maybe User is maybe none

# result: typed cause
var cfg as result of Config to ConfigError is calling ok_of with parsed
return calling err_of with ConfigError.Missing
```

- `some x`, `calling ok_of with x` and `calling err_of with x` are the only
  constructors. **`ok x` and `err x` do not exist** (`E0004`); do not write them.
- The type of `E` must be the one declared by the `result`. Do not mix a
  `string` with an `omen` just because both are “errors”.
- Boxing an owning payload from a variable or field **moves** it: the box
  becomes the owner and the source slot is emptied. Do not `banish` the source
  after `some s` / `ok_of with s` / `err_of with s`.
- Inside a function, a string/container parameter is **borrowed**: boxing it
  clones the payload and the caller keeps its own copy. Do not try to move the
  caller's slot from the callee.
- `banish m` on a `maybe`/`result` releases the payload the box owns and the
  box. In an `or:` over a `result`, the `error` binding owns the payload; if you
  do not re-box it, release it inside the block.
- `result of void to E` has no success payload; the current idiom is
  `return calling ok_of with 0` (a dummy that is never read).

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
weave load_config into result of Config to ConfigError:
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

**Debugging:** when a generic pipeline makes an optional's static type
non-obvious, print `type of value` (`"maybe int"`, `"result of int to string"`).
It is a compile-time string with zero runtime cost — use it for diagnostics and
assertions, never as a runtime type check to branch on (§14.28).

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
| `archivum.copy(src, dst)` — neither is "the subject" | module function | `calling archivum.copy with src, dst` |
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

### 6.7 Primitive enchanting (`shard T where T: …`)

A primitive (`int`, `float`, `char`, `bool`, …) is a valid `enchanting` target. Unlike runes, `self` is **a value**, not a reference: `set self` is rejected with `E0006` and `self->field` with `E0003`.

When the method applies to **several** primitive types, bound it with `shard T where T: …`:

```pengu
# ✅ Pengunic: one definition, N types
enchanting shard T where T: Num and T: Ordo and T: Par:
    weave abs into T:
        if self < donum T:
            return -self
        return self

# ❌ Anti-Pengunic: N identical definitions
enchanting int:   weave abs into int: ...
enchanting i64:   weave abs into i64: ...
enchanting float: weave abs into float: ...
enchanting f64:   weave abs into f64: ...
```

Rules:

1. **One module per capability, not per type.** `numerus` (`Num`), `integrum` (`Integrum`), `fractio` (`Real`), `littera` (`char`), `logica` (`bool`).
2. **The bound decides which types have the method.** The compiler checks it at the call site: `(1.5).is_even` is `E0005` because `float` does not satisfy `Integrum`.
3. **Monomorphization per concrete type.** The emitted C is `int_abs`, `f64_abs`, etc. Zero overhead.
4. **`Num` grants neither ordering nor equality.** Those are the orthogonal concepts `Ordo` (`<`, `<=`, `>`, `>=`) and `Par` (`==`, `!=`). The refinements `Integrum` and `Real` grant both: every type satisfying either is a numeric primitive, and every numeric primitive is ordered and comparable. That is why `std.integrum` can write `where T: Integrum:` and still use `<`, `<=`, `==`. A generic that only needs `+ - * /` and compares by hand writes `where T: Num and T: Ordo and T: Par:` — which is what `std.numerus` does.
5. **Never `antiquus` for trivial logic.** Use `declare` to `libm` when C is genuinely needed (`sqrt`, `sin`).
6. **Predicates with `is_*`.** Pure queries keep the bare name (`abs`, `floor`).
7. **One method per correct bound.** If a method cannot work for every type of a bound, move it to the strictest bound that fits. `sqrt` does not work on `int`, so it lives in `fractio` (`Real`), not in `numerus` (`Num`).
8. **`@mutates` for the mutating/pure pair.** A method that returns the receiver's own type may be marked `@mutates`: `calling x.clamp with …` **mutates `x`** (statement only) and `calling x.get_clamp with …` returns the value without touching it. Exactly **one** C function is emitted and the body stays pure (`self` is a value, `E0006` intact): the call site does the assignment. Outside an `enchanting` block, with an `into` that is not the receiver's type, or with a body that assigns to `self`, it is `E0067`; declaring `get_<name>` as well is `E0068`; using the mutating form where a value is required is `E0066`. See `LANGUAGE.md` §10.1.

**`Donum` is automatic for runes.** A `rune` or `echo` whose every field is
defaultable implements `Donum` — `donum Point` just works, with no `derive
Donum` and no `bind` (see `LANGUAGE.md` §11.4). A container field (`list`, `map`,
`slice`, `maybe`, `result`) removes it, because a zeroed container would be
corrupt rather than empty; `derive Donum` is `E0005` (§14.29).

| Module | Bound | Covers | Mutating (statement) | Pure form |
|---|---|---|---|---|
| `std.numerus` | `T: Num and T: Ordo and T: Par` | all numeric primitives | `abs`, `clamp`, `pow_int`, `round` | `get_abs`, `get_clamp`, ... |
| `std.integrum` | `T: Integrum` | integers only | `gcd`, `lcm`, `next_prime`, `factorial` | `get_gcd`, `get_lcm`, ... |
| `std.fractio` | `T: Real` | `float`, `f32`, `f64`, `double` | `sqrt`, `sin`, `exp`, `reciprocal` | `get_sqrt`, `get_sin`, ... |
| `std.littera` | `char` | `char` | `to_upper`, `to_lower` | `get_to_upper`, `get_to_lower` |
| `std.logica` | `bool` | `bool` | `implies`, `xor`, `iff`, `toggle` | `get_implies`, `get_xor`, ... |

Since version 2.1.0 of these modules every method that returned the receiver's own
type is marked `@mutates`: `calling x.abs` **rewrites `x`** and is only valid as
a statement, while `calling x.get_abs` returns the value and leaves `x` alone.
Exactly **one** C function per receiver is emitted.  Predicates (`is_even`,
`is_nan`, `approx_eq`) and conversions (`to_int`, `to_hex`, `div_rem`) still
return their value and take no part in the split.  See `LANGUAGE.md` §10.1 and
`MIGRATION.md`.

Transcendentals that call `libm` live in two **concrete** blocks (`enchanting float:` and `enchanting f64:`) rather than in the shard, because C exposes different symbols per width (`sqrtf` vs `sqrt`). Pure predicates and utilities stay in the single `enchanting shard T where T: Real:` block. Declare only the canonical names (`float`, `f64`): `f32` and `double` are aliases of the same C type, and declaring both spellings is `E0047`.

The five modules cover **every** primitive type of the language. Import the module whose bound matches the receiver and the methods appear at zero runtime cost: the compiler monomorphizes each call into a plain C function (`int_abs`, `f64_sqrt`, `char_to_upper`, `bool_to_int`, …). A program that imports none of them pays nothing for them; a program that imports one pays only for the methods it actually calls.

`std.arithmancy` keeps its scalar functions (`abs_i`, `clamp_f`, `sqrt_f`, …) for compatibility, but their implementation is a **one-line wrapper** over the methods of the five modules. The algorithm lives in exactly one place: the module that owns the bound. The `Vec2`/`Vec3`/`Mat4`/`Quat` types and the `PI`/`TAU`/`E`/`EPSILON` constants remain `arithmancy`'s responsibility.

### 6.8 Manual memory with `std.memoria`

`std.memoria` is the canonical API for reserving and manipulating heap blocks. It does **not** replace the language operators — it complements them: `banish` still frees, `size of T` still measures, `sigil of x` still takes an address, `essence of p` still dereferences.

| You need | Use |
|---|---|
| Reserve one value | `calling memoria.alloc of T` |
| Reserve N elements | `calling memoria.alloc_array of T with n` |
| Grow/shrink a block | `calling memoria.resize_array of T with p, old_n, new_n` |
| Copy blocks (possibly overlapping) | `calling memoria.copy of T with dst, src, n` |
| Fill / reset a block | `calling memoria.fill of T with p, value, n` · `calling memoria.zero of T with p, n` |
| Free | `banish p` (there is **no** `memoria.free`!) |
| Size of `T` | `size of T` (there is **no** `memoria.sizeof`!) |

Every method is `shard T`: the compiler monomorphizes the call into a plain C function (`memoria_alloc_int`, `memoria_alloc_array_byte`, `memoria_resize_array_float`, …). No boxing, no vtables.

**Rule:** put `defer banish` (or `errdefer banish`) immediately after allocating:

```pengu
import std.memoria

weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 16
    defer banish buf
    calling memoria.fill of int with buf, 7, 16
    calling memoria.zero of int with buf, 16
    return 0
    # `defer banish buf` reads the *variable* at scope exit, so if `buf` was
    # reassigned by `resize_array`, it frees the current pointer, not a snapshot.
```

`resize_array` takes an explicit `old_n` because C's `realloc` cannot know how many elements the block holds, and it may move the block: **after a successful resize the old pointer is invalid — use only the return value**. `defer banish buf` + `set buf is calling memoria.resize_array …` is the safe pattern.

> ⚠️ A `defer banish` in the *same* scope as a `return` of the same pointer is a bug: the defer runs and frees the block, and the caller receives a dangling pointer. Return ownership by moving the release to the caller.

**OOM**: `alloc`, `alloc_array` and `resize_array` abort with `[PENGU] out of memory`. When you would rather handle the failure, use the `try_*` variants, which return `maybe`:

```pengu
var mp as maybe ref to int is calling memoria.try_alloc of int
if p as ref to int is mp:
    set essence of p is 1
    banish p        # free the block
banish mp           # free the maybe box (a `maybe ref to T` owns the box, not the pointee)
```

**Zeroed by default**: `alloc` and `alloc_array` return zeroed memory. There is no `alloc_uninit`; if you truly need an uninitialized block (measured performance, startup code), use an `antiquus` block with `malloc` and document why.

---

### 6.9 Thick functions and callbacks with context

PenguScript has no closures, by design (`LANGUAGE.md` §8.4.1). A callback that
"remembers" something is not an environment the compiler captures; it is a
**value you pass explicitly**. Five patterns cover every case a closure would
solve, all of them zero-cost and visible at the call site.

#### Pattern 1 — a C callback with `void* user_data`

This already works with the language primitives: declare the C signature with
`ref to void` in the callback's state slot, pass the address of your state with
`sigil of`, and cast it back inside the callback.

```pengu-fragment
# C: void visit_all(void (*cb)(void *item, void *user), void *items, int n);
declare visit_all with cb as ref to weave with item as ref to void, user as ref to void into void, items as ref to void, n as int into void

weave count_item with item as ref to void, user as ref to void into void:
    var counter as ref to int is transmute user to ref to int
    set essence of counter is (essence of counter) + 1

weave main into int:
    var hits as int is 0
    var xs as list of int is [1, 2, 3]
    calling visit_all with count_item, (sigil of xs), 3
    return 0
```

The `transmute` is the C boundary talking; it is the same cast C itself writes.
Keep it in the callback, never in the pipeline.

#### Pattern 2 — a visitor over an AST

A visitor has several methods that share state, so the state belongs in a
`rune` and the contract in a `concept`. `bind` implements the contract, and
`judge over rune` dispatches on the node without a vtable or a closure:

```pengu
import std.spark

rune Expr:
    kind as ExprKind
    int_value as int
    left as ref to Expr
    right as ref to Expr

omen ExprKind:
    Literal
    Binary
    Neg

concept ExprVisitor:
    weave visit_literal with e as ref to Expr into int
    weave visit_binary with e as ref to Expr into int
    weave visit_neg with e as ref to Expr into int

rune Printer:
    marker as int

bind Printer with ExprVisitor:
    weave visit_literal with e as ref to Expr into int:
        return e->int_value
    weave visit_binary with e as ref to Expr into int:
        return (calling walk with (essence of self), e->left) + (calling walk with (essence of self), e->right)
    weave visit_neg with e as ref to Expr into int:
        return 0 - (calling walk with (essence of self), e->left)

weave walk shard V where V: ExprVisitor with v as V, e as ref to Expr into int:
    judge e over kind:
        when Literal -> calling v.visit_literal with e
        when Binary -> calling v.visit_binary with e
        when Neg -> calling v.visit_neg with e

weave main into int:
    var one as Expr is with kind is Literal, int_value is 3
    var two as Expr is with kind is Literal, int_value is 4
    var sum as Expr is with kind is Binary, left is (sigil of one), right is (sigil of two)
    var neg as Expr is with kind is Neg, left is (sigil of sum)
    var p as Printer is with marker is 0
    calling spark.println with "{calling walk with p, (sigil of neg)}"   # -7
    return 0
```

The `walk` is monomorphized per visitor, so calling `visit_literal` is a plain
C call. Adding a variant means adding a method to the `concept`: the compiler
reports every `bind` that does not implement it.

#### Pattern 3 — a pipeline step with an extra parameter

When the callback is only called inside a loop, it does not need a `Fn` at all:
pass the context to the `*_ctx` family. The context can be a rune, a scalar, a
`ref to` or a `string`.

```pengu
import std.loom
import std.spark

rune Scaler:
    factor as int
    min_value as int

weave scale with s as ref to Scaler, x as int into int:
    return s->factor * x

weave keep with s as ref to Scaler, x as int into bool:
    return x >= s->min_value

weave main into int:
    var s as Scaler is with factor is 2, min_value is 6
    var xs as list of int is [1, 2, 3, 4]
    var scaled as list of int is calling loom.map_ctx with xs, (sigil of s), scale
    var kept as list of int is calling loom.filter_ctx with scaled, (sigil of s), keep
    calling spark.println with "{scaled at 0} {scaled at 3} {kept at 0} {kept at 1}"   # 2 8 6 8
    banish scaled
    banish kept
    return 0
```

`fold_ctx`, `for_each_ctx`, `zip_with_ctx`, `find_first_ctx`, `any_ctx`,
`all_ctx`, `partition_ctx` and `filter_map_ctx` take the same explicit context.
The context is borrowed for the synchronous call; the returned list is yours.

#### Pattern 4 — returning a configured function

Two shapes, both explicit:

```pengu-fragment
# (a) a rune with a method: the type names the configuration
rune Doubler:
    factor as int

enchanting Doubler:
    weave call with a as int into int:
        return self->factor * a

# (b) std.functor.Fn1: one callable type for every configuration
import std.functor

rune Multiplier:
    factor as int

weave apply with m as ref to Multiplier, x as int into int:
    return m->factor * x

var m as Multiplier is with factor is 3
var f as functor.Fn1 of int, int is calling functor.make_fn1 with apply, (sigil of m)
```

Use (a) when the callable is part of the domain (a `Validator`, a `Filter`, a
`Reducer`) and deserves a name and doc comments. Use (b) when the callable is an
implementation detail stored in a field or passed through several layers: one
`Fn1` type serves every configuration, but the context must outlive it and the
call is dynamic.

#### Pattern 5 — storing a callback with state

A `Fn1`/`Fn2`/`Fn3` is a value, so it can be a field of a larger rune. This is
the event-handler shape: the state lives in the context, the rune stores the
callback, and the caller owns both lifetimes explicitly.

```pengu
import std.functor
import std.spark

rune Button:
    label as string
    on_click as functor.Fn1 of int, void

weave log_click with clicks as ref to int, button as int into void:
    set essence of clicks is (essence of clicks) + 1
    calling spark.println with "button {button} clicked {essence of clicks}"

weave main into int:
    var clicks as int is 0
    var f as functor.Fn1 of int, void is calling functor.make_fn1 with log_click, (sigil of clicks)
    var b as Button is with label is "Save", on_click is f
    calling b.on_click.call with 1
    calling b.on_click.call with 1
    return 0
```

| You need… | Use… |
|---|---|
| a C callback with `void*` | `ref to void` + `sigil of` |
| a visitor over an AST | `concept` + `bind` + `judge over rune` |
| a pipeline step with an extra parameter | `loom.*_ctx` |
| to return a configured function | a `rune` with a method **or** `functor.Fn1` |
| a callback stored for later | `functor.Fn1` / `Fn2` / `Fn3` |
| an event handler with state | a `rune` + `functor.FnN`, or `rune` + `enchanting` when the handler is a method |

The rule of thumb: **build the context as a value, pass it explicitly, and let
the type say who owns what**. If a callback needs more than one operation or
several pieces of state, it is a `concept`/`rune`, not a `Fn`.

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
| `sqrt`, `is_nan`, `floor`, `ceil` (float-only operations) | `T: Real` |
| `a == b`, `a != b` | `T: Par` |
| `a < b`, `a <= b`, `a > b`, `a >= b` | `T: Ordo` |
| `donum T` | `T: Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Forma` or `Donum` |
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

### 8.8 Choosing an allocation strategy

Four tools cover almost every allocation in PenguScript. Pick by **lifetime**, not
by type:

| Tool | Lifetime | Use it for | Do **not** use it for |
|---|---|---|---|
| `memoria.alloc` / `alloc_array` | one value, released by you | a single object, a long-lived buffer, a struct that outlives the call | a tree of many objects released together |
| `std.arena` | one batch, released together | ASTs, parse trees, temporary graphs, per-frame scratch | one object (that is `memoria.alloc`), or objects with different lifetimes |
| `std.builder` | one text value, built incrementally | CSV, HTML, logs, codegen, any loop that appends | two or three fixed pieces (interpolation is clearer and allocates once) |
| `std.bitset` | a dense universe of integers | visited flags, sieves, Bloom filters, occupancy maps | a sparse set (use `map of int to int`) |

#### Text: interpolation vs `StringBuilder`

```pengu
import std.builder

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "row: "
    calling sb.append_int with 7
    var row as string is calling sb.to_string
    defer banish row
    return 0
```

`"{a}{b}{c}"` is one allocation and is the right spelling for a fixed number of
pieces. A builder is for a loop whose piece count is unknown: `n` appends cost
`O(total bytes)`, while `out = "{out}{piece}"` in a loop costs `O(n²)`.

#### Trees: `Arena` vs one allocation per node

```pengu
import std.arena

rune Node:
    value as int

weave main into int:
    var a as Arena is calling Arena.new
    defer banish a
    defer calling a.free
    var n as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set n->value is 1
    return 0
```

One `free` releases every node. Remember that `reset`/`free` do not run
destructors: if a node owns a `string`, release that string first or keep the
arena contents POD.

#### Dense sets: `BitSet`

```pengu
import std.bitset

weave main into int:
    var seen as BitSet is calling BitSet.new with 1024
    defer banish seen
    calling seen.set with 42
    return 0
```

`BitSet` is O(1) per bit and `bit_len / 8` bytes total. For a handful of values in
a huge universe, `map of int to int` is smaller and faster.

#### Anti-patterns

- **Builder for two strings.** `"{a}{b}"` allocates once and is shorter.
- **Arena for one object.** Use `memoria.alloc` + `banish`; an arena adds blocks
  and a lifecycle for no benefit.
- **BitSet for a sparse set.** A million-bit bitset for ten values is 125 KiB of
  mostly zeros; a map is ten entries.
- **Keeping a borrowed view across a mutation.** `bytes_view`, `to_bytes` and
  `arena.alloc` pointers are invalidated by growth, `reset`, `free` or `banish`.

---

## 9. C interoperability

### 9.1 `.d.pengu` for bindings

**Never** declare `declare foo...` in a pure-logic `.pengu`. Bindings go in their `.d.pengu`:

```pengu
# sqlite3 satellite binding — installed with `pengu add <url>`
include "sqlite3.h"
link "sqlite3"

rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to ref to opaque into int
declare sqlite3_close with db as ref to opaque into int
```

External C bindings no longer live in `std/`: `sqlite3` was extracted to a satellite repository installed with `pengu add <url>` (catalogue: [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)). The same holds for `raylib`, `yaml`, `uuid`, `xlsx` and the rest; the `.d.pengu` rules below apply to all of them.

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

(`raylib` is a satellite binding: install it with `pengu add <url>` — see [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).)

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
| `std.arithmancy` | Python's `math`; Rust's `f64` methods |
| `std.cipher` | Python's `base64`, `json`; Rust's `serde_json` |
| `std.filum` | Python's `threading`, Go's `sync`; Rust's `std::thread` |
| `std.lot` | Python's `random`; Rust's `rand` |

If, on reading your API, a Python/Rust/Go user says *"I would do this in two lines with `X`"*, **your API needs that `X`**. Regex (`regulus`) and HTTP (`precis`) are no longer `std.*`: they are satellite bindings (`pengu add <url>`, catalogue in [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)).

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

The same holds for a function that only wraps a method. Do not copy the algorithm; delegate:

```pengu
# ✅ Pengunic: the algorithm lives in std.numerus
weave abs_i with x as int into int:
    return calling x.abs
```


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

`Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum` are **compiler globals** and are not redefined.

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

### 14.25 Using the `@mutates` form where a value is expected

```pengu
# ❌ E0066: 'clamp' mutates the receiver and returns nothing
var capped as int is calling hp.clamp with 0, 100

# ✅ Pengunic: the pure form returns the value
var capped as int is calling hp.get_clamp with 0, 100
```

A `@mutates` method (and the in-place forms of `std.scrolls`) is a **statement**:
it mutates the receiver and produces no value. Inside a chain or an expression you
must use `get_<name>`. See §6.7 and `LANGUAGE.md` §10.1.

### 14.26 Rune with a discriminant when an `omen` would do

```pengu
# ❌ Anti-Pengunic: the discriminant adds a tag the union does not need
rune Event:
    kind as EventKind
    key as string
    x as int
    y as int

omen EventKind:
    Key
    Click

# ✅ Pengunic: the algebraic `omen` says exactly what each variant carries
omen Event:
    Key with key as string
    Click with x as int, y as int
```

### 14.27 Unnecessary label on a single loop

```pengu
# ❌ Anti-Pengunic: a label that no 'break'/'continue' targets
outer: for x in xs:
    calling process with x

# ✅ Pengunic: the only loop needs no label
for x in xs:
    calling process with x
```

A label is for leaving an **outer** loop from inside an inner one (`LANGUAGE.md`
§7.5). On a single loop it adds a name, an `E0069` risk (labels are function-local
and unique) and no capability.

### 14.28 `type of` used as a runtime type check

```pengu
# ❌ Anti-Pengunic: 'type of' is a compile-time constant, not a runtime check
if type of value == "int":
    calling handle_int with value
else:
    calling handle_other with value

# ✅ Pengunic: branch at compile time with a generic (or an overload)
weave handle shard T with value as T into void:
    calling print with "{value}"
```

`type of expr` yields a borrowed string literal chosen while compiling; the
`else` branch above is dead before C is emitted. Use it for diagnostics and test
assertions, and use a generic/overload for behaviour.

### 14.29 `derive Donum`

```pengu
# ❌ E0005: 'Donum' is automatic for rune 'Point'; no 'derive' is needed
rune Point derive Donum:
    x as int

# ✅ Pengunic: every field is defaultable, so 'donum Point' just works
rune Point:
    x as int
```

`Donum` is **not** one of the five derivable concepts (`Par`, `Ordo`, `Vinculum`,
`Imago`, `Nexus`). A rune or echo gets it automatically when every field is
defaultable (`LANGUAGE.md` §11.4).

### 14.30 A closure disguised as a rune with a single `ctx` field

```pengu
# ❌ Anti-Pengunic: the rune exists only to carry one parameter through a loop
rune Multiplier:
    factor as int

weave apply_all with xs as list of int, m as ref to Multiplier into list of int:
    var out as list of int is list of int
    for x in xs:
        calling out.push with (m->factor * x)
    return out

# ✅ Pengunic: the transformation is one named callback; the loop is loom's job
rune Multiplier:
    factor as int

weave scale with m as ref to Multiplier, x as int into int:
    return m->factor * x

var ys as list of int is calling loom.map_ctx with xs, (sigil of m), scale
```

If the rune only exists to carry a parameter through a loop, the loop is the
thing to remove: `loom.map_ctx` already knows how to iterate, the callback is
reusable outside the loop, and no new type is invented. A rune is a domain
concept, not a closure with a name.

### 14.31 Wrapping everything in `Fn1` when a `concept` + `bind` is clearer

```pengu-fragment
# ❌ Anti-Pengunic: one Fn1 per method, and the visitor has three
var visit as functor.Fn1 of Expr, void is calling functor.make_fn1 with visit_one, (sigil of self)
calling visit.call with e

# ✅ Pengunic: several methods sharing state are a concept + bind
concept ExprVisitor:
    weave visit_literal with e as ref to Expr into int
    weave visit_binary with e as ref to Expr into int
    weave visit_neg with e as ref to Expr into int

bind Printer with ExprVisitor:
    weave visit_literal with e as ref to Expr into int:
        return e->int_value
    weave visit_binary with e as ref to Expr into int:
        return 0
    weave visit_neg with e as ref to Expr into int:
        return 0
```

`functor.Fn1` is **one** callback with **one** context. If the visitor has
several methods that share state, a `concept` names each operation, `bind` puts
the state in a `rune`, and the call stays monomorphized. A `Fn1` would force one
dynamic call per operation and bury the contract in the call site.

### 14.32 `loom.map_ctx` for complex logic that deserves a named rune

```pengu
# ❌ Anti-Pengunic: business logic buried in a callback
omen Mode:
    Fast
    Slow

rune Config:
    mode as Mode

weave apply_complex with cfg as ref to Config, x as int into int:
    if cfg->mode == Mode.Fast:
        return x * 2
    if x < 0:
        return 0
    return x + 1

var results as list of int is calling loom.map_ctx with xs, (sigil of cfg), apply_complex

# ✅ Pengunic: the logic has a name and a home
enchanting Config:
    weave transform with x as int into int:
        if self->mode == Mode.Fast:
            return x * 2
        if x < 0:
            return 0
        return x + 1

var results2 as list of int is for x in xs then (calling cfg.transform with x)
```

`loom.map_ctx` is for a **pure, simple** transformation. When the callback has
branches, constants and "personality", it is a method of the rune that owns the
state: it gets a name, a docstring, tests, and a call site that reads like
domain code instead of a loop with a lambda.

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
| No unsafe conversion (§9.4) | **Enforced** | `0 W0001` across all 29 modules. `std/functor` is the **one named exception**: its eight `transmute` calls are the Zig/Odin thick-function constructor, silenced with a module-level `# pengu: allow-warnings W0001` directive (see `LANGUAGE.md` §8.4.1). Everywhere else `std/` has zero `transmute` calls; the only other occurrence is an explanatory comment in `std/ffi.pengu:67`. If another module ever needs one, it is confined to `std/ffi`/`std/filum` and must be same-size | `python pengu_project.py check --entry std/<module>.pengu` |
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
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"

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
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"
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
let slug is calling raw.get_trim.get_lower.get_replace with " ", "-"
```

If an intermediate link needs arguments and is not the last one, the chain cannot be written; split it:

```pengu
# ❌ Anti-Pengunic: there is no way to pass 'with 0, 4' to the intermediate 'substring'
# let slug is calling raw.get_trim.get_substring with 0, 4.lower

# ✅ Pengunic: two expressions, explicit names
let head is calling raw.get_trim.get_substring with 0, 4
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
calling raw.get_trim.get_lower.get_replace(" ", "-").split("-").filter_nonempty.first_or("none")

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

### 14.33 Handling `JsonValue` with `if kind == ...` instead of `as_*`

```pengu
# ❌ Anti-Pengunic: the variant is inspected by hand and every miss is a panic
if calling value.type_name == "string":
    var s as string is value.raw_string
else:
    calling panic with "not a string"

# ✅ Pengunic: an explicit maybe, no hidden panic
var s as maybe string is calling value.as_string
if text as string is s:
    calling use with text
banish s
```

`as_bool`, `as_int`, `as_float`, `as_number`, `as_string`, `as_array` and
`as_object` are the typed, non-panicking accessors. Use `type_name` only for
diagnostics, not for dispatch.

### 14.34 Building diagnostics by hand instead of `DiagnosticBag`

```pengu
# ❌ Anti-Pengunic: a string that no tool can consume
calling spark.println with "error: bad thing at line 4"

# ✅ Pengunic: a structured diagnostic, rendered for a human or the LSP
calling bag.error with "bad thing", span
var text as string is calling bag.render_colored
```

The structured form carries the span, severity and code; `render_colored` and
`render_json` are just two views of the same data.

### 14.35 Serializing a user type without an explicit conversion

```pengu
# ❌ There is no implicit reflection: this does not compile, and adding it
#    would hide allocation and field order.
var text as string is calling json.stringify with user

# ✅ Convert explicitly to a JsonValue, then serialize
var obj as JsonValue is calling JsonValue.empty_object
calling obj.put_json with "name", (calling JsonValue.string_val with user.name)
var text as string is calling json.stringify with obj
banish obj
```

`std.json` serializes `JsonValue`, not arbitrary PenguScript values. The
conversion is the schema: it makes field order, renaming and omitted fields
visible at the call site.

### 14.36 Iterating `for ch in s` to process UTF-8 text

```pengu-invalid
# ❌ Anti-Pengunic: iterates encoding bytes; 'ch' is a one-byte string, so a
#    multibyte character is split and every count is a byte count.
for ch in text:
    if ch == "ñ":
        calling spark.println with "found"
```

```pengu
# ✅ Pengunic: decode first, then decide on codepoints
var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with text
if decoded.is_ok:
    var cps as list of Codepoint is decoded.value
    var i as int is 0
    while i < cps.len:
        if (cps at i) to u32 == 0xF1:
            calling spark.println with "found"
        set i is i + 1
    banish decoded
```

`scrolls.char_at` and `for ch in s` are byte operations. They are correct for
ASCII and for byte-exact protocols; use `lingua` when the unit is a character.

### 14.37 Using a regex to parse JSON, HTML or XML

```pengu-invalid
# ❌ Anti-Pengunic: a regex cannot parse nested structures, quoted delimiters
#    or escapes. This accepts some invalid documents and rejects valid ones.
var compiled as result of Regex to RegexError is calling Regex.compile with r"\{[^}]*\}"
```

```pengu
# ✅ Pengunic: use the parser that owns the grammar
var parsed as result of JsonValue to json.JsonError is calling json.parse with text
```

Regexes match regular languages. JSON, HTML and XML are not regular. Use
`std.json` for JSON and a real parser (or `std.ledger` for CSV) for the rest.

### 14.38 Building a regex by concatenating raw strings

```pengu-invalid
# ❌ Anti-Pengunic: user text is interpreted as pattern syntax
var compiled as result of Regex to RegexError is calling Regex.compile with user_input
```

```pengu
# ✅ Pengunic: quote the literal, then compose deliberately
var quoted as string is calling regulus.escape with user_input
var pattern as string is "{quoted}$"
var compiled as result of Regex to RegexError is calling Regex.compile with pattern
banish pattern
banish quoted
```

`regulus.escape` makes a literal a literal. If the input is meant to be a
pattern, say so at the API boundary and document the grammar the user may use.

### 14.39 Using `std.regulus` for complex validation (RFC 5322 e-mail, URLs)

```pengu-invalid
# ❌ Anti-Pengunic: "validate an e-mail with a regex" is a shape check,
#    not delivery, and the full RFC grammar does not fit this engine.
var compiled as result of Regex to RegexError is calling Regex.compile with "^[^@]+@[^@]+$"
```

```pengu
# ✅ Pengunic: check the shape explicitly, then let the real system decide
var at as int is calling scrolls.find with address, "@"
if at <= 0 or at >= (address length) - 1:
    return 1
# ... send a confirmation mail; that is the only real validation ...
```

A regex can reject obvious typos. It cannot prove an address exists, and RFC 5322
has comments, quoted local parts and domain literals that this engine cannot
express. If the validation is genuinely complex, install a PCRE satellite and
document the grammar; do not smuggle a parser into a tiny engine.

### 14.40 Ignoring the `result` of `send`

```pengu-invalid
# ❌ Anti-Pengunic: the response (and the error) of a request is a `result`.
var r as result of Response to HttpError is calling petitio.get with url
var resp as Response is r.value          # unsafe when r is an error
calling spark.println with resp.body     # empty Response, no explanation
```

```pengu
# ✅ Pengunic: branch on the result, then move or borrow the payload
var r as result of Response to HttpError is calling petitio.get with url
defer banish r
if not r.is_ok:
    var failure as HttpError is calling petitio.take_error with (sigil of r)
    var why as string is calling failure.message
    calling spark.eprintln with why
    banish why
    banish failure
    return 1
var resp as Response is calling petitio.take_response with (sigil of r)
defer banish resp
var body as string is calling resp.text
calling spark.println with body
banish body
```

A `result` is the whole point: DNS failure, a timeout, a TLS error and a 500 all
look different and all need a decision. `r.value` on a failed result yields a
zeroed payload, and the failure reason is silently dropped — along with the
diagnostic that would have explained the bug.

### 14.41 Building a URL by concatenating unencoded strings

```pengu-invalid
# ❌ Anti-Pengunic: a space, '&', '#', '?' or a non-ASCII byte corrupts the URL.
var url as string is "https://api.example.com/search?q=" + query
```

```pengu
# ✅ Pengunic: encode, or let build_query_string sort and encode for you
var params as map of string to string is map of string to string
calling params.put with "q", query
var url as string is calling petitio.with_query with "https://api.example.com/search", params
defer banish url
banish params
```

`+` is not concatenation in PenguScript (see §14.1), but the same mistake comes
back as interpolating raw input into a URL. `url_encode` escapes every byte
outside RFC 3986's unreserved set, and `build_query_string` also sorts the keys so
the same parameters always produce the same URL.

### 14.42 Releasing a `result` and the payload it owns

```pengu-invalid
# ❌ Anti-Pengunic: the result owns the Response; both banishes free its strings.
var r as result of Response to HttpError is calling petitio.get with url
var resp as Response is r.value
banish resp
banish r
```

```pengu
# ✅ Pengunic: one owner, one release. Borrow and release the result...
var r as result of Response to HttpError is calling petitio.get with url
defer banish r
if not r.is_ok:
    return 1
var resp as Response is r.value          # borrowed copy: do not banish
calling spark.println_int with resp.status

# ...or move the payload out and release each half independently.
var box as result of Response to HttpError is calling petitio.get with url
defer banish box
if not box.is_ok:
    return 1
var owned as Response is calling petitio.take_response with (sigil of box)
defer banish owned
```

`r.value` / `r.error` hand out a shallow copy of the payload box; the box still
owns the strings. Releasing the copy and the result frees the same buffers twice.
Use `take_response` / `take_error` when the value must outlive the result scope:
they clear the box so the two releases are independent.

### 14.43 Compressing data that is already compressed

```pengu-invalid
# ❌ Anti-Pengunic: a JPEG/PNG/MP4/ZIP/.gz payload is already compressed.
# Gzip can only add a header and a trailer; the output is *larger* and the
# CPU is spent for nothing.
var packed as result of string to CompressError is calling compressus.gzip_compress with jpeg_bytes, CompressionLevel.Best
```

```pengu
# ✅ Pengunic: compress once, at the source, and pass the bytes through.
# Check the magic instead of guessing from the file extension.
var kind as maybe CompressionFormat is calling compressus.detect_format with payload
if kind is present:
    # Already gzip or zlib: store it as-is, do not re-compress.
    calling archivum.write_bytes with path, payload
else:
    var packed as result of string to CompressError is calling compressus.gzip_compress with payload, CompressionLevel.Default
    defer banish packed
    if packed.is_ok:
        calling archivum.write_bytes with path, packed.value
```

Compression ratios come from *redundancy*. Text, JSON, logs, source code and
uncompressed media have plenty; JPEG, PNG, MP4, ZIP and gzip have already had it
removed. Double compression also defeats content-addressed caches and checksums:
the same image re-encoded at a different moment produces different bytes.

---

### 14.44 One-shot for files over ~100 MB

```pengu-invalid
# ❌ Anti-Pengunic: read 8 GiB, allocate 8 GiB, compress into another 8 GiB.
# Peak memory is input + output and the allocator will fail before the file ends.
var r as result of int to CompressError is calling compressus.gzip_compress_file with "huge.tar", "huge.tar.gz", CompressionLevel.Best
```

```pengu
# ✅ Pengunic: split the input into independent gzip members and concatenate.
# Every reader (gzip -d, Python, std.compressus) accepts a multi-member file,
# and the output side stays bounded by one chunk instead of the whole archive.
var source as maybe string is calling archivum.read_bytes with "huge.tar"
if not (source is present):
    return 1
var whole as string is source.value
var out as StringBuilder is calling StringBuilder.new
defer banish out
var offset as int is 0
while offset < (whole length):
    var stop as int is offset + 8388608          # 8 MiB per member
    if stop > (whole length):
        set stop is whole length
    var chunk as string is calling scrolls.substring with whole, offset, stop
    var piece as result of string to CompressError is calling compressus.gzip_compress with chunk, CompressionLevel.Default
    if piece.is_ok:
        calling out.append with piece.value
    banish piece
    banish chunk
    set offset is stop
var joined as string is calling out.finish
calling archivum.write_bytes with "huge.tar.gz", joined
banish joined
banish source
```

The file helpers (`gzip_compress_file`, `gzip_decompress_file`) are convenience
wrappers: they read the whole file and write the whole result. That is fine for
a configuration file or a source tarball, and wrong for a disk image. The
threshold is not a hard rule — measure the peak memory of *your* workload — but
~10 MB is where chunking starts to pay and ~100 MB is where one-shot stops being
defensible. A first-class streaming API is scheduled for 2.14.1.

---

### 14.45 Ignoring the checksum of transported data

```pengu-invalid
# ❌ Anti-Pengunic: "it decompressed" is not "it is the file we asked for".
# A truncated download or a proxy that swapped the body can still produce a
# shorter, valid-looking gzip stream.
var r as result of string to CompressError is calling compressus.gzip_decompress with downloaded
calling spark.println with r.value
```

```pengu
# ✅ Pengunic: verify the checksum from the manifest before using the bytes.
var r as result of string to CompressError is calling compressus.gzip_decompress with downloaded
defer banish r
if not r.is_ok:
    return 1
var actual as u32 is calling compressus.crc32 with r.value
if actual != expected_crc32:
    calling spark.eprintln with "checksum mismatch: refusing to install"
    return 1
# ... only now write the file or extract the archive ...
```

The gzip and zlib trailers protect the *transport* of one stream: a corrupt
body is `Corrupt`, not silent garbage. They do **not** prove that the stream is
the artefact you asked for. A dependency manifest must carry its own checksum
(SHA-256 in `pengu.lock`; CRC-32 is a fast first line, not a security boundary).
Verify before you execute, extract or overwrite anything.
