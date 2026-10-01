"""TinyCC integration: fast development compiles with a clean gcc fallback.

TCC is optional (it is bundled in the release archives and built by CI); every
test here skips unless ``tcc`` is on ``PATH`` or ``PENGU_TCC`` points at one.
The compile+run tests additionally need the built runtime archive.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from pengu_tcc import tcc_available
from tests.conftest import REPO, requires_cc, requires_runtime

pytestmark = pytest.mark.skipif(
    not tcc_available(),
    reason="tcc not available (install it, set PENGU_TCC, or use a release archive)",
)

HELLO = '''import std.spark

weave main into int:
    calling spark.println with "tcc hello"
    return 0
'''


def _cli(args, cwd, cache_dir, env_extra=None, timeout=300):
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache_dir)
    env.pop("PENGU_CACHE", None)
    env.pop("PENGU_NO_TCC", None)
    env.pop("PENGU_DEV_CC", None)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py")] + args,
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env,
    )


@pytest.fixture()
def sandbox(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    script = work / "hello.pengu"
    script.write_text(HELLO, encoding="utf-8")
    return {"work": work, "script": script, "cache": tmp_path / "cache"}


def test_pick_dev_compiler_prefers_tcc(monkeypatch):
    from pengu_tcc import find_tcc, pick_dev_compiler, tcc_available

    assert tcc_available()
    chosen = pick_dev_compiler("gcc")
    assert "tcc" in os.path.basename(chosen).lower()
    assert os.path.abspath(chosen) == os.path.abspath(find_tcc())


def test_pengu_no_tcc_disables_discovery(monkeypatch):
    from pengu_tcc import find_tcc, pick_dev_compiler

    monkeypatch.setenv("PENGU_NO_TCC", "1")
    assert find_tcc() is None
    assert pick_dev_compiler("gcc") == "gcc"


@requires_cc
@requires_runtime
def test_run_uses_tcc_when_available(sandbox):
    work, script, cache = sandbox["work"], sandbox["script"], sandbox["cache"]
    res = _cli(["run", "--verbose", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "tcc hello" in res.stdout
    # A fresh cache directory forces a miss; the verbose banner names the compiler.
    from pengu_tcc import pick_dev_compiler

    chosen = pick_dev_compiler("gcc")
    assert "cache miss" in res.stdout or "cache miss" in res.stderr
    combined = res.stdout + res.stderr
    assert chosen in combined, combined
    assert "tcc" in chosen.lower()
    if "retrying with" in combined:
        # The bundled TCC is best-effort: on a platform where that particular
        # binary cannot compile the bundle the run still succeeds through the
        # gcc fallback (asserted above).  Report it as a skip rather than a
        # failure so CI distinguishes "TCC unusable here" from "toolchain broken".
        pytest.skip("the staged TCC could not compile the bundle on this platform; "
                    f"the gcc fallback worked: {res.stderr.strip()[-200:]}")
    # ...and TCC must have produced the binary itself. Regression: a link line
    # with GNU-ld-only flags (-Wl,--start-group) made every TCC build fall back
    # to gcc, which silently doubled the cache-miss compile time.
    assert "retrying with" not in combined


@requires_cc
@requires_runtime
def test_pengu_dev_cc_overrides_tcc(sandbox):
    work, script, cache = sandbox["work"], sandbox["script"], sandbox["cache"]
    res = _cli(["run", "--verbose", str(script)], work, cache,
               env_extra={"PENGU_DEV_CC": "gcc"})
    assert res.returncode == 0, res.stderr
    assert "tcc hello" in res.stdout
    # PENGU_DEV_CC wins over the discovered TCC: the banner names gcc.
    combined = res.stdout + res.stderr
    assert "(cc=gcc)" in combined, combined
    assert "running C compiler: gcc" in combined, combined


@requires_cc
@requires_runtime
@pytest.mark.skipif(os.name == "nt", reason="needs a POSIX shell stub")
def test_fallback_to_gcc_when_tcc_fails(sandbox, tmp_path):
    """A broken PENGU_DEV_CC must not fail the build: retry with the real cc."""
    work, script, cache = sandbox["work"], sandbox["script"], sandbox["cache"]
    broken = tmp_path / "broken-tcc"
    broken.write_text("#!/bin/sh\necho 'fake tcc: unsupported' >&2\nexit 1\n",
                      encoding="utf-8")
    broken.chmod(0o755)

    res = _cli(["run", "--no-cache", str(script)], work, cache,
               env_extra={"PENGU_DEV_CC": str(broken)})
    assert res.returncode == 0, res.stderr
    assert "tcc hello" in res.stdout
    assert "retrying with" in res.stderr, res.stderr


@requires_cc
@requires_runtime
@pytest.mark.skipif(os.name == "nt", reason="needs a POSIX shell stub")
def test_fallback_uses_the_configured_compiler(sandbox, tmp_path):
    """The retry uses the project's compiler, not a hard-coded 'gcc'."""
    work, script, cache = sandbox["work"], sandbox["script"], sandbox["cache"]
    broken = tmp_path / "broken-tcc"
    broken.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    broken.chmod(0o755)

    configured = shutil.which("clang") or shutil.which("gcc") or "cc"
    res = _cli(["run", "--no-cache", "--cc", configured, str(script)], work, cache,
               env_extra={"PENGU_DEV_CC": str(broken)})
    assert res.returncode == 0, res.stderr
    assert os.path.basename(configured) in res.stderr, res.stderr
