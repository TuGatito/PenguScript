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


# ---------------------------------------------------------------------------
# B1 — `pengu check <file>` must check THAT file (item 1.2)
# ---------------------------------------------------------------------------

def _broken(tmp_path, name="roto.pengu"):
    return _write_program(
        tmp_path / name,
        "weave main:\n  var x as int is undefined_thing\n",
    )


def _good(tmp_path, name="ok.pengu"):
    return _write_program(tmp_path / name, "weave main into int:\n  return 42\n")


def test_check_positional_file_reports_its_error(tmp_path):
    """`check <file>` validates the file, not the surrounding project.

    Regression for B1: the positional was silently discarded and the command
    reported "Clean no errors found" for a project the user never mentioned.
    """
    f = _broken(tmp_path)
    r = cli(["check", str(f)], cwd=tmp_path)
    assert r.returncode == 1, f"expected rc=1, got {r.returncode}\n{r.stdout}\n{r.stderr}"
    assert "E0004" in (r.stdout + r.stderr)


def test_check_positional_good_file_passes(tmp_path):
    f = _good(tmp_path)
    r = cli(["check", str(f)], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_nonexistent_file_fails(tmp_path):
    r = cli(["check", str(tmp_path / "noexiste.pengu")], cwd=tmp_path)
    assert r.returncode != 0
    assert "not found" in (r.stdout + r.stderr).lower()


def test_check_multiple_files_aggregates(tmp_path):
    """One bad file among good ones must make the command fail."""
    good, bad = _good(tmp_path), _broken(tmp_path)
    assert cli(["check", str(good), str(bad)], cwd=tmp_path).returncode == 1
    assert cli(["check", str(good), str(good)], cwd=tmp_path).returncode == 0


def test_check_positional_resolves_stdlib_imports(tmp_path):
    """A file checked in place must still resolve `import std.*`.

    The base_dir for a positional file is its own directory, so the project
    config (lib_dir / include_dirs / defines) has to keep applying.
    """
    f = _write_program(
        tmp_path / "withstd.pengu",
        'import std.spark\n'
        'weave main into int:\n'
        '    calling spark.println with "hi"\n'
        '    return 0\n',
    )
    r = cli(["check", str(f)], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_json_lines_with_positional(tmp_path):
    """--json must stay machine-readable on the positional path (rule C1)."""
    import json as _json
    f = _broken(tmp_path)
    r = cli(["check", str(f), "--json"], cwd=tmp_path)
    assert r.returncode == 1
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    payloads = [_json.loads(ln) for ln in lines]
    assert any(p.get("type") == "diagnostic" and p.get("code") == "E0004" for p in payloads), payloads
    summary = [p for p in payloads if p.get("type") == "summary"]
    assert summary and summary[-1]["ok"] is False


def test_check_project_mode_unchanged(tmp_path):
    """Without positionals the old project behaviour must be untouched."""
    proj = tmp_path / "p"
    assert cli(["init", "p"], cwd=tmp_path).returncode == 0
    assert cli(["check"], cwd=proj).returncode == 0
    _write_program(proj / "src" / "main.pengu",
                   "weave main:\n  var x as int is undefined_thing\n")
    r = cli(["check"], cwd=proj)
    assert r.returncode == 1
    assert "E0004" in (r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# B2 — a missing entry point is an error (item 1.3)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("subcommand", ["check", "build", "test"])
def test_missing_entry_point_fails(subcommand, tmp_path):
    """In a directory with no entry file, every build command must fail.

    Regression for B2: `check` returned ok=True with an empty module list and
    printed "Clean", and `test` exited 0 with "No tests to run." because the
    generated test harness is a valid C program even with no input.
    """
    empty = tmp_path / "vacio"
    empty.mkdir()
    r = cli([subcommand], cwd=empty)
    assert r.returncode != 0, (
        f"`pengu {subcommand}` in an empty dir returned {r.returncode}\n"
        f"{r.stdout}\n{r.stderr}"
    )
    assert "entry point not found" in (r.stdout + r.stderr).lower()


@pytest.mark.parametrize("subcommand", ["check", "build", "test"])
def test_missing_entry_point_is_json_on_request(subcommand, tmp_path):
    """--json must emit a diagnostic plus summary, not a bare exit code."""
    import json as _json
    empty = tmp_path / "vacio"
    empty.mkdir()
    r = cli([subcommand, "--json"], cwd=empty)
    assert r.returncode != 0
    payloads = [_json.loads(ln) for ln in r.stdout.splitlines() if ln.strip()]
    assert any(p.get("type") == "diagnostic" and "entry point not found" in p.get("message", "")
               for p in payloads), payloads
    assert any(p.get("type") == "summary" and p.get("ok") is False for p in payloads), payloads


def test_present_entry_point_still_builds(tmp_path):
    """The guard must not fire for a healthy project."""
    proj = tmp_path / "ok"
    assert cli(["init", "ok"], cwd=tmp_path).returncode == 0
    assert cli(["build"], cwd=proj).returncode == 0
