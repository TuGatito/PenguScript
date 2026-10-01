"""Dead-code elimination (DCE) end-to-end tests.

The pass is a pure compiler pass, so these tests only need ``pengu expand``
(bundle to C, no C compiler, no runtime archive) and therefore run everywhere.

The cache directory is module-scoped on purpose: building Lark's LALR tables
costs a few seconds, and paying that once per test would dominate the suite.
It is still hermetic — the user's real cache is never touched.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO

SPARK_PRINTLN = '''import std.spark

weave main into int:
    calling spark.println with "hello dce"
    return 0
'''

SPARK_BOTH = '''import std.spark

weave main into int:
    calling spark.println with "a"
    calling spark.print with "b"
    return 0
'''


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory):
    """One shared, isolated cache root for the whole module."""
    return tmp_path_factory.mktemp("dce-cache")


def _expand(script, cwd, cache_dir, extra_env=None, defines=()):
    """Runs ``pengu expand <script>`` and returns (returncode, stdout, stderr)."""
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache_dir)
    env.pop("PENGU_CACHE", None)
    env.pop("PENGU_NO_DCE", None)
    env.update(extra_env or {})
    cmd = [sys.executable, str(REPO / "pengu_project.py"), "expand", str(script)]
    for d in defines:
        cmd += ["-D", d]
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                         timeout=300, env=env)
    return res.returncode, res.stdout, res.stderr


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_dce_prunes_unused_std_weaves(tmp_path, cache_dir):
    """Only the weaves reachable from main survive (spark.println here)."""
    work = tmp_path / "w"
    work.mkdir()
    script = _write(work / "hello.pengu", SPARK_PRINTLN)

    rc, dce, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "pengu_main" in dce
    assert "spark_println" in dce
    # The rest of std.spark is gone: without DCE the bundle is >400 lines.
    assert len(dce.splitlines()) < 200, f"bundle.c still has {len(dce.splitlines())} lines"
    assert "spark_version" not in dce


def test_no_dce_env_keeps_everything(tmp_path, cache_dir):
    """PENGU_NO_DCE=1 restores the pre-DCE code generator exactly."""
    work = tmp_path / "w"
    work.mkdir()
    script = _write(work / "hello.pengu", SPARK_PRINTLN)

    rc, with_dce, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    rc, without_dce, err = _expand(script, work, cache_dir,
                                   extra_env={"PENGU_NO_DCE": "1"})
    assert rc == 0, err

    assert len(without_dce.splitlines()) > 3 * len(with_dce.splitlines())
    for needle in ("spark_version", "spark_assert", "spark_input"):
        assert needle in without_dce
        assert needle not in with_dce


def test_dce_keeps_referenced_weaves(tmp_path, cache_dir):
    """A second std weave stays alive when main calls it too."""
    work = tmp_path / "w"
    work.mkdir()
    script = _write(work / "both.pengu", SPARK_BOTH)

    rc, c, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "spark_println" in c
    assert "spark_print(" in c
    # ...but the ones that are still unreferenced do not come back.
    assert "spark_version" not in c


def test_dce_never_prunes_user_module_public_symbols(tmp_path, cache_dir):
    """User modules are API surface: every weave is emitted, used or not."""
    work = tmp_path / "w"
    work.mkdir()
    _write(work / "helper.pengu",
           'weave used_public into int:\n    return 1\n\n'
           'weave unused_public into int:\n    return 2\n')
    script = _write(work / "prog.pengu",
                    "import helper\n\n"
                    "weave main into int:\n"
                    "    calling helper.used_public\n"
                    "    return 0\n")

    rc, c, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "used_public" in c
    assert "unused_public" in c, "public weaves of user modules must never be pruned"


def test_dce_prunes_unused_lib_binding_weaves(tmp_path, cache_dir):
    """``lib/<binding>/`` is vendored third-party code: it *is* prunable."""
    work = tmp_path / "w"
    (work / "lib" / "vendor" / "pengu").mkdir(parents=True)
    _write(work / "lib" / "vendor" / "pengu" / "vendor.pengu",
           'weave used_vendor into int:\n    return 7\n\n'
           'weave unused_vendor into int:\n    return 8\n')
    script = _write(work / "prog.pengu",
                    "import vendor\n\n"
                    "weave main into int:\n"
                    "    calling vendor.used_vendor\n"
                    "    return 0\n")

    rc, c, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "used_vendor" in c
    assert "unused_vendor" not in c, (
        "an unreferenced weave of a lib/ binding must be pruned"
    )


def test_dce_does_not_drop_by_module_alias(tmp_path, cache_dir):
    """A weave named ``*_<module>`` must not be kept just because the module is.

    Regression: the previous suffix heuristic stripped ``unused_vendor`` down to
    ``vendor``, which appears in every call site as the module alias, so nothing
    in a ``lib/`` binding was ever pruned.
    """
    work = tmp_path / "w"
    (work / "lib" / "vendor" / "pengu").mkdir(parents=True)
    _write(work / "lib" / "vendor" / "pengu" / "vendor.pengu",
           'weave vendor_helper into int:\n    return 1\n\n'
           'weave unused_vendor into int:\n    return 2\n')
    script = _write(work / "prog.pengu",
                    "import vendor\n\n"
                    "weave main into int:\n"
                    "    calling vendor.vendor_helper\n"
                    "    return 0\n")

    rc, c, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "vendor_helper" in c
    assert "unused_vendor" not in c


def test_dce_marks_the_bundle(tmp_path, cache_dir):
    """bundle.c is self-describing: a DCE build says what it pruned."""
    work = tmp_path / "w"
    work.mkdir()
    script = _write(work / "hello.pengu", SPARK_PRINTLN)

    rc, with_dce, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "Dead-code elimination: pruned" in with_dce
    assert "35 -> 2" in with_dce

    rc, without_dce, err = _expand(script, work, cache_dir,
                                   extra_env={"PENGU_NO_DCE": "1"})
    assert rc == 0, err
    assert "Dead-code elimination: disabled (PENGU_NO_DCE)" in without_dce
    assert "pruned" not in without_dce


def test_dce_prunes_std_weaves_transitively(tmp_path, cache_dir):
    """A weave pulled in by another prunable weave is kept transitively."""
    work = tmp_path / "w"
    (work / "lib" / "dep" / "pengu").mkdir(parents=True)
    _write(work / "lib" / "dep" / "pengu" / "dep.pengu",
           'weave inner into int:\n    return 5\n\n'
           'weave outer into int:\n    return calling inner\n\n'
           'weave unused_dep into int:\n    return 9\n')
    script = _write(work / "prog.pengu",
                    "import dep\n\n"
                    "weave main into int:\n"
                    "    calling dep.outer\n"
                    "    return 0\n")

    rc, c, err = _expand(script, work, cache_dir)
    assert rc == 0, err
    assert "outer" in c
    assert "inner" in c, "a weave referenced by another kept weave must survive"
    assert "unused_dep" not in c
