# F7 — Per-module codegen and parallel C compilation

<!-- toc -->
- [What already landed](#what-already-landed)
- [Why the current design is a single translation unit](#why-the-current-design-is-a-single-translation-unit)
- [What is already in place](#what-is-already-in-place)
- [Target design](#target-design)
- [Implementation phases](#implementation-phases)
  - [Phase 1 — emitter plumbing (no behavior change)](#phase-1-emitter-plumbing-no-behavior-change)
  - [Phase 2 — driver and build cache](#phase-2-driver-and-build-cache)
  - [Phase 3 — correctness closure](#phase-3-correctness-closure)
  - [Phase 4 — performance](#phase-4-performance)
- [Acceptance criteria](#acceptance-criteria)
- [Risks and open questions](#risks-and-open-questions)
<!-- /toc -->

## What already landed

The emitter side is implemented and exercised:

* `bundle.generate_units_c` writes a `bundle.h` (includes, ABI pin, types,
  constants, clones, cleanups and every prototype), a `core.c` (JSON codec
  bodies and the `main` wrapper) and one `u<id>_<module>.c` per module.
* `codegen.api.generate_units` / `free_units` expose it, and
  `psc emit-c <entry> --split-dir DIR` writes the files.
* `tests/regress_split.sh` compiles the units separately, links and runs the
  result.
* The compiler itself (139 units) builds with `xargs -P 8`: ~5 s wall for the
  C compile step versus ~5.5 s for the single TU.
* Runtime globals that were `static` in `pengu_runtime.h` (`g_pengu_argc`,
  `g_pengu_argv`, `g_pengu_log_level`) are now `extern` and weakly defined in
  `runtime/pengu_runtime.c`; otherwise every unit had its own copy and
  `pengu_init` only initialised `core.c`'s.

The driver path is wired too: `psc build <project> --split-codegen --jobs=N`
writes the units under `build/units/`, compiles each with `-c` in a worker pool
and links the objects. It is opt-in for `exe`/native only; `obj`, `static`,
wasm and Windows stay on the single-TU path.

Each unit object is cached under `unit-object-v1` (header hash + unit source
hash + compiler + flags). With the cache warm, 137 of 137 units are reused and
the split build drops to **~14.8 s** versus **~19.9 s** for the single TU;
the first split build is ~23.9 s because all units compile.

The C step itself is ~5 s wall with 8 jobs, but every unit re-parses the
~5k-line header. The default remains the single TU until that cost is reduced.

Still pending: header slimming / PCH, parallel *codegen* (emission is still one
process), and wasm/Windows/static coverage.
so parallel C compilation actually wins, and parallel *codegen* (today emission
is still one process).

This document is the implementation plan for the remaining driver work. It is written against the current sources
(`src/psc/codegen/bundle.pengu`, `src/psc/driver/build.pengu`) so the next
change can start without re-discovering the seams. It is written against the current sources
(`src/psc/codegen/bundle.pengu`, `src/psc/driver/build.pengu`) so the next
change can start without re-discovering the seams.

## Why the current design is a single translation unit

`generate_bundle_c` emits one C file with, in order:

1. header includes and ABI pins,
2. forward type declarations, type definitions and aliases,
3. constants, derived clones and cleanup helpers,
4. JSON codecs (`derive Json`), antiquus bodies,
5. lambda prototypes,
6. every live function body (emitted into a temporary buffer first),
7. prototypes for every function in the catalog,
8. lambda bodies,
9. the `main` wrapper or the test runner.

Step 6 is emitted before step 7 because emitting a body can create new
specializations (receiver-dependent container methods), and those must appear in
the prototype block. The final order is still legal C: prototypes are spliced
before the buffered bodies. Splitting per module therefore cannot simply cut the
current string at module boundaries; the phases have to be re-grouped.

## What is already in place

* `CgFunction.module` identifies the owning `SemaModule`; `live_out` already
  records which modules have live functions.
* Bodies are emitted into a separate `StringBuilder` (`body_text`) before being
  appended, so the per-module buffers can replace that single buffer.
* `funcgen.signature` produces a declarator without a body, and
  `funcgen.emit_function` produces the definition. The same split exists for
  lambdas (`emit_prototype` / `emit_body`).
* `jsongen.emit_all` is the only mixed emitter: it writes prototypes and bodies
  in one call. It can be split into `emit_prototypes` and `emit_bodies` without
  changing codec logic.
* The cache key already hashes every module and every C input, so per-module
  cache entries can reuse the existing `cache.key` helper with a module prefix.

## Target design

Let `H` be a generated header and `M0..Mn` the module translation units.

```text
H: includes, ABI pins, types, aliases, constants, clones, cleanups,
   prototypes (normal, antiquus, JSON, lambdas)
M0: #include "bundle.h" + bodies of functions whose module == 0
...
Mn: #include "bundle.h" + bodies of functions whose module == n
core.c: #include "bundle.h" + JSON codec bodies + antiquus bodies +
        lambda bodies + main/test runner
```

The driver compiles `M0..Mn` and `core.c` as separate objects (in parallel with
`--jobs`), then links them into the final artifact. `build/bundle.c` can remain
as the concatenation for `--emit-c`/debugging compatibility, or be replaced by
`build/bundle.h` + `build/bundle.core.c`; `psc expand` keeps the single-TU path
until the split is stable.

## Implementation phases

### Phase 1 — emitter plumbing (no behavior change)

* Add `CgUnit {suffix, text}` and `CgMulti {header, core, modules}` to
  `psc/codegen/api.pengu`.
* Add `generate_units_c` that reuses the existing emission helpers but routes
  output to `H`, `core` and per-module emitters.
* Split `jsongen.emit_all` into `emit_prototypes` and `emit_bodies`; keep
  `emit_all` as a wrapper for the single-TU path.
* Emit antiquus and lambda prototypes into `H`; move their definitions to
  `core`.
* Make lambda symbols non-`static` (their names already include module and
  node, so they are unique per program). This is required for a lambda used by
  a module TU but defined in `core`.
* Guard the new path behind `--split-codegen`; the default stays single-TU.

### Phase 2 — driver and build cache

* In `BuildOptions`, add `split_codegen`, `jobs` (default 1).
* Write `build/bundle.h`, `build/bundle.core.c` and `build/<module>.c` (sanitize
  the logical module path into a file name; keep a map in `build/bundle.map`).
* Compile each unit with the existing flag list, then link. `--jobs N` uses
  `std.filum` worker threads (or a small process pool) and a bounded queue.
* Cache each unit by `cache.key(["unit", ck_sources, module_path, unit_hash])`;
  on a one-module edit, only that unit and the link are rebuilt.
* Keep the final-artifact cache (`psc-cache-2`) unchanged; add its key to the
  unit key so a compiler/flag change invalidates both.

### Phase 3 — correctness closure

* Compare single-TU and split artifacts in CI: build the same project both ways,
  run the test suite, and compare exit codes and stdout.
* Run the full regression suite with `--split-codegen` for at least the
  compiler, a JSON project, a coroutine project, a thread project and a wasm
  project.
* Require identical `sha256` for release builds (same toolchain, same flags) or
  document the difference if the linker orders symbols differently.

### Phase 4 — performance

* Measure `tools/bench.sh` with `--jobs 1/2/4/8`.
* Target: cold codegen+cc under 2 s for the compiler on 8 cores. The current
  single-TU baseline is ~20.5 s codegen + ~5.5 s cc (debug compiler).
* Keep the warm path (<2 s, ~0.2 s measured) untouched.

## Acceptance criteria

1. `psc build .` and `psc build . --split-codegen` produce a working compiler
   that passes `tests/run.sh` and `tests/regress.sh`.
2. `psc build . --split-codegen --jobs 4` on an 8-core machine is at least 2×
   faster in the codegen+cc phase than `--jobs 1`.
3. Editing one module rebuilds only that module's unit plus the link (verified
   by counting `cc:` lines with `--verbose`).
4. `--split-codegen` works for `exe`, `static` and `shared` outputs; wasm can
   stay single-TU until the emcc link path is validated.
5. `psc expand` and `--emit-c` keep the single-TU contract.

## Risks and open questions

* **Static state in generated helpers.** Any `static` variable emitted into the
  preamble would be duplicated per unit. Audit the preamble for mutable statics
  before enabling the split; immutable `static const` is fine.
* **Symbol visibility.** Lambdas and generated helpers that are currently
  `static` must become global (unique names) or stay in the unit that uses
  them. The latter needs a use graph, which DCE does not provide today.
* **JSON codecs** reference each other; keeping all definitions in `core`
  avoids one codec per module and keeps the split simple.
* **Generic specializations** are created during body emission. The header must
  be emitted after the discovery pass; do not move prototype emission before
  bodies.
* **DCE**: `reach` is global. Each unit must emit only live functions, but the
  header still declares all prototypes.
* **Windows / wasm**: the driver's object/link path differs; keep those targets
  on the single-TU path until CI covers them.
