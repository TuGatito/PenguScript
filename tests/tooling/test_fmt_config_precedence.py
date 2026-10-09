"""Phase 4 item 4.3: ``.pengufmt.toml``, its precedence and the fmt walker.

Adding a formatting config to the repository turned ``--indent N`` into a silent
no-op: ``fmt_files`` resolved ``cfg["tab_size"]`` *before* the CLI value, and
because argparse gave ``--indent`` a non-``None`` default it could not tell "the
user asked for 4" from "the user did not pass the flag". The contract is now

    --indent N (explicit)  >  .pengufmt.toml  >  default 4

and the walker no longer descends into ``build/`` and friends (gitignored,
ephemeral build output), so ``pengu fmt --check .`` is a usable gate: it must be
clean over the repository.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

SRC_2SP = "weave main into int:\n  var x as int is 5\n  return 0\n"
SRC_4SP = "weave main into int:\n    var x as int is 5\n    return 0\n"


def _fmt(path, *args, cwd=None):
    return subprocess.run(
        [*PENGU, "fmt", str(path), *args],
        capture_output=True, text=True, timeout=60, cwd=str(cwd) if cwd else None,
    )


def _indent_of(path, needle="var x"):
    for line in path.read_text(encoding="utf-8").splitlines():
        if needle in line:
            return len(line) - len(line.lstrip())
    raise AssertionError(f"{needle!r} not found in {path}")


@pytest.fixture()
def proj(tmp_path):
    """A project directory with a 2-space ``.pengufmt.toml``.

    The CLI runs from ``tmp_path/sub`` so the upward config walk finds the
    temporary config first and never the repository's own file.
    """
    (tmp_path / ".pengufmt.toml").write_text("[formatting]\ntab_size = 2\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    return tmp_path, sub


# ---------------------------------------------------------------------------
# Precedence: explicit flag > config > hardcoded default
# ---------------------------------------------------------------------------


def test_indent_flag_beats_config(proj):
    root, sub = proj
    f = root / "a.pengu"
    f.write_text(SRC_2SP, encoding="utf-8")
    res = _fmt(f, "--indent", "4", cwd=sub)
    assert res.returncode == 0, res.stderr
    assert _indent_of(f) == 4


def test_config_wins_over_default(proj):
    root, sub = proj
    f = root / "b.pengu"
    f.write_text(SRC_4SP, encoding="utf-8")
    res = _fmt(f, cwd=sub)          # no --indent: the config's 2 must apply
    assert res.returncode == 0, res.stderr
    assert _indent_of(f) == 2


def test_hardcoded_default_used_without_config(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "c.pengu"
    f.write_text(SRC_2SP, encoding="utf-8")
    res = _fmt(f, cwd=sub)
    assert res.returncode == 0, res.stderr
    assert _indent_of(f) == 4


def test_tabs_flag_beats_config(proj):
    """`--tabs` is explicit too: it must not be overridden by insert_spaces."""
    root, sub = proj
    f = root / "d.pengu"
    f.write_text(SRC_4SP, encoding="utf-8")
    res = _fmt(f, "--tabs", cwd=sub)
    assert res.returncode == 0, res.stderr
    assert f.read_text(encoding="utf-8").splitlines()[1].startswith("\t")


def test_config_insert_spaces_wins_when_no_flag(proj):
    root, sub = proj
    (root / ".pengufmt.toml").write_text(
        "[formatting]\ntab_size = 2\ninsert_spaces = false\n", encoding="utf-8"
    )
    f = root / "e.pengu"
    f.write_text(SRC_2SP, encoding="utf-8")
    res = _fmt(f, cwd=sub)          # no --tabs: use_tabs from config applies
    assert res.returncode == 0, res.stderr
    assert f.read_text(encoding="utf-8").splitlines()[1].startswith("\t")


def test_stdin_indent_flag_beats_config(proj):
    root, sub = proj
    res = subprocess.run(
        [*PENGU, "fmt", "--stdin", "--indent", "4"],
        input=SRC_2SP, capture_output=True, text=True, timeout=60, cwd=str(sub),
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.splitlines()[1].startswith("    var x")


# ---------------------------------------------------------------------------
# Walker: ephemeral build output is not source
# ---------------------------------------------------------------------------


def test_walker_skips_build_and_caches(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text("weave main into int:\n  return 0\n", encoding="utf-8")
    for skipped in ("build", "dist", "__pycache__", ".venv", "node_modules"):
        d = tmp_path / skipped
        d.mkdir()
        (d / "gen.pengu").write_text("weave main into int:\n  return 0\n", encoding="utf-8")

    res = _fmt(tmp_path / "src", "--check", cwd=tmp_path)
    assert res.returncode == 1, "the source file should be reported"

    from pengu_project import _collect_pengu_files

    found = _collect_pengu_files([str(tmp_path)])
    assert [os.path.basename(p) for p in found] == ["main.pengu"], found
    assert not any(os.sep + "build" + os.sep in p for p in found)


def test_explicit_file_inside_skipped_dir_is_honoured(tmp_path):
    from pengu_project import _collect_pengu_files

    d = tmp_path / "build"
    d.mkdir()
    target = d / "explicit.pengu"
    target.write_text("weave main into int:\n  return 0\n", encoding="utf-8")
    assert _collect_pengu_files([str(target)]) == [str(target)]


# ---------------------------------------------------------------------------
# The phase criterion: the repository is clean
# ---------------------------------------------------------------------------


def test_repository_sources_are_clean_under_pengu_fmt():
    res = subprocess.run(
        [*PENGU, "fmt", "--check", str(REPO)],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, (
        "pengu fmt --check <repo> reports changes:\n"
        + "\n".join(ln for ln in res.stdout.splitlines() if "would" in ln)
    )


def test_repository_config_is_honoured():
    from pengu_lsp.formatting import load_format_config

    assert load_format_config(str(REPO / "pengu_project.py"))["tab_size"] == 4
    assert load_format_config(str(REPO / "std" / "tally.pengu"))["tab_size"] == 4
