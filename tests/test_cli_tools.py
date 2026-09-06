#!/usr/bin/env python3
"""Consolidated tests for the PenguScript project / CLI / tooling layer.

Replaces the removed per-area suites (test_cli_tools, test_build_manager,
test_project_manager, test_when_main[CLI parts], test_pengu_doc,
test_bindings_and_project_structure and test_archivum_tree) with one file:

* ``pengu init`` scaffolding (config file, src/ layout, exe/static templates),
* ``pengu build`` / ``pengu run`` compile+execute of small projects,
* ``pengu check`` exit codes (clean vs semantic error) and ``--entry`` override,
* ``pengu fmt`` formatting round-trip via the CLI and the shared formatter,
* ``pengu run <file>.pengu`` script mode (``when main`` and plain ``weave main``),
* ``pengu doc`` markdown generation,
* ``update`` / ``clean`` subcommands (network-free local dependency),
* C-compilation failure reporting (``CompileFailedError``),
* config discovery (pengu.toml / pengu.yaml / pengu.json),
* project structure helpers (module resolution, bindings, add_dependency),
* a pure-Pengu std test for std.archivum copy_tree/list_files_recursive.

Every generated project lives in a temporary directory under ``build/``
(gitignored) and is removed afterwards; nothing is written into the repo root.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tests.conftest import (
    REPO,
    BUILD_DIR,
    compile_run,
    requires_cc,
    requires_runtime,
)

PY = sys.executable
MODULE = "pengu_project"
PROJECT_SCRIPT = str(REPO / "pengu_project.py")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _tmp_dir(prefix: str) -> str:
    """Creates a unique scratch directory under build/ (repo root untouched)."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    return tempfile.mkdtemp(prefix=f"cli_{prefix}_", dir=BUILD_DIR)


@pytest.fixture()
def proj_dir():
    """Yields a fresh scratch root under build/ and removes it afterwards."""
    d = _tmp_dir("proj")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cli(args, cwd=None, timeout=600):
    """Runs the pengu CLI in a subprocess the way the old suite did."""
    return subprocess.run(
        [PY, "-m", MODULE] + list(args),
        cwd=cwd or REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def cli_from(cwd, args, timeout=600):
    """Runs the CLI from an arbitrary cwd using the repo script path."""
    return subprocess.run(
        [PY, PROJECT_SCRIPT] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def runtime_yaml(proj: str, name: str, entry: str, output: str = "exe",
                 extra: str = "") -> str:
    """Writes a pengu.yaml wired to the repo's built runtime archives."""
    lib = (BUILD_DIR / "lib").resolve()
    inc = (BUILD_DIR / "include").resolve()
    yaml_text = (
        'project:\n'
        f'  name: "{name}"\n'
        '  version: "0.1.0"\n'
        f'  entry: "{entry}"\n'
        f'  output: "{output}"\n'
        f'  output_name: "{name}"\n'
        '\n'
        'build:\n'
        '  build_dir: "build"\n'
        '  links: ["pengu_runtime"]\n'
        f'  lib_dirs: [{json.dumps(str(lib).replace(chr(92), "/"))}]\n'
        f'  include_dirs: [{json.dumps(str(inc).replace(chr(92), "/"))}, '
        f'{json.dumps(str(BUILD_DIR).replace(chr(92), "/"))}]\n'
        f'{extra}'
    )
    with open(os.path.join(proj, "pengu.yaml"), "w", encoding="utf-8") as f:
        f.write(yaml_text)
    return yaml_text


def write_file(root: str, rel: str, content: str) -> str:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# --------------------------------------------------------------------------
# fixtures used by several tests (script module + small projects)
# --------------------------------------------------------------------------

SCRIPTMOD = """\
import std.spark

weave greet with who as string into void:
    calling spark.println with "greeting " + who
    when main:
        calling spark.println with "greet inner-main"

when main:
    weave main into int:
        calling spark.println with "scriptmod entry"
        calling greet with "World"
        return 0
"""

RUNNER = """\
import std.spark
import scriptmod

weave main into int:
    calling spark.println with "runner entry"
    calling scriptmod.greet with "driver"
    return 0
"""


def _write_when_main_project(root: str) -> str:
    """Writes a project whose entry imports a sibling module using 'when main'.

    Returns the project directory.
    """
    write_file(root, "src/main.pengu", RUNNER)
    write_file(root, "src/scriptmod.pengu", SCRIPTMOD)
    runtime_yaml(root, "runner_proj", "src/main.pengu")
    return root


# ==========================================================================
# pengu init
# ==========================================================================


class TestInit:
    def test_init_cli_creates_exe_scaffolding(self, proj_dir):
        res = cli_from(proj_dir, ["init", "my_game", "--type", "exe"])
        assert res.returncode == 0, res.stderr
        base = os.path.join(proj_dir, "my_game")
        for rel in ("pengu.yaml", "src/main.pengu", ".gitignore", "README.md"):
            assert os.path.isfile(os.path.join(base, rel)), rel
        for rel in ("src", "lib", "include", "c"):
            assert os.path.isdir(os.path.join(base, rel)), rel
        main = open(os.path.join(base, "src", "main.pengu"), encoding="utf-8").read()
        assert "weave main into void:" in main
        assert "Hello from my_game!" in main
        yaml_txt = open(os.path.join(base, "pengu.yaml"), encoding="utf-8").read()
        assert '"exe"' in yaml_txt

    def test_init_exe_structure_and_config_roundtrip(self, proj_dir):
        from pengu_project import ProjectConfig, init_project

        base_dir = os.path.join(proj_dir, "inner")
        os.makedirs(base_dir, exist_ok=True)
        proj = init_project("my_rpg", output_type="exe", target_dir=base_dir)
        for rel in ("src", "lib", "include", "c"):
            assert os.path.isdir(os.path.join(proj, rel))
        for rel in ("src/main.pengu", "pengu.yaml", ".gitignore", "README.md"):
            assert os.path.isfile(os.path.join(proj, rel))
        cfg = ProjectConfig.load(proj)
        assert cfg.name == "my_rpg"
        assert cfg.src_dir == "src"
        assert cfg.lib_dir == "lib"
        assert cfg.include_dir == "include"
        assert cfg.c_dir == "c"
        assert cfg.resolve_entry() == os.path.abspath(
            os.path.join(proj, "src", "main.pengu"))

    def test_init_static_template_content(self, proj_dir):
        from pengu_project import ProjectConfig, OutputType, init_project

        base_dir = os.path.join(proj_dir, "inner")
        os.makedirs(base_dir, exist_ok=True)
        proj = init_project("my_lib", output_type="static", target_dir=base_dir)
        main = open(os.path.join(proj, "src", "main.pengu"), encoding="utf-8").read()
        assert "weave add" in main
        assert "Static library" in main
        cfg = ProjectConfig.load(proj)
        assert cfg.output == OutputType.STATIC


# ==========================================================================
# pengu check
# ==========================================================================


class TestCheck:
    def test_check_clean_project_exit_zero(self, proj_dir):
        proj = _write_when_main_project(proj_dir)
        res = cli(["check", "-c", proj, "-e", "src/main.pengu"])
        assert res.returncode == 0, res.stderr
        assert "Clean" in res.stdout

    def test_check_entry_override_reports_semantic_error(self, proj_dir):
        # A valid project whose *default* entry would be unrelated: the
        # --entry override is what is checked.
        proj = _write_when_main_project(proj_dir)
        bad = write_file(proj_dir, "bad.pengu", "const main as int is 1\n")
        res = cli(["check", "-c", proj, "-e", bad])
        assert res.returncode == 1
        assert "E0040" in res.stderr
        assert "bad.pengu" in res.stderr

    def test_check_accepts_entry_override_of_valid_file(self, proj_dir):
        proj = _write_when_main_project(proj_dir)
        res = cli(["check", "-c", proj, "-e", "src/scriptmod.pengu"])
        assert res.returncode == 0, res.stderr


# ==========================================================================
# pengu fmt + shared formatter
# ==========================================================================


class TestFmt:
    def test_format_strips_trailing_ws_and_normalizes_indent(self):
        from pengu_lsp.formatting import format_pengu_source

        src = "weave main into void:\n   var x as int is 1   \n"
        out = format_pengu_source(src, tab_size=2)
        assert out == "weave main into void:\n  var x as int is 1\n"
        assert all(l == l.rstrip() for l in out.splitlines())

    def test_format_preserves_clean_indentation(self):
        from pengu_lsp.formatting import format_pengu_source

        src = "weave main into void:\n    calling f with x\n"
        assert format_pengu_source(src, tab_size=2) == src

    def test_format_tabs_kept_when_insert_spaces_false(self):
        from pengu_lsp.formatting import format_pengu_source

        src = "weave main into void:\n\tvar x as int is 0\n"
        assert format_pengu_source(src, tab_size=2, insert_spaces=False) == src

    def test_fmt_check_reports_changes(self, proj_dir):
        f = write_file(proj_dir, "demo.pengu",
                       "weave main into void:\n    var x as int is 0   \n"
                       "    calling f with x\n")
        res = cli(["fmt", "--check", f])
        assert res.returncode == 1
        assert "would be reformatted" in res.stdout

    def test_fmt_write_then_check_clean(self, proj_dir):
        f = write_file(proj_dir, "demo.pengu",
                       "weave main into void:\n    var x as int is 0   \n"
                       "    calling f with x\n")
        res = cli(["fmt", f])
        assert res.returncode == 0, res.stderr
        content = open(f, encoding="utf-8").read()
        assert "   \n" not in content
        res2 = cli(["fmt", "--check", f])
        assert res2.returncode == 0, res2.stdout


# ==========================================================================
# pengu run <script> script mode
# ==========================================================================


@requires_cc
@requires_runtime
class TestRunScript:
    def test_cli_run_script_with_when_main(self, proj_dir):
        script = write_file(proj_dir, "scriptmod.pengu", SCRIPTMOD)
        # Script-mode artifacts land in build/scriptmod_run/ (isolated per
        # script inside the repo build dir), so runs never fight over shared
        # files; the proj_dir fixture holds only the sources.
        res = cli(["run", script])
        assert res.returncode == 0, res.stderr
        assert "scriptmod entry" in res.stdout
        assert "greeting World" in res.stdout
        assert "greet inner-main" in res.stdout

    def test_cli_run_script_plain_weave_main(self, proj_dir):
        script = write_file(proj_dir, "plainmain.pengu",
                            'weave main into int:\n'
                            '    calling print with "plain main ok"\n'
                            '    return 0\n')
        res = cli(["run", script])
        assert res.returncode == 0, res.stderr
        assert "plain main ok" in res.stdout


# ==========================================================================
# pengu build / pengu run project mode (compile + execute)
# ==========================================================================


@requires_cc
@requires_runtime
class TestBuildRunProject:
    def test_cli_run_project_default_keeps_imported_main_off(self, proj_dir):
        proj = _write_when_main_project(proj_dir)
        res = cli(["run", "-c", proj])
        assert res.returncode == 0, res.stderr
        assert "runner entry" in res.stdout
        assert "greeting driver" in res.stdout
        # scriptmod is imported: its 'when main' blocks must not appear, and a
        # default project build keeps even the entry's 'main' compile-time off.
        assert "scriptmod entry" not in res.stdout
        assert "greet inner-main" not in res.stdout

    def test_project_bundle_entry_as_main_gates_when_main(self, proj_dir):
        """Entry-as-main: only the entry module sees 'when main' (no gcc needed).

        Mirrors the old compile+run matrix (entry script, default project mode
        and import-with-entry-as-main) at the PenguBuilder/bundle level.
        """
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _write_when_main_project(proj_dir)

        def bundle_c(entry, entry_as_main):
            cfg = ProjectConfig.load(proj)
            cfg.entry = entry
            builder = PenguBuilder(cfg)
            builder.entry_as_main = entry_as_main
            path, _ = builder.bundle()
            with open(path, encoding="utf-8") as f:
                return f.read()

        # (a) script compiled as the entry with entry-as-main on: 'when main'
        # blocks are emitted.
        on = bundle_c("src/scriptmod.pengu", True)
        assert "scriptmod entry" in on
        assert "greet inner-main" in on
        # (b) the same module in default project mode (entry-as-main off):
        # 'when main' blocks are dropped, the unguarded helper remains.
        off = bundle_c("src/scriptmod.pengu", False)
        assert "greeting " in off
        assert "scriptmod entry" not in off
        assert "greet inner-main" not in off
        # (c) runner imports scriptmod with entry-as-main on: imported modules
        # still compile with 'main' false, so scriptmod's blocks are dropped.
        imported = bundle_c("src/main.pengu", True)
        assert "runner entry" in imported
        assert "greeting " in imported
        assert "scriptmod entry" not in imported
        assert "greet inner-main" not in imported

    def test_cli_build_compiles_exe_and_cached_rebuild(self, proj_dir):
        write_file(proj_dir, "src/main.pengu",
                   'import std.spark\n\n'
                   'weave main into int:\n'
                   '    calling spark.println with "build me ok"\n'
                   '    return 0\n')
        runtime_yaml(proj_dir, "hello_proj", "src/main.pengu")
        res = cli(["build", "-c", proj_dir])
        assert res.returncode == 0, res.stderr
        suffix = ".exe" if os.name == "nt" else ""
        artifact = os.path.join(proj_dir, "build", "hello_proj" + suffix)
        assert os.path.isfile(artifact)
        run_res = subprocess.run([artifact], capture_output=True, text=True,
                                 timeout=300)
        assert run_res.returncode == 0, run_res.stderr
        assert "build me ok" in run_res.stdout
        # The incremental machinery must consider the bundle up to date now
        # (checked in-process; the CLI timing path is environment sensitive).
        from pengu_parser.pengu_symbols import resolve_imports
        from pengu_project import PenguBuilder, ProjectConfig

        cfg = ProjectConfig.load(proj_dir)
        b = PenguBuilder(cfg)
        bundle_path = os.path.join(proj_dir, "build", "bundle.c")
        module_order = resolve_imports(proj_dir, cfg.resolve_entry(), b.parser)
        assert b.is_bundle_up_to_date(bundle_path, module_order)
        # a second CLI build is idempotent and still yields a runnable artifact
        res2 = cli(["build", "-c", proj_dir])
        assert res2.returncode == 0, res2.stderr
        assert os.path.isfile(artifact)
        run_res2 = subprocess.run([artifact], capture_output=True, text=True,
                                  timeout=300)
        assert run_res2.returncode == 0, run_res2.stderr
        assert "build me ok" in run_res2.stdout

    def test_bundle_output_c_and_runtime_header_copy(self, proj_dir):
        from pengu_project import PenguBuilder, ProjectConfig, OutputType

        main = write_file(proj_dir, "main.pengu",
                          "weave main into void:\n  var x as int is 42\n")
        cfg = ProjectConfig(name="test_c", entry=main, output=OutputType.C,
                            build_dir="build", base_dir=proj_dir)
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle()
        assert os.path.isfile(bundle_path)
        content = open(bundle_path, encoding="utf-8").read()
        assert "pengu_runtime.h" in content
        assert "main.pengu" in content
        # output=C never invokes the C compiler
        out, _ = builder.compile(bundle_path)
        assert out == bundle_path
        assert os.path.isfile(os.path.join(proj_dir, "build", "pengu_runtime.h"))

    def test_bundle_respects_custom_build_dir(self, proj_dir):
        from pengu_project import PenguBuilder, ProjectConfig, OutputType

        main = write_file(proj_dir, "main.pengu",
                          'weave main into void:\n  var m as string is "test"\n')
        cfg = ProjectConfig(name="app_dir", entry=main,
                            build_dir="custom_build", output=OutputType.C,
                            base_dir=proj_dir)
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle()
        assert os.path.abspath(bundle_path) == os.path.abspath(
            os.path.join(proj_dir, "custom_build", "bundle.c"))
        assert not os.path.exists(os.path.join(proj_dir, "bundle.c"))

    def test_compile_failure_reports_command(self, proj_dir):
        write_file(proj_dir, "src/main.pengu",
                   "weave main into void:\n  calling print with 1\n")
        write_file(proj_dir, "c/glue.c", "this is not valid C @@\n")
        runtime_yaml(proj_dir, "cfail", "src/main.pengu")
        res = cli(["build", "-c", proj_dir])
        assert res.returncode == 1
        assert "Command:" in res.stderr
        assert "cfail" in res.stderr


# ==========================================================================
# builder compile-command / output-type / profile plumbing
# ==========================================================================


class TestBuildCommands:
    def test_output_types(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig

        cfg = ProjectConfig(output=OutputType.OBJ, output_name="mod",
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands("bundle.c", "mod.o")
        assert cmds[0][:4] == ["gcc", "-c", "bundle.c", "-o"]

        cfg = ProjectConfig(output=OutputType.STATIC, output_name="mylib",
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands("bundle.c", "mylib.a")
        assert len(cmds) == 2
        assert cmds[1][:3] == ["ar", "rcs", "mylib.a"]

        cfg = ProjectConfig(output=OutputType.SHARED, output_name="mylib",
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands("bundle.c", "mylib.dll")
        assert any("-shared" in c for c in cmds)
        if os.name == "nt":
            assert not any("-fPIC" in c for c in cmds)
        else:
            assert any("-fPIC" in c for c in cmds)

        cfg = ProjectConfig(output=OutputType.C, base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands("bundle.c", "bundle.c")
        assert cmds == []

    def test_compile_exe_custom_links(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig

        cfg = ProjectConfig(name="game", output=OutputType.EXE,
                            output_name="game_bin", links=["raylib", "m"],
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "bundle.c", "game_bin.exe")
        assert len(cmds) == 1
        cmd_str = " ".join(cmds[0])
        assert "-lraylib" in cmd_str
        assert "-lm" in cmd_str

    def test_no_hardcoded_raylib_with_empty_links(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig

        cfg = ProjectConfig(name="headless", output=OutputType.EXE,
                            output_name="headless_app", links=[],
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "bundle.c", "headless_app.exe")
        cmd_str = " ".join(cmds[0])
        assert "-lraylib" not in cmd_str
        assert "-l" not in cmd_str

    def test_profiles_apply_flags(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig

        cfg = ProjectConfig(name="release_app", output=OutputType.EXE,
                            profile="release", base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "build/bundle.c", "build/app.exe")
        cmd_str = " ".join(cmds[0])
        assert "-O3" in cmd_str
        assert "-DNDEBUG" in cmd_str

        cfg = ProjectConfig(name="debug_app", output=OutputType.EXE,
                            profile="debug", base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "build/bundle.c", "build/app.exe")
        cmd_str = " ".join(cmds[0])
        assert "-g" in cmd_str
        assert "-DDEBUG" in cmd_str

    def test_compile_commands_collect_c_and_lib_dirs(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig

        proj = os.path.join(proj_dir, "multi_c_proj")
        for sub in ("src", "include", "c"):
            os.makedirs(os.path.join(proj, sub), exist_ok=True)
        for sub in ("c", "include", "lib"):
            os.makedirs(os.path.join(proj, "lib", "mylib", sub), exist_ok=True)
        write_file(proj, "c/helper.c", "void helper_fn() {}\n")
        write_file(proj, "lib/mylib/c/mylib_glue.c", "void mylib_c_func() {}\n")
        write_file(proj, "lib/mylib/lib/libmylib_native.a", "dummy archive")

        cfg = ProjectConfig(name="multi_c_app", base_dir=proj,
                            entry="src/main.pengu", output=OutputType.EXE)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "build/bundle.c", "build/app.exe")
        assert len(cmds) == 1
        args = cmds[0]
        cmd_str = " ".join(args)
        assert any("helper.c" in a for a in args)
        assert any("mylib_glue.c" in a for a in args)
        assert any(a.startswith("-I") and "include" in a for a in args)
        assert any(a.startswith("-I") and "mylib" in a for a in args)
        assert any(a.startswith("-L") and "mylib" in a for a in args)
        assert "-lmylib_native" in cmd_str


# ==========================================================================
# project config parsing / discovery
# ==========================================================================


class TestProjectConfig:
    def test_load_yaml_file(self, proj_dir):
        from pengu_project import ProjectConfig, OutputType

        yaml_path = write_file(proj_dir, "pengu.yaml", """\
project:
  name: "physics_app"
  version: "0.2.0"
  entry: "main.pengu"
  output: "static"
  output_name: "libphysics"

build:
  links: ["m", "pthread"]
  cflags: ["-O3", "-Wall"]
""")
        config = ProjectConfig.load(yaml_path)
        assert config.name == "physics_app"
        assert config.version == "0.2.0"
        assert config.output == OutputType.STATIC
        assert config.output_name == "libphysics"
        assert config.links == ["m", "pthread"]

    def test_load_json_file(self, proj_dir):
        from pengu_project import ProjectConfig, OutputType

        data = {
            "project": {
                "name": "web_server", "version": "1.0.0",
                "entry": "server.pengu", "output": "shared",
                "output_name": "libserver",
            },
            "build": {
                "links": ["ssl", "crypto"],
                "include_dirs": ["./include"],
                "lib_dirs": ["./lib"],
            },
        }
        json_path = write_file(proj_dir, "pengu.json", json.dumps(data))
        config = ProjectConfig.load(json_path)
        assert config.name == "web_server"
        assert config.entry == "server.pengu"
        assert config.output == OutputType.SHARED
        assert config.links == ["ssl", "crypto"]
        assert config.include_dirs == ["./include"]
        assert config.lib_dirs == ["./lib"]

    def test_discovery_prefers_toml_then_yaml_then_json(self, proj_dir):
        from pengu_project import ProjectConfig, OutputType

        # pengu.toml only
        d = os.path.join(proj_dir, "a")
        os.makedirs(d, exist_ok=True)
        write_file(d, "pengu.toml", """\
[project]
name = "toml_proj"
version = "0.3.0"
entry = "main.pengu"
output = "c"
output_name = "libtoml"

[build]
links = ["m"]
""")
        cfg = ProjectConfig.load(d)
        assert cfg.name == "toml_proj"
        assert cfg.output == OutputType.C
        assert cfg.links == ["m"]

        # pengu.json discovery
        d2 = os.path.join(proj_dir, "b")
        os.makedirs(d2, exist_ok=True)
        write_file(d2, "pengu.json", json.dumps(
            {"project": {"name": "json_proj", "output": "obj",
                         "output_name": "jmod"}}))
        cfg = ProjectConfig.load(d2)
        assert cfg.name == "json_proj"
        assert cfg.output == OutputType.OBJ

        # precedence: when both exist, pengu.toml wins over pengu.yaml
        d3 = os.path.join(proj_dir, "c")
        os.makedirs(d3, exist_ok=True)
        write_file(d3, "pengu.yaml",
                   "project:\n  name: yaml_proj\n  entry: a.pengu\n")
        write_file(d3, "pengu.toml",
                   '[project]\nname = "toml_wins"\nentry = "b.pengu"\n')
        cfg = ProjectConfig.load(d3)
        assert cfg.name == "toml_wins"


# ==========================================================================
# pengu update / pengu clean (network-free)
# ==========================================================================


class TestUpdateClean:
    def test_update_local_dependency_runs_build_script(self, proj_dir):
        from pengu_project import update_project

        write_file(proj_dir, "pengu.toml", """\
name = "upd_test"
version = "0.1.0"
entry = "src/main.pengu"

[dependencies.dep_local]
url = "."
""")
        write_file(proj_dir, "lib/dep_local/build.py",
                   'import pathlib\n'
                   'pathlib.Path("marker.txt").write_text("built", '
                   'encoding="utf-8")\n')
        updated = update_project(config_path=proj_dir, verbose=True)
        assert updated == 1
        marker = os.path.join(proj_dir, "lib", "dep_local", "marker.txt")
        assert os.path.isfile(marker), "build.py should have run"
        assert open(marker, encoding="utf-8").read() == "built"

    def test_update_no_dependencies(self, proj_dir):
        from pengu_project import update_project

        assert update_project(config_path=proj_dir) == 0

    def test_clean_removes_build_dir(self, proj_dir):
        from pengu_project import clean_project

        build_dir = os.path.join(proj_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        write_file(build_dir, "artifact.bin", "x")
        clean_project(config_path=proj_dir)
        assert not os.path.exists(build_dir)
        clean_project(config_path=proj_dir)  # nothing to clean: no exception

    def test_clean_cli_subcommand(self, proj_dir):
        write_file(proj_dir, "src/main.pengu", "weave main into void:\n  return\n")
        write_file(proj_dir, "pengu.yaml",
                   "project:\n  name: cln\n  entry: src/main.pengu\n")
        build_dir = os.path.join(proj_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        write_file(build_dir, "bundle.c", "x")
        res = cli(["clean", "-c", proj_dir])
        assert res.returncode == 0, res.stderr
        assert not os.path.exists(build_dir)


# ==========================================================================
# pengu doc
# ==========================================================================


DOC_SOURCE = """\
## Greets a name warmly.
weave greet with name as string into string:
  return "hello " + name

## A 2D vector type.
rune Vec2:
  x as float
  y as float

## Supported output levels.
omen Level with string:
  Info
  Error

## Default greeting.
const DEFAULT_GREET as string is "hi"
"""


class TestPenguDoc:
    def _doc_project(self, proj_dir):
        write_file(proj_dir, "src/greet.pengu", DOC_SOURCE)
        write_file(proj_dir, "pengu.yaml", """\
project:
  name: "docgen"
  version: "0.1.0"
  entry: "src/greet.pengu"
  output: "c"
  output_name: "docgen"
""")
        return proj_dir

    def test_doc_generates_index_and_pages(self, proj_dir):
        from pengu_doc import doc_project

        proj = self._doc_project(proj_dir)
        index = doc_project(config_path=proj,
                            output=os.path.join(proj, "docs"))
        assert os.path.isfile(index)
        index_text = open(index, encoding="utf-8").read()
        assert "greet" in index_text

        page = os.path.join(proj, "docs", "src_greet.md")
        assert os.path.isfile(page)
        text = open(page, encoding="utf-8").read()
        assert "Greets a name warmly." in text
        assert "**greet**(name: string) -> string" in text
        assert "A 2D vector type." in text
        assert "`x` : float" in text
        assert "Default greeting." in text
        assert "`Info` = `Info`" in text

    def test_doc_cli_subcommand(self, proj_dir):
        proj = self._doc_project(proj_dir)
        out = os.path.join(proj, "docs")
        res = cli(["doc", "-c", proj, "-o", out])
        assert res.returncode == 0, res.stderr
        assert os.path.isfile(os.path.join(out, "index.md"))
        assert os.path.isfile(os.path.join(out, "src_greet.md"))
        assert "Generated" in res.stdout


# ==========================================================================
# project structure / bindings helpers
# ==========================================================================


class TestProjectStructure:
    def test_extract_lib_name(self):
        from pengu_project import extract_lib_name

        assert extract_lib_name("libwebui-2-static.a") == "webui-2-static"
        assert extract_lib_name("libraylib.a") == "raylib"
        assert extract_lib_name("webui.lib") == "webui"
        assert extract_lib_name("libfoo.so") == "foo"
        assert extract_lib_name("libbar.dylib") == "bar"
        assert extract_lib_name("foo.dll") == "foo"
        assert extract_lib_name("readme.txt") is None
        assert extract_lib_name("main.pengu") is None

    def test_find_module_path_in_src_and_lib(self, proj_dir):
        from pengu_parser.pengu_symbols import find_module_path

        vec = write_file(proj_dir, "src/math/vec.pengu",
                         "rune Vec2:\n  x as float\n  y as float\n")
        web = write_file(proj_dir, "lib/webui/pengu/webui.pengu",
                         'include "webui.h"\nlink "webui"\n'
                         "weave new_window into int:\n  return 1\n")
        assert os.path.abspath(find_module_path(proj_dir, "math.vec")) == \
            os.path.abspath(vec)
        assert os.path.abspath(find_module_path(proj_dir, "webui")) == \
            os.path.abspath(web)

    def test_resolve_imports_with_binding(self, proj_dir):
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_symbols import resolve_imports

        write_file(proj_dir, "lib/raylib/pengu/raylib.pengu",
                   'include "raylib.h"\nlink "raylib"\n'
                   "weave init_window with w as int, h as int into void:\n"
                   "  return\n")
        write_file(proj_dir, "src/main.pengu",
                   "import raylib\n\n"
                   "weave main into void:\n"
                   "  calling raylib.init_window with 800, 600\n")
        order = resolve_imports(proj_dir, "src/main.pengu", PenguParser())
        assert len(order) == 2
        assert order[0].endswith("raylib.pengu")
        assert order[1].endswith("main.pengu")

    def test_bundle_with_binding_and_codegen(self, proj_dir):
        from pengu_project import PenguBuilder, ProjectConfig

        write_file(proj_dir, "lib/ui/pengu/ui.pengu",
                   'include "ui_native.h"\nlink "ui_native"\n'
                   "weave show_dialog with msg as string into void:\n"
                   "  calling print with msg\n")
        write_file(proj_dir, "src/main.pengu",
                   "import ui\n\n"
                   "weave main into void:\n"
                   '  var txt as string is "Hello UI"\n'
                   "  calling ui.show_dialog with txt\n")
        cfg = ProjectConfig(name="gui_app", base_dir=proj_dir,
                            entry="src/main.pengu")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle()
        assert os.path.isfile(bundle_path)
        c_code = open(bundle_path, encoding="utf-8").read()
        assert '#include "ui_native.h"' in c_code
        assert "show_dialog" in c_code
        assert "pengu_main" in c_code

    def test_add_dependency_local_folder(self, proj_dir):
        from pengu_project import add_dependency, init_project

        proj = init_project("main_app", output_type="exe", target_dir=proj_dir)
        ext = os.path.join(proj_dir, "webui_repo")
        for sub in ("pengu", "include", "c", "lib"):
            os.makedirs(os.path.join(ext, sub), exist_ok=True)
        write_file(ext, "pengu/webui.pengu",
                   "weave webui_init into int:\n  return 0\n")
        write_file(ext, "include/webui.h", "int webui_init(void);\n")
        write_file(ext, "build.py", 'print("Building webui...")\n')

        added_dir = add_dependency(source=ext, name="webui",
                                   config_path=proj, run_build=True)
        assert os.path.isdir(added_dir)
        assert os.path.isfile(os.path.join(added_dir, "pengu", "webui.pengu"))
        assert os.path.isfile(os.path.join(added_dir, "include", "webui.h"))
        yaml_txt = open(os.path.join(proj, "pengu.yaml"), encoding="utf-8").read()
        assert "webui" in yaml_txt

    def test_legacy_flat_project_compatibility(self, proj_dir):
        from pengu_project import PenguBuilder, ProjectConfig

        legacy = os.path.join(proj_dir, "legacy")
        os.makedirs(legacy, exist_ok=True)
        main_pengu = write_file(legacy, "main.pengu",
                                "weave main into void:\n  calling print with 123\n")
        write_file(legacy, "pengu.yaml",
                   "project:\n  name: legacy\n  entry: main.pengu\n")
        config = ProjectConfig.load(legacy)
        assert config.resolve_entry() == os.path.abspath(main_pengu)
        builder = PenguBuilder(config)
        bundle_path, _ = builder.bundle()
        assert os.path.isfile(bundle_path)


# ==========================================================================
# CLI plumbing that needs no toolchain (verbose / --cc / error shaping)
# ==========================================================================


class TestCliPlumbing:
    def test_builder_verbose_and_check_sources(self, proj_dir):
        from pengu_project import PenguBuilder, ProjectConfig

        write_file(proj_dir, "src/scriptmod.pengu", SCRIPTMOD)
        write_file(proj_dir, "src/main.pengu", RUNNER)
        runtime_yaml(proj_dir, "runner_proj", "src/main.pengu")
        cfg = ProjectConfig.load(proj_dir)
        builder = PenguBuilder(cfg)
        builder.entry_as_main = True
        builder.verbose = True
        ok, messages = builder.check_sources()
        assert ok, messages
        assert builder.verbose

    def test_cc_override_lands_on_config(self):
        from pengu_project import PenguBuilder, ProjectConfig

        cfg = ProjectConfig(entry="src/main.pengu", base_dir=".",
                            output="exe")
        cfg.cc = "clang"
        builder = PenguBuilder(cfg)
        assert builder.config.cc == "clang"

    def test_compile_failed_error_message_shapes(self):
        from pengu_project import CompileFailedError

        err = CompileFailedError(
            "C compilation failed (app)\n\nCommand: gcc x.c")
        text = str(err)
        assert "Command: gcc x.c" in text


# ==========================================================================
# std.archivum copy_tree / list_files_recursive (pure-Pengu std behaviour)
# ==========================================================================


@requires_cc
@requires_runtime
class TestArchivumTree:
    def test_copy_tree_and_list_files_recursive(self):
        import uuid
        tag = uuid.uuid4().hex[:10]
        rel_src = f"build/archivum_tree_{tag}_src"
        rel_dst = f"build/archivum_tree_{tag}_dst"
        src_dir = os.path.join(REPO, rel_src.replace("/", os.sep))
        dst_dir = os.path.join(REPO, rel_dst.replace("/", os.sep))
        shutil.rmtree(src_dir, ignore_errors=True)
        shutil.rmtree(dst_dir, ignore_errors=True)
        try:
            source = f"""\
import std.spark
import std.archivum

weave main into int:
    var ok_root as bool is calling archivum.create_dir with "{rel_src}" and true
    if ok_root == false:
        calling spark.println with "mkdir failed"
        return 1
    var ok_a as bool is calling archivum.write_file with "{rel_src}/a.txt" and "alpha"
    if ok_a == false:
        return 1
    var ok_sub as bool is calling archivum.create_dir with "{rel_src}/sub" and true
    if ok_sub == false:
        return 1
    var ok_b as bool is calling archivum.write_file with "{rel_src}/sub/b.txt" and "beta"
    if ok_b == false:
        return 1
    var copied as bool is calling archivum.copy_tree with "{rel_src}" and "{rel_dst}"
    if copied == false:
        calling spark.println with "copy failed"
        return 1
    var files as list of string is calling archivum.list_files_recursive with "{rel_dst}"
    if files.len == 2:
        calling spark.println with "list ok"
    var a_ok as bool is calling archivum.is_file with "{rel_dst}/a.txt"
    var b_ok as bool is calling archivum.is_file with "{rel_dst}/sub/b.txt"
    if a_ok:
        if b_ok:
            calling spark.println with "copy_tree ok"
    return 0
"""
            res = compile_run(source, tag=f"arch_{tag}")
            assert res.returncode == 0, res.stderr
            assert "list ok" in res.stdout
            assert "copy_tree ok" in res.stdout
            assert os.path.isfile(os.path.join(dst_dir, "a.txt"))
            assert os.path.isfile(os.path.join(dst_dir, "sub", "b.txt"))
        finally:
            shutil.rmtree(src_dir, ignore_errors=True)
            shutil.rmtree(dst_dir, ignore_errors=True)
