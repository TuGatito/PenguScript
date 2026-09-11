"""Single source of truth for the PenguScript language version.

Every part of the toolchain that reports a version imports it from here, so the
CLI banner, the generated-C header, the grammar docstring and the release
packager can never drift apart:

    from pengu_version import __version__

The value is read from the repository's ``VERSION`` file (the same file
``make_release.py`` uses). When the toolchain is shipped as a frozen binary the
file may not be next to the code, so a fallback constant is kept here; a unit
test asserts that the fallback, the file and the places that spell the version
out stay in sync.
"""

import os
import re
from typing import Optional

#: Version used when the ``VERSION`` file cannot be read (frozen/packaged runs).
FALLBACK_VERSION = "0.10.0"

#: Root of the source checkout (the directory that holds ``VERSION``).
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

_VERSION_RE = re.compile(r"^\s*(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)")


def read_version_file(path: Optional[str] = None) -> Optional[str]:
    """Reads the version string from a ``VERSION`` file.

    Args:
        path: Optional explicit path; defaults to ``<repo root>/VERSION``.

    Returns:
        The version string, or None when the file is missing or malformed.
    """
    version_path = path or os.path.join(ROOT_DIR, "VERSION")
    try:
        with open(version_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = _VERSION_RE.match(text)
    return match.group(1) if match else None


def _resolve_version() -> str:
    """Returns the version reported by the toolchain."""
    return read_version_file() or FALLBACK_VERSION


#: The language/toolchain version, e.g. ``"0.10.0"``.
__version__ = _resolve_version()

#: Version with a leading ``v``, for banners: ``"v0.10.0"``.
__version_tag__ = f"v{__version__}"
