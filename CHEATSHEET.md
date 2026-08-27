# PenguScript Language Syntax & C Translation Cheatsheet

> A fast, elegant, statically typed programming language combining the clean readability of **Python**, the memory safety and scoping rules of **V**, and the raw speed of **C**.

---

## Table of Contents

1. [Core Principles & Safety Rules](#1-core-principles--safety-rules)
2. [Comments](#2-comments)
3. [Imports & C Interoperability](#3-imports--c-interoperability)
4. [Types & Memory Representation](#4-types--memory-representation)
5. [Variables & Scoping (`const`, `var`, `let`)](#5-variables--scoping-const-var-let)
6. [Arithmetic, Conversions & Bitwise Operators](#6-arithmetic-conversions--bitwise-operators)
7. [Structures & Methods (`rune` & `enchanting`)](#7-structures--methods-rune--enchanting)
8. [Tagged Unions & Enums (`echo` & `omen`)](#8-tagged-unions--enums-echo--omen)
9. [Collections (`array`, `slice`, `list`, `map`)](#9-collections-array-slice-list-map)
10. [Nullable & Result Types (`maybe` & `result`)](#10-nullable--result-types-maybe--result)
11. [Functions & External Declarations (`weave` & `declare`)](#11-functions--external-declarations-weave--declare)
12. [Generics (`shard_params`)](#12-generics-shard_params)
13. [Control Flow & Pattern Matching (`if`, `unless`, `judge/when`, loops)](#13-control-flow--pattern-matching)
14. [Scoped Mutation (`with`)](#14-scoped-mutation-with)
15. [Memory Safety (`defer`, `errdefer`, `banish`, pointers)](#15-memory-safety-defer-errdefer-banish-pointers)
16. [Standard Library Reference (25 Modules)](#16-standard-library-reference-25-modules)

---

## 1. Core Principles & Safety Rules

- **Indentation-Based**: Clean Python-like indentation (no semicolons `;`, no curly braces `{}`).
- **Explicit Keywords**:
  - `as` defines a **Type** (`x as int`)
  - `is` assigns a **Value** (`is 42`)
  - `to` performs **Type Casting** (`10 to float`)
  - `into` specifies **Return Types** (`into int:`)
- **V-Style Scoping (No Mutable Globals)**:
  - `const` is **only allowed at top-level** (translated directly to `#define` / constant literals).
  - `var` (mutable) and `let` (immutable) are **only allowed inside functions / blocks**.
- **Unified Expressions**: `if`, `when`, `judge`, and loops evaluate as expressions that can yield values.
- **Explicit References**: In `enchanting` methods, `self` is always a pointer reference (`ref to Self`) accessed via the arrow operator (`self->field`).

---

## 2. Comments

| PenguScript Syntax | Generated C Code | Description |
|---|---|---|
| `# Single line comment` | `// Single line comment` | Single-line comment |
| `## Multi-line`<br>`comment block ##` | `/* Multi-line`<br>`comment block */` | Block comment (preserved for LSP docstrings) |

---

## 3. Imports & C Interoperability

```pengu
# 1. Import internal/standard library modules
import std.spark
import std.oracle
import my_module

# 2. Include C header files (generates #include)
include "stdio.h"
include "raylib.h"

# 3. Link C external libraries (generates -l flags)
link "raylib"
link "m"
link "pthread"
```

```c
#include "stdio.h"
#include "raylib.h"
#include "pengu_runtime.h"
// Bundled PenguScript modules compiled into a single C translation unit.
// CLI invokes: gcc bundle.c -lraylib -lm -lpthread -o app
```

---

## 4. Types & Memory Representation

| PenguScript Type | C Equivalent | Size (Bytes) | Description |
|---|---|---|---|
| `int`, `i32` | `int32_t` | 4 | 32-bit signed integer |
| `i64` | `int64_t` | 8 | 64-bit signed integer |
| `float`, `f32` | `float` | 4 | 32-bit single-precision float |
| `f64` | `double` | 8 | 64-bit double-precision float |
| `bool` | `bool` (`uint8_t`) | 1 | Boolean (`true` / `false`) |
| `string` | `PenguString` | 16 | Dynamic UTF-8 string `{ char* ptr; size_t len; size_t cap; }` |
| `void` | `void` | 0 | Empty / unit return type |
| `ref to T` | `T*` | 8 | Pointer / reference to type `T` |
| `ref to void` | `void*` | 8 | Generic void pointer (for callbacks/C interop) |
| `array of T with size N` | `T[N]` | `N * sizeof(T)` | Fixed-size contiguous stack array |
| `slice of T` | `PenguSlice` | 24 | View over contiguous memory `{ T* ptr; size_t len; size_t cap; }` |
| `list of T` | `PenguList` | 24 | Heap-allocated dynamic array (`push`, `pop`, `len`) |
| `map of K to V` | `PenguMap` | 24 | Hash map collection |
| `maybe T` | `struct { bool is_present; T value; }` | `sizeof(T) + 4` | Null-safe optional container |
| `result of T to E` | `struct { bool is_ok; T val; E err; }` | `sizeof(T) + sizeof(E) + 4` | Error handling container |
| `opaque` | `struct OpaqueType*` | 8 | Incomplete C type pointer (e.g. `Texture2D`) |

---

## 5. Variables & Scoping (`const`, `var`, `let`)

```pengu
# Top-level (Global constants only)
const MAX_USERS as int is 1000
const API_URL as string is "https://api.penguscript.org"

weave main into void:
    # Local mutable variable
    var count as int is 0
    set count is count + 1

    # Local immutable binding (const in C)
    let max_limit as int is MAX_USERS * 2

    # Pointer reference
    let ptr as ref to int is sigil of count
```

```c
#define MAX_USERS 1000
#define API_URL "https://api.penguscript.org"

void main(void) {
    int count = 0;
    count = count + 1;

    const int max_limit = MAX_USERS * 2;
    int* ptr = &count;
}
```

---

## 6. Arithmetic, Conversions & Bitwise Operators

```pengu
weave math_demo into void:
    let sum is 10 + 20 * 2
    let f as float is 42 to float          # Explicit type casting with 'to'
    let bits as int is transmute f to int  # Raw bitwise memory reinterpretation

    # Bitwise operators (Ideal for flags and graphics programming)
    let flags is 0x01 | 0x02
    let masked is flags & 0xFF
    let inverted is ~flags
    let shifted is 1 << 4
```

```c
void math_demo(void) {
    int sum = 10 + 20 * 2;
    float f = (float)42;
    int bits = *(int*)&f;

    int flags = 0x01 | 0x02;
    int masked = flags & 0xFF;
    int inverted = ~flags;
    int shifted = 1 << 4;
}
```

---

## 7. Structures & Methods (`rune` & `enchanting`)

```pengu
# Define composite struct
rune Vector2:
    x as float
    y as float

# Attach methods (self is always passed as ref to Vector2)
enchanting Vector2:
    weave magnitude into float:
        return (self->x * self->x + self->y * self->y) to float

    weave scale with factor as float into void:
        set self->x is self->x * factor
        set self->y is self->y * factor

weave main into void:
    # Struct instantiation with 'with ... is ... and ... is ...'
    var vec as Vector2 is with x is 3.0 and y is 4.0
    calling vec.scale with 2.0
```

```c
typedef struct {
    float x;
    float y;
} Vector2;

float Vector2_magnitude(Vector2* self) {
    return (float)(self->x * self->x + self->y * self->y);
}

void Vector2_scale(Vector2* self, float factor) {
    self->x = self->x * factor;
    self->y = self->y * factor;
}

void main(void) {
    Vector2 vec = (Vector2){ .x = 3.0f, .y = 4.0f };
    Vector2_scale(&vec, 2.0f);
}
```

---

## 8. Tagged Unions & Enums (`echo` & `omen`)

### `echo` (C-Compatible Tagged Union)
```pengu
echo DataPayload:
    as_int as int
    as_float as float
    as_str as string
```

### `omen` (Algebraic Data Types / Enums with Payloads)
```pengu
omen NetworkState:
    Disconnected
    Connecting with retry_count as int
    Connected with session_token as string
    Failed with error_code as int and reason as string

weave handle_state with state as NetworkState into void:
    judge state:
        when Connected with session_token:
            # Handle connected session
            pass
        when Connecting with retry_count:
            # Retry connection
            pass
        when Failed with error_code and reason:
            # Report error
            pass
        else:
            pass
```

---

## 9. Collections (`array`, `slice`, `list`, `map`)

```pengu
weave collections_demo into void:
    # 1. Fixed array on the stack
    var arr as array of int with size 3 is [10, 20, 30]

    # 2. Dynamic heap list
    var numbers as list of int is list of int
    calling numbers.push with 100
    calling numbers.push with 200
    let count is numbers.len
    let item is numbers[0]

    # 3. Hash Map
    var scores as map of string to int is map of string to int
    calling scores.set with "Alice" and 95
    let score as maybe int is scores.get("Alice")
```

---

## 10. Nullable & Result Types (`maybe` & `result`)

### `maybe T` (Zero-cost Option type avoiding null pointer exceptions)
```pengu
weave find_index with query as string into maybe int:
    if query == "admin":
        return some(0)
    return none

weave test_maybe into void:
    let res as maybe int is calling find_index with "admin"
    if res.is_present:
        let idx is res.value
    let fallback is res.or_value(-1)
```

### `result of T to E` (Functional error handling)
```pengu
weave divide with a as float and b as float into result of float to string:
    if b == 0.0:
        return err("Division by zero error")
    return ok(a / b)

weave test_result into void:
    let calc is calling divide with 10.0 and 2.0
    if calc.is_ok:
        let val is calc.value
    else:
        let msg is calc.error_value
```

---

## 11. Functions & External Declarations (`weave` & `declare`)

```pengu
# External C ABI binding
declare puts with str as string into int
declare c_sqrt with val as float into float

# PenguScript function with typed parameters and default argument
## Computes base raised to power exponent.
weave power with base as int and exp as int is 2 into int:
    var result as int is 1
    for i in 0 to exp:
        set result is result * base
    return result
```

```c
extern int puts(const char* str);
extern float c_sqrt(float val);

int power(int base, int exp) {
    int result = 1;
    for (int i = 0; i < exp; i++) {
        result = result * base;
    }
    return result;
}
```

---

## 12. Generics (`shard_params`)

```pengu
rune Container of [T]:
    item as T
    id as int

weave create_container of [T] with val as T and id as int into Container of [T]:
    return with item is val and id is id

weave test_generics into void:
    var int_box as Container of [int] is calling create_container of [int] with 42 and 1
    var str_box as Container of [string] is calling create_container of [string] with "Pengu" and 2
```

---

## 13. Control Flow & Pattern Matching

### `if` / `unless`
```pengu
# if expression
let status is if score >= 60 then "Passed" else "Failed"

# unless (syntactic sugar for if not)
unless is_ready:
    calling spark.println with "System not ready"
```

### `judge` / `when` (Pattern Matching)
```pengu
let category is judge code:
    when 200: "OK"
    when 400 to 499: "Client Error"
    when 500 to 599: "Server Error"
    else: "Unknown"
```

### Loops (`while` & `for`)
```pengu
# Range loop (inclusive start to exclusive end)
for i in 0 to 10:
    calling spark.println with i

# In-collection loop
for item in my_list:
    calling spark.println with item

# While loop
while is_active:
    calling poll_event
```

---

## 14. Scoped Mutation (`with`)

```pengu
rune Player:
    x as int
    y as int
    score as int

weave reset_player with p as ref to Player into void:
    with p:
        set x is 0
        set y is 0
        set score is 100
```

```c
void reset_player(Player* p) {
    p->x = 0;
    p->y = 0;
    p->score = 100;
}
```

---

## 15. Memory Safety (`defer`, `errdefer`, `banish`, pointers)

```pengu
weave process_file with filename as string into result of string to string:
    var file_handle as ref to void is calling open_file with filename
    if file_handle == null:
        return err("Could not open file")

    # defer always executes when exiting the enclosing function scope (LIFO)
    defer calling close_file with file_handle

    # errdefer only executes if an error is returned
    errdefer calling log_failure with filename

    var buffer as ref to char is calling allocate_memory with 1024
    # banish explicitly frees heap allocated reference
    defer banish buffer

    return ok("File read successfully")
```

---

## 16. Standard Library Reference (25 Modules)

| Module | Import | Description |
|---|---|---|
| **spark** | `import std.spark` | Fast terminal I/O (`print`, `println`, `read_line`, ANSI color formatting). |
| **oracle** | `import std.oracle` | String conversions, parsing integers/floats, string interpolation helpers. |
| **chronicle** | `import std.chronicle` | High-precision time, timestamps, date/time formatting, sleep, stopwatch. |
| **whisper** | `import std.whisper` | File system operations (`read_file`, `write_file`, `append_file`, `exists`, `remove`). |
| **filum** | `import std.filum` | Advanced string manipulation (`split`, `join`, `replace`, `trim`, `starts_with`). |
| **atlas** | `import std.atlas` | System environment variables, CLI arguments, process execution, exit codes. |
| **tally** | `import std.tally` | Advanced math functions (`min`, `max`, `abs`, `clamp`, `sqrt`, `sin`, `cos`, `pow`). |
| **ledger** | `import std.ledger` | High-performance CSV & TSV parsing, delimiter detection, row serializer. |
| **vault** | `import std.vault` | Key-value memory stores, configuration dictionary mappings. |
| **parchment** | `import std.parchment` | XML / HTML document tree parser and XPath navigation (powered by `libxml2`). |
| **regulus** | `import std.regulus` | High-speed regular expressions (powered by `PCRE2 10.47`). |
| **seal** | `import std.seal` | Cryptographic hashing (`MD5`, `SHA1`, `SHA256`, `SHA512`, `CRC32`) and `zlib`/`gzip` compression. |
| **precis** | `import std.precis` | HTTP client (`GET`, `POST`, `PUT`, `DELETE`), embedded HTTP micro-server, raw TCP sockets. |
| **ward** | `import std.ward` | Runtime assertions (`assert`, `assert_eq`, `assert_ne`, `assert_ok`, `panic`). |
| **trial** | `import std.trial` | Automated unit testing framework (suites, test cases, before/after hooks, summary report). |
| **alembic** | `import std.alembic` | Data encoding/decoding (`Base64`, `Hex`, `URL encoding`). |
| **prism** | `import std.prism` | Color space transformations (`RGB`, `HEX`, `HSL`, `HSV`). |
| **matrix** | `import std.matrix` | 2D/3D math vectors, matrix multiplication, transformation helpers. |
| **loom** | `import std.loom` | Multi-threading primitives, worker tasks, and synchronization mutexes. |
| **fable** | `import std.fable` | Pseudo-random number generators, seeds, random range, shuffle algorithms. |
| **forge** | `import std.forge` | Binary data buffers, byte swapping, endianness conversions (`read_u16`, `write_u32`). |
| **scroll** | `import std.scroll` | JSON serialization and deserialization helpers. |
| **beacon** | `import std.beacon` | Structured logging framework (`debug`, `info`, `warn`, `error`, `fatal`). |
| **harbor** | `import std.harbor` | Cross-platform directory traversing, file watcher notifications. |
| **quarry** | `import std.quarry` | In-memory query engine and array filtering/sorting algorithms. |
