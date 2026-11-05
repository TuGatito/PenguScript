# Building a PenguScript library

This guide describes how to write a library that other projects can install
with `psc add` and import like any other module. Everything below is tested
against `psc` 0.32.0 on Linux and macOS; the notes call out what only works on
newer compilers.

A library in PenguScript is **a git repository** (or a local directory) with a
`pengu.toml`, a `src/` tree whose modules are importable, and optionally an
`include/` directory with C declarations. There is no registry: the source URL
*is* the package.

<!-- toc -->
- [1. Repository layout](#1-repository-layout)
- [2. `pengu.toml`](#2-pengutoml)
- [3. The façade](#3-the-façade)
- [4. C code: two options](#4-c-code-two-options)
  - [Option A — header-only C (recommended)](#option-a-header-only-c-recommended)
  - [Option B — a real library (`-l`)](#option-b-a-real-library--l)
  - [Calling back into Pengu](#calling-back-into-pengu)
- [5. Publishing and installing](#5-publishing-and-installing)
  - [`build.pengu`](#buildpengu)
- [6. Testing a library](#6-testing-a-library)
- [7. Documentation and versioning](#7-documentation-and-versioning)
- [8. Licensing](#8-licensing)
- [9. Checklist](#9-checklist)
- [10. Known pitfalls](#10-known-pitfalls)
<!-- /toc -->

---

## 1. Repository layout

```
my_lib/
├── pengu.toml
├── src/
│   ├── my_lib.pengu          # façade: what `import my_lib` gives the user
│   └── my_lib/
│       ├── app.pengu         # import my_lib.app
│       ├── router.pengu      # import my_lib.router
│       └── native.d.pengu    # C declarations (private)
├── include/
│   └── my_lib_native.h       # C prototypes and header-only C code
├── tests/                    # optional: consumer projects and scripts
├── examples/                 # optional: runnable examples
├── LICENSE
├── THIRD_PARTY.md            # if you vendor third-party code
└── README.md
```

Two rules make the difference between "works locally" and "works after
`psc add`":

1. **The package's `src/` becomes a module root.** `psc add` copies the
   repository to `lib/<name>/` and adds `lib/<name>/src` to the module search
   path. A file at `src/foo.pengu` is therefore imported as `import foo`, and a
   file at `src/my_lib/router.pengu` as `import my_lib.router`. There is no
   package prefix other than the file path.
2. **Do not put your only entry point at `src/<name>.d.pengu`.** A file
   `src/native.d.pengu` is importable as `import native` from the consumer; a
   `.d.pengu` inside `src/<name>/` is namespaced and private in practice
   (`import my_lib.native`). The façade belongs in `src/<name>.pengu`.

`include/` is added as `-I` for the consumer, which is how `#include
"my_lib_native.h"` resolves from the generated C.

---

## 2. `pengu.toml`

A library is built as a static library (or shared), never as an executable:

```toml
[project]
name = "my_lib"
version = "0.1.0"
entry = "src/my_lib.pengu"
output = "static"

[build]
src_dir = "src"
include_dir = "include"
strict_c99 = true
```

- `name` must be a valid PenguScript identifier (lowercase, no dashes); it
  becomes the directory in `lib/` and the name in `pengu.toml` of consumers.
- `version` is semver. Consumers can pin it with `version = "^0.1"`, `tag`, or
  `branch`.
- `entry` only matters when the package is built on its own (CI, `psc build`);
  `psc add` installs the sources, not an artifact.

You do **not** need a `main` weave in a library. A `weave main into int` would
make `psc run` ambiguous; put demos in `examples/`.

---

## 3. The façade

The consumer writes `import my_lib` and expects one module with the public API.
Keep that module small: imports, aliases, constants, and thin wrappers.

```pengu-fragment
## my_lib — a small HTTP-ish library for PenguScript.
##
## Import `my_lib`; the implementation lives in `my_lib.*`.
import my_lib.app
import my_lib.router

alias Application as my_lib.app.Application
alias Router as my_lib.router.Router

## Creates an application with default settings.
weave new_application into Application:
    return calling my_lib.app.new_application
```

Re-exporting a type with `alias` also re-exports its methods: a value typed
`my_lib.Application` can call methods declared in `my_lib.app`. This is the
supported way to build a façade, because imports are not re-exports.

What to keep private: modules that the docs do not mention. A consumer can
still `import my_lib.native`, but the `_`-prefixed fields and the `##` contract
tell them not to. If you need real privacy, keep the implementation in a
module the façade never exposes and do not document it.

Naming follows the language guide: `snake_case` files, `PascalCase` types,
`snake_case` functions, no `utils`/`helpers`/`common` modules. A library is a
good place to be strict about this, because its names become other people's
vocabulary.

---

## 4. C code: two options

The consumer's build does **not** compile your `c/` directory and does **not**
read `links` from your `pengu.toml`. Only two things travel: your `src/` (as
modules) and your `include/` (as `-I`). `ldflag "..."` declared in a module
*is* emitted into the consumer's link line.

### Option A — header-only C (recommended)

Put the C implementation in `include/my_lib_native.h` as `static` functions and
declare it from `src/my_lib/native.d.pengu`:

```c
/* include/my_lib_native.h */
#ifndef MY_LIB_NATIVE_H
#define MY_LIB_NATIVE_H

#include <stdint.h>

static inline int32_t my_lib_add(int32_t a, int32_t b) {
    return a + b;
}

#endif
```

```pengu-fragment
## Declaraciones C de my_lib (privado).
include "my_lib_native.h"

declare my_lib_add with a as int, b as int into int
```

This is what makes `psc add` "just work": the whole project is a single C
translation unit, so header-only code is compiled in, dead code is dropped by
the C compiler, and nothing has to be found at link time. Keep the header
self-contained (`static inline`, no global state unless documented) and prefix
everything with your package name (`my_lib_`) to avoid clashes.

For bigger C dependencies, **amalgamate** them into one header at release time
(the way `stb` and `sqlite3` are distributed) instead of asking users to
install a system library. A generated `include/my_lib_llhttp.h` with `static`
functions is still header-only, and you keep the source in `vendor/` with its
license.

### Option B — a real library (`-l`)

If you must link a system library, declare it in a module:

```pengu-fragment
link "mylib"
```

The linker flag is emitted only if a live symbol needs it (DCE applies), but
the user must have the library installed and the compiler must find it. That
breaks the "one command" promise, so reserve it for libraries that are already
ubiquitous (libc, pthreads) or for optional features documented as such.

You can also ship a prebuilt static library inside your package and point at it
with an absolute or relative `ldflag`. It works, but the path is baked into the
generated link line: moving the project or vendoring the package breaks it.
Prefer option A.

### Calling back into Pengu

A C function can call a Pengu weave passed as a function pointer. The portable
handle is `ref to void`:

```pengu-fragment
declare my_lib_run with cb as weave with userdata as ref to void into void, userdata as ref to void into int
```

Pass `sigil of state` as the user data and `transmute` it back inside the
callback. This is how an event loop (or a server) delivers events to the
library.

---

## 5. Publishing and installing

1. Commit, tag, push:

   ```sh
   git tag v0.1.0
   git push origin main --tags
   ```

2. The user installs it:

   ```sh
   psc add https://github.com/you/my_lib --trust
   ```

   `--trust` is required because `psc add` runs the package's `build.pengu` if
   it exists (it executes code). Without `--trust`, the sources are still
   installed but the build script is skipped (`--no-build` does the same).

3. `pengu.toml` of the consumer gets:

   ```toml
   [dependencies.my_lib]
   url = "https://github.com/you/my_lib"
   version = "^0.1"
   ```

   and `pengu.lock` pins the exact commit. Commit the lock file; use
   `--locked` in development and `--frozen` in CI.

On compilers **0.28.0 and older**, `psc add` without `--name` corrupts the
manifest (fixed in 0.31.0). Pass `--name my_lib` explicitly if you are stuck on
0.28.0.

### `build.pengu`

An optional program at the package root, run with `psc run build.pengu --` in
the package directory when the user trusts it. Use it to generate code, check
the environment, or build native artifacts. Keep it idempotent and fast; it
runs on every `psc add` unless the user passes `--no-build`. A typical script
prints one line per step and exits non-zero on failure, so the install stops.

---

## 6. Testing a library

`psc test` runs the `test "..."` blocks in your `src/`:

```pengu-fragment
test "adds two numbers":
    let got as int is calling my_lib_add with 2, 3
    assert got == 5
```

For the public API, add a consumer project under `tests/consumer/` that
installs the library by path and runs a program. That is the only way to test
what the user actually experiences (module resolution, `include/`, ldflags):

```sh
psc add ../.. --name my_lib --trust
psc run src/main.pengu
```

Automate it in CI with a script that copies the repository to a temporary
directory, adds it to a fresh project, and checks the output. Keep the
"compiles in a clean project" test separate from unit tests; it catches the
packaging bugs that unit tests cannot.

---

## 7. Documentation and versioning

- Every public symbol gets a `##` docstring. `psc doc` publishes it; a public
  symbol without documentation is unfinished.
- Document ownership for anything that allocates: does the caller own the
  returned string/list? Are parameters borrowed? PenguScript does not check
  this for you.
- Semver: patch for fixes, minor for additions (new modules, new functions),
  major for breaking changes. Deprecate with `@deprecated("use X instead")`
  and keep the old symbol for at least one minor release.
- Note the compiler version you test against in the README and pin it in CI.

---

## 8. Licensing

- Put a `LICENSE` at the root (MIT is the usual choice for PenguScript code).
- If you vendor C code, keep its license text, record the origin and version in
  `THIRD_PARTY.md`, and make sure the license is permissive (MIT, BSD-2/3,
  Apache-2.0, ISC, public domain). GPL code cannot be linked into most
  projects; do not vendor it.
- Apache-2.0 requires keeping the `NOTICE` file and the attribution.

---

## 9. Checklist

- [ ] `pengu.toml` with `output = "static"` and a valid `name`.
- [ ] Public API in `src/<name>.pengu`; implementation in `src/<name>/*.pengu`.
- [ ] Type façade re-exported with `alias`, not by re-declaring it.
- [ ] C code header-only in `include/`, prefixed, documented; or a documented
      `link` for a system library.
- [ ] `psc build` and `psc test` pass in the library itself.
- [ ] A consumer project installs it with `psc add` and runs.
- [ ] `psc doc` runs clean; the module docstring says what the library does
      **not** do.
- [ ] `LICENSE` and, if needed, `THIRD_PARTY.md`.
- [ ] Version tagged, `pengu.lock` of the consumer committed.

---

## 10. Known pitfalls

- **`import` is path-based, not package-based.** If `import my_lib.core`
  fails after `psc add`, check that the file is at
  `lib/my_lib/src/my_lib/core.pengu`, not `lib/my_lib/src/core.pengu`.
- **No closures.** A callback is a named weave plus `ref to void` user data
  (or `std.functor`); a lambda cannot capture. Design APIs around a
  context/handle parameter.
- **`concept` has no dynamic dispatch.** A list of `concept` values is not
  possible; use a tagged `omen`, a `rune` with function pointers, or an enum
  plus `judge`.
- **`let` bindings are frozen in some positions** (`ref to frozen T`); use
  `var` when you need to call a mutating method on the local.
- **Every statement needs a form:** `calling f with x`, `let y is ...`,
  `return ...`. A bare call is a syntax error.
- **`with` needs `field is value`**: `Widget with name is "x"`, never
  `Widget with "x"`.
- **Empty containers need a type**: `let xs as list of int is []`.
- **`at` is an operator**: write `xs at 0`, not `calling xs.at with 0`.
- **Strings are owned by default.** A function that takes a `string` parameter
  borrows it; returning one transfers ownership to the caller. Do not `banish`
  a parameter.
- **The consumer does not compile your C.** If `psc add` works but the
  consumer's link fails with an undefined symbol, you shipped C in `c/`
  instead of `include/`.
