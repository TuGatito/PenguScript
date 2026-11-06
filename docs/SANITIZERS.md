# Sanitizer profiles

<!-- toc -->
- [Quick start](#quick-start)
- [AddressSanitizer (ASan)](#addresssanitizer-asan)
- [UndefinedBehaviorSanitizer (UBSan)](#undefinedbehaviorsanitizer-ubsan)
- [ThreadSanitizer (TSan)](#threadsanitizer-tsan)
- [Profiles in `pengu.toml`](#profiles-in-pengutoml)
- [Limitations](#limitations)
- [Regression coverage](#regression-coverage)
<!-- /toc -->

PenguScript generates plain C, so the standard GCC/Clang sanitizers apply
directly. The compiler exposes them as first-class flags so the flags, the cache
key and the link line stay consistent.

## Quick start

```console
$ psc build . --sanitize=address      # ASan
$ psc test  . --sanitize=undefined    # UBSan
$ psc build . --sanitize=thread       # TSan
```

Each mode adds:

```
-g -fno-omit-frame-pointer -fsanitize=<kind>      # compile and link
```

`--sanitize` is part of the build-cache key, so an ASan binary and a plain
binary never alias, even for identical sources.

## AddressSanitizer (ASan)

Finds heap/stack overflows, use-after-free and double free.

```console
$ psc build . --sanitize=address --no-cache
$ ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 ./build/app
```

Recommended environment for CI:

```
ASAN_OPTIONS=detect_leaks=0:abort_on_error=1:symbolize=1
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
```

Leaks are detected by default on Linux. PenguScript frees its own allocations;
if a *third-party* C library leaks intentionally (for example a global cache),
disable leak detection for that job and document why.

## UndefinedBehaviorSanitizer (UBSan)

Catches signed overflow, misaligned access, invalid shifts/enums and similar
undefined behaviour. UBSan is cheap and can run in every CI job:

```console
$ UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 psc test . --sanitize=undefined
```

Combine ASan + UBSan by passing `--sanitize=address` and adding
`-fsanitize=undefined` to the profile `cflags`/`ldflags` in `pengu.toml`; the
driver already forwards both lists.

## ThreadSanitizer (TSan)

For `std.filum` programs and the runtime's thread pool:

```console
$ psc test . --sanitize=thread
```

**Fibers and TSan.** Stackful coroutines (`std.coro`, backed by minicoro) switch
stacks inside one OS thread. TSan models threads, not user-level stacks, so
fiber-heavy tests can produce false positives around `mco_resume`. Keep TSan
jobs focused on `filum` tests; use ASan/UBSan for coroutine tests. The runtime
regression suite follows this split (`tests/regress_threads_tsan.sh` vs
`tests/regress_coros_asan.sh`).

## Profiles in `pengu.toml`

If you prefer manifest-driven instrumentation (works with any `psc` command and
survives IDE integration):

```toml
[profiles.debug]
cflags = ["-g", "-O1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
ldflags = ["-fsanitize=address,undefined"]
```

Then `psc build . --profile=debug`. The built-in `--sanitize` flag is preferable
because it is validated, documented in `psc build --help`, and included in the
cache key automatically.

## Limitations

* TSan and ASan are mutually exclusive; one process, one instrumentation.
* Sanitizers require a native target. `wasm32-unknown-emscripten` does not
  support them.
* `-static` builds and sanitizers are incompatible on most glibc systems.
* MSan is not exposed as a flag (it requires an instrumented libc); use
  `cflags`/`ldflags` manually if you have one.

## Regression coverage

`tests/regress_sanitize.sh` builds a tiny project with ASan and UBSan and fails
if the instrumentation is missing or the binary does not run. The existing
`tests/regress_threads_asan.sh`, `regress_threads_tsan.sh`,
`regress_coros_asan.sh`, `regress_coros_tsan.sh` and `regress_json_std_asan.sh`
cover the runtime itself.
