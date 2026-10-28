from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"


def env(tmp_path: Path) -> dict[str, str]:
    e = os.environ.copy()
    e["PENGU_STD_DIR"] = str(ROOT / "std")
    e["PENGU_LIB_DIR"] = str(ROOT / "build" / "lib")
    e["PENGU_INCLUDE_DIR"] = str(ROOT / "build" / "include")
    e["PSC_CACHE_DIR"] = str(tmp_path / "cache")
    return e


def run(args: list[str], cwd: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PSC), *args], cwd=cwd, env=env(tmp_path), text=True, capture_output=True
    )


pytestmark = pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")


def test_f6_init_build_run_test_clean(tmp_path: Path) -> None:
    r = run(["init", "demo"], tmp_path, tmp_path)
    assert r.returncode == 0, r.stderr
    proj = tmp_path / "demo"
    (proj / "src" / "main.pengu").write_text(
        'import std.spark\n\n'
        'weave add with a as int, b as int into int:\n    return a + b\n\n'
        'test "add":\n    calling spark.assert with ((calling add with 2, 3) == 5)\n\n'
        'weave main into int:\n    calling spark.println with "f6"\n    return 7\n',
        encoding="utf-8",
    )
    b = run(["build", "."], proj, tmp_path)
    assert b.returncode == 0, b.stderr
    assert subprocess.run([str(proj / "build" / "demo")]).returncode == 7
    assert list((tmp_path / "cache").glob("*/app")), "project build must populate the cache"
    b2 = run(["build", "."], proj, tmp_path)
    assert b2.returncode == 0, b2.stderr

    t = run(["test", "."], proj, tmp_path)
    assert t.returncode == 0, t.stderr
    assert "All 1 test(s) passed." in t.stdout
    tj = run(["test", ".", "--json"], proj, tmp_path)
    assert tj.returncode == 0, tj.stderr
    assert '"event":"summary"' in tj.stdout

    r2 = run(["run", "."], proj, tmp_path)
    assert r2.returncode == 7
    assert "f6" in r2.stdout

    c = run(["clean", "."], proj, tmp_path)
    assert c.returncode == 0
    assert not (proj / "build").exists()


def test_f6_metadata_fmt_doc_assets(tmp_path: Path) -> None:
    assert run(["init", "demo"], tmp_path, tmp_path).returncode == 0
    proj = tmp_path / "demo"
    (proj / "assets").mkdir(exist_ok=True)
    (proj / "assets" / "hello.txt").write_text("hola", encoding="utf-8")

    m = run(["metadata"], proj, tmp_path)
    assert m.returncode == 0, m.stderr
    data = json.loads(m.stdout)
    assert data["name"] == "demo"
    assert data["schema_version"] == 1

    f = run(["fmt", "src/main.pengu"], proj, tmp_path)
    assert f.returncode == 0, f.stderr
    assert run(["fmt", "--check", "src/main.pengu"], proj, tmp_path).returncode == 0

    d = run(["doc"], proj, tmp_path)
    assert d.returncode == 0, d.stderr
    assert (proj / "docs" / "api" / "main.md").is_file()

    a = run(["assets"], proj, tmp_path)
    assert a.returncode == 0, a.stderr
    assert (proj / "src" / "arca.pengu").is_file()
    assert (proj / "build" / "arca_assets.c").is_file()
    ls = run(["assets", "--list"], proj, tmp_path)
    assert ls.returncode == 0
    assert "hello.txt" in ls.stdout


def test_f6_stubs_and_cache(tmp_path: Path) -> None:
    r = run(["add", "x"], tmp_path, tmp_path)
    assert r.returncode == 1
    assert "pengu.toml" in r.stderr

    script = tmp_path / "cache_script.pengu"
    script.write_text('import std.spark\n\nweave main into int:\n    return 0\n', encoding="utf-8")
    first = run(["run", str(script)], tmp_path, tmp_path)
    assert first.returncode == 0, first.stderr
    assert list((tmp_path / "cache").glob("*/app"))
    second = run(["run", str(script)], tmp_path, tmp_path)
    assert second.returncode == 0
    gc = run(["gc", "--all"], tmp_path, tmp_path)
    assert gc.returncode == 0
    assert not any((tmp_path / "cache").glob("*/app"))


def test_f6_check_project_is_pure(tmp_path: Path) -> None:
    assert run(["init", "demo"], tmp_path, tmp_path).returncode == 0
    proj = tmp_path / "demo"
    r = run(["check", "."], proj, tmp_path)
    assert r.returncode == 0, r.stderr
    assert not (proj / "build" / "bundle.c").exists()
