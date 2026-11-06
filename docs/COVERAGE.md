# Coverage (`psc test --coverage`)

<!-- toc -->
- [Usage](#usage)
- [Requirements](#requirements)
- [What is measured](#what-is-measured)
- [Limits](#limits)
- [CI recipe](#ci-recipe)
<!-- /toc -->

`psc test --coverage` instruments the generated C bundle with GCC/Clang's
`gcov` support and reports coverage **against the original `.pengu` lines**.

The generated C carries `#line N "src/foo.pengu"` markers (see
`docs/psc/CODEGEN.md`), so `gcov` attributes every counter to the PenguScript
file and line that produced it. No source maps, no post-processing step and no
extra tool are required.

## Usage

```console
$ psc test . --coverage
$ psc test . --coverage --profile=release
$ psc test . --coverage --target=wasm32-unknown-emscripten   # not supported
```

Coverage forces a fresh build (the cache is bypassed) because the instrumented
object files and `.gcda` counters must match the current source tree.

After the tests run, `psc` invokes `gcov -b` on the bundle object. The raw
counters live next to the artifact; `gcov` writes the readable `.gcov` reports
in the current directory (the project root):

```
build/app_test-bundle.gcno
build/app_test-bundle.gcda
main.pengu.gcov
pengu_runtime.h.gcov
```

`psc` also prints a compact per-module summary, filtering out runtime headers:

```console
$ psc test . --coverage
coverage: src/main.pengu  83% (10/12 lines)
coverage: src/lib.pengu   60% (6/10 lines)
```

Rename, move or archive the `.gcov` files in CI. If you invoke `gcov` yourself,
force the C locale (`LC_ALL=C gcov -b -o build build/app_test-bundle.gcno`),
because its summary labels are translated.

```console
$ LC_ALL=C gcov -b -o build build/app_test-bundle.gcno
$ grep -E '^(File|Lines executed|Branches executed)' *.pengu.gcov
```

## Requirements

* `gcc` (or `clang` with `--coverage` support) and the matching `gcov` binary in
  `PATH`. On macOS the Homebrew `gcc`/`llvm` toolchains provide both.
* The `debug` or `release` profile; coverage adds `-g --coverage
  -fprofile-arcs -ftest-coverage` automatically.

If `gcov` is missing, `psc test` still runs the tests but prints a warning and
does not claim coverage was produced.

## What is measured

* Every executable line of every project module reachable from the entry point.
* Branch counts (`-b`) for `if`/`while`/`match` conditions.
* Runtime and `std_c` headers are also instrumented by GCC and produce
  `pengu_runtime.h.gcov`; the summary printed by `psc test --coverage` filters
  them out, but the raw file remains next to the report.

## Limits

* Line coverage of a `.pengu` file is only meaningful for functions that were
  emitted. Code removed by dead-code elimination (or never reachable from the
  entry point) has no counters and appears as if it did not exist.
* `-O2` may merge or reorder lines. Use the default `debug` profile for
  line-accurate reports.
* `gcov` versions differ in their HTML/JSON output; the raw `.gcov` text format
  used here is stable across GCC 9+ and LLVM.
* WebAssembly targets (`emcc`) are not supported by `--coverage` yet; the
  command prints a clear error instead of producing bogus numbers.

## CI recipe

```yaml
- run: psc test . --coverage
- run: |
    total=$(grep -h 'Lines executed' src/*.pengu.gcov | sed 's/.*://; s/%.*//' | awk '{s+=$1; n++} END {print s/n}')
    echo "line coverage: ${total}%"
```

Keep `.gcno`/`.gcda` out of version control (they are already covered by the
`build/` ignore rule).
