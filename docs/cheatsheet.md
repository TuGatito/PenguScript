# PenguScript 0.1.0 - Language Guide

## Whitespace
---

PenguScript is a whitespace sensitive language. This means that instead of using do and end (or { and }) to delimit sections of code we use line-breaks and indentation.

This means that how you indent your code is important. Luckily PenguScript doesn’t care how you do it but only requires that you be consistent.

An indent must be at least 1 space or 1 tab, but you can use as many as you like. All the code snippets on this page will use two spaces.

## Types
---

Table convention:
- **PenguScript**: what you write in the language.
- **C++20**: what the codegen outputs.
- **Header**: the `#include` that is added automatically.
- **Notes**: differences or pending decisions.

### Primitives (without includes)

| PenguScript | C++20 | Notas |
|---|---|---|
| `void` | `void` | keyword |
| `bool` | `bool` | |
| `char` | `char` | |
| `signed char` | `signed char` | |
| `unsigned char` | `unsigned char` | |
| `short` | `short` | |
| `unsigned short` | `unsigned short` | |
| `int` | `int` | |
| `unsigned int` | `unsigned int` | |
| `long` | `long` | |
| `unsigned long` | `unsigned long` | |
| `long long` | `long long` | |
| `unsigned long long` | `unsigned long long` | |
| `float` | `float` | |
| `double` | `double` | |
| `long double` | `long double` | |
| `wchar_t` | `wchar_t` | |
| `char8_t` | `char8_t` | C++20 |
| `char16_t` | `char16_t` | |
| `char32_t` | `char32_t` | |
| `nullptr_t` | `std::nullptr_t` | `<cstddef>` |

### Fixed-size integers

| PenguScript | C++20 | Header |
|---|---|---|
| `int8_t` / `int16_t` / `int32_t` / `int64_t` | `std::int8_t` … `std::int64_t` | `<cstdint>` |
| `uint8_t` / `uint16_t` / `uint32_t` / `uint64_t` | `std::uint8_t` … `std::uint64_t` | `<cstdint>` |
| `size_t` | `std::size_t` | `<cstddef>` |
| `ptrdiff_t` | `std::ptrdiff_t` | `<cstddef>` |
| `intptr_t` / `uintptr_t` | `std::intptr_t` / `std::uintptr_t` | `<cstdint>` |
| `byte` | `std::byte` | `<cstddef>` |

### Strings

| PenguScript | C++20 | Header | Notas |
|---|---|---|---|
| `string` | `std::string` | `<string>` | UTF-8 laxo (no estricto) |
| `wstring` | `std::wstring` | `<string>` | |
| `u8string` | `std::u8string` | `<string>` | C++20, UTF-8 estricto |
| `u16string` / `u32string` | `std::u16string` / `std::u32string` | `<string>` | |
| `string_view` | `std::string_view` | `<string_view>` | |
| `wstring_view` | `std::wstring_view` | `<string_view>` | |
| `u8string_view` | `std::u8string_view` | `<string_view>` | C++20 |
| `u16string_view` / `u32string_view` | idem | `<string_view>` | |

### Containers

| PenguScript | C++20 | Header |
|---|---|---|
| `vector<T>` | `std::vector<T>` | `<vector>` |
| `array<T, N>` | `std::array<T, N>` | `<array>` |
| `deque<T>` | `std::deque<T>` | `<deque>` |
| `list<T>` | `std::list<T>` | `<list>` |
| `forward_list<T>` | `std::forward_list<T>` | `<forward_list>` |
| `set<T>` | `std::set<T>` | `<set>` |
| `multiset<T>` | `std::multiset<T>` | `<set>` |
| `unordered_set<T>` | `std::unordered_set<T>` | `<unordered_set>` |
| `unordered_multiset<T>` | `std::unordered_multiset<T>` | `<unordered_set>` |
| `map<K,V>` | `std::map<K,V>` | `<map>` |
| `multimap<K,V>` | `std::multimap<K,V>` | `<map>` |
| `unordered_map<K,V>` | `std::unordered_map<K,V>` | `<unordered_map>` |
| `unordered_multimap<K,V>` | `std::unordered_multimap<K,V>` | `<unordered_map>` |
| `stack<T>` | `std::stack<T>` | `<stack>` |
| `queue<T>` | `std::queue<T>` | `<queue>` |
| `priority_queue<T>` | `std::priority_queue<T>` | `<queue>` |
| `span<T>` | `std::span<T>` | `<span>` |
| `pair<A,B>` | `std::pair<A,B>` | `<utility>` |
| `tuple<...>` | `std::tuple<...>` | `<tuple>` |
| `bitset<N>` | `std::bitset<N>` | `<bitset>` |

### Smart pointers

| PenguScript | C++20 | Header |
|---|---|---|
| `unique<T>` | `std::unique_ptr<T>` | `<memory>` |
| `shared<T>` | `std::shared_ptr<T>` | `<memory>` |
| `weak<T>` | `std::weak_ptr<T>` | `<memory>` |
| `ref<T>` | `T&` | Safe |
| `raw<T>` | `T*` | — (solo en `unsafe`) |

### Utilities and compound types

| PenguScript | C++20 | Header | Notas |
|---|---|---|---|
| `T?` | `std::optional<T>` | `<optional>` | **azúcar**; `T?` ≡ `optional<T>` |
| `optional<T>` | `std::optional<T>` | `<optional>` | forma larga |
| `variant<...>` | `std::variant<...>` | `<variant>` | |
| `any` | `std::any` | `<any>` | |
| `function<Sig>` | `std::function<Sig>` | `<functional>` | callbacks, not declarations |
| `init_list<T>` | `std::initializer_list<T>` | `<initializer_list>` | |
| `complex<T>` | `std::complex<T>` | `<complex>` | |
| `atomic<T>` | `std::atomic<T>` | `<atomic>` | |
| `mutex` | `std::mutex` | `<mutex>` | |
| `shared_mutex` | `std::shared_mutex` | `<shared_mutex>` | |
| `condition_variable` | `std::condition_variable` | `<condition_variable>` | |
| `thread` | `std::thread` | `<thread>` | |

## Imports
---

Every `.pengu` and `.d.pengu` file is a **module**. A module's declarations live in a **realm** — a named namespace, explained in the next section. To use another module, `invoke` it by path.

Imports are **top-level only**: they appear at the top of a file, before any declaration, and apply to the whole file. There is no `invoke` inside a function.

### Basic import

```coffee
invoke "math"

x = math::sqrt(2.0)
```

`invoke "math"` finds the module at `<project_root>/math` (resolved as `math.pengu` or `math/index.pengu`), reads its realm name, and binds that realm locally under its own name.

### Selective import

```coffee
invoke {sqrt, pow} from "math"

x = sqrt(2.0)
y = pow(2.0, 8)
```

Brings specific symbols directly into scope — no realm prefix. For when you use only a few names from a module and don't want the prefix noise.

### Aliases

Namespaces and individual symbols can both be renamed at import time:

```coffee
invoke "utils/strings" as str
s = str::upper("hello")

invoke {format as fmt_std} from "std/fmt"
invoke {format as fmt_json} from "json/fmt"
```

The alias is **local to the importing file**. Other files that import `"utils/strings"` still see it as `strings::` (its declared realm name).

### Path resolution

Import paths are **absolute from the project root** by default. The project root is the directory containing `pengu.toml`.

For a path `"foo"`, the compiler tries, in order:

1. `foo.pengu` (a file)
2. `foo/index.pengu` (a directory's entry point)

If both exist, `foo.pengu` wins. There is no extension guessing — `.pengu` is the only module extension.

**Relative imports** are available for local siblings. They start with `./` or `../` and resolve from the current file's directory:

```coffee
invoke "./sibling"
invoke "../shared/utils"
```

`../` is allowed but **discouraged**. Long chains like `../../../shared/utils` are a maintenance hazard — if the file moves, every relative import breaks. Prefer absolute paths unless the import is genuinely local.

### Cycles

Import cycles (`A` imports `B`, `B` imports `A`) are **compile errors**. The dependency graph must be a DAG. This makes load order deterministic and lets the compiler emit includes in the right order.

Diamond imports are fine: if `A` imports `B` and `C`, and both import `D`, then `D` is compiled once.

### Evaluation order

Imports run in the order they appear, top to bottom. A module's top-level `const` declarations are evaluated when the module is first imported, before any of its functions run.

```coffee
invoke "config"                -- config::DEFAULTS is computed here
invoke "logger"                -- logger uses config::DEFAULTS
```

### What gets imported

It works the same as C/C++. Public by default

## Realms
---

A **realm** is PenguScript's namespace. It groups top-level declarations under a name, so two modules can each define `format` without colliding, and so related symbols share a single access prefix.

It plays the role of `namespace` in C++, `package` in Go and Java, and `mod` in Rust — but with a shorter, more evocative keyword. `realm` is five letters, English-friendly for non-native speakers, and carries a connotation of *owned territory* that maps well to how namespaces actually behave: they own their symbols, they're defended by visibility rules, and they can be claimed by any module that declares them.

### Declaration

A realm is declared at the top of a file, before imports and declarations:

```coffee
realm geometry

invoke "math"

area = (r: double) -> double
  math::pi * r * r

_helper = (r: double) -> double 
  r * 2.0
```

The realm must be declared **before** any top-level statement. A file may declare **at most one** realm, and only one.

If a file declares no realm, its realm name defaults to the **file name** (without extension):

- `utils/strings.pengu` → implicit realm `strings`
- `utils/strings/index.pengu` → implicit realm `strings`

Every module has a realm — declared or not — and importers always bind that realm's name.

### Reopening

Multiple files may declare the same realm. Their symbols **merge** into a single namespace, like C++ `namespace` blocks or Go packages spread across files:

```coffee
-- geometry/circles.pengu
realm geometry
circle_area = (r: double) -> double
  pi * r * r

-- geometry/squares.pengu
realm geometry
square_area = (s: double) -> double
  s * s
```

Any file that imports either one sees `geometry::circle_area` (or `geometry::square_area`). To see both, import both files — the realm does not auto-import its siblings.

### Access — `::`

Symbols in a realm are accessed with `::`:

```coffee
invoke "geometry"

r = 2.0
a = geometry::circle_area(r)
```

The operator **`::`** is reserved for static, compile-time-resolved access — realms, modules, and their contents. The operator **`.`** is reserved for dynamic, runtime field access on values:

- `geometry::area` — the symbol `area` in realm `geometry` (resolved at compile time)
- `point.x` — the field `x` of the value `point` (resolved at runtime)

The two never mix. `geometry.x` is a type error (`geometry` is a realm, not a value); `point::x` is a type error (`point` is a value, not a realm). The distinction makes code readable at a glance: `::` always means "something named in a namespace", `.` always means "something stored in a value".

### Names on both sides

It works just like in C/C++. Everything is accessible from any place where the *realm* is imported. The Lua/C/Python convention for "private" symbols is used—for example, `_function_intended_for_internal_module_use_only`. This signals to the programmer that they should not use that method, though it remains technically accessible.

```coffee
realm strings

_helper = (s: ref<string>) -> string
  ...

upper = (s: ref<string>) -> string
  strings::_helper(s)                  -- OK: same module
  ...
```

### Comparison

| Concept | C++ | Go | Rust | PenguScript |
|---------|-----|----|------|-------------|
| Declaration | `namespace` | `package` | `mod` | `realm` |
| Access operator | `::` | `.` | `::` | `::` |
| Reopening across files | yes | yes (per package) | yes (per module tree) | yes |
| Visibility modifier | `public`/`private` in class| capitalized-first-letter | `pub` | no (convention: _prefix is private-by-convention)|
| Mutable realm member | yes | yes | yes | **no** (compile error) |

## Assignment
---

Variables must be declared and initialized.  This means that variables always have an initial value.

Variables infer the type from the value, but you can assign a specific type to them if needed.

Unlike most other languages, PenguScript, like V, only allows defining variables in functions. We do not allow global variables.

For consistency across different code bases, all variable and function names must use the snake_case style, as opposed to type names, which must use PascalCase.

```coffee
hello = "world"
mut a, b, c = 1, 2, 3
my_double: double = 12.11231
static mut speed = 200 -- Inside a function or struct

const GLOBAL_CONSTANT = 100 -- Unique way global
```

```c++
#include <string>

const std::string hello = "world";
int a = 1, b = 2, c = 3;
double my_double = 12.11231;
static int speed = 200;

constexpr int GLOBAL_CONSTANT = 100;
```

## Update Assignment

| Operator | Example | Same AS |
|---|---|---|
| = 	   | x = 5 	 | x = 5 	|
| += 	   | x += 3  | x = x + 3 |	
| -= 	   | x -= 3  | x = x - 3 |	
| *= 	   | x *= 3  | x = x * 3 |	
| /= 	   | x /= 3  | x = x / 3 |	
| %= 	   | x %= 3  | x = x % 3 |	
| &= 	   | x &= 3  | x = x & 3 |	
| |= 	   | x |= 3  | x = x | 3 |	
| ^= 	   | x ^= 3  | x = x ^ 3 |	
| >>= 	   | x >>= 3 | x = x >> 3 |	
| <<= 	   | x <<= 3 | x = x << 3 |

## Comments
---

Like Lua, comments start with -- and continue to the end of the line. 

```lua
-- I am a comment.
```

## Literals & Operators
---

Unlike C++, Line breaks are allowed inside of single and double quote strings without an escape sequence:

```coffee
some_string = "Here is a string
  that has a line break in it."

age = 42
user = "Alex"
result = "Name: #{user}, Age: #{age}"
```

```c++
#include <string>
#include <format>

const std::string some_string = "Here is a string\n  that has a line break in it.";
const int age = 42;
const std::string user = "Alex";
const std::string result = std::format("Name: {}, Age: {}", user, age);
```

## Function Literals
---

All functions are created using a function expression. A simple function is denoted using the arrow: ->

```coffee
my_function = -> void -- Declared

empty_function = -> void
  pass
empty_function! 
```

```c++
void my_function();

void empty_function() {}
empty_function();
```

The body of the function can either be one statement placed directly after the arrow (The return type will be inferred), or it can be a series of statements indented on the following lines:

```coffee
func_a = -> io::println("hello world")

func_b = -> void
  value = 100
  io::println("The value:", value)
```

```c++
void func_a(void) {
  io::println("hello world");
}

void func_b(void) {
  const int value = 100;
  io::println("The value:", value);
}
```

Functions will coerce the last statement in their body into a return statement, this is called implicit return:

```coffee
sum = (x: int, y: int) -> int
  x + y
```

```c++
int sum(int x, int y) {
  return x + y;
}
```

## Argument Defaults
---

Arguments may declare a default value. The default is applied when the argument is **omitted at the call site** — not when it is `null`. This is Kotlin-style semantics, and it separates two concerns that the previous design conflated:

- **Optionality** (`T?`) — the value may genuinely be absent.
- **Defaults** (`= expr`) — the caller may skip the argument.

A defaulted parameter has type `T` (not `T?`) inside the function body. Nullable-with-default (`T? = expr`) is deferred to a later version: distinguishing "omitted" from "passed `null`" requires `std::optional<std::optional<T>>` and is rarely needed in practice.

Once an argument declares a default, every following argument must also declare one.

Defaults are evaluated **inside the function body**, in declaration order, so a default may reference earlier arguments.

```coffee
sum = (x: int = 100, y = x + 1000) -> int
  x + y

sum()          -- 100 + 1100
sum(50)        -- 50 + 1050
sum(50, 60)    -- 50 + 60
```

```c++
int sum(std::optional<int> x_opt = std::nullopt,
        std::optional<int> y_opt = std::nullopt) {
  int x = x_opt ? *x_opt : 100;
  int y = y_opt ? *y_opt : (x + 1000);
  return x + y;
}
```

Codegen rules:

- Every defaulted parameter is emitted as `std::optional<T> name_opt = std::nullopt`.
- At the top of the function body, in declaration order, the compiler emits `T name = name_opt ? *name_opt : default_expr;`. The ternary is **lazy** — the default expression is not evaluated when the argument is provided.
- The rest of the body sees `name` as type `T`. The `_opt` names are not visible to the programmer.
- Calls in PenguScript never pass `nullopt`. Omission is the only way to use a default. Passing a `T?` value to a `T` parameter is a type error.
- Move-only types (e.g. `unique<T>`) are handled by moving out of `name_opt`: `T name = name_opt ? std::move(*name_opt) : default_expr;`.

## Memory

PenguScript has no garbage collector. Every allocation is freed at a well-defined point: by scope (values), by ownership (smart pointers), or explicitly through unsafe code. That determinism is the point — but it means the programmer has to decide *how* each piece of data is owned and accessed.

To keep that decision tractable, PenguScript follows one rule, borrowed from safe C++ practice:

> **References → Smart pointers → Pointers.**
> Only step up a level when it is absolutely necessary, and verify that it is truly safe to do so.

Each level adds power and removes safety. Most code lives at level 0 or 1. Level 2 is for dynamic lifetimes. Level 3 is a controlled escape hatch.

### The ladder

| Level | Type | Ownership | Nullable | Heap | Checked | C++20 |
|-------|------|-----------|----------|------|---------|-------|
| 0 | `T` | value (stack or in-place) | no | no | **yes** | `T` |
| 1 | `ref<T>` | borrowed, non-owning | no | no | **yes** | `const T&` |
| 2 | `unique<T>` | sole owner | no | yes | **yes** | `std::unique_ptr<T>` |
| 2 | `shared<T>` | shared owner | no | yes | **yes** | `std::shared_ptr<T>` |
| 2 | `weak<T>` | observer of `shared` | yes | no | **yes** | `std::weak_ptr<T>` |
| 3 | `raw<T>` | non-owning pointer | yes | no | **no** | `T*` |

Absence is orthogonal to ownership: use `T?` (≡ `optional<T>` ≡ `std::optional<T>`) to express "may not exist". `unique<T>?` is a nullable unique pointer; `int?` is a nullable int.

### Level 0 — Values (`T`)

The default. Stored on the stack (locals) or inline (fields), copied on assignment, moved when possible.

```coffee
greeting = "hello"
numbers = vector<int>[1, 2, 3]
origin = Point(0, 0)
```

```c++
const std::string greeting = "hello";
const std::vector<int> numbers = {1, 2, 3};
const Point origin = Point(0, 0);
```

Use values whenever the data does not need to outlive its scope. Passing a value copies it; use `ref<T>` to avoid the copy.

### Level 1 — References (`ref<T>`)

A reference is a **non-owning, non-nullable view** of an existing value. Zero overhead: it compiles to a C++ reference.

```coffee
print_name = (name: ref<string>) -> void
  io::println(name)

increment = (mut count: int) -> void
  count += 1

count = 0
increment(mut count)
print_name(greeting)
```

```c++
void print_name(const std::string& name) {
  io::println(name);
}

void increment(int& count) {
  count += 1;
}

int count = 0;
increment(count);
print_name(greeting);
```

Rules:

- `ref<T>` is always initialized — as a parameter, or with `ref(x)` for a local alias.
- `ref<T>` cannot be null. If absence is meaningful, use `T?`.
- `mut x: T` already compiles to `T&`. Do not write `mut ref<T>` — it is redundant.
- Assignment through a `mut ref<T>` writes to the **referent**. Rebinding is not possible; use `raw<T>` under `unsafe` if you need that.
- `ref<T>` is **not allowed as a struct field.** Use `raw<T>` under `unsafe` if a borrow must outlive the current scope; the danger has to be visible.
- `ref<shared<T>>` is redundant: declare `mut x: shared<T>` instead.
- Passing a temporary to `ref<T>` extends its lifetime for the call (same as C++).

### Level 2 — Smart pointers (`unique<T>`, `shared<T>`, `weak<T>`)

When data must outlive the current scope, it lives on the heap. The pointer carries ownership, so it is freed automatically — manual lifetime control **without** manual `delete`.

- **`unique<T>`** — single owner, move-only. No runtime overhead. **Default for heap allocation.**
- **`shared<T>`** — multiple owners, reference-counted. Use only when ownership is genuinely shared.
- **`weak<T>`** — an observer of a `shared<T>`. Does not keep the value alive. Use it to break reference cycles.

```coffee
box = unique<Node>(42)
process(box)                  -- moves box; box is invalid afterwards

config = shared<Config>(Config())
worker = (c: shared<Config>) -> void
  io::println(c.name)

root = shared<Node>(0)
child = shared<Node>(1)
root.child = child             -- shared → shared
child.parent = weak(root)      -- shared → weak (breaks the cycle)
```

```c++
auto box = std::make_unique<Node>(42);
process(std::move(box));

auto config = std::make_shared<Config>();
void worker(std::shared_ptr<Config> c) {
  io::println(c->name);
}

auto root  = std::make_shared<Node>(0);
auto child = std::make_shared<Node>(1);
root->child  = child;
child->parent = root;   // weak_ptr<Node>
```

Style rules:

- **Prefer `unique<T>` over `shared<T>`.** Reach for `shared<T>` only when you can point at the exact places that need to co-own the value.
- **`shared<T>` must not form cycles** without a matching `weak<T>`. The language does not detect this — it is a documented contract, the same as in C++ and Rust.
- Construction goes through `unique<T>(args...)` / `shared<T>(args...)`; the compiler emits `std::make_unique` / `std::make_shared`, so allocation and construction stay fused.
- Passing a `unique<T>` **by value moves it.** To keep ownership, pass `mut ref<unique<T>>` to mutate in place, or `raw<T>` under `unsafe` to observe without owning.
- `weak<T>` may be null; access requires promotion (`w.lock()`), which the compiler emits automatically on `.` access.

### Level 3 — Raw pointers (`raw<T>`)

A raw pointer is an address. It owns nothing, it may be null, and nothing guarantees it points to live memory. It exists for three reasons:

1. Interop with C APIs (`fopen`, `read`, `mmap`, …).
2. Systems-level layouts (device registers, packed structs, custom allocators).
3. Pointer arithmetic and reinterpretation.

Every use of `raw<T>` requires `unsafe`. Outside an unsafe context, `raw<T>` does not type-check.

### `unsafe` — the escape hatch

`unsafe` marks code the compiler cannot verify. It does not change the generated code; it only opens the door to operations that are otherwise rejected. There are two forms.

**Unsafe function** — the body runs in an unsafe context, and **the caller must also be in an unsafe context**:

```coffee
unsafe write_u8 = (p: raw<uint8_t>, v: uint8_t) -> void
  *p = v

set_flag = (p: raw<uint8_t>) -> void
  unsafe
    write_u8(p, 1)
```

```c++
void write_u8(std::uint8_t* p, std::uint8_t v) {
  *p = v;
}

void set_flag(std::uint8_t* p) {
  write_u8(p, 1);
}
```

**Unsafe block** — a scoped region inside otherwise safe code:

```coffee
read_bytes = (buf: raw<uint8_t>, n: size_t) -> uint8_t
  total: uint8_t = 0
  unsafe
    for i in 0..<n
      total += buf[i]
  total
```

```c++
std::uint8_t read_bytes(std::uint8_t* buf, std::size_t n) {
  std::uint8_t total = 0;
  for (std::size_t i = 0; i < n; ++i) {
    total += buf[i];
  }
  return total;
}
```

Rules:

- **`raw<T>` only appears inside `unsafe`.** Anywhere else it is a compile error.
- **An unsafe function is unsafe to call.** Calling it from safe code requires wrapping the call in `unsafe` (or being inside another unsafe function).
- **Keep `unsafe` blocks as small as possible.** The larger the block, the more code loses compiler guarantees.
- **Justify every `unsafe` with a comment.** Inside an unsafe block, the compiler trusts the programmer — say why that trust is warranted.
- **Never return `ref<T>` from safe code.** If a function must return a borrowed view that outlives its arguments, it must be `unsafe` and return `raw<T>` (or return a value instead).

### Choosing a type — quick reference

| Situation | Use |
|-----------|-----|
| Local data, not shared | `T` |
| Argument, avoid copy | `ref<T>` |
| Argument, mutate caller's value | `mut x: T` |
| Heap allocation, single owner | `unique<T>` |
| Heap allocation, shared owner | `shared<T>` |
| Back-reference inside a `shared` graph | `weak<T>` |
| Value may be absent | `T?` |
| C interop, pointer arithmetic | `raw<T>` + `unsafe` |

## Arrays
---

PenguScript has two ordered sequence types. They share **literal syntax, indexing, length, and iteration** — only the type annotation decides which one you get:

- `vector<T>` — dynamic, heap-allocated, growable. **Default for `[...]` literals.**
- `array<T, N>` — fixed size, stack-allocated. `N` is part of the type.

Both map to `<vector>` / `<array>` respectively. `array<T, N>` has no `push`/`pop`; everything else is identical.

### Literals

An array literal is written with `[...]`, comma-separated. Types are inferred from the first element, or forced with a type prefix. All elements must have the same type.

```coffee
empty: vector<int> = []       -- empty needs a type annotation
primes = [2, 3, 5, 7, 11]     -- vector<int>
matrix = [[1, 2], [3, 4]]     -- vector<vector<int>>
fixed: array<int, 4> = [1, 2, 3, 4]

explicit = vector<int>[1, 2, 3]   -- same as [1, 2, 3], but typed
```

```c++
const std::vector<int> primes = {2, 3, 5, 7, 11};
const std::vector<std::vector<int>> matrix = {{1, 2}, {3, 4}};
const std::array<int, 4> fixed = {1, 2, 3, 4};

const std::vector<int> explicit_ = std::vector<int>{1, 2, 3};
```

An empty literal `[]` without a type annotation is a compile error — the element type cannot be inferred.

### Access

Indexing is **0-based**. There are three accessors, depending on what should happen out of bounds.

```coffee
first = primes[0]           -- checked
last  = primes[#primes - 1] -- checked

maybe = primes.get(0)       -- T?, nullopt if out of bounds

unsafe
  fast = primes.get_unchecked(0)   -- no bounds check
```

```c++
int first = primes.at(0);
int last  = primes.at(primes.size() - 1);

std::optional<int> maybe = get_at(primes, 0);

// inside unsafe
int fast = primes[0];
```

| Form | Bounds | Returns | Requires `unsafe` |
|------|--------|---------|-------------------|
| `arr[i]` | checked | `T` (throws on OOB) | no |
| `arr.get(i)` | checked | `T?` (`nullopt` on OOB) | no |
| `arr.get_unchecked(i)` | **unchecked** | `T` (UB on OOB) | **yes** |

Use `arr[i]` when you have already proven `i` is valid. Use `arr.get(i)` when absence is a legitimate outcome. Use `arr.get_unchecked(i)` only in hot loops where the bound has been hoisted into an `unsafe` block with an explicit invariant comment.

`arr.get(i)` requires `T: copyable`. For move-only element types (e.g. `vector<unique<Node>>`), use `#arr > i` followed by `arr[i]` — `get` would otherwise have to move out of the container.

### Length

`#` returns the number of elements. It works on any sequence-like type (`vector<T>`, `array<T,N>`, `string`, `string_view`, `span<T>`).

```coffee
n = #primes
```

```c++
std::size_t n = primes.size();
```

### Editing

Writing through an index uses the same `[]` syntax and is bounds-checked:

```coffee
primes[0] = 1                 -- checked write

primes.push(13)               -- append
removed = primes.pop()        -- remove last, returns T (panics if empty)
maybe   = primes.pop_opt()    -- returns T?

primes.insert(2, 99)          -- insert at index 2, shifts right
gone    = primes.remove_at(2) -- remove by index, returns removed T
primes.clear()                -- empty

b = 7 in primes               -- membership
```

```c++
primes.at(0) = 1;

primes.push_back(13);
int removed = pop_back_checked(primes);          // helper, panics if empty
std::optional<int> maybe = pop_back_optional(primes);

primes.insert(primes.begin() + 2, 99);
int gone = erase_at(primes, 2);

primes.clear();

bool b = std::find(primes.begin(), primes.end(), 7) != primes.end();
```

`array<T, N>` does **not** have `push`, `pop`, `insert`, `remove_at`, or `clear` — its length is fixed at compile time. Calling any of them on a fixed-size array is a compile error.

### Iteration

`for ... in arr` iterates values. `for i, x in arr` iterates both index and value. Iteration binds **references by default** — no copies.

```coffee
for x in primes               -- const T& per element
  io::println(x)

for mut x in primes           -- T& per element; writes persist
  x *= 2

for i, x in primes            -- i: size_t, x: const T&
  io::println(i, x)

for i, mut x in primes        -- both index and mutable element
  x += i
```

```c++
for (const auto& x : primes) {
  io::println(x);
}

for (auto& x : primes) {
  x *= 2;
}

for (std::size_t i = 0; i < primes.size(); ++i) {
  const auto& x = primes.at(i);
  io::println(i, x);
}

for (std::size_t i = 0; i < primes.size(); ++i) {
  auto& x = primes.at(i);
  x += i;
}
```

Same `mut` rules as function parameters: without `mut`, iteration binds a `const T&` and you cannot reassign the loop variable. `mut` on `x` gives you `T&` and mutations persist in the container. `mut` on `i` is not allowed — the index is a fresh value each iteration.

### Bounds and safety summary

All out-of-bounds behavior is **deterministic**:

- `arr[i]` — panics (`std::out_of_range` is caught by the runtime and reported as a panic, not propagated as an exception to user code).
- `arr.get(i)` — returns `nullopt`.
- `arr.get_unchecked(i)` — undefined behavior, `unsafe` only.

If you want the panic to become a value, use `arr.get(i)`:

```coffee
match primes.get(idx)
  Some(v) then io::println("found", v)
  None    then io::println("no such index")
```

(Nullability pattern matching is not yet specified — placeholder syntax, to be finalized with `none`/`??`/`match`.)

### Fixed-size vs dynamic

Choose `array<T, N>` when the size is known at compile time — it is stack-allocated, has no heap overhead, and its length is a type-level constant.

Choose `vector<T>` for everything else. It is the idiomatic default; the extra heap allocation is almost never the bottleneck.

```coffee
rgb: array<uint8_t, 3> = [255, 128, 0]    -- stack, no alloc
pixels: vector<uint8_t> = []              -- heap, growable
```

Both satisfy `#`, `[]`, `get`, iteration, and `in`.

## Maps
---

PenguScript has four mapping types. All share the same **literal syntax, accessors, iteration, and editing API**; only ordering and multiplicity differ.

| Type | Order | Values per key | Lookup | C++20 |
|------|-------|----------------|--------|-------|
| `map<K,V>` | sorted by `K` | exactly 1 | `O(log n)` | `std::map<K,V>` |
| `unordered_map<K,V>` | unspecified | exactly 1 | `O(1)` avg | `std::unordered_map<K,V>` |
| `multimap<K,V>` | sorted by `K` | 0 or more | `O(log n)` | `std::multimap<K,V>` |
| `unordered_multimap<K,V>` | unspecified | 0 or more | `O(1)` avg | `std::unordered_multimap<K,V>` |

`map<K,V>` is the default for `{...}` literals — deterministic iteration is worth `O(log n)` for the vast majority of code. Reach for `unordered_map` only when profiling says you need it; reach for `multimap` when a key can legitimately repeat.

Sets (`set<T>`, `unordered_set<T>`, etc.) are key-only maps and share the same literal syntax — see the end of this section.

### Literals

A map literal is written `{key: value, ...}`. Types are inferred from the entries, or forced with a type prefix.

```coffee
empty: map<string, int> = {}

ages = {"alice": 30, "bob": 25}              -- map<string, int>
scores: map<string, double> = {"alice": 9.5}  -- forced value type
```

**Bare identifiers as keys** are sugar for string literals:

```coffee
config = {host: "localhost"}   -- key is the string "host"
```

A map has **one value type**. Mixing values is a type error:

```coffee
bad = {host: "localhost", port: 8080}   -- ✗ string vs int
```

For heterogeneous values, use `variant`:

```coffee
config: map<string, variant<string, int>> = {
  host: "localhost",
  port: 8080,
}
```

**Computed keys** use brackets:

```coffee
{[1]: "one", [2]: "two"}      -- map<int, string>
k = "alice"
{[k]: 30}                      -- map<string, int>, key is the value of `k`
```

The bare-identifier rule is deliberate: `{alice: 30}` always means the string key `"alice"`, never the variable `alice`. Wrap the variable in brackets to use its value as the key.

**Multiline literals** may omit trailing commas when each entry is on its own line:

```coffee
routes = {
  "/": "home"
  "/about": "about"
  "/contact": "contact"
}
```

An empty literal `{}` without a type annotation is a compile error.

### Access

Maps have the same three accessors as arrays. **`m[k]` never accidentally inserts** — unlike C++'s `map::operator[]`, which default-constructs on missing keys.

```coffee
v = m["alice"]                    -- V (panics if missing)
maybe = m.get("alice")            -- V? (nullopt if missing)
fallback = m.get_or("alice", 0)   -- V (default if missing)
```

```c++
int v = m.at("alice");                             // throws → panic
std::optional<int> maybe = map_get(m, "alice");    // helper
int fallback = map_get_or(m, "alice", 0);          // helper
```

| Form | Bounds | Returns | Requires `unsafe` |
|------|--------|---------|-------------------|
| `m[k]` | checked | `V` (panics if missing) | no |
| `m.get(k)` | checked | `V?` | no |
| `m.get_or(k, default)` | checked | `V` | no |

`.get(k)` requires `V: copyable`. For move-only values (e.g. `map<string, unique<Node>>`), use `.extract(k) -> V?`, which moves the value out and removes the entry. `.remove(k)` (below) also requires `V: moveable`, which is satisfied by all types.

`multimap` does **not** support `m[k]` — a key may map to multiple values, so the result would be ambiguous. Use `.get(k)` for the first value or `.get_all(k)` for all of them:

```coffee
first = tags.get("color")       -- V? (first value with key "color")
all   = tags.get_all("color")   -- vector<V> (every value with key "color")
```

### Length and membership

```coffee
n = #m               -- size_t: number of entries
has = "alice" in m   -- bool: does the key exist?
```

`#m` on a `multimap` counts **total pairs**, not unique keys. Use `.key_count()` for distinct keys:

```coffee
pairs = #tags             -- total entries
keys  = tags.key_count()  -- size_t: distinct keys
```

### Editing

```coffee
m["alice"] = 31                  -- insert or update
inserted = m.insert("bob", 25)   -- bool (false if "bob" already existed)
removed  = m.remove("alice")     -- V? (removed value, or nullopt)
m.clear()
```

```c++
m.insert_or_assign("alice", 31);
bool inserted = m.insert({"bob", 25}).second;
std::optional<int> removed = map_remove(m, "alice");
m.clear();
```

`m.insert(k, v)` on `multimap` always succeeds (adds another entry) and returns `void`:

```coffee
tags.insert("color", "red")
tags.insert("color", "blue")          -- both retained
tags.insert_all("color", ["green", "yellow"])
```

Multimap removal has two forms:

```coffee
one  = tags.remove("color")       -- V? (first value removed)
many = tags.remove_all("color")   -- size_t (count removed)
```

### Iteration

```coffee
for k, v in m                -- pairs (zero-copy)
  io::println(k, v)

for k, mut v in m            -- pairs, values mutable
  v += 1

for k in m.keys              -- keys only
  io::println(k)

for v in m.values            -- values only
  io::println(v)
```

```c++
for (const auto& [k, v] : m)  { io::println(k, v); }
for (auto& [k, v] : m)        { v += 1; }
for (const auto& [k, _] : m)  { io::println(k); }
for (const auto& [_, v] : m)  { io::println(v); }
```

Keys are always `const` — you cannot mutate a map key during iteration. Values can be mutated with `mut v`.

`m.keys` and `m.values` are **iteration targets only** — they do not exist as standalone values. To materialize them:

```coffee
ks = [k for k, _ in m]     -- vector<K>
vs = [v for _, v in m]     -- vector<V>
```

### Order and hashing

`map` and `multimap` iterate in **ascending key order** — deterministic, stable across runs.

`unordered_map` and `unordered_multimap` iterate in **unspecified order**. Never depend on insertion order or hash order for correctness.

Key requirements:

| Type | `K` must implement |
|------|--------------------|
| `map<K,V>` | `<` (strict weak order) |
| `unordered_map<K,V>` | `==` and a hash function |

Primitives, `string`, and `pair<A,B>` satisfy both. Custom types compare field-by-field in declaration order (for `<`) and require `#[derive(Hash)]` for unordered variants — the same mechanism as Rust or Kotlin data classes.

### Sets (brief)

Sets share the map literal syntax with one difference: **no values**. Prefix with `set` to disambiguate:

```coffee
empty: set<int> = set{}
colors = set{"red", "green", "blue"}
nums: unordered_set<int> = unordered_set{1, 2, 3}
```

`{}` always means an empty **map**, never an empty set. Sets require the `set{}` or `unordered_set{}` prefix.

```coffee
colors.contains("red")    -- bool
colors.insert("yellow")   -- bool (false if already present)
colors.remove("red")      -- bool (false if absent)
#colors                   -- size_t
for c in colors           -- elements
  io::println(c)
```

Sets iterate in sorted order (for `set<T>`) or unspecified order (for `unordered_set<T>`). Set operations (`union`, `intersection`, `difference`) are not defined in v0.1.0 — use `for` + `insert` explicitly.

### Quick reference

| Operation | `map` | `multimap` | `unordered_map` | `unordered_multimap` |
|-----------|:-----:|:----------:|:---------------:|:--------------------:|
| `m[k]` | ✅ | ❌ | ✅ | ❌ |
| `m[k] = v` | ✅ | ❌ | ✅ | ❌ |
| `m.get(k) -> V?` | ✅ | ✅ (first) | ✅ | ✅ (first) |
| `m.get_or(k, d) -> V` | ✅ | ❌ | ✅ | ❌ |
| `m.get_all(k) -> vector<V>` | ❌ | ✅ | ❌ | ✅ |
| `m.insert(k, v)` | `-> bool` | `-> void` | `-> bool` | `-> void` |
| `m.insert_all(k, vs)` | ❌ | `-> void` | ❌ | `-> void` |
| `m.remove(k) -> V?` | ✅ | ✅ (first) | ✅ | ✅ (first) |
| `m.remove_all(k) -> size_t` | ❌ | ✅ | ❌ | ✅ |
| `m.key_count() -> size_t` | ❌ | ✅ | ❌ | ✅ |
| `#m` | ✅ | ✅ | ✅ | ✅ |
| `k in m` | ✅ | ✅ | ✅ | ✅ |
| `for k, v in m` | ✅ | ✅ | ✅ | ✅ |
| `for k in m.keys` | ✅ | ✅ | ✅ | ✅ |
| `for v in m.values` | ✅ | ✅ | ✅ | ✅ |

## Control Flow
---

### Boolean operators

PenguScript uses words for boolean operators, not symbols:

| Operator | C++20 | Meaning |
|----------|-------|---------|
| `not x` | `!x` | logical negation |
| `a and b` | `a && b` | logical AND (short-circuit) |
| `a or b` | `a \|\| b` | logical OR (short-circuit) |

Precedence, loosest to tightest: `or` → `and` → `not` → comparison → arithmetic. This means `not a == b` parses as `not (a == b)`, matching Python. Parenthesize when in doubt.

All three operators require `bool` operands. PenguScript has **no truthiness** — `if 0` and `if x` (where `x : T?`) are type errors. Write the comparison explicitly:

```coffee
if x != none            -- not `if x`
if #arr > 0             -- not `if arr`
if not done             -- ok, `done : bool`
```

Composition:

```coffee
if x > 0 and x < 100
  io::println("in range")

if name == "alex" or name == "pengu"
  io::println("known user")

if not (done or failed)
  io::println("running")
```

`not in` is available as sugar for `not (x in seq)`:

```coffee
if x not in blocked
  io::println("allowed")
```

### `if` / `else if` / `else` / `unless`

Statements use indentation. The `else` must be at the same indent as the `if`.

```coffee
if x > 0
  io::println("positive")
else if x < 0
  io::println("negative")
else
  io::println("zero")
```

```c++
if (x > 0) {
  io::println("positive");
} else if (x < 0) {
  io::println("negative");
} else {
  io::println("zero");
}
```

`unless cond` is sugar for `if not cond`:

```coffee
unless done
  io::println("still running")
```

```c++
if (!(done)) {
  io::println("still running");
}
```

`if` is also an **expression**, when it produces a value in every branch:

```coffee
-- inline (requires `then`)
sign = if x > 0 then "positive" else if x < 0 then "negative" else "zero"

-- multi-line
status = if count > 0
  "ok"
else if count == 0
  "empty"
else
  "invalid"
```

```c++
std::string sign = [&]() -> std::string {
  if (x > 0) return "positive";
  if (x < 0) return "negative";
  return "zero";
}();

std::string status = [&]() -> std::string {
  if (count > 0) return "ok";
  if (count == 0) return "empty";
  return "invalid";
}();
```

The compiler emits a ternary when the expression is a single two-branch `if`, and an IIFE otherwise.

### `while` and `until`

```coffee
while count < 10
  count += 1
```

```c++
while (count < 10) {
  count += 1;
}
```

`until cond` is sugar for `while not cond`:

```coffee
until count >= 10
  count += 1
```

```c++
while (!(count >= 10)) {
  count += 1;
}
```

### `repeat ... until`

A post-condition loop. The body runs at least once; the condition is checked after each iteration.

```coffee
repeat
  line = read_line()
  process(line)
until line == "quit"
```

```c++
std::string line;
do {
  line = read_line();
  process(line);
} while (!(line == "quit"));
```

`repeat` has no pre-condition — it always runs at least once. For the common case (read-until-EOF), `repeat ... until` avoids the "prime the first read" pattern that `while` forces.

### `for` — numeric form

The MoonScript-style numeric loop. Bounds are **inclusive** on both ends.

```coffee
for i = 1, 10
  io::println(i)

for i = 10, 1
  io::println(i)       -- direction inferred from bounds

for i = 1, 10, 2
  io::println(i)       -- explicit step

for i = 10, 1, -2
  io::println(i)       -- explicit negative step
```

```c++
for (int i = 1; i <= 10; ++i)       { io::println(i); }
for (int i = 10; i >= 1; --i)       { io::println(i); }
for (int i = 1; i <= 10; i += 2)    { io::println(i); }
for (int i = 10; i >= 1; i -= 2)    { io::println(i); }
```

The direction is inferred when the step is omitted. If the step is provided, its sign must match `b - a` — `for i = 1, 10, -1` is a compile error.

The loop variable's type is the common type of the endpoints. Integer literals coerce to it, so `for i = 1, #arr` gives `i : size_t` because `#arr` is `size_t`. To be explicit:

```coffee
for i: size_t = 0, n - 1
  ...
```

### `for` — iterable form

`for x in seq` iterates any sequence-like value: `vector<T>`, `array<T,N>`, `string`, `string_view`, `span<T>`, and ranges. Bindings are references by default (same rules as in **Arrays**).

```coffee
for x in items                -- x: const T&
  io::println(x)

for mut x in items            -- x: T&; writes persist
  x *= 2

for i, x in items             -- i: size_t, x: const T&
  io::println(i, x)
```

```c++
for (const auto& x : items) { io::println(x); }
for (auto& x : items)       { x *= 2; }
for (std::size_t i = 0; i < items.size(); ++i) {
  const auto& x = items.at(i);
  io::println(i, x);
}
```

### Ranges

`a..b` is inclusive; `a..<b` is exclusive. Both endpoints must have the same type; integer literals coerce to the other endpoint's type.

```coffee
for i in 0..<#items
  io::println(items[i])

for i in 1..100
  total += i
```

```c++
for (std::size_t i = 0; i < items.size(); ++i) {
  io::println(items.at(i));
}

for (int i = 1; i <= 100; ++i) {
  total += i;
}
```

Ranges are **not first-class values** in v0.1.0 — they only appear in `for`. Passing a range to a function (e.g. `sum(1..100)`) is a future feature.

### Loop control — `break`, `continue`, `break value`

`break` exits the innermost loop. `continue` skips to the next iteration.

```coffee
for i = 1, 10
  if i == 5
    break
  if i % 2 == 0
    continue
  io::println(i)      -- prints 1, 3
```

```c++
for (int i = 1; i <= 10; ++i) {
  if (i == 5) break;
  if (i % 2 == 0) continue;
  io::println(i);
}
```

`break value` exits the loop **with a value**. This is how loops become expressions that produce a `T?`:

```coffee
found = for x in items
  if x > 100
    break x
-- found : int? — nullopt if no element exceeds 100
```

```c++
std::optional<int> found = [&]() -> std::optional<int> {
  for (const auto& x : items) {
    if (x > 100) return x;
  }
  return std::nullopt;
}();
```

Rules:

- If **any** `break` in a loop carries a value, **all** `break`s in that loop must carry values of the **same type `T`**.
- A loop with typed `break`s has type `T?`. `nullopt` means "the loop ran to completion without breaking".
- A loop with no `break value` is a **statement** — it has no value, and using it in value position is a type error.
- `continue` never carries a value.

### Loop `else`

`for ... else` and `while ... else` run the `else` block when the loop completed **without `break`**. This is the idiomatic "no element matched" pattern, borrowed from Python and V.

```coffee
for x in items
  if x == target
    io::println("found")
    break
else
  io::println("not in list")
```

```c++
bool _broke = false;
for (const auto& x : items) {
  if (x == target) {
    io::println("found");
    _broke = true;
    break;
  }
}
if (!_broke) {
  io::println("not in list");
}
```

`else` runs when the loop **never broke**, not when the loop body was never executed. An empty loop still runs `else`.

`while` and `repeat` accept `else` too, with the same semantics.

### Comprehensions

A comprehension collects the value of an expression into a `vector<T>`. It is the primary way to build an array from a loop.

```coffee
squares = [x * x for x in items]
evens   = [x for x in items if x % 2 == 0]
both    = [x * x for x in items if x % 2 == 0]
nums    = [i for i in 0..<10]

-- numeric form inside brackets
cubes   = [i * i * i for i = 1, 10]

-- multiple `for` clauses = nested loops (last clause varies fastest)
pairs   = [[x, y] for x in xs for y in ys]

-- index binding
tagged  = [f"{i}:{x}" for i, x in items]
```

```c++
auto squares = [&]() {
  std::vector<int> _out;
  for (const auto& x : items) _out.push_back(x * x);
  return _out;
}();

auto evens = [&]() {
  std::vector<int> _out;
  for (const auto& x : items) {
    if (!(x % 2 == 0)) continue;
    _out.push_back(x);
  }
  return _out;
}();

auto nums = [&]() {
  std::vector<std::size_t> _out;
  for (std::size_t i = 0; i < 10; ++i) _out.push_back(i);
  return _out;
}();

auto pairs = [&]() {
  std::vector<std::vector<int>> _out;
  for (const auto& x : xs) {
    for (const auto& y : ys) {
      _out.push_back({x, y});
    }
  }
  return _out;
}();
```

Rules:

- The result is always `vector<T>`, where `T` is the type of the value expression.
- The `if` clause is optional; it acts as a filter (`continue` when false).
- Multiple `for` clauses nest left-to-right; the **last** clause is the innermost loop.
- Same `mut`/binding rules as regular `for` apply.
- Comprehensions are expressions — they can be assigned, returned, or passed as arguments.

### Summary

| Construct | Form | Value? | C++20 |
|-----------|------|--------|-------|
| `if` / `else` | statement | no | `if` / `else` |
| `if ... then ... else ...` | expression | `T` | ternary or IIFE |
| `unless cond` | statement | no | `if (!(cond))` |
| `while cond` | statement | no | `while` |
| `until cond` | statement | no | `while (!(cond))` |
| `repeat ... until` | statement | no | `do { } while (!(cond))` |
| `for i = a, b[, step]` | statement | no | numeric `for` |
| `for x in seq` | statement | no | range-`for` |
| `for ... else` | statement | no | `for` + broke flag |
| `while ... else` | statement | no | `while` + broke flag |
| `break` | statement | — | `break;` |
| `continue` | statement | — | `continue;` |
| `break value` | expression | `T?` | `return value;` in IIFE |
| `[expr for ...]` | expression | `vector<T>` | IIFE + `push_back` |

## Runes
---

A **rune** is PenguScript's product type. It groups named fields into a single value, and optionally declares lifecycle methods (constructor, destructor). Behavior is added separately in `enchanting` blocks.

Runes are **not classes**. There is no virtual dispatch, no interfaces, no objects, no `this` pointer passed around. A rune is a `struct` — a named layout of fields — with a few conveniences layered on top. This is a deliberate choice: PenguScript has no OOP.

Runes support **C-style single inheritance**: a rune may inherit from exactly one other rune. There is no multiple inheritance, no mixins, and **no implicit upcasting** (see *Slicing* below).

### Declaration

A rune is declared in a realm (or in the module's implicit realm) with fields and optional lifecycle methods:

```coffee
realm shapes

rune Point
  x: double
  y: double

  constructor(x: double, y: double)
    @x = x
    @y = y

  destructor
    io::println("Point gone")
```

`constructor` and `destructor` are **keywords**. They appear at field indentation inside the rune body, in any order relative to fields, but at most one of each per rune.

Lifecycle methods live **inside** the rune. All other methods live in `enchanting` blocks (below).

### Constructor and destructor

```coffee
rune Dog
  name: string
  age: int

  constructor(name: string, age: int = 0)
    @name = name
    @age = age

  destructor
    io::println(f"goodbye {@name}")
```

```c++
struct Dog {
  std::string name;
  int age;

  Dog(std::string name, std::optional<int> age_opt = std::nullopt) {
    this->name = name;
    this->age = age_opt ? *age_opt : 0;
  }

  ~Dog() {
    io::println(std::format("goodbye {}", this->name));
  }
};
```

Rules:

- **All fields must be initialized** — either at the declaration (`x: double = 0.0`) or in the constructor body.
- The **constructor's signature** is what call sites use: `Dog("rex", 3)` in expressions. There is no `new`; the constructor call **is** the value.
- The **destructor takes no arguments** and cannot be called directly. It runs at the end of the value's scope, in reverse declaration order.
- Both are **implicitly `mut`**. Do not write `mut constructor`; the keyword already implies mutation of the object being built/destroyed.
- **If a rune declares no constructor**, an implicit one is generated taking all fields positionally, in declaration order, with defaults where fields declare them. `rune Point` with `x: double = 0.0, y: double = 0.0` gets `Point()` for free.
- **If a rune declares a constructor**, every field must still end up initialized — either in the body or via a field default. Uninitialized fields are a compile error.
- **If a rune declares no destructor**, an implicit one destroys all fields in reverse declaration order. Declaring `destructor` with an empty body is equivalent to omitting it (useful for documentation).
- **No copy or move constructors** in v0.1.0. A rune is copyable iff all its fields are copyable, moveable iff all its fields are moveable. This is the C++ default and needs no syntax.

### Access — `@`

Inside any method (constructor, destructor, or enchanting), fields are accessed with `@`. Bare identifiers resolve to parameters or locals, never to fields.

```coffee
rune Counter
  count: int

  constructor
    @count = 0

enchanting Counter
  mut increment = -> void
    @count += 1

  report = -> void
    io::println(f"count = {@count}")
```

`@` alone (without a field name) is the instance itself, as a value:

```coffee
enchanting Counter
  compare = (other: Counter) -> bool
    @count == other.count

  pass_to = (f: function<(ref<Counter>) -> void>) -> void
    f(@)  -- pass this Counter by reference
```

The operator **`@`** always means "the current instance". The operator **`.`** on a value means "a field or method of that value" (from the outside). They never mix:

- `@count` — the field `count` of the current instance
- `c.count` — the field `count` of `c`
- `@increment()` — call `increment` on the current instance
- `c.increment()` — call `increment` on `c`

Inside a `constructor` or `destructor`, `@` is always available. Inside an `enchanting` block, `@` is available in every method.

### `enchanting` — behavior blocks

Methods that are not the constructor or destructor go in a separate `enchanting` block. This is PenguScript's equivalent of Rust's `impl` — the rune declares data and lifecycle, `enchanting` adds behavior.

```coffee
rune Point
  x: double
  y: double

enchanting Point
  len = -> double
    (@x*@x + @y*@y).sqrt()

  mut translate = (dx: double, dy: double) -> void
    @x += dx
    @y += dy
```

```c++
struct Point {
  double x;
  double y;
  double len() const;
  void translate(double dx, double dy);
};

double Point::len() const {
  return std::sqrt(this->x * this->x + this->y * this->y);
}

void Point::translate(double dx, double dy) {
  this->x += dx;
  this->y += dy;
}
```

Rules:

- **A rune may have multiple `enchanting` blocks.** They merge, in source order.
- **The `enchanting` block goes in the same file as the rune.** It is not a "reopening" — it's a within-file grouping.
- **`enchanting` methods are const by default.** They can read `@field` but not write.
- **`mut` before the method name** makes the method non-const: it can write `@field` and C++ emits a non-`const` method.
- **`mut` on a parameter** is independent: `(mut other: ref<Point>)` means the caller's argument can be mutated.
- Method names must not collide with field names, with `constructor`, or with `destructor`.

### Method calls

Methods are called with `.` on a value, and with `@` on the current instance:

```coffee
p = Point(3.0, 4.0)
d = p.len()              -- call const method
p.translate(1.0, 2.0)    -- call mut method (p must be declared with `mut`)

enchanting Point
  normalize = -> Point
    l = @len()           -- call sibling method
    Point(@x / l, @y / l)
```

A `mut` method can only be called on a value declared `mut`:

```coffee
fixed = Point(1.0, 2.0)
fixed.translate(1.0, 1.0)   -- ✗ compile error: fixed is not mut

mut m = Point(1.0, 2.0)
m.translate(1.0, 1.0)       -- ✓
```

Same rule as `mut` on parameters. Constructors and destructors are the only methods implicitly `mut`; everything else follows the `mut` rules.

### Inheritance — `heir`

A rune may inherit from **one** other rune. This is C-style inheritance: the derived rune has all the parent's fields (and the parent's methods via enchanting), plus its own. It compiles to a C++ `struct Derived : Parent`.

```coffee
realm animals

rune Animal
  name: string
  legs: int

  constructor(name: string, legs: int)
    @name = name
    @legs = legs

enchanting Animal
  describe = -> string
    f"{@name} with {@legs} legs"

rune Dog heir Animal
  breed: string

  constructor(name: string, breed: string, legs: int = 4)
    parent(name, legs)          -- call Animal's constructor
    @breed = breed

enchanting Dog
  bark = -> string
    f"{@name} says woof"
```

```c++
struct Animal {
  std::string name;
  int legs;
  Animal(std::string name, int legs);
  std::string describe() const;
};

struct Dog : public Animal {
  std::string breed;
  Dog(std::string name, std::string breed,
      std::optional<int> legs_opt = std::nullopt);
  std::string bark() const;
};

Dog::Dog(std::string name, std::string breed,
         std::optional<int> legs_opt)
  : Animal(name, legs_opt ? *legs_opt : 4) {
  this->breed = breed;
}
```

Rules:

- **`parent(...)`** calls the parent's constructor. It must appear as the **first statement** of the child's constructor. If the parent has no constructor (all fields defaultable), `parent()` may be omitted — the compiler calls the default constructor.
- **If the child declares no constructor**, an implicit one is generated from the child's fields (positionally), and the parent is default-constructed. This is only valid if the parent is default-constructible; otherwise, the compiler errors and asks for an explicit constructor.
- **Inherited fields are visible with `@`** in the child's methods (`@name` in `Dog` accesses `Animal::name`).
- **Inherited methods are callable with `.`** (`dog.describe()` works).
- **A child's method may shadow a parent's method with the same name.** No `override` keyword; no virtual dispatch; the shadow is resolved statically by the **compile-time type** of the receiver.
- **Multiple `enchanting` blocks on a child may call parent methods** with `.` on `@`: `@describe()`.

### Slicing — explicitly forbidden

Passing a derived rune where a parent is expected is a **compile error** in PenguScript:

```coffee
f = (a: Animal) -> void
  io::println(a.name)

d = Dog("rex", "lab")
f(d)                    -- ✗ compile error: expected Animal, got Dog
```

```c++
void f(Animal a);       // taking Animal by value
f(d);                   // would slice
```

To pass a derived value where a parent is expected, use **`ref<Parent>`** (no copy, no slicing):

```coffee
f = (a: ref<Animal>) -> void
  io::println(a.name)

f(ref(d))               -- ✓ no slicing; d is passed by reference
```

But note: **`ref<Dog>` is not implicitly `ref<Animal>`**. The call `f(ref(d))` type-checks only because `ref(d)` creates a `ref<Animal>` view of the `Animal` subobject of `d`. It works because references are non-owning views and the lifetime of `d` outlives the call. If `f` stored the reference somewhere, the compiler would reject it (references cannot be stored in fields). So `ref<Parent>` is safe by construction.

This is stricter than C++, where slicing is silently allowed. It is the price of "safe as V" — and it eliminates the largest class of inheritance bugs.

### Visibility

There is no `pub` or `private`. All fields and all methods are public, same as C `struct`s. Internal helpers are marked by convention with a leading underscore:

```coffee
rune Stack
  _items: vector<int>

  Stack = -> void
    @_items = []

enchanting Stack
  _ensure_capacity = (n: size_t) -> void
    ...

  push = (v: int) -> void
    @_items.push(v)
```

The `_` prefix is documentation, not enforcement — the compiler does not hide `_ensure_capacity`. This matches the C/Python/Lua convention and lets code be tested and inspected freely.

### Summary

| Feature | PenguScript | C++20 |
|---------|-------------|-------|
| Struct | `rune` | `struct` |
| Behavior block | `enchanting` | method definitions |
| Inheritance | `rune Dog heir Animal` | `struct Dog : Animal` |
| Instance access | `@field`, `@method()`, `@` alone | `this->field`, `this->method()`, `*this` |
| Constructor | `constructor` | `Dog(...)` |
| Destructor | `destructor` | `~Dog()` |
| Parent constructor call | `parent(...)` (first statement) | initializer list |
| Const method | default | `const` |
| Mut method | `mut name = ...` | non-`const` |
| Field visibility | all public (`_` = internal convention) | all public |
| Implicit upcast | **forbidden** | allowed (slicing) |
| Safe upcast | `ref<Parent>(ref(child))` | `static_cast<Parent&>(child)` |

## Omens
---

An **omen** is PenguScript's enumerated type. It declares a fixed, named set of variant values, all sharing the same underlying integer type.

Omens are **scoped**: variants are accessed through the omen name with `::`, and the omen is a distinct type — no implicit conversion to `int`. This is the C++20 `enum class` model, chosen for safety. Unscoped C-style enums are not supported.

### Declaration

```coffee
omen Color
  Red, Green, Blue
```

```c++
enum class Color : int {
  Red, Green, Blue
};
```

Variants may be on one line (comma-separated) or one per line. The two forms are equivalent:

```coffee
omen Color
  Red, Green, Blue

omen Color
  Red
  Green
  Blue
```

The underlying type is `int` by default and can be annotated:

```coffee
omen Color: uint8_t
  Red, Green, Blue
```

```c++
enum class Color : std::uint8_t {
  Red, Green, Blue
};
```

### Values

Variants auto-number from `0`, following C++ rules:

```coffee
omen Color
  Red        -- 0
  Green      -- 1
  Blue       -- 2
```

Explicit values are allowed, and auto-incrementing continues from the last explicit value:

```coffee
omen HttpStatus
  Ok          = 200
  Created                -- 201
  Accepted               -- 202
  NotFound    = 404
  ServerError            -- 405? no: it continues from 404 → 405
```

Actually — careful. In C++, after `NotFound = 404`, the next is `405`. If you want a gap, write it explicitly:

```coffee
omen HttpStatus
  Ok          = 200
  Created     = 201
  Accepted    = 202
  NotFound    = 404
  ServerError = 500
```

Explicit is preferred when values are non-sequential. Auto-increment is fine when values are contiguous. Two variants may share a value (an alias):

```coffee
omen Signal
  Term    = 15
  Sigterm = 15     -- alias, same value
```

### Access

Variants are accessed with `::`. Omens are a **type**, not a value, so `.` is never valid:

```coffee
c = Color::Red
if c == Color::Green
  io::println("green!")
```

The distinction matches realms: `::` is compile-time named access, `.` is runtime value access.

### Casting

An omen value converts to its underlying type with `as`:

```coffee
c = Color::Red
n = c as int              -- 0, safe
u = c as uint8_t          -- safe (uint8_t is the underlying type)
```

```c++
int n = static_cast<int>(c);
std::uint8_t u = static_cast<std::uint8_t>(c);
```

Going **from** an integer to an omen is where the danger lives: an arbitrary integer may not correspond to any variant. PenguScript provides two paths:

**Safe conversion** via `Omen::try_from`, which checks against the known variants and returns `Omen?`:

```coffee
c = Color::try_from(1)          -- Some(Color::Green)
bad = Color::try_from(99)       -- None
```

```c++
std::optional<Color> Color_try_from(int n) {
  switch (n) {
    case 0: return Color::Red;
    case 1: return Color::Green;
    case 2: return Color::Blue;
    default: return std::nullopt;
  }
}
```

The compiler generates this switch from the variant list — it knows every valid value, including aliases (aliases resolve to the first variant with that value). Use `try_from` whenever the integer comes from outside the program (file, network, user input).

**Unsafe conversion** via `as` inside `unsafe`, which does an unchecked `static_cast`:

```coffee
unsafe
  c = 1 as Color         -- unchecked; 99 as Color would be UB-ish (technically defined, but no variant matches)
```

```c++
Color c = static_cast<Color>(1);
```

Use `as` only when you've already validated the value elsewhere. In safe code, `as Color` is a compile error.

### Flags

A **flags omen** is an omen whose variants are bit positions, intended to be combined with `|`. The `flags` modifier auto-numbers variants as `1 << 0`, `1 << 1`, `1 << 2`, … and generates the bitwise operators.

```coffee
flags omen Permission
  Read, Write, Execute
```

```c++
enum class Permission : int {
  Read    = 1 << 0,
  Write   = 1 << 1,
  Execute = 1 << 2
};

constexpr Permission operator|(Permission a, Permission b) {
  return static_cast<Permission>(std::to_underlying(a) | std::to_underlying(b));
}
constexpr Permission operator&(Permission a, Permission b) {
  return static_cast<Permission>(std::to_underlying(a) & std::to_underlying(b));
}
constexpr Permission operator^(Permission a, Permission b) {
  return static_cast<Permission>(std::to_underlying(a) ^ std::to_underlying(b));
}
constexpr Permission operator~(Permission a) {
  constexpr int all = std::to_underlying(Permission::Read)
                    | std::to_underlying(Permission::Write)
                    | std::to_underlying(Permission::Execute);
  return static_cast<Permission>(all & ~std::to_underlying(a));
}
constexpr Permission& operator|=(Permission& a, Permission b) { return a = a | b; }
constexpr Permission& operator&=(Permission& a, Permission b) { return a = a & b; }

constexpr bool has(Permission self, Permission mask) {
  return (self & mask) == mask;
}
```

Usage:

```coffee
mut perms = Permission::Read | Permission::Write
perms |= Permission::Execute
perms &= ~Permission::Write

if perms.has(Permission::Read)
  io::println("can read")

if perms.has(Permission::Read | Permission::Write)
  io::println("can read and write")
```

Explicit values are allowed in flags too, and follow the same rules as a regular omen:

```coffee
flags omen Permission
  None    = 0
  Read    = 1 << 0
  Write   = 1 << 1
  Execute = 1 << 2
```

The `None = 0` convention is common; it gives you a zero value and lets `~` produce a meaningful complement within the known universe. It is not auto-generated — declare it if you want it.

`flags` combines with the underlying-type annotation:

```coffee
flags omen Permission: uint8_t
  Read, Write, Execute
```

```c++
enum class Permission : std::uint8_t {
  Read    = 1 << 0,
  Write   = 1 << 1,
  Execute = 1 << 2
};
```

The `~` operator's "universe" is computed from the declared variants — bits not declared are never set. This means `~Read` on `Permission` yields `Write | Execute`, not `0xFF..F ~ Read`. That's the safe behavior for flags.

### Enchanting

Omens share the `enchanting` mechanism with runes. Methods inside `enchanting OmenName` receive `@` as the current variant value:

```coffee
omen Color
  Red, Green, Blue

enchanting Color
  is_warm = -> bool
    @ == Color::Red

  name = -> string
    if @ == Color::Red then "red"
    else if @ == Color::Green then "green"
    else "blue"
```

```c++
enum class Color : int { Red, Green, Blue };

bool Color::is_warm() const {
  return *this == Color::Red;
}

std::string Color::name() const {
  if (*this == Color::Red) return "red";
  if (*this == Color::Green) return "green";
  return "blue";
}
```

Rules:

- **Methods are `const` by default.** Omens are value types; a "mut method" makes no sense (there's nothing to mutate). `mut` before a method name is a compile error inside an omen's `enchanting` block.
- **`@` alone** is the current value. `@ == Color::Red` is idiomatic.
- **No fields.** An omen has no instance state beyond its variant.
- **Associated functions** (callable on the type, not a value) take no `@` and are declared with `const` or `Omen::method()` at the call site — same mechanism, just no `@` usage inside.

### Summary

| Feature | PenguScript | C++20 |
|---------|-------------|-------|
| Declaration | `omen Color` | `enum class Color : int` |
| Underlying type | `omen Color: uint8_t` | `enum class Color : std::uint8_t` |
| Variants | `Red, Green, Blue` | `Red, Green, Blue` |
| Access | `Color::Red` | `Color::Red` |
| Cast to int | `c as int` | `static_cast<int>(c)` |
| Safe cast from int | `Color::try_from(n) -> Color?` | generated `switch` helper |
| Unsafe cast from int | `n as Color` in `unsafe` | `static_cast<Color>(n)` |
| Flags declaration | `flags omen Permission` | `enum class` + operators |
| Bitwise ops | `\|`, `&`, `^`, `~`, `\|=`, `&=` | generated free functions |
| Membership test | `perms.has(Permission::Read)` | generated `has()` |
| Methods | `enchanting Color` | free functions / member definitions |

## Echoes and Seals
---

Two mechanisms define custom types without adding behavior or runtime cost. Together with `rune` and `omen`, they cover every "type definition" the language allows:

| Keyword | What it defines | Runtime cost | Underlying C++ |
|---------|-----------------|--------------|----------------|
| `rune` | struct with fields | layout | `struct` |
| `omen` | enum with named variants | `int` | `enum class` |
| `echo` | **transparent alias** | **zero** | `using` |
| `seal` | **opaque newtype** | **zero** (wraps a single value) | `struct { T value; }` |

Use `echo` when you want a shorter name for a long type. Use `seal` when you want the compiler to stop you from mixing values that happen to share a representation (meters vs. Celsius, user IDs vs. session tokens, raw strings vs. validated emails).

### Echo — transparent aliases

An echo declares an **alternative name** for an existing type:

```coffee
echo Entity = int
echo Callback = function<(int) -> void>
echo Matrix = vector<vector<double>>

f = (e: Entity) -> Entity
  e * 2

n: int = f(10)      -- OK: Entity and int are the same type
```

```c++
using Entity = int;
using Callback = std::function<void(int)>;
using Matrix = std::vector<std::vector<double>>;
```

Aliases are **fully transparent**. They introduce no new type, no conversion, no safety. They exist only to shorten names and document intent. Two aliases of the same underlying type are interchangeable, and an alias is interchangeable with its target:

```coffee
echo Meters = double
echo Seconds = double

m: Meters = 5.0
s: Seconds = m          -- ✓ compiles: both are double
```

```c++
using Meters = double;
using Seconds = double;

Meters m = 5.0;
Seconds s = m;         // fine, both are double
```

If you want the compiler to prevent `Meters` and `Seconds` from mixing, use `seal`, not `echo`.

Aliases may reference other aliases, runes, omens, or any type expression:

```coffee
echo Handler = function<(ref<string>) -> void>
echo ColorMap = map<string, Color>
echo Points = vector<Point>
```

Recursive or cyclic aliases (`echo A = A`, `echo A = B` with `echo B = A`) are compile errors.

Echoes may be declared inside a realm and imported like any other symbol:

```coffee
realm identifiers
echo Entity = int
echo EntityList = vector<Entity>

-- elsewhere
invoke {Entity, EntityList} from "identifiers"
e: Entity = 42
```

`echo` works inside any file, including the implicit realm of a module. It has no `enchanting` block — an alias has no separate identity to enchant, and adding methods to the underlying type would defeat the point.

### Seal — newtypes

A seal declares a **new type** with a fixed underlying representation:

```coffee
seal UserId = int
seal SessionToken = string
seal Meters = double
seal Celsius = double
```

```c++
struct UserId       { int          value; };
struct SessionToken { std::string  value; };
struct Meters       { double       value; };
struct Celsius      { double       value; };
```

Sealed types are **opaque**: `UserId` and `int` are not interchangeable, and `Meters` and `Celsius` are not interchangeable — even though both wrap a `double`. This is the safety win that `echo` cannot provide:

```coffee
seal Meters = double
seal Celsius = double

m = Meters(100.0)
c: Celsius = m            -- ✗ compile error
c2 = Celsius(m as double) -- ✓ explicit: unwrap then wrap
```

**Construction** wraps the underlying value. The constructor is generated automatically from the seal declaration — no need to write it:

```coffee
id    = UserId(42)
token = SessionToken("abc123")
d     = Meters(100.0)
```

```c++
UserId       id    = UserId{42};
SessionToken token = SessionToken{"abc123"};
Meters       d     = Meters{100.0};
```

There is no `try_from` for construction. A seal wraps *any* value of its underlying type with no check — there is nothing that could fail.

**Unwrapping** uses `as`, and is always safe (no `unsafe` needed):

```coffee
n: int    = id as int
s: string = token as string
x: double = d as double
```

```c++
int         n = id.value;
std::string s = token.value;
double      x = d.value;
```

Unwrapping always succeeds because seals have no invariants — they wrap exactly one value, and the underlying type holds every possible value the seal could hold.

**Default operators are not inherited.** `Meters + Meters` is a compile error; you have to unwrap and rewrap explicitly, or add methods via `enchanting`:

```coffee
a = Meters(100.0)
b = Meters(50.0)
c = a + b                   -- ✗ compile error
c = Meters((a as double) + (b as double))   -- ✓
```

This is deliberate: meters and Celsius both wrap `double`, but `Meters(30.0) + Meters(50.0)` should produce `Meters(80.0)`, not `80.0`. Operators are opt-in through `enchanting`.

Seals may be declared inside a realm and imported like any other symbol.

### Enchanting seals

A seal may have one or more `enchanting` blocks that add methods. Inside any method, `@` is the **underlying value**, not "the wrapper":

```coffee
seal Meters = double

enchanting Meters
  add = (other: Meters) -> Meters
    Meters(@ + (other as double))

  to_feet = -> double
    @ * 3.28084

  describe = -> string
    f"{@} m"
```

```c++
struct Meters { double value; };

Meters Meters::add(Meters other) const {
  return Meters{this->value + other.value};
}

double Meters::to_feet() const {
  return this->value * 3.28084;
}

std::string Meters::describe() const {
  return std::format("{} m", this->value);
}
```

Rules:

- **`@` is the underlying value.** `@ * 3.28084` is `double * double`. `Meters(@ + ...)` wraps the result back.
- **Methods are `const` by default.** `mut` before a method name makes it non-`const` (rare for seals, but possible if the underlying type is a mutable container).
- **No fields.** Seals wrap exactly one value.
- **No inheritance.** `rune X heir Y` cannot target a seal, and a seal cannot inherit from anything.
- **No `try_from` is generated.** Seals never fail to construct. If you need invariants (a "positive int", a "validated email"), use a `rune` with a constructor that panics on invalid input.

### Limitations (v0.1.0)

- **No generic echoes or seals.** `echo Stack<T> = vector<T>` and `seal Wrapper<T> = T` are future features.
- **No transitive seal unwrapping.** `A as C` where `A` wraps `B` and `B` wraps `C` requires `A as B as C` (or, more likely, is a design smell).
- **No seal-to-seal casting with `as`.** `m as Celsius` is a compile error; you must go through the underlying type (`Celsius(m as double)`). This is intentional: it forces the conversion to be visible.

## Type Conversions
---

PenguScript has two cast operators and two checked conversion helpers:

| Form | Verification | Requires `unsafe` | Returns |
|------|--------------|:-----------------:|---------|
| `x as T` | **compile-time** (lossless only) | no | `T` |
| `x as T` inside `unsafe` | none (C-style) | **yes** | `T` |
| `T::try_from(x)` | runtime | no | `T?` |
| `T::from(x)` | runtime (panics on failure) | no | `T` |

The rule is simple: **safe casts are `as`; dangerous casts need `unsafe as`; anything that may fail at runtime uses `try_from` or `from`.**

### Safe casts — `as`

`as` is accepted by the compiler only when the conversion is **guaranteed lossless and defined** — no data loss, no UB. Anything else requires `unsafe as` (or a checked helper).

```coffee
i8:  int8_t  = 42
i16: int16_t = i8 as int16_t          -- ✓ widening signed
u8:  uint8_t = 200
u16: uint16_t = u8 as uint16_t        -- ✓ widening unsigned
s16: int16_t = u8 as int16_t          -- ✓ uint8_t fits in int16_t

f:   float   = i16 as float           -- ✓ int -> float (may lose precision)
d:   double  = f as double            -- ✓ float -> double (lossless)
```

```c++
std::int8_t  i8  = 42;
std::int16_t i16 = static_cast<std::int16_t>(i8);
std::uint8_t u8  = 200;
std::uint16_t u16 = static_cast<std::uint16_t>(u8);
std::int16_t s16 = static_cast<std::int16_t>(u8);
float  f = static_cast<float>(i16);
double d = static_cast<double>(f);
```

The safe `as` accepts:

- **Same type** → trivial.
- **Widening integers**: `int8_t → int16_t → int32_t → int64_t`, and similarly for unsigned.
- **Unsigned to wider signed**: `uint8_t → int16_t`, `uint16_t → int32_t`, `uint32_t → int64_t`.
- **`float` to `double`**.
- **Any integer to `float` or `double`**. This is the one lossy-but-safe direction: no UB, no out-of-range wrap, but precision may be lost for large values (above 2²⁴ for `float`, above 2⁵³ for `double`). Documented, not prevented — the same policy Rust uses.
- **Seal unwrap**: `UserId → int`, `Meters → double`.
- **Omen to underlying**: `Color → int`, `Color → uint8_t`.

That's the full whitelist. Narrowing, sign changes, and float-to-int are **not** safe `as`.

### Unsafe casts — `unsafe as`

The dangerous conversions require an `unsafe` block or function. The compiler performs no check; the programmer asserts the value is representable:

```coffee
unsafe
  n:  int32_t  = big_int64 as int32_t          -- truncates; wrap-around if out of range
  f:  float    = d as float                    -- loses precision
  i:  int      = d as int                      -- truncates toward zero; UB if out of range
  u:  uint32_t = neg as uint32_t               -- negative wraps to a huge positive
  c:  Color    = 1 as Color                    -- UB if 1 isn't a declared variant
```

```c++
std::int32_t  n = static_cast<std::int32_t>(big_int64);
float         f = static_cast<float>(d);
int           i = static_cast<int>(d);
std::uint32_t u = static_cast<std::uint32_t>(neg);
Color         c = static_cast<Color>(1);
```

Always comment why the cast is safe:

```coffee
unsafe
  -- safe: idx is bounds-checked above; #arr < 2^31
  i: int32_t = idx as int32_t
```

### Checked casts — `T::try_from(x)` and `T::from(x)`

When the conversion may fail at runtime, use the checked helpers. `try_from` returns `T?`; `from` panics on failure.

**Numeric narrowing** — the canonical case:

```coffee
big: int64_t = 5_000_000_000

maybe = int32_t::try_from(big)     -- None (too big)
small: int32_t = 42
ok    = int32_t::try_from(small)   -- Some(42)
```

```c++
std::optional<std::int32_t> maybe = int32_t_try_from(big);
std::optional<std::int32_t> ok    = int32_t_try_from(small);
```

**Float to int** — checked for range, truncates toward zero:

```coffee
d = 3.7
n = int::try_from(d)               -- Some(3): truncated, in range
bad = int::try_from(1e20)          -- None (out of range for int)
```

**String parsing** — the other checked direction:

```coffee
maybe = int::try_from("42")        -- Some(42)
bad   = int::try_from("hello")     -- None

n = int::from("42")                -- 42
bad = int::from("hello")           -- panics
```

**Enum from int** — checked against the declared variant list:

```coffee
c = Color::try_from(1)             -- Some(Color::Green)
bad = Color::try_from(99)          -- None
```

`T::try_from` and `T::from` work for **any numeric source and destination**, string→number, and int→enum. They never require `unsafe` — that's their purpose.

`T::from(x)` panics on failure. The panic is not a C++ exception; the runtime terminates the process with a message. Same behavior as `arr[i]` on out-of-bounds.

### Conversion matrix — what to use when

| From → To | `as` | `unsafe as` | `try_from` / `from` |
|-----------|:----:|:-----------:|:-------------------:|
| Widening int | ✅ | — | ✅ (redundant) |
| Narrowing int | ✗ | ✅ | ✅ |
| Signed ↔ unsigned (same width) | ✗ | ✅ | ✅ |
| Unsigned → wider signed | ✅ | — | ✅ |
| Int → float / double | ✅ | — | ✗ (never fails) |
| float → double | ✅ | — | ✗ (never fails) |
| double → float | ✗ | ✅ | ✅ |
| Float / double → int | ✗ | ✅ | ✅ |
| Seal construct | — | — | `SealName(x)` |
| Seal unwrap | ✅ | — | ✗ (never fails) |
| Seal → seal | ✗ | ✗ | ✗ (go through underlying) |
| Omen → int | ✅ | — | ✗ (never fails) |
| Int → omen | ✗ | ✅ | ✅ |
| String → number | ✗ | ✗ | ✅ |
| Number → string | ✗ | ✗ | via `f"{}"` |

### Summary

| Operation | Syntax | Requires `unsafe` | Returns |
|-----------|--------|:-----------------:|---------|
| Safe cast | `x as T` | no | `T` |
| Dangerous cast | `x as T` inside `unsafe` | **yes** | `T` |
| Checked cast | `T::try_from(x)` | no | `T?` |
| Checked cast (panics) | `T::from(x)` | no | `T` |
| Seal construct | `SealName(x)` | no | `SealName` |
| Seal unwrap | `s as T` | no | `T` |
| Enum → int | `e as int` | no | `int` |
| Int → enum (checked) | `Omen::try_from(n)` | no | `Omen?` |

## Sigils
---

A **sigil** is a generic type parameter. Sigils are **static**: they monomorphize at compile time, exactly like C++ templates. There is no runtime dispatch, no boxing, and no type erasure — each instantiation produces a distinct C++ type.

Sigils may appear on functions, runes, echoes, and seals. They are declared between `<` and `>` directly after the name:

```coffee
identity = <T>(x: T) -> T
  x
```

### Generic functions

```coffee
identity = <T>(x: T) -> T
  x

pair = <A, B>(a: A, b: B) -> tuple<A, B>
  (a, b)

swap = <T>(mut a: T, mut b: T) -> void
  temp = a
  a = b
  b = temp
```

```c++
template<typename T>
T identity(T x) {
  return x;
}

template<typename A, typename B>
std::tuple<A, B> pair(A a, B b) {
  return {a, b};
}

template<typename T>
void swap(T& a, T& b) {
  T temp = a;
  a = b;
  b = temp;
}
```

### Generic runes

A generic rune declares its sigils on the same line as the rune name. Every `enchanting` block targeting a generic rune must **repeat the sigil list**:

```coffee
rune Box<T>
  value: T

  constructor(v: T)
    @value = v

enchanting Box<T>
  get = -> ref<T>
    ref(@value)

  mut set = (v: T) -> void
    @value = v
```

```c++
template<typename T>
struct Box {
  T value;
  Box(T v) : value(v) {}
  const T& get() const;
  void set(T v);
};

template<typename T>
const T& Box<T>::get() const {
  return value;
}

template<typename T>
void Box<T>::set(T v) {
  value = v;
}
```

Construction infers the sigil from the argument, or accepts an explicit one:

```coffee
b = Box(42)           -- infers Box<int>
c = Box("hello")      -- infers Box<string>
d = Box<int>(42)      -- explicit
```

```c++
auto b = Box{42};
auto c = Box{std::string{"hello"}};
auto d = Box<int>{42};
```

### Generic echoes and seals

Sigils may also appear on `echo` and `seal`. They are transparent in use — inference works exactly like runes:

```coffee
echo Pair<T> = tuple<T, T>
echo Map<T> = map<string, T>

seal Wrapper<T> = T

w = Wrapper(42)       -- Wrapper<int>
n: int = w as int
```

```c++
template<typename T>
using Pair = std::tuple<T, T>;

template<typename T>
using Map = std::map<std::string, T>;

template<typename T>
struct Wrapper { T value; };

auto w = Wrapper{42};
int n = w.value;
```

### Sigil inference

Sigils are inferred from argument types using C++20 template argument deduction rules:

```coffee
x = identity(42)          -- T = int
y = pair(1, "hi")         -- A = int, B = string
b = Box(3.14)             -- T = double
```

When a sigil appears **only in the return type**, inference fails and the caller must pass it explicitly:

```coffee
make_vector = <T>() -> vector<T>
  []

nums = make_vector<int>()     -- ✓ explicit
bad  = make_vector()          -- ✗ cannot infer T
```

Explicit instantiation is always allowed, even when inference would succeed:

```coffee
nums = make_vector<int>()
s    = identity<string>("hi")
```

### Constraints — `needs`

Without a constraint, the compiler only reports an error if an operation used in the body is unavailable **in some instantiation**. That's duck typing — flexible, but errors point at the operator, not at the sigil.

A `needs` clause makes the requirement explicit. It does **not** add dispatch or vtables — it only documents what the body already assumes, and produces a targeted error when an instantiation doesn't satisfy it:

```coffee
find_min = <T needs Ord>(items: ref<vector<T>>) -> T?
  if #items == 0
    none
  else
    mut min = items[0]
    for x in items
      if x < min
        min = x
    min
```

Built-in constraints (structural, not nominal):

| Constraint | What `T` must support |
|------------|-----------------------|
| `Eq` | `==`, `!=` |
| `Ord` | `<`, `<=`, `>`, `>=` (implies `Eq`) |
| `Hash` | hashing via the compiler's hash generator |
| `Copy` | copy construction and assignment |
| `Move` | move construction and assignment |
| `Default` | zero-argument construction |
| `Numeric` | `+`, `-`, `*`, `/`, `%`, unary `-` |
| `Floating` | `Numeric` plus `sqrt()`, `abs()`, `is_nan()`, … |
| `Display` | string formatting via `f"{}"` |
| `Into<U>` | convertible to `U` via `as` |
| `From<U>` | constructible from `U` via `T::from` |

Multiple constraints are comma-separated:

```coffee
describe = <T needs Ord, Display>(x: T) -> string
  f"{x} is comparable and printable"
```

Constraints are checked **at instantiation**, not at declaration. A rune satisfies a constraint structurally — if it has the required operations via `enchanting`, it satisfies the constraint. There is no `impl Copy for Foo` declaration, no `impl Ord for Foo`. If the operations exist, the constraint is satisfied; if not, the compiler reports which operation is missing:

```
error: `Point` does not satisfy `Ord` required by `find_min`
  → `Point` has no `<` operator
  → add `<` via `enchanting Point` or use a different type
```

### Generic inheritance

A rune may inherit from a generic rune, passing its own sigils along or instantiating with concrete types:

```coffee
rune Animal<T>
  name: T

rune Dog heir Animal<string>
  breed: string

rune Container<T> heir Animal<T>
  payload: T
```

```c++
template<typename T>
struct Animal { T name; };

struct Dog : Animal<std::string> { std::string breed; };

template<typename T>
struct Container : Animal<T> { T payload; };
```

A child may **not** inherit from an uninstantiated generic: `rune Dog heir Animal` is a compile error. The parent must be fully instantiated, same rule as C++.

### Limitations (v0.1.0)

- **No user-defined constraints.** `needs` accepts only the built-in constraints listed above. Custom concepts would require a `concept` keyword and a mechanism to bind operations to concepts — deferred to a future version.
- **No default sigils.** `<T = int>` is not supported.
- **No variadic sigils.** `<...Ts>` is not supported.
- **No generic omens.** An omen has no per-instance data, so a sigil on an omen adds nothing. Generic omens become meaningful only once omens can carry associated data — a future feature.
- **No higher-kinded sigils.** `<F<T>>` is not supported.
- **No specialization.** Every instantiation uses the same template body.

### Summary

| Feature | PenguScript | C++20 |
|---------|-------------|-------|
| Function sigil | `f = <T>(x: T) -> T` | `template<typename T> T f(T x)` |
| Rune sigil | `rune Box<T>` | `template<typename T> struct Box` |
| Enchanting sigil | `enchanting Box<T>` | `template<typename T>` on each member |
| Echo sigil | `echo Pair<T> = tuple<T, T>` | `template<typename T> using Pair = …` |
| Seal sigil | `seal Wrapper<T> = T` | `template<typename T> struct Wrapper` |
| Explicit instantiation | `make_vector<int>()` | `make_vector<int>()` |
| Inference | `identity(42)` | `identity(42)` |
| Constraint | `<T needs Ord>` | `template<std::totally_ordered T>` |
| Multiple constraints | `<T needs Ord, Display>` | `template<...> requires ...` |

## Operators
---

Operators are declared inside `enchanting` blocks with the `operator` keyword. They are **methods** — same `@` access, same `mut`/`const` rules — but bound to a symbol instead of a name. Every operator has a well-known arity and return type; the compiler checks both.

Operator overloading exists so that user-defined types can behave like the built-in ones. `Meters + Meters` should produce `Meters`, not `double`. `Point == Point` should compare coordinates, not addresses.

### Declaration

An operator is declared with `operator` and the symbol, followed by `= (params) -> ret`. The arity determines whether it is unary or binary.

```coffee
rune Point
  x: double
  y: double

enchanting Point
  operator + = (other: Point) -> Point
    Point(@x + other.x, @y + other.y)

  operator - = (other: Point) -> Point
    Point(@x - other.x, @y - other.y)

  operator - = -> Point                    -- unary minus (0 args)
    Point(-@x, -@y)

  mut operator += = (other: Point) -> void
    @x += other.x
    @y += other.y
```

```c++
struct Point {
  double x;
  double y;
  Point operator+(Point other) const;
  Point operator-(Point other) const;
  Point operator-() const;
  void operator+=(Point other);
};

Point Point::operator+(Point other) const {
  return Point{this->x + other.x, this->y + other.y};
}

Point Point::operator-(Point other) const {
  return Point{this->x - other.x, this->y - other.y};
}

Point Point::operator-() const {
  return Point{-this->x, -this->y};
}

void Point::operator+=(Point other) {
  this->x += other.x;
  this->y += other.y;
}
```

Rules:

- **Binary operators take exactly one parameter.** `enchanting T { operator OP = (other: U) }` defines `T OP U`.
- **Unary operators take no parameters.** `operator - = -> T` defines `-t`.
- **Operators are `const` by default.** They cannot write `@field`.
- **`mut operator` makes the method non-`const`.** Required for `+=`, `-=`, `[] =`, etc.
- **Return types are fixed by the operator**, not inferred (see the table below). The compiler rejects mismatched returns.
- **No `@` in free operators.** Free operators (below) use their parameter names explicitly.

### Supported operators

| Category | Operator | Arity | Return type | Codegen |
|----------|----------|:-----:|-------------|---------|
| Arithmetic | `+` `-` `*` `/` `%` | binary | `T` (same as receiver) | `operator+` etc. |
| Arithmetic | `-` `+` | unary | `T` | `operator-`, `operator+` |
| Bitwise | `&` `\|` `^` `<<` `>>` | binary | `T` | `operator&` etc. |
| Bitwise | `~` | unary | `T` | `operator~` |
| Comparison | `==` `!=` | binary | `bool` | `operator==`, `operator!=` |
| Comparison | `<` `<=` `>` `>=` | binary | `bool` | `operator<` etc. |
| Spaceship | `<=>` | binary | `Ordering` | `operator<=>` |
| Compound | `+=` `-=` `*=` `/=` `%=` | binary | `void` | `operator+=` etc. |
| Compound | `&=` `\|=` `^=` `<<=` `>>=` | binary | `void` | `operator&=` etc. |
| Index | `[]` | 1+ args | `V` (the element type) | `operator[]` |
| Call | `()` | 0+ args | user-defined | `operator()` |

The return type is **not inferred**. `operator + = (other: Point) -> int` is a compile error; the compiler requires the return type to be the receiver type. Same for comparison (`bool`), compound (`void`), and spaceship (`Ordering`).

**Not overloadable** (deliberately):

- `=` — copy assignment is C++ default; overloading it silently breaks move semantics. Use `constructor(mut other: ref<T>)` for explicit copy if needed (future feature).
- `&&`, `||`, `!` — reserved for `bool`. The keywords `and`, `or`, `not` are not user-extensible.
- `++`, `--` — no such operators in PenguScript.
- `as` — conversion is handled by `## Type Conversions`; user-defined casts go through `T::from` / `try_from`.
- `&` (address-of), `*` (deref) — reserved for `raw<T>` / pointers.
- `->` — no arrow operator.
- `new`, `delete` — no such operators.

### Symmetric operators — free form

The `enchanting` form defines `T OP U` where `T` is the receiver. For the reverse (`U OP T`), declare a **free operator** at file scope:

```coffee
-- in the same file as Point

operator + = (a: int, b: Point) -> Point
  Point(a + b.x, a + b.y)

operator * = (a: double, b: Point) -> Point
  Point(a * b.x, a * b.y)
```

```c++
Point operator+(int a, Point b) {
  return Point{a + b.x, a + b.y};
}

Point operator*(double a, Point b) {
  return Point{a * b.x, a * b.y};
}
```

Free operators follow the same rules as `enchanting` operators (return types fixed, no `@`), but they are **not methods** — they are top-level functions and can have any parameter types, as long as one is a user-defined rune or seal.

If both `enchanting T { operator OP }` and a free `operator OP` with the same first parameter `T` exist, that's a **redefinition error**.

### Comparison operators and `<=>`

Comparison needs special care. In C++20, `operator==` auto-generates `operator!=`, and `operator<=>` auto-generates all four of `<`, `<=`, `>`, `>=`. PenguScript exposes both shortcuts.

**Define `==` only** — the compiler generates `!=` for free:

```coffee
enchanting Point
  operator == = (other: Point) -> bool
    @x == other.x and @y == other.y
```

```c++
struct Point {
  double x;
  double y;
  bool operator==(Point other) const;
  // operator!= auto-generated by C++20
};
```

**Define `<=>`** — the compiler generates all six comparisons:

```coffee
enchanting Point
  operator <=> = (other: Point) -> Ordering
    if @x != other.x
      @x <=> other.x
    else
      @y <=> other.y
```

```c++
struct Point {
  double x;
  double y;
  std::partial_ordering operator<=>(Point other) const;
  // ==, !=, <, <=, >, >= auto-generated
};
```

`Ordering` is PenguScript's name for `std::strong_ordering` / `std::weak_ordering` / `std::partial_ordering` (the compiler picks the strictest one that matches the fields). See *Ordering* below.

**Define all four explicitly** — allowed but discouraged. If you define `==`, `!=`, `<`, `<=`, `>`, `>=` manually, `<=>` is not required. This is for cases where the comparison order differs from the equality order.

If both `==` and `<=>` are declared, both are used — `<=>` generates the ordered comparisons, `==` generates equality. This is the C++20 default and needs no special syntax.

If only `==` is declared and `<=>` is missing, `<` and friends are unavailable on the type. Comparison with `<` is then a compile error.

### Compound operators

A compound operator (`+=`, `-=`, etc.) must be declared explicitly. The compiler does **not** auto-derive `+=` from `+`:

```coffee
enchanting Point
  mut operator += = (other: Point) -> void
    @x += other.x
    @y += other.y
```

If `+=` is missing, `p += q` is a compile error. This is deliberate: `@ = @ + other` requires `T` to be copyable or moveable, and the compiler should not silently pay for a copy that the user did not ask for.

The common pattern is to define both — `+` (returning a new value) and `+=` (mutating in place). Types that are expensive to copy (large vectors, buffers) should prefer the `+=` form and skip `+`.

### Index — `[]`

The index operator takes any number of parameters and returns the element type. It may be `const` (read-only) or `mut` (writable):

```coffee
rune Matrix
  _data: vector<double>
  _rows: size_t
  _cols: size_t

enchanting Matrix
  constructor(rows: size_t, cols: size_t)
    @_rows = rows
    @_cols = cols
    @_data = vector<double>(rows * cols, 0.0)

  operator [] = (r: size_t, c: size_t) -> ref<double>
    ref(@_data[r * @_cols + c])

  mut operator [] = (r: size_t, c: size_t) -> mut ref<double>
    ref(@_data[r * @_cols + c])
```

```c++
struct Matrix {
  std::vector<double> _data;
  std::size_t _rows;
  std::size_t _cols;

  const double& operator[](std::size_t r, std::size_t c) const;
  double& operator[](std::size_t r, std::size_t c);
};
```

Usage:

```coffee
mut m = Matrix(3, 3)
m[0, 0] = 1.0
v = m[1, 1]
```

The const version returns `ref<double>`; the mut version returns `mut ref<double>`. The compiler picks based on whether the receiver is `mut`.

For a single-index container, declare `operator [] = (i: size_t) -> ref<V>` (or `mut ref<V>`). Multi-index is a PenguScript extension over C++ — the compiler lowers `m[i, j]` to `m.operator[](i, j)`.

### Call — `()`

The call operator makes a rune callable like a function:

```coffee
rune Adder
  base: int

  constructor(b: int)
    @base = b

enchanting Adder
  operator () = (x: int) -> int
    @base + x

add_five = Adder(5)
result = add_five(10)        -- 15
```

```c++
struct Adder {
  int base;
  Adder(int b);
  int operator()(int x) const;
};

Adder add_five = Adder(5);
int result = add_five(10);
```

The return type is user-defined. `()` is the only operator whose return type is not fixed by the compiler.

### `Ordering`

`<=>` returns `Ordering`, which maps to one of the three C++20 ordering types:

| PenguScript | C++20 | When chosen |
|-------------|-------|-------------|
| `Ordering.Strong` | `std::strong_ordering` | All fields are totally ordered (`int`, `string`, etc.) |
| `Ordering.Weak` | `std::weak_ordering` | Fields are weakly ordered (some values are equivalent) |
| `Ordering.Partial` | `std::partial_ordering` | Fields include `double` / `float` (NaN is unordered) |

The compiler picks the strictest that matches the field types. If a rune has any `double` field, `<=>` returns `Ordering.Partial`, because `NaN` makes the comparison incomplete.

The `<=>` body uses the `<=>` operator on the fields:

```coffee
enchanting Point
  operator <=> = (other: Point) -> Ordering
    if @x != other.x
      @x <=> other.x
    else
      @y <=> other.y
```

If the user's `<=>` body only uses `if/else` and returns `Ordering.Strong` values, the compiler accepts it as `Ordering.Weak` or `Ordering.Partial` — the return type is widened, not narrowed.

### Seals

Seals support operator overloading with the same syntax. `@` is the underlying value:

```coffee
seal Meters = double

enchanting Meters
  operator + = (other: Meters) -> Meters
    Meters(@ + (other as double))

  operator == = (other: Meters) -> bool
    @ == (other as double)

  operator < = (other: Meters) -> bool
    @ < (other as double)

  operator <=> = (other: Meters) -> Ordering
    @ <=> (other as double)
```

```c++
struct Meters { double value; };

Meters Meters::operator+(Meters other) const {
  return Meters{value + other.value};
}

bool Meters::operator==(Meters other) const {
  return value == other.value;
}

bool Meters::operator<(Meters other) const {
  return value < other.value;
}

std::partial_ordering Meters::operator<=>(Meters other) const {
  return value <=> other.value;
}
```

Free operators on seals work the same way:

```coffee
operator * = (a: double, b: Meters) -> Meters
  Meters(a * (b as double))
```

```c++
Meters operator*(double a, Meters b) {
  return Meters{a * b.value};
}
```

### Omens and echoes

**Echoes do not need operator overloading.** An `echo X = Y` is transparent — `X` has exactly the operators of `Y`, no more and no less. Declaring `enchanting X { operator + }` where `X` is an alias is a compile error.

**Omens do not support operator overloading** in v0.1.0. An omen is an `enum class` and already has `==` and `!=` for free. Adding `+` to an enum is almost always a sign that the type should be a rune or a seal.

### Interaction with sigils and `needs`

Operator definitions are what makes a type satisfy a constraint. If `T needs Ord`, then `T` must have `operator <` (and the friends) — usually via `<=>` or via explicit `<`, `<=`, `>`, `>=`. The compiler checks this at instantiation:

```coffee
find_min = <T needs Ord>(items: ref<vector<T>>) -> T?
  ...

-- Point has operator <=>, so it satisfies Ord
p = find_min(ref(points))     -- ✓

-- Meters has operator <=>, so it satisfies Ord
m = find_min(ref(distances))  -- ✓
```

If a type is used where a constraint is required and lacks the corresponding operator, the compiler reports which operator is missing:

```
error: `Point` does not satisfy `Ord` required by `find_min`
  → `Point` has no `<`, `<=`, `>`, `>=` or `<=>`
  → add `operator <=>` via `enchanting Point`
```

The constraints (`Ord`, `Numeric`, etc.) are **structural**: any type that has the right operators satisfies them. There is no `impl Ord for Point` declaration. This is the "no OOP" guarantee extended to type classes.

### Limitations (v0.1.0)

- **No assignment operator overloading.** `=` is C++ default copy/move.
- **No `&&`, `||`, `!`.** Reserved for `bool`.
- **No `++`, `--`.** No such operators.
- **No custom `as`.** Conversion is `T::from` / `try_from`, not operator overloading.
- **No `&` (address-of) or `*` (deref).** Reserved for raw pointers.
- **No symmetric `<=>`.** Both sides must be the same type, or one side must be a free operator.
- **No default implementations.** Every operator must be declared explicitly; no `#[derive(Ord)]` in v0.1.0.
- **No operators on omens.** An omen is an `enum class`; use `enchanting` methods for logic.

### Summary

| Feature | PenguScript | C++20 |
|---------|-------------|-------|
| Binary operator | `operator + = (other: T) -> T` | `T operator+(T other) const` |
| Unary operator | `operator - = -> T` | `T operator-() const` |
| Mut operator | `mut operator += = (other: T) -> void` | `void operator+=(T other)` |
| Free operator | `operator + = (a: int, b: T) -> T` | `T operator+(int a, T b)` |
| Comparison (shortcut) | `operator == = (other: T) -> bool` | `bool operator==(T other) const` + C++20 `!=` |
| Spaceship | `operator <=> = (other: T) -> Ordering` | `auto operator<=>(T other) const` + C++20 comparisons |
| Index | `operator [] = (i: size_t) -> ref<V>` | `V& operator[](std::size_t)` |
| Call | `operator () = (x: int) -> int` | `int operator()(int)` |
| Arity check | compiler | compiler |
| Return type check | compiler | compiler |
| `needs Ord` / `Numeric` satisfaction | structural | structural (C++20 concepts) |
`