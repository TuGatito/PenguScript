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
from pathlib import Path
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

    for prefix in fhs_prefixes():
        p = prefix / "include" / "pengu"
        if p.is_dir():
            dirs.append(p)

    exe_dir = executable_dir()
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

    mip = getattr(sys, "_MEIPASS", None)
    if mip:
        for sub in ("runtime/include", "runtime", ""):
            p = (Path(mip) / sub) if sub else Path(mip)
            if p.is_dir():
                dirs.append(p)

    return _dedup(dirs)


def runtime_lib_dirs() -> List[Path]:
    """Directories that may contain the runtime's static libraries."""
    dirs: List[Path] = []

    env = os.environ.get("PENGU_LIB_DIR")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            dirs.append(p)

    for prefix in fhs_prefixes():
        # Scoped strictly to lib/pengu and lib64/pengu to prevent auto-linking
        # arbitrary system libraries from /usr/lib.
        for sub in ("lib/pengu", "lib64/pengu"):
            p = prefix / sub
            if p.is_dir():
                dirs.append(p)

    exe_dir = executable_dir()
    if exe_dir is not None:
        for sub in ("runtime/lib", "runtime"):
            p = exe_dir / sub
            if p.is_dir():
                dirs.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "build" / "lib"
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

    for prefix in fhs_prefixes():
        for sub in ("share/pengu/std", "lib/pengu/std"):
            p = prefix / sub
            if p.is_dir():
                dirs.append(p)

    exe_dir = executable_dir()
    if exe_dir is not None:
        p = exe_dir / "std"
        if p.is_dir():
            dirs.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "std"
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

    for prefix in fhs_prefixes():
        for sub in ("share/pengu/VERSION", "lib/pengu/VERSION"):
            p = prefix / sub
            if p.is_file():
                files.append(p)

    exe_dir = executable_dir()
    if exe_dir is not None:
        p = exe_dir / "VERSION"
        if p.is_file():
            files.append(p)

    for base in (module_root(), Path.cwd()):
        p = base / "VERSION"
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


def find_version_file() -> Optional[Path]:
    """Return the first ``VERSION`` file found across every layout."""
    files = version_files()
    return files[0] if files else None


# ---------------------------------------------------------------------------
# pkg-config helpers (POSIX only).  build_runtime.py deliberately skips the
# Windows-tuned static builds of libxml2 / libcurl / libmicrohttpd on POSIX
# hosts; these helpers give the same include/link flags those libraries would
# have provided on Windows.
# ---------------------------------------------------------------------------


def _pkg_config(args: List[str]) -> List[str]:
    if sys.platform.startswith("win"):
        return []
    pkgconfig = shutil.which("pkg-config")
    if not pkgconfig:
        return []
    try:
        res = subprocess.run([pkgconfig] + args, capture_output=True, text=True)
    except OSError:
        return []
    if res.returncode != 0:
        return []
    return [tok for tok in res.stdout.split() if tok]


def pkg_config_cflags(package: str) -> List[str]:
    """``pkg-config --cflags <package>`` (empty list when unavailable)."""
    return _pkg_config(["--cflags", package])


def pkg_config_libs(package: str) -> List[str]:
    """``pkg-config --libs <package>`` (empty list when unavailable)."""
    return _pkg_config(["--libs", package])
