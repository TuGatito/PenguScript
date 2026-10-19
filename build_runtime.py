#!/usr/bin/env python3
"""build_runtime.py - Compiles the PenguScript C runtime.

Compiles into ``build/lib/``:

  - ``build_pengu_runtime`` -> ``libpengu_runtime.a`` (core + filum)
  - ``build_runtime_pch``   -> ``build/include/pengu_runtime.h.gch`` (optional)

With ``--target emscripten`` it instead compiles the same sources for
WebAssembly with ``emcc``/``emar`` into ``build/wasm/lib/``, leaving the host
archive untouched (see ``docs/WASM.md``).

The runtime has **no external C dependencies**: it needs nothing beyond
libc, libm and pthreads / Win32 threads. Bindings to external libraries
(graphics, databases, compression, crypto, networking, document formats, ...)
no longer live in this repository: they ship as satellite repositories
installed per project with ``pengu add``. See ``docs/EXTERNAL_MODULES.md``.

The download/hash infrastructure that used to fetch the vendored sources is
kept in ``extern_manifest.py`` (with an empty manifest) so the satellite
repositories can copy it.

The archive ships one object per subsystem (core, filum) so the linker can
pull only what a program references. See ``RUNTIME_OBJECTS`` below.

Headers are copied into ``build/include/``.
"""

import os
import sys
import platform as _platform_mod
import shutil
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
EXTERN_DIR = ROOT_DIR / "extern"
BUILD_DIR = ROOT_DIR / "build"
INCLUDE_DIR = BUILD_DIR / "include"
LIB_DIR = BUILD_DIR / "lib"
PARSER_DIR = ROOT_DIR / "pengu_parser"

#: WebAssembly (Emscripten) output. Deliberately *not* ``build/lib``: a wasm
#: object file and a host object file share neither machine code nor ABI, so
#: mixing them in one search path would let a misconfigured build link the wrong
#: one and fail with an unrelated-looking error much later.
WASM_DIR = BUILD_DIR / "wasm"
WASM_LIB_DIR = WASM_DIR / "lib"
WASM_INCLUDE_DIR = WASM_DIR / "include"

#: The emsdk install/activation instructions, quoted verbatim in the error that
#: `--target emscripten` raises when the toolchain is missing.
EMSDK_HELP = (
    "  git clone https://github.com/emscripten-core/emsdk.git\n"
    "  cd emsdk && ./emsdk install latest && ./emsdk activate latest\n"
    "  source ./emsdk_env.sh"
)

IS_WINDOWS = sys.platform.startswith("win")
IS_DARWIN = sys.platform.startswith("darwin")
IS_POSIX = not IS_WINDOWS

# Section splitting. The linker resolves a static archive at *member* (.o)
# granularity, and every object here is a whole translation unit. Compiling
# every object with one section per function lets the link step's
# `--gc-sections` (Linux/BSD) / `-dead_strip` (macOS) drop what the program
# never calls. See pengu_project.py (release/small profiles) and BENCHMARKS.md
# §Binary size.
SECTION_FLAGS = ["-ffunction-sections", "-fdata-sections"]

#: The optional-subsystem gates `pengu_runtime.h` defines. `pengu_runtime.c`
#: wraps each subsystem in `#if <gate>`, so one translation-unit compile per
#: gate produces one object per subsystem.
RUNTIME_GATES = (
    "PENGU_ENABLE_THREADS",
)

#: (object file name, the one gate that is ON) -- `None` for the core object.
#:
#: One member per subsystem makes the linker's usual "pull a member only for a
#: symbol it defines" rule do the pruning on every platform, with no GC
#: required. PE's `--gc-sections` keeps unreferenced sections of an archive
#: member, so Windows needs the split even more than ELF/Mach-O do.
RUNTIME_OBJECTS = (
    ("pengu_runtime.o", None),
    ("pengu_runtime_filum.o", "PENGU_ENABLE_THREADS"),
)

_venv_bin = Path(sys.executable).resolve().parent
if str(_venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_venv_bin) + os.pathsep + os.environ.get("PATH", "")


def platform_machine():
    """Returns the CPU architecture of the host (normalized)."""
    m = _platform_mod.machine().lower()
    if m in ("amd64", "x86_64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "arm64"
    return m


def get_toolchain():
    """Detects available C compiler and archiver."""
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    ar = shutil.which("ar") or shutil.which("llvm-ar")
    if not cc:
        raise RuntimeError("No C compiler (gcc/clang/cc) found in PATH.")
    if not ar:
        raise RuntimeError("No static archiver (ar/llvm-ar) found in PATH.")
    return cc, ar


def get_toolchain_wasm():
    """Detects the Emscripten compiler/archiver, or explains how to install it.

    ``emcc`` and ``emar`` are both required: the runtime archive is a real ar
    archive of wasm objects, and ``ar`` cannot build one (it would emit a host
    archive whose members the wasm linker rejects).
    """
    cc = shutil.which("emcc")
    ar = shutil.which("emar")
    if not cc or not ar:
        missing = ", ".join(n for n, p in (("emcc", cc), ("emar", ar)) if not p)
        raise RuntimeError(
            f"{missing} not found in PATH.\n"
            f"  Install and activate the Emscripten SDK:\n{EMSDK_HELP}"
        )
    return cc, ar


def build_pengu_runtime_wasm(cc, ar, rebuild=False):
    """Compiles pengu_runtime.c into ``build/wasm/lib/libpengu_runtime.a``.

    Same one-object-per-subsystem partition as the host build, but every object
    is a wasm object produced by ``emcc``.  ``-pthread`` is mandatory even for
    the core object: it is what makes Emscripten emit the atomics/shared-memory
    target features, and an archive whose members disagree on them cannot be
    linked together.
    """
    target_lib = WASM_LIB_DIR / "libpengu_runtime.a"
    runtime_c = PARSER_DIR / "pengu_runtime.c"
    runtime_h = ROOT_DIR / "pengu_runtime.h"

    WASM_INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runtime_h, WASM_INCLUDE_DIR / "pengu_runtime.h")

    if not runtime_c.exists():
        print("[RUNTIME-WASM] pengu_runtime.c not found yet, skipping.")
        return None

    if target_lib.exists() and not rebuild:
        newest_input = max(runtime_c.stat().st_mtime, runtime_h.stat().st_mtime)
        if target_lib.stat().st_mtime >= newest_input:
            print(f"[RUNTIME-WASM] {target_lib.name} is up to date.")
            return target_lib

    print(f"[RUNTIME-WASM] Compiling pengu_runtime.c for wasm32 ({cc})...")
    obj_dir = WASM_DIR / "obj_runtime"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2",
        "-std=c11",
        # Required for <stdatomic.h> to lower to real wasm atomics and for
        # `__thread` to become per-Worker TLS instead of a shared global.
        "-pthread",
        "-I" + str(ROOT_DIR),
        "-I" + str(INCLUDE_DIR),
    ] + SECTION_FLAGS

    objects = []
    for obj_name, on_gate in RUNTIME_OBJECTS:
        obj_path = obj_dir / obj_name
        gates = [f"-D{gate}=1" if gate == on_gate else f"-D{gate}=0"
                 for gate in RUNTIME_GATES]
        core = "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=0" if on_gate is None \
            else "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=1"
        cmd = [cc] + flags + gates + [core, "-c", str(runtime_c), "-o", str(obj_path)]
        run_cmd(cmd)
        objects.append(str(obj_path))

    WASM_LIB_DIR.mkdir(parents=True, exist_ok=True)
    if target_lib.exists():
        target_lib.unlink()
    run_cmd([ar, "rcs", str(target_lib)] + objects)
    print(f"[RUNTIME-WASM] Created {target_lib} ({len(objects)} objects)")
    return target_lib


def run_cmd(cmd, cwd=None, env=None):
    """Runs a shell command and raises an error on failure."""
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"  [EXEC] {cmd_str}")
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}:")
        print(res.stderr)
        raise RuntimeError(f"Command failed: {cmd_str}\n{res.stderr}")
    return res


def build_pengu_runtime(cc, ar, rebuild=False):
    """Compiles pengu_runtime.c into build/lib/libpengu_runtime.a."""
    target_lib = LIB_DIR / "libpengu_runtime.a"
    runtime_c = PARSER_DIR / "pengu_runtime.c"
    runtime_h = ROOT_DIR / "pengu_runtime.h"

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    # Also copy pengu_runtime.h to build/include/
    shutil.copy2(runtime_h, INCLUDE_DIR / "pengu_runtime.h")

    if not runtime_c.exists():
        print("[RUNTIME] pengu_runtime.c not found yet, skipping pengu_runtime compilation.")
        return None

    if target_lib.exists() and not rebuild:
        # `pengu_runtime.c` includes `pengu_runtime.h`, and the ABI version and
        # every struct layout live in the header. Comparing only against the
        # `.c` mtime kept a stale `libpengu_runtime.a` alive across an ABI bump:
        # the generated bundle then failed the `_Static_assert` (or, worse,
        # linked against mismatched struct offsets). Both inputs must be older.
        newest_input = max(runtime_c.stat().st_mtime, runtime_h.stat().st_mtime)
        if target_lib.stat().st_mtime >= newest_input:
            print(f"[RUNTIME] {target_lib.name} is up to date.")
            return target_lib

    print("[RUNTIME] Compiling pengu_runtime.c (one object per subsystem)...")
    obj_dir = BUILD_DIR / "obj_runtime"
    obj_dir.mkdir(parents=True, exist_ok=True)

    # The runtime has no external headers to point at: libc/libm/pthreads only.
    flags = [
        "-O2",
        "-I" + str(ROOT_DIR),
        "-I" + str(INCLUDE_DIR),
    ] + SECTION_FLAGS
    objects = []
    for obj_name, on_gate in RUNTIME_OBJECTS:
        obj_path = obj_dir / obj_name
        gates = [f"-D{gate}=1" if gate == on_gate else f"-D{gate}=0"
                 for gate in RUNTIME_GATES]
        # The ABI pin and the FFI bridges are non-static: they belong to the core
        # object only, or their definitions would collide once the linker pulls
        # two members.
        core = "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=0" if on_gate is None \
            else "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=1"
        cmd = [cc] + flags + gates + [core, "-c", str(runtime_c), "-o", str(obj_path)]
        run_cmd(cmd)
        objects.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    # A stale archive may hold members from an older partition (`ar rcs` only
    # replaces the names it is given), so start clean.
    if target_lib.exists():
        target_lib.unlink()
    run_cmd([ar, "rcs", str(target_lib)] + objects)
    print(f"[RUNTIME] Created {target_lib} ({len(objects)} objects)")
    return target_lib


def _std_c_sources():
    """Returns the vendored C translation units under ``std_c/``.

    Each ``std_c/<name>.c`` becomes ``lib<name>.a`` so a module that imports
    the matching binding can ask for it with ``link "<name>"``. A program that
    never imports that binding never receives the ``-l`` flag, which is the
    smart-linking contract this directory exists for.
    """
    std_c_dir = ROOT_DIR / "std_c"
    if not std_c_dir.is_dir():
        return []
    return sorted(p for p in std_c_dir.glob("*.c") if p.is_file())


#: System headers a vendored ``std_c/<name>.c`` needs from the host.  When one
#: is missing the translation unit is *skipped* with an actionable message
#: instead of failing the whole runtime build: a machine without the libcurl
#: development headers can still build every other module, and a program that
#: imports the module then gets a clear ``-lpetitio`` link error.  Keeping the
#: stdlib buildable without optional system libraries is what lets
#: `pengu_project.py build` work out of the box.
STD_C_REQUIRES = {
    "petitio": ("curl/curl.h",),
}

#: Per-unit ``-D`` flags for the vendored ``std_c/*.c`` translation units.
#:
#: ``miniz.c`` includes ``miniz.h`` directly (the vendored file is untouched),
#: so the configuration macros must reach *this* translation unit on the command
#: line.  ``std_c/miniz_bind.h`` repeats the same set behind ``#ifndef`` guards
#: for every consumer bundle, so the archive and its users cannot disagree.  See
#: the comment at the top of ``std_c/miniz_bind.h`` for why each macro exists.
STD_C_DEFINES = {
    "miniz": (
        "-DMINIZ_NO_ZLIB_COMPATIBLE_NAMES",
        "-DMINIZ_NO_ARCHIVE_APIS",
        "-DMINIZ_NO_STDIO",
        "-DMINIZ_NO_TIME",
    ),
}


def _header_available(cc, header):
    """True when ``cc`` can preprocess ``#include <header>``."""
    try:
        res = subprocess.run(
            [cc, "-E", "-x", "c", "-"],
            input=f"#include <{header}>\n",
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


def build_std_c(cc, ar, dest_dir, rebuild=False, extra_flags=None):
    """Compiles every ``std_c/*.c`` into ``<dest_dir>/lib/lib<name>.a``.

    The archives are cached by mtime against the ``.c`` file and every header
    in ``std_c/`` (a header-only dependency such as ``utf8.h`` can change the
    generated code without touching the ``.c``). Compilation is strict:
    ``-std=c99 -Wall -Wextra -Werror`` so a warning in the vendored code is a
    build failure rather than noise in every consumer build.

    A unit listed in :data:`STD_C_REQUIRES` whose system header is missing is
    skipped (see that constant).  ``pengu_runtime.h`` is on the include path
    because a bridge that takes or returns a ``string`` must see the real ABI
    declaration, not a copy.

    Args:
        cc: C compiler executable.
        ar: Static archiver executable.
        dest_dir: Build root; the archives land in ``dest_dir/lib``.
        rebuild: Force a rebuild even when the archive is newer than its inputs.
        extra_flags: Additional compiler flags (used by the wasm build).

    Returns:
        The list of created archive names (without the ``lib`` prefix/ext), or
        an empty list when ``std_c/`` has no C sources.
    """
    sources = _std_c_sources()
    if not sources:
        print("[STD_C] no std_c/*.c sources found; skipping.")
        return []

    std_c_dir = ROOT_DIR / "std_c"
    lib_dir = Path(dest_dir) / "lib"
    obj_dir = Path(dest_dir) / "obj_std_c"
    lib_dir.mkdir(parents=True, exist_ok=True)
    obj_dir.mkdir(parents=True, exist_ok=True)

    headers = sorted(p for p in std_c_dir.glob("*.h") if p.is_file())
    # Stage the headers where every include path already looks: build/include
    # (portable release: runtime/include) and build/wasm/include. A generated
    # bundle says `#include "utf8.h"` / `#include "re.h"`; without this copy a
    # frozen release would have the archives but not the headers.
    include_dir = Path(dest_dir) / "include"
    include_dir.mkdir(parents=True, exist_ok=True)
    for header in headers:
        shutil.copy2(header, include_dir / header.name)
    flags = [
        "-O2",
        "-std=c99",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I" + str(std_c_dir),
        # `std_c/petitio.c` includes `pengu_runtime.h` for PenguString: a
        # bridge that speaks `string` needs the real ABI, not a copy.
        "-I" + str(ROOT_DIR),
        "-I" + str(include_dir),
    ] + SECTION_FLAGS + list(extra_flags or [])

    built = []
    for source in sources:
        name = source.stem
        target_lib = lib_dir / f"lib{name}.a"
        obj_path = obj_dir / f"{name}.o"

        missing = [h for h in STD_C_REQUIRES.get(name, ()) if not _header_available(cc, h)]
        if missing:
            print(f"[STD_C] Skipping {source.name}: "
                  f"{', '.join(missing)} not found. "
                  f"Install the matching development package to build the "
                  f"`{name}` module.")
            continue

        inputs = sources + headers
        newest_input = max(p.stat().st_mtime for p in inputs)
        if target_lib.exists() and not rebuild and target_lib.stat().st_mtime >= newest_input:
            print(f"[STD_C] {target_lib.name} is up to date.")
            built.append(name)
            continue

        print(f"[STD_C] Compiling {source.name} -> {target_lib.name}...")
        unit_flags = flags + list(STD_C_DEFINES.get(name, ()))
        run_cmd([cc] + unit_flags + ["-c", str(source), "-o", str(obj_path)])
        if target_lib.exists():
            target_lib.unlink()
        run_cmd([ar, "rcs", str(target_lib), str(obj_path)])
        built.append(name)
        print(f"[STD_C] Created {target_lib}")

    return built


def build_runtime_pch(cc, rebuild=False):
    """Generates ``build/include/pengu_runtime.h.gch`` for later builds.

    gcc/clang pick a ``.gch`` up automatically when it sits *next to* the header
    and the compilation flags match (same ``-std``, same ``-D``/``-I`` set). If
    a project uses different ``-D`` values gcc silently ignores the file and
    parses the header normally — a graceful degradation, never an error.

    This is best effort: a missing header or a failed compile prints a warning
    and returns ``None`` without failing the runtime build.
    """
    header = INCLUDE_DIR / "pengu_runtime.h"
    if not header.is_file():
        src = ROOT_DIR / "pengu_runtime.h"
        if not src.is_file():
            print("[PCH] pengu_runtime.h not found; skipping", file=sys.stderr)
            return None
        INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, header)

    gch = header.parent / (header.name + ".gch")
    if gch.is_file() and not rebuild:
        try:
            if gch.stat().st_mtime >= header.stat().st_mtime:
                print(f"[PCH] {gch.name} is up to date.")
                return gch
        except OSError:
            pass

    # Minimal, stable flag set: the same defines build_pengu_runtime uses by
    # default, so the PCH matches an ordinary project compile.
    flags = [
        "-x", "c-header",
        "-std=c11",
        "-O2",
        "-I" + str(INCLUDE_DIR),
        "-I" + str(ROOT_DIR),
    ] + SECTION_FLAGS
    cmd = [cc] + flags + [str(header), "-o", str(gch)]
    print(f"[PCH] compiling {gch.name}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        print(f"[PCH] generation failed (best-effort, skipping): {e}", file=sys.stderr)
        return None
    if res.returncode != 0:
        print(f"[PCH] generation failed (best-effort, skipping):\n{(res.stderr or '')[-500:]}",
              file=sys.stderr)
        try:
            gch.unlink()
        except OSError:
            pass
        return None
    print(f"[PCH] created {gch}")
    return gch


def main():
    parser = argparse.ArgumentParser(
        description="Build the PenguScript static runtime (no external dependencies).")
    parser.add_argument("--rebuild", action="store_true", help="Force a rebuild.")
    parser.add_argument("--target", choices=["native", "emscripten", "wasi"],
                        default="native",
                        help="Runtime flavour to build: 'native' (host, default) or "
                             "'emscripten' (wasm32 for WebAssembly).")
    parser.add_argument("--headers-only", action="store_true",
                        help="Only stage pengu_runtime.h into build/include/.")
    args = parser.parse_args()

    if args.headers_only:
        INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT_DIR / "pengu_runtime.h", INCLUDE_DIR / "pengu_runtime.h")
        std_c_dir = ROOT_DIR / "std_c"
        if std_c_dir.is_dir():
            for header in std_c_dir.glob("*.h"):
                shutil.copy2(header, INCLUDE_DIR / header.name)
        print("[RUNTIME] staged pengu_runtime.h only (--headers-only)")
        return

    if args.target == "wasi":
        # Recognised on purpose rather than left to argparse: "wasi" is a
        # plausible typo for a request this project cannot satisfy yet, and a
        # bare "invalid choice" would hide that it is a roadmap item.
        print("[RUNTIME] 'wasi' is not supported yet; only 'native' and "
              "'emscripten' are available (see docs/WASM.md).", file=sys.stderr)
        raise SystemExit(2)

    if args.target == "emscripten":
        try:
            cc, ar = get_toolchain_wasm()
        except RuntimeError as e:
            # A missing SDK is a configuration problem, not a crash: print the
            # actionable message instead of a traceback.
            print(f"[RUNTIME-WASM] {e}", file=sys.stderr)
            raise SystemExit(2)
        print(f"=== Building PenguScript Runtime for wasm32 (CC: {cc}, AR: {ar}) ===")
        # The wasm build deliberately does not touch build/lib: the host and wasm
        # archives coexist so a project can build for both targets in one tree.
        result = build_pengu_runtime_wasm(cc, ar, rebuild=args.rebuild)
        std_c_wasm = build_std_c(cc, ar, WASM_DIR, rebuild=args.rebuild,
                                 extra_flags=["-pthread"])
        print(f"=== Wasm runtime build finished. Built: "
              f"{'RUNTIME-WASM' if result else '(none)'}"
              f"{', STD_C-WASM' if std_c_wasm else ''} ===")
        return

    cc, ar = get_toolchain()
    print(f"=== Building PenguScript Runtime (CC: {cc}, AR: {ar}) ===")

    # The manifest is empty for the core runtime, but the download/hash
    # infrastructure stays in place for the satellite repositories that copy
    # it. Calling it here is a harmless no-op.
    from extern_manifest import download_and_extract_externs
    download_and_extract_externs(EXTERN_DIR)

    built = []

    def _build(label, fn, *a, **kw):
        """Runs one builder; failures abort (there is no optional build left)."""
        result = fn(*a, **kw)
        if result is not None:
            built.append(label)

    _build("RUNTIME", build_pengu_runtime, cc, ar, rebuild=args.rebuild)
    # The vendored single-file C libraries behind std.lingua/std.regulus.
    # They are archived here (not compiled into the runtime) so their code is
    # only linked by a program that imports the matching binding.
    _build("STD_C", build_std_c, cc, ar, BUILD_DIR, rebuild=args.rebuild)

    # A shared PCH of pengu_runtime.h: 'pengu build'/'pengu run' reuse it through
    # -Ibuild/include instead of regenerating a throw-away one per build. It is
    # strictly best effort and never fails the runtime build.
    try:
        pch = build_runtime_pch(cc, rebuild=args.rebuild)
        if pch is not None:
            built.append("PCH")
    except Exception as e:  # noqa: BLE001 - the PCH is an optional accelerator
        print(f"[PCH] skipped ({e})", file=sys.stderr)

    print(f"=== Runtime build finished. Built: {', '.join(built) or '(none)'} ===")


if __name__ == "__main__":
    main()
