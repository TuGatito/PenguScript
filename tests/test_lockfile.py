"""Roadmap Phase 4 / §4.1 — pengu.lock: pinning, checksums and --locked/--frozen."""

import os
import subprocess

import pytest

from pengu_lock import (
    LockedPackage,
    LockFile,
    build_lock_from_graph,
    compute_tree_hash,
    diff_locks,
    dumps,
    read_lock,
    write_lock,
)
from pengu_project import (
    ProjectConfig,
    add_dependency,
    build_project,
    init_project,
)
from tests.conftest import have_tool

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


def _project_with_dep(tmp_path):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("lock_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "lock_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    return ProjectConfig.load(proj), repo


# --------------------------------------------------------------------------- pure


def test_tree_hash_is_deterministic_and_content_sensitive(tmp_path):
    root = tmp_path / "dep"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("hello", encoding="utf-8")
    (root / "sub" / "b.txt").write_text("world", encoding="utf-8")
    h1 = compute_tree_hash(str(root))
    assert h1 == compute_tree_hash(str(root))
    (root / "a.txt").write_text("HELLO", encoding="utf-8")
    assert compute_tree_hash(str(root)) != h1


def test_tree_hash_ignores_vcs_and_build_dirs(tmp_path):
    root = tmp_path / "dep"
    root.mkdir()
    (root / "keep.txt").write_text("k", encoding="utf-8")
    base = compute_tree_hash(str(root))

    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: x", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "out.o").write_bytes(b"\x00\x01")
    assert compute_tree_hash(str(root)) == base


def test_lock_round_trip(tmp_path):
    lock = LockFile(version=1, targets=["x86_64-w64-mingw32"], packages=[
        LockedPackage(name="a", source="u", constraint="^1.0.0", version="1.2.0",
                      commit="abc", sha256="dead", required_by=["<root>"], children=["b"]),
    ])
    path = write_lock(str(tmp_path), lock)
    assert os.path.basename(path) == "pengu.lock"
    back = read_lock(str(tmp_path))
    assert back is not None
    assert back.targets == ["x86_64-w64-mingw32"]
    assert back.packages[0].name == "a"
    assert back.packages[0].commit == "abc"
    assert back.packages[0].children == ["b"]


def test_diff_locks_reports_every_kind(tmp_path):
    base = LockFile(packages=[
        LockedPackage(name="a", commit="aaa", version="1.0.0", sha256="h1"),
        LockedPackage(name="gone", commit="zzz", version="1.0.0"),
    ], targets=["linux"])
    current = LockFile(packages=[
        LockedPackage(name="a", commit="bbb", version="1.0.0", sha256="h1"),
        LockedPackage(name="new", commit="ccc", version="3.0.0"),
    ], targets=["linux"])
    problems = diff_locks(base, current, target="linux")
    joined = "\n".join(problems)
    assert "'gone' is in pengu.lock but missing" in joined
    assert "'new' is not recorded" in joined
    assert "commit bbb != locked aaa" in joined

    # content hash mismatch
    current2 = LockFile(packages=[LockedPackage(name="a", commit="aaa", sha256="h2"),
                                  LockedPackage(name="gone", commit="zzz")])
    assert any("content changed" in p for p in diff_locks(base, current2))

    # target mismatch
    assert any("target" in p for p in diff_locks(base, current, target="x86_64-w64-mingw32"))


# ------------------------------------------------------------------------ end-to-end


@requires_git
def test_build_writes_lock_and_locked_passes(tmp_path):
    cfg, _ = _project_with_dep(tmp_path)
    out = os.path.join(cfg.base_dir, "b.c")
    build_project(config_path=cfg.base_dir, output=out)

    lock_path = os.path.join(cfg.base_dir, "pengu.lock")
    assert os.path.isfile(lock_path)
    lock = read_lock(cfg.base_dir)
    assert [p.name for p in lock.packages] == ["dep"]
    assert lock.packages[0].commit and lock.packages[0].sha256
    assert lock.targets

    # Verification-only modes must not fail on a fresh lock.
    build_project(config_path=cfg.base_dir, output=out, locked=True)
    build_project(config_path=cfg.base_dir, output=out, frozen=True)


@requires_git
def test_tampered_lock_fails_with_e0061(tmp_path, capsys):
    cfg, _ = _project_with_dep(tmp_path)
    out = os.path.join(cfg.base_dir, "b.c")
    build_project(config_path=cfg.base_dir, output=out)

    lock_path = os.path.join(cfg.base_dir, "pengu.lock")
    text = open(lock_path, encoding="utf-8").read()
    tampered = text.replace('commit = "', 'commit = "deadbeef', 1)
    assert tampered != text
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(tampered)

    with pytest.raises(SystemExit) as exc:
        build_project(config_path=cfg.base_dir, output=out, locked=True)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "E0061" in err


@requires_git
def test_frozen_requires_lock(tmp_path, capsys):
    cfg, _ = _project_with_dep(tmp_path)
    out = os.path.join(cfg.base_dir, "b.c")
    assert not os.path.isfile(os.path.join(cfg.base_dir, "pengu.lock"))
    with pytest.raises(SystemExit) as exc:
        build_project(config_path=cfg.base_dir, output=out, frozen=True)
    assert exc.value.code == 1
    assert "E0061" in capsys.readouterr().err


@requires_git
def test_content_change_is_detected_and_refreshed(tmp_path, capsys):
    cfg, _ = _project_with_dep(tmp_path)
    out = os.path.join(cfg.base_dir, "b.c")
    build_project(config_path=cfg.base_dir, output=out)

    dep_file = os.path.join(cfg.base_dir, "lib", "dep", "pengu", "m.pengu")
    with open(dep_file, "a", encoding="utf-8") as f:
        f.write("\n# tampered\n")

    with pytest.raises(SystemExit):
        build_project(config_path=cfg.base_dir, output=out, locked=True)
    assert "content changed" in capsys.readouterr().err

    # A normal build refreshes the lock and the tree hash.
    build_project(config_path=cfg.base_dir, output=out)
    lock = read_lock(cfg.base_dir)
    assert lock.packages[0].sha256 == compute_tree_hash(os.path.join(cfg.base_dir, "lib", "dep"))


def test_lock_from_graph_matches_packages():
    class _Node:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    graph = {
        "a": _Node(path="", source="u", constraint="*", resolved_version="1.0.0",
                   commit="c1", required_by=["<root>"], children=["b"]),
        "b": _Node(path="", source="v", constraint="^1.0.0", resolved_version="1.1.0",
                   commit="c2", required_by=["a"], children=[]),
    }
    lock = build_lock_from_graph(graph, target="linux", hash_trees=False)
    assert [p.name for p in lock.packages] == ["a", "b"]
    assert lock.packages[0].children == ["b"]
    assert lock.targets == ["linux"]
    assert 'name = "a"' in dumps(lock)
