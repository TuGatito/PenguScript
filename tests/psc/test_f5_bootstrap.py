from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"


@pytest.mark.skipif(os.environ.get("PSC_BOOTSTRAP") != "1", reason="set PSC_BOOTSTRAP=1")
@pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")
def test_f5_bootstrap_fixed_point() -> None:
    p = subprocess.run(
        [sys.executable, str(ROOT / "psc" / "tools" / "bootstrap.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert "punto fijo: OK" in p.stdout
    assert "bootstrap: OK" in p.stdout
