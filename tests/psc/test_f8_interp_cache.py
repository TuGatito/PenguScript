from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"


def test_string_length_interpolation_and_run_cache_identity(tmp_path: Path) -> None:
    src = tmp_path / "main.pengu"
    src.write_text(
        'import std.spark\n\nweave main into int:\n'
        '    var body as string is "abc"\n'
        '    calling spark.println with "len={body length}"\n'
        '    return 0\n',
        encoding="utf-8",
    )
    e = os.environ.copy()
    e.update(PENGU_STD_DIR=str(ROOT / "std"), PENGU_LIB_DIR=str(ROOT / "build" / "lib"),
             PENGU_INCLUDE_DIR=str(ROOT / "build" / "include"), PSC_CACHE_DIR=str(tmp_path / "cache"))
    for _ in range(2):
        r = subprocess.run([str(PSC), "run", str(src)], cwd=tmp_path, env=e, text=True, capture_output=True)
        assert r.returncode == 0, r.stderr
        assert "len=3" in r.stdout
