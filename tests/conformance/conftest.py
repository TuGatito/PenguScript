"""Plumbing for the conformance corpus (``tests/conformance/compliance``).

Each ``*.pengu`` file is a complete program: it must pass ``pengu check``,
compile with ``pengu build`` and run with ``pengu run``.  The fixtures mirror
``tests/compiler/conftest.py`` but stay local so the corpus has no dependency on
the compiler test package.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CLI_NOISE = re.compile(r"^\s+(Scripting|Compiling|Building|Linking|Finished|Running|Cached)\b")


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file()


@pytest.fixture(scope="session")
def has_cc() -> bool:
    return _have_cc()


@pytest.fixture
def pengu_cli(tmp_path):
    """Runs ``pengu_project.py <args>`` in ``tmp_path``."""
    if not _have_cc():
        pytest.skip("no C compiler available")
    if not _have_runtime():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    def _run(*args: str, timeout: int = 240) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "pengu_project.py"), *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
        )

    return _run


@pytest.fixture
def compile_and_run(tmp_path):
    """Runs a complete program and returns its stdout without CLI chatter."""
    if not _have_cc():
        pytest.skip("no C compiler available")
    if not _have_runtime():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    def _run(source_path: Path, timeout: int = 240) -> str:
        res = subprocess.run(
            [sys.executable, str(ROOT / "pengu_project.py"), "run",
             "--ephemeral", str(source_path)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        assert res.returncode == 0, (
            f"run failed ({res.returncode}):\n--- stdout ---\n{res.stdout}\n"
            f"--- stderr ---\n{res.stderr}"
        )
        return "\n".join(line for line in res.stdout.splitlines() if not _CLI_NOISE.match(line))

    return _run
