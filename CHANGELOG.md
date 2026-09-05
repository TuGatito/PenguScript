# Changelog
All notable changes to PenguScript will be documented in this file.

## [0.8.4] - Unreleased

### Repository, testing & cross-platform preparation

- **Cleanup before commit**: removed developer leftovers (`pengu_runtime_original.h`,
  personal scratch notes, stray root test artifacts) and extended `.gitignore`
  (logs, `*.csv`, caches, release staging).
- **Test-suite rewritten & unified**: the two test folders (`tests/`, `tests_std/`)
  were merged into `tests/` and the ~100 scattered test files were replaced by a
  small, organised suite — 7 pytest files grouped by area:
  `test_compiler_core.py`, `test_compiler_features.py`, `test_modules_bindings.py`,
  `test_lsp.py`, `test_cli_tools.py`, `test_ffi_libs.py`, `test_stdlib.py`
  (+ shared `tests/conftest.py` helpers and one exercise program per std module
  under `tests/std_programs/`, several libraries covered per file).
  Full suite: **484 passed / 0 failed** (up from 438).
- **Unbuildable extern removed**: `libwebsockets` was dropped from
  `extern_manifest.py` and `extern/` (2023-era sources do not build cleanly with
  modern GCC); `build_runtime.py` never referenced it. Manifest typo
  `tomic17`→`tomlc17` fixed and its docstring updated.
- **Cross-platform runtime builds**: `build_runtime.py` now selects the CMake
  generator per host (MinGW Makefiles + mingw32-make on Windows; Unix Makefiles /
  Ninja on POSIX), skips the Windows-tuned static builds of libxml2/libcurl/
  libmicrohttpd on Linux/macOS (the C runtime then links the system libraries;
  libxml2 include dirs discovered via `pkg-config`), makes best-effort builds
  non-fatal with a per-library summary, and skips the x64-only WebUI prebuilt on
  Apple Silicon. `pengu_project.py` links the POSIX runtime/system libraries
  (`-pthread -lm -ldl`, falling back to system libcurl/libxml2/libmicrohttpd)
  and `make_release.py` stays OS-generic.
- **CI on three operating systems**: `.github/workflows/ci.yml` now runs the full
  build + test + packaging matrix on **Windows, Linux and macOS** (Python 3.14 +
  Node 20, per-OS C-library dev packages via apt/brew, `build_runtime.py`,
  `pytest tests/`, `make_release.py`) and uploads per-OS standalone artifacts plus
  the VS Code extension `.vsix`. `release.yml` mirrors the matrix and publishes
  the release assets.
- **CI cross-platform fixes** (validated on the 3-OS matrix):
  - `build_runtime.py` re-applies the libuv MinGW const patch to
    `src/win/util.c` automatically (extern/ is re-downloaded per CI run) and
    stages libzip's CMake-generated `zipconf.h` after every build, fixing
    fresh-checkout xlsxio builds.
  - On POSIX the C runtime compiles against system libxml2/libcurl/
    libmicrohttpd headers via `pkg-config` (with a Homebrew include fallback),
    and the macOS workflow installs curl + sets `PKG_CONFIG_PATH`.
  - Link lines (tests and `pengu_project.py`) add the Homebrew `-L` prefix on
    macOS; Windows-only test libs (`bcrypt`, `comdlg32`, …) are now gated to
    Windows, and GUI link-probes (webui/raylib/tinyfd) run on Windows only.
  - `pengu_c_filum_goroutine_id` returns a real OS thread id on Linux/macOS
    (`pthread_threadid_np`) so `std.filum` reports it correctly there.
  - Test compile helpers tolerate newer-GCC error-promoted warnings
    (`-Wno-error=implicit-*`, `-Wno-error=int-conversion`).
- **Documentation overhaul**: `CHEATSHEET.md` rewritten from scratch — 2,300+
  lines, 20 numbered topical sections, entirely in English, every Pengu example
  that maps to generated code followed by the emitted C, balanced code fences and
  checked internal anchors. `README.md` rewritten with a current project layout
  and a complete Third-Party Acknowledgements section (Python + every C /
  single-header runtime dependency with license details read from the vendored
  headers).

### Language Server performance

- **Debounced validation on `didChange`**: typing no longer triggers a full
  parse + semantic-check per keystroke. Changes are coalesced per document
  with a 350 ms debounce, and any pending run is cancelled when new edits
  arrive, so a fast typing burst produces one validation of the final text.
  `didOpen` and `didSave` still validate immediately (and flush pending
  debounces on save).
- **Validation runs off the event loop**: the (now rarer) full-document
  checks execute in a worker thread via `run_in_executor`, keeping hover /
  completion / go-to-definition responsive while a large file validates;
  results are published back on the asyncio loop thread.
- **Content-hash validation cache**: re-validating a document whose text did
  not change (duplicate didChange / didSave after didChange) re-publishes the
  cached diagnostics instead of re-running the parser and checker.
- The programmatic sync entry points (`validate_document`, `did_open`,
  `did_change`, `did_save`) keep their immediate semantics for embedders and
  tests; new tests cover debounce coalescing, flush-on-save, cache hits and
  cache eviction.

### Compiler bug fixes (found by the rewritten test-suite)

- **`ritual` (static) methods no longer emit corrupted C**: the grammar wraps
  `ritual`/`inline` weave modifiers in a `weave_modifier` Tree, which the code
  generator previously mistook for the function name — leaking the raw AST
  repr into prototypes/definitions (e.g. `Vec2_Tree(Token('RULE', ...))`) and
  mangling the return type. `skip_weave_modifiers()` now handles both the Tree
  and bare-Token shapes in declares, weaves and monomorphized weaves; ritual
  methods emit clean `Type_name(void)` / `Type_name(params)` signatures with no
  `self` parameter.
- **Algebraic `omen` construction fixed and unified**: generated payload
  structs use a single `data` union member (was `as`) so construction,
  patterns and type definitions agree; `with Variant is with field is …`
  constructs the right tag + payload; and bare-payload forms such as
  `with code is 404` now resolve the field to its owning variant
  (`.tag = …_Failure, .data.Failure = {.code = 404}`) instead of emitting a
  bogus tag and dropping the value. Fields from different variants in one
  initializer and ambiguous/unknown fields are rejected (`E0041`).
- **Generic `omen` specializations print their mangled name**: a specialized
  `Status of string` now declares C variables as `Status_string` (the template's
  `c_name` leaked through `substitute()` before, producing an undeclared base
  type), making generic omens usable end to end.

### FFI language features (word-first style)

- **`bytes of <string>`** — borrows a string's characters as a read-only
  `ref to byte` for native C byte APIs (`((uint8_t*)((s).data))`), no copy.
- **`bytes of <array of byte>`** — yields a writable `ref to byte` to the first
  element of a fixed-size byte buffer (`&(buf)[0]`), enabling C output buffers.
  Non-string/non-byte-array operands are rejected (`E0005`).
- **Weave → C function pointers (proven at runtime, both directions)**: a
  `weave` name passed where a callback is expected decays to its C function
  pointer; a runtime helper in `pengu_runtime.h`
  (`pengu_call_callback_int`) plus a minicoro shim
  (`std_c/wrappers_minicoro.c` `pengu_mco_*`, externs in the runtime header)
  let C call PenguScript weaves and run a **PenguScript weave as a minicoro
  coroutine body** (resume/yield) from pure Pengu.
- VS Code: `bytes of` keyword + snippets; CHEATSHEET §14 (C Interop & FFI).
- **G5 xlsx stack**: `extern_manifest.py` += `libzip-1.11.3`, `expat-2.6.4`, `libyaml-0.2.5`; `build_runtime.py`
  gains tolerant `build_libzip`/`build_libexpat`/`build_xlsxio` builders (libzip & expat via CMake,
  xlsxio compiled directly with `-DSTATIC` incl. its shared-strings source). `pengu_project.py` injects
  `-DSTATIC` when xlsxio libs are linked (fixes `__imp_*` on Windows). `tests/test_extern_g5.py` proves a
  real write+read `.xlsx` round-trip.
- **libuv 1.52.1** integrated into `build_runtime.py` (`build/lib/libuv.a`, headers staged; one-line MinGW const fix in `extern/libuv-1.52.1/src/win/util.c`); `pengu_project.py` links `psapi/userenv/iphlpapi` on Windows.
- **YAML built**: `libyaml-0.2.5` (direct gcc of 8 sources + minimal `build/include/config.h` with `-DHAVE_CONFIG_H`) and `libcyaml-1.4.2` (direct gcc with `VERSION_*` defines) wired into `build_runtime.py` (`build_libyaml`/`build_libcyaml`, no-op verified); headers `yaml.h`/`cyaml/cyaml.h` staged.
- **G5 Pengu layer** (curated bindings + wrappers, all semantic-checked and compile+link+run verified):
  - `std/xlsxio.d.pengu` (xlsxio *write* API: open/close/next_row/add_cell_string/int/float/add_column/set_detection_rows) + pure-Pengu wrapper `std/xlsx.pengu` (`xlsx.write_sheet` / `xlsx.write_rows`) that writes a real `.xlsx` workbook; runtime strings reach C `const char*` parameters via `bytes of <string>`. Verified by a Pengu compile+run that produces a valid workbook (sheet name + cell strings checked inside the produced zip).
  - `std_c/wrappers_tomlc17.c` + `std_c/pengu_tomlc17.h`: `pengu_toml_valid`/`pengu_toml_valid_file` shim over tomlc17's by-value `toml_result_t` API (which pure Pengu cannot express); `build_tomlc17` now compiles the shim into `libtomlc17.a` and stages the companion header. Binding: `std/tomlum.d.pengu`.
  - `std/yaml.d.pengu`: libyaml version query via out-`int` parameters (`yaml.get_version`, `sigil of`); YAML/libcyaml *parsing* remains C-level only (schema/event structs) - documented in the module header.
  - libzip/libexpat/libuv stay C-level dependencies (no raw binding; xlsxio uses them); documented in CHEATSHEET §15 (Standard Library).
- Tests for the FFI/G5 features live in the consolidated suite: `tests/test_compiler_features.py`
  (bytes of, weave→pointer, coroutine) and `tests/test_ffi_libs.py` (xlsxio/xlsx round-trip,
  tomlum validity incl. file variant, yaml version, sqlite3, runtime + stb link checks,
  semantic sweep over every `std/*.d.pengu`).

## [0.8.3] - Unreleased

### Manual curated bindings for the remaining `std_c/` libraries

- **`std/xxhash.d.pengu`** — hand-written binding for the vendored `xxhash.h`
  (it cannot be auto-bound by `pengu bind`): `XXH_versionNumber`, the XXH32 /
  XXH64 / XXH3_64bits / XXH3_128bits one-shots (with `_withSeed`), the three
  opaque streaming state types and their `createState / freeState / reset /
  update / digest` families, plus the `XXH128_hash_t` struct result. Uses the
  real C symbol names (no insignia). Verified end-to-end from PenguScript
  (canonical vectors + streaming==one-shot consistency).
- **`std/uuid.d.pengu`** — every public function of `uuid.h` (uuid0_generate,
  uuid4_generate, uuid_type, uuid_to_string, uuid_from_string, uuid_copy).
  uuid.h is C++-only upstream (uses the bare `uuid` tag without a typedef) and
  its Windows `uuid4_generate` only handled MSVC, so the vendored header was
  patched (added `typedef struct uuid uuid;`, `<stdbool.h>`, and a MinGW/
  `_WIN32` branch using the BCrypt RNG). `struct uuid` cannot yet be
  constructed from pure PenguScript (no fixed byte arrays), so the functions
  are verified with a C-level probe.
- **`std/minicoro.d.pengu`** — curated coroutine core: mco_create / destroy /
  resume / yield / status / running (current) / get_user_data /
  result_description plus the storage interface; state/result constants
  documented. Coroutine entry bodies need a C function pointer, which
  PenguScript weaves cannot supply yet, so the roundtrip is verified with a
  C-level probe against the compiled implementation.
- **`std/miniaudio.d.pengu`** — documented *small* subset meaningful without an
  audio device (version macros + `ma_version_string` / `ma_version`). Audio
  backend APIs are intentionally omitted and the 4 MB single-header
  implementation is not compiled into the runtime; see module header comment.
- **`std/rlights.d.pengu`** — curated subset of the vendored raylib-6 "RLG"
  lighting framework expressible with plain numbers/bools and the opaque
  `RLG_Context` handle (context, view position, parallax, light control,
  shadow knobs). Signatures passing raylib structs by value/ref are
  intentionally omitted (documented); no implementation archive is built.
- **`std/celeris.pengu`** — pure-PenguScript wrapper over `std/xxhash`
  (`hash32/hash64/hash3_64/hash3_128` + `*_seeded`). Documents that a
  PenguString *variable* cannot yet be passed where a C byte pointer is
  expected (codegen emits the PenguString struct, not its buffer), so data is
  given as `ref to char` plus an explicit byte `length`.

### Build integration (`build_runtime.py` / `libpengu_stb.a`)

- `SINGLE_HEADER_NAMES` extended so `xxhash.h`, `uuid.h`, `minicoro.h`,
  `miniaudio.h`, `raygui.h`, `rlights.h`, `tinyfiledialogs.h` and
  `tinyfd_moredialogs.h` are staged into `build/include/`.
- `build_pengu_stb` now compiles each implementation unit to its own object
  (`std_c/wrappers_xxhash.c`, `wrappers_uuid.c`, `wrappers_minicoro.c`,
  `wrappers_raygui.c`, plus the real `tinyfiledialogs.c` /
  `tinyfd_moredialogs.c` sources) so archive members stay independently
  linkable. xxhash uses `XXH_STATIC_LINKING_ONLY` + `XXH_IMPLEMENTATION` (this
  vendored header requires both); minicoro uses `MINICORO_IMPL`.
- Link probes (C) prove the archive symbols: xxhash canonical vectors,
  uuid4 generation/parse-back, minicoro create/resume/yield/resume/destroy
  roundtrip, `tinyfd_version` string print.

### Tests & docs

- `tests/test_std_c_libs.py` — semantic checks of every new binding + celeris,
  PenguScript compile+run tests for `std.xxhash` and `std.celeris`, and
  C-level run probes for uuid/minicoro/tinyfiledialogs; each skips cleanly
  when the matching archive member is missing.
- README "Third-Party Acknowledgments & Credits" extended with the vendored
  `std_c/` libraries (origin URLs + license notes); CHEATSHEET §30 tables and
  examples updated; completeness-gap report appended to
  `scratch/std_c_support_plan.md`.

## [0.8.2] - Unreleased

### Stdlib enrichment (grounded scope)

- **`std/archivum` recursive helpers (pure PenguScript)**: new `copy_tree`
  (iterative, whole-directory copy) and `list_files_recursive` (returns every
  file below a root), built on the existing C primitives; verified end-to-end
  (`tests/test_archivum_tree.py`).
- **Bindings for the remaining `std_c/` headers**: `stb_image_resize2.d.pengu`
  (`insignia stbir_`) and `stb_herringbone_wang_tile.d.pengu` (`insignia stbh_`)
  added via `pengu bind`; duplicate omen values deduplicated; both pass
  `pengu check`. Every header in `std_c/` now has a `.d.pengu` binding in
  `std/`.
- **Scope note**: the broader single-header/std-module expansion (std_/ folder,
  XLSX/YAML/TOML/WebSocket/audio/GUI modules, async FS/watch, etc.) cannot be
  implemented from this repository alone — those headers/libraries are not
  present. See the agent report for the concrete gap list and next steps.

## [0.8.1] - Unreleased

### Integrated external libraries (build_runtime.py)

- **New static libraries** produced by `build_runtime.py` into `build/lib/`
  (headers staged in `build/include/`, `--rebuild`-aware and idempotent):
  - `libsqlite3.a` — SQLite3 3.53.4 amalgamation (`-DSQLITE_THREADSAFE=0`,
    FTS5) with `sqlite3.h`/`sqlite3ext.h`.
  - `libraylib.a` — Raylib 6.0 desktop (`PLATFORM_DESKTOP`, OpenGL 3.3,
    GLFW via raylib's amalgamated `rglfw.c`) + full `src/` header set.
  - `libwebui.a` — WebUI 2.5.0-beta.3 installed from the official prebuilt
    mingw release asset (the in-repo sources target the MSVC UNICODE API set
    and do not compile with mingw); cached under `extern/`.
  - `libpengu_stb.a` — the STB single headers renamed to Latin in `std_c/`
    (`imago.h`, `scriptor.h`, `typis.h`, `pactum.h`, `datastructura.h`,
    `perlinum.h`) plus `nanosvg`/`nanosvgrast`, compiled once from
    `std_c/wrappers_stb.c` (`*_IMPLEMENTATION` units; `pactum` precedes
    `typis` for stb_truetype's rect-pack coupling).
- **Bindings**: `std/*.d.pengu` updated for the new names — `imago`,
  `scriptor`, `typis`, `pactum`, `datastructura`, `perlinum` (renamed and
  re-checked), `webui` include/links fixed (`include "webui.h"`, `link
  "webui"`), `sqlite3` and `raylib` verified; every binding passes
  `pengu check`.
- **Linking**: `pengu_project.py` auto-links any new `.a` found in `build/lib`
  and adds the Windows UI platform libs (`-lopengl32 -lgdi32 -lole32 -luuid
  -lshell32`).
- **Tests**: `tests/test_integrated_libs.py` — sqlite3 + imago end-to-end via
  the std bindings (compile+run), semantic checks of the remaining renamed
  bindings, WebUI and Raylib link checks (headless host: link-only).
- **Docs**: PENGU_BUILD §4, CHEATSHEET §30 "Integrated External Libraries",
  README notes updated.

## [0.8.0] - Unreleased

### `pengu bind` — C header to PenguScript bindings

- New CLI command `pengu bind <header.h>` that translates a C header into a
  `.d.pengu` declaration file (`pengu_bind.py`):
  - Preprocesses with the C preprocessor (retaining line markers so pycparser
    can attribute every node to its source file) using a vendored minimal stub
    include tree (`c_bind_stubs/`) — the Windows/SDK-guarded sections are
    excluded by undefining their guards (`-U_WIN32` etc.) so real-world headers
    stay parseable; `--no-cpp` and `--include-paths` are available for custom
    setups.
  - Maps C types to PenguScript (`size_t`→`size_t`, `bool`, fixed-width
    integers, `char*`/`const char*`→`ref to char`, `T*`→`ref to T`,
    `struct`→`rune`, `union`→`echo`, `enum`→`omen` with values, typedefs and
    function pointers → `alias … as ref to weave …`).
  - Emits, in order: `include`/`link` directives, numeric/string `#define`
    constants, type declarations (runes/echos/omens/aliases), the
    `insignia <prefix>` directive, then `declare` lines for every function
    (the prefix spelled by the header is stripped so `insignia` does not
    double it).
  - Attaches `##` documentation comments from the source header (Doxygen
    `/** … */`, `///`, `//`); `--no-comments` disables them.
  - `--prefix`, `--links`, `--output`, `--ignore`, `--include-paths` options.
- The generated file is a pure declaration file: the real C header stays
  `include`d, so no C structs/enums/prototypes are duplicated.
- **Tests**: `tests/test_pengu_bind.py` (type mapping, structs/enums/callbacks,
  constants, ignore patterns, insignia, comments) plus an end-to-end run over
  `CToPenguTest/webui.h` whose output passes the semantic checker.
- **Release packaging**: `make_release.py` installs `pycparser` in the build
  venv, adds `pycparser` (c_parser/c_lexer/c_ast/plyparser/ast_transforms) and
  `pengu_bind`/`pengu_lsp.*` to the PyInstaller hidden imports, and bundles
  `c_bind_stubs/` as an `--add-data` folder so `pengu bind` works inside the
  frozen `pengu.exe` (stub lookup also checks `sys._MEIPASS`).
  `requirements.txt` gained `pycparser>=2.21`.

## [0.7.1] - Unreleased

### Bug fix: module-member calls no longer degrade to `void`

- **Root cause**: `PenguChecker._resolve_call_target` resolved calls of the
  form `calling archivum.write_file` only by heuristically looking up the
  prefixed name (`archivum_write_file`) or the bare member name, and when both
  misses it silently returned `FnType(return_type=void)` for any member of an
  imported module. In typing flows where the bare member name is not present in
  the global registry (module collection registers imported members under the
  import-scope and prefixed names only), every typed call into an imported
  module inferred as `void` — producing spurious
  `E0020 "Returned value of type 'void' does not match weave return type ..."`
  diagnostics in the LSP / `pengu check`.
- **Fix** (`pengu_parser/pengu_infer.py`): module member calls now resolve
  against the import's `module_scope` first (the authoritative `FnType`
  signature), then fall back to the prefixed registry names; a genuinely
  missing member raises `E0004 "Module ... has no exported member ..."` instead
  of silently guessing `void`. The tolerant extern fallback is kept only for
  documents that actually declare C `include`s.
- **Tests**: `tests/test_lsp_return_types.py` covers typed returns
  (`bool`/`int`/`string`/`maybe int`/`void`) for same-file, forward-reference,
  stdlib-module-member, import-alias and local-module-member calls, plus a
  negative test asserting unknown members raise `E0004` (they previously
  produced the misleading void/E0020 behaviour).

## [0.7.0] - Unreleased

### CLI developer experience

- **Clearer C-compile errors**: `PenguBuilder.compile()` now raises a dedicated
  `CompileFailedError` carrying the exact compiler command, exit code and the
  full compiler stdout/stderr; the `pengu` CLI prints it formatted (no raw
  traceback) and exits with status 1.
- **`pengu check`**: parses and type-checks every module (respecting per-module
  `when main`) without generating any code — CI friendly. Reports one
  `file:line:col [CODE] message` per problem and exits non-zero on failure
  (`PenguBuilder.check_sources()`).
- **`pengu fmt`**: formats `.pengu` files/directories with the standard style
  (reuses the LSP formatter, extracted to `pengu_lsp/formatting.py`). Defaults
  to writing files; `--check` only reports and exits 1 when changes are needed;
  `--indent` / `--tabs` control indentation.
- **`pengu update`**: for every configured dependency, runs `git pull` (with the
  configured branch) and re-runs the dependency build script
  (`build.py` / `build.bat` / `build.sh` / `Makefile`); local copies are
  rebuilt in place (`_run_dependency_build` shared with `pengu add`).
- **`--cc` override** on `build`, `run`, `test` and `run <script>` wins over the
  compiler configured in `pengu.yaml`.
- **`--verbose`** on `build`/`run`/`test`/`check`/`update`/`fmt` prints the
  resolved module order, phase timings (semantic check / codegen), every C
  command executed and per-file progress.

### LSP developer experience

- **Contextual completion**: after `when` the editor suggests the compile-time
  variables `main`, `os`, `arch`, `compiler`, `defined(...)` (plus literals);
  after `as` / `into` it suggests every built-in type plus the project's runes,
  echos, omens, aliases, seals and generic runes; a `when` snippet was added.
- **Hover documentation fallback**: when a symbol carries no doc text yet,
  `##`/`#` doc comments directly above its declaration are extracted from the
  source file (`extract_doc_from_file`), so stdlib and cross-file definitions
  show documentation. Memory-size annotations were already present.
- **Code actions**: new `textDocument/codeAction` handler offering
  "Add missing import" when the cursor is on an undefined identifier — a cached
  symbol index (stdlib + project modules) maps the symbol to its module and the
  fix inserts `import …` at the top or after existing imports.
- Go-to-definition already resolves local symbols, imported-module members and
  stdlib files (e.g. `spark.println` → `std/spark.pengu`).

### Tests & docs

- New suites: `tests/test_cli_tools.py` (check/fmt/update/--cc/--verbose),
  `tests/test_lsp_context.py` (when/type completion contexts),
  `tests/test_lsp_code_actions.py` (add-missing-import) and
  `tests/test_lsp_hover_docs.py` (doc fallback). Full pytest suite green.
- CHEATSHEET §28 (CLI & LSP tooling) and README usage notes updated.

## [0.6.0] - Unreleased

### Standalone scripts (`when main`)

- **Compile-time `main` variable**: `main` is `true` when the module currently
  being compiled is the program entry point and `false` for every imported
  module. Combined with the existing `when` clauses it enables Python-style
  `if __name__ == "__main__"` behavior:

  ```pengu
  when main:
      weave main into int:
          calling saludar with "Mundo"
          return 0
  ```

- **Per-module environment**: the builder/checker/code generator now resolve the
  `main` flag separately for each source file (`pengu_comptime.CompileTimeEnv`
  gained `is_main`, `with_main()`, and `main` in `eval_comptime`; `PenguCodegen`
  gained `entry_main_mode`/`entry_file` with per-file flag application), so
  importing a module never activates its `when main:` blocks.
- **CLI**: `pengu run <archivo.pengu>` compiles and runs a standalone script
  with `main=true` (new `run_script` helper; artifacts under `build/`). Plain
  `pengu build`/`pengu run`/`pengu test` are unchanged and default to
  `main=false`; an explicit opt-in is available via `-D main` or `-D main=true`.
- **Reserved name**: declaring `var main` / `let main` / `static var main` /
  `const main` now reports `error[E0040]: 'main' is a reserved compile-time
  variable`. Defining the entry function `weave main ...` is unaffected.
- **Tests**: `tests/test_when_main.py` (9 tests) verifies codegen emission/drop
  of `when main` blocks, the `E0040` guard, direct-run vs import behavior of a
  real module (`tests/fixtures_when_main/`), default-off project builds, and the
  `pengu run <file>` CLI path end-to-end.
- **Docs**: CHEATSHEET gained Appendix C ("v0.6 Standalone Scripts
  (`when main`)"), §27; README usage notes updated.

## [0.5.0] - 2026-03-01

### Compiler extensions (stdlib-unblocking)

- **`some expr`**: keyword constructing a present `maybe T`; the value is heap-copied (`pengu_sigil_alloc` + `memcpy`) so it outlives the expression. Types as `MaybeType(element=T)` and is never constant-folded.
- **`ord expr`** / **`chr expr`**: byte-level access without parentheses. `ord` returns the byte code of a single-character string (string-literal length validated); `chr` builds a single-character string from an int in 0-255 (constant range validated). `pengu_string_from_char` in the runtime now allocates a heap copy (fixes a dangling-stack-pointer bug that made runtime `chr` empty).
- **`insignia` primitive-method exemption**: `insignia pengu_` prefixes module-level weaves/declares only; `enchanting` methods on primitive/collection types (`string`, `list`, `map`, `slice`, `maybe`, `result`) keep their plain C names, so `string.substring` can never collide with the runtime `pengu_string_substring` primitive.

### Stdlib migrations

- **`scrolls` fully pure**: `lower`, `upper`, `is_alpha`, `is_digit`, `is_alnum` now implemented in PenguScript via `ord`/`chr`; the remaining C primitives (`pengu_string_upper/lower/is_alpha/is_digit/is_alnum`) were removed from `pengu_runtime.h`. `std/scrolls.pengu` carries `insignia pengu_`.
- **`cipher` Base64 pure**: `encode_base64`/`decode_base64`/`is_base64` implemented in PenguScript (byte loops with `ord`/`chr`, `some`/`maybe none` for decoding); C implementations (`PENGU_B64_CHARS`, `pengu_c_cipher_encode_base64`, `pengu_b64_char_val`, `pengu_c_cipher_decode_base64`) removed from the header.
- **`ledger` fully pure (CSV/TSV)**: `escape_field`, `parse_line`, `parse_csv`, `to_csv_string`, `detect_delimiter`, TSV variants and `read_csv`/`write_csv`/`read_tsv`/`write_tsv` (file I/O via `std.archivum`) are now implemented in PenguScript; the whole C ledger block (`pengu_c_ledger_escape_field`, `_parse_line`, `_parse_csv`, `_generate_csv`, `_read_file`, `_write_file`, `_detect_delimiter`) was removed from `pengu_runtime.h`.
- **`cipher` fully pure (Base64 + JSON)**: JSON `parse_json`/`stringify_json`/`pretty_json`/`parse_value`/`stringify_value` and file helpers now use a PenguScript tokenizer (whitespace/string/escape/raw-token scanning) over the new `pengu_map_keys_string` runtime helper; the entire C JSON block (`pengu_json_skip_ws`, `pengu_json_parse_str`, `pengu_json_parse_val_str`, `pengu_c_cipher_parse_json`, `_stringify_json`, `_parse_value`, `_stringify_value`, `_pretty_json`) was removed from `pengu_runtime.h`.
- **`compass` fully pure (paths)**: `join`/`join_all`, `basename`, `dirname`, `ext`, `stem`, `suffixes`, `has_ext`/`has_suffix`, `normalize`, `parent`, `split`, `is_absolute`/`is_relative`, `is_root`, `drive`, `separator`/`alt_separator`, `change_ext`, `add_ext`, `relative_to` and every `Path` method are now implemented in PenguScript (internal `cp_*` helpers over string slicing/`ord`/`chr`, with platform semantics selected by `when os == "windows"`); the entire C path section (`pengu_c_path_is_sep` ... `pengu_c_path_relative_to`, ~470 lines) was removed from `pengu_runtime.h`. `precis` (MIME by extension) and the `compass` stdlib test remain green.
- **Compiler fix**: codegen field access now prefers the live local-variable type over (possibly stale/leaked) global symbols when resolving `.value`/fields, so `maybe`-deref on locals whose names were previously seen as parameters elsewhere works reliably.
- **Tests**: `tests/test_feature_some_ord_chr.py` added; `test_runtime_h.py` updated to assert the runtime header no longer defines the migrated string/Base64/JSON/path helpers.

## [0.4.0] - 2026-02-20

### Standard Library Reorganization (runtime -> PenguScript)

- **String utilities migrated out of the C runtime**:
  - Removed the `scrolls_len` ... `scrolls_reverse` block from `pengu_runtime.h`; those 19 functions are no longer implemented in C.
  - `std/scrolls.pengu` now implements the string API in pure PenguScript: `contains`, `starts_with`, `ends_with`, `index_of`, `last_index_of`, `substring`, `char_at`, `trim`/`trim_start`/`trim_end`, `replace`, `replace_all` (now a true global replacement), `split`, `repeat`, `reverse` - built on compiler string slicing/indexing and the retained primitives (`pengu_string_substring`, `pengu_string_char_at`, concat, equality).
  - Only byte-level ASCII case conversion and classification (`lower`, `upper`, `is_alpha`, `is_digit`, `is_alnum`) remain as declared C primitives.
- **Compiler string operations** (enablers for the migration):
  - `s at a to b` on strings now emits `pengu_string_substring(...)` (was invalid C).
  - `s at i` on strings now emits `pengu_string_char_at(...)`.
  - `for c in s` iterates a string character by character (single-char `PenguString` values).
  - Fixed `judge` string pattern emission (`pengu_string_equals` -> `pengu_string_equal`).
- **Fixes found during migration**:
  - `pengu_symbols.py` now imports `ConceptType`/`SealType` (previously raised `NameError` at runtime).
  - `PenguCodegen._infer_node_type` now seeds the temporary symbol table correctly.
- **`arithmancy` integer helpers migrated**: `is_prime`, `gcd`, `lcm` removed from `pengu_runtime.h` and reimplemented in `std/arithmancy.pengu` (pure PenguScript, Euclid/6k±1 algorithms), removing their C definitions (`pengu_c_is_prime`/`pengu_c_gcd`/`pengu_c_lcm`).
- **Tests**: full pytest suite green (353 tests), including `tests_std/*.pengu` compiled with GCC via `test_stdlib.py`.
- **Documentation**: CHEATSHEET §23 now describes the stdlib architecture (PenguScript modules over declared C primitives / external-library backends).

## [0.3.0] - 2026-01-30

### Language & Compiler

- **Indexed iteration (`for i, item in collection`)**:
  - Added two-binding `for` loops: index (`int`, immutable) plus element, with `_` discard support (`for i, _ in col`, `for _, v in col`); the classic single-binding `for v in col` is unchanged.
  - Generated C keeps the requested index identifier as the loop counter (`for (int32_t i = 0; i < N; i++) { Elem v = (col)[i]; ... }`); element/index type checking handled in `_check_for_in_stmt`.
- **Map literals (`{ key: value, ... }`)**:
  - Added `{ "Alice": 100, "Bob": 90 }`, identifier keys (`host: "localhost"` -> string keys), and `and`/`,` separators.
  - Keys unify to `string`; values must share one type (int/float/string unification); empty maps require an explicit `as map of K to V` annotation; duplicate keys are rejected (`E0038`).
  - Codegen emits `pengu_map_new(sizeof(K), sizeof(V))` plus one `pengu_map_put` per entry.
- **Import aliases (`import path as name`)**:
  - Added `import std.spark as sp`; the alias becomes the module symbol (`kind="import"`); members resolve as `alias.export`. Aliases must not be `_` or collide with existing symbols (`E0036`). Generated C names are unaffected by the alias.
- **Compile-time conditionals (`when`)**:
  - Top-level, statement-level and expression (`when c then a else b`) forms; the inactive branch is syntax-checked but discarded (no codegen, no symbols).
  - New compile-time environment (`pengu_parser/pengu_comptime.py`) exposing `os`, `arch`, `compiler` and `defined(NAME)`, overridable via `-D NAME` / `-D os=linux` etc.
  - Non-constant `when` conditions are rejected (`E0039`); `when` blocks splice textually at statement level.
- **Integrated unit tests (`test ...:` blocks)**:
  - Added top-level `test "name":` / `test name:` blocks; semantically validated as `void` functions in every build; `.d.pengu` files reject them (`E0025`).
  - Normal builds ignore tests; `--test` emits `static void pengu_test_N(void)`, a `pengu_run_tests()` runner and a test `main`.
  - New CLI: `pengu test`, `pengu build --test`, `pengu run --test`.
- **String-valued omens**:
  - `omen Color with string:` auto-assigns each variant its name as a string value; explicit `Variant is "value"` strings are also supported.
  - Integer/string value mixing is rejected (`E0029`); payload variants are forbidden in string mode; string omens generate `#define Color_Red pengu_string_from_cstr("Red")` macros instead of enums, and variant references type as `string`.
- **Function-static variables (`static var`)**:
  - Added `static var` inside function bodies: mutable, initialized once, persists between calls; top-level, nested-block and array statics are rejected (`E0035`).
  - Codegen emits `static int32_t count = 0;` for constant scalars and a first-call `_initialized` guard for non-constant initializers.
- **`##` doc comments now lex**:
  - Single-line (`## text`), self-closed (`## text ##`) and multi-line (`##` ... `##`) documentation comments are supported by the lexer while preserving source line numbers.

### Tooling & Docs

- **`pengu doc`**: new subcommand generating a Markdown reference site (per-module pages + `index.md`) from `##` docs and inferred signatures (`pengu_doc.py`).
- **`-D` defines** on `pengu build`/`run`/`test` feed the compile-time `when` environment (plain `-D NAME` sets `defined(NAME)`; `-D os=...`, `-D arch=...`, `-D compiler=...` override context variables; project/`cc` config is honored too).
- **Tests**: `tests/test_feature_indexed_for.py`, `test_feature_map_literals.py`, `test_feature_import_alias.py`, `test_feature_when.py`, `test_feature_string_omens.py`, `test_feature_static_var.py`, `test_feature_tests.py`, `test_features_e2e.py` (GCC compile+run gates), `test_pengu_doc.py`.
- **CHEATSHEET.md**: new "25. Appendix A: v0.3 Language Extensions" section covering every feature with examples and generated C.
- **VSCode extension**: keywords (`when`, `test`, `static`, `omen ... with string`, `defined`) added to syntax highlighting; snippets for `test`, `when`, `static var`, map literal and `import ... as`; `pengu doc`/`pengu test` documented in the extension README.

## [Unreleased]

- **Type System Enhancements (`concept`, `bind`, `seal`, `ritual`, `where`)**:
  - **Concepts (Traits & Interfaces - `concept`)**:
    - Added `concept` declarations to define method contracts with required parameter and return types.
    - Supported both instance methods and static `ritual` methods within concepts.
    - Added generic concepts with type parameters (`concept Sharded shard T:`).
  - **Concept Implementations (`bind ... with ...`)**:
    - Added `bind Type with Concept:` syntax to associate concepts with runes and types.
    - Enforces full implementation of all concept methods; emits `UnimplementedConceptMethodError` (`E0031`) if any method is missing.
    - Validates method signatures and parameter counts; emits `ConceptMethodMismatchError` (`E0030`) on signature mismatch.
  - **Distinct Types & Nominal Newtypes (`seal ... as ...`)**:
    - Added `seal NominalName as UnderlyingType` declarations creating zero-overhead distinct types.
    - Enforces strict type separation to prevent accidental assignments across different seals or between seal and underlying type without explicit `to` cast; emits `SealTypeMismatchError` (`E0035`).
    - Generates corresponding C `typedef UnderlyingType NominalName;` in `bundle.c`.
  - **Static & Factory Methods (`ritual`)**:
    - Added `ritual` modifier for methods declared inside `enchanting` blocks or `concept`/`bind` blocks.
    - Ritual methods do not receive a `self` instance parameter and are called statically on the type name (e.g. `calling Vec2.zero`).
    - Enforces safety: prevents accessing `self` inside a ritual method (`InvalidRitualSelfAccessError` / `E0033`) and prevents calling a ritual method on an instance (`InvalidRitualCallError` / `E0034`).
    - Codegen emits clean C functions without `self` pointer parameters.
  - **Generic Constraints (`where`)**:
    - Added `where <Param>: <Concept>` clause to generic functions, methods, runes, and concepts.
    - Validates that generic type arguments satisfy all declared concept bounds upon specialization/monomorphization; emits `ConceptBoundNotSatisfiedError` (`E0032`) if unfulfilled.
    - Allows method calls on generic type parameters (`calling item.print_me`) backed by concept bounds.
  - **Test Suite & Documentation**:
    - Added comprehensive unit and semantic tests in `tests/test_type_system_enhancements.py`.
    - Documented all 5 features with PenguScript examples and translated C code in `CHEATSHEET.md` Sections 8, 10, 11, and 13.

- **Null Pointer Literal (`null`)**:
  - Added the `null` literal for safe null pointer representation in C FFI interoperability and raw references.
  - Implemented `NullType` (and `NULL_TYPE` singleton), compatible strictly with reference types (`ref to T`), `opaque` types, and `any`.
  - Type safety rules: forbids assigning `null` to value types (`int`, `string`, `bool`, `rune`, etc.), emitting `TypeMismatchError` (`E0005`).
  - Requires explicit type annotations on declarations initialized with `null` (e.g. `var ptr as ref to int is null`), emitting `E0014` if omitted.
  - Supports equality and inequality comparisons (`==`, `!=`) against references, opaque handles, and `null`, rejecting non-pointer comparisons and ordering comparisons (`<`, `<=`, `>`, `>=`).
  - Memory safety: forbids taking address of `null` (`sigil of null`), emitting `E0008`.
  - Translates `null` expressions to standard C `NULL` in generated `bundle.c`.
  - Comprehensive unit test suite in `tests/test_null.py`.
  - Updated TextMate syntax highlighting for VSCode and documented in `CHEATSHEET.md` Section 20.

- **Explicit Values & Auto-Increment for `omen` Enums**:
  - Added support for assigning compile-time integer constant values to simple `omen` enum variants using `Variant is <expr>`.
  - Added automatic increment rules: default starts at `0` for unassigned first variants, and unassigned variants following an explicit value continue with `previous + 1`.
  - Added semantic validation enforcing integer types (evaluated with `ConstFolder`) and emitting compile error `E0029` (`InvalidOmenConstantValueError`) for non-integer or non-constant values.
  - Added duplicate value detection across all variants in an `omen`, emitting compile error `E0027` (`DuplicateOmenValueError`).
  - Added payload restriction forbidding `is <expr>` assignments on algebraic variants with payload (`with`), emitting compile error `E0028` (`InvalidOmenPayloadValueError`).
  - Updated C code generator to emit explicit `= <val>` expressions in `typedef enum Name { ... } Name;` C declarations.
  - Comprehensive unit test suite in `tests/test_omen_values.py`.
  - Documented in `CHEATSHEET.md` Section 9.

- **Insignia Module Prefix Directive (`insignia`)**:
  - Added the `insignia <PREFIX>` top-level directive in modules and declaration files to define a global C identifier prefix for subsequent declarations.
  - Automatically prepends prefix to generated C function names (`declare`, `weave`), struct/union/enum types (`rune`, `echo`, `omen`, `alias`), constants (`const`), and `enchanting` methods.
  - Keeps PenguScript call syntax clean without prefix (e.g. `webui.new_window` translates to `webui_new_window()`).
  - Position-dependent: declarations prior to `insignia` remain unprefixed.
  - Restricts modules to at most one `insignia` directive, emitting compile error `E0026` (`MultipleInsigniaError`) on duplicates.
  - Comprehensive unit and integration test suite in `tests/test_insignia.py`.
  - Documented in `CHEATSHEET.md` Section 3.

- **Declaration Files Support (`.d.pengu`)**:
  - Added support for TypeScript-like declaration files (`.d.pengu`) containing type definitions (`rune`, `echo`, `omen`, `alias`, `seal`, `concept`), linker flags (`link`), C includes (`include`), and external function declarations (`declare`).
  - Strict validation forbidding function implementation bodies (`weave`): emits compile error `E0025` (`"Implementation body not allowed in declaration file (.d.pengu)"`).
  - Import resolution (`find_module_path`) resolves `.d.pengu` files when importing modules, with priority given to `.pengu` implementation files when both exist.
  - Code generator suppresses C code emission (forward declarations, struct/union/enum/typedef definitions, `#define` constants, and `declare` prototypes) for declarations originating in `.d.pengu` files to prevent redefinition conflicts with included native C headers, while preserving full symbol and type information for semantic checking, LSP, and function call translation.
  - Comprehensive unit and integration test suite in `tests/test_declaration_files.py`.
  - Documented `.d.pengu` declaration files in `CHEATSHEET.md`.

- **Context-Aware String Literals for `ref to char` (`const char*`)**:
  - String literals assigned to `ref to char` (`const char*` / `char*`) variables, struct fields, or passed to function parameters expecting `ref to char` are now emitted directly as C string literals (`"..."`) without wrapping in `pengu_string_from_cstr`.
  - Type inference and semantic checker validate string literals against expected `ref to char` types.
  - String interpolation (`{expr}`) within string literals assigned or passed where `ref to char` is expected raises a compile-time `SemanticError`.
  - Full support for `ref to char` fields in struct/rune initializers (`with ...`).
  - Unit and integration tests in `tests/test_ref_char_literals.py`.

