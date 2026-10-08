"""Phase 4 item 4.1 (B4): ``pengu fmt`` must not corrupt indentation.

``format_pengu_source`` decoded the input indentation with the *output*
``tab_size`` (``indent_level = leading_spaces // tab_size``).  Whenever the unit
already used by the file differed from the requested one, every level was
miscomputed: a 2-space source with ``--indent 4`` collapsed to column 0 (with
exit code 0), and a 4-space source with ``--indent 2`` doubled the depth.  The
reformatted file no longer parsed, so the failure was destructive *and* silent.

The unit of the input is a property of the file, not of the invocation, so it is
now detected from the source itself (smallest non-zero run of leading spaces; a
tab counts as one level).

These tests assert *behaviour*: a formatted document must still be valid
PenguScript (``pengu check`` exits 0) and formatting must be idempotent, rather
than comparing the incidental shape of the output text.
"""

import subprocess
import sys

import pytest

from pengu_lsp.formatting import format_pengu_source
from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

TWO_SPACES = "weave main into int:\n  var x as int is 5\n  if x > 0:\n    return x\n  return 0\n"
FOUR_SPACES = "weave main into int:\n    var x as int is 5\n    if x > 0:\n        return x\n    return 0\n"
TABS = "weave main into int:\n\tvar x as int is 5\n\tif x > 0:\n\t\treturn x\n\treturn 0\n"


def _fmt(text: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*PENGU, "fmt", "--stdin", *args],
        input=text, capture_output=True, text=True, timeout=60,
    )


def _check(path) -> subprocess.CompletedProcess:
    """Type-check a file through the CLI (no C compiler needed)."""
    return subprocess.run(
        [*PENGU, "check", str(path)],
        capture_output=True, text=True, timeout=120,
    )


def _indents(text: str) -> list:
    return [
        (len(ln) - len(ln.lstrip(" ")), ln.lstrip(" "))
        for ln in text.splitlines() if ln.strip()
    ]


# ---------------------------------------------------------------------------
# 1-2. The destructive bug itself: source unit != requested unit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source,indent,expected", [
    (TWO_SPACES, "4", TWO_SPACES),
    (FOUR_SPACES, "2", TWO_SPACES),
    (TWO_SPACES, "2", TWO_SPACES),
    (FOUR_SPACES, "4", FOUR_SPACES),
])
def test_indentation_is_rescaled_and_preserved(source, indent, expected):
    """Every line keeps its nesting depth, re-encoded in the requested unit."""
    res = _fmt(source, "--indent", indent)
    assert res.returncode == 0, res.stderr

    target = int(indent)
    src_unit = min(w for w, _ in _indents(source) if w > 0)
    src_levels = [w // src_unit for w, _ in _indents(source)]
    out_lines = _indents(res.stdout)
    out_levels = [w // target for w, _ in out_lines]

    assert out_levels == src_levels, res.stdout
    assert [txt for _, txt in out_lines] == [txt for _, txt in _indents(source)]


# ---------------------------------------------------------------------------
# 3-4. Idempotence in both directions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source,indent", [
    (TWO_SPACES, "2"), (TWO_SPACES, "4"),
    (FOUR_SPACES, "2"), (FOUR_SPACES, "4"),
    (TABS, "4"), (TABS, "2"),
])
def test_fmt_is_idempotent(source, indent):
    once = _fmt(source, "--indent", indent)
    assert once.returncode == 0, once.stderr
    twice = _fmt(once.stdout, "--indent", indent)
    assert twice.returncode == 0, twice.stderr
    assert twice.stdout == once.stdout


# ---------------------------------------------------------------------------
# 5-6. Tabs
# ---------------------------------------------------------------------------


def test_tabs_are_normalized_to_the_requested_unit():
    res = _fmt(TABS, "--indent", "4")
    assert res.returncode == 0, res.stderr
    assert "    var x as int is 5" in res.stdout
    assert "        return x" in res.stdout


def test_tabs_stay_tabs_with_tabs_flag():
    res = _fmt(TWO_SPACES, "--tabs")
    assert res.returncode == 0, res.stderr
    assert "\tvar x as int is 5" in res.stdout
    assert "\t\treturn x" in res.stdout
    twice = _fmt(res.stdout, "--tabs")
    assert twice.stdout == res.stdout


# ---------------------------------------------------------------------------
# 7-8. Non-idiomatic and degenerate sources
# ---------------------------------------------------------------------------


def test_non_idiomatic_unit_is_normalized_not_collapsed():
    """A 3-space source (see tests/tooling/test_fmt_phase3.py) keeps its depth."""
    src = "weave f into int:\n   return 1\n"
    res = _fmt(src, "--indent", "2")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "weave f into int:\n  return 1\n"


def test_anomalous_indent_keeps_the_deeper_line_deeper():
    """{4, 6, 8} spaces: minimum (4) keeps the 8-space line deeper than the 6.

    The anomalous 6-space line is re-encoded as one level (2 spaces) because it
    is not a multiple of the detected unit, but the line below it must stay
    strictly deeper than the line above it.
    """
    src = ("weave main into int:\n"
           "    var x as int is 5\n"
           "      if x > 0:\n"
           "        return x\n"
           "    return 0\n")
    res = _fmt(src, "--indent", "2")
    assert res.returncode == 0, res.stderr
    out = res.stdout.splitlines()
    assert out == [
        "weave main into int:",
        "  var x as int is 5",
        "  if x > 0:",
        "    return x",
        "  return 0",
    ]


@pytest.mark.parametrize("source", ["", "\n", "weave main into int:\n  return 0\n"])
def test_degenerate_sources_do_not_crash(source):
    res = _fmt(source)
    assert res.returncode == 0, res.stderr


# ---------------------------------------------------------------------------
# 9. The contract the bug broke: the output must still be valid PenguScript
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source,indent", [
    (TWO_SPACES, "4"), (FOUR_SPACES, "2"),
    (TWO_SPACES, "2"), (FOUR_SPACES, "4"), (TABS, "4"),
])
def test_formatted_output_is_still_valid_penguscript(tmp_path, source, indent):
    res = _fmt(source, "--indent", indent)
    assert res.returncode == 0, res.stderr
    out = tmp_path / "formatted.pengu"
    out.write_text(res.stdout, encoding="utf-8")
    chk = _check(out)
    assert chk.returncode == 0, f"fmt corrupted the file:\n{res.stdout}\n{chk.stdout}\n{chk.stderr}"


def test_detection_helper_uses_minimum_and_tabs(tmp_path):
    from pengu_lsp.formatting import _detect_source_unit

    assert _detect_source_unit(TWO_SPACES.splitlines(), 4) == 2
    assert _detect_source_unit(FOUR_SPACES.splitlines(), 2) == 4
    assert _detect_source_unit(TABS.splitlines(), 4) == 1
    assert _detect_source_unit(["weave f into int:", "  return 1"], 8) == 2
    # No indented line at all: the fallback keeps the requested output unit.
    assert _detect_source_unit(["weave f into int:", "return 0"], 3) == 3


def test_library_api_default_does_not_collapse():
    """The shared formatter (also used by the LSP) gets the same guarantee."""
    assert format_pengu_source(TWO_SPACES, tab_size=4) == FOUR_SPACES
    assert format_pengu_source(FOUR_SPACES, tab_size=2) == TWO_SPACES
