"""Roadmap Phase 6 / §6.0 — residual Phase 5 bugs (verified against the code).

Findings that the audit got wrong are recorded as refutation tests.
"""

import os
import subprocess

import pytest

from pengu_project import (
    PenguBuilder,
    ProjectConfig,
    add_dependency,
    build_project,
    init_project,
    run_script,
    verify_project,
)
from pengu_lock import read_lock
from tests.conftest import have_tool, requires_cc, requires_runtime

requires_git = pytest.mark.skipif(not have_tool("git"), reason="git not available")

DEPRECATED = (
    '@deprecated("use new_fn instead")\n'
    "weave old_fn into int:\n"
    "  return 1\n\n"
    "weave main into int:\n"
    "  return calling old_fn\n"
)


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
# BUG-6.1 — --locked must fail when pengu.lock is missing
# --------------------------------------------------------------------------- #


@requires_git
def test_locked_without_lockfile_fails(tmp_path, capsys):
    """A project WITH dependencies and no lock must fail under --locked."""
    repo = _make_repo(tmp_path, "dep.git")
    init_project("l_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "l_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    assert not os.path.isfile(os.path.join(proj, "pengu.lock"))
    with pytest.raises(SystemExit) as exc:
        build_project(config_path=proj, output=os.path.join(proj, "b.c"), locked=True)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "E0061" in err and "--locked" in err


@requires_git
def test_frozen_without_lockfile_still_fails(tmp_path, capsys):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("f_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "f_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    with pytest.raises(SystemExit):
        build_project(config_path=proj, output=os.path.join(proj, "b.c"), frozen=True)
    err = capsys.readouterr().err
    assert "E0061" in err and "--frozen" in err


def test_dependency_free_project_needs_no_lock(tmp_path):
    """Nothing to resolve => no lock required (documented behaviour)."""
    init_project("none_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "none_app")
    build_project(config_path=proj, output=os.path.join(proj, "b.c"), locked=True,
                  frozen=True)
    assert not os.path.isfile(os.path.join(proj, "pengu.lock"))


@requires_git
def test_locked_passes_once_the_lock_exists(tmp_path):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("ok_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "ok_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    out = os.path.join(proj, "b.c")
    build_project(config_path=proj, output=out)          # writes the lock
    assert os.path.isfile(os.path.join(proj, "pengu.lock"))
    build_project(config_path=proj, output=out, locked=True)
    build_project(config_path=proj, output=out, frozen=True)


# --------------------------------------------------------------------------- #
# BUG-6.2 — the script cache key must include --release-unsafe
# --------------------------------------------------------------------------- #


def test_script_cache_key_includes_release_unsafe(tmp_path, monkeypatch):
    if not (have_tool("gcc") or have_tool("clang")):
        pytest.skip("no C compiler")
    script = tmp_path / "s.pengu"
    script.write_text("weave main into int:\n  return 0\n", encoding="utf-8")

    captured = []
    import pengu_project as P

    real = P.script_cache_key

    def _capture(*a, **kw):
        captured.append(kw)
        return real(*a, **kw)

    monkeypatch.setattr(P, "script_cache_key", _capture)

    try:
        run_script(str(script), release_unsafe=False, keep=True, no_cache=False)
    except SystemExit:
        pass
    except Exception:
        pass
    try:
        run_script(str(script), release_unsafe=True, keep=True, no_cache=False)
    except SystemExit:
        pass
    except Exception:
        pass

    assert len(captured) >= 2, "script_cache_key was not called twice"
    digests = [tuple(kw.get("extra_digests") or ()) for kw in captured]
    assert any("release-unsafe" in d for d in digests), digests
    assert digests[0] != digests[1], "release_unsafe did not change the cache key"


# --------------------------------------------------------------------------- #
# BUG-6.3 — one check pass for --deny-deprecated
# --------------------------------------------------------------------------- #


def test_diagnostics_are_memoised_per_builder(tmp_path):
    proj = tmp_path / "mem_app"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.pengu").write_text(DEPRECATED, encoding="utf-8")
    (proj / "pengu.toml").write_text(
        '[project]\nname = "mem"\nentry = "src/main.pengu"\n', encoding="utf-8"
    )
    builder = PenguBuilder(ProjectConfig.load(str(proj)))
    calls = {"n": 0}
    real_parse = builder.parser.parse

    def _counting_parse(*a, **kw):
        calls["n"] += 1
        return real_parse(*a, **kw)

    builder.parser.parse = _counting_parse
    first = builder.check_sources_diagnostics()
    after_first = calls["n"]
    second = builder.check_sources_diagnostics()
    assert after_first > 0
    assert calls["n"] == after_first, "second call re-parsed the sources"
    assert first[0] == second[0]


def test_build_with_deny_deprecated_uses_one_builder(tmp_path):
    """The gate must not construct a throwaway builder (roadmap 6.0.c)."""
    proj = tmp_path / "one_app"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.pengu").write_text(DEPRECATED, encoding="utf-8")
    (proj / "pengu.toml").write_text(
        '[project]\nname = "one"\nentry = "src/main.pengu"\n', encoding="utf-8"
    )
    import pengu_project as P

    constructed = []
    real = P.PenguBuilder

    class _Spy(real):
        def __init__(self, *a, **kw):
            constructed.append(1)
            super().__init__(*a, **kw)

    P.PenguBuilder = _Spy
    try:
        with pytest.raises(SystemExit):
            build_project(config_path=str(proj), output=str(proj / "b.c"),
                          deny_deprecated=True)
    finally:
        P.PenguBuilder = real
    assert len(constructed) == 1, f"built {len(constructed)} builders"


# --------------------------------------------------------------------------- #
# BUG-6.9 — verify compares the git origin URL
# --------------------------------------------------------------------------- #


@requires_git
def test_verify_detects_a_changed_origin(tmp_path, capsys):
    repo = _make_repo(tmp_path, "dep.git")
    init_project("o_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "o_app")
    add_dependency(source=repo, name="dep", config_path=proj, run_build=False)
    build_project(config_path=proj, output=os.path.join(proj, "b.c"))
    assert verify_project(config_path=proj) == 0

    other = _make_repo(tmp_path, "other.git")
    dep_dir = os.path.join(proj, "lib", "dep")
    _git(dep_dir, "remote", "set-url", "origin", other)
    assert verify_project(config_path=proj) == 1
    assert "origin" in capsys.readouterr().err


@requires_git
def test_verify_tolerates_git_suffix_and_trailing_slash(tmp_path):
    from pengu_project import _same_source

    assert _same_source("https://x/y.git", "https://x/y")
    assert _same_source("https://x/y/", "https://x/y")
    assert _same_source("/tmp/A.git", "/tmp/a")
    assert not _same_source("https://x/y.git", "https://x/z.git")


# --------------------------------------------------------------------------- #
# BUG-6.10 — run_script honours --deny-deprecated
# --------------------------------------------------------------------------- #


@requires_cc
@requires_runtime
def test_run_script_deny_deprecated_fails(tmp_path, capsys):
    script = tmp_path / "dep_script.pengu"
    script.write_text(DEPRECATED, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        run_script(str(script), deny_deprecated=True, keep=True)
    assert exc.value.code == 1
    assert "W0006" in capsys.readouterr().err


@requires_cc
@requires_runtime
def test_run_script_without_deny_deprecated_succeeds(tmp_path):
    script = tmp_path / "ok_script.pengu"
    script.write_text(DEPRECATED, encoding="utf-8")
    # The script returns old_fn() == 1; what matters is that the build ran.
    assert run_script(str(script), keep=True) in (0, 1)


# --------------------------------------------------------------------------- #
# BUG-6.12 — the incbin threshold invalidates the artifact fingerprint
# --------------------------------------------------------------------------- #


def test_incbin_threshold_invalidates_the_fingerprint(tmp_path, monkeypatch):
    proj = tmp_path / "assets_app"
    (proj / "src").mkdir(parents=True)
    (proj / "assets").mkdir()
    (proj / "src" / "main.pengu").write_text("weave main into int:\n  return 0\n", encoding="utf-8")
    (proj / "assets" / "blob.bin").write_bytes(b"x" * 4096)
    (proj / "pengu.toml").write_text(
        '[project]\nname = "a"\nentry = "src/main.pengu"\n\n[build]\nassets_embed = true\n',
        encoding="utf-8",
    )
    cfg = ProjectConfig.load(str(proj))
    assert cfg.assets_embed

    monkeypatch.setenv("PENGU_ASSETS_INCBIN_THRESHOLD", "100")
    small = PenguBuilder(ProjectConfig.load(str(proj)))
    small.generate_assets()
    fp_small = small.compute_sources_fingerprint(["main"])

    monkeypatch.setenv("PENGU_ASSETS_INCBIN_THRESHOLD", "1000000")
    big = PenguBuilder(ProjectConfig.load(str(proj)))
    big.generate_assets()
    fp_big = big.compute_sources_fingerprint(["main"])

    assert fp_small != fp_big, "threshold change did not invalidate the fingerprint"


def test_assets_digest_already_includes_the_threshold():
    """Refutation of the audit's framing: pengu_assets does include it."""
    from tests.conftest import REPO

    text = (REPO / "pengu_assets.py").read_text(encoding="utf-8")
    assert "incbin={getattr(cfg, 'incbin_threshold', 0) or 0}" in text
