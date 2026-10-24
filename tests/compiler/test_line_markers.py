"""B11: #line directives stay on by default and --no-line-markers removes them."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


_SOURCE = """
import std.spark

weave helper with x as int into int:
    return x + 1

weave main into int:
    calling spark.println_int with (calling helper with 1)
    return 0
"""


def _expand(pengu_cli, tmp_path: Path, extra: tuple[str, ...] = (),
            env: dict | None = None) -> str:
    script = tmp_path / "app.pengu"
    script.write_text(_SOURCE, encoding="utf-8")
    out = tmp_path / "bundle.c"
    res = pengu_cli("expand", str(script), "-o", str(out), *extra, env=env)
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    return out.read_text(encoding="utf-8")


def test_line_markers_are_on_by_default(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path)
    assert "\n#line " in c


def test_no_line_markers_flag_removes_them(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, extra=("--no-line-markers",))
    assert "\n#line " not in c


def test_no_line_markers_env_removes_them(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, env={"PENGU_NO_LINE_MARKERS": "1"})
    assert "\n#line " not in c


def test_no_line_markers_keeps_the_program_compilable(pengu_cli, tmp_path):
    script = tmp_path / "app.pengu"
    script.write_text(_SOURCE, encoding="utf-8")
    res = pengu_cli("run", "--no-line-markers", "--ephemeral", str(script))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")


def test_no_line_markers_shrinks_the_bundle(pengu_cli, tmp_path):
    on = _expand(pengu_cli, tmp_path)
    off = _expand(pengu_cli, tmp_path, extra=("--no-line-markers",))
    assert len(off) < len(on)
