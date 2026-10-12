#!/usr/bin/env python3
"""build_runtime.py - Compiles the PenguScript C runtime.

Compiles into ``build/lib/``:

  - ``build_pengu_runtime`` -> ``libpengu_runtime.a`` (core + filum)
  - ``build_runtime_pch``   -> ``build/include/pengu_runtime.h.gch`` (optional)

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
    parser.add_argument("--headers-only", action="store_true",
                        help="Only stage pengu_runtime.h into build/include/.")
    args = parser.parse_args()

    cc, ar = get_toolchain()
    print(f"=== Building PenguScript Runtime (CC: {cc}, AR: {ar}) ===")

    if args.headers_only:
        INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT_DIR / "pengu_runtime.h", INCLUDE_DIR / "pengu_runtime.h")
        print("[RUNTIME] staged pengu_runtime.h only (--headers-only)")
        return

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
