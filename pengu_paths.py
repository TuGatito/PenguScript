#!/usr/bin/env python3
"""pengu_paths.py - Locate PenguScript runtime assets across all supported layouts.

PenguScript ships its runtime (static C libraries + C headers), its standard
library (``std/*.pengu``) and its version file in one of four layouts:

* **Source checkout** (development):
      <repo>/build/lib/*.a
      <repo>/build/include/*.h
      <repo>/std/ ,  <repo>/VERSION

* **Portable bundle** (``pengucc_build/`` produced by ``make_release.py``):
      <bundle>/runtime/lib/*.a
      <bundle>/runtime/include/*.h
      <bundle>/runtime/pengu_runtime.h
      <bundle>/std/ ,  <bundle>/VERSION

* **FHS install** (Linux/macOS user or system prefix):
      <prefix>/bin/pengu
      <prefix>/lib/pengu/*.a
      <prefix>/include/pengu/*.h
      <prefix>/share/pengu/std/*.pengu
      <prefix>/share/pengu/VERSION

* **PyInstaller** (``_MEIPASS`` data payload, fallback only).

The helpers probe every layout in priority order and return the first
directories that exist. Environment overrides (``PENGU_PREFIX``,
``PENGU_INCLUDE_DIR``, ``PENGU_LIB_DIR``, ``PENGU_STD_DIR``,
``PENGU_VERSION_FILE``, ``PENGU_RUNTIME_HEADER``) short-circuit the search
for testing and relocation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Tuple
from typing import Iterable, List, Optional


_PENGU_EXE_NAMES = frozenset({"pengu", "pengu.exe", "pengu-cli", "pengu-cli.exe"})


def _is_pengu_binary(path: Path) -> bool:
    return path.name.lower() in _PENGU_EXE_NAMES


def _dedup(paths: Iterable[Path]) -> List[Path]:
    out: List[Path] = []
    seen = set()
    for p in paths:
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def module_root() -> Path:
    """Directory containing this module (repo root in a source checkout)."""
    return Path(__file__).resolve().parent


def executable_dir() -> Optional[Path]:
    """Directory of the running ``pengu`` binary, or ``None`` under a plain
    Python interpreter (development mode)."""
    exe = Path(sys.executable)
    if not _is_pengu_binary(exe):
        return None
    try:
        return exe.resolve().parent
    except OSError:
        return exe.parent


def _install_dir() -> Optional[Path]:
    """Directory of the installed ``pengu`` binary, stable across processes.

    ``executable_dir`` only recognises the documented binary names.  A frozen
    build can be renamed (``pengu-linux``, a wrapper, ...), and in that case the
    data next to the executable is still the stable, user-visible installation:
    preferring it over PyInstaller's per-process ``_MEIPASS`` is what makes the
    script cache reusable.  Returns ``None`` for a plain ``python`` run.
    """
    found = executable_dir()
    if found is not None:
        return found
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        try:
            return exe.resolve().parent
        except OSError:
            return exe.parent
    return None


def fhs_prefixes() -> List[Path]:
    """FHS prefixes to probe, highest priority first.

    * ``$PENGU_PREFIX`` (explicit override)
    * ``<prefix>`` when ``pengu`` lives at ``<prefix>/bin/pengu``
    * ``~/.local`` (POSIX)
    * ``$XDG_DATA_HOME``'s sibling prefix (POSIX)
    * ``/usr/local`` and ``/usr`` (POSIX)
    """
    prefixes: List[Path] = []

    env = os.environ.get("PENGU_PREFIX")
    if env:
        prefixes.append(Path(env).expanduser())

    exe_dir = executable_dir()
    if exe_dir is not None and exe_dir.name == "bin":
        prefixes.append(exe_dir.parent)

    if not sys.platform.startswith("win"):
        home = Path.home()
        prefixes.append(home / ".local")

        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            prefixes.append(Path(xdg_data).expanduser().parent)

        prefixes.append(Path("/usr/local"))
        prefixes.append(Path("/usr"))

    return _dedup(prefixes)


def runtime_include_dirs() -> List[Path]:
    """Directories that may contain ``pengu_runtime.h`` and dependency headers."""
    dirs: List[Path] = []

    env = os.environ.get("PENGU_INCLUDE_DIR")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            dirs.append(p)

    env_prefix = os.environ.get("PENGU_PREFIX")
    if env_prefix:
        p = Path(env_prefix).expanduser() / "include" / "pengu"
        if p.is_dir():
            dirs.append(p)

    # The installation directory is stable across processes; PyInstaller's
    # ``_MEIPASS`` is recreated for every invocation.  Prefer the former so the
    # compiler reads the same runtime header a user can inspect and update, and
    # so the script-cache key does not inherit an ephemeral path.
    exe_dir = _install_dir()
    if exe_dir is not None:
        for sub in ("runtime/include", "runtime"):
            p = exe_dir / sub
            if p.is_dir():
                dirs.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "build" / "include"
        if p.is_dir():
            dirs.append(p)
        if (base / "pengu_runtime.h").is_file():
            dirs.append(base)

    for prefix in fhs_prefixes():
        p = prefix / "include" / "pengu"
        if p.is_dir():
            dirs.append(p)

    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        for sub in ("runtime/include", "runtime", ""):
            p = (Path(mip) / sub) if sub else Path(mip)
            if p.is_dir():
                dirs.append(p)

    return _dedup(dirs)


def runtime_lib_dirs() -> List[Path]:
    """Directories that may contain the runtime's static libraries.

    ``PENGU_LIB_DIR`` is an **override**, not one more search path: when it is
    set to an existing directory, that directory is the only one searched.

    That distinction matters beyond deployment. The built-in candidates always
    include the source checkout's ``build/lib``, so an additive variable could
    never express "there is no runtime here" -- and
    ``tests/test_build_runtime_link.py`` needs exactly that to exercise the
    missing-archive pre-flight. Because it could not, that test renamed the real
    ``libpengu_runtime.a`` out of the checkout for the duration of one build.
    Every other build running at that moment then failed with
    ``cannot find -lpengu_runtime``: invisible in a serial run, and the single
    largest source of failures under pytest-xdist.
    """
    dirs: List[Path] = []

    env = os.environ.get("PENGU_LIB_DIR")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return [p]

    env_prefix = os.environ.get("PENGU_PREFIX")
    if env_prefix:
        p_env = Path(env_prefix).expanduser()
        for sub in ("lib/pengu", "lib64/pengu"):
            p = p_env / sub
            if p.is_dir():
                dirs.append(p)

    exe_dir = _install_dir()
    if exe_dir is not None:
        for sub in ("runtime/lib", "runtime"):
            p = exe_dir / sub
            if p.is_dir():
                dirs.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "build" / "lib"
        if p.is_dir():
            dirs.append(p)

    for prefix in fhs_prefixes():
        # Scoped strictly to lib/pengu and lib64/pengu to prevent auto-linking
        # arbitrary system libraries from /usr/lib.
        for sub in ("lib/pengu", "lib64/pengu"):
            p = prefix / sub
            if p.is_dir():
                dirs.append(p)

    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        for sub in ("runtime/lib", "runtime", ""):
            p = (Path(mip) / sub) if sub else Path(mip)
            if p.is_dir():
                dirs.append(p)

    return _dedup(dirs)


def std_dirs() -> List[Path]:
    """Directories that may contain the ``std/`` standard library."""
    dirs: List[Path] = []

    env = os.environ.get("PENGU_STD_DIR") or os.environ.get("PENGU_STD_PATH")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            dirs.append(p)

    env_prefix = os.environ.get("PENGU_PREFIX")
    if env_prefix:
        p_env = Path(env_prefix).expanduser()
        for sub in ("share/pengu/std", "lib/pengu/std"):
            p = p_env / sub
            if p.is_dir():
                dirs.append(p)

    # Stable installation first: in a frozen build ``module_root()`` is inside
    # the per-process ``_MEIPASS`` extraction, and a path from there changes on
    # every run (which used to poison both the import cache and the binary key).
    exe_dir = _install_dir()
    if exe_dir is not None:
        p = exe_dir / "std"
        if p.is_dir():
            dirs.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "std"
        if p.is_dir():
            dirs.append(p)

    for prefix in fhs_prefixes():
        for sub in ("share/pengu/std", "lib/pengu/std"):
            p = prefix / sub
            if p.is_dir():
                dirs.append(p)

    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        p = Path(mip) / "std"
        if p.is_dir():
            dirs.append(p)

    return _dedup(dirs)


def version_files() -> List[Path]:
    """Files that may contain the toolchain version string."""
    files: List[Path] = []

    env = os.environ.get("PENGU_VERSION_FILE")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            files.append(p)

    env_prefix = os.environ.get("PENGU_PREFIX")
    if env_prefix:
        p_env = Path(env_prefix).expanduser()
        for sub in ("share/pengu/VERSION", "lib/pengu/VERSION"):
            p = p_env / sub
            if p.is_file():
                files.append(p)

    exe_dir = _install_dir()
    if exe_dir is not None:
        p = exe_dir / "VERSION"
        if p.is_file():
            files.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "VERSION"
        if p.is_file():
            files.append(p)

    for prefix in fhs_prefixes():
        for sub in ("share/pengu/VERSION", "lib/pengu/VERSION"):
            p = prefix / sub
            if p.is_file():
                files.append(p)

    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        p = Path(mip) / "VERSION"
        if p.is_file():
            files.append(p)

    return _dedup(files)


def find_runtime_header() -> Optional[Path]:
    """Return the first ``pengu_runtime.h`` found across every layout."""
    env = os.environ.get("PENGU_RUNTIME_HEADER")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()

    for d in runtime_include_dirs():
        p = d / "pengu_runtime.h"
        if p.is_file():
            return p

    # Last-ditch: alongside this module (source checkout without build_runtime).
    for base in (module_root(), Path.cwd()):
        for sub in ("pengu_parser", ""):
            p = (base / sub / "pengu_runtime.h") if sub else (base / "pengu_runtime.h")
            if p.is_file():
                return p

    return None


def find_std_dir() -> Optional[Path]:
    """Return the first ``std/`` directory found across every layout."""
    dirs = std_dirs()
    return dirs[0] if dirs else None


def std_c_dir() -> Optional[Path]:
    """Return the stable directory holding the vendored ``std_c`` C headers.

    The generated bundle may ``#include "utf8.h"`` / ``"re.h"`` from here, so it
    is a build input: the installation copy must win over the per-process
    PyInstaller extraction, both for correctness after an upgrade and for a
    stable script-cache key.
    """
    candidates: List[Path] = []
    exe_dir = _install_dir()
    if exe_dir is not None:
        candidates.append(exe_dir / "std_c")
    for base in (module_root(), Path.cwd()):
        candidates.append(base / "std_c")
    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        candidates.append(Path(mip) / "std_c")
    for candidate in _dedup(candidates):
        if candidate.is_dir():
            return candidate
    return None


def find_version_file() -> Optional[Path]:
    """Return the first ``VERSION`` file found across every layout."""
    files = version_files()
    return files[0] if files else None


# ---------------------------------------------------------------------------
# pkg-config helpers (POSIX only).  The core runtime needs no external
# libraries, but a satellite binding installed with `pengu add` may: these
# helpers resolve the include/link flags of whatever pkg-config module a
# project's `links:`/native dependencies name.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=128)
def _pkg_config_cached(pkgconfig: str, args: Tuple[str, ...]) -> Tuple[str, ...]:
    """Memoized ``pkg-config`` probe.

    A single ``pengu build``/``pengu run`` asks for the same four packages from
    several places (cflags, libs, the platform tail); spawning pkg-config every
    time costs ~250 ms per cache miss, which is a third of a TCC build.  The
    resolved path of pkg-config is part of the key, so a different toolchain (or
    a test that changes ``PATH``) cannot read another one's results.
    ``PKG_CONFIG_PATH`` changes within a process are not tracked: call
    :func:`clear_pkg_config_cache` when mutating it in-process.
    """
    try:
        res = subprocess.run([pkgconfig, *args], capture_output=True, text=True)
    except OSError:
        return ()
    if res.returncode != 0:
        return ()
    return tuple(tok for tok in res.stdout.split() if tok)


def clear_pkg_config_cache() -> None:
    """Forgets every memoized pkg-config probe (tests, in-process env changes)."""
    _pkg_config_cached.cache_clear()


def _pkg_config(args: List[str]) -> List[str]:
    if sys.platform.startswith("win"):
        return []
    pkgconfig = shutil.which("pkg-config")
    if not pkgconfig:
        return []
    return list(_pkg_config_cached(pkgconfig, tuple(args)))


def pkg_config_cflags(package: str) -> List[str]:
    """``pkg-config --cflags <package>`` (empty list when unavailable)."""
    return _pkg_config(["--cflags", package])


def pkg_config_libs(package: str) -> List[str]:
    """``pkg-config --libs <package>`` (empty list when unavailable)."""
    return _pkg_config(["--libs", package])
