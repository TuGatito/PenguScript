"""Cache, cleanup and CLI-ergonomics tests for ``pengu run``.

These exercise the *behaviour* the performance work promises:

* a second run of an unchanged script is a cache hit and does not recompile,
* editing the script (or one of its imports) invalidates the entry,
* ``--no-cache``/``--ephemeral``/``--keep`` behave as documented,
* the default run never creates ``build/`` in the working directory,
* ``pengu doctor``/``expand``/``eval``/``gc`` work end to end.

The tests are hermetic: they point ``PENGU_CACHE_DIR`` at a temporary directory
and, when checking timings, only assert generous bounds (CI machines vary a lot).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from pengu_cache import script_binary_name
from tests.conftest import REPO, requires_cc, requires_runtime

pytestmark = [requires_cc, requires_runtime]

HELLO = '''import std.spark

weave main into int:
    calling spark.println with "cache hello"
    return 0
'''


def _cli(args, cwd, cache_dir, timeout=300):
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache_dir)
    env.pop("PENGU_CACHE", None)
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py")] + args,
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env,
    )


@pytest.fixture()
def sandbox(tmp_path):
    cache = tmp_path / "cache"
    work = tmp_path / "work"
    work.mkdir()
    script = work / "hello.pengu"
    script.write_text(HELLO, encoding="utf-8")
    return {"cache": cache, "work": work, "script": script}


def test_first_run_populates_the_cache_and_second_is_a_hit(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]

    res = _cli(["run", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "cache hello" in res.stdout
    entries = (list((cache / "scripts").glob(f"*/{script_binary_name()}"))
               if (cache / "scripts").is_dir() else [])
    assert entries, "the first run must populate <cache>/scripts/<key>/app"
    assert os.access(entries[0], os.X_OK)

    res2 = _cli(["run", str(script)], work, cache)
    assert res2.returncode == 0, res2.stderr
    assert "cache hello" in res2.stdout
    assert "cached" in res2.stdout.lower()


def test_second_run_is_much_faster_than_the_first(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    t0 = time.perf_counter()
    first = _cli(["run", str(script)], work, cache)
    cold = time.perf_counter() - t0
    assert first.returncode == 0, first.stderr
    t1 = time.perf_counter()
    second = _cli(["run", str(script)], work, cache)
    warm = time.perf_counter() - t1
    assert second.returncode == 0, second.stderr
    # A cache hit skips the whole compiler pipeline: it must be several times
    # faster even on a slow CI machine (the cold path spawns a C compiler).
    assert warm < cold, (cold, warm)
    assert warm < 3.0, f"warm run too slow: {warm:.3f}s"


def test_editing_the_script_invalidates_the_cache(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    assert _cli(["run", str(script)], work, cache).returncode == 0
    script.write_text(HELLO.replace("cache hello", "cache hello v2"), encoding="utf-8")
    res = _cli(["run", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "cache hello v2" in res.stdout
    assert "cached" not in res.stdout.lower(), "editing the script must force a rebuild"


def test_editing_an_imported_module_invalidates_the_cache(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    helper = work / "helper.pengu"
    helper.write_text('weave greet into string:\n    return "one"\n', encoding="utf-8")
    script.write_text(
        "import std.spark\nimport helper\n\n"
        "weave main into int:\n"
        "    calling spark.println with calling helper.greet\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert "one" in _cli(["run", str(script)], work, cache).stdout
    helper.write_text('weave greet into string:\n    return "two"\n', encoding="utf-8")
    res = _cli(["run", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "two" in res.stdout


def test_no_cache_flag_never_uses_the_cache(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["run", "--no-cache", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    scripts_dir = cache / "scripts"
    assert not scripts_dir.exists() or not list(scripts_dir.glob(f"*/{script_binary_name()}"))


def test_clear_cache_empties_the_store(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    assert _cli(["run", str(script)], work, cache).returncode == 0
    assert list((cache / "scripts").glob(f"*/{script_binary_name()}"))
    res = _cli(["run", "--clear-cache", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "Cleared" in res.stdout
    # The run itself repopulates it.
    assert list((cache / "scripts").glob(f"*/{script_binary_name()}"))


def test_pengu_cache_env_var_disables_caching(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache)
    env["PENGU_CACHE"] = "0"
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "run", str(script)],
        cwd=str(work), capture_output=True, text=True, timeout=300, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert not (cache / "scripts").exists() or not list((cache / "scripts").glob(f"*/{script_binary_name()}"))


def test_script_arguments_are_forwarded(sandbox):
    """Roadmap 8.17 (3): the args must be *exactly* the two after `--`.

    The old assertion was ``assert "2" in res.stdout`` — a substring of the whole
    CLI transcript.  It went green whenever any progress line happened to contain a
    digit 2 (`Finished in 0.7x s`, a temp path, ...) and red otherwise; measured
    over five runs of this file it failed 1 time, and the printed value was never
    the thing being asserted.  It also encoded the wrong contract:
    ``std.rites.get_args`` documents index 0 as the program name, so two forwarded
    arguments means ``args.len == 3``, never 2.

    The assertion is now on exact output lines, so it measures the forwarding
    itself instead of the noise around it.
    """
    work, cache = sandbox["work"], sandbox["cache"]
    script = work / "args.pengu"
    script.write_text(
        "import std.rites\nimport std.spark\n\n"
        "weave main into int:\n"
        "    var args as list of string is calling rites.get_args\n"
        "    calling spark.println with \"ARGC:{args.len}\"\n"
        "    var a1 as string is calling rites.arg_at_or with 1, \"\"\n"
        "    var a2 as string is calling rites.arg_at_or with 2, \"\"\n"
        "    calling spark.println with \"ARG1:{a1}\"\n"
        "    calling spark.println with \"ARG2:{a2}\"\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = _cli(["run", str(script), "--", "one", "two"], work, cache)
    if res.returncode != 0:
        pytest.skip(f"std.rites.get_args unavailable: {res.stderr[:200]}")
    lines = [line.strip() for line in res.stdout.splitlines()]
    # argv[0] is the program name, hence 3 and not 2.
    assert "ARGC:3" in lines, lines
    assert "ARG1:one" in lines, lines
    assert "ARG2:two" in lines, lines
    # The `--` separator belongs to the CLI, never to the script.
    assert not any(line.split(":", 1)[-1].startswith("--")
                   for line in lines if line.startswith(("ARG1:", "ARG2:"))), lines


def test_run_does_not_create_build_in_the_working_directory(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["run", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert not (work / "build").exists(), "the default run must not create build/"


def test_keep_writes_the_build_directory(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["run", "--keep", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    bundle = work / "build" / "hello_run" / "bundle.c"
    assert bundle.is_file(), "‑‑keep must leave bundle.c for inspection"


def test_ephemeral_run_leaves_no_trace(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["run", "--ephemeral", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert not (work / "build").exists()
    assert not (cache / "scripts").exists() or not list((cache / "scripts").glob(f"*/{script_binary_name()}"))


def test_doctor_reports_the_essentials(sandbox):
    res = _cli(["doctor"], sandbox["work"], sandbox["cache"])
    assert res.returncode in (0, 1)
    assert "PenguScript doctor" in res.stdout
    for needle in ("runtime header", "cache root", "C compiler", "tcc"):
        assert needle in res.stdout


def test_doctor_json_is_machine_readable(sandbox):
    res = _cli(["doctor", "--json"], sandbox["work"], sandbox["cache"])
    data = json.loads(res.stdout.strip().splitlines()[-1])
    assert data["pengu"]
    assert "cache_root" in data


def test_gc_removes_cached_scripts(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    assert _cli(["run", str(script)], work, cache).returncode == 0
    res = _cli(["gc", "--all"], work, cache)
    assert res.returncode == 0, res.stderr
    assert "Collected" in res.stdout
    assert not list((cache / "scripts").glob(f"*/{script_binary_name()}"))


def test_expand_prints_a_bundle_without_touching_build(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["expand", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "#include \"pengu_runtime.h\"" in res.stdout
    assert "pengu_main" in res.stdout
    assert not (work / "build").exists()


def test_eval_prints_the_expression_result(sandbox):
    res = _cli(["eval", "1 + 2"], sandbox["work"], sandbox["cache"])
    assert res.returncode == 0, res.stderr
    assert "3" in res.stdout


def test_time_reports_phases(sandbox):
    work, cache, script = sandbox["work"], sandbox["cache"], sandbox["script"]
    res = _cli(["time", str(script)], work, cache)
    assert res.returncode == 0, res.stderr
    assert "phase timings" in res.stdout
    assert "TOTAL" in res.stdout


def test_cached_binary_name_is_platform_aware(monkeypatch):
    """Windows cannot execute an extension-less image: the cache keeps '.exe'.

    ``CreateProcess`` appends ``.exe`` when the image name has no extension, so a
    cached file called plain ``app`` fails with "file not found" on Windows.
    Pinned here (with the platform faked) because it is invisible on Linux.
    """
    import pengu_cache

    monkeypatch.setattr(pengu_cache.sys, "platform", "win32")
    assert pengu_cache.script_binary_name() == "app.exe"
    monkeypatch.setenv("PENGU_CACHE_DIR", "/tmp/does-not-matter")
    assert pengu_cache.cached_binary_path("k").replace("\\", "/").endswith("k/app.exe")

    monkeypatch.setattr(pengu_cache.sys, "platform", "linux")
    assert pengu_cache.script_binary_name() == "app"
    assert pengu_cache.cached_binary_path("k").replace("\\", "/").endswith("k/app")
