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

The second half of the file is the Phase 8 / item 8.8 exit-code contract: one
row per subcommand (success + every applicable failure class), kept honest by an
introspection test that reads the real parser instead of the ``--help`` text.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

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


# ===========================================================================
# Phase 8 / item 8.8 — the exit-code contract, one row per subcommand
# ===========================================================================
#
# Each row below pins, for one subcommand:
#
#   * success      an invocation that must exit 0 **and** leave a structured
#                  effect behind (a file on disk, parsed --json, an exact
#                  computed value). Never a prose substring (rule C1).
#   * missing      an invocation that omits a required positional -> rc 2.
#   * unknown flag every command except ``run`` rejects an extra flag -> rc 2.
#                  ``run`` forwards everything after the script path to the
#                  script (see test_run_forwards_unknown_args_to_the_script).
#   * nonexistent  a missing input file / dependency must fail with rc != 0 and
#                  must NOT raise a Python traceback (rule C4).
#   * bad option   a value argparse rejects (``choices=`` / ``type=int``) must
#                  fail. ``--profile`` is deliberately NOT used as the bad-value
#                  probe: profiles are user-extensible in the manifest, so
#                  ``--profile nope`` is a legitimate custom profile name.
#
# ``watch`` and ``lsp`` block forever when run for real, so their success row
# invokes ``--help`` (documented in the row note): the contract being pinned is
# "the parser accepts the command", not the long-running server loop.
#
# Violations found while writing this table are recorded with the *observed*
# exit code and an ``xfail(strict=True)`` on the violated expectation, so a
# future fix turns the xfail into a hard XPASS failure instead of being missed.
# Known violations (see the final report):
#   * ``pengu time <missing>``  rc 1 but raises CompileFailedError (C4)
#   * ``pengu fmt <missing>``   rc 1 but raises FileNotFoundError (C4)
#   * ``pengu doc --entry <missing>``  rc 0
#   * ``pengu build --entry <missing>`` rc 0 (silently builds the default entry)
#   * ``pengu test --entry <missing>``  rc 0 (silently tests the default entry)

#: Every subcommand, in the order ``pengu --help`` lists them (parser order).
SUBCOMMANDS = [
    "init", "new", "add", "remove", "upgrade", "tree", "metadata", "verify",
    "vendor", "build", "run", "doctor", "gc", "benchmark", "expand", "time",
    "eval", "watch", "test", "check", "update", "bind", "fmt", "clean",
    "lsp", "doc", "assets",
]

#: Rule C4 assertion target: the literal banner a Python traceback starts with.
TRACEBACK_BANNER = "Traceback (most recent call last)"

CLI_TIMEOUT = 600


@dataclass(frozen=True)
class Contract:
    """One subcommand's exit-code contract."""

    success: tuple                  # argv that must exit 0
    effect: str                     # key into _EFFECTS (checked after rc == 0)
    cwd: str = "tmp"                # "tmp" or "proj"
    setup: tuple = ()               # ordered setup tokens (see _prepare)
    missing: tuple | None = None    # argv that omits a required positional
    unknown_flag: bool = True       # run is the documented exception
    nonexistent: tuple | None = None
    nonexistent_cwd: str = "tmp"
    # Exit code observed while writing the table. The contract is "rc != 0"; a
    # recorded 0 is a violation and the row carries xfail_rc.
    nonexistent_rc: int | None = None
    xfail_rc: str = ""              # reason: the rc expectation is violated
    xfail_traceback: str = ""       # reason: C4 is violated (traceback leaks)
    bad_option: tuple | None = None
    requires_git: bool = False      # success row needs git on PATH
    marks: tuple = ()               # requires_cc / requires_runtime
    note: str = ""


_CC = (requires_cc,)
_CC_RT = (requires_cc, requires_runtime)
_SCRIPT = "weave main into int:\n    return 0\n"


@pytest.fixture(autouse=True)
def _isolated_cli_home(tmp_path, monkeypatch):
    """Keeps every CLI invocation away from the developer's ``~/.cache/pengu``.

    ``cli()`` copies ``os.environ`` into the subprocess, so pointing HOME /
    XDG_CACHE_HOME / PENGU_CACHE_DIR at the test's tmp_path is enough to make
    the caches, the script-binary store and ``pengu gc`` operate on scratch
    data. It also applies to the Phase 1 tests above, which only benefit.
    """
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("PENGU_CACHE_DIR", str(home / "pengu-cache"))


def _paths(tmp_path: Path) -> dict:
    """Path placeholders substituted into every row's argv."""
    return {
        "tmp": str(tmp_path),
        "proj": str(tmp_path / "proj"),
        "script": str(tmp_path / "ok.pengu"),
        "unformatted": str(tmp_path / "unformatted.pengu"),
        "header": str(tmp_path / "mini.h"),
        "nope": str(tmp_path / "noexiste.pengu"),
        "nope_dir": str(tmp_path / "noexiste_dir"),
        "nope_h": str(tmp_path / "noexiste.h"),
        "dep": str(tmp_path / "mylib"),
        "csv": str(tmp_path / "bench.csv"),
        "bundle": str(tmp_path / "bundle.c"),
        "bound": str(tmp_path / "mini.d.pengu"),
    }


def _materialize(ctx: dict) -> None:
    """Creates the scratch files every row may refer to."""
    Path(ctx["script"]).write_text(_SCRIPT, encoding="utf-8")
    # Two-space indentation: `pengu fmt` rewrites it to four (observable effect).
    Path(ctx["unformatted"]).write_text(
        "weave main into int:\n  return 0\n", encoding="utf-8")
    Path(ctx["header"]).write_text("int mini_add(int a, int b);\n", encoding="utf-8")
    dep = Path(ctx["dep"])
    dep.mkdir(parents=True, exist_ok=True)
    (dep / "mylib.h").write_text("int mylib_add(int a, int b);\n", encoding="utf-8")


def _git(*argv, cwd=None):
    return subprocess.run(["git"] + list(argv), cwd=None if cwd is None else str(cwd),
                          capture_output=True, text=True)


def _make_git_dependency(ctx: dict, tmp_path: Path) -> None:
    """Installs a git-backed dependency with a real upstream (so `upgrade` works).

    A bare remote + clone is the smallest setup whose ``git pull`` succeeds,
    which is what ``pengu upgrade`` runs for a tracked dependency.
    """
    remote = tmp_path / "gitlib.git"
    work = tmp_path / "gitlib_work"
    res = _git("init", "-q", "--bare", remote)
    assert res.returncode == 0, res.stderr
    res = _git("clone", "-q", str(remote), str(work))
    assert res.returncode == 0, res.stderr
    (work / "gitlib.h").write_text("int gitlib_add(int a, int b);\n", encoding="utf-8")
    for argv in (("add", "."),
                 ("-c", "user.email=contract@test", "-c", "user.name=contract",
                  "commit", "-qm", "init"),
                 ("push", "-q", "-u", "origin", "HEAD")):
        res = _git(*argv, cwd=work)
        assert res.returncode == 0, f"git {argv}: {res.stderr}"
    r = cli(["add", str(work), "-n", "gitlib", "--no-build", "--trust"],
            cwd=ctx["proj"], timeout=CLI_TIMEOUT)
    assert r.returncode == 0, r.stdout + r.stderr


def _prepare(step: str, ctx: dict, tmp_path: Path) -> None:
    """Runs one named setup step for a contract row."""
    if step == "init":
        r = cli(["init", "proj"], cwd=tmp_path, timeout=CLI_TIMEOUT)
        assert r.returncode == 0, r.stdout + r.stderr
    elif step == "dep":
        r = cli(["add", ctx["dep"], "-n", "mylib", "--no-build"],
                cwd=ctx["proj"], timeout=CLI_TIMEOUT)
        assert r.returncode == 0, r.stdout + r.stderr
    elif step == "git-dep":
        _make_git_dependency(ctx, tmp_path)
    elif step == "lock":
        (Path(ctx["proj"]) / "pengu.lock").write_text("version = 1\n", encoding="utf-8")
    elif step == "dirty-build":
        build = Path(ctx["proj"]) / "build"
        build.mkdir(parents=True, exist_ok=True)
        (build / "junk.o").write_text("x", encoding="utf-8")
    else:  # pragma: no cover - a typo in the table must fail loudly
        raise AssertionError(f"unknown setup step {step!r}")


def _json_lines(text: str) -> list:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# --------------------------------------------------------------------------
# Observable effects — never a prose substring (rule C1)
# --------------------------------------------------------------------------

def _effect_init_manifest(ctx, r):
    assert (Path(ctx["tmp"]) / "demo" / "pengu.toml").is_file()


def _effect_new_manifest(ctx, r):
    assert (Path(ctx["tmp"]) / "demo_new" / "pengu.toml").is_file()


def _effect_add_lib(ctx, r):
    assert (Path(ctx["proj"]) / "lib" / "mylib").is_dir()


def _effect_removed_lib(ctx, r):
    assert not (Path(ctx["proj"]) / "lib" / "mylib").exists()


def _effect_upgrade_kept(ctx, r):
    assert (Path(ctx["proj"]) / "lib" / "gitlib" / ".git").is_dir()


def _effect_tree_json(ctx, r):
    payload = _json_lines(r.stdout)[-1]
    assert payload.get("type") == "tree"
    assert isinstance(payload.get("dependencies"), list)


def _effect_metadata_json(ctx, r):
    payload = json.loads(r.stdout)
    assert payload.get("project") == "proj"
    assert isinstance(payload.get("dependencies"), list)


def _effect_rc_only(ctx, r):
    """For commands whose only machine-checkable outcome today is the exit code."""
    return None


def _effect_vendor_dir(ctx, r):
    assert (Path(ctx["proj"]) / "vendor").is_dir()


def _effect_build_artifact(ctx, r):
    assert (Path(ctx["proj"]) / "build" / "proj").is_file()


def _effect_doctor_json(ctx, r):
    payload = json.loads(r.stdout)
    assert payload["problems"] == [], payload["problems"]


def _effect_gc_json(ctx, r):
    payload = json.loads(r.stdout)
    assert payload["removed"] == 0
    assert Path(payload["cache_root"]).is_relative_to(Path(ctx["tmp"]))


def _effect_bench_csv(ctx, r):
    header = Path(ctx["csv"]).read_text(encoding="utf-8").splitlines()[0]
    assert "case" in header and "pengu_build_s" in header, header


def _effect_expand_bundle(ctx, r):
    assert "int main" in Path(ctx["bundle"]).read_text(encoding="utf-8")


def _effect_eval_result(ctx, r):
    assert r.stdout.strip() == "5"


def _effect_test_json(ctx, r):
    payloads = _json_lines(r.stdout)
    assert any(p.get("event") == "end" and p.get("exit_code") == 0
               for p in payloads), payloads


def _effect_check_json(ctx, r):
    payload = _json_lines(r.stdout)[-1]
    assert payload.get("type") == "summary" and payload.get("ok") is True, payload


def _effect_bind_file(ctx, r):
    assert "mini_add" in Path(ctx["bound"]).read_text(encoding="utf-8")


def _effect_fmt_written(ctx, r):
    assert Path(ctx["unformatted"]).read_text(encoding="utf-8") == _SCRIPT


def _effect_clean_build_gone(ctx, r):
    assert not (Path(ctx["proj"]) / "build").exists()


def _effect_doc_index(ctx, r):
    assert (Path(ctx["proj"]) / "docs" / "index.md").is_file()


def _effect_assets_generated(ctx, r):
    assert (Path(ctx["proj"]) / "src" / "arca.pengu").is_file()
    assert (Path(ctx["proj"]) / "build" / "arca_assets.c").is_file()


_EFFECTS = {
    "init_manifest": _effect_init_manifest,
    "new_manifest": _effect_new_manifest,
    "add_lib": _effect_add_lib,
    "removed_lib": _effect_removed_lib,
    "upgrade_kept": _effect_upgrade_kept,
    "tree_json": _effect_tree_json,
    "metadata_json": _effect_metadata_json,
    "rc_only": _effect_rc_only,
    "vendor_dir": _effect_vendor_dir,
    "build_artifact": _effect_build_artifact,
    "doctor_json": _effect_doctor_json,
    "gc_json": _effect_gc_json,
    "bench_csv": _effect_bench_csv,
    "expand_bundle": _effect_expand_bundle,
    "eval_result": _effect_eval_result,
    "test_json": _effect_test_json,
    "check_json": _effect_check_json,
    "bind_file": _effect_bind_file,
    "fmt_written": _effect_fmt_written,
    "clean_build_gone": _effect_clean_build_gone,
    "doc_index": _effect_doc_index,
    "assets_generated": _effect_assets_generated,
}


# --------------------------------------------------------------------------
# The contract table
# --------------------------------------------------------------------------

CONTRACT: dict = {
    "init": Contract(
        success=("init", "demo"), effect="init_manifest",
        missing=("init",),
        bad_option=("init", "--type", "nope", "bad_init"),
    ),
    "new": Contract(
        success=("new", "lib", "demo_new"), effect="new_manifest",
        missing=("new",),
        bad_option=("new", "nope", "bad_new"),
    ),
    "add": Contract(
        success=("add", "{dep}", "-n", "mylib", "--no-build"), effect="add_lib",
        cwd="proj", setup=("init",),
        missing=("add",),
        nonexistent=("add", "{nope_dir}"), nonexistent_cwd="proj", nonexistent_rc=1,
    ),
    "remove": Contract(
        success=("remove", "mylib"), effect="removed_lib",
        cwd="proj", setup=("init", "dep"),
        missing=("remove",),
        nonexistent=("remove", "ghost"), nonexistent_cwd="proj", nonexistent_rc=1,
    ),
    "upgrade": Contract(
        success=("upgrade", "gitlib"), effect="upgrade_kept",
        cwd="proj", setup=("init", "git-dep"), requires_git=True,
        missing=("upgrade",),
        nonexistent=("upgrade", "ghost"), nonexistent_cwd="proj", nonexistent_rc=1,
    ),
    "tree": Contract(
        success=("tree", "--json"), effect="tree_json", cwd="proj", setup=("init",),
    ),
    "metadata": Contract(
        success=("metadata",), effect="metadata_json", cwd="proj", setup=("init",),
    ),
    "verify": Contract(
        success=("verify",), effect="rc_only", cwd="proj", setup=("init", "lock"),
        nonexistent=("verify", "--config", "{nope_dir}"), nonexistent_rc=1,
        note="success needs a pengu.lock; an empty one verifies 0 packages",
    ),
    "vendor": Contract(
        success=("vendor",), effect="vendor_dir", cwd="proj", setup=("init",),
    ),
    "build": Contract(
        success=("build",), effect="build_artifact", cwd="proj", setup=("init",),
        marks=_CC_RT,
        bad_option=("build", "--target-compiler", "nope"),
        nonexistent=("build", "--entry", "{nope}"), nonexistent_cwd="proj",
        nonexistent_rc=0,
        xfail_rc="build --entry <missing> exits 0: it silently builds the default entry",
    ),
    "run": Contract(
        success=("run", "{script}"), effect="rc_only", marks=_CC_RT,
        unknown_flag=False,  # documented exception: run forwards extra args
        bad_option=("run", "--target-compiler", "nope", "{script}"),
        nonexistent=("run", "{nope}"), nonexistent_rc=1,
    ),
    "doctor": Contract(
        success=("doctor", "--json"), effect="doctor_json", marks=_CC_RT,
    ),
    "gc": Contract(
        success=("gc", "--json"), effect="gc_json",
        bad_option=("gc", "--max-age", "nope"),
    ),
    "benchmark": Contract(
        success=("benchmark", "--only", "hello_world", "--repeat", "1",
                 "--csv", "{csv}"),
        effect="bench_csv", marks=_CC_RT,
        bad_option=("benchmark", "--repeat", "nope"),
    ),
    "expand": Contract(
        success=("expand", "{script}", "-o", "{bundle}"), effect="expand_bundle",
        missing=("expand",),
        nonexistent=("expand", "{nope}"), nonexistent_rc=1,
    ),
    "time": Contract(
        success=("time", "{script}"), effect="rc_only", marks=_CC_RT,
        missing=("time",),
        nonexistent=("time", "{nope}"), nonexistent_rc=1,
        xfail_traceback="C4: pengu time on a missing script raises CompileFailedError",
    ),
    "eval": Contract(
        success=("eval", "2 + 3"), effect="eval_result", marks=_CC_RT,
        missing=("eval",),
        bad_option=("eval", "1 +"),
    ),
    "watch": Contract(
        success=("watch", "--help"), effect="rc_only",
        missing=("watch",),
        nonexistent=("watch", "{nope}"), nonexistent_rc=1,
        note="success uses --help because the real command blocks forever",
    ),
    "test": Contract(
        success=("test", "--json"), effect="test_json", cwd="proj", setup=("init",),
        marks=_CC_RT,
        bad_option=("test", "--target-compiler", "nope"),
        nonexistent=("test", "--entry", "{nope}"), nonexistent_cwd="proj",
        nonexistent_rc=0,
        xfail_rc="test --entry <missing> exits 0: it silently tests the default entry",
    ),
    "check": Contract(
        success=("check", "{script}", "--json"), effect="check_json",
        nonexistent=("check", "{nope}"), nonexistent_rc=1,
    ),
    "update": Contract(
        success=("update",), effect="rc_only", cwd="proj", setup=("init",),
    ),
    "bind": Contract(
        success=("bind", "{header}", "--output", "{bound}"),
        effect="bind_file", marks=_CC,
        missing=("bind",),
        nonexistent=("bind", "{nope_h}"), nonexistent_rc=1,
        note="the default path runs the C preprocessor, hence requires_cc",
    ),
    "fmt": Contract(
        success=("fmt", "{unformatted}"), effect="fmt_written",
        bad_option=("fmt", "--indent", "nope", "{script}"),
        nonexistent=("fmt", "{nope}"), nonexistent_rc=1,
        xfail_traceback="C4: pengu fmt on a missing path raises FileNotFoundError",
    ),
    "clean": Contract(
        success=("clean",), effect="clean_build_gone", cwd="proj",
        setup=("init", "dirty-build"),
    ),
    "lsp": Contract(
        success=("lsp", "--help"), effect="rc_only",
        bad_option=("lsp", "--port", "nope"),
        note="success uses --help because the real command blocks forever",
    ),
    "doc": Contract(
        success=("doc",), effect="doc_index", cwd="proj", setup=("init",),
        nonexistent=("doc", "--entry", "{nope}"), nonexistent_cwd="proj",
        nonexistent_rc=0,
        xfail_rc="doc --entry <missing> exits 0 and documents the default entry",
    ),
    "assets": Contract(
        success=("assets",), effect="assets_generated", cwd="proj", setup=("init",),
        nonexistent=("assets", "--config", "{nope_dir}"), nonexistent_rc=1,
    ),
}


# --------------------------------------------------------------------------
# Parser introspection: the table cannot silently drift from the CLI
# --------------------------------------------------------------------------

def _parser_subcommands() -> list:
    """Reads the real subcommand choices out of ``create_cli_parser()``.

    Introspection, not ``--help`` scraping: a new subcommand shows up here even
    if nobody remembers to document it.
    """
    import pengu_project

    parser = pengu_project.create_cli_parser()
    assert parser._subparsers is not None, "the CLI has no subparsers group"
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(actions) == 1, f"expected one subparsers action, got {len(actions)}"
    return list(actions[0].choices)


def test_subcommand_table_matches_the_real_parser():
    """SUBCOMMANDS is the parser's own list, not a hand-copied one."""
    real = _parser_subcommands()
    assert set(SUBCOMMANDS) == set(real), (
        f"table {sorted(set(SUBCOMMANDS) ^ set(real))} does not match the parser"
    )
    assert len(SUBCOMMANDS) == len(real)
    assert len(set(SUBCOMMANDS)) == len(SUBCOMMANDS), "duplicate entry in SUBCOMMANDS"


def test_contract_covers_every_subcommand():
    """Every real subcommand has a contract row, and vice versa."""
    assert set(CONTRACT) == set(SUBCOMMANDS)
    assert len(CONTRACT) == len(SUBCOMMANDS)


def test_every_row_has_a_success_case_and_a_failure_class():
    """Coverage cannot shrink by deleting a failure class from a row."""
    for name in SUBCOMMANDS:
        row = CONTRACT[name]
        assert row.success, f"{name}: no success invocation"
        assert row.effect in _EFFECTS, f"{name}: unknown effect {row.effect!r}"
        classes = [
            ("missing positional", row.missing),
            ("unknown flag", True if row.unknown_flag else None),
            ("nonexistent input", row.nonexistent),
            ("bad option value", row.bad_option),
        ]
        assert any(case for _, case in classes), f"{name}: no failure class at all"
        if row.nonexistent is not None:
            assert row.nonexistent_rc is not None, (
                f"{name}: pin the observed rc for the nonexistent-input case"
            )


# --------------------------------------------------------------------------
# Parametrization helpers
# --------------------------------------------------------------------------

def _params_with(selector):
    """Builds pytest params, applying each row's marks and strict xfail."""
    params = []
    for name in SUBCOMMANDS:
        row = CONTRACT[name]
        marks, argv = selector(row)
        if argv is None:
            continue
        if marks:
            params.append(pytest.param(name, marks=marks, id=name))
        else:
            params.append(pytest.param(name, id=name))
    return params


def _success(row):
    marks = list(row.marks)
    if row.requires_git:
        marks.append(pytest.mark.skipif(shutil.which("git") is None,
                                        reason="git not available"))
    return marks, row.success


def _missing(row):
    return [], row.missing


def _unknown_flag(row):
    # Sentinel: the test builds its own `[sub, "--bogus"]` argv.
    return ([], (True,)) if row.unknown_flag else ([], None)


def _bad_option(row):
    return [], row.bad_option


def _nonexistent_rc(row):
    marks = []
    if row.xfail_rc:
        marks.append(pytest.mark.xfail(strict=True, reason=row.xfail_rc))
    return marks, row.nonexistent


def _nonexistent_traceback(row):
    if row.nonexistent is None or row.nonexistent_rc == 0:
        # A row whose invocation does not fail is covered by the rc test; rule
        # C4 only says a *failure* must not leak a traceback.
        return [], None
    marks = []
    if row.xfail_traceback:
        marks.append(pytest.mark.xfail(strict=True, reason=row.xfail_traceback))
    return marks, row.nonexistent


def _invoke(row, argv_attr, tmp_path, cwd_attr):
    """Runs one row invocation inside the isolated tmp_path sandbox."""
    ctx = _paths(tmp_path)
    _materialize(ctx)
    for step in row.setup:
        _prepare(step, ctx, tmp_path)
    raw = getattr(row, argv_attr)
    argv = [a.format(**ctx) for a in raw]
    cwd = ctx["proj"] if getattr(row, cwd_attr) == "proj" else tmp_path
    return ctx, argv, cli(argv, cwd=cwd, timeout=CLI_TIMEOUT)


def _assert_no_traceback(r, argv):
    combined = r.stdout + r.stderr
    assert TRACEBACK_BANNER not in combined, (
        f"pengu {' '.join(argv)} leaked a Python traceback (rule C4):\n{combined}"
    )


# --------------------------------------------------------------------------
# Success rows
# --------------------------------------------------------------------------

@pytest.mark.parametrize("sub", _params_with(_success))
def test_contract_success(sub, tmp_path):
    """The success invocation exits 0 and leaves the documented effect."""
    row = CONTRACT[sub]
    ctx, argv, r = _invoke(row, "success", tmp_path, "cwd")
    assert r.returncode == 0, (
        f"pengu {' '.join(argv)} exited {r.returncode}\n{r.stdout}\n{r.stderr}"
    )
    _EFFECTS[row.effect](ctx, r)


# --------------------------------------------------------------------------
# Failure classes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("sub", _params_with(_missing))
def test_missing_required_positional_is_usage_error(sub, tmp_path):
    """Dropping a required positional is an argparse usage error (rc 2)."""
    row = CONTRACT[sub]
    argv = list(row.missing)
    r = cli(argv, cwd=tmp_path, timeout=CLI_TIMEOUT)
    assert r.returncode == 2, (
        f"pengu {' '.join(argv)} exited {r.returncode}, expected 2\n{r.stderr}"
    )
    _assert_no_traceback(r, argv)


@pytest.mark.parametrize("sub", _params_with(_unknown_flag))
def test_unknown_flag_is_usage_error(sub, tmp_path):
    """An extra flag on any command but `run` is a usage error (rc 2, item 1.1)."""
    argv = [sub, "--bogus"]
    r = cli(argv, cwd=tmp_path, timeout=CLI_TIMEOUT)
    assert r.returncode == 2, (
        f"pengu {' '.join(argv)} exited {r.returncode}, expected 2\n{r.stderr}"
    )
    _assert_no_traceback(r, argv)


@pytest.mark.parametrize("sub", _params_with(_bad_option))
def test_bad_option_value_fails(sub, tmp_path):
    """A value argparse rejects must fail, and never with a traceback."""
    row = CONTRACT[sub]
    ctx = _paths(tmp_path)
    _materialize(ctx)
    argv = [a.format(**ctx) for a in row.bad_option]
    r = cli(argv, cwd=tmp_path, timeout=CLI_TIMEOUT)
    assert r.returncode != 0, (
        f"pengu {' '.join(argv)} exited 0, expected a failure\n{r.stdout}"
    )
    _assert_no_traceback(r, argv)


@pytest.mark.parametrize("sub", _params_with(_nonexistent_rc))
def test_nonexistent_input_pins_its_exit_code(sub, tmp_path):
    """A missing file/dependency must fail with the contract's exit code.

    ``nonexistent_rc`` records the code actually observed while the table was
    written. When it is 0 the row is a recorded violation (see ``xfail_rc``):
    the assertion below still enforces the contract ("a missing input must
    fail"), so the strict xfail turns into XPASS the day it is fixed.
    """
    row = CONTRACT[sub]
    _, argv, r = _invoke(row, "nonexistent", tmp_path, "nonexistent_cwd")
    if row.nonexistent_rc == 0:
        assert r.returncode != 0, (
            f"pengu {' '.join(argv)} exited 0; the contract requires a failure "
            f"(recorded violation, observed rc 0)\n{r.stdout}\n{r.stderr}"
        )
    else:
        assert r.returncode == row.nonexistent_rc, (
            f"pengu {' '.join(argv)} exited {r.returncode}, "
            f"expected {row.nonexistent_rc}\n{r.stdout}\n{r.stderr}"
        )


@pytest.mark.parametrize("sub", _params_with(_nonexistent_traceback))
def test_nonexistent_input_has_no_traceback(sub, tmp_path):
    """Rule C4: no malformed invocation may raise a Python traceback."""
    row = CONTRACT[sub]
    _, argv, r = _invoke(row, "nonexistent", tmp_path, "nonexistent_cwd")
    assert r.returncode != 0, (
        f"pengu {' '.join(argv)} exited 0\n{r.stdout}"
    )
    _assert_no_traceback(r, argv)
