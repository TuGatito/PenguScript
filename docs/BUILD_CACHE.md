# Incremental builds and the artifact cache

<!-- toc -->
- [What is in the key](#what-is-in-the-key)
- [Fast path](#fast-path)
- [Explaining a miss](#explaining-a-miss)
- [Commands](#commands)
- [Writing entries](#writing-entries)
- [Measuring](#measuring)
- [Reproducibility](#reproducibility)
- [Troubleshooting](#troubleshooting)
<!-- /toc -->

PenguScript caches the final executable (or library/object) keyed by a hash of
everything that can change the output. A warm build of the compiler itself takes
**~0.3 s** instead of ~30 s.

## What is in the key

The cache key is a SHA-256 over, in a fixed order:

* compiler binary bytes (or its path if the binary cannot be read),
* cache schema version (`psc-cache-2`),
* target triple, wasm target, OS, architecture,
* `cc`, `--profile`, `--cc` override,
* output kind and name, `--test`, `--json`, `--strict`, `--unsafe`,
  `--no-dce`, `--prune-types`, `--no-line-markers`, `--force-exe`,
  `--no-lines`-family flags,
* every project and dependency `cflags`, `links`, `lib_dirs`, `ldflags`,
  `defines`,
* `pengu.toml`, `pengu.lock` and the entry file,
* the **content** (path + bytes) of every `.pengu` file in `src_dir`,
  `lib_dir` and dependency source trees, plus the standard library,
* C sources (`c_dir`), headers (`include_dir`), assets (`assets_dir`),
* runtime archive, wasm shell, JS prelude/library.

The project `build_dir` is deliberately **excluded**. Build outputs do not
invalidate the cache, so touching `build/unrelated.txt` is free. `.git`,
`node_modules` and `.cache` are skipped.

## Fast path

The key is computed **before** semantic analysis and code generation. On a hit
the driver:

1. copies the cached artifact to the output path (atomically, so concurrent
   builds cannot read a partial file),
2. applies the executable bit,
3. returns without parsing, checking or generating C.

That is why a hit costs milliseconds even for the 50 kLOC compiler. On the
previous design the key was computed after codegen, so every "hit" still paid
~20 s of code generation.

If the output path is the currently running binary (rebuilding `psc` with
`psc`), `rename`/copy fails with `ETXTBSY`; the driver then compares the cached
bytes with the running executable and treats an identical artifact as a hit.

`psc check` uses the same pre-sema key with the fixed output kind `check` and
stores an empty marker (`cache.mark`). A second check of an unchanged project
skips parsing and sema entirely: `psc check .` drops from ~1.9 s to ~0.18 s.
A source/flag/runtime change changes the key, so a stale marker can never hide
a new diagnostic.

## Explaining a miss

The cache is keyed per program, but a miss should never be a mystery. After
semantic analysis the driver stores the `path<TAB>sha256` of every loaded
module in `build/.psc-modules`; the next build compares against that snapshot
and, with `--verbose`, prints exactly what invalidated the key:

```console
$ psc build . --verbose
cache: key=...
cache: module changed src/lib.pengu
```

Added and removed modules are reported too. This is diagnostic only: the key
still covers the whole program, and the fingerprint file lives in the build
directory, which is excluded from the key.

## Commands

```console
$ psc build .                    # uses the cache
$ psc build . --no-cache         # force a rebuild, still writes the entry
$ psc build . --clear-cache      # empty the cache, then build
$ psc build . --ephemeral        # read the cache, do not write it
$ psc gc                         # prune entries older than 30 days
$ psc gc --max-age=7             # prune older than a week
$ psc check .                    # 2nd run hits the check marker (<0.2 s)
$ psc gc --max-size=2048         # arbitrary entries until the cache is <= 2 GiB
$ psc gc --all                   # remove every entry
$ psc gc --json                  # machine-readable summary
```

The cache lives in `$PSC_CACHE_DIR`, else `$XDG_CACHE_HOME/pengu/psc`, else
`~/.cache/pengu/psc`, else `/tmp/pengu-psc-cache`.

## Writing entries

`cache.put` writes `app.<pid>.tmp` in the entry directory, `chmod +x`, then
`rename`s it into place. A crashed or concurrent build can leave a `.tmp` file
but never a truncated `app`. The key is stable across runs once the build
directory exists (the earlier key included the build dir and missed once).

## Measuring

```console
$ PSC_TIME=1 psc build .        # prints sema/codegen milliseconds
$ time psc build .              # wall clock, cold and warm
$ ./tools/bench.sh . --gate-warm 2000 --gate-check 1000  # cold/hot/gated
```

Measured on the compiler itself (Linux x86_64, gcc 15, `-O0`):

| Phase | Debug compiler (`-O0`) | Release compiler (shipped) |
|---|---|---|
| semantic analysis | ~1.5 s | ~0.5 s |
| C code generation | ~20.5 s | ~4.7–5.0 s |
| C compiler | ~5.5 s | ~5.5 s |
| **warm cache hit** | **~0.23 s** | **~0.23 s** |
| `psc check` (first) | ~1.9 s | ~0.9 s |
| `psc check` (cached) | **~0.17 s** | **~0.17 s** |

Code generation dominates cold builds. The main costs are string building for
the 5 MB bundle and the generics/DCE scans; the cache removes them entirely for
unchanged trees. Semantic analysis dropped from ~3.8 s to ~1.5 s by removing a
per-declaration `split("\n")` of the whole source file, indexing import
aliases in the symbol table and deleting the redundant linear scan of every
import symbol in the `lookup_name` fallback. `tools/bench.sh` is the reproducible harness used
by CI (`--gate-warm 2000`); per-module codegen and parallel codegen remain the
next step for cold builds.

## Reproducibility

Two builds of the same tree with the same toolchain produce byte-identical
binaries (verified for `debug` and `release`). No `__DATE__`, `__TIME__` or
random seed is embedded. Absolute paths do appear in debug info and in
`#line` markers, so builds from different directories differ in the debug
sections; use `SOURCE_DATE_EPOCH` when packaging and strip debug info for
byte-for-byte release artifacts. `tools/release.py` honours
`SOURCE_DATE_EPOCH` (default `1700000000`).

## Troubleshooting

* **A stale artifact after changing a header** — headers in `include_dir` and
  the toolchain include dirs are hashed; if you include a header from an
  unhashed absolute path, pass it through `include_dirs` or disable the cache.
* **Cache grows without bound** — run `psc gc --max-size=N` (or `psc gc`) in
  CI/cron; `--max-size` drops arbitrary entries (any entry is disposable), so it
  is safe under concurrency but may reduce the next build's hit rate.
* **Key changes every build** — check that `include_dirs` does not point at
  `build/` or another directory that the build itself writes. The driver skips
  the configured build dir, not arbitrary output directories.
