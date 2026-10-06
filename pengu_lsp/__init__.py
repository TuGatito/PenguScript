"""PenguScript Language Server Protocol package.

The package version is not hardcoded here: it re-exports the single source of
truth from :mod:`pengu_version` (which in turn reads the ``VERSION`` file).
"""

from pengu_version import __version__

__all__ = ["__version__"]
