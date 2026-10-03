"""Roadmap Phase 5 / §5.3 — supply-chain security.

Covers `pengu verify` (lockfile integrity), the binding preprocessor sandbox and
the trust gate for dependency build scripts (the last one lives in
tests/test_phase5_bugfixes.py).
"""

import os
import shutil
import subprocess
import tomllib

import pytest

from pengu_project import (
    ProjectConfig,
    add_dependency,
    build_project,
    init_project,
    verify_project,
)
from tests.conftest import REPO, have_tool

requires_git = pytest.mark.skipif(not have_tool("git"), reason="git not available")


def _git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, capture_output=True, text=True,
    )


def _make_repo(base, name, tag="v1.0.0"):
    repo = os.path.join(str(base), name)
    os.makedirs(os.path.join(repo, "pengu"), exist_ok=True)
    with open(os.path.join(repo, "pengu", "m.pengu"), "w", encoding="utf-8") as f:
        f.write("weave m_fn into int:\n  return 1\n")
    with open(os.path.join(repo, "pengu.toml"), "w", encoding="utf-8") as f:
        f.write(f'[project]\nname = "{name}"\n\n[dependencies]\n')
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    if tag:
        _git(repo, "tag", tag)
    return repo


# --------------------------------------------------------------------------- #
# pengu verify
# --------------------------------------------------------------------------- #


def test_verify_requires_a_lockfile(tmp_path, capsys):
    init_project("nv_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "nv_app")
    assert verify_project(config_path=proj) == 1
    assert "pengu.lock" in capsys.readouterr().err


@requires_git
def test_verify_passes_on_a_good_lock(tmp_path, capsys):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("v_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "v_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    build_project(config_path=proj, output=os.path.join(proj, "b.c"))

    assert verify_project(config_path=proj, verbose=True) == 0
    assert "Verified" in capsys.readouterr().out


@requires_git
def test_verify_detects_content_tampering(tmp_path, capsys):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("t_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "t_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    build_project(config_path=proj, output=os.path.join(proj, "b.c"))

    with open(os.path.join(proj, "lib", "dep", "pengu", "m.pengu"), "a", encoding="utf-8") as f:
        f.write("\n# tampered\n")

    assert verify_project(config_path=proj) == 1
    assert "sha256" in capsys.readouterr().err


@requires_git
def test_verify_detects_a_missing_dependency(tmp_path, capsys):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("m_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "m_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    build_project(config_path=proj, output=os.path.join(proj, "b.c"))

    shutil.rmtree(os.path.join(proj, "lib", "dep"))
    assert verify_project(config_path=proj) == 1
    assert "not installed" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Binding preprocessor sandbox
# --------------------------------------------------------------------------- #


def _bind(header_path, **kw):
    from pengu_bind import generate_bind_file

    return generate_bind_file(str(header_path), output=str(header_path) + ".d.pengu", **kw)


def test_absolute_include_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("PENGU_ALLOW_ABSOLUTE_INCLUDES", raising=False)
    header = tmp_path / "evil.h"
    header.write_text('#include "/etc/passwd"\nint foo(void);\n', encoding="utf-8")
    with pytest.raises(Exception) as exc:
        _bind(header)
    assert "absolute #include" in str(exc.value)


def test_windows_drive_include_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("PENGU_ALLOW_ABSOLUTE_INCLUDES", raising=False)
    header = tmp_path / "evil2.h"
    header.write_text('#include "C:\\\\Windows\\\\system.ini"\nint foo(void);\n', encoding="utf-8")
    with pytest.raises(Exception):
        _bind(header)


def test_parent_escaping_include_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("PENGU_ALLOW_ABSOLUTE_INCLUDES", raising=False)
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "secret.h").write_text("int secret;\n", encoding="utf-8")
    header = sub / "evil.h"
    header.write_text('#include "../secret.h"\nint foo(void);\n', encoding="utf-8")
    with pytest.raises(Exception) as exc:
        _bind(header)
    assert "escapes the header directory" in str(exc.value)


def test_allow_absolute_includes_opt_out(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_ALLOW_ABSOLUTE_INCLUDES", "1")
    header = tmp_path / "ok.h"
    header.write_text("int foo(void);\n", encoding="utf-8")
    out = _bind(header)
    assert os.path.isfile(out)


def test_sibling_include_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("PENGU_ALLOW_ABSOLUTE_INCLUDES", raising=False)
    (tmp_path / "dep.h").write_text("typedef int my_int;\n", encoding="utf-8")
    header = tmp_path / "main.h"
    header.write_text('#include "dep.h"\nmy_int foo(void);\n', encoding="utf-8")
    out = _bind(header)
    assert os.path.isfile(out)


def test_sandbox_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_NO_SANDBOX", "1")
    header = tmp_path / "plain.h"
    header.write_text("int foo(void);\n", encoding="utf-8")
    assert os.path.isfile(_bind(header))


def test_bwrap_prefix_is_well_formed():
    from pengu_bind import _sandbox_prefix

    prefix = _sandbox_prefix(["/tmp"])
    if not prefix:
        pytest.skip("bwrap not available")
    assert prefix[0].endswith("bwrap")
    assert "--unshare-net" in prefix
    assert prefix[-1] == "--"
    assert prefix.count("--ro-bind") >= 2


# --------------------------------------------------------------------------- #
# SECURITY.md
# --------------------------------------------------------------------------- #


def test_security_policy_document_exists():
    text = (REPO / "SECURITY.md").read_text(encoding="utf-8")
    for needle in ("Reporting a vulnerability", "90 days", "Supported versions",
                   "Patch SLAs", "Scope"):
        assert needle in text, needle
