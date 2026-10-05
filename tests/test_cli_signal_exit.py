"""Phase 4 item 4.9: a signalled child is reported as ``128 + signal``.

``subprocess`` reports a child killed by a signal as a **negative** code, and
``sys.exit(-8)`` surfaces as ``248`` (Python masks the status to 8 bits) — the
opposite of the ``136`` a shell reports for SIGFPE.

Measured before the fix, with a test block that performs an integer division by
zero: `pengu test` → rc=248 and `pengu test --json` →
`{"event":"end","aborted":true,"exit_code":-8}`. The script paths already
reported 136 because `pengu_runtime.h` installs a handler that calls
`_exit(128 + sig)`; a **test** bundle does not install it, so the process really
dies from the signal and this mapping is the safety net (item 4.18 installs the
handler in test bundles and adds the `[PENGU CRASH]` message).
"""

import json
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

CRASHING_TEST = (
    "weave main into int:\n"
    "    return 0\n"
    "\n"
    'test "div cero":\n'
    "    var a as int is 1\n"
    "    var b as int is 0\n"
    "    var c as int is a / b\n"
    "    if c == 0:\n"
    "        return\n"
)

SIGFPE_EXIT = 128 + 8        # 136, what a shell reports


def _run(args, cwd=None):
    env = dict(os.environ, NO_COLOR="1")
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300,
        cwd=str(cwd) if cwd else None, env=env,
    )


@pytest.fixture()
def crashing_project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    project = tmp_path / "ok"
    (project / "src" / "main.pengu").write_text(CRASHING_TEST, encoding="utf-8")
    return project


@requires_cc
@requires_runtime
def test_test_command_reports_signal_as_128_plus(crashing_project):
    res = _run(["test"], cwd=crashing_project)
    assert res.returncode == SIGFPE_EXIT, (res.returncode, res.stdout, res.stderr)


@requires_cc
@requires_runtime
def test_test_json_reports_signal_exit_code(crashing_project):
    res = _run(["test", "--json"], cwd=crashing_project)
    assert res.returncode == SIGFPE_EXIT, (res.returncode, res.stdout, res.stderr)
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    objects = [json.loads(ln) for ln in lines]      # every line must be JSON
    final = objects[-1]
    assert final["event"] == "end"
    assert final["exit_code"] == SIGFPE_EXIT
    assert final["aborted"] is True


@requires_cc
@requires_runtime
def test_run_script_reports_signal_as_128_plus(tmp_path):
    script = tmp_path / "div.pengu"
    script.write_text(
        "weave main into int:\n"
        "    var a as int is 1\n"
        "    var b as int is 0\n"
        "    return a / b\n", encoding="utf-8")
    res = _run(["run", str(script)])
    assert res.returncode == SIGFPE_EXIT, (res.returncode, res.stdout, res.stderr)


def test_exit_code_helper_unit():
    from pengu_project import _exit_code_from_child

    assert _exit_code_from_child(-8) == 136
    assert _exit_code_from_child(-11) == 139
    assert _exit_code_from_child(0) == 0
    assert _exit_code_from_child(1) == 1
    assert _exit_code_from_child(136) == 136


# ---------------------------------------------------------------------------
# Item 4.18: the --test entry point installs the crash handler too
# ---------------------------------------------------------------------------


@requires_cc
@requires_runtime
def test_test_bundle_reports_the_crash_dump(crashing_project):
    """Without the handler the process dies by signal and prints nothing."""
    res = _run(["test"], cwd=crashing_project)
    assert res.returncode == SIGFPE_EXIT, (res.returncode, res.stdout, res.stderr)
    combined = res.stdout + res.stderr
    assert "[PENGU CRASH]" in combined, combined
    assert "signal/code 8" in combined, combined
    # The dump must blame the test that faulted, not just the process start.
    assert "main.pengu:4" in combined, combined


@requires_cc
@requires_runtime
def test_test_json_keeps_json_contract_with_the_handler(crashing_project):
    """Installing the handler must not break the `--json` stream on stdout."""
    res = _run(["test", "--json"], cwd=crashing_project)
    assert res.returncode == SIGFPE_EXIT, (res.returncode, res.stdout, res.stderr)
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    objects = [json.loads(ln) for ln in lines]      # every stdout line is JSON
    assert objects[-1]["exit_code"] == SIGFPE_EXIT
    assert "[PENGU CRASH]" in res.stderr, res.stderr
