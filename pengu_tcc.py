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

The prebuilt Windows archive is downloaded only from a pinned URL and only when
its SHA-256 matches :data:`TCC_RELEASE_SHA256` (Phase 9, items 9.2/9.3): a
compromised mirror must not be able to put a binary inside a release.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from typing import List, Optional

from pengu_archive import UnsafeArchiveError, safe_extract_zip, sha256_file

#: Where the prebuilt Windows TinyCC comes from (TinyCC publishes no official
#: Windows binary; this is the widely packaged ``tcc_20221020`` build).
TCC_RELEASE_URL = (
    "https://github.com/FitzRoyX/tinycc/releases/download/"
    "tcc_20221020/tcc_20221020.zip"
)

#: SHA-256 of that archive, pinned in the *code* (not only in a workflow) so the
#: verification travels with every caller: ``make_release.py``, the CI staging
#: step and any local build.  Derived once with::
#:
#:     python -c "import hashlib,urllib.request as u; \
#:         print(hashlib.sha256(u.urlopen(u.Request(TCC_RELEASE_URL)).read()).hexdigest())"
#:
#: ``PENGU_TCC_SHA256`` overrides it (only useful together with a mirror URL,
#: and the override still has to match or the download is refused).
TCC_RELEASE_SHA256 = "bba017566c78f6fbd350708957248c470920477fe42c990a72fff3de0c111fb5"


class TccIntegrityError(RuntimeError):
    """The downloaded TinyCC archive does not match the pinned SHA-256."""


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
        # Older release archives shipped the Windows binary without the '.exe'
        # suffix (the destination name used to be hard-coded); keep probing it so
        # those bundles still find their compiler.
        os.path.join(base, "tcc", "tcc"),
        os.path.join(base, _exe("tcc")),
        os.path.join(base, "tcc-dist", "bin", _exe("tcc")),
        os.path.join(base, "tcc-dist", _exe("tcc")),
        # A checkout where 'make_release.py' (or the CI staging step) ran
        # 'ensure_tcc("build/tcc-dist")': it installs under '<dest>/tcc-dist', so
        # the result lives at 'build/tcc-dist/tcc-dist/bin/tcc'.
        os.path.join(base, "build", "tcc-dist", "tcc-dist", "bin", _exe("tcc")),
        os.path.join(base, "build", "tcc-dist", "tcc-dist", _exe("tcc")),
        os.path.join(base, "build", "tcc-dist", "bin", _exe("tcc")),
        os.path.join(base, "build", "tcc-dist", _exe("tcc")),
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


def _download_windows_tcc(
    dest_dir: str,
    url: Optional[str] = None,
    expected_sha256: Optional[str] = None,
) -> Optional[str]:
    """Downloads a prebuilt TCC for Windows into ``dest_dir``.

    TinyCC has no official Windows binary release, so the release pipeline uses
    the widely packaged ``tcc_20221020`` build.  ``PENGU_TCC_URL`` overrides the
    URL (mirrors, pinned internal builds) and ``PENGU_TCC_SHA256`` the digest;
    the default digest lives in :data:`TCC_RELEASE_SHA256`, so verification does
    not depend on a workflow remembering to pass it.

    A **mismatch raises** :class:`TccIntegrityError` and nothing is extracted.
    A network failure still returns None (TCC is optional: the release falls back
    to gcc/clang), because "could not download" is not "downloaded something
    else".  Returns the ``tcc.exe`` path or None.
    """
    import urllib.request

    url = url or os.environ.get("PENGU_TCC_URL") or TCC_RELEASE_URL
    if expected_sha256 is None:
        expected = os.environ.get("PENGU_TCC_SHA256") or TCC_RELEASE_SHA256
    else:
        expected = expected_sha256
    expected = expected.strip().lower()
    if len(expected) != 64:
        raise TccIntegrityError(
            f"refusing an unpinned TinyCC download: {expected!r} is not a SHA-256"
        )
    print(f"  [TCC] downloading prebuilt TCC from {url}")
    archive = os.path.join(dest_dir, "tcc.zip")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PenguScript-Release/1"})
        with urllib.request.urlopen(req, timeout=180) as resp, open(archive, "wb") as out:
            while True:
                buf = resp.read(1024 * 1024)
                if not buf:
                    break
                out.write(buf)

        actual = sha256_file(archive)
        if actual != expected:
            raise TccIntegrityError(
                f"TinyCC archive SHA-256 mismatch for {url}\n"
                f"  expected {expected}\n"
                f"  actual   {actual}\n"
                f"  Refusing to extract or bundle it."
            )
        print(f"  [TCC] sha256 verified: {actual}")

        with zipfile.ZipFile(archive) as zf:
            safe_extract_zip(zf, dest_dir)
    except (TccIntegrityError, UnsafeArchiveError):
        # Integrity is not negotiable: never degrade to "no TCC" silently, and
        # never treat a hostile member ("../evil") as a failed download.
        raise
    except Exception as e:  # noqa: BLE001 - a failed download is not a corrupt one
        print(f"  [TCC] download failed: {e}", file=sys.stderr)
        return None
    finally:
        try:
            if os.path.isfile(archive):
                os.unlink(archive)
        except OSError:
            pass

    for root, _dirs, files in os.walk(dest_dir):
        for name in files:
            if name.lower() == "tcc.exe":
                return os.path.abspath(os.path.join(root, name))
    return None


def ensure_tcc(dest_dir: str, verbose: bool = False) -> Optional[str]:
    """Builds or downloads TCC into ``dest_dir`` (used by ``make_release.py``).

    Linux/macOS: builds TinyCC from source with the system toolchain.
    Windows: downloads a prebuilt archive (``PENGU_TCC_URL`` overrides the URL)
    unless one is already unpacked.

    Returns the path of the produced ``tcc`` binary, or None when unavailable
    (the release then ships without TCC and falls back to gcc/clang).

    Raises:
        TccIntegrityError: on Windows, when the downloaded archive does not hash
            to the pinned digest.  That is deliberately *not* a "no TCC" result:
            a release must not bundle bytes that failed verification.
    """
    # Absolute: 'make install' runs with cwd=<src>, so a relative --prefix would
    # silently land inside the source tree instead of dest_dir.
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    def _existing() -> Optional[str]:
        """A previously staged TCC, preferring the installed layout.

        ``ensure_tcc`` builds into ``<dest>/tcc-dist`` but the build also leaves
        a ``tcc`` binary inside ``<dest>/tinycc-src``; the installed one is the
        only one with a matching ``lib/tcc/include`` tree next to it, so it must
        win (the release bundles that include directory).
        """
        candidates = [
            os.path.join(dest_dir, "bin", _exe("tcc")),
            os.path.join(dest_dir, _exe("tcc")),
            os.path.join(dest_dir, "tcc", _exe("tcc")),
            os.path.join(dest_dir, "tcc-dist", "bin", _exe("tcc")),
            os.path.join(dest_dir, "tcc-dist", _exe("tcc")),
        ]
        for cand in candidates:
            if os.path.isfile(cand) and (os.access(cand, os.X_OK) or sys.platform == "win32"):
                return os.path.abspath(cand)
        for root, dirs, files in os.walk(dest_dir):
            dirs[:] = [d for d in dirs if "tinycc-src" not in d]
            for name in files:
                if name.lower() == _exe("tcc").lower():
                    cand = os.path.join(root, name)
                    if os.access(cand, os.X_OK) or sys.platform == "win32":
                        return os.path.abspath(cand)
        return None

    if (found := _existing()):
        if verbose:
            print(f"  [TCC] reusing {found}")
        return found

    if sys.platform == "win32":
        found = _download_windows_tcc(dest_dir)
        if found and verbose:
            print(f"  [TCC] ready at {found}")
        return found

    src = os.path.join(dest_dir, "tinycc-src")
    if not os.path.isdir(src):
        if not shutil.which("git"):
            print("  [TCC] git not found; skipping", file=sys.stderr)
            return None
        try:
            res = subprocess.run(["git", "clone", "--depth", "1",
                                  "https://github.com/TinyCC/tinycc.git", src],
                                 capture_output=True, text=True)
        except OSError as e:
            print(f"  [TCC] git clone failed: {e}", file=sys.stderr)
            return None
        if res.returncode != 0:
            print(f"  [TCC] git clone failed: {res.stderr[-300:]}", file=sys.stderr)
            return None
    prefix = os.path.join(dest_dir, "tcc-dist")
    configure = os.path.join(src, "configure")
    if not os.path.isfile(configure):
        print(f"  [TCC] {configure} not found", file=sys.stderr)
        return None
    jobs = str(max(1, (os.cpu_count() or 2)))
    for cmd in (["./configure", f"--prefix={prefix}", "--extra-cflags=-O2"],
                ["make", f"-j{jobs}"],
                ["make", "install"]):
        try:
            res = subprocess.run(cmd, cwd=src, capture_output=True, text=True)
        except OSError as e:
            # 'make' missing, './configure' not executable, ...
            print(f"  [TCC] cannot run {' '.join(cmd)}: {e}", file=sys.stderr)
            return None
        if res.returncode != 0:
            print(f"  [TCC] {' '.join(cmd)} failed: {(res.stderr or '')[-300:]}",
                  file=sys.stderr)
            return None
    # The source tree is ~30 MB and only needed to produce the installed binary;
    # drop it unless the caller wants to iterate on TCC itself.
    if not os.environ.get("PENGU_KEEP_TCC_SRC"):
        shutil.rmtree(src, ignore_errors=True)
    for name in (os.path.join("bin", _exe("tcc")), _exe("tcc")):
        cand = os.path.join(prefix, name)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return None


def main(argv: Optional[List[str]] = None) -> int:
    """CLI used by the release workflow: ``python pengu_tcc.py --stage DIR``.

    Exit codes are the gate:

    * 0 — TCC staged (or, with ``--allow-missing``, simply unavailable),
    * 1 — the downloaded archive failed verification, or TCC was required and
      could not be produced.

    A digest mismatch is **never** downgraded to ``--allow-missing``: that is the
    difference between "no TCC" and "a TCC that is not the one we pinned".
    """
    import argparse

    parser = argparse.ArgumentParser(description="Stage TinyCC for a release build.")
    parser.add_argument("--stage", metavar="DIR", default="build/tcc-dist",
                        help="destination directory (default: build/tcc-dist)")
    parser.add_argument("--allow-missing", action="store_true",
                        help="exit 0 when TCC is unavailable (digest failures still exit 1)")
    args = parser.parse_args(argv)

    try:
        path = ensure_tcc(args.stage, verbose=True)
    except (TccIntegrityError, UnsafeArchiveError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    if not path:
        message = "TinyCC unavailable; the release will fall back to gcc/clang"
        if args.allow_missing:
            print(f"::warning::{message}")
            return 0
        print(f"::error::{message}", file=sys.stderr)
        return 1
    print(f"tcc: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
