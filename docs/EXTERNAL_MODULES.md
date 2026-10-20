# External Modules

PenguScript's compiler repository ships only the pure-PenguScript standard
library. Bindings to external C libraries live in satellite repositories that
are installed per project with `pengu add`.

## Available satellite repositories

| Module (old) | Repository | Install with |
| ------------ | ---------- | ------------ |
| `raylib`, `raymath`, `rlgl`, `rlights`, `raygui` | [`pengu-lang/pengu-raylib`](https://github.com/pengu-lang/pengu-raylib) | `pengu add https://github.com/pengu-lang/pengu-raylib` |
| `sqlite3` | [`pengu-lang/pengu-sqlite`](https://github.com/pengu-lang/pengu-sqlite) | `pengu add https://github.com/pengu-lang/pengu-sqlite` |
| `webui` | [`pengu-lang/pengu-webui`](https://github.com/pengu-lang/pengu-webui) | `pengu add https://github.com/pengu-lang/pengu-webui` |
| `miniaudio` | [`pengu-lang/pengu-miniaudio`](https://github.com/pengu-lang/pengu-miniaudio) | `pengu add https://github.com/pengu-lang/pengu-miniaudio` |
| `tomlum`, `yaml` | [`pengu-lang/pengu-formats`](https://github.com/pengu-lang/pengu-formats) | `pengu add https://github.com/pengu-lang/pengu-formats` |
| `uuid`, `xxhash`, `celeris` | [`pengu-lang/pengu-hash`](https://github.com/pengu-lang/pengu-hash) | `pengu add https://github.com/pengu-lang/pengu-hash` |
| `xlsxio`, `xlsx` | [`pengu-lang/pengu-xlsx`](https://github.com/pengu-lang/pengu-xlsx) | `pengu add https://github.com/pengu-lang/pengu-xlsx` |
| `imago`, `typis`, `scriptor`, `perlinum`, `stb_image_resize2`, `stb_herringbone_wang_tile` | [`pengu-lang/pengu-stb`](https://github.com/pengu-lang/pengu-stb) | `pengu add https://github.com/pengu-lang/pengu-stb` |
| `nanosvg`, `nanosvgrast` | [`pengu-lang/pengu-svg`](https://github.com/pengu-lang/pengu-svg) | `pengu add https://github.com/pengu-lang/pengu-svg` |
| `minicoro` | [`pengu-lang/pengu-coroutines`](https://github.com/pengu-lang/pengu-coroutines) | `pengu add https://github.com/pengu-lang/pengu-coroutines` |
| `datastructura` | [`pengu-lang/pengu-datastructura`](https://github.com/pengu-lang/pengu-datastructura) | `pengu add https://github.com/pengu-lang/pengu-datastructura` |
| `fenestra` | [`pengu-lang/pengu-fenestra`](https://github.com/pengu-lang/pengu-fenestra) | `pengu add https://github.com/pengu-lang/pengu-fenestra` |
| `pactum` | [`pengu-lang/pengu-pactum`](https://github.com/pengu-lang/pengu-pactum) | `pengu add https://github.com/pengu-lang/pengu-pactum` |
| `regulus` | [`pengu-lang/pengu-regulus`](https://github.com/pengu-lang/pengu-regulus) | `pengu add https://github.com/pengu-lang/pengu-regulus` |
| `parchment` | [`pengu-lang/pengu-parchment`](https://github.com/pengu-lang/pengu-parchment) | `pengu add https://github.com/pengu-lang/pengu-parchment` |
| `seal` | [`pengu-lang/pengu-seal`](https://github.com/pengu-lang/pengu-seal) | `pengu add https://github.com/pengu-lang/pengu-seal` |
| `precis` | [`pengu-lang/pengu-precis`](https://github.com/pengu-lang/pengu-precis) | `pengu add https://github.com/pengu-lang/pengu-precis` |

## Installing

```bash
cd my_project
pengu add https://github.com/pengu-lang/pengu-raylib --trust
pengu update --trust
```

`--trust` is required because the satellite ships a `build.pengu` (or, in older
satellites, a legacy `build.py`) that compiles its native part. Without it the
dependency is still installed, and the toolchain warns that the build script was
skipped. `pengu add ... --rebuild` forces the build, and
`pengu update --no-build` skips it.

If `pengu` is not on `PATH` in CI, set `PENGU_BIN=/path/to/pengu` so the nested
`pengu run <dep>/build.pengu` works. A satellite whose `lib/` is committed does
not need a build at install time at all.

Then import normally:

```pengu
import std.raylib
```

## Building a satellite repository

A satellite binding is a normal PenguScript project with a `pengu.toml`
declaring its own dependencies and an `extern_manifest.py` (copy from the
compiler repo) declaring the upstream C library's URL and pinned SHA-256.

See `pengu-lang/pengu-raylib` for a reference implementation.
