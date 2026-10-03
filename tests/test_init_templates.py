"""Roadmap Phase 4 / §4.10 — `pengu init --template` (+ generated-code regression).

While adding templates this also fixes a pre-existing bug: the `static` and
`shared` entry points started with `//`, which is not a comment in PenguScript,
so `pengu init --type static` produced code that did not parse.
"""

import os

import pytest

from pengu_project import OutputType, ProjectConfig, build_project, init_project
from tests.conftest import REPO


def _init(tmp_path, name, **kw):
    return init_project(name, target_dir=str(tmp_path), **kw)


def _bundles(tmp_path, name):
    """Bundles the generated project to C (no C compiler needed)."""
    proj = os.path.join(str(tmp_path), name)
    out = os.path.join(proj, "bundle_check.c")
    build_project(config_path=proj, output=out)
    return open(out, encoding="utf-8").read()


def test_default_template_is_exe(tmp_path):
    proj = _init(tmp_path, "plain")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "weave main into void:" in main
    assert ProjectConfig.load(proj).output == OutputType.EXE


def test_cli_template(tmp_path):
    proj = _init(tmp_path, "cliapp", template="cli")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "import std.spark" in main
    assert "usage" in main
    assert "weave main into void:" in main
    assert "pengu_main" in _bundles(tmp_path, "cliapp")


def test_game_template(tmp_path):
    proj = _init(tmp_path, "gameapp", template="game")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "while" in main
    assert "frame" in main
    assert "pengu_main" in _bundles(tmp_path, "gameapp")


def test_lib_template_switches_output_to_static(tmp_path):
    proj = _init(tmp_path, "libapp", template="lib")
    cfg = ProjectConfig.load(proj)
    assert cfg.output == OutputType.STATIC
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "weave add" in main and "weave sub" in main
    assert "//" not in main
    _bundles(tmp_path, "libapp")


def test_lib_template_respects_explicit_output_type(tmp_path):
    proj = _init(tmp_path, "libexe", template="lib", output_type="exe")
    assert ProjectConfig.load(proj).output == OutputType.EXE


@pytest.mark.parametrize("out_type", ["static", "shared", "obj", "c"])
def test_generated_entry_points_parse_for_every_output_type(tmp_path, out_type):
    """Regression: the generated main must be valid PenguScript for all types."""
    name = f"gen_{out_type}"
    proj = _init(tmp_path, name, output_type=out_type)
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "//" not in main, f"{out_type} template uses a C-style comment"
    # Bundling parses + checks the entry point.
    build_project(config_path=proj, output=os.path.join(proj, "bundle_check.c"))


def test_templates_are_buildable_end_to_end(tmp_path):
    for i, template in enumerate(("exe", "cli", "game", "lib")):
        name = f"tpl{i}_{template}"
        _init(tmp_path, name, template=template)
        _bundles(tmp_path, name)
