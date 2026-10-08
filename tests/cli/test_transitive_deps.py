"""Roadmap Phase 4 / §4.2 (transitive deps, SemVer in the manifest) and
§4.8 (`pengu tree` / `pengu metadata`)."""

import json
import os
import subprocess
import tomllib

import pytest

from pengu_project import (
    DependencyConflictError,
    ProjectConfig,
    add_dependency,
    init_project,
    print_dependency_tree,
    resolve_transitive_dependencies,
)
from pengu_semver import Version, parse_constraint, satisfies
from tests.conftest import have_tool

requires_git = pytest.mark.skipif(not have_tool("git"), reason="git not available")


def _git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, capture_output=True, text=True,
    )


def _make_repo(base, name, deps=None, tag="v1.0.0"):
    """Creates a git dependency repo; `deps` is a manifest-deps text block."""
    repo = os.path.join(str(base), name)
    os.makedirs(os.path.join(repo, "pengu"), exist_ok=True)
    with open(os.path.join(repo, "pengu", "mod.pengu"), "w", encoding="utf-8") as f:
        f.write(f"weave {name.split('.')[0]}_fn into int:\n  return 1\n")
    manifest = f'[project]\nname = "{name}"\n\n[dependencies]\n'
    if deps:
        manifest += deps + "\n"
    with open(os.path.join(repo, "pengu.toml"), "w", encoding="utf-8") as f:
        f.write(manifest)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    if tag:
        _git(repo, "tag", tag)
    return repo


def _project(tmp_path, name="app"):
    init_project(name, output_type="exe", target_dir=str(tmp_path))
    return ProjectConfig.load(os.path.join(str(tmp_path), name))


@requires_git
def test_transitive_dependency_is_installed(tmp_path):
    leaf = _make_repo(tmp_path, "leaf.git")
    parent = _make_repo(tmp_path, "parent.git", deps=(
        f'[dependencies.leaf]\nurl = "{leaf}"\nversion = "^1.0.0"\n'
    ))
    cfg = _project(tmp_path)
    add_dependency(source=parent, name="parent", config_path=cfg.base_dir, run_build=False)

    lib = os.path.join(cfg.base_dir, "lib")
    assert os.path.isdir(os.path.join(lib, "parent"))
    assert os.path.isdir(os.path.join(lib, "leaf")), "transitive dep was not installed"

    # Only the direct dependency belongs to the root manifest.
    data = tomllib.loads(open(os.path.join(cfg.base_dir, "pengu.toml"), encoding="utf-8").read())
    assert set(data["dependencies"]) == {"parent"}


@requires_git
def test_resolve_graph_shape(tmp_path):
    leaf = _make_repo(tmp_path, "leaf.git")
    parent = _make_repo(tmp_path, "parent.git", deps=(
        f'[dependencies.leaf]\nurl = "{leaf}"\nversion = "^1.0.0"\n'
    ))
    cfg = _project(tmp_path)
    add_dependency(source=parent, name="parent", config_path=cfg.base_dir, run_build=False)

    graph = resolve_transitive_dependencies(cfg, install_missing=False)
    assert set(graph) == {"parent", "leaf"}
    assert graph["parent"].children == ["leaf"]
    assert graph["parent"].required_by == ["<root>"]
    assert graph["leaf"].required_by == ["parent"]
    assert graph["leaf"].resolved_version == "1.0.0"
    assert graph["leaf"].commit


@requires_git
def test_version_conflict_rolls_back(tmp_path):
    leaf = _make_repo(tmp_path, "leaf.git")  # only v1.0.0 exists
    parent = _make_repo(tmp_path, "parent.git", deps=(
        f'[dependencies.leaf]\nurl = "{leaf}"\nversion = "^1.0.0"\n'
    ))
    other = _make_repo(tmp_path, "other.git", deps=(
        f'[dependencies.leaf]\nurl = "{leaf}"\nversion = "^2.0.0"\n'
    ))
    cfg = _project(tmp_path)
    add_dependency(source=parent, name="parent", config_path=cfg.base_dir, run_build=False)

    with pytest.raises(DependencyConflictError) as exc:
        add_dependency(source=other, name="other", config_path=cfg.base_dir, run_build=False)
    msg = str(exc.value)
    assert "leaf" in msg and "^1.0.0" in msg and "^2.0.0" in msg

    # Rollback: neither the directory nor the manifest entry survive.
    assert not os.path.isdir(os.path.join(cfg.base_dir, "lib", "other"))
    data = tomllib.loads(open(os.path.join(cfg.base_dir, "pengu.toml"), encoding="utf-8").read())
    assert set(data["dependencies"]) == {"parent"}


@requires_git
def test_cycle_terminates(tmp_path):
    a = os.path.join(str(tmp_path), "cyc_a.git")
    b = os.path.join(str(tmp_path), "cyc_b.git")
    _make_repo(tmp_path, "cyc_a.git", deps=(
        f'[dependencies.cyc_b]\nurl = "{b}"\n'
    ))
    _make_repo(tmp_path, "cyc_b.git", deps=(
        f'[dependencies.cyc_a]\nurl = "{a}"\n'
    ))
    cfg = _project(tmp_path)
    add_dependency(source=a, name="cyc_a", config_path=cfg.base_dir, run_build=False)
    graph = resolve_transitive_dependencies(cfg, install_missing=False)
    assert "cyc_a" in graph and "cyc_b" in graph


@requires_git
def test_print_tree_and_metadata(tmp_path, capsys):
    leaf = _make_repo(tmp_path, "leaf.git")
    parent = _make_repo(tmp_path, "parent.git", deps=(
        f'[dependencies.leaf]\nurl = "{leaf}"\nversion = "^1.0.0"\n'
    ))
    cfg = _project(tmp_path)
    add_dependency(source=parent, name="parent", config_path=cfg.base_dir, run_build=False)

    assert print_dependency_tree(cfg, as_json=False) == 0
    out = capsys.readouterr().out
    assert "parent" in out and "leaf" in out

    assert print_dependency_tree(cfg, as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    names = {d["name"] for d in payload["dependencies"]}
    assert names == {"parent", "leaf"}
    leaf_entry = next(d for d in payload["dependencies"] if d["name"] == "leaf")
    assert leaf_entry["required_by"] == ["parent"]
    assert leaf_entry["version"] == "1.0.0"


def test_manifest_version_constraint_is_read(tmp_path):
    (tmp_path / "pengu.toml").write_text(
        '[project]\nname = "x"\n\n[dependencies.foo]\nurl = "https://x/foo.git"\nversion = "^1.2.0"\n',
        encoding="utf-8",
    )
    from pengu_project import _read_config_dependency

    entry = _read_config_dependency(str(tmp_path), "foo")
    assert entry["version"] == "^1.2.0"
    assert satisfies(Version.parse("1.5.0"), parse_constraint(entry["version"]))


def test_no_dependencies_graph_is_empty(tmp_path):
    cfg = _project(tmp_path, "empty")
    assert resolve_transitive_dependencies(cfg, install_missing=False) == {}
    assert print_dependency_tree(cfg) == 0
