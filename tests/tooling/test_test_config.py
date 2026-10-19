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
