"""Roadmap Phase 4 / §4.10 — `pengu init --template` (+ generated-code regression).

While adding templates this also fixes a pre-existing bug: the `static` and
`shared` entry points started with `//`, which is not a comment in PenguScript,
so `pengu init --type static` produced code that did not parse.
"""

import os
import subprocess

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
    assert "import std.invoke" in main
    # Help/usage is produced by std.invoke, not by a hand-written weave.
    assert "add_flag" in main and "add_option" in main
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

# --------------------------------------------------------------------------- #
# Roadmap 6.2 — the templates must do what their name promises
# --------------------------------------------------------------------------- #


def _toml_path(path) -> str:
    """Spells a filesystem path for a TOML basic string.

    On Windows ``str(BUILD_LIB)`` is ``D:\\a\\...\\build\\lib`` and interpolating
    it raw into the manifest produced
    ``TOMLDecodeError: Unescaped '\\' in a string``. A forward slash is accepted
    by MinGW gcc, clang and cl.exe alike, so no escaping is needed.
    """
    return str(path).replace("\\", "/")


def _manifest(proj: str) -> dict:
    import tomllib

    with open(os.path.join(proj, "pengu.toml"), "rb") as f:
        return tomllib.load(f)


def test_game_template_links_raylib(tmp_path):
    """BUG-6.5: without this every raylib import fails at link time."""
    proj = _init(tmp_path, "game_links", template="game")
    data = _manifest(proj)
    assert "raylib" in data["build"]["links"]


def test_game_template_opens_a_window(tmp_path):
    """BUG-6.4: the roadmap criterion is a real window, not a print loop."""
    proj = _init(tmp_path, "game_win", template="game")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "import std.raylib" in main
    for call in ("InitWindow", "BeginDrawing", "EndDrawing", "CloseWindow",
                 "WindowShouldClose"):
        assert call in main, call
    assert "spark.println" not in main


def test_game_template_bundles(tmp_path):
    """The generated game code must at least parse, check and emit C."""
    _init(tmp_path, "game_bundle", template="game")
    _bundles(tmp_path, "game_bundle")


def test_cli_template_uses_std_invoke(tmp_path):
    """BUG-6.6: a CLI template must actually parse arguments."""
    proj = _init(tmp_path, "cli_invoke", template="cli")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert "import std.invoke" in main
    assert "import std.rites" in main
    assert "add_flag" in main and "add_option" in main
    assert "get_args" in main
    assert "calling res.get_or" in main or "get_bool_or" in main
    _bundles(tmp_path, "cli_invoke")


def test_cli_template_parses_and_help_work(tmp_path):
    """E2E: build the CLI and check that flags and --help are handled."""
    from tests.conftest import BUILD_INCLUDE, BUILD_LIB, HAVE_CC, HAVE_RUNTIME

    if not (HAVE_CC and HAVE_RUNTIME):
        pytest.skip("no C compiler or runtime archive")
    proj = _init(tmp_path, "cli_e2e", template="cli")
    manifest = os.path.join(proj, "pengu.toml")
    text = open(manifest, encoding="utf-8").read()
    text = text.replace('lib_dirs = []', f'lib_dirs = ["{_toml_path(BUILD_LIB)}"]')
    text = text.replace('include_dirs = []',
                        f'include_dirs = ["{_toml_path(BUILD_INCLUDE)}", "{_toml_path(BUILD_LIB.parent)}"]')
    text = text.replace('links = []', 'links = ["pengu_runtime"]')
    with open(manifest, "w", encoding="utf-8") as f:
        f.write(text)

    build_project(config_path=proj)
    exe = os.path.join(proj, "build", "cli_e2e")
    if os.name == "nt":
        exe += ".exe"
    assert os.path.isfile(exe), exe

    res = subprocess.run([exe, "--verbose", "--output=out.txt", "in.csv"],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert "verbose: on" in res.stdout
    assert "output -> out.txt" in res.stdout
    assert "input  -> in.csv" in res.stdout

    helptext = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=60)
    assert "Usage:" in (helptext.stdout + helptext.stderr)
    assert "--verbose" in (helptext.stdout + helptext.stderr)


def test_lib_template_includes_a_test_block(tmp_path):
    """BUG-6.7: a library template must ship a smoke test."""
    proj = _init(tmp_path, "lib_test", template="lib")
    main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
    assert 'test "' in main
    assert "std.ward" in main


def test_lib_template_tests_pass(tmp_path):
    from tests.conftest import BUILD_INCLUDE, BUILD_LIB, HAVE_CC, HAVE_RUNTIME

    if not (HAVE_CC and HAVE_RUNTIME):
        pytest.skip("no C compiler or runtime archive")
    proj = _init(tmp_path, "lib_run", template="lib")
    manifest = os.path.join(proj, "pengu.toml")
    text = open(manifest, encoding="utf-8").read()
    text = text.replace('lib_dirs = []', f'lib_dirs = ["{_toml_path(BUILD_LIB)}"]')
    text = text.replace('include_dirs = []',
                        f'include_dirs = ["{_toml_path(BUILD_INCLUDE)}", "{_toml_path(BUILD_LIB.parent)}"]')
    text = text.replace('links = []', 'links = ["pengu_runtime"]')
    with open(manifest, "w", encoding="utf-8") as f:
        f.write(text)

    from pengu_project import test_project

    assert test_project(config_path=proj) == 0
