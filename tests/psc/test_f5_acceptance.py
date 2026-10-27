from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"


def env() -> dict[str, str]:
    e = os.environ.copy()
    e["PENGU_STD_DIR"] = str(ROOT / "std")
    e["PENGU_LIB_DIR"] = str(ROOT / "build" / "lib")
    e["PENGU_INCLUDE_DIR"] = str(ROOT / "build" / "include")
    return e


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PSC), *args], cwd=cwd, env=env(), text=True, capture_output=True
    )


@pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")
def test_f5_build_run_expand(tmp_path: Path) -> None:
    (tmp_path / "pengu.toml").write_text(
        '[project]\nname = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\n',
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "import std.spark\n\n"
        "weave main into int:\n"
        '    calling spark.println with "hola"\n'
        "    return 7\n",
        encoding="utf-8",
    )

    b = run(["build", "."], tmp_path)
    assert b.returncode == 0, b.stderr
    exe = tmp_path / "build" / "app"
    assert exe.is_file()
    assert subprocess.run([str(exe)], text=True, capture_output=True).returncode == 7

    r = run(["run", "."], tmp_path)
    assert r.returncode == 7, r.stderr
    assert "hola" in r.stdout

    e = run(["expand", ".", "--out=bundle.c"], tmp_path)
    assert e.returncode == 0, e.stderr
    assert (tmp_path / "bundle.c").is_file()


@pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")
def test_f5_build_rejects_bad_source(tmp_path: Path) -> None:
    f = tmp_path / "bad.pengu"
    f.write_text("weave main into int:\n    return missing\n", encoding="utf-8")
    r = run(["build", str(f)], tmp_path)
    assert r.returncode == 1
    assert "undefined identifier" in r.stderr
