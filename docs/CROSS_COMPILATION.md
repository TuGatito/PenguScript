# Cross-compilation with PenguScript (`--target`)

> **Status:** PenguScript 0.16.0. Expands [`LANGUAGE.md` §20.2.3](../LANGUAGE.md#L3325) with the
> behaviour of the implementation. Supplementary, not normative: when this text and the source
> disagree, [`pengu_project.py`](../pengu_project.py) wins. The feature is real code but is **not
> exercised by CI** — read [§9](#9-limitations-and-known-gaps) first.

## 1. What "cross-compilation" means here

PenguScript is not a native code generator. `pengu build` emits one C99/C11 translation unit
(`build/bundle.c`, plus project C glue) and invokes a C compiler. Cross-compilation is three
separate things, and `--target` only does the first:

1. **Target selection for naming and linking.** The OS parsed out of the triple chooses the
   artifact extension (`.exe`, `.dll`, `.dylib`, `.so`) and the target-specific link libraries —
   [`pengu_project.py:823-849`](../pengu_project.py#L823), [`1700-1733`](../pengu_project.py#L1700).
2. **A cross C compiler.** Install one and pass `--cc`, or let `resolve_compiler()` auto-detect
   MinGW — [`pengu_project.py:777-807`](../pengu_project.py#L777).
3. **A runtime archive built for the target.** The shipped `libpengu_runtime.a` is host-built; a
   cross link needs a target-built one via `PENGU_RUNTIME_CROSS` —
   [`pengu_project.py:809-821`](../pengu_project.py#L809).

Per [`LANGUAGE.md` §20.2.3](../LANGUAGE.md#L3325), only **Linux ⇄ Windows** is supported in 1.0.
The parser recognizes more triple families than the toolchain can serve:

| Host → Target | Status in 1.0 | Notes |
|---|---|---|
| Linux → Windows | **Supported path** | MinGW-w64 compiler + `PENGU_RUNTIME_CROSS`; produces a PE `.exe` when both are present. Never run end-to-end in this CI. |
| Windows → Linux | **Effectively unsupported** | No automatic candidate is probed ([§2.2](#22-windows--linux)), the Linux link tail is host-derived ([§6](#6-artifacts-and-link-libraries)), and a reliable Windows→Linux GCC is uncommon. Use WSL — that is not cross-compilation. |
| → macOS (from anywhere) | **Not supported** | The triple parses (`darwin`) so a `.dylib` is named, but there is no Darwin cross path and it will not link. |
| Anything → same OS | Not cross | `is_cross` is false and `PENGU_RUNTIME_CROSS` is ignored — [`pengu_project.py:773-775`](../pengu_project.py#L773). |

**The one path needing no toolchain:** the C bundle. `pengu build --target <recognized-triple> -o
bundle.c` writes it and never calls a compiler (tested:
[`tests/test_cross_compile.py:93-108`](../tests/test_cross_compile.py#L93)).

## 2. Required toolchains

### 2.1 Linux → Windows (MinGW-w64)

Install a MinGW-w64 GCC whose driver is named after the triple, because that is what
`resolve_compiler()` probes. Package names verified against distribution indexes; the host used to
check this document is **Arch Linux**.

| Distribution | Install | Driver(s) provided |
|---|---|---|
| Arch Linux | `sudo pacman -S mingw-w64-gcc` (`extra`) | `x86_64-w64-mingw32-gcc` |
| Debian/Ubuntu | `sudo apt install mingw-w64` (`gcc-mingw-w64-x86-64`, `gcc-mingw-w64-i686` are the individual compilers) | `x86_64-w64-mingw32-gcc`, `i686-w64-mingw32-gcc` |
| Fedora/RHEL | `sudo dnf install mingw64-gcc` (win64) / `mingw32-gcc` (win32) | same names |

The compiler's own hint uses the Debian/Ubuntu spelling ([`pengu_project.py:804`](../pengu_project.py#L804)):

```text
Install one (e.g. 'apt install mingw-w64') or pass --cc <compiler>.
```

The package pulls in the matching `ar`. For validation also install `wine` (Arch:
`sudo pacman -S wine`) — see [§8](#8-worked-example-linux--windows-exe).

### 2.2 Windows → Linux

There is no candidate list for this direction. Detection appends `<full-triple>-gcc` for any triple,
then adds MinGW names only when the target OS is Windows
([`pengu_project.py:791-798`](../pengu_project.py#L791)):

```python
candidates.append(f"{triple.raw}-gcc")
if self.target_os == "windows":
    ... "i686-w64-mingw32-gcc", "x86_64-w64-mingw32-gcc", "mingw32-gcc"
```

For `--target x86_64-unknown-linux-gnu` on Windows the only probe is `x86_64-unknown-linux-gnu-gcc`,
which no mainstream toolchain installs: pass `--cc` explicitly, and it must exist
([§10.2](#102---cc-points-at-a-compiler-that-is-not-installed)). Even then two linker inputs are
host-derived — [`pengu_project.py:1723-1733`](../pengu_project.py#L1723): the platform tail
(`-lrt -lcrypto -lssl` on Linux, `-framework CoreFoundation` on macOS) and, on a non-Windows target,
the `pkg-config` lookup (line 1716) for `libxml-2.0`/`libcurl`/`libmicrohttpd`/`mbedtls`, normally
absent on Windows and silently yielding no `-l` flags. **Recommendation:** build Linux binaries on
Linux; on Windows use WSL2 as a native Linux build. This is a documented gap, not a supported workflow.

## 3. The two `--target*` flags are different

| Flag | Meaning | Values | Where |
|---|---|---|---|
| `--target <triple>` | Cross target **OS** (extension, link libs, compiler lookup) | any triple string | `build`/`run`: [`pengu_project.py:5509`](../pengu_project.py#L5509); `test`: [`5597`](../pengu_project.py#L5597) |
| `--target-compiler <dialect>` | C **dialect** emitted (attributes, `restrict`) | `gcc`, `clang`, `msvc`, `tcc` | `build`/`run`: [`5506`](../pengu_project.py#L5506); `test`: [`5594`](../pengu_project.py#L5594) |

`--target-compiler` never selects a compiler; it only decides keyword spelling and is validated
against the real `--cc` ([`pengu_project.py:2693-2727`](../pengu_project.py#L2693)). For MinGW leave
it alone — inferred from `--cc`, and `x86_64-w64-mingw32-gcc` maps to the `gcc` dialect. A triple
containing `msvc` (e.g. `x86_64-pc-windows-msvc`) still only means "Windows target"; it does not
switch the dialect. `--target` does **not** change the compile-time `when os` environment either —
[§7.4](#74-target-does-not-change-the-when-os-environment).

## 4. CLI usage

`--target` exists on `build`, `run` and `test`; the `pengu.yaml` equivalent is `build: target:`
([`pengu_project.py:515`](../pengu_project.py#L515)). `--cc` wins over the configured `build: cc:`
([`495`](../pengu_project.py#L495); CLI override at [`2215-2216`](../pengu_project.py#L2215)).

```bash
# Explicit cross compiler (recommended: no detection surprises).
pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc
# Let resolve_compiler() find MinGW. A configured `cc: gcc` counts as "unset" for cross builds.
pengu build --target x86_64-w64-mingw32
# C bundle only: works for any recognized triple, no cross toolchain needed.
pengu build --target x86_64-w64-mingw32 --output build/windows_bundle.c
# 32-bit Windows.
pengu build --target i686-w64-mingw32 --cc i686-w64-mingw32-gcc
```

```yaml
project:
  name: hello
  entry: src/main.pengu
build:
  target: x86_64-w64-mingw32
  cc: x86_64-w64-mingw32-gcc
```

With that manifest plain `pengu build` cross-compiles; a CLI `--target` overrides it. Two verified
behaviours:

* `--cc` is authoritative only when neither empty nor the literal `gcc`
  ([`pengu_project.py:789-790`](../pengu_project.py#L789)). A project that wants the *host* `gcc` with
  a Windows target cannot say `cc: gcc`; it must use an absolute path.
* `-o/--output` redirects the build **only** when the path ends in `.c`; it then switches the output
  type to `C` and writes the bundle exactly there ([`2210-2212`](../pengu_project.py#L2210),
  [`2286-2289`](../pengu_project.py#L2286)). For executables/libraries the path is always
  `<build_dir>/<artifact name>`; to rename, change `output_name`.

## 5. Supported triples

There is no whitelist: `parse_target_triple()` classifies by substring
([`pengu_project.py:217-245`](../pengu_project.py#L217)). `mingw`/`windows`/`win32`/`msvc` → Windows;
`darwin`/`apple`/`macos` → Darwin; `linux`/`musl`/`gnu` → Linux; anything else yields an empty OS.
The env field is `musl`, `msvc`, `mingw`, `gnu` or empty.

| Triple | `os` | `env` | 1.0 support |
|---|---|---|---|
| `x86_64-w64-mingw32` | `windows` | `mingw` | **Supported** (canonical example) |
| `i686-w64-mingw32` | `windows` | `mingw` | **Supported** (32-bit) |
| `x86_64-pc-windows-gnu` | `windows` | `gnu` | Parses; folds to the same lockfile target as `x86_64-w64-mingw32` |
| `x86_64-pc-windows-msvc` | `windows` | `msvc` | Parses, but there is no MSVC toolchain in the repo ([§9](#9-limitations-and-known-gaps)) |
| `x86_64-unknown-linux-gnu` | `linux` | `gnu` | Windows→Linux only, with an explicit `--cc` |
| `x86_64-linux-musl` | `linux` | `musl` | Parses; no musl toolchain set up |
| `aarch64-apple-darwin` | `darwin` | *(empty)* | Naming only; cross-linking unsupported |

> **Gotcha — unknown triples are silently ignored.** A triple matching none of the substrings (e.g.
> `riscv64-unknown-elf`) parses to `os=""`, `target_triple` returns `None`, and the build proceeds
> **for the host** ([`pengu_project.py:762-765`](../pengu_project.py#L762)), with no warning. Verified:
> `pengu build --target riscv64-unknown-elf` produced the host binary `build/xt` (no `.exe`). If a
> target behaves like the host, check the spelling.

The lockfile stores a canonicalized target so equivalent triples do not break `--frozen`
([`pengu_project.py:2061-2079`](../pengu_project.py#L2061)): `x86_64-w64-mingw32` and
`x86_64-pc-windows-gnu` both become `x86_64-windows-gnu`. With no `--target`, the lock target is the
host OS name.

## 6. Artifacts and link libraries

Naming follows the **target**, not the host ([`pengu_project.py:823-849`](../pengu_project.py#L823)):
`exe` → `<name>.exe` on Windows, `<name>` elsewhere; `shared` → `<name>.dll` / `lib<name>.dylib` /
`lib<name>.so`; `static` → `<name>.lib` on Windows, `<name>.a` elsewhere; `obj` → `<name>.o` always;
`c` → `bundle.c` always.

The link set changes with the target ([`pengu_project.py:1697-1733`](../pengu_project.py#L1697)):

* **Always** (the `pengu_runtime` entry expands to a fixed group):
  `-lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz`.
* **Windows target**: adds the Win32 system libraries — `-lws2_32 -lwinmm -ladvapi32 -lcrypt32
  -lbcrypt -lopengl32 -lgdi32 -lole32 -luuid -lshell32 -lpsapi -luserenv -liphlpapi`. `pkg-config`
  lookups are skipped entirely ([`pengu_project.py:1643`](../pengu_project.py#L1643)).
* **Non-Windows target**: appends the `pkg-config` libs for `libxml-2.0`, `libcurl`, `libmicrohttpd`,
  `mbedtls`, then a platform tail chosen from the **host** `sys.platform` — `-lrt -lcrypto -lssl` on
  Linux, `-framework CoreFoundation` on macOS — followed by `-pthread -lm -ldl`.
* Static archives are wrapped in `-Wl,--start-group … -Wl,--end-group` on GNU linkers. A MinGW `gcc`
  on a Linux host *does* receive the group (verified in the emitted command line); TCC and `cl.exe` do
  not ([`1741-1748`](../pengu_project.py#L1741)).

The cross-runtime `-L`/`-I` flags are inserted into `common_flags` **before** the project and host
search paths ([`1530-1533`](../pengu_project.py#L1530), host paths at 1654–1675), so a
`PENGU_RUNTIME_CROSS` archive wins. Verified with `--verbose`: `-L<prefix>/lib -I<prefix>/include`
precede the host `build/lib`/`build/include`.

## 7. The runtime archive problem

### 7.1 The shipped archive is host-built

Every linking build requires `libpengu_runtime.a`, and the bundle references `pengu_abi_version` so a
stale archive fails at link time (see [`ABI.md`](ABI.md)). The shipped archive was compiled by the
host toolchain; an ELF archive cannot satisfy a MinGW link, and vice versa. A pre-flight check looks
for the archive *before* invoking the C compiler
([`pengu_project.py:2010-2012`](../pengu_project.py#L2010), [`2655-2670`](../pengu_project.py#L2655)).
It searches the host runtime dirs from [`pengu_paths.py`](../pengu_paths.py#L162) (`PENGU_LIB_DIR`,
`$PENGU_PREFIX/lib/pengu`, checkout `build/lib`, `./build/lib`, portable `runtime/lib`, FHS prefixes,
`_MEIPASS`) — **not `PENGU_RUNTIME_CROSS`**. So a cross build needs a discoverable host
`libpengu_runtime.a` *and* a target archive in the cross prefix (from a normal checkout the host one
is already there).

### 7.2 `PENGU_RUNTIME_CROSS`

Point the variable at a **prefix**; the build turns it into search flags
([`pengu_project.py:809-821`](../pengu_project.py#L809)): `-L<prefix>/lib` if that directory exists,
else `-L<prefix>`; plus `-I<prefix>/include` if it exists.

```text
<prefix>/
  include/    # pengu_runtime.h, pcre2.h, curl/, mbedtls/, microhttpd.h, zlib.h, ...
  lib/        # libpengu_runtime.a, libpcre2-8.a, libxml2.a, libcurl.a,
              # libmbedcrypto.a, libmicrohttpd.a, libz.a
```

The variable is ignored unless the build is actually cross (target OS ≠ host OS), and the `-I` mainly
serves dependency headers: `bundle.c` uses `#include "pengu_runtime.h"`, resolved next to the bundle
in `build/` from the just-copied host header. The **header is target-independent; the archive is not.**

### 7.3 Building the runtime for the target

[`build_runtime.py`](../build_runtime.py) has **no cross mode**: the only option is `--rebuild`
([`1293-1297`](../build_runtime.py#L1293)), and `get_toolchain()` unconditionally picks the host
`gcc`/`clang`/`cc` ([`89-96`](../build_runtime.py#L89)). No `--target`/`--cc`/`--host`, and its CMake
projects are configured with the host compiler. Options:

1. **Cross-build the stack with explicit CMake toolchain files**, configuring each dependency and the
   runtime with `-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc`, then copy
   archives to `<prefix>/lib` and headers to `<prefix>/include`. You reproduce by hand what
   `build_runtime.py` does internally.
2. **Build natively on Windows and copy the prefix.** On Windows `python build_runtime.py` uses MinGW
   gcc — exactly what CI does ([`.github/workflows/ci.yml:105-118`](../.github/workflows/ci.yml#L105)).
   Copy `build/include` and `build/lib` to a prefix on the Linux side and use it as
   `PENGU_RUNTIME_CROSS`. It must be built against the same `pengu_runtime.h` (ABI v1); it is the same
   file shipped in the repo.
3. **Do not** substitute distro MinGW libraries for the bundled static stack: the ABI/version pairing
   is what makes the link work.

Pointing `PENGU_RUNTIME_CROSS` at a prefix containing only host (ELF) archives should be expected to
fail with an archive-format complaint (`file format not recognized` / `skipping incompatible`) or
undefined symbols. That wording is illustrative — this repo does not capture that failure verbatim.

### 7.4 `--target` does not change the `when os` environment

The compile-time environment comes from the **host** Python process, not from `--target`
([`pengu_parser/pengu_comptime.py:25-36`](../pengu_parser/pengu_comptime.py#L25)). Only `-D os=…`,
`-D arch=…`, `-D compiler=…` override it ([`169-176`](../pengu_parser/pengu_comptime.py#L169)):

```bash
pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc -D os=windows
```

Verified with a program returning `1` under `when os == "windows"` and `0` otherwise:
`--target x86_64-w64-mingw32` alone emitted the `else` branch (`return 0`); adding `-D os=windows`
emitted `return 1`. Without the define you get a correctly named `.exe` running the wrong code.

## 8. Worked example: Linux → Windows `.exe`

Assumes Arch Linux, `mingw-w64-gcc`, `wine`, and a Windows runtime prefix built as in
[§7.3](#73-building-the-runtime-for-the-target).

```bash
# 1. Minimal project.
mkdir -p hello/src
printf 'project:\n  name: hello\n  entry: src/main.pengu\n' > hello/pengu.yaml
printf 'weave main into int:\n  say "hello from windows"\n  return 0\n' > hello/src/main.pengu

# 2. Confirm the Windows C bundle generates without any toolchain.
cd hello
pengu build --target x86_64-w64-mingw32 --output build/windows_bundle.c

# 3. Cross-link the executable against the Windows-built runtime prefix.
PENGU_RUNTIME_CROSS=/opt/pengu-win \
  pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc --profile release
# -> build/hello.exe

# 4. Inspect the artifact instead of trusting the extension.
file build/hello.exe            # PE32+ executable (console) x86-64, for MS Windows

# 5. Validate behaviour under Wine.
wine build/hello.exe            # -> hello from windows
```

If the program uses `when os == "windows"` blocks, add `-D os=windows`
([§7.4](#74-target-does-not-change-the-when-os-environment)).

**Honesty note:** there is no automated end-to-end run of this example.
`tests/test_cross_compile.py` covers triple parsing, artifact naming, compiler auto-detection and its
error, `PENGU_RUNTIME_CROSS` flag generation, and the C-bundle-only Windows build. The only test
touching a real MinGW compiler is compile-only and skipped when the toolchain is absent
([`tests/test_cross_compile.py:119-130`](../tests/test_cross_compile.py#L119)):

```python
@pytest.mark.skipif(not shutil.which("x86_64-w64-mingw32-gcc"),
                    reason="MinGW cross compiler not installed")
def test_real_mingw_cross_compile_bundle(tmp_path):
```

No test produces a `.exe`, and none runs it under Wine.

## 9. Limitations and known gaps

* **No CI coverage.** There is no `cross-compile.yml`; CI runs
  `windows-latest`/`ubuntu-latest`/`macos-latest` natively
  ([`.github/workflows/ci.yml:40-50`](../.github/workflows/ci.yml#L40)). Recorded as open in
  [`AUDIT_1.0.md:1120`](../AUDIT_1.0.md#L1120), [`AUDIT_1.0.md:2922`](../AUDIT_1.0.md#L2922) and
  `ROADMAP_2.0.md` item 8.12.
* **The MinGW test is opt-in and compile-only** — a stub `.c`, not a PenguScript program
  ([`tests/test_cross_compile.py:119-130`](../tests/test_cross_compile.py#L119)).
* **No MSVC.** The real matrix is gcc (Linux) / clang-or-gcc (macOS) / MinGW (Windows):
  `build_runtime.py` has no `cl.exe` branch and `ci.yml` hardcodes `gcc` on Windows —
  [`AUDIT_1.0.md` §15.3](../AUDIT_1.0.md#L2960). An `msvc` triple buys no MSVC build.
* **Unknown triples silently fall back to the host** ([§5](#5-supported-triples)).
* **No automated way to build the target runtime** ([§7.3](#73-building-the-runtime-for-the-target));
  the whole dependency stack (PCRE2, libxml2, curl, mbedTLS, libmicrohttpd, zlib) must be cross-built,
  because the runtime link group names all of them.
* **The runtime pre-flight ignores `PENGU_RUNTIME_CROSS`** ([§7.1](#71-the-shipped-archive-is-host-built)).
* **`--target` is decoupled from `when os`** ([§7.4](#74-target-does-not-change-the-when-os-environment)).
* **Windows→Linux is not a real path** ([§2.2](#22-windows--linux)).
* **`run`/`test` accept `--target` but execute the artifact locally**
  ([`5509`](../pengu_project.py#L5509), [`5597`](../pengu_project.py#L5597)). On a Linux host a
  Windows-target `pengu run` builds the `.exe` then tries to execute it — expect an execution error.
  Use `build`, then Wine.
* **`--target` is missing from [`CHEATSHEET.md` §17.2](../CHEATSHEET.md#L2516)** as of 0.16.0, though
  it is in `pengu build --help` ([`AUDIT_1.0.md:2689`](../AUDIT_1.0.md#L2689)); this file is roadmap
  item 7.11.

## 10. Troubleshooting

### 10.1 No cross compiler found

Auto-detection failure stops the build with
([`pengu_project.py:802-807`](../pengu_project.py#L802)):

```text
no cross compiler found for target 'x86_64-w64-mingw32'.
Install one (e.g. 'apt install mingw-w64') or pass --cc <compiler>.
Cross-compilation also needs a runtime built for the target; point PENGU_RUNTIME_CROSS at its directory.
```

Check the probed names (`<triple>-gcc`; for Windows also `x86_64-w64-mingw32-gcc`,
`i686-w64-mingw32-gcc`, `mingw32-gcc`) at [`pengu_project.py:791-798`](../pengu_project.py#L791).

### 10.2 `--cc` points at a compiler that is not installed

`--cc` bypasses detection, so a typo surfaces only at the C step
([`pengu_project.py:1984-1988`](../pengu_project.py#L1984)):

```text
Error:
C compilation failed (hello)

Command: <the full command line>
Could not execute: [Errno 2] No such file or directory: 'x86_64-w64-mingw32-gcc'
```

Run `which x86_64-w64-mingw32-gcc` (or your driver's name) first.

### 10.3 `libpengu_runtime.a not found`

For `exe`/`shared` outputs the pre-flight refuses to invoke the compiler
([`pengu_project.py:2794-2805`](../pengu_project.py#L2794)):

```text
libpengu_runtime.a not found.
  Every PenguScript build links the runtime, so the archive is required.
  Run `python build_runtime.py` to build it, set PENGU_LIB_DIR to the
  directory that holds it, or install a release that ships it.
  Searched:
    <one path per line>
```

If a host archive exists but the cross link still fails on the archive, the problem is the target
runtime ([§7.1](#71-the-shipped-archive-is-host-built)).

### 10.4 Stale cache

The triple is part of both cache keys — [`pengu_project.py:686`](../pengu_project.py#L686) (project
builds) and [`4849`](../pengu_project.py#L4849) (scripts) — so switching `--target` invalidates the
cache. If you still suspect a stale artifact, use `pengu clean` (project) or `pengu gc --all`
(script cache).

## 11. Where every documented flag/behaviour is verified

| Item | File:line |
|---|---|
| `--target` (`build`/`run`, `test`) | [`pengu_project.py:5509`](../pengu_project.py#L5509), [:5597](../pengu_project.py#L5597) |
| `--cc` (`build`/`run`/`test`) | [`5463`](../pengu_project.py#L5463), [:5484](../pengu_project.py#L5484), [:5584](../pengu_project.py#L5584) |
| `--target-compiler` (`build`/`run`, `test`) | [`5506`](../pengu_project.py#L5506), [:5594](../pengu_project.py#L5594) |
| `--output` C-only redirection; `build: target:`/`cc:` | [`2210`](../pengu_project.py#L2210), [:2286](../pengu_project.py#L2286), [:515](../pengu_project.py#L515), [:495](../pengu_project.py#L495) |
| Triple parsing; `is_cross`; auto-detection | [`217-245`](../pengu_project.py#L217), [:767-775](../pengu_project.py#L767), [:791-801](../pengu_project.py#L791) |
| `PENGU_RUNTIME_CROSS` → `-L`/`-I`, applied first | [`809-821`](../pengu_project.py#L809), [:1530-1533](../pengu_project.py#L1530) |
| Archive pre-flight; error texts | [`2010-2012`](../pengu_project.py#L2010), [:2655-2670](../pengu_project.py#L2655), [:2794-2805](../pengu_project.py#L2794), [:1984-1988](../pengu_project.py#L1984) |
| Extensions; link libraries | [`823-849`](../pengu_project.py#L823), [:1697-1733](../pengu_project.py#L1697) |
| Lockfile target; cache keys | [`2061-2079`](../pengu_project.py#L2061), [:686](../pengu_project.py#L686), [:4849](../pengu_project.py#L4849) |
| `when os` from host, not `--target` | [`pengu_comptime.py:25-36`](../pengu_parser/pengu_comptime.py#L25), [:169-176](../pengu_parser/pengu_comptime.py#L169) |
| Runtime search layouts; no cross mode in `build_runtime.py` | [`pengu_paths.py:162-207`](../pengu_paths.py#L162), [`build_runtime.py:89-96`](../build_runtime.py#L89), [:1293-1297](../build_runtime.py#L1293) |
| Tests; CI matrix | [`tests/test_cross_compile.py`](../tests/test_cross_compile.py), [`.github/workflows/ci.yml:40-50`](../.github/workflows/ci.yml#L40) |
