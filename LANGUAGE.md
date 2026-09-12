# PenguScript Language Reference

> **Version covered:** 0.9.x (C99/C11 code generator; runtime headers under `pengu_runtime.h`).
> This is the definitive syntax & semantics guide, written against the compiler
> sources (`pengu_grammar.py`, `pengu_checker.py`, `pengu_codegen.py`,
> `pengu_infer.py`, `pengu_runtime.h`). It complements the quick
> [`CHEATSHEET.md`](CHEATSHEET.md) and explains every feature with PenguScript
> examples and, where relevant, the generated C.

---

## Table of contents

1. [Introduction & principles](#1-introduction--principles)
2. [Quick start](#2-quick-start)
3. [Lexical structure](#3-lexical-structure)
4. [Type system](#4-type-system)
5. [Variables, constants & scope](#5-variables-constants--scope)
6. [Operators & expressions](#6-operators--expressions)
7. [Control flow](#7-control-flow)
8. [Functions](#8-functions)
9. [Composite types](#9-composite-types)
10. [Methods, concepts & binding](#10-methods-concepts--binding)
11. [Generics](#11-generics)
12. [Optionals & errors](#12-optionals--errors)
13. [Memory & pointers](#13-memory--pointers)
14. [Modules, imports & C interop](#14-modules-imports--c-interop)
15. [Literals: strings, arrays, maps, indent blocks & ranges](#15-literals-strings-arrays-maps-indent-blocks--ranges)
16. [Conditional compilation (`when`)](#16-conditional-compilation-when)
17. [Unit tests (`test`)](#17-unit-tests-test)
18. [Block-style construction (`with:` expressions)](#18-block-style-construction-with-expressions)
19. [Standard library](#19-standard-library)
20. [Tooling & project layout](#20-tooling--project-layout)
21. [Complete example](#21-complete-example)

---

## 1. Introduction & principles

PenguScript is an indentation-sensitive, statically typed language that
compiles directly to C99/C11. Its design rules:

- **One keyword per task.** Reserved words are semantic (`weave` for
  functions, `rune` for structs, `omen` for enums/sum types, `calling` for
  calls, `set` for assignment, `banish` for explicit free, …).
- **Explicit over hidden.** Memory is *not* garbage collected: heap values are
  freed explicitly with `banish`, deferred with `defer`/`errdefer`. Ownership
  of every runtime helper is documented in `pengu_runtime.h`.
- **Compile-time friendly.** `const`, generic monomorphization (`shard`),
  `when` compile-time branching and constant folding happen before C is
  emitted.
- **C is the target *and* the boundary.** `declare`/`include`/`link` make any C
  library usable; `rune`/`echo` map 1:1 to C `struct`/`union`; opaque C
  handles are `opaque` types.

> [!NOTE]
> The compiler pipeline is: Lark grammar → `PenguParser` → `PenguChecker`
> (two passes: collect top-level definitions, then validate statements) →
> `TypeInferrer`/`ConstFolder` → `PenguCodegen` (C text). A compiled artifact
> is a single C file (`bundle.c`) linked against `libpengu_runtime.a`.

---

## 2. Quick start

```pengu
# hello.pengu  — a standalone script
weave main into int:
    calling print with "Hello, Pengu!\n"
    return 0
```

```console
$ pengu run hello.pengu          # build + execute a loose script
$ pengu run                      # build+run ./pengu.yaml project target
$ pengu build                    # compile project (default output exe)
$ pengu check                    # parse + type-check every module, no C
$ pengu test                     # compile & run the project's `test` blocks
$ pengu fmt                      # format .pengu files
$ pengu doc                      # emit Markdown from ## comments
$ pengu bind header.h            # generate a .d.pengu binding from a C header
$ pengu lsp                      # launch the language server (pygls)
```

> [!IMPORTANT]
> The entry `weave` must be named `main` for executables. The generated C
> function is `pengu_main`; `main` itself is reserved as a compile-time
> variable (see [`when`](#16-conditional-compilation-when)).

---

## 3. Lexical structure

### 3.1 Files

| File | Purpose |
|------|---------|
| `*.pengu` | Source module (may contain implementation bodies). |
| `*.d.pengu` | Declaration-only module (bindings). Implementation bodies are an error (`E0025`). Mirrors TypeScript `.d.ts`; no C is emitted for its types. |
| `std/*` | Standard library modules (wrapper modules or `*.d.pengu` bindings). |

### 3.2 Comments & docs

```pengu
# line comment
## doc comment (used by `pengu doc` and hover/extraction)
# banner --------------------------------------------
```

Both `#` and `##` are collected as documentation when they appear directly
above a declaration; `##` is the preferred docstring marker.

### 3.3 Identifiers & visibility

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Style: `snake_case` for values,
`PascalCase` for type names.

- A leading underscore (`_private`, `_secret_field`) makes the symbol
  **private to its module or rune**: cross-module/rune access raises `E0043`.
- `_` alone is the **discard binding** (`for _, v in col`), never a variable.
- `main` is reserved: you cannot `var main`, `let main`, `static var main`, or
  `const main` (`E0040`) — but you *define* the entry as `weave main …`.

### 3.4 Reserved words

`import include link insignia const var let set static weave declare enchanting
rune echo omen alias seal concept bind shard where when test ritual inline if
unless else while for in from to step judge calling with into as is many return
break continue defer errdefer banish some ord chr bytes of essence of sigil of
transmute size of try defined not and or lambda null true false maybe none error`

`frozen` is a **soft** keyword: it only acts in type position
(`frozen T`, `ref to frozen T`); identifiers named `frozen` keep working
everywhere else. See [§9.5](#95-frozen--read-only-qualification).

---

## 4. Type system

### 4.1 Primitive types

| Pengu | C (typical) | Size (bits) | Notes |
|-------|-------------|-------------|-------|
| `int` / `i32` | `int32_t` | 32 | default integer |
| `i8`/`i16`/`i64` | `int8_t`/`int16_t`/`int64_t` | 8/16/64 | |
| `u8`/`byte` | `uint8_t` | 8 | `byte` aliases `u8` |
| `u16`/`u32`/`u64` | `uint16_t`/… | 16/32/64 | |
| `usize`/`isize` | `size_t`/`ssize_t`-ish | pointer width | used for C sizes |
| `float`/`f64`/`double` | `double` | 64 | default float |
| `f32` | `float` | 32 | |
| `bool` | `bool` | 8 | `true`/`false` |
| `char` | `char` | 8 | single C byte |
| `string` | `PenguString` | runtime | see 4.2 |
| `void` | `void` | – | no value |

Integer literal suffixes and `to` casts are available (`1.5 to int`, `x to
string`). `size_t`, `int8_t`… spellings are accepted as type aliases.

### 4.2 Runtime containers

| Pengu | Runtime C type | Layout summary |
|-------|----------------|----------------|
| `string` | `PenguString` | `{ char *data; int len; }` |
| `slice of T` | `PenguSlice` | `{ void *data; int len; size_t elem_size; }` |
| `list of T` | `PenguList` | `{ void *data; int len; int cap; size_t elem_size; }` |
| `map of K to V` | `PenguMap` | hash map with deep-copied entries |
| `maybe T` | `PenguMaybe` | `{ bool is_present; void *value; }` |
| `result of T to E` | `PenguResult` | `{ bool is_ok; void *ok_val; void *err_val; }` |
| `range` (`a to b`, `a..b`) | `PenguRange` | `{ int64_t start; int64_t end; }` |

`PenguString` is a (length, pointer) pair; string literals used at runtime are
heap-allocated owning buffers (`pengu_string_new`), while `pengu_string_from_cstr`
returns a non-owning view.

### 4.3 Composite & user types

- `rune Name:` — C `struct` (records), see [§9.1](#91-rune-structs).
- `echo Name:` — C `union` (tagged union *without* runtime tag), [§9.2](#92-echo-unions).
- `omen Name:` — C `enum` or tagged `struct` (algebraic data type), [§9.3](#93-omen-enums--algebraic-data-types).
- `seal Name as T` — distinct newtype requiring explicit casts, [§9.4](#94-seal--alias--opaque).
- `alias Name as T` — transparent type alias, [§9.4](#94-seal--alias--opaque).
- `opaque` — C opaque handle (`void*`-ish; usable via `ref to`), [§9.4](#94-seal--alias--opaque).
- `ref to T`, `array of T with size N`, `array of array of T with size M with size N`
  (C `T[M][N]`, outer dimension first — see §15.3), `list of T`, `slice of T`,
  `map of K to V`, `maybe T`, `result of T to E`, `fn`/weave-pointer types.
- `frozen T` — read-only qualification (C `const T`) usable on any of the
  above as a **type modifier**, [§9.5](#95-frozen--read-only-qualification).

> [!NOTE]
> Sizes shown by the LSP hover come from the compiler's `estimate_size`;
> struct sizes include padding the way C lays the structs out.

---

## 5. Variables, constants & scope

### 5.1 Declarations

```pengu
const ANSWER as int is 42                 # top-level compile-time constant
static var cache as int is 0              # function-static state (kept across calls)
var count as int is 0                     # mutable local (only inside functions)
let name as string is "Ada"               # immutable local binding
let a, b is pair_value                    # destructuring a rune into its fields
```

- `const` is top-level only (`E0001` inside functions). Values are folded and
  emitted as C constants.
- `var`/`let` are forbidden at top level (`E0002`) to keep global state
  read-only (V-safety).
- `set` reassigns a mutable variable/field (`E0006` if immutable).

```pengu
var x as int is 1
set x is x + 1
```

#### Compound assignment

`set` also accepts the compound operators `+= -= *= /= %= &= |= ^= <<= >>=`:

```pengu
set counter += 1
set total -= fee
set acc *= factor
set acc /= n
set mask <<= 2
set flags |= 0x08
set text += " suffix"      # string concatenation
```

| Operator | Allowed types | Notes |
|---|---|---|
| `+=` | numeric, `string` | on `string` it concatenates (`pengu_string_concat`) |
| `-=` `*=` `/=` `%=` | numeric | `%` is integer-only, as in `%` |
| `&=` `\|=` `^=` `<<=` `>>=` | integers | bitwise/shift; `E0005` on non-integers |

The left-hand side follows the normal `set` rules: it must be mutable (`E0006`
otherwise) and may be a plain variable, a field, or a `.field` inside a `with`
scope. Type errors are `E0005` (e.g. `set s += 1` where `s` is a `string`, or
`set b &= true` where `b` is a `bool` — use `and`/`or` for booleans).

### 5.2 Scope

Scopes are delimited by indentation: weave bodies, `if`/`while`/`for`
branches, `with` blocks, `or:` blocks, etc. Lookup is lexical; a name declared
in an inner scope shadows outer ones. `banish`/`defer`/`errdefer` are only
allowed inside function bodies (`E0008`).

### 5.3 Visibility recap

Public by default; `_`-prefixed symbols are module/rune private. There is no
`pub` keyword (removed in 0.9.1): the leading underscore is the single
mechanism.

---

## 6. Operators & expressions

### 6.1 Precedence (loosest → tightest)

1. `or else`, `or return`, `or:` blocks, then `try`
2. `or` (boolean, short-circuit)
3. `and` (boolean, short-circuit)
4. `judge … when … -> … else -> …`, `if … then … else …` (expressions), `when … then … else …`
5. comparisons `== != <= >= < >`, word tests `is present`, `is not present`,
   `is true`, `is false`
6. `|` `&` `^` bitwise
7. shifts `<< >>`
8. additive `+ -`
9. multiplicative `* / %`
10. unary `~ not -`, `sigil of`, `essence of`, `transmute … to`, `size of`,
    `banish`, `some`, `ord`, `chr`, `bytes of`
11. postfix `at`, slicing `at a to b`, `length`, `.field`, `->field`, cast `to`
12. atoms: literals, `calling`, `with` init/struct-init, containers, `defined(…)`,
    `lambda … into …`

Everything left-associative. `or` binds looser than `and`, so
`a or b and c` is `a or (b and c)`. `and`/`or` are **boolean** operators
(short-circuit); `&`/`|` remain **integer bitwise** operators.

> **`at` is postfix and takes a single atom as its index.** Since level 11 binds
> tighter than additive `+ -` (level 8), the index is one operand and a *computed*
> index needs parentheses:
>
> ```pengu
> xs at i + 1          # (xs at i) + 1 — arithmetic on the element
> xs at (i + 1)        # the element at index i + 1
> set xs at (n - 1) is 77      # assignment targets too
> ```
>
> `set xs at n - 1 is 77` is a syntax error (`E0000`) whose message says so
> explicitly. The same rule applies to slices (`arr at a to b`), `length`,
> `.field`/`->field` and casts.

> **BREAKING CHANGE (0.10.0):** `and` is no longer a list separator next to
> expressions. Use `,` in call arguments, `weave`/`declare` parameters,
> struct-init literals, array/map literals and indented literals
> (`calling f with 1, 2`, `weave g with x as int, y as int`,
> `with x is 1, y is 2`). Writing the old separator is a parse error
> (`E0000`) that points at the offending `and`. `and` still separates the
> lists that can never hold an expression — `shard T and U`, concept bounds
> (`where T: A and T: B`), omen payloads, generic arguments
> (`Box of int and string`) and function-**type** parameters
> (`weave with x as int and y as int into int`) — although `,` works there
> too. In `map of K to V` the separator is `to`.
>
> **Nota de migración interna:** la stdlib (`std/`) y la suite de
> tests del repositorio **ya están migradas** a la sintaxis con comas en
> esta misma versión (725 separadores en `std/`, más los programas de
> `tests/` y las fuentes Pengu embebidas en `tests/*.py`). Además,
> `lambda` pasa a ser palabra reservada: `std/lot.pengu` renombró su
> parámetro `lambda` a `rate`.

### 6.2 Arithmetic & bitwise

```pengu
let z as int is (a + b) * 2 % 7
let f as float is 1.5
let bits as int is (x << 2) | (y & 0x0F)
let neg as bool is not ready
let flip as int is ~mask
```

String `+` concatenates (emits `pengu_string_concat`); comparing strings with
`==`/`!=` uses content equality (`pengu_string_equal`).

#### Logical operators (`and` / `or`)

```pengu
if a > 0 and b > 0:
    calling print with "both positive\n"

if ready or (retry < 3):
    calling print with "go\n"

let ok as bool is not (paused or full) and retries < 3
```

- `and` / `or` are **boolean-only** and **short-circuit**: `or` evaluates its
  right side only when the left is `false`, `and` only when the left is `true`.
  Both emit `&&` / `||` in C.
- Operands must be `bool`; anything else is `E0005` (with a hint to use `&`/`|`
  for bitwise work).
- `not` is the boolean negation (`!`); `~` is bitwise.
- Precedence: `or` < `and` < comparison, so `x > 0 and y > 0 or z` is
  `((x > 0 and y > 0) or z)`.
- `&`/`|`/`^` stay **integer** bitwise operators (`&`/`|` on `bool` is `E0005`).
- Because `and` is now an operator, it is no longer accepted as a separator
  where an operand could be an expression — see the migration note in §6.1.
- A bare `and`/`or` is **not** an element of a comma-separated list. Array, map
  and indented literals (`[1 and 2]`, `{"k": a and b}`) and parameter defaults
  fail to parse (`E0000`), and a bare `and`/`or` glued to a call with arguments
  (`calling find with 1 and true`) or a struct literal (`with flag is a and b`)
  is `E0005` *Ambiguous 'and' after …* — those are exactly the shapes where the
  old separator was written, and the boolean reading stays valid whenever both
  operands are `bool`. Parenthesise the boolean value instead:

  ```pengu
  var xs as array of bool with size 1 is [(a and b)]
  var v as Vec is with flag is (a and b)
  var ok as bool is (calling find with 1) and true
  ```

  Everywhere a single value is expected the operators work unparenthesised
  (`if a and b:`, `var ok as bool is a and b`, `return a or b`).

### 6.3 Comparison, membership & word tests

```pengu
if x > 0: ...
if m is present: ...          # m must be 'maybe T'; anything else is E0005
unless m is present: ...
if b is true: ...
if ch in "aeiou": ...
if key in my_map: ...
```

`in` / `not in` work on ranges, strings, slices, arrays, lists and maps.
`a in b to c` checks membership in a half-open range.

`is present` / `is not present` inspect the flag of a `maybe T` value and
return `bool`; applying them to any other type is `E0005`. The same holds for
`is true` / `is false` on `bool`.

A word test applies to the expression on its **left**, and the argument list of
`calling` is greedy, so a bare test in an argument list is rejected as
ambiguous (`E0005`). Spell out which reading you mean:

```pengu
calling print_bool with (m is present)        # pass the test as the argument
if (calling find_user with 1) is present:     # test the call's result
if calling ready is true:                     # no arguments: unambiguous
```

### 6.4 Address, dereference & size

```pengu
var p as ref to int is sigil of x     # &x
var v as int is essence of p          # *p
let n as usize is size of MyRune      # sizeof
```

- `sigil of expr` requires an addressable value.
- `essence of ref` dereferences.
- `transmute x to T` is an unsafe bit reinterpretation (warning `W0001`); use
  `to` for safe casts.
- `to` casts: `(int64)`, `(float)`, `(string)` conversions, etc.
  `10 to float` is a cast; `1 to 10` is a range (context decides).

### 6.5 Character & byte primitives

```pengu
let code as int is ord "A"      # 65
let ch as string is chr 66      # "B"  (single character)
let raw as ref to byte is bytes of text
```

- `ord` requires exactly one byte/character (`E0005` otherwise).
- `chr` requires a byte value in range.
- `bytes of` yields a read-only byte view of a `string`, `array of byte`, or
  `ref to byte` buffer; used heavily in C interop (see §14).

### 6.6 `maybe` constructors & error literal

```pengu
var m as maybe int is some 42
var n as maybe int is maybe none
# inside an or: block the current failure is bound to `error`
let v is calling may_fail with x or:
    let e is error
    ...
```

---

## 7. Control flow

### 7.1 `if` / `unless` (statements) and `if`-expressions

```pengu
if score >= 100:
    calling print with "winner"
else:
    calling print with "keep going"

unless muted:
    calling play_sound with "beep"

let label as string is if x > 10 then "big" else "small"
```

`unless cond:` is `if !cond:`. Conditions must be `bool` (`E0005` otherwise).
Branches with compile-time constant conditions are folded and the unreachable
branch is eliminated (warning `W0004` for unreachable code).

An `if` or `unless` whose branches are indented blocks can also be used as a
**value** when it sits in a value position — see [§7.6](#76-block-expressions-do-value-position-if--unless-and-loops).

#### `if` bindings: `if v as T is <maybe>:`

An `if` condition may bind the value held by a `maybe` and run the branch only
when it is present:

```pengu
weave describe with user as maybe User into string:
    if u as User is user:               # u is User inside the branch
        return u.name
    else:
        return "anonymous"
```

- The operand must be `maybe T` — anything else is `E0005` (`Binding 'u'
  requires a maybe value, got 'int'`).
- `T` must match the element type of the maybe (`E0005` otherwise).
- A redundant trailing `is present` is accepted and means the same thing
  (`if u as User is user is present:`); `is not present` combined with a binding
  is rejected, because a binding already implies presence.
- It works in value position too: `let label is if u as User is user: u.name
  else: "anonymous"`.

The binding lowers to a scoped C block that evaluates the maybe **once**, tests
its presence flag and copies the value out of the heap cell — the bound name
does not leak into the `else` branch or past the `if`.

A branch may also hold a **single statement on the same line**; it is sugar for
an indented one-statement block and behaves identically (same C, same checks):

```pengu
if x == 1: return 1
unless x == 0: calling print with "non-zero"
while i < n: set i is i + 1
for j from 0 to 3: calling tick with j
```

### 7.2 `while`

```pengu
var i as int is 0
while i < 10:
    calling tick with i
    set i is i + 1
```

### 7.3 `for`

```pengu
for i from 0 to 10:            # integer range, end-exclusive
    calling print with (i to string)

for item in items:             # array / list / slice / string / map iteration
    calling handle with item

for i, item in indexed:        # indexed form (i is the C loop counter)
for _, v in values:            # discard index
for j from 5 to 0 step -1:     # negative step
```

String iteration yields each character as a single-character `PenguString`
(via `pengu_string_char_at`).

Comprehension:

```pengu
let squares is for x in nums then x * x
let evens  is for x in nums when x % 2 == 0 then x
```

### 7.4 `judge` — pattern matching

```pengu
let state_desc is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done with result is 200 -> "done-200"
    when Done -> "done"
    else -> "unknown"
```

- Works on `omen`s (variants), integers and strings.
- On an `omen`/`bool` subject without an `else ->` the checker enforces
  **exhaustiveness** (`E0044`).
- Compiles to a C `switch` over integer enums, or to a ternary chain for
  non-integer matches.

### 7.5 `break` / `continue` / `return`

Standard semantics; `break`/`continue` only inside loops (`E0007`). `return`
must match the weave's declared `into` type (`E0020`); bare `return` is only
valid in `void` weaves.

### 7.6 Block expressions: `do:`, value-position `if` / `unless`, and loops

An indented block can supply a value:

```pengu
let x is do:                      # a do: block evaluates to its last statement
    var a is 10
    set a is a + 5
    a * 2                         # x == 30

let status is if score >= 100:    # an if in a value position yields a branch value
    let msg is "winner"
    msg
else:
    let msg is "keep going"
    msg

let fallback is unless score > 0: # unless is the mirror image
    "zero or less"
else:
    "positive"

let squares as list of int is for i from 0 to 5:
    i * i                         # a loop collects its body's value per iteration

let steps as list of int is while n < 100:
    set n is n * 2
    n
```

- `do:` runs its statements in a fresh local scope; `var`/`let` declared inside
  do not escape. The block's value is its **last statement's value** — an
  expression, or a trailing value-position `if`/`unless`/loop.
- `if`/`unless` supply a value when they appear in a **value position**. Every
  branch must end with an expression and all branches must share one **common
  type**; mixing a value branch with a value-less branch, or incompatible branch
  types, is `E0005`. (`unless` is the mirror: the then-branch runs when the
  condition is false.) Anywhere else they are ordinary statements (unchanged).
- **Loops** (`while`, `for i from a to b [step s]`, `for v in col`,
  `for i, v in col` — all of them) supply a value too: a loop in a value position
  **collects** its body's last expression on every iteration into a `list of T`.
  The body must produce a value on each iteration (`E0005` otherwise);
  `continue` skips that iteration's value and `break` ends the loop. A loop in
  statement position is unchanged.
- Value positions:
  - initializers: `var` / `let` / `static var`
  - `set` targets (including `set .field is …` inside a `with:` builder)
  - `return` values — `return if c: …`, `return unless c: …`, `return for …: …`
  - call arguments (positional and `name is <block>`) and struct-literal fields
    (`with x is <block>, y is <block>`)
  - the last statement of a value block (`do:`, an `if`/`unless` branch, a loop
    body) — which is why these forms nest recursively
  Block forms are **not** allowed inside operators, parentheses, array/map
  literals, conditions or iterables: `1 + if c: …`, `(for …: …)`, `[if c: …]`
  and `for v in for …:` are parse errors. Use the expression forms
  (`if … then … else`, `for … then …`) or bind to a variable first.
- Chains: `else if <cond>:` and `else:` followed by an indented nested
  `if`/`unless` are both accepted, because a block's value is its last
  statement's value:

```pengu
let tag is if n < 5:
    n
else if n < 10:          # or: else: + an indented if (same semantics)
    n * 2
else:
    n * 3

let other is unless n > 5:
    n
else:
    unless n > 10:       # nested block values compose recursively
        n * 2
    else:
        n * 3
```

- Building collections of runes works with the `with:` builder inside the loop:

```pengu
var points as list of Point is for i from 0 to 3:
    var p as Point with:
        set .x is i
        set .y is i * 2
    p                    # each iteration appends a Point

var more as list of Point is for i from 0 to 3:
    with:                # the builder itself is the iteration value: the target
        set .x is i      # type comes from the element type ('Point')
        set .y is 7
```
- Value-ness is decided by **position**, not by a second syntax: `if cond:` +
  block is token-identical as a statement and as a value, so each keyword has a
  single grammar rule and the checker/codegen treat the node as a value only in a
  value slot. Statement semantics — binding conditions, constant folding,
  `W0004` unreachable-code warnings, loop control — are unchanged.
- Blocks compile to a GNU statement-expression (with a typed temporary assigned
  per branch, or a `PenguList` for loops), so they compose with each other, with
  the `with:` builder (§18) and with struct literals.

> [!NOTE]
> The block-expression family is complete: `do:`, value-position `if`/`unless`
> and value-position loops. `judge` and the `for … then` comprehension were
> already expressions. Remaining ideas (not implemented): block forms inside
> operators/brackets, `break <value>`, and a `from … to … then` comprehension.
> CHEATSHEET §6.1.4 has the definitive list of what is and is not an expression.

---

## 8. Functions

### 8.1 `weave` — functions

```pengu
weave greet with name as string, times as int is 1 into void:
    for i from 0 to times:
        calling print with "Hi " + name

weave double with x as int into int:
    return x * 2
```

- Parameters may have **default values** (`times as int is 1`).
- A body whose last expression is a value returns it implicitly
  (`weave double with x as int into int:\n  x * 2`).
- `calling` invokes:
  - positional: `calling greet with "Ada", 3`
  - named: `calling greet with name is "Ada", times is 2` (`arg: NAME "is" expr`)
  - module member: `calling spark.println with "x"`
  - object method: `calling player.move with 5, 3`

  A `calling … with …` expression used as an **operand** must be parenthesised,
  because the argument list is greedy: `calling raygui.Button with bounds, "ok" == 1`
  compares the *argument* `"ok"` with 1, while
  `(calling raygui.Button with bounds, "ok") == 1` compares the call's result.

```pengu
weave sum_many with values as many int into int:   # variadic
    var acc as int is 0
    for v in values:
        set acc is acc + v
    return acc

weave inline fast with x as int into int:          # always-inline in C
    return x + 1
```

- `many T` is the variadic parameter type (`E0023`/`E0024` misuse checks).
- The `inline` weave modifier emits `static inline __attribute__((always_inline))`.

### 8.2 `declare` — external C functions

```pengu
declare pengu_print with s as string into void
declare strlen_c with s as ref to char into usize
declare my_callback with cb as ref to weave with x as int into void into void
declare printf with fmt as ref to frozen char, ... into int     # C varargs
```

`declare` registers the signature so `calling name with …` translates to a
direct C call with the declared C name (see §14).

**C variadic functions.** A trailing `...` after the last fixed parameter marks a
C variadic function (`printf`, raylib's `TextFormat`/`TraceLog`, sqlite3's
`mprintf`). The fixed parameters keep their declared type and are type-checked;
the extra arguments are passed through **verbatim** — no `PenguSlice` packing, no
type checking — so C's default argument promotions apply, exactly as in C:

```pengu
declare printf with fmt as ref to frozen char, ... into int
declare TextFormat with text as ref to frozen char, ... into ref to frozen char

calling printf with "%d-%d\n", 4, 2
calling raylib.DrawText with (calling TextFormat with "Score: %08i", score), 200, 80, 20, raylib.RED
```

Rules and caveats:

- The minimum argument count is the number of fixed parameters; there is no
  maximum (`calling printf with fmt` alone is valid C and valid here).
- Extra arguments get **no** expected type, so a runtime `string` must be spelled
  `bytes of s` (or `ffi.cstr_from_string with s`) when a C `char*` is wanted; a
  string *literal* is already emitted as a C literal.
- Because the extra arguments are unchecked, a wrong format specifier is a C-level
  bug, not a PenguScript error — the same trade-off C makes.
- A function that is only reachable through `include` (no `declare` in scope) is
  *not* known to the checker: `calling printf with "%d", 1` type-checks and then
  fails in C. Declare it (as above) to get correct codegen.

Only `declare` accepts `...`; `weave` bodies, `alias … as ref to weave with …`
callback types and `shard` generics use `many T` (§8.1) instead, which *is* typed.


### 8.3 Function pointers & callbacks

A function-pointer value has type `weave … into …`; a declared
`ref to weave … into …` (or an alias of it) is the same thing, because a
function value decays to a pointer in C. Both spellings are interchangeable:

```pengu
alias Handler as weave with x as int into void

weave handler with x as int into void:
    return

weave main into void:
    var cb as ref to weave with x as int into void is handler   # or 'as Handler'
    calling register_cb with handler                            # C callback parameter
    calling cb with 1                                           # call through the pointer
```

**C callbacks.** Bindings declare the callback typedef from the C header, so
passing a Pengu weave to a C API works directly:

```pengu
import std.raylib

weave on_audio with buffer as ref to void, frames as u32 into void:
    return

weave main into int:
    var stream as raylib.AudioStream is calling raylib.LoadAudioStream with 44100, 32, 2
    calling raylib.SetAudioStreamCallback with stream, on_audio
    calling raylib.UnloadAudioStream with stream
    return 0
```

The compiler **casts the function value to the declared callback type**
(`((AudioCallback)on_audio)`). That is what makes headers whose prototypes carry
qualifiers the `.d.pengu` binding cannot express — `const char*` in raylib's
`TraceLogCallback`, for instance — compile under GCC 14+.

Two things worth knowing:

- A callback parameter written **inline** (`compar as ref to weave with a as ref
  to frozen void, b as ref to frozen void into int`) is cast to the type spelled
  by those Pengu parameters, so spell the qualifiers the C prototype uses: with
  `ref to frozen void` the cast is `(int32_t (*)(const void*, const void*))` and
  `qsort` compiles directly (see [§9.5](#95-frozen--read-only-qualification)).
  Spelling mutable `ref to void` for a `const void*` prototype still makes GCC 14+
  reject the cast — fix the spelling rather than adding a C shim. Callbacks
  declared through an alias of a C typedef are unaffected, because the cast names
  the typedef.
- `va_list` exists as a parameter type (it is emitted verbatim) for callbacks such
  as raylib's `TraceLogCallback`, and C variadic functions themselves are declared
  with a trailing `...` and called normally ([§8.2](#82-declare--external-c-functions)).

### 8.4 Lambdas

Anonymous functions are written with `lambda`, typed parameters (comma
separated) and `into` for the body:

```pengu
lambda into 42                            # no parameters
lambda x as int into x * 2                # one parameter
lambda a as int, b as int into a + b      # several parameters
```

```pengu
weave apply with f as weave with x as int into int, v as int into int:
    return calling f with v

weave main into int:
    let double is lambda x as int into x * 2
    var f as weave with x as int into int is lambda x as int into x + 1

    var a as int is calling double with 21          # 42
    var b as int is calling f with 9                # 10
    var c as int is calling apply with double, 5     # 10
    return 0
```

- **Parameters require explicit types** (the language is statically typed); the
  **return type is inferred** from the body.
- **There is no capture.** A lambda body only sees its own parameters plus
  module-level symbols (weaves, constants, types) — it cannot read locals of the
  enclosing function. That is what lets the compiler emit a plain top-level
  `static` C function (no GCC nested functions, portable C99).
- A lambda value has a `weave … into …` (**`FnType`**) type, so it can be
  stored in a `var`/`let` (with or without that annotation), passed as an
  argument where a callback/`weave` parameter is expected, and called through
  (`calling f with v`).
- Compiles to one `static` function per lambda, named `_pengu_lambda_N`, emitted
  between the prototypes and the function definitions; the expression itself
  evaluates to the function's name (a function pointer in C).
- Lambdas are not usable at compile time (`when`/`defined` contexts) — a lambda
  is a runtime value.
- A lambda can be stored in a variable typed with a callback alias
  (`alias Handler as weave with x as int into int` +
  `var h as Handler is lambda x as int into x * 2`) as well as with an inline
  `ref to weave … into …` type, and a named `weave` can be used the same way.

### 8.5 `ritual` methods (static)
```pengu
enchanting Vec2:
    weave ritual zero into Vec2:
        return with x is 0.0, y is 0.0

    weave length_sq into float:
        return self->x * self->x + self->y * self->y

weave main into int:
    var origin as Vec2 is calling Vec2.zero     # ritual: called on the TYPE
    var l as float is calling origin.length_sq  # instance method: on the value
    return 0
```

`ritual` methods have no `self` and are invoked on the type name
(`Vec2.zero`); instance enchanting methods receive `self` as `ref to T`
(`self->field`).

---

## 9. Composite types

### 9.1 `rune` — structs

```pengu
rune Player:
    name as string
    hp as int
    is_alive as bool
```

Construction:

```pengu
var p as Player is with name is "Hero", hp is 100, is_alive is true
var q as Player with:                        # block form, see §18
    set .name is "Villain"
    set .hp is 50
```

Field access: `p.name`; through a `ref to Player`: `p->name`. Runes map 1:1 to
C structs, so native layout is preserved across the FFI boundary.

### 9.2 `echo` — unions

```pengu
echo Number:
    i as int
    f as float
```

A C `union`. Field access is unchecked and may alias (warning `W0002`);
usually `omen` (with a tag) is safer for sum types.

### 9.3 `omen` — enums & algebraic data types

```pengu
omen Level:
    One
    Two

omen NetworkState:
    Disconnected
    Connecting with retry as int
    Connected with session_id as string
```

Simple omens compile to C `enum`; algebraic omens compile to a tagged struct
(`{ tag; union { … } data; }`). Variant references accept the simple name
(`One`) or the dotted/full name (`Level.One`, `Level_One`). Duplicate variant
values → `E0027`; **name collisions** between variant names and other global
symbols or built-in types are reported (`E0046`). In `.d.pengu` declaration
files an `omen` mirrors a header enum, so C emits the *bare* variant names
(no `Omen_` prefix) — see §14.

### 9.4 `seal`, `alias`, `opaque`

```pengu
seal UserId as int          # distinct newtype: needs explicit `to` casts
alias Inches as int         # transparent alias: interchangeable
alias Buffer as opaque      # C opaque handle (used behind `ref to`)
```

- `seal` forbids silent mixing with the underlying type (`E0004`/mismatch
  errors unless you cast with `to`).
- `alias` is a pure synonym.
- `opaque` types are passed through pointers (`ref to Opaque`); never allocate
  them by value.

### 9.5 `frozen` — read-only qualification

`frozen` is C's `const`: it marks a value or a pointee as not writable. It is
orthogonal to `let`/`var`, which control whether the **name** can be reassigned.

```pengu
frozen int                      # const int
ref to frozen int               # const int*
frozen ref to int               # alias of 'ref to frozen int'
frozen Player                   # const Player
ref to frozen void              # const void*   ← what qsort asks for
```

`frozen` is a **soft** keyword: it is only special in type position, so a
variable, field or weave named `frozen` keeps working.

#### Assignment

A mutable value flows into `frozen` (as in C); the reverse does not:

```pengu
var x as int is 5
set x is 6                      # OK

var y as frozen int is x        # OK: 'y' is a read-only copy
# set y is 7                    # E0006: cannot write through 'frozen'
```

`let` and `frozen` are orthogonal and compose without conflict:

```pengu
let a as ref to int             # int* const a        (name fixed, pointee writable)
var b as ref to frozen int      # const int* b        (name writable, pointee read-only)
let c as ref to frozen int      # const int* const c  (both)
```

Writing **through** a frozen pointee is rejected too:

```pengu
rune P:
    x as int

weave poke with p as ref to frozen P into int:
    # set p->x is 1             # E0006
    return 0
```

#### Use in C interop

`frozen` exists to describe C signatures that carry `const`. Complete `qsort`
example (sorted output: `1 2 3`):

```pengu
include "stdlib.h"

declare qsort with base as ref to void, nmemb as usize, size as usize, compar as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void

weave compare_ints with a as ref to frozen void, b as ref to frozen void into int:
    let xa is essence of (transmute a to ref to frozen int)
    let xb is essence of (transmute b to ref to frozen int)
    if xa < xb:
        return -1
    if xa > xb:
        return 1
    return 0

weave main into int:
    var xs as array of int with size 3 is [3, 1, 2]
    calling qsort with xs, 3, (size of int), compare_ints
    var i as int is 0
    while i < 3:
        calling spark.println with ((xs at i) to string)
        set i is i + 1
    return 0
```

Generated C:

```c
int32_t compare_ints(const void* a, const void* b);          /* prototype */

int32_t compare_ints(const void* restrict a, const void* restrict b) {
  const int32_t xa = (*(((const int32_t*)(a))));
  const int32_t xb = (*(((const int32_t*)(b))));
  if ((xa < xb)) { return -1; }
  if ((xa > xb)) { return 1; }
  return 0;
}

int32_t pengu_main(void) {
  int32_t xs[3] = { 3, 1, 2 }; /* stack */
  qsort(xs, 3, (sizeof(int32_t)), ((int32_t (*)(const void*, const void*))compare_ints));
  for (int32_t i = 0; i < 3; i++) { spark_println((pengu_to_string((xs[i])))); }
  return 0;
}
```

Without `frozen` the callback would be declared `int32_t (*)(void*, void*)`,
and GCC 14+ rejects handing that to `qsort` (different qualifiers). With
`frozen` the Pengu signature matches the C prototype and the function-pointer
cast is legal. (`restrict` on a parameter does not affect type compatibility;
the array argument decays to a pointer as in C.)

`void` is the catch-all object pointer it is in C, so `ref to void` and
`ref to frozen void` accept a pointer to anything — mutable or frozen — an array
(decay), and a C string *literal* (`char*` → `const void*`), which is emitted as
a C literal:

```pengu
declare UpdateTexture with texture as Texture2D, pixels as ref to frozen void into void
declare XXH64 with input as ref to frozen void, length as usize, seed as u64 into u64

calling UpdateTexture with tex, sigil of pixels     # any T*
var h as u64 is calling XXH64 with "PenguScript", 11, 0
```

Away from `void`, the qualification still drops in one direction only:
`ref to frozen int` where `ref to int` is expected is `E0005`.

> [!NOTE]
> `frozen ref to T` is sugar: it normalises to `ref to frozen T` (pointee
> `const`). PenguScript never emits `T* const` — to freeze the *pointer* itself
> use `let`.

#### What does not change

- `frozen T` has the same size and layout as `T`.
- Inside expressions a `frozen int` behaves as an `int` (arithmetic,
  comparisons, indexing); only writing is restricted. An operation's result is
  a plain value, so `return a + 0` is an `int`.
- `frozen` never appears in literals, only in type annotations.
- Assignability is checked where a value is written (initialisers, arguments,
  `return`, `set`); there is no deeper const-propagation analysis. A frozen
  value that must land in a mutable slot is converted explicitly:
  `var n as int is (a to int)`.

---

## 10. Methods, concepts & binding

```pengu
enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

concept Speaker:
    weave greet with name as string into void
    weave loudness into int

rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with name as string into void:
        return
    weave loudness into int:
        return 1
```

- `enchanting T:` attaches methods to a type (`self` is `ref to T`).
- `concept C:` declares a trait/interface; `bind T with C:` implements it.
  Missing methods → `E0031`; signature mismatches → `E0030`.
- Generic constraints `where T: Concept` (see next section).
- The LSP offers *"Implement missing concept methods"* as a code action inside
  a `bind` block.

---

## 11. Generics

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x

weave swap shard T and U with a as T, b as U into Pair of U and T:
    return with first is b, second is a

weave output shard T where T: Printable with item as T into void:
    calling item.print_me
```

- `shard T` introduces a type parameter (multiple allowed: `shard T and U`).
- Application uses `of`: `Box of int`, `Pair of string and int`.
- `where T: Concept` bounds a parameter to concept-implementing types.
- Generic functions are monomorphized: each concrete call instantiates a
  specialized C function with substituted types.
- Generic `rune`s may appear with `of` in signatures; inference for type
  parameters that only appear in return/container positions is limited (see
  the note in §18’s references) — provide concrete argument types.

> [!IMPORTANT]
> PenguScript has no “turbofish” (`f::<T>`). Type parameters are inferred from
> argument types; when a type only appears in the *result* (e.g. a generic
> container builder) you must give the compiler concrete context, or the check
> fails with “Could not infer type parameter(s)”.

---

## 12. Optionals & errors

```pengu
weave find_user with id as int into maybe string:
    if id == 1:
        return some "Admin"
    return maybe none

weave main into void:
    var user as maybe string is calling find_user with 1

    if user is present:
        let name is user.value          # unwrap only after a presence check
        calling print with name

    let fallback is user or else "Guest"          # value or fallback
    # let u is user or return 0                   # value or early return
    # let f is calling risky() or:                # handle failure with a block
    #     let err is error                        # 'error' is bound here
    #     ...
    # let f2 is try calling risky()               # propagate to the caller
```

Semantics and codegen:

- `maybe T` / `result of T to E` are value containers in C
  (`PenguMaybe`/`PenguResult`). Present values are heap copies inside the
  container.
- `or else` yields the fallback lazily on absence/error (ternary in a GNU
  statement-expression).
- `or return X` returns `X` from the enclosing function on failure.
- `or:` runs a handler block; the failure is bound to `error` (only legal
  inside `or:` → `E0015`).
- `try expr` unwraps and **propagates** to the caller: allowed only inside a
  function whose return type is `maybe T` (for a maybe operand) or a
  compatible `result` (error type must match) — otherwise `E0045`. On failure
  the codegen `return`s `maybe none` / the error result.
- `some v` boxes a value; `maybe none` needs an explicit type context
  (`E0014` otherwise).

```pengu
weave parse_int_or_default with s as string into maybe int:
    return calling parse_int with s      # runtime parse → maybe int

weave load into maybe string:
    let f is try calling open_file with "data.txt"
    return some f
```

`E0020` guards return-type compatibility, `E0045` guards `try` placement.

> [!WARNING]
> `or:` sólo es válido como initializer directo de `var` / `let`
> (`var x is <expr> or: ...`). Usarlo dentro de una expresión más grande
> (`return f() or: ...`, `calling g with (x or: ...)`, `a + (b or: ...)`)
> no está soportado: usa `or else` o `or return`, o extrae el `or:` a una
> variable intermedia.

---

## 13. Memory & pointers

```pengu
var raw as ref to int is sigil of value   # &value
var copy as int is essence of raw         # *raw
defer banish ptr                          # run on scope exit
errdefer banish ptr                       # run only on error return
banish ptr                                # explicit free now
banish str_var                            # free dynamic string (pengu_banish_string)
banish list_var                           # free list allocation (pengu_banish_list)
banish map_var                            # free map allocation and string keys/values (pengu_banish_map)
```

Rules:

- `banish target` accepts an lvalue of type `ref to T`, `string`, `list of T`, or `map of K to V`. Rejects non-lvalues, literals, `const`, and `frozen` (`E0008`).
- `banish ptr` (where `ptr as ref to T`): emits `pengu_banish((void*)(ptr))` to release heap-allocated memory.
- `banish s` (where `s as string`): emits `pengu_banish_string(&s)`. Frees dynamically allocated string heap buffers (`free(s.data)`), sets `s.data = NULL` and `s.len = 0`, emptying the string. Do not access after banishing.
- `banish l` (where `l as list of T`): emits `pengu_banish_list(&l)`. Frees the internal items buffer and resets capacity and length to 0.
- `banish m` (where `m as map of K to V`): emits `pengu_banish_map(&m)`. Frees hash buckets and entries, and automatically frees all `string` keys and `string` values (`pengu_banish_string`), avoiding leaks in dynamic dictionaries.
- `defer`/`errdefer` statements work with `banish` (e.g. `defer banish s`) as well as blocks; execution is LIFO on scope exit (or only on error paths for `errdefer`).
- `ref to T` is passed as a pointer: enables mutation from C and efficient `self` receivers.
- The runtime also ships explicit cleanup bridges for native handles (e.g. `std.filum` `free` methods, `std.regulus.regex_free`, `std.parchment.free_document`, `pengu_precis_free_response`).

> [!WARNING]
> `ref to` pointing at a local value is only valid while that local lives —
> like C. There is no borrow checker; keeping a returned reference to a local
> is user error, not compiler-managed.

### 13.1 Indexing through pointers and borrowing C buffers

A `ref to T` can be indexed directly, in reads and in writes, with the same `at`
operator arrays use (one more reason to prefer `p at i` over pointer
arithmetic):

```pengu
weave fill with p as ref to int, count as int into int:
    for i in 0 to count:
        set p at i is i * 10        # p[i] = i * 10
    return p at 0                   # p[0]

weave main into int:
    var buf as array of int with size 4 is [0, 0, 0, 0]
    calling fill with buf, 4        # arrays decay to 'ref to int'
    return 0
```

- The element type is the pointee: `set p at i is v` through a
  `ref to frozen T` is `E0006`, and `p at i` yields `frozen T` there.
- `ref to void` and `ref to opaque` cannot be indexed (their element size is
  unknown): the error's `help:` suggests `transmute p to ref to T` or a slice
  (below).
- The index must be an integer; it is an additive expression, so `p at n - 1`
  indexes `n - 1` (see the note on `at` in §6.1).

To hand a pointer *and its length* to code that wants a view, use the generic
bridge in `std.ffi` — it works for any element type, including structs:

```pengu
import std.ffi
import std.raylib

weave main into int:
    # any buffer: a local array, or memory handed to you by C
    var pts as array of Vector2 with size 4 is [with x is 1.0, y is 2.0]
    var sl as slice of Vector2 is calling ffi.slice_from_ptr of Vector2 with (sigil of pts), 4
    var total as f32 is 0.0
    for p in sl:
        set total += p.x
    return 0
```

**Pointer arithmetic (`p + 1`) is not part of the language.** Indexing
(`p at i`), slices (`ffi.slice_from_ptr`, `arr at a to b`) and `transmute` cover
the same ground with bounds-carrying or explicit types; use them.

> **Nota:** A partir de 0.10.0, los locales heap-owned se liberan solos al salir de su scope; ver §13.4.

### 13.2 Strict Pointer Typing & Interoperability

PenguScript enforces strict pointee typing for `ref to T` to prevent silent buffer-type mismatches. While numeric values allow widening (`int` → `i64`), pointers require identical pointees (or `void`/`opaque` wildcard).

| Source Pointer (`src`) | Destination Expected (`dst`) | Allowed? | Rule / Note |
|---|---|---|---|
| `ref to T` | `ref to T` | ✅ Yes | Exact pointee match |
| `ref to char` | `ref to frozen char` | ✅ Yes | Mutable flows into frozen (`const`) |
| `ref to byte` | `ref to char` | ✅ Yes | Raw C byte buffer interop (`char*` ↔ `uint8_t*`) |
| `ref to char` | `ref to byte` | ✅ Yes | Raw C byte buffer interop (`char*` ↔ `uint8_t*`) |
| `ref to T` | `ref to void` / `ref to frozen void` | ✅ Yes | Universal wildcard object pointer |
| `array of T with size N` | `ref to T` / `ref to frozen T` | ✅ Yes | Array-to-pointer decay |
| `bytes of s` | `ref to byte` / `ref to char` / `ref to frozen void` | ✅ Yes | String byte storage borrow |
| `ref to frozen T` | `ref to T` | ❌ No (`E0005`) | Const qualifier cannot be dropped |
| `ref to i32` | `ref to char` / `ref to byte` | ❌ No (`E0005`) | Numeric widening does not apply to pointers |
| `ref to u8` | `ref to char` | ❌ No (`E0005`) | Only `char` ↔ `byte` exception is permitted |
| `array of i32 with size N` | `ref to char` | ❌ No (`E0005`) | Pointee mismatch during decay |
| `ref to f32` | `ref to f64` | ❌ No (`E0005`) | Float pointees must match strictly |

### 13.3 Ownership de buffers C

Los bindings C declaran funciones que devuelven punteros asignados por la
propia librería (`LoadAudioStream`, `malloc`, `strdup`, ...). La convención
es:

1. **El binding documenta quién libera.** Los comentarios `##` del binding
   (generados desde el header, o escritos a mano) deben indicar la función
   de liberación correspondiente.

2. **PenguScript no adivina el allocator.** La memoria asignada por una
   librería C debe liberarse con la función de liberación de esa misma
   librería, **no** con `banish`. `banish` sólo libera memoria gestionada
   por el runtime de PenguScript (`pengu_sigil_alloc`, strings, listas,
   mapas).

3. **Patrón recomendado: `defer calling lib_free with p`**

   ```pengu
   import std.raylib

   weave play_and_free into int:
       var stream as raylib.AudioStream is calling raylib.LoadAudioStream with 44100, 32, 2
       defer calling raylib.UnloadAudioStream with stream
       calling raylib.PlayAudioStream with stream
       while (not calling raylib.WindowShouldClose):
           calling raylib.UpdateAudioStream with stream
       return 0
       # 'UnloadAudioStream' se ejecuta al salir del weave.
   ```

4. **`banish` sí funciona para containers de PenguScript.** `banish s`
   (string), `banish l` (list), `banish m` (map) liberan el buffer interno
   del runtime. Un `PenguString` devuelto por una función C que lo asignó
   con `pengu_string_new` sí se libera con `banish`.

5. **Cerrar handles opacos con `defer`.** File descriptors, sockets,
   handles — el mismo patrón:

   ```pengu
   var sock is calling connect_tcp with host, port
   defer calling close_socket with sock
   ```

6. **Errores y `errdefer`.** Cuando una función puede fallar tras adquirir
   un recurso, usa `errdefer` para liberar sólo en la ruta de error:

   ```pengu
   var f is calling open_file with path
   errdefer calling close_file with f
   # ... si algo falla a partir de aquí, close_file corre.
   ```

### 13.4 Scope-owned locals (auto-banish)

Un local declarado sin `borrowed` es **dueño** de su valor heap y se libera
automáticamente al salir de su scope:

```pengu
weave build_greeting with name as string into string:
    var greeting is "Hello, " + name + "!"
    calling print with greeting
    return greeting            # transferencia al caller; NO auto-banish
```

#### Cuándo **sí** se auto-banea

Un local `x` es auto-owned si:

1. Su tipo es `string`, `list of T` o `map of K to V`.
2. Se declara **sin** `borrowed`.
3. Su inicializador **no** es un alias (`var y is x`, `obj.field`, `arr at i`, ni un literal de string puro).
4. No escapa (`return x`, `push x`, `put k, x`, `set obj.field is x`, `sigil of x`).
5. No se reasigna con `set x is ...`.
6. No aparece en un `defer banish x` o `errdefer banish x`.

#### Cuándo **no** se auto-banea

- Tipos escalares (`int`, `bool`, `float`, ...), `ref to T`, `maybe T`, `result of T to E`, runes/echos/omens, `array of T` (stack), `slice of T` (no owning).
- Inicializado con un literal de string puro (`var s is "hi"`): el `PenguString` apunta a `.rodata`, no es owning.
- Declarado `borrowed`.
- Reasignado con `set` en el mismo scope.
- Escapa a un campo, lista, mapa, o es retornado.

#### Escapes reconocidos

- `return x` (donde `x` es `string`/`list`/`map`) → **transferencia**.
- `calling lst.push with x` (o `append`) → escape.
- `calling m.put with k, x` (o `insert`/`set`) → escape.
- `set obj.field is x` → escape.
- `sigil of x` (cualquier forma) → escape.

#### Control explícito

- `borrowed`: préstamo, sin auto-banish. No se puede baniar (`E0048`).
- `defer banish x` / `errdefer banish x`: desactiva el auto-banish de `x` y agenda la liberación en la pila LIFO de defers existente.
- `banish x` explícito: sólo válido en locales no-owning. En owned → `E0047`. En `borrowed` → `E0048`.

#### Advertencia sobre contenedores

`calling lst.push with x` (con `x` owned) transfiere a la lista, pero
**no** al caller de la lista. El que reciba la lista es responsable de liberar
los elementos antes de banear la lista. Asimetría conocida; ver §13.3.

#### `borrowed` como identificador

`borrowed` es una **soft keyword**: solo se reserva inmediatamente después de
`var` o `let`. En cualquier otro contexto (nombre de variable, campo,
parámetro, función, módulo) es un identificador normal:

```pengu
rune R:
    borrowed as int           # campo llamado 'borrowed' ✓

weave f with borrowed as int into int:
    return borrowed           # parámetro y variable ✓

weave g into int:
    var borrowed is 5         # ✗ Syntax error: 'borrowed' no es un nombre en esta posición
    return 0
```

---

## 14. Modules, imports & C interop

### 14.1 Imports & modules

```pengu
import std.spark
import std.scrolls as s              # alias
import components.player             # project module (src/components/player.pengu)
```

Module resolution: dotted path → file lookup (`.pengu`, then `.d.pengu`)
relative to `src/` or configured roots; `std.…` maps to the bundled standard
library. Import alias collisions are `E0036`; module-private members are not
exported (`E0043`).

### 14.2 `include`, `link`, `insignia`, `declare`

```pengu
include "raylib.h"
link "raylib"
link "m"
insignia mylib_
```

- `include` adds the C header to the generated file.
- `link` adds the library to the linker command.
- `insignia` changes the C prefix for every subsequent declaration/type in
  the module (e.g. `insignia pengu_` makes `weave helper` become
  `pengu_helper` at the C level).
- `declare` gives exact typed signatures for C functions. Every external C
  function must have an explicit `declare` signature (`E0004` if called without declaration).

**Spelling constants and enum variants from a binding.** `omen` variants declared
in a `.d.pengu` (`omen KeyboardKey:` + `KEY_RIGHT is 39`) are reachable in three
ways, and the first two are the ones to use:

```pengu
import std.raylib

calling raylib.IsKeyDown with raylib.KEY_RIGHT                # bare module-qualified ✅
calling raylib.IsKeyDown with raylib.KeyboardKey.KEY_RIGHT   # nested: type-qualified ✅
calling raylib.IsKeyDown with KEY_RIGHT                      # unqualified ✅
calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT   # qualified #define / variant ✅
```

All three forms are supported: bare module-qualified (`raylib.KEY_RIGHT`, `raylib.FLAG_MSAA_4X_HINT`), type-qualified (`raylib.KeyboardKey.KEY_RIGHT`), and unqualified (`KEY_RIGHT`). Struct-valued constants such as `raylib.RAYWHITE` are also supported (their value is emitted as defined).


### 14.3 `ref to char`, `opaque`, `.d.pengu`, and `bytes of`

C strings: pass `ref to char` parameters; PenguScript string literals convert
automatically to C string pointers where a `ref to char` is expected. Use
`bytes of s` for byte views, `std.ffi.string_from_cstr` / `cstr_from_string`
for explicit round trips (owning vs. borrowed semantics documented in the
module). Opaque handles are declared `alias X as opaque` and handled through
`ref to X`.

`.d.pengu` **declaration files**:

```pengu
# std/sqlite3.d.pengu (excerpt)
rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to opaque into int
```

- They register types/signatures only; implementations live in the C header.
- An `omen` declared in a `.d.pengu` mirrors a header enum, so emitted C uses
  the **bare** variant names (`KEY_LEFT`, not `KeyboardKey_KEY_LEFT`).

### 14.4 Project structure & `pengu.yaml`

```yaml
name: my_app
output: exe            # exe | c | obj | static | shared
# entry defaults to src/main.pengu; source roots default to ./src
```

The CLI supports `init`, `add`, `build`, `run`, `test`, `check`, `update`,
`bind`, `fmt`, `clean`, `lsp`, `doc`.

### 14.5 Module state patterns (singletons & services)

Top-level `var` and `let` declarations are strictly forbidden by design (`E0002`). All module-level symbols must be compile-time constants (`const`).

**Why mutable globals are forbidden:**
- **Concurrency & Safety:** Mutable globals create hidden data races, non-local side effects, and reentrancy bugs.
- **Deterministic Initialisation:** C compilation order across separate modules produces undefined global initialisation order. Forbidding global `var` ensures reproducible compilation and predictable lifetimes.
- **V-like Scoping:** PenguScript adheres to strict lexical scoping where mutable state belongs to execution scopes, not module namespaces.

When creating stateful services, singletons, or tracking state across calls, use one of two idiomatic patterns:

#### Pattern A: Encapsulated State via `static var` Accessor Weaves
State is contained inside accessor functions using `static var`. A `static var` inside a `weave` maintains its value across repeated calls and is initialized only once:

```pengu
# score_tracker.pengu
weave add_score with delta as int into int:
    static var score as int is 0
    set score is score + delta
    return score

weave get_score into int:
    return calling add_score with 0

weave reset_score into void:
    static var score as int is 0
    set score is 0
```

```c
// Generated C mapping
int32_t score_tracker_add_score(int32_t delta) {
    static int32_t score = 0;
    score = score + delta;
    return score;
}
```

#### Pattern B: Explicit Context Struct (`ref to Context`)
A clean, reentrant, and thread-safe pattern where the module defines a state `rune` and functions accept a pointer (`ref to Context`):

```pengu
# audio_manager.pengu
rune AudioContext:
    volume as float
    is_muted as bool

weave init into AudioContext:
    return with volume is 1.0, is_muted is false

weave set_volume with ctx as ref to AudioContext, vol as float into void:
    set ctx->volume is vol
```

```pengu
# main.pengu
import audio_manager as audio

weave main into int:
    var ctx as audio.AudioContext is calling audio.init
    calling audio.set_volume with sigil of ctx, 0.75
    return 0
```

---

## 15. Literals: strings, arrays, maps, indent blocks & ranges

### 15.1 Numbers, characters, booleans, null

```pengu
42  -7  0xFF  0b101  1_000        # integers
1.5  -0.25  2e3                    # floats
'A'  '\n'  '\x41'                  # characters
true  false  null
```

### 15.2 Strings

```pengu
let a as string is "plain"
let b as string is "value: {x} and {name}"      # interpolation → pengu_string_format
let c as string is r"raw \n no escapes"          # raw string
let d as string is """triple
   quoted   string"""                            # dedented multiline
let e as string is r"""raw triple"""             # raw + triple
```

- Interpolated strings compile to `pengu_string_format` / `snprintf`-style C.
- Raw strings keep backslashes verbatim.
- Triple quotes strip a common leading indent.

> [!IMPORTANT]
> **Use raw strings for text that is not PenguScript** — GLSL/HLSL shader source,
> regexes, JSON templates, Windows paths. In a normal string `{…}` is an
> *interpolation* and `\n`/`\t`/`\\` are escapes, so unescaped syntax inside `{…}`
> like `"#version 330\nvoid main() { gl_Position = …; }"` produces diagnostic
> `E0019` located against the string literal with an explicit hint recommending
> raw strings. The idiom is a raw triple string, which keeps the newlines *and*
> the braces literal:
>
> ```pengu
> var vs as string is r"""#version 330
> in vec3 vertexPosition;
> uniform mat4 mvp;
> void main() { gl_Position = mvp * vec4(vertexPosition, 1.0); }
> """
> var sh as raylib.Shader is calling raylib.LoadShaderFromMemory with (calling ffi.cstr_from_string with vs), (calling ffi.cstr_from_string with fs)
> ```
>
> Pass such a string to a C `const char*` with
> `ffi.cstr_from_string with s` (owning copy) or `bytes of s` (borrow, emits a
> pointer-sign warning).

### 15.3 Arrays, lists, slices, maps

```pengu
let nums as array of int with size 3 is [10, 20, 30]      # fixed C array
let dyn as list of int is list of int                      # growable PenguList
let sl as slice of int is nums at 1 to 3                   # view, end-exclusive
let m as map of string to int is map of string to int
calling m.put with "a", 1                          # insert/update
let v as int is calling m.get with "a"                # value for an existing key
```

Bracket literals `[1, 2, 3]` always produce a **fixed array** whose size is
inferred from the element count; element type follows the first element and
all must be compatible (`E0005`). Growable lists are created with `list of T`
(optionally `with capacity N`) and filled with `push`/`append`; slices are
non-owning views (`PenguSlice`).

**Multidimensional arrays.** Nesting `array of` gives a C multidimensional array.
The **outer dimension comes first**, and the inner one may be omitted when the
rows are literal, because it is inferred from them:

```pengu
var m as array of array of f32 with size 2 with size 3 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
# same type:  var m as array of array of f32 with size 2 is [...]   (3 inferred from the rows)

set m at 1 at 0 is 9.5          # m[1][0] = 9.5
var v as f32 is m at 0 at 1     # m[0][1]
var rows as int is (m length)          # 2
var cols as int is ((m at 0) length)   # 3
```

- Emitted C is `float m[2][3]`, so the layout matches C exactly (outer first).
- Rows must all have the same length; otherwise `E0041`.
- If no dimension can be inferred (e.g. `... with size 2 is []`), the checker
  raises `E0015` (`UnknownArrayDimensionError`) instead of emitting an invalid
  `[None]` size.
- A 2-D array decays for C interop as `T (*)[inner]` (only the outer dimension is
  dropped), so it can be passed where a `ref to array of T with size N` is
  expected; `m at 0` is a `ref to f32` to the first row.
- Like every fixed array, a 2-D array needs an initializer (`is [[…]]`); an
  indented literal (see §15.4) is the readable spelling for bigger grids.


### 15.4 Indentation literals

Arrays, maps and rune/struct literals can be written block style:

```pengu
var grid as array of array of int with size 2 with size 3 is:
    1, 2, 3
    4, 5, 6

var lookup as map of string to int is:
    "one": 1
    "two": 2

var p as Player is:
    name is "Ada"
    hp is 100
```

Grammar: `indent_array` rows for arrays (2-D = one row per sub-array),
`indent_entries` (`NAME: expr` map entries and `NAME is expr` field entries)
for maps and structs.

### 15.5 Ranges & membership

```pengu
1 to 10         # PenguRange [1, 10)
1..10           # same range syntax
for i in 1 to 5: ...
if x in 0 to 100: ...
```

Ranges are half-open (`end` excluded) and compile to `PenguRange`
(`int64_t start/end`). `to` doubles as the cast keyword when the right side is
a type (`10 to float`); context disambiguates.

---

## 16. Conditional compilation (`when`)

`when` works at three levels:

```pengu
when main:                     # top-level: only compile the chosen block
    weave app_main into int: return 0
when os == "windows":          # per-block / per-item
    declare win_only with ... into void
when os == "linux": ...
```

```pengu
when main:                     # inside a body
    calling platform_main with ...
else:
    calling module_main with ...
```

```pengu
let scale as int is when arch == "x64" then 2 else 1    # expression form
```

Available compile-time variables: `main` (bool: true for the module executed
directly), `debug` (bool: true when the active build profile is `debug` or `-D debug`),
`os` (`'windows'|'linux'|'macos'|…`), `arch` (`'x64'|'x86'|'arm64'
|…`), `compiler` (`'gcc'|'clang'|'msvc'|…`), and `defined(NAME)` for `-D`
macros. Non-constant conditions are rejected (`E0039`).

Blocks guarded with `when debug:` are useful for assertions, diagnostics, and development-only
instrumentation; `debug` evaluates to true when the build profile is `debug` (the default) and
evaluates to false under `release`.

---

## 17. Unit tests (`test`)

```pengu
test "arithmetic":
    calling expect_eq_int with 1 + 1, 2
test "strings":
    calling expect_eq_string with "ab" + "c", "abc"
```

Test blocks are compiled and run only by the test pipeline (`pengu test` /
`--test`); they are excluded from normal builds. `test` blocks inside
`.d.pengu` declaration files are rejected (`E0025`).

---

## 18. Block-style construction (`with:` expressions)

For long/complex initializers, a `with:` block builds a *fresh* value of an
explicitly typed target by mutating an implicit temporary; the block evaluates
to the built value:

```pengu
rune Point:
    x as int
    y as int

enchanting Point:
    weave shift with dx as int, dy as int into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into int:
    var p as Point with:
        set .x is 10
        set .y is 20
        calling .shift with 5, 3     # enchanting method on the temporary
    return p.x + p.y                    # 38
```

Rules (enforced by the checker):

- The declaration must annotate the target type (`var p as Point with:`);
  otherwise `E0014` (“requires an explicit type annotation”).
- Inside the block, `.field` refers to the value under construction; only
  `set .field is expr` and `calling .method` statements are allowed (`E0007`
  for anything else).
- Unknown fields (`E0004`-style: “Rune … has no field”), unknown methods, and
  missing type annotations are compile errors.
- Codegen emits a GNU statement-expression
  (`Tipo _with = {0}; …assignments…; _with;`), so the construct is usable in
  any expression position.

The one-line `with x is …, y is …` struct literal is unchanged, and each
field value may itself be a block value (a multi-line block must be the last
field, or the following `,` must start a new line) —
see [§7.6](#76-block-expressions-do-value-position-if--unless-and-loops).

> [!NOTE]
> Block members are written with the implicit `.` (`set .x is 10`), consistent
> with `with target:` scopes. `set x is 10` inside the block would assign a
> *local variable* named `x`, which normally does not exist.

---

## 19. Standard library

Wrapper modules (import `std.…`):

| Module | Purpose |
|--------|---------|
| `spark` | I/O: `print`, `println`, `print_line`, `input`, panic, conversion helpers |
| `oracle` | `Maybe*`/`Result*` runes: constructors and unwrap helpers |
| `scrolls` | string utilities (`upper`, `contains`, `split`, `substring`, …) |
| `compass` | path manipulation (join, basename, normalize, …) |
| `archivum` | files & directories (read/write/copy/metadata, CSV) |
| `cipher` | base64 + JSON parse/serialize |
| `chronicle` | date/time helpers (UTC formatting/parsing) |
| `lot` | pseudo-random numbers (seeded ranges, normal/exponential) |
| `rites` | process helpers (`exec`, `spawn`, env, pid, hostname) |
| `whisper` | leveled logging |
| `ward` | assertions and invariants |
| `trial` | lightweight test framework |
| `tally` | list helpers (`sum`, `max`, `min`) |
| `atlas` | map helpers |
| `coven` | string/int set helpers |
| `regulus` | regex (PCRE2): compile/search/match/find_all/replace/split + free |
| `parchment` | XML/HTML parsing (libxml2) + node/doc frees |
| `seal` | compression & hashing (gzip/zlib, md5/sha1/sha256/sha512, crc32) |
| `precis` | HTTP client/server, TCP, DNS, URL codecs, query parsing |
| `filum` | concurrency: threads, channels, mutex/wait-group/once/cond, atomics |
| `loom` | JSON/structured weaving helpers |
| `invoke` | CLI argument parsing |
| `ffi` | C ⇄ Pengu bridge helpers (strings, byte views, slices/lists, maps) |
| `celeris`, `xlsx`, `ledger`, `whisper`… | convenience packs / formats |

Binding `.d.pengu` modules (import as `std.raylib`, `std.sqlite3`,
`std.webui`, `std.miniaudio`, `std.tomlum`, `std.uuid`, `std.yaml`, …) expose
native C APIs 1:1 with upstream documentation retained inline.

---

## 20. Tooling & project layout

- **LSP** (`pengu lsp`): diagnostics, contextual completion, hover with
  memory sizes, go-to-definition/implementation, find references, rename,
  highlight, signature help, code actions (add import, remove unused,
  organize imports, implement concept methods), formatting.
- **Formatter** (`pengu fmt`): 2-space indentation (configurable via client
  options or `pengu.yaml`), strips trailing whitespace, keeps `#`/`##`
  comments intact.
- **Docs** (`pengu doc`): generates Markdown from the `##` / `#` comments
  directly above a declaration (generated bindings use `#`, like `pengu bind`).
- **Bind** (`pengu bind`): generates `.d.pengu` bindings from C headers. It blanks
  GNU compiler extensions before parsing, auto-imports the bindings of included
  headers, and takes `--define/-D NAME[=V]`, `--cpp-flags "…"`,
  `--system-includes`, `--include-paths DIR…`, `--preprocessed FILE.i` and
  `--no-blank-extensions` for headers that need a specific preprocessor setup.
  Failures name the offending construct and the flag to try.
- **Diagnostics point at your source.** Generated C carries `#line` directives
  back to the `.pengu` file and line, so a gcc/clang error (including one caused
  by a construct the checker accepted) is reported against your code, not against
  `build/bundle.c`.
- **Exit status.** The value of `weave main` becomes the process exit status
  (widened to `int`; `weave main into void` exits `0`), so CI and `pengu run`
  see failures. `pengu --version` / `-V` prints the toolchain version, and the
  version lives in the `VERSION` file (`pengu_version.py`).
- **Program arguments**: the entry wrapper calls `pengu_init(argc, argv)`, so
  `rites.get_argc()` / `get_argv()` / `get_args()` return the real arguments.
- **Release packaging**: `make_release.py` builds the compiler binary +
  VS Code extension; `build_runtime.py` builds `libpengu_runtime.a` and the
  vendored C libraries.

Known tooling gaps (as of 0.10.0): the `pengu` CLI has no `-I`/`-L`/`-l` flags
(use `pengu.yaml`), and `build/app.exe` is a shared default output path so building a
different entry reuses the same binary name (the cache is content-keyed, so it
rebuilds correctly). Parameters passed as `ref to T` and `self` are emitted as
standard C pointers without `restrict`, guaranteeing safety for aliasing buffers.

Typical layout:

```
my_project/
├── pengu.yaml
├── src/
│   └── main.pengu
├── lib/            # external dependencies/bindings
└── build/          # generated artifacts (gitignored)
```

---

## 21. Complete example

```pengu
import std.spark
import std.scrolls
import std.tally

# --- types --------------------------------------------------------------
rune Player:
    name as string
    hp as int

omen Phase:
    Idle
    Fighting

concept Named:
    weave display_name into string

bind Player with Named:
    weave display_name into string:
        return "Hero"

enchanting Player:
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100

    weave damage with amount as int into void:
        set self->hp is self->hp - amount
        if self->hp < 0:
            set self->hp is 0

# --- generics -----------------------------------------------------------
rune Pair shard A, B:
    first as A
    second as B

weave first_of shard A, B with p as Pair of A, B into A:
    return p.first

# --- main ---------------------------------------------------------------
weave main into int:
    var hero as Player with:                    # block construction
        set .name is "Ada"
        calling .damage with 30

    let desc is judge Phase.Fighting:
        when Phase.Idle -> "idle"
        when Phase.Fighting -> "fighting"
        else -> "?"

    var scores as list of int is list of int
    calling scores.push with 10
    calling scores.push with 20
    calling scores.push with 30
    calling spark.println with "sum: " + ((calling tally.sum with scores) to string)
    var part as string is calling scrolls.substring with "done", 0, 4
    calling spark.println with part

    var ok as maybe int is some 1
    if ok.is_present:
        return 0
    return 1
```

Generated C is a single translation unit: `struct Player { PenguString name;
int32_t hp; }; enum Phase { Phase_Idle, Phase_Fighting };` (plus methods as
`Player_new_hero`, `Player_damage`, monomorphized `Pair` structs, etc.),
wrapped by `int32_t pengu_main(void)` and a standard `main`.

---

*End of reference. Corrections welcome — this document mirrors compiler
behavior at version 0.9.x; run `pengu check` on any snippet to confirm
semantics on your toolchain.*
