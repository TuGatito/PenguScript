"""Shared plumbing for generated-C checks (``tests/codegen/``)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def has_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


@pytest.fixture
def pengu_cli(tmp_path):
    def _run(*args: str, cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "pengu_project.py"), *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd or tmp_path),
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )

    return _run
