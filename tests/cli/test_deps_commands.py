"""Roadmap Phase 4 / §4.5 — `pengu remove` and `pengu upgrade`."""

import os
import subprocess
import tomllib

import pytest

from pengu_project import (
    _read_config_dependency,
    _remove_config_dependency,
    _set_config_dependency,
    add_dependency,
    init_project,
    remove_dependency,
    upgrade_dependency,
)
from tests.conftest import have_tool

requires_git = pytest.mark.skipif(not have_tool("git"), reason="git not available")


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def _make_git_dep(base, name="dep.git", tag="v1.0.0"):
    repo = os.path.join(str(base), name)
    os.makedirs(os.path.join(repo, "pengu"), exist_ok=True)
    with open(os.path.join(repo, "pengu", "dep.pengu"), "w", encoding="utf-8") as f:
        f.write("weave dep_fn into int:\n  return 1\n")
    _git("init", "-q", cwd=repo)
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "init", cwd=repo)
    if tag:
        _git("tag", tag, cwd=repo)
    return repo


def test_remove_config_dependency_toml(tmp_path):
    init_project("p_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "p_app")
    _set_config_dependency(proj, "alpha", {"url": "https://x/a.git"})
    assert _read_config_dependency(proj, "alpha")["url"] == "https://x/a.git"
    assert _remove_config_dependency(proj, "alpha") is True
    assert _read_config_dependency(proj, "alpha") is None
    assert _remove_config_dependency(proj, "alpha") is False


def test_remove_config_dependency_yaml(tmp_path):
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: y\n  entry: src/main.pengu\n"
        "dependencies:\n  beta:\n    url: \"https://x/b.git\"\n",
        encoding="utf-8",
    )
    assert _remove_config_dependency(str(tmp_path), "beta") is True
    txt = (tmp_path / "pengu.yaml").read_text(encoding="utf-8")
    assert "beta" not in txt


def test_remove_dependency_requires_existing(tmp_path):
    init_project("r_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "r_app")
    with pytest.raises(FileNotFoundError):
        remove_dependency("ghost", config_path=proj)


def test_remove_dependency_keep_files(tmp_path):
    init_project("k_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "k_app")
    dep_dir = os.path.join(proj, "lib", "gone")
    os.makedirs(dep_dir, exist_ok=True)
    _set_config_dependency(proj, "gone", {"url": "https://x/g.git"})

    remove_dependency("gone", config_path=proj, keep_files=True)
    assert os.path.isdir(dep_dir)
    assert _read_config_dependency(proj, "gone") is None


def test_remove_dependency_deletes_dir(tmp_path):
    init_project("d_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "d_app")
    dep_dir = os.path.join(proj, "lib", "gone")
    os.makedirs(dep_dir, exist_ok=True)
    _set_config_dependency(proj, "gone", {"url": "https://x/g.git"})

    remove_dependency("gone", config_path=proj)
    assert not os.path.exists(dep_dir)


def test_upgrade_requires_git_checkout(tmp_path):
    init_project("u_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "u_app")
    dep_dir = os.path.join(proj, "lib", "local")
    os.makedirs(dep_dir, exist_ok=True)
    _set_config_dependency(proj, "local", {"url": "https://x/l.git"})
    # No .git → the helper is a no-op rather than an error.
    assert upgrade_dependency("local", config_path=proj) == dep_dir


def test_upgrade_requires_manifest_url(tmp_path):
    init_project("n_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "n_app")
    os.makedirs(os.path.join(proj, "lib", "orphan"), exist_ok=True)
    with pytest.raises(ValueError):
        upgrade_dependency("orphan", config_path=proj)


@requires_git
def test_add_upgrade_remove_end_to_end(tmp_path):
    repo = _make_git_dep(tmp_path)
    init_project("e2e_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "e2e_app")

    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    dep_dir = os.path.join(proj, "lib", "dep")
    assert os.path.isdir(os.path.join(dep_dir, ".git"))
    assert _read_config_dependency(proj, "dep")["url"] == repo

    # Upgrade to the tag recorded in the manifest.
    upgrade_dependency("dep", version="v1.0.0", config_path=proj)
    entry = _read_config_dependency(proj, "dep")
    assert entry["version"] == "v1.0.0"

    # The manifest must still be valid TOML after both writes.
    data = tomllib.loads(open(os.path.join(proj, "pengu.toml"), encoding="utf-8").read())
    assert "dep" in data["dependencies"]

    remove_dependency("dep", config_path=proj)
    assert not os.path.exists(dep_dir)
    data = tomllib.loads(open(os.path.join(proj, "pengu.toml"), encoding="utf-8").read())
    assert "dep" not in data.get("dependencies", {})
