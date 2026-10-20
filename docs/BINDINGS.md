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
├── build.pengu                # optional native extensions (no-op without c/)
├── pengu/
│   └── my_algorithms.pengu    # the module + inline `test` blocks
├── c/
├── include/
└── lib/
```

The generated `build.pengu` exits 0 with "nothing to compile" until you drop a
`.c` file into `c/`; then it compiles every `c/*.c` into
`lib/lib<name>.a`. You never have to edit it to enable that.

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
├── build.pengu            # fetches/compiles the native part → lib/
├── pengu/
│   └── raylib.d.pengu     # declarations
├── include/
│   └── raylib.h           # the real C header
├── c/
│   └── raylib_glue.c      # optional glue (compiled by the consumer)
├── vendor/                # optional, gitignored third-party sources
└── lib/
    └── libraylib.a        # compiled native library (built by build.pengu)
```

Create one with:

```bash
pengu init pengu_raylib --template cbind
```

The generated repository compiles and links out of the box: it ships a tiny C
implementation (`c/<name>.c`), a header, and a `build.pengu` that archives that
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

### 2.1.1 Internal bindings: wrapper + companion declaration file

A binding can be **internal**: the consumer imports a wrapper that adds types,
ownership and a PenguScript-shaped API, while the raw C declarations stay in a
sibling file. The convention is:

```
pengu/
├── lingua.pengu       # public wrapper: import std.lingua
└── lingua.d.pengu     # internal declarations: include, link, declare
```

`import std.lingua` resolves to the non-declaration spelling
(`find_module_path` prefers `lingua.pengu`), so the binding file is never a
public module. To make it reachable, `resolve_imports` adds a **companion
declaration file** as an implicit dependency of the wrapper: the companion is
checked first (registering its `declare`/`include`/`link` lines) and then the
wrapper body. A `.d.pengu` file may only declare, never define (`E0025`), which
is why the length-aware C bridge lives in the wrapper's `antiquus` functions.

This is exactly how `std.lingua`/`std.regulus` are built; see
[`LINGUA.md`](LINGUA.md) §10 and [`REGULUS.md`](REGULUS.md) §11.

### 2.2 The `build.pengu` script

`build.pengu` is the **official** build-script format for bindings and
PenguScript libraries. It is ordinary PenguScript: the toolchain compiles it with
the same runtime and `std/` it uses for your project, so it needs no Python and
no separate dependency.

It runs when the binding is installed with `pengu add <url> --trust`, again on
every `pengu update --trust` (with `--force`), and manually:

```bash
pengu run build.pengu              # skip when lib/lib<name>.a already exists
pengu run build.pengu -- --force   # always rebuild
```

It must:

- download the library's sources when needed (`git clone`, `make -C`, …);
- compile the static library (`.a`, `.lib`) or shared library (`.so`,
  `.dylib`, `.dll`);
- copy the result into `./lib/` — any name matching
  `lib<name>.a|.so|.dylib|.dll` is auto-detected;
- copy the header(s) into `./include/`.

Keep it idempotent: `pengu update --trust` re-runs it with `--force`. A
`build.pengu` is arbitrary third-party code, so `pengu add`/`pengu update` only
execute it when explicitly trusted (`--trust`, `PENGU_TRUST_ALL=1`, or an
interactive "yes"); otherwise they warn and skip it.

The generated cbind script is the canonical minimal example:

```pengu
import std.archivum
import std.compass
import std.invoke
import std.rites
import std.scrolls
import std.spark

const BINDING_NAME as string is "raylib"

weave cbind_log with message as string into void:
    calling spark.println with "[cbind] {message}"

weave main into int:
    var _d as bool is calling archivum.create_dir with "lib"
    var parser as invoke.Parser is calling invoke.new_parser with "build", "build the binding"
    calling parser.add_flag with "force", "f", "rebuild", false
    let argv as list of string is calling rites.get_args
    let res as invoke.ParseResult is calling parser.parse with argv
    let force as bool is calling res.get_bool_or with "force", false

    let archive as string is "lib/lib{BINDING_NAME}.a"
    if (calling archivum.is_file with archive) and not force:
        calling cbind_log with "{archive} already exists (use --force)"
        return 0

    let sources as list of string is calling archivum.find_by_ext with "c", ".c", false
    for src in sources:
        let stem as string is calling compass.stem with src
        let obj as string is "lib/{stem}.o"
        let src_q as string is calling rites.shell_escape with src
        let obj_q as string is calling rites.shell_escape with obj
        if (calling rites.run_shell with "cc -c -fPIC -I include {src_q} -o {obj_q}") != 0:
            return 1
    # archive the objects with `ar rcs lib/lib<name>.a …`
    return 0
```

Two practical notes learned from real bindings:

- `std.archivum.glob` matches **names** recursively (a substring match), not
  shell globs: use `find_by_ext`/`find_files` instead of `glob("c/*.c")`.
- A top-level weave called `log` collides with `log()` from `<math.h>` in the
  generated C; name it `cbind_log` (or anything unique).

The equivalent **pengu-lib** script is a no-op until you add C glue; it is
generated by `pengu init --template pengu-lib` and mirrors the one above with
`c/` empty by default.

A real, complete reference is
[`TuGatito/raylib-pengu`](https://github.com/TuGatito/raylib-pengu): its
`build.pengu` resolves a raylib checkout (`$RAYLIB_SRC`, `vendor/raylib`,
`extern/raylib-*`), clones it when necessary, builds with
`make PLATFORM=PLATFORM_DESKTOP`, compares the tree's headers with the committed
ones and installs `lib/libraylib.a`. The repository keeps a tiny `build.py`
shim that forwards to `build.pengu` for pengu < 2.16.

#### 2.2.1 Discovery order and legacy scripts

The toolchain looks for build scripts in this order (first hit wins):

1. `build.pengu` — preferred, invoked as `pengu run <dep>/build.pengu [-- --force]`;
2. `build.py` — legacy, run with the current Python interpreter;
3. `build.bat` — legacy, Windows only;
4. `build.sh` — legacy, POSIX only;
5. `Makefile` — legacy, run with `make`.

The legacy forms still work, receive `--force` as a plain argument, and print an
informational note (suppressed by `--quiet` and in CI). They are **deprecated**
and will be removed in **3.0.0**; the deprecation window is 2.16.0 through the
2.x line (see [DEPRECATIONS.md](DEPRECATIONS.md)).

#### 2.2.2 Migrating a `build.py` to `build.pengu`

The mapping is mechanical because `std.archivum`, `std.rites` and
`std.compass` cover what a binding build needs:

| Python | PenguScript |
| ------ | ----------- |
| `os.makedirs(p, exist_ok=True)` | `calling archivum.create_dir with p, true` |
| `shutil.which("git")` | `calling rites.which with "git"` (returns `maybe string`) |
| `subprocess.run(["make", "-C", src], check=False).returncode` | `calling rites.run_shell with "make -C {src_q}"` |
| `open(path, "rb").read()` | `calling archivum.read_bytes with path` (`maybe string`) |
| `shutil.copy2(src, dst)` | `calling archivum.copy_file with src, dst, true` |
| `glob.glob("extern/raylib-*")` | `calling archivum.find_dirs with "extern", false` + `std.scrolls.starts_with` |
| `os.remove(path)` | `calling archivum.delete_file with path` |
| `sys.exit(N)` | `return N` from `weave main into int` |
| `argparse` `--force` | `std.invoke` `add_flag` + `get_bool_or` |
| `os.environ.get("CC")` | `calling rites.getenv_or with "CC", ""` |

Remember: `calling compass.join with ...` takes a **list** (`[a, b]`), a
`maybe` is tested with `is present` / `is not present` (never `is none`), and a
list literal cannot be passed directly as an argument — assign it to a typed
variable first.

#### 2.2.3 `PENGU_BIN`

When `build.pengu` runs inside `pengu add`/`pengu update`, the toolchain invokes
itself. It finds itself, in order, as the frozen executable, as the source
checkout (`python pengu_project.py …`), or as `pengu` on `PATH`. Set
`PENGU_BIN=/path/to/pengu` to override all of that — useful in CI, in a
PATH-less shell, or when testing a specific binary.

#### 2.2.4 Transitive dependencies are not built automatically

`add` builds the dependency you named, once. Transitive dependencies discovered
from its manifest are installed with `run_build=False` on purpose: `--trust` is
consent for *one* repository, not for everything it happens to depend on. To
build a transitive dependency, add it explicitly:

```bash
pengu add <transitive-repo> --trust
```

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
root-level `.pengu` module into `lib/<name>/pengu/` (**except `build.pengu`**,
which is a build script, not a module), runs the build script when trusted,
records the dependency in `pengu.toml`, and prints the module name to import:

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
  `build.pengu` (or a legacy build script) to run, and it only runs when
  trusted.
- ❌ **Naming a build helper `log`.** The generated C includes `<math.h>`, whose
  `log()` collides with a weave of that name; use `cbind_log`.
- ❌ **Using `archivum.glob("c/*.c")`.** `glob` matches names recursively by
  substring, not POSIX shell patterns; use `find_by_ext`/`find_files`.
- ❌ **Depending on C-string ↔ PenguScript-string conversion.** A C `const
  char *` is `ref to frozen char`; PenguScript does not convert it to a
  `string` automatically.
