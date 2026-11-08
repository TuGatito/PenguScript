# Building a PenguScript library

This guide describes how to write a library that other projects install with
`psc add` and import like any other module. It reflects `psc` 0.53.0.

A library is a git repository (or a local directory) with a `pengu.toml`, an
importable source tree, and optional C headers and native archives. There is no
registry: the source URL *is* the package.

<!-- toc -->
- [1. Repository layout](#1-repository-layout)
- [2. `pengu.toml`](#2-pengutoml)
- [3. The façade](#3-the-façade)
- [4. C code and native libraries](#4-c-code-and-native-libraries)
  - [Option A — header-only C](#option-a--header-only-c)
  - [Option B — a real native library](#option-b--a-real-native-library)
  - [`build.pengu`](#buildpengu)
- [5. Publishing and installing](#5-publishing-and-installing)
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
├── pengu/                    # or src/; declared by [build] src_dir
│   ├── my_lib.pengu          # façade: what `import my_lib` gives the user
│   └── my_lib/
│       ├── app.pengu         # import my_lib.app
│       ├── router.pengu      # import my_lib.router
│       └── native.d.pengu    # C declarations (private)
├── include/
│   └── my_lib_native.h       # C prototypes and header-only C code
├── lib/                      # native .a/.so/.dylib/.dll, if any
├── build.pengu               # optional: stages native artifacts
├── tests/                    # optional: consumer projects and scripts
├── examples/                 # optional: runnable examples
├── LICENSE
├── THIRD_PARTY.md            # if you vendor third-party code
└── README.md
```

Two rules make the difference between "works locally" and "works after
`psc add`":

1. **`[build] src_dir` is the module root.** The driver adds
   `<package>/<src_dir>` to the consumer's module search path. With
   `src_dir = "pengu"`, `pengu/foo.pengu` is `import foo` and
   `pengu/my_lib/router.pengu` is `import my_lib.router`. Older packages that
   only have `src/` keep working because the default is `src_dir = "src"`.
2. **The directory name and the import name are different things.** The
   consumer installs into `lib/<name>`, but imports by module path. Declare the
   intended namespace in the manifest; see below.

`include/` is added as `-I` for the consumer, which resolves
`#include "my_lib_native.h"` from the generated C. `lib/` is added as `-L`, so
`link "my_lib"` finds `lib/libmy_lib.a` without a hard-coded path.

---

## 2. `pengu.toml`

A library is built as a static or shared library, never as an executable:

```toml
[project]
name = "my-lib-repo"        # repository/package name; may contain dashes
import = "my_lib"           # optional: default import/dir when `psc add` has no --name
version = "0.1.0"
entry = "pengu/my_lib.pengu"
output = "static"

[build]
src_dir = "pengu"           # default: "src"
include_dir = "include"     # default: "include"
lib_dir = "lib"             # default: "lib"
c_dir = "c"                 # only for this repo's own `psc build`
```

- `name` is the package identity used in `pengu.lock` and diagnostics. It may
  contain letters, digits, `_` and `-`.
- `import` is the namespace users type. If present and the user did not pass
  `--name`, `psc add` installs into `lib/<import>` and writes the dependency
  under that key. Example: `psc add https://github.com/TuGatito/raylib-pengu`
  installs `lib/raylib`, so users write `import raylib`.
- `version` is semver. Consumers pin it with `version = "^0.1"`, `tag`, or
  `branch`. Tag the repository (for example `v0.1.0`); a repository without
  tags still installs from its default branch when the constraint is `*`.
- `entry` only matters when the package is built on its own (CI, `psc build`);
  `psc add` installs sources and, with trust, runs `build.pengu`.
- `lib_dir` is both where `build.pengu` leaves native archives and what the
  driver adds to the consumer's `-L`.

You do **not** need a `main` weave in a library. Put demos in `examples/`.

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

Naming follows the language guide: `snake_case` files, `PascalCase` types,
`snake_case` functions, no `utils`/`helpers`/`common` modules.

---

## 4. C code and native libraries

The consumer does **not** compile your `c/` directory and does **not** read
`links` from your `pengu.toml`. Three things travel: your source tree (as
modules), your `include/` (as `-I`), and anything your `build.pengu` stages in
`lib/` (as `-L`). `link "..."` and `ldflag "..."` declared in a module are
emitted into the consumer's link line.

### Option A — header-only C

Put the C implementation in `include/my_lib_native.h` as `static` functions and
declare it from `pengu/my_lib/native.d.pengu`:

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

This is the simplest distribution: a single C translation unit, no link-time
lookup, dead code dropped by the C compiler. Keep the header self-contained
(`static inline`, no global state unless documented) and prefix everything with
your package name.

### Option B — a real native library

For a prebuilt or compiled archive:

1. Put the archive in `lib/libmy_lib.a` (or `.so`/`.dylib`/`.dll`/`.lib`).
2. Declare `link "my_lib"` in the module that uses it.
3. Make `build.pengu` produce that file when it is missing.

The driver adds `<package>/lib` (or the declared `lib_dir`) to `-L`, so the
consumer does not need `ldflag` with a path. A hard-coded `ldflag` is still
supported for compatibility but is fragile: moving or vendoring the package
breaks it.

Native archives are copied by `psc add` (only the archives, not the whole
`lib/` tree) and preserved by `psc vendor`, so `--frozen` works offline.

### `build.pengu`

An optional PenguScript program at the package root. `psc add`, `psc update`
and `psc upgrade` run it **only with `--trust`** (or `PENGU_TRUST_ALL=1`);
without trust it is skipped with a message. It runs with the package directory
as cwd. Exit non-zero on failure: `psc` then aborts the install and rolls back a
new dependency.

Keep it idempotent: if the archive is already present, return 0. A typical
script:

```pengu
import std.archivum
import std.rites
import std.spark

weave main into int:
    if calling archivum.is_file with "lib/libmy_lib.a":
        return 0
    # Descarga verificada, o clona y compila el proyecto C.
    var rc as int is calling rites.run_shell with "make -C native"
    if rc != 0:
        return 1
    return 0
```

Do not ship `build.py`, `build.sh` or any other name: the installer only looks
for `build.pengu`. If a package needs Python today, port the logic to
PenguScript (`std.petitio` for HTTP, `std.digest` for checksums,
`std.archivum` for files) or commit a `build.pengu` that invokes an external
tool explicitly and fails when it is unavailable.

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
   psc add https://gitlab.com/you/my_lib --trust
   ```

   `--trust` is required to run `build.pengu`. Without it the sources are
   installed but native artifacts are not produced; `--no-build` is the
   explicit way to skip the script.

3. `pengu.toml` of the consumer gets:

   ```toml
   [dependencies.my_lib]
   url = "https://github.com/you/my_lib"
   version = "^0.1"
   ```

   or, for a local path:

   ```toml
   [dependencies.my_lib]
   path = "/home/you/my_lib"
   ```

   `pengu.lock` is schema 2: it pins source, commit, version, constraint,
   SHA-256 of the installed tree and the target. Commit the lock; use
   `--locked` in development and `--frozen` in CI.

URL forms accepted by `add`:

- `https://github.com/you/my_lib` (GitHub, default branch)
- `https://gitlab.com/you/my_lib/-/tree/v0.2.0` (ref from GitLab URL)
- `https://github.com/you/my_lib#v0.2.0` (explicit ref)
- `file:///absolute/path` and `ssh://git@host/repo.git`
- a local path, absolute or relative to the current directory

GitLab needs no special code: it is plain git over HTTPS/SSH. Private
repositories use the user's normal git credentials; avoid putting tokens in the
URL because the manifest and lock would store them.

---

## 6. Testing a library

`psc test` runs the `test "..."` blocks in your source tree:

```pengu-fragment
test "adds two numbers":
    let got as int is calling my_lib_add with 2, 3
    assert got == 5
```

For the public API, add a consumer project under `tests/consumer/` that
installs the library by path and runs a program. That is the only way to test
what the user experiences (layout, module resolution, `-I`, `-L`, native
archive):

```sh
psc add ../.. --trust
psc run src/main.pengu
```

Test it twice: with a clean checkout (no `lib/*.a`) and with `--frozen` after
`psc vendor`. The first catches a missing `build.pengu`; the second catches a
vendor that dropped native files.

---

## 7. Documentation and versioning

- Every public symbol gets a `##` docstring. `psc doc` publishes it.
- Document ownership for anything that allocates.
- Semver: patch for fixes, minor for additions, major for breaking changes.
  Tag releases; `psc add --version '^0.2'` selects the highest matching tag.
- State the `psc` version you test against in the README.

---

## 8. Licensing

- Put a `LICENSE` at the root (MIT is the usual choice).
- If you vendor C code, keep its license, record origin/version in
  `THIRD_PARTY.md`, and use a permissive license (MIT, BSD, Apache-2.0, ISC).
- Apache-2.0 requires keeping `NOTICE`.

---

## 9. Checklist

- [ ] `pengu.toml` with `output = "static"` (or `shared`), a valid `name` and,
      if the import name differs, `import`.
- [ ] Public API in `<src_dir>/<import>.pengu`; implementation below it.
- [ ] `[build] src_dir` / `include_dir` / `lib_dir` match the repository.
- [ ] C header-only in `include/`, or a native archive in `lib/` produced by
      `build.pengu`.
- [ ] `build.pengu` idempotent, verified downloads, non-zero on failure.
- [ ] `psc build` and `psc test` pass in the library itself.
- [ ] A clean consumer installs with `psc add --trust` and builds without
      symlinks or manual `-L`.
- [ ] `psc vendor` + `psc build --frozen` works.
- [ ] `LICENSE`, tags, and the consumer's `pengu.lock` committed.

---

## 10. Known pitfalls

- **`import` is path-based.** If `import my_lib.core` fails, check
  `lib/my_lib/<src_dir>/my_lib/core.pengu`. The driver reads `src_dir`; it no
  longer assumes `src/`.
- **The package name is not the import.** `raylib-pengu` installs as
  `lib/raylib-pengu` unless the manifest declares `import = "raylib"` or the
  user passes `--name raylib`.
- **Untrusted builds do nothing.** `psc add` without `--trust` skips
  `build.pengu`; a native package then fails at link time. Use `--trust` in a
  clean environment or document the artifacts.
- **The consumer never compiles `c/`.** Put reusable C in `include/` or stage a
  real archive in `lib/`.
- **No closures.** A callback is a named weave plus `ref to void` user data.
- **`concept` has no dynamic dispatch.** Use a tagged `omen`, a `rune` with
  function pointers, or an enum plus `judge`.
- **Empty containers need a type**: `let xs as list of int is []`.
- **`at` is an operator**: `xs at 0`, not `calling xs.at with 0`.
- **Strings are owned by default.** A `string` parameter is borrowed; do not
  `banish` it. Returning a string transfers ownership.
- **Vendoring keeps only native archives from `lib/`**, not the whole tree.
  Do not rely on arbitrary files under `lib/` at consumer build time.
