"""End-to-end tests for the CLI templates (``init`` / ``new`` / ``add``).

These drive ``pengu_project.py`` as a subprocess on purpose: the templates are a
CLI contract (which files land where, what the manifest says, whether a
consumer can ``import`` the result), and every one of the bugs fixed in 2.1.0
was only visible across a process boundary.

The file is split by cost:

* ``@pytest.mark.smoke`` cases only create/copy files, so they run in the fast
  tier on every platform (no C compiler, no runtime archive).
* ``test_cbind_roundtrip_add_and_build`` compiles real C through gcc/clang and
  is marked ``slow``; it skips when the toolchain is unavailable.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

#: Repository root: ``tests/compiler/test_cli_templates.py`` -> tests -> checkout.
HERE = Path(__file__).resolve().parents[2]
CLI = HERE / "pengu_project.py"
RUNTIME_ARCHIVE = HERE / "build" / "lib" / "libpengu_runtime.a"


def run_cli(*args: str, cwd: Path | None = None, check: bool = True):
    """Runs the CLI with this interpreter and returns the CompletedProcess."""
    cmd = [sys.executable, str(CLI), *args]
    env = dict(os.environ)
    # Deterministic, self-contained runs: never touch the shared dependency
    # cache, and never ask interactively about trusting a build script.
    env["PENGU_NO_DEP_CACHE"] = "1"
    env["PENGU_CACHE"] = "0"
    env["NO_COLOR"] = "1"
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                         capture_output=True, text=True, env=env)
    if check and res.returncode != 0:
        raise AssertionError(
            f"CLI {' '.join(args)} failed (rc={res.returncode})\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
    return res


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_ar() -> bool:
    return bool(shutil.which("ar") or shutil.which("llvm-ar"))


@pytest.mark.smoke
def test_init_pengu_lib_creates_pengu_dir(tmp_path: Path) -> None:
    run_cli("init", "my_lib", "--template", "pengu-lib", cwd=tmp_path)
    proj = tmp_path / "my_lib"
    assert (proj / "pengu" / "my_lib.pengu").is_file()
    assert (proj / "pengu.toml").is_file()
    assert not (proj / "src").exists()
    manifest = (proj / "pengu.toml").read_text(encoding="utf-8")
    assert 'entry = "pengu/my_lib.pengu"' in manifest
    assert 'output = "static"' in manifest
    assert 'src_dir = "pengu"' in manifest


@pytest.mark.smoke
def test_init_cbind_creates_full_binding_scaffold(tmp_path: Path) -> None:
    run_cli("init", "pengu_demo", "--template", "cbind", cwd=tmp_path)
    proj = tmp_path / "pengu_demo"
    assert (proj / "pengu" / "pengu_demo.d.pengu").is_file()
    assert (proj / "include" / "pengu_demo.h").is_file()
    assert (proj / "c" / "pengu_demo.c").is_file()
    assert (proj / "lib").is_dir()
    assert (proj / "build.pengu").is_file()
    assert not (proj / "build.py").exists()
    assert (proj / "README.md").is_file()
    manifest = (proj / "pengu.toml").read_text(encoding="utf-8")
    assert 'entry = "pengu/pengu_demo.d.pengu"' in manifest
    assert 'output = "c"' in manifest
    # The declaration file is the contract the consumer relies on.
    decl = (proj / "pengu" / "pengu_demo.d.pengu").read_text(encoding="utf-8")
    assert 'include "pengu_demo.h"' in decl
    assert 'link "pengu_demo"' in decl
    assert "declare pengu_demo_add" in decl


@pytest.mark.smoke
def test_init_refuses_nonempty_dir_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("hi", encoding="utf-8")

    res = run_cli("init", "existing", check=False, cwd=tmp_path)
    assert res.returncode != 0
    assert "already exists and is not empty" in (res.stdout + res.stderr)
    assert (existing / "keep.txt").read_text(encoding="utf-8") == "hi"
    assert not (existing / "src").exists()


@pytest.mark.smoke
def test_init_force_overwrites_nonempty_dir(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("hi", encoding="utf-8")

    run_cli("init", "existing", "--force", cwd=tmp_path)
    assert (existing / "src" / "main.pengu").is_file()
    # --force writes into the directory; it does not delete what is already there.
    assert (existing / "keep.txt").is_file()


@pytest.mark.smoke
def test_new_cbind_alias(tmp_path: Path) -> None:
    run_cli("new", "cbind", "pengu_sdl", cwd=tmp_path)
    assert (tmp_path / "pengu_sdl" / "pengu" / "pengu_sdl.d.pengu").is_file()


@pytest.mark.smoke
def test_new_pengu_lib_alias(tmp_path: Path) -> None:
    run_cli("new", "pengu-lib", "my_algorithms", cwd=tmp_path)
    assert (tmp_path / "my_algorithms" / "pengu" / "my_algorithms.pengu").is_file()


@pytest.mark.smoke
def test_template_lib_is_deprecated_alias(tmp_path: Path) -> None:
    res = run_cli("init", "legacy_lib", "--template", "lib", cwd=tmp_path)
    assert (tmp_path / "legacy_lib" / "pengu" / "legacy_lib.pengu").is_file()
    assert "deprecated" in (res.stdout + res.stderr).lower()


@pytest.mark.smoke
def test_add_moves_root_pengu_files_into_pengu_dir(tmp_path: Path) -> None:
    """Regression: `add_dependency` used to COPY root .pengu, leaving duplicates."""
    repo = tmp_path / "legacy"
    (repo / "pengu").mkdir(parents=True)
    (repo / "pengu.toml").write_text(
        '[project]\nname = "legacy"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (repo / "legacy.pengu").write_text(
        "weave ping into int:\n  return 1\n", encoding="utf-8"
    )

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    run_cli("init", "app", cwd=consumer)
    res = run_cli("add", str(repo), cwd=consumer / "app")

    installed = consumer / "app" / "lib" / "legacy"
    assert (installed / "pengu" / "legacy.pengu").is_file()
    assert not (installed / "legacy.pengu").is_file(), (
        "root .pengu must be MOVED, not copied, into pengu/"
    )
    # `pengu add` must tell the user what to import (2.1.0).
    assert "Try: import legacy" in (res.stdout + res.stderr)


@pytest.mark.slow
def test_cbind_roundtrip_add_and_build(tmp_path: Path) -> None:
    """Full flow: create a cbind repo, install it, import it, and build."""
    if not (_have_cc() and _have_ar()):
        pytest.skip("no C compiler / archiver available")
    if not RUNTIME_ARCHIVE.is_file():
        pytest.skip("runtime archive not built in this environment")

    # 1. Create the binding repository.
    binding_root = tmp_path / "binding_repo"
    binding_root.mkdir()
    run_cli("init", "pengu_demo", "--template", "cbind",
            "--force", cwd=binding_root)
    binding_repo = binding_root / "pengu_demo"

    # 2. Create the consumer project.
    consumer_root = tmp_path / "consumer"
    consumer_root.mkdir()
    run_cli("init", "app", cwd=consumer_root)
    app_dir = consumer_root / "app"

    # 3. Install the binding; --trust lets build.pengu compile the native part.
    run_cli("add", str(binding_repo), "--trust", cwd=app_dir)

    installed = app_dir / "lib" / "pengu_demo"
    assert (installed / "pengu" / "pengu_demo.d.pengu").is_file()
    # The redundant root copy must not exist (bug fix 4.2).
    assert not (installed / "pengu_demo.d.pengu").is_file()
    # build.pengu compiled the toy C library into lib/.
    assert (installed / "lib" / "libpengu_demo.a").is_file()

    # 4. Use the binding from a program.
    (app_dir / "src" / "main.pengu").write_text(
        textwrap.dedent(
            """\
            import pengu_demo

            weave main into int:
              var x as int is calling pengu_demo.pengu_demo_add with 2, 3
              calling print with x
              return x
            """
        ),
        encoding="utf-8",
    )

    # 5. Build: import resolution + include dir + propagated `link "pengu_demo"`
    #    must all line up without touching pengu.toml.
    run_cli("build", cwd=app_dir)
