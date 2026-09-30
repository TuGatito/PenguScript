"""TinyCC discovery and packaged-binary helpers.

TCC compiles the generated bundle roughly an order of magnitude faster than gcc,
which matters for the *cache miss* path of ``pengu run``.  It is shipped inside
the PyInstaller bundle (``--add-binary``) and located in this order:

1. ``<bundle>/tcc/tcc`` (``sys._MEIPASS`` when frozen),
2. ``<checkout>/tcc/tcc`` (an unpacked release next to the sources),
3. ``$PENGU_TCC``,
4. ``PATH``.

``PENGU_DEV_CC`` overrides everything (handy for CI or for forcing gcc when TCC
miscompiles something), and ``PENGU_NO_TCC=1`` disables TCC entirely.

The runtime header uses GNU extensions (``__extension__`` statement
expressions, ``__attribute__((always_inline))``) that TCC supports, but a
failure is expected to be handled by the caller: rebuild with the configured
``cc`` and report it (see ``PenguBuilder.compile``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional


def _exe(name: str) -> str:
    return name + (".exe" if sys.platform == "win32" else "")


def _bundle_base() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def find_tcc() -> Optional[str]:
    """Absolute path of a usable TCC, or None."""
    if os.environ.get("PENGU_NO_TCC", "").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    base = _bundle_base()
    candidates: List[str] = [
        os.path.join(base, "tcc", _exe("tcc")),
        os.path.join(base, _exe("tcc")),
        os.path.join(base, "tcc-dist", "bin", _exe("tcc")),
        os.path.join(base, "tcc-dist", _exe("tcc")),
    ]
    env = os.environ.get("PENGU_TCC")
    if env:
        candidates.append(env)
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return os.path.abspath(cand)
    found = shutil.which("tcc")
    return os.path.abspath(found) if found else None


def tcc_lib_dirs(tcc_path: Optional[str] = None) -> List[str]:
    """Include dirs shipped next to TCC (its own headers)."""
    tcc_path = tcc_path or find_tcc()
    if not tcc_path:
        return []
    root = os.path.dirname(tcc_path)
    dirs = []
    for rel in ("include", os.path.join("lib", "tcc", "include"),
                os.path.join(os.path.dirname(root), "lib", "tcc", "include")):
        cand = os.path.join(root, rel)
        if os.path.isdir(cand):
            dirs.append(os.path.abspath(cand))
    return dirs


def pick_dev_compiler(configured: Optional[str] = None) -> str:
    """Compiler to use for a *development* compile (``pengu run``).

    ``PENGU_DEV_CC`` wins, then TCC when available, then the configured
    compiler, then ``gcc``.
    """
    override = os.environ.get("PENGU_DEV_CC")
    if override:
        return override
    tcc = find_tcc()
    if tcc:
        return tcc
    return configured or "gcc"


def tcc_available() -> bool:
    return find_tcc() is not None


def tcc_version(tcc_path: Optional[str] = None) -> Optional[str]:
    tcc_path = tcc_path or find_tcc()
    if not tcc_path:
        return None
    try:
        res = subprocess.run([tcc_path, "-v"], capture_output=True, text=True, timeout=10)
        text = (res.stderr or res.stdout or "").strip().splitlines()
        return text[0] if text else "tcc (unknown version)"
    except Exception:
        return None


def ensure_tcc(dest_dir: str, verbose: bool = False) -> Optional[str]:
    """Builds or downloads TCC into ``dest_dir`` (used by ``make_release.py``).

    Linux/macOS: builds TinyCC from source with the system toolchain.
    Windows: expects a prebuilt archive to be provided via ``PENGU_TCC_URL`` or
    already unpacked in ``dest_dir`` (CI downloads it with PowerShell).

    Returns the path of the produced ``tcc`` binary, or None when unavailable
    (the release then ships without TCC and falls back to gcc/clang).
    """
    os.makedirs(dest_dir, exist_ok=True)
    existing = find_tcc() if False else None  # never reuse the dev checkout here
    del existing
    for name in (_exe("tcc"), os.path.join("bin", _exe("tcc"))):
        cand = os.path.join(dest_dir, name)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    if not verbose:
        pass

    if sys.platform == "win32":
        marker = os.path.join(dest_dir, "tcc.exe")
        return os.path.abspath(marker) if os.path.isfile(marker) else None

    src = os.path.join(dest_dir, "tinycc-src")
    if not os.path.isdir(src):
        if not shutil.which("git"):
            return None
        res = subprocess.run(["git", "clone", "--depth", "1",
                              "https://github.com/TinyCC/tinycc.git", src],
                             capture_output=True, text=True)
        if res.returncode != 0:
            return None
    prefix = os.path.join(dest_dir, "tcc-dist")
    configure = os.path.join(src, "configure")
    if not os.path.isfile(configure):
        return None
    jobs = str(max(1, (os.cpu_count() or 2)))
    for cmd in (["./configure", f"--prefix={prefix}", "--extra-cflags=-O2"],
                ["make", f"-j{jobs}"],
                ["make", "install"]):
        res = subprocess.run(cmd, cwd=src, capture_output=True, text=True)
        if res.returncode != 0:
            return None
    for name in (os.path.join("bin", _exe("tcc")), _exe("tcc")):
        cand = os.path.join(prefix, name)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return None
