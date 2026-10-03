"""Phase 1 — CLI contract regressions.

Rule C1 (ROADMAP_2.0 Anexo C): a test may not approve a property by inspecting
text. Every test here drives the real CLI in a subprocess and asserts on the
**exit code** and on **structured output**, never on a substring chosen to match
an implementation.

Why this file exists
--------------------
`pengu check <file>` used to ignore its positional argument and report
"Clean no errors found" (blocker B1), and `parse_known_args()` used to discard
unknown flags silently (blocker B3). Both survived 2074 green tests because no
test ever invoked the CLI the way a user does. These tests do.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"


def cli(args, cwd=None, timeout=300, stdin=None):
    """Runs the real CLI entry point in a subprocess.

    Invoked as ``python -m pengu_project`` because the ``pengu`` console script
    is only installed inside the project's virtualenv, which CI does not put on
    PATH. This is the same convention as ``tests/test_cli_tools.py``.
    """
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    # The CLI lives in the repo root, but several tests run it from a scratch
    # cwd, so the module must be importable regardless of the working directory.
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(REPO), existing) if p)
    return subprocess.run(
        [PY, "-m", MODULE] + list(args),
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        input=stdin,
        env=env,
    )


def _write_program(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# B3 — unknown flags must be rejected (item 1.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [
    ["check", "--bogus"],
    ["check", "--strictc99"],      # typo for --strict-c99
    ["build", "--strictc99"],      # typo for --strict-c99
    ["test", "--frozem"],          # typo for --frozen
    ["run", "--noexiste"],
    ["check", "--deny-deprecatedd"],
    ["--bogus-global"],
])
def test_unknown_flag_is_rejected(argv):
    """An unrecognised argument exits 2 with an actionable message.

    Regression for B3: `parse_known_args()` used to drop these silently, so a
    misspelled `--strict-c99` produced a green build with no C99 guarantee.
    """
    r = cli(argv)
    assert r.returncode == 2, (
        f"expected rc=2 for {argv}, got {r.returncode}\n"
        f"stdout={r.stdout}\nstderr={r.stderr}"
    )
    combined = (r.stdout + r.stderr).lower()
    assert "unrecognized arguments" in combined, combined


def test_known_flags_still_accepted(tmp_path):
    """The rejection must not break real flags (guard against over-reach)."""
    proj = tmp_path / "known"
    assert cli(["init", "known"], cwd=tmp_path).returncode == 0
    r = cli(["build", "--profile", "debug"], cwd=proj)
    assert r.returncode == 0, r.stdout + r.stderr


def test_help_and_version_still_work():
    assert cli(["--help"]).returncode == 0
    r = cli(["-V"])
    assert r.returncode == 0
    # The version must actually be a version, not an empty string.
    assert any(ch.isdigit() for ch in r.stdout)


def test_run_forwards_unknown_args_to_the_script(tmp_path):
    """`pengu run script.pengu ARGS...` forwards ARGS; it must NOT exit 2.

    This is the one deliberate exception to the unknown-flag rule: the `run`
    subparser has no REMAINDER positional, so everything after the script path
    is a script argument. Verified by executing, not by reading the parser.
    """
    script = _write_program(
        tmp_path / "args.pengu",
        'weave main into int:\n'
        '  return 0\n',
    )
    for extra in ([], ["hello"], ["--", "hello"], ["--flag", "x"]):
        r = cli(["run", str(script)] + extra, cwd=tmp_path)
        assert r.returncode == 0, (
            f"`run {script.name} {' '.join(extra)}` exited {r.returncode}\n"
            f"{r.stdout}\n{r.stderr}"
        )
