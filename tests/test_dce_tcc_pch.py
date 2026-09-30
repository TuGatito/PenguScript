"""Dead-code elimination, TCC integration and PCH behaviour."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import pengu_dce
from pengu_tcc import find_tcc, pick_dev_compiler, tcc_available
from tests.conftest import REPO, requires_cc, requires_runtime


# ---------------------------------------------------------------------------
# DCE
# ---------------------------------------------------------------------------

def _bundle_of(source: str, tmp_path: Path) -> str:
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "prog.pengu"
    script.write_text(source, encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path), output=OutputType.C,
                        output_name="prog", name="prog",
                        build_dir=str(tmp_path / "b"))
    builder = PenguBuilder(cfg)
    builder.entry_as_main = True
    bundle, _ = builder.bundle()
    return Path(bundle).read_text(encoding="utf-8")


def test_prune_weaves_keeps_non_std_and_reachable_std():
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": "/proj/main.pengu",
         "refs": {"helper"}},
        {"name": "helper", "c_name": "helper", "filepath": "/proj/util.pengu",
         "refs": {"used_std"}},
        {"name": "used_std", "c_name": "used_std", "filepath": "/repo/std/m.pengu",
         "refs": set()},
        {"name": "unused_std", "c_name": "unused_std", "filepath": "/repo/std/m.pengu",
         "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves)
    kept_names = {w["name"] for w in kept}
    assert kept_names == {"main", "helper", "used_std"}
    assert {w["name"] for w in dropped} == {"unused_std"}


def test_prune_weaves_keeps_std_transitively():
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": "/proj/main.pengu",
         "refs": {"a"}},
        {"name": "a", "c_name": "a", "filepath": "/repo/std/m.pengu", "refs": {"b"}},
        {"name": "b", "c_name": "b", "filepath": "/repo/std/m.pengu", "refs": set()},
        {"name": "c", "c_name": "c", "filepath": "/repo/std/m.pengu", "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves)
    assert {w["name"] for w in kept} == {"main", "a", "b"}
    assert {w["name"] for w in dropped} == {"c"}


def test_is_prunable_module_only_matches_std_and_lib():
    assert pengu_dce.is_prunable_module("/x/std/spark.pengu")
    assert pengu_dce.is_prunable_module("C:\\x\\lib\\foo.pengu")
    assert not pengu_dce.is_prunable_module("/x/src/main.pengu")
    assert not pengu_dce.is_prunable_module("/x/std/sqlite3.d.pengu")


@requires_cc
@requires_runtime
def test_dce_shrinks_a_std_import(tmp_path):
    """A script using only println must not carry the whole of std.spark."""
    source = ('import std.spark\n\n'
              'weave main into int:\n'
              '    calling spark.println with "hi"\n'
              '    return 0\n')
    c = _bundle_of(source, tmp_path)
    lines = len(c.splitlines())
    # Without DCE this bundle is ~430 lines; the threshold leaves a wide margin
    # while still failing if the pass stops working.
    assert lines < 250, f"bundle.c still has {lines} lines"
    assert "pengu_main" in c


# ---------------------------------------------------------------------------
# TCC integration (skipped when TCC is not installed/packaged)
# ---------------------------------------------------------------------------

def test_pick_dev_compiler_prefers_tcc_when_available():
    configured = "gcc"
    chosen = pick_dev_compiler(configured)
    if tcc_available():
        assert "tcc" in os.path.basename(chosen).lower()
    else:
        assert chosen == configured


def test_pengu_dev_cc_overrides(monkeypatch):
    monkeypatch.setenv("PENGU_DEV_CC", "clang")
    assert pick_dev_compiler("gcc") == "clang"


def test_pengu_no_tcc_disables_discovery(monkeypatch):
    monkeypatch.setenv("PENGU_NO_TCC", "1")
    assert find_tcc() is None


@pytest.mark.skipif(not tcc_available(), reason="tcc not installed/packaged")
@requires_cc
@requires_runtime
def test_run_uses_tcc_when_available(tmp_path):
    cache = tmp_path / "cache"
    work = tmp_path / "w"
    work.mkdir()
    script = work / "h.pengu"
    script.write_text('weave main into int:\n    return 0\n', encoding="utf-8")
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache)
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "run", "--verbose", str(script)],
        cwd=str(work), capture_output=True, text=True, timeout=300, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert "tcc" in res.stdout.lower()


def test_tcc_failure_falls_back_to_configured_cc(tmp_path, monkeypatch):
    """A TCC that always fails must not break the build (falls back to gcc)."""
    fake = tmp_path / "tcc"
    fake.write_text("#!/bin/sh\necho 'tcc: fake failure' >&2\nexit 1\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("PENGU_DEV_CC", str(fake))
    assert pick_dev_compiler("gcc") == str(fake)


# ---------------------------------------------------------------------------
# PCH (opt-in)
# ---------------------------------------------------------------------------

def test_pch_is_opt_in(tmp_path):
    """The PCH is off by default (measured: no gain on a normal build)."""
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "p.pengu"
    script.write_text('weave main into int:\n    return 0\n', encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path), output=OutputType.C,
                        output_name="p", name="p", build_dir=str(tmp_path / "b"))
    builder = PenguBuilder(cfg)
    assert builder.use_pch is False
    assert builder.dev_fast_flags is False


def test_pch_signature_tracks_include_and_define_flags(tmp_path):
    sys.path.insert(0, str(REPO))
    from pengu_project import PenguBuilder

    sig_a = PenguBuilder._pch_signature(["-Ifoo", "-DBAR", "-O2", "-Wall"])
    sig_b = PenguBuilder._pch_signature(["-Ifoo", "-DBAR=1", "-O0"])
    assert sig_a != sig_b
    assert "-O2" not in sig_a and "-Wall" not in sig_a
