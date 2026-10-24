"""Repository-root pytest bootstrap.

``pytest`` is commonly installed as a console script.  Depending on the
installer, that script does **not** put the current directory on ``sys.path``
(the ``python -m pytest`` form does).  Without this file the suite worked only
under ``python -m pytest``; a bare ``pytest tests/`` failed to import
``pengu_project`` from ``tests/build/``.  AGENT_TESTING.md documents the bare
``pytest tests/`` command as the fast path, so make it work deterministically.

This must stay a *plain* path insertion: importing any project module here
would run before pytest has configured rootdir and can mask import errors.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
