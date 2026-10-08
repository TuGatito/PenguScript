"""Phase 1 — return-flow analysis for value-returning weaves.

Rule C1 (ROADMAP_2.0 Anexo C): each case is compiled by the real front end and
the assertion is on the resulting diagnostic code, not on message prose.

Item 1.9 of ROADMAP_2.0: `weave f into int: while true: return 1` used to be
rejected with E0020 ("does not return a value"), which forced authors to append
an unreachable `return 0` after an infinite loop purely to satisfy the checker.
The analysis now treats a `while` whose condition folds to a constant true as a
terminating path -- and only that case, so a genuine missing-return is still
reported.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"


def check_source(tmp_path, name, body):
    """Writes `body` to a file and returns (returncode, diagnostic codes)."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, "check", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    return r.returncode, sorted(set(re.findall(r"E\d{4}", out))), out


# ---------------------------------------------------------------------------
# Terminating loops (must be accepted)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cond", ["true", "1 < 2", "1 == 1"])
def test_constant_true_while_is_terminating(tmp_path, cond):
    """A `while` with a foldable-true condition cannot fall through."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        f"weave f into int:\n  while {cond}:\n    return 1\n",
    )
    assert rc == 0, out
    assert "E0020" not in codes, out


def test_infinite_loop_with_work_then_return(tmp_path):
    """The realistic shape: a server/state-machine loop that returns."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        "weave f with n as int into int:\n"
        "  var i as int is 0\n"
        "  while true:\n"
        "    if i == n:\n"
        "      return i\n"
        "    set i += 1\n",
    )
    assert rc == 0, out
    assert "E0020" not in codes, out


# ---------------------------------------------------------------------------
# Non-terminating loops (must still be rejected)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cond", ["1 > 2", "false"])
def test_constant_false_while_is_not_terminating(tmp_path, cond):
    """A `while` that never runs cannot satisfy a non-void return type."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        f"weave f into int:\n  while {cond}:\n    return 1\n",
    )
    assert rc == 1, out
    assert "E0020" in codes, out


def test_dynamic_while_is_not_terminating(tmp_path):
    """A condition the folder cannot evaluate may be false on entry."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        "weave f with n as int into int:\n  while n > 0:\n    return 1\n",
    )
    assert rc == 1, out
    assert "E0020" in codes, out


def test_missing_return_still_reported(tmp_path):
    """Guard against over-reach: ordinary missing returns stay E0020."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        "weave f into int:\n  var x as int is 2\n",
    )
    assert rc == 1, out
    assert "E0020" in codes, out


def test_if_without_else_still_reported(tmp_path):
    """Only one branch returns -> still an error."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        "weave f with c as bool into int:\n"
        "  if c:\n"
        "    return 1\n",
    )
    assert rc == 1, out
    assert "E0020" in codes, out


def test_both_branches_return_is_accepted(tmp_path):
    """The complement of the previous case."""
    rc, codes, out = check_source(
        tmp_path, "w.pengu",
        "weave f with c as bool into int:\n"
        "  if c:\n"
        "    return 1\n"
        "  else:\n"
        "    return 2\n",
    )
    assert rc == 0, out
    assert "E0020" not in codes, out
