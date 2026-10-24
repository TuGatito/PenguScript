"""Phase 3: opt-in tree-shaking of ordinary project modules."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_UTIL = """
weave helper_used with x as int into int:
    return x + 1

weave helper_dead with x as int into int:
    return x + 99
"""

_MAIN = """
import util

weave entry_dead with x as int into int:
    return x + 7

weave main into int:
    return calling util.helper_used with 1
"""


def _expand(pengu_cli, tmp_path: Path, extra: tuple[str, ...] = (),
            env: dict | None = None) -> str:
    (tmp_path / "util.pengu").write_text(_UTIL, encoding="utf-8")
    (tmp_path / "main.pengu").write_text(_MAIN, encoding="utf-8")
    out = tmp_path / "bundle.c"
    res = pengu_cli("expand", str(tmp_path / "main.pengu"), "-o", str(out),
                    *extra, env=env)
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    return out.read_text(encoding="utf-8")


def test_default_scope_keeps_user_weaves(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path)
    assert "util_helper_dead" in c
    assert "entry_dead" in c
    assert "scope=user" not in c


def test_user_scope_prunes_unused_user_weaves(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, extra=("--dce-scope=user",))
    assert "util_helper_used" in c
    assert "util_helper_dead" not in c
    assert "entry_dead" not in c
    assert "(scope=user)" in c


def test_tree_shake_user_alias(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, extra=("--tree-shake-user",))
    assert "util_helper_dead" not in c
    assert "(scope=user)" in c


def test_env_scope_user(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, env={"PENGU_DCE_SCOPE": "user"})
    assert "util_helper_dead" not in c
    assert "(scope=user)" in c


def test_export_survives_user_scope(pengu_cli, tmp_path):
    (tmp_path / "main.pengu").write_text("""
@export("keep_export")
weave exported_dead with x as int into int:
    return x + 100

weave main into int:
    return 0
""", encoding="utf-8")
    out = tmp_path / "bundle.c"
    res = pengu_cli("expand", str(tmp_path / "main.pengu"), "-o", str(out),
                    "--dce-scope=user")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = out.read_text(encoding="utf-8")
    assert "keep_export" in c


def _project(tmp_path: Path, output: str = "c") -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "util.pengu").write_text(_UTIL, encoding="utf-8")
    (tmp_path / "src" / "main.pengu").write_text(_MAIN, encoding="utf-8")
    (tmp_path / "pengu.toml").write_text(
        'name = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\n'
        f'output = "{output}"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_library_output_never_prunes_user_code(pengu_cli, tmp_path):
    _project(tmp_path, output="static")
    res = pengu_cli("build", "--cc", "gcc", "--dce-scope=user")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert "util_helper_dead" in c
    assert "scope=user" not in c


def test_test_mode_never_prunes_user_code(pengu_cli, tmp_path):
    _project(tmp_path)
    (tmp_path / "src" / "main.pengu").write_text(_MAIN + """
test "entry helper":
    if (calling entry_dead with 1) == 8:
        return
""", encoding="utf-8")
    res = pengu_cli("build", "--cc", "gcc", "--test", "--output", "build/bundle.c",
                    "--dce-scope=user")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert "util_helper_dead" in c
    assert "entry_dead" in c
    assert "scope=user" not in c


def test_c_glue_keeps_a_user_weave(pengu_cli, tmp_path):
    _project(tmp_path)
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "glue.c").write_text(
        "int keep_from_glue(void) { return util_helper_dead(1); }\n",
        encoding="utf-8",
    )
    res = pengu_cli("build", "--cc", "gcc", "--output", "build/bundle.c",
                    "--dce-scope=user")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert "util_helper_dead" in c


def test_no_dce_wins_over_user_scope(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, extra=("--dce-scope=user",),
                env={"PENGU_NO_DCE": "1"})
    assert "util_helper_dead" in c
    assert "Dead-code elimination: disabled" in c
