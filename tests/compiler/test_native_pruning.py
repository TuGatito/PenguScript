"""Optional native include/link pruning (--prune-native)."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _expand(pengu_cli, tmp_path: Path, source: str, extra: tuple[str, ...] = (),
            env: dict | None = None) -> str:
    script = tmp_path / "main.pengu"
    script.write_text(source, encoding="utf-8")
    out = tmp_path / "bundle.c"
    res = pengu_cli("expand", str(script), "-o", str(out), *extra, env=env)
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    return out.read_text(encoding="utf-8")


def test_native_pruning_drops_an_unused_binding_include(pengu_cli, tmp_path):
    source = """
import std.petitio

weave main into int:
    return 0
"""
    default = _expand(pengu_cli, tmp_path, source)
    assert '#include "petitio.h"' in default
    pruned = _expand(pengu_cli, tmp_path, source, extra=("--prune-native",))
    assert '#include "petitio.h"' not in pruned
    assert "--prune-native" not in pruned


def test_native_pruning_keeps_include_referenced_by_c_glue(pengu_cli, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "import std.petitio\n\nweave main into int:\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "glue.c").write_text(
        "/* the scanner keeps petitio_url_encode even from a comment */\n"
        "int keep_petitio(void) { return 0; }\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.toml").write_text(
        'name = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    res = pengu_cli("build", "--output", "build/bundle.c", "--prune-native")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert '#include "petitio.h"' in c


def test_native_pruning_keeps_library_and_test_includes(pengu_cli, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "import std.petitio\n\nweave main into int:\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.toml").write_text(
        'name = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "static"\n',
        encoding="utf-8",
    )
    res = pengu_cli("build", "--cc", "gcc", "--prune-native")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert '#include "petitio.h"' in c

    (tmp_path / "build").exists() and __import__("shutil").rmtree(tmp_path / "build")
    (tmp_path / "pengu.toml").write_text(
        'name = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    res = pengu_cli("build", "--test", "--output", "build/bundle.c", "--prune-native")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert '#include "petitio.h"' in c


def test_native_pruning_no_dce_keeps_includes(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, """
import std.petitio

weave main into int:
    return 0
""", extra=("--prune-native",), env={"PENGU_NO_DCE": "1"})
    assert '#include "petitio.h"' in c


@pytest.mark.slow
def test_native_link_pruning_with_c_glue(pengu_cli, tmp_path):
    if not (ROOT / "build" / "lib" / "libpetitio.a").is_file():
        pytest.skip("libpetitio.a not built")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "import std.petitio\n\nweave main into int:\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.toml").write_text(
        'name = "app"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "exe"\n',
        encoding="utf-8",
    )
    res = pengu_cli("build", "--cc", "gcc", "--prune-native", "--verbose")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    log = (res.stdout or "") + (res.stderr or "")
    line = [ln for ln in log.splitlines() if "running C compiler" in ln][-1]
    assert "-lpetitio" not in line
    assert "-lcurl" not in line

    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "glue.c").write_text(
        "/* the scanner keeps petitio_url_encode even from a comment */\n"
        "int keep_petitio(void) { return 0; }\n",
        encoding="utf-8",
    )
    res = pengu_cli("build", "--cc", "gcc", "--prune-native", "--verbose")
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    log = (res.stdout or "") + (res.stderr or "")
    line = [ln for ln in log.splitlines() if "running C compiler" in ln][-1]
    assert "-lpetitio" in line
    assert "-lcurl" in line
