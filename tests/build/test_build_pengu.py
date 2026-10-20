"""``build.pengu`` as the preferred build-script format.

The contract (docs/BINDINGS.md, LANGUAGE.md §20.2.6):

* discovery prefers ``build.pengu`` over ``build.py``/``build.sh``/``build.bat``
  and ``Makefile``;
* the CLI runs it as ``pengu run <dep>/build.pengu [-- --force]``;
* a refreshed checkout (``git pull``) and ``pengu update`` force a rebuild;
* a missing runtime archive or a missing CLI degrades to an actionable warning,
  never a crash;
* ``pengu init --template cbind`` / ``pengu-lib`` emit a ``build.pengu`` that
  actually compiles ``c/*.c`` into ``lib/lib<name>.a``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import pengu_project as pp

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "pengu_project.py"


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return pp._find_runtime_archive() is not None


needs_toolchain = pytest.mark.skipif(
    not (_have_cc() and _have_runtime()),
    reason="C compiler or libpengu_runtime.a not available (run build_runtime.py)",
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def _fake_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Installs a fake ``pengu`` CLI that appends its argv to ``FAKE_CLI_LOG``.

    ``_run_dependency_build`` only needs the argv shape; compiling a real
    script for the discovery/force tests would make them depend on a C
    toolchain for no added coverage (``test_build_pengu_compiles_toy_source``
    covers the real path).
    """
    marker = tmp_path / "fake-cli.log"
    script = _write(tmp_path / "fake_pengu.py", """
        import os
        import sys
        with open(os.environ["FAKE_CLI_LOG"], "a", encoding="utf-8") as fh:
            fh.write(" ".join(sys.argv[1:]) + "\\n")
    """)
    monkeypatch.setenv("FAKE_CLI_LOG", str(marker))
    monkeypatch.setattr(pp, "_pengu_cli_argv", lambda: [sys.executable, str(script)])
    monkeypatch.setattr(pp, "_find_runtime_archive", lambda target_os="": str(tmp_path / "libpengu_runtime.a"))
    return marker


# ---------------------------------------------------------------------------
# _pengu_cli_argv
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_pengu_cli_argv_source_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PENGU_BIN", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    argv = pp._pengu_cli_argv()
    assert argv[0] == sys.executable
    assert Path(argv[1]).name == "pengu_project.py"
    assert Path(argv[1]).is_file()


@pytest.mark.smoke
def test_pengu_cli_argv_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PENGU_BIN", str(tmp_path / "fake-pengu"))
    assert pp._pengu_cli_argv() == [str(tmp_path / "fake-pengu")]


@pytest.mark.smoke
def test_pengu_cli_argv_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PENGU_BIN", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert pp._pengu_cli_argv() == [sys.executable]


@pytest.mark.smoke
def test_pengu_cli_argv_from_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PENGU_BIN", raising=False)
    monkeypatch.setattr(pp, "__file__", "/tmp/not-a-source-checkout.py")
    monkeypatch.setattr(pp.shutil, "which", lambda name: "/opt/bin/pengu")
    assert pp._pengu_cli_argv() == ["/opt/bin/pengu"]


@pytest.mark.smoke
def test_pengu_cli_argv_not_found_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PENGU_BIN", raising=False)
    monkeypatch.setattr(pp, "__file__", "/tmp/not-a-source-checkout.py")
    monkeypatch.setattr(pp.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="PENGU_BIN"):
        pp._pengu_cli_argv()


# ---------------------------------------------------------------------------
# _run_dependency_build discovery
# ---------------------------------------------------------------------------


def _dep_with_build_pengu(tmp_path: Path) -> Path:
    dep = tmp_path / "dep"
    _write(dep / "build.pengu", "## build script\n")
    return dep


@pytest.mark.smoke
def test_run_dependency_build_prefers_build_pengu(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dep = _dep_with_build_pengu(tmp_path)
    legacy_marker = dep / "build_py_ran"
    _write(dep / "build.py", f"""
        from pathlib import Path
        Path({str(legacy_marker)!r}).write_text("ran")
    """)
    log = _fake_cli(monkeypatch, tmp_path)

    assert pp._run_dependency_build(str(dep), "dep", trusted=True) is True
    line = log.read_text(encoding="utf-8").strip()
    assert line.startswith("run ")
    assert line.endswith("build.pengu")
    assert not legacy_marker.exists(), "build.py must not run when build.pengu exists"
    assert "legacy build script" not in capsys.readouterr().out


@pytest.mark.smoke
def test_run_dependency_build_falls_back_to_py(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dep = tmp_path / "dep"
    marker = dep / "build_py_ran"
    _write(dep / "build.py", f"""
        from pathlib import Path
        Path({str(marker)!r}).write_text("ran")
    """)
    assert pp._run_dependency_build(str(dep), "dep", trusted=True) is True
    assert marker.read_text() == "ran"
    assert "legacy build script (build.py)" in capsys.readouterr().out


@pytest.mark.smoke
def test_run_dependency_build_force_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dep = _dep_with_build_pengu(tmp_path)
    log = _fake_cli(monkeypatch, tmp_path)
    assert pp._run_dependency_build(str(dep), "dep", trusted=True, force=True) is True
    line = log.read_text(encoding="utf-8").strip()
    assert line.endswith("-- --force")


@pytest.mark.smoke
def test_run_dependency_build_missing_runtime(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dep = _dep_with_build_pengu(tmp_path)
    monkeypatch.setattr(pp, "_find_runtime_archive", lambda target_os="": None)

    assert pp._run_dependency_build(str(dep), "dep", trusted=True) is False
    err = capsys.readouterr().err
    assert "libpengu_runtime.a not found" in err
    assert "build_runtime.py" in err


@pytest.mark.smoke
def test_run_dependency_build_missing_pengu(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dep = _dep_with_build_pengu(tmp_path)
    monkeypatch.setattr(pp, "_find_runtime_archive", lambda target_os="": str(tmp_path / "runtime.a"))
    monkeypatch.setenv("PENGU_BIN", str(tmp_path / "does-not-exist" / "pengu"))
    monkeypatch.delenv("PENGU_TRUST_ALL", raising=False)

    # Must warn and return False, never raise.
    assert pp._run_dependency_build(str(dep), "dep", trusted=True) is False
    assert "could not execute the build script" in capsys.readouterr().err


@pytest.mark.smoke
def test_run_dependency_build_requires_trust(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dep = _dep_with_build_pengu(tmp_path)
    log = _fake_cli(monkeypatch, tmp_path)
    monkeypatch.delenv("PENGU_TRUST_ALL", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    assert pp._run_dependency_build(str(dep), "dep", trusted=False) is False
    assert not log.exists() or log.read_text(encoding="utf-8") == ""
    assert "pass --trust" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# add / update integration
# ---------------------------------------------------------------------------


@needs_toolchain
def test_add_dependency_runs_build_pengu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pp.init_project(name="demo", template="cbind", target_dir=str(tmp_path / "src"))
    binding = tmp_path / "src" / "demo"
    (binding / "lib" / "libdemo.a").unlink(missing_ok=True)

    pp.init_project(name="app", template="exe", target_dir=str(tmp_path / "consumer"))
    consumer = tmp_path / "consumer" / "app"
    monkeypatch.chdir(consumer)

    installed = pp.add_dependency(str(binding), trusted=True)

    assert Path(installed) == consumer / "lib" / "demo"
    assert (consumer / "lib" / "demo" / "lib" / "libdemo.a").is_file()
    # The build script stays at the root (it is not an importable module).
    assert (consumer / "lib" / "demo" / "build.pengu").is_file()
    assert not (consumer / "lib" / "demo" / "pengu" / "build.pengu").exists()


def test_add_dependency_existing_repo_forces_rebuild(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    origin = tmp_path / "origin" / "demo"
    _write(origin / "build.pengu", "## build script\n")
    _write(origin / "pengu.toml", '[project]\nname = "demo"\nversion = "0.1.0"\nentry = "build.pengu"\n')
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test",
         "commit", "-q", "-m", "init"],
    ):
        subprocess.run(cmd, cwd=origin, check=True, capture_output=True)

    log = _fake_cli(monkeypatch, tmp_path)
    pp.init_project(name="app", template="exe", target_dir=str(tmp_path / "consumer"))
    consumer = tmp_path / "consumer" / "app"
    monkeypatch.chdir(consumer)

    pp.add_dependency(origin.as_uri(), trusted=True)
    first = log.read_text(encoding="utf-8").splitlines()
    assert len(first) == 1
    assert "--force" not in first[0]

    # Re-adding pulls (already up to date still returns 0) and must force the
    # build, because the checkout was refreshed.
    pp.add_dependency(origin.as_uri(), trusted=True)
    second = log.read_text(encoding="utf-8").splitlines()
    assert len(second) == 2, second
    assert second[1].endswith("-- --force")


def test_update_trusted_forces_rebuild(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log = _fake_cli(monkeypatch, tmp_path)
    pp.init_project(name="app", template="exe", target_dir=str(tmp_path / "consumer"))
    consumer = tmp_path / "consumer" / "app"
    monkeypatch.chdir(consumer)
    dep = consumer / "lib" / "logdep"
    _write(dep / "build.pengu", "## build script\n")
    pp._update_config_dependency(str(consumer), "logdep", str(tmp_path / "origin"), None)

    pp.update_project(config_path=str(consumer), trusted=True)
    first = log.read_text(encoding="utf-8").splitlines()
    assert len(first) == 1
    assert first[0].endswith("-- --force")

    # --no-build: the script must not run again.
    pp.update_project(config_path=str(consumer), trusted=True, rebuild=False)
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1


def test_transitive_dependency_is_not_built(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """B10: `add` builds the direct dependency once, never transitive scripts."""
    child = tmp_path / "child"
    _write(child / "build.pengu", "## child build\n")
    parent = tmp_path / "parent"
    _write(parent / "build.pengu", "## parent build\n")
    _write(parent / "pengu.toml", f'''
        [project]
        name = "parent"
        version = "0.1.0"
        entry = "build.pengu"

        [dependencies]
        child = {{ url = {str(child)!r} }}
    ''')

    log = _fake_cli(monkeypatch, tmp_path)
    pp.init_project(name="app", template="exe", target_dir=str(tmp_path / "consumer"))
    consumer = tmp_path / "consumer" / "app"
    monkeypatch.chdir(consumer)

    pp.add_dependency(str(parent), trusted=True)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, lines
    assert "parent" in lines[0]
    assert (consumer / "lib" / "child" / "build.pengu").is_file()

    # Explicitly adding the transitive dependency runs its script.
    pp.add_dependency(str(child), trusted=True)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, lines
    assert "child" in lines[1]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_init_cbind_emits_build_pengu(tmp_path: Path) -> None:
    pp.init_project(name="foo", template="cbind", target_dir=str(tmp_path))
    binding = tmp_path / "foo"
    assert (binding / "build.pengu").is_file()
    assert not (binding / "build.py").exists()
    text = (binding / "build.pengu").read_text(encoding="utf-8")
    assert 'const BINDING_NAME as string is "foo"' in text
    assert "pengu run build.pengu -- --force" in text


@pytest.mark.smoke
def test_init_pengu_lib_emits_build_pengu(tmp_path: Path) -> None:
    pp.init_project(name="foo", template="pengu-lib", target_dir=str(tmp_path))
    lib = tmp_path / "foo"
    assert (lib / "build.pengu").is_file()
    for sub in ("c", "include", "lib"):
        assert (lib / sub).is_dir(), sub
    text = (lib / "build.pengu").read_text(encoding="utf-8")
    assert 'const LIBRARY_NAME as string is "foo"' in text


@pytest.mark.smoke
def test_add_dependency_rejects_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B9: `--name ..` must not create lib/../.."""
    pp.init_project(name="app", template="exe", target_dir=str(tmp_path / "consumer"))
    consumer = tmp_path / "consumer" / "app"
    monkeypatch.chdir(consumer)
    with pytest.raises(ValueError, match="outside"):
        pp.add_dependency(str(tmp_path), name="..", run_build=False)
    # The rejection happened before the copy: lib/ is still empty.
    assert list((consumer / "lib").iterdir()) == []


@pytest.mark.smoke
def test_rmtree_ignore_errors_handles_readonly(tmp_path: Path) -> None:
    """B8: read-only trees (a Windows git checkout) must not break rollback."""
    victim = tmp_path / "tree"
    (victim / "objects").mkdir(parents=True)
    lock = victim / "objects" / "pack"
    lock.write_text("x")
    # A git checkout marks files, not their directories, read-only.
    lock.chmod(0o444)
    try:
        pp._rmtree_ignore_errors(str(victim))
    finally:
        if victim.exists():
            victim.chmod(0o755)
    assert not victim.exists()


# ---------------------------------------------------------------------------
# The generated build.pengu really compiles
# ---------------------------------------------------------------------------


def _run_build(binding: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "run", "build.pengu", *extra],
        cwd=binding, capture_output=True, text=True, timeout=300,
    )


@needs_toolchain
def test_build_pengu_compiles_toy_source(tmp_path: Path) -> None:
    pp.init_project(name="foo", template="cbind", target_dir=str(tmp_path))
    binding = tmp_path / "foo"
    result = _run_build(binding)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (binding / "lib" / "libfoo.a").is_file()
    assert "compilando c/foo.c" in result.stdout


@needs_toolchain
def test_build_pengu_force_rebuilds(tmp_path: Path) -> None:
    pp.init_project(name="foo", template="cbind", target_dir=str(tmp_path))
    binding = tmp_path / "foo"
    assert _run_build(binding).returncode == 0

    skipped = _run_build(binding)
    assert skipped.returncode == 0
    assert "ya existe" in skipped.stdout

    forced = _run_build(binding, "--", "--force")
    assert forced.returncode == 0, forced.stdout + forced.stderr
    assert "compilando c/foo.c" in forced.stdout


@needs_toolchain
def test_build_pengu_no_sources(tmp_path: Path) -> None:
    pp.init_project(name="foo", template="pengu-lib", target_dir=str(tmp_path))
    result = _run_build(tmp_path / "foo")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nada que compilar" in result.stdout


@needs_toolchain
def test_build_pengu_respects_cc_env(tmp_path: Path) -> None:
    """`CC=...` may be an absolute path, which `rites.which` does not accept."""
    pp.init_project(name="foo", template="cbind", target_dir=str(tmp_path))
    binding = tmp_path / "foo"
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    env = dict(os.environ, CC=cc)
    result = subprocess.run(
        [sys.executable, str(CLI), "run", "build.pengu"],
        cwd=binding, capture_output=True, text=True, timeout=300, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (binding / "lib" / "libfoo.a").is_file()
