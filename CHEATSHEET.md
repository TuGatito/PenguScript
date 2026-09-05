# PenguScript Language Reference

> A statically typed, compiled programming language that blends the clean, indentation-based readability of **Python**, the strict scoping and memory-safety rules of **V**, and the raw speed, small footprint, and seamless C interoperability of **C**. PenguScript sources compile to readable **C99/C11**, which is then compiled with `gcc`, `clang`, or `msvc` into standalone native binaries on Windows, Linux, and macOS.

This reference is organized by topic. Every PenguScript example that maps to generated code is followed by the emitted C. The standard library catalog and the CLI reference are kept in tables so they can be scanned quickly.

---

## Table of Contents

1. [About PenguScript](#1-about-penguscript)
2. [Quick Start](#2-quick-start)
3. [Syntax Fundamentals](#3-syntax-fundamentals)
4. [Types & C Representation](#4-types--c-representation)
5. [Variables, Constants & Scoped Bindings](#5-variables-constants--scoped-bindings)
6. [Operators & Expressions](#6-operators--expressions)
7. [Control Flow](#7-control-flow)
8. [Functions: `weave`, `calling` & `many`](#8-functions-weave-calling--many)
9. [Methods, Concepts & Generics](#9-methods-concepts--generics)
10. [Composite & Nominal Types: `rune`, `echo`, `omen`, `seal`, `alias`, `opaque`](#10-composite--nominal-types-rune-echo-omen-seal-alias-opaque)
11. [Optionals & Error Handling: `maybe`, `result` & `or`](#11-optionals--error-handling-maybe-result--or)
12. [Memory Model & Pointers](#12-memory-model--pointers)
13. [Modules, Imports & Project Layout](#13-modules-imports--project-layout)
14. [C Interop & FFI](#14-c-interop--ffi)
15. [Standard Library](#15-standard-library)
16. [Language Server & Tooling](#16-language-server--tooling)
17. [CLI Reference](#17-cli-reference)
18. [Building from Source & Release Packaging](#18-building-from-source--release-packaging)
19. [Example Gallery](#19-example-gallery)
20. [Keywords at a Glance](#20-keywords-at-a-glance)

---

## 1. About PenguScript

PenguScript is a compiled language with a deliberately small vocabulary of keyword-style operators. Program structure is expressed with words (`with`, `is`, `of`, `as`, `to`, `calling`, `into`) instead of punctuation, while the type system stays strict and the generated C stays fast.

### 1.1 Core principles

- **Indentation-based blocks.** No semicolons, no curly braces. Nesting is expressed with indentation (`_INDENT` / `_DEDENT`).
- **Three role words for declarations:**
  - `as` declares a **type** (`x as int`)
  - `is` binds a **value** (`is 42`, `with field is 1`)
  - `into` declares a **return type** (`weave f into int:`)
- **`to` is the cast operator** (`10 to float`); `transmute` performs raw bit reinterpretation.
- **Everything that looks like a statement can be an expression** when useful: `if`, `when`, `judge`, and comprehension loops evaluate to values.
- **V-style scoping — no mutable globals:**
  - `const` is a top-level compile-time constant and is emitted as a C `#define` or constant literal.
  - `var` (mutable) and `let` (immutable) are local bindings inside function bodies and control-flow blocks. Mutable state is never global.
- **Deterministic cleanup.** `defer` (LIFO on scope exit), `errdefer` (only when the scope returns an error), and explicit `banish` (free) give predictable lifetimes without a garbage collector.

### 1.2 Compilation pipeline

```
PenguScript source (.pengu / .d.pengu)
        │  pengu_parser/  (Lark grammar → semantic check → codegen)
        ▼
bundle.c  (+ project c/*.c, lib/*/c/*.c glue)
        │  gcc / clang / msvc  (configured in pengu.yaml, --cc, profiles)
        ▼
native executable / static lib / shared lib / object / plain C
```

The compiler ships as Python modules in `pengu_parser/` (`pengu_grammar.py`, `pengu_types.py`, `pengu_checker.py`, `pengu_infer.py`, `pengu_codegen.py`, `pengu_symbols.py`, `pengu_comptime.py`, `pengu_errors.py`). The runtime that generated code links against lives in `pengu_runtime.h` / `pengu_runtime.c`; the standard library is written in PenguScript under `std/`; vendored single-header C libraries live under `std_c/`; minimal C standard-library stubs for header binding live in `c_bind_stubs/`. `pengu_project.py` implements the `pengu` CLI, `pengu_lsp/` the language server, `pengu_bind.py` the C-header → declaration-file generator, and `pengu_doc.py` the documentation generator.

### 1.3 How to read this reference

Examples alternate a PenguScript snippet (```pengu) with the corresponding generated C (```c) where the mapping is interesting. Many examples reference the standard library module `std.spark` for terminal output — the idiom is `calling spark.println with "text"`. See [Standard Library](#15-standard-library) for the catalog and [Example Gallery](#19-example-gallery) for complete programs.

---

## 2. Quick Start

### 2.1 Requirements

- Python 3.10+ (to run the compiler toolchain from source)
- A C compiler on `PATH`: `gcc`, `clang`, or `msvc`
- Node.js 18+ and `npm` only if you build the VS Code extension

### 2.2 Your first program

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello from PenguScript"
    return 0
```

Entry point is a top-level `weave main` returning `int` (exit code) or `void`.

### 2.3 Project workflow

```bash
# Create a Cargo-style project and build/run it
pengu init my_game --type exe
cd my_game
pengu run                # build (debug profile) and execute
pengu build --profile release   # optimized binary

# Type-check without producing code (CI friendly)
pengu check

# Run any .pengu file directly as a standalone script
pengu run hello.pengu    # 'when main:' is enabled for the script

# Format sources (or verify with --check)
pengu fmt src/
pengu fmt --check src/

# Generate Markdown reference documentation from '##' comments
pengu doc                # writes <project>/docs (index.md + one page per module)

# Clean build artifacts
pengu clean
```

From a source checkout the same commands run as `python pengu_project.py …` (the module installs a `pengu` entry point when packaged by `make_release.py`).

### 2.4 Standalone scripts

A `.pengu` file can act like `python script.py`:

```bash
pengu run script.pengu
```

The executed file is compiled with the compile-time variable `main` set to `true`; every imported module is compiled with `main` set to `false`. Guard script-only code with `when main:` (see [Compile-time conditionals](#73-compile-time-conditionals-when)):

```pengu
import std.spark

weave greet with name as string into void:
    calling spark.println with "Hello, " + name

when main:
    weave main into int:
        calling greet with "Ada"
        return 0
```

Running it prints `Hello, Ada!`. Importing the same file from another module drops the `when main:` block entirely, so only `greet` is available.

How the `main` compile-time flag is decided:

| Scenario | Entry module | Imported modules |
| -------- | ------------ | ---------------- |
| `pengu run script.pengu` | `true` | `false` |
| `pengu build` / `run` / `test` with `-D main` (explicit opt-in) | `true` | `false` |
| plain `pengu build` / `pengu run` (project) | `false` | `false` |

The flag is resolved per module file: importing a module never turns on its `when main:` blocks.

---

## 3. Syntax Fundamentals

### 3.1 Files and structure

- Source files end in `.pengu`. Declaration-only files end in `.d.pengu` (see [Declaration files](#133-declaration-files-dpengu)).
- A file is a sequence of top-level statements. Allowed at top level:
  `import`, `include`, `link`, `insignia`, `const`, `var`/`let` (rejected by the checker outside function bodies), `rune`, `echo`, `omen`, `alias`, `seal`, `concept`, `bind`, `weave`, `enchanting`, `declare`, `when` (compile-time), `test`.
- Statements inside bodies: `var`, `let`, `static var`, `const`, `set`, `if`/`unless`/`else`, `while`, `for`, `when`, `with`, `defer`, `errdefer`, `banish`, `return`, `break`, `continue`, bare expressions, and named assignments (`name is expr`).

### 3.2 Comments

```pengu
# Single line comment

##
Multi-line block comment.

Documentation comments: a ## block (single-line "## text", self-closed
"## text ##", or multi-line "## ... ##") attaches to the declaration that
follows it and is surfaced by the LSP hover and by 'pengu doc'.
##
```

```c
// Single line comment

/*
  Multi-line block comment.
*/
```

The LSP and `pengu doc` turn `##` documentation into tooltips / Markdown pages, combining the doc text with the inferred signature (parameters, return type, fields, constants, variant values).

### 3.3 Identifiers

Identifiers match `[a-zA-Z_][a-zA-Z0-9_]*`. `_` alone is the discard binding (e.g. `for _, v in col`); it never creates a variable. Names are case-sensitive; conventional style uses `snake_case` for values and `PascalCase` for type declarations. `main` is reserved: `var main`, `let main`, `static var main`, or `const main` raise `error[E0040]` because `main` is a compile-time variable (see [Standalone scripts](#24-standalone-scripts)). Defining the entry function `weave main …` is unaffected.

### 3.4 Words with multiple jobs

| Word | Role in `x as int` / `weave f with a as int` | Role in `let x is 42` | Role in `with w is 1` | Other roles |
| ---- | ------------------------------------------- | --------------------- | --------------------- | ----------- |
| `as` | type annotation | — | — | — |
| `is` | — | value binding / assignment | field initializer | comparison: `expr is present`, `expr is not present`, `expr is true`, `expr is false`; enum values (`Variant is 3`); string-valued omens (`Variant is "v"`) |
| `to` | — | — | — | cast: `10 to float`; slicing: `arr at 1 to 4`; ranges: `for i from 0 to 5`; generics are *not* `to` |
| `into` | return type after `into` | — | — | — |
| `and` / `,` | parameter separator | — | field initializer separator | argument separator in `calling f with a and b`; type-parameter separator (`shard T and U`) |

> [!IMPORTANT]
> `and` and `,` are **list separators** (parameters, arguments, struct fields), never logical operators. PenguScript has no `&&`/`||`; boolean negation is the unary word `not`, and bitwise/logical `|`, `&`, `^` follow the C precedence ladder in [Operators & Expressions](#6-operators--expressions).

### 3.5 Reserved words

`import include link insignia const var let set static weave declare enchanting rune echo omen alias seal concept bind shard where when test ritual inline if unless else while for in from to step judge calling with into as is many return break continue defer errdefer banish some ord chr bytes of essence of sigil of transmute size of try defined not null true false maybe none error`.

---

## 4. Types & C Representation

### 4.1 Type vocabulary

| Kind | PenguScript spelling |
| ---- | -------------------- |
| Booleans | `bool` |
| Integers | `int`, `i32`, `i64`, `u32`, `u64`, `i16`, `u16`, `i8`, `u8`/`byte`, `char`, plus C-style spellings: `int8`…`uint64`, `int8_t`…`uint64_t`, `short`, `ushort`, `long`, `ulong`, `uint`, `usize`, `isize`, `size_t` |
| Floats | `float`, `f32`, `f64`, `double` |
| Text | `string` |
| Unit | `void` |
| Optional | `maybe T` |
| Result | `result of T to E` (E defaults to the runtime error type) |
| References | `ref to T` (pointer), `ref to void` (generic pointer) |
| Arrays | `array of T with size N` |
| Slices | `slice of T` |
| Lists | `list of T` (with optional `list of T with capacity C`) |
| Maps | `map of K to V` |
| Variadic | `many T` (parameter-only) |
| Opaque | `opaque` |
| Functions | `weave with … into …` (type-position signature) |
| User types | `rune` (struct), `echo` (union), `omen` (enum / algebraic sum), `seal` (nominal newtype), `alias` (transparent synonym), `concept` (interface) — see [section 10](#10-composite--nominal-types-rune-echo-omen-seal-alias-opaque) |

### 4.2 Primitive mapping to C

| PenguScript | C | Notes |
| ----------- | -- | ----- |
| `int`, `i32` | `int32_t` | Default integer; literals like `42`, hex `0x2A` |
| `i64` | `int64_t` | |
| `u32` | `uint32_t` | |
| `u64` | `uint64_t` | |
| `i16` / `u16` | `int16_t` / `uint16_t` | |
| `i8` / `byte`, `u8` | `int8_t` / `uint8_t` | `byte` is the raw-byte type used with `bytes of` buffers |
| `char` | `char` | Single-character literal: `'k'` |
| `float`, `f32` | `float` | |
| `f64`, `double` | `double` | |
| `bool` | `bool` | `true` / `false` |
| `string` | `PenguString` | Dynamic UTF-8, immutable value `{ char* data; int len; }` |
| `void` | `void` | Unit / no value |
| `opaque` | `void*` | Incomplete type: declare `alias Texture as opaque`, the real definition comes from an `include`d C header |
| `ref to T` | `T*` | |
| `ref to void` | `void*` | |
| `usize` / `size_t` | `size_t` | |
| `isize` | `intptr_t` | |
| `array of T with size N` | `T[N]` | Fixed-size contiguous stack array |
| `slice of T` | `PenguSlice` | Fat view `{ void* data; int len; size_t elem_size; }` |
| `list of T` | `PenguList` | Growable heap array `{ void* data; int len; int cap; size_t elem_size; }` |
| `map of K to V` | `PenguMap` | Open-addressing hash map (`entries`, `len`, `cap`, `key_size`, `val_size`) |
| `maybe T` | `PenguMaybe` | `{ bool is_present; void* value; }` — a present value is a heap copy, see [section 11](#11-optionals--error-handling-maybe-result--or) |
| `result of T to E` | `PenguResult` | `{ bool is_ok; void* ok_val; void* err_val; }` |
| `many T` (parameter) | `PenguSlice` | Behaves as `slice of T` inside the body |

> [!NOTE]
> Integer aliases share a C type: `int`/`i32`/`int32`/`int32_t` → `int32_t`; `float`/`f32` → `float`; `double`/`f64` → `double`; `byte`/`u8`/`uint8`/`uint8_t` → `uint8_t`, and so on for every fixed-width family. `char` maps to C `char`.

The compiler reports an approximate byte size for every type (LSP hover shows it). Fixed sizes on 64-bit targets: `bool` 1, `int`/`i32`/`float`/`f32` 4, `i64`/`f64` 8, `string` 16, a reference 8, `maybe T` ≈ `sizeof(T)+4`, `result of T to E` ≈ `ok + err + 4`, an array `N * sizeof(elem)`, `slice`/`list`/`map` 24 (estimator value; `PenguMap`'s real struct is larger). Run `pengu build` and hover in the LSP for the exact per-type number used by the checker.

### 4.3 Literals

```pengu
var a as int is 42
var h as int is 0xFF            # hex literal
var pi as float is 3.14159
var flag as bool is true
var name as string is "Pengu"
var letter as char is 'k'
var nothing as ref to int is null      # null pointer literal
var absent as maybe int is maybe none  # empty optional
```

String literals are context aware:

- Where a `string` is expected they emit `pengu_string_from_cstr("…")` (or `pengu_string_format(...)` when they contain `{expr}` interpolation).
- Where a `ref to char` (C `const char*`) is expected they are emitted **directly as C string literals** `"…"` with no allocation. String interpolation inside a `ref to char` context is rejected at compile time.

```pengu
let s as string is "Hello {name}"   # interpolated PenguString (name is a variable)
let c as ref to char is "raw C"     # direct C literal, no allocation
```

### 4.4 Casts

```pengu
let f as float is 10 to float       # numeric cast
let i as int is (3.7 to int)        # truncating float → int
let bits is transmute f to int      # raw bitwise reinterpretation
let p as ref to int is transmute x to ref to int
```

```c
float f = (float)10;
int i = (int)(3.7);
int bits = *(int*)&f;               // transmute pattern
int* p = (int*)(uintptr_t)x;
```

`to` performs checked numeric/type casting. `transmute` reinterprets the raw bytes between two types (mismatched sizes produce a warning). Casting between nominal `seal` types and their underlying type also requires explicit `to` ([section 10.4](#104-distinct-nominal-types-seal)).

---

## 5. Variables, Constants & Scoped Bindings

### 5.1 Declaration keywords

| Keyword | Scope | Mutability | C output |
| ------- | ----- | ---------- | -------- |
| `const NAME as T is expr` | top-level compile-time constant | immutable | `#define` / constant literal |
| `var NAME as T is expr` | local | mutable via `set` | plain C local |
| `let NAME as T is expr` | local | immutable | `const` C local |
| `static var NAME as T is expr` | function body only | mutable, persists between calls | C `static` |
| `set target is expr` | — | mutation statement | C assignment |

```pengu
const MAX_ENTITIES as int is 1000
const PI as float is 3.14159
const TITLE as ref to char is "Pengu"     # emits #define TITLE "Pengu"

weave main into int:
    var x as int is 10         # mutable local
    let y as int is 20         # immutable binding (const int in C)
    let p as ref to int is sigil of x

    set x is x + 1             # mutation
    # set y is 30              # COMPILE ERROR: y is immutable
    return 0
```

```c
#define MAX_ENTITIES 1000
#define PI 3.14159f
#define TITLE "Pengu"

int main(void) {
    int x = 10;
    const int y = 20;
    int* p = &x;
    x = x + 1;
    return 0;
}
```

Rules:

- `const` is compile-time and normally top level. Integer/string constants feed compile-time logic (`when`, enum values, `array of … with size N`).
- Global `var`/`let` is rejected: mutable state is always local.
- A `let` may omit the type when it is inferable (`let total is 5`), and may declare several names for destructuring: `let x, y is v` copies struct fields by name (see [Destructuring](#66-destructuring-bindings)).
- Declarations whose initializer must not be re-evaluated each call belong to `static var`, which is only allowed directly inside a `weave` body:

```pengu
weave next_id into int:
    static var counter as int is 0
    set counter is counter + 1
    return counter
```

```c
int32_t next_id(void) {
    static int32_t counter = 0;   // constant initializers emit a plain static
    counter = counter + 1;
    return counter;
}
```

Non-constant `static var` initializers (strings, structs, …) are zero-initialized and assigned once on first execution behind an `_initialized` guard.

### 5.2 Compile-time variables

The compile-time environment exposes `os` (`windows` / `linux` / `macos` / …), `arch` (`x64` / `x86` / `arm64` / …), `compiler` (`gcc` / `clang` / `msvc` / …), and `defined(NAME)`. The entry-point flag `main` is `true` only for the module being executed. All are readable inside `when` conditions ([7.3](#73-compile-time-conditionals-when)) and overridable on the command line with `-D`:

```bash
pengu build -D WEB               # defined(WEB) == true
pengu build -D os=linux          # target another OS
pengu build -D arch=arm64 -D compiler=clang
pengu build -D main              # treat this build as the script entry (main == true)
```

### 5.3 The `null` literal

`null` represents null pointers for C interop and raw references:

- Compatible only with reference types (`ref to T`), `opaque` types, and `any`; assigning it to value types such as `int`, `string`, or `bool` is a compile error (`E0005`).
- An explicit type annotation is required (`var p as ref to int is null`, `E0014` if omitted).
- Compare with `==` / `!=` against references, opaque handles, and `null`. Relational comparisons (`<`, `<=`, `>`, `>=`) are rejected.
- Taking the address of `null` (`sigil of null`) is rejected (`E0008`).
- Translates to C `NULL`.

```pengu
var ptr as ref to int is null
let handle as opaque is null

if ptr == null:
    calling spark.println with "pointer is null"
else:
    calling spark.println with "pointer is valid"

var value as int is 42
set ptr is sigil of value
```

> Prefer `maybe none` for idiomatic optional values; reserve `null` for raw C pointers and FFI handles.

---

## 6. Operators & Expressions

### 6.1 Precedence, from loosest to tightest

1. `or else`, `or return`, `or:` blocks, then `try`
2. `judge … when … -> … else -> …` expressions and `if/when … then … else …`
3. comparisons: `== != <= >= < >` and word tests `is present`, `is not present`, `is true`, `is false`
4. bitwise/logical `|` `&` `^`
5. shifts `<<` `>>`
6. additive `+ -`
7. multiplicative `* / %`
8. unary `~` `not` `-`, word unaries `sigil of`, `essence of`, `transmute … to`, `size of`, `banish`, `some`, `ord`, `chr`, `bytes of`
9. postfix `at`, slicing `at a to b`, `length`, `.field`, `->field`, cast `to`
10. atoms: literals, `calling` calls, `with`/list/map/array initializers, `defined(...)`

The grammar folds each level with left associativity, so `10 + 20 * 2` parses as `10 + (20 * 2)`.

### 6.2 Arithmetic & bitwise

```pengu
weave operators_demo into void:
    let a is 10 + 20 * 2
    let b is (10 + 20) * 2
    let rem is 17 % 5

    # Bitwise (flags, graphics, hashing)
    let flags is 0x01 | 0x02        # OR
    let masked is flags & 0xFF      # AND
    let xor is flags ^ 1            # XOR
    let flipped is ~flags           # NOT
    let shifted is 1 << 5           # left shift
    let rshift is 32 >> 2           # right shift
    let neg is -a
    var flag as bool is true
    let inv is not flag             # logical not (word form)
```

```c
void operators_demo(void) {
    int32_t a = 10 + 20 * 2;
    int32_t b = (10 + 20) * 2;
    int32_t rem = 17 % 5;
    int32_t flags = 0x01 | 0x02;
    int32_t masked = flags & 0xFF;
    int32_t xor = flags ^ 1;
    int32_t flipped = ~flags;
    int32_t shifted = 1 << 5;
    int32_t rshift = 32 >> 2;
    int32_t neg = -a;
}
```

`+` concatenates strings (`"a" + "b"`), and every arithmetic operator requires numeric operands. Conditions must be real `bool` values — there is no truthiness coercion.

### 6.3 Word operators

| Expression | Meaning | Example |
| ---------- | ------- | ------- |
| `sigil of x` | address of (C `&x`) | `let p as ref to int is sigil of x` |
| `essence of p` | dereference (C `*p`) | `set essence of p is 100` |
| `size of T` | byte size of a type | `let n is size of int` → `sizeof(...)` |
| `banish p` | free a heap allocation | `banish buffer` (also a statement) |
| `some v` | present `maybe T` from value `v` | `let m as maybe int is some 42` |
| `ord s` | byte code of a single-character string | `ord "A"` → `65` |
| `chr n` | single-character string from byte 0–255 | `chr 66` → `"B"` |
| `bytes of s` | borrow string bytes as `ref to byte` (no copy) | see [FFI](#146-passing-strings-to-c) |
| `null` | null pointer literal | `var p as ref to int is null` |
| `maybe none` | empty optional | `let m as maybe int is maybe none` |
| `error` | the error value inside an `or:` block | `let err is error` |
| `defined(NAME)` | compile-time flag test | `when defined(WEB):` |

```pengu
let code as int    is ord "A"          # 65
let ch   as string is chr 66           # "B"
let next as string is chr (ord "A" + 1)
let m as maybe int is some 42
```

- `ord` accepts a single-character string; string-literal length is validated at compile time.
- `chr` accepts an int in 0–255 (constant range is checked) and returns a single-character string backed by a heap copy.
- `some` heap-copies its operand (`pengu_sigil_alloc` + `memcpy`) so the value outlives the expression.

### 6.4 String operations

```pengu
let s as string is "PenguScript"
let n is s length              # 11 — postfix 'length'
let c is s at 0                # "P" (single-character string)
let sub is s at 5 to 9         # slice [5,9) → "Script"
let greeting is "Hi, {name}!"  # interpolation (string context only)

var items as list of string is list of string
calling items.push with "a"
let first is items at 0        # element access with 'at'
```

```c
PenguString s = pengu_string_from_cstr("PenguScript");
int32_t n = s.len;
PenguString c = pengu_string_char_at(s, 0);
PenguString sub = pengu_string_substring(s, 5, 9);
PenguString greeting = pengu_string_format("Hi, %s!", (name).data);
```

`x length` works on strings, slices and collections; `at` indexes arrays, slices, lists, maps (value position) and strings; `at a to b` slices contiguous memory (`pengu_string_substring` for strings, `pengu_slice_new` for arrays). Element access is uniform across all collections.

### 6.5 `calling` & argument passing

Calls use the `calling` keyword. Arguments are positional or named (`name is value`), separated by `and` or `,`:

```pengu
let s is calling add with 10 and 20          # positional
calling DrawText with text is "Hi" and x is 100   # named (defaults omitted)
calling player.move with 1.0 and 0.0         # method call
calling spark.println with "done"            # module member call
```

See [Functions](#8-functions-weave-calling--many) for the full call grammar, default arguments, and variadics.

### 6.6 Destructuring bindings

```pengu
rune Vec2:
    x as float
    y as float

weave test_destructure into void:
    var v as Vec2 is with x is 10.0 and y is 20.0
    let x, y is v       # bind v.x → x, v.y → y
```

```c
typedef struct { float x; float y; } Vec2;

void test_destructure(void) {
    Vec2 v = (Vec2){ .x = 10.0f, .y = 20.0f };
    const float x = v.x;
    const float y = v.y;
}
```

---

## 7. Control Flow

### 7.1 Conditionals: `if` / `unless` / ternary

```pengu
weave conditionals_demo with x as int into void:
    if x > 10:
        calling spark.println with "greater than 10"
    else:
        calling spark.println with "10 or less"

    unless x == 0:                # sugar for 'if not'
        calling spark.println with "non-zero"

    # if-expression (ternary)
    let color as string is if x > 10 then "red" else "blue"

    # chained else if
    if x == 1:
        calling spark.println with "one"
    else if x == 2:
        calling spark.println with "two"
```

```c
void conditionals_demo(int32_t x) {
    if (x > 10) {
        printf("greater than 10\n");
    } else {
        printf("10 or less\n");
    }

    if (!(x == 0)) {
        printf("non-zero\n");
    }

    const char* color = (x > 10) ? "red" : "blue";

    if (x == 1) {
        printf("one\n");
    } else if (x == 2) {
        printf("two\n");
    }
}
```

`if` conditions can bind a `maybe` and test presence in one step: `if user as maybe string is calling find_user with 1 is present:`.

### 7.2 Loops

```pengu
weave loops_demo into void:
    var x as int is 0
    while x < 10:
        set x is x + 1
        if x == 5:
            continue
        if x == 9:
            break

    for i from 0 to 5:            # half-open range [0, 5)
        calling spark.println with (i to string)

    for i from 10 to 0 step -2:   # optional 'step'
        calling spark.println with (i to string)

    var numbers as array of int with size 3 is [10, 20, 30]
    for num in numbers:           # element iteration
        calling spark.println with (num to string)

    for i, num in numbers:        # indexed iteration (index is immutable int)
        if i > 0:
            calling spark.println with (num to string)

    for _, num in numbers:        # '_' discards the index binding
        calling spark.println with (num to string)

    # comprehension expression: collect elements passing a filter
    let evens is for num in numbers when num % 2 == 0 then num
```

```c
void loops_demo(void) {
    int32_t x = 0;
    while (x < 10) {
        x = x + 1;
        if (x == 5) continue;
        if (x == 9) break;
    }

    for (int32_t i = 0; i < 5; i++) {
        printf("%d\n", i);
    }

    for (int32_t i = 10; i > 0; i += -2) {
        printf("%d\n", i);
    }

    int32_t numbers[3] = { 10, 20, 30 };
    for (int32_t _idx = 0; _idx < 3; _idx++) {
        int32_t num = numbers[_idx];
        printf("%d\n", num);
    }

    for (int32_t i = 0; i < 3; i++) {          // indexed iteration keeps 'i'
        int32_t num = (numbers)[i];
        if (i > 0) printf("%d\n", num);
    }
}
```

Loop variants at a glance:

| Form | Meaning |
| ---- | ------- |
| `for i from a to b` | numeric range `[a, b)` |
| `for i from a to b step s` | numeric range with step (can be negative) |
| `for v in col` | element iteration over array / slice / list / map keys / string characters |
| `for i, v in col` | indexed element iteration (`i` is `int`, immutable) |
| `for i, _ in col` / `for _, v in col` | discard index or element |

### 7.3 Compile-time conditionals: `when`

`when` evaluates its condition at compile time; the inactive branch is syntax-checked but discarded — it generates no code and takes part in no symbol resolution. Three forms:

1. Top level — used for platform includes/links and declaration blocks:

```pengu
when os == "windows":
    include "windows.h"
    link "kernel32"
else:
    include "unistd.h"
    link "pthread"
```

2. Statement level inside a body — behaves like textual substitution: names declared in the active branch stay visible in the enclosing scope:

```pengu
weave audit with what as string into void:
    calling spark.println with "audit: " + what
    when main:
        calling spark.println with "(running as a script)"
```

3. Expression form: `when cond then a else b`.

Conditions must be compile-time boolean constants built from the built-in variables (`os`, `arch`, `compiler`, `main`) and `defined(NAME)`; anything else is rejected (`E0039`). `when main:` is the idiomatic Python-`__main__` guard — see [Standalone scripts](#24-standalone-scripts) for how the `main` flag is decided per module.

### 7.4 Pattern matching: `judge`

`judge` evaluates a subject against inline `when pattern -> expr` clauses and returns the first match:

```pengu
weave describe with key as int into string:
    let state as string is judge key:
        when 1 -> "active"
        when 2 -> "pending"
        when 3 -> "finished"
        else -> "unknown"
    return state
```

```c
PenguString describe(int32_t key) {
    switch (key) {
        case 1:   return pengu_string_from_cstr("active");
        case 2:   return pengu_string_from_cstr("pending");
        case 3:   return pengu_string_from_cstr("finished");
        default:  return pengu_string_from_cstr("unknown");
    }
}
```

Patterns may be integers, floats, strings, characters, `true`/`false`, `maybe none`, or named constants; an `else ->` clause is optional. Integer/enum subjects compile to C `switch`, and string comparisons use the runtime string equality helper. The grammar also accepts optional payload bindings (`when Variant with field -> …`) for algebraic omens.

### 7.5 Integrated tests: `test …`

Top-level `test "name":` (or `test name:`) blocks are validated semantically in every build but only compiled when requested with `--test`:

```pengu
import std.ward as w

weave add with a as int and b as int into int:
    return a + b

test "addition works":
    let r is calling add with 2 and 3
    calling w.assert_eq_int with r and 5

test add_zero:
    let r is calling add with 0 and 0
    calling w.assert_eq_int with r and 0
```

In a normal build the blocks are ignored and nothing appears in `bundle.c`. With `--test`, each block becomes `static void pengu_test_N(void)`, a `pengu_run_tests()` runner and a test `main` are generated, failing assertions panic with a non-zero exit code, and passing tests print `[PASS]`.

```bash
pengu test                   # compile in test mode and run
pengu build --test -o bundle_test.c
pengu run --test
```

---

## 8. Functions: `weave`, `calling` & `many`

### 8.1 Declaring functions

```pengu
# 1. Implicit return: the last expression is the return value
weave add with a as int and b as int into int:
    a + b

# 2. Explicit return + default argument values
weave DrawText with text as string and x as int is 0 and y as int is 0 into void:
    calling spark.println with text
    return

# 3. A parameterless function
weave now into string:
    return "now"

# 4. Inlined function
inline weave fast_add with a as int and b as int into int:
    a + b

# 5. 'pass' style empty body is not a keyword — use a comment + return
weave no_op into void:
    return
```

A default is written `name as type is default`; the compiler fills omitted defaults at every call site. Named arguments let callers skip optional parameters. `void` functions may `return` with no value. `inline` maps to `static inline` C.

### 8.2 Calling functions

```pengu
weave demo_calls into void:
    # named argument call — y defaults to 0
    calling DrawText with text is "Hello, Pengu!" and x is 100

    # positional call
    let sum is calling add with 10 and 20

    # chained / method-style call
    calling player.move with 1.0 and 0.0

    # no-argument call
    calling CloseWindow
```

### 8.3 Generated C for defaults, inline & calls

```c
int32_t add(int32_t a, int32_t b) {
    return a + b;
}

void DrawText(PenguString text, int32_t x, int32_t y) {
    printf("%s\n", (text).data);
    return;
}

PenguString now(void) {
    return pengu_string_from_cstr("now");
}

static inline int32_t fast_add(int32_t a, int32_t b) {
    return a + b;
}

void demo_calls(void) {
    DrawText(pengu_string_from_cstr("Hello, Pengu!"), 100, 0);  // default filled in
    int32_t sum = add(10, 20);
    Player_move(&player, 1.0f, 0.0f);      // methods receive 'self' by pointer
    CloseWindow();
}
```

### 8.4 Variadic parameters: `many`

```pengu
weave sum_all with base as int and values as many int into int:
    var total as int is base
    for num in values:
        set total is total + num
    return total

weave test_variadic into void:
    let total1 is calling sum_all with 10 and 20 and 30 and 40
    let total2 is calling sum_all with 5          # zero variadic args
```

Rules:

- At most **one** `many` parameter per function (`E0023`), and it **must be last** (`E0024`).
- Inside the body the `many` parameter behaves as a `slice of T` (`PenguSlice`): `length`, `at` indexing, `for … in` iteration.

```c
int32_t sum_all(int32_t base, PenguSlice values) {
    int32_t total = base;
    for (int32_t _i = 0; _i < values.len; _i++) {
        int32_t num = (((int32_t*)values.data)[_i]);
        total = total + num;
    }
    return total;
}

void test_variadic(void) {
    int32_t total1 = sum_all(10, ({ int32_t _tmp_arr[] = { 20, 30, 40 };
        PenguSlice _tmp_slice = { .data = _tmp_arr, .len = 3, .elem_size = sizeof(int32_t) };
        _tmp_slice; }));
    int32_t total2 = sum_all(5, ({ PenguSlice _tmp_slice = { .data = NULL, .len = 0,
        .elem_size = sizeof(int32_t) }; _tmp_slice; }));
}
```

### 8.5 Function pointers

Type-position signatures use `weave with … into …`; declare pointer aliases with `alias`:

```pengu
alias BinaryOp as ref to weave with a as int and b as int into int
alias WebUICallback as ref to weave with event as ref to void into void

weave add with a as int and b as int into int:
    return a + b

weave execute_op with op as BinaryOp and x as int and y as int into int:
    return calling op with x and y

weave test_callback into void:
    let fn_ptr as BinaryOp is sigil of add
    let result is calling execute_op with fn_ptr and 10 and 20

    # A weave name passed where a callback type is expected decays to its
    # C function pointer automatically (C can also call back into PenguScript
    # weaves through runtime helpers — see section 14).
    let direct is calling execute_op with add and 3 and 4
```

```c
typedef int32_t (*BinaryOp)(int32_t, int32_t);
typedef void (*WebUICallback)(void*);

int32_t add(int32_t a, int32_t b) { return a + b; }

int32_t execute_op(BinaryOp op, int32_t x, int32_t y) {
    return op(x, y);
}

void test_callback(void) {
    BinaryOp fn_ptr = &add;
    int32_t result = execute_op(fn_ptr, 10, 20);

    int32_t direct = execute_op(&add, 3, 4);  // weave name decays to its address
}
```

---

## 9. Methods, Concepts & Generics

### 9.1 `enchanting` receiver blocks

`enchanting Type:` attaches methods to a type. Inside a method, `self` is always a `ref to SelfType` and is accessed with the arrow operator (`self->field`). Methods marked `ritual` are static/factory methods that take **no** `self` instance and are called on the type name.

```pengu
rune Vec2:
    x as float
    y as float

enchanting Vec2:
    # 1. Static ritual (factory / constructor) — no self
    weave ritual zero into Vec2:
        return with x is 0.0 and y is 0.0

    weave ritual create with x as float and y as float into Vec2:
        return with x is x and y is y

    # 2. Instance method returning a value
    weave add with other as Vec2 into Vec2:
        return with x is self->x + other.x and y is self->y + other.y

    # 3. In-place mutating instance method
    weave move with dx as float and dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into void:
    var origin as Vec2 is calling Vec2.zero
    var a as Vec2 is calling Vec2.create with 10.0 and 20.0
    var b as Vec2 is calling Vec2.create with 5.0 and 5.0

    let c as Vec2 is calling a.add with b      # value instance → &a passed to self
    calling a.move with 10.0 and 0.0
```

```c
typedef struct { float x; float y; } Vec2;

Vec2 Vec2_zero(void) {
    return (Vec2){ .x = 0.0f, .y = 0.0f };
}

Vec2 Vec2_create(float x, float y) {
    return (Vec2){ .x = x, .y = y };
}

Vec2 Vec2_add(Vec2* self, Vec2 other) {
    return (Vec2){ .x = self->x + other.x, .y = self->y + other.y };
}

void Vec2_move(Vec2* self, float dx, float dy) {
    self->x += dx;
    self->y += dy;
}

void main(void) {
    Vec2 origin = Vec2_zero();
    Vec2 a = Vec2_create(10.0f, 20.0f);
    Vec2 b = Vec2_create(5.0f, 5.0f);
    Vec2 c = Vec2_add(&a, b);
    Vec2_move(&a, 10.0f, 0.0f);
}
```

Safety rules enforced by the checker: accessing `self` inside a `ritual` method is rejected (`E0033`); calling a `ritual` method on an instance is rejected (`E0034`). Methods can also be attached to **primitive types** (`enchanting string:`, `enchanting list:`, `enchanting map:`, `enchanting slice:`, `enchanting maybe:`, `enchanting result:`); those methods keep their plain C names (never the module prefix) so they cannot collide with runtime primitives.

### 9.2 Scoped mutation `with target:`

```pengu
rune Player:
    x as int
    y as int
    health as int

enchanting Player:
    weave heal with amount as int into void:
        set self->health is self->health + amount

weave reset_player with p as ref to Player into void:
    with p:
        set.x is 100
        set.y is 200
        calling.heal with 50
```

```c
typedef struct { int32_t x; int32_t y; int32_t health; } Player;

void Player_heal(Player* self, int32_t amount) {
    self->health += amount;
}

void reset_player(Player* p) {
    p->x = 100;
    p->y = 200;
    Player_heal(p, 50);
}
```

`with target:` opens a block whose dot statements (`set.field …`, `calling.method …`) act on `target` without repeating its name. Do not confuse it with the `with field is value` struct initializer expression.

### 9.3 Concepts & `bind`

`concept` declares a contract of required instance methods and static `ritual` methods. `bind Type with Concept:` supplies the implementations and must satisfy the whole contract (missing method → `E0031`, signature mismatch → `E0030`).

```pengu
concept Drawable:
    weave draw into void
    weave ritual default_name into string

concept Printable:
    weave print_me into void

rune Circle:
    radius as float

rune Rectangle:
    width as float
    height as float

bind Circle with Drawable:
    weave draw into void:
        return

    weave ritual default_name into string:
        return "Circle"

bind Rectangle with Drawable:
    weave draw into void:
        return

    weave ritual default_name into string:
        return "Rectangle"

weave demo_concepts into void:
    var c as Circle is with radius is 5.0
    calling c.draw
    let name as string is calling Circle.default_name
```

```c
typedef struct { float radius; } Circle;
typedef struct { float width; float height; } Rectangle;

void Circle_draw(Circle* self) { return; }
PenguString Circle_default_name(void) { return pengu_string_from_cstr("Circle"); }

void Rectangle_draw(Rectangle* self) { return; }
PenguString Rectangle_default_name(void) { return pengu_string_from_cstr("Rectangle"); }

void demo_concepts(void) {
    Circle c = (Circle){ .radius = 5.0f };
    Circle_draw(&c);
    PenguString name = Circle_default_name();
}
```

### 9.4 Generics: `shard`, `of` & `where`

Type parameters are declared with `shard` and specialized with `of` (or inferred). Concept bounds use `where T: Concept`.

```pengu
concept Printable:
    weave print_me into void

rune Document:
    title as string

bind Document with Printable:
    weave print_me into void:
        return

# 1. Generic struct
rune Box shard T:
    item as T
    id as int

# 2. Multiple type parameters
rune Pair shard T and U:
    first as T
    second as U

# 3. Generic function with a concept bound
weave print_item shard T where T: Printable with item as T into void:
    calling item.print_me

weave create_box shard T with val as T and id as int into Box of T:
    return with item is val and id is id

weave main into void:
    var int_box as Box of int is calling create_box of int with 42 and 1
    var str_box as Box of string is calling create_box of string with "Pengu" and 2

    var doc as Document is with title is "PenguScript Reference"
    calling print_item with doc
```

```c
typedef struct { int32_t item; int32_t id; } Box_int;
typedef struct { PenguString item; int32_t id; } Box_string;
typedef struct { PenguString title; } Document;

void Document_print_me(Document* self) { return; }

Box_int create_box_int(int32_t val, int32_t id) {
    return (Box_int){ .item = val, .id = id };
}

Box_string create_box_string(PenguString val, int32_t id) {
    return (Box_string){ .item = val, .id = id };
}

void print_item_Document(Document item) {
    Document_print_me(&item);
}

void main(void) {
    Box_int int_box = create_box_int(42, 1);
    Box_string str_box = create_box_string(pengu_string_from_cstr("Pengu"), 2);
    Document doc = (Document){ .title = pengu_string_from_cstr("PenguScript Reference") };
    print_item_Document(doc);
}
```

Generics are monomorphized — one concrete C struct/function per specialization — so there is zero runtime abstraction cost. Generic runes/echos/omens/aliases/functions/concepts all accept `shard`, and `of T and U` supplies the arguments at use sites. Unfulfilled concept bounds are rejected at specialization time (`E0032`).

---

## 10. Composite & Nominal Types: `rune`, `echo`, `omen`, `seal`, `alias`, `opaque`

### 10.1 `rune` — structs

```pengu
rune Vec2:
    x as float
    y as float

weave struct_demo into void:
    var v as Vec2 is with x is 10.0 and y is 20.0
    let vx is v.x
    set v.x is 100.0

    var vp as ref to Vec2 is sigil of v
    set vp->x is 200.0          # '->' dereferences a ref to a struct
```

```c
typedef struct {
    float x;
    float y;
} Vec2;

void struct_demo(void) {
    Vec2 v = (Vec2){ .x = 10.0f, .y = 20.0f };
    float vx = v.x;
    v.x = 100.0f;
    Vec2* vp = &v;
    vp->x = 200.0f;
}
```

Struct initializers use `with field is value and …`. Element access is `.` on values and `->` on references.

### 10.2 `echo` — C-compatible unions

```pengu
echo Value:
    as_int as int
    as_float as float
```

```c
typedef union {
    int32_t as_int;
    float as_float;
} Value;
```

### 10.3 `omen` — enums & algebraic data types

Simple enums map to C `typedef enum`. Variants can carry explicit compile-time integer values (`Variant is expr`, auto-increment otherwise, duplicate values → `E0027`) or — with `omen Name with string:` — auto string values usable wherever a `string` is expected.

```pengu
omen Level:
    One is 3
    Two          # 4 (auto-increment)
    Three        # 5

omen Flags:
    None_ is 0
    Start is 10
    Next         # 11
    Shifted is 1 << 4    # 16

omen Color with string:    # string-valued omen: variant name is the value
    Red
    Green
```

```c
typedef enum Level {
  Level_One = 3,
  Level_Two = 4,
  Level_Three = 5,
} Level;

typedef enum Flags {
  Flags_None_ = 0,
  Flags_Start = 10,
  Flags_Next = 11,
  Flags_Shifted = 16,
} Flags;

#define Color_Red   pengu_string_from_cstr("Red")
#define Color_Green pengu_string_from_cstr("Green")
```

Variants with payloads turn the omen into an algebraic sum type — a C tag + union:

```pengu
omen NetworkState:
    Disconnected
    Connecting with retry_count as int
    Connected with session_id as string
    Failed with error_code as int and reason as string

weave demo_omen into void:
    var state as NetworkState is with Connected is with session_id is "sess_12345"
    var retry_state as NetworkState is with Connecting is with retry_count is 3
```

```c
typedef enum {
    NetworkState_Disconnected,
    NetworkState_Connecting,
    NetworkState_Connected,
    NetworkState_Failed
} NetworkState_Tag;

typedef struct {
    NetworkState_Tag tag;
    union {
        struct { int32_t retry_count; } Connecting;
        struct { PenguString session_id; } Connected;
        struct { int32_t error_code; PenguString reason; } Failed;
    } data;
} NetworkState;

void demo_omen(void) {
    NetworkState state = (NetworkState){
        .tag = NetworkState_Connected,
        .data.Connected = { .session_id = pengu_string_from_cstr("sess_12345") }
    };
    NetworkState retry_state = (NetworkState){
        .tag = NetworkState_Connecting,
        .data.Connecting = { .retry_count = 3 }
    };
}
```

Rules: payload variants cannot use `is <value>` (`E0028`); integer and string values cannot be mixed in one omen (`E0029`); string omens cannot carry payloads; duplicate values are rejected. Algebraic omens with payload fields are what `or:`-style error containers cannot represent directly — for that use the built-in `result of T to E` type (section 11).

### 10.4 Distinct nominal types: `seal`

`seal Name as T` creates a zero-overhead distinct type. Values of different seals — or of a seal and its underlying type — are never interchangeable without an explicit `to` cast (`E0035`):

```pengu
seal UserId as int
seal PostId as int

weave seal_demo into void:
    var user_id as UserId is 1001 to UserId
    var post_id as PostId is 2002 to PostId
    # set user_id is post_id      # Compile error E0035
    var raw_id as int is user_id to int
```

```c
typedef int32_t UserId;
typedef int32_t PostId;

void seal_demo(void) {
    UserId user_id = (UserId)(1001);
    PostId post_id = (PostId)(2002);
    int32_t raw_id = (int32_t)(user_id);
}
```

### 10.5 `alias`, `opaque` & function-pointer aliases

`alias Name as T` is a transparent synonym — an `alias Score as int` is interchangeable with `int`. `alias Name as opaque` declares an opaque handle whose real definition comes from an included C header; codegen emits only `typedef struct Name Name;`. Function-pointer aliases were covered in [8.5](#85-function-pointers).

```pengu
include "raylib.h"

alias Score as int              # transparent
alias Texture as opaque         # incomplete C struct from raylib.h

declare LoadTexture with path as string into Texture
declare UnloadTexture with texture as Texture into void
```

```c
#include "raylib.h"

typedef int32_t Score;
typedef struct Texture Texture;   // real definition comes from raylib.h

extern Texture LoadTexture(const char* path);
extern void UnloadTexture(Texture texture);
```

### 10.6 The `insignia` prefix directive

`insignia <PREFIX>` is a top-level directive that prefixes the **emitted C names** of every symbol declared *after* it in the same module file — `declare`, `weave`, `rune`, `echo`, `omen`, `alias`, `const`, and `enchanting` methods — while PenguScript sources keep the clean, unprefixed spelling. This is the workhorse of C-library bindings (`webui_*`, `raylib_*`, …).

- At most one `insignia` per module file (`E0026`).
- Position-dependent: declarations before it stay unprefixed.
- Enchanting methods on primitive types keep plain names regardless of prefix (see [9.1](#91-enchanting-receiver-blocks)).
- Calling `webui.show` translates to the C symbol `webui_show(...)`; declared constants also receive the prefix in their emitted C names (`webui_TIMEOUT`, …).

---

## 11. Optionals & Error Handling: `maybe`, `result` & `or`

### 11.1 `maybe T` — optional values

`maybe T` is an optional container: either *present* (holding a heap-copied value) or *absent*. Construct with `maybe none` or `some expr`; test with `is present` / `is not present`; unwrap with `.value` (only after a presence check) or `or else` / `or return`.

```pengu
weave find_user with id as int into maybe string:
    if id == 1:
        return some "Admin"
    return maybe none

weave test_maybe into void:
    let user as maybe string is calling find_user with 1

    # Presence check
    if user is present:
        let name is user.value
        calling spark.println with name

    # Fallback value
    let final_name is user or else "Guest"

    # Early return from the function on absence
    # let u is user or return 0

    # Handle absence with a block; 'error' is bound inside the block
    # let file is calling open_file with "data.txt" or:
    #     let err is error
    #     calling spark.println with err
    #     return
```

```c
// maybe T is the runtime PenguMaybe container; present values are heap copies.
PenguMaybe find_user(int32_t id) {
    if (id == 1) {
        // 'some "Admin"' — boxed:
        //   PenguMaybe _maybe; _maybe.is_present = true;
        //   _maybe.value = pengu_sigil_alloc(sizeof(PenguString));
        //   memcpy(_maybe.value, &tmp, sizeof(PenguString));
    }
    return pengu_maybe_none();
}

// 'user is present'          → pengu_maybe_is_present(&user)
// 'user.value' (present only) → (*(PenguString*)user.value)
```

`maybe T` appears throughout the standard library (file reads, parsing, environment lookups) and is the safe replacement for raw `null` pointers.

### 11.2 `result of T to E` — typed errors

The built-in result type is spelled `result of T to E` and lowers to `PenguResult` (`is_ok`, `ok_val`, `err_val`). It is typically given a name through `alias` and returned by FFI declarations or fallible operations:

```pengu
alias IntResult as result of int to string

declare may_fail into IntResult     # C extern returning PenguResult

weave main into void:
    var val as int is calling may_fail or:
        var err as string is error   # 'error' holds the failure message
        calling spark.println with err
        return
```

```c
void main(void) {
    PenguResult _res = may_fail();
    if (!pengu_result_is_ok(&_res)) {
        PenguString error = pengu_string_from_cstr(_res.err_val ? _res.err_val : "error");
        printf("%s\n", (error).data);
        return;
    }
    int32_t val = (int32_t)(_res.ok_val);
}
```

### 11.3 Unwrap operators

| Operator | Meaning | Applies to |
| -------- | ------- | ---------- |
| `expr or else fallback` | value when present/ok, otherwise the fallback expression | `maybe T`, `result of T to E` |
| `expr or return value` | bind the value on success; otherwise `return value` from the current function | `maybe T`, `result of T to E` |
| `expr or:` (block) | on failure run the block; inside it `error` is a `string` describing the error | `maybe T`, `result of T to E` |
| `try expr` | unwrap success values from error/maybe unions, propagating failures to the caller | `maybe T`, `result of T to E` |

Using any unwrap operator on a non-maybe/non-result expression is a type error (`E0005`).

---

## 12. Memory Model & Pointers

### 12.1 Pointers: `sigil of` and `essence of`

```pengu
weave memory_demo into int:
    var value as int is 42
    let ptr as ref to int is sigil of value   # &value
    set essence of ptr is 100                 # *ptr = 100
    return 0
```

```c
int32_t memory_demo(void) {
    int32_t value = 42;
    int32_t* ptr = &value;
    *ptr = 100;
    return 0;
}
```

### 12.2 `defer`, `errdefer`, `banish`

- `defer expr` — the expression runs when the enclosing scope exits, in LIFO order (the last deferred runs first).
- `errdefer expr` — runs only when the function returns an error path.
- `banish target` — deallocates a heap allocation (`pengu_banish`).

```pengu
declare malloc with size as int into ref to void
declare free with ptr as ref to void into void
declare CloseWindow into void

weave memory_demo into int:
    # 1. Allocation and null check
    var buffer as ref to char is calling malloc with 1024 to ref to char
    if buffer == null:
        return 1

    # 2. Defer accepts any expression or call (LIFO on scope exit)
    defer banish buffer
    defer calling CloseWindow

    # 3. Errdefer executes only on an error return from this function
    errdefer calling spark.println with "cleanup failed transaction"

    # 4. Pointer arithmetic & dereference
    var value as int is 42
    let ptr as ref to int is sigil of value
    set essence of ptr is 100

    return 0
```

```c
int32_t memory_demo(void) {
    char* buffer = (char*)malloc(1024);
    if (buffer == NULL) {
        return 1;
    }

    int32_t value = 42;
    int32_t* ptr = &value;
    *ptr = 100;

    // defers run at scope exit, reversed: CloseWindow(); free(buffer);
    CloseWindow();
    free(buffer);
    return 0;
}
```

### 12.3 Ownership & lifetime notes

- `maybe`/`result` present values are heap copies (`pengu_sigil_alloc` + `memcpy`), so they outlive the expression that created them; `maybe none` and error results carry no allocation. Treat the value reached through `.value` as data owned by the container.
- `bytes of <string>` returns a **borrowed** read-only pointer to the string's internal buffer — do not store it beyond the operand's lifetime (see [14.6](#146-passing-strings-to-c)).
- `static var` with non-constant initializers is guarded so it initializes exactly once.
- The checker runs escape-analysis passes over local references (see `tests/test_escape_analysis.py`), and mutable globals are impossible by construction, which keeps lifetimes local and deterministic.

---

## 13. Modules, Imports & Project Layout

### 13.1 Import forms

```pengu
# 1. Standard library modules (std/)
import std.spark
import std.scrolls as sc       # alias: sc.println style, C names unaffected

# 2. Project source modules (by path from the project root)
import components.player
import math.vec2

# 3. External binding packages (lib/<binding>/pengu/)
import webui
import raylib
```

An `import path as name` alias becomes the module symbol in the current scope; members are reached as `alias.member`. The alias must be a real identifier (not `_`) and must not collide with existing symbols (`E0036`). The alias never changes the emitted C name, which always comes from the module's own declarations (`insignia`, standard-library prefix, etc.).

Import resolution: `import raylib` looks for `raylib.pengu` first; if only `raylib.d.pengu` exists, the declaration file is used.

### 13.2 `include` and `link`

```pengu
include "stdio.h"     # emits #include; searches include/ and lib/*/include/
link "m"              # emits -l flags; searches lib/ and lib/*/lib/
link "pthread"
```

`include`/`link` directives may live at the top of any module, and are collected from imported modules into the final compile (`#include`s go into `bundle.c`, `link`s into the compiler flags). Identifiers coming from included C headers (macros, enums, GL constants, …) can be referenced transparently without re-declaring them (see [14.7](#147-transparent-c-identifiers)).

### 13.3 Declaration files (`.d.pengu`)

Analogous to TypeScript's `.d.ts`: a declaration file defines types, constants, C headers, linker flags and external function signatures (`declare`) **without** implementation bodies.

- **Allowed statements:** `include`, `link`, `import`, `insignia`, `const`, `rune`, `echo`, `omen`, `alias`, `seal`, `concept`, `declare`.
- **Forbidden:** function bodies — defining a `weave` body inside a `.d.pengu` file is compile error `E0025`.
- **No C redefinitions:** types and constants declared in `.d.pengu` exist for the LSP and semantic checker only; they do **not** emit C structs, unions, enums, typedefs, or `#define`s into `bundle.c` (the real definitions arrive through the `include`d native header).
- `declare` statements register signatures so calls translate directly to the native C functions; `insignia` supplies the C prefix.

Example binding (`lib/webui/pengu/webui.d.pengu`):

```pengu
include "webui.h"
link "webui-2-static"

insignia webui_

const TIMEOUT as int is 5000

rune WindowConfig:
    width as int
    height as int

declare new_window into int
declare show with win as int and content as string into void
declare wait into void
```

Consumed from project code:

```pengu
import webui

weave main into void:
    var win as int is calling webui.new_window
    calling webui.show with win and "Hello World"
    calling webui.wait
```

```c
#include "webui.h"

#define webui_TIMEOUT 5000
struct webui_WindowConfig {
  int32_t width;
  int32_t height;
};

int32_t webui_new_window(void);
void webui_show(int32_t win, PenguString content);
void webui_wait(void);

int pengu_main(void) {
  int32_t win = webui_new_window();
  webui_show(win, pengu_string_from_cstr("Hello World"));
  webui_wait();
  return 0;
}
```

### 13.4 Project layout

```
my_project/
├── pengu.yaml          # project metadata, build settings & dependencies
├── src/                # main PenguScript source files
│   └── main.pengu      # entry point (weave main into int:)
├── lib/                # external bindings & dependencies (pengu add)
│   └── webui/
│       ├── pengu/      #   PenguScript binding definitions (.pengu / .d.pengu)
│       ├── include/    #   C headers (.h)
│       ├── c/          #   C glue / wrapper sources (.c)
│       ├── lib/        #   precompiled native binaries (.a / .so / .dll / .lib)
│       └── build.py    #   optional build script run on 'pengu add'
├── include/            # project C headers
├── c/                  # project C glue sources
└── build/              # generated artifacts (bundle.c, binaries) — gitignored
```

Configuration (`pengu.yaml`, but `pengu.toml` and `pengu.json` are also accepted):

```yaml
project:
  name: "my_game"
  version: "0.1.0"
  entry: "src/main.pengu"
  output: "exe"            # exe | c | obj | static | shared
  output_name: "app"

build:
  src_dir: "src"
  lib_dir: "lib"
  include_dir: "include"
  c_dir: "c"
  build_dir: "build"
  includes: []             # extra global C includes, e.g. ["stdio.h"]
  links: []                # extra linker flags, e.g. ["m", "pthread"]
  lib_dirs: []
  include_dirs: []
  cflags: ["-Wall", "-std=c11"]
  ldflags: []
  defines: []
  cc: "gcc"

dependencies:
  webui:
    url: "https://github.com/webui-dev/webui"
    branch: "main"

profiles:
  debug:
    cflags: ["-g", "-O0", "-Wall"]
    defines: ["DEBUG"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: ["NDEBUG"]
```

When building, the builder collects headers from `include/` and `lib/*/include/` (`-I`), library archives from `lib/` and `lib/*/lib/` (`-L` with auto `-l`), compiles all C glue from `c/*.c` and `lib/*/c/*.c` together with `bundle.c`, and emits the artifact into `build/`.

### 13.5 Dependency management

```bash
# Add an external dependency / binding (git repo or local path)
pengu add https://github.com/webui-dev/webui
pengu add ../my_local_binding --name my_lib

# Update dependencies: git pull (configured branch) + re-run build scripts
pengu update

# Binding packages may ship build.py / build.bat / build.sh / a Makefile,
# executed automatically on 'pengu add' (skip with --no-build)
```

---

## 14. C Interop & FFI

### 14.1 `declare` — external C functions

```pengu
declare InitWindow with w as int and h as int and title as string into void
declare WindowShouldClose into bool
declare CloseWindow into void
declare malloc with size as int into ref to void
declare free with ptr as ref to void into void
```

```c
extern void InitWindow(int32_t w, int32_t h, const char* title);
extern bool WindowShouldClose(void);
extern void CloseWindow(void);
extern void* malloc(int32_t size);
extern void free(void* ptr);
```

`declare` never emits a body; the symbol is resolved by the linked C library. Parameters map through the type table in [4.2](#42-primitive-mapping-to-c).

### 14.2 Struct & union layout

`rune`/`echo` map 1:1 to C `struct`/`union`, so native structures can be declared (or bound with `pengu bind`) and passed by value or reference. Struct values passed to C functions keep their C layout, including `ref to` fields. Opaque C structs are declared `alias Name as opaque` (section 10.5) and handled through pointers, which is the recommended pattern for C handles (`Texture`, `WebUI` windows, regex/sqlite handles, …).

### 14.3 Out-parameters

Native functions that return values through pointer parameters take `ref to T`; pass the address of a local with `sigil of`:

```pengu
declare yaml_get_version with major as ref to int and minor as ref to int and patch as ref to int into void

weave main into void:
    var ma as int is -1
    var mi as int is -1
    var pa as int is -1
    calling yaml_get_version with (sigil of ma) and (sigil of mi) and (sigil of pa)
```

### 14.4 Fixed byte buffers as C output

Declare a fixed-size `array of byte` and borrow its storage with `bytes of` so C can fill it:

```pengu
declare hash_bytes with data as ref to byte and len as int into i64

weave digest with msg as string into i64:
    var view as ref to byte is bytes of msg     # borrow msg's internal bytes
    return calling hash_bytes with view and (msg length)
```

```c
int64_t digest(PenguString msg) {
    // bytes of <string>  → ((uint8_t*)((msg).data))
    // bytes of <byte array> → &(buf)[0]  (writable, for output buffers)
    uint8_t* view = ((uint8_t*)((msg).data));
    return hash_bytes(view, msg.len);
}
```

`bytes of`:

- On a `string` yields a **read-only** `ref to byte` pointing at the string's internal character storage — no copy.
- On an `array of byte` variable yields a **writable** `ref to byte` to the first element (e.g. an output buffer filled by C).
- Accepts string literals, string variables, and `array of byte` variables; any other operand is rejected at compile time. The pointer is **borrowed** — do not store it beyond the operand's lifetime.

### 14.5 Struct-to-C `ref` parameters & callbacks

References (`ref to T`) are passed as pointers, enabling in-place mutation from C and efficient `self` receivers for methods ([9.1](#91-enchanting-receiver-blocks)). Weaves can be handed to C as function pointers: a `weave` name decays to its C function pointer wherever a callback alias is expected ([8.5](#85-function-pointers)). The runtime also provides helpers (such as `pengu_call_callback_int` and the minicoro shim in `std_c/wrappers_minicoro.c`) that let C call back into PenguScript weaves, and a PenguScript weave can be used as a minicoro coroutine body — see `std/minicoro.d.pengu` and `std_c/`.

### 14.6 Passing strings to C

| C parameter type | PenguScript spelling | Emission |
| ---------------- | -------------------- | -------- |
| `const char*` / `char*` | `ref to char` | string **literals** become plain C literals; interpolation is rejected |
| byte pointer + length | `ref to byte` + `int` | runtime string variables pass `bytes of <string>` (read-only, NUL-terminated buffer) |

### 14.7 Transparent C identifiers

Identifiers from an `include`d header (raylib constants, OpenGL macros, C enums) are usable directly without re-declaring them:

```pengu
include "raylib.h"

weave configure_window into void:
    let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
    let key is KEY_SPACE
```

```c
#include "raylib.h"

void configure_window(void) {
    int32_t flags = FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT;
    int32_t key = KEY_SPACE;
}
```

### 14.8 C header → PenguScript bindings: `pengu bind`

`pengu bind <header.h>` preprocesses a C header (with line markers retained) and emits a `.d.pengu` declaration file, so existing C libraries can be called from PenguScript quickly. The generated file contains, in order:

1. `include "<header>"` plus the `link "…"` lines;
2. numeric/string `#define` constants as `const … as i64/string is …`;
3. types — `rune` (struct), `echo` (union), `omen` (enum with explicit values), simple typedefs as `alias … as …`, function-pointer typedefs as `alias … as ref to weave with … into …`;
4. the `insignia <prefix>` directive (a prefix already spelled on the C functions is stripped so it is not doubled);
5. one `declare name with p as T, … into R` per function.

Type mapping highlights: `size_t`→`size_t`, `bool`→`bool`, `int`/`uint32_t`→`int`/`u32`, `long long`→`i64`, `unsigned char`→`byte`, `float`/`double`→`f32`/`f64`, `char*`/`const char*`→`ref to char`, `T*`→`ref to T`, `void*`→`ref to void`. `##` doc comments are extracted from the source header above each declaration.

```bash
pengu bind webui.h --prefix webui_ --links webui-2-static ole32 stdc++ uuid
```

The preprocessor pass keeps line markers so pycparser can attribute every node to the original header; nodes pulled in from system/stub headers are skipped. A vendored minimal stub tree in `c_bind_stubs/` supplies `stdint.h`/`stddef.h`/`stdbool.h`/… types, and Windows-guarded sections are excluded by default. `--no-cpp` parses without preprocessing for very simple headers.

The output is declaration-only: the real header stays `include`d, so no C structs/enums/prototypes are duplicated and the binding passes `pengu check`.

---

## 15. Standard Library

### 15.1 Architecture

The standard library lives under `std/` and is written in PenguScript. High-level logic — string search/slicing/trimming/splitting/case mapping & ASCII classification, Base64/JSON, CSV/TSV, path manipulation, range/collection helpers, CLI parsing, assertions, test runners, logging composition — is pure PenguScript compiled through the normal pipeline. Only true byte/memory primitives (string allocation/concat/equality, list/map/maybe/result operations) and platform or external-library backends (stdio & console, file system, time, rand, processes/environment, PCRE2, libxml2, curl/microhttpd, mbedTLS/zlib hashing) remain in the C runtime (`pengu_runtime.h` static-inline primitives plus `pengu_runtime.c` externs) and are reached via `declare`. The migration was unlocked by the keyword primitives `some`, `ord`, `chr`, and `bytes of` (sections 6.3 & 14.4) plus the `insignia pengu_` module prefix for module-level weaves.

`std/spark.pengu` defines `SPARK_VERSION` and `STD_VERSION` constants; `spark.spark_version` returns the version string.

### 15.2 Core module catalog (24 modules)

| Module | Import | Implementation | Purpose & key functions |
| ------ | ------ | -------------- | ----------------------- |
| **spark** | `import std.spark` | C runtime + Pengu wrappers | Core runtime & terminal I/O: `print`, `println`/`print_line`, `eprint_line`, `input`, `panic`, `assert`/`assert_msg`, conversions (`str_int`, `str_float`, `str_bool`, `parse_int`, `parse_float`), `len_string`, `range`, `spark_version`. |
| **scrolls** | `import std.scrolls` | Pure PenguScript | Full string API: `contains`, `starts_with`, `ends_with`, `index_of`, `last_index_of`, `substring`, `char_at`, `trim`/`trim_start`/`trim_end`, `replace`, `split`, `repeat`, `reverse`, `len`, `is_empty`, ASCII case & classification (`lower`, `upper`, `is_alpha`, `is_digit`, `is_alnum`) via `ord`/`chr`. Enchants `string` (`calling s.trim`). |
| **oracle** | `import std.oracle` | Pure PenguScript | Optional/result value types: `MaybeInt`, `MaybeFloat`, `MaybeString`, `ResultInt`, `ResultString` with constructors (`maybe_some_int`, `maybe_none_string`, `result_ok_int`, `result_err_string`, …) and methods `is_present`, `is_none`, `unwrap`, `unwrap_or`, `is_ok`, `is_err`. |
| **tally** | `import std.tally` | Pure PenguScript | Dynamic list utilities: `is_empty`, `sum`, `max_val`, `min_val`, plus element indexing and transformations. |
| **atlas** | `import std.atlas` | Pure PenguScript | Hash map helpers over the built-in `map of K to V` (`map_len_str_int`, …). |
| **coven** | `import std.coven` | Pure PenguScript | Unique set collections `SetString`/`SetInt` (`new_set_string`, `new_set_int`) with `add`, `contains`, `remove`, `len`, `clear`, `is_empty`. |
| **compass** | `import std.compass` | Pure PenguScript | Cross-platform path handling + the `Path` value type: `join`/`join_all`, `basename`, `dirname`, `ext`, `stem`, `suffixes`, `has_ext`, `normalize`, `parent`, `split`, `is_absolute`/`is_relative`, `drive`, `separator`, `change_ext`, `add_ext`, `relative_to`; platform semantics via `when os == "windows"`. |
| **archivum** | `import std.archivum` | C primitives + Pengu sugar | File system: `read_file` (→ `maybe string`), `write_file`, `append_file`, `delete_file`, `exists`, `is_file`/`is_dir`/`is_symlink`, `create_dir`, `remove_dir`, `read_dir`, `copy_file`, `move_file`, `rename`, `glob`, `walk`, `touch`, `symlink`, `realpath`, metadata, plus pure-Pengu recursive `copy_tree` and `list_files_recursive`. |
| **arithmancy** | `import std.arithmancy` | C math + pure int helpers | Math: constants `PI`/`TAU`/`E`, `abs`/`abs_i`, `sqrt`, `pow`, `floor`, `ceil`, `round`, `trunc`, `fmod`, `sin`/`cos`/`tan`/`asin`/`acos`/`atan`/`atan2`, `exp`, `log`/`log10`/`log2`, hyperbolic family; pure `is_prime`, `gcd`, `lcm`. |
| **chronicle** | `import std.chronicle` | C primitives | Time & date: `time`, `monotonic`, `sleep_ms`, `sleep`, `format`, `format_now`, `parse`, UTC/local field getters (`utc_year`…, `local_year`…), stopwatch helpers. |
| **lot** | `import std.lot` | C primitives | Randomness: `seed`, `rand_int`, `rand_float`, `rand_range`, `rand_range_float`, `rand_normal`, `rand_exp`, `rand_bool`, `rand_poisson`, plus collection shuffling. |
| **rites** | `import std.rites` | C primitives | OS & system: `getenv`, `setenv`, `unsetenv`, `get_argc`/`get_argv`/`get_args`, `getpid`, `getppid`, `getcwd`, `chdir`, `exit`, `exec`, `spawn`, `uname`, `hostname`. |
| **invoke** | `import std.invoke` | Pure PenguScript | CLI argument parsing: `new_parser`, `add_positional`, `add_option`, `add_flag`, `print_help`, `parse`, `get`, `get_or`, `is_set`, `is_ok`, `is_err`. |
| **ledger** | `import std.ledger` | Pure PenguScript | CSV/TSV: `escape_field`, `parse_line`, `parse_csv`, `to_csv_string`, `detect_delimiter`, TSV variants, and file helpers `read_csv`/`write_csv`/`read_tsv`/`write_tsv`. |
| **cipher** | `import std.cipher` | Pure PenguScript | JSON + Base64: `parse_json`, `stringify_json`, `pretty_json`, `encode_base64`, `decode_base64`, `is_base64`, value-level `parse_value`/`stringify_value`, file helpers. |
| **parchment** | `import std.parchment` | libxml2 backend | XML/HTML DOM: `parse_xml`, `parse_html`, `find`, `find_all`, `attr`, `set_attr`, `text`, `set_text`, `create_element`, `create_text`, `append_child`, serialization (`to_string`, `doc_to_string`, `escape_text`). |
| **regulus** | `import std.regulus` | PCRE2 backend | Regular expressions: `compile`, `is_match`, `is_full_match`, `search`, `match`, `find_all`, `replace`, `split`, `escape`, `is_valid`, `quick_match`, `quick_replace`; `Match`/`Regex` value types. |
| **seal** | `import std.seal` | mbedTLS/zlib backend | Hashing & compression: `crc32`, `md5`, `sha1`, `sha256`, `sha512` (+ `*_file` variants), `gzip`/`unzip`, zlib `compress`/`decompress` (file helpers included). |
| **precis** | `import std.precis` | libcurl/microhttpd backend | Networking: HTTP client `get`/`post`/`put`/`delete`/`request`, embedded HTTP server (`serve_http`, `response`, `serve_file`), TCP sockets (`connect_tcp`, `tcp_send`, `tcp_recv`, `tcp_close`, `dns_lookup`), `url_encode`/decode; `ClientResponse`/`Request` types. |
| **filum** | `import std.filum` | C primitives | Concurrency: `mutex`/`lock`/`unlock`/`try_lock`, `wait_group` (`add`, `done`, `wait`), `once`, channels, thread spawn, condition variables, atomics (opaque-handle value types). |
| **loom** | `import std.loom` | Pure PenguScript | Functional collection utilities: `range`, `repeat`, `take`, `skip`, `chain`, `chunks`, `windows`, `sum`, `product`, `max`/`min`, plus map/filter/reduce style helpers and zip/flattening. |
| **ward** | `import std.ward` | Pure PenguScript | Assertions & invariants: `assert`, `assert_msg`, `assert_true`/`assert_false`, `assert_eq_*` / `assert_ne_*` (int/string/bool), `assert_present_*`/`assert_none_*`, `assert_ok_*`/`assert_err_*`, `expect*` message variants, `panic`, `unreachable`, and result-returning `check*` helpers. |
| **trial** | `import std.trial` | Pure PenguScript | Unit-test framework: re-exports `ward` assertions, plus suites (`new_suite`), `test_case`/`test`, lifecycle hooks and colored reporting (`summary`). |
| **whisper** | `import std.whisper` | C primitives + Pengu | Structured logging: `set_level`, `get_level`, `get_level_name`, level constants `LOG_TRACE`…`LOG_FATAL`, and level loggers `trace`, `debug`, `info`, `warn`, `error`, `fatal`. |

### 15.3 Integrated external libraries

`build_runtime.py` compiles static libraries into `build/lib/` (headers staged in `build/include/`); a project whose `links` include `pengu_runtime` auto-links whatever is present in `build/lib`. Their PenguScript bindings live in `std/` as `.d.pengu` declaration modules.

| Library | Lib file | Pengu module (`import`) | Purpose |
| ------- | -------- | ----------------------- | ------- |
| SQLite3 3.53.4 | `libsqlite3.a` | `import std.sqlite3` | Embedded SQL database |
| Raylib 6.0 | `libraylib.a` | `import std.raylib` | Graphics / audio / game dev |
| WebUI 2.5.0-beta.3 (prebuilt) | `libwebui.a` | `import std.webui` | Native web-UI windows |
| stb_image | `libpengu_stb.a` | `import std.imago` | PNG/JPEG decode |
| stb_image_write | `libpengu_stb.a` | `import std.scriptor` | Image encode (PNG/JPG/…) |
| stb_truetype | `libpengu_stb.a` | `import std.typis` | TTF/OTF font rasterization |
| stb_rect_pack | `libpengu_stb.a` | `import std.pactum` | Rectangle packing |
| stb_ds | `libpengu_stb.a` | `import std.datastructura` | Typed hash maps / dynamic arrays |
| stb_perlin | `libpengu_stb.a` | `import std.perlinum` | Perlin noise |
| nanosvg / nanosvgrast | `libpengu_stb.a` | `import std.nanosvg` / `import std.nanosvgrast` | SVG parse / rasterize |
| stb_image_resize2 | header only | `import std.stb_image_resize2` (`insignia stbir_`) | Image resize/resample |
| stb_herringbone_wang_tile | header only | `import std.stb_herringbone_wang_tile` (`insignia stbh_`) | Wang-tile textures |
| xxHash (~0.8.3-era dev) | `libpengu_stb.a` | `import std.xxhash` (raw) / `import std.celeris` (wrapper) | Fast non-cryptographic hashing |
| uuid.h 0.1 (wc-duck/uuid_h) | `libpengu_stb.a` | `import std.uuid` (declarations; drive from C) | UUID v4 / null generation, parse, format |
| minicoro | `libpengu_stb.a` | `import std.minicoro` (declarations; drive from C) | Stackful asymmetric coroutines |
| tinyfiledialogs 3.21.3 | `libpengu_stb.a` | `import std.fenestra` (tinyfd binding) | Native message/open/save dialogs |
| raygui 5.0 | `libpengu_stb.a` | use with `import std.raylib` | Immediate-mode raylib GUI controls |
| miniaudio 0.11.25 | declaration only | `import std.miniaudio` | Audio (curated subset; no device APIs) |
| rlights (RLG_) | declaration only | `import std.rlights` | raylib lighting framework |
| xlsxio 0.2.36 | `libxlsxio_write.a` + `libxlsxio_read.a` | `import std.xlsxio` (raw) / `import std.xlsx` (pure write wrapper) | Real `.xlsx` spreadsheet writing (opt-in) |
| libyaml 0.2.5 | `libyaml.a` | `import std.yaml` | YAML 1.1 (version query bound; parsing stays C-level) |
| libcyaml 1.4.2 | `libcyaml.a` | (C-level only) | Schema-driven YAML struct binding |
| tomlc17 | `libtomlc17.a` | `import std.tomlum` | TOML validity shim (`pengu_toml_valid` / `pengu_toml_valid_file`) |
| libzip 1.11.3 / libexpat 2.6.4 | `libzip.a` / `libexpat.a` | (C-level dependencies of xlsxio) | Zip archives / XML parsing |
| libuv 1.52.1 | `libuv.a` | (no binding yet) | Async I/O / event loop |

> libwebsockets 4.5.1 was evaluated but is **not part of the project**: the 2023-era
> sources do not build cleanly with modern GCC (vendored win32 zlib + `-Werror`
> trips), so it was removed from `extern_manifest.py` / the extern directory rather
> than shipped half-broken.

Notes:

- The STB single headers are vendored in `std_c/` under Latin names (`imago.h`, `scriptor.h`, `typis.h`, …). Their `*_IMPLEMENTATION` units — plus xxhash, uuid, minicoro, raygui, tinyfiledialogs and tinyfd_moredialogs — are compiled each from its own translation unit (`std_c/wrappers_*.c`) into `libpengu_stb.a`, so the archive stays independently linkable (a program that only calls xxhash does not pull in raylib/BCrypt symbols).
- Bindings are `pengu bind` output or hand-curated declaration files, verified with `pengu check`.
- miniaudio and rlights are bound declarations only (no implementation archive is built: audio needs a device/backend, rlights needs raylib + OpenGL at runtime, and the resize2/herringbone headers need their own `*_IMPLEMENTATION` wrapper `.c` when used).
- `std/celeris` wraps `std/xxhash` with one-shot helpers (`hash32`, `hash64`, `hash3_64`, `hash3_128` and `*_seeded` variants). PenguString *variables* cannot yet be passed where a C byte pointer is expected, so hashing helpers take `ref to char` plus an explicit byte `length`.
- `std/archivum` additionally exposes pure recursive `copy_tree` and `list_files_recursive`.

---

## 16. Language Server & Tooling

### 16.1 Running the LSP

```bash
pengu lsp --stdio                 # standard I/O (default)
pengu lsp --tcp --host 127.0.0.1 --port 2087
python -m pengu_lsp               # from a source checkout
```

### 16.2 LSP features

- **Diagnostics.** Rust-style errors with `error[CODE]`, `help:` and `note:` text, reported live as you type.
- **Contextual completion.** After `when` it offers the compile-time variables (`main`, `os`, `arch`, `compiler`, `defined(...)`) and literals; after `as` / `into` it offers every built-in type plus project runes/echos/omens/aliases/seals and generic runes; module members complete through imported aliases too.
- **Hover.** Type signatures with memory sizes (bits/bytes) and the `##` documentation of the symbol. When a symbol has no doc attached, the doc block directly above its declaration is read from its source file (works for standard library symbols too).
- **Go to definition.** Local symbols, imported-module members and stdlib modules resolve to their source file and line (e.g. `spark.println` jumps to `std/spark.pengu`).
- **Code actions.** *Add missing import* — with the cursor on an undefined identifier, a cached stdlib + project symbol index finds the exporting module and inserts `import …` after existing imports (or at the top of the file).

### 16.3 `pengu fmt`

`pengu fmt` formats files/directories (recursively) with the same engine as the LSP formatter (`pengu_lsp/formatting.py`): 2-space indentation by default, `--indent N` / `--tabs` to change it, `--check` to verify without writing (exit 1 when changes are needed), `--verbose` to list every file considered.

### 16.4 VS Code extension

The official extension (`pengus-*.vsix`, built by `make_release.py`) adds:

- Formal TextMate **syntax highlighting** (keywords include `when`, `test`, `static`, `omen … with string`, `defined`, `bytes of`, …),
- live LSP diagnostics, contextual hovers with byte-size annotations,
- module-scoped autocompletion, go-to-definition,
- project commands (Build / Run / Clean / Init) from the Command Palette,
- snippets for `test`, `when`, `static var`, map literals and `import … as`.

Install from the **Extensions** panel → *Install from VSIX…* → select the built `pengus-*.vsix`.

### 16.5 Documentation generation

`##` doc comments plus inferred signatures (parameters, return type, fields, constants, variant values) feed `pengu doc`, which writes a Markdown reference site — `index.md` plus one page per module — under `<project>/docs` (or `-o path`).

---

## 17. CLI Reference

### 17.1 Subcommands

| Command | Description |
| ------- | ----------- |
| `pengu init NAME` | Create a new Cargo-style project template |
| `pengu add SOURCE` | Add an external dependency/binding (git URL or local folder) |
| `pengu build` | Compile the project according to its configuration |
| `pengu run [FILE.pengu]` | Build and execute the project target, or run a standalone script |
| `pengu test` | Compile in `--test` mode and run integrated `test` blocks |
| `pengu check` | Parse and type-check every module; no code generation (CI) |
| `pengu fmt PATHS…` | Format files/directories with the standard style |
| `pengu update` | Update dependencies: `git pull` + re-run dependency build scripts |
| `pengu bind HEADER.h` | Generate a `.d.pengu` binding from a C header |
| `pengu clean` | Remove the build directory and generated artifacts |
| `pengu lsp` | Launch the Language Server Protocol server |
| `pengu doc` | Generate Markdown documentation from `##` comments |

### 17.2 Options by command

| Command | Flags |
| ------- | ----- |
| `init` | `--type/-t exe\|c\|obj\|static\|shared` (default `exe`), `--links/-l`, `--output-name`, `--cc` (default `gcc`) |
| `add` | `--branch/-b`, `--name/-n`, `--config/-c`, `--no-build` |
| `build` | `--profile/-p debug`, `--config/-c`, `--entry/-e`, `--output/-o`, `--test`, `--cc`, `--verbose`, `-D/--define` (repeatable) |
| `run` | `script` (optional), `--profile/-p`, `--config/-c`, `--entry/-e`, `--test`, `--cc`, `--verbose`, `-D/--define` |
| `test` | `--profile/-p`, `--config/-c`, `--entry/-e`, `--cc`, `--verbose`, `-D/--define` |
| `check` | `--profile/-p`, `--config/-c`, `--entry/-e`, `--cc`, `--verbose`, `-D/--define` |
| `fmt` | `paths…`, `--check`, `--write` (default), `--indent N` (default 2), `--tabs`, `--verbose` |
| `update` | `--config/-c`, `--verbose` |
| `bind` | `header`, `--prefix`, `--links …`, `--output`, `--no-comments`, `--ignore …`, `--include-paths …`, `--no-cpp` |
| `clean` | `--config/-c` |
| `lsp` | `--stdio` (default), `--tcp`, `--host` (default `127.0.0.1`), `--port` (default `2087`) |
| `doc` | `--config/-c`, `--entry/-e`, `--output/-o` (default `<project>/docs`) |

`-D` defines feed the compile-time `when` environment: plain `-D NAME` sets `defined(NAME)`; `-D os=…`, `-D arch=…`, `-D compiler=…`, and `-D main` override the context variables (repeatable).

### 17.3 Behavior notes

- `build`/`run`/`test`/`check`/`update`/`fmt` accept `--verbose`, which prints the resolved module order, phase timings (semantic check / codegen), every C command executed, and per-file progress.
- `--cc` overrides the compiler configured in `pengu.yaml`; it also steers `when compiler`.
- C-compilation failures raise a formatted error including the exact compiler command and full stdout/stderr (no raw traceback) and exit with status 1.
- `check` reports one `file:line:col [CODE] message` per problem and exits non-zero when anything fails; it never writes `bundle.c`.
- `run FILE.pengu` compiles the file (plus imports) into `build/` with `main=true` for the script and executes it; plain project builds default to `main=false`.

### 17.4 Output types

| `--type` | Output artifact |
| -------- | --------------- |
| `exe` | `build/app.exe` / `build/app` |
| `c` | `build/bundle.c` (pure bundled C) |
| `obj` | `build/<name>.o` |
| `static` | `build/lib<name>.a` |
| `shared` | `build/<name>.dll` / `.so` / `.dylib` |

---

## 18. Building from Source & Release Packaging

### 18.1 From a source checkout

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # lark, pygls, pycparser>=2.21, pytest, …
pytest tests/                      # full test suite
```

The compiler itself is pure Python; no C build is needed just to translate and run PenguScript code (the C compiler still compiles the emitted `bundle.c`).

### 18.2 Release pipeline

```bash
python make_release.py
```

`make_release.py` orchestrates the full release:

1. `extern_manifest.py` downloads the pinned external C libraries into `extern/`;
2. `build_runtime.py` compiles and installs the C runtime and every integrated static library into `build/lib/` (`libpengu_runtime.a`, `libpengu_stb.a`, `libsqlite3.a`, `libraylib.a`, `libwebui.a`, xlsxio/zlib/expat/yaml/tomlc17 archives, …) with headers staged in `build/include/` — idempotent and `--rebuild`-aware;
3. PyInstaller packages the standalone `pengu` / `pengu.exe` CLI + LSP (including `pycparser` and `c_bind_stubs/` so `pengu bind` works inside the frozen executable);
4. the VS Code extension is built as `pengus-<version>.vsix`.

The distribution lands in `pengucc_build/`:

```
pengucc_build/
├── pengu (.exe)              # Standalone PenguScript CLI & LSP
├── pengus-<version>.vsix     # VS Code extension
├── std/                      # Standard library (PenguScript sources)
└── runtime/                  # C runtime headers + libpengu_runtime.a
```

### 18.3 Platform notes

- Windows, Linux and macOS are all supported end to end; `gcc`, `clang` and `msvc` are valid `cc` choices.
- Compile-time `when os == "…"` / `arch` / `compiler` branches let bindings and stdlib modules adapt per platform (`std/raylib.d.pengu` links `opengl32`/`gdi32` on Windows vs `GL`/`dl`/`rt`/`X11` elsewhere).
- `build_runtime.py` links the Windows UI platform libraries (`-lopengl32 -lgdi32 -lole32 -luuid -lshell32`) automatically when it sees the corresponding archives in `build/lib`.
- On Linux/macOS `build_runtime.py` skips the Windows-tuned static builds of libxml2/libcurl/libmicrohttpd and the C runtime links the system libraries instead (see `README.md` → *Building the Runtime from Source*); libuv 1.52.1 is built and its headers staged, but no PenguScript binding exists yet. libwebsockets is not part of the project (see the §15 note).

---

## 19. Example Gallery

### 19.1 Hello, world (project)

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, PenguScript"
    return 0
```

```bash
$ pengu run
Hello, PenguScript
```

### 19.2 Structs, methods & collections

```pengu
import std.spark

rune Player:
    name as string
    score as int

enchanting Player:
    weave label into string:
        return self->name + " (" + (self->score to string) + ")"

weave best with players as list of Player into maybe Player:
    var found as bool is false
    var top as Player is with name is "" and score is -1
    for p in players:
        if found == false:
            set top is p
            set found is true
        else if p.score > top.score:
            set top is p
    if found:
        return some top
    return maybe none

weave main into int:
    var roster as list of Player is list of Player
    calling roster.push with with name is "Ada" and score is 9
    calling roster.push with with name is "Grace" and score is 10
    calling roster.push with with name is "Linus" and score is 7

    let winner as maybe Player is calling best with roster
    if winner is present:
        let top as Player is winner.value
        calling spark.println with "winner: " + calling top.label
    else:
        calling spark.println with "no players"

    var scores as map of string to int is { "Ada": 9, "Grace": 10 }
    calling scores.set with "Linus" and 7
    if calling scores.has with "Grace":
        calling spark.println with "Grace is in the scores map"
    return 0
```

```bash
$ pengu run
winner: Grace (10)
Grace is in the scores map
```

### 19.3 Maybe, `or:` and result unwrapping

```pengu
import std.spark

alias IntResult as result of int to string

weave safe_divide with a as int and b as int into maybe int:
    if b == 0:
        return maybe none
    return some (a / b)

weave main into int:
    let q as maybe int is calling safe_divide with 10 and 2
    if q is present:
        calling spark.println with "10 / 2 = " + (q.value to string)
    let fallback is q or else -1
    calling spark.println with "fallback: " + (fallback to string)
    return 0
```

```bash
$ pengu run
10 / 2 = 5
fallback: 5
```

### 19.4 File I/O with the standard library

```pengu
import std.spark
import std.archivum

weave main into int:
    var ok as bool is calling archivum.write_file with "out.txt" and "PenguScript"
    if ok == false:
        calling spark.println with "write failed"
        return 1

    let content as maybe string is calling archivum.read_file with "out.txt"
    if content is present:
        calling spark.println with content.value
    else:
        calling spark.println with "read failed"
        return 1
    return 0
```

```bash
$ pengu run
PenguScript
```

### 19.5 Methods, concepts & algebraic omens

```pengu
import std.spark

rune Vec2:
    x as float
    y as float

enchanting Vec2:
    weave ritual origin into Vec2:
        return with x is 0.0 and y is 0.0

    weave len_squared into float:
        return self->x * self->x + self->y * self->y

omen Direction:
    North with dy as int
    South with dy as int
    East with dx as int
    West with dx as int

weave main into int:
    let a as Vec2 is calling Vec2.origin
    var b as Vec2 is with x is 3.0 and y is 4.0
    calling spark.println with "dist² = " + (calling b.len_squared to string)

    var move as Direction is with North is with dy is -1
    calling spark.println with "move chosen"
    return 0
```

```bash
$ pengu run
dist² = 25
move chosen
```

### 19.6 Standalone script with `when main`

```pengu
# greet.pengu
import std.spark

weave greet with name as string into void:
    calling spark.println with "Hello, " + name + "!"

when main:
    weave main into int:
        calling greet with "Pengu"
        return 0
```

```bash
$ pengu run greet.pengu
Hello, Pengu!
```

### 19.7 Native window with the Raylib binding

Requires `libraylib.a` built by `build_runtime.py` (see section 15.3).

```pengu
import std.raylib          # calling raylib.InitWindow / raylib.BeginDrawing / ...
import std.spark

const SCREEN_WIDTH as int is 800
const SCREEN_HEIGHT as int is 600

rune Player:
    x as float
    y as float
    speed as float

enchanting Player:
    weave update into void:
        if calling raylib.IsKeyDown with KEY_RIGHT:
            set self->x is self->x + self->speed
        if calling raylib.IsKeyDown with KEY_LEFT:
            set self->x is self->x - self->speed

    weave draw into void:
        calling raylib.DrawCircle with (self->x to int) and (self->y to int) and 20.0 and MAROON

weave main into int:
    calling raylib.InitWindow with SCREEN_WIDTH and SCREEN_HEIGHT and "PenguScript 2D Game"
    defer calling raylib.CloseWindow
    calling raylib.SetTargetFPS with 60

    var player as Player is with x is 400.0 and y is 300.0 and speed is 5.0

    while calling raylib.WindowShouldClose is false:
        calling player.update
        calling raylib.BeginDrawing
        calling raylib.ClearBackground with RAYWHITE
        calling player.draw
        calling raylib.EndDrawing
    return 0
```

(Colors such as `MAROON`/`RAYWHITE`, key constants and other raylib identifiers are either `const` values or transparent identifiers from the included `raylib.h` — see sections 10.5 and 14.7.)

### 19.8 Hash a string with xxHash via `std.celeris`

```pengu
import std.spark
import std.celeris

weave main into int:
    # xxHash one-shots: pass a string literal + explicit byte length
    var h64 as u64 is calling celeris.hash64 with "PenguScript" and 11
    var h3 as u64 is calling celeris.hash3_64 with "PenguScript" and 11
    if h64 == 0x610DF71A00097754:
        if h3 == 0xC5617D8EE18E0403:
            calling spark.println with "xxhash + celeris ok"
    return 0
```

---

## 20. Keywords at a Glance

### 20.1 Declarations & modules

| Keyword | Purpose |
| ------- | ------- |
| `import path [as name]` | Import a module (std library, project, or binding) |
| `include "header.h"` | Emit a C `#include` |
| `link "lib"` | Emit a C `-l` link flag |
| `insignia PREFIX_` | Prefix subsequent emitted C names |
| `const NAME as T is expr` | Top-level compile-time constant |
| `var` / `let` | Mutable / immutable local binding |
| `static var` | Function-static mutable binding |
| `set target is expr` | Reassign / mutate |
| `rune NAME:` | Struct declaration |
| `echo NAME:` | C-union declaration |
| `omen NAME:` | Enum / algebraic sum type |
| `alias NAME as T` | Transparent type synonym |
| `seal NAME as T` | Distinct nominal newtype |
| `concept NAME:` / `bind T with C:` | Interface contract / implementation |
| `enchanting T:` | Method receiver block |
| `weave` / `declare` | Function definition / C function declaration |
| `shard T` / `where T: C` / `of T` | Generics: parameters, bounds, specialization |
| `test "name":` | Integrated unit test (compiled with `--test`) |

### 20.2 Statements & flow

| Keyword | Purpose |
| ------- | ------- |
| `if` / `else` / `unless` | Conditionals (with `if a then b else c` ternary form) |
| `while cond:` | Loop while condition holds |
| `for i from a to b [step s]:` | Numeric range loop |
| `for [i,] v in col:` | Collection iteration |
| `judge x:` / `when p -> v` | Pattern-match expression |
| `when cond:` | Compile-time conditional (also `when c then a else b`) |
| `with target:` | Scoped mutations on a target |
| `defer` / `errdefer` / `banish` | Deterministic cleanup |
| `return` / `break` / `continue` | Function / loop control |

### 20.3 Expressions

| Keyword | Purpose |
| ------- | ------- |
| `calling … with …` | Function / method / module-member call |
| `as` / `is` / `into` / `to` | Type annotation / binding / return type / cast |
| `some v` / `maybe none` | Present / absent optional value |
| `error` | Error value inside `or:` blocks |
| `try e`, `e or else x`, `e or return x`, `e or:` | Unwrapping operators |
| `ord s` / `chr n` | Byte ↔ single-character string |
| `bytes of s` | Borrow string / byte-array memory |
| `sigil of x` / `essence of p` | Address-of / dereference |
| `size of T` | `sizeof` of a type |
| `transmute x to T` | Raw bit reinterpretation |
| `null` / `true` / `false` | Literals |
| `defined(NAME)` | Compile-time flag test |
| `not`, `~`, `-` | Unary logical / bitwise / numeric negation |
| `+ - * / %` `<< >> & \| ^` `== != < <= > >=` | Binary operators |

### 20.4 Common diagnostics

Diagnostics use Rust-style formatting (`error[CODE]: message`, plus `help:` and `note:` lines). Codes referenced throughout this reference: `E0004` unknown module member, `E0005` type mismatch, `E0008` `sigil of null`, `E0014` missing type annotation, `E0020` return type mismatch, `E0023`/`E0024` variadic `many` misuse, `E0025` body in `.d.pengu`, `E0026` duplicate `insignia`, `E0027` duplicate omen value, `E0028` payload + explicit value, `E0029` mixed/invalid omen values, `E0030`–`E0032` concept/signature/bound errors, `E0033`/`E0034` ritual misuse, `E0035` seal mismatch, `E0036` import-alias collision, `E0038` duplicate map key, `E0039` non-constant `when`, `E0040` reserved `main`.

---

*Happy weaving. 🐧*
