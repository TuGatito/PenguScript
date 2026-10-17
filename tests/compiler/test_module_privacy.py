"""Private rune fields are private to their *module*, not to the whole program.

Before 2.7.0 the rule was a heuristic: `_field` was reachable if the checking
file lived under a `std/` directory or if it declared an `insignia`.  That made a
private field of a user rune unreachable even from the very module that declares
it, while any std file could reach any other std file's privates.

Now every nominal type records the module that declares it (its file path), and a
private field is reachable from that module only.  These tests build a real
two-module project and check both directions.
"""
from __future__ import annotations

import textwrap

import pytest

_SECRET = """
omen BoxKind:
    A
    B

rune Box:
    _hidden as int
    _kind as BoxKind
    shown as int

weave peek with b as Box into int:
    return b._hidden

weave make_box with v as int into Box:
    return with _hidden is v, _kind is BoxKind.A, shown is v

enchanting Box:
    weave hidden_plus with n as int into int:
        return self-> _hidden + n
"""


def _project(tmp_path, main_source: str):
    """Writes ``secret.pengu`` + ``main.pengu`` and returns the src directory."""
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "secret.pengu").write_text(textwrap.dedent(_SECRET), encoding="utf-8")
    (src / "main.pengu").write_text(textwrap.dedent(main_source), encoding="utf-8")
    (tmp_path / "pengu.yaml").write_text("name: privacy\nversion: 0.1.0\n", encoding="utf-8")
    return src


def _check(pengu_cli, tmp_path, main_source: str):
    src = _project(tmp_path, main_source)
    return pengu_cli("check", str(src / "main.pengu"), cwd=tmp_path)


def test_private_field_is_reachable_inside_its_module(pengu_cli, tmp_path):
    """The module that declares the rune may read its own `_field`."""
    result = _check(pengu_cli, tmp_path, """
        import secret

        weave main into int:
            return calling secret.peek with calling secret.make_box with 1
    """)
    assert result.returncode == 0, result.stdout + result.stderr


def test_private_field_is_rejected_from_another_module(pengu_cli, tmp_path):
    result = _check(pengu_cli, tmp_path, """
        import secret

        weave main into int:
            var b as Box is calling secret.make_box with 1
            return b._hidden
    """)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "E0043" in (result.stdout + result.stderr), result.stdout + result.stderr


def test_public_field_is_reachable_from_another_module(pengu_cli, tmp_path):
    result = _check(pengu_cli, tmp_path, """
        import secret

        weave main into int:
            var b as Box is calling secret.make_box with 1
            return b.shown
    """)
    assert result.returncode == 0, result.stdout + result.stderr


def test_enchanting_block_may_touch_private_fields(pengu_cli, tmp_path):
    """An `enchanting` block for the rune is inside the rune, wherever it is."""
    result = _check(pengu_cli, tmp_path, """
        import secret

        enchanting Box:
            weave own with n as int into int:
                return self->_hidden + n

        weave main into int:
            return 0
    """)
    assert result.returncode == 0, result.stdout + result.stderr


def test_judge_over_a_private_field_from_another_module_is_rejected(pengu_cli, tmp_path):
    result = _check(pengu_cli, tmp_path, """
        import secret

        omen Kind:
            A

        weave main into int:
            var b as Box is calling secret.make_box with 1
            judge b over _kind:
                when A -> 1
                else -> 0
    """)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "E0043" in (result.stdout + result.stderr), result.stdout + result.stderr


def test_private_field_is_reachable_from_the_declaring_module_after_import(pengu_cli, tmp_path):
    """`secret.pengu` itself must pass: it is the owner, not an outsider."""
    src = _project(tmp_path, """
        import secret

        weave main into int:
            return 0
    """)
    result = pengu_cli("check", str(src / "secret.pengu"), cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
