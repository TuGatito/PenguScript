# PenguScript Language Reference

> **Version covered:** PenguScript **2.0.0** (synchronized with `VERSION` and `pengu_version.py`; C99/C11 code generator; runtime headers under `pengu_runtime.h`).
> **Language policy.** English is the canonical language of the PenguScript
> documentation, so **this document is the normative one**. A Spanish translation is
> maintained at [`LANGUAGE_Spanish.md`](LANGUAGE_Spanish.md); it is **non-normative**,
> it may lag, and where the two disagree this file wins. The lag is measured and
> cannot grow — see `tests/test_language_policy.py`.
>
> This is the definitive syntax & semantics guide, written against the compiler
> sources (`pengu_grammar.py`, `pengu_checker.py`, `pengu_codegen.py`,
> `pengu_infer.py`, `pengu_runtime.h`). It complements the quick
> [`CHEATSHEET.md`](CHEATSHEET.md) and [`README.md`](README.md), explaining every
> feature with PenguScript examples and generated C.

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
13. [Manual Memory Management](#13-manual-memory-management)
14. [Modules, imports & C interop](#14-modules-imports--c-interop)
15. [Literals: strings, arrays, maps, indent blocks & ranges](#15-literals-strings-arrays-maps-indent-blocks--ranges)
16. [Conditional compilation (`when`)](#16-conditional-compilation-when)
17. [Unit tests (`test`)](#17-unit-tests-test)
18. [Block-style construction (`with:` expressions)](#18-block-style-construction-with-expressions)
19. [Standard library](#19-standard-library)
    - 19.1 [Pure PenguScript Modules](#191-pure-penguscript-modules-38-modules)
    - 19.1.1 [Choosing between `std.loom` and `std.tally`](#1911-choosing-between-stdloom-and-stdtally)
    - 19.1.2 [The four fundamental modules](#1912-the-four-fundamental-modules)
    - 19.1.3 [The data modules: `std.diagnostic`, `std.json`, `std.jsonrpc`](#1913-the-data-modules-stddiagnostic-stdjson-stdjsonrpc)
    - 19.1.4 [The text modules: `std.lingua` and `std.regulus`](#1914-the-text-modules-stdlingua-and-stdregulus)
    - 19.2 [External bindings (satellite repositories)](#192-external-bindings-satellite-repositories)
    - 19.3 [Core Standard Library Examples](#193-core-standard-library-examples)
    - 19.4 [Embedded Project Assets (`arca`)](#194-embedded-project-assets-arca)
    - 19.5 [Memory model: borrowed `string` parameters and expression temporaries](#195-memory-model-borrowed-string-parameters-and-expression-temporaries)
20. [Tooling & project layout](#20-tooling--project-layout)
21. [Complete example](#21-complete-example)
22. [Appendix: Compiler Diagnostic Catalog (`E0000`–`E0050` & Warnings)](#22-appendix-compiler-diagnostic-catalog)

---

## 1. Introduction & principles

PenguScript is an indentation-sensitive, statically typed language that
compiles directly to C99/C11. Its design rules:

- **One keyword per task.** Reserved words are semantic (`weave` for
  functions, `rune` for structs, `omen` for enums/sum types, `calling` for
  calls, `set` for assignment, `banish` for explicit free, …).
- **Explicit over hidden.** Memory is *not* garbage collected: heap values are
  freed explicitly with `banish`, deferred with `defer`/`errdefer`. Who releases
  every runtime helper's result is documented in `pengu_runtime.h`.
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

> [!NOTE]
> **BOM Stripping:** `PenguParser.parse` automatically detects and strips UTF-8 Byte Order Marks (`\xef\xbb\xbf`) from source inputs before tokenization, preventing unexpected syntax errors when files are edited on Windows tools.

### 3.2 Comments & docs

```pengu-fragment
# line comment
## doc comment (used by `pengu doc` and hover/extraction)
# banner --------------------------------------------
## multi-line doc comment
   describing complex APIs
##
```

- Single-line comments begin with `#` (`/#[^#\r\n]*$/m`).
- Documentation comments begin with `##` (`## doc comment` or multi-line `##[\s\S]*?##`). Both `#` and `##` directly preceding declarations are harvested by `pengu doc` and the LSP server.
- **Line Preservation:** The parser executes `_strip_comments` during lexical analysis, replacing comments with whitespace. This guarantees that source line and column numbers remain 100% exact across error reports, LSP spans, and generated C `#line` directives.

### 3.3 Identifiers & visibility

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Style conventions follow `snake_case` for values, variables, and weaves, and `PascalCase` for user types (`rune`, `echo`, `omen`, `concept`).

**Identifiers are ASCII-only.** There is no Unicode identifier support: `日本語`,
`café` or `Ω` as a name is a syntax error (`E0000`), in every declaration position.
The restriction is lexical, so it applies to `const` names, `weave` names, fields,
parameters and type names alike.

This is deliberately narrower than the rest of the toolchain, which is
Unicode-clean elsewhere: source files may carry a UTF-8 BOM, CRLF line endings are
accepted, and **string literals are full Unicode** (`"日本語 café Ω"` is a valid
value, and `"\u{1F427}"` is a valid escape). If you need non-ASCII *text*, put it
in a string; if you need it in an identifier, transliterate
(`const 日本語 as int` → `const nihongo as int`).

- **Module & Rune Privacy (`_` prefix):** Any top-level symbol (function, type, constant) starting with `_` is strictly private to its module. Any rune field starting with `_` (e.g. `_internal_ptr`) is strictly private to the module that declares the rune (and to any `enchanting` block for it, §9.1). Accessing a private symbol from outside its module raises `E0043: PrivateSymbolAccessError`.
- **Compiler Internals (`_pengu_*`):** All compiler-generated symbols, temporaries, and runtime helpers use the `_pengu_` or `pengu_` prefix. Users should avoid declaring identifiers with this prefix to prevent symbol collisions.
- **Discard Binding (`_`):** A standalone underscore `_` acts as a wildcard discard binding (`for _, v in col`). It discards the value without binding an identifier in the symbol table.
- **Reserved Entry Point (`main`):** `main` is reserved as the entry point weave (`weave main …`). It cannot be declared as a local or global variable, constant, or static variable (`var main`, `let main`, `const main`, `static var main` all raise `E0040`).

### 3.4 Reserved words

The following keywords are reserved by PenguScript:

```text
import include link insignia const var let set static weave antiquus declare enchanting
rune echo omen alias seal concept bind shard where when test if
unless else while for in from to step judge calling with into as is many return
break continue defer errdefer banish some ord chr bytes of essence of sigil of
transmute size of try defined not and or lambda null true false maybe none error
derive cyclus donum
```

**Soft Keywords:**
- `frozen`: Active only in type expression positions (`frozen int`, `ref to frozen T`). Identifiers named `frozen` in variable, field, or function names are valid. See [§9.5](#95-frozen--read-only-qualification).
- `inline`, `ritual`: Active only as weave modifiers (`weave inline f into void:`, `inline weave f into void:`, `weave ritual make into T:`). Everywhere else, they are treated as ordinary identifiers.

**C Identifier Protection (`E0035`):**
To guarantee that generated C compiles cleanly without name collisions against the C standard library or C runtime types, PenguScript reserves C standard library type names (`C_RESERVED_TYPE_NAMES`, e.g. `FILE`, `size_t`, `int8_t`, `uint32_t`, `bool`) and common C function names (`C_RESERVED_FN_NAMES`, e.g. `printf`, `malloc`, `free`, `exit`, `memcpy`). Declaring top-level functions or user types with these names raises `E0035`, unless:
1. Declared inside a `.d.pengu` binding file;
2. Prefixed with a leading underscore (`_`); or
3. Prefixed using the module's `insignia` directive.

---

## 4. Type system

### 4.1 Primitive types

Every primitive has **one canonical C type** and a set of accepted Pengu spellings.
The mapping below is exactly what the code generator emits (verified by compiling
each spelling and reading the emitted C); anything in the "also accepted as"
column compiles to the same C type and is therefore interchangeable at the ABI
level.

| Canonical C type | Also accepted as | Size (bits) | Use for |
|---|---|---|---|
| `int32_t` | `int`, `i32`, `int32`, `int32_t` | 32 | **default integer** |
| `int64_t` | `i64`, `int64`, `int64_t`, `long` | 64 | wide signed |
| `int16_t` | `i16`, `int16`, `int16_t`, `short` | 16 | narrow signed |
| `int8_t` | `i8`, `int8`, `int8_t` | 8 | narrowest signed |
| `uint32_t` | `u32`, `uint32`, `uint32_t`, `uint` | 32 | unsigned 32 |
| `uint64_t` | `u64`, `uint64`, `uint64_t`, `ulong` | 64 | unsigned 64 |
| `uint16_t` | `u16`, `uint16`, `uint16_t`, `ushort` | 16 | unsigned 16 |
| `uint8_t` | `byte`, `u8`, `uint8`, `uint8_t` | 8 | **bytes and unsigned 8** |
| `size_t` | `usize`, `size_t` | pointer | **lengths and indices** |
| `intptr_t` | `isize` | pointer | signed pointer-sized |
| `float` | `float`, `f32` | 32 | 32-bit IEEE |
| `double` | `f64`, `double` | 64 | **default float** |
| `char` | `char` | 8 | a single C byte / ASCII character |
| `bool` | `bool` | 8 | `true` / `false` |
| `void` | `void` | – | no value |
| `PenguString` | `string` | runtime | length-prefixed slice (§4.2) |
| `void*` | `opaque` | pointer | opaque C handle |

**`float` is 32-bit, and it is the default.** `float` and `f32` both emit C
`float`; `f64` and `double` both emit C `double`. An earlier revision of this
table claimed `float` was 64-bit and mapped to `double`, which was wrong: it
would have led a reader to expect double precision and silently get single.
Write `f64` explicitly when you need 64-bit precision.

A float **literal** is a `float` (f32) until its context says otherwise, so
`var x as f64 is 3.141592653589793` keeps all 16 digits: a literal folded into a
`double`/`f64` target (or into a `T: Real` parameter that monomorphizes to
`f64`) is emitted as a C `double`, with no `f` suffix. Only a `float`/`f32`
target emits the single-precision `…f` literal.

**`ssize_t` is not a Pengu type.** `CTypeMapper.to_c_type` has an arm for it, but
the grammar's `base_type` production does not list it, so it cannot be written.
Use `isize` (which emits `intptr_t`) instead. The dead arm is recorded in
`AUDIT_1.0_FASE2.md` §2.

**Style.** `int`, `byte`, `size_t`, `float`, `f32`, `f64`, `bool`, `string`,
`void` and `char` are the spellings the standard library uses (`int` 4643 times,
`i64` 463, `size_t` 202, `byte` 197, `u32` 161). The C-style names
(`int32_t`, `uint64_t`, `short`, `long`, `double`, `uint`) exist so a declaration
copied from a C header keeps its exact width without translation, and so
`pengu bind` can emit them verbatim. Use them at a C boundary; prefer the short
forms elsewhere.

<!-- Machine-readable form of the table above. tests/test_docs_primitive_types.py
     compiles each spelling and fails if the emitted C type disagrees. One line
     per canonical C type: ctype: spelling1, spelling2, ... -->
```text prim-c-map
int32_t: int, i32, int32, int32_t
int64_t: i64, int64, int64_t, long
int16_t: i16, int16, int16_t, short
int8_t: i8, int8, int8_t
uint32_t: u32, uint32, uint32_t, uint
uint64_t: u64, uint64, uint64_t, ulong
uint16_t: u16, uint16, uint16_t, ushort
uint8_t: byte, u8, uint8, uint8_t
size_t: usize, size_t
intptr_t: isize
float: float, f32
double: f64, double
```

Integer literal suffixes and `to` casts are available (`1.5 to int`, `x to string`).

<!-- Machine-readable form of the table above. tests/test_docs_primitive_types.py
     parses this block and fails if it disagrees with the mapping that
     CTypeMapper.to_c_type actually emits. One line per canonical C type:
     ctype: spelling1, spelling2, ... -->
```text prim-c-map
int32_t: int, i32, int32, int32_t
int64_t: i64, int64, int64_t, long
int16_t: i16, int16, int16_t, short
int8_t: i8, int8, int8_t
uint32_t: u32, uint32, uint32_t, uint
uint64_t: u64, uint64, uint64_t, ulong
uint16_t: u16, uint16, uint16_t, ushort
uint8_t: byte, u8, uint8, uint8_t
size_t: usize, size_t
intptr_t: isize, ssize_t
float: f32
double: float, f64, double
```

> [!NOTE]
> **Size Estimation (`estimate_size`):**
> The compiler calculates byte size approximations using `estimate_size` (`pengu_types.py`). For `rune` structs, `estimate_size` directly sums the estimated sizes of its constituent fields without computing native C alignment padding. Exact memory layout and struct padding are handled natively by the downstream C compiler during code generation. This estimate is surfaced in LSP hover tooltips and used for container layout heuristics.

### 4.2 Runtime containers

PenguScript defines clean, C-compatible container structs in `pengu_runtime.h`:

| Pengu | Runtime C type | Layout & Struct Definition |
|-------|----------------|----------------------------|
| `string` | `PenguString` | `typedef struct { char *data; int len; } PenguString;` |
| `slice of T` | `PenguSlice` | `typedef struct { void *data; int len; size_t elem_size; } PenguSlice;` |
| `list of T` | `PenguList` | `typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;` |
| `map of K to V` | `PenguMap` | `typedef struct { PenguMapEntry *entries; int len; int cap; size_t key_size; size_t val_size; } PenguMap;` |
| `maybe T` | `PenguMaybe` | `typedef struct { bool is_present; void *value; } PenguMaybe;` |
| `result of T to E` | `PenguResult` | `typedef struct { bool is_ok; void *ok_val; void *err_val; } PenguResult;` |
| `range` (`a to b`) | `PenguRange` | `typedef struct { int64_t start; int64_t end; } PenguRange;` |
| Call Frame | `PenguFrame` | `typedef struct { const char *fn_name; const char *file; int line; } PenguFrame;` |

#### Container Semantics & Memory:
- **`PenguString`:** Represents an immutable string view. String literals in runtime expressions reference `.rodata` and are non-owning (`is_owned == 0`), while dynamic strings created from format `{expr}` or conversions are heap-allocated (`is_owned == 1`). `pengu_string_from_cstr` creates a non-owning view over a C string. Nothing is released automatically: call `banish` (or `defer banish`) on a string you allocated when you are done with it (§13).
- **`PenguSlice`:** Represents a non-owning window over contiguous elements. Created via slicing (`nums at 1 to 3`) or through `std.ffi.slice_from_ptr`. Never owns heap memory; do not `banish` a slice.
- **`PenguList`:** Growable dynamic vector. Manages an internal heap array of size `cap * elem_size`, expanding with 2x amortized growth upon `push`/`append`.
- **`PenguMap`:** Hash table using open addressing and linear probing. Entries are stored in `PenguMapEntry { void *key; void *val; bool occupied; }`. Keys and values are copied into entry cells with `memcpy`; the map does not clone the payloads they reference. Iteration order is **hash order**, not insertion order.
- **`PenguMaybe`:** Value container for optional values. If `is_present` is `true`, `value` points to a heap copy allocated via `pengu_sigil_alloc(sizeof(T))`. If `is_present` is `false`, `value` is `NULL`.
- **`PenguResult`:** Represents either a success (`is_ok = true`, payload at `ok_val`) or failure (`is_ok = false`, payload at `err_val`).
- **`PenguFrame`:** Circular ring buffer of 64 frames. Tracks active function calls (`pengu_frame_push` / `pengu_frame_pop`) to emit human-readable source backtraces on fatal crashes.

### 4.3 Composite & user types

- `rune Name:` — C `struct` (records), see [§9.1](#91-rune-structs).
- `echo Name:` — C `union` (tagged union *without* runtime tag), [§9.2](#92-echo-unions).
- `omen Name:` — C `enum` (simple/string-valued) or tagged `struct` (algebraic sum type), [§9.3](#93-omen-enums--algebraic-data-types).
- `seal Name as T` — strong nominal newtype requiring explicit casts, [§9.4](#94-seal--alias--opaque).
- `alias Name as T` — transparent structural type alias, [§9.4](#94-seal--alias--opaque).
- `opaque` — C opaque pointer handle (`void*`-ish; usable via `ref to`), [§9.4](#94-seal--alias--opaque).
- `ref to T`, `array of T with size N`, `array of array of T with size M with size N` (C `T[M][N]`), `list of T`, `slice of T`, `map of K to V`, `maybe T`, `result of T to E`, `fn`/weave-pointer types.
- `frozen T` — read-only qualification (C `const T`) usable on any type as a **type modifier**, [§9.5](#95-frozen--read-only-qualification).

#### Type Compatibility & Conversion Rules:

| Type Family | Target Type | Assignable? | Semantic Rule |
|-------------|-------------|-------------|---------------|
| `AliasType` | Any `U` | Transparent | `alias A as B` inherits all compatibility rules of `B`. |
| `SealType` | Base `T` | ❌ Requires `to` | Strictly nominal. A `seal S as int` cannot be implicitly passed to `int` without `(val to int)`. |
| `FrozenType` | `T` (mutable) | ❌ Directional | `mutable -> frozen` is valid; `frozen -> mutable` is rejected by `_drops_frozen()`. |
| `RefType` | `ref to void` | ✅ Wildcard | Pointer to any object type implicitly casts to `ref to void` or `ref to frozen void`. |
| `RefType` | `ref to T` | Strict pointee | Pointee types must match exactly (`_same_pointee`), with the single exception of `char` ↔ `byte`. |
| `ArrayType` | `ref to T` | ✅ Decay | Fixed array decays to pointer to its first element. |
| `FnType` | `ref to weave` | ✅ Decay | Function declarations decay seamlessly to function pointer references. |
| `CVarArgsType` | Variadic | Special | Only allowed in `declare ...` signatures; extra call arguments pass through verbatim without conversion. |

**`to` never parses text.** There is no `string -> number` cast: `s to int` is
`E0005`, because the backend would have to emit a C cast from a string object.
Use `spark.parse_int` / `spark.parse_float` for numbers, and `ord s` for the
byte of a one-character string. Numeric and character casts are unaffected:
`(c to int)`, `(n to char)`, `(b to char)` and `(c to byte)` all work.

---

## 5. Variables, constants & scope

### 5.0 Safety guarantees and their opt-outs

Three failure modes have a *defined* behaviour by default; each has exactly one
explicit way to opt out.

| Failure | Default behaviour | Opt-out |
|---|---|---|
| Out-of-bounds `at` access | `[PENGU] Index out of bounds` panic with a frame stack (in every profile) | an `unsafe:` block, or `pengu build --release-unsafe` |
| Signed integer overflow | debug: trap (SIGABRT); release: two's-complement wrapping | `--release-unsafe` (restores C's undefined behaviour) |
| Out of memory | `[PENGU] out of memory` + `abort()` | `-DPENGU_OOM_ABORT=0` when embedding the runtime |

**Bounds checks are not a debug extra.** They are emitted in every profile, so
`--profile release` cannot be used to trade memory safety for speed. Use
`unsafe:` where a hot loop has already proven the index in range:

```pengu
weave sum with xs as array of int, n as int into int:
    var acc as int is 0
    unsafe:                     # emits [W0007]; disables checks for this block
        for i from 0 to n:
            set acc is acc + (xs at i)
    return acc
```

`unsafe:` is a statement (it can wrap several statements and nest), it is only
allowed inside a function body, and it always warns `[W0007]` so the opt-out is
visible in code review.

**Integer overflow.** C leaves signed overflow undefined, which lets optimizers
rewrite arithmetic. PenguScript pins the behaviour: debug builds compile with
`-ftrapv` (abort on overflow), release builds with `-fwrapv` (wrapping modulo
2^N). Only `--release-unsafe` drops both, and that is a deliberate request to
accept undefined behaviour.

**Division by zero.** `x / 0` and `x % 0` are a runtime fault: on POSIX the
process receives `SIGFPE` and terminates; PenguScript does not silently produce a
value. The compiler does not insert a divisor check (it would cost a branch on
every division), so guard divisors when they can legitimately be zero:

```pengu-fragment
if d == 0:
    return 0
return n / d
```

**Out of memory.** An allocation failure prints a diagnostic and aborts rather
than returning NULL, because continuing with a NULL allocation corrupts memory
and crashes far from the cause. Embedders that install their own allocator can
set `-DPENGU_OOM_ABORT=0` to receive NULL instead.

### 5.1 Declarations

PenguScript supports eight declaration layouts for variables, constants, and destructured bindings:

```pengu-fragment
# 1. Explicitly typed variable / binding with initializer
var count as int is 0
let name as string is "Ada"

# 2. Inferred variable / binding
var total is 100                          # inferred as int
let greeting is "Hello"                   # inferred as string

# 3. Zero-initialized variable with explicit type constructor
var buffer as array of byte with size 64 is array of byte with size 64

# 4. Destructuring binding (inferred container type)
let (x, y) is point_value

# 5. Destructuring with element-wise type annotations
var (id, label) as (int, string) is user_record

# 6. Destructuring with composite type annotation
let (r, g, b, a) as Color is current_color

# 7. Top-level compile-time constant
const MAX_USERS as int is 1024
const PI is 3.14159                       # type inferred as float

# 8. Function-static variable (preserved across invocations)
static var call_count as int is 0
```

- **Top-Level Constants (`const`):** Must be declared at top-level scope (`E0001` if placed inside a function). Evaluated and constant-folded at compile time.
  - **C Codegen per Type:**
    - `RangeConst` (`a to b`): Emits `static const PenguRange c_name = { .start = a, .end = b };`.
    - `ref to char` (C-string literal): Emits `#define c_name "..."`.
    - `string`: Emits `#define c_name pengu_string_from_cstr("...")`.
    - `bool`: Emits `#define c_name true` or `false`.
    - Numeric scalars: Emits `#define c_name <folded_val>`.
    - Fixed arrays (`array of T with size N`): Emits `static const T c_name[N] = { ... };` (and nested dimensions `[M][N]` for multi-dimensional arrays).
    - Other statically initializable types: Emits `static const T c_name = <expr>;`.
  - **Validation & Prohibitions (`_check_const_decl`):**
    - **Reserved Identifier `main` (`E0040`):** Cannot be named `main` (reserved for entrypoint and comptime `when`).
    - **C Identifier Conflicts (`E0035`):** Cannot shadow C reserved words or standard type names (`C_RESERVED_TYPE_NAMES`, `C_RESERVED_WORDS`).
    - **No Heap Collections (`E0005`):** `list of T` and `map of K to V` are rejected as constants because they require dynamic heap allocation. Use fixed arrays (`array of T`) instead.
    - **Statically Initializable Arrays (`E0005`):** Constant array elements must be statically initializable (numeric, bool, char, `ref to char`, or static runes/omens).
    - **Known Dimensions (`E0015`):** Array constants cannot have unknown or omitted dimensions (`UnknownArrayDimensionError`).
    - **Compile-Time Expressions (`E0005`):** Initializers must be strictly compile-time constant expressions.
    - **Explicit Null Typing (`E0014`):** Initializing a constant with `null` requires an explicit type annotation (e.g. `const PTR as ref to int is null`; untyped `const PTR is null` raises `E0014`).
- **Local Scoping (`var`/`let`):** Forbidden at top-level scope (`E0002`) to guarantee safety against shared mutable global state. `var` bindings are mutable; `let` bindings are immutable.
- **Static Function Locals (`static var`):** Declared inside a weave to maintain persistent function-local state across repeated invocations (§14.5). Emitted as C `static` variables with one-time initialization guards.

#### Destructuring Rules & Targets (`E0017`):

Destructuring unpacks composite structures into multiple independent local bindings in a single statement.
- **`rune` Structs:** Unpacks fields in the exact order declared in the `rune` definition.
- **Fixed Arrays (`array of T with size N`):** Binds elements from index `0` up to `N - 1`.
- **Slices (`slice of T`):** Binds elements through data pointer indexing `data[i]`.
- **Lists (`list of T`):** Binds elements sequentially via `pengu_list_at(&lst, i)`.

> [!WARNING]
> Destructuring is supported exclusively on runes, fixed arrays, slices, and lists. Attempting to destructure any other type (scalars, pointers, maps) or providing a binding count that mismatches the structure raises `E0017: DestructuringTypeError`.

#### Assignment & `set` Targets

`set` reassigns a mutable target. The left-hand side of `set` can be:
1. A plain variable name: `set x is 42`
2. A rune field: `set player.hp is 100`
3. A pointer arrow field: `set self->hp is 80`
4. A builder dot field: `set .x is 10` (inside `with:` builders)
5. An indexed container: `set items at (i + 1) is new_item`
6. A dereferenced pointer: `set essence of ptr is 99`

Attempting to assign to an immutable `let` binding, a `const`, or a `frozen` value/pointee raises `E0006: MutabilityError`.

##### Bounds are enforced on `set`

When the target's type is a **bare type parameter**, the assigned value must
satisfy every bound declared for that parameter (the same rule the call site
applies to arguments):

```pengu-fragment
weave store shard T where T: Num with x as ref to T into void:
    set essence of x is "hello"     # E0005: 'string' does not satisfy 'Num'
    set essence of x is 42          # OK: 'int' implements 'Num'

weave loose shard T with x as ref to T into void:
    set essence of x is "anything"  # OK: an unbounded T is a wildcard
```

The check applies equally to element targets (`set xs at 0 is v` with
`xs as ref to list of T`) and accepts `any`, `null` and another type parameter
(those are resolved later). This closes the asymmetry where
`TypeParam.is_compatible(concrete)` honoured the bounds but
`concrete.is_compatible(TypeParam)` accepted anything.

#### Compound assignment

`set` also accepts the compound operators `+= -= *= /= %= &= |= ^= <<= >>=`:

```pengu-fragment
set counter += 1
set total -= fee
set acc *= factor
set acc /= n
set mask <<= 2
set flags |= 0x08
set text is "{text} suffix"  # strings use interpolation, never '+='
set essence of ptr += 5      # dereference assignment
```

| Operator | Allowed types | Notes |
|---|---|---|
| `+=` | numeric | `E0005` on `string`: compose with `"{expr}"` interpolation |
| `-=` `*=` `/=` `%=` | numeric | `%` is integer-only, as in `%` |
| `&=` `\|=` `^=` `<<=` `>>=` | integers | bitwise/shift; `E0005` on non-integers |

The left-hand side follows normal `set` rules: it must be mutable (`E0006` otherwise). Type errors are reported as `E0005`.

### 5.2 Scope

Scopes are delimited by indentation: weave bodies, `if`/`while`/`for` branches, `with:` blocks, `or:` blocks, and `do:` expressions. Lookup is lexical; a name declared in an inner scope shadows outer identifiers. `banish`, `defer`, and `errdefer` are only permitted inside function bodies (`E0008`).

### 5.3 Visibility recap

Symbols are public across modules by default. Any top-level symbol or rune field starting with a leading underscore (`_`) is strictly private (`E0043`); a private rune field is private to the module that declares the rune (§9.1). There is no `pub` keyword; leading underscores provide the sole encapsulation mechanism.

---

## 6. Operators & expressions

### 6.1 Precedence (loosest → tightest)

1. `or else`, `or return`, `or:` blocks, `try`
2. `or` (boolean, short-circuit)
3. `and` (boolean, short-circuit)
4. `judge … when … -> … else -> …`, `if … then … else …` (expressions), `when … then … else …`
5. comparisons `== != <= >= < >`, word tests `is present`, `is not present`, `is true`, `is false`, membership `in`, `not in`
6. `|` `&` `^` bitwise operators
7. shifts `<< >>`
8. additive `+ -`
9. multiplicative `* / %`
10. unary `~ not -`, `sigil of`, `essence of`, `transmute … to`, `size of`, `banish`, `some`, `ord`, `chr`, `bytes of`
11. postfix `at`, slicing `at a to b`, `length`, `.field`, `->field`, cast `to`
12. atoms: literals, `calling`, `with` init/struct-init, containers, `defined(…)`, `lambda … into …`

Everything is left-associative. `or` binds looser than `and`, so `a or b and c` evaluates as `a or (b and c)`. `and`/`or` are **boolean** operators (short-circuiting to `&&`/`||` in C); `&`/`|`/`^` are **integer bitwise** operators.

> [!NOTE]
> **`at` Postfix Precedence:** Because `at` binds tighter than additive arithmetic (`+` / `-`), indexing expressions involving computed offsets require parentheses:
> ```pengu
> xs at i + 1          # Parsed as (xs at i) + 1 — arithmetic on the retrieved element
> xs at (i + 1)        # The element at computed index i + 1
> set xs at (n - 1) is 77   # Assignment target
> ```
> Omitting parentheses (`xs at i + 1` when index calculation was intended) is rejected as a syntax error (`E0000`).

> [!IMPORTANT]
> **Comma Separation & Ambiguity Rules (`E0005`):**
> List items in function calls, parameters, array literals, and struct literals must be separated by commas (`,`). When `and` appears directly after an argument or struct field (`calling find with 1 and true`), the compiler rejects it with `E0005: Ambiguous 'and' after ...` to avoid confusion with legacy syntax. Parenthesize boolean expressions explicitly: `calling find with (1 and true)`.

### 6.2 Arithmetic & bitwise

```pengu-fragment
let z as int is (a + b) * 2 % 7
let f as float is 1.5
let bits as int is (x << 2) | (y & 0x0F)
let neg as bool is not ready
let flip as int is ~mask
```

- **Strings (`+` is a compile error, `==` is fine):** `+` is **numeric-only**. String composition has exactly one spelling: `"{expr}"` interpolation inside a string literal (§15.2). `"a" + b` raises `E0005`; there is no implicit `to string` promotion and no hidden temporary. Equality `a == b` emits `pengu_string_equal(a, b)` (passed by value, non-allocating content equality).
- **Logical Short-Circuit (`and` / `or`):** Operands must be strictly `bool` (`E0005` otherwise). `or` evaluates its right operand only if the left is `false`; `and` evaluates its right operand only if the left is `true`.
  > **Note on short-circuit vs fallback semantics:** `or` and `and` are exclusively boolean logical operators (`bool and bool -> bool`), not value-coalescing or fallback operators. To unwrap an optional or result with a fallback value, use `or else` (e.g. `val or else default`, §12) or an `or:` block (§12). Expressions such as array/list indexing (`at`) under debug mode perform eager bounds-checking that aborts if out of bounds; they should not be guarded using logical operators without an explicit `if` check or safe fallback method.


### 6.3 Comparison, membership & word tests

```pengu-fragment
if x > 0: ...
if m is present: ...          # m must be 'maybe T'; anything else is E0005
unless m is present: ...
if b is true: ...             # b must be 'bool'
if ch in "aeiou": ...         # uses strchr for char, strstr for string
if key in my_map: ...         # uses pengu_map_get
if p == null: ...             # valid for any pointer/opaque type
```

- **Membership (`in` / `not in`):**
  - **Strings:** If searching for a `char`, emits `strchr`. If searching for a `string`, emits `strstr`.
  - **Maps:** Emits `pengu_map_get(&map, key)` to test key membership.
  - **Ranges:** Checks half-open range `a <= x and x < b`.
- **String Comparisons:** Equality (`==`, `!=`) is supported via `pengu_string_equal`. Relational ordering (`<`, `<=`, `>`, `>=`) on `string` is **not supported** (`E0005`) because `PenguString` is a struct; use character comparisons or `std.scrolls.compare`.
- **Word Tests (`is present`, `is true`):**
  - `is present` and `is not present` are valid **only on `maybe T`**. Applying them to `result of T to E` is `E0005` (use `.is_ok` on results).
  - `is true` and `is false` require a `bool` operand (`E0005` otherwise).
  - In call argument positions, test keywords must be parenthesized (`calling print_bool with (m is present)`), because `_reject_test_argument` forbids unparenthesized tests to prevent syntactic ambiguity.
- **`null` Comparisons:** Comparing `p == null` or `p != null` is valid for all pointer types (`ref to T`, `ref to void`, `opaque`). Comparing `null` against non-pointer types (such as `int == null`) raises `E0005`.

### 6.4 Address, dereference & size

```pengu-fragment
var p as ref to int is sigil of x     # &x
var v as int is essence of p          # *p
set essence of p is 42                # *p = 42 (LHS of assignment)
let n as usize is size of MyRune      # sizeof(MyRune)
let t as string is type of p          # "ref to int" (static type; p is not evaluated)
let raw_ptr as ref to void is transmute p to ref to void   # unsafe bit-cast
```

- **`sigil of expr` (`&`):** Takes the address of an lvalue. Cannot be applied to literals, expressions, `const`, or `frozen` variables (`E0008: InvalidMemoryOpError`).
- **`essence of expr` (`*`):** Dereferences a pointer. The operand must be a `ref to T` or `Any`. It can be used both as an rvalue and as the left-hand side target of a `set` assignment (`set essence of ptr is val`).
- **`size of TYPE`:** Evaluates the compile-time byte size of any type (`sizeof(T)` in C) and returns `usize`.
- **`type of expr`:** Reports the **static** type of `expr` as a `string`, using the canonical PenguScript spelling. It is a compile-time operator: the operand is type-checked but **never evaluated**, so side effects inside it do not run. The result is a borrowed string literal (`pengu_string_from_cstr("int")`, `is_owned == 0`): it costs nothing at runtime, and `banish` on it only clears the handle, like on any borrowed string. `type` and `of` are **soft keywords** — `type of` is one lexer token only when the two words are adjacent on the same line, so `var type as int is 5` (and `var size as int is 5`, which used to collide with `size of`; that is fixed) still work as ordinary identifiers.
- **`transmute expr to TYPE`:** Unsafe bit-level reinterpretation cast. Always triggers compiler warning `[W0001] transmute is unsafe`. If the source and destination types have different estimated sizes, `W0001` includes a size mismatch notification. Safe conversions must use `(expr to TYPE)`.

Canonical names reported by `type of` (every spelling of the same C type gives the same name — `int32`, `int32_t`, `i32` and `int` all give `"int"`):

| C type (any accepted spelling) | `type of` reports |
|---|---|
| `int32_t` (`int`, `i32`, `int32`, …) | `"int"` |
| `int64_t` (`i64`, `int64`, `long`, …) | `"i64"` |
| `uint8_t` (`byte`, `u8`, `uint8`, …) | `"byte"` |
| `size_t` (`usize`, …) | `"size_t"` |
| `intptr_t` (`isize`) | `"isize"` |
| `double` (`f64`) | `"f64"` |
| `float` (`f32`) | `"float"` |
| `char` / `bool` / `void` | `"char"` / `"bool"` / `"void"` |
| `opaque` (C `void*`) | `"opaque"` |
| `PenguString` (`string`) | `"string"` |

Composites are recursive and spelled in PenguScript: `"ref to T"`, `"ref to frozen T"`, `"frozen T"`, `"list of T"`, `"slice of T"`, `"map of K to V"`, `"maybe T"`, `"result of T to E"`, `"array of T with size N"`, `"({T}, {U})"` for tuples, and `"weave with {T} into {U}"` for function types. A nominal type reports its **local** base name, never the module qualifier (`rune Point` → `"Point"`, likewise `omen`, `echo`, `seal` and `alias`); a monomorphized generic reports `"Box of int"`. Inside generic code the operator resolves **per instantiation**: in `weave describe shard T with x as T into string:` it yields `"int"` for `calling describe with 42` and `"string"` for `calling describe with "hi"`. Use it for diagnostics, generic self-description and test assertions — **not** as a runtime type check to branch on behaviour, because it is a compile-time constant (style guide §14.28).

### 6.5 Character & byte primitives

```pengu-fragment
let code as int is ord "A"            # 65
let empty_code as int is ord ""       # 0
let ch as string is chr 66            # "B" (single-character string)
let raw_str as ref to frozen byte is bytes of my_string   # read-only view
let raw_arr as ref to byte is bytes of byte_array         # writable view
```

- **`ord expr`:** Converts a single character string or char literal to its ASCII integer value. Multi-character literals raise `E0005`. Empty string `ord ""` evaluates to `0`.
- **`chr expr`:** Converts an integer byte code (0–255) into a single-character `PenguString`.
- **`bytes of expr`:** Borrows a byte pointer:
  - If applied to `string`: returns `ref to frozen byte` (read-only view into the string's character buffer).
  - If applied to `array of byte with size N`: returns `ref to byte` (writable pointer).
  - Applying `bytes of` to other types raises `E0005`.

### 6.6 `maybe` constructors & `null` context

```pengu-fragment
var m as maybe int is some 42         # boxes 42 into a PenguMaybe heap cell
var n as maybe int is maybe none      # empty optional
var p as ref to int is null           # null pointer
```

- **`some expr` Boxing:** Evaluates `expr` and copies it into a heap-allocated cell via `pengu_sigil_alloc(sizeof(T))`:
  ```c
  /* Generated C for: some 42 */
  int32_t _some_1 = 42;
  PenguMaybe _maybe_2;
  _maybe_2.is_present = true;
  _maybe_2.value = pengu_sigil_alloc(sizeof(_some_1));
  if (!_maybe_2.value) _maybe_2.is_present = false;
  else memcpy(_maybe_2.value, &(_some_1), sizeof(_some_1));
  ```
- **`maybe none` Lowering:** `maybe none` lowers to the runtime call `pengu_maybe_none()`, returning an empty `PenguMaybe` with `.is_present = false` and `.value = NULL`.
- **Context Requirement for `maybe none` & `null` (`E0014`):**
  Neither `maybe none` nor `null` carry an inherent type. They require an expected type context (such as an explicit variable type annotation `var m as maybe int is maybe none` or `var p as ref to int is null`). Initializing an unannotated variable with `maybe none` or `null` raises `E0014: TypeMismatchError`.
- **`error` Variable in `or:`:** Inside an `or:` block, failure details are bound to the scoped variable `error` (type `string` for `maybe T`, or error type `E` for `result of T to E`). Accessing `error` outside an `or:` block is an error (`E0015`).
- **`null` and generic parameters (known limitation):** `null` is accepted where a *bare* type parameter is expected, whatever its bounds, because a `T` without bounds can be instantiated with a pointer. Tightening this (`T: Num` rejecting `null`) is deliberately left permissive for backwards compatibility; casts are checked normally.

---

## 7. Control flow

### 7.1 `if` / `unless` (statements) and `if`-expressions

```pengu-fragment
if score >= 100:
    calling print with "winner"
else:
    calling print with "keep going"

unless muted:
    calling play_sound with "beep"

let label as string is if x > 10 then "big" else "small"
```

`unless cond:` is equivalent to `if not cond:`. Conditions must evaluate to `bool` (`E0005` otherwise). Branches with compile-time constant conditions are folded and the unreachable branch is eliminated (warning `[W0004]` for unreachable code).

#### `if` bindings: `if v as T is <maybe>:`

An `if` condition may safely bind the value held by a `maybe T` without an explicit unwrap:

```pengu-fragment
weave describe with user as maybe User into string:
    if u as User is user:               # u is User inside the branch
        return u.name
    else:
        return "anonymous"
```

- The operand must be `maybe T` (`E0005` otherwise).
- `T` must match the element type of the maybe container.
- It also works in value position: `let label is if u as User is user: u.name else: "anonymous"`.
- Lowered to a scoped C block that tests `pengu_maybe_is_present(&tmp)` once and extracts the value; the bound identifier does not leak into the `else` branch or outer scope.

#### Single-line statements (`simple_stmt`)

A control flow block or branch may contain a single statement on the same line following the colon (`:`):

```pengu-fragment
if x == 1: return 1
unless x == 0: calling print with "non-zero"
while i < n: set i is i + 1
for j from 0 to 3: calling tick with j
```

The allowed statement forms on the same line as a colon (`simple_stmt`) are: `continue`, `break`, `return [expr]`, `set target is expr`, `set target OP expr`, and any general expression (such as `calling fn(...)`). Declarations, blocks, `defer`, `errdefer`, and `banish` cannot be written on the same line as a colon.

### 7.2 `while`

```pengu-fragment
var i as int is 0
while i < 10:
    calling tick with i
    set i is i + 1

outer: while i < 10:          # optional label: NAME ':' before the loop (§7.5)
    calling tick with i
    set i is i + 1
```

- **Loop labels:** A `while` may carry an optional `NAME ":"` immediately before the keyword, on the same line. `break NAME` / `continue NAME` target that loop instead of the innermost one; a label is function-local and must be unique within the function (`E0069`). See §7.5.

### 7.3 `for`

```pengu-fragment
for i from 0 to 10:            # integer range [0, 10), end-exclusive
    calling print with (i to string)

for item in items:             # array / list / slice / string / map iteration
    calling handle with item

for i, item in indexed:        # indexed form (i is iteration counter)
for _, v in values:            # discard index
for j from 5 to 0 step -1:     # negative step

rows: for i from 0 to 3:       # label any of the three loop forms (§7.5)
    for j from 0 to 3:
        continue rows
```

- **Loop Labels:** `NAME ":"` may precede `for … from … to … [step …]` or `for … in …`, on the same line. `break NAME` / `continue NAME` target it; bare `break` / `continue` still target the innermost loop. A label is **function-local** and not a symbol: it is not in `symbols.functions`, cannot be imported, and is invisible outside its weave. Two loops with the same label in one function are `E0069`, even when they are siblings rather than nested. See §7.5.

- **Loop Bindings Validation (`E0037`):** In the indexed form `for i, v in col`, the index identifier `i` and element identifier `v` must be distinct. Using the same identifier name for both raises `E0037`. The wildcard `_` can be used to discard either binding.
- **String Iteration:** Iterating over a string (`for ch in "abc":`) yields each character as a single-character `PenguString` via `pengu_string_char_at`.
- **Map Iteration:** Iterating over a map (`for k in my_map` or `for i, k in my_map`) iterates over keys. The codegen scans the internal hash table array (`entries[slot]`), checking `entries[slot].occupied`. **Iteration order is hash order**, not insertion order. In the indexed form, `i` increments only when an occupied slot is visited.

#### Comprehensions (`for_comp`)

List comprehensions produce a new `list of T` by evaluating an expression across an iterable:

```pengu-fragment
let squares is for x in nums then x * x
let evens  is for x in nums when x % 2 == 0 then x
```

- **Syntax:** `for item in col [when condition] then expr`. Inline comprehensions bind a single element variable `item` (the indexed `i, item` form is not supported in inline comprehensions; use a value-position `for` loop block for indexed collection). Supported collection types include fixed arrays (`array of T`), slices (`slice of T`), dynamic lists (`list of T`), ranges (`a to b`), and maps (`map of K to V`, which iterates over active keys in hash order).
- **Codegen Lowering:** Evaluates into a GNU statement-expression allocating a `PenguList`:
  ```c
  (__extension__({
    PenguList _comp_list = pengu_list_new(sizeof(T));
    /* loop over col */
    if (condition) {
      T _val = expr;
      pengu_list_push(&_comp_list, &_val);
    }
    _comp_list;
  }))
  ```

### 7.4 `judge` — pattern matching

```pengu-fragment
let state_desc is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
    else -> "unknown"
```

- **Supported Subjects:** `omen` variants, `bool`, `int`, `string`, and `char`.
- **Pattern Forms:**
  - Bare variant name: `when Ready ->`
  - Dotted variant name: `when Phase.Ready ->`
  - Full C name: `when Phase_Ready ->`
  - Literals: `when 42 ->`, `when "admin" ->`, `when 'X' ->`
  - Alternatives: `when Ready | Loading ->` — either one matches, and each
    alternative counts as covered (see below).
  - Fallback default: `else -> <expr>`, or an indented body (`else ->` followed
    by a block), which lets a default declare `let`s exactly like a `when` body.
- **Exhaustiveness Rules (`E0044`):**
  - For `omen` and `bool` subjects, all possible variants/values must be handled unless a default `else ->` clause is provided. Missing branches raise `E0044: NonExhaustiveJudgeError`.
  - For `int`, `string`, and `char`, exhaustiveness is not enforced. If no `else ->` is present and no pattern matches, the expression evaluates to its default zero/empty value (`0`, `""`, `'\0'`).
- **Pattern Payloads (`with <fields>`):** Extract variant fields directly into local bindings in the clause body:
  ```pengu
  judge status:
      when Status.Ok with value -> value + 1
      when Status.Err with code -> code
  ```
- **Guards (`if <cond>` / `when <cond>`):** Filter pattern branches using boolean expressions evaluated with bound payload variables in scope:
  ```pengu
  judge number:
      when Number.Val with n if n > 0 -> "positive"
      when Number.Val with n if n < 0 -> "negative"
      when Number.Val with n -> "zero"
  ```
  Guarded patterns do not count toward exhaustiveness; an unguarded pattern or `else ->` is required.
- **Or-patterns (`when A | B ->`):** One clause matches either alternative, and every alternative counts as covered, so `when A | B -> 1` plus `when C -> 2` is exhaustive over `A`, `B`, `C`. A `with` list may follow the alternatives, but a name it binds must be a field of **every** alternative (`E0005` otherwise). With an `int` subject the alternatives share one clause body and become adjacent C labels (`case 1: case 2:`); in the `over` form each alternative gets its own `case`.
- **Narrowed `with` patterns are `over`-only:** `field as Literal` (a nested variant), `field as some` / `none` (a `maybe`), `field as ok` / `err` (a `result`) and `field as (a, b)` (a tuple) are described in §7.4.1 and apply to the `judge <rune> over <field>` form. The `with` list of this form binds the variant's payload fields as they are.
- **Codegen:** Emits a C `switch` statement when all pattern cases are compile-time integer constants without guards or payloads; generates structured `if` branches with payload extraction and guard checks when payloads or guards are present, or falls back to an `if-else` ternary chain for string or variable patterns.
- **Second form:** A `rune` whose variant is carried by a field (`kind`, `op_kind`, …) is matched with the `over` form described in §7.4.1 instead.

### 7.4.1 `judge` over `rune`

`judge` matches an `omen` *directly*. The other common shape — the C tagged
union, where a `rune` carries every variant's fields and an `omen` field says
which of them is live — has no clean spelling with the form above: the user
writes `if`/`else if` chains that compare the tag, get no exhaustiveness check
and cannot bind the rune's fields.

`judge <subject> over <discriminant>:` closes that gap. The subject is a
`rune`, `over` names one of its fields, and that field's type is the `omen`
whose variants select the branch. `over` is a **soft keyword**: it only means
this inside a `judge` header, so `var over as int is 5` still compiles.

```pengu-fragment
judge <subject> over <discriminant>:
    when <Variant> with <field1>, <field2> [if <guard>] -> <expr>
    when <Variant> [if <guard>] -> <expr>
    else -> <expr>
```

The canonical use is a recursive expression tree:

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

**Rules.**

- **Subject.** A `rune` value, `ref to` a rune, `frozen` rune, or an `alias` /
  nominal `seal` over one. Anything else is `E0005`; use the plain
  `judge <expr>:` form for `omen`/`bool`/`int`/`string`/`char`. The subject may
  be a name, `w.inner`, `p->inner`, `self->node`, or any expression; a
  non-lvalue subject is evaluated **once** into a `_judge_subj_N` temporary, so
  a call in the subject cannot run twice.
- **Discriminant.** The name after `over` must be a field of the rune (`E0013`
  otherwise) whose type is an `omen` — possibly behind a `seal`, which is
  unwrapped because the compiler knows the representation (`E0005` otherwise).
  Like every field, a leading-underscore discriminant is private to the module
  that declares the rune (`E0043`, §9.1).
- **Bindings are by field name, not by position.** `with a, b` binds those two
  fields of the *rune*; the order is free and the names are ordinary
  identifiers in the clause. `with left, op` and `with op, left` are the same
  clause. A name that is not a rune field is `E0013`. Because the rune is a
  single struct, every field exists in every clause: `when Literal with left`
  compiles, even though `left` is only meaningful for `Binary`.
- **Narrowing a field (`field as <pattern>`).** A `with` entry may narrow the
  field it binds; the field is still bound, so the clause body and its guard
  can read it. The pattern is a *test* on top of the variant match:
  - **Nested variant** — `when Binary with left as Literal -> …`: `left` must be
    a rune carrying a field of the **same** discriminant `omen` as the enclosing
    `judge`, and the clause additionally requires `e.left->kind ==
    ExprKind_Literal`. A non-rune field or a different `omen` is `E0005`.
  - **`maybe` state** — `opt as some` / `opt as none` on a `maybe T` field,
    emitted as `is_present` / `!(…is_present)`.
  - **`result` state** — `res as ok` / `res as err` on a `result of T to E`
    field, emitted as `is_ok` / `!(…is_ok)`.
  - **Tuple destructuring** — `pair as (n, flag)` on a `(int, bool)` field binds
    one immutable name per element (`.v0`, `.v1`); the arity must match
    (`E0005`) and the field itself is **not** bound. A tuple always has that
    shape, so this form is a binding, not a test.

  A narrowed clause is a **test**, exactly like a guard: it does **not** complete
  coverage of its variant. Without a plain `when Binary -> …` (or an `else`) the
  uncovered variant is `E0044`.
- **Bindings are immutable `let`s.** `set field is …` inside a clause is
  `E0006`. They are scoped to their clause and never leak between clauses.
- **Guards.** `when Binary with op if op == Op.Add ->` is allowed; guards see
  the bindings and the enclosing scope, and may call functions with effects.
  The original subject stays accessible. A guard that reads a field through `->`
  must parenthesise the access — `if (right->int_value) > 0` — because `->` is
  also the clause separator; a bare `right->int_value` in a guard is a syntax
  error.
- **Exhaustiveness.** If the `omen` has variants not covered by an *unguarded*
  clause and there is no `else ->`, the clause is `E0044:
  NonExhaustiveJudgeError`, with the missing variants named in the message. A
  guarded clause never counts as coverage, exactly like §7.4.
- **Clause bodies.** A clause body is an expression on the same line, or an
  indented statement block whose last statement is its value — the `do:` shape.
  The block form is what lets a clause declare `let`s and nest another `judge`.
  `else ->` takes the same two shapes, so the default branch can also declare
  locals:

```pengu-fragment
judge shape over kind:
    when Square with width if width > 0 -> width * width
    when Square -> 0
    when Rect with height, width -> width * height
    else ->
        var fallback as int is 0 - 1
        fallback
```

The narrowing forms on one recursive tree — a nested variant, an or-pattern and
a plain clause that completes coverage:

```pengu
omen ExprKind:
    Literal
    Neg
    Binary

rune Expr:
    kind as ExprKind
    int_value as int
    left as ref to Expr
    right as ref to Expr

weave describe with e as ref to Expr into string:
    judge e over kind:
        when Literal -> "literal"
        when Neg with left as Literal -> "neg of a literal"
        when Neg | Binary -> "compound"
```

**Generated C.** The discriminant is switched on directly, each clause gets a
braced `case` that declares its bindings, and no `default:` is emitted when the
clauses are exhaustive (an `else` becomes the `default`). A guarded-only
variant jumps to the shared default block, so nothing is duplicated:

```c
int32_t _judge_res_1 = (0);
switch (e->kind) {
case ExprKind_Literal: {
  int32_t int_value = e->int_value;
  _judge_res_1 = (int_value);
  break;
}
case ExprKind_Binary: {
  int32_t bin_op = e->bin_op;
  Expr* left = e->left;
  ...
  break;
}
default: _judge_over_default_2: { _judge_res_1 = (0); break; }
}
_judge_res_1;
```

`judge over rune` is zero-cost: it lowers to the same `switch` a hand-written
tag check would use, with no allocation, boxing or vtable. A string-valued
`omen` cannot be a C `switch`, so that (rare) discriminant falls back to a
`pengu_string_equal` chain. A narrowed clause adds its test as an `if` inside
the `case`, and the remaining clauses for that same variant run after it in the
same `case`, in source order:

```c
case ExprKind_Neg: {
  Expr* left = e->left;
  if (e->left->kind == ExprKind_Literal) { _judge_res_1 = (…); break; }
  _judge_res_1 = (…);   /* the `when Neg -> …` that completes coverage */
  break;
}
```

**Differences from matching an `omen` directly.**

| | `judge <omen>:` (§7.4) | `judge <rune> over <field>:` (§7.4.1) |
| --- | --- | --- |
| Subject | the `omen` itself | a `rune` and one of its `omen` fields |
| `with` list | positional payload fields **of the variant** | named fields **of the rune**, any order |
| Field available in a clause | only that variant's payload | any rune field |
| Shared fields (`line`, `col`) | repeated per variant | declared once |
| C layout | tag + union sized per variant | one flat struct, stable layout |
| Exhaustiveness | required | required |

**Interaction with `seal`, `frozen`, `derive`.**

- `seal X as OmenY`: the discriminant is unwrapped and the seal's variants are
  matched; the seal stays nominal everywhere else.
- `frozen Expr` / `ref to frozen Expr`: allowed, and each binding is emitted as
  a `const` copy so a read-only rune cannot be mutated through a match.
- `derive Par`: a `rune` with a plain-`omen` discriminant may derive `Par`; the
  derived `==` compares the tag. (Algebraic and string-valued omens still need
  an explicit `bind`.)

**Limitations (2.7.0).** Nested variant patterns, or-patterns, `maybe`/`result`
field states and tuple destructuring are supported (above). The remaining gap is
a **deliberate design boundary**, not a pending feature: **array/list patterns**
(`items as [a, b]`) are absent. A list pattern is a hidden length test plus one
bind per element — O(n) work the syntax does not show — and the language already
expresses it without hiding anything, with the length test in the open:

```pengu-fragment
# What `items as [callee, arg]` would hide; spell it out instead:
when Call with items if items.length == 2 ->
    let callee is items at 0
    let arg is items at 1
```

`judge` also has no `maybe`/`result` *subject* form: an optional is matched with
`if v as T is m is present:` (§7.1) or unwrapped with `or:`. There is no
positional binding form — the names are always rune fields — and matching is on
one discriminant field per `judge`; branch on a second tag with a nested
`judge`, as the `eval` example does.

**Diagnostics.** `E0005` (subject is not a rune / discriminant is not an
`omen` / an ill-typed narrowing), `E0013` (unknown discriminant or binding),
`E0043` (private field), `E0044` (non-exhaustive), `E0006` (assignment to a
binding), `E0000` (a pattern form outside the grammar).

### 7.5 `break` / `continue` / `return`

Standard control flow statements. `break` and `continue` are only permitted inside loop blocks (`E0007`). `return` must produce a type matching the enclosing weave's `into` specification (`E0020`); bare `return` is valid only in `void` weaves.

A loop may be **labeled**, which makes `break` / `continue` able to leave more than the innermost loop:

```pengu
import std.spark

weave main into int:
    var lines as list of string is ["a;b", "c}d", "e"]
    outer: for line in lines:
        for ch in line:
            if ch == ";":
                continue outer          # next line: step + condition run
            if ch == "}":
                break outer             # leave the labeled loop
            calling spark.println with "{ch}"
    return 0
```

- **Syntax:** `NAME ":"` immediately before a `while`, a `for … from … to … [step …]`, or a `for … in …`, on the same line. A jump is written `break label` / `continue label`; bare `break` / `continue` are unchanged and target the innermost loop, even inside a labeled one.
- **Semantics:** `continue label` continues the *labeled* loop — its step expression and condition run again, exactly as a `continue` of that loop would. `break label` leaves the labeled loop. The label must name an **enclosing labeled loop**.
- **Errors:** an unknown label is `E0004`; a label that exists but does not enclose the statement is `E0007`; a label used twice in one function is `E0069` (`DuplicateLabelError`), even for two sibling loops. Labels are **function-local** and are not symbols: they are not in `symbols.functions`, cannot be imported, and are invisible outside their weave.
- **Codegen lowering:** C has no labeled `break`, so a labeled jump lowers to `goto _pengu_label_<label>_<continue|break>;`. The `_continue` anchor is emitted as the last line of the labeled loop's body, so the C step and condition still run (exactly `continue` semantics); the `_break` anchor is emitted right after the loop but **before** the loop's own cleanup (for example the `banish` of a materialized iterable), so both the normal exit and a jump out of the loop run that cleanup. The jump itself also releases the temporaries of every loop it leaves *between* itself and its target, innermost first, because C does not unwind scopes. An anchor is emitted only when a jump targets it, so an unused label costs zero lines of C and does not trigger `-Wunused-label`.
- **Pengunic naming:** `snake_case`, descriptive (`outer`, `lines_loop`, `next_row`), never a single letter. Label a loop only when at least two loops are nested and you must leave the outer one from inside it.

### 7.6 Block expressions: `do:`, value-position `if` / `unless`, and loops

Any indented block can evaluate to a value when placed in a value position:

```pengu-fragment
let x is do:                      # evaluates to its last statement's value
    var a is 10
    set a is a + 5
    a * 2                         # x == 30

let status is if score >= 100:    # if in value position
    let msg is "winner"
    msg
else:
    let msg is "keep going"
    msg

let squares as list of int is for i from 0 to 5:
    i * i                         # collects each iteration value into a list
```

- **`do:` Expression:** Executes statements in a fresh lexical scope. The value of `do:` is the value of its final expression statement. Lowered to GCC statement-expression `__extension__(({ <stmts>; <last_expr>; }))`.
- **Value-Position `if` / `unless`:** Every branch must conclude with an expression sharing a common type (`E0005` on mismatch). Lowered to:
  ```c
  __extension__(({
    T _if_1;
    if (cond) { ... _if_1 = then_expr; }
    else { ... _if_1 = else_expr; }
    _if_1;
  }))
  ```
- **Value-Position Loops:** Loops (`while`, `for i from ... to ...`, `for x in col`) placed in value position collect each iteration's trailing value into a newly allocated `list of T`.
- **Valid Tail Statements (`_check_block_value_stmt`):** The final statement of a value block determines the block's resulting value. The compiler recognizes:
  1. `if_stmt` / `unless_stmt`: Recursively checked in value position, enabling nested branching.
  2. `while_stmt` / `for_range_stmt` / `for_in_stmt`: Evaluated as collecting loops, yielding a `list of T`.
  3. `do_expr`: Nested lexical value block.
  4. `with_init_expr`: Trailing builder block, inferring its type from the enclosing value slot.
  5. Any standard expression or call statement.
- **Checker Protocol (`_pengu_value_type`):** The semantic checker attaches `_pengu_value_type` to AST nodes sitting in value slots. The codegen inspects this metadata to select statement-expression emission.

> [!NOTE]
> CHEATSHEET §6.1.4 has the definitive list of what is and is not an expression. Statement-level control operations (like bare `break` without value or declarations) cannot serve as block tail values.

---

## 8. Functions

### 8.1 `weave` — functions

```pengu
weave greet with name as string, times as int is 1 into void:
    for i from 0 to times:
        calling print with "Hi {name}"

weave double with x as int into int:
    return x * 2
```

- **Parameters & Defaults:** Parameters may specify default values (`times as int is 1`). Default expressions must be compile-time constants.
- **Implicit Return:** A function body whose last statement is an expression implicitly returns that value without needing an explicit `return`.
- **Calling Syntax:**
  - Positional arguments: `calling greet with "Ada", 3`
  - Named arguments: `calling greet with name is "Ada", times is 2`
  - Module member: `calling spark.println with "Hello"`
  - Object method: `calling player.move with 5, 3`
- **Parentheses Requirement:** The argument list following `with` is greedy. When a call is nested inside an arithmetic expression or comparison, wrap the call in parentheses: `(calling get_count) > 0`.
- **Call Diagnostics & Error Codes:**
  - `E0004`: Module member not found (`Module 'X' has no exported member 'Y'`), or external C function called without a matching `declare`.
  - `E0018`: `list of T` push argument mismatch (`List of T push expects T, got U`).
  - `E0034: InvalidRitualCallError`: Attempting to call a `ritual` (static) method on an instance object, or calling an instance method on a type name.
  - `E0043: PrivateSymbolAccessError`: Calling a private function (prefixed with `_`) from outside its defining module.
  - `E0045`: `try` used inside a function whose return type is incompatible with the unwrapped failure.

#### Automatic Inlining Heuristic (`inline`)

Functions can be explicitly declared with the `inline` modifier: `inline weave fast_calc ...`. Additionally, the semantic checker (`_check_weave_decl`) automatically marks small functions as `is_inline = True` when:
1. The function body contains 3 or fewer statements (`len(stmt_children) <= 3`), or the total AST node count is 25 or fewer (`node_count <= 25`).
2. The function contains **no loops** (`while`, `for i from ...`, `for item in ...`).
3. The function contains **no static variables** (`static var`).

For all inlined functions, the code generator emits `static inline __attribute__((always_inline))` on both the forward prototype and the C implementation, eliminating function call overhead in performance-critical code.

#### Entry Point Wrapper (`pengu_main`)

The user entry point must be named `main` (`weave main into int:` or `into void:`). The compiler generates the C function `pengu_main`, wrapped by a standard C runtime `main`:

```c
/* Generated C runtime entry point wrapper */
int main(int argc, char** argv) {
    pengu_init(argc, argv);
    int pengu_status = (int)pengu_main();
    fflush(stdout);
    fflush(stderr);
    return pengu_status;
}
```

This automatic wrapper initializes the runtime arguments, exposes them to `std.rites.get_args()`, executes `pengu_main()`, flushes standard I/O buffers, and returns the exit status code.

### 8.2 `declare` — external C functions

```pengu
declare pengu_print with s as string into void
declare strlen_c with s as ref to char into usize
declare my_callback with cb as ref to weave with x as int into void into void
declare printf with fmt as ref to frozen char, ... into int     # C varargs
```

`declare` registers external C function prototypes so that calls translate directly to native C invocations without glue wrappers.

#### C Variadic Functions (`...` vs `many T`)

A trailing `...` in a `declare` parameter list represents raw C variadic arguments (`CVarArgsType`):
- **Fixed Parameters:** Are strictly type-checked according to their declared types.
- **Variadic Arguments:** Extra arguments are passed through **verbatim** to C. No `PenguSlice` packing or runtime boxing occurs; C default argument promotions apply directly.
- **Distinction from `many T`:** `many T` is PenguScript's safe, slice-backed variadic mechanism for `weave` functions. `...` is reserved exclusively for external C `declare` signatures.
- **Modifiers:** `declare` can also be combined with `inline` or `ritual` modifiers.

##### `many T` — slice-backed variadics on `weave`

`with xs as many T` makes a `weave` variadic. At the call site you list the
arguments normally; the compiler packs them into a temporary fixed array and
passes it as a `PenguSlice`, so inside the body `xs` is an ordinary indexable
sequence (`xs at i`, `xs length`):

```pengu
weave count_args with xs as many int into int:
  return (xs length to int)

weave main into int:
  var n as int is calling count_args with 7, 8, 9   # n == 3
  return 0
```

Verified end to end (it compiles, links and runs). Two restrictions are worth
knowing, because each is enforced at a different stage:

| Form | Accepted? | Diagnostic |
|---|---|---|
| `many T` in a `weave` signature | ✅ | — |
| `many T` in a `declare` signature | ❌ | `E0005 'many' parameters are not allowed in 'declare' statements` |
| `...` in a `declare` signature | ✅ | raw C varargs |
| `...` in a `weave` signature | ❌ | syntax error |

**Call-site spread (`f(...xs)`) is not implemented.** Listing the arguments is the
only form; there is no way to expand a runtime container into N arguments. Spread
is ⏸️ deferred (see `ROADMAP_1.1.md`).

### 8.3 Function pointers & callbacks

A function value has type `weave … into …` (`FnType`). In C, function identifiers decay seamlessly to function pointers. Both `weave with … into …` and `ref to weave with … into …` are fully interchangeable:

```pengu-fragment
alias Handler as weave with x as int into void

weave handler with x as int into void:
    return

weave main into void:
    var cb as ref to weave with x as int into void is handler   # function decay
    calling register_cb with handler                            # passes C callback
    calling cb with 1                                           # calls through pointer
```

- **Callback Decay to `void*`:** Any `weave` identifier or lambda can be passed where `ref to void` or `ref to frozen void` is expected (common in C APIs taking `void* user_data` callback pointers).
- **Callback Casting:** The compiler automatically emits explicit function pointer casts (e.g. `((AudioCallback)on_audio)`) to satisfy strict C99/C11 compilers (such as GCC 14+).

### 8.4 Lambdas

Anonymous inline functions are declared using `lambda`, comma-separated typed parameters, and an `into` expression:

```pengu-fragment
let no_args as weave into int is lambda into 42
let double as weave with x as int into int is lambda x as int into x * 2
let add as weave with a as int, b as int into int is lambda a as int, b as int into a + b
```

- **Parameter & Return Types:** Lambda parameters require explicit type annotations. The return type is inferred automatically from the body expression.
- **No Closures / Static Functions:** Lambdas do not capture surrounding local variables. They can access only their own parameters and module-level constants, types, and weaves.
- **Codegen:** Lambdas are pre-scanned and emitted as top-level `static` C functions named `_pengu_lambda_1`, `_pengu_lambda_2`, etc. At the call site, the lambda evaluates to the static function's address.
- **Runtime Callstack Tracking:** Lambda functions participate in the runtime's 64-frame ring buffer by emitting `pengu_frame_push("_pengu_lambda_N", file, line)` and `pengu_frame_pop()`, ensuring panics and fatal crash signals originating within lambdas accurately report their source line.
- **A lambda body is a function boundary.** Because the body becomes its own C function, `break` / `continue` inside it can never target a loop of the enclosing `weave`: a bare jump is `E0007` (there is no loop in *this* function) and a labeled one is `E0004` (the label is not in the lambda). A loop *inside* the lambda works normally, and its labels are the lambda's own, so the same label name may appear in the lambda and in the enclosing weave (`E0069` counts duplicates within one function only).

```pengu-fragment
outer: for i from 0 to 3:
    var step as weave into int is lambda into do:
        break outer            # E0004: 'outer' labels a loop in another function
    var ignored as int is calling step
```

### 8.4.1 Why lambdas don't capture

A lambda is a **static** function with no hidden environment. That is a
language decision, not a missing feature.

PenguScript's peers — Zig, Odin and Nelua — do not have closures either.
Implementing them requires one of: a garbage collector (excluded by §13),
lifetime tracking (a new type system), or a late-binding trampoline (not
portable C99 and not zero-cost). All three would violate **explicit over
hidden** and the zero-cost-abstraction rule. The cases that make programmers
reach for a closure have explicit answers:

| You need… | Use… |
|---|---|
| a C callback with `void* user_data` | `ref to void` + `sigil of` (§8.3) |
| a visitor over an AST | `concept` + `bind` + `judge over rune` (§10.2, §7.4.1) |
| a pipeline step with an extra parameter | `std.loom.*_ctx` (§19.3) |
| to return a configured function | a `rune` with a `concept`, or `std.functor.Fn1` (§19.3) |
| a callback stored for later | `std.functor.Fn1` / `Fn2` / `Fn3` (§19.3) |
| an event handler with state | a `rune` + `enchanting` (§10.1) |

This is not a compromise forced on the compiler: the self-hosted toolchain uses
exactly these patterns. The formatter is a `concept` visitor over the AST, the
documentation generator stores `std.functor.Fn*` callbacks, and the pipeline
stages that need configuration take `loom.*_ctx` contexts. A callback that
remembers something is a **value you build explicitly**, never an environment
the compiler captures behind your back.

```pengu
# The thick-function pattern from std.functor: the context is an explicit value.
import std.functor
import std.spark

rune Multiplier:
    factor as int

weave apply with m as ref to Multiplier, x as int into int:
    return m->factor * x

weave main into int:
    var m as Multiplier is with factor is 3
    var f as functor.Fn1 of int, int is calling functor.make_fn1 with apply, (sigil of m)
    calling spark.println with "{calling f.call with 5}"     # 15
    return 0
```

### 8.5 `ritual` methods (static)

```pengu-fragment
enchanting Vec2:
    weave ritual zero into Vec2:
        return with x is 0.0, y is 0.0

    weave length_sq into float:
        return self->x * self->x + self->y * self->y

weave main into int:
    var origin as Vec2 is calling Vec2.zero     # called on TYPE
    var l as float is calling origin.length_sq  # called on INSTANCE
    return 0
```

- `ritual` methods are associated functions (static methods) belonging to a type namespace. They have no `self` parameter. Referencing `self` inside a `ritual` raises `E0033: InvalidRitualSelfAccessError`.
- Calling a `ritual` method on an instance object, or calling an instance method on a type name, raises `E0034: InvalidRitualCallError`.

---

## 9. Composite types

### 9.1 `rune` — structs

```pengu
rune Player:
    name as string
    hp as int
    is_alive as bool
    _secret_id as int                    # private field (E0043 outside its module)
```

Construction:

```pengu-fragment
var p as Player is with name is "Hero", hp is 100, is_alive is true
var q as Player with:                        # block form, see §18
    set .name is "Villain"
    set .hp is 50

# Nested construction:
var hero as Person with:
    set .name is "Ada"
    set .age is 30
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
        set .zip is "12345"
```

- **Layout:** Runes map 1:1 to C structs, preserving exact memory layout and field alignment across C FFI boundaries.
- **Field Access:** Direct access uses `p.name`; access through a reference `ref to Player` uses pointer arrow syntax `p->name` (`E0003` if dot is used on reference).
- **Destructuring:** Runes can be unpacked into local variables using destructuring declarations: `let (n, h, a) is p` (§5.1).
- **Encapsulation (`E0043`):** Fields with a leading underscore (e.g. `_secret_id`) are private to the **module** that declares the rune — its file — and to any `enchanting` block for that rune, wherever it lives. Access or assignment via dot (`p._secret_id`) or pointer arrow (`p->_secret_id`) from any other module raises `E0043: PrivateSymbolAccessError`; so does `judge p over _secret_id` and binding `_secret_id` in a `with` list from another module. Two modules of one program:

```pengu-fragment
# --- secret.pengu: the module that declares the rune owns its privates ------
rune Box:
    _hidden as int
    shown as int

weave peek with b as Box into int:
    return b._hidden                       # OK: same module

enchanting Box:
    weave bump with n as int into int:
        return self->_hidden + n           # OK: an enchanting block is inside the rune

# --- main.pengu: a different module ----------------------------------------
import secret

weave steal with b as secret.Box into int:
    return b._hidden                       # E0043: private to 'secret'
```

#### 9.1.1 `cyclus` — self-referential types

By default a type that contains itself **by value** has infinite size and is
rejected with `E0050`:

```pengu-fragment
rune Bad:
    next as Bad          # E0050: infinite type size
```

`cyclus` states explicitly that the declaration is intentionally
self-referential; the cycle must still be broken by pointer indirection
(`ref to`, `maybe ref to`, `slice`, `list`, `map`):

```pengu
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T      # OK: indirection breaks the cycle
```

`cyclus` is documentation-as-syntax: it does **not** make a by-value cycle
legal (that would still produce a C struct containing itself), it only marks
recursive declarations so readers and tooling know the recursion is intended.

#### 9.1.2 `derive` — automatic concept implementations

`derive` asks the compiler to generate the C helpers for a built-in concept
from the rune's fields:

```pengu
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int
```

| Concept | Generated C | Enables |
|---|---|---|
| `Par` | `<Rune>_eq`, `<Rune>_eq_val`, `<Rune>_Par` | `==`, `!=` |
| `Ordo` | `<Rune>_cmp`, `<Rune>_cmp_val`, `<Rune>_Ordo` | `<`, `<=`, `>`, `>=` |
| `Vinculum` | `<Rune>_Vinculum`, `<Rune>_hash` | rune as a `map` key |
| `Imago` | `<Rune>_clone`, `_pengu_clone_<Rune>` | a deep-copy helper you call before storing a rune |
| `Nexus` | `<Rune>_nexus`, `_pengu_cleanup_<Rune>` | a destructor you invoke with `banish` |

Rules:

* Only `Par`, `Ordo`, `Vinculum`, `Imago` and `Nexus` are derivable; anything
  else raises `E0005`.
* Every field must itself implement the derived concept, otherwise `E0032`
  points at the offending field.
* On a generic rune the derived concepts become **bounds on the type
  parameters**: `rune Point shard T derive Par` implies `T: Par` in the
  generated helpers.
* `Imago` and `Nexus` are implied by each other: a type that can deep-copy its
  fields can also release them, so `derive Imago` also generates `Nexus` and
  vice versa. Neither is applied automatically to a container store.
* Comparison on a rune without the matching `derive` is `E0049`; without it the
  generated C would call a helper that does not exist.
* `derive` is rejected with `E0005` on `echo` declarations: an `echo` is an
  untagged C union, so equality/ordering/hashing would read memory the last
  write did not initialise. Use an algebraic `omen` (§9.3) or implement the
  concept explicitly with `bind` (§10.3).
* Algebraic omens are tagged structs and support the same `derive` clause on
  their payload variants (only the active variant's payload is inspected).
  A payload-less variant may be used as a value (`var s as Shape is Point`) or
  in a comparison (`s == Point`), not only as a `judge` pattern.
* A value with a derived `Nexus` can be released explicitly — `banish doc`
  lowers to `_pengu_cleanup_Doc(&doc)` (idempotent: the runtime banish helpers
  null the buffers they free), so `defer banish doc` is the idiom for a local
  whose fields hold heap memory. Nothing releases a local *rune* for you; write
  `derive Nexus` when you want a destructor and call `banish` yourself.

### 9.2 `echo` — unions

```pengu
echo Number:
    i as int
    f as float
```

An `echo` compiles directly to a C `union`. Accessing any field of an `echo` union triggers compiler warning `[W0002] Echo union access is unsafe`, because union fields share memory without an automatic discriminant tag. For type-safe sum types, prefer algebraic `omen`s.

### 9.3 `omen` — enums, string-valued omens & algebraic sum types

PenguScript provides three distinct flavors of `omen`:

```pengu
# 1. Numeric Enum (simple C enum)
omen Direction:
    North is 0
    South is 1
    East is 2
    West is 3

# 2. String-Valued Omen
omen Color with string:
    Red
    Green
    Blue

# 3. Algebraic Data Type (Sum Type with Payloads)
omen NetworkEvent:
    Disconnected
    Connecting with attempt as int
    Connected with session_id as string, latency_ms as float
```

#### String-Valued Omens (`omen X with string:`):
- Declared with `with string:` after the omen name.
- Every variant evaluates to a `PenguString` containing its own variant name (`Red` -> `"Red"`).
- **No Payloads Allowed:** Variants of a string-valued omen cannot declare payloads; adding `with` to a variant raises `E0028: InvalidOmenPayloadValueError`.
- **Codegen:** Emits `#define <Omen>_<variant> pengu_string_from_cstr("<variant>")`. In expressions, `Color.Red` or `Red` yields an immutable `string`.

#### Codegen Emission Modes:
- **Normal `.pengu` numeric omen:** Emits a C `typedef enum { <Omen>_<variant> = val, ... } <Omen>;`.
- **Declaration `.d.pengu` omen:** Emits **bare variant names** (`MODE_FAST`, `FLAG_VERBOSE`) matching upstream C header enums without prefixing.
- **Insignia-Prefixed Mode (`c_name != name`):** When the module specifies an `insignia <prefix>` directive, the generated C enum type receives the prefix (`<c_name>`, e.g. `mylib_Color`), and all variant enum tags are generated as `<c_name>_<variant>` (e.g. `mylib_Color_Red`), avoiding C name collisions across multi-module builds.
- **String-Valued omen:** Emits string constant definitions (`#define <c_name>_<variant> pengu_string_from_cstr("<variant>")`).
- **Algebraic omen:** Emits a tagged C struct containing a discriminant tag (`<c_name>_Tag`) and a payload union:
  ```c
  typedef struct {
      int32_t tag;
      union {
          struct { int32_t attempt; } Connecting;
          struct { PenguString session_id; float latency_ms; } Connected;
      } data;
  } NetworkEvent;
  ```

#### Omen Invariants & Validation:
- Simple variant names can be referenced directly (`Red`) or qualified (`Color.Red`, `Color_Red`).
- Duplicate variant values raise `E0027: DuplicateOmenValueError`.
- Variant values must be compile-time integer constants (`E0029`).
- If variant names collide across different omens in the same module, unqualified references raise `E0046`, requiring explicit qualification.

### 9.4 `seal`, `alias`, `opaque`

```pengu
seal UserId as int          # distinct nominal type: needs explicit `to` casts
alias Inches as int         # transparent structural alias: interchangeable
alias Buffer as opaque      # C opaque pointer handle (used behind `ref to`)
```

- **`alias` (Structural):** A pure synonym for another type. Passes all type checks interchangeably (`AliasType.is_compatible` is transparent).
- **`seal` (Nominal):** Strong newtype wrapping an underlying representation. Prohibits implicit assignment to or from the underlying type. Casting requires an explicit conversion: `var id as UserId is (raw_id to UserId)`.
- **`opaque` (Handles):** Represents incomplete C types. Direct instantiation by value is forbidden (`E0012: Cannot instantiate opaque type`). Opaque types must be manipulated through pointers: `ref to Buffer`.

### 9.5 `frozen` — read-only qualification

`frozen` is C's `const`: it marks a value or a pointee as not writable. It is
orthogonal to `let`/`var`, which control whether the **name** can be reassigned.

```pengu-fragment
frozen int                      # const int
ref to frozen int               # const int*
frozen ref to int               # accepted alias — normalises to 'ref to frozen int'
frozen Player                   # const Player
ref to frozen void              # const void*   ← what qsort asks for
```

- **Canonical qualifier placement:** `frozen` qualifies the *pointee*, so the
  canonical spelling is `ref to frozen T`. `frozen ref to T` is accepted and
  normalised by `ast_to_type` to the same type — write the canonical form in new
  code so that a grep for `ref to frozen` finds every read-only view.

`frozen` is a **soft** keyword: it is only special in type position, so a
variable, field or weave named `frozen` keeps working.

#### Assignment & Directional Compatibility

A mutable value flows into `frozen` (as in C); the reverse does not:

```pengu-fragment
var x as int is 5
set x is 6                      # OK

var y as frozen int is x        # OK: 'y' is a read-only copy
# set y is 7                    # E0006: cannot write through 'frozen'
```

- **`_drops_frozen()` Enforcement:** The semantic checker strictly forbids stripping the `frozen` qualifier (`frozen -> mutable` raises `E0005: TypeMismatchError`).
- **Pointee Protection (`_frozen_write_block`):** Writing through a pointer to a frozen pointee (`ref to frozen T`) is rejected:
  - Setting arrow field: `set p->x is 1` raises `E0006`.
  - Setting index element: `set p at i is 1` raises `E0006`.
  - Setting pointer dereference: `set essence of p is 1` raises `E0006`.
- **Pointer Normalization:** `frozen ref to T` normalizes in `ast_to_type` to `ref to frozen T` (pointee constness). PenguScript never emits `T* const`.
- **Wildcard Pointers:** `ref to void` and `ref to frozen void` accept any pointer type, enabling universal interop with C APIs.

#### Use in C interop

`frozen` exists to describe C signatures that carry `const`. Complete `qsort`
example (sorted output: `1 2 3`):

```pengu-fragment
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

```pengu-fragment
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

### 9.6 `antiquus` — embedded C blocks

An `antiquus` declares a function whose body is **literal C code**, delimited by triple quotes. It is the language's escape hatch: system primitives, performance-critical code and FFI glue that PenguScript does not yet express directly, without leaving the `.pengu` file or maintaining a separate `.c`.

The header has the shape of a `weave`:

```pengu
antiquus name shard T with p1 as T, p2 as int is 3 into int:
    """
    /* C body */
    return p1;
    """
```

#### Rules

- **The body must be a triple-quoted string**, `"""…"""` or `r"""…"""`. The `r"""…"""` form is recommended when the C contains backslashes (`printf("a\n")`), because it does not interpret escapes. A missing or empty body is `E0059`.
- The header is exactly a `weave` header: `shard_params`, `where`, parameters with default values and any type (`string`, `list of T`, runes, `ref to T`, …) are valid, and the return type is written with `into`.
- **Parameter names must be valid C identifiers.** The body sees them verbatim, so a parameter named `if`, `int` or `while` is `E0035`: `_c_ident`'s `_name` escape is deliberately *not* applied, because then the body could not name it.
- `many T` is **not** allowed (`E0005`). For raw C varargs, declare a separate `declare` binding with `...`; `antiquus` only takes ordinary parameters. To pass a variable number of elements, use a `slice of T` and read `s.data` / `s.len`.
- **Not allowed in a `.d.pengu`** (`E0025`): a declaration file cannot contain bodies.
- `main` cannot be an `antiquus` (`E0040`); the entry point is a `weave`.
- Supported attributes: `@inline`, `@cold`, `@deprecated`, `@noreturn` and `@export("symbol")`.

An `antiquus` is called like any `weave`:

```pengu
import std.spark

antiquus add with a as int, b as int into int:
    """
    return a + b;
    """

weave main into int:
    var total as int is calling add with 20, 22
    calling spark.println with "{total}"
    return 0
```

#### `@export` and dead-code elimination

The C name of an `antiquus` honours the module's `insignia` exactly like a `weave`. `@export("symbol")` pins the emitted C symbol and turns the declaration into a **DCE root**: it survives even when no PenguScript code calls it, because it is the FFI entry point the attribute promises.

```pengu
@export("pengu_fast_double")
antiquus fast_double with x as int into int:
    """
    return x * 2;
    """
```

Without `@export`, an `antiquus` declared in a `std/` or `lib/` module is pruned when nothing references it, exactly like an unused `weave`.

#### What the C body can do

- Read and write its **parameters**, by their exact C names.
- Call the whole **PenguScript runtime** (`pengu_string_from_cstr`, `pengu_println`, `pengu_list_push`, `pengu_map_put`, …): every bundle includes `pengu_runtime.h` first.
- Use `#include` — both the module's own and any written inside the body — plus any earlier declaration (`rune`, `declare`, `include`, `link`) of the module.

#### What it **cannot** do

- **The C is not type-checked.** If you write `return "a";` in an `antiquus into int`, the diagnostic comes from the C compiler, not from PenguScript.
- **Ownership is not tracked.** If you return an owned `string`, documenting and releasing it with `banish` is your responsibility.
- **It captures no local variables.** The body sees only its parameters and the module's globals; there is no closure over the surrounding PenguScript scope.
- **It cannot live in a `.d.pengu`.**

#### Compilation errors inside the C body

Every body is emitted behind `#line 1 "antiquus:<name>"`, so a syntax or type error in the C points at the `antiquus` and at the line of the **body**, counted from 1:

```text
antiquus:fast_abs:3:12: error: expected ';' before 'return'
```

#### Examples

An architecture primitive, selected at compile time:

```pengu
when arch == "x64" and os == "linux":
    antiquus read_tsc into u64:
        """
        unsigned int lo, hi;
        __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
        return ((unsigned long long)hi << 32) | lo;
        """
else:
    antiquus read_tsc into u64:
        """
        return 0;
        """
```

Returning a runtime value:

```pengu
antiquus make_hello into string:
    """
    return pengu_string_from_cstr("hello from C");
    """
```

Small helpers the monolithic `pengu_runtime.h` should not have to host:

```pengu
antiquus fast_abs with x as int into int:
    """
    return x < 0 ? -x : x;
    """

antiquus fast_min with a as int, b as int into int:
    """
    return a < b ? a : b;
    """
```

#### When to use `antiquus`

- To reach the system's C (syscalls, threading primitives, SIMD, hardware counters).
- To wrap a C library that cannot be expressed as a `declare`.
- To reimplement `pengu_runtime.h` helpers in the `std/` module that uses them, so DCE can prune them when nothing imports that module.

#### When **not** to use `antiquus`

- For logic PenguScript already expresses. Loops, conditionals, error handling and collections are written in pure PenguScript; rewriting them in C loses type checking and ownership tracking and gains nothing.
- For FFI to an existing library. That is what `declare` + `include` + `link` are for: they bind the real function and emit **no** embedded C.

---

## 10. Methods, concepts & binding

In PenguScript, methods, contracts, and type extensions are separated from struct definitions:
- Methods are attached to types via `enchanting T:` blocks.
- Contracts are declared via `concept Name:` blocks and implemented via `bind Type with Concept:` blocks.

> [!IMPORTANT]
> **Concepts are compile-time contracts, NOT runtime interfaces.**
> Unlike interfaces in Java, C#, or Go, a `concept` does not represent a runtime type, does not generate a virtual method table (vtable), and does not support dynamic dispatch or polymorphic fat pointers. Concepts exist strictly to define compile-time constraints and bounds for generic type parameters (`where T: Concept`), guaranteeing zero runtime overhead.

---

### 10.1 `enchanting` — métodos sobre tipos

Methods are attached to any user-defined type (`rune`, `echo`, `omen`) or built-in container using an `enchanting` block:

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    # Instance method: 'self' is implicit and has type 'ref to Player'
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

    # Associated (static) function: declared with 'ritual', no 'self'
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100
```

#### Reglas de `self` y métodos `ritual`:
1. **Acceso a `self`:** `self` se pasa implícitamente por referencia (`ref to T`). Por tanto, el acceso a sus campos requiere la flecha `self->field`. El uso de punto `self.field` arroja el error `E0003: SelfDotAccessError` (*help: Change 'self.' to 'self->'*).
2. **Métodos asociados (`ritual`):** Las funciones estáticas asociadas a un tipo se declaran anteponiendo la palabra clave `ritual`. No reciben `self`. Referenciar `self` dentro de un método `ritual` arroja `E0033: InvalidRitualSelfAccessError`.
3. **Invocación:**
   - Los métodos de instancia se invocan sobre valores o variables: `calling player.heal with 25` o `calling player->heal with 25`.
   - Los métodos `ritual` se invocan exclusivamente sobre el nombre del tipo: `var p as Player is calling Player.new_hero with "Ada"`.
   - Invocar un método `ritual` sobre una instancia o un método de instancia sobre el nombre del tipo arroja `E0034: InvalidRitualCallError`.

#### `@mutates` — one method, an in-place form and a pure form

`@mutates` declares a method whose *result* the compiler assigns back to the
receiver. It is only valid on a method inside an `enchanting` block, the method
must return the receiver's own type, and the body is written as if it were
**pure**: `self` is still an immutable value and the body `return`s the new
value. The compiler never relaxes `E0006` — the assignment happens at the call
site, not inside the method.

One C function is emitted (<code>&lt;Type&gt;_&lt;method&gt;</code>); it has two
surface forms at the call site:

| Spelling | Meaning | Returns |
|---|---|---|
| `calling x.clamp with lo, hi` | mutates `x` in place | nothing (statement only) |
| `calling x.get_clamp with lo, hi` | pure | the new value |

```pengu
import std.spark

enchanting int:
    @mutates
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

weave main into int:
    var hp as int is 150
    calling hp.clamp with 0, 100     # hp == 100 (mutates)
    var raw as int is calling hp.get_clamp with 0, 50
    calling spark.println with "{hp} {raw}"
    return 0
```

Rules:

- `@mutates` outside an `enchanting` block, with a mismatched return type, or on
  a body that assigns to the receiver is `E0067`.
- Declaring an explicit `weave get_<name>` next to `@mutates weave <name>` is
  `E0068`: the `get_<name>` spelling is reserved for the pure form.
- Using the bare mutating name where a value is required (an initializer, an
  argument, a `return`) is `E0066`; use `get_<name>` there.
- The receiver must be writable: `calling let_x.clamp` is `E0006`, exactly as
  `set let_x is …` would be.
- Chained statements stay sequential — `calling x.clamp` followed by
  `calling x.twice` emits `x = int_clamp(x, …); x = int_twice(x);`, never one
  nested temporary.

For a **reference** receiver (`string`, a collection, a `rune`) the same effect
is available without `@mutates`: write an ordinary `weave <name> into void:` that
mutates through `self` (e.g. `set essence of self is …`) and declare the pure
`weave get_<name> into T:` alongside it.

#### Nomenclatura en C y prefijos de `insignia`:
- Los métodos de instancia se emiten en C como `<Type>_<method>(Type* restrict self, ...)`:
  ```c
  void Player_heal(Player* restrict self, int32_t amount);
  ```
- Los métodos `ritual` se emiten en C como `<Type>_<method>(...)` sin el primer parámetro `self`.
- **Regla de prefijo de `insignia`:** La directiva `insignia` prefija las funciones de módulo y los tipos de usuario. Sin embargo, para métodos que encantan tipos primitivos o contenedores estándar (`string`, `list`, `map`, `slice`, `maybe`, `result`), el generador de código **no** aplica el prefijo de módulo, emitiendo nombres limpios como `string_trim`, `list_of_int_sum` o `map_of_string_to_int_keys` para evitar colisiones con las funciones internas del runtime (`pengu_string_*`, `pengu_list_*`).

#### Encantamiento de contenedores integrados (`list`, `map`):
Los módulos de la biblioteca estándar como `std.tally` y `std.atlas` encantan directamente contenedores estándar:
- `enchanting list of int:` agrega métodos OOP como `calling xs.sum`, `calling xs.first`, `calling xs.reverse`, `calling xs.sort_asc`.
- `enchanting map of string to int:` agrega métodos como `calling m.keys`, `calling m.keys_sorted`, `calling m.get_or with k, 0`, `calling m.sum_values`.
- Dentro de un bloque `enchanting` sobre contenedores, `self` tiene tipo `ref to list of ...` o `ref to map of ...`. La iteración sobre la colección se realiza mediante `for x in essence of self:`, y el acceso indexado mediante `self at i` o `self at key`.

#### Encantamiento genérico de contenedores estándar (`shard` en `enchanting`):
A partir de PenguScript 0.15.0, es posible encantar contenedores estándar (`map`, `list`, `slice`, `maybe`, `result`) de forma genérica usando parámetros `shard`:

```pengu
enchanting map of shard K to shard V:
    weave size into int:
        return calling self.len

    weave is_empty into bool:
        return (calling self.len) == 0

    weave has_key with k as K into bool:
        return calling self.contains with k

    weave get_or with k as K, fallback as V into V:
        if calling self.contains with k:
            return self at k
        return fallback

    weave clone into map of K to V:
        var res as map of K to V is map of K to V
        with res:
            for k in essence of self:
                calling .put with k, (self at k)
        return res

    weave rename_key with old_key as K, new_key as K into bool:
        if not (calling self.contains with old_key):
            return false
        var val as V is self at old_key
        with self:
            calling .remove with old_key
            calling .put with new_key, val
        return true
```

##### Mecánica y Reglas del Encantamiento Genérico:
1. **Sintaxis de tipo:** El objetivo de `enchanting` acepta la palabra clave `shard` precediendo los parámetros de tipo en contenedores:
   - `enchanting map of shard K to shard V:`
   - `enchanting list of shard T:`
   - `enchanting slice of shard T:`
   - `enchanting maybe shard T:`
   - `enchanting result of shard T to shard E:`
2. **Monomorfización bajo demanda:** Al compilar, el compilador (`pengu_codegen.py`) monomorfiza los métodos genéricos únicamente para las combinaciones de tipos concretas invocadas en el programa (por ejemplo, `map of string to string` o `map of int to float`), emitiendo funciones C especializadas (ej. `map_of_string_to_string_get_or`, `map_of_int_to_float_clone`).
3. **Resolución de dependencias transitivas:** Cuando un método genérico invoca a otro método genérico sobre `self` (como `copy` delegando en `self.clone`), el compilador detecta la invocación transitiva e itera hasta alcanzar un punto fijo, registrando todas las firmas y prototipos antes de generar el código C.
4. **Precedencia por especificidad (Overriding concreto):** Si existe un bloque concreto (por ejemplo, `enchanting map of string to int:`), sus métodos tienen precedencia estricta sobre la implementación genérica para ese tipo concreto. Esto permite especializaciones de alto rendimiento o métodos específicos del tipo (como `sum_values` o `all_values_positive` en mapas numéricos) conviviendo con métodos genéricos estructurales (`clone`, `put_all`, `rename_key`).
5. **Mutación in-place con `with self:`**: Dado que `self` es una referencia (`ref to map of K to V`), la mutación de la colección se realiza de forma natural y segura mediante bloques de contexto `with self:`, invocando métodos del runtime como `.put`, `.remove`, `.clear`.
6. **Cero sobrecoste en tiempo de ejecución:** Todo el proceso de inferencia y sustitución ocurre en tiempo de compilación. No existen vtables, boxing de primitivos ni sobrecarga dinámica.

> **Implementación:** `pengu_grammar.py` (`type_or_param`), `pengu_types.py` (`shard_param_ref`), `pengu_checker.py::_check_enchanting_decl`, `pengu_codegen.py::_collect_weave`, `pengu_infer.py::_resolve_call_target`.

#### Encantamiento de primitivos y de `shard T`

Every primitive is a valid `enchanting` target. A primitive has no identity in C
(`int32_t` is a value, not an addressable object), so **`self` is the value
itself**: it is passed by value, `set self` is rejected with `E0006`, and
`self->field` is rejected with `E0003`. There are no fields to dereference and no
receiver to mutate.

```pengu
enchanting int:
    # 'self' has type 'int' (a value), not 'ref to int'.
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

# 'shard T' is one body for every type satisfying the bounds, monomorphized per
# concrete receiver at the call site ('int_is_even', 'i64_is_even').
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave main into int:
    var edad as int is 200
    var corregida as int is calling edad.clamp with 0, 120
    if calling corregida.is_even:
        return 1
    return 0
```

Rules:

1. **Spelling.** `int`, `i32`, `int32` and `int32_t` are one C type, so they are
   one method table: a method declared with `enchanting int:` is callable through
   any of them (the same holds for `byte`/`u8`). The emitted C symbol uses the
   canonical spelling: `<tname>_<method>`, e.g. `int_clamp`, `char_to_upper`,
   `bool_to_int`, `float_round`.
2. **Receiver by value.** `self` is `T`; a `ref to T` receiver is dereferenced at
   the call site (`calling p.double` with `p as ref to int` emits
   `int_double((*p))`). Runes, echos, omens, collections, `maybe`/`result` and
   `string` keep `ref to T` and `self->field`.
3. **Opt-in.** A primitive method exists only where the `enchanting` block is
   visible, and `(type, method)` may be provided once in the whole program
   (`E0047`), because two providers would emit the same C symbol.
4. **Zero overhead.** The body is emitted as a plain C function whose first
   parameter is the receiver value; there is no vtable, no boxing and no heap
   allocation for the call itself.

> **Implementación:** `pengu_types.py` (`PRIMITIVE_ALIASES`, `canonical_primitive_name`, `FnType.self_is_value`), `pengu_checker.py::_check_enchanting_decl`, `pengu_infer.py::_resolve_shard_method`, `pengu_codegen/symbols.py::_enchanted_receiver_is_value`.

---

### 10.2 `concept` — contratos de compile-time

Un `concept` define un conjunto de firmas de métodos que un tipo debe satisfacer para cumplir el contrato:

```pengu
concept Speaker:
    weave greet with target as string into string
    weave ritual default_greeting into string
```

#### Características y sintaxis:
- **Sintaxis completa:** `concept Name [shard T [and U]] [where T: OtherConcept] :` seguido de una o más firmas `weave`.
- **Sin cuerpos de implementación:** Los métodos dentro de un `concept` son puramente declarativos; no llevan `:` ni sentencias.
- **Concepts genéricos:** Los concepts pueden aceptar parámetros de tipo (`shard T`), permitiendo modelar contenedores y operaciones parametrizadas:
  ```pengu
  concept Container shard T:
      weave push with item as T into void
      weave len into int
  ```
- **Soporte de métodos `ritual`:** Los concepts pueden exigir métodos estáticos asociados (`weave ritual ...`), obligando al tipo a proveer constructores o utilidades estáticas.
- **Sin campos:** Un `concept` no puede declarar campos de datos, variables ni estados; únicamente firmas `weave`.

> **Implementación:** `pengu_grammar.py::concept_decl`, `pengu_checker.py::_collect_top_level`, `pengu_symbols.py::define_concept`.

---

### 10.3 `bind` — implementación del contrato

Un bloque `bind` conecta formalmente un tipo concreto con un `concept`:

```pengu-fragment
rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with target as string into string:
        return "Woof, {target}!"

    weave ritual default_greeting into string:
        return "Woof!"
```

#### Reglas impuestas por el compilador:
1. **Exhaustividad obligatoria (`E0031`):** Se deben implementar **todos** los métodos requeridos por el concept. Si falta uno o más métodos, el chequeador emite `E0031: UnimplementedConceptMethodError` (*Type 'T' does not implement method 'm' required by concept 'C'*).
2. **Concordancia estricta de firmas (`E0030`):** Cada método en el `bind` debe tener exactamente la misma cantidad de parámetros y un tipo de retorno compatible con la definición del concept (`E0030: ConceptMethodMismatchError`).
3. **Tipos de parámetros idénticos (`E0030`):** Los tipos de cada parámetro deben coincidir exactamente con los declarados en el concept.
4. **Existencia previa del tipo y concept (`E0004`):** El tipo objetivo (`Type`) y el concept (`Concept`) deben estar declarados antes de su bloque `bind` (salvo que provengan de un `.d.pengu` con includes C).
5. **Múltiples contratos:** Un tipo puede tener tantos bloques `bind` como concepts necesite (`bind Player with Speaker:`, `bind Player with Serializable:`).
6. **Sin métodos por defecto:** Los concepts no proveen implementaciones por omisión (*default methods*); cada `bind` debe escribir la implementación completa de cada método.

> **Implementación:** `pengu_checker.py::_collect_top_level` (rama `bind_decl`), `pengu_symbols.py::concept_bindings`.

---

### 10.4 Resolución de métodos en compile-time

Cuando el compilador encuentra una llamada `calling x.method(...)`, el analizador semántico (`pengu_infer.py::_resolve_call_target`) resuelve la función destino siguiendo una búsqueda determinista:

1. **Determinación del receptor:** Se evalúa la expresión `x` para obtener su tipo base (`obj_type`).
2. **Desenvolvimiento de referencias:** Si `obj_type` es un `ref to T`, un alias (`alias`) o un tipo calificado (`frozen`, `seal`), se desenvuelve hasta el tipo subyacente `t_name`.
3. **Parámetro de tipo (`TypeParam`):** Si `x` es un parámetro genérico `T`, el compilador consulta los bounds declarados en la cláusula `where T: Concept`. Si el concept contiene el método, resuelve la llamada contra la firma del concept.
4. **Tabla unificada de métodos:** Se busca la tupla `(t_name, method_name)` en `symbols.methods` (tabla poblada por bloques `enchanting` y `bind`). Si el método es `ritual`, rechaza la llamada con `E0034`.
5. **Búsqueda por nombre calificado:** Se busca en `symbols.functions[f"{t_name}_{method_name}"]`.
6. **Caída a plantilla monomorfizada:** Si el tipo fue monomorfizado a partir de un genérico (ej. `Box_int`), se obtiene el nombre base `base_tname = t_name.split("_")[0]` (`Box`) y se busca en `symbols.generic_methods`. Las variables de tipo se sustituyen con los argumentos concretos correspondientes.
7. **Tabla de bindings de concepts:** Se busca `(base_tname, concept)` en `symbols.concept_bindings` para resolver métodos provistos mediante `bind`.
8. **Métodos integrados de contenedor:** Se comprueban métodos primitivos de listas (`push`, `pop`, `len`, etc.) y mapas (`get`, `put`, `contains`, etc.).
9. **Fallo:** Si ningún paso localiza el método, se emite `E0004: Type 't_name' has no method 'method_name'`.

#### Diagrama de resolución:

```text
  calling x.method(...)
         │
         ▼
  ¿Es 'x' un TypeParam (T)?  ──[Sí]──► Buscar en bounds (where T: Concept)
         │ [No]
         ▼
  Desenvolver punteros / alias -> t_name
         │
         ▼
  ¿Existe en symbols.methods[(t_name, method)]? ──[Sí]──► Verificar !ritual -> FnType
         │ [No]
         ▼
  ¿Existe en symbols.functions[t_name_method]? ──[Sí]──► Retornar FnType
         │ [No]
         ▼
  base_tname = t_name.split("_")[0]
  ¿Existe en generic_methods[(base_tname, method)]? ──[Sí]──► Sustituir shards -> FnType
         │ [No]
         ▼
  ¿Existe en concept_bindings[(base_tname, concept)]? ──[Sí]──► Retornar FnType
         │ [No]
         ▼
  ¿Es método nativo de ListType o MapType? ──[Sí]──► Retornar FnType sintético
         │ [No]
         ▼
  Error E0004: Type 't_name' has no method 'method'
```

> **Implementación:** `pengu_infer.py::_resolve_call_target`.

---

### 10.5 Bounds en genéricos (`where T: A and T: B`)

Los concepts se emplean principalmente como restricciones de tipo (*bounds*) en funciones y estructuras genéricas:

```pengu-fragment
concept Measurable:
    weave weight into float

concept Printable:
    weave print_me into void

weave display_weight shard T where T: Measurable and T: Printable with item as T into void:
    calling item.print_me
    calling spark.println with "Weight: {(calling item.weight to string)}"
```

- **Sintaxis de restricciones:** Se declaran tras `shard` mediante la cláusula `where T: Concept1 and T: Concept2` (o separadas por comas `where T: Concept1, T: Concept2`).
- **Verificación en el punto de llamada:** Cuando una función genérica se especializa con un tipo concreto (ej. `calling display_weight with my_dog`), el compilador invoca `implements_concept(arg_t, bound, symbols)`.
- **Falta de bound (`E0032`):** Si el tipo argumento no cuenta con un bloque `bind` para el concept requerido, el compilador emite:
  ```text
  error[E0032]: generic type argument 'Dog' does not implement required concept bound 'Printable'
  ```
  *(help: Bind the required concept to the type using 'bind Type with Concept:'.)*

> **Implementación:** `pengu_checker.py::_check_type_bounds`, `pengu_infer.py::implements_concept`.

---

### 10.6 Limitaciones explícitas de los concepts

Un `concept` en PenguScript no es un tipo de datos ordinario en tiempo de ejecución. Las siguientes limitaciones son fundamentales por diseño:

1. **No puede utilizarse como tipo de valor de primera clase:** Aunque declarar `var s as Speaker` pasa la fase sintáctica (porque internamente `ConceptType` se acepta durante el chequeo preliminar), **el generador de C mapea cualquier `ConceptType` directamente a `void*`** (`CTypeMapper.to_c_type`), perdiendo la estructura de tipos. En consecuencia, invocar `calling s.greet` fallará con `E0004: Type 'Speaker' has no method 'greet'`.
2. **Sin despacho dinámico ni vtables:** El compilador emite llamadas directas en C. No existen punteros a tablas virtuales ni sobrecarga de indirección en tiempo de ejecución.
3. **Sin colecciones heterogéneas:** No es posible crear una lista `list of Speaker` que contenga instancias mixtas de `Dog`, `Player` y `Robot` para despachar llamadas polimórficas.
4. **Sin herencia entre concepts:** No existe `concept A extends B`. Las combinaciones de contratos se expresan mediante bounds múltiples (`where T: A and T: B`).
5. **Sin campos o variables de instancia:** Los concepts no pueden definir campos de datos.
6. **Sin métodos por omisión:** Cada tipo debe implementar explícitamente todos los métodos requeridos.
7. **Sin verificación ni introspección en runtime:** No existen operadores como `instanceof`, `as`, ni `is Speaker` en tiempo de ejecución. La conformidad con un concept es 100% estática.

#### Ejemplo de uso incorrecto vs. corrección idiomática:

```pengu-invalid
concept Speaker:
    weave greet into string

rune Dog:
    name as string

bind Dog with Speaker:
    weave greet into string:
        return "Woof"

weave main into void:
    var d as Dog is with name is "Buddy"

    # ❌ INCORRECTO: Usar el concept como tipo de variable
    # var s as Speaker is d           # El C codegen mapea 'Speaker' a void*
    # calling s.greet                 # E0004: Type 'Speaker' has no method 'greet'

    # ✅ CORRECTO 1: Invocación directa sobre el tipo concreto
    calling d.greet

    # ✅ CORRECTO 2: Invocación polimórfica estática mediante genéricos con bounds
    calling greet_anyone with d

weave greet_anyone shard T where T: Speaker with s as T into void:
    calling spark.println with calling s.greet
```

> **Implementación:** `pengu_codegen.py::CTypeMapper.to_c_type`, `pengu_infer.py::_resolve_call_target`.

---

### 10.7 Comparativa con interfaces de Java/C#

| Característica | Interfaces (Java / C#) | Concepts (PenguScript) |
|---|---|---|
| **Mecanismo de despacho** | Dinámico (vtable / itable) en runtime | Estático (direct C call) en compile-time |
| **Uso como tipo de variable (`var x as T`)** | ✅ Sí (referencia polimórfica) | ❌ No (se mapea a `void*`) |
| **Colecciones heterogéneas (`list of T`)** | ✅ Sí (`List<Speaker>`) | ❌ No (`list of Speaker` no es utilizable) |
| **Herencia entre contratos** | ✅ Sí (`interface B extends A`) | ❌ No (bounds múltiples `where T: A and T: B`) |
| **Métodos por defecto (*default methods*)** | ✅ Sí (Java 8+, C# 8+) | ❌ No (cada `bind` implementa todo) |
| **Campos o propiedades** | ✅ En C# / constantes en Java | ❌ No (solo firmas `weave`) |
| **Inspección en runtime (`instanceof` / `is`)** | ✅ Sí | ❌ No (resuelto en tiempo de compilación) |
| **Restricciones genéricas (*bounds*)** | ✅ Sí (`<T extends Speaker>`) | ✅ Sí (`shard T where T: Speaker`) |
| **Implementación externa (*ad-hoc*)** | ❌ Requiere declarar `implements` en la clase | ✅ Sí (`bind` se declara fuera del `rune`) |
| **Parámetros genéricos en el contrato** | ✅ Sí (`Comparable<T>`) | ✅ Sí (`concept Container shard T:`) |
| **Métodos estáticos requeridos** | ❌ Limitado o no exigible | ✅ Sí (`weave ritual` en `concept`) |
| **Sobrecarga de rendimiento** | Puntero a objeto + puntero a vtable | **Cero overhead** (inlined o salto directo) |

---

### 10.8 Ejemplo end-to-end compilable

El siguiente programa ilustra la definición de un `concept` con métodos de instancia y `ritual`, su implementación mediante `bind`, y su consumo a través de funciones genéricas con cláusulas `where`:

```pengu
import std.spark

# 1. Definición del contrato
concept Formatter:
    weave format_entry with title as string into string
    weave ritual category_name into string

# 2. Tipos de datos
rune LogEntry:
    level as string
    message as string

# 3. Implementación del contrato
bind LogEntry with Formatter:
    weave format_entry with title as string into string:
        return "[{self->level}] {title}: {self->message}"

    weave ritual category_name into string:
        return "SYSTEM_LOG"

# 4. Función genérica restringida por el concept
weave print_formatted shard T where T: Formatter with item as T, header as string into void:
    var rendered as string is calling item.format_entry with header
    calling spark.println with rendered

# 5. Punto de entrada
weave main into int:
    var entry as LogEntry is with level is "INFO", message is "Compiler pipeline ready"

    # Llamada al método ritual estático del concept directamente sobre el tipo
    calling spark.println with "Category: {calling LogEntry.category_name}"

    # Llamada a través de la función genérica con bound comprobado estáticamente
    calling print_formatted with entry, "Build"
    return 0
```

### 10.9 Built-in concepts

PenguScript ships a closed set of concepts that the compiler, the checker and
the generated C already understand. They are **not** keywords: they are
reserved names in the global scope. They may be used as `where` bounds, and the
ones marked *derivable* may also appear in a `derive` clause.

| Concept | Latin | Operations / capabilities it enables |
|---|---|---|
| `Num` | *numerus* | `+`, `-`, `*`, `/` and unary `-` on a type parameter |
| `Integrum` | *integer* | integer-only operators: `%`, `&`, `|`, `^`, `<<`, `>>`, `~`, plus `==`, `!=` and `<`, `<=`, `>`, `>=` |
| `Real` | *real* | floating-point only: `+`, `-`, `*`, `/` and unary `-`, plus `==`, `!=` and `<`, `<=`, `>`, `>=` |
| `Par` | *par* | `==`, `!=` |
| `Ordo` | *ordo* | `<`, `<=`, `>`, `>=` |
| `Vinculum` | *vinculum* | usable as a `map` key (hashing) |
| `Imago` | *imago* | deep copy (a `clone` helper for the rune) |
| `Nexus` | *nexus* | destruction (a `cleanup` helper invoked by `banish`) |
| `Forma` | *forma* | string interpolation / formatting (`"{x}"`) |
| `Iterabilis` | *iterabilis* | `for x in col` iteration |
| `Donum` | *donum* | default value via the `donum T` expression |

`Integrum` is a strict refinement of `Num`: an `Integrum` bound also satisfies
`Num` (so `where T: Integrum` allows `+`), but not the other way round — this is
what makes `%` reject `float`.

`Integrum` and `Real` are **disjoint branches** of `Num`. `Integrum` is the
integer-only refinement and `Real` the floating-point-only one, so no type
satisfies both: `float.is_even` (against `Integrum`) and `int.is_nan` (against
`Real`) are both `E0005`. A generic that only needs `+ - * /` should still bound
on `Num`; reach for `Integrum`/`Real` only when the method genuinely cannot work
for the other kind (`%` needs `Integrum`; `sqrt`/`is_nan` need `Real`).

**The bound set is a monotone chain.** A bound only ever *adds* capabilities, so
adding one can never break code that already compiled:

```
(no bound)  grants nothing  -- an unconstrained `shard T` may be instantiated
                               with a rune or a `string`, where `a + b` has no
                               C translation. It is still usable for any
                               concept-free plumbing, e.g.
                               `weave ident shard T with x as T into T`.
Num         + - * / and unary -
├─ Integrum    Num plus % & | ^ << >> ~ == != < <= > >=
└─ Real        Num plus == != < <= > >=   (floats only)
Par         == !=
Ordo        < <= > >=
Any         everything (an explicit escape hatch)
```

In particular `T: Num` does **not** grant `==` or `<`: equality needs `Par` and
ordering needs `Ordo`. A generic that both adds and compares says so:

```pengu-fragment
weave clamped shard T where T: Num and T: Ordo with lo as T, hi as T, v as T into T:
  if v < lo then return lo
  if v > hi then return hi
  return v
```

<!-- Machine-readable form of the chain above. tests/compiler/test_docs_bounds_sync.py
     parses this block and fails if it disagrees with CONCEPT_OPERATORS in
     pengu_parser/pengu_types.py. One concept per line, concept-table operator
     names, comma separated. -->
```text bounds-ops
Num: add, sub, mul, div, neg
Integrum: add, sub, mul, div, neg, mod, band, bor, bxor, shl, shr, bnot, eq, ne, lt, le, gt, ge
Real: add, sub, mul, div, neg, eq, ne, lt, le, gt, ge
Par: eq, ne
Ordo: lt, le, gt, ge
```

Which primitive and container types satisfy which concept is fixed by the
compiler's concept table:

| Type | Concepts |
|---|---|
| integer primitives (`int`, `i8`…`u64`, `usize`, `isize`, `byte`, …) | `Num`, `Integrum`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| floats (`float`, `f32`, `f64`, `double`) | `Num`, `Real`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| `bool` | `Par`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| `char` | `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| `string` | `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum`, `Iterabilis` |
| `list of T` / `map of K to V` | `Par`, `Iterabilis`, `Imago`, `Nexus`, `Donum` |
| `slice of T` | `Par`, `Iterabilis`, `Donum` |
| `maybe T` | `Par`, `Imago`, `Nexus`, `Donum` |
| `result of T to E` | `Par`, `Imago`, `Nexus` (no `Donum`: its payloads are heap pointers, §11.4) |
| `rune` (every field implements `Donum`) | `Donum` (automatic; a single non-defaultable field removes it) |

Runes, echos and algebraic omens gain a concept through `derive` (§9.1.2) or an
explicit `bind` (§10.3); a `where` bound is then satisfied by the derived
implementation. `Donum` is the exception: a `rune` or `echo` whose **every**
field implements `Donum` implements it automatically — no `derive` and no `bind`
— recursively through nested runes, `ref to T` (always `NULL`), `frozen`/`alias`/`seal`
wrappers, arrays and the defaultable containers (`list`, `map`, `slice`,
`maybe`). A single non-defaultable field (`result of T to E`, or a generic
parameter without a defaultable bound) removes `Donum` from the type. See §11.4.

`char` and `byte` are defaultable like their aliases (`i8`, `u8`): `donum char`
and `donum byte` are both `0`.

### 10.10 Coherence of `bind`

A type may bind several concepts, but the `(type, method)` pair may only be
provided once:

```pengu-fragment
concept A:
    weave f into int

concept B:
    weave f into int

bind Foo with A:
    weave f into int:
        return 1

bind Foo with B:
    weave f into int:
        return 2      # E0052: 'f' of 'Foo' is already provided by concept 'A'
```

Binding the *same* `(type, concept)` pair twice is also `E0052`.

(Primitive methods use their own code, `E0047`, for the same reason: see §10.1.) Splitting the
object-safe operations of one type over two concepts is fine as long as the
method names are distinct.

---

## 11. Generics

```pengu-fragment
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
- **Generic container enchanting:** Standard containers can be enchanted with type parameters directly (`enchanting map of shard K to shard V:`, `enchanting list of shard T:`, `enchanting slice of shard T:`). The compiler monomorphizes methods per concrete usage with full support for transitive calls on `self` and priority override from concrete blocks (see §10.1).

> [!IMPORTANT]
> PenguScript has no “turbofish” (`f::<T>`). Type parameters are inferred from
> argument types; when a type only appears in the *result* (e.g. a generic
> container builder) you must give the compiler concrete context, or the check
> fails with “Could not infer type parameter(s)”.

### 11.1 `shard` fundamentals

A type parameter is declared with `shard` and is in scope from the `with`
parameter list to the end of the declaration; it may also be used in the return
type and inside `rune` bodies:

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x

weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if calling xs.len == 0:
        return fallback
    return xs at 0
```

Every *concrete* call instantiates a specialized C function/struct
(`identity_int`, `Box_of_string`, …). Nesting a generic inside a generic is
supported without redeclaring helpers: `Box of (Box of int)`.

Explicit type arguments are available when inference cannot see them:

```pengu-fragment
var a as int is calling identity of int with 5
var b as string is calling identity of string with "hi"
```

### 11.2 Bounds

`where` clauses attach concepts to type parameters (see §10.5 for the full
grammar and §10.9 for the concept table):

```pengu-fragment
weave sum shard T where T: Num with xs as list of T into T:
    ...

weave clamped shard T where T: Num and T: Ordo with lo as T, hi as T into T:
    ...
```

Bounds are also propagated **into method bodies**: every `TypeParam` built while
checking a generic `weave`, `enchanting` or `bind` carries the bounds declared on
the receiver (`enchanting Box shard T where T: Par`) and on the method itself.

Bounds are enforced in **both directions**:

* reading/deriving — `T` may only be used where its bounds allow it
  (operators, `donum T`, iteration, …);
* writing — assigning into a `T` target requires a value that implements every
  bound (`set essence of x is "s"` with `T: Num` is `E0005`, §5.1); an unbounded
  `T` stays a wildcard, and `any`/`null`/another parameter are always accepted.

### 11.3 Operators in generic contexts

Operators are only available when the corresponding concept is in the bounds:

| Bound | Operators available on `T` |
|---|---|
| `Num` | `+`, `-`, `*`, `/`, unary `-` |
| `Integrum` | `%`, `&`, `\|`, `^`, `<<`, `>>`, `~`, `==`, `!=`, `<`, `<=`, `>`, `>=` (and everything `Num` allows) |
| `Real` | `+`, `-`, `*`, `/`, unary `-`, `==`, `!=`, `<`, `<=`, `>`, `>=` (and everything `Num` allows) |
| `Par` | `==`, `!=` |
| `Ordo` | `<`, `<=`, `>`, `>=` |

`Integrum` grants equality and ordering as well as the integer-only operators:
every type that satisfies `Integrum` in this language is an integer primitive, and
every integer primitive satisfies `Par` and `Ordo`. That is what lets the
canonical primitive-enchanting idiom `enchanting shard T where T: Integrum:`
write `(self % (2 to T)) == donum T` and `while (k * k) <= n` without restating
`and T: Par` / `and T: Ordo` (§10.1).

`Real` is the floating-point-only refinement: every type that satisfies `Real`
satisfies `Num`, and the only primitives that satisfy it are `float`, `f32`,
`f64` and `double`. It grants arithmetic, equality and ordering for the same
reason `Integrum` does — every type satisfying `Real` is a floating-point
primitive, and every floating-point primitive satisfies `Par` and `Ordo` — so
`enchanting shard T where T: Real:` can write `self != self` (`is_nan`),
`(a - b).abs < eps` (`approx_eq`) and `self + self` without restating
`and T: Par` / `and T: Ordo`. The two refinements are disjoint:
`Integrum` never satisfies `Real` and vice versa.

The same table bounds `enchanting shard T:` method bodies: a method declared on a
bounded shard is only instantiated for receivers that satisfy the bound, and the
violation is reported where the body is instantiated
(`float.is_even` against `where T: Integrum` is `E0005`).

Using an operator without its bound raises `E0049` with the exact `where`
clause to add:

```pengu-fragment
weave bad shard T with a as T, b as T into T:
    return a + b            # E0049: add 'where T: Num'

weave mod2 shard T where T: Num with a as T, b as T into T:
    return a % b            # E0049: '%' needs 'where T: Integrum'
```

### 11.4 `donum T` — default values

`donum T` is the zero/default value of a defaultable type. For scalars,
pointers and structs it lowers to the C compound literal `(T){0}` (an
array-typed slot gets the brace form `{0}`); containers and `maybe` have a
*semantic* default instead (see "Container defaults" below):

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

`donum T` needs a bound whose types are defaultable (`Num`, `Integrum`, `Real`,
`Par`, `Ordo`, `Forma`, `Donum`), or a concrete type that implements `Donum`:

```pengu-fragment
var n as int is donum int                 # 0
var s as string is donum string           # empty string
var f as float is donum float             # 0.0
```

**Automatic `Donum` for runes and echos.** A `rune` or `echo` implements
`Donum` automatically when **every field** implements `Donum`; no `derive
Donum`, no `bind X with Donum:` and no helper are needed. The rule is recursive
through the field types:

- a field whose type is another all-defaultable `rune`/`echo` counts;
- `ref to T` is always defaultable (`NULL`), whatever `T` is;
- `frozen T`, `alias X as T` and `seal X as T` delegate to what they wrap;
- `array of T with size N` follows `T` (`N` zeroed elements);
- `list of T`, `map of K to V`, `slice of T` and `maybe T` are defaultable — an
  empty value, not a blind zero (below) — so a rune field of any of them counts.

A single non-defaultable field removes `Donum` from the whole rune, and the
error names the rune: `donum Bag` for `rune Bag: payload as result of int to
string` is `E0049` with "not every field implements 'Donum'". `char` and `byte`
are defaultable like their aliases (`i8`, `u8`).

**Generic runes.** `rune Box shard T: value as T` is `Donum` only under a
defaultable bound such as `where T: Donum` (or another bound from the compiler's
defaultable set: `Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Forma`, `Donum`).
`donum (Box of T)` without such a bound is `E0049`. A concrete instantiation
such as `donum (Box of int)` is accepted, because `int` itself is defaultable:

```pengu
rune Box shard T where T: Donum:
    value as T

weave zero_box shard T where T: Donum into Box of T:
    return donum (Box of T)               # requires the bound above
```

**Container defaults are semantic empty values.** `list`, `map`, `slice` and
`maybe` implement `Donum`. Their default is not a blind `(T){0}`: it is a
designated-initialiser compound literal that sets only the metadata the
container needs, leaving every other field zero, so the value is a *usable empty
container* and the first `push`/`put` allocates:

```pengu-fragment
var xs as list of int is donum (list of int)              # ((PenguList){ .elem_size = sizeof(int32_t) })
var m as map of string to int is donum (map of string to int)
var sl as slice of int is donum (slice of int)
var opt as maybe int is donum (maybe int)                 # pengu_maybe_none()
```

- `list` / `slice`: `elem_size` is set; `data` is `NULL`, `len` and `cap` are 0.
- `map`: `key_size` and `val_size` are set; there are no entries.
- `maybe T`: `pengu_maybe_none()` — not present.

None of these allocate, so `donum (list of int)` is usable in any value
position: a local, a struct field, an argument, a `static var` initialiser. The
reason the default is not `(PenguList){0}` is that a blind zero leaves
`elem_size == 0`, which is a **corrupt** container, not an empty one — the first
`push` would copy zero bytes.

**`result` deliberately has no default.** `result of T to E` does not implement
`Donum`: both payloads are heap pointers, so a zeroed result would hand out a
`NULL` `.error` / `.value` (a crash) and a real one would need an allocation,
which `donum` must not perform. `donum (result of int to string)` is `E0049`,
and the message points at the constructors:

```pengu-invalid
# Invalid: a result has no neutral value.
var r as result of int to string is donum (result of int to string)

# Fix: build one side explicitly.
var ok_r as result of int to string is calling ok_of with 1
var err_r as result of int to string is calling err_of with "boom"
```

**`derive Donum` is rejected** with `E0005` ("`Donum` is automatic for rune
'X'; no 'derive' is needed"). `Donum` is *not* one of the derivable concepts;
the five remain `Par`, `Ordo`, `Vinculum`, `Imago` and `Nexus` (§11.6).

### 11.5 Iterating generics

Iteration needs a concrete element type. `list of T`, `slice of T`, arrays,
strings and maps all work inside generic code:

```pengu
weave count shard T where T: Par with xs as list of T into int:
    var n as int is 0
    for x in xs:                 # element type is T
        set n is n + 1
    return n
```

Iterating a *bare* type parameter (`xs as T` with `for x in xs`) is rejected
with `E0005`: the element type is unknown and the generated C could not index
the value. Use `list of T` / `slice of T`, or wait for associated types
(§11.7).

### 11.6 `derive` on generic types

`derive` works on generic declarations; the derived concepts become bounds on
the type parameters of the helper functions:

```pengu
rune Point shard T derive Par, Ordo:
    x as T
    y as T
```

`Point of int` and `Point of string` both get working `==`, `<`, … as long as
the substituted argument implements the concept (checked at the call site).

#### Which concepts are derivable

Exactly five, and each one produces something different:

| Concept | Derivable | What it produces |
|---|---|---|
| `Par` | ✅ | `==` / `!=` between values of the rune |
| `Ordo` | ✅ | `<` `<=` `>` `>=` |
| `Vinculum` | ✅ | a hash, so the rune works as a `map` key |
| `Imago` | ✅ | `_pengu_clone_<T>`, the C-level deep-copy helper |
| `Nexus` | ✅ | `_pengu_cleanup_<T>`, the destructor `banish` calls |
| `Forma` | ❌ | `E0005 Concept 'Forma' cannot be automatically derived` |
| `Iterabilis` | ❌ | `E0005` |
| `Donum` | ❌ (automatic) | never written in `derive`: implied when every field is defaultable (§11.4); `derive Donum` is `E0005` |

Three details that are easy to get wrong:

* **`Imago` does not add a `.clone()` method to the rune.** It emits the C
  callback; writing `a.clone` on a `derive Imago` rune is `E0004 Type 'T' has no
  method 'clone'`. `Imago` **implies `Nexus`** (a type that clones its elements
  must also be able to release them), so `derive Imago` alone emits *both*
  `_pengu_clone_T` and `_pengu_cleanup_T`.
* Deriving a comparison concept on a **generic** rune bounds the parameters, so
  the check happens at the substitution site, not at the declaration.
* **`Donum` is never derived.** A rune or echo gets it automatically when every
  field implements it (§11.4); `derive Donum` is `E0005`. A **generic** rune is
  defaultable only under a defaultable bound: write
  `rune Box shard T where T: Donum:` so that `donum (Box of T)` is accepted.
  Without the bound, `donum (Box of T)` is `E0049`; a concrete
  `donum (Box of int)` is still fine because `int` is defaultable.

### 11.7 Associated types (not implemented — ⏸️ deferred to 1.1)

Iterator-style concepts such as Rust's `Iterator` need an *associated type* so
generic code can name the element. The intended shape is:

```
concept Iterabilis shard Self:
    alias Item
    weave next with it as ref to Self into maybe Self.Item
```

**`alias Item` inside a `concept` is NOT accepted by the parser.** An earlier
revision of this section claimed the syntax "is accepted for forward
compatibility"; that was false. Writing it produces:

```
error[E0000]: Syntax error: unexpected 'alias'
```

because the `concept_method` production in `pengu_grammar.py` accepts only
`weave` signatures. Declaring an associated type, and resolving `Self.Item` to a
concrete C type during monomorphization, are both **deferred to 1.1** (see the
`⏸️ DIFERIDO` table in `ROADMAP_1.1.md`). Until then:

* use `list of T` / `slice of T` for generic iteration (§11.5);
* `for x in xs` over a bare `T: Iterabilis` is a compile error;
* there is no linked `Item` form, so such a concept must be written with a second
  type parameter (`shard Self and Item`) instead.

The sketch above is deliberately **not** marked as a ```pengu block: it is
documentation of the intended shape, not code that compiles.

`tests/test_audit_regressions.py::test_alias_in_concept_is_not_implemented` pins
the current behaviour so the feature cannot be reintroduced silently.

### 11.8 Related sections

* Generic methods and containers: §10.1.
* Concept definitions and `bind`: §10.2, §10.3.
* Built-in concept table: §10.9.
* Coherence rules for `bind`: §10.10.
* Derived concept implementations: §9.1.2.
* Container element semantics (`Imago`/`Nexus`): §13.5.

---

## 12. Optionals & errors

```pengu-fragment
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
    let u is user or return 0                     # value or early return
    let f is calling risky with 42 or:            # handle failure with a block
        calling spark.println with error
        return 1
    let f2 is try calling risky with 10           # propagate to caller
```

### Choosing between `maybe` and `result` (decision D5)

Both containers exist and neither replaces the other:

- **`maybe T`** answers *"is there a value?"*. Use it when the absence of a
  value is the whole story: lookups, optional fields, "find the first match".
- **`result of T to E`** answers *"what went wrong?"*. Use it when an operation
  can fail for several reasons and the caller may want to react differently:
  I/O, network, parsing, decoding.

Migration is additive, never breaking: `std.archivum` keeps `read_file` →
`maybe string` (and `write_file` → `bool`) exactly as before, and adds
`read_file_result`, `write_file_result` and `delete_file_result` returning
`result of T to IoError`, where `IoError` is an omen (`NotFound`,
`IsADirectory`, `NotAFile`, `Permission`, `Unknown`):

```pengu
import std.archivum

weave load with path as string into string:
    var r is calling archivum.read_file_result with path
    if r.is_ok:
        return r.value
    if r.error == archivum.IoError.NotFound:
        return "missing"                       # distinguishable from...
    if r.error == archivum.IoError.Permission:
        return "denied"                        # ...this, without FFI
    return calling archivum.describe_error with r.error
```

The rest of the standard library keeps `maybe`/`bool` until each module gets the
same additive treatment; the full migration is tracked as roadmap 4.4 and is
deliberately last because it touches public APIs.

### Semantics & Codegen Lowering:

- **Value Containers:** `maybe T` and `result of T to E` are represented in C as `PenguMaybe` and `PenguResult` structs. Present values are heap-allocated copies allocated via `pengu_sigil_alloc(sizeof(T))`.
- **Field Inspection:**
  - `maybe T`: exposes `.is_present` (`bool`) and `.value` (`T`, safe to access when `is_present` is true).
  - `result of T to E`: exposes `.is_ok` (`bool`), `.value` (`T`, safe when `is_ok` is true), and `.error` / `.err` (`E`, safe when `is_ok` is false).
- **`or else <expr>` (Lazy Fallback):** Evaluates `<expr>` only if the primary value is absent or an error. Emits a GNU statement-expression:
  ```c
  __extension__(({
    PenguMaybe _m = user;
    _m.is_present ? (*(string*)_m.value) : ("Guest");
  }))
  ```
- **`or return <expr>` (Early Return):** Checks presence/success. If absent or failed, it automatically runs all registered cleanup handlers (`defer`, `errdefer`) and returns `<expr>` from the enclosing weave.
- **`try <expr>` (Propagation):** Unwraps the value or immediately returns an empty/error result from the enclosing function:
  - Requires the enclosing function to return `maybe T` (for a `maybe` operand) or a compatible `result` type (`E0045: TypeMismatchError` if mismatched).
  - On failure, cleans up active scopes and executes `pengu_frame_pop(); return pengu_maybe_none();` (or returns the error result).
- **`or:` Blocks (Statement vs Expression):**
  - **As Target Initializer (`var x is f() or: ...`):** Emitted as clean C statements (`if (res.is_ok) { x = res.value; } else { ... }`).
  - **As Standalone Expression:** Emitted as a GNU statement-expression.
  - **Lexical `error` Scope:** Inside an `or:` block, the failure payload is bound to `error` (type `string` for `maybe T`, or error type `E` for `result`). Accessing `error` outside an `or:` block is a compile-time error (`E0015`). Once the block closes, `error` is removed from the scope.
- **Syntactic Positions (`list_value_expr` vs Arithmetic):**
  - **In Call Arguments & Struct Initializers:** `or else`, `or return`, and `or:` blocks are valid directly without parentheses in function/weave arguments (`calling f with a, b or else "default"`) and struct field initializers (`with name is get_name() or else "guest"`), because `list_value_expr` parses unwrap expressions directly.
  - **In Binary Arithmetic:** `or else` and `or return` bind with lower precedence than binary operators (`+`, `-`, `*`, `/`). When used as an operand in arithmetic, parentheses are required around the unwrap expression: `var total is 10 + (bonus or else 0)`. Writing `10 + bonus or else 0` groups as `(10 + bonus) or else 0`, which triggers a type mismatch error (`E0005`) when evaluating the binary addition.

> [!NOTE]
> For a module-level API over these operators, see the native helpers in `std.oracle` (`some_int`, `unwrap_int`, `unwrap_or_string`, …).

---

## 13. Manual Memory Management

> [!NOTE]
> For the low-level primitives (`alloc`, `alloc_array`, `resize_array`, `copy`,
> `fill`, `zero`, `swap`, `compare`, `bytes_for`), see `std.memoria` (§19.1).
> `banish`, `sigil of`, `essence of` and `size of` remain the language
> operators; `std.memoria` does **not** duplicate them (`free`, `sizeof` and
> `address_of` are deliberately absent).

PenguScript has no garbage collector, no borrow checker and no automatic release
at scope exit. Memory is managed by hand, like C, Zig, Odin and Nelua: **you
allocate, you release.** The compiler checks types; it does not track lifetimes,
with the single syntactic exception in §13.4.

```pengu
weave main into int:
    var s is "hello"
    defer banish s
    calling print with s
    return 0
```

Rules:
- `banish target` accepts a mutable lvalue of type `ref to T`, `string`, `list of T`, `map of K to V`, `maybe T`, `result of T to E`, or a rune with `derive Nexus`. An element access (`banish xs at 0`, `banish m at "k"`) is an lvalue too, and releases the owned element in place.
- `banish ptr` (where `ptr as ref to T`): emits `pengu_banish((void*)(ptr))` to release heap-allocated memory.
- `banish s` (where `s as string`): emits `pengu_banish_string(&s)`. When the string owns its buffer (`is_owned == 1`) this frees it, sets `s.data = NULL` and `s.len = 0`. String literals and other non-owning views carry `is_owned == 0`, so banishing them is a safe no-op. Do not access the string after banishing.
- `banish l` (where `l as list of T`): emits `pengu_banish_list(&l)`. Frees the list's own element buffer and resets length and capacity to 0. It does **not** release the elements (see §13.5).
- `banish m` (where `m as map of K to V`): emits `pengu_banish_map(&m)`. Frees the map's own entries table and per-entry key/value cells and resets length and capacity. It does **not** release heap buffers referenced by string keys or values (see §13.5).
- `banish d` (where `d` is a rune with `derive Nexus`): emits `_pengu_cleanup_D(&d)`, the destructor the rune opted into (§9.1.2).
- `banish m` (where `m as maybe T` / `result of T to E`): releases the payload the box owns and then the box itself. Nothing calls this implicitly; it is the lowering of the `banish` you wrote.
- `defer banish x` / `errdefer banish x` schedule the release instead of running it now: `defer` runs it at scope exit, `errdefer` only on an error return, both in LIFO order.
- `ref to T` is passed as a pointer: enables mutation from C and efficient `self` receivers.

Where heap values come from:
- `sigil of x` takes a raw address; `pengu_sigil_alloc` is the runtime allocator behind `some`.
- `some x`, `ok x`, `err x` box the payload in a `PenguMaybe`/`PenguResult` with `memcpy`. They do **not** clone a heap payload: the box holds a copy of the value, and if that value references a heap buffer, releasing the original stays your decision.
- Container constructors (`list of T`, `map of K to V`, `[...]`, map literals) allocate the container's own buffer; format `{expr}` and `(x to string)` allocate a fresh string buffer.
- `pengu_string_copy` and `pengu_banish_string` are the explicit copy/release pair for strings.

#### Why not ownership?

Rust infers when to free through its borrow checker; PenguScript does not. The
compiler refuses to guess, because a wrong guess is either a silent leak or a
use-after-free. Allocation and release are therefore explicit — a constructor or
`sigil of` to allocate, `banish` now or via `defer banish` to release — exactly
as in C, Zig, Odin and Nelua. When you want the release written for you, ask for
it per type with `derive Nexus`. The trade is deliberate: the compiler never
frees something you still need, and never keeps something you wanted gone.

#### Validation & Prohibitions (`_check_banish_stmt` & `banish_expr`):
- **Literals & Non-Lvalues (`E0008`):** Attempting to banish a literal (`banish "str"`, `banish 10`) raises `E0008: InvalidMemoryOpError`.
- **Temporary Expressions (`E0008`):** Expressions without an assignable memory location (calls, binary operators, unwraps) raise `E0008`. Assign the temporary to a variable first: `var tmp is f(); banish tmp`.
- **Nominal `seal` Types (`E0008`):** Strong newtypes cannot be banished directly even if their underlying type is a string or pointer. An explicit conversion is required: `banish (v to string)`.
- **`frozen` (Read-Only) Targets (`E0008`):** Banish modifies and deallocates target memory; banishing a `frozen` variable or value raises `E0008`.
- **Constants (`E0008`):** Constants cannot be banished.

### 13.1 Indexing through pointers and borrowing C buffers

A `ref to T` can be indexed directly, in reads and in writes, with the same `at` operator arrays use:

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

- Slices can be constructed over arbitrary C pointers using `std.ffi.slice_from_ptr`:
  `var sl as slice of Vector2 is calling ffi.slice_from_ptr of Vector2 with (sigil of pts), 4`.
- **Pointer arithmetic (`p + 1`) is deliberately unsupported.** Indexing (`p at i`), slices (`ffi.slice_from_ptr`), and `transmute` provide bounds-carrying or explicit alternatives.

### 13.2 Strict Pointer Typing & Interoperability

PenguScript enforces strict pointee typing for `ref to T` to prevent silent buffer-type mismatches. While numeric values allow widening (`int` → `i64`), pointers require identical pointees (or `void`/`opaque` wildcard).

| Source Pointer (`src`) | Destination Expected (`dst`) | Allowed? | Rule / Note |
|---|---|---|---|
| `ref to T` | `ref to T` | ✅ Yes | Exact pointee match (`_same_pointee`) |
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

### 13.3 C Buffer Lifetime & Cleanup Conventions

C bindings declare functions that return heap buffers allocated by underlying libraries (`malloc`, `strdup`, `mylib.stream_open`, `mylib_cache_open`, etc.):
1. **Binding Documentation:** The `##` docstrings specify the library's designated cleanup function.
2. **Library Cleanup vs Banish:** Memory allocated by an external C library must be released with that library's own cleanup routine (e.g. `defer calling mylib.release with handle`), **not** with `banish`. `banish` is reserved for memory managed by the PenguScript runtime (`pengu_sigil_alloc`, dynamic strings, lists, maps).

### 13.4 What Is Not Automatic

The compiler allocates and releases nothing on its own. In particular:

- **No release at scope exit.** A local goes out of scope when its block ends, but its heap buffer does not: only `defer banish x` / `errdefer banish x` schedule a release, and they run in LIFO order.
- **No stack/heap inference.** No pass decides whether a local lives on the stack or the heap; a value is wherever its declaration and type put it.
- **No deep copy on store.** `list.push` / `map.put` copy the element bytes with `memcpy` and never clone the payload; writing a `string` into a struct field or a container element is the same copy. The container does not take over releasing what the copy points at.
- **No implicit `Imago` / `Nexus`.** A rune gets a clone callback or a destructor only when it declares `derive Imago` / `derive Nexus` (§11.6). Nothing derives them from the fields.
- **No hidden boxing clone.** `some x`, `ok x` and `err x` store a `memcpy` of the payload in a `PenguMaybe`/`PenguResult`; they do not duplicate a heap buffer it references.
- **Two owning temporaries have no name to banish.** Both follow from the rule above and must be handled by binding the value to a local:
  - an interpolated literal passed *directly* to a call — `calling println with "{x}"` — allocates a fresh `string` (LANGUAGE.md §15.2) that no binding names, so it leaks. Bind it first: `let msg as string is "{x}"`, then `banish msg` when done. The same applies to `(x to string)`, `s.substring`, `s.char_at`, `s.trim` and every other owned-string producer used as an argument.
  - `for ch in s` binds `ch` to a **fresh owned one-byte `string` per iteration** (a `pengu_string_char_at` result, not a view). If the body neither stores nor `banish ch`es it, it leaks; `banish ch` at the end of the body releases it, and a `return`/`break` leaves the current `ch` to be released before leaving. Iterate bytes without allocating with a `ref to byte` index loop (`bytes of s`) when the character is only inspected.
  
  `banish` rejects a non-lvalue (`E0008`), so neither temporary can be released in place; binding it is the only spelling that works.

The runtime helpers that made the old automatic model possible — `PenguElemCleanup`, `PenguElemClone`, `pengu_list_new_owned`, `pengu_map_new_owned`, `pengu_list_cleanup`, `pengu_list_clone`, `pengu_map_cleanup`, `pengu_map_clone`, `pengu_string_cleanup` and `pengu_string_clone` — no longer exist. `pengu_string_copy` and `pengu_banish_string` remain.

#### The one lifetime rule the compiler enforces

Returning a `slice of` a **stack** array is rejected with `E0051`, because the
array's storage dies when the weave returns and the slice would dangle:

```pengu-fragment
weave bad into slice of int:
    var xs as array of int with size 4 is [1, 2, 3, 4]
    return xs at 0 to 2       # E0051: the slice would dangle
```

Copy the array into a `list of T` (heap) before slicing, or return the array by
value. Module-level arrays are static storage and are allowed.

#### Runtime Heap Functions Summary:

| Function | Signature / Operation | Behavior | Release semantics |
|----------|-----------------------|----------|-------------------|
| `pengu_sigil_alloc` | `void* pengu_sigil_alloc(size_t sz)` | Allocates zero-initialized heap memory for `some` optionals. | The caller must `banish` the returned pointer. |
| `pengu_string_new` | `PenguString pengu_string_new(const char *s, int len)` | Allocates an owned string buffer on the heap. | The caller must `banish` the returned `PenguString.data`. |
| `pengu_string_from_cstr` | `PenguString pengu_string_from_cstr(const char *s)` | Creates a non-owning view over a C string (`is_owned == 0`). | Non-owning; `banish` is a no-op. |
| `pengu_string_format_ex` | `PenguString pengu_string_format_ex(const char *fmt, ...)` | Byte-exact `"{expr}"` formatter: `%.*s` copies `len` bytes (NULs included). | Allocates a new buffer; the caller must `banish` it. |
| `pengu_string_concat` | `PenguString pengu_string_concat(PenguString a, PenguString b)` | Allocates and returns concatenated string. | Allocates a new buffer; the caller must `banish` it. Inputs `a`, `b` unchanged. |
| `pengu_string_equal` | `bool pengu_string_equal(PenguString a, PenguString b)` | Compares byte content and length for equality. | Non-allocating; inputs passed by value. |
| `pengu_to_string` | `pengu_to_string(x)` | Generic macro converting primitive `x` to `PenguString`. | Returns an owned heap string for formatted values, or a non-owning view. |
| `pengu_string_format` | `PenguString pengu_string_format(const char *fmt, ...)` | Allocates formatted string via `vsnprintf`. | The caller must `banish` the returned `PenguString.data`. |
| `pengu_string_copy` | `PenguString pengu_string_copy(PenguString s)` | Allocates an independent copy of `s`. | The caller must `banish` the copy. |
| `pengu_banish_string`| `void pengu_banish_string(PenguString *s)` | Frees the heap buffer when `is_owned`, then nullifies data/len/is_owned. | Safe no-op on a non-owning view. |
| `pengu_banish_list`  | `void pengu_banish_list(PenguList *l)` | Frees the list's element buffer and resets length/capacity. | Does not touch the elements. |
| `pengu_banish_string_list` | `void pengu_banish_string_list(PenguList *l)` | Banishes each `PenguString` element, then the list. | The opt-in helper for `list of string`. |
| `pengu_banish_map`   | `void pengu_banish_map(PenguMap *m)` | Frees the map's entries table and per-entry key/value cells. | Does not release heap buffers referenced by keys/values. |
| `pengu_banish`       | `void pengu_banish(void *ptr)` | Calls standard heap `free(ptr)`. | Releases a raw pointer allocation. |

### 13.5 Containers: `memcpy` on Store, Explicit Release

`PenguList` and `PenguMap` store element bytes; they never clone and never
recursively release. The runtime ABI is **v2** (`PENGU_ABI_VERSION == 2`):

```c
typedef struct {
    void *data; int len; int cap; size_t elem_size;   /* 24 bytes */
} PenguList;

typedef struct {
    PenguMapEntry *entries; int len; int cap;
    size_t key_size, val_size;                        /* 32 bytes */
} PenguMap;
```

* `pengu_list_push` / `pengu_map_put` copy `elem_size` (or `key_size` /
  `val_size`) bytes with `memcpy`. There are no `elem_cleanup` / `elem_clone`
  callbacks: the v1 fields and `pengu_list_new_owned` / `pengu_map_new_owned`
  are gone.
* `pengu_banish_list` frees the element buffer and nothing else;
  `pengu_banish_map` frees the entries table and the per-entry key/value cells.
  Neither recurses into the elements.
* **Invariant:** `elem_size` / `key_size` / `val_size` are immutable once the
  container exists — changing the stride would desynchronise it from the slots
  already stored. Mutate elements in place instead of re-typing a container.
* FFI helpers `pengu_list_of_string_from_cstrs(arr, count)` and
  `pengu_list_of_string_from_cstrv(arr)` build a `list of string` from a C array,
  copying each string; the list owns its element buffer but each `PenguString`
  owns its own bytes, so use `pengu_banish_string_list` to release both.

Because store copies bytes, the container and the source are separate values —
but if the element references a heap buffer, both now reference the same buffer,
and releasing it exactly once is your responsibility:

```pengu
weave main into int:
    var rows as list of list of string is list of list of string
    var row as list of string is ["a", "b"]     # row owns its element buffer
    calling rows.push with row                  # memcpy of the PenguList struct
    # 'rows at 0' and 'row' now alias the same buffer:
    banish row                                  # free it once, through either name
    banish rows                                 # frees only rows' own buffer
    return 0
```

For a raw heap block, `std.memoria` is the canonical allocator; `banish`
remains the release operator:

```pengu
import std.memoria

weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 16
    defer banish buf
    calling memoria.zero of int with buf, 16
    return 0
```

A rune with heap fields gets a destructor only if it asks for one. `derive
Nexus` emits `_pengu_cleanup_D`, and `banish d` calls it:

```pengu
rune Doc derive Par, Nexus:
    title as string
    tags as list of string

weave main into int:
    var d as Doc with:
        set .title is "spec!"
        set .tags is ["a", "b"]
    defer banish d          # -> _pengu_cleanup_Doc(&d) at scope exit
    return 0
```

---

## 14. Modules, imports & C interop

### 14.1 Imports & modules

```pengu-fragment
import std.spark
import std.scrolls as s              # alias
import components.player             # project module (src/components/player.pengu)
```

#### Resolution, Dependency Ordering & Import Rules:
- **Module Resolution:** Dotted paths map directly to file paths relative to `src/` or configured roots (`components.player` -> `src/components/player.pengu` or `player.d.pengu`). Standard library modules (`std.*`) resolve to the bundled compiler standard library.
- **Topological Sorting (`import_order`):** `resolve_imports` (`pengu_symbols.py`) visits modules recursively, computing a topological sort order (reverse post-order) so that dependencies are type-checked and emitted in C before their dependents.
- **Circular Dependency Detection (`E0004`):** Dependency resolution uses a three-color DFS traversal (`visited` / `visiting`). If an active module is revisited, a circular import cycle is detected and raises `SemanticError` (`E0004`), displaying the full cycle path (e.g. `a.pengu -> b.pengu -> a.pengu`).
- **Duplicate Imports (`E0004`):** Importing the same module multiple times in the same file raises `E0004: Duplicate import of module '...'`.
- **Import Alias Restrictions (`E0036`):**
  - **Discard Alias Forbidden:** Binding an import to `_` (`import std.math as _`) raises `E0036: Import alias cannot be '_' (discard)`.
  - **Local Symbol Conflicts:** An alias colliding with an existing local symbol in the current module raises `E0036`.
- **Encapsulation (`E0043`):** Top-level symbols starting with `_` are module-private and cannot be accessed from importing modules (`E0043: PrivateSymbolAccessError`).

### 14.2 `include`, `link`, `insignia`, `declare`

```pengu
include "mylib.h"
link "mylib"
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
in a `.d.pengu` (`omen Options:` + `MODE_FAST is 1`) are reachable in three
ways, and the first two are the ones to use:

```pengu-fragment
import mylib

calling mylib.is_enabled with mylib.MODE_FAST                 # bare module-qualified ✅
calling mylib.is_enabled with mylib.Options.MODE_FAST         # nested: type-qualified ✅
calling mylib.is_enabled with MODE_FAST                       # unqualified ✅
calling mylib.set_option with mylib.FLAG_VERBOSE              # qualified #define / variant ✅
```

All three forms are supported: bare module-qualified (`mylib.MODE_FAST`, `mylib.FLAG_VERBOSE`), type-qualified (`mylib.Options.MODE_FAST`), and unqualified (`MODE_FAST`). Struct-valued constants such as `mylib.DEFAULT_CONFIG` are also supported (their value is emitted as defined).


### 14.3 `ref to char`, `opaque`, `.d.pengu`, and `bytes of`

C strings: pass `ref to char` parameters; PenguScript string literals convert
automatically to C string pointers where a `ref to char` is expected. Use
`bytes of s` for byte views, `std.ffi.string_from_cstr` / `cstr_from_string`
for explicit round trips (who releases the result is documented in the
module). Opaque handles are declared `alias X as opaque` and handled through
`ref to X`.

`.d.pengu` **declaration files**:

```pengu
# mylib.d.pengu (excerpt)
rune mylib:
    _ptr as opaque

declare mylib_open with filename as ref to char, ppDb as ref to opaque into int
```

- They register types/signatures only; implementations live in the C header.
- An `omen` declared in a `.d.pengu` mirrors a header enum, so emitted C uses
  the **bare** variant names (`MODE_FAST`, not `Options_MODE_FAST`).

### 14.4 Project structure & configuration (`pengu.yaml` / `pengu.toml`)

PenguScript projects are configured via `pengu.yaml` or `pengu.toml` located at the project root. If both files exist, `pengu.toml` takes precedence.

#### Complete `pengu.yaml` Schema:

```yaml
name: my_app
version: 2.0.0
output: exe                  # exe | c | obj | static | shared
entry: src/main.pengu        # main entry module (defaults to src/main.pengu)
src_dirs: [src]              # source lookup roots (default: [src])
include_dirs: [include]      # additional C header search paths (-I)
lib_dirs: [lib]              # additional library search paths (-L)
links: [m, pthread]          # static / dynamic libraries to link (-l)
ldflags: []                  # raw linker flags
cflags: []                   # raw C compiler flags
defines: [ENABLE_LOGS]       # preprocessor macros (-D)
cc: gcc                      # default C compiler (gcc, clang)

profiles:
  debug:
    cflags: ["-g", "-O0"]
    defines: ["DEBUG=1"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: []

assets:
  dir: "assets"              # directory relative to project root
  module: "arca"             # generated PenguScript module name (src/arca.pengu)
  embed: true                # true = embedded in .rodata; false = runtime disk reader
  exclude: ["*.tmp", "*.bak"]

dependencies:
  - name: my_c_lib
    git: "https://github.com/example/my_c_lib.git"
    build: "make"
```

#### Project Directory Layout & Build Artifacts:
- **`c/` Directory for Glue Code:** Any `.c` or `.h` files placed in `./c/` are automatically included, compiled, and linked into the final executable alongside `bundle.c`.
- **`lib/<binding>/pengu/`:** Standard directory layout for external PenguScript package bindings.
- **Generated Build Directory (`build/`):**
  - `build/bundle.c`: The unified C translation unit emitted by the code generator.
  - `build/arca_assets.c`: The embedded binary asset data table generated when `assets.embed` is enabled.
  - `build/lib/*.a`: Precompiled static archives for the PenguScript runtime (`libpengu_runtime.a`) and bundled C libraries.
  - `build/include/`: Header files for bundled third-party C libraries.

### 14.5 Module state patterns (singletons & services)

Top-level `var` and `let` declarations are strictly forbidden by design (`E0002`). All module-level symbols must be compile-time constants (`const`).

When creating stateful services, singletons, or tracking state across calls, use one of two idiomatic patterns:

#### Pattern A: Encapsulated State via `static var` Accessor Weaves
State is contained inside accessor functions using `static var`. A `static var` maintains its value across repeated calls:

```pengu
# score_tracker.pengu
weave add_score with delta as int into int:
    static var score as int is 0
    set score is score + delta
    return score

weave get_score into int:
    return calling add_score with 0
```

**Codegen Initialization Strategy:**
- For compile-time constant scalars (`int`, `float`, `bool`), the codegen emits a simple static C initializer: `static int32_t score = 0;`.
- For complex, dynamic, or heap-allocated initializers, the codegen emits a static guard boolean:
  ```c
  static MyStruct ctx;
  static bool ctx_initialized = false;
  if (!ctx_initialized) {
      ctx = ...;
      ctx_initialized = true;
  }
  ```

**`static var` Rules & Validation (`_check_static_var_decl`):**
- **Direct Weave Child Only (`E0035` / `E0002`):** `static var` must be declared directly inside a `weave` body. Placing it at module top-level raises `E0002`; nesting it inside control-flow blocks (`if`, `while`, `for`, `do:`, `or:`) raises `E0035`.
- **Reserved Identifier `main` (`E0040`):** Cannot be named `main`.
- **Arrays Prohibited (`E0035`):** Static variables cannot have an array type (`array of T with size N`). Because C arrays cannot be reassigned at runtime, array statics are rejected. Use a pointer (`ref to T`), a rune wrapper, or a `list of T` instead.
- **Explicit Null Typing (`E0014`):** Initializing a static variable with `null` requires an explicit type annotation (e.g. `static var buf as ref to byte is null`; untyped `static var buf is null` raises `E0014`).

#### Pattern B: Explicit Context Struct (`ref to Context`)
A reentrant, thread-safe pattern where the module defines a state `rune` and functions receive a reference:

```pengu
rune AudioContext:
    volume as float
    is_muted as bool

weave init into AudioContext:
    return with volume is 1.0, is_muted is false

weave set_volume with ctx as ref to AudioContext, vol as float into void:
    set ctx->volume is vol
```

---

## 15. Literals: strings, arrays, maps, indent blocks & ranges

### 15.1 Numbers, characters, booleans, null

```pengu-fragment
42  -7  0xFF  0b101  1_000        # integers
1.5  -0.25  2e3                    # floats
'A'  '\n'  '\x41'                  # characters
true  false  null
```

- **`null`:** The literal `null` represents a null pointer. It requires an expected pointer type context (`var p as ref to int is null`). Standalone `null` declarations without type annotations raise `E0014: TypeMismatchError`.

### 15.2 Strings

```pengu-fragment
let a as string is "plain"
let b as string is "value: {x} and {name}"      # interpolation → pengu_string_format
let c as string is r"raw \n no escapes"          # raw single-line
let d as string is """triple
   quoted   string"""                            # dedented multiline
let e as string is r"""raw triple"""             # raw + multiline
```

- **Interpolation (`{expr}`) is *the* string-composition operator.** It emits `pengu_string_format` using type-specific format specifiers:
  - `%c` for `char` and `byte`
  - `%d` for signed and unsigned integers (`int`, `i8`..`i64`, `u8`..`u64`)
  - `%f` for floating-point numbers (`float`, `f32`, `f64`)
  - `%s` for `bool` (`"true"` / `"false"`)
  - `%.*s` for `string` (passing `.len` and `.data`)
  - `%s` for C string pointers (`ref to char`)
  Passing unsupported complex types (e.g. runes) without conversion raises a compiler error.
- **Byte-exact composition:** an interpolated `string` argument is copied using its
  length, not `printf`'s NUL-terminated `%s` rule. `"a{nul}b"` therefore keeps the
  embedded `\0` and is 3 characters long — binary payloads (hash digests,
  Base64/hex decoders) survive composition. **Floats format identically on every
  path** — interpolation, `to string` and the `print` builtin all use `%g`, so
  `"{0.5}"`, `(0.5 to string)` and `print 0.5` all produce `"0.5"`. Formatting is
  compact rather than fixed-precision: `1.0/3.0` gives `0.333333`, not
  `0.3333333333333333`. Use an explicit conversion when the textual form matters.
- **Quotes inside `{expr}`:** the interpolated expression may contain a
  double-quoted literal (`"v={(calling getenv_or with k, "")}"`). Expressions with
  unbalanced braces are not supported inside a literal; build them in a local.
- **Why `+` is not a string operator:** `"a" + b` raises `E0005`. There is exactly one way to build a dynamic string, so there is no ambiguity between `+` on numbers and `+` on text, no implicit `to string` promotion, and no extra hidden allocation on every concatenation. Convert explicitly when you need it (`"{b}"` or `b to string`), and accumulate with interpolation:

  ```pengu
  # instead of:  "Hello, " + name
  let greeting as string is "Hello, {name}"

  # instead of:  set acc += item
  set acc is "{acc}{item}"      # O(n²) in a loop: prefer a 'list of string' + join
  ```

- **Triple-Quoted Strings (`"""..."""`):** Strips common leading indentation automatically.
- **Raw Strings (`r"..."` and `r"""..."""`):** Treat backslashes, escape sequences, and curly braces literally without interpolation. Essential for GLSL/HLSL shaders, regex patterns, and embedded templates.

### 15.3 Arrays, lists, slices, maps

```pengu-fragment
const MAX as int is 3
let nums as array of int with size MAX is [10, 20, 30]   # size by const name
let dyn as list of int is list of int                    # growable PenguList
let sl as slice of int is nums at 1 to 3                 # non-owning view
let m as map of string to int is map of string to int
```

- **Array Size by Constant Identifier:** Fixed arrays support sizing via constant names (`array of T with size NAME`), where `NAME` is resolved from the symbol table during semantic checking (`ast_to_type`).
- **Bracket Literals (`[1, 2, 3]`):** Produce fixed stack arrays. Element types must be mutually compatible (`E0005`).
- **Multidimensional Arrays:** Declared outer-dimension first:
  ```pengu
  var grid as array of array of f32 with size 2 with size 3 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
  ```
  Emits `float grid[2][3]`. The inner dimension can be omitted if inferred from rows. Rows must have identical lengths (`E0041: ArraySizeMismatchError`).
- **Map Iteration Order:** Iterating over a map visits slots in internal hash table order, not insertion order.

### 15.4 Indentation literals

Arrays, maps, and struct literals can be declared using clean, block-indented syntax:

```pengu-fragment
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

### 15.5 Ranges & membership

```pengu-fragment
1 to 10         # PenguRange [1, 10), end-exclusive — this is the canonical form
for i in 1 to 5: ...
if x in 0 to 100: ...
```

- **Canonical syntax: `a to b`.** The older `a..b` spelling still works through
  1.x but is deprecated and **removed in 2.0**; using it emits `W0013`
  (`RangeSyntaxDeprecated`) and `pengu fmt` rewrites it. Write `a to b` in new
  code and migrate existing code with `pengu fmt`.
- Ranges are half-open (`[start, end)`).
- **Compile-Time Range Validation (`E0042`):** When start and end are known at compile time, `start <= end` is enforced for positive ranges. If `start > end` without a negative step, the compiler raises `E0042: InvalidRangeError`.

---

## 16. Conditional compilation (`when`)

PenguScript evaluates `when` blocks strictly at compile time before semantic checking and C code generation. Inactive branches are pruned entirely from the AST and emit no C.

### Three Forms of `when`:

#### 1. Top-Level Declarations (`when_top_decl`)
Conditionally include or exclude functions, types, constants, or bindings. Supports chained `else when` branches and a fallback `else:`:

```pengu
when os == "windows":
    include "windows.h"
    declare Sleep with dwMilliseconds as u32 into void
else when os == "linux":
    include "unistd.h"
    declare usleep with usec as u32 into int
else:
    declare dummy_sleep into void
```

`when_top_decl` branches are evaluated at compile time via `_active_when_top_stmts`. Only statements in the active branch are registered in the symbol table and type-checked; inactive branches are pruned before semantic analysis.

#### 2. Statement Blocks & Chains (`when_stmt`)
Compile-time branching inside function bodies, supporting `else when` chains and final `else:`:

```pengu-fragment
weave sleep_ms with ms as int into void:
    when os == "windows":
        calling Sleep with (ms to u32)
    else when os == "linux" or os == "macos":
        calling usleep with ((ms * 1000) to u32)
    else:
        calling spark.println with "Unsupported OS"
```

#### 3. Expression Form (`when_expr`)
Compile-time ternary expression:

```pengu-fragment
let buffer_size as int is when arch == "x64" then 8192 else 4096
```

### Comptime Variables & Intrinsics:
- **`defined(NAME)`:** Evaluates to `true` if identifier `NAME` was provided via `-D NAME` or exists in the predefined compiler environment. `defined(wasm)` is also true whenever the target is WebAssembly (see below).
- **`main`:** `bool`. Evaluates to `true` **only** for the project entry-point module (`compile_env.is_main`). When the `-D main` or `-D main=true` CLI flag is passed (e.g. `pengu build -D main` or `pengu run main.pengu -D main`), `main_flag_requested` enables entry-main semantics exclusively for the entry module; imported secondary modules always compile with `is_main = false`, preventing conflicting entry points.
- **`debug`:** `bool`, `true` when compiling with the `debug` profile or `-D debug`; `false` under `--profile release`.
- **`os`:** String constant matching the host operating system (`'windows'`, `'linux'`, `'macos'`, `'freebsd'`). Note that `--target` does **not** change it — a `wasm32-unknown-emscripten` build still sees the host's `os` unless `-D os=emscripten` is passed. Use `wasm` / `wasm_target` below for the WebAssembly target.
- **`arch`:** String constant matching target CPU architecture (`'x64'` / `'x86_64'`, `'arm64'`, `'x86'`).
- **`compiler`:** String constant matching the target C compiler (`'gcc'`, `'clang'`, `'msvc'`, `'tcc'`). A `wasm32-unknown-emscripten` target reports `'emcc'` — the driver that will actually run, whether it was configured or auto-detected — so `when compiler == "emcc":` is reliable. `-D compiler=...` always wins.
- **`wasm`:** `bool`, `true` when the build target is WebAssembly — i.e. `os` is `'emscripten'` or `'wasi'`, which `--target wasm32-unknown-emscripten` (or `--target wasm`) selects. `false` for every native build. `-D wasm` forces it true, and the two spellings agree: `when wasm:` and `when defined(wasm):` always answer alike.
- **`wasm_target`:** `string`. The WebAssembly target's OS name — `'emscripten'` or `'wasi'` — and the **empty string** for a native build. Use it to distinguish the two:

  ```pengu
  when wasm_target == "emscripten":
      include "emscripten.h"
      declare emscripten_get_now into f64
  when not wasm:
      weave now_ms into f64:
          return 0.0
  ```

  Both variables resolve before code generation, so the inactive branch leaves no trace in `bundle.c`. `std.web` is built on exactly this mechanism; see [`docs/WASM.md`](docs/WASM.md).
- Non-constant conditions in `when` constructs raise `E0039: SemanticError`.

---

## 17. Unit tests (`test`)

PenguScript features first-class unit testing support built directly into the language and toolchain.

```pengu-fragment
test "arithmetic":
    calling expect_eq_int with 1 + 1, 2

test string_formatting:
    calling expect_eq_string with "abc", "abc"
```

- **Definition:** Test blocks are declared with `test <name>:`, where `<name>` can be a string literal or an identifier.
- **Semantic Validation:** Test bodies are semantically validated and type-checked across **all** compilation modes (`pengu check`, `pengu build`, `pengu run`, `pengu test`) via `_check_test_decl`. Syntax and type errors inside test blocks surface immediately even during regular builds.
- **C Codegen Isolation:** C test harnesses, test runner weaves, and test execution calls are emitted only when compiling under `--test` mode (`pengu test`). Production executables and library builds omit test code entirely.
- **Declarations:** `test` blocks inside `.d.pengu` declaration files are strictly forbidden (`E0025`).

### Running Tests

```console
$ pengu test              # Compile and execute all test blocks in project
$ pengu test --watch      # Watch mode: monitor .pengu sources and rerun on change
$ pengu test --json       # Machine-readable JSON Lines (JSONL) events for CI
```

- **Watch Mode (`--watch`):** Continuously polls project source files (`mtime`), clearing the terminal and rerunning tests upon change.
- **CI Output (`--json`):** Emits structured JSON Lines events to stdout (`start`, `test_start`, `test_pass`, `end`), keeping stderr clean.

---

## 18. Block-style construction (`with:` expressions)

For complex struct construction and in-place mutation, PenguScript provides `with:` builder blocks. A `with:` block allocates a zeroed temporary and evaluates to the resulting struct value:

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
        calling .shift with 5, 3     # call enchanting method on temporary
    return p.x + p.y                 # 38
```

### Builder Rules & Validation (`E0014`):
- **Allowed Statements:** Only `set .field is expr` assignments and method calls on the target (`calling .method with ...` or normal calls) are permitted inside builder blocks.
- **Forbidden Statements:** Control flow statements (`if`, `while`, `for`, `return`, `break`, `continue`), variable declarations (`var`, `let`), and memory management (`defer`, `banish`) are strictly rejected with `E0014: InvalidBuilderStatementError`.
- **Target Mutability Rules:**
  - `var x with:` or `with var_target:`: mutable, fields can be modified.
  - `let x with:` (rune value): immutable binding after construction.
  - `with let_val:`: attempting to mutate an existing immutable `let` rune raises `E0006: MutabilityError`.
  - `with let_ptr:` (where `let_ptr as ref to T`): mutable, because a `ref to T` points to mutable memory.
  - `frozen T` or `ref to frozen T`: immutable; field modification raises `E0006`.
- **Codegen Statement-Expression Lowering:**
  ```c
  __extension__(({
    Point _with_1 = {0};
    _with_1.x = 10;
    _with_1.y = 20;
    Point_shift(&_with_1, 5, 3);
    _with_1;
  }))
  ```

### Nesting `with:` blocks

A `with:` builder can be nested at any depth. Inner builders infer their target types from the fields they are assigned to, requiring no redundant type annotations:

```pengu
rune Address:
    street as string
    city as string
    zip as string

rune Person:
    name as string
    age as int
    address as Address

weave build into Person:
    return with:                       # target type inferred from weave return type
        set .name is "Ada"
        set .age is 30
        set .address is with:          # target type inferred as Address
            set .street is "123 Main St"
            set .city is "New York"
            set .zip is "12345"

weave rename into void:
    var p as Person with:
        set .name is "Ada"
        set .age is 30
        set .address is with:
            set .street is "1 First Ave"
            set .city is "Springfield"
            set .zip is "00001"

    with p:                            # edit the existing rune
        set .name is "Grace"
        set .address is with:          # nested builder, same inference rules
            set .street is "2 Second Ave"
            set .city is "Shelbyville"
            set .zip is "00002"
```

Rules and guarantees:

- The inner builder inherits its target type from the field it is assigned to
  (`Person.address` in the example above). No extra annotation is required.
- Nesting works at any depth; each level allocates its own implicit C
  temporary (`_with_N`), so inner and outer builders never collide.
- `set .field is <block>` accepts any value block (see §7.6), including nested
  `with:` builders, value-position `if`/`unless`, `do:` blocks and value-
  position loops.
- Type checking is unchanged: a wrong field name (`E0013`-style), a missing
  field, or a type mismatch inside a nested builder still raises the same
  diagnostic it would raise at the top level.
- The generated C is a GNU statement-expression per builder
  (`({ Person _with_N = {0}; …; _with_N; })`), so nesting lowers naturally.

The `with:` builder is also the iteration value inside a value-position loop
(§7.6), which lets you build collections of composite runes without repeating
the target type:

```pengu-fragment
var ps as list of Person is for i from 0 to 3:
    with:                              # element type comes from 'list of Person'
        set .name is "p"
        set .age is i
        set .address is with:
            set .street is "s"
            set .city is "c"
            set .zip is "z"
```

The one-line `with x is …, y is …` struct literal is unchanged, and each
field value may itself be a block value (a multi-line block must be the last
field, or the following `,` must start a new line) —
see [§7.6](#76-block-expressions-do-value-position-if--unless-and-loops).

> [!NOTE]
> Block members are written with the implicit `.` (`set .x is 10`), consistent
> with `with target:` scopes. `set x is 10` inside the block would assign a
> *local variable* named `x`, which normally does not exist.
>
> A builder block is itself a value, so it can appear as a field initializer
> (nesting, above), as a loop iteration value, as a branch of a value-position
> `if`/`unless`, and as a `do:` block tail. It is **not** a general expression:
> it cannot sit inside a call argument list or as an arithmetic operand — see the
> position table below. The `as T` annotation on `var`/`let`/`static var` is only
> needed at the outermost level; inner builders infer their type from the field
> they are assigned to.

### `with:` in value positions (verified)

A `with:` builder needs a **target type** before it can be checked. The table
says where the compiler can supply one and where it cannot; every ✅ row was
verified by compiling the example with `pengu check`.

| Position | Valid? | Notes |
|---|---|---|
| `var`/`let`/`static var` initializer with an annotation | ✅ | type inferred from the annotation (`as T`) |
| `var`/`let` initializer without an annotation | ❌ | `E0014`: a builder cannot infer from the enclosing `into`; use `return with:` (next row) |
| `return with:` | ✅ | target type comes from the weave's `into` |
| `set .field is with:` and `set x is with:` | ✅ | nested builder infers from the field; `set x is with:` reuses the local's declared type |
| `with:` as the iteration value of a loop | ✅ | element type from the annotated `list of T`; one element per iteration |
| `with:` in a value-position `if`/`unless` branch | ✅ | branch type from the expected slot; every branch must agree |
| `with:` as the tail of a `do:` block | ✅ | `do:` yields the builder |
| `with:` as a call argument | ❌ | `calling f with (with: …)` is `E0000`; the bare form is `E0014`. Pass a named value, or the one-line `with x is …` literal |
| `with:` as the last field of an enclosing `with:` | ✅ | nested builder; the last field may be any block value |
| Multiline `with:` whose last field is itself a block value | ✅ | e.g. a value-position `if`/`unless` or a nested `with:` as the last field |
| `with:` as an arithmetic operand | ❌ | bare is `E0014`; even `(with: …).x` is `E0000`. Assign the builder to a typed variable first |

The annotation/expected type is what the builder uses; there is no inference
from field assignments alone:

```pengu-fragment
var p as Point with:              # 1: the annotation supplies Point
    set .x is 1
    set .y is 2

let q as Point with:              # 1: 'let' works the same way
    set .x is 3
    set .y is 4

weave build into Point:
    return with:                  # 3: 'into Point' supplies the target type
        set .x is 5
        set .y is 6

set p is with:                    # 4: reuses the declared type of 'p'
    set .x is 7
    set .y is 8

var seg as Segment with:
    set .start is with:           # 4: nested builder infers Point from the field
        set .x is 0
        set .y is 0
    set .end_pt is with:
        set .x is 1
        set .y is 1
```

```pengu-fragment
var ps as list of Point is for i from 0 to 3:
    with:                         # 5: one Point per iteration
        set .x is i
        set .y is i * 2

var p as Point is if flag:        # 6: value-position branch
    with:
        set .x is 1
        set .y is 2
else:
    with:
        set .x is 3
        set .y is 4

var q as Point is do:             # 7: 'do:' yields its tail
    var seed as int is 10
    with:
        set .x is seed
        set .y is seed + 1
```

```pengu-fragment
var s as Segment with:
    set .start is with:           # 9: first field is an enclosing-builder field
        set .x is 0
        set .y is 0
    set .end_pt is if flag:       # 10: last field is itself a block value
        with:
            set .x is 3
            set .y is 4
    else:
        with:
            set .x is 5
            set .y is 6
```

A call argument must be a named value or a one-line struct literal — a block
builder is not accepted in either parenthesised or bare form:

```pengu-fragment
calling show with p                       # ✅ named value
calling show with with x is 1, y is 2     # ✅ one-line struct literal
```

```pengu-invalid
calling show with (with:          # E0000: '(' cannot open a builder block
    set .x is 1
    set .y is 2)

calling show with with:           # E0014: no target type reaches the argument
    set .x is 1
    set .y is 2

var n as int is 1 + with:         # E0014: not an arithmetic operand
    set .x is 1
    set .y is 2
```

### 18.2 `with` scopes on collections (`list` and `map`)

The `with` statement also operates directly on existing collections (`list of T` and `map of K to V`, or references to them `ref to list of T` / `ref to map of K to V`). Inside the block, leading-dot method calls invoke the collection's built-in methods without repeating the collection variable name:

```pengu-fragment
var scores as list of int is list of int
with scores:
    calling .push with 10
    calling .push with 20
    calling .push with 30

var registry as map of string to int is map of string to int
with registry:
    calling .put with "alpha", 1
    calling .put with "beta", 2
```

Supported built-in methods inside collection `with` blocks:
- **`list`:** `.push(item)`, `.append(item)`, `.pop()`, `.clear()`, `.contains(item)`, `.index_of(item)`, `.at(idx)`, `.len()`, `.is_empty()`
- **`map`:** `.put(key, val)`, `.insert(key, val)`, `.set(key, val)`, `.get(key)`, `.remove(key)`, `.contains(key)`, `.len()`, `.is_empty()`, `.clear()`

---

## 19. Standard library

PenguScript ships with **38 standard-library modules** (`std.<module>`), providing high-level, idiomatic abstractions for I/O,
strings, concurrency, serialization, math, testing, and memory bridging.

Bindings to external C libraries are no longer part of `std/`: they are distributed
as satellite repositories installed per project with `pengu add <url>` (§19.2).

### Builtin `print`
`print` is a compiler builtin that lowers directly to `printf` according to the argument type (`print "hello"`, `print 42`, etc.). For structured or formatted printing with broader options, use `std.spark.println` or `std.spark.print`.

### 19.0 Standard-library versioning policy

The standard library ships **coupled to the compiler** in the 1.x series (decision
D6): a program compiled with PenguScript 1.4 uses the `std/` that shipped with
1.4, and there is no separate stdlib version to resolve. Each pure module exports
a `<MODULE>_VERSION` constant (e.g. `std.ffi` → `FFI_VERSION`, `std.archivum` →
`ARCHIVUM_VERSION`, `std.loom` → `LOOM_VERSION`, `std.functor` →
`FUNCTOR_VERSION`) holding the release that last changed that module, so code
can assert the library it was built against:

```pengu
import std.archivum

test "stdlib version":
    if archivum.ARCHIVUM_VERSION == "":
        assert false
```

`tests/stdlib/test_std_versioning.py` enforces that every hand-written `std/`
module exports that constant with a valid release version (optionally with a
semver prerelease suffix). Because the standard library is coupled to the
compiler, the constant names the **stdlib release it ships with**, not the last
release that happened to edit that file: every module of 2.11.0 reports
`"2.11.0"` (except `std.spark`, whose `SPARK_VERSION` keeps its own
`0.8.0-spark` API revision, and `JSONRPC_PROTOCOL_VERSION`, which is the wire
protocol version `"2.0"`). Namespacing already keeps each module
self-contained (`std.<module>.<symbol>`), so decoupling the stdlib into
independently versioned packages is reserved for 2.0.

The four fundamental modules of the 2.9 series, the three data modules of the
2.10 series and the two text modules of 2.11 (`std.lingua`, `std.regulus`) all
follow the same rule. `std.builder` exports `BUILDER_VERSION`, `std.arena`
exports `ARENA_VERSION`, `std.sourcemap` exports `SOURCEMAP_VERSION`,
`std.bitset` exports `BITSET_VERSION`, `std.diagnostic` exports
`DIAGNOSTIC_VERSION`, `std.json` exports `JSON_VERSION`, `std.jsonrpc` exports
`JSONRPC_VERSION`, `std.lingua` exports `LINGUA_VERSION` and `std.regulus`
exports `REGULUS_VERSION`, all `"2.11.0"`. The builder and arena modules also
export their default tuning constants (`BUILDER_DEFAULT_CAPACITY`,
`ARENA_DEFAULT_BLOCK_SIZE`, `ARENA_DEFAULT_ALIGNMENT`) for callers that want to
reserve exactly what the module would reserve.

### 19.1 Pure PenguScript Modules (38 modules)

All pure modules are located in the `std/` directory and imported as `import std.<module>`.

"Pure" here means **no external C library**: everything ships in this repository and
links against nothing but the PenguScript runtime. Two modules are general C bridges — `std.ffi` and `std.web` — and two more are
deliberate wrappers over the vendored single-file C libraries
(`std.lingua` over `std_c/utf8.h`, `std.regulus` over `std_c/re.h`/`re.c`).
Those four use `include`, `declare`, `link` and `antiquus` as the explicit
boundary; the other 34 are written entirely in PenguScript. Bindings to
third-party libraries are satellites installed with `pengu add`, not part of
this list.

| Module | Purpose & Core Capabilities |
|---|---|
| `std.spark` | Fundamental I/O and core runtime: `print`, `println`, `print_line`, `input`, `panic`, numeric conversions (`str_int`, `parse_int`, `parse_float`), integer ranges (`range_to`, `range_inclusive`), numeric helpers (`min_int`, `max_int`, `abs_int`, `clamp_int`), typed print variants (`print_int`, `println_int`, `print_float`, `println_float`, `print_bool`, `println_bool`), `eprintln`, and typed input (`read_line`, `read_int`, `read_float`). |
| `std.scrolls` | High-level string manipulation via enchanting methods and module functions: case conversions (`capitalize`, `title`, `swap_case`, `to_snake_case`, `to_kebab_case`, `upper`, `lower`), search and metrics (`find`, `rfind`, `count`, `line_count`, `word_count`), trimming and padding (`trim`, `lstrip`, `rstrip`, `ljust`, `rjust`, `zfill`, `center`), prefixes and splits (`removeprefix`, `removesuffix`, `partition`, `split`, `split_lines`), character and byte access (`chars`, `bytes`), formatting (`ellipsis`, `join`), validations (`is_lower`, `is_upper`, `is_space`, `is_palindrome`, `starts_with`, `ends_with`, `contains`), and three-way ordering via `compare` (the canonical way to sort and order strings in PenguScript, as `< <= > >=` are forbidden on `string`). |
| `std.oracle` | Container unwrap and propagation helpers with native/legacy API split: native constructors (`some_int`, `some_float`, `some_string`, `some_bool`, `none_*`), native unwrappers (`unwrap_*`, `unwrap_or_*`), native result helpers (`is_ok_int_result`, `is_err_int_result`, `unwrap_int_result`, `unwrap_or_int_result`), bridge conversions between legacy runes and native containers (`to_native_*`, `from_native_*`), string formatters (`describe_int`, `describe_string`, `describe_result_*`, `describe_maybe_*`), and legacy runes (`MaybeInt`, `ResultInt`, etc.) with `judge`-powered `is_none`, `is_err`, and `unwrap_or`. |
| `std.compass` | Cross-platform filesystem path manipulation: `join`, `join_all`, `basename`, `filename`, `dirname`, `ext`, `stem`, `file_stem`, `with_extension`, `without_extension`, `with_filename`, `add_ext`, `normalize`, `is_absolute`, `is_relative`, `is_root`, `is_hidden`, `is_unc`, `has_wildcard`, `matches` (glob pattern matching with `*` and `?`), `parent`, `split`, `components`, `has_component`, `cwd`, `expand_user`, `absolute`, separator queries (`separator`, `alt_separator`, `is_windows`, `is_unix`), and the `Path` rune (`from_str`, `cwd`, `new_path`, `current_dir`) with chainable query and transform methods (`to_string`, `name`, `parent`, `stem`, `suffix`, `suffixes`, `drive`, `parts`, `components`, `is_absolute`, `is_relative`, `is_root`, `has_suffix`, `has_suffix_with`, `is_empty`, `is_hidden`, `matches`, `exists`, `is_file`, `is_dir`, `to_absolute`, `expand_user`, `to_uri`, `normalize`, `relative_to`, `with_suffix`, `with_name`, `add_suffix`, `without_suffix`). |
| `std.archivum` | Filesystem operations: text and binary file I/O (`read_file`, `read_bytes`, `write_file`, `write_bytes`, `append_file`, `append_bytes`), line operations (`read_lines`, `read_first_n_lines`, `count_lines`, `write_lines`, `append_lines`), file lifecycle (`delete_file`, `copy_file`, `move_file`, `rename`, `touch`), entry predicates (`exists`, `is_file`, `is_dir`, `is_symlink`, `is_empty_file`, `is_empty_dir`), directory operations (`create_dir`, `remove_dir`, `read_dir`, `copy_tree`, `list_files_recursive`), search and traversal (`find_files`, `find_dirs`, `find_by_name`, `find_by_ext`, `glob`, `walk`), symlink and canonical path handling (`symlink`, `read_symlink`, `realpath`), temporary filesystem helpers (`temp_dir`, `temp_file`), and comprehensive metadata inspection (`metadata`, `file_size`, `dir_size`, `modified_time`, `created_time`, `accessed_time`, `permissions`). |
| `std.cipher` | Cryptographic encodings, hashing, and JSON manipulation: Base64 and variants (`encode_base64`, `decode_base64`, `is_base64`, `encode_base64_url`, `decode_base64_url`, `encode_base64_unpadded`, `encode_hex`, `decode_hex`, `is_hex`, `encode_base32`, `decode_base32`, `is_base32`), string enchantments (`to_base64`, `from_base64`, `to_base64_url`, `from_base64_url`, `to_hex`, `from_hex`, `to_base32`, `from_base32`), JSON escaping/unescaping (`json_escape`, `json_unescape`), JSON arrays (`parse_json_array`, `stringify_json_array`), typed getters (`json_get`, `json_get_int`, `json_get_float`, `json_get_bool`, `json_get_string`), navigation (`json_deep_clone`, `json_merge`, `json_path`, `json_parse_at`), and validation (`omen JsonKind`, `json_kind_of`, `is_valid_json`). |
| `std.chronicle` | Date, time, calendar, and timer management: clocks and delays (`time`, `now_ms`, `time_ms`, `monotonic`, `monotonic_ms`, `sleep`, `sleep_ms`), formatted string conversion and parsing (`format`, `format_now`, `parse`, `from_iso`, `to_iso`, `to_date_string`, `to_time_string`, `to_datetime_string`, `now_utc_iso`, `now_local_iso`, `now_date`, `now_time`), UTC and local calendar component getters (`utc_year`, `utc_month`, `utc_day`, `utc_hour`, `utc_minute`, `utc_second`, `utc_weekday`, `utc_yearday`, `utc_is_dst`, `local_year`, `local_month`, `local_day`, `local_hour`, `local_minute`, `local_second`, `local_weekday`, `local_yearday`, `local_is_dst`), calendar helpers and boundaries (`is_leap_year`, `days_in_month`, `days_in_year`, `start_of_day`, `end_of_day`, `today`, `yesterday`, `tomorrow`, `start_of_month`, `start_of_year`), timestamp arithmetic and relations (`add_seconds`, `add_minutes`, `add_hours`, `add_days`, `add_weeks`, `diff_seconds`, `diff_days`, `is_before`, `is_after`, `is_between`), duration helpers (`format_duration`, `parse_duration`), the `DateTime` rune (`datetime_utc`, `datetime_local`, `to_iso`, `to_date`, `to_time`), and monotonic high-resolution timer rune `Stopwatch` (`new`, `new_stopwatch`, `elapsed_sec`, `elapsed_ms`, `reset`). |
| `std.lot` | Pseudo-random number generation (PRNG), sampling, and statistical distributions: LCG state management (`seed`, `next_int`, `next_float`, `rand_int`, `rand_float`), continuous and discrete distributions (`rand_uniform`, `rand_gauss`, `rand_exp`, `rand_between`, `rand_sign`, `rand_bit`, `rand_coin`, `rand_bool_with`, `rand_triangular`, `rand_lognormal`, `rand_weibull`, `rand_gamma`, `rand_beta`), collection sampling and shuffling (`choice`, `choice_string`, `choice_weighted`, `choice_weighted_string`, `shuffle`, `shuffle_string`, `sample`, `sample_with_replacement`, `sample_string`, `permutation`), and randomized string generators (`rand_alpha`, `rand_digit_string`, `rand_alnum_string`, `rand_hex_string`, `rand_bytes_hex`, `rand_password`, `rand_from_charset`). |
| `std.rites` | Operating system process, environment, and system utilities: environment variables and bulk management (`getenv`, `setenv`, `unsetenv`, `get_env_keys`, `getenv_or`, `has_env`, `getenv_int`, `getenv_float`, `getenv_bool`, `get_env_map`, `set_env_map`, `clear_env`), variable expansion (`expand_env`, `env_substitute`), program arguments (`get_argc`, `get_argv`, `get_args`, `arg_at_or`, `parse_flags`, `has_flag`, `get_flag_value`), standard directories (`home_dir`, `temp_dir`, `config_dir`, `cache_dir`, `data_dir`), platform inspection (`uname`, `hostname`, `os_arch`, `os_family`, `is_windows`, `is_unix`, `is_macos`, `is_linux`), executable resolution (`which`, `which_all`), process identity and control (`getpid`, `getppid`, `getcwd`, `chdir`, `exit`, `exec`, `spawn`, `exec_ok`, `exec_or_panic`, `run_shell`, `shell_escape`, `current_user`). |
| `std.whisper` | Structured leveled logging with severity levels (`LOG_TRACE` through `LOG_FATAL`, `COLOR_*`): global helpers (`log`, `trace`, `debug`, `info`, `warn`, `error`, `fatal`, `set_level`, `get_level`, `get_level_name`, `get_level_color`, `is_enabled`, `set_level_from_string`, `set_level_from_env`, `fatal_and_exit`, `log_json`, `log_levels`), and object-oriented `Logger` rune (`Logger.new`, `Logger.named`, `Logger.from_env`, `default_logger`) with methods (`.log`, `.trace`, `.debug`, `.info`, `.warn`, `.error`, `.fatal`, `.set_level`, `.get_level`, `.is_enabled`, `.enable_timestamp`, `.disable_timestamp`, `.enable_color`, `.disable_color`, `.to_file`, `.child`, `.log_json`). |
| `std.ward` | Defensive programming, invariant assertions, and contract validation with informative failure messages: core assertions (`assert_true`, `assert_false`, `assert_eq_int`, `assert_ne_int`, `assert_eq_string`, `assert_ne_string`, `assert_eq_bool`), floating-point tolerance (`assert_eq_float`, `assert_ne_float`, `assert_almost_eq`), ordering and range checks (`assert_gt_int`, `assert_ge_int`, `assert_lt_int`, `assert_le_int`, `assert_gt_float`, `assert_ge_float`, `assert_lt_float`, `assert_le_float`, `assert_in_range_int`, `assert_in_range_float`), string and container validation (`assert_string_contains`, `assert_string_starts_with`, `assert_string_ends_with`, `assert_string_empty`, `assert_string_not_empty`, `assert_eq_int_list`, `assert_eq_string_list`, `assert_list_empty_int`, `assert_list_not_empty_int`, `assert_list_len_int`, `assert_map_has_key`, `assert_map_not_has_key`), generic container assertions (`shard T`: `assert_maybe_present`, `assert_maybe_none`, `assert_result_ok`, `assert_result_err`), non-fatal test wrappers (`expect_*`, `check_*`), and invariant failure utilities (`fail`, `fail_unreachable`). |
| `std.trial` | Integrated unit test framework: test suites, assertions (`assert_eq`, `assert_true`), benchmark runners, and structured test reporting. |
| `std.tally` | Integer list utilities: enchants `list of int` directly (`calling xs.sum`, `calling xs.first`, `calling xs.reverse`) alongside module-level functions (`calling tally.sum with xs`). Includes length and access (`len`, `first`, `last`, `at_or`, `at_safe`), search (`contains`, `index_of`, `count_of`, `find_first_gt`, `find_first_lt`), reductions (`sum`, `product`, `max_val`, `min_val`, `max_index`, `min_index`), statistics (`mean`, `median`, `mode`), transformations (`reverse`, `sort_asc`, `sort_desc`, `unique`, `dedup`, `flatten`), selection (`take`, `drop`, `slice_list`), combination (`concat`, `zip_sum`, `dot`, `repeat`), predicates, filters (`filter_*`), and mappings (`map_*`). |
| `std.atlas` | Multi-type map collection utilities across 6 key-value combinations (`map of string to int`, `map of string to string`, `map of string to float`, `map of int to int`, `map of int to string`, `map of string to bool`). Enchants map types directly (`calling m.keys`, `calling m.get_or with k, default`, `calling m.update with k, v`, `calling m.rename_key with old_k, new_k`, `calling m.clone`, `calling m.remove with k`, `calling m.clear`) alongside module-level functions (`calling atlas.keys with m`, `calling atlas.get_or_ss with m, k, def`). Includes length & predicates (`size`, `is_empty`, `has_key`, `has_any_key`, `has_all_keys`), access (`get_or`, `get_safe`, `find_key_by_value`), in-place mutation (`update`, `rename_key`, `remove`, `clear`, `remove_all`), bulk accessors (`keys`, `values`, `keys_sorted`, `values_sorted`), numeric reductions (`sum_values`, `max_value`, `min_value`), bool counters (`count_true`, `count_false`), filters and transformations (`filter_*`, `map_values_*`), combination (`merge_*`, `merge_keep_left_*`), conversions (`from_lists_*`, `to_keys_list`, `to_values_list`), and generic utilities (`shard K, V`: `map_size`, `map_has_key`, `map_get_or`, `map_keys`, `map_values`, `map_put`, `map_remove`, `map_clear`). |
| `std.coven` | Unique-set collections (`SetString`, `SetInt`): insertion and predicates (`add`, `contains`, `remove`, `len`, `clear`, `is_empty`), full set algebra (`union`, `intersect`, `difference`, `symmetric_difference`, `is_subset`, `is_superset`, `is_disjoint`, `equals`), conversions (`to_list`, `to_set_int`, `to_set_string`, `from_list`, `clone`), and specialized filters (`filter_starts_with`, `filter_length_ge`). |
| `std.filum` | Multithreaded concurrency primitives: mutual exclusion (`Mutex` with `lock`, `unlock`, `try_lock`, `free`), synchronization counters (`WaitGroup` with `add`, `done`, `wait`, `free`), once guards (`Once` with `do_once`, `do_action`, `free`), condition variables (`Cond` with `cond_wait`, `wait_mutex`, `signal`, `broadcast`, `free`), thread-safe integers (`AtomicInt` with `load`, `store`, `add`, `sub`, `inc`, `dec`, `inc_and_get`, `dec_and_get`, `swap`, `get_and_set`, `compare_swap`, `is_zero`, `reset`, `free`), typed channels (`ChanInt`, `ChanString`, `ChanFloat`, `ChanBool` with `new`, `with_capacity`, `send`, `recv`, `close`, `len`, `cap`, `free`), and system/time utilities (`sleep`, `sleep_sec`, `num_cpu`, `goroutine_id`). |
| `std.fractio` | Floating-point-only methods via `enchanting shard T where T: Real:` plus two concrete blocks (`enchanting float:` and `enchanting f64:`) for the `libm` transcendentals, because C exposes `sqrtf`/`sqrt` as distinct symbols. IEEE 754 classification (`is_nan`, `is_finite`, `is_infinite`, `is_positive_infinity`, `is_negative_infinity`); approximation (`approx_eq` with absolute tolerance, `lerp`); utilities (`reciprocal`, `copysign`, `degrees`, `radians`); transcendentals via `libm`: `sqrt`, `cbrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `ln`, `log2`, `log10`, `pow`, `hypot`. Monomorphized to `f64_sqrt`, `float_is_nan`, … — zero runtime overhead. Universal methods live in `std.numerus`; `Real` implies `Num`. |
| `std.integrum` | Integer-only methods across every signed/unsigned primitive via `enchanting shard T where T: Integrum:`. Predicates (`is_even`, `is_odd`, `is_power_of_two`, `is_multiple_of`, `is_prime`); bit operations (`bit_count`, `bit_length`, `leading_zeros`, `trailing_zeros`, `next_power_of_two`, `prev_power_of_two`); Euclidean division (`div_rem` → `(T, T)`, `div_floor`, `mod_floor`); number theory (`gcd`, `lcm`, `next_prime`, `prev_prime`, `factorial`); representations (`to_hex`, `to_bin`, `to_oct`, all allocating — `banish` them). Monomorphized to `int_is_even`, `i64_gcd`, … — zero runtime overhead. Universal methods (`abs`, `clamp`, `pow_int`) live in `std.numerus`; `Integrum` implies `Num`. |
| `std.littera` | Methods on `char` via `enchanting char:`. ASCII classification (`is_digit`, `is_alpha`, `is_alnum`, `is_upper`, `is_lower`, `is_space`, `is_whitespace`, `is_control`, `is_printable`, `is_punctuation`, `is_hex_digit`, `is_ascii`); conversions (`to_upper`, `to_lower`, `to_int`, `digit_value`). Pure PenguScript — no `<ctype.h>`, no locale, deterministic across Linux/macOS/Windows. `is_space` is only `' '`; use `is_whitespace` for the full C `isspace` set. `to_int` is `ord` (the unsigned byte, 0–255). |
| `std.logica` | Methods on `bool` via `enchanting bool:`. Chainable versions of the language operators (`toggle`, `and_with`, `or_with`); derived connectives the language has no operator for (`xor`, `iff` — biconditional, `nand`, `nor`, `implies` — material implication, `false` only when `self` is `true` and `other` is `false`); conversion `to_int` (`true` → 1, `false` → 0). Pure PenguScript — no C. Closes the primitive-methods series alongside `std.numerus`, `std.integrum`, `std.fractio` and `std.littera`. |
| `std.numerus` | Universal numeric methods across every primitive via `enchanting shard T where T: Num and T: Ordo and T: Par:`: `abs`, `signum`, `negated`, `min_with`, `max_with`, `clamp`, `is_between`, predicates (`is_zero`, `is_positive`, `is_negative`, `is_non_negative`, `is_non_positive`), arithmetic (`twice`, `half`, `square`, `cube`, `pow_int`), rounding (`truncate`, `floor`, `ceil`, `round`), conversions (`to_f64`, `to_i64`). Monomorphized to `int_abs`, `f64_clamp`, … — zero runtime overhead. Integer-only methods live in `std.integrum`; floating-point-only methods in `std.fractio`. |
| `std.loom` | Sequence generation, functional transformations, and generic algorithms: sequences (`range`, `repeat`, `take`, `skip`, `chain`, `chunks`, `windows`), reductions (`mean`, `sum_squares`, `running_sum`, `running_max`, `running_min`, `differences`), predicates (`any_zero`, `all_equal`, `is_strictly_asc`, `is_strictly_desc`, `is_sorted_asc`, `is_sorted_desc`), transforms (`zip_with`, `zip_longest`, `enumerate`, `interleave`, `round_robin`, `rotate_left`, `rotate_right`, `intersperse`, `pairwise`, `flat_map_identity`), sorted set-like operations (`union_sorted`, `intersect_sorted`, `difference_sorted`, `symmetric_difference_sorted`), search (`find_first`, `find_last`, `binary_search`, `count_if_even`, `count_if_positive`, `index_min`, `index_max`), structural modifications (`insert_at`, `remove_at`, `replace_at`, `swap_at`, `pad_left`, `pad_right`), statistics (`median`, `mode`, `variance`, `stddev`, `percentile`), and generic algorithms (`shard T`: `first_or`, `generic_take`, `generic_take_last`, `generic_reverse`, `generic_chain`, `generic_index_of`), plus the context-taking pipelines `map_ctx`, `filter_ctx`, `fold_ctx`, `for_each_ctx`, `zip_with_ctx`, `find_first_ctx`, `any_ctx`, `all_ctx`, `partition_ctx` and `filter_map_ctx`. |
| `std.functor` | Thick functions: an explicit callback plus a borrowed context, with no closures. `Fn0<R>`, `Fn1<A,R>`, `Fn2<A,B,R>` and `Fn3<A,B,C,R>` (two pointers each), constructors `make_fn0`..`make_fn3`, methods `call`, `is_null` and `call_or`, and `FUNCTOR_VERSION`. Construction reinterprets the function pointer once (the Zig/Odin pattern, the only `transmute` in the module); calling is one C indirect call and allocates nothing. |
| `std.memoria` | Manual heap memory management via `shard T` module functions: `alloc`, `alloc_array`, `try_alloc`, `try_alloc_array`, `resize_array` (with explicit `old_n`), `try_resize_array`, `copy` (memmove semantics — safe with overlap), `fill`, `zero`, `swap`, `compare` (returns `-1`/`0`/`1` like `memcmp`), `bytes_for`. Zeroed by default; OOM aborts unless the `try_*` variant is used. Composes with `banish`/`defer banish`/`errdefer banish`/`derive Nexus`. `free`, `sizeof` and `address_of` are deliberately absent — those are `banish`, `size of` and `sigil of` in the language itself. Experts needing an uninitialized block use `antiquus`. |
| `std.invoke` | Command-line interface (CLI) argument parsing: POSIX and GNU syntax (`--flag`, `--key=value`, `-k=value`), boolean flag negation (`--no-flag`), subcommands (`rune Subcommand`), typed options (int, float, bool, string, multi), repeat multi-options (`rune MultiOption`), Levenshtein typo suggestions, formatted help and usage strings (`usage_string`, `full_help`), error reporting, and robust parse variants (`parse`, `parse_no_exit`, `parse_or_exit`, `parse_or_usage`, `ParseResult` accessors `get`, `get_or`, `get_int`, `get_int_or`, `get_float`, `get_float_or`, `get_bool`, `get_bool_or`, `get_all`, `to_map_values`, `to_map_flags`). |
| `std.ffi` | Low-level C foreign function interface bridge: null pointer utilities (`null_void`, `null_char`, `null_byte`, `is_null`, `is_valid`, `ptr_eq`), architecture constants and inspection (`SIZEOF_POINTER`, `SIZEOF_INT`, `SIZEOF_FLOAT`, `pointer_size`, `size_of shard T`, `alignment_of shard T`), null-terminated C string conversions (`string_from_cstr`, `cstr_from_string`, `string_from_cstr_n`, `string_from_bytes`, `bytes_from_string`), memory views (`slice_from_ptr`), generic collections from C buffers (`list_from_ptr shard T`, `map_from_entries shard K, V`), raw memory copy/set (`memcpy_raw`, `memset_raw`), and 10 canonical C interop patterns. |
| `std.web` | WebAssembly / Emscripten bridge, compiled away entirely on native targets. Picks the branch with the `when wasm:` compile-time variable, so on a native build every entry point still exists (safe stubs) and on wasm the Web calls are emitted. Console (`console_log`, `console_warn`, `console_error`, `console_trace` — reaching the JavaScript console, or stderr natively), a real main loop (`set_main_loop` with an optional fps and `simulate_infinite_loop`, `cancel_main_loop`, `pause_main_loop`, `resume_main_loop`), high-resolution monotonic time (`now_ms`), JavaScript evaluation (`eval_js`), deferred calls (`set_timeout`, `clear_timeout`), and the `IS_WASM` constant. `emscripten_sleep` is deliberately **not** here: it needs `-sASYNCIFY`, and everything in this module works with a plain `emcc` build. See `docs/WASM.md`. |
| `std.ledger` | Tabular data, CSV/TSV parsing, serialization, and matrix operations: parsing (`parse_csv`, `parse_tsv`, `parse_line`, `detect_delimiter`, `parse_csv_strict`, `parse_csv_nocomments`, `parse_csv_skip`, `parse_line_strict`, `parse_csv_normalized`), table abstraction `rune CsvTable` (`from_csv`, `from_rows`, `row_count`, `column_count`, `has_column`, `column_index`, `get`, `get_or`, `column`, `row_as_map`, `to_csv`), matrix enchantments (`list of list of string`: `row_count`, `column_count`, `is_rectangular`, `column`, `transpose`), key-value map conversions (`parse_csv_as_pairs`, `parse_csv_key_value`, `write_key_value_map`), escaping (`escape_field`, `escape_field_rfc4180`, `escape_field_backslash`), formatters (`to_csv_string`, `to_tsv_string`, `to_csv_string_no_trailing_newline`, `to_csv_string_crlf`), and file operations (`read_csv`, `read_tsv`, `write_csv`, `write_tsv`, `write_csv_safe`). |
| `std.arithmancy` | Advanced math and game-ready linear algebra. **Two parts:** (a) the scalar functions (`abs_i`, `abs_f`, `min_i`, `max_i`, `min_f`, `max_f`, `clamp_i`, `clamp_f`, `sqrt_f`, `pow_f`, `sin_f`, `cos_f`, `tan_f`, `asin_f`, `acos_f`, `atan_f`, `atan2_f`, `deg_to_rad`, `rad_to_deg`, `lerp_f`, `smoothstep_f`, `is_prime`, `gcd`, `lcm`, `is_power_of_two`) are now **thin wrappers** over the primitive-methods modules (`std.numerus`, `std.integrum`, `std.fractio`) — the algorithm lives in the module that owns the bound; (b) the vector/matrix/quaternion types (`Vec2`, `Vec3`, `Vec4`, `Mat4`, `Quat`) and the constants (`PI`, `TAU`, `E`, `EPSILON`, `HALF_PI`, `SQRT2`, …), which have no equivalent elsewhere and remain the source of truth. Four rounding helpers (`floor`/`ceil`/`round`/`trunc`), `approx_eq`, `fmod` and `next_power_of_two` deliberately stay local: they differ from the module methods in domain or boundary semantics. |
| `std.builder` | `StringBuilder`, an amortised-O(1) text accumulator: `new`, `with_capacity`, `from_string`; `append`, `append_char`, `append_int`, `append_i64`, `append_float`, `append_f64`, `append_bool`, `append_bytes`, `append_slice`, `append_repeat`, `append_spaces`; `insert_at` / `insert`, `set_char_at`, `truncate`, `reverse`; `len`, `capacity`, `is_empty`, `char_at`, `byte_at`, `bytes_view`, `substring`; `reserve`, `shrink_to_fit`, `clear`, `reset`; `finish` (ownership transfer, O(1)) and `to_string` (copy). Comparable to `java.lang.StringBuilder` and `zig.ArrayList(u8)`. |
| `std.arena` | Bump allocator for temporary object graphs: `Arena.new`, `Arena.with_block_size`, `alloc`, `alloc_aligned`, `alloc_str`, `alloc_cstr`, `total_allocated`, `block_count`, `block_size`, `reset` (keeps the first block, reuses the arena) and `free` (releases every block). Oversized blocks and absolute-address alignment are supported; `arena_alloc of T` / `arena_alloc_one of T` return typed, zeroed memory. Comparable to `zig.heap.ArenaAllocator` and `bumpalo`. |
| `std.sourcemap` | Byte-offset ↔ 1-indexed `(line, column)` translation: `SourceMap.from_source`, `source`, `line_count`, `source_len`, `position_at` (O(log lines)), `offset_of` (O(1)), `line_text` (CRLF-aware), `line_span`, `span_at`, `span_to_positions`, `is_valid_offset`, `is_valid_position`, `clamp_offset`, plus the `Position` and `Span` runes. Comparable to `rustc_span::SourceMap`. |
| `std.bitset` | Fixed-length dense bit set: `new`, `filled`, `from_bytes`; `set`, `clear`, `toggle`, `set_to`, `get`; `set_all`, `clear_all`, `toggle_all`; `count_ones`, `count_zeros`, `is_empty`, `is_full`, `any`, `all`; `and_with`, `or_with`, `xor_with`, `and_not_with`, `not`, the matching `*_in_place` forms, `find_first_set`, `find_first_clear`, `find_next_set`, `find_next_clear`, `equals`, `copy`, `iter_set` and a non-owning `to_bytes`. Comparable to `java.util.BitSet` and `zig.DynamicBitSet`. |

| `std.diagnostic` | General-purpose diagnostics with source spans: `Span`, `Severity`, `Label`, `Diagnostic`, `DiagnosticBag` (`new`, `add`, `extend`, `error`/`warning`/`info`/`hint`, `len`, counts, `errors_only`, `warnings_and_errors`, `clear`, `add_source`, `source_of`), `RenderOptions` (`default_render_options`), Rust-style `render`/`render_plain`/`render_colored` with ANSI colour, `NO_COLOR` and TTY detection, `span_from_positions`, `span_point` and `span_merge`, plus `render_json` producing an LSP-compatible `Diagnostic[]` (0-indexed positions, severity 1–4, `relatedInformation`). Comparable to `rustc_diagnostic` and `codespan-reporting`. |
| `std.json` | Strict RFC 8259 JSON: `parse`, `parse_with`, `parse_bytes`, `parse_in_arena`, `validate`, `validate_bytes`; `JsonValue` as an algebraic `omen` (`Null`, `Bool`, `Int(i64)`, `Float(f64)`, `Str`, `Arr`, `Obj`) preserving insertion order; eight typed `as_*` accessors, `at`/`first`/`last`/`get`/`keys`/`values`/`entries`, `array_len`/`object_len`/`has_key`/`type_name`; JSON Pointer (RFC 6901) via `pointer`; recursive `find_key`; `equals`/`equals_numeric`; deep `clone`; in-place `push_json`/`pop_json`/`set_at`/`put_json`/`set_key`/`remove_key`/`merge`; `stringify`, `stringify_with`, `stringify_pretty`, `write_to_builder`, `try_stringify` with shortest-round-trip floats; `ParseOptions` (strict, comments, trailing commas, NaN/Infinity, depth) and `SerializeOptions` (indent, sort, ASCII, slash, NaN, separators, newline); `deep_merge`; `validate_schema` (a practical JSON Schema subset); byte-exact `JsonError` with kind/line/column/offset. Covers everything Python's `json` does and adds pointer, search, validation, arena mode and schema checks. |
| `std.jsonrpc` | JSON-RPC 2.0: `JsonRpcId`, `JsonRpcMessage` (`Request`/`Notification`/`ResponseOk`/`ResponseError`), `JsonRpcError`, the five standard codes (`PARSE_ERROR` … `INTERNAL_ERROR`), `request`/`notification`/`response_ok`/`response_error` constructors, `encode_request`/`encode_notification`/`encode_response_ok`/`encode_response_error`/`encode_message`, `parse_message`, `parse_batch`, `take_messages`, `free_messages`, the standard error constructors, `JsonRpcParseError`/`JsonRpcErrorKind`, and LSP framing (`encode_framed`, `decode_framed_bytes`, `decode_framed`, `FramedDecode` with `consumed`/incomplete semantics). Comparable to Rust's `jsonrpc-core`. |

| `std.lingua` | UTF-8 text over codepoints: `Codepoint` (a `seal` over `u32`), `LinguaError` with byte offsets, `decode`/`decode_prefix`, `encode`/`encode_one`, `is_valid`/`validate`, `codepoint_count`/`utf16_length`, `is_ascii`/`is_bmp`/`is_letter`/`is_digit`/`is_whitespace`/`is_punctuation`/`is_symbol`/`is_control`/`is_surrogate`, `to_u32`/`from_u32`/`to_utf16`, `codepoint_at`/`byte_offset_of`/`next_codepoint`/`prev_codepoint`, and an approximate `grapheme_count`. Wrapper over `std_c/utf8.h` (sheredom, public domain). See `docs/LINGUA.md`. Comparable to `utf8proc` (Julia) and Lua's `utf8`. |
| `std.regulus` | Small, explicit regular expressions: `Regex.compile`, `pattern`, `is_match`, `match`, `match_at`, `matches`, `replace_first`, `replace_all`, `split`, `escape`, `Match` and `RegexError`, plus one-shot `is_match`/`find_first`. Complete grammar: `. ^ $ * + ? [] \d \w \s`; **no** groups, alternation, `{n,m}`, lookaround, backreferences or Unicode classes. Wrapper over `std_c/re.h` + `re.c` (kokke/tiny-regex-c, public domain). See `docs/REGULUS.md`. Comparable to Python's `re` for basic search. |

### 19.1.1 Choosing between `std.loom` and `std.tally`

`std.loom` and `std.tally` both operate on lists and share 15 public names
(`mean`, `median`, `mode`, `min_max`, `sum`, `flatten`, `take`, `windowed`,
`zip_with`, `running_sum`, `scan_left`, `repeat`, `enumerate_pairs`,
`is_sorted_asc`, `is_sorted_desc`). They are **not duplicates**: no shared name
has the same signature. They are two deliberate API philosophies, and the
choice is decided by what an empty or absent input should mean.

| | `std.tally` | `std.loom` |
|---|---|---|
| Shape | enchants `list of T` (`calling xs.sum`) plus concrete `list of int` module functions | module functions only (`calling loom.sum with xs`); declares no `enchanting` |
| Empty input | collapses to a sentinel (`0`, `""`, `false`) | signals absence (`maybe none`) |
| Fractional results | truncated to `int` | preserved as `float` (`maybe float` for `median`) |
| Generics | methods are generic (`T: Num/Ordo/Par/Integrum`); compatibility functions are concrete | `shard T` on the `generic_*` cores; the rest is concrete `list of int` |
| Reach for it when | the sentinel is meaningful and the caller wants no branching (`sum`, `product_num`, `max_val`, `min_val` over counts) | absence must stay distinguishable (`mean` as a real average, `median`/`mode` on an empty list, `min_max` meaning "no elements") |

Concrete example of the divergence:

```pengu
import std.loom
import std.tally

weave main into int:
    var xs as list of int is calling loom.range with 1, 3, 1
    var exact as float is calling loom.mean with xs      # 1.5
    var lossy as int is calling tally.mean with xs       # 1
    var no_median as maybe float is calling loom.median with (list of int)  # none
    return 0
```

Rule of thumb: **use `tally` when the operation is a reduction with a natural
identity** (`sum` -> 0, `product_num` -> 1, and `max_val` -> 0 is a deliberate
sentinel) and **`loom` when an empty list has no answer**, where returning a
sentinel would hide a bug.

The deprecation status of the legacy aliases in both modules is catalogued in
[`docs/DEPRECATIONS.md`](docs/DEPRECATIONS.md); unifying the two families is
deferred to 1.1 because either direction is a breaking change for the callers of
whichever family loses (item 6.5, `AUDIT_1.0_FASE6.md`).

### 19.1.2 The four fundamental modules

The 2.11.0 line keeps the three data modules and the four fundamental modules of
the 2.9 series. The fundamental modules provide the building blocks the
self-hosted compiler (and every other tool that builds text, trees, positions or
dense sets) needs first. They are deliberately
general: `builder` is as useful for CSV, HTML and logs as for code generation;
`arena` is as useful for a parser's AST as for a renderer's temporary graph;
`sourcemap` is as useful for a linter as for a compiler; `bitset` is as useful
for a Bloom filter or an occupancy map as for a data-flow set.

| Module | Reach for it when | Typical cost |
|---|---|---|
| `std.builder` | you append text in a loop or in a recursive traversal | one `memcpy` per append, 2x amortised growth |
| `std.arena` | many objects share one lifetime and are released together | O(1) per allocation |
| `std.sourcemap` | you have a byte offset and need a line/column (or the reverse) | O(log lines) query, O(n) build |
| `std.bitset` | the universe is a dense range of integers and membership matters | O(1) per bit, O(n/8) bulk |

#### `std.builder`

`StringBuilder` owns one contiguous buffer. `finish` hands that buffer to a new
`string` without copying; `to_string` copies and leaves the builder usable.

```pengu
import std.builder
import std.spark

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "total: "
    calling sb.append_int with 42
    var out as string is calling sb.finish
    defer banish out
    calling spark.println with out
    return 0
```

`append` is amortised O(1); `append_int`/`append_float` format directly into the
builder (no temporary string). `insert_at`, `truncate` and `reverse` are
O(n) in the bytes they move.

#### `std.arena`

`Arena` hands out slices of large blocks and never frees an individual object.
`reset` keeps the first block and makes the arena reusable; `free` releases every
block. `reset`/`free` release **memory only** — they do not run destructors or
free `string`/`list` buffers stored inside arena memory.

```pengu
import std.arena
import std.spark

rune Node:
    value as int
    next as ref to Node

weave main into int:
    var a as Arena is calling Arena.new
    defer banish a
    defer calling a.free
    var head as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set head->value is 7
    set head->next is calling arena_alloc_one of Node with (sigil of a)
    set head->next->value is 8
    calling spark.println with "{(head->value) + (head->next->value)}"
    return 0
```

`alloc_aligned` aligns the **absolute address**, so page-aligned and SIMD-aligned
buffers work even though the underlying block came from `malloc`. `alloc(size)`
uses `ARENA_DEFAULT_ALIGNMENT` (16 bytes). An allocation may be larger than the
normal block; it gets its own oversized block.

> [!IMPORTANT]
> `banish arena` releases the two bookkeeping lists, not the blocks. Release the
> blocks with `free` first (`defer calling a.free`), then `banish a`.

#### `std.sourcemap`

`SourceMap` indexes line starts once and answers both directions. Lines and
columns are 1-indexed; a column is a **byte** offset (not a codepoint index) so
`offset = line_start + column - 1` is exact even for invalid UTF-8. In a CRLF
file the `
` counts for offsets but is excluded from `line_text`.

```pengu
import std.sourcemap
import std.spark

weave main into int:
    var sm as SourceMap is calling SourceMap.from_source with "a\nb"
    defer banish sm
    var p as Position is calling sm.position_at with 2
    var line as string is calling sm.line_text with 2
    defer banish line
    calling spark.println with "line {p.line}, col {p.col}: {line}"
    return 0
```

`position_at` clamps out-of-range offsets; `offset_of` panics on a bad line or
column. `line_text` and `substring` return owned strings (release them);
`source` and `bytes_view`-style accessors return borrows.

#### `std.bitset`

`BitSet` has a fixed `bit_len` and keeps the padding bits of the last byte at
zero, so `count_ones` is exact. Binary operations require equal lengths;
`equals` returns `false` for different lengths instead of panicking.

```pengu
import std.bitset
import std.spark

weave main into int:
    var seen as BitSet is calling BitSet.new with 64
    defer banish seen
    calling seen.set with 3
    calling seen.set with 7
    var count as int is calling seen.count_ones
    var first as maybe int is calling seen.find_first_set
    calling spark.println with "count={count} first={first}"
    banish first
    return 0
```

Use `map of int to int` for a sparse set: a bitset reserves `bit_len / 8` bytes
whether it holds two elements or two million.


### 19.1.3 The data modules: `std.diagnostic`, `std.json`, `std.jsonrpc`

The data modules are the three pieces a tool needs to speak a modern
protocol: a diagnostic model for human and machine output, a JSON DOM for the
wire payload, and JSON-RPC 2.0 (with LSP framing) for the transport. They are
independent of each other except that `std.diagnostic` uses `std.json` for
`render_json`; `std.json` never imports `std.diagnostic`.

#### `std.json`: parse, query, serialize

```pengu
import std.json
import std.spark

weave main into int:
    var source as string is r"""{"name":"pengu","tags":[1,2],"nested":{"ok":true}}"""
    var parsed as result of JsonValue to json.JsonError is calling json.parse with source
    var root as JsonValue is parsed or:
        calling spark.println with "line {error.line}, col {error.col}: {error.message}"
        return 1
    defer banish root

    var name as JsonValue is calling json.get_or_null with root, "name"
    defer banish name
    var text as string is (calling name.as_string) or else ""
    # `as_string` returns an owned copy inside a maybe; `take_string` moves it
    # out and frees the box in one step.
    var sv as maybe string is calling name.as_string
    var owned as string is calling json.take_string with (sigil of sv)
    defer banish owned
    calling spark.println with owned                         # pengu

    var second as JsonValue is (calling root.pointer with "/tags/1") or:
        calling JsonValue.null_value
    defer banish second
    var n as maybe i64 is calling second.as_int
    calling spark.println with "{(n or else 0)}"             # 2

    var wire as string is calling json.stringify_pretty with root, 2
    defer banish wire
    calling spark.print with wire
    return 0
```

Key points:

- **Strict by default** (RFC 8259). `ParseOptions` opts into comments, trailing
  commas, `NaN`/`Infinity`, `strict=false` control characters, or a different
  depth limit.
- **Errors carry position**: `kind`, `message`, 1-indexed `line`/`col`, and the
  0-indexed byte `offset`.
- **Integers are `i64`**. A literal outside that range is `IntegerOverflow`;
  there are no bigints.
- **Objects preserve insertion order**. Duplicate keys keep the first position
  and the last value.
- **Every query returns an owned copy**. `at`, `get`, `first`, `last`,
  `pointer`, `find_key` and `clone` are independent of the source; `banish`
  them. `as_array`/`as_object`/`values`/`entries` return deep copies released
  with `free_values`/`free_entries`; `keys` with `free_strings`.
- **`parse_in_arena`** returns an arena-backed tree: strings and list buffers
  live in the arena, `banish arena` releases everything, and banishing the
  value is a safe no-op. The lists are immutable (their `cap` is negative).
- **Floats round-trip**: the serializer emits the shortest decimal form that
  `strtod` maps back to the same bits, formatted like Python (`1.0`,
  `10000000000.0`, `1e+20`, `1e-05`).
- **`try_stringify`** returns an error instead of panicking on a non-finite
  float; `stringify` panics unless `allow_nan` is set.

Compatibility with Python's `json`:

| Python | `std.json` |
|---|---|
| `json.loads(s)` | `parse(s)` |
| `json.dumps(v)` | `stringify(v)` |
| `json.dumps(v, indent=2)` | `stringify_pretty(v, 2)` |
| `json.dumps(v, sort_keys=True)` | `stringify_with(v, {..., sort_keys: true})` |
| `json.dumps(v, ensure_ascii=False)` | the default |
| `json.dumps(v, allow_nan=True)` | `stringify_with(v, {..., allow_nan: true})` |
| `JSONDecodeError.lineno/colno/pos/msg` | `err.line` / `err.col` / `err.offset` / `err.message` |
| `json.load(fp)` / `json.dump(v, fp)` | `parse(archivum.read_file(path))` / `archivum.write_file(path, stringify(v))` |
| (none) | `pointer`, `find_key`, `validate`, `deep_merge`, `parse_in_arena`, `validate_schema` |

#### `std.diagnostic`: spans, labels and output

```pengu
import std.diagnostic as diag
import std.spark

weave main into int:
    var bag as DiagnosticBag is calling DiagnosticBag.new
    defer banish bag
    calling bag.add_source with "src/main.pengu", "var x as int is \"hello\"\n"

    var span as Span is calling diag.span_from_positions with "src/main.pengu", 1, 18, 1, 25, 17, 24
    var label as Label is calling diag.label with span, "expected 'int' here", true
    calling bag.add with (calling diag.diagnostic with diag.Severity.Error, "E0005",
        "expected 'int', found 'string'", (calling diag.labels with label),
        (some "use '(s to int)'"), (some "'string' is not assignable to 'int'"),
        (calling diag.no_related))

    var human as string is calling bag.render_colored
    defer banish human
    calling spark.print with human

    var json_text as string is calling bag.render_json     # LSP Diagnostic[]
    defer banish json_text
    return 0
```

- `render`/`render_plain`/`render_colored` produce a rustc-style block with a
  `gutter`, context lines, `^^^^`/`----` markers, `note:`, `help:` and
  `related:`. `render_colored` honours `NO_COLOR` and non-TTY output;
  `RenderOptions.force_color` bypasses both for tests.
- A diagnostic without labels (or without a primary label) renders only its
  header or its position-only lines; it never panics.
- A span whose file has no registered source prints `file:line:col` and the
  label messages, without context. This is the remote/position-only case.
- `render_json` emits one LSP `Diagnostic` object per diagnostic: `range`
  (0-indexed), numeric `severity`, optional `code`, `source: "pengu"`,
  `message`, and `relatedInformation` for secondary labels and `related`
  diagnostics.
- Tabs are expanded with `tab_width`; multi-byte UTF-8 codepoints count as one
  visual column, so carets line up under `ñ` or an emoji even though `Span`
  columns are bytes.

#### `std.jsonrpc`: JSON-RPC 2.0 and LSP framing

```pengu
import std.json
import std.jsonrpc as rpc
import std.spark

weave main into int:
    var id as JsonRpcId is with Number is 1
    var params as JsonValue is calling json.empty_array
    calling params.push_json with (calling JsonValue.int_val with 42)
    var msg as JsonRpcMessage is calling rpc.request with id, "echo", (some params)
    defer banish msg

    var frame as string is calling rpc.encode_framed with msg
    defer banish frame
    calling spark.print with frame
    # Content-Length: 43\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"echo","params":[42]}

    var decoded as result of rpc.FramedDecode to rpc.JsonRpcParseError is calling rpc.decode_framed_bytes with frame
    if decoded.is_ok:
        var d as rpc.FramedDecode is decoded.value
        if d.message.is_present:
            var back as JsonRpcMessage is d.message.value
            var same as bool is calling back.equals with msg
            calling spark.println with "roundtrip: {same}"
    banish decoded
    return 0
```

- Messages are `Request`, `Notification`, `ResponseOk` or `ResponseError`; the
  wire member for a failed response is `error`, while the PenguScript field is
  named `err` (because `error` is the reserved `or:` binding name).
- `parse_message` validates `jsonrpc: "2.0"`, the id type (integer or string;
  `null`/floats are rejected), params being array/object, and the
  result/error mutual exclusion. The error kind says exactly which rule failed.
- `parse_batch` returns the first invalid element as the error and releases
  messages decoded before it. `take_messages` moves the list out of a
  successful result so `free_messages` can release it.
- `decode_framed_bytes` returns a `FramedDecode`: `consumed == 0` and no
  message means "read more bytes"; a positive `consumed` is the exact frame
  size. Header parsing is case-insensitive and requires `Content-Length`.
- The standard error codes are constants: `PARSE_ERROR`, `INVALID_REQUEST`,
  `METHOD_NOT_FOUND`, `INVALID_PARAMS`, `INTERNAL_ERROR`; `error_server`
  covers the `-32000..-32099` application range.

### 19.1.4 The text modules: `std.lingua` and `std.regulus`

These two modules close the "text, but not ASCII" gap. They are **thin wrappers**
over vendored C, not reimplementations: `std.lingua` owns the UTF-8 decoding and
`std.regulus` owns the regex engine. Both return `result` values for every
fallible operation and both keep their C out of the bundle unless imported.

#### `std.lingua`: codepoints with an error offset

```pengu
import std.lingua
import std.spark

weave main into int:
    var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with "año 😀"
    if not decoded.is_ok:
        return 1
    var cps as list of Codepoint is decoded.value
    calling spark.println_int with cps.len                         # 5
    calling spark.println_int with (calling lingua.utf16_length with "😀")   # 2
    calling spark.println_bool with (calling lingua.is_valid with "hola")    # true
    banish decoded
    return 0
```

`decode` returns `err` with the byte offset of the first invalid sequence:
`InvalidByte`, `TruncatedSequence`, `OverlongEncoding`, `SurrogateCodepoint`,
`CodepointOutOfRange` or `IndexOutOfRange`. `is_valid`, `validate`,
`codepoint_count` and `utf16_length` are O(n) and allocate nothing (the counts
return `-1` for invalid input). Classification is approximate — see
[`docs/LINGUA.md`](docs/LINGUA.md) for the exact ranges and the out-of-scope
items (normalisation, full case folding, UAX #29 graphemes).

#### `std.regulus`: a small, complete grammar

```pengu
import std.regulus
import std.spark

weave main into int:
    var compiled as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if not compiled.is_ok:
        return 1
    var rx as Regex is compiled.value
    calling spark.println_bool with (calling rx.is_match with "abc123")    # true
    var replaced as string is calling rx.replace_all with "a1b22", "N"     # "aNbN"
    banish replaced
    banish compiled
    return 0
```

Supported syntax is exactly `. ^ $ * + ? [abc] [a-z] [^abc] \d \D \w \W \s
\S` and `\x`. There are **no** capture groups, alternation, `{n,m}`,
lookaround, backreferences, inline flags or Unicode properties; `(...)` and `|`
are literal bytes. Limits: 255-byte pattern, 30 compiled symbols, 40 bytes of
character classes. Use `regulus.escape` before embedding user text in a pattern.
For anything beyond that grammar, install a PCRE satellite. See
[`docs/REGULUS.md`](docs/REGULUS.md).

#### Smart linking

`std/lingua.d.pengu` emits `include "utf8.h"`; `std/regulus.d.pengu` emits
`include "re.h"` and `link "re"`. The build manager processes those directives
only for modules actually imported, so a program that uses neither module
contains neither header and links no `libre.a`. `build_runtime.py` builds
`build/lib/libre.a` from `std_c/re.c` (it is not part of
`libpengu_runtime.a`). The matrix is enforced by
`tests/build/test_smart_linking.py`.

### 19.2 External bindings (satellite repositories)

Bindings to external C libraries are distributed as satellite repositories installed with `pengu add <url>`. See [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).

### 19.3 Core Standard Library Examples

#### Memory & C Interop (`std.ffi`)
Provides bridge routines between C pointers and PenguScript types. Memory views do **not** copy and must **not** be banished; conversions that return a container allocate a new one and copy the source bytes (the elements themselves are copied with `memcpy`, not cloned):

```pengu
import std.ffi
import std.spark

weave demonstrate_ffi with c_buf as ref to frozen byte, len as int into void:
    # 1. Borrow C memory as a slice view (zero allocations, non-owning)
    var view as slice of byte is calling ffi.slice_of_bytes_from_ptr with (transmute c_buf to ref to void), len
    calling spark.println with "Slice length: {view.length}"

    # 2. Convert null-terminated C string into an owned PenguScript string
    var c_str as ref to char is transmute c_buf to ref to char
    var owned_s as string is calling ffi.string_from_cstr with c_str

    # 3. Obtain non-owning null-terminated C string pointer from PenguScript string
    var back_to_c as ref to char is calling ffi.cstr_from_string with owned_s
    calling spark.println with "Converted string successfully"
```

#### String Manipulation (`std.scrolls`)
Pure PenguScript string algorithms operating through the `string` type enchantment:

```pengu
import std.spark
import std.scrolls

weave demonstrate_strings into void:
    var raw as string is "  PenguScript,Systems,Language  "
    var trimmed as string is calling raw.get_trim
    var parts as list of string is calling trimmed.split with ","

    for part in parts:
        var upper_part as string is calling part.get_upper
        if calling upper_part.contains with "SYSTEMS":
            calling spark.println with "Found target: {upper_part}"

    var sub as string is calling scrolls.substring with trimmed, 0, 11
    calling spark.println with "Substring: {sub}"
```

#### Multithreaded Concurrency (`std.filum`)
Thread spawning, mutual exclusion, wait groups, and channels:

```pengu
import std.spark
import std.filum

weave worker_routine with wg_ptr as ref to filum.WaitGroup, m_ptr as ref to filum.Mutex into void:
    calling filum.lock with m_ptr
    calling spark.println with "Inside synchronized critical section"
    calling filum.unlock with m_ptr
    calling filum.done with wg_ptr

weave demonstrate_concurrency into void:
    var m as filum.Mutex is calling filum.mutex
    var wg as filum.WaitGroup is calling filum.wait_group

    calling filum.add with (sigil of wg), 1
    # Run worker tasks with explicit handle passing
    calling worker_routine with (sigil of wg), (sigil of m)
    calling filum.wait with (sigil of wg)

    calling filum.free_mutex with (sigil of m)
    calling filum.free_wait_group with (sigil of wg)
```

#### Thick functions (`std.functor`)

A `Fn1` is a function pointer plus a borrowed context. Construction does the
only `transmute` once; every call is a plain C indirect call.

```pengu
import std.functor
import std.spark

rune Multiplier:
    factor as int

weave apply with m as ref to Multiplier, x as int into int:
    return m->factor * x

weave main into int:
    var m as Multiplier is with factor is 3
    var f as functor.Fn1 of int, int is calling functor.make_fn1 with apply, (sigil of m)
    calling spark.println with "{calling f.call with 5}"   # 15
    return 0
```

The context is borrowed, never owned: free it after the last call. A `Fn` is the
right tool when the callback must be **stored** (a field, a list, a struct) or
**returned**; when it is only invoked inside a loop, the `loom.*_ctx` family
needs no wrapper at all.

#### Pipelines with an explicit context (`loom.*_ctx`)

`map_ctx` and its nine siblings take the callback's context as an argument, so a
pipeline step can carry configuration without a closure:

```pengu
import std.loom
import std.spark

rune Scaler:
    factor as int

weave scale with s as ref to Scaler, x as int into int:
    return s->factor * x

weave main into int:
    var s as Scaler is with factor is 3
    var xs as list of int is [1, 2, 3]
    var ys as list of int is calling loom.map_ctx with xs, (sigil of s), scale
    calling spark.println with "{ys at 0} {ys at 1} {ys at 2}"   # 3 6 9
    banish ys
    return 0
```

`ctx` is borrowed for the duration of the (synchronous) call; the returned list
is new and belongs to the caller. `filter_ctx`, `fold_ctx`, `for_each_ctx`,
`zip_with_ctx`, `find_first_ctx`, `any_ctx`, `all_ctx`, `partition_ctx` and
`filter_map_ctx` follow the same contract.

### 19.4 Embedded Project Assets (`arca`)

PenguScript projects can bundle static files (shaders, audio, images, configs, fonts, templates, HTML/JS/CSS) directly into the executable via the `assets` feature. The compiler generates a pure PenguScript module (default: `src/arca.pengu`) and a C implementation (`build/arca_assets.c`).

#### Configuration (`pengu.yaml`)

```yaml
assets:
  dir: "assets"           # directory relative to project root
  module: "arca"          # module name (generates src/arca.pengu)
  embed: true             # true = compiled into .rodata; false = runtime disk reader
  exclude: ["*.psd", "*.tmp"]
```

#### API Reference (`arca`)

All functions are pure, null-safe, and self-contained:

| Function | Signature | Description |
|---|---|---|
| `count` | `weave count into int` | Total number of tracked assets. |
| `name` / `name_at` | `weave name with index as int into string` | Logical relative path of the $i$-th asset (0-indexed). |
| `has` / `exists` | `weave has with name as string into bool` | `true` if an asset with `name` exists and has non-zero size. |
| `size` | `weave size with name as string into usize` | Size in bytes (0 if not found). |
| `ptr` | `weave ptr with name as string into ref to frozen void` | Direct pointer to asset bytes in `.rodata` or heap cache (`null` if not found). |
| `bytes` | `weave bytes with name as string into slice of byte` | Non-owning slice view over the asset bytes (do not `banish`). |
| `string` | `weave string with name as string into string` | Content as an **owned string** (`PenguString` copy, safe to `banish` or store). |

> [!NOTE]
> **Memory Model:**
> - `arca.string(name)` returns an **owned copy** of the asset as a `string` (via `pengu_string_new`). It is safe to store in structs, pass across threads, or release with `banish`.
> - `arca.bytes(name)` and `arca.ptr(name)` return **read-only views** directly referencing the embedded binary section (`.rodata`) in `embed: true` mode, or the internal memory cache in `embed: false` mode. They do not allocate heap memory and must **never** be banished or freed.

#### Supported Formats & Format Agnosticism

PenguScript asset embedding is completely binary and format-agnostic. The bytes are preserved 1:1 without modification or re-encoding. Common file types include:
- **Images**: PNG, JPG/JPEG, QOI, BMP, SVG
- **Audio**: WAV, OGG, MP3, QOA, FLAC
- **Shaders & 3D**: GLSL (`.vs`, `.fs`), HLSL, WGSL, OBJ, MTL, GLTF/GLB
- **Web & UI**: HTML, CSS, JS, WASM, JSON, SVG
- **Fonts & Data**: TTF, OTF, FNT, TOML, YAML, CSV, SQLite database files

#### Asset Constants

Constants for every tracked asset are emitted with a deterministic, collision-free identifier format (`ASSET_<MODULE>_<CLEANED>_<SHA1_8>`):
- **`CLEANED`:** The relative file path with all non-alphanumeric characters replaced by underscores and converted to uppercase (`re.sub(r"[^A-Za-z0-9]", "_", name).upper()`). If the cleaned name begins with a digit, a leading underscore `_` is prepended.
- **`SHA1_8`:** The first 8 hexadecimal characters of the uppercase SHA-1 digest of the UTF-8 relative path string:
  ```python
  hashlib.sha1(name.encode("utf-8")).hexdigest()[:8].upper()
  ```
- **Prefix:** `ASSET_` when using the default module `arca`, or `ASSET_<MODULE>_` when a custom module name is configured in `pengu.yaml` (e.g. `ASSET_RECURSOS_`).

This ensures unique, C99-compliant identifiers even when filenames differ only by punctuation, path separators, or case:

```pengu
const ASSET_LOGO_PNG_A731E040 as string is "logo.png"
const ASSET_SHADERS_GRAYSCALE_FS_E362493E as string is "shaders/grayscale.fs"
```

You can pass either the generated constant (`arca.ASSET_LOGO_PNG_A731E040`) or the string literal (`"logo.png"` / `"shaders/grayscale.fs"`). Run `pengu assets --list` to view all constants and file sizes.

#### Usage Examples

The graphics and desktop-UI bindings that used to be shown here now ship as
satellite repositories installed with `pengu add`; see
[`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).

**Decoding an Embedded Image Through a Satellite Binding:**
```pengu-fragment
import arca
import mylib
import std.ffi
import std.spark

weave main into int:
    # Borrow the embedded bytes directly from .rodata (zero disk I/O)
    var p_logo as ref to frozen void is calling arca.ptr with "logo.png"
    var sz_logo as usize is calling arca.size with "logo.png"

    # Decode through the satellite binding; it owns the returned handle
    var img as mylib.Image is calling mylib.image_from_memory with (transmute p_logo to ref to frozen byte), (sz_logo to int)
    defer calling mylib.release with img

    calling spark.println with "Decoded embedded image"
    return 0
```

**Serving an Embedded HTML Interface:**
```pengu-fragment
import arca
import mylib
import std.spark

weave main into int:
    var html as string is calling arca.string with "ui/index.html"
    var w as mylib.Window is calling mylib.window_open with "Embedded UI"
    calling mylib.window_show with w, html
    calling mylib.window_wait with w
    return 0
```

### 19.5 Memory model: borrowed `string` parameters and expression temporaries

Manual memory (§13) is the rule; the compiler only steps in where a temporary it
created would otherwise leak. Four rules cover the whole model:

- **A `string` parameter is borrowed.** The callee may read it for the duration
  of the call; it must not `banish` it and must not keep it past the return. The
  caller keeps ownership. This is the contract `std.spark.println` relies on.
- **A temporary the caller creates for a call is released by the caller.** An
  interpolation (`"{a} {b}"`) or a `to string` conversion allocates a
  `PenguString` that the callee only borrows. The call is emitted inside a GNU
  statement expression that binds the temporary, makes the call and banishes it:

```c
(__extension__(({ PenguString _arg_1 = (pengu_string_format_ex(...));
                  spark_println(_arg_1);
                  pengu_banish_string(&_arg_1); })))
```

  The release happens only when it cannot dangle. It is unconditional for a
  `void` or scalar result (numbers, `bool`, `char`, a plain `omen`). For a
  `string` result it is guarded — `if (res.data != arg.data)
  pengu_banish_string(&arg)` — because a callee may return its parameter
  (`weave id with s as string into string: return s`) and the returned buffer
  must survive. For a reference, rune or container result (including
  `maybe`/`result`) nothing is released: the result could have stored the
  borrowed pointer.
- **A value the caller already owns is never released.** A variable, a field or
  a call result passed as an argument stays with the caller: `calling
  spark.println with s` does not free `s`, and you still write `banish s`.
- **`strict_c99: true` has no statement expressions.** A call in *statement*
  position releases through a plain block (bind, call, banish); a call in
  *value* position cannot, and keeps the old behaviour (no release).

`return` unwinds loops too: it releases every active loop temporary before the
frame is popped, so a `for v in calling make_list()` cannot leak when the body
returns early — the element is copied into the loop variable before the release.
The same rule drives labeled jumps (§7.5): a `break` / `continue label` releases
the temporaries of every loop it leaves, and the owning loop's `_break` anchor
sits *before* its release, so the normal exit and a jump out of the loop both
run it.

A complete program — the interpolation is a caller-owned temporary, released as
soon as `spark.println` returns:

```pengu
import std.spark

weave greet with name as string, n as int into int:
    calling spark.println with "hello {name}, n={n}"   # temporary freed after the call
    return n

weave main into int:
    return calling greet with "pengu", 2
```

**Generated C is warning-clean for unused bindings.** A parameter or local the
program never reads is emitted with a `(void)name;` cast, so a program that
binds a value and ignores it still compiles under `-Wall -Wextra -Werror`.
`type of p` is the sharpest case: it inspects the static type and never emits
`p`, so that parameter counts as unread and gets the cast.

---

## 20. Tooling & project layout

The `pengu` unified command-line toolchain manages project creation, compilation, testing, formatting, C header binding generation, documentation, and Language Server Protocol (LSP) integration.

### 20.1 Project Initialization (`pengu init`)

Generates a new project directory with standard folder structure, gitignore, and boilerplate:

```bash
pengu init <name> [--type {exe,c,obj,static,shared}] [--links LINKS] [--output-name OUTPUT_NAME] [--cc CC]
```

- `--type, -t`: Target artifact format:
  - `exe`: Standalone native executable (default).
  - `c`: Transpiled single-file C source bundle (`build/bundle.c`).
  - `obj`: Compiled native object file (`.o` / `.obj`).
  - `static`: Compiled static library (`.a` / `.lib`).
  - `shared`: Compiled dynamically linked shared library (`.so` / `.dll` / `.dylib`).
- `--links, -l`: Comma-separated native C libraries to link (e.g. `mylib,m,pthread`).
- `--output-name`: Custom output binary base name.
- `--cc`: C compiler override (default: `gcc`).

### 20.2 Compilation & Build Profiles (`pengu build`)

Compiles the PenguScript project into the designated target:

```bash
pengu build [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--output OUTPUT] [--test] [--cc CC] [--verbose] [-D DEFINES]
            [--strict-c99] [--target-compiler {gcc,clang,msvc,tcc,emcc}]
```

- `--profile, -p`: Selects optimization and diagnostic profiles:
  - `debug` (default): Includes debug symbols (`-g`), runtime bounds checking (`pengu_assert_bounds`), runtime callstack tracking (`pengu_frame_push`/`pop`), and asserts.
  - `release`: Maximizes performance (`-O3`) and disables runtime callstack tracking for zero overhead. Bounds and overflow checks **stay on** in this profile (roadmap 5.2): the only opt-out is `--release-unsafe` or an explicit `unsafe:` block.
  - `small`: Maximizes size reduction (`-Os`, no unwind tables, `-fno-ident`, `-fno-plt`) while keeping the same section garbage collection as `release`. Intended for embedded binaries or for distribution across many platforms.
- `--test`: Includes and compiles all top-level `test` blocks into the executable bundle.
- `-D, --define`: Sets compile-time variables for `when` conditions (e.g. `-D os=linux`, `-D arch=x64`, `-D compiler=clang`, `-D debug`, `-D main`). Repeatable.
- `--verbose`: Emits detailed phase timings, module resolution order, and invoked C compiler commands. Since 2.0 it also prints, as `std modules imported:` and `native archives linked:` lines, exactly which `std` modules entered the bundle and which native archives were passed to the linker.
- `--config, -c`: Path to custom `pengu.yaml` or project root.
- `--entry, -e`: Overrides root entrypoint file (default: `src/main.pengu`).
- `--output, -o`: Custom target output path (e.g. `build/bundle.c` or `build/game.exe`).
- `--strict-c99`: Emits C99-oriented output instead of GNU statement expressions.
  By default the generated C uses `__extension__(({ ... }))` (a GCC/Clang
  extension); with this flag expression-level temporaries are *hoisted* into the
  enclosing statement, which removes `__auto_type` from the bundle. Can also be set
  with `PENGU_STRICT_C99=1` or `build: strict_c99: true` in `pengu.yaml`. The GNU
  path remains the default, so existing builds are unaffected.

  > [!WARNING]
  > **⏸️ `--strict-c99` is not functional for programs that import `std` in
  > 0.16.0. Deferred to 1.1. Do not use it as a CI or release portability gate.**
  >
  > Measured: the `tests/std_programs/` corpus used for this measurement was
  > removed by the std 2.0 migration, so the count is **`[recalcular]`**. Three
  > independent causes:
  >
  > | Cause | Programs | Signature |
  > |---|---|---|
  > | Index hoisted out of the loop that declares its operand | `[recalcular]` | `'k' undeclared` |
  > | Statement-expressions `({...})` remaining in strict bundles | `[recalcular]` | `ISO C forbids braced-groups within expressions` |
  > | Qualifier/cast diagnostics | `[recalcular]` | `discards 'const' qualifier`, `casting nonscalar` |
  >
  > A minimal reproduction is 4 lines:
  >
  > ```pengu
  > weave main into int:
  >   var xs as list of int is [1, 2, 3]
  >   var ys as list of int is [4, 5, 6]
  >   var zs as list of int is for k in xs then ((xs at k) + (ys at k))
  >   return 0
  > ```
  >
  > It emits `int64_t _p_idx_9 = (int64_t)(k);` **before** the `for` loop that
  > declares `k`. `_block_expr` hoists to the enclosing statement's prelude, which
  > in GNU mode is harmless because `({ ... })` creates a scope enclosing the loop
  > variable, and in strict mode is out of scope. See `AUDIT_1.0_FASE3.md` §6–§7.
- `--target-compiler`: Selects the C dialect used for attributes and `restrict`
  (`gcc`, `clang`, `msvc`, `tcc`, `emcc`; default: inferred from `--cc`). Also
  `PENGU_TARGET_COMPILER` or `build: target_compiler:` in `pengu.yaml`.
  `emcc` is clang with a different driver, so it takes the GNU column below and
  the plain `restrict` spelling; `--cc emcc` infers it automatically, and
  `--target-compiler gcc|clang|emcc` are all coherent with it.

Attribute mapping per target:

| Pengu attribute | GCC / Clang / TCC / emcc | MSVC (`cl.exe`) |
| --- | --- | --- |
| `@inline` | `static inline __attribute__((always_inline))` | `static __forceinline` |
| `@cold` | `__attribute__((cold))` | omitted (no direct equivalent) |
| `@deprecated("m")` | `__attribute__((deprecated("m")))` | `__declspec(deprecated("m"))` |
| `@packed` | `__attribute__((packed))` | `#pragma pack(push, 1)` … `#pragma pack(pop)` |
| `@align(N)` | `__attribute__((aligned(N)))` | `__declspec(align(N))` |
| `restrict` (opt-in) | `restrict` | `__restrict` |

**Binary size and section garbage collection (2.0).** The `release` and `small`
profiles compile every object with `-ffunction-sections -fdata-sections` and link
with `-Wl,--gc-sections` (GNU ld / lld) or `-Wl,-dead_strip` (macOS ld64), so the
linker drops every function the program does not reach. `build_runtime.py` compiles
`libpengu_runtime.a` with the same flags — without that half the *section GC* can
prune nothing, because a static archive is resolved per *member* (`.o`), not per
symbol.

The core runtime links only `libc`, `libm` and `pthreads`; there is no conditional
native linking any more. Bindings to external C libraries are installed per project
as satellite repositories (`pengu add <url>`, see
[`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)) and declare their own native
archives, which the project's build passes to the linker.

### 20.2.1 Runtime ABI version

`pengu_runtime.h` defines `PENGU_ABI_VERSION 2`, the frozen layout of the runtime
containers (`PenguString`, `PenguSlice`, `PenguList`, `PenguMap`, `PenguMaybe`,
`PenguResult`, `PenguRange`). The exact sizes/offsets for 64-bit targets are
documented next to the macro and asserted by `tests/abi/test_abi_layout.c`. A
mismatch means a prebuilt `libpengu_runtime.a` was compiled against a different
ABI than the generated bundle.

**`libpengu_runtime.a` is a build requirement.** `pengu build` always links it
(regardless of `links` in `pengu.toml`) and every bundle references
`pengu_abi_version()`, so an archive built against a different ABI fails at link
instead of reinterpreting struct fields. If the archive is missing the build
stops before invoking the C compiler with an actionable message
(`python build_runtime.py`), rather than an `undefined reference`. The link-time
guarantee is verified under **gcc** and **clang**; **tcc** strips its output, so
the symbol cannot be inspected there — see [`docs/ABI.md`](docs/ABI.md).

### 20.2.2 Machine-readable diagnostics (`--json`)

`pengu check --json` and `pengu build --json` emit JSON Lines (nothing else on
stdout), so CI can parse them directly:

```bash
pengu check --json | jq -c 'select(.type=="diagnostic") | {file,line,col,code}'
```

- one `{"type":"diagnostic","file","line","col","code","severity","message",
  "help","note"}` object per problem;
- a final `{"type":"summary","ok":<bool>,"errors":<n>,"duration_ms":<ms>}`
  (`build` adds `artifact`, `cached` and `profile`). `check` and `build` exit 1
  when `ok` is false.

### 20.2.3 Cross-compilation (`--target`)

```bash
pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc
```

- `--target <triple>` (`build`, `run`, `test`; or `build: target:` in
  `pengu.yaml`) selects the target OS from a triple such as
  `x86_64-w64-mingw32`, `i686-w64-mingw32`, `aarch64-apple-darwin` or
  `x86_64-unknown-linux-gnu`. **Linux ⇄ Windows** and
  **wasm32-unknown-emscripten** are the supported targets; see §20.2.3.1 for
  WebAssembly and `docs/WASM.md` for its limitations.
- Artifact extensions follow the target (`.exe`, `.dll`, `.dylib`, `.so`) and so
  do the native archives declared by the project's satellite bindings.
- With a Windows target from a non-Windows host the compiler is auto-detected
  (`<triple>-gcc`, `x86_64-w64-mingw32-gcc`, `i686-w64-mingw32-gcc`); `--cc`
  always wins. If none is installed the build fails with an actionable message.
- The shipped runtime archive is host-built. Generating the C bundle for another
  target needs nothing else, but *linking* a cross executable requires a runtime
  built for the target: point `PENGU_RUNTIME_CROSS` at its prefix and the build
  adds `-L<prefix>/lib -I<prefix>/include`. Satellite bindings must likewise provide
  native archives built for the target.

### 20.2.3.1 WebAssembly (`--target wasm32-unknown-emscripten`)

```bash
python build_runtime.py --target emscripten             # once: build/wasm/lib/libpengu_runtime.a
pengu build --target wasm32-unknown-emscripten          # build/app.html + app.js + app.wasm
pengu run   --target wasm32-unknown-emscripten          # builds, then runs app.js with node
pengu run   --target wasm script.pengu                  # 'wasm' is a shorthand for the full triple
```

- The backend is **Emscripten** (`emcc`/`emar`), invoked as a cross compiler.
  `emcc` is auto-detected, or passed with `--cc`; when it is missing the build
  stops with the emsdk installation commands instead of a linker error.
- `--target <triple>` (`build`, `run`, `test`; or `build: target:` in
  `pengu.yaml`). `wasm`, `wasm32` and `emscripten` are accepted shorthands.
  `when os == ...` sees `emscripten` for this target.
- **Artifacts.** `exe` → `app.html` (Emscripten also writes `app.js` and
  `app.wasm`; `node app.js` runs the program headlessly). `static` → `app.a`, an
  archive of wasm objects built with `emar`, linkable into another wasm bundle.
  `obj` → `app.o`. `c` → `bundle.c`, unchanged. `shared` is **refused**: a wasm
  side module needs `-fPIC` on every input, including the runtime archive.
- **The runtime archive is target-specific.** `build/lib/libpengu_runtime.a` is
  host-built and can never satisfy a wasm link, so the wasm search
  (`build/wasm/lib`, or `PENGU_LIB_DIR`/`PENGU_RUNTIME_CROSS`) is disjoint from
  the host one by design. A missing archive is reported before the compiler runs.
- **Threads.** `-pthread` is added exactly when the program imports
  `std.filum`, which is the same condition that switches `PENGU_ENABLE_THREADS`
  on in the bundle. Goroutines then become real Web Workers
  (`SharedArrayBuffer` + wasm atomics); in a browser that requires
  `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp`.
- **`exec`/`spawn`.** There is no process to spawn: `pengu_c_exec` and
  `pengu_c_spawn` return `-1` and write a diagnostic to stderr under
  `PENGU_EMSCRIPTEN`. They are unchanged on every other target.
- **WASI is not supported.** A `wasm32-wasi` target is recognized and refused
  with an explicit message; it is not silently treated as the host.
- Full details, limitations (the `static var` initialization race, why
  LeakSanitizer cannot see `filum` handle leaks, stdin) and troubleshooting live
  in [`docs/WASM.md`](docs/WASM.md).

### 20.2.4 Formatting (`pengu fmt`)

```bash
pengu fmt src/ --check        # exit 1 when a file would change (CI gate)
pengu fmt src/ --diff         # print a unified diff per changed file
pengu fmt --stdin < in.pengu  # format stdin to stdout
```

Formatting settings are read from the nearest `.pengufmt.toml`, `pengu.yaml` or
`pengu.toml` (walking up from each file), either at the root or under
`[formatting]`/`formatting:`. Both `key = value` (TOML) and `key: value` (YAML)
spellings work:

```toml
[formatting]
tab_size = 2          # or indent / indent_size
insert_spaces = true  # or use_tabs / tabs
blank_lines_max = 1   # collapse consecutive blank lines (never inside literals)
```

The language server also formats on type: typing `:` at the end of a block
opener indents the next line one level, and a newline after an opener indents
the fresh line.

### 20.2.5 Documentation (`pengu doc`)

`pengu doc` renders a Markdown reference plus a self-contained search page:

- Doxygen tags in `##` comments (`@param`, `@return`, `@see`, `@deprecated`, …)
  become a structured bullet list;
- symbols marked `@deprecated` show a deprecation badge and a `[deprecated]`
  marker in the index;
- `docs/index.md` groups every symbol by kind (concepts, runes, echoes, omens,
  seals, aliases, constants, functions, C declarations);
- `docs/index.html` embeds the symbol index as JSON and offers a client-side
  search box (name / kind / module / signature / summary).


### 20.3 Execution & Script Mode (`pengu run`)

Compiles and immediately executes the project target:

```bash
pengu run [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--test] [--cc CC] [--verbose] [-D DEFINES] [script]
```

- `[script]`: When an optional `.pengu` source file is provided (e.g. `pengu run hello.pengu`), the compiler executes it as a standalone script on the fly, evaluating its `when main:` conditional blocks without requiring a full project directory.
- **The compiled binary is cached by content hash** (`~/.cache/pengu/scripts/<key>/app`), so an unchanged script starts in milliseconds and never touches the project's `build/` directory. `--keep` builds into `build/<name>_run/` instead, `--no-cache` bypasses the cache, `--ephemeral` uses a throw-away directory (CI) and `--clear-cache` empties the store.
- Arguments after `--` are forwarded to the script (`std.rites.get_args`).
- `PENGU_CACHE=0` disables the caches, `PENGU_DEV_CC`/`PENGU_TCC`/`PENGU_NO_TCC` control the compiler choice. See `docs/PERFORMANCE.md`.

### 20.3.1 Diagnostics, cache and one-liners

| Command | What it does |
| ------- | ------------ |
| `pengu doctor [--json]` | Reports the compiler, TCC availability, runtime header, `std/`, cache paths and write permissions. |
| `pengu gc [--all] [--max-age N]` | Collects cached script binaries older than N days (30 by default). |
| `pengu expand FILE.pengu [-o OUT]` | Prints the generated `bundle.c` (useful to inspect dead-code elimination). |
| `pengu time FILE.pengu` | Runs the script and prints per-phase timings (imports, check, codegen, C compiler, run). |
| `pengu eval "EXPR"` | Wraps the expression in a temporary script, compiles it through the cache and prints the result. |
| `pengu watch FILE.pengu` | Re-runs the script whenever it or any module it imports changes. |

Global flags: `--quiet`, `--no-color` (or `NO_COLOR=1`) and `--verbose`.

### 20.4 Integrated Unit Testing (`pengu test`)

Compiles and runs all `test "..."` blocks defined across the project:

```bash
pengu test [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--cc CC] [--verbose] [-D DEFINES] [--json] [--watch]
```

- `--watch`: Runs in file-watcher mode, automatically recompiling and re-executing unit tests whenever any `.pengu` file is modified.
- `--json`: Emits machine-readable JSON Lines to `stdout` for CI/CD integration, containing test results, duration, and failure diagnostics.

### 20.5 Fast Type Checking (`pengu check`)

Validates project syntax and types without invoking GCC/Clang or emitting C code:

```bash
pengu check [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--cc CC] [--verbose] [-D DEFINES]
```

- Rapidly type-checks all ASTs and verifies module symbol tables. Ideal for git pre-commit hooks and continuous integration lint steps.

### 20.6 C Header Binding Generator (`pengu bind`)

Translates C header files (`.h`) directly into native PenguScript declaration bindings (`.d.pengu`):

```bash
pengu bind <header> [--prefix PREFIX] [--links LINKS...] [--output OUTPUT] [--no-comments] [--ignore IGNORE...] [--include-paths INCLUDE_PATHS...] [--define DEFINES] [--cpp-flags CPP_FLAGS] [--system-includes] [--preprocessed FILE.i] [--no-blank-extensions] [--no-cpp] [--auto-import DIR]
```

- Automatically blanks GNU compiler extensions (`__attribute__`, `__asm__`, `__extension__`) prior to parsing.
- `--define, -D`: Defines C preprocessor macros (e.g. `-D Z_SOLO`).
- `--cpp-flags`: Raw preprocessor flags (e.g. `"-DZ_SOLO -DXXH_INLINE_ALL=0"`).
- `--system-includes`: Preserves system compiler headers instead of minimal stubs.
- `--preprocessed FILE.i`: Bypasses preprocessor invocation and parses an existing `.i` file directly.
- `--auto-import DIR`: Automatically emits `import` statements for sibling `.d.pengu` bindings corresponding to included headers.
- `--links`: Emits `link "..."` directives in the binding output.

### 20.7 Source Code Formatter (`pengu fmt`)

Formats `.pengu` source files according to the standard style conventions:

```bash
pengu fmt <paths...> [--check] [--write] [--indent INDENT] [--tabs] [--verbose]
```

- Enforces 2-space indentation (configurable via `--indent` or `--tabs`).
- Strips trailing whitespace, normalizes block indentation, and preserves `#` / `##` comments intact.
- `--check`: Verifies formatting without writing back to disk; exits with non-zero status if changes are needed.
- Automatically skips any source file starting with `## @generated`.

### 20.8 Documentation Generator (`pengu doc`)

Generates Markdown documentation from source docstrings:

```bash
pengu doc [--config CONFIG] [--entry ENTRY] [--output OUTPUT]
```

- Extracts doc comments (`##`) preceding weaves, runes, concepts, omens, and constants across all project modules into structured Markdown files in `docs/`.

### 20.9 Embedded Assets Manager (`pengu assets`)

Inspects and updates embedded project assets:

```bash
pengu assets [--config CONFIG] [--list] [--force]
```

- Rebuilds `src/arca.pengu` and `build/arca_assets.c` from the configured `assets:` directory.
- `--list`: Displays all tracked asset files, their exact byte size, and their generated PenguScript constant identifiers.
- `--force`: Regenerates all asset tables unconditionally, bypassing modification caches.

### 20.10 Language Server Protocol (`pengu lsp`)

Powers IDE integration (VS Code, Neovim, Emacs, Helix):

```bash
pengu lsp [--stdio] [--tcp] [--host HOST] [--port PORT]
```

- `--stdio`: Standard I/O communication (default for editor sub-processes).
- `--tcp`, `--host`, `--port`: Runs the LSP server over a TCP socket (default port: `2087`).
- Capabilities:
  - Real-time diagnostic reporting with Rust-like caret spans.
  - Contextual code completion (keywords, runes, methods, local variables, module symbols).
  - Hover information showing type signatures, docstrings, and calculated struct memory sizes/alignments.
  - Go to definition and go to implementation.
  - Find references and workspace symbol search.
  - Document symbol outline and workspace symbols.
  - Rename symbol across files.
  - Code actions: import module, remove unused symbols, implement concept methods.
  - Document formatting.

### 20.11 Dependency Management (`pengu add` & `pengu update`)

Integrates external PenguScript modules and C bindings:

```bash
pengu add <source> [--branch BRANCH] [--name NAME] [--config CONFIG] [--no-build]
pengu update [--config CONFIG] [--verbose]
```

- `pengu add`: Clones a remote git repository or symlinks a local directory into `lib/<name>`, and records the dependency in `pengu.yaml`.
- `pengu update`: Performs `git pull` across all dependencies in `lib/` and re-runs dependency build scripts.

### 20.12 Project Clean (`pengu clean`)

Cleans the project workspace:

```bash
pengu clean [--config CONFIG]
```

- Deletes the `build/` directory, compiled objects, C bundles, and temporary caches.

### 20.12.1 Benchmarks (`pengu benchmark`)

Runs the reproducible harness in `benches/` and prints per-case build time, run
time (best of N) and stripped artifact size, plus the environment block:

```bash
pengu benchmark [--repeat N] [--csv FILE] [--only CASE]
```

- Measures the PenguScript program and, when their toolchain is installed, the C/
  Rust/Zig baselines; a missing toolchain is reported as `skipped`, never as a win.
- `--only`: a single case by name (`hello_world`, `fib_40`, `string_ops`,
  `list_ops`, `stdlib_ops`).
- `stdlib_ops` is the case that goes through `std` (`std.tally` + `std.spark`);
  the others measure the bare language on purpose.
- The published numbers live in [`BENCHMARKS.md`](BENCHMARKS.md).

### 20.13 Toolchain Versioning (`pengu -V` / `--version`)

```bash
pengu -V
pengu --version
```

- Outputs the version string (e.g. `PenguScript v2.0.0`). The compiler version is tracked in `VERSION` and mirrored in `pengu_version.py`.

### 20.14 Runtime Infrastructure & Diagnostics

#### Minimal Runtime Backtraces
The runtime maintains a lightweight, thread-local circular frame ring buffer:
- `pengu_frame_push(fn_name, file, line)` and `pengu_frame_pop()` record active callstack frames up to `PENGU_MAX_FRAMES` (64 by default).
- Crash handlers for `SIGSEGV`, `SIGABRT`, `SIGFPE` (integer division by zero), `SIGILL` and `SIGBUS` (and `SetUnhandledExceptionFilter` on Windows) intercept fatal errors and write the callstack — with `.pengu` source filenames and line numbers — directly to `stderr`. The handler is **async-signal-safe**: it formats with hand-written primitives and calls only `write(2)`/`_exit()`, never `snprintf`, `malloc` or stdio. A weave's returned expression is evaluated *before* its frame is popped, so a fault inside it (e.g. `return a / b`) is attributed to that weave rather than to its caller.

#### Bounds Checking (on in every profile)
- Indexing operations (`xs at i` and `set xs at i`) emit bounds assertions (`pengu_assert_bounds`), halting with a callstack trace on out-of-bounds access. They are emitted in **every** profile (roadmap 5.2), not only under `debug`.
- The only opt-out is an explicit `unsafe:` block (which emits `[W0007]`) or `pengu build --release-unsafe`; `--profile release` does not disable them.

#### `#line` Directives
Generated C code carries `#line` directives mapping every C statement back to the originating `.pengu` source file and line. C compiler diagnostics and GDB/LLDB debuggers point directly to the PenguScript source.

#### Program Arguments & Exit Codes
- `int32_t pengu_main(void)` returns the process exit code (`0` for success).
- The C `main(argc, argv)` initializes the runtime via `pengu_init(argc, argv)` before invoking `pengu_main`, ensuring `std.rites.get_argc()`, `get_argv()`, and `get_args()` receive authentic OS arguments.

#### Standard Project Directory Layout

```
my_project/
├── pengu.yaml          # Project configuration (dependencies, build flags, assets)
├── src/
│   ├── main.pengu      # Entrypoint module
│   └── arca.pengu      # Auto-generated embedded assets module (optional)
├── assets/             # Static game/application assets (optional)
├── lib/                # External dependencies and C bindings
├── c/                  # Native C/C++ helper source files (compiled automatically)
└── build/              # Output binaries, object files, and bundle.c (gitignored)
```

---

## 21. Complete example

```pengu
import std.spark
import std.scrolls
import std.tally

# --- Types --------------------------------------------------------------
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
        return self->name

enchanting Player:
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100

    weave damage with amount as int into void:
        set self->hp is self->hp - amount
        if self->hp < 0:
            set self->hp is 0

# --- Generics -----------------------------------------------------------
rune Pair shard A, B:
    first as A
    second as B

weave first_of shard A, B with p as Pair of A, B into A:
    return p.first

# --- Main Entrypoint ---------------------------------------------------
weave main into int:
    var hero as Player with:                    # Block-style builder construction
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
    calling spark.println with "sum: {((calling tally.sum with scores) to string)}"
    var part as string is calling scrolls.substring with "done", 0, 4
    calling spark.println with part

    var ok as maybe int is some 1
    if ok.is_present:
        return 0
    return 1
```

Generated C is a single translation unit containing struct layouts (`struct Player`, `enum Phase`), monomorphized types (`Pair_int_string`), methods (`Player_new_hero`, `Player_damage`), and the entrypoint wrapper `pengu_main(void)`.

---

## 22. Appendix: Compiler Diagnostic Catalog

PenguScript uses a Rust-inspired compiler diagnostic reporter with ANSI color output, line gutters, caret span underlines, error codes (`[Exxxx]`), `note:`, and `help:` hints.

### 22.1 Diagnostic Format

When an error occurs, the compiler formats the diagnostic as follows:

```text
error[E0006]: cannot assign to immutable variable 'count'
  --> src/main.pengu:14:5
   |
14 |     set count is count + 1
   |     ^^^^^^^^^^^^^^^^^^^^^^ cannot assign to 'let' binding
   |
   = note: 'let' bindings are immutable by default.
   = help: Declare the variable with 'var' instead of 'let' to allow mutation.
```

<!-- BEGIN GENERATED DIAGNOSTIC CATALOG — tools/gen_error_catalog.py -->

### 22.2 Compiler Error Catalog (`E0000`–`E0069`)

Generated from the compiler sources by `tools/gen_error_catalog.py` (error classes and their `code=` defaults in [`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py), every `code="Exxxx"` emission in `pengu_parser/`, `pengu_project.py` and `pengu_lsp/`).  The machine-readable form of this table is [`docs/error_catalog.json`](docs/error_catalog.json); `tests/test_error_catalog_sync.py` fails when the code and this table diverge, so **do not edit it by hand** — run `python tools/gen_error_catalog.py --write`.

`Conditions` is the number of distinct message shapes the code can carry (interpolated values are shown as `{}`).  `help:`/`note:` lists how many guidance pairs are attached to the code.

| Code | Exception class | Conditions | Explanation | help: / note: |
|---|---|---|---|---|
| `E0000` | `ParseError`, `SemanticError` | 3 | the source text could not be parsed (syntax error).  Raised by ``PenguParser.parse`` instead of leaking a raw Lark exception, so the CLI/LSP can report syntax problems with the usual ``[Ecode] message`` + ``help:`` / ``note:`` shape. Kept on the generic E0000 code: syntax problems share the "not valid source" bucket with the other infrastructure errors instead of consuming a new semantic code. | 1 help / 1 note |
| `E0001` | `ConstInsideWeaveError` | 1 | const declared inside weave / function body. | 1 help / 1 note |
| `E0002` | `VarLetTopLevelError` | 3 | var/let declared at top-level. | 1 help / 1 note |
| `E0003` | `SelfDotAccessError`, `SemanticError` | 7 | self accessed with dot instead of arrow. | 1 help / 1 note |
| `E0004` | `SemanticError`, `UndefinedIdentifierError` | 16 | identifier not defined in symbol table. | 1 help / 1 note |
| `E0005` | `ConceptBoundNotSatisfiedError`, `SemanticError`, `TypeMismatchError` | 152 | types incompatible. | 1 help / 1 note |
| `E0006` | `InvalidMemoryOpError`, `MutabilityError` | 12 | assignment to immutable let binding or constant. | 1 help / 1 note |
| `E0007` | `InvalidControlFlowError` | 2 | break/continue outside loop. | 1 help / 1 note |
| `E0008` | `InvalidMemoryOpError`, `SemanticError`, `TypeMismatchError` | 15 | invalid sigil/banish on literal/const. | 1 help / 1 note |
| `E0009` | `InvalidWithTargetError`, `SemanticError` | 2 | leading dot access outside with block. | 1 help / 1 note |
| `E0010` | `SemanticError` | 1 | — | — |
| `E0011` | `SemanticError` | 1 | — | — |
| `E0012` | `SemanticError` | 1 | — | — |
| `E0013` | `SemanticError`, `TypeMismatchError` | 10 | — | — |
| `E0014` | `InvalidBuilderStatementError`, `SemanticError`, `TypeMismatchError` | 10 | invalid statement inside with: builder block. | 1 help / 1 note |
| `E0015` | `SemanticError`, `UnknownArrayDimensionError` | 4 | Array dimension size is unknown and cannot be inferred. | 1 help / 1 note |
| `E0016` | `UndefinedIdentifierError` | 1 | — | — |
| `E0017` | `SemanticError` | 5 | — | — |
| `E0018` | `TypeMismatchError` | 1 | — | — |
| `E0019` | `SemanticError`, `UndefinedIdentifierError` | 3 | — | — |
| `E0020` | `SemanticError`, `TypeMismatchError` | 9 | — | — |
| `E0021` | `GenericTypeMissingArgsError` | 1 | Generic type used without required type arguments. | 1 help / 1 note |
| `E0022` | `TypeParamOutsideGenericError` | 1 | Type parameter used outside generic declaration context. | 1 help / 1 note |
| `E0023` | `MultipleManyParamsError` | 2 | Multiple many parameters in a function. | 1 help / 1 note |
| `E0024` | `ManyParamNotLastError` | 2 | many parameter is not the last parameter. | 1 help / 1 note |
| `E0025` | `SemanticError` | 2 | — | — |
| `E0026` | `MultipleInsigniaError` | 1 | Multiple insignia directives in a single file. | 1 help / 1 note |
| `E0027` | `DuplicateOmenValueError` | 1 | Duplicate variant value in omen. | 1 help / 1 note |
| `E0028` | `InvalidOmenPayloadValueError` | 1 | Value assignment in algebraic omen variant with payload. | 1 help / 1 note |
| `E0029` | `InvalidOmenConstantValueError`, `SemanticError` | 3 | Non-constant or non-integer value in omen variant. | 1 help / 1 note |
| `E0030` | `ConceptMethodMismatchError` | 3 | Concept method signature mismatch in bind implementation. | 1 help / 1 note |
| `E0031` | `UnimplementedConceptMethodError` | 1 | Missing required concept method implementation. | 1 help / 1 note |
| `E0032` | `ConceptBoundNotSatisfiedError`, `SemanticError` | 4 | Generic type argument does not implement required concept bound. | 1 help / 1 note |
| `E0033` | `InvalidRitualSelfAccessError` | 1 | Using 'self' inside a ritual (static) method. | 1 help / 1 note |
| `E0034` | `InvalidRitualCallError` | 2 | Calling instance method statically or ritual method on instance. | 1 help / 1 note |
| `E0035` | `SemanticError` | 5 | — | — |
| `E0036` | `SemanticError` | 2 | — | — |
| `E0037` | `SemanticError` | 1 | — | — |
| `E0038` | `SemanticError` | 1 | — | — |
| `E0039` | `SemanticError`, `TypeMismatchError` | 3 | — | — |
| `E0040` | `SemanticError` | 2 | — | — |
| `E0041` | `ArraySizeMismatchError`, `SemanticError` | 9 | Array literal dimensions or row length do not match declared size. | 1 help / 1 note |
| `E0042` | `InvalidRangeError` | 3 | Invalid range expression bounds. | 1 help / 1 note |
| `E0043` | `PrivateSymbolAccessError` | 2 | Attempted access to private symbol from another module. | 1 help / 1 note |
| `E0044` | `NonExhaustiveJudgeError` | 3 | Non-exhaustive judge expression without default else clause. | 1 help / 1 note |
| `E0045` | `SemanticError`, `TypeMismatchError` | 4 | — | — |
| `E0046` | `SemanticError` | 5 | — | — |
| `E0047` | `DuplicatePrimitiveMethodError` | 2 | a method of a primitive is provided twice.  ``enchanting int:`` emits the C function ``int_clamp`` with external linkage, so the ``(primitive, method)`` pair may only be provided once in the whole program: two modules (or two blocks in one module) would emit the same symbol, and a call site could not choose between them. | 1 help / 1 note |
| `E0049` | `SemanticError` | 10 | — | — |
| `E0050` | `InfiniteTypeSizeError` | 1 | recursive type without indirection (infinite size). | 1 help / 1 note |
| `E0051` | `SemanticError` | 1 | — | — |
| `E0052` | `DuplicateConceptBindingError` | 2 | duplicate concept binding or duplicate (type, method) implementation.  Covers two cases: binding the same ``(type, concept)`` pair twice, and two distinct concepts providing the same ``(type, method)`` pair (which a call site could not resolve). | 1 help / 1 note |
| `E0053` | `SemanticError` | 3 | — | — |
| `E0054` | `SemanticError` | 1 | — | — |
| `E0055` | `SemanticError` | 1 | — | — |
| `E0056` | `SemanticError`, `UnknownAttributeError` | 9 | unknown attribute or invalid attribute usage. | 1 help / 1 note |
| `E0057` | `InvalidCharLiteralError` | 2 | char literal cannot hold codepoint > 0x7F. | 1 help / 1 note |
| `E0058` | `SemanticError` | 1 | — | — |
| `E0059` | `AntiquusBodyError` | 2 | an `antiquus` body is missing, empty, or not a triple-quoted string.  The C body of an ``antiquus`` declaration is literal text emitted into the generated ``bundle.c``; it must be delimited by ``"""…"""`` or ``r"""…"""`` so the extractor can lift it out before the textual preprocessing passes run.  A single-line ``"…"`` string cannot hold C line structure and is rejected here rather than silently compiling to an empty function body. | 1 help / 1 note |
| `E0063` | `StaticVarPlacementError` | 1 | 'static var' declared outside a function body.  A function-static variable is C's ``static`` local: it belongs to one weave and is created once.  Declaring it in a ``test`` block, at module top level, or nested inside a conditional has no coherent C translation, so it is rejected on placement rather than on type.  This used to share ``E0035`` with the "name collides with a C reserved word" diagnostic -- two conditions with nothing in common, which made a code-based quick-fix impossible (roadmap Phase 7, item 7.2). | 1 help / 1 note |
| `E0064` | `InvalidTestNameError` | 1 | a ``test`` block has no usable name.  Unit tests are reported by name, so ``test`` with an empty or ``_``-only name cannot be identified in the runner output.  This used to share ``E0035`` (roadmap Phase 7, item 7.2). | 1 help / 1 note |
| `E0065` | `CFieldCollisionError` | 1 | two PenguScript fields map to the same C field name.  ``_c_ident`` escapes C keywords by prefixing an underscore, so ``x`` and ``_x`` both emit the C field ``_x``.  The collision is between two *user* fields, not with a C reserved word, which is why it is not ``E0035``.  This used to share ``E0035`` (roadmap Phase 7, item 7.2). | 1 help / 1 note |
| `E0066` | `MutatingMethodInExpressionError` | 0 | a ``@mutates`` method used where a value is expected.  ``@mutates`` exposes one C function under two surface forms: the bare name assigns the result back to the receiver and yields nothing, while ``get_<name>`` returns the value.  The mutating spelling therefore has no value to contribute inside an initializer, an argument or a return, and it is rejected there instead of quietly behaving like the pure form. | 1 help / 1 note |
| `E0067` | `InvalidMutatesAttributeError` | 0 | ``@mutates`` applied where in-place mutation cannot work.  ``@mutates`` is only meaningful on a method inside an ``enchanting`` block, and only when the method returns the receiver's own type -- that return value is what the call site assigns back to the receiver.  A top-level ``weave``, a ``declare``, a mismatched return type or a body that both returns a value and assigns to the receiver is rejected here. | 1 help / 1 note |
| `E0068` | `MutatingGetterCollisionError` | 0 | ``@mutates weave foo`` collides with an explicit ``weave get_foo``.  The compiler reserves ``get_<name>`` for the pure form of a ``@mutates`` method, so declaring both would give ``get_<name>`` two definitions with no way to choose between them. | 1 help / 1 note |
| `E0069` | `DuplicateLabelError` | 1 | two loops in the same function declare the same label.  A loop label (``outer: for …``) is a *function-local* name; the code generator turns it into a single C label, so two loops sharing a name inside one function would emit two identical C labels.  The rule is deliberately stricter than "two nested loops may not share a name": two *sibling* loops with the same label are rejected as well, because the name no longer identifies one place to jump to. | 1 help / 1 note |

### 22.3 Compiler Warning Catalog (`W0000`–`W0013`)

Warnings are emitted as `"[Wxxxx] message"` strings; the symbolic name and the recommended practice come from `WARNING_CATALOG` in [`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py), which is also generated into [`docs/error_catalog.json`](docs/error_catalog.json).

| Code | Warning name | Conditions | Recommended practice |
|---|---|---|---|
| `W0000` | UncategorizedWarning | 0 | None — infrastructure fallback, used when a warning string does not match the '[Wxxxx] message' shape. |
| `W0001` | UnsafeTransmuteWarning | 2 | Use safe 'to <Type>' casting where possible, or verify that the memory layout sizes match. |
| `W0002` | UnsafeEchoAccessWarning | 1 | Untagged union reads are inherently unsafe; prefer algebraic 'omen' variants with payloads. |
| `W0003` | (reserved) | 0 | — |
| `W0004` | UnreachableCodeWarning | 2 | Remove dead code following unconditional returns or compile-time false branches. |
| `W0005` | ShadowedGlobalWarning | 2 | Rename the local, or qualify the call so the intent is explicit. |
| `W0006` | DeprecatedSymbolWarning | 2 | Migrate to the replacement named in the reason. CI can turn this into an error with --deny-deprecated. |
| `W0007` | UnsafeBlockWarning | 1 | Keep 'unsafe:' blocks as small as possible and document why they are sound. |
| `W0013` | RangeSyntaxDeprecated | 1 | Write 'a to b'. The '..' form keeps working through 1.x and is removed in 2.0. |

### 22.3.1 Project-layer diagnostics (`E0061`–`E0062`)

Emitted by the project layer (`pengu.lock` under `--locked`/`--frozen`, and dependency resolution) as plain `[Exxxx]` strings — **not** by the language compiler, and not through a `code=` keyword.  They share the `Exxxx` namespace, so the numbering is kept disjoint from §22.2 by `tests/test_error_catalog_sync.py`.

| Code | Conditions | Layer |
|---|---|---|
| `E0061` | 2 | project |
| `E0062` | 1 | project |

<!-- END GENERATED DIAGNOSTIC CATALOG -->

### 22.4 Illustrative Diagnostic Scenarios

#### Scenario 1: Top-Level Mutable State (`E0002`)
```pengu-invalid
# Invalid:
var counter as int is 0

# Fix: Use const or encapsulate in a stateful weave with static var:
const INITIAL_COUNTER as int is 0

weave next_counter into int:
    static var counter as int is 0
    set counter is counter + 1
    return counter
```

#### Scenario 2: Leading Dot Access Outside Builder (`E0009`)
```pengu-invalid
# Invalid:
set .hp is 100

# Fix: Wrap inside with block or assign directly to instance:
with player:
    set .hp is 100
# Or:
set player.hp is 100
```

#### Scenario 3: Non-Exhaustive Judge (`E0044`)
```pengu-invalid
# Invalid (missing Fighting variant):
let name is judge current_phase:
    when Phase.Idle -> "Standing by"

# Fix: Add missing variant or else branch:
let name is judge current_phase:
    when Phase.Idle -> "Standing by"
    when Phase.Fighting -> "In battle"
    else -> "Unknown"
```

#### Scenario 4: String Composition (`E0005`)
```pengu-invalid
# Invalid: '+' never concatenates strings.
var name as string is "world"
calling print with "Hello, " + name
#   E0005: Cannot concatenate strings with '+' (the left operand is 'string')
#   = help: Use string interpolation: "text{value}more". '+' only adds numbers.

# Fix: one interpolation literal composes the whole string:
calling print with "Hello, {name}"

# Invalid: '+=' on a string.
var acc as string is "a"
set acc += "b"
#   E0005: Cannot concatenate strings with '+='

# Fix: rebind through interpolation.
set acc is "{acc}b"
```

---

---

### 22.5 The executable compatibility corpus

The catalogue above describes the diagnostics; the behaviour they protect is
pinned by two corpora that **compile and execute** real programs, never by
inspecting text (project rule C1):

- [`tests/conformance/compliance/README.md`](tests/conformance/compliance/README.md) — one canonical
  program per section of this document, checked, built and run by the real
  toolchain (`pytest tests/test_compliance_corpus.py -q`). It pins the language
  **as it is today**.
- [`tests/migration/README.md`](tests/migration/README.md) — one program per
  published version line from `0.10.0` on, with the outcome `MIGRATION.md`
  documents for it (`pytest tests/test_migration_corpus.py -q`). It pins the
  syntax of every version the project has **shipped**, including the two
  pre-`0.10.0` forms the compiler now refuses with `E0000`/`E0005`.

Together they are what a 1.x compatibility claim is checked against: a change
that makes a compliance program stop passing, or that contradicts a migration
entry, is a break under §23 and needs a MAJOR release and a `MIGRATION.md`
update — not a quiet edit to the corpus.

---

## 23. Deprecation & Stability Policy

PenguScript follows strict [Semantic Versioning](https://semver.org): a version
is `MAJOR.MINOR.PATCH`, where `MAJOR` may break source compatibility, `MINOR`
adds backwards-compatible functionality (and may deprecate), and `PATCH` only
fixes bugs. From 1.0.0 onwards the rules below are binding.

### 23.1 What may change in a minor release

- **Additions** are always allowed: new weaves, new runes, new modules, new
  optional parameters with defaults, new warning codes.
- **Behaviour changes** in the standard library are allowed only when they fix
  a bug, and are called out in `CHANGELOG.md` under the affected module.
- **Removals and signature changes** are *never* allowed in a minor release.

### 23.2 Deprecating a symbol

Mark the symbol with the `@deprecated("reason")` attribute:

```pengu-fragment
## Reads a file. Prefer read_file_result for the failure cause.
## @deprecated use read_file_result to distinguish the failure cause
@deprecated("use read_file_result to distinguish the failure cause")
weave read_file_legacy with path as string into maybe string:
    return calling read_file with path
```

Using a deprecated symbol anywhere (call, type reference, field access, or
signature) emits the warning `[W0006]`:

```
main.pengu:4:0 [W0006] Symbol 'read_file_legacy' is deprecated: use read_file_result ...
```

`@deprecated` is supported on `weave`, `declare`, `rune` and their fields.

### 23.3 The two-release rule

A deprecated symbol must remain **fully functional for at least two minor releases**
before it can be removed. The recommended sequence is:

| Release | Action |
|---|---|
| `1.4.0` | Add the replacement; mark the old symbol `@deprecated("use <new> instead")`. |
| `1.5.0` | Keep both; the changelog repeats the migration note. |
| `1.6.0` | May remove the symbol — this is the first release where removal is legal. |

Removal before the two-release window is a breaking change and requires a
`MAJOR` bump.

### 23.4 Enforcing deprecation in CI

`--deny-deprecated` promotes every `[W0006]` to an error and exits non-zero, so a
project can adopt a stricter policy than the compiler default:

```bash
pengu check --deny-deprecated        # warnings become errors
pengu build --deny-deprecated        # build fails on deprecated use
```

Warnings are always reported: `pengu check` prints them (and counts them in the
summary), and `pengu check --json` emits them as diagnostics with
`"severity": "warning"`. Only warnings that a project explicitly denies become
errors.

### 23.5 Stability of the standard library

The standard library is versioned **together with the compiler** in the 1.x
series (see §19.0). A `MAJOR` bump is therefore the only place where a module can
be restructured; module renames are handled with the deprecation rules above.

## 24. Method chaining

A single `calling` may chain several method calls. Each `.name` link is resolved
against the type produced by the previous link:

```pengu
import std.scrolls

weave shorten with raw as string into string:
    return calling raw.get_trim.get_substring with 0, 2
```

This is *not* the parenthesis-call syntax of C-like languages: PenguScript method
calls take their arguments with `with`, and a chain adds no parentheses. A `with`
argument list binds to the **last** link only.

A chained link must produce a value, so a `@mutates` method (and the in-place
`string` forms of `std.scrolls`) cannot appear in a chain: it returns nothing.
Use the `get_<name>` spelling while chaining, as above.

### 24.1 Multi-line chains

A chain may be split over several lines. A continuation line begins with `.` (or
`->`) and is folded into the previous line before lexing:

```pengu
import std.scrolls

weave shorten with raw as string into string:
    return calling raw
        .get_trim
        .get_substring with 0, 2
```

The fold preserves line numbering, so a diagnostic on a chained expression
reports the line where the chain *starts*. Lines inside a triple-quoted string
are never folded.

### 24.2 Lowering and restrictions

Each link that is a genuine method is evaluated into a temporary inside a GNU
statement-expression, and the chain's value is the last temporary. A chain is
only treated as such when every intermediate link resolves to a method: a
sequence of *field* reads is not a chain, and a field read after a method result
must be written as a separate expression.

> [!NOTE]
> A chain requires at least two links. `calling x.method` is the canonical
> single-call form and is unchanged.

## 25. Multiple return values

A weave may return a product of two or more values by declaring a **tuple** type
and returning the values separated by commas:

```pengu
weave divide with a as int, b as int into (int, bool):
    if b == 0:
        return 0, false
    return (a / b), true
```

`(int, bool)` is a `TupleType`. It is emitted as a C struct
(`_pengu_tup_tup_int_bool`) whose fields are `v0`, `v1`, … in declaration order,
so the ABI is pass-by-value exactly like any other rune.

### 25.1 Destructuring the result

```pengu-fragment
weave use_div into int:
    let (quotient, ok) is calling divide with 10, 2
    if not ok:
        return 0
    return quotient
```

The number of names must equal the number of tuple elements (`E0017`), and each
returned value is checked against its element type in order (`E0020`).

### 25.2 Parenthesised destructuring

`let (x, y) is p` and `let x, y is p` are equivalent; both spellings produce the
same binding list. The parenthesised form is the one this reference documents.

> [!WARNING]
> Tuples compose with destructuring only. They do **not** compose with `try`,
> `or else` or `or:` propagation; use `maybe`/`result` for fallible returns.

## 26. Shorthand struct initializers

A field of a `with` literal may omit `is <value>` and take the same-named binding
instead:

```pengu
rune Player:
    name as string
    hp as int

weave make into Player:
    let name is "Ada"
    var hp is 100
    return with name, hp
```

`with name, hp` is exactly `with name is name, hp is hp`. Both forms may be mixed
in one literal, and a field whose slot holds anything other than a single bare
name must use the explicit `is` form.

> [!NOTE]
> This rewrite happens before parsing and never adds or removes a line, so
> `#line` directives and diagnostic positions stay exact. A `with` that
> introduces a call's *argument* list (`calling f with a, b`) is never rewritten.

## 27. Function attributes: `@noreturn` and `@export`

Both attributes apply to `weave` declarations.

`@noreturn` asserts that the weave never returns to its caller. The weave must be
declared `into void` (`E0056`); the generated C carries `_Noreturn` on both the
prototype and the definition (`__declspec(noreturn)` for MSVC):

```pengu
import std.spark

@noreturn
weave stop with msg as string into void:
    calling spark.println with "stop: {msg}"
```

`@export("c_name")` pins the emitted C symbol, which is what an external caller
links against. The PenguScript name is unchanged — only the C name is:

```pengu
@export("pengu_exported_add")
weave add with a as int, b as int into int:
    return a + b
```

The weave above is still called `calling add with 1, 2` from PenguScript, and is
emitted as `int pengu_exported_add(int32_t a, int32_t b)`. An exported weave is a
root of dead-code elimination even when nothing in the program references it.

## 28. Layout attributes: `@packed` and `@align(N)`

`@packed` removes inter-field padding from a `rune`, and `@align(N)` sets its
alignment. `N` must be a power of two between 1 and 128 (`E0056`), because both
GCC/Clang and MSVC require that:

```pengu
@packed
rune NetHeader:
    magic as u16
    version as u8
    flags as u8
    length as u32
```

With `@packed` this rune occupies 8 bytes rather than the 12 that padding would
require. `@align(N)` may also be applied to an individual field to align it
within its struct.

> [!NOTE]
> `@packed` and `@align` apply to `rune` declarations and their fields. An `echo`
> declaration has no attribute position in the grammar, so they cannot be written
> there; a C union has its own layout rules.

*End of reference. Corrections welcome — this document mirrors compiler
behavior at version 2.0.x; run `pengu check` on any snippet to confirm
semantics on your toolchain.*

