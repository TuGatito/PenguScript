# PenguScript compiler architecture

This document maps the **implementation** of the PenguScript toolchain: which
Python file owns each stage of `parse → collect → check → infer → codegen →
cache`, which symbol is the entry point, what flows in and out, and where a
failure surfaces. It is descriptive, not normative, and is written against the
sources as of **v0.16.0**.

For the *language* read [`../LANGUAGE.md`](../LANGUAGE.md); for the runtime
contract, [`ABI.md`](ABI.md); for the dependency/runtime build,
[`PENGU_BUILD.md`](PENGU_BUILD.md). Where this document and the code disagree,
the code wins — and that disagreement is a bug in this file.

`pengu_project.py` is the CLI and the orchestrator; `pengu_parser/` holds the
front end and back end; `pengu_cache.py`, `pengu_bind.py`, `pengu_paths.py` and
`build_runtime.py` provide the surrounding services.

> Line numbers below are anchors into the tree as it stood when this was written
> (`v0.16.0`). The three largest files (`pengu_project.py`,
> `pengu_parser/pengu_checker.py`, `pengu_parser/pengu_codegen.py`) change often,
> so re-grep the symbol name if a cited line looks wrong — the symbol, not the
> number, is the contract.

---

## 1. Pipeline at a glance

```text
                  .pengu sources (+ pengu.toml / pengu.yaml)
                                |
  pengu_project.py:  main() -> build_project() -> PenguBuilder.compile()
                                |  (PenguBuilder.bundle loops over module_order)
                                v
  1 parse    PenguParser.parse()          [pengu_parser/pengu_parser.py]
               in source text | out lark.Tree | err ParseError E0000
                                v
  2 collect  resolve_imports()            [pengu_parser/pengu_symbols.py]
               out module_order (topological List[str])
               err SemanticError E0004 (missing module, import cycle)
             PenguChecker._collect_top_level()               (pass 1)
               out SymbolTable | err recorded by _record_error
                                v
  3 check    PenguChecker.check()         [pengu_parser/pengu_checker.py]
               _validate_declared_types() (1b), _check_node() (2)
               out errors: List[PenguError]
               err raises errors[0] carrying .all_errors/.rendered_all
                                v
  4 infer    TypeInferrer.infer()         [pengu_parser/pengu_infer.py]
               out pengu_types.Type
               err raises SemanticError; _check_node catches it and
                   calls _record_error, joining the errors list
                                v
  5 codegen  PenguCodegen.collect_declarations()/generate_bundle()
             [pengu_parser/pengu_codegen.py]
             + DCE: pengu_parser/pengu_dce.prune_weaves()
               out build/bundle.c | err raises SemanticError
                                v
  6 cc       build_compile_commands() -> gcc/clang/tcc -> build/app
               err CompileFailedError, remapped by remap_c_diagnostics()
                                v
  7 cache    pengu_cache.py + build/.bundle_hash (project builds)
```

Stages 1–4 run **once per module**, in `module_order`, inside a single loop in
`PenguBuilder.bundle()`. Stage 5 runs once for the whole program. The first
module is the entry module and the only one that may reset the symbol table
(`reset_symbols=(i == 0)`).

---

## 2. Stage map

| Stage | Principal file(s) | Entry symbol | Input | Output | Failures |
|---|---|---|---|---|---|
| **parse** | `pengu_parser/pengu_parser.py`, `pengu_parser/pengu_grammar.py` | `PenguParser.parse()` | PenguScript source `str` | `lark.Tree` (LALR(1)) | `ParseError` `[E0000]`, raised by `_parse_error()` |
| **collect (imports)** | `pengu_parser/pengu_symbols.py` | `resolve_imports()` | `base_dir`, `entry_file`, `PenguParser`, `lib_dir` | `List[str]` module paths, topological | `SemanticError` `[E0004]` (missing module, circular import) |
| **collect (symbols)** | `pengu_parser/pengu_checker.py`, `pengu_parser/pengu_symbols.py` | `PenguChecker._collect_top_level()` → `SymbolTable` | `Tree`, `import_order` | populated `SymbolTable` (`checker.symbols`) | accumulated in `errors`: `E0004`/`E0026`/`E0035`/`E0036`/`E0040`/`E0046`/`E0050`/`E0053`/`E0055`/`E0056` |
| **check** | `pengu_parser/pengu_checker.py` | `PenguChecker.check()` → `_validate_declared_types()`, `_check_node()` | `Tree`, source text, filename | `errors: List[PenguError]` (+ `warnings: List[str]`) | accumulates; raises `errors[0]` with `.all_errors`, `.rendered_all` |
| **infer** | `pengu_parser/pengu_infer.py`, `pengu_parser/pengu_types.py` | `TypeInferrer.infer()` | AST node, optional expected `Type` | `pengu_types.Type` | raises `SemanticError`; `_check_node` calls `_record_error()` |
| **codegen** | `pengu_parser/pengu_codegen.py`, `pengu_parser/pengu_dce.py` | `PenguCodegen.collect_declarations()`, `PenguCodegen.generate_bundle()` | `SymbolTable`, `[(path, Tree)]`, `CompileTimeEnv`, options | `build/bundle.c` | raises `SemanticError` |
| **cache** | `pengu_cache.py`, `build/.bundle_hash` | `script_cache_key()`, `PenguBuilder.is_bundle_up_to_date()` | content digests, flags, toolchain version | cache hit/miss, cached binary path | never fatal; degrades to "no cache" |
| **C toolchain** | `pengu_project.py`, `pengu_paths.py` | `PenguBuilder.compile()`, `build_compile_commands()` | `bundle.c`, flags, `libpengu_runtime.a` | exe / `.o` / `.a` / `.so` / `.c` | `CompileFailedError`; `remap_c_diagnostics()` re-points gcc/clang output at `.pengu` files |

---

## 3. Stage by stage

### 3.1 parse — `pengu_parser/pengu_parser.py`

`PenguParser` (line 94) wraps Lark in **LALR(1)** mode with a custom indenter
(`PenguIndenter`, line 38) and `start=['start', 'expr']`, so it also serves
`parse_expr()` for `pengu eval`. The grammar is the module-level string `GRAMMAR`
in `pengu_parser/pengu_grammar.py` (line 9, closed at line 572);
`SIMPLE_STMT_ALIASES` (line 578) is a normalisation table shared by the checker
and the code generator.

Parser tables are cached: `__init__` passes
`pengu_cache.parser_cache_path(grammar_digest(GRAMMAR))` to Lark as `cache=`, and
a missing, corrupt or unwritable cache drops the kwarg and rebuilds in memory, so
editing `pengu_grammar.py` cannot silently reuse stale tables. `parse()`
(line 391) runs `strip_bom`, normalises CRLF, records style warnings from
`_check_indentation_consistency()` into `self.warnings`, then `_strip_comments()`.

**Failure** is always `pengu_errors.ParseError` (`[E0000]`) from `_parse_error()`
(line 469); Lark's `UnexpectedInput`/`BaseError` never leak. `PenguParser.warnings`
is populated but **not consumed by the build pipeline** — its `[W0005]`
indentation warning only reaches the user through the `warnings` module (§4).

### 3.2 collect — import graph and symbol tables

`resolve_imports()` (`pengu_parser/pengu_symbols.py`, line 654) parses the entry
file, walks `import_stmt` nodes, resolves each dotted path with
`find_module_path()` (line 548) — std directories first from `get_stdlib_dirs()`
(line 512, delegating to `pengu_paths.std_dirs()`), then the project `lib_dir`
and the shadowing `src/` layout — and returns a **topologically sorted**
`List[str]` of absolute module paths. A missing module raises `SemanticError`
`[E0004]`; a cycle raises the same code with the cycle rendered (line 726).
`pengu_cache.resolve_module_list_cached()` (line 286) can front this for
`pengu run <script>`.

`PenguChecker._collect_top_level()` (line 827) is pass 1 of the checker: it
registers runes, echos, omens, aliases, weaves, enchantings, concepts, constants
and imports in the `SymbolTable` (`pengu_parser/pengu_symbols.py`, line 153), and
reads the module-wide `insignia` C prefix (`insignia_stmt`, line 863) — each later
declaration gets `c_name = f"{insignia}{name}"`, and only one `insignia` per file
is allowed (`[E0026]`, line 869). `SymbolTable` holds nested `Scope`s (line 67),
the builtin prelude (`_init_builtins`, line 203) and the lookup helpers
(`lookup`, `lookup_local`, `lookup_type`, `lookup_concept`, `lookup_seal`,
`current_return_type`, ...). The inferrer and codegen read this same object, which
is why the checker must finish first.

**Failure** here is *recorded*, not raised: `_make_error(...)` then
`_record_error(err)` appends to `self.errors`, so collection keeps going and every
problem is reported at once.

### 3.3 check — `pengu_parser/pengu_checker.py`

`PenguChecker.check()` (line 409) resets `errors`/`warnings`/`const_definitions`,
then runs `_collect_top_level()` (pass 1), `_check_omen_variant_collisions()`
(line 7071), `_validate_declared_types()` (pass 1b, line 5176, now that every type
name is known) and `_check_node()` (pass 2, line 2208) — the recursive body walk
covering mutability, ownership (`banish`, `borrowed`), control flow, `with:`
builders, `judge` exhaustiveness, concept bounds, deprecation (`[W0006]`) and
`unsafe:` blocks (`[W0007]`). It then folds in `self.inferrer.warnings` and, if
anything was recorded, renders every error with an `ErrorReporter`, attaches
`first_err.all_errors = self.errors` and `first_err.rendered_all`, and **raises
the first error** (lines 473–478).

That contract is why `PenguBuilder.check_sources_diagnostics()` (line 1300) reads
`exc.all_errors`: one exception yields N diagnostics. It never generates C and
memoises its result in `self._diagnostics_cache`, converting warning strings back
into dicts with the regex
`\[(W\d{4})\]\s*(.*?)(?:\s+on line\s+(\d+)(?:\s+col\s+(\d+))?)?$` — the
`on line L col C` suffix is appended by `TypeInferrer._warn()`
(`pengu_parser/pengu_infer.py`, line 449), because warnings are plain strings.

### 3.4 infer — `pengu_parser/pengu_infer.py`

`TypeInferrer` (line 413) is created by `PenguChecker.__init__` (line 405) and
**re-created** at the start of every `check()` (line 452) so it shares the fresh
symbol table. `infer()` (line 850) is a bottom-up recursion: given an AST node and
an optional expected `Type`, it returns a `Type` from
`pengu_parser/pengu_types.py`. `ConstFolder` (line 145) folds constants;
`eval_comptime()`/`CompileTimeEnv` come from `pengu_parser/pengu_comptime.py`;
concept bounds go through `check_generic_bounds()` (`pengu_types.py`, line 2004)
and surface as `[E0032]`/`[E0049]`. Diagnostics use the inferrer's own
`_make_error()` (line 517) and are **raised immediately** — inference has no
accumulator. `_check_node` wraps inferrer calls in `try/except SemanticError` and
calls `self._record_error(e)` (e.g. lines 2585–2586, 4110–4111): **the inferrer
raises, the checker accumulates.** Warnings go through `_warn()` (line 449) —
`[W0001]` transmute, `[W0002]` echo union access, `[W0006]` deprecation,
`[W0013]` `..` ranges.

### 3.5 codegen — `pengu_parser/pengu_codegen.py`

`PenguBuilder.bundle()` constructs `PenguCodegen(checker.symbols, module_order,
base_dir, compile_env=..., use_gnu_extensions=..., target_compiler=...)` (class
line 434, `__init__` line 436), copies the runtime header into the build
directory, then `collect_declarations(parsed_trees)` (line 1999) — registering
runes, echos, omens, aliases, consts, weaves, enchantings and `test` blocks from
the trees the checker already parsed (reused, not re-parsed) — and
`generate_bundle(...)` (line 9829), which emits `build/bundle.c` in fixed
sections: banner, `#include "pengu_runtime.h"`, the ABI `_Static_assert` and
`pengu_abi_version` pin, custom includes, forward declarations, type definitions,
prototypes, bodies in topological order, and `generate_entry_point()` (line 9614)
or `generate_test_entry_point()` (line 9799) in `--test` mode. Statements and
expressions go through `_translate_stmt_impl()` (line 4283) and
`_translate_expr_impl()` (line 7010).

Dead-code elimination runs **first** in `generate_bundle()` (line 9861), before
any section is emitted, so prototypes and definitions stay consistent:
`pengu_parser.pengu_dce.prune_weaves()` (line 175), rooted at
`collect_references()` (line 97) plus the references of every `test` block.
`PENGU_NO_DCE=1` disables it; statistics land in `codegen.dce_stats`. The
generated C carries `#line N "source.pengu"` markers, so native diagnostics land
on the `.pengu` file the user wrote. `build_runtime.py` is *not* part of a normal
build — it is the maintainer/CI step that produces `build/lib/libpengu_runtime.a`
(§7).

### 3.6 C toolchain — `pengu_project.py`

`PenguBuilder.compile()` (line 1949) is the last stage that can fail before a
binary exists. For `OutputType.C` the bundle *is* the artifact and it stops there;
a cached bundle is only trusted if the binary is at least as new as the bundle
(line 1973). `_find_runtime_archive()` (line 2655) pre-flights
`libpengu_runtime.a`, so a missing archive is an actionable message instead of an
`undefined reference` for `pengu_abi_version`. `build_compile_commands()`
(line 1488) assembles the command lines (base + profile flags, includes from
`collect_include_dirs()`, links from `collect_lib_dirs_and_links()`,
`_msvc_command()` line 1433 for MSVC); each runs with `subprocess.run` and the
first non-zero exit becomes a `CompileFailedError` (line 549). A development
compiler (TCC, via `pengu_tcc.pick_dev_compiler`) is retried once with the
configured compiler.

`main()` (line 5840) routes `build` to `build_project()` (line 2169), `check` to
`check_project()` (line 2333) or `check_files()` (line 2484), script execution to
`run_script()` (line 4701), and `_print_compile_error()` (line 5746) renders a
`CompileFailedError` after `remap_c_diagnostics()` (line 5722) rewrote
`bundle.c:LINE:COL` back to `.pengu` positions.

### 3.7 The language server — `pengu_lsp/`

`pengu lsp` (`create_cli_parser()`, line 5354; dispatch at line 6175) imports the
module-level `server` object (`pengu_lsp/server.py`, line 325, an instance of
`PenguLanguageServer`, line 231) and starts it over stdio or TCP;
`pengu_lsp/__main__.py` (`main()`, line 21) does the same for `python -m pengu_lsp`.
`_compute_diagnostics()` (line 461) **reuses the front end directly** — a fresh
`PenguParser()` plus `PenguChecker(base_dir=..., lib_dir=...)`, then
`parse()` + `check()` — and converts failures with `diagnostics_from_errors()`
(line 155); checker `[Wxxxx]` warnings are **not** published by the LSP today.

---

## 4. Diagnostic model

Every language-level error derives from `PenguError`
(`pengu_parser/pengu_errors.py`, line 5), carrying `code`, `message`, `file`,
`line`, `col`, `snippet`, `span_start`, `span_end`, `help`, `note`, `label` and
the accumulation slots `all_errors` / `rendered_all`. `SemanticError` (line 71)
is the general subclass; `ParseError` (line 105) specialises it for `[E0000]`.

**Creation.** The checker and the inferrer both build errors through a private
`_make_error(err_cls, message, node=None, **kwargs)`:
`pengu_parser/pengu_checker.py` line 604 and `pengu_parser/pengu_infer.py`
line 517. Each resolves `(line, col)` from the node via `_get_loc()`, derives
`span_start`/`span_end` (token length or `meta.end_column`), slices the snippet
from the source, and defaults `file`/`snippet`. Convenience builders add the
domain help text: `_make_undefined_error()` (checker line 642, infer line 545)
attaches fuzzy suggestions from `pengu_errors.suggest_similar_identifier()`
(line 500); `_make_type_mismatch_error()` (checker line 670) chooses between
`to <Type>` conversion help and string-interpolation help.

**Accumulation.** `PenguChecker._record_error(err)` (line 701) is the single sink
(`self.errors.append(err)`), and pass 2 uses it to absorb every `SemanticError`
the inferrer raises. `PenguChecker.check()` then raises `self.errors[0]`
**after** attaching the whole list to `.all_errors` and the pre-rendered
multi-error text to `.rendered_all`, so one exception can be treated as a batch.
`PenguBuilder.check_sources_diagnostics()` (line 1300) normalises everything —
including `EntryPointNotFoundError` and warning strings — into dicts with keys
`file, line, col, code, severity, message, help, note`, which is what
`pengu check --json` and `build_project(json_output=True)` serialise as JSON
Lines.

**Rendering.** `ErrorReporter` (`pengu_parser/pengu_errors.py`, line 507) renders
the Rust-style block: `error[E0006]: ...`, a `--> file:line:col` line, a gutter
with the offending source line, caret underlines sized from
`span_start`/`span_end`, and optional `note:` / `help:` lines. `report()`
(line 521) is one error, `report_all()` (line 572) is many; `PenguError.render()`
is the per-error shortcut. ANSI colour is opt-out (`NO_COLOR`,
`pengu --no-color`).

**Catalogues.**

The catalogue is **generated** from the sources by
[`../tools/gen_error_catalog.py`](../tools/gen_error_catalog.py) — do not edit
[`../LANGUAGE.md`](../LANGUAGE.md) §22.2/§22.3 by hand. `python
tools/gen_error_catalog.py --write` regenerates both the document and
[`error_catalog.json`](error_catalog.json); `--check` is the CI gate, and
`tests/test_error_catalog_sync.py` fails when they drift.

| Range | Owner | Notes |
|---|---|---|
| `E0000`–`E0058` | language front end | §22.2 of [`../LANGUAGE.md`](../LANGUAGE.md). Emitted through the `code=` keyword, so this is the range a language tool sees. `E0000` parse, `E0001`/`E0002` top-level placement, `E0004` undefined identifier / import graph, `E0005` type mismatch, ... `E0058` `error` outside `or:`. |
| `E0063` | language front end | `StaticVarPlacementError` — `'static var'` outside a function body. Added by roadmap item 7.2. |
| `E0064` | language front end | `InvalidTestNameError` — a `test` block with no usable name. Added by roadmap item 7.2. |
| `E0065` | language front end | `CFieldCollisionError` — two user fields map to the same C identifier. Added by roadmap item 7.2. |
| `E0061` | project layer, `pengu_project.py` | `pengu.lock` missing/out of date under `--locked`/`--frozen` (`_ensure_lockfile`, line 2082). Emitted as a plain `"[E0061] …"` string, **not** through `code=`. Not a language code. |
| `E0062` | project layer, `pengu_semver.py` | `DependencyConflictError` (line 201) for unsatisfiable version constraints. Also a plain string prefix. Not a language code. |
| `W0001`–`W0013` | front end | §22.3 of [`../LANGUAGE.md`](../LANGUAGE.md). `W0001` transmute, `W0002` untagged `echo` access, `W0003` reserved, `W0004` unreachable code, `W0005` shadowed global, `W0006` `@deprecated` use, `W0007` `unsafe:` block, `W0013` `..` range syntax. The symbolic names and recommended practices live in `WARNING_CATALOG` in `pengu_parser/pengu_errors.py`. |

> **The `Exxxx` namespace is shared between two layers**, and this is a live
> hazard: the language front end emits `code=` keywords (`E0000`–`E0058`,
> `E0063`–`E0065`) while the project layer prints `[Exxxx]` strings (`E0061`,
> `E0062`). `tests/test_error_catalog_sync.py::test_language_and_project_codes_are_disjoint`
> fails if the two ever overlap — during roadmap item 7.2 a new language error was
> very nearly assigned `E0061`, which the lockfile already owned.

Two caveats the catalogues do not state:

1. **`W0005` covers two unrelated things.** The checker uses it for a local
   shadowing a global weave (`pengu_parser/pengu_checker.py`, lines 4017, 4373),
   matching the catalogue; the *parser* also uses `[W0005]` for inconsistent
   tab/space indentation (`pengu_parser/pengu_parser.py`, line 147), surfaced
   only through the `warnings` module — which the build pipeline does not read,
   so that warning is effectively invisible.
2. **`W0008`–`W0012` have no emitter.** The only occurrence of `W0012` is a
   comment in `pengu_parser/pengu_infer.py` line 4326; `W0000` is a fallback used
   by `check_sources_diagnostics()` when a warning string does not match the
   `[Wxxxx]` shape.

Warnings never stop a build unless `--deny-deprecated` promotes `[W0006]` to an
error: `build_project()` re-labels the diagnostic inside
`check_sources_diagnostics()` and aborts in `_report_denied_deprecations()`
(line 2138) / `enforce_deny_deprecated()` (line 2157).

---

## 5. Build cache and incremental builds

`pengu_cache.py` owns three XDG-compliant caches rooted at `cache_root()` (line
56: `$PENGU_CACHE_DIR`, else `~/.cache/pengu`, `%LOCALAPPDATA%`, or
`~/Library/Caches`). `PENGU_CACHE=0` disables them all; a read-only root falls
back to a per-user temp directory instead of failing a build.

| Sub-cache | Path | Key | Written by |
|---|---|---|---|
| Lark tables | `parser/grammar-<digest16>.lark` | `grammar_digest(GRAMMAR)` (line 123); Lark re-validates against grammar + options + Lark/Python version | `PenguParser.__init__` via `parser_cache_path()` (line 115) |
| Script binaries | `scripts/<key>/app[.exe]` | `script_cache_key()` (line 137) | `store_cached_binary()` (line 203), read by `lookup_cached_binary()` (line 195) |
| Import lists | `imports/<entry-digest>.json` | content digest of the entry plus every resolved module | `store_module_list()` (line 260), read by `load_module_list()` (line 227) |
| `std/` | — | reserved for future pre-parsed std blobs | — |

**What the script key includes.** `script_cache_key()` is a SHA-256 over, in
order: toolchain `version`, C compiler (`cc`), `profile`, sorted `defines`,
sorted `links`, sorted `cflags`, the normcased absolute entry path, every
module's absolute path **and content digest**, the content digest of
`pengu_runtime.h`, and any `extra_digests`. `run_script()` (line 4701) passes the
build-shaping flags as `extra_digests` — `dce=off`, `release-unsafe`,
`PENGU_CFLAGS`, `strict-c99`, the target compiler dialect, the target triple —
which is why a debug/DCE-off/sanitizer build cannot collide with a plain one. It
is keyed on **content, never mtimes**.

**Project builds: `build/.bundle_hash`.** For `pengu build` the incremental
decision lives in the build directory, not the XDG cache.
`PenguBuilder.bundle()` writes `<build>/.bundle_hash` with two space-separated
tokens (`pengu_project.py`, line 1291):

```text
<config hash> <sources fingerprint>
```

`compute_config_hash()` (line 664) hashes profile, cflags/ldflags/defines/
includes/links, output type, test mode, entry-as-main, compiler, include/lib
dirs, asset embedding options, `strict_c99`, `release_unsafe`, target and target
compiler, and `PENGU_CFLAGS`/`PENGU_LDFLAGS`. `compute_sources_fingerprint(
module_order)` (line 695) hashes the resolved entry path, each module's relative
path and content, every project C source, the embedded-asset contents and the
`.incbin` threshold.

`is_bundle_up_to_date()` (line 1099) returns `False` — rebuild — unless the file
exists, the saved key has exactly two tokens (a one-token file is the old
config-hash-only format and is treated as stale), *and* both tokens match. On top
of the content hashes it still compares mtimes for C glue files, headers in the
include dirs, the manifest files and `pengu_runtime.h`, because content-hashing
every header would cost more than the rebuild it avoids.

**Why a stale cache must not produce a stale binary.** `build/bundle.c` and
`build/app` are shared by every program built in the same directory, and the old
key was the config hash alone — so a *different* program's older bundle could
look up to date and its binary would be reused. Two guards close that hole: the
fingerprint is over **contents**, including the normcased entry path, so a cache
hit is always the right program (`compute_sources_fingerprint()`'s docstring
names the stale-binary bug it fixes); and even on a bundle cache hit,
`PenguBuilder.compile()` compares mtimes and rebuilds when the regenerated bundle
is newer than the binary, because "the bundle being up to date is not enough: the
artifact must have been produced *from* it".

Maintenance: `clear_script_cache()` (line 300), `gc_script_cache()` (line 317),
`cache_summary()` (line 342, used by `pengu doctor`).

---

## 6. The FFI boundary: `.d.pengu` declaration files and `insignia`

A C library becomes usable from PenguScript through a **`.d.pengu` declaration
file**: a `.pengu` module that may contain types and `declare` signatures but no
implementation bodies. The checker enforces this by filename — `is_d_pengu =
self.filename.endswith(".d.pengu")` (`pengu_parser/pengu_checker.py`, line 838) —
and rejects bodies (`[E0025]`) at lines 1911, 2067 and 5460. The same flag
relaxes C-reserved-name checks, since a declaration file is *supposed* to name C
symbols.

`insignia` is the module-wide C prefix declared in such a file. It is parsed in
`_collect_top_level()` (line 863), stored on `SymbolTable.insignia`, and applied
to every `c_name` the checker mints, so the generated C calls
`<insignia><name>` while PenguScript code uses the bare name. Exactly one
`insignia` per file is allowed (`[E0026]`, line 869).

Generation is `pengu_bind.py`:

1. **`preprocess_and_parse()`** (line 1205) runs the C preprocessor over the
   header and parses the result with `pycparser`, under a sandbox
   (`_sandbox_environment()`, `_reject_unsafe_includes()`, header-size cap).
2. **`BindGenerator`** (line 173) walks the C AST and emits PenguScript for
   enums, structs/unions, typedefs and prototypes (`_emit_enum`, `_emit_struct`,
   `emit_typedef`, `emit_function`), plus `link` lines, constants and inferred
   `import` lines from `discover_binding_headers()` (line 478).
3. **`generate_bind_file()`** (line 1375) is the public API, wired to the
   `pengu bind` subcommand in `pengu_project.py` (line 6099). It writes
   `<stem>.d.pengu` next to the header, or wherever `--output` says, and returns
   the path. `HeaderParseError` (line 107) is the failure type.

Supporting pieces: `c_bind_stubs/` holds minimal C stub headers used when the
real system headers are unavailable (`_default_stub_dir()`, line 1060);
`migrate_manual_bindings.py` and `regen_std_bindings.py` are one-off migration
and regeneration scripts for the shipped `std/` bindings, not part of a build.
`pengu_paths.py` is the layout oracle the whole toolchain shares:
`runtime_include_dirs()` (line 117), `runtime_lib_dirs()` (line 162),
`std_dirs()` (line 210), `find_runtime_header()` (line 298), `find_std_dir()`
(line 321), plus cached `pkg-config` helpers (line 376).

The result: a `.pengu` module becomes C by *declaration only* — the compiler
emits prototypes and calls under the `insignia` prefix, and the linker resolves
them against the native library named in `link`, exactly like any other C
translation unit.

---

## 7. The runtime / ABI boundary

The runtime ships as a header plus a static archive:

* **`pengu_runtime.h`** (repository root) is the public contract: container
  layouts, helper declarations, `#define PENGU_ABI_VERSION 1` (line 58) and
  `int pengu_abi_version(void);` (line 77).
  `PenguBuilder.locate_and_copy_runtime()` (line 851) copies it next to
  `bundle.c` — a project-local vendored copy wins, otherwise
  `pengu_paths.find_runtime_header()` decides.
* **`pengu_parser/pengu_runtime.c`** is the implementation. It is compiled by
  `build_runtime.build_pengu_runtime()` (line 1171) into
  `build/lib/libpengu_runtime.a`, and also copied to `build/include/`.
  `build_runtime.build_runtime_pch()` (line 1234) optionally produces
  `pengu_runtime.h.gch`; `build_runtime.main()` (line 1293) first downloads and
  extracts the external C dependencies through
  `extern_manifest.download_and_extract_externs()` (line 65) before building
  zlib, pcre2, mbedtls, curl, sqlite3 and friends.
* **`libpengu_runtime.a`** is located at link time by `runtime_lib_dirs()`
  (`pengu_paths.py`, line 162) and pre-flighted by `_find_runtime_archive()`
  (`pengu_project.py`, line 2655).

The two-way pin is generated into every bundle by `generate_bundle()`
(`pengu_parser/pengu_codegen.py`, lines 9906–9921):

```c
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(PENGU_ABI_VERSION == 1,
    "pengu_runtime.h ABI mismatch: bundle expects v1");
#endif
extern int pengu_abi_version(void);
#if defined(__GNUC__) || defined(__clang__)
__attribute__((used))
#endif
static int (*const _pengu_abi_pin)(void) = pengu_abi_version;
```

The expected number is `PENGU_EXPECTED_ABI_VERSION`
(`pengu_parser/pengu_codegen.py`, line 32), consumed by
`PenguCodegen.expected_abi_version` (line 461). The `_Static_assert` catches a
bundle compiled against a mismatched header; the forced `_pengu_abi_pin`
reference guarantees the archive is actually pulled in, so a stale
`libpengu_runtime.a` fails at **link** time instead of silently reinterpreting
struct fields at runtime.

The policy — what bumps `PENGU_ABI_VERSION`, what explicitly does not, and how
each guarantee is verified per compiler — is documented in [`ABI.md`](ABI.md) and
deliberately **not duplicated here**. Runtime build layouts are in
[`PENGU_BUILD.md`](PENGU_BUILD.md) §4.

---

## 8. Where to make a change

Order matters: each row assumes the previous ones are done.

| Change | Touch, in order |
|---|---|
| **New syntax form** | 1. `pengu_parser/pengu_grammar.py` — add the rule to `GRAMMAR` (and to `SIMPLE_STMT_ALIASES` if it is a simple statement). 2. `pengu_parser/pengu_parser.py` — only if it needs preprocessing/indentation handling. 3. `pengu_parser/pengu_checker.py` — handle the new `node.data` in `_collect_top_level()` and/or `_check_node()`. 4. `pengu_parser/pengu_infer.py` — teach `infer()` its type. 5. `pengu_parser/pengu_codegen.py` — emit C in `_translate_stmt_impl()` or `_translate_expr_impl()`. 6. `LANGUAGE.md`, `CHEATSHEET.md`, tests under `tests/`. |
| **New diagnostic** | 1. `pengu_parser/pengu_errors.py` — add the `PenguError` subclass (or reuse `SemanticError`) with a default `code`. 2. Take the next free code and add it to `LANGUAGE.md` §22. 3. Raise it at the site: `self._record_error(self._make_error(...))` in the checker, or `raise self._make_error(...)` in the inferrer/codegen. 4. Add a test asserting the code reaches `checker.errors` / CLI output. |
| **New warning** | 1. `LANGUAGE.md` §22.3 table. 2. Emit `"[Wxxxx] message"`; from the inferrer use `TypeInferrer._warn()` (`pengu_parser/pengu_infer.py`, line 449) so the `on line L col C` suffix is attached — otherwise it renders as `file:0:0`. 3. From the checker append to `self.warnings` with the same suffix convention. 4. To make it deniable, follow the `W0006` path: `deny_deprecated` handling in `check_sources_diagnostics()` + `_report_denied_deprecations()`. |
| **New codegen construct** | 1. `pengu_parser/pengu_codegen.py` — extend `collect_declarations()` if it introduces a declaration, and the relevant `generate_*` section or `_translate_*_impl()` if it is a statement/expression. 2. `pengu_parser/pengu_types.py` — add the `Type` subclass plus `mangle_type()`/`estimate_size()` handling if it has a new type. 3. `pengu_parser/pengu_dce.py` — update `collect_references()` if it can reference a std weave. 4. `pengu_parser/pengu_symbols.py` — only if it needs a new symbol kind. |
| **New `when` predicate / compile-time variable** | 1. `pengu_parser/pengu_comptime.py` — extend `CompileTimeEnv`, `default_env()`, `parse_cli_defines()` and `eval_comptime()`. 2. `pengu_project.py` — thread the value through `PenguBuilder.__init__` (the `compiler=`/`debug`/`main` handling there is the model). 3. Document it in `LANGUAGE.md`. |
| **New cache input** | 1. `pengu_project.py::compute_config_hash()` (project builds) and/or the `extra_digests` list in `run_script()` (script builds). 2. `pengu_cache.py::script_cache_key()` only if the input is global rather than per-invocation. |
| **Change the emitted C ABI** | 1. `pengu_runtime.h` — the layout and `PENGU_ABI_VERSION` (bump it for a breaking change). 2. `pengu_parser/pengu_runtime.c`. 3. `pengu_parser/pengu_codegen.py::PENGU_EXPECTED_ABI_VERSION`. 4. `docs/ABI.md`. 5. `build_runtime.py` if the build flags change. |
| **New C binding for `std/`** | 1. `pengu bind <header> --prefix <insignia>` to produce the `.d.pengu` (`pengu_bind.generate_bind_file()`), or run `regen_std_bindings.py` for the standard set. 2. Add the archive to `link` and the headers to `include_dirs` where the module is used. |

Repository-wide checks that catch drift between these files: the suites under
`tests/` (in particular the diagnostic-code, deprecation-table and
line-directive tests) and `pengu doctor` (`pengu_project.py::doctor_report()`,
line 4357), which reports the cache layout and warns when `libpengu_runtime.a`
has not been built.
