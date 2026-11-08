# PenguScript Language Reference

PenguScript is a small, statically typed language that compiles to C. This
reference documents the language as implemented by `psc` 0.52.0: every
construct, its semantics, and the C it lowers to.

It is the *language* document of the documentation set:

| Document | Answers |
| --- | --- |
| **LANGUAGE.md** (this file) | How do I write this construct, and what does it become in C? |
| [PENGUNIC.md](PENGUNIC.md) | How do I write PenguScript that is safe, idiomatic and fast? |
| [STDLIB.md](STDLIB.md) | Which standard module do I use, and where is its API? |

Spanish: [LANGUAGE.es.md](LANGUAGE.es.md).

<!-- toc -->
- [0. How to read this reference](#0-how-to-read-this-reference)
- [1. Lexical structure](#1-lexical-structure)
  - [1.1 Files and modules](#11-files-and-modules)
  - [1.2 Comments](#12-comments)
  - [1.3 Identifiers and keywords](#13-identifiers-and-keywords)
  - [1.4 Layout](#14-layout)
  - [1.5 Literals](#15-literals)
- [2. Types](#2-types)
  - [2.1 Primitive and runtime types](#21-primitive-and-runtime-types)
  - [2.2 Composite types](#22-composite-types)
  - [2.3 Value vs reference](#23-value-vs-reference)
- [3. Variables and constants](#3-variables-and-constants)
  - [3.1 Declarations](#31-declarations)
  - [3.2 Assignment and `set`](#32-assignment-and-set)
  - [3.3 Scope and shadowing](#33-scope-and-shadowing)
  - [3.4 Safety guarantees and opt-outs](#34-safety-guarantees-and-opt-outs)
- [4. Operators](#4-operators)
  - [4.1 Precedence](#41-precedence)
  - [4.2 Arithmetic and bitwise](#42-arithmetic-and-bitwise)
  - [4.3 Comparison, membership, word tests](#43-comparison-membership-word-tests)
  - [4.4 Address, dereference, size](#44-address-dereference-size)
  - [4.5 Character and byte primitives](#45-character-and-byte-primitives)
  - [4.6 Casts and conversions](#46-casts-and-conversions)
  - [4.7 `defined`, `size of`, and compile-time values](#47-defined-size-of-and-compile-time-values)
- [5. Control flow](#5-control-flow)
  - [5.1 `if`, `unless` and `if`-bindings](#51-if-unless-and-if-bindings)
  - [5.2 `while`](#52-while)
  - [5.3 `for`](#53-for)
  - [5.4 `judge` — pattern matching](#54-judge-pattern-matching)
  - [5.5 `break`, `continue`, `return`](#55-break-continue-return)
  - [5.6 Block expressions](#56-block-expressions)
  - [5.7 `with` as a statement](#57-with-as-a-statement)
- [6. Functions](#6-functions)
  - [6.1 `weave`](#61-weave)
  - [6.2 Calling conventions](#62-calling-conventions)
  - [6.3 Variadic parameters](#63-variadic-parameters)
  - [6.4 `declare`](#64-declare)
  - [6.5 Lambdas](#65-lambdas)
  - [6.6 `ritual` methods](#66-ritual-methods)
  - [6.7 Entry point](#67-entry-point)
- [7. Modules and imports](#7-modules-and-imports)
  - [7.1 Module = file](#71-module-file)
  - [7.2 `import`](#72-import)
  - [7.3 Module-level state](#73-module-level-state)
- [8. C interop](#8-c-interop)
  - [8.1 `include`, `link`, `ldflag`, `insignia`](#81-include-link-ldflag-insignia)
  - [8.2 `declare`](#82-declare)
  - [8.3 `opaque`, `ref to`, `bytes of`](#83-opaque-ref-to-bytes-of)
  - [8.4 `.d.pengu` declaration files](#84-dpengu-declaration-files)
  - [8.5 `antiquus` — embedded C](#85-antiquus-embedded-c)
  - [8.6 `transmute`, `@packed`, `@align`](#86-transmute-packed-align)
- [9. Composite types](#9-composite-types)
  - [9.1 `rune` — structs](#91-rune-structs)
  - [9.2 `cyclus` — recursive types](#92-cyclus-recursive-types)
  - [9.3 `echo` — unions](#93-echo-unions)
  - [9.4 `omen` — enums and sum types](#94-omen-enums-and-sum-types)
  - [9.5 `seal`, `alias`, `opaque`](#95-seal-alias-opaque)
  - [9.6 `frozen`](#96-frozen)
  - [9.7 `derive`](#97-derive)
  - [9.7.1 `derive Json`](#971-derive-json)
  - [9.8 `with:` builders](#98-with-builders)
- [10. Methods and concepts](#10-methods-and-concepts)
  - [10.1 `enchanting` — methods on a type](#101-enchanting-methods-on-a-type)
  - [10.2 `@mutates`](#102-mutates)
  - [10.3 `concept` — compile-time contracts](#103-concept-compile-time-contracts)
  - [10.4 `bind` — implementing a concept](#104-bind-implementing-a-concept)
  - [10.5 Method resolution](#105-method-resolution)
  - [10.6 Built-in concepts](#106-built-in-concepts)
- [11. Generics](#11-generics)
  - [11.1 `shard`](#111-shard)
  - [11.2 Bounds](#112-bounds)
  - [11.3 `donum T`](#113-donum-t)
  - [11.4 Generic methods and derivation](#114-generic-methods-and-derivation)
  - [11.5 Limits](#115-limits)
- [12. Optionals and errors](#12-optionals-and-errors)
  - [12.1 `maybe T` and `result of T to E`](#121-maybe-t-and-result-of-t-to-e)
  - [12.2 Constructors](#122-constructors)
  - [12.3 Inspection and unwrapping](#123-inspection-and-unwrapping)
  - [12.4 `or else`, `or return`, `try`, `or:`](#124-or-else-or-return-try-or)
  - [12.5 `panic`](#125-panic)
  - [12.6 `defer` and `errdefer`](#126-defer-and-errdefer)
  - [12.7 Ownership of boxed values](#127-ownership-of-boxed-values)
- [13. Memory](#13-memory)
  - [13.1 The model](#131-the-model)
  - [13.2 `banish`](#132-banish)
  - [13.3 `defer` and `errdefer`](#133-defer-and-errdefer)
  - [13.4 What the compiler does not do](#134-what-the-compiler-does-not-do)
  - [13.5 Owned temporaries in expressions](#135-owned-temporaries-in-expressions)
  - [13.6 Boxed values move](#136-boxed-values-move)
  - [13.7 Returned values and parameters](#137-returned-values-and-parameters)
  - [13.8 Debugging leaks](#138-debugging-leaks)
  - [13.9 `derive Drop`: deterministic destruction](#139-derive-drop-deterministic-destruction)
  - [13.10 Move by default](#1310-move-by-default)
  - [13.11 Shared ownership: `Rc`, `Arc`, `Weak`](#1311-shared-ownership-rc-arc-weak)
  - [13.12 Copy-on-write containers](#1312-copy-on-write-containers)
- [14. Attributes](#14-attributes)
  - [14.1 Threads](#141-threads)
  - [14.2 Coroutines](#142-coroutines)
- [15. Tests and tooling](#15-tests-and-tooling)
  - [15.1 `test` blocks](#151-test-blocks)
  - [15.2 Commands](#152-commands)
  - [15.3 Build options](#153-build-options)
  - [15.4 Project manifest](#154-project-manifest)
  - [15.5 `psc doc`](#155-psc-doc)
- [16. Chaining, pipes, tuples and shorthand](#16-chaining-pipes-tuples-and-shorthand)
  - [16.1 Method chains](#161-method-chains)
  - [16.2 Pipes](#162-pipes)
  - [16.3 Tuples and multiple returns](#163-tuples-and-multiple-returns)
  - [16.4 Shorthand struct initialisers](#164-shorthand-struct-initialisers)
- [17. Deprecation](#17-deprecation)
- [18. Diagnostics](#18-diagnostics)
- [19. Complete example](#19-complete-example)
- [Appendix A. Keywords](#appendix-a-keywords)
- [Appendix B. Runtime representations](#appendix-b-runtime-representations)
- [Appendix C. Grammar sketch](#appendix-c-grammar-sketch)
<!-- /toc -->

## 0. How to read this reference

Every construct is documented once, in the order the compiler sees it: lexing,
types, declarations, expressions, statements, then the features that need their
own section (generics, memory, interop).

* A ```pengu block is valid PenguScript. Blocks marked `pengu-fragment` are
  fragments; they illustrate a form and are not meant to compile alone.
* A ```c block is the *representative* C that `psc emit-c` produces, with
  `#line` markers and unused-variable `(void)` casts removed. Names of generated
  helpers (`pengu_list_new`, `_pengu_clone_*`, …) are verbatim.
* The keyword lists, type mappings and diagnostic codes are exhaustive; the
  prose is not — [PENGUNIC.md](PENGUNIC.md) covers *how to use* the language and
  [STDLIB.md](STDLIB.md) covers the standard library.
* Version: `psc` 0.52.0. The ABI version the generated C expects is 3.

## 1. Lexical structure

### 1.1 Files and modules

| Item | Rule |
| --- | --- |
| Source file | `*.pengu`, UTF-8, LF or CRLF |
| Declaration file | `*.d.pengu` — `declare`/`include`/`link`/types only; no bodies by convention |
| Module id | the path relative to the source root, with `/` → `.`, without extension |
| Entry point | `weave main into int` in the module built as the program |
| Test entry | blocks declared with `test` (§16) |

### 1.2 Comments

```pengu
# line comment
## documentation comment (extracted by `psc doc` and the LSP)

rune Point:
    x as int   # trailing comments are allowed
```

A run of `##` lines at the top of the file, before the first declaration, is the
module docstring. A run of `##` lines immediately above a declaration documents
that declaration. `psc doc` renders both (§16.3).

### 1.3 Identifiers and keywords

Identifiers start with a letter or `_` and continue with letters, digits or `_`.
`_` alone is the discard binding (`for _, v in xs`). Names that collide with C
reserved words or C type names are rejected (`E0035`); so is `main` as a
constant.

The language has 71 reserved words; Appendix A lists them. There is no
`true`-like contextual keyword except `over` (only meaningful after a `judge`
subject), `of` and `at`/`to` in their operator positions.

### 1.4 Layout

Blocks are delimited by indentation. A block is the statements indented deeper
than its header; dedenting ends it. The formatter (`psc fmt`) uses four spaces
(`.pengufmt.toml`: `tab_size = 4`, `insert_spaces = true`) and is the reference
for layout.

```pengu
weave classify with n as int into string:
    if n < 0:
        return "negative"
    else if n == 0:
        return "zero"
    else:
        return "positive"
```

A logical line may be continued inside an open `(`, `[` or `{`. Statements are
otherwise one per line; `,` separates items in argument, parameter, field and
element lists — never a statement terminator.

### 1.5 Literals

| Literal | Example | Type |
| --- | --- | --- |
| Decimal integer | `42`, `1_000_000` | `int` |
| Hexadecimal | `0xFF`, `0x1F_2E` | `int` |
| Binary | `0b1010` | `int` |
| Float | `3.5`, `1e-9` | `float` (32-bit) |
| Float, 64-bit | `3.5f64` is not a suffix — annotate: `var x as f64 is 3.5` | `f64` |
| Boolean | `true`, `false` | `bool` |
| Character | `'A'`, `'\n'` | `char` |
| String | `"hi"`, `"a\nb"` | `string` |
| Raw string | `r"a\nb"` (no escapes) | `string` |
| Multi-line string | `"""line 1\nline 2"""` | `string` |
| Interpolated | `"total: {total}"` | `string` |
| List | `[1, 2, 3]` | `list of int` |
| Map | `{"a": 1, "b": 2}` | `map of string to int` |
| Fixed array | `[3, 1, 2]` in an `array of int with size 3` slot | `array of int with size 3` |
| Range | `0 to 10` | integer range — only in `for`, `in` and comprehensions, not a writable type |
| Null | `null` | any pointer, `opaque`, or `maybe T` |

Escapes in ordinary strings: `\n \t \r \\ \" \' \0 \xNN \u{...}`. Interpolation
takes an expression: `"{name} v{version}"`; `{{` and `}}` produce literal
braces. A `:` inside the braces selects a `printf` format: `"{ratio:.2f}"`,
`"{id:04d}"`, `"{n:x}"`, `"{name:10s}"`. The spec is validated at compile time
(`E0019`) and must match the value: `d i o u x X` for integers, `f e g` for
floats and `s` for strings.

```pengu-fragment
var ratio as float is 1.23456
calling print with "{ratio:.2f}\n"     # 1.23
```

A float literal is single precision until its target type says otherwise: in a
`f64` slot the same literal is emitted as a C `double` with all digits kept.

## 2. Types

### 2.1 Primitive and runtime types

| PenguScript | C type | Size | Notes |
| --- | --- | --- | --- |
| `int` | `int32_t` | 4 | default integer |
| `i64`, `long` | `int64_t` | 8 | |
| `i16`, `short` | `int16_t` | 2 | |
| `i8` | `int8_t` | 1 | |
| `u32`, `uint` | `uint32_t` | 4 | |
| `u64`, `ulong` | `uint64_t` | 8 | |
| `u16`, `ushort` | `uint16_t` | 2 | |
| `byte`, `u8` | `uint8_t` | 1 | bytes and unsigned 8 |
| `size_t`, `usize` | `size_t` | pointer | lengths and indices |
| `isize` | `intptr_t` | pointer | signed pointer-sized |
| `float`, `f32` | `float` | 4 | IEEE-754 single |
| `f64`, `double` | `double` | 8 | IEEE-754 double |
| `char` | `char` | 1 | one byte |
| `bool` | `bool` | 1 | `true` / `false` |
| `void` | `void` | – | no value |
| `string` | `PenguString` | 16 | `{ char *data; int len; int32_t is_owned; }` |
| `opaque` | `void *` | pointer | C handle, only behind `ref to` |

Prefer the short spellings (`int`, `byte`, `size_t`, `float`, `f64`). The
C-width spellings exist so a signature copied from a header keeps its exact
width and so `psc bind` can emit it verbatim.

The runtime owning types are plain C structs (`build/include/pengu_runtime.h`):

```c
typedef struct { char *data; int len; int32_t is_owned; } PenguString;
typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;
typedef struct { bool is_present; void *value; } PenguMaybe;
```

`PenguString` keeps the length, so it may hold NUL bytes; `is_owned == 0`
marks a borrowed view. `PenguList` stores elements by value at a fixed
`elem_size` and owns only its element buffer.

### 2.2 Composite types

| Type | Spelling | C representation |
| --- | --- | --- |
| List | `list of T` | `PenguList` (CC vector) |
| Map | `map of K to V` | `PenguMap` (CC map) |
| Fixed array | `array of T with size N` | `T[N]`, nested as `T[M][N]` |
| Slice | `slice of T` | `PenguSlice { void *data; int len; size_t elem_size; }` |
| Optional | `maybe T` | tagged box, payload heap-allocated |
| Result | `result of T to E` | tagged box, payload heap-allocated |
| Pointer | `ref to T`, `ref to frozen T` | `T *` |
| Tuple | `(T, U)`, `(T, U, V)` | anonymous struct |
| Function pointer | `weave with T into U` | `U (*)(T)` |
| User type | `rune`, `echo`, `omen`, `seal`, `alias` | struct / union / enum / wrapper |

`string`, `list`, `map` and boxed `maybe`/`result` values are *owned* unless a
function returns a borrowed view (§14). `slice`, `range`, `ref to T`, tuples and
scalar types are plain values.

Container literals construct the value where it is written:

```pengu-fragment
var xs as list of int is [1, 2, 3]
defer banish xs
var ages as map of string to int is {"ada": 36, "alan": 41}
defer banish ages
```

A map literal needs a known key and value type, so it is only accepted where the
type is written: a `var`/`let` annotation, a field, a parameter or a return type.
Anywhere else the compiler reports `E0076` (`map literal needs a type
annotation`). Keys may be string literals or any expression of the key type,
including interpolations (`{"k{n}": n}`).

The literal builds the container once, when it is evaluated. For a map it is one
allocation plus one insert per entry, never a rebuild on each read:

```c
PenguMap ages = __extension__(({ PenguMap _map0 = pengu_map_new(sizeof(PenguString), sizeof(int32_t)); PenguString _mk1; int32_t _mv2; _mk1 = pengu_string_from_cstr_len("ada", 3); _mv2 = 36; pengu_map_put(&_map0, &_mk1, &_mv2); _mk1 = pengu_string_from_cstr_len("alan", 4); _mv2 = 41; pengu_map_put(&_map0, &_mk1, &_mv2); _map0; }));
```

The map owns copies of its keys and values, so the temporaries above are only
borrowed while the entry is inserted. `banish` releases the whole map (§13).

### 2.3 Value vs reference

* `string`, `list`, `map`, `rune` containing any of them, `maybe`, `result`:
  assignment copies the value, but strings and containers inside are shared
  unless the language says otherwise — the compiler's cleanup functions assume
  one owner (§14.3).
* `slice of T` and `ref to T` are non-owning views. Copying them never
  duplicates the storage.
* `frozen T` is a read-only qualification; `ref to frozen T` is a read-only
  pointer.

## 3. Variables and constants

### 3.1 Declarations

These forms are accepted:

```pengu-fragment
var count as int is 0                 # typed, mutable
let name as string is "Ada"           # typed, immutable
var total is 100                      # inferred int
let greeting is "Hello"               # inferred string
var buffer as array of byte with size 64 is array of byte with size 64

let (x, y) as Pair is point_value     # rune fields, in declaration order
var (a, b) as Pair is point_value     # same, mutable bindings
let q, r is calling divmod with 9, 2  # tuple from a multi-return call

const MAX_USERS as int is 1024        # top level only, compile-time
const PI is 3.14159                   # inferred float

static var calls as int is 0          # inside a weave: persists across calls
```

Rules:

* `var` binding is mutable, `let` is not (`E0006` on assignment).
* `var`/`let` are forbidden at top level (`E0002`). Top-level state is `const`
  or `static var` inside a function.
* `const` is top-level only (`E0001`) and must be a compile-time expression.
  A `list` or `map` constant evaluates its expression at every use; when you
  want one static object, use `array of T`.
* `null` needs an explicit type: `const NIL as ref to int is null`.
* Destructuring binds the fields of a rune (in declaration order) or the
  elements of a tuple returned by a call. The number of names must match the
  value (`E0079`). A rune value needs `as T` so the compiler knows its fields;
  tuples are inferred from the call.

### 3.2 Assignment and `set`

Assignment is `set`; there is no bare `x = 1`.

```pengu-fragment
set count is 42
set player.hp is 100
set self->hp is 80
set items at (i + 1) is new_item
set essence of ptr is 99            # *ptr = 99
set .x is 10                        # only inside a `with:` builder
```

Compound forms exist: `+= -= *= /= %= &= |= ^= <<= >>=`. `+=` on `string` is
`E0005`; compose strings with interpolation instead.

```pengu-fragment
set counter += 1
set flags |= 0x08
set text is "{text} suffix"
```

The target must be mutable: assigning to a `let`, a `const`, a `frozen` value
or through a `ref to frozen T` is `E0006`.

### 3.3 Scope and shadowing

Scopes are indentation blocks: weave bodies, `if`/`while`/`for` branches,
`with:` builders, `or:` blocks and `do:` expressions. Lookup is lexical and an
inner declaration shadows an outer one.

At module level, an unqualified name resolves in the current module first, then
in the modules that module imports (transitively, in import order), and never in
an unrelated module. A qualified name follows the imported aliases:
`calling father.child.fn` inside `father` names `father.child.fn`, not a local
`fn` of `father`.

```pengu
weave main into int:
    let x is 1
    if x == 1:
        let x is "shadowed"      # a different x, same name
        calling print with x
    return x                     # 1
```

`banish`, `defer` and `errdefer` are only valid inside a function body
(`E0008`).

### 3.4 Safety guarantees and opt-outs

Bounds checks are on by default (indexing a list, slice, array, string or map
aborts with a message on out-of-range indices). Integer-overflow checks are
**not implemented yet**: arithmetic wraps like C. `--release-unsafe` turns the
bounds check off for a release build, never per statement. See §16 for the
build profiles and §14 for what stays manual even with checks on.

## 4. Operators

### 4.1 Precedence

Loosest first:

| Level | Operators |
| --- | --- |
| 1 | `or else`, `or return`, `try`, `or:` |
| 2 | `or` |
| 3 | `and` |
| 4 | `not` |
| 5 | `is`, `is present`, `is not present`, `as`, `in`, `not in` |
| 6 | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| 7 | `&#124;` (bitwise or) |
| 8 | `^` (bitwise xor) |
| 9 | `&` (bitwise and) |
| 10 | `<<`, `>>` |
| 11 | `+`, `-`, `+` for strings |
| 12 | `*`, `/`, `%` |
| 13 | unary `-`, `~`, `not`, `sigil of`, `essence of`, `bytes of`, `size of`, `align of`, `transmute ... to`, `banish`, `some`, `ord`, `chr` |
| 14 | `.field`, `->field`, `at i`, `calling f with ...`, `(...)` |

`pipe` starts a new link at the beginning of a continuation line (§16.2);
it is not an infix operator.

### 4.2 Arithmetic and bitwise

```pengu-fragment
var a as int is 7
var b as int is 2
var q as int is a / b        # 3, integer division truncates toward zero
var r as int is a % b        # 1
var f as float is 7.0 / 2.0  # 3.5
var m as int is a & 0x0F
var s as int is a << 2
```

`/` and `%` on integers truncate; `%` on a negative left operand follows C
(remainder keeps the sign of the dividend). `%` on `float` is `E0005`. Use
`std.fractio` for floating-point helpers.

Integer arithmetic is unchecked in this release: `int` wraps like C
(`2147483647 + 1` is `-2147483648`). Checked arithmetic is planned; division by
zero still aborts (`SIGFPE`). `--release-unsafe` only affects bounds checks.

### 4.3 Comparison, membership, word tests

```pengu
weave classify with a as int, b as int, value as maybe int into string:
    if a == b and a < 10:
        return "small equal"
    if value is present:
        return "present"
    return "none"
```

`in` works on lists, arrays, slices, maps (key membership), strings (substring)
and ranges (`i in 0 to 10`). `is present` / `is not present` test a `maybe`; `is` also
tests an omen variant (`state is Ready`).

Strings compare by content (`pengu_string_eq`); `==` on two `list`s compares
element by element only if the element type has `Par` (§12).

### 4.4 Address, dereference, size

| Form | Meaning | C |
| --- | --- | --- |
| `sigil of x` | address of a variable/field | `&x` |
| `essence of p` | dereference | `*p` |
| `p at i` | pointer/array indexing | `p[i]` |
| `size of T` | compile-time size | `sizeof(T)` |
| `align of T` | compile-time alignment | `_Alignof(T)` |
| `bytes of s` | byte view of a string/array | `(uint8_t*)s.data` |

```pengu-fragment
var n as int is 5
var p as ref to int is sigil of n
set essence of p is 6
var raw as ref to frozen byte is bytes of "abc"
var dist as isize is p2 - p1     # element distance
```

`p++`, `p[i]` and `p + 1` are not PenguScript: use `p at i`, `p + n` for pointer
arithmetic (element-scaled). `ref to void` arithmetic is rejected.

### 4.5 Character and byte primitives

```pengu-fragment
var c as char is 'A'
var code as int is ord c        # 65
var back as string is chr 65    # "A"
```

`ord` accepts `char`; `chr` accepts an integer in 0–255 and returns a
one-character `string`.

### 4.6 Casts and conversions

| Form | Meaning | Runtime check |
| --- | --- | --- |
| `x to T` | numeric or nominal conversion (narrows silently) | no |
| `if n as T is v:` | narrows a `maybe`/`result` and binds `n` | yes, presence test |
| `transmute x to T` | reinterpret the bits | no, unsafe |

```pengu-fragment
var i as int is 65
var c as char is i to char
var f as float is 1 to float
var v as maybe int is some 3
if n as int is v:
    calling print with "{n}"
```

The binding comes first: `if n as T is v` tests that `v` holds a `T` and, only
if it does, binds `n` for the branch. The reversed spelling (`if v as T is n`)
is not a binding. `as` is only valid in a condition (`if`, `while`, `judge`
guard); it is not a general-purpose numeric cast. `to` converts between numeric types (truncating: `300 to u8` is
`44`) and between `seal` and its representation. `transmute` is reserved for FFI
layout tricks and is covered in §9.6.

### 4.7 `defined`, `size of`, and compile-time values

`defined(NAME)` is true when `-D NAME` was passed or the name is a predefined
environment fact (`wasm`, `debug`, `main`). `size of`/`align of` are folded at
compile time. Both are usable in `when` and in `const` initialisers.

## 5. Control flow

### 5.1 `if`, `unless` and `if`-bindings

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

A condition must be `bool` (`E0005`). A branch can hold one statement on the
same line as the colon (`if x == 1: return 1`); declarations, `defer` and
`banish` cannot.

An `if` condition can bind the payload of a `maybe`:

```pengu-fragment
if u as User is user:
    calling print with user.name
else:
    calling print with "anonymous"
```

The bound name is scoped to the `then` branch and is lowered to a single
`pengu_maybe_is_present` test plus extraction.

### 5.2 `while`

```pengu-fragment
var i as int is 0
while i < 10:
    calling tick with i
    set i is i + 1
```

Loops accept a label before the keyword (`outer: while ...`); see §5.5.

### 5.3 `for`

```pengu-fragment
for i from 0 to 10:              # [0, 10), end-exclusive
    calling tick with i

for i from 10 to 0 step -1:      # descending
    calling tick with i

for item in items:               # list, array, slice, string, map
    calling handle with item

for i, item in indexed:          # index + element
    calling handle with i

for _, v in values:              # discard the index
    calling handle with v
```

| Form | Iterates over | Element type |
| --- | --- | --- |
| `for i from a to b` | integer range `[a, b)` | `int` |
| `... step k` | range with step `k` (may be negative) | `int` |
| `for x in list` | `list of T` | `T` |
| `for x in array` | `array of T with size N` | `T` |
| `for x in slice` | `slice of T` | `T` |
| `for ch in s` | `string` | one-byte `string` (a byte view, no allocation) |
| `for k in map` | `map of K to V` keys, hash order | `K` |
| `for k, v in map` | key and value, hash order (no index) | `K`, `V` |
| `for x in a .. b` | integer range `[a, b)` | `int` |
| `for i in a to b` | integer range `[a, b)` (same as `..`) | `int` |

The indexed form `for i, v in col` requires distinct names (`E0037`); `_`
discards either binding. A map has no meaningful index: two bindings over a
map are the **key and the value**, and the third form (`for kk, vv`) is the
same. Iterating a map walks its hash order, so the order is unspecified.

`a .. b` and `a to b` are the expression forms of a range (the same as
`for i from a to b`); both evaluate to `range of int` and are half-open:
`1 .. 4` and `1 to 4` yield `1`, `2`, `3`. Inside `for … in` and to the right
of `in`, `to` is a range separator, not a cast; outside them it keeps meaning
"cast to type" (`x to int`).

**Comprehensions** build a list from an expression:

```pengu-fragment
let squares as list of int is for x in nums then x * x
let evens as list of int is for x in nums when x % 2 == 0 then x
```

Comprehensions accept the element form only (no index binding) and lower to a
statement-expression that allocates a `PenguList` and pushes each value. They
work over lists, arrays, slices, strings, ranges and maps (the element of a map
is its key).

```c
/* for i from 0 to 3 */
for (int32_t i = 0; i < 3; i++) { ... }

/* for item in xs: */
for (int _k = 0; _k < xs.len; _k++) {
    int32_t item = *(int32_t*)pengu_list_at(&xs, _k);
    ...
}

/* for k, v in m: */
for (; pengu_map_iter_valid(&it); pengu_map_iter_advance(&it)) {
    PenguString k = *(const PenguString*)pengu_map_iter_key(&it);
    int32_t v = *(const int32_t*)pengu_map_iter_value(&it);
    ...
}

/* for ch in s: borrowed byte view, no malloc */
for (int _k = 0; _k < s.len; _k++) {
    PenguString ch = (PenguString){ (char*)s.data + _k, 1, 0 };
    ...
}
```

An array is lowered with its compile-time length (`N`), never `sizeof`, so a
loop over an array parameter does not decay to a pointer length.

### 5.4 `judge` — pattern matching

```pengu-fragment
let desc as string is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
    else -> "unknown"
```

Subjects: `omen`, `bool`, `int`, `string`, `char`.

| Pattern | Example |
| --- | --- |
| Bare variant | `when Ready ->` |
| Qualified variant | `when Phase.Ready ->` |
| Full C name | `when Phase_Ready ->` |
| Literal | `when 42 ->`, `when "admin" ->`, `when 'X' ->` |
| Alternatives | `when Ready &#124; Loading ->` |
| Payload binding | `when Ok with value ->` |
| Guard | `when Val with n if n > 0 ->` |
| Default | `else ->` |

Exhaustiveness is enforced for `omen` and `bool` subjects (`E0044`); for `int`,
`string` and `char` a missing match yields the zero value unless an `else ->` is
present. Guarded patterns do not count as coverage.

`judge` is also a statement: write it without a value position and each arm runs
for its side effects. Guards are evaluated top to bottom, and a guarded arm that
does not hold falls through to the next matching arm, so the same pattern may
appear twice when the first occurrence is guarded.

```pengu
omen State:
    Ready is 0
    Loading is 1
    Done is 2

weave handle with state as State:
    judge state:
        when Ready ->
            calling print with "run\n"
        when Loading | Done ->
            calling print with "waiting\n"
        else ->
            calling print with "unknown\n"

weave main:
    calling handle with Ready
    calling handle with Loading
```

Emitting a `bool` subject compiles to `switch ((int)(x))` with `case true` and
`case false`; guards compile to an `if` chain (never a `switch`), which keeps the
generated C free of duplicate `case` labels.

**`judge ... over`** matches a rune whose discriminant is one of its fields:

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

`over` is a soft keyword: `var over as int is 5` still compiles. The `over` form
also supports narrowed payloads (`field as some`, `field as ok`, `field as
(a, b)`).

Codegen emits a C `switch` when every arm is an integer constant; otherwise it
emits `if`/`else` chains with payload extraction and guard checks.

```c
switch (state.tag) {
  case Ready: return pengu_string_from_cstr("ready");
  case Loading: return pengu_string_from_cstr("loading");
  case Done: return pengu_string_from_cstr("done");
  default: return pengu_string_from_cstr("unknown");
}
```

### 5.5 `break`, `continue`, `return`

`break` and `continue` require an enclosing loop (`E0007`). `return` must match
the enclosing `into` type (`E0020`); a bare `return` is valid only in a `void`
weave.

Loops can be labeled to leave more than the innermost one:

```pengu-fragment
outer: for line in lines:
    for ch in line:
        if ch == ";":
            continue outer
        if ch == "}":
            break outer
```

Labels are function-local, unique per function (`E0069`) and lower to
`goto _pengu_label_<name>_{continue,break}` with the loop's cleanup preserved.

### 5.6 Block expressions

A comprehension (`for x in xs then expr`), the one-line conditional
expression (`if c then a else b`) and an **indented block** in value position
are values. `do:` and a multi-line `if`/`unless` evaluate to the value of their
last expression; the statements before it run in the block's own scope.

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

Blocks lower to GNU statement expressions (`__extension__(({ ... }))`), so the
generated C needs GCC or Clang, the supported toolchains. `return`, `banish`
and `defer` inside the block keep their usual meaning. A loop in value
position (`for x in xs then expr`) collects each iteration's value into a new
`list of T`.

### 5.7 `with` as a statement

A `with` block names a receiver once and lets the body address it with
`.field` and `calling .method`:

```pengu
rune Point:
    x as int
    y as int

enchanting Point:
    weave shift with dx as int, dy as int into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into int:
    var p as Point is with x is 1, y is 2
    with p:
        var y0 as int is .y
        set .x is .x + 1
        calling .shift with 2, 1
    return p.x + p.y
```

`.field` reads or writes a field of the target and `calling .method` dispatches
on its type, so the receiver is written once instead of on every line. The
target is evaluated exactly once and must be an addressable place — a variable,
a field, an element (`xs at i`) or a borrow — otherwise the compiler reports
`E0077`. Every statement in the body is type-checked: an unknown name or a field
that does not belong to the target's type is `E0004`.

For a `rune` or `echo` target the target is bound to a pointer, which is why the
receiver appears dereferenced:

```c
{
    Point* _w0 = &(p);
    int32_t y0 = (*_w0).y;
    (*_w0).x = ((*_w0).x + 1);
    Point_shift(&((*_w0)), 2, 1);
}
```

For a `list`, `map` or `string` target the body calls the built-in methods
(`calling .push with 4`, `calling .put with "k", 1`). A `with` builder in value
position (`var p as Point with: ...`) is §9.8.

## 6. Functions

### 6.1 `weave`

```pengu
weave greet with name as string, times as int is 1 into void:
    for i from 0 to times:
        calling print with "Hi {name}"

weave double with x as int into int:
    return x * 2
```

* `with` introduces the parameters, `into` the return type. A `void` weave may
  omit the value of `return`.
* Default parameter values must be compile-time constants — literals, `const`s
  and integer arithmetic of those — and must match the parameter type. Defaults
  are the trailing parameters: one without a default cannot follow one that has
  it (`E0072`). A default that is not constant, or that does not fit the type,
  is `E0073`; a generic default is checked again for every instantiation.
* A body whose last statement is an expression returns it implicitly.
* Calls accept positional and named arguments: `calling greet with "Ada",
  times is 2` and `calling greet with times is 2, name is "Ada"` are equivalent;
  every parameter must be covered exactly once, positionally, by name or by its
  default (see §6.2).
* The argument list after `with` is greedy — parenthesise a call used inside a
  larger expression: `(calling get_count) > 0`.
* `weave inline ...` forces the C function to be emitted as
  `static inline __attribute__((always_inline))`.

`psc emit-c` turns each weave into a C function named `<module>_<name>`:

```c
int32_t d1_add(int32_t a, int32_t b) {
    return (a + b);
}
```

A returned `string`, `list` or `map` is returned by value; the callee transfers
ownership to the caller.

Defaults are folded to their value once, when the function is declared, and the
call site emits that value directly:

```pengu
weave greet with name as string, times as int is 2 into void:
    calling print with "{name} {times}"

weave main into int:
    calling greet with "Ada"
    calling greet with "Ada", 2
    return 0
```

```c
d1_greet(pengu_string_from_cstr("Ada"), 2);
```

Both calls emit the same C, and a default never re-evaluates per call.

### 6.2 Calling conventions

```pengu-fragment
calling greet with "Ada", 3        # free function
calling spark.println with "hi"    # module-qualified
calling player.heal with 25        # method on a value
calling Player.new_hero with "Ada" # ritual (static) method, on the type
calling items.push with 4          # built-in container method
```

Built-in container methods (`list`: `push`, `pop`, `len`, `at`, `clear`;
`map`: `get`, `put`, `contains`, `remove`, `len`, `keys`, `values`) are
resolved by the compiler without an `enchanting` block.

Named arguments bind by parameter name, in any order, and the compiler prints
the arguments in declaration order — both call forms below produce the same C:

```pengu
weave greet with name as string, times as int is 2, loud as bool is false into void:
    calling print with "{name}"

weave main into int:
    calling greet with "Ada", times is 3
    calling greet with times is 3, name is "Ada"
    return 0
```

```c
d1_greet(pengu_string_from_cstr("Ada"), 3, false);
```

* Positional arguments come first. A named argument may follow them; a
  positional argument after a named one is `E0071`.
* A parameter is covered at most once. Repeating it — `a is 1, a is 2` or
  `1, a is 2` — is `E0071`; so is a name the function does not take.
* A parameter without a default left uncovered, or extra arguments, is `E0005`.
* Chain and pipe steps (`calling p.plus with 1` followed by `.plus with by is 2`)
  still take positional arguments only; naming one is `E0071`. Call the method
  directly instead: `calling p.plus with by is 2`.

### 6.3 Variadic parameters

A `many T` parameter accepts zero or more `T` arguments. It must be the last
parameter, only one is allowed per signature, and it cannot have a default
(`E0024`, `E0023`, `E0074`). In C it travels as a `PenguSlice`, so the callee
indexes it like a slice and asks for `xs.len`:

```pengu
weave total with xs as many int into int:
    var t as int is 0
    var i as int is 0
    while i < xs.len:
        set t is t + (xs at i)
        set i is i + 1
    return t

weave main into int:
    calling print with "{calling total with 1, 2, 3}"
    return 0
```

```c
int32_t total(PenguSlice xs);

total((PenguSlice){ (int32_t[]){ 1, 2, 3 }, 3, sizeof(int32_t) });
```

The call site packs loose arguments into a C99 compound literal and passes
`(PenguSlice){ 0, 0, sizeof(T) }` for zero arguments. Passing an existing
`slice`, `many` or array forwards the same view without copying:

```pengu
weave count with xs as many int into int:
    return xs.len

weave main into int:
    var arr as array of int with size 3 is array of int with size 3
    calling print with "{calling count with arr}"
    return 0
```

```c
total(pengu_slice_new(arr, sizeof(arr[0]), (int)(sizeof(arr) / sizeof(arr[0]))));
```

Elements are borrowed: the callee must not `banish` an element it did not
create, and a `many T` cannot be stored past the call. A `many` parameter is
not allowed in `declare` (`E0075`); use a trailing `...` for raw C varargs
there. Call-site spread (`f(...xs)`) does not exist.

### 6.4 `declare`

```pengu
declare pengu_print with s as string into void
declare strlen_c with s as ref to char into usize
declare printf with fmt as ref to frozen char, ... into int
```

`declare` binds an external C function; calls become direct C calls. Types must
match the header exactly. A trailing `...` is raw C varargs (valid only in
`declare`). Every external function needs a `declare`, or the call is `E0004`.

### 6.5 Lambdas

```pengu-fragment
let no_args as weave into int is lambda into 42
let double as weave with x as int into int is lambda x as int into x * 2
let add as weave with a as int, b as int into int is lambda a as int, b as int into a + b
```

Lambdas are static C functions (`_pengu_lambda_N`) with **no captures**: they see
their parameters and module-level declarations only. Their parameter types are
mandatory; the return type is inferred. A lambda body is a function boundary, so
`break`/`continue` cannot target a loop of the enclosing weave.

### 6.6 `ritual` methods

A `ritual` is an associated (static) function declared inside `enchanting` or
`bind`. It receives no `self` and is called on the type name:

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    weave ritual new with name as string into Player:
        return with name is name, hp is 100
```

Calling a ritual on an instance, or an instance method on the type name, is
`E0034`; using `self` inside a ritual is `E0033`.

### 6.7 Entry point

The program entry is `weave main into int` (or `into void`) in the entry module.
The compiler emits `pengu_main` and a C `main` that calls
`pengu_init(argc, argv)`, runs `pengu_main`, flushes stdio and returns the
status. The entry module sees `main` as `true` in `when` conditions; imported
modules see `false`.

## 7. Modules and imports

### 7.1 Module = file

A module is a `.pengu` file. Its module id is its path under the source root
with `/` replaced by `.` and the extension removed: `src/components/player.pengu`
is `components.player`. Files under the standard library are `std.*`.

### 7.2 `import`

```pengu-fragment
import std.spark                  # bundled standard library
import std.scrolls as s           # alias
import components.player          # project module (src/components/player.pengu)
import utils                      # src/utils.pengu
```

| Rule | Behaviour |
| --- | --- |
| Resolution | dotted path → `src/<path>.pengu`, then `<path>.d.pengu`, then `__init__.pengu` |
| Order | modules are checked and emitted in dependency order (topological) |
| Cycles | `E0004`, with the cycle printed (`a -> b -> a`) |
| Duplicates | importing the same module twice is `E0004` |
| Alias | `as name`; `_` is rejected (`E0036`), and a colliding alias is `E0036` |
| Privacy | top-level names starting with `_` are module-private (`E0043`) |
| Type names | module-scoped: use `a.Config` from another module |

Importing a module does not run code. There are no wildcard imports and no
`from ... import ...`.

### 7.3 Module-level state

`var` and `let` are forbidden at top level (`E0002`). Persistent state has two
legal forms: `const` (compile-time value) and `static var` inside a weave, which
emits a C `static` with a one-time initialisation guard:

```pengu
weave next_id into int:
    static var counter as int is 0
    set counter += 1
    return counter
```

`static` state is per-process and never freed; prefer passing state explicitly.

## 8. C interop

### 8.1 `include`, `link`, `ldflag`, `insignia`

```pengu
include "mylib.h"        # add the header to the generated C
link "mylib"             # add -lmylib when a live function needs it
link "m"
ldflag "-sUSE_GLFW=3"    # raw linker option, for what a library name cannot express
insignia mylib_          # C prefix for every declaration below
```

`link` is conditional: the flag reaches the linker only when the module has a
live symbol that needs it (release prunes unused native code). `ldflag` is
emitted outside the `--start-group` wrapper and can be overridden by the
project's own `ldflags`.

`insignia` prefixes generated C names: with `insignia pengu_`, `weave helper`
becomes `pengu_helper`, and an `omen Color` becomes `pengu_Color` with variants
`pengu_Color_Red`. It is the tool that keeps a binding from colliding with libc.

### 8.2 `declare`

```pengu
declare strlen_c with s as ref to char into usize
declare printf with fmt as ref to frozen char, ... into int
declare qsort with base as ref to void, n as usize, size as usize, cmp as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void
```

Parameter lists for `declare` must be written on one line: the parser does not
continue a parameter list after a trailing comma.

* Every external function must be declared before use (`E0004`).
* Parameter and return types must match the C prototype exactly; PenguScript
  does not convert silently at the boundary.
* A trailing `...` means raw C varargs (`declare` only).
* `declare` may be combined with `@noreturn` and with `inline`.

C strings: pass `ref to char`; a PenguScript string literal converts
automatically where `ref to char` is expected. Use `bytes of s` for a mutable
byte view and `std.ffi` for explicit conversions.

### 8.3 `opaque`, `ref to`, `bytes of`

```pengu
alias File as opaque

declare fopen with path as ref to char, mode as ref to char into ref to File
declare fclose with f as ref to File into int

weave main into int:
    var f as ref to File is calling fopen with "/tmp/x", "r"
    if f == null:
        return 1
    defer banish f          # only if the module documents that it owns the handle
    var raw as ref to frozen byte is bytes of "abc"
    return 0
```

* `opaque` is an incomplete C type: it cannot be instantiated and is
  only usable behind `ref to`.
* `bytes of s` yields `ref to byte` for a string or a fixed byte array; the view
  is borrowed and must not be banished.
* `sigil of x` is `&x`; `essence of p` is `*p`.

### 8.4 `.d.pengu` declaration files

```pengu
# mylib.d.pengu
include "mylib.h"
link "mylib"

omen Mode:
    MODE_FAST is 1
    MODE_SAFE is 2

declare mylib_open with name as ref to char into ref to opaque
```

A `.d.pengu` holds `include`/`link`/`ldflag`/`insignia`/`declare` and type
declarations; it is not where executable code belongs. It is the hand-written or
`psc bind` generated companion of a C library, and the Latin-named wrapper
(`std/mylib.pengu`) is where the public, safe API lives. The compiler does not
currently reject a body in a `.d.pengu`, so this is a convention you must keep.

`psc bind header.h --output=mylib.d.pengu` generates the declarations from a C
header (see `docs/EXTERNAL_MODULES.md`).

### 8.5 `antiquus` — embedded C

```pengu
antiquus add with a as int, b as int into int:
    """
    return a + b;
    """
```

The body is literal C in a triple-quoted string. Header rules match `weave`
(`shard`, `where`, defaults, any parameter type); the body sees the parameter
names verbatim, so they must be valid C identifiers (`E0035`). `many T` is not
allowed, `main` cannot be an `antiquus`. An `antiquus` is a definition, so it
belongs in a `.pengu`, not in a `.d.pengu`. Prefer `r"""..."""` when the C
contains backslashes.

`@export("sym")` pins the emitted symbol and makes it a DCE root.

### 8.6 `transmute`, `@packed`, `@align`

```pengu
@packed
rune Header:
    magic as u32
    version as u16

weave bits_of with f as float into u32:
    return transmute f to u32
```

`transmute x to T` reinterprets the bits (no check): it copies `min(sizeof(T),
sizeof(x))` bytes through a temporary, so `transmute 1.0 to int` is
`1065353216`, not `1`. `@packed` removes struct
padding; `@align(N)` sets the alignment. Both change the C layout and are meant
for on-disk or wire formats — see §14.

## 9. Composite types

### 9.1 `rune` — structs

```pengu
rune Player:
    name as string
    hp as int
    is_alive as bool
    _secret_id as int          # private to the module (E0043 outside)
```

Construction:

```pengu-fragment
var p as Player is with name is "Hero", hp is 100, is_alive is true

var q as Player with:
    set .name is "Villain"
    set .hp is 50
```

Nested `with` initializers must be parenthesized; the comma belongs to the
outermost `with`, so `address is (with city is "Madrid"), zip is 1` is the
correct spelling and `address is with city is "Madrid", zip is 1` would try to
put `zip` inside `address` (a C error against the nested rune). The compiler
reports unknown and repeated fields (`E0004`) and suggests the parentheses.

Nested builders infer the field's type:

```pengu-fragment
var person as Person with:
    set .name is "Ada"
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
```

Fields are read with `.` on a value and `->` on a reference (`self->hp`).
A rune is a C `struct`; its fields appear in declaration order.

A rune lowers to a C struct plus a clone helper and a cleanup helper; both are
generated even when they are trivial, so containers can copy and release any
rune uniformly:

```c
struct Point { int32_t x; int32_t y; };

static inline void _pengu_clone_Point(Point* out, const Point* v) { *out = *v; }
static inline void _pengu_cleanup_Point(Point* p) { (void)p; }
```

A rune whose fields own memory generates a cleanup that releases its top-level
`string`/`list`/`map` fields (and an omen's payload shell), and `derive Nexus`
is what makes `banish` call it. The cleanup is deliberately shallow: nested
elements and the contents of a copied value are not followed, because values are
copied by value and the copies share those buffers. Compose `banish` with your
own deep free (or use a type that owns its tree, such as `JsonValue.free`).

### 9.2 `cyclus` — recursive types

```pengu
rune Node cyclus:
    value as int
    next as maybe ref to Node
```

By-value recursion is infinite and rejected (`E0050`). `cyclus` marks the
declaration as intentionally recursive; the cycle must still be broken by
indirection (`ref to`, `list`, `map`, `slice`).

A *generic* self-reference (`rune Node shard T:` with `ref to Node of T` inside)
is rejected with `E0021` in 0.28.0: the type parameter is not in scope inside
its own body. Wrap the payload instead (`value as ref to void`, or a non-generic
node holding `slice of T`).

### 9.3 `echo` — unions

```pengu
echo Number:
    i as int
    f as float
```

An `echo` is a C `union`: all fields share storage and the record is as large as
its biggest field. Field access is unchecked — writing one field overwrites the
others. For a tagged sum type use `omen`.

### 9.4 `omen` — enums and sum types

```pengu
omen Direction:              # numeric enum
    North is 0
    South is 1

omen Event:                  # algebraic sum type
    Disconnected
    Connecting with attempt as int
    Connected with session_id as string, latency_ms as float
```

| Flavour | Spelling | C |
| --- | --- | --- |
| Numeric | `omen X:` with `is N` | `typedef enum { X_A = 0, ... } X;` |
| String | `omen X with string:` | rejected with `E0005` (not implemented yet) |
| Algebraic | variants with `with` payloads | struct with `int32_t tag` + payload `union` |

Variants are reachable unqualified (`Red`), qualified (`Color.Red`) or by full C
name (`Color_Red`). `is N` sets the numeric value and it is preserved in the
emitted enum; a variant without `is` takes the previous value plus one. Duplicate
values are `E0027`, non-constant values `E0029`, payloads on a string-valued omen
`E0028`. Interpolating an omen prints its variant name.

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
seal UserId as int          # nominal: no implicit conversion
alias Inches as int         # transparent synonym
alias Buffer as opaque      # incomplete C handle
```

In this release a `seal` is a transparent synonym like `alias`: the value is
interchangeable with its target, and the nominal check that would require an
explicit `raw to UserId` is still pending (documented as `E0005` in the plan).
Prefer `alias` while that check lands. `opaque` cannot be instantiated
and lives behind `ref to`.

### 9.6 `frozen`

```pengu-fragment
frozen int              # const int
ref to frozen int       # const int *
frozen Player           # const Player
```

`frozen` qualifies the pointee; the canonical spelling is `ref to frozen T`.
It is orthogonal to `let`: `let` freezes the name, `frozen` freezes the value.
A mutable value flows into `frozen`; the reverse does not compile.

### 9.7 `derive`

```pengu
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int
```

| Concept | Derivable | Generates |
| --- | --- | --- |
| `Par` | yes | `==`, `!=` |
| `Ordo` | yes | `<`, `<=`, `>`, `>=` |
| `Vinculum` | yes | hash, usable as a map key |
| `Imago` | yes | `_pengu_clone_<T>`: shallow copy (the copy shares owned buffers) |
| `Nexus` | yes | `_pengu_cleanup_<T>`: first-level destruction, invoked by `banish` |
| `Drop` | yes | `Nexus` + destruction at every scope exit + move-only (§13.9) |
| `Json` | yes | `_pengu_json_encode_<T>` / `_pengu_json_decode_<T>` (implies `Nexus`; see §9.7.1) |
| `Forma`, `Iterabilis` | no (`E0005`) | — |
| `Donum` | automatic | implied when every field is defaultable; `derive Donum` is `E0005` |

Deriving a comparison concept on a generic rune bounds its parameters; the check
happens at each substitution site.

### 9.7.1 `derive Json`

`Json` is a built-in concept that generates a JSON codec for a rune at compile
time. It lowers to plain C: no reflection, no runtime type tables, no dependency
on `std.json`.

```pengu
rune Address derive Json:
    city as string
    zip as int

rune User derive Json:
    id as i64
    name as string
    @json("e-mail") email as string
    @skip password as string
    tags as list of string
    nick as maybe string
    address as Address
```

Deriving `Json` adds two methods to the rune (and implies `Nexus`):

| Method | Shape | Emitted C |
| --- | --- | --- |
| `to_json` | `weave to_json into string` (instance) | `_pengu_json_encode_<T>(T*)` |
| `from_json` | `weave ritual from_json with text as string into result of T to string` (static) | `_pengu_json_decode_<T>(PenguString)` |

```pengu-fragment
var user as User is with id is 7, name is "Ana", email is "a@b.c",
    password is "x", tags is ["a"], nick is (maybe none),
    address is (with city is "Madrid", zip is 28001)

var text as string is calling user.to_json
var parsed as result of User to string is calling User.from_json with text
if parsed.is_ok:
    calling print with parsed.value.name
else:
    calling print with parsed.error     # json: line 1, col 12: expected a string
```

#### Field attributes

| Attribute | Meaning |
| --- | --- |
| `@json("external")` | JSON key for the field (default: the field name) |
| `@skip` | never encoded and never required when decoding |

Inside a rune that derives `Json`, any other field attribute is `E0054`; the
compiler does not interpret validations such as `@format("email")`. Do that at
your HTTP boundary with a hand-written `weave validate`. Runes that do not derive
`Json` keep ignoring these attributes.

#### Type mapping

| PenguScript | JSON |
| --- | --- |
| `bool` | `true` / `false` |
| `i8`…`i64`, `int`, `isize` | number (range-checked on decode) |
| `u8`…`u64`, `usize` | number (range-checked on decode) |
| `float`, `f64` | number (shortest round-trip form; non-finite values panic) |
| `string` | string (UTF-8, `"` `\\` and C0 controls escaped) |
| `list of T` | array |
| `map of string to V` | object with sorted keys |
| `maybe T` | `null` when absent, otherwise `T` |
| rune with `derive Json` | object |
| `omen` without payload | string with the variant name |

Rejected with `E0054`: `result`, tuples, fixed arrays, `ref`/pointers, `fn`,
`opaque`, `char`, generic runes (`rune shard T`), `echo`, and omens with payload.

#### Decode semantics

- The document root must be an object.
- Unknown keys are validated and skipped.
- A duplicate key for a known field is an error: silently overwriting would leak
  the value stored first.
- Missing required fields are an error; `maybe T` fields are optional.
- Numbers are strict JSON numbers and range errors name the field and the type
  (`field 'count': 300 does not fit in u8`).
- Nesting is limited to 64 levels; trailing bytes are rejected.
- On failure the decoder frees everything it reserved, returns `err` with a
  message that carries `line`/`col`, and leaves no value for the caller. It uses
  its own `_pengu_json_free_<T>`, so it is exact even though `banish` is shallow.

#### Emitted C

`psc emit-c` prints the five functions per rune (declarations first, then
bodies), plus `_pengu_json_free_<T>`. For `User`:

```c
static PenguString _pengu_json_encode_User(User* self) {
    PenguJsonOut _o;
    pengu_json_out_init(&_o);
    _pengu_json_write_User(&_o, self);
    return pengu_json_out_finish(&_o);
}

static PenguResult _pengu_json_decode_User(PenguString text) {
    PenguJsonIn _in;
    pengu_json_in_init(&_in, text);
    User* _out = (User*)malloc(sizeof(User));
    if (!_out) abort();
    PenguString _err = pengu_json_no_error();
    if (!_pengu_json_read_User(&_in, _out, &_err)) {
        free(_out);
        return pengu_result_err(pengu_json_box_error(&_err));
    }
    if (!pengu_json_in_finish(&_in, &_err)) {
        _pengu_json_free_User(_out);
        free(_out);
        return pengu_result_err(pengu_json_box_error(&_err));
    }
    return pengu_result_ok(_out);
}

static bool _pengu_json_read_User(PenguJsonIn* in, User* out, PenguString* err) {
    memset(out, 0, sizeof(*out));
    if (!pengu_json_in_object_begin(in, err)) return false;
    bool _seen0 = false;              /* id */
    bool _seen4 = false;              /* tags */
    for (;;) { /* first element or ',' ; in_key ; key_eq */ }
    if (!_seen0) {
        pengu_json_failf(err, in, "missing field 'id'");
        _pengu_json_free_User(out);
        return false;
    }
    if (!pengu_json_in_object_end(in, err)) {
        _pengu_json_free_User(out);
        return false;
    }
    return true;
}
```

The writer emits fields in declaration order, skipping `@skip`; the reader uses
`pengu_json_skip` for unknown keys, so a JSON document produced by another
version of the rune still decodes.

### 9.8 `with:` builders

```pengu-fragment
var p as Point with:
    set .x is 10
    set .y is 20
    calling .shift with 5, 3
```

A builder allocates a zeroed temporary, applies `set .field` and calls, and
evaluates to the value. Only `set .field is ...` and calls on the target are
allowed (`E0014`); `if`, `var`, `defer` and `banish` are rejected. Mutability
follows the binding: `let p with:` builds once and freezes the name; `with
let_ptr:` where `let_ptr as ref to T` stays mutable because the pointee is.

## 10. Methods and concepts

### 10.1 `enchanting` — methods on a type

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

* `self` is implicit and has type `ref to Player`, so fields are written
  `self->hp`. `self.hp` is `E0003`.
* A method declared with `ritual` is static: no `self`, called on the type name
  (`calling Player.new_hero with "Ada"`). Using `self` there is `E0033`.
* Calling a ritual on an instance, or an instance method on a type, is `E0034`.
* `enchanting` works on user types and on built-in containers, including generic
  forms: `enchanting list of shard T:`.

A method becomes a free C function whose first parameter is the receiver
pointer, named `<Type>_<method>`:

```c
void Player_heal(Player* self, int32_t amount) {
    self->hp = (self->hp + amount);
}

/* call site */
Player_heal(&p, 2);
```

There is no vtable: `bind` and concepts are resolved at compile time, so a
concept method call is a direct C call to the concrete implementation.

### 10.2 `@mutates`

`@mutates` declares a method whose result is assigned back to the receiver. The
body is written as if it were pure — `self` is not mutated and the body returns
the new value — and the assignment happens at the call site.

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    @mutates
    weave grown with by as int into Player:
        return with name is self->name, hp is self->hp + by
```

It is valid only inside `enchanting`, the return type must be the receiver's
type, and one C function serves both the pure and the in-place surface forms.

### 10.3 `concept` — compile-time contracts

```pengu
concept Speaker:
    weave greet with target as string into string
```

A concept lists method signatures only — no bodies, no fields, no state. It may
take type parameters (`concept Container shard T:`). `ritual` methods inside a
concept are not supported in 0.28.0 (the checker records the modifier as the
method name); declare rituals in `enchanting` instead.

### 10.4 `bind` — implementing a concept

```pengu
concept Speaker:
    weave greet with target as string into string

rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with target as string into string:
        return "Woof, {target}!"
```

| Rule | Diagnostic |
| --- | --- |
| Every required method must be implemented | `E0031` |
| Parameter count/types and return type must match exactly | `E0030` |
| Type and concept must exist before the `bind` | `E0004` |
| One type may bind any number of concepts | — |
| No default methods: each `bind` writes every body | — |

### 10.5 Method resolution

`calling x.m with ...` resolves in this order:

1. Unwrap `ref to`, `alias`, `seal` and `frozen` to the base type.
2. If `x` is a type parameter, use its `where` bounds.
3. Look up `(base type, method)` in the method table populated by `enchanting`
   and `bind`.
4. Look up the monomorphised name (`Box_int` → `Box`).
5. Look up the concept-binding table.
6. Fall back to built-in container methods (`push`, `pop`, `len`, `get`, …).
7. Otherwise `E0004`.

Resolution is static; there is no vtable and no dynamic dispatch.

### 10.6 Built-in concepts

| Concept | Enables |
| --- | --- |
| `Num` | `+`, `-`, `*`, `/`, unary `-` |
| `Integrum` | `%`, `&`, `&#124;`, `^`, `<<`, `>>`, `~`, comparisons |
| `Real` | float arithmetic and comparisons |
| `Par` | `==`, `!=` |
| `Ordo` | `<`, `<=`, `>`, `>=` |
| `Vinculum` | usable as a `map` key (hashing) |
| `Imago` | shallow structural copy (`_pengu_clone_<T>`) |
| `Nexus` | first-level destruction (`_pengu_cleanup_<T>`, invoked by `banish`) |
| `Json` | JSON codec (`to_json` / `from_json`, see §9.7.1) |
| `Forma` | string interpolation (`"{x}"`) |
| `Iterabilis` | `for x in col` |
| `Donum` | `donum T` default value |

`Integrum` and `Real` are disjoint refinements of `Num`; a type satisfies `Num`
through either. A generic that only needs `+ - * /` should bound on `Num`.

## 11. Generics

### 11.1 `shard`

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x
```

A `shard` parameter is in scope from the `with` list to the end of the
declaration, including the return type and the body. Every concrete use
instantiates a specialised C function or struct (`identity_int`,
`Box_of_string`). Nesting is supported: `Box of (Box of int)`.

Explicit arguments are available when inference cannot see them:

```pengu-fragment
var a as int is calling identity of int with 5
var b as string is calling identity of string with "hi"
```

Each instantiation is a separate C function, suffixed with an instantiation
number:

```c
int32_t d2_identity_inst3(int32_t x) { return x; }
```

The suffix is internal; the PenguScript name stays `identity`. A generic rune
instantiates a struct per type argument, and only the instantiations the
program uses are emitted (DCE).

### 11.2 Bounds

```pengu
weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if xs.len == 0:
        return fallback
    return xs at 0
```

Bounds are written with `where`; several are joined with `and`
(`where T: Num and T: Ordo`). A bound is what lets a generic body use an
operator or method on `T`; without it, the operator is `E0005`.

### 11.3 `donum T`

`donum T` is the default value of a defaultable type: `0` for numbers, `false`,
`""`, a zeroed struct, an empty container.

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

A rune or echo implements `Donum` automatically when every field does. A generic
container needs the bound: `rune Box shard T where T: Donum:`.

### 11.4 Generic methods and derivation

```pengu
rune Point shard T derive Par, Ordo:
    x as T
    y as T
```

Derived concepts on a generic become bounds on its parameters; the check happens
at each substitution. `derive Donum` is never written (`E0005`).

### 11.5 Limits

* Associated types are not implemented (deferred).
* There are no wildcard or higher-kinded parameters.
* Generic types and types with methods are not module-scoped: two modules
  declaring the same generic name is `E0070`.

## 12. Optionals and errors

### 12.1 `maybe T` and `result of T to E`

* `maybe T` answers *is there a value?* — lookups, optional fields, "find".
* `result of T to E` answers *what went wrong?* — I/O, parsing, network.

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

`maybe T` is a `PenguMaybe` — a flag plus a boxed payload. `some x` allocates
the payload and moves the value into it:

```c
PenguMaybe m = __extension__(({ int32_t _p = 3;
    int32_t* _h = malloc(sizeof(int32_t)); if (!_h) abort();
    *_h = _p; PenguMaybe _r = pengu_maybe_some(_h); _r; }));
```

Reading a present value dereferences and copies it out; `banish` frees the box.
The boxed payload is why `some x` moves an owning value instead of copying it.

### 12.2 Constructors

| Constructor | Produces |
| --- | --- |
| `some x` | present `maybe T` |
| `maybe none` | empty `maybe T` |
| `calling ok_of with v` | `ok` side of a `result` |
| `calling err_of with e` | `err` side of a `result` |

`ok` and `err` are **not** keywords or constructors: `ok 1` is
`E0004: Undefined identifier 'ok'`. `result of T` without `to E` defaults `E` to
`error` (a `const char *`); prefer naming the error type.

### 12.3 Inspection and unwrapping

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

`maybe` exposes `.is_present` and `.value`; `result` exposes `.is_ok`,
`.value` and `.error` (alias `.err`). Reading `.value` when absent is undefined —
guard first, or use `as`, `or else`, `or return`, `try` or `or:`.

### 12.4 `or else`, `or return`, `try`, `or:`

* `x or else fallback` — evaluates `fallback` only when absent or errored.
* `x or return expr` — runs the pending `defer`/`errdefer` cleanups and returns
  `expr` from the enclosing weave.
* `try x` — propagates an empty `maybe` or an error `result` from the enclosing
  function; the return type must be compatible. The function must
  return a `maybe` or a compatible `result`.
* `x or:` — a block that handles the failure; inside it, `error` is bound to the
  failure payload (type `string` for `maybe`, the error type for `result`) and
  owns it.

```pengu-fragment
var parsed as JsonValue is calling json.parse with text or:
    calling spark.println with "invalid: {error}"
    return 1
```

`error` is only visible inside the `or:` block (`E0015` outside). In arithmetic
position, unwrap expressions need parentheses: `10 + (bonus or else 0)`.

### 12.5 `panic`

`panic` aborts the process after printing the message and a stack trace
(`std.spark.panic`). It is for bugs and unsatisfiable states, never for expected
failure — expected failure is a `result`.

### 12.6 `defer` and `errdefer`

```pengu-fragment
weave copy_file with src as string, dst as string into result of void to IoError:
    var in as string is try calling archivum.read_file_result with src
    defer banish in
    var out as string is calling transform with in
    errdefer banish out          # runs only if the weave returns an error
    if out.len == 0:
        return calling err_of with IoError.Unknown
    return calling ok_of with 0
```

`defer` runs at scope exit on every path; `errdefer` runs only when the scope
exits via an error `return` (a `result` error). Both run in LIFO order and both
run before an `or return`/`try` propagates.

### 12.7 Ownership of boxed values

`some`, `ok_of` and `err_of` box the payload with a `memcpy`. When the operand is
a live owning slot (a variable, a field, `essence of`), the constructor **moves**
it: the source is emptied and the box becomes the only owner. Do not use or
`banish` the source afterwards. An rvalue is copied into the box directly, and a
borrowed parameter is cloned, so the caller keeps its buffer.

`banish m` releases the payload the box owns and then the box.

## 13. Memory

### 13.1 The model

No GC, no borrow checker. Since 0.52 there are three layers on top of the
manual model, and each one is opt-in or visible in the type:

* **Layer 1 — `derive Drop`**: a rune is destroyed when it leaves the scope, in
  every path, and it is move-only (§13.9).
* **Layer 2 — `std.consortium`**: `Rc`/`Arc`/`Weak` add reference counting when
  several owners must outlive each other (§13.11).
* **Layer 3 — copy-on-write containers**: copying a `string`/`list`/`map` is
  O(1) and the first mutation clones the buffer (§13.12).

Everything else keeps the manual model: you allocate, you `banish`. The
compiler checks types and, with one syntactic exception (boxing moves), does not
track lifetimes across functions.

```pengu
weave main into int:
    var s as string is "hello"
    defer banish s
    calling print with s
    return 0
```

### 13.2 `banish`

`banish target` accepts a mutable lvalue of type `ref to T`, `string`,
`list of T`, `map of K to V`, `maybe T`, `result of T to E`, or a rune with
`derive Nexus` (or with a cleanup helper).

| Target | Emitted C |
| --- | --- |
| `string` | `pengu_banish_string(&s)` |
| `list of T` | `pengu_banish_list(&l)` |
| `map of K to V` | `pengu_banish_map(&m)` |
| `ref to T` | `pengu_banish((void*)p)` |
| `maybe` / `result` | payload + box |
| rune with `Nexus` | `_pengu_cleanup_T(&v)` |
| element (`xs at 0`, `m at "k"`) | releases that element in place |

Banishing a string or container resets it to empty. A borrowed string
(`is_owned == 0`) is a safe no-op. Banishing a `list of string` frees the list's
own buffer but **not** the strings inside it: release each string, or use
`pengu_banish_string_list`.

Rejected targets (`E0008`): literals, temporaries (assign to a variable first),
`seal` newtypes (convert explicitly), `frozen` values, and constants.

### 13.3 `defer` and `errdefer`

Schedule a release instead of running it now. `defer` runs at scope exit on every
path; `errdefer` only on an error return. Both are LIFO.

```pengu-fragment
var buf as list of int is [1, 2, 3]
defer banish buf
```

### 13.4 What the compiler does not do

* It does not free a plain container at scope exit: `string`, `list` and `map`
  still need `banish`. Only runes with `derive Drop` are released automatically.
* It does not detect double free or use after free when you `banish` by hand.
  It does detect a *use of a moved value* and an *implicit copy of a `Drop`
  value* inside a function (`E0080`, `E0081`).
* It does not track ownership through function boundaries: a parameter of
  container type is a borrow (§13.7), and whoever allocates decides who
  releases; the API must document it.
* It does not free the elements of a `list`/`map` when the container is
  banished: only the element buffer is released, and nested `string`s leak
  unless you release them explicitly (§13.12, `free_strings` in `std.json`,
  `std.toml`, `std.yaml`).

### 13.5 Owned temporaries in expressions

Interpolation (`"{x}"`), string concatenation (`+`) and a string view
(`s at a to b`) produce a fresh owning `string`. When such a value is used as a
call argument the compiler frees it right after the call, in the same
statement:

```pengu-fragment
calling print with "hi {i}!\n"     # the formatted string is freed
set acc += "{i}"                    # appends without leaking the old buffer
```

`+=` on a `string` lowers to `pengu_string_append`, which releases the previous
buffer only when the variable owned it, so appending to a borrowed parameter
never frees the caller's memory.

### 13.6 Boxed values move

`some x`, `ok_of x`, `err_of x` empty a live owning source slot (see §12.7).
After boxing, the source is empty; banishing it is a no-op, using it is a bug.

### 13.7 Returned values and parameters

* A weave that returns a `string`, `list` or `map` returns ownership to the
  caller; the caller banishes it.
* A parameter of string/container type is **borrowed** by the callee, unless the
  signature says otherwise. The callee must not banish it.
* A returned `ref to T` is a borrowed view unless the module documents a
  transfer of ownership.
* Crossing a task boundary is a transfer: `filum.start` moves owning values and
  requires `@shared` for refs; `coro.start` moves them too, but accepts `ref to
  T` without `@shared` because the coroutine never changes thread. In both cases
  the original binding becomes unusable (`E0008`).

### 13.8 Debugging leaks

* Build debug and run under `valgrind --leak-check=full` or ASan
  (`cc -fsanitize=address`); the generated C is ordinary C.
* The runtime keeps a 64-frame ring buffer for panic traces, so a `panic` points
  at the line that raised it.
* `std.arena` is the escape hatch for a group of allocations with one lifetime:
  allocate from the arena, then `banish arena` to release everything at once.

### 13.9 `derive Drop`: deterministic destruction

`derive Drop` turns a rune into an owned value with a destructor. Three things
change, and all three are visible in the declaration:

1. It is destroyed at every scope exit — `return`, `break`, `continue`, the end
   of the block, and the error path of `or return` / `try`.
2. Assigning, returning or binding it **moves** it: the source is emptied and
   using it again is `E0080`.
3. Copying it implicitly is `E0081`; the explicit copy is `.clone()`.

```pengu
rune Buffer derive Drop:
    data as string
    size as int

weave make_buffer with text as string into Buffer:
    return with data is text, size is 1

weave main into int:
    var a as Buffer is calling make_buffer with "x"
    var c as Buffer is calling a.clone      # deep copy
    calling print with "{c.size}"
    return 0
```

The destructor is `_pengu_cleanup_Buffer`, the same first-level cleanup that
`derive Nexus` generated, plus a `memset` that makes it idempotent:

```c
static inline void _pengu_cleanup_Buffer(Buffer* p) {
    pengu_banish_string(&(p->data));
    (void)p;
    memset(p, 0, sizeof(*p));
}
```

The clone is a field-by-field deep copy (`_pengu_deepclone_Buffer`), and the
destructor calls are inserted at every exit:

```c
Buffer a = d_make_buffer(pengu_string_from_cstr_len("x", 1));
Buffer c = _pengu_deepclone_Buffer(&(a));
/* ... */
_pengu_cleanup_Buffer(&(c));
_pengu_cleanup_Buffer(&(a));
```

`banish` still works on a `Drop` value and is a no-op afterwards, because the
cleanup zeroes the value: `banish a` followed by the automatic drop frees once.

A `Drop` type may not be generic, and its fields may not be `maybe`/`result`
(the deep clone cannot copy those boxes yet); both are `E0005` with a message
that says what to do instead.

### 13.10 Move by default

Only `derive Drop` types move. A move is the destination taking the value and
the source losing its destructor; the C for it is a plain struct assignment plus
the absence of the cleanup call:

```pengu-fragment
var a as Buffer is calling make_buffer with "x"
var b as Buffer is a          # moves: `a` is unusable now
```

```c
Buffer b = a;                 /* no _pengu_cleanup_Buffer(&(a)) later */
```

Using the moved binding is `E0080`:

```pengu-fragment
calling print with "{a.size}"   # error[E0080]: value 'a' was moved
```

Moving out of a **borrowed** place is `E0081`: a parameter, a field or a
dereference. A parameter of a `Drop` type is a borrow, so passing a value to a
function does *not* move it; the callee must `.clone()` if it wants to keep it:

```pengu-fragment
weave consume with b as Buffer into int:
    return b.size             # borrow: fine
```

Explicit destruction is `.drop()`, which runs the destructor immediately and
leaves the value in zero; returning a `Drop` value by value from an
`@export`-ed weave is `E0084`, because the C caller has no destructor to call.

### 13.11 Shared ownership: `Rc`, `Arc`, `Weak`

`std.consortium` adds reference counting for the cases where ownership cannot be
threaded through the code:

| Type | Copy | Crosses `filum.start` | Mutation |
| --- | --- | --- | --- |
| `Rc of T` | implicit, non-atomic increment | no (`E0082`) | `get_mut`, `make_mut` |
| `Arc of T` | `.clone()`, atomic | yes, if `T` is `@shared` (`E0083`) | `make_mut` |
| `WeakRc of T` / `WeakArc of T` | implicit, weak increment | no / yes | none |

```pengu
import std.consortium
import std.spark

weave main into int:
    var r as Rc of int is calling Rc.new with 42
    calling spark.println with "{calling r.strong_count}"   # 1
    banish r
    return 0
```

`new` and the destructor are the interesting lowering:

```c
Rc r = __extension__(({ Rc _rcn = {0};
    _rcn.ptr = pengu_rc_new(sizeof(int32_t), NULL, NULL);
    *((int32_t*)_rcn.ptr) = (42); _rcn; }));
/* ... */
if ((r).ptr) { pengu_rc_release((r).ptr); (r).ptr = NULL; }
```

The payload destructor and cloner travel inside the header, so the drop site
does not need to know `T`: `pengu_rc_new(size, drop, clone)`. For a `Drop`
payload the compiler passes `_pengu_rc_drop_T` and `_pengu_rc_clone_T`, both
`static inline` next to `_pengu_cleanup_T`.

`get` returns `ref to frozen T`, so a shared value cannot be mutated by
accident. `get_mut` succeeds only when the handle is the only owner (`strong ==
1 and weak == 0`); `make_mut` clones the payload when it is shared, which is why
it is spelled out at the call site. `WeakRc.upgrade` returns `maybe Rc of T` and
is `none` once the value is gone — that is how a cycle is broken.

### 13.12 Copy-on-write containers

`string`, `list of T` and `map of K to V` keep a reference counter in front of
the buffer. Copying a binding is O(1), and the first mutation clones:

```pengu-fragment
var s as list of int is list of int
calling s.push with 1
var t as list of int is s
calling t.push with 2          # clones: `s` keeps one element
```

```c
PenguList s = pengu_list_new(sizeof(int32_t), 0);
pengu_cow_list_push(&(s), &_push_tmp);
PenguList t = s;
pengu_cow_list_share(&(t));
pengu_cow_list_push(&(t), &_push_tmp);   /* ensure_unique clones the buffer */
```

The header is two words in front of `data`:

```c
typedef struct { uint64_t magic; int32_t rc; int32_t pad; } PenguCowHdr;
typedef struct { size_t elem_size; void (*drop_elem)(void *); } PenguCowAux;
/* [PenguCowAux][PenguCowHdr][elements...] */
```

Three methods expose the state: `is_shared`, `ref_count` and `make_unique`
(force a private buffer now). `banish` releases the buffer once the last binding
goes away. Element drop is still the programmer's job: the runtime cannot tell
whether an element handle is owned or borrowed, so freeing elements
automatically is deferred to a future release (see `PENGUNIC` §21.4).

Copy-then-mutate inside a loop is the pattern where COW is slower than plain
copies. `psc check --lint=cow` reports it as `W0008` (informational, off by
default).

Composition with `fundere` (§9.9) lets a host declare a field with the same
name as one promoted from an embed: the host's field wins and the embed's field
stays reachable through the explicit path. `psc check --lint=shadow` reports
that deliberate shadowing as `W0009` (informational, off by default).

## 14. Attributes

Attributes are written on the line above the declaration they modify.

| Attribute | Applies to | Effect | C |
| --- | --- | --- | --- |
| `@inline` | `weave` | force inlining | `static inline __attribute__((always_inline))` |
| `@cold` | `weave` | mark a rare path | `__attribute__((cold))` |
| `@deprecated("msg")` | any declaration | warn on use (`W0006`) | `__attribute__((deprecated("msg")))` |
| `@noreturn` | `weave`, `declare`, `antiquus` | the call never returns | `__attribute__((noreturn))` |
| `@export("symbol")` | `weave`, `antiquus` | pin the C symbol and keep it alive (DCE root) | exported C function |
| `@packed` | `rune` | remove struct padding | `__attribute__((packed))` |
| `@align(N)` | `rune` | set alignment | `__attribute__((aligned(N)))` |
| `@mutates` | method in `enchanting` | assign the result back to the receiver | one C function, two call forms |
| `@shared` | `rune`, `omen` | allow `ref to T` to cross a `filum.start` boundary | no code change; compile-time flag |
| `@spawn` | `weave` | marks the function that starts a thread; validates worker and ownership at each call | no code change; compiler contract |
| `@coroutine` | `weave` | marks the function that starts a coroutine; validates worker and ownership | no code change; compiler contract |

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

`@export` without a project-specific prefix can collide with libc symbols; prefix
it (`@export("mylib_fast_double")`). `@packed` and `@align(N)` change the ABI of
the struct: only use them for wire or on-disk formats, and mirror the layout in
the C side exactly. `@shared` is a promise that the rune's methods synchronize;
the compiler checks the boundary, not the implementation.

### 14.1 Threads

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

`start` moves owning arguments into the worker; a moved local cannot be read
again (`E0008`). `start0`, `start2` and `start3` cover workers with zero, two and
three arguments. A `ref to T` requires `@shared` on `T`; scalars are copied.
`join` waits and returns `result of void to ThreadError`; `detach` is
fire-and-forget; `free` releases the handle. `Thread` is a copyable id, so a
supervisor can keep it. TLS, `Pool` and `parallel_for` live in `std.filum` too.

### 14.2 Coroutines

A coroutine is an explicit, cooperative, *stackful* task: it suspends at
`coro.yield` and only advances when its owner calls `resume`. It runs on the
thread that created it, so there are no data races or migration; use
`std.filum` for parallelism.

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

`start` creates the coroutine suspended and moves the owning argument; `start0`
covers a worker with no arguments. `resume` runs it to the next `yield` or until
it returns, and reports `suspended` or `finished`; `status` reads the state
without running it. `free` releases only a finished coroutine; `abandon`
discards a suspended one (and does not run its `defer`s). `yield` outside a
coroutine, or `resume` on a finished one, is a panic: a program bug, not a
recoverable error.

The default stack is 64 KiB (shared, recycled arena); a `ref to T` does not
require `@shared` because it never crosses threads, and a `string`/`list`/`map`
moves into the worker. There is no automatic scheduler, `async`/`await`
syntax, cancellation or value passing through `yield`: control is explicit and
data travels through `ref to` or the owner's shared state. The scheduling
policy is a user-space object, `std.reactor.EventLoop`, created explicitly,
started with `spawn` and run with `run`; `std.coro` alone never resumes
anything on its own:

```pengu
import std.reactor

weave worker with loop as ref to reactor.EventLoop, n as ref to int into void:
    calling loop.sleep_ms with 10

weave main into int:
    var loop as reactor.EventLoop is calling reactor.EventLoop.new
    calling loop.spawn with worker, 0
    calling loop.run          # epoll_wait/poll + resume of ready tasks
    calling loop.close
    return 0
```

The `*_async` variants in `std.net`, `std.archivum` and `std.petitio` are
ordinary functions with the same return types as their synchronous siblings:
they suspend the current coroutine and must be called from a loop task; outside
one they panic. There is no function-coloring transformation and no hidden
state machine.

**Translation to C.** Each `Coroutine` wraps a minicoro `mco_desc`
(`runtime/pengu_coro.c`): `pengu_c_coro_new` allocates the argument box and the
64 KiB stack from a per-thread arena with a free-list; `resume` checks that the
current thread is the owner (TLS) and calls `mco_resume`; `yield` calls
`mco_yield`. The ownership contract is enforced in Pengunic before C is
emitted; the runtime keeps the wrong-thread and stack-exhaustion diagnostics.
`std.coro` is not available on wasm.

`@coroutine` marks the function that starts the task (the implementation of
`std.coro.start`); if you write your own starter, mirror the contract: first
argument the worker, remaining arguments the worker's, worker returns `void`.

## 15. Tests and tooling

### 15.1 `test` blocks

```pengu
import std.ward

test "arithmetic":
    calling ward.assert_eq_int with 1 + 1, 2

test string_formatting:
    calling ward.assert_eq_string with "abc", "abc"
```

A test is `test <name>:` where the name is a string literal or an identifier.
Bodies are type-checked in every mode (`check`, `build`, `run`, `test`), but the
C harness is emitted only for `psc test`. `test` blocks belong in `.pengu` files, not in `.d.pengu`.

```console
$ psc test              # run every test block in the project
$ psc test --watch      # rerun on change
$ psc test --diagnostics=json   # JSON Lines events for CI
```

### 15.2 Commands

| Command | Purpose |
| --- | --- |
| `psc build [TARGET]` | compile to C and link |
| `psc run FILE [-- args]` | build and run a program or a single file |
| `psc check [TARGET]` | type-check only |
| `psc emit-c FILE` | print the generated C |
| `psc test` | run `test` blocks |
| `psc fmt [PATHS]` | format (`--check`, `--diff`, `--stdin`, `--indent=N`, `--tabs`) |
| `psc doc` | generate `docs/api` from `##` comments (`--include-std`, `--html`, `--output=DIR`) |
| `psc bind HEADER` | generate a `.d.pengu` from a C header (`--prefix`, `--links`, `--ignore`, `--output`) |
| `psc init` / `psc new` | scaffold a project |
| `psc add` / `psc remove` / `psc update` | dependencies |
| `psc lsp` | start the language server (stdio) |
| `psc doctor` | diagnose the toolchain |
| `psc assets` | embed project assets |
| `psc gc` | remove stale build artifacts |
| `psc tree` | print the module graph |
| `psc time` | time the compilation phases |
| `psc watch` | rebuild on change |
| `psc eval` | evaluate an expression |
| `psc version` / `--version` / `-V` | print the compiler version |

### 15.3 Build options

| Flag | Meaning |
| --- | --- |
| `--profile=debug` &#124; `--profile=release` | optimisation and checks |
| `--target=TRIPLE` &#124; `--target=wasm` | cross-compile |
| `--cc=NAME` | C compiler |
| `--out=PATH` | artifact path |
| `--exe` | link an executable even for a library project |
| `--strict-c99` | portable C99 (no statement expressions) |
| `--release-unsafe` | disable bounds checks |
| `--verbose` | print the compiler command |

`--diagnostics=json` on `check`/`build`/`test` emits machine-readable diagnostics;
`--json` is accepted as an alias by `psc check` (parity with older releases). Exit
codes: `0` success, `1` compilation or test failure, `2` usage error.

### 15.4 Project manifest

`pengu.toml` (preferred) or `pengu.yaml` at the project root declares `name`,
`version`, `src_dir`, `lib_dir`, `std_dirs`, `dependencies`, `output`, `cc`,
`ldflags`, `cflags`. `psc init` writes a minimal one.

### 15.5 `psc doc`

`psc doc` renders one page per module from the `##` comments. With
`--include-std` it also documents the standard library, which is how
[docs/api](api/README.md) is produced:

```console
$ psc doc --include-std --html --output docs/api
Generated 182 module(s) in docs/api
```

Each page starts with `# <module>`, a `> Source:` line and the module docstring,
then one `###` section per exported symbol with its signature and its `##` text.
The index is `docs/api/README.md`, and `--html` adds a filterable
`docs/api/index.html`.

## 16. Chaining, pipes, tuples and shorthand

### 16.1 Method chains

A chain starts with a `calling` expression and continues with `.method` links.
Each link may carry its own `with` list:

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

The chain above is the multi-line form; it is the one to use when a link takes
arguments. A link is always a method call, never a field read. Every link but
the last must produce a value; a `@mutates` method may only be last.

A continuation line starts with `.` (or `->` for a reference receiver) and is
folded into the previous line before lexing.

### 16.2 Pipes

`pipe` chains **free functions**: the previous value becomes the first argument
of the next call.

```pengu-fragment
var text as string is 42
    pipe spark.str_int

weave editar with value as int, delta as int into int:
    return value + delta

var total as int is calling base
    pipe editar with 2
    pipe editar with 3
```

`pipe` is contextual (a valid identifier), only recognised at the start of a
continuation line. Steps must be free functions, not methods (`E0053`). The last
step may return `void`, in which case the pipe keeps the previous value.

### 16.3 Tuples and multiple returns

```pengu
weave divmod with a as int, b as int into (int, int):
    return a / b, a % b

weave main into int:
    let (q, r) is calling divmod with 7, 2
    return q + r
```

A tuple type is `(T, U)`; a tuple value is `(a, b)`. Destructuring works on
tuples and runes. Tuples are C anonymous structs and are not heap-allocated.

A tuple type lowers to a struct named after its component types, with fields
`first`, `second`, `third`, …:

```c
typedef struct { int32_t first; int32_t second; } PenguTuple_int32_t_int32_t;

PenguTuple_int32_t_int32_t _pengu_tup0 = d2_divmod(7, 2);
int32_t q = _pengu_tup0.first;
int32_t r = _pengu_tup0.second;
```

A `let a, b is expr` stores `expr` in a temporary first, so the expression runs
exactly once; the two bindings are reads of that temporary.

### 16.4 Shorthand struct initialisers

Inside a `with` literal, a field may omit `is value` and take the same-named
binding:

```pengu-fragment
weave make into Player:
    let name is "Ada"
    var hp is 100
    return with name, hp        # same as: with name is name, hp is hp
```

Both forms can be mixed; a field whose value is not a single bare name needs the
explicit `is` form.

## 17. Deprecation

Mark a declaration with `@deprecated("reason")`; every use emits `W0006` with
that reason, and `psc doc` shows a deprecated badge.

```pengu
## @deprecated use read_file_result to distinguish the failure cause
@deprecated("use read_file_result to distinguish the failure cause")
weave read_file with path as string into maybe string:
    return maybe none
```

Policy: a deprecated symbol keeps working for at least one minor release and is
removed only in a major release; the changelog names the replacement. Do not
deprecate without naming the alternative.

## 18. Diagnostics

Every diagnostic has a stable code. Errors stop the compilation; warnings do not.

| Code | Meaning |
| --- | --- |
| `E0000` | syntax error |
| `E0001` | `const` inside a weave |
| `E0002` | top-level `var`/`let` |
| `E0003` | `self.` instead of `self->` |
| `E0004` | undefined name, member, module or label |
| `E0005` | type mismatch |
| `E0006` | mutability violation |
| `E0007` | `break`/`continue` outside a loop, or a label that does not enclose |
| `E0008` | invalid memory operation (`banish` of a temporary, literal, `frozen`, …) |
| `E0014` | invalid statement inside a `with:` builder |
| `E0015` | array dimension unknown |
| `E0019` | invalid interpolation expression |
| `E0020` | `return` type mismatch |
| `E0021` | wrong number of generic arguments |
| `E0022` | type parameter used outside its declaration |
| `E0023` | more than one `many` parameter |
| `E0024` | `many` is not the last parameter |
| `E0026` | more than one `insignia` |
| `E0027` | duplicate omen variant value |
| `E0028` | payload on a string-valued omen |
| `E0029` | non-constant omen variant value |
| `E0030` | concept method signature mismatch |
| `E0031` | concept method not implemented |
| `E0032` | bound not satisfied |
| `E0033` | `self` inside a `ritual` |
| `E0034` | ritual called on an instance, or method on a type |
| `E0035` | name not a valid C identifier |
| `E0036` | invalid import alias |
| `E0037` | duplicate binding name (loop index/element) |
| `E0038` | reserved C name |
| `E0039` | field name collides with a C name |
| `E0041` | array size invalid |
| `E0042` | invalid range |
| `E0043` | private symbol accessed from another module |
| `E0044` | non-exhaustive `judge` |
| `E0047` | method not available on a primitive |
| `E0049` | operator not allowed by the bound |
| `E0050` | infinitely sized type |
| `E0051` | dangling reference |
| `E0052` | duplicate concept |
| `E0053` | wrong composition form (`.` vs `pipe`) |
| `E0054` | invalid `derive Json` (shape, attribute or field type) |
| `E0056` | attribute not allowed here |
| `E0057` | character out of range |
| `E0059` | `antiquus` without a body |
| `E0063` | `static` in the wrong position |
| `E0064` | invalid test name |
| `E0065` | field name collision in C |
| `E0066` | `@mutates` used in value position |
| `E0067` | `@mutates` on a non-method |
| `E0068` | `@mutates` return type is not the receiver |
| `E0069` | duplicate loop label |
| `E0070` | duplicate type name in a module |
| `E0071` | unknown, repeated or misplaced named argument |
| `E0072` | parameter without a default after a defaulted one |
| `E0073` | default value is not constant or does not match the type |
| `E0074` | `many` parameter with a default value |
| `E0075` | `many` parameter in `declare` |
| `E0079` | destructuring with the wrong number of names |
| `E0076` | map literal without a type annotation |
| `E0077` | `with` target is not an addressable place |
| `E0080` | use of a moved value (§13.10) |
| `E0081` | implicit copy of a `Drop` value; use `.clone()` |
| `E0082` | an `Rc` cannot cross a thread or coroutine boundary |
| `E0083` | an `Arc of T` crossing a thread boundary needs `T` to be `@shared` |
| `E0084` | an `@export`-ed weave cannot return a `Drop` value by value |
| `E0085` | a `fundere` type is not a `rune` |
| `E0087` | a field promoted by `fundere` is ambiguous between two embeds |
| `E0088` | a method promoted by `fundere` is ambiguous between two embeds |
| `E0089` | a `fundere` type has no implicit field name; write `as name` |
| `W0008` | copy of a container mutated inside a loop (`--lint=cow`) |
| `W0009` | a host field shadows a field promoted by `fundere` (`--lint=shadow`) |
| `W0001` | `transmute` used |
| `W0002` | `echo` field access (unchecked union) |
| `W0004` | unreachable code |
| `W0005` | shadowed binding |
| `W0006` | deprecated symbol used |
| `W0007` | unsafe operation |
| `W0013` | range is empty or reversed |

`psc check --diagnostics=json` and `psc build --diagnostics=json` emit each diagnostic as a JSON object
with `code`, `severity`, `message`, `file`, `line`, `column` and optional
`help`.

## 19. Complete example

A task list that exercises `omen`, `rune`, `enchanting`, `judge`, `with`,
`maybe`, `for`, `defer` and string interpolation:

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

Output:

```text
write docs [high]
2 task(s)
```

The interesting lowering: `Task` becomes a C struct, `Priority` an enum,
`judge p:` a `switch`, the `with` literal a compound literal, the `maybe` a
`PenguMaybe` whose payload is heap-boxed, and `defer banish tasks` a cleanup
call emitted on every return path.

## Appendix A. Keywords

| Keyword | Meaning |
| --- | --- |
| `alias` | transparent type synonym |
| `and` | logical and (also joins bounds) |
| `antiquus` | function whose body is literal C |
| `as` | checked cast / narrowing |
| `banish` | release owned storage |
| `bind` | implement a concept for a type |
| `break` | leave a loop |
| `bytes` | byte-view operator (`bytes of`) |
| `calling` | call prefix |
| `chr` | integer to character |
| `concept` | compile-time contract |
| `const` | top-level compile-time value |
| `continue` | next iteration |
| `cyclus` | mark an intentionally recursive type |
| `declare` | external C function |
| `defer` | run at scope exit |
| `defined` | compile-time name test |
| `derive` | generate concept implementations |
| `donum` | default value of a type |
| `echo` | C union |
| `else` | fallback branch |
| `enchanting` | methods on a type |
| `errdefer` | run on error return |
| `error` | failure payload inside `or:` |
| `essence` | dereference (`essence of`) |
| `false` | boolean false |
| `for` | loop |
| `from` | range start / loop form |
| `fundere` | declare embedded runes (composition, no inheritance) |
| `if` | conditional |
| `import` | module import |
| `in` | membership / iteration |
| `include` | add a C header |
| `insignia` | C name prefix |
| `into` | return type separator |
| `is` | predicate / naming form |
| `judge` | pattern match |
| `lambda` | anonymous static function |
| `ldflag` | raw linker option |
| `let` | immutable binding |
| `link` | link a library |
| `many` | variadic parameter marker (see §6.3) |
| `maybe` | optional type / empty constructor |
| `none` | empty `maybe` (`maybe none`) |
| `not` | logical negation / `not in` |
| `null` | null pointer value |
| `of` | type constructor (`list of T`) |
| `omen` | enum / sum type |
| `or` | logical or / fallback forms |
| `ord` | character to integer |
| `return` | return from a weave |
| `rune` | struct |
| `seal` | nominal newtype |
| `set` | assignment |
| `shard` | generic type parameter |
| `sigil` | address-of (`sigil of`) |
| `some` | present `maybe` |
| `static` | persistent local |
| `step` | loop stride |
| `test` | test block |
| `to` | conversion / range end |
| `transmute` | reinterpret bits |
| `true` | boolean true |
| `try` | propagate failure |
| `unless` | negated `if` |
| `var` | mutable binding |
| `weave` | function |
| `when` | match arm / compile-time branch |
| `where` | generic bounds |
| `while` | loop |
| `with` | parameter list / literal / builder |

## Appendix B. Runtime representations

| PenguScript | C |
| --- | --- |
| `string` | `typedef struct { char *data; int len; int32_t is_owned; } PenguString;` |
| `list of T` | `typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;` |
| `map of K to V` | `typedef struct { void *state; int len; int cap; size_t key_size; size_t val_size; } PenguMap;` |
| `slice of T` | `typedef struct { void *data; int len; size_t elem_size; } PenguSlice;` |
| `maybe T` | `PenguMaybe` — presence flag + boxed payload |
| `result of T to E` | `PenguResult` — ok flag + boxed payload/error |
| `ref to T` | `T *` |
| `rune` | `struct` with fields in order |
| `echo` | `union` |
| `omen` (numeric) | `enum` |
| `omen` (algebraic) | `struct { int32_t tag; union { ... } data; }` |
| `weave ... into ...` | function pointer type |
| tuple `(T, U)` | named `struct PenguTuple_<mangled>` with fields `first`, `second`, … |
| `Rc of T` / `WeakRc of T` | `struct { void *ptr; }` — `ptr` points **past** a `PenguRcHdr` |
| `Arc of T` / `WeakArc of T` | same handle; the header is `PenguArcHdr` with `_Atomic int32_t` counters |
| copy-on-write buffer | `[PenguCowAux][PenguCowHdr][elements…]`; `PenguCowHdr { uint64_t magic; int32_t rc; int32_t pad; }` |

`PenguRcHdr` is `{ int32_t strong; int32_t weak; uint32_t magic; uint32_t pad;
void (*drop)(void *); void (*clone)(const void *, void *); size_t size; }`: the
payload destructor and cloner travel with the value, so `pengu_rc_release` does
not need a type. A copy-on-write list carries `PenguCowAux { size_t elem_size;
void (*drop_elem)(void *); }` in front of the counter, which is what makes
`banish` release the elements.

Generated helpers: `pengu_string_from_cstr`, `pengu_string_format_ex`,
`pengu_string_copy`, `pengu_banish_string`, `pengu_list_new`, `pengu_list_push`,
`pengu_list_at`, `pengu_banish_list`, `pengu_map_new`, `pengu_map_put`,
`pengu_map_get`, `pengu_banish_map`, `pengu_maybe_some`, `pengu_maybe_none`,
`pengu_maybe_is_present`, `pengu_sigil_alloc`, `_pengu_clone_<T>`,
`_pengu_cleanup_<T>`, `_pengu_lambda_<N>`.

## Appendix C. Grammar sketch

A compact EBNF of the implemented language; it omits expression precedence
(§4.1) and the contextual keywords (`over`, `pipe`, `frozen`).

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
weave_decl     = [ "@" attr ] { "@" attr } "weave" [ "inline" ] ident
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
               | for_stmt | judge_stmt | with_stmt | return_stmt | break_stmt
               | continue_stmt | defer_stmt | banish_stmt | expr_stmt
               | "do" ":" block ;
with_stmt      = "with" expr ":" block ;
var_decl       = [ "static" ] "var" ident [ "as" type ] "is" expr
               | "let" ( ident | "(" ident { "," ident } ")" )
                 [ "," ident { "," ident } ] [ "as" type ] "is" expr ;
set_stmt       = "set" lvalue ( "is" expr | op "=" expr ) ;
lvalue         = [ "self" ( "." | "->" ) ] ident
               | lvalue "at" expr | "." ident | expr "." ident ;
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
               | "many" type | "maybe" type | "result" "of" type [ "to" type ]
               | "(" type { "," type } ")"
               | "weave" [ "with" params ] "into" type
               | ident [ "of" type ] ;
```
