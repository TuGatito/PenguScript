from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"

pytestmark = pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")


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


def test_f7_fmt_idempotent_and_config(tmp_path: Path) -> None:
    (tmp_path / ".pengufmt.toml").write_text("indent = 2\ninsert_spaces = true\n", encoding="utf-8")
    (tmp_path / "a").mkdir()
    src = tmp_path / "a" / "x.pengu"
    original = 'weave main into int:\n    var s as string is "a   ,   b"\n    return 0\n'
    src.write_text(original, encoding="utf-8")
    r = run(["fmt", "a/x.pengu"], tmp_path, tmp_path)
    assert r.returncode == 0, r.stderr
    once = src.read_text(encoding="utf-8")
    assert "\n  var s" in once
    assert '"a   ,   b"' in once
    r2 = run(["fmt", "a/x.pengu"], tmp_path, tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert src.read_text(encoding="utf-8") == once
    assert run(["fmt", "--check", "a/x.pengu"], tmp_path, tmp_path).returncode == 0


def test_f7_fmt_matches_stage0_on_fixtures(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT))
    from pengu_lsp.formatting import format_pengu_source

    samples = [
        "weave main into int:\n\tvar a as int is 0\n    return a\n",
        'weave f into int:\n    var s as string is "a   ,   b"\n    return 0',
        'weave f into int:\n    var s as string is """x\n  y\n"""\n    return 0\n',
    ]
    for text in samples:
        stage0 = format_pengu_source(text, tab_size=4, insert_spaces=True, blank_lines_max=2)
        r = subprocess.run(
            [str(PSC), "fmt", "--stdin"], input=text, text=True, capture_output=True
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout == stage0


def test_f7_doc_uses_signatures(tmp_path: Path) -> None:
    assert run(["init", "demo"], tmp_path, tmp_path).returncode == 0
    proj = tmp_path / "demo"
    (proj / "src" / "main.pengu").write_text(
        "## Adds two ints.\nweave add with a as int, b as int into int:\n"
        "    return a + b\n\nweave main into int:\n    return 0\n",
        encoding="utf-8",
    )
    r = run(["doc", "--html"], proj, tmp_path)
    assert r.returncode == 0, r.stderr
    page = (proj / "docs" / "api" / "src_main.md").read_text(encoding="utf-8")
    assert "**add**(a: int, b: int) -> int" in page
    assert "Adds two ints." in page
    assert (proj / "docs" / "api" / "index.html").is_file()
    assert "test" not in page


def test_f7_assets_incremental_and_disk(tmp_path: Path) -> None:
    assert run(["init", "demo"], tmp_path, tmp_path).returncode == 0
    proj = tmp_path / "demo"
    (proj / "assets").mkdir(exist_ok=True)
    (proj / "assets" / "a.txt").write_text("hola", encoding="utf-8")
    first = run(["assets"], proj, tmp_path)
    assert first.returncode == 0, first.stderr
    assert "Generated 1 asset" in first.stdout
    second = run(["assets"], proj, tmp_path)
    assert second.returncode == 0, second.stderr
    assert "up to date" in second.stdout
    forced = run(["assets", "--force"], proj, tmp_path)
    assert forced.returncode == 0
    assert "Generated 1 asset" in forced.stdout


def test_f7_watch_once_and_benchmark(tmp_path: Path) -> None:
    assert run(["init", "demo"], tmp_path, tmp_path).returncode == 0
    proj = tmp_path / "demo"
    w = run(["watch", "src/main.pengu", "--once"], proj, tmp_path)
    assert w.returncode == 0, w.stderr
    b = run(["benchmark", "--only=f7_arith", "--repeat=1", "--warmup=0", "--json"], ROOT, tmp_path)
    assert b.returncode == 0, b.stderr
    data = json.loads(b.stdout)
    assert data["schema_version"] == 1
    assert data["cases"][0]["name"] == "f7_arith"
    assert data["cases"][0]["status"] == "ok"
