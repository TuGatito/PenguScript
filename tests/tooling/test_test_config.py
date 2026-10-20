"""The suite's time budget is part of the contract.

A serial `pytest tests/` takes ~53 minutes; the parallel default takes ~3. This
guard fails if the configuration that makes it fast is ever removed, because the
regression is otherwise invisible until someone runs the suite on a deadline.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTEST_INI = ROOT / "pytest.ini"


@pytest.mark.smoke
def test_default_run_is_parallel():
    text = PYTEST_INI.read_text(encoding="utf-8")
    addopts = next(
        (line for line in text.splitlines() if line.startswith("addopts")), ""
    )
    assert "-n auto" in addopts, "pytest.ini must default to -n auto (serial run ~53 min)"
    assert "--dist loadgroup" in addopts, "xdist needs --dist loadgroup for shared bundles"


@pytest.mark.smoke
def test_the_time_budget_is_documented():
    guide = (ROOT / "AGENT_TESTING.md").read_text(encoding="utf-8")
    assert "7 minutes" in guide
    assert "10 minutes" in guide
    assert "pytest tests/" in guide


@pytest.mark.smoke
def test_tests_build_is_collected():
    """`tests/build/` must not be hidden by pytest's default `norecursedirs`.

    Pytest's default ignore list contains `build` as a *basename* pattern, so
    `pytest tests` used to skip `tests/build/` entirely. `selftest --smoke`
    still ran `test_build_pengu.py` because it passes the marker-selected file
    paths directly, which is how the gap went unnoticed; the full suite never
    collected it, nor `tests/build/test_smart_linking.py`.
    """
    text = PYTEST_INI.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert any(line == "testpaths = tests" for line in lines), (
        "pytest.ini needs `testpaths = tests` so bare pytest does not scan the "
        "generated top-level build/ while tests/build/ stays collectable"
    )
    norec = next((line for line in lines if line.startswith("norecursedirs")), "")
    assert norec, "pytest.ini must define norecursedirs explicitly"
    patterns = norec.split("=", 1)[1].split()
    assert "build" not in patterns, (
        "removing `build` from norecursedirs is what collects tests/build/"
    )
    assert (ROOT / "tests" / "build" / "test_build_pengu.py").is_file()
    assert (ROOT / "tests" / "build" / "test_smart_linking.py").is_file()
