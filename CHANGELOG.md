# Changelog

All notable changes to PenguScript will be documented in this file.

## [0.10.0] - Unreleased

### Fixed (production criticals)

The three production-critical defects identified in `PRODUCTION_READINESS.md` §9.3 (C1, C2, C3) are resolved, with comprehensive test coverage in `tests/test_p3_criticals.py`:

- **C1: Bare module-qualified binding variants (`module.VARIANT`).** Referencing constants and omen variants from C bindings using the bare module-qualified spelling (e.g. `raylib.FLAG_MSAA_4X_HINT`, `raylib.KEY_RIGHT`, `raylib.SHADER_UNIFORM_FLOAT`) previously emitted an invalid prefixed C identifier (`raylib_FLAG_MSAA_4X_HINT`), failing at C compilation time. The code generator now resolves these to the clean, unprefixed C identifiers defined by the native header, while keeping user-defined PenguScript omen variants properly prefixed (`Color_Rojo`).
- **C2: String interpolation diagnostics for non-PenguScript text (`{...}`).** Embedding text containing curly braces (such as GLSL/HLSL shader source or regexes) in normal strings previously failed with a generic `E0000` syntax error pointing at line 1 column 3 of the interpolated snippet. The type inferrer now reports `E0019` against the actual string literal location with clear context and explicit `help:` pointing to raw strings (`r"..."` or `r"""..."""`), where curly braces and escape characters are preserved verbatim.
- **C3: Dropped unconditional `restrict` from generated parameters and `self`.** Function parameter prototypes and definitions generated for `ref to T` and `self` previously emitted `T* restrict`, introducing undefined behavior under optimization (`-O2`) for APIs that alias or overlap buffers in-place. Generated C now emits standard pointers (`T* self`, `T* p`), guaranteeing aliasing safety. The mapper retains `restrict=True` as an explicit opt-in mechanism (`CTypeMapper.to_c_decl`).

### CI/CD and Cross-Platform Test Hardening

- **Automated Tagging and GitHub Release**: Enhanced GitHub Actions CI workflow (`.github/workflows/ci.yml`) to automatically parse release notes, title, and version from `CHANGELOG.md` upon successful test completion across all platforms (Windows, Linux, macOS), creating the Git tag and publishing a GitHub Release with platform binaries (`.zip`, `.tar.gz`) and the VS Code extension (`.vsix`).
- **Cross-Platform Raylib Test Guards**: Added `@requires_lib("raylib")` annotations to compile-and-run tests in `tests/test_p3_criticals.py` while keeping pure codegen verification enabled unconditionally across all platforms, resolving linker failures on POSIX CI runners where Raylib compilation is optional/best-effort.
- **Headless OpenGL Environment Tolerance**: Added `rl.IsWindowReady()` check to `test_rlgl_coexistence_with_raylib` in `tests/test_p2_features.py`, preventing GLFW initialization crashes on headless CI runners lacking hardware OpenGL contexts.
- **Release Smoke Test Argument Separator**: Fixed outdated pre-0.10.0 syntax in `make_release.py` where the smoke test used `and` instead of `,` as an argument separator in `calling ward.assert_eq_int with 40 + 2, 42`, which triggered `E0005: Ambiguous 'and' after a call with arguments` during the post-packaging verification step on all platforms.

### P0 toolchain hardening (production hygiene)

The five items the readiness assessment (`PRODUCTION_READINESS.md` §7, P0) called
out as "what makes everything else debuggable" are done, with regression tests in
`tests/test_p0_toolchain.py` (23 tests):

- **`weave main`'s value is the process exit status.** The generated wrapper used
  to call `pengu_main();` and `return 0`, so every program exited 0 and CI could
  not detect a failure. It now emits
  `int pengu_status = (int)pengu_main(); … return pengu_status;`, widening any
  integer return type (`u8`, `bool`, `i64`, …) and using `0` for `weave main into
  void`. `pengu run` already forwarded the child's status, so the chain is now
  end to end.
- **Generated C carries `#line` directives.** Every statement in a function body
  and every function definition is preceded by
  `#line <n> "<relative .pengu path>"`, so a gcc/clang diagnostic names the file
  and line the user wrote instead of `build/bundle.c`. Compiler-generated
  sections (lambda trampolines, entry wrapper, test runner) are reset with
  `#line 1 "bundle.c"`. Markers are deliberately **not** emitted inside
  expression contexts, where the C is a GCC statement expression that may become
  the argument of the function-like macro `pengu_to_string(x)` (a directive there
  would break the macro invocation).
- **The build cache keys on content, not mtimes.** `build/` is shared by every
  program built in a directory, and the cache compared mtimes against
  `build/bundle.c`, so a *different* program's older bundle could look "up to
  date" and its binary was shipped. The cache key is now
  `<config hash> <sources fingerprint>` in `build/.bundle_hash`, where the
  fingerprint covers the resolved entry path, every module's relative path and
  content and the project C sources; single-token (legacy) hash files are treated
  as stale. `compile()` additionally requires the artifact to be newer than the
  bundle, and identical content with a bumped mtime still counts as cached (so
  `touch` no longer forces a rebuild).
- **Program arguments reach the runtime.** The entry wrapper calls
  `pengu_init(argc, argv)` (and so does the test runner), so
  `rites.get_argc()` / `get_argv()` / `get_args()` return the real arguments
  instead of 0/empty.
- **One version, everywhere.** `VERSION` is the single source of truth, read by
  the new `pengu_version.py` (`__version__`, `__version_tag__`, fallback constant
  and `read_version_file()`). The CLI banner and the generated-C banner take the
  value from there, a new `pengu --version` / `-V` flag reports it,
  `make_release.py` now syncs the VS Code extension manifest from `VERSION`
  before packaging, and the places that used to spell a stale number (grammar
   docstring, runtime header, README badge, extension `package.json`) no longer
   claim one. `tests/test_p0_toolchain.py::TestVersion` fails if any of them drift.

### P1 — Unblock the raylib corpus

The five items identified in `PRODUCTION_READINESS.md` §7 (P1) to unlock ≈92% of the
raylib corpus:

- **P1.3 Fixed array length (`(xs length)`).** Codegen now checks the semantic
  type of array expressions and emits their declared compile-time size as an
  integer literal instead of invalid `.len` member accesses.
- **P1.2 Struct arrays and index assignment without spurious `E0011`.** Struct
  signatures in struct-initialization expressions are deduplicated by member
  fingerprint, element types propagate through array literals and assignment
  targets, and indexed field paths (`cs at 1 . x`) infer accurately.
- **P1.1 C varargs support (`...` in `declare`).** Added terminal `VARARGS` and
  `CVarArgsType` to grammar, checker, and inferrer. In C function calls, arguments
  matching the C varargs ellipsis are emitted directly without `PenguSlice` wrappers
  or argument type checks. `pengu_bind` automatically emits `...` for C ellipsis
  parameters, unblocking `raylib.TextFormat`, `raylib.TraceLog`, `sqlite3.mprintf`, etc.
- **P1.5 Pointer indexing (`p at i`) & generic slice bridge.** Inferrer and
  checker now permit indexing typed pointers (`RefType`), preserving `frozen`
  read-only qualifications and rejecting void/opaque pointers with actionable guidance.
  Array arguments decay to pointers for `RefType` parameters. Added generic
  `ffi.slice_from_ptr shard T with data as ref to void, count as int into slice of T`
  backed by `pengu_ffi_slice_raw` in the runtime.
- **P1.4 `raymath` C shim and std binding.** Added non-inline C wrapper library
  `libpengu_raymath.a` and header `pengu_raymath.h` wrapping all 146 inline functions
  from `raymath.h` with `pengu_rm_` symbols, integrated into `build_runtime.py`,
  and generated the full declaration binding `std/raymath.d.pengu`.

#### `at` index expressions: assignment targets now agree with reads (audit follow-up)

`at` is a **postfix** operator (CHEATSHEET §6.1), so `xs at i + 1` is
`(xs at i) + 1` and a computed index is written `xs at (i + 1)`. Reads already
behaved that way, but the *target* grammar accepted an additive expression, so
`set xs at n - 1 is v` wrote to index `n-1` while the equivalent read computed
`(xs at n) - 1` — one spelling, two meanings, and the reading one can index out of
bounds. Both positions are now postfix, which means:

- `set xs at (n - 1) is v` is the (always correct) spelling for a computed index;
- `set xs at n - 1 is v` is a syntax error with a dedicated `E0000` hint
  ("The index after 'at' binds tighter than '-': parenthesise the index
  expression") instead of a bare parse failure;
- pinned by `tests/test_p1_features.py::TestAtIndexSemantics` (5 tests), and
  documented in `CHEATSHEET.md` §6.1.

### P2 — Breadth and safety (`PRODUCTION_READINESS.md` §7, P2)

The six "breadth" items, with regression tests in `tests/test_p2_features.py` (34 tests):

- **P2.2 — Multidimensional arrays.** `array of array of T with size M with size N`
  now maps to C `T[M][N]` (outer dimension first) instead of the invalid
  `T[M][None]` the previous codegen produced; the inner dimension is inferred from
  the initializer rows when omitted, and a missing/unknowable dimension is a
  semantic error (`E0015`, `UnknownArrayDimensionError`) rather than a leaked
  `None` in the generated C. Ragged literals are rejected (`E0041`), row length
  (`((m at 0) length)`) emits the inner size, 2-D values decay correctly when
  passed to a C parameter (`T (*)[N]`), and the syntax is documented in
  `CHEATSHEET.md`.
- **P2.4 — Explicit release for `string` / `list` / `map`.** `banish` now accepts
  `string`, `list of T` and `map of K to V` lvalues in addition to `ref to T`,
  emitting `pengu_banish_string` / `pengu_banish_list` / `pengu_banish_map`
  (the runtime already had them; nothing could call them from PenguScript
  before). Literals, temporaries, `const` and `frozen` targets stay `E0008`, and
  `defer banish x` works. Ownership semantics documented in `LANGUAGE.md` and
  `CHEATSHEET.md` (including that `pengu_banish_map` releases string keys/values).
- **P2.3 — Module state idiom.** Top-level `var` remains `E0002` **by design**;
  the two supported patterns are now documented (private `static var` behind
  accessor weaves, and an explicit context struct passed by `ref`), the `E0002`
  message suggests them, and a two-module executable test proves the state is
  per-module and persists across calls.
- **P2.1 — `rlgl` binding.** `std/rlgl.d.pengu` is generated (163 `declare`s,
  122 `const`s, 11 `omen`s, rlgl's own `rlDrawCall`/`rlVertexBuffer`/`rlRenderBatch`
  runes), imports `std.raylib` instead of redeclaring raylib's types, links
  `raylib`, and coexists with `std.raylib` in one program. A sixth ported example
  (`scratch/port/06_rlgl_solar_system.pengu`) builds and runs.
- **P2.5 — Strict pointer typing.** A pointer is only compatible with another
  pointer when its **pointee** matches: `_same_pointee` unwraps aliases/`frozen`
  and compares exactly (with `char` ↔ `byte` as the documented C
  `char*`/`uint8_t*` equivalence, so `bytes of s` keeps working, and
  `void`/`opaque` as the wildcard). This closes the hole where
  `ref to i32` was accepted for a `ref to char` parameter — and where an
  `array of i32` decayed to `ref to char` — with no diagnostic. Numeric widening
  of *values* (`int` → `i64`) is unchanged; `frozen` stays one-directional.
- **P2.6 — `pengu bind` on real headers.** New flags (`--define/-D`,
  `--cpp-flags`, `--system-includes`, `--preprocessed FILE.i`,
  `--no-blank-extensions`), GNU-extension blanking enabled by default, new stubs
  (`pthread.h`, `unistd.h`, `limits.h`, `fcntl.h`, `sys/types.h`, documented in
  `c_bind_stubs/README.md`) and actionable failure diagnostics that name the
  offending construct and the flag to try. `zlib.h` (with `--define Z_SOLO`) is the
  first third-party header that used to fail and now binds end to end, and
  `sqlite3.h` / `rlgl.h` are covered as regressions.

#### Audit follow-ups (P2 review)

- **Generated names are kept verbatim.** The generator was sanitizing every
  struct member and parameter whose name is a language keyword or type name
  (`type` → `_type`, `size` → `_size`, `opaque` → `_opaque`). That silently
  blocked regeneration of `std/nanosvg.d.pengu` and `std/typis.d.pengu` (both use
  such member names) and changed the generated API for no compile-time gain: no
  parameter name breaks a `declare` signature, and no member name breaks a
  `rune`. The policy is now evidence-based — members are never renamed, `declare`
  parameters keep their C name (only `self`/`type` are quoted), and **callback
  aliases** (whose grammar *does* reject type-like parameter names, e.g.
  `with opaque as voidpf`) sanitize exactly that class (`opaque`, `void`, `int`,
  the fixed-width type names, `null`). Covered by
  `tests/test_p2_features.py::TestPenguBind` (`…names_are_kept_verbatim`,
  `…callback_alias_sanitizes_type_like_parameter_names`) and verified by
  `regen_std_bindings.py --check` (13 tool-produced bindings identical, incl.
  nanosvg and typis).
- **`std/rlgl.d.pengu` explains its hand edit.** `rlgl.h` does not
  `#include "raylib.h"` (it expects the includer to have done so), so the
  generator cannot see the dependency and would emit a duplicate `Matrix` rune;
  the binding's `import std.raylib` is therefore added by hand and the file now
  documents that, why `regen_std_bindings.py` skips it, and how to regenerate it.
- **`bind` CLI-flag test fixed**: it asserted a `no_blank_extensions` namespace
  attribute while the flag is (correctly) `--no-blank-extensions` with
  `dest="blank_extensions"` and `store_false`; a default-value test was added too.

### Added

- **`frozen` type qualifier (C's `const`).** `frozen T` emits `const T`,
  `ref to frozen T` emits `const T*`, and `frozen ref to T` is sugar that
  normalises to `ref to frozen T` (the qualification always lands on the
  pointee; `T* const` is what `let` already expresses). It is orthogonal to
  `let`/`var`, has the same size and layout as its target and is usable as the
  target inside expressions — only writing is restricted, in the C direction:
  a mutable value flows into `frozen` (`int` → `frozen int`), the reverse is
  `E0005`, and `set` through a frozen value or frozen pointee is `E0006`.
  This is what makes C signatures carrying `const` expressible, e.g. `qsort`:

  ```pengu
  declare qsort with base as ref to void, nmemb as usize, size as usize, compar as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void

  weave compare_ints with a as ref to frozen void, b as ref to frozen void into int:
      let xa is essence of (transmute a to ref to frozen int)
      ...
  ```

  emits `int32_t compare_ints(const void* restrict a, const void* restrict b)`
  and `qsort(xs, 3, sizeof(int32_t), ((int32_t (*)(const void*, const void*))compare_ints))`,
  which GCC 14+ accepts (before, the callback was spelled `void*` and rejected
  for differing qualifiers). See LANGUAGE §9.5.
- **`frozen` is a soft keyword.** It is a plain string literal in the grammar,
  so Lark's contextual lexer only prefers it where a type may start; identifiers
  named `frozen` (variables, fields, weaves, modules) keep working — verified by
  tests, and there were no such identifiers in `std/` or `tests/`.
- **Arrays decay to pointers where a reference is expected.**
  `calling qsort with xs, 3, …` now type-checks (`array of T` → `ref to T`,
  `ref to void`, `ref to frozen void`), matching C's array-to-pointer decay;
  the element type must still be compatible.

### Fixed

- **C callbacks with `const`-qualified parameters now compile under GCC 14+**
  when the binding is written with `ref to frozen void` (`qsort` and friends).
  The argument check also no longer accepts the reverse compatibility direction
  when it would silently discard a `frozen` qualification, so
  `ref to frozen int` → `ref to int` is `E0005` as in C.
- **`frozen` writes are rejected** (`E0006`): `set` on a `frozen`-typed binding,
  and any `set` that writes *through* a frozen pointee (`set p->field is …`
  where `p as ref to frozen T`). Rebinding a `ref to frozen T` pointer itself
  stays allowed, because the qualification is on the pointee.
- **`ref to frozen void` (C's `const void*`) keeps C's wildcard behaviour.**
  The bindings spell `const void*` as `ref to frozen void`, but only a literal
  `ref to (frozen) void` argument was accepted, so
  `calling UpdateTexture with …, sigil of pixels` and
  `calling xxhash.XXH64 with "PenguScript", 11, 0` failed with `E0005`. As in C,
  a pointer target is now the same catch-all for both spellings: any `T*`
  (mutable or frozen) converts to `void*` and `const void*` in one direction
  (`frozen T*` → `T*` stays `E0005`), arrays still decay, and a string *literal*
  converts too — `char*` → `const void*` — emitting a C literal rather than a
  Pengu string object (`string_lit` and `_is_ref_char_type` look through
  `frozen`/aliases and list `void` next to `char`).
- **`std_c/rlights.h` restored.** The tracked header was missing from the
  working tree (reported by `git status` as deleted), which breaks
  `build_runtime.py`'s `SINGLE_HEADER_NAMES` staging step; it was restored from
  `HEAD`, so `std/rlights.d.pengu`'s `std_c/rlights.h` reference is accurate
  again.

- **Logical operators `and` / `or` (boolean, short-circuit).** New
  `bool_or_expr` / `bool_and_expr` levels sit between `try` and `comparison`
  (`or` looser than `and`), so `if a > 0 and b > 0:` and
  `let ok is (p and q) or not r` work. Operands must be `bool` (`E0005`
  otherwise, with a hint to use `&`/`|` for bitwise); codegen emits `&&`/`||`,
  `ConstFolder` folds constant operands and `eval_comptime` evaluates them with
  short-circuit (the right operand is only evaluated when needed).

  > **Implementation note (maintainers).** A plain `"or"`/`"and"` literal would
  > have created a shift/reduce conflict at the `or` token against the existing
  > `or else` / `or return` / `or:` chain, which LALR(1) cannot resolve (it would
  > need two tokens of lookahead) — resolving it as shift silently broke
  > `a or else b` / `a or:`. The operators are therefore **separate terminals**:
  > `_BOOL_OR.3: /or\b(?!\s*(else|return|:))/`, `_BOOL_AND.2: /and\b/`, plus
  > `_AND_SEP.5: "and"` for the separator sites that survive (type/name lists).
  > The negative lookahead keeps the unwrap forms on the plain `OR` token, the
  > priority keeps the boolean operators from being shadowed where both are
  > expected, and the leading underscore keeps all three out of the AST (so
  > `bool_and`/`bool_or` nodes have exactly two children).
- **Compound assignment: `set x += 1`** and the other nine operators
  (`-= *= /= %= &= |= ^= <<= >>=`), as a new `compound_set_stmt` alternative of
  `set_stmt` (plus the one-line `compound_set_simple`, wired through
  `SIMPLE_STMT_ALIASES`). The checker reuses the whole `set` target validation
  (mutability, `with_target`, `essence_target`, private fields, `self->`) and
  adds per-operator type rules: `+=` on a string requires a string (and lowers to
  `pengu_string_concat`), the arithmetic operators require numerics, the
  bitwise/shift operators require integers.
- **Lambda expressions with explicit parameter types:**
  `lambda into 42`, `lambda x as int into x * 2`,
  `lambda a as int, b as int into x + y`. Parameters are typed (the language is
  static), the return type is inferred from the body, and there is **no
  capture** — a body only sees its parameters and module-level symbols. That
  lets codegen emit **one top-level `static` C function per lambda**
  (`_pengu_lambda_N`, between the prototypes and the definitions), so the result
  is portable C99 with no GCC nested functions. A lambda value has a
  `weave … into …` (`FnType`) type: it can be bound with or without that
  annotation, passed as a callback argument and called through
  (`calling f with v`). Lambdas are runtime-only (not usable in
  `when`/`defined`).
- **Variable declarations of function-pointer type now emit a valid
  declarator.** `var f is lambda …` (or any `FnType`-valued `var`/`let`/
  `static var`) used to emit `int32_t (*)(int32_t) f = …;` — invalid C. They now
  emit `int32_t (*f)(int32_t) = …;` via `CTypeMapper.to_c_decl`.
- **Block-shaped values are no longer constant-folded.** `ConstFolder.fold` used
  to recurse into a single-child node and replace it with a constant, so
  `lambda into 42` compiled to the literal `42` (invalid initializer) and a
  one-statement `do:`/value-position `if`/loop could be reduced away, dropping
  behaviour. Those rules now return "not constant".
- **Friendly `E0000` syntax errors (no more raw Lark traceback).** Every Lark
  syntax exception raised while parsing a module is now converted to
  `ParseError` (a `SemanticError` subclass, code `E0000`), carrying the line, the
  column, the offending snippet and the usual `help`/`note`. When the parser
  actually fails *on* an `and` that used to be a separator, the message explains
  the 0.10.0 change, points at that token and suggests `,` — e.g.
  `[E0000] 'and' is no longer a separator: use ',' (offending 'and' at line 2,
  column 33)`. The hint is only used when the error lands on the `and` itself, so
  an unrelated error on the same line is reported as a plain syntax error.
  `pengu check` also wraps import resolution, so a syntax error inside an
  imported module is reported the same way instead of escaping as a traceback.
- **`is present` / `is not present` validate their operand.** The checker used to
  accept any operand and emit `pengu_maybe_is_present(&(expr))` regardless, which
  read a presence flag out of whatever type was there and failed in C. The
  operand must now be `maybe T` (unresolved generics and `any` are allowed);
  anything else is `E0005` — `'is present' requires a maybe type, got 'int'` —
  with a hint. The check binds to the expression on its left, so the result of a
  call must be parenthesised: `if (calling find_user with 1) is present:`.
- **`if NAME as T is <maybe>:` bindings compile (and actually run).** The
  pattern used to emit
  `if ((int32_t v = opt, pengu_maybe_is_present(&v)))` — the `PenguMaybe` (or the
  presence `bool`) assigned to the unwrapped type inside a comma expression,
  which is not even valid C (a declaration cannot appear there). It now lowers to
  a scoped block that evaluates the maybe **once**, tests presence and declares
  the bound name from the heap copy:

  ```c
  {
      PenguMaybe _maybe_1 = (opt);
      if (pengu_maybe_is_present(&_maybe_1)) {
          int32_t v = (*(int32_t*)_maybe_1.value);
          /* body */
      }
  }
  ```

  Bindings also work in value position (`let r is if v as int is opt: … else: …`)
  and are never constant-folded. A redundant trailing `is present` is accepted
  (`if v as int is opt is present:` — the presence test is inherent, and the
  grammar's `if_cond_binding_present` alternative is in fact unreachable because
  the operand would swallow the test), while `is not present` combined with a
  binding is `E0005`. The checker now requires the operand to be `maybe T`
  (`Binding 'v' requires a maybe value, got 'int'`) and the declared type to
  match the element type.
- **Parentheses now survive into the AST.** `"(" expr ")"` is aliased to
  `paren_expr` instead of being inlined. The node is semantically transparent
  (`infer`/`fold`/codegen unwrap it) but it is what lets the checker tell
  `calling f with a, b` from `(calling f with a) and b` — see the list rule
  below.
- **Single-element array literals are no longer folded to their element.**
  `ConstFolder.fold` collapsed any single-child node to its child, so
  `var p as array of byte with size 4 is [0]` emitted
  `uint8_t p[4] = 0;` — invalid C (`invalid initializer`). Array and map
  literals are now never folded, so the initializer is `{ 0 }`. Multi-element
  literals were unaffected.
- **A leading UTF-8 BOM no longer breaks the parser.** Editors on Windows
  (Notepad, Visual Studio, PowerShell's `Set-Content`) write one; it used to
  produce `Syntax error: unexpected '\ufeff' at line 1, column 1`. The parser
  strips a leading BOM from the entry file and from every imported module.
- **Cross-module bindings can be imported together (`E0046`).** Generated
  bindings are self-contained per header, so `raygui.h` (which includes
  `raylib.h`) re-declares raylib's `KEY_*` defines as `const … as i64` while
  `std/raylib.d.pengu` declares them as `KeyboardKey` omen variants. Importing
  both used to fail with `E0046 … collides with the built-in type 'KEY_RIGHT'`.
  A `const` whose value equals the variant's value now denotes the same number
  and is accepted; a genuine mismatch (say `std/whisper.pengu`'s `LOG_INFO` = 2
  against raylib's `TraceLogLevel.LOG_INFO` = 3) is still `E0046`, and the
  message now says "top-level constant" instead of "built-in type".
- **`std/raygui.d.pengu` imports `std.raylib` and `std/nanosvgrast.d.pengu`
  imports `std.nanosvg`.** Their signatures use types from the header they
  include (`Rectangle`, `Font`, `Color`, `NSVGimage`); without the import the
  type became a generic placeholder and every call failed with
  `Argument 'bounds' of 'Button' expects 'Rectangle_any', got 'Rectangle'`.
- **A bare array/map literal is no longer accepted as a statement (`E0005`).**
  C-style indexing (`arr[0]`, which PenguScript spells `arr at 0`) parses as the
  variable plus a stray `[0]` statement; it used to compile into a useless
  `{ 0 };` (and, before the folding fix above, into `0;`). The checker now
  reports *An array literal is not a statement* with the hint "PenguScript
  indexes with 'x at i', not 'x[i]'".
- **The `ref to char` argument mismatch now explains the conversion.** Passing a
  `string` value where a binding expects `ref to char` says: *A string literal
  converts automatically, but a string value needs
  `calling ffi.cstr_from_string with s` (std.ffi)*.
- **`build_runtime.py` stages two more headers.** `stb_herringbone_wang_tile.h`
  and `stb_image_resize2.h` live in `std_c/` and have `std/*.d.pengu` bindings,
  but were missing from `SINGLE_HEADER_NAMES`, so any program importing
  `std.stb_herringbone_wang_tile` or `std.stb_image_resize2` failed with
  `fatal error: stb_image_resize2.h: No such file or directory`.

### Changed — BREAKING

- **`and` is no longer a list separator next to expressions** (it is the boolean
  operator now). It was removed from `arg_list`, `param_list`, `struct_init`,
  `array_lit`, `map_lit` and `indent_row`. Use `,`:

  | Before | After |
  |---|---|
  | `calling f with 1 and 2` | `calling f with 1, 2` |
  | `weave g with x as int and y as int` | `weave g with x as int, y as int` |
  | `declare d with a as int and b as int` | `declare d with a as int, b as int` |
  | `with x is 1 and y is 2` | `with x is 1, y is 2` |
  | `1 and 2 and 3` (indented array row) | `1, 2, 3` |

- **`and` stays a separator in pure name/type lists**, where no expression can
  follow: `shard_params` (`shard T and U`), `where_clause`,
  `fn_param_list` (the parameter list inside a `weave` **type**), `omen_field`
  and the judge `when … with` payload. Commas are accepted there too.
- **A bare `and`/`or` is not a list element.** Elements of a comma-separated
  list stop below the boolean operator levels, so the old separator can never be
  read silently as one boolean element:

  - array literals, map literals, indented literals and parameter defaults now
    fail at parse time with the `E0000` hint (`var xs is [1 and 2]` →
    `'and' is no longer a separator: use ','`);
  - a bare `and`/`or` glued to a **call with arguments** (`calling find with 1
    and true`) or to a **struct literal** (`with flag is a and b`) is `E0005`
    — *Ambiguous 'and' after a call with arguments* — because those shapes are
    where the removed separator was written most often and the boolean reading
    is silently valid when both operands happen to be `bool`.

  Parenthesise to pass a boolean: `[(a and b)]`, `with flag is (a and b)`,
  `(calling find with 1) and true`. Bare `and`/`or` keep working everywhere a
  single value is expected (conditions, `var`/`let` initialisers, `return`,
  `set`, nested calls), so `var ok as bool is a and b` and `if a and b:` are
  unchanged.
- Docs in this repo (`LANGUAGE.md`, `CHEATSHEET.md`) were migrated to commas;
  `CHEATSHEET` §3.4 now documents `,` as *the* list separator.

### Migration

- Replace separator `and` with `,` in: `calling` arguments, `weave`/`declare`
  parameter lists, struct-init literals (`with x is …, y is …`), array and map
  literals (bracket and indented forms).
- `calling f with a and b` no longer means "two arguments" and it no longer
  compiles: it used to parse as `(calling f with a) and b`, which was silently
  accepted whenever both operands were `bool`. It is now `E0005`, so the
  mistake is caught at compile time instead of changing the meaning of the
  program. Write `calling f with a, b` for two arguments or
  `(calling f with a) and b` for a boolean combination.

### Migration performed in this change (repo-wide)

`std/` and `tests/` were migrated together with the language change, so the
repository compiles and the full suite is green (**610 passed**):

- **`std/*.pengu` and `std/*.d.pengu`**: 725 code-level separators rewritten in
  47 files. Comments and string literals were left untouched (the std modules are
  full of English prose containing "and"), and every file was re-parsed after the
  rewrite.
  > The `std/` half of this migration was re-applied later in the same release
  > (the parser-driven pass counted 697 separators this time; the difference is
  > the modules that were added or edited in between) because a `git checkout
  > -- std/` while regenerating bindings discarded it. The documentation that
  > those files carried was restored from the `pengucc_build/std/` snapshot
  > first, and the result is `pengu check`-clean for all 49 importable modules
  > and compiles as a single bundle.
- **`tests/**/*.pengu`** (the stdlib exercise programs) were migrated in the same
  pass.
- **Pengu sources embedded in `tests/*.py`**: 218 separators across 106 string
  literals plus one f-string, migrated by an `ast`-based pass that works on the
  literal *values* and only rewrites snippets that parse as Pengu — so expected
  messages such as `"ranges and in ok"` or
  `"Omen variant name 'ONE' is used by both omen 'A' and omen 'B'"` and C header
  strings were preserved verbatim.
- **`std/lot.pengu`**: its `lambda` parameter was renamed to `rate`. `lambda` is
  a reserved word since this version (lambda expressions), so it can no longer be
  used as an identifier.
- **`README.md`**: its two ```pengu blocks (`with model is "Pengu" and speed is
  0.0`, `calling xxhash.XXH64 with "PenguScript" and 11 and 0`) and the
  `weave name with a as T and b as T into R` prose were rewritten to commas.
  All other fenced Pengu blocks in the repo were re-parsed with
  `PenguParser`; the remaining `and` occurrences are boolean operators or English
  prose inside comments.
- **VS Code extension snippets**: five bodies still expanded the removed
  separator (`weave` params, `ward.assert_eq_int`/`_string`, `weave_many`,
  the `test` template). They now use commas; the `and-or` snippet keeps `and`
  because it inserts the *operator*. Two snippets were added for the
  now-working maybe binding (`ifbind`/`iflet`) and the presence test
  (`present`).
- `examples/` does not exist in this repository (and `scratch/` is gitignored
  dev scratch that still contains pre-0.10.0 sources; it is not part of the
  tree).

### Added — C callbacks, word tests in argument lists

- **Function-pointer values and C callbacks work.** Three defects kept `alias …
  as ref to weave …` / `ref to weave …` unusable:

  1. `FnType` was not compatible with a declared `ref to weave …` (nor with an
     alias of it), so `var cb as ref to weave with x as int into int is lambda …`
     failed with *declared as 'ref to weave …', but initialized with 'weave …'*.
     A function value now decays to a function pointer for compatibility.
  2. Calling **through** a function-pointer variable (`calling cb with 21`) was
     reported as *Undefined function 'cb'*; the callee resolution now unwraps
     `RefType(FnType)` (and aliases of it) and uses its signature.
  3. The C declarator for such a variable was emitted as
     `int32_t (*)(int32_t) cb` (invalid C — the identifier must go inside the
     parentheses) and `to_c_type` spelled `ref to weave …` as a pointer *to* a
     function pointer. Both now go through `CTypeMapper.to_c_decl`.

  On top of that, a function value passed to a callback parameter is now
  **cast to the declared callback type** (`((AudioCallback)on_audio)`). That is
  what makes raylib's callbacks compile under GCC 14+: their C prototypes carry
  `const` qualifiers the `.d.pengu` binding does not express
  (`const char *text` in `TraceLogCallback`, `const void*` in `qsort`). Verified
  by building real programs for `SetAudioStreamCallback`,
  `SetTraceLogCallback`, `SetSaveFileDataCallback` and
  `SetLoadFileTextCallback`, plus an `atexit` callback that runs
  (`tests/test_callbacks.py`).
- **`va_list` (and every bare custom type) is no longer mangled.** The optional
  `of type …` part of a `custom_type` leaves a `None` child behind, and
  `ast_to_type` treated it as a type argument, turning `va_list` into the bogus
  generic `va_list_any` (`Rectangle_any`, `NSVGimage_any` had the same cause).
  Bare custom types now keep their plain name, so the emitted C uses `va_list`
  (from `<stdarg.h>`, already included by the runtime header).
- **A word test in argument position is now rejected (`E0005`).**
  `calling find with 1 is true` parses as `calling find with (1 is true)` — the
  test applies to the *last argument*, while a C-style `find(1) == true` tests
  the call's result, and the mistake was silent whenever the parameter happened
  to be `bool`. The checker now reports *Ambiguous 'is true' in the arguments of
  'find'* and the help spells out both readings:
  `calling f with (x is true)` (test as the argument) and
  `(calling f with x) is true` (test the call's result). The same applies to
  `is false`, `is present` and `is not present`. Tests in other positions are
  unaffected (`if m is present:`, `calling ready is true` with no arguments,
  struct-literal field values), so nothing in `std/` or the suite needed
  changing.

### Known issues found while validating this change (not addressed here)

- **Inline callback parameters cannot express C `const` qualifiers.** A callback
  parameter written inline (`compar as ref to weave with a as ref to void, b as
  ref to void into int`) is cast to the type spelled by those Pengu parameters,
  so `qsort`'s `int (*)(const void*, const void*)` still mismatches and GCC 14+
  rejects it. Callbacks declared through an alias of a **C typedef** are immune,
  because the cast names the typedef — which is how every raylib callback is
  bound. Fixing the inline case needs `const` in the type grammar (and in
  `pengu bind`), which is not part of this change.
- **`x to T` only casts to simple types.** The `to` operator is the *range*
  operator with a cast heuristic on the right operand, so
  `ptr to ref to int` is a syntax error; use `transmute ptr to ref to int` for
  pointers, `maybe T`, arrays and other compound types.
- **A Pengu function named after a C keyword is emitted unmangled in its
  definition** (`weave double …` → `int32_t double(int32_t x)`), while uses go
  through `_c_ident` (`_double`). Rename such functions for now.
- **The grammar's `if_cond_binding_present` alternative is unreachable.** Every
  `if NAME as T is <expr> is present:` parses as `if_cond_binding` with the
  presence test inside the operand (the operand is greedy), which is why the
  checker/codegen unwrap a trailing `is_present` themselves. The dead
  alternative is kept for now to avoid perturbing the LALR tables.
- **One silently-resolved LALR shift/reduce conflict (maintainers).** The
  grammar has always been built without `strict=True`, so Lark resolves
  conflicts by shift. It had one on `COMMA` before the list rule above; the
  same underlying `if_cond` binding ambiguity is now reported on `AS`. Both
  spellings are covered by tests (`tests/test_maybe_bindings.py`,
  `tests/test_error_ux.py`) and by the full suite.

### `std/` audit performed in this change (50 modules)

- **Separators**: an AST audit found **194 multi-argument calls** across the 50
  modules and **0 leftover `and` separators** — every code-level `and` in
  `std/` sits inside a `bool_and`/`bool_or` node (the boolean operator). The
  remaining `and` occurrences are English prose in comments.
- **Compilation**: every module parses and type-checks on its own, and a single
  entry importing **48 of them at once** (all but `whisper`, whose `LOG_*`
  constants genuinely clash with raylib's `TraceLogLevel`) builds with gcc and
  links in ~36 s. `pengu check` on the 50-module entry reports only those five
  `LOG_*` collisions.
- **Runtime**: the repository's own stdlib programs (27 `tests/std_programs/*`,
  compiled and run by `tests/test_stdlib.py`) are green, plus these new manual
  checks: a ported `raylib` **basic window** and a `raylib` + `raygui` window
  both open and stay alive; `perlinum` runs; `nanosvg`/`nanosvgrast` compile but
  the vendored library crashes (see below).

### `pengu bind`: the generator now targets the current language

`pengu_bind.py` was updated so a freshly generated binding is valid today, and
the tool-produced `std/*.d.pengu` files were regenerated with it:

- **Comments are PenguScript single-line `#` comments.** A multi-line C block
  (`/* … */`, `/** … */`) or a run of `//`/`///` lines becomes one `# …` line
  per source line, with the `*` gutters and the opening/closing markers
  stripped. Only the generated-file banner keeps `##`.
  A multi-line block was not even *detected* before: `_comment_before` only
  recognised a comment whose first inspected line started with `/*`, so blocks
  closed by ` */` were dropped entirely.
- **`const` signatures become `frozen`.** `const char *text` →
  `text as ref to frozen char`, `const void *blob` → `ref to frozen void`,
  `const T value` → `frozen T`. A *const pointer* (`T * const p`) is deliberately
  dropped — that is what `let` expresses, and `frozen` always qualifies the
  pointee. 98 parameters/returns across the regenerated bindings gained the
  qualifier.
- **`va_list` (and `__builtin_va_list`) map to `va_list`** instead of leaking a
  compiler-specific spelling, so raylib's `TraceLogCallback` can be described.
- **Callback aliases are hoisted out of the declaration that needs them.**
  `alias Callback1 as ref to weave …` used to be appended at the point of
  discovery, which put it *inside* a `rune` body and produced invalid code
  (`alias Callback1 …` followed by `  read as Callback1`). They are queued and
  flushed before the `rune`/`declare` line.
- **Enum aliases are dropped with a warning.** C allows two enumerators to share
  a value; `omen` does not (`E0027`), so the second name is skipped instead of
  emitting a binding that cannot compile.
- **`import` lines for included headers are auto-detected.** The generator scans
  the sibling bindings' `## Source header:` banners and emits the `import`s a
  binding needs to reuse the *same* types as the headers it includes
  (`raygui.h` includes `raylib.h` → `import std.raylib`, `nanosvgrast.h` →
  `import std.nanosvg`). Two mistakes are avoided here: a binding never imports
  itself (the `.d.pengu` suffix has two dots, so the module name is stripped by
  hand), and the scan is skipped when the header is bound elsewhere.
  New flag: `pengu bind --auto-import DIR` (default: the output directory,
  empty string disables it).
- **Regeneration tool**: `regen_std_bindings.py` re-runs the generator for the
  bindings that carry the tool banner, keeps each file's hand-written preamble
  and *refuses* to rewrite a file when declarations would be lost — that is how
  the hand-curated ones (raylib's colour constants and platform links, the
  pure-Pengu wrappers, the hand-written webui/sqlite3/xxhash/yaml bindings) stay
  untouched. It regenerated 12 bindings: `datastructura`, `fenestra`, `imago`,
  `nanosvg`, `nanosvgrast`, `pactum`, `perlinum`, `raygui`, `scriptor`,
  `stb_herringbone_wang_tile`, `stb_image_resize2` and `typis`.

Because bindings now carry `frozen`, two call sites had to follow: a
`ref to frozen char` parameter still accepts a string literal (the literal and
`_is_ref_char_type` now look through `frozen`), and a `frozen` *result* cannot be
stored in a mutable local without a conversion
(`tests/test_ffi_libs.py`'s `imago.failure_reason` smoke now declares
`var why as ref to frozen char`).

### Hand-written bindings migrated to the same style

The 11 bindings the generator cannot produce were brought in line by hand
(`migrate_manual_bindings.py` merges the generator's signatures into a
hand-written file by declaration name — parameters must line up — and refuses to
write when a declaration or a parse would be lost):

- **`const` → `frozen`.** `raylib.d.pengu` (146 signatures:
  `SetClipboardText with text as ref to frozen char`, `GetMonitorName into ref to
  frozen char`, `SetShaderValue … value as ref to frozen void`), `sqlite3.d.pengu`
  (12, including the callback aliases that now take
  `ref to frozen Fts5ExtensionApi`), `xlsxio.d.pengu` (`get_version_string`,
  `open`'s filename/sheetname, `add_cell_string`, `add_column`),
  `xxhash.d.pengu` (`const void* input` → `ref to frozen void` on every one-shot
  hash and `_update`, and `XXH*_digest`'s `const XXH*_state_t*` →
  `ref to frozen XXH*_state_t`), `yaml.d.pengu` (`get_version_string`),
  `miniaudio.d.pengu` (`ma_version_string`).
- **`##` docs → `#`**, the generator's spelling. No documentation is lost:
  `pengu_lsp/hover.py`'s `extract_doc_from_file` and the checker's
  `_extract_preceding_doc` both read `#` comments as doc text, so hover and
  `pengu doc` keep working. `tomlum`, `uuid`, `minicoro` and `webui` needed only
  this change (0 signatures were stale).
- **Stale doc examples using `and` as an argument separator became `,`** (23
  comment lines across `std/*.pengu`), so the documentation a reader copies
  shows the current syntax.

These 5 files cannot be regenerated by the tool at all — `miniaudio.h` needs
`pthread.h` (absent from `c_bind_stubs/`), `xlsxio`/`xxhash`/`yaml` trip
pycparser on GNU constructs the preprocessed text keeps, and `rlights.h` has no
`include` line on purpose (it pulls in raylib plus an OpenGL loader) — so
`regen_std_bindings.py` skips them ("hand-written, no `pengu bind` banner") and
they stay hand-maintained.

### Known issues found while auditing `std/` (not addressed here)

- **`pengu build` can leave a stale binary and still report "(cached)".** The
  up-to-date check compares the output's mtime with the *entry source* mtime on
  the fixed path `build/app.exe`, so it does not notice that the existing
  binary came from a **different** program. Repro (verified): build program A
  (fresh), build program B (fresh) and then build A again — the second A build
  prints `Finished (cached)` and leaves B's binary in place. Touching the source
  forces the rebuild. `pengu run` is not affected in the same way (it uses a
  per-entry `build/<tag>_run/` directory). Workaround: delete `build/app.exe`
  (and `build/.bundle_hash`) or touch the entry before building.
- **`std/nanosvg` + `std/nanosvgrast` compile but crash at run time.** The
  vendored single-header library segfaults inside `nsvgParse` for any non-empty
  SVG. It reproduces in **plain C** with the repository's own header and
  `libpengu_stb.a` (`nsvgParse("")` returns an image, `nsvgParse("<svg></svg>")`
  raises `0xC0000005`), at `-O0`, `-O1` and `-O2`, so it is a vendor-source
  problem, not a compiler or codegen bug. `perlinum` (same object file) works.
- **`weave main`'s return value is discarded.** The generated wrapper calls
  `pengu_main();` and returns 0, so a program whose `main` returns 42 still
  exits with status 0. Scripts that need an exit status must call
  `spark.exit`-style helpers or write to stderr.
- **A `string` value is not accepted where a binding declares `ref to char`.**
  String *literals* are converted (`DrawText("hi", …)` works), but passing a
  `string` variable fails with
  `Argument 'input' of 'Parse' expects 'ref to char', got 'string'`.
- **`calling … with …` used as an operand needs parentheses.** In
  `if calling GuiButton with bounds, "Click me" == 1:` the comparison binds to
  the *last argument*, so the C idiom `GuiButton(...) == 1` must be written
  `(calling raygui.Button with bounds, "Click me") == 1`.
- **Two std modules can define the same constant name.** `std/whisper.pengu`
  (`LOG_INFO` = 2) and `std/raylib.d.pengu` (`TraceLogLevel.LOG_INFO` = 3)
  cannot be imported together; the `E0046` message tells the user to use the
  full omen name (`TraceLogLevel_LOG_INFO`) or rename. A `const`/`const`
  clash across modules (two modules defining the same plain constant) is not
  detected at all — the last registration wins silently.
- **`std/imago.d.pengu` and `std/sqlite3.d.pengu` reference `FILE` and
  `va_list`.** Those functions cannot be called from Pengu code (unknown C
  types become generic placeholders; variadic C functions are not callable
  anyway). The rest of both modules is usable.

## [0.9.1] - Unreleased

### Added

- **`try`, `or else` and `or return` now generate real C code.** Previously the
  three unwrap operators type-checked but fell through codegen's default branch
  (translating only the first child), so a program using them emitted invalid C
  (`PenguMaybe` assigned to the unwrapped type). They now lower to a GNU
  statement-expression that unwraps the success value lazily and `return`s on
  failure: `or else` yields the fallback, `or return X` returns `X` from the
  enclosing function, and `try` propagates `maybe none` / the error result to
  the caller.
- **`try` is now restricted to functions that can propagate the failure**
  (E0045). A `try` over `maybe T` requires the enclosing weave/enchanting to
  return `maybe T`; a `try` over `result of T to E` requires a result return
  whose error type is compatible with `E`. Misuse used to type-check and then
  fail in C; it is now a clear English semantic error.
- **Omen variant name collisions are detected** (E0046). Both the full
  (`Omen_variant`) and simple (`variant`) names occupy the global scope, so a
  weave/const/alias reusing one of them — or two omens sharing a variant name —
  silently shadowed a registration; it now reports a clear error.
- **`bind` validates that the bound target type exists** (E0004) before
  registering concept methods on it.
- **`pengu_precis_free_response()` runtime helper** releases a
  `PenguPrecisClientResponse` (header map, owned body string and the struct),
  matching the ownership contract documented in `pengu_runtime.h`.
- **Resource cleanup for native handles.** New runtime helpers plus std
  wrappers (functional weaves and `free` enchanting methods) for every
  concurrency primitive (`pengu_c_filum_{mutex,wait_group,once,cond,
  atomic_int,chan}_free` in `std/filum.pengu`), compiled regexes
  (`pengu_c_regulus_regex_free`, `pengu_c_regulus_match_free` in
  `std/regulus.pengu`) and parsed XML/HTML documents and nodes
  (`pengu_c_parchment_document_free`, `pengu_c_parchment_node_free` in
  `std/parchment.pengu`). Because PenguScript copies wrapper structs by value,
  these helpers release the native resources (PCRE2 code, libxml2 document,
  owned string buffers) and null dangling fields instead of `free()`-ing the
  value-copied structs; the ownership contract is documented in
  `pengu_runtime.h`.
- **`include` no longer invents method signatures.** The raw-C fallback that
  turned *any* unknown enchanting/instance method into a parameterless `void`
  call whenever a C header was included is gone: misspelled method calls now
  raise `E0004`. Bare unknown function calls in include modules remain the
  documented FFI escape hatch (the C header declares them).
- **Omen variant collisions with built-in types report a clear message**
  (E0046): `omen Color:\n  int` now explains that `int` is a reserved
  built-in type and points to the full `Color_int` variant name.
- **Ownership documentation completed** in `pengu_runtime.h` for every
  allocating function: Archivum file/metadata/dir reads, Regulus split/find-all,
  Parchment serialization/attribute/text, and Precis URL encode/decode and
  query parsing now state who owns the returned buffers.
- **LSP: instant completion for imported module members.** The server keeps a
  global module cache (import alias → module scope, only non-empty scopes)
  refreshed on every document validation (even when the document has errors,
  since imports are collected in pass 1). Completion for `spark.` / `alias.`
  resolves members from the cache only when the alias is **not** defined in the
  current document (unvalidated or unimported files); a defined import symbol
  is authoritative and never falls back to the cache, so a stale or foreign
  cached scope can no longer leak another module's members into the
  suggestions. Aliased imports (`import std.spark as s`) and project modules
  work the same way.
- **C ⇄ Pengu conversion bridges** (runtime + `std/ffi`). New runtime helpers
  in `pengu_runtime.h` / `pengu_runtime.c` for embedding/library code, all
  NULL-safe and documented with ownership rules:
  - string views: `pengu_string_to_cstr` / `pengu_string_bytes` (read-only,
    never NULL for empty strings), plus owning `pengu_string_copy`;
  - container accessors `pengu_slice_data` / `pengu_list_data`;
  - deep-copying constructors `pengu_list_from_data`,
    `pengu_map_from_entries`, exporters `pengu_map_to_entries`
    (`PenguEntryArray`) + `pengu_entry_array_free`, and
    `pengu_string_as_slice`.
  New module **`std/ffi.pengu`** exposes concrete PenguScript wrappers
  (string↔C string, byte views, byte/int/float slices and lists from raw
  pointers, and a string→int map built from parallel slices), each with
  module docstrings explaining the ownership model. PenguScript container
  types are nominal, so per-element-type typed symbols were added
  (`pengu_ffi_slice_i32`, `pengu_ffi_list_f64`, `pengu_ffi_cstr_string`, …);
  fully generic (`shard T`) buffer bridges cannot be expressed today because
  the language cannot infer type parameters that appear only in the return
  type of container conversions.
  Exercised by `tests/std_programs/test_ffi.pengu`, a C driver test
  (`tests/test_ffi_bridges.py`) and bundle-emission assertions on the
  generated `bundle.c`.
- **Standard-library documentation pass (`std/`).** Every wrapper module
  (non-`.d.pengu`) now matches the `std/ffi.pengu` documentation standard:
  module header with description, usage and ownership model; section
  separators; and a doc comment above each of the 789 public declarations
  (weave, declare, rune/enchanting methods, aliases, constants) with purpose,
  signature and ownership/null notes verified against the runtime sources. The
  `.d.pengu` C-binding files keep their extensive upstream documentation; they
  gained a consistent module header (purpose + "pure `.d` binding" note) and,
  where missing, an ownership note. Changes are comment-only; every file was
  re-parsed and the full suite stays green.
- **Omen variants declared in `.d.pengu` emit their simple C names.** When an
  `omen` lives in a `.d.pengu` declaration file it mirrors an enum already
  defined by the included C header, so codegen now emits the bare variant name
  (`KEY_LEFT`, `.tag = KeyDown`, `case KEY_LEFT:`) instead of the prefixed
  `Omen_variant` form, for every emission path: `var_ref` / bare names, module
  members (`keys.KEY_LEFT`), `Omen.variant` accesses, algebraic-tag
  initializers and `judge` cases. Omens declared in normal `.pengu` modules
  keep the collision-safe `Omen_variant` prefix, and declaration omens still
  generate no C type definitions. Centralized in
  `PenguCodegen._get_omen_variant_c_name`; covered by
  `TestOmenDeclarationEmission`.
- **LSP: module-name completion in `import` statements.** Typing `import ` now
  offers the standard-library modules (`std.spark`, …) plus project modules
  under `src/` (`components.player`, …); `import std.` suggests the short names
  (`spark`, `archivum`, `sqlite3`, …) and replaces exactly the typed prefix via
  a `textEdit`, so the selected module is inserted without duplicating text.
  Partial prefixes filter the list (`import st…`, `import std.s…`), private
  `_`-prefixed files/directories are hidden, and `.d.pengu` bindings are
  offered under their real spec (`std.sqlite3`). The directory scan is cached
  per project root for 5 seconds.
- **LSP lint warnings.** Clean documents are now linted for unused imports and
  unused local `var` / `let` declarations, published as
  `DiagnosticSeverity.Warning` diagnostics (conservative textual analysis:
  any occurrence outside the declaration counts as a use; `_`-prefixed discard
  names are exempt). Implemented in `server._style_warning_diagnostics`.
- **LSP "Organize imports" code action.** `code_actions.organize_imports_action`
  drops import statements whose module is never referenced outside the import
  block and sorts the remaining imports alphabetically by spec, replacing the
  contiguous import block in a single edit (no-op when the block is already
  tidy).
- **LSP Go to Implementation.** New `textDocument/implementation` handler
  returns every declaration of the symbol under the cursor across the standard
  library and the current project (functions, types, constants and
  enchanting/bind `weave` methods), via `code_actions.declaration_locations`
  (cached per set of roots; `.d.pengu` bodies skipped).
- **LSP Find References.** New `textDocument/references` handler: local
  `var`/`let`/`param` symbols resolve within the current document only, while
  global symbols resolve across stdlib + project sources
  (`code_actions.word_occurrences_in_roots`), honouring
  `context.include_declaration` for the active document. Bounded project-root
  discovery (never escalates to a filesystem root).
- **LSP contextual completion.** Three new completion contexts:
  - inside a `judge` block, typing `when ` offers the subject omen's variants
    (or `true`/`false` for a bool) plus an `else ->` item — resolved by walking
    up to the `judge <expr>:` line (takes precedence over the compile-time
    `when` variables);
  - typing `set.` inside a `with target:` block offers the rune's fields;
  - after `var x as Type is with ` offers the rune's fields with per-type
    default initializers and an "(all fields)" fill snippet.
  `get_completions` gained an optional `doc_text` parameter for the multi-line
  contexts (the server passes the document text).
- **LSP "Implement missing concept methods" code action.** When the cursor
  sits inside a ``bind Target with Concept:`` block,
  `code_actions.implement_concept_methods_action` appends a weave skeleton for
  every concept method not yet implemented there (correct parameter list,
  return type and a per-type default body: `return`, `return 0`, `return
  false`, `return ""`, `return maybe none`, …), skipping methods that already
  exist. Wired into the `textDocument/codeAction` handler.
- **LSP richer hover.** Rune hovers now list the enchanting methods attached to
  the type (via `symbols.methods` and `RuneType.methods`) and, for generic
  runes, show the declared type parameters and concrete type arguments
  (`**Type arguments**: `int``). Omens/variants already listed payloads and
  sizes; docstrings stay appended.
- **LSP formatting reads `pengu.yaml`.** `formatting.load_format_config` finds
  the nearest project config (bounded upward walk) and extracts `tab_size` /
  `indent` / `indent_size` / `indent_width` and `insert_spaces` / `use_tabs`.
  `textDocument/formatting` honours client FormattingOptions first, then the
  project config, then the 2-space default.
- **Block-style construction expressions (`with:`).** `var x as SomeType with:`
  followed by an indented body of `set .field is ...` assignments and
  `calling .method` calls now builds a fresh value through an implicit mutable
  temporary and evaluates to the built object (any expression position). The
  target type must be annotated (`E0014` otherwise); unknown fields/methods
  and disallowed statements inside the body are semantic errors (`E0004` /
  `E0007` style). Grammar adds `with_init_expr`; typing mirrors `with target:`
  scopes; codegen emits a GNU statement-expression. The single-line
  `with field is … and …` initializer is unchanged. Covered by
  `TestWithInitBlock`.
- **Imported dotted types resolve correctly.** `rl.Rectangle` in type
  annotations used to fall through `lookup_type` (creating an empty rune and
  false `E0013`/`E0022` errors for fields and, with `with:` blocks, builder
  scopes). `SymbolTable.lookup_type` now resolves dotted names through the
  import-prefixed registries (`rl_Rectangle`) or the import's module scope,
  and codegen's type lookup delegates to it — fixing Raylib-style structs and
  any other binding whose types are referenced through an import alias.
  Covered by `TestImportedModuleDottedTypes`.
- **`do:` block expressions.** An indented `do:` block is an expression: its
  statements run in a fresh local scope (declared variables do not escape)
  and the block evaluates to its last expression statement (or `void`).
  Works as a `var`/`let` initializer with full type checking; type mismatches
  with the declared annotation are normal errors. Compiles to a GNU
  statement-expression. `do` is now a control keyword (VS Code TextMate +
  snippet, LSP snippet). Covered by `TestDoBlockExpression`. Block forms of
  `unless`/`judge` and value-returning `for`/`while` remain roadmap items.
- **`if … else:` blocks as expressions.** An `if` whose branches are indented
  statement blocks now supplies a value when it sits in a value position: each
  branch runs in its own scope and must end with an expression; all branches must
  share one common type. A value block's value is its last statement's value, so
  both `else if <cond>:` and `else:` + a nested indented `if` chain, and `do:`
  blocks ending in an `if`, all work. Value-ness is **positional**: `if cond:` +
  block is token-identical as a statement and as a value, so `if` keeps a single
  grammar rule (`if_stmt`) and the checker records the branch type on the node
  (`_pengu_value_type`) when the `if` is in a value slot; codegen emits a GNU
  statement-expression with a typed temporary assigned per branch. Statement
  `if` semantics (dead-code elimination, `W0004`, binding conditions) are
  untouched. Covered by `TestIfBlockExpression` (including a regression test
  that statement-level `if` bodies still execute) and
  `TestDoBlockExpression`; CHEATSHEET §6.1.2 documents it.

  > A separate `if_block_expr` grammar rule reachable from the expression chain
  > must **not** be reintroduced: it makes every statement-level `if` parse as an
  > expression and silently drops branch bodies.

- **`unless … else:` blocks as expressions, and more value positions.** `unless`
  is the mirror of the value-position `if` (`value_expr` now accepts
  `unless_stmt`; `PenguChecker._check_unless_value` reuses `_check_value_block`
  and `_merge_branch_value_types`, and codegen reuses `_translate_value_if` with
  the condition negated). The same machinery now also covers the remaining value
  slots, which share one walker (`_check_value_exprs`) so nested block values are
  validated wherever they appear:

  - `return` — `return if c: …` / `return unless c: …` (and a block value
    anywhere in the returned expression, e.g.
    `return calling pick with if c: …`); `return_stmt`'s trailing `_NEWLINE` is
    now optional, because a block value consumes its own line break.
  - call arguments — positional and `name is <block>`.
  - struct-literal fields — `with x is <block> and y is <block>`.
  - `set .field is <block>` inside a `with:` builder (composition with §18).

- **Loops as expressions (all loop forms).** Every loop the language has —
  `while cond:`, `for i from a to b [step s]:`, `for v in col:` and
  `for i, v in col:` (incl. `_` discard) — now works in a value position and
  **collects** its body's last expression per iteration into a `list of T`:

  - Grammar: `value_expr` accepts `while_stmt` / `for_stmt`, so loops work in
    every value slot already covered (`var`/`let`/`static var` initializers,
    `set`, `return`, call arguments, struct-literal fields, block tails). The
    `for … then …` comprehension keeps working (it stays a plain expression and
    is distinguished by `then` vs `:`).
  - Checker: `_check_loop_value` wraps the element type into
    `ListType(element=T)` and records it on the node (`_pengu_value_type`); the
    three loop checkers took a `collect` flag that checks the body as a value
    block instead of a statement block and returns the per-iteration type. A body
    that produces no value is `E0005` (*loop used as a value must produce a value
    on every iteration*). A loop that merely ends a value block is best-effort
    (no error) so statement-style bodies keep working.
  - Codegen: `_translate_loop_value` emits
    `({ PenguList l = pengu_list_new(sizeof(T), 8); for (…) { …; T v = <value>;
    pengu_list_push(&l, &v); } l; })` by threading an `append_ctx` through the
    existing `while`/`for_range`/`for_in` translators, whose bodies now go through
    `_translate_loop_body`. The push sits at the end of the body, so `continue`
    skips a value and `break` ends the loop for free. Nested loops build
    `list of list of T`.
  - Types resolved through context: `_check_value_exprs` now takes the enclosing
    slot's expected type, so a trailing `with:` builder inside a loop body is
    typed from the list element (`var ps as list of Point is for …: with: …`), and
    the same plumbing now reaches `if`/`unless`/`do` initializers.
  - Docs: CHEATSHEET §6.1.3 (loops as expressions) and §6.1.4, the *definitive*
    table of what is and is not an expression (12 constructs × 8 value positions,
    verified by probe) — plus LANGUAGE.md §7.6.
  - Tests: `TestLoopValueExpression` (13).

- **Fixed: a loop variable was rewritten inside a `with:` builder.** Codegen
  treated any bare name inside a `with` scope as a field of the target unless the
  *global* symbol table knew it, so a loop variable used in a builder emitted
  `_with_1.i` (invalid C: `'Point' has no member named 'i'`). Names present in
  `local_vars` now stay plain identifiers.

- **Fixed: `do:` nested as a block's tail lost its value** (a trailing
  `expr_stmt`-wrapped `do:` is a value block, like a trailing `if`/loop).

- **Fixed: iterating an inline array literal emitted invalid C.** `for v in
  [1, 2, 3]` produced `({ 1, 2, 3 })[_i]` — an array literal is a brace
  initializer with no storage. The for-in codegen now materializes it into a
  temporary array (`int32_t _lit[] = { 1, 2, 3 };`) and indexes that.

  Covered by `TestUnlessValueExpression` and `TestBlockValuePositions`;
  LANGUAGE.md §7.6 and CHEATSHEET §6.1.2 document the positions.
- **Single-line block statements now compile and are type-checked.** The
  one-line block form (`block: ":" simple_stmt _NEWLINE`) parses into aliased
  nodes (`return_simple`, `set_simple`, `named_simple`, `continue_simple`,
  `break_simple`) or a bare `simple_stmt` holding one expression. The checker and
  codegen had no dispatch for those nodes, so `if c: return 0`,
  `while i < n: set i is i + 1` and `for i from 0 to 3: calling tick with i`
  silently emitted **no C at all** and skipped every semantic check. Both now
  re-dispatch through `SIMPLE_STMT_ALIASES` (exported by `pengu_grammar`) onto the
  canonical statement rules, so single-line bodies emit the same C as — and are
  validated exactly like — their indented spelling (mutability, return type,
  loop-control placement, expression type checking). Covered by
  `TestSingleLineBlockBodies`.

### Removed

- **The `pub` keyword is gone.** Visibility is determined exclusively by the
  underscore naming convention: identifiers starting with `_` are module
  private (E0043 on cross-module access) and everything else is public. `pub`
  never had semantic effect, so removing it simplifies the grammar, the
  checker/codegen top-level unwrapping and the docs with zero behavior change
  for existing programs.

## [0.9.0] - Minimal Modern C

### Stabilization pass (repo-preparation fixes)

- **Grammar file repaired**: duplicated trailing token definitions and a stray
  `"""` after `DOTDOT` made `pengu_parser` fail at import; the duplicate block
  was removed so the grammar imports cleanly.
- **`to` cast ambiguity removed**: the duplicate `logic_or "to" base_type ->
  cast_expr` alternative in `range_expr` was deleted — casts live only in
  `postfix`, so `10 to float` is a cast while `1 to 10` is a range.
- **`at` chains are left-associative semantically**: `grid at 0 at 0` parsed
  right-nested (`at(grid, at(0, 0))`), breaking typing and codegen. A flatten
  helper now rewrites the chain to `[base, idx, idx, ...]` and folds it
  left-to-right in both `pengu_infer` and `pengu_codegen` (`g[0][0]`).
- **Rune/field indent literals**: indented literal blocks accept `NAME is expr`
  rows (in addition to array rows and `key: value` map entries) so
  `var p as Player is\n  x is 10.0\n  y is 20.0` parses.
- **English-only diagnostics**: E0041/E0042/E0044 messages (array-size
  mismatches, inverted ranges, non-exhaustive judge) were bilingual or mojibake;
  they are now English, matching the rest of the error catalogue.
- **Version strings**: bundle header and module docstrings now read
  **v0.9.0** (was `v0.6`); `VERSION` file bumped to `0.9.0`.

### Modern Language Expressiveness & Semantic Rigor

- **Multiline Arrays**: Bracket-delimited collections (`[ ... ]`) now bypass indentation rules via `OPEN_PAREN_types = ["LSQB", "LPAR", "LBRACE"]` in `PenguIndenter`, allowing naturally formatted multiline arrays across arbitrary indentation levels.
- **Triple-Quoted Strings & String Interpolation**:
  - Added triple-quoted strings (`"""..."""`) with automatic common whitespace dedent.
  - Added expression interpolation (`{expr}`) inside format strings, compiling directly into human-readable `snprintf` / `pengu_string_format` C99 output.
  - Added raw string literals (`r"..."` and `r"""..."""`) preventing escape sequences and interpolation expansion.
- **Indent Literals (Bare & Colon Syntax)**:
  - Introduced clean off-side literal syntax for 2D arrays (`indent_row` with `and`), 1D arrays, Runes (`field: value`), and Maps (`key: value`).
  - Supports both bare `is` and colon-prefixed `is:` without LALR(1) shift/reduce conflicts.
- **Enhanced Local Type & Size Inference**:
  - Full type inference for local declarations (`var x is 42`, `let arr is [1, 2, 3]`).
  - Array sizes automatically inferred from literal element counts when explicit sizes are omitted.
  - Semantic error `E0014` enforced on untyped `null` assignments (`var x is null`).
- **Ranges and Membership Operators**:
  - Native range expressions via `to` (`start to end`) and `..` (`start..end`), backed by stack-allocated `PenguRange` structs in C.
  - Direct range loop iteration in `for i in start to end:`.
  - Native `in` and `not in` operators for ranges, strings, arrays, and maps.
- **Semantic Checker Rigor (E0041 - E0044)**:
  - `E0041` (`ArraySizeMismatchError`): Detects dimension and shape mismatches in array literals at compile time.
  - `E0042` (`InvalidRangeError`): Validates static range boundaries to prevent inverted ranges (`start > end`).
  - `E0043` (`PrivateSymbolAccessError`): Enforces symbol privacy for identifiers prefixed with `_` outside their defining module or rune.
  - `E0044` (`NonExhaustiveJudgeError`): Guarantees exhaustive case handling in `judge` expressions for omens and booleans when no `else` fallback is present.
- **Multi-Line Defer & Errdefer Blocks**:
  - Extended `defer:` and `errdefer:` to accept multi-statement indented blocks alongside single expressions.
  - Compound statement blocks are scheduled on the LIFO defer stack, guaranteeing clean RAII-style cleanup upon function exit.
- **Verification & Zero Regressions**:
  - Full test suite expanded to 315 tests (209 core, 90 features, 16 v0.9.0 dedicated tests) with 100% pass rate.
  - Validated standalone end-to-end showcase `test_090.pengu` compiling cleanly to C99/C11 and executing via GCC.

## [0.8.4] - Released

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

### Call-argument type checking & imported enchanting methods

- **Function/method call arguments are now type-checked** (`E0005`): calling a
  weave or an `enchanting` method with a value that does not match the declared
  parameter type is a compile error that names the parameter, the expected type
  and the actual type — instead of silently generating C that fails at link
  time (e.g. passing a string where a `bool` is declared, or passing a `weave`
  where a `list of string` is expected). Same rules as assignments: numeric
  widening is allowed, unknown/type-param operands pass, `weave → ref to
  void` / `ref to weave` function-pointer decay stays legal, and native
  `list.push`/`map.put` diagnostics (`E0018`) are unchanged.
- **LSP resolves imported `enchanting` methods on unsaved buffers**: the
  semantic checker loads imported modules relative to the entry file, so when
  the editor validates a document that is not yet saved to disk the LSP now
  materializes a temporary shadow file — methods like
  `Parser.add_option` from `std.invoke` are no longer reported as missing
  (`E0004`) while typing, and genuine argument mistakes surface as precise
  diagnostics instead.

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
