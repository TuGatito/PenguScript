"""Shared plumbing for the standard-library test-suite (``tests/stdlib/``).

The stdlib tests prove a *shipped module* works end to end: each case writes a
small PenguScript program that imports the module under test, runs it through the
documented CLI (``pengu run``) and inspects what the program printed. They are
the counterpart of ``tests/compiler/`` (which tests the language) and
``tests/conformance/`` (which tests whole programs).

Design notes:

* **Batched assertions.** Compiling is the expensive part (~2 s per program with
  gcc), so every test file compiles at most three programs and each program
  carries many checks inside it. A helper ``eq_*`` prints ``FAIL …`` instead of
  panicking, the program ends with ``DONE``, and the Python side asserts that no
  ``FAIL`` appeared. One build validates twenty assertions.
* **Ephemeral and isolated.** ``--ephemeral`` keeps the build out of the checkout
  and ``cwd=tmp_path`` keeps a stray ``pengu.toml`` or ``build/`` from changing
  what the program resolves.
* **No toolchain, no failure.** Without a C compiler (or the built runtime) the
  fixture skips, exactly like ``tests/compiler/conftest.py``.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

#: Repository root: ``tests/stdlib/conftest.py`` -> ``tests/stdlib`` -> ``tests``
#: -> the checkout.
ROOT = Path(__file__).resolve().parents[2]

#: Progress lines the CLI prints before the program's own output.
_CLI_NOISE = re.compile(
    r"^\s+(Scripting|Compiling|Building|Linking|Finished|Running|Cached|Testing)\b"
)


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file()


@pytest.fixture(scope="session")
def has_cc() -> bool:
    """True when a C compiler is on PATH (the e2e tests skip without one)."""
    return _have_cc()


@pytest.fixture
def compile_and_run(tmp_path, has_cc):
    """Compiles and runs a PenguScript source; returns the program's stdout.

    Skips (never fails) when no C compiler or runtime is available, so the suite
    is meaningful on a developer box and inert on a bare one.
    """
    if not has_cc:
        pytest.skip("no C compiler available")
    if not _have_runtime():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    def _run(source: str, timeout: int = 120) -> str:
        script = tmp_path / "test.pengu"
        script.write_text(source, encoding="utf-8")
        res = subprocess.run(
            [sys.executable, str(ROOT / "pengu_project.py"), "run",
             "--ephemeral", str(script)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        assert res.returncode == 0, (
            f"run failed ({res.returncode}):\n"
            f"--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
        )
        return "\n".join(
            line for line in res.stdout.splitlines() if not _CLI_NOISE.match(line)
        )

    return _run
