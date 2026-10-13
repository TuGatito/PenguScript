# PenguScript Bindings

A **binding** exposes a native C library (or a pure PenguScript library) to
PenguScript code. Bindings are ordinary Git repositories: a consumer installs
one with `pengu add <url>` and then `import`s it.

This document describes the two supported kinds, the exact layout `pengu add`
relies on, and how a binding's `link "..."` statements reach the consumer's
link line. It is the contract behind `pengu init --template pengu-lib` and
`pengu init --template cbind`.

---

## 1. Pure PenguScript libraries

A pure library is just `.pengu` sources: no C, no `link`, no archive. Consumers
`import <name>` and call its `weave`s directly.

```
my_algorithms/
├── pengu.toml
├── README.md
├── .gitignore
└── pengu/
    └── my_algorithms.pengu    # the module + inline `test` blocks
```

Create one with:

```bash
pengu init my_algorithms --template pengu-lib
```

The module lives under `pengu/` from the start. `pengu add` standardises every
dependency to `pengu/`, so a library that already uses that directory is
installed without moving a single file (and therefore without leaving a stale
duplicate behind).

Because the manifest points `entry` at `pengu/<name>.pengu`, `pengu test`
inside the library runs its inline `test` blocks:

```bash
cd my_algorithms
pengu test
```

Consumers do:

```bash
pengu add https://github.com/me/my_algorithms
# → lib/my_algorithms/pengu/my_algorithms.pengu
```

```pengu
import my_algorithms

weave main into int:
  return calling my_algorithms.add with 2, 3
```

---

## 2. C bindings

A C binding wraps a native library (raylib, SDL, sqlite3, zlib, …). Layout:

```
pengu_raylib/
├── pengu.toml
├── README.md
├── .gitignore
├── build.py               # fetches/compiles the native part → lib/
├── pengu/
│   └── raylib.d.pengu     # declarations
├── include/
│   └── raylib.h           # the real C header
├── c/
│   └── raylib_glue.c      # optional glue (compiled by the consumer)
└── lib/
    └── libraylib.a        # compiled native library (built by build.py)
```

Create one with:

```bash
pengu init pengu_raylib --template cbind
```

The generated repository compiles and links out of the box: it ships a tiny C
implementation (`c/<name>.c`), a header, and a `build.py` that archives that
implementation into `lib/lib<name>.a`. Replace the toy with the real library,
then regenerate the declarations.

### 2.1 The `.d.pengu` file

`pengu/raylib.d.pengu` is a **declaration file**: it declares the C surface and
the native libraries, and nothing else. Three rules:

```pengu
include "raylib.h"

link "raylib"
link "m"
link "pthread"
link "dl"

alias AudioStream as opaque
declare InitWindow with width as int, height as int, title as ref to frozen char into void
```

1. **`include "..."`** tells the C compiler to include the real header. The
   header must live in `include/`, because the consumer's build adds
   `lib/<name>/include/` to its `-I` path.
2. **`link "..."`** names one native library per statement. These
   **propagate automatically** to the consumer's link line. Declare them here,
   not in the binding's own `pengu.toml` `links` key — that key only affects the
   binding's own build, which consumers never run.
3. **`declare` / `alias` / `rune` / …** is the C surface. `pengu bind` can
   generate all of it from a header.

Generate (or regenerate) the declarations from the header:

```bash
pengu bind include/raylib.h --output pengu/raylib.d.pengu --links raylib
```

`pengu bind` writes the `include "..."` line for the header, so the output is
directly usable. Re-read it afterwards: `link "..."` may still need to be added
by hand (one line per library the linker needs).

### 2.2 The `build.py` script

`build.py` runs when the binding is installed with `pengu add <url> --trust`
and again on every `pengu update`. It must:

- download the library's sources (`git clone`, `curl`, `pip`, CMake, …);
- compile the static library (`.a`, `.lib`) or shared library (`.so`,
  `.dylib`, `.dll`);
- copy the result into `./lib/` — any name matching
  `lib<name>.a|.so|.dylib|.dll` is auto-detected;
- copy the header(s) into `./include/`.

Keep it idempotent: `pengu update` re-runs it. A `build.py` is arbitrary
third-party code, so `pengu add` only executes it when explicitly trusted
(`--trust`, `PENGU_TRUST_ALL=1`, or an interactive "yes"); otherwise it warns
and skips it.

### 2.3 How the consumer's build finds everything

After `pengu add`, the consumer's `pengu build` resolves, with no edit to
`pengu.toml`:

| Piece | Where it is found |
| ----- | ----------------- |
| `import raylib` | `lib/pengu_raylib/pengu/raylib.d.pengu` |
| `#include "raylib.h"` | `lib/pengu_raylib/include/` (`-I`) |
| `-lraylib` | `lib/pengu_raylib/lib/libraylib.a` (`-L` + auto-detect) |
| extra `link` | `checker.symbols.links`, aggregated across imports |
| glue C | `lib/pengu_raylib/c/*.c`, compiled into the bundle |

`PenguBuilder.build_compile_commands` merges three sources of `-l` flags:

1. `config.links` from the consumer's `pengu.toml`;
2. `checker.symbols.links` — where every imported module's `link "..."`
   statements land, including the binding's `.d.pengu`;
3. auto-detected names from `lib/*/lib/*.a` (a bare archive with no `link`
   statement still links, provided its name matches the `-l` flag).

On GNU ld the whole set is wrapped in `-Wl,--start-group … -Wl,--end-group`,
so inter-archive dependencies resolve regardless of `-l` order. Apple's `ld64`
rejects `--start-group`, so macOS omits it; MSVC's `link.exe` receives the
translated `/LIBPATH:` + `.lib` form instead.

### 2.4 Using the binding

```pengu
import raylib

weave main into int:
  calling raylib.InitWindow with 800, 600, "My Game"
  calling raylib.SetTargetFPS with 60
  calling raylib.CloseWindow
  return 0
```

---

## 3. Installing a binding

```bash
pengu add https://github.com/me/pengu_raylib --trust
```

`pengu add` clones (or copies) the repository into `lib/<name>/`, moves any
root-level `.pengu` module into `lib/<name>/pengu/`, runs `build.py` when
trusted, records the dependency in `pengu.toml`, and prints the module name to
import:

```
       Added dependency 'pengu_raylib' to .../lib/pengu_raylib
     👉 Try: import raylib
```

Refresh later with `pengu update` (pull + rebuild) or `pengu update <name>`.

---

## 4. Common pitfalls

- ❌ **Declaring `link "raylib"` only in the binding's `pengu.toml`.** The
  consumer never reads that file's `links`; put it in the `.d.pengu`.
- ❌ **Leaving `.pengu` files at the repository root.** `pengu add` moves them
  into `pengu/`; committing them under `pengu/` from the start avoids the
  relocation (and the duplicate it used to leave behind).
- ❌ **Shipping `lib/libfoo.a` without `link "foo"`.** Auto-detection only
  produces `-l<name>` when the archive name matches; declare it explicitly when
  in doubt.
- ❌ **Forgetting `--trust`.** A binding whose `lib/` is not committed needs
  `build.py` to run, and `build.py` only runs when trusted.
- ❌ **Depending on C-string ↔ PenguScript-string conversion.** A C `const
  char *` is `ref to frozen char`; PenguScript does not convert it to a
  `string` automatically.
