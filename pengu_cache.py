"""Global, XDG-compliant caches for the PenguScript toolchain.

Three kinds of artefacts are persisted outside the project tree so that
``pengu run`` stays fast and never touches the user's ``build/`` directory:

``<cache>/parser/``
    Lark's serialized LALR tables for the embedded grammar.  Building them costs
    seconds on every process start (they are pure-Python), so this is the single
    biggest startup win of the whole toolchain.  Lark validates the cache with a
    sha256 over the grammar + options + Lark/Python version, so an edit to
    ``pengu_grammar.py`` invalidates it automatically.

``<cache>/scripts/<key>/``
    The compiled binary of a standalone ``pengu run script.pengu``.  The key is a
    sha256 over the *content* of the script, every module it imports, the
    runtime header, the toolchain version, the compiler and the build options —
    never over mtimes, so a cache hit is always the right binary.

``<cache>/std/``
    Reserved for future pre-parsed std blobs.

Every helper degrades gracefully: if the cache root is not writable (read-only
CI runner, restricted container), the functions fall back to a temporary
directory or signal "no cache" instead of failing the build.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from typing import Iterable, List, Optional

#: Set ``PENGU_CACHE=0`` to disable every persistent cache (parser tables and
#: script binaries) for a single invocation or globally.
_FALSY = {"0", "false", "no", "off", ""}


def cache_disabled() -> bool:
    """True when the user disabled the caches via ``PENGU_CACHE``."""
    return os.environ.get("PENGU_CACHE", "1").strip().lower() in _FALSY


def _xdg_cache_home() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return base


def cache_root() -> str:
    """Root directory of the PenguScript cache (``PENGU_CACHE_DIR`` overrides)."""
    override = os.environ.get("PENGU_CACHE_DIR")
    if override:
        return os.path.abspath(override)
    return os.path.join(_xdg_cache_home(), "pengu")


_fallback_root: Optional[str] = None


def _writable_dir(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".pengu_write_test")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("")
        os.unlink(probe)
        return True
    except OSError:
        return False


def _ensure_subdir(name: str) -> Optional[str]:
    """Returns a writable cache sub-directory, or None when caching is off.

    A read-only cache root (common on CI runners) falls back to a per-user
    temporary directory instead of failing the whole build.
    """
    global _fallback_root
    if cache_disabled():
        return None
    primary = os.path.join(cache_root(), name)
    if _writable_dir(primary):
        return primary
    if _fallback_root is None:
        _fallback_root = os.path.join(tempfile.gettempdir(), f"pengu-cache-{os.getuid() if hasattr(os, 'getuid') else 'user'}")
    fallback = os.path.join(_fallback_root, name)
    if _writable_dir(fallback):
        return fallback
    return None


def file_content_digest(path: str, chunk: int = 1 << 20) -> str:
    """sha256 of a file's *content* (never its mtime)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Parser tables
# ---------------------------------------------------------------------------

def parser_cache_path(grammar_digest: str) -> Optional[str]:
    """Path of the serialized Lark tables for the embedded grammar."""
    directory = _ensure_subdir("parser")
    if directory is None:
        return None
    return os.path.join(directory, f"grammar-{grammar_digest[:16]}.lark")


def grammar_digest(grammar: str) -> str:
    """sha256 of the grammar text (Lark re-validates it internally too)."""
    return hashlib.sha256(grammar.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Script binaries
# ---------------------------------------------------------------------------

def script_cache_root() -> Optional[str]:
    """Directory holding one sub-directory per compiled script."""
    return _ensure_subdir("scripts")


def script_cache_key(
    entry_abs: str,
    module_order: Iterable[str],
    *,
    version: str,
    profile: str = "debug",
    cc: str = "",
    defines: Optional[Iterable[str]] = None,
    links: Optional[Iterable[str]] = None,
    cflags: Optional[Iterable[str]] = None,
    runtime_header: Optional[str] = None,
    extra_digests: Optional[Iterable[str]] = None,
) -> str:
    """sha256 over the *contents* that decide the resulting binary.

    ``defines``/``links``/``cflags``/``cc``/``profile`` are part of the key on
    purpose: ``-D os=linux`` and ``-D os=windows`` are different programs.
    """
    h = hashlib.sha256()
    h.update(version.encode("utf-8"))
    h.update(b"\0cc\0" + (cc or "").encode("utf-8"))
    h.update(b"\0profile\0" + str(profile).encode("utf-8"))
    h.update(b"\0defines\0" + "\0".join(sorted(defines or [])).encode("utf-8"))
    h.update(b"\0links\0" + "\0".join(sorted(links or [])).encode("utf-8"))
    h.update(b"\0cflags\0" + "\0".join(sorted(cflags or [])).encode("utf-8"))
    h.update(b"\0entry\0" + os.path.normcase(entry_abs).encode("utf-8"))
    for mod in module_order:
        h.update(b"\0mod\0" + os.path.normcase(os.path.abspath(mod)).encode("utf-8") + b"\0")
        try:
            h.update(file_content_digest(mod).encode("ascii"))
        except OSError:
            h.update(b"missing")
    if runtime_header and os.path.isfile(runtime_header):
        h.update(b"\0runtime\0" + file_content_digest(runtime_header).encode("ascii"))
    for digest in extra_digests or []:
        h.update(b"\0extra\0" + str(digest).encode("ascii"))
    return h.hexdigest()[:32]


def script_binary_name() -> str:
    """File name of a cached script binary for this platform.

    Windows ``CreateProcess`` appends ``.exe`` when it is given an extension-less
    image name, so a cached file called plain ``app`` is *not* executable there
    (the OS looks for ``app.exe`` and fails with "file not found").  Keeping the
    platform suffix makes the cached artefact runnable everywhere.
    """
    return "app.exe" if sys.platform == "win32" else "app"


def cached_binary_path(key: str) -> Optional[str]:
    """Path where the binary of ``key`` lives (``None`` when caching is off)."""
    root = script_cache_root()
    if root is None:
        return None
    return os.path.join(root, key, script_binary_name())


def lookup_cached_binary(key: str) -> Optional[str]:
    """Existing cached binary for ``key``, if any."""
    path = cached_binary_path(key)
    if path and os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    return None


def store_cached_binary(key: str, source: str) -> Optional[str]:
    """Copies a freshly built binary into the cache (atomically enough)."""
    dest = cached_binary_path(key)
    if dest is None or not os.path.isfile(source):
        return None
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + f".{os.getpid()}.tmp"
        shutil.copy2(source, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, dest)
        return dest
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Import graph (module list) cache
# ---------------------------------------------------------------------------

def _imports_dir() -> Optional[str]:
    return _ensure_subdir("imports")


def load_module_list(entry_abs: str) -> Optional[List[str]]:
    """Reuses a previously resolved import list when nothing changed.

    Resolving the graph parses every module; the expensive part is the *parse*,
    not the walk, so the list is stored together with the content digest of each
    module.  Any edit (including a new ``import`` line) invalidates it.
    """
    import json
    directory = _imports_dir()
    if directory is None or not os.path.isfile(entry_abs):
        return None
    try:
        entry_digest = file_content_digest(entry_abs)
    except OSError:
        return None
    path = os.path.join(directory, f"{entry_digest[:32]}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        modules = data.get("modules") or []
        digests = data.get("digests") or {}
        if not modules or data.get("entry") != os.path.normcase(entry_abs):
            return None
        for mod in modules:
            if not os.path.isfile(mod):
                return None
            if digests.get(mod) != file_content_digest(mod):
                return None
        return list(modules)
    except (OSError, ValueError):
        return None


def store_module_list(entry_abs: str, modules: Iterable[str]) -> None:
    """Persists the resolved import list of ``entry_abs`` (best effort)."""
    import json
    directory = _imports_dir()
    if directory is None or not os.path.isfile(entry_abs):
        return
    try:
        entry_digest = file_content_digest(entry_abs)
        modules = [os.path.abspath(m) for m in modules]
        digests = {}
        for mod in modules:
            try:
                digests[mod] = file_content_digest(mod)
            except OSError:
                return
        path = os.path.join(directory, f"{entry_digest[:32]}.json")
        tmp = path + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"entry": os.path.normcase(entry_abs),
                       "modules": modules,
                       "digests": digests}, fh)
        os.replace(tmp, path)
    except (OSError, ValueError):
        return


def resolve_module_list_cached(entry_abs: str, resolver) -> List[str]:
    """``resolver()`` with the import-list cache in front of it."""
    cached = load_module_list(entry_abs)
    if cached:
        return cached
    modules = list(resolver())
    store_module_list(entry_abs, modules)
    return modules


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def clear_script_cache(verbose: bool = False) -> int:
    """Removes every cached script binary. Returns the number of entries removed."""
    root = script_cache_root()
    if root is None or not os.path.isdir(root):
        return 0
    removed = 0
    for name in os.listdir(root):
        entry = os.path.join(root, name)
        if not os.path.isdir(entry):
            continue
        shutil.rmtree(entry, ignore_errors=True)
        removed += 1
    if verbose:
        print(f"cleared {removed} cached script(s) from {root}")
    return removed


def gc_script_cache(max_age_days: int = 30, verbose: bool = False,
                    everything: bool = False) -> int:
    """Removes cached scripts unused for ``max_age_days`` (all when ``everything``)."""
    import time as _time
    root = script_cache_root()
    if root is None or not os.path.isdir(root):
        return 0
    cutoff = _time.time() - max_age_days * 86400
    removed = 0
    for name in os.listdir(root):
        entry = os.path.join(root, name)
        if not os.path.isdir(entry):
            continue
        try:
            mtime = os.path.getmtime(entry)
        except OSError:
            continue
        if everything or mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
            if verbose:
                print(f"  removed {name}")
    return removed


def cache_summary() -> List[str]:
    """Human-readable lines describing the cache layout (used by ``pengu doctor``)."""
    lines = [f"cache root: {cache_root()}"]
    for name in ("parser", "scripts", "std"):
        directory = os.path.join(cache_root(), name)
        if os.path.isdir(directory):
            try:
                count = len(os.listdir(directory))
            except OSError:
                count = 0
            lines.append(f"  {name}/: {count} entr{'y' if count == 1 else 'ies'}")
        else:
            lines.append(f"  {name}/: (absent)")
    if cache_disabled():
        lines.append("  caching: DISABLED (PENGU_CACHE=0)")
    return lines
