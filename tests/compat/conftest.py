"""Fixtures for Python-compatibility tests (``tests/compat/``).

The test compiles one PenguScript program with ``pengu run`` and reads the
files it is given. The fixture mirrors ``tests/stdlib/conftest.py`` so the
compat suite needs no C compiler of its own.
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
_CLI_NOISE = re.compile(
    r"^\s+(Scripting|Compiling|Building|Linking|Finished|Running|Cached|Testing)\b"
)


@pytest.fixture(scope="session")
def has_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


@pytest.fixture
def compile_and_run(tmp_path, has_cc):
    if not has_cc:
        pytest.skip("no C compiler available")
    if not (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    def _run(source: str, timeout: int = 300) -> str:
        script = tmp_path / "compat.pengu"
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
