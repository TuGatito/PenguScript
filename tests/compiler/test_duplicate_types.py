"""Track B4: type names are program-global (E0070)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _check(pengu_cli, script: Path) -> tuple[int, str]:
    res = pengu_cli("check", str(script))
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def test_duplicate_type_in_one_module_is_e0070(pengu_cli, tmp_path):
    script = tmp_path / "main.pengu"
    _write(script, "rune Thing:\n    a as int\n\nrune Thing:\n    b as int\n")
    rc, out = _check(pengu_cli, script)
    assert rc != 0
    assert "E0070" in out
    assert "declared more than once" in out


@pytest.mark.parametrize("decl", [
    "rune Thing:\n    a as int\n",
    "echo Thing:\n    a as int\n",
    "omen Thing:\n    A\n",
    "alias Thing as int\n",
    "seal Thing as int\n",
])
def test_same_module_duplicate_for_every_type_kind(pengu_cli, tmp_path, decl):
    script = tmp_path / "main.pengu"
    _write(script, decl + "\n" + decl)
    rc, out = _check(pengu_cli, script)
    assert rc != 0
    assert "E0070" in out


def test_two_modules_cannot_declare_the_same_type(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "rune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\nweave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc != 0
    assert "E0070" in out
    assert "'a.pengu'" in out and "'b.pengu'" in out


def test_rune_and_omen_share_the_type_namespace(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Thing:\n    a as int\n")
    _write(tmp_path / "b.pengu", "omen Thing:\n    A\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\nweave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc != 0
    assert "E0070" in out


def test_diamond_import_of_one_type_is_not_a_duplicate(pengu_cli, tmp_path):
    _write(tmp_path / "common.pengu", "rune Shared:\n    x as int\n")
    _write(tmp_path / "a.pengu", "import common\n")
    _write(tmp_path / "b.pengu", "import common\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\nweave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc == 0, out


def test_unimported_module_does_not_collide(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "rune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\n\nweave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc == 0, out


def test_insignia_does_not_make_types_distinct(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "insignia a_\n\nrune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "insignia b_\n\nrune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\nweave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc != 0
    assert "E0070" in out


@pytest.mark.slow
def test_all_std_modules_can_be_imported_together(pengu_cli, tmp_path):
    """Every std module in one compilation: no E0070 and valid C."""
    std = ROOT / "std"
    imports = []
    for path in sorted(std.glob("*.pengu")):
        if path.name.endswith(".d.pengu"):
            continue
        imports.append(f"import std.{path.stem}")
    script = tmp_path / "all.pengu"
    _write(script, "\n".join(imports) + "\n\nweave main into int:\n    return 0\n")
    res = pengu_cli("check", str(script))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    assert "E0070" not in (res.stdout or "") + (res.stderr or "")

    c = tmp_path / "all.c"
    res = pengu_cli("expand", str(script), "-o", str(c))
    assert res.returncode == 0, res.stderr
    text = c.read_text(encoding="utf-8")
    assert re.search(r"struct\s+\w*CipherJsonValue", text)
    assert "struct CommandParser" in text
    assert "struct SourceSpan" in text
    assert "JsonRpcMessage_RpcRequest" in text


@pytest.mark.slow
def test_regulus_and_petitio_import_together(pengu_cli, tmp_path):
    """The former OutOfMemory/IoError/Request collisions now compile."""
    _write(tmp_path / "main.pengu", """
import std.regulus
import std.petitio

weave main into int:
    var e as RegexError is RegexError.RegexOutOfMemory
    var h as HttpError is HttpError.HttpOutOfMemory
    return 0
""")
    res = pengu_cli("check", str(tmp_path / "main.pengu"))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
