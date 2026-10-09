"""Roadmap Phase 4 / §4.6 (vendor/offline) and §4.7 (global dependency cache)."""

import os
import subprocess

import pytest

from pengu_project import (
    ProjectConfig,
    _dep_cache_key,
    _dep_cache_key_for,
    _dep_cache_root,
    _local_source_revision,
    add_dependency,
    build_project,
    init_project,
    upgrade_dependency,
    vendor_dependencies,
)
from pengu_lock import read_lock
from tests.conftest import have_tool, remove_tree

requires_git = pytest.mark.skipif(not have_tool("git"), reason="git not available")


def _git(repo, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, capture_output=True, text=True,
    )


def _rev(repo):
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


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


def test_cache_key_is_deterministic_and_branch_sensitive(tmp_path):
    assert _dep_cache_key("https://x/a.git", None) == _dep_cache_key("https://x/a.git", None)
    assert _dep_cache_key("https://x/a.git", None) != _dep_cache_key("https://x/a.git", "dev")
    assert _dep_cache_key("https://x/a.git", None) != _dep_cache_key("https://x/b.git", None)


def test_cache_root_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PENGU_DEP_CACHE", str(tmp_path / "c"))
    assert _dep_cache_root() == str(tmp_path / "c")
    monkeypatch.setenv("PENGU_NO_DEP_CACHE", "1")
    assert _dep_cache_root() is None
    monkeypatch.delenv("PENGU_NO_DEP_CACHE")
    monkeypatch.delenv("PENGU_DEP_CACHE")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert _dep_cache_root() == str(tmp_path / "xdg" / "pengu" / "deps")


@requires_git
def test_dependency_is_cached_and_restored(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("PENGU_DEP_CACHE", str(cache))
    repo = _make_repo(tmp_path, "dep.git")
    init_project("c_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "c_app")

    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    key = _dep_cache_key_for(repo, None)
    assert os.path.isdir(cache / key), "cache was not populated"

    # Removing lib/ and re-adding must restore from the cache, not the network.
    remove_tree(os.path.join(proj, "lib", "dep"))
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    assert os.path.isdir(os.path.join(proj, "lib", "dep"))


def test_local_source_revision_is_the_head_or_none(tmp_path):
    """The key input is resolved from the source, never guessed from the string."""
    assert _local_source_revision("https://x/a.git") is None
    assert _local_source_revision(str(tmp_path / "does-not-exist")) is None
    plain = tmp_path / "plain"
    plain.mkdir()
    assert _local_source_revision(str(plain)) is None


@requires_git
def test_changed_local_source_is_not_served_from_a_stale_cache(tmp_path, monkeypatch):
    """Roadmap 8.17 (finding F8-N1): the key follows a local source's HEAD.

    Regression test for the flaky `test_add_upgrade_remove_end_to_end`.  The cache
    was keyed by the source *string*, so a local dependency that gained a commit
    (moving its ``v1.0.0`` tag onto it) was still restored from the snapshot taken
    at the previous commit; ``pengu upgrade`` then aborted with
    ``git fetch failed … would overwrite existing tag``.  Reverting
    ``_local_source_revision`` makes the second project below receive the *first*
    commit, so the assertion on ``second`` fails.
    """
    cache = tmp_path / "cache"
    monkeypatch.setenv("PENGU_DEP_CACHE", str(cache))
    repo = _make_repo(tmp_path, "dep.git")
    first = _rev(repo)
    assert first

    init_project("a_app", output_type="exe", target_dir=str(tmp_path))
    proj_a = os.path.join(str(tmp_path), "a_app")
    add_dependency(source=repo, name="dep", config_path=proj_a, run_build=False)
    assert _rev(os.path.join(proj_a, "lib", "dep")) == first

    # The local source moves on: a new commit, with the tag moved onto it.
    with open(os.path.join(repo, "pengu", "m.pengu"), "w", encoding="utf-8") as f:
        f.write("weave m_fn into int:\n  return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "second")
    _git(repo, "tag", "-f", "v1.0.0")
    second = _rev(repo)
    assert second != first

    # A brand-new project must see the *new* state, not the cached snapshot.
    init_project("b_app", output_type="exe", target_dir=str(tmp_path))
    proj_b = os.path.join(str(tmp_path), "b_app")
    add_dependency(source=repo, name="dep", config_path=proj_b, run_build=False)
    assert _rev(os.path.join(proj_b, "lib", "dep")) == second, (
        "the stale cached snapshot was restored"
    )

    # ...and the upgrade path that used to explode now succeeds.
    upgrade_dependency("dep", version="v1.0.0", config_path=proj_b)
    assert _rev(os.path.join(proj_b, "lib", "dep")) == second


@requires_git
def test_vendor_and_offline_frozen_build(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_DEP_CACHE", str(tmp_path / "cache"))
    repo = _make_repo(tmp_path, "dep.git")
    init_project("v_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "v_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)

    # Generate the lock first (build writes it).
    build_project(config_path=proj, output=os.path.join(proj, "b.c"))
    vendor_dependencies(ProjectConfig.load(proj))

    vendor = os.path.join(proj, "vendor")
    assert os.path.isdir(os.path.join(vendor, "dep"))
    assert os.path.isfile(os.path.join(vendor, "pengu.lock"))
    assert os.path.isfile(os.path.join(vendor, "README.md"))
    # Build outputs are not vendored.
    assert not os.path.isdir(os.path.join(vendor, "dep", "build"))

    # Fresh-clone simulation: no lib/, no network, --frozen must restore+verify.
    remove_tree(os.path.join(proj, "lib"))
    build_project(config_path=proj, output=os.path.join(proj, "b.c"), frozen=True)
    assert os.path.isdir(os.path.join(proj, "lib", "dep"))

    lock = read_lock(proj)
    assert [p.name for p in lock.packages] == ["dep"]


@requires_git
def test_vendor_preserves_git_for_upgrade(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_DEP_CACHE", str(tmp_path / "cache"))
    repo = _make_repo(tmp_path, "dep.git")
    init_project("vg_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "vg_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    vendor_dependencies(ProjectConfig.load(proj))
    assert os.path.isdir(os.path.join(proj, "vendor", "dep", ".git"))
