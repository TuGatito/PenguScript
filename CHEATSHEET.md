# PenguScript Language Syntax & C Translation Cheatsheet

> A fast, elegant, statically typed programming language combining the clean readability of **Python** and **MoonScript**, the memory safety and scoping rules of **V**, and the raw speed of **C**.

---

## Table of Contents

1. [Core Principles & Safety Rules](#1-core-principles--safety-rules)
2. [Comments](#2-comments)
3. [Imports & C Interoperability](#3-imports--c-interoperability)
4. [Types & Memory Layout](#4-types--memory-layout)
5. [Variables & Scoping (`const`, `var`, `let`, `set`)](#5-variables--scoping-const-var-let-set)
6. [Arithmetic, Conversions & Bitwise Operators](#6-arithmetic-conversions--bitwise-operators)
7. [Arrays, Slices, Lists & Maps](#7-arrays-slices-lists--maps)
8. [Structures, Tagged Unions & Opaque Types (`rune`, `echo`, `alias`, `opaque`)](#8-structures-tagged-unions--opaque-types-rune-echo-alias-opaque)
9. [Algebraic Enums (`omen`)](#9-algebraic-enums-omen)
10. [Methods & Receiver Blocks (`enchanting`)](#10-methods--receiver-blocks-enchanting)
11. [Functions & External Declarations (`weave` & `declare`)](#11-functions--external-declarations-weave--declare)
12. [Function Pointers & Callbacks](#12-function-pointers--callbacks)
13. [Generics (`shard` & `of`)](#13-generics-shard--of)
14. [Control Flow: Conditionals (`if`, `unless`, Ternary)](#14-control-flow-conditionals-if-unless-ternary)
15. [Control Flow: Pattern Matching (`judge` & `when`)](#15-control-flow-pattern-matching-judge--when)
16. [Control Flow: Loops (`while`, `for ... in`, `for ... from ... to`)](#16-control-flow-loops-while-for--in-for--from--to)
17. [Scoped Mutation (`with`)](#17-scoped-mutation-with)
18. [Destructuring Bindings](#18-destructuring-bindings)
19. [Nullable & Error Handling (`maybe`, `omen Result`, `or`, `try`)](#19-nullable--error-handling-maybe-omen-result-or-try)
20. [Memory Management (`sigil`, `essence`, `defer`, `errdefer`, `banish`)](#20-memory-management-sigil-essence-defer-errdefer-banish)
21. [Transparent C Identifier Resolution](#21-transparent-c-identifier-resolution)
22. [Complete Real-World Example: Raylib Game](#22-complete-real-world-example-raylib-game)
23. [Standard Library Reference (24 Modules)](#23-standard-library-reference-24-modules)

---

## 1. Core Principles & Safety Rules

- **Indentation-Based**: Clean Python-like indentation (no semicolons `;`, no curly braces `{}`).
- **Explicit Type & Value Keywords**:
  - `as` defines a **Type** (`x as int`)
  - `is` assigns a **Value** (`is 42`)
  - `to` performs **Type Casting** (`10 to float`)
  - `into` specifies **Return Types** (`into int:`)
- **Unified Expressions**: `if`, `when`, `judge`, and loops evaluate as expressions that can yield values.

> [!IMPORTANT]
> **V-Style Scoping (No Mutable Globals)**:
>
> - `const` is **strictly top-level** (global constants translated directly to `#define` / constant literals).
> - `var` (mutable) and `let` (immutable) are **strictly local** inside function bodies and control flow blocks. Global `var`/`let` is a compile error, preventing unsafe global mutable state.

> [!NOTE]
> **Explicit References**: In `enchanting` methods, `self` is **always** a pointer reference (`ref to SelfType`) and **must always** be accessed via the arrow operator (`self->field`).

---

## 2. Comments

```pengu
# Single line comment

##
  Multi-line block comment
  (preserved for LSP documentation tooltips)
##
```

```c
// Single line comment

/*
  Multi-line block comment
  (preserved for LSP documentation tooltips)
*/
```

---

## 3. Imports & C Interoperability

```pengu
# 1. Import internal/standard library modules (merged into a single bundle)
import std.spark
import std.oracle
import src.components.Player
import src.math.Vec2

# 2. Include C header files (generates #include)
include "stdio.h"
include "raylib.h"

# 3. Link external C libraries (generates -l flags for the compiler)
link "raylib"
link "m"
link "pthread"
```

```c
#include "stdio.h"
#include "raylib.h"
#include "pengu_runtime.h"

// Bundled code from Player.pengu, Vec2.pengu, and standard modules
// Compiler command: gcc bundle.c -lraylib -lm -lpthread -o app
```

---

## 4. Types & Memory Layout

| PenguScript Type         | C Equivalent                           | Size (Bytes)           | Description                                              |
| ------------------------ | -------------------------------------- | ---------------------- | -------------------------------------------------------- |
| `int`, `i32`             | `int32_t`                              | 4                      | 32-bit signed integer                                    |
| `i64`                    | `int64_t`                              | 8                      | 64-bit signed integer                                    |
| `float`, `f32`           | `float`                                | 4                      | 32-bit single-precision float                            |
| `f64`                    | `double`                               | 8                      | 64-bit double-precision float                            |
| `bool`                   | `bool` (`uint8_t`)                     | 1                      | Boolean (`true` / `false`)                               |
| `string`                 | `PenguString`                          | 16                     | Dynamic UTF-8 string `{ char* data; int len; }`          |
| `void`                   | `void`                                 | 0                      | Empty / unit return type                                 |
| `ref to T`               | `T*`                                   | 8                      | Pointer / reference to type `T`                          |
| `ref to void`            | `void*`                                | 8                      | Generic void pointer (for callbacks/C interop)           |
| `array of T with size N` | `T[N]`                                 | `N * sizeof(T)`        | Fixed-size contiguous stack array                        |
| `slice of T`             | `PenguSlice`                           | 16                     | View over contiguous memory `{ T* data; int len; }`      |
| `list of T`              | `PenguList`                            | 24                     | Dynamic heap array (`push`, `pop`, `len`, `cap`)         |
| `map of K to V`          | `PenguMap`                             | 24                     | Hash map collection (`set`, `get`, `has`, `len`)         |
| `maybe T`                | `struct { bool is_present; T value; }` | `sizeof(T) + 4`        | Null-safe optional container                             |
| `opaque`                 | `typedef struct Name Name;`            | Incomplete (C-defined) | Incomplete C forward declaration type (e.g. `Texture2D`) |

> [!TIP]
> Use `to` for explicit numerical conversions (`x to float`) and `transmute` for raw bitwise memory reinterpretation (`transmute f to int`).

---

## 5. Variables & Scoping (`const`, `var`, `let`, `set`)

```pengu
# Top-level: ONLY const, rune, echo, omen, alias, import, include, link, weave, enchanting
const MAX_ENTITIES as int is 1000
const PI as float is 3.14159

weave main into int:
    var x as int is 10         # Mutable local variable
    let y as int is 20         # Immutable local binding (const in C)
    let p as ref to int is sigil of x

    set x is x + 1             # Mutation with 'set'
    # set y is 30              # COMPILE ERROR: y is immutable (let)
    return 0
```

```c
#define MAX_ENTITIES 1000
#define PI 3.14159f

int main(void) {
    int x = 10;
    const int y = 20;
    int* p = &x;

    x = x + 1;
    return 0;
}
```

---

## 6. Arithmetic, Conversions & Bitwise Operators

```pengu
weave operators_demo into void:
    let a is 10 + 20 * 2
    let b is (10 + 20) * 2
    let f as float is 10 to float          # Type casting with 'to'
    let bits is transmute f to int         # Bitwise memory reinterpretation

    # Bitwise operations (ideal for flags and graphics)
    let flags is 0x01 | 0x02               # Bitwise OR
    let masked is flags & 0xFF             # Bitwise AND
    let xor is flags ^ 1                   # Bitwise XOR
    let not_flags is ~flags                # Bitwise NOT
    let shifted is 1 << 5                  # Bitwise Left Shift
    let rshift is 32 >> 2                  # Bitwise Right Shift
```

```c
void operators_demo(void) {
    int a = 10 + 20 * 2;
    int b = (10 + 20) * 2;
    float f = (float)10;
    int bits = *(int*)&f;

    int flags = 0x01 | 0x02;
    int masked = flags & 0xFF;
    int xor = flags ^ 1;
    int not_flags = ~flags;
    int shifted = 1 << 5;
    int rshift = 32 >> 2;
}
```

---

## 7. Arrays, Slices, Lists & Maps

Elements in arrays, slices, and dynamic lists are accessed with the `at` keyword.

```pengu
weave collections_demo into void:
    # 1. Stack Array (Fixed size)
    var arr as array of int with size 5 is [1, 2, 3, 4, 5]
    let first is arr at 0
    set arr at 0 is 99

    # 2. Slice (Memory view)
    let part as slice of int is arr at 1 to 4
    let slice_len is part length

    # 3. Dynamic Heap List
    var items as list of int is list of int with capacity 100
    calling items.push with 42
    let item_val is items at 0
    let total_items is items.len

    # 4. Hash Map
    var scores as map of string to int is map of string to int
    calling scores.set with "Alice" and 100
    let alice_score is calling scores.get with "Alice"

    # 5. String Interpolation
    let name as string is "Pengu"
    let greeting is "Hello, {name}! You have {first} points."
```

```c
void collections_demo(void) {
    // 1. Stack Array
    int arr[5] = { 1, 2, 3, 4, 5 };
    int first = arr[0];
    arr[0] = 99;

    // 2. Slice
    PenguSlice part = (PenguSlice){ .data = (void*)&arr[1], .len = 3 };
    int slice_len = part.len;

    // 3. Dynamic List
    PenguList items = pengu_list_new(sizeof(int), 100);
    int _val = 42;
    pengu_list_push(&items, &_val);
    int item_val = *(int*)pengu_list_get(&items, 0);
    int total_items = items.len;

    // 4. Hash Map
    PenguMap scores = pengu_map_new();
    int _s = 100;
    pengu_map_set(&scores, pengu_string_from_cstr("Alice"), &_s);

    // 5. String Interpolation
    PenguString name = pengu_string_from_cstr("Pengu");
    PenguString greeting = pengu_string_format("Hello, %s! You have %d points.", name.data, first);
}
```

---

## 8. Structures, Tagged Unions & Opaque Types (`rune`, `echo`, `alias`, `opaque`)

```pengu
include "raylib.h"

# 1. Composite Struct
rune Vec2:
    x as float
    y as float

# 2. Tagged Union (C Union)
echo Value:
    as_int as int
    as_float as float

# 3. Type Aliases & Opaque C Structs
alias Score as int
alias Texture as opaque                    # Incomplete C struct from raylib.h

declare LoadTexture with path as string into Texture
declare UnloadTexture with texture as Texture into void

weave struct_demo into void:
    # Struct instantiation with 'with field is val and ...'
    var v as Vec2 is with x is 10.0 and y is 20.0
    let vx is v.x
    set v.x is 100.0

    # Pointer access with ->
    var vp as ref to Vec2 is sigil of v
    set vp->x is 200.0

    # Opaque handle usage
    let tex as Texture is calling LoadTexture with "assets/player.png"
    defer calling UnloadTexture with tex
```

```c
#include "raylib.h"

// 1. Struct
typedef struct {
    float x;
    float y;
} Vec2;

// 2. Union
typedef union {
    int as_int;
    float as_float;
} Value;

// 3. Aliases
typedef int Score;
typedef struct Texture Texture;

extern Texture LoadTexture(const char* path);
extern void UnloadTexture(Texture texture);

void struct_demo(void) {
    Vec2 v = (Vec2){ .x = 10.0f, .y = 20.0f };
    float vx = v.x;
    v.x = 100.0f;

    Vec2* vp = &v;
    vp->x = 200.0f;

    Texture tex = LoadTexture("assets/player.png");
    UnloadTexture(tex);
}
```

---

## 9. Algebraic Enums (`omen`)

```pengu
omen NetworkState:
    Disconnected
    Connecting with retry_count as int
    Connected with session_id as string
    Failed with error_code as int and reason as string

weave demo_omen into void:
    # Instantiation of omen variants
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
        struct { int retry_count; } Connecting;
        struct { PenguString session_id; } Connected;
        struct { int error_code; PenguString reason; } Failed;
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

---

## 10. Methods & Receiver Blocks (`enchanting`)

`self` is **always** `ref to SelfType` and accessed via `self->field`.

```pengu
rune Vec2:
    x as float
    y as float

enchanting Vec2:
    # Value return method
    weave add with other as Vec2 into Vec2:
        return with x is self->x + other.x and y is self->y + other.y

    # Length method
    weave length into float:
        return (self->x * self->x + self->y * self->y) to float

    # In-place mutating method
    weave move with dx as float and dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into void:
    var a as Vec2 is with x is 10.0 and y is 20.0
    var b as Vec2 is with x is 5.0 and y is 5.0

    let c as Vec2 is calling a.add with b
    calling a.move with 10.0 and 0.0
```

```c
typedef struct { float x; float y; } Vec2;

Vec2 Vec2_add(Vec2* self, Vec2 other) {
    return (Vec2){ .x = self->x + other.x, .y = self->y + other.y };
}

float Vec2_length(Vec2* self) {
    return (float)(self->x * self->x + self->y * self->y);
}

void Vec2_move(Vec2* self, float dx, float dy) {
    self->x += dx;
    self->y += dy;
}

void main(void) {
    Vec2 a = (Vec2){ .x = 10.0f, .y = 20.0f };
    Vec2 b = (Vec2){ .x = 5.0f, .y = 5.0f };

    Vec2 c = Vec2_add(&a, b);
    Vec2_move(&a, 10.0f, 0.0f);
}
```

---

## 11. Functions & External Declarations (`weave` & `declare`)

```pengu
# 1. Function with implicit return (last expression is returned automatically)
weave add with a as int and b as int into int:
    a + b

# 2. Function with default argument values
weave DrawText with text as string and x as int is 0 and y as int is 0 into void:
    # Function body...
    pass

# 3. Calling functions with named arguments and omitted default values
weave demo_calls into void:
    # Named argument call (y defaults to 0)
    calling DrawText with text is "Hello, Pengu!" and x is 100

    # Positional argument call
    let sum is calling add with 10 and 20

# 4. Inlined function
inline weave fast_add with a as int and b as int into int:
    a + b

# 5. External C ABI declarations
declare InitWindow with w as int and h as int and title as string into void
declare WindowShouldClose into bool
declare CloseWindow into void
```

```c
// 1. Function with implicit return
int add(int a, int b) {
    return a + b;
}

// 2. Function with default argument values
void DrawText(PenguString text, int x, int y) {
    // Function body...
}

// 3. Calling functions (compiler fills default arguments at call sites)
void demo_calls(void) {
    // Named arguments call: y is automatically filled with default value 0
    DrawText(pengu_string_from_cstr("Hello, Pengu!"), 100, 0);

    // Positional call
    int sum = add(10, 20);
}

// 4. Inlined function
static inline int fast_add(int a, int b) {
    return a + b;
}

// 5. External C ABI declarations
extern void InitWindow(int w, int h, const char* title);
extern bool WindowShouldClose(void);
extern void CloseWindow(void);
```

---

## 12. Function Pointers & Callbacks

```pengu
# Define function pointer alias
alias BinaryOp as ref to weave with a as int and b as int into int
alias WebUICallback as ref to weave with event as ref to void into void

weave add with a as int and b as int into int:
    return a + b

weave execute_op with op as BinaryOp and x as int and y as int into int:
    return calling op with x and y

weave test_callback into void:
    let fn_ptr as BinaryOp is sigil of add
    let result is calling execute_op with fn_ptr and 10 and 20
```

```c
typedef int (*BinaryOp)(int, int);
typedef void (*WebUICallback)(void*);

int add(int a, int b) { return a + b; }

int execute_op(BinaryOp op, int x, int y) {
    return op(x, y);
}

void test_callback(void) {
    BinaryOp fn_ptr = &add;
    int result = execute_op(fn_ptr, 10, 20);
}
```

---

## 13. Generics (`shard` & `of`)

Type parameters are declared on definitions using `shard` and specialized at usage with `of`. PenguScript uses monomorphization to compile generic structures and functions into specialized, zero-overhead C code.

```pengu
# Generic Struct declaration with 'shard'
rune Box shard T:
    item as T
    id as int

# Generic Struct with multiple type parameters
rune Pair shard T and U:
    first as T
    second as U

# Generic Function declaration with 'shard'
weave create_box shard T with val as T and id as int into Box of T:
    return with item is val and id is id

weave main into void:
    # Instantiation and specialized calls with 'of'
    var int_box as Box of int is calling create_box of int with 42 and 1
    var str_box as Box of string is calling create_box of string with "Pengu" and 2
```

```c
// Monomorphized C Structs
typedef struct { int item; int id; } Box_int;
typedef struct { PenguString item; int id; } Box_string;

// Monomorphized C Functions
Box_int create_box_int(int val, int id) {
    return (Box_int){ .item = val, .id = id };
}

Box_string create_box_string(PenguString val, int id) {
    return (Box_string){ .item = val, .id = id };
}

void main(void) {
    Box_int int_box = create_box_int(42, 1);
    Box_string str_box = create_box_string(pengu_string_from_cstr("Pengu"), 2);
}
```

---

## 14. Control Flow: Conditionals (`if`, `unless`, Ternary)

```pengu
weave conditionals_demo with x as int into void:
    # 1. Standard if / else
    if x > 10:
        calling spark.println with "Greater than 10"
    else:
        calling spark.println with "10 or less"

    # 2. unless statement (syntactic sugar for if not)
    unless x == 0:
        calling spark.println with "Non-zero"

    # 3. Ternary if expression
    let color as string is if x > 10 then "red" else "blue"
```

```c
void conditionals_demo(int x) {
    // 1. If / else
    if (x > 10) {
        printf("Greater than 10\n");
    } else {
        printf("10 or less\n");
    }

    // 2. Unless
    if (!(x == 0)) {
        printf("Non-zero\n");
    }

    // 3. Ternary
    const char* color = (x > 10) ? "red" : "blue";
}
```

---

## 15. Control Flow: Pattern Matching (`judge` & `when`)

`judge` evaluates a target expression against inline `when expr -> expr` clauses.

```pengu
weave pattern_demo with key as int into string:
    # Pattern matching expression with inline when clauses
    let state as string is judge key:
        when 1 -> "Active"
        when 2 -> "Pending"
        when 3 -> "Finished"
        else -> "Unknown"
    return state
```

```c
PenguString pattern_demo(int key) {
    switch (key) {
        case 1:
            return pengu_string_from_cstr("Active");
        case 2:
            return pengu_string_from_cstr("Pending");
        case 3:
            return pengu_string_from_cstr("Finished");
        default:
            return pengu_string_from_cstr("Unknown");
    }
}
```

---

## 16. Control Flow: Loops (`while`, `for ... in`, `for ... from ... to`)

```pengu
weave loops_demo into void:
    # 1. While loop with break and continue
    var x as int is 0
    while x < 10:
        set x is x + 1
        if x == 5:
            continue
        if x == 9:
            break

    # 2. Numerical Range loop with 'from ... to'
    for i from 0 to 5:
        calling spark.println with "Index: {i}"

    # 3. Collection iteration loop
    var numbers as array of int with size 3 is [10, 20, 30]
    for num in numbers:
        calling spark.println with (num to string)

    # 4. For expression (List comprehension)
    let evens is for num in numbers when num % 2 == 0 then num
```

```c
void loops_demo(void) {
    // 1. While
    int x = 0;
    while (x < 10) {
        x = x + 1;
        if (x == 5) continue;
        if (x == 9) break;
    }

    // 2. Range For
    for (int i = 0; i < 5; i++) {
        printf("%d\n", i);
    }

    // 3. Collection For
    int numbers[3] = { 10, 20, 30 };
    for (int _idx = 0; _idx < 3; _idx++) {
        int num = numbers[_idx];
        printf("%d\n", num);
    }
}
```

---

## 17. Scoped Mutation (`with`)

- `is with ...` initializes a struct (expression).
- `with target:` scopes mutations and method calls on the target object using dot notation (`set.field`, `calling.method`) without repeating the receiver name (statement).

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
typedef struct {
    int x;
    int y;
    int health;
} Player;

void Player_heal(Player* self, int amount) {
    self->health += amount;
}

void reset_player(Player* p) {
    p->x = 100;
    p->y = 200;
    Player_heal(p, 50);
}
```

---

## 18. Destructuring Bindings

```pengu
rune Vec2:
    x as float
    y as float

weave test_destructure into void:
    var v as Vec2 is with x is 10.0 and y is 20.0
    let x, y is v
```

```c
void test_destructure(void) {
    Vec2 v = (Vec2){ .x = 10.0f, .y = 20.0f };
    const float x = v.x;
    const float y = v.y;
}
```

---

## 19. Nullable & Error Handling (`maybe`, `omen Result`, `or`, `try`)

### `maybe T` (Null Safety)

```pengu
weave find_user with id as int into maybe string:
    if id == 1:
        return some("Admin")
    return maybe none

weave test_maybe into void:
    let user as maybe string is calling find_user with 1

    # Check presence
    if user is present:
        let name is user.value

    # Fallback with or else
    let final_name is user or else "Guest"
```

### Algebraic `omen Result` & Error Blocks (`or:`, `try`)

```pengu
omen Result:
    Ok with value as float
    Err with msg as string

weave divide with a as float and b as float into Result:
    if b == 0.0:
        return with Err is with msg is "Division by zero"
    return with Ok is with value is a / b

weave test_result into void:
    # Error handling block
    let res is calling divide with 10.0 and 2.0 or:
        let err_msg is error
        calling spark.println with err_msg
        return

    # Error propagation with try
    let calc is try calling divide with 10.0 and 5.0
```

```c
typedef struct { bool is_present; PenguString value; } Maybe_string;

typedef struct {
    enum { Result_Ok, Result_Err } tag;
    union {
        struct { float value; } Ok;
        struct { PenguString msg; } Err;
    } data;
} Result;
```

---

## 20. Memory Management (`sigil`, `essence`, `defer`, `errdefer`, `banish`)

```pengu
declare malloc with size as int into ref to void
declare free with ptr as ref to void into void
declare CloseWindow into void

weave memory_demo into int:
    # 1. Allocation
    var buffer as ref to char is calling malloc with 1024 to ref to char
    if buffer == null:
        return 1

    # 2. Defer accepts any expression or call (executed in LIFO order upon exiting scope)
    defer banish buffer
    defer calling CloseWindow

    # 3. Errdefer (Executes ONLY when an error is returned)
    errdefer calling spark.println with "Cleanup failed transaction"

    # 4. Pointer dereferencing with 'essence of' and address-of with 'sigil of'
    var value as int is 42
    let ptr as ref to int is sigil of value
    set essence of ptr is 100

    return 0
```

```c
int memory_demo(void) {
    char* buffer = (char*)malloc(1024);
    if (buffer == NULL) {
        return 1;
    }

    // Pointer arithmetic & dereference
    int value = 42;
    int* ptr = &value;
    *ptr = 100;

    // defer cleanup
    CloseWindow();
    free(buffer);
    return 0;
}
```

---

## 21. Transparent C Identifier Resolution

Any identifier originating from an `include` header (such as Raylib constants, OpenGL macros, or C enums) can be used directly without re-declaring them.

```pengu
include "raylib.h"

weave configure_window into void:
    let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
    let key is KEY_SPACE
```

```c
#include "raylib.h"

void configure_window(void) {
    int flags = FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT;
    int key = KEY_SPACE;
}
```

---

## 22. Complete Real-World Example: Raylib Game

```pengu
include "raylib.h"
link "raylib"
link "m"
link "pthread"

import std.spark

const SCREEN_WIDTH as int is 800
const SCREEN_HEIGHT as int is 600

rune Player:
    x as float
    y as float
    speed as float

enchanting Player:
    weave update into void:
        if calling IsKeyDown with KEY_RIGHT:
            set self->x is self->x + self->speed
        if calling IsKeyDown with KEY_LEFT:
            set self->x is self->x - self->speed

    weave draw into void:
        calling DrawCircle with (self->x to int) and (self->y to int) and 20.0 and MAROON

declare InitWindow with w as int and h as int and title as string into void
declare WindowShouldClose into bool
declare CloseWindow into void
declare SetTargetFPS with fps as int into void
declare BeginDrawing into void
declare EndDrawing into void
declare ClearBackground with color as ref to void into void
declare DrawCircle with x as int and y as int and radius as float and color as ref to void into void
declare IsKeyDown with key as int into bool

weave main into int:
    calling InitWindow with SCREEN_WIDTH and SCREEN_HEIGHT and "PenguScript 2D Game"
    defer calling CloseWindow

    calling SetTargetFPS with 60

    var player as Player is with x is 400.0 and y is 300.0 and speed is 5.0

    while calling WindowShouldClose is false:
        calling player.update

        calling BeginDrawing
        calling ClearBackground with RAYWHITE
        calling player.draw
        calling EndDrawing

    return 0
```

```c
#include "raylib.h"
#include "pengu_runtime.h"

#define SCREEN_WIDTH 800
#define SCREEN_HEIGHT 600

typedef struct {
    float x;
    float y;
    float speed;
} Player;

void Player_update(Player* self) {
    if (IsKeyDown(KEY_RIGHT)) self->x += self->speed;
    if (IsKeyDown(KEY_LEFT))  self->x -= self->speed;
}

void Player_draw(Player* self) {
    DrawCircle((int)self->x, (int)self->y, 20.0f, MAROON);
}

int main(void) {
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "PenguScript 2D Game");
    SetTargetFPS(60);

    Player player = (Player){ .x = 400.0f, .y = 300.0f, .speed = 5.0f };

    while (!WindowShouldClose()) {
        Player_update(&player);

        BeginDrawing();
        ClearBackground(RAYWHITE);
        Player_draw(&player);
        EndDrawing();
    }

    CloseWindow();
    return 0;
}
```

---

## 23. Standard Library Reference (24 Modules)

| Module         | Import                  | Description                                                                                                                                  |
| -------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **spark**      | `import std.spark`      | Core runtime and terminal I/O (`print`, `println`, `read_line`, ANSI styling, basic conversions, panic).                                     |
| **scrolls**    | `import std.scrolls`    | Comprehensive string manipulation (`split`, `join`, `replace`, `trim`, `starts_with`, `ends_with`, `contains`, case conversions).            |
| **oracle**     | `import std.oracle`     | Null-safe optional and functional error types (`MaybeInt`, `MaybeFloat`, `MaybeString`, `ResultInt`, `ResultString`, `is_present`, `is_ok`). |
| **tally**      | `import std.tally`      | Dynamic array and list manipulation utilities, element indexing, sorting, and transformations.                                               |
| **atlas**      | `import std.atlas`      | Hash map key-value store structures and mapping utilities.                                                                                   |
| **coven**      | `import std.coven`      | Dynamic unique set collections (`insert`, `contains`, `remove`, union, intersection, difference).                                            |
| **compass**    | `import std.compass`    | Cross-platform file path manipulation (`join`, `basename`, `dirname`, `ext`, normalization, absolute paths).                                 |
| **archivum**   | `import std.archivum`   | Complete file system operations: reading, writing, appending, copying, moving, deleting, directory listing, and metadata.                    |
| **arithmancy** | `import std.arithmancy` | Advanced mathematical functions: trigonometry (`sin`, `cos`, `tan`), powers, roots, logarithms, rounding, and clamping.                      |
| **chronicle**  | `import std.chronicle`  | High-precision time, timestamps, date/time formatting, monotonic clocks, sleep delays, and stopwatch benchmarking.                           |
| **lot**        | `import std.lot`        | Pseudorandom number generation, seeds, range-bounded integers/floats, and collection shuffling.                                              |
| **rites**      | `import std.rites`      | Operating system interface: process execution, environment variables, command running, and exit codes.                                       |
| **invoke**     | `import std.invoke`     | Command-line argument parsing for CLI applications (flags, options, positional arguments, and automated `--help`).                           |
| **ledger**     | `import std.ledger`     | High-performance CSV and TSV parsing, delimiter detection, and tabular row serialization.                                                    |
| **cipher**     | `import std.cipher`     | JSON serialization/deserialization and Base64 encoding/decoding.                                                                             |
| **parchment**  | `import std.parchment`  | XML and HTML DOM parsing, node traversal, attribute manipulation, and serialization (powered by `libxml2`).                                  |
| **regulus**    | `import std.regulus`    | High-performance regular expression compilation, matching, search, replace, and capture groups (powered by `PCRE2 10.47`).                   |
| **seal**       | `import std.seal`       | Cryptographic hashing (`MD5`, `SHA1`, `SHA256`, `SHA512`, `CRC32`) and gzip/zlib compression (`deflate`/`inflate`).                          |
| **precis**     | `import std.precis`     | Full networking stack: HTTP client (`GET`, `POST`, `PUT`, `DELETE`), embedded HTTP micro-server, TCP sockets, and URL encoding.              |
| **filum**      | `import std.filum`      | Concurrency primitives: thread spawning, communication channels, mutexes, wait groups, and atomics.                                          |
| **loom**       | `import std.loom`       | Functional collection utilities and iterators (`map`, `filter`, `reduce`, `zip`, chunking, flattening).                                      |
| **ward**       | `import std.ward`       | Runtime assertions and invariant validations (`assert`, `assert_eq`, `assert_ne`, `assert_present`, `assert_ok`, `panic`).                   |
| **trial**      | `import std.trial`      | Automated unit testing framework (suites, test cases, before/after lifecycle hooks, and colored reporting).                                  |
| **whisper**    | `import std.whisper`    | Structured logging framework with severity levels (`trace`, `debug`, `info`, `warn`, `error`, `fatal`).                                      |
