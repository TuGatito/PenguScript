"""Global, XDG-compliant caches for the PenguScript toolchain.

Four kinds of artefacts are persisted outside the project tree so that
``pengu run`` stays fast and never touches the user's ``build/`` directory:

``<cache>/parser/``
    Lark's serialized LALR tables for the embedded grammar.  Building them costs
    seconds on every process start (they are pure-Python), so this is the single
    biggest startup win of the whole toolchain.  Lark validates the cache with a
    sha256 over the grammar + options + Lark/Python version, so an edit to
    ``pengu_grammar.py`` invalidates it automatically.

``<cache>/imports/``
    The resolved import graph of one entry file: root-relative module references
    plus a content digest each.  A PyInstaller onefile build extracts ``std/``
    into a new ``_MEIPASS`` on every run, so storing absolute paths there made
    the manifest permanently invalid.  References are re-resolved against the
    current ``std`` roots and a digest decides whether the graph still matches.

``<cache>/scripts/<key>/``
    The compiled binary of a standalone ``pengu run script.pengu``.  The key is a
    sha256 over the *content* of the script, every module it imports, the
    runtime header/archive, the toolchain version, the compiler and the build
    options — never over mtimes or absolute module paths, so a cache hit is
    always the right binary.

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


def _relative_id(path: str, root: str) -> Optional[str]:
    """``path`` relative to ``root`` as a POSIX-style string, or None.

    Returns None when ``path`` is outside ``root`` or on another Windows drive,
    so callers can try the next candidate root instead of caching ``../..``.
    """
    try:
        rel = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
    except ValueError:
        return None
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return None
    return rel.replace(os.sep, "/")


def logical_module_id(
    path: str,
    *,
    entry_abs: Optional[str] = None,
    base_dir: Optional[str] = None,
    std_dirs: Iterable[str] = (),
) -> str:
    """A layout-independent identity for a compiled module.

    The binary cache used to hash each module's **absolute path** together with
    its content.  In a PyInstaller onefile build the standard library lives
    under a new ``/tmp/_MEI...`` directory on every invocation, so the key
    changed even when nothing the user wrote had changed.  The identity keeps
    the logical location (``std:spark``, ``project:lib/helper``) and the caller
    hashes the content separately.

    ``std:`` wins over ``project:`` because the standard library is identified
    by its logical module name, not by which installation directory supplied it.
    """
    path_abs = os.path.abspath(path)
    for root in std_dirs:
        rel = _relative_id(path_abs, root)
        if rel is not None:
            return "std:" + rel
    for root in (base_dir, os.path.dirname(os.path.abspath(entry_abs)) if entry_abs else None):
        if not root:
            continue
        rel = _relative_id(path_abs, root)
        if rel is not None:
            return "project:" + rel
    # A module outside every known root (a binding vendored elsewhere).  The
    # content digest disambiguates two files that happen to share a basename.
    return "external:" + os.path.basename(path_abs).lower()


def directory_digest(path: str) -> str:
    """sha256 over every file under ``path`` (relative name + content)."""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, path).replace(os.sep, "/")
            h.update(b"\0file\0" + rel.encode("utf-8") + b"\0")
            try:
                h.update(file_content_digest(full).encode("ascii"))
            except OSError:
                h.update(b"missing")
    return h.hexdigest()


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
    runtime_archive: Optional[str] = None,
    module_ids: Optional[Iterable[str]] = None,
    entry_id: Optional[str] = None,
    extra_digests: Optional[Iterable[str]] = None,
) -> str:
    """sha256 over the *contents* that decide the resulting binary.

    ``defines``/``links``/``cflags``/``cc``/``profile`` are part of the key on
    purpose: ``-D os=linux`` and ``-D os=windows`` are different programs.

    Paths are deliberately **not** part of the key: ``module_ids`` carries the
    logical identity (see :func:`logical_module_id`) and the compiler path is
    reduced to its basename.  Otherwise the per-process ``_MEIPASS`` directory
    (or a bundled TCC's extraction path) made every run a cache miss.
    """
    h = hashlib.sha256()
    h.update(version.encode("utf-8"))
    h.update(b"\0cc\0" + os.path.basename(cc or "").lower().encode("utf-8"))
    h.update(b"\0profile\0" + str(profile).encode("utf-8"))
    h.update(b"\0defines\0" + "\0".join(sorted(defines or [])).encode("utf-8"))
    h.update(b"\0links\0" + "\0".join(sorted(links or [])).encode("utf-8"))
    h.update(b"\0cflags\0" + "\0".join(sorted(cflags or [])).encode("utf-8"))
    h.update(b"\0entry\0" + (entry_id or os.path.basename(entry_abs)).encode("utf-8"))
    modules = list(module_order)
    ids = list(module_ids) if module_ids is not None else None
    if ids is not None and len(ids) != len(modules):
        raise ValueError(
            f"module_ids has {len(ids)} entries but module_order has {len(modules)}"
        )
    for idx, mod in enumerate(modules):
        ident = ids[idx] if ids is not None else os.path.basename(mod)
        h.update(b"\0mod\0" + ident.encode("utf-8") + b"\0")
        try:
            h.update(file_content_digest(mod).encode("ascii"))
        except OSError:
            h.update(b"missing")
    if runtime_header and os.path.isfile(runtime_header):
        h.update(b"\0runtime\0" + file_content_digest(runtime_header).encode("ascii"))
    # The archive is a build input too: a runtime bugfix that does not touch the
    # header must not reuse a binary linked against the old archive.
    if runtime_archive and os.path.isfile(runtime_archive):
        h.update(b"\0runtime-archive\0" + file_content_digest(runtime_archive).encode("ascii"))
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
    """Existing cached binary for ``key``, if any.

    A hit refreshes the entry directory's mtime.  ``gc_script_cache`` ages
    entries by that mtime, so without this a cache entry used every day could be
    deleted on day 30 while one never used stayed forever.
    """
    path = cached_binary_path(key)
    if path and os.path.isfile(path) and os.access(path, os.X_OK):
        try:
            os.utime(os.path.dirname(path), None)
        except OSError:
            pass
        return path
    return None


def store_cached_binary(key: str, source: str) -> Optional[str]:
    """Copies a freshly built binary into the cache (atomically enough)."""
    dest = cached_binary_path(key)
    if dest is None or not os.path.isfile(source):
        return None
    dest_dir = os.path.dirname(dest)
    tmp = dest + f".{os.getpid()}.tmp"
    try:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(source, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, dest)
        return dest
    except OSError:
        # Leave no empty directory behind: `gc`/`doctor` would count it as an
        # entry, and the next failed store would try to reuse it.
        try:
            if os.path.isfile(tmp):
                os.unlink(tmp)
            if os.path.isdir(dest_dir) and not os.listdir(dest_dir):
                os.rmdir(dest_dir)
        except OSError:
            pass
        return None


# ---------------------------------------------------------------------------
# Import graph (module list) cache
# ---------------------------------------------------------------------------

def _imports_dir() -> Optional[str]:
    return _ensure_subdir("imports")


def _normalise_resolution(entry_abs: str, resolution: Optional[dict]) -> dict:
    """Fills and normalises a resolution context.

    Only ``base_dir``/``lib_dir``/``src_dir`` are persisted: the ``std`` roots
    are intentionally *not* frozen into the manifest, because a onefile build
    supplies a different ``_MEIPASS`` on every run.  Refs are re-resolved against
    the current roots and a content digest decides whether each one is still the
    same module.
    """
    source = dict(resolution or {})
    base_dir = os.path.abspath(source.get("base_dir") or os.path.dirname(os.path.abspath(entry_abs)))
    std_dirs = list(source.get("std_dirs") or ())
    if not std_dirs:
        from pengu_paths import std_dirs as _std_dirs
        std_dirs = [str(p) for p in _std_dirs()]
    return {
        "base_dir": base_dir,
        "lib_dir": str(source.get("lib_dir") or "lib"),
        "src_dir": str(source.get("src_dir") or "src"),
        "std_dirs": [os.path.abspath(str(p)) for p in std_dirs],
    }


def _resolution_fingerprint(resolution: dict) -> str:
    raw = "\0".join((
        os.path.normcase(os.path.abspath(resolution["base_dir"])),
        str(resolution["lib_dir"]),
        str(resolution["src_dir"]),
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _module_list_path(entry_abs: str, resolution: dict) -> Optional[str]:
    directory = _imports_dir()
    if directory is None:
        return None
    try:
        entry_digest = file_content_digest(entry_abs)
    except OSError:
        return None
    # The entry *path* participates through the resolution fingerprint, so two
    # scripts with identical text in different projects do not fight over one
    # file.  A change to base/lib/src selects a different file, i.e. a miss.
    return os.path.join(
        directory,
        f"v2-{entry_digest[:24]}-{_resolution_fingerprint(resolution)}.json",
    )


def _module_ref(path: str, resolution: dict) -> dict:
    """Serialises a module as a root-relative reference."""
    path_abs = os.path.abspath(path)
    for root in resolution["std_dirs"]:
        rel = _relative_id(path_abs, root)
        if rel is not None:
            return {"kind": "std", "rel": rel}
    rel = _relative_id(path_abs, resolution["base_dir"])
    if rel is not None:
        return {"kind": "base", "rel": rel}
    return {"kind": "abs", "path": path_abs}


def _resolve_module_ref(ref: dict, resolution: dict, expected_digest: str) -> Optional[str]:
    """Maps a reference back to the current file with that content digest."""
    kind = ref.get("kind")
    if kind == "std":
        rel = ref.get("rel") or ""
        # Honour the *current* search order: the first root that provides the
        # module is the one the resolver would use now.  Comparing its digest
        # (and stopping on a mismatch, instead of looking for the old content in
        # a lower-priority root) is what makes `PENGU_STD_DIR=<new std>` invalidate
        # the manifest while an unchanged `_MEIPASS` copy cannot mask the change.
        for root in resolution["std_dirs"]:
            candidate = os.path.join(root, *rel.split("/"))
            if not os.path.isfile(candidate):
                continue
            try:
                if file_content_digest(candidate) == expected_digest:
                    return os.path.abspath(candidate)
            except OSError:
                pass
            return None
        return None
    if kind == "base":
        candidate = os.path.join(resolution["base_dir"], *(ref.get("rel") or "").split("/"))
    elif kind == "abs":
        candidate = ref.get("path") or ""
    else:
        return None
    if not os.path.isfile(candidate):
        return None
    try:
        if file_content_digest(candidate) != expected_digest:
            return None
    except OSError:
        return None
    return os.path.abspath(candidate)


def load_module_list(entry_abs: str, resolution: Optional[dict] = None) -> Optional[List[str]]:
    """Reuses a previously resolved import list when nothing changed.

    Resolving the graph parses every module; the expensive part is the *parse*,
    not the walk, so the list is stored together with the content digest of each
    module.  Modules are stored as root-relative references, not absolute paths:
    a onefile build extracts ``std/`` to a different ``_MEIPASS`` every run, and
    storing that path made the cache permanently invalid (and poisoned the
    binary key).  Any edit — including a new ``import`` line — still invalidates
    the entry through its digest.
    """
    import json
    if not os.path.isfile(entry_abs):
        return None
    context = _normalise_resolution(entry_abs, resolution)
    path = _module_list_path(entry_abs, context)
    if path is None:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("entry") != os.path.normcase(entry_abs):
            return None
        stored = data.get("resolution") or {}
        current = {
            "base_dir": os.path.normcase(os.path.abspath(context["base_dir"])),
            "lib_dir": str(context["lib_dir"]),
            "src_dir": str(context["src_dir"]),
        }
        if stored.get("base_dir") != current["base_dir"]:
            return None
        if str(stored.get("lib_dir")) != current["lib_dir"]:
            return None
        if str(stored.get("src_dir")) != current["src_dir"]:
            return None
        refs = data.get("refs") or []
        digests = data.get("digests") or []
        if not refs or len(refs) != len(digests):
            return None
        modules: List[str] = []
        for ref, digest in zip(refs, digests):
            resolved = _resolve_module_ref(ref, context, str(digest))
            if resolved is None:
                return None
            modules.append(resolved)
        return modules
    except (OSError, ValueError, TypeError):
        return None


def store_module_list(
    entry_abs: str,
    modules: Iterable[str],
    resolution: Optional[dict] = None,
) -> None:
    """Persists the resolved import list of ``entry_abs`` (best effort)."""
    import json
    if not os.path.isfile(entry_abs):
        return
    context = _normalise_resolution(entry_abs, resolution)
    path = _module_list_path(entry_abs, context)
    if path is None:
        return
    try:
        modules = [os.path.abspath(m) for m in modules]
        refs: List[dict] = []
        digests: List[str] = []
        for mod in modules:
            try:
                digests.append(file_content_digest(mod))
            except OSError:
                return
            refs.append(_module_ref(mod, context))
        payload = {
            "entry": os.path.normcase(entry_abs),
            "resolution": {
                "base_dir": os.path.normcase(os.path.abspath(context["base_dir"])),
                "lib_dir": str(context["lib_dir"]),
                "src_dir": str(context["src_dir"]),
            },
            "refs": refs,
            "digests": digests,
        }
        tmp = path + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except (OSError, ValueError, TypeError):
        return


def resolve_module_list_cached(
    entry_abs: str,
    resolver,
    resolution: Optional[dict] = None,
) -> List[str]:
    """``resolver()`` with the import-list cache in front of it."""
    context = _normalise_resolution(entry_abs, resolution)
    cached = load_module_list(entry_abs, context)
    if cached:
        return cached
    modules = list(resolver())
    store_module_list(entry_abs, modules, context)
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
