"""Track B4/3.0: module-scoped data types; E0070 for unsupported duplicates."""
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


def test_two_modules_can_declare_data_types_with_the_same_name(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "rune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave use with x as a.Config, y as b.Config into int:\n"
                 "    return 0\n\n"
                 "weave main into int:\n"
                 "    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc == 0, out
    res = pengu_cli("expand", str(main), "-o", str(tmp_path / "bundle.c"))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "bundle.c").read_text(encoding="utf-8")
    assert "struct a_Config" in c and "struct b_Config" in c


def test_rune_and_omen_can_share_a_logical_name(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Thing:\n    a as int\n")
    _write(tmp_path / "b.pengu", "omen Thing:\n    A\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave use with x as a.Thing, y as b.Thing into int:\n"
                 "    return 0\n\n"
                 "weave main into int:\n"
                 "    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc == 0, out


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


def test_insignia_duplicate_types_get_module_scoped_c_names(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "insignia a_\n\nrune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "insignia b_\n\nrune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave use with x as a.Config, y as b.Config into int:\n"
                 "    return 0\n\n"
                 "weave main into int:\n"
                 "    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc == 0, out


def test_duplicate_types_with_methods_are_e0070(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu",
           "rune Config:\n    a as int\n\n"
           "enchanting Config:\n    weave get_a into int:\n        return self->a\n")
    _write(tmp_path / "b.pengu",
           "rune Config:\n    b as int\n\n"
           "enchanting Config:\n    weave get_b into int:\n        return self->b\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave main into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc != 0
    assert "E0070" in out
    assert "has methods" in out


def test_duplicate_generic_types_are_e0070(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Box shard T:\n    value as T\n")
    _write(tmp_path / "b.pengu", "rune Box shard T:\n    item as T\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave main into int:\n    return 0\n")
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


def test_duplicate_data_types_compile_and_run(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Config:\n    a as int\n\n"
                                 "weave make_a into Config:\n    return with a is 1\n")
    _write(tmp_path / "b.pengu", "rune Config:\n    b as int\n\n"
                                 "weave make_b into Config:\n    return with b is 2\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave main into int:\n"
                 "    var x as a.Config is calling a.make_a\n"
                 "    var y as b.Config is calling b.make_b\n"
                 "    return x.a + y.b\n")
    res = pengu_cli("run", "--keep", "--no-cache", str(main))
    assert res.returncode == 3, (res.stdout or "") + (res.stderr or "")
    c = (tmp_path / "build" / "main_run" / "bundle.c").read_text(encoding="utf-8")
    assert "struct a_Config" in c and "struct b_Config" in c


def test_unqualified_duplicate_type_is_an_error(pengu_cli, tmp_path):
    _write(tmp_path / "a.pengu", "rune Config:\n    a as int\n")
    _write(tmp_path / "b.pengu", "rune Config:\n    b as int\n")
    main = tmp_path / "main.pengu"
    _write(main, "import a\nimport b\n\n"
                 "weave use with c as Config into int:\n    return 0\n")
    rc, out = _check(pengu_cli, main)
    assert rc != 0
    assert "Config" in out
