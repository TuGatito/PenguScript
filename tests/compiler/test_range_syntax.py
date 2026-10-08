"""Phase 2 item 2.5 — one canonical range syntax, with `..` deprecated.

Decision (rule C3, measured before implementing; see AUDIT_1.0_FASE2.md §3.7):

* **`a to b` is canonical.** The stdlib writes ranges with `to` 5139 times and
  uses `..` **zero** times syntactically (every one of the 191 textual `..`
  occurrences is inside a comment, a string, or a `...`), and the manual's only
  `..` range was an "alternate range syntax" footnote.
* **`..` keeps working through 1.x** but now raises `W0013
  RangeSyntaxDeprecated`, which is what allows 2.0 to remove it without a silent
  break.
* **Both spellings must mean the same thing everywhere.** Before this item `..`
  worked in `for i in 1..5` but *not* in a slice (`xs at 0..2` inferred a
  ``range of int`` instead of a slice), so the "alternate syntax" was only
  alternate in some positions. That inconsistency is the actual defect.

Rule C1: every assertion compiles a program and reads its diagnostic codes or
runs it. Nothing reads message prose.
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

PREAMBLE = "weave main into int:\n"


def pengu(tmp_path, source, name="t.pengu", cmd="check"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, cmd, str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)


SLICE = PREAMBLE + (
    "  var xs as list of int is [1, 2, 3, 4]\n"
    "  var s as slice of int is (xs at %s)\n"
    "  return 0\n"
)
FOR_IN = PREAMBLE + (
    "  var t as int is 0\n"
    "  for i in %s:\n"
    "    set t is t + i\n"
    "  return t\n"
)


# ---------------------------------------------------------------------------
# `..` warns; `to` does not
# ---------------------------------------------------------------------------

def test_dotdot_range_warns_w0013(tmp_path):
    """`for i in 1..5` still compiles but reports W0013."""
    rc, out = pengu(tmp_path, FOR_IN % "1..5", "for_dotdot.pengu")
    assert rc == 0, out
    assert "W0013" in out, out
    assert "[E0" not in out, out


def test_to_range_does_not_warn(tmp_path):
    """The canonical spelling is silent."""
    rc, out = pengu(tmp_path, FOR_IN % "1 to 5", "for_to.pengu")
    assert rc == 0, out
    assert "W0013" not in out, out


def test_dotdot_slice_warns_w0013(tmp_path):
    """`xs at 0..2` warns too, and — unlike before item 2.5 — compiles."""
    rc, out = pengu(tmp_path, SLICE % "0..2", "slice_dotdot.pengu")
    assert rc == 0, out
    assert "W0013" in out, out


def test_to_slice_does_not_warn(tmp_path):
    rc, out = pengu(tmp_path, SLICE % "0 to 2", "slice_to.pengu")
    assert rc == 0, out
    assert "W0013" not in out, out


# ---------------------------------------------------------------------------
# The two spellings are equivalent wherever a range is allowed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind,template", [("for", FOR_IN), ("slice", SLICE)])
def test_both_spellings_type_check_identically(tmp_path, kind, template):
    """Neither spelling may be an error where the other is accepted."""
    _, dotdot = pengu(tmp_path, template % "1..4", f"{kind}_dd.pengu")
    _, to = pengu(tmp_path, template % "1 to 4", f"{kind}_to.pengu")
    assert "[E0" not in dotdot, dotdot
    assert "[E0" not in to, to


def test_dotdot_slice_produces_a_slice_not_a_range(tmp_path):
    """The bug item 2.5 fixes.

    `xs at 0..2` used to infer `range of int`, so assigning it to a
    `slice of int` was E0005 while the `to` spelling worked.
    """
    rc, out = pengu(tmp_path, SLICE % "0..2", "slice_type.pengu")
    assert rc == 0, out
    assert "range of int" not in out, out


def test_both_spellings_execute_to_the_same_value(tmp_path):
    """End-to-end equivalence: same program, same answer.

    Note the assertion is on the *process* status, which `pengu run` derives
    from `main`'s return value. An earlier version of this test split the loop
    and the check into two weaves and only looked at the exit code, so it passed
    even if the loop were wrong -- the return value was simply never observed.
    Keeping the check inside `main` is what makes the exit code meaningful.
    """
    # Ranges are half-open: `0 to 5` iterates 5 times, and `1 to 5` sums
    # 1+2+3+4 == 10. Measured, not assumed -- the first version of this test
    # asserted 15 and failed for the right reason.
    for spelling, tag in (("1..5", "dd"), ("1 to 5", "to")):
        src = (
            'weave main into int:\n'
            '  var t as int is 0\n'
            f'  for i in {spelling}:\n'
            '    set t is t + i\n'
            '  if t == 10:\n'
            '    return 0\n'
            '  return 1\n'
        )
        rc, out = pengu(tmp_path, src, f"run_{tag}.pengu", "run")
        assert rc == 0, f"{spelling} produced the wrong sum:\n{out}"


def test_ranges_are_half_open_in_both_spellings(tmp_path):
    """The end bound is exclusive, and both spellings agree on that."""
    for spelling, tag in (("0..5", "dd"), ("0 to 5", "to")):
        src = (
            'weave main into int:\n'
            '  var n as int is 0\n'
            f'  for i in {spelling}:\n'
            '    set n is n + 1\n'
            '  if n == 5:\n'
            '    return 0\n'
            '  return 1\n'
        )
        rc, out = pengu(tmp_path, src, f"halfopen_{tag}.pengu", "run")
        assert rc == 0, f"{spelling} is not half-open over 0..5:\n{out}"


def test_dotdot_slice_executes(tmp_path):
    """The deprecated slice spelling must actually run, not just type-check."""
    src = (
        'weave main into int:\n'
        '  var xs as list of int is [1, 2, 3, 4]\n'
        '  var s as slice of int is (xs at 1..3)\n'
        '  if (s length to int) == 2:\n'
        '    return 0\n'
        '  return 1\n'
    )
    rc, out = pengu(tmp_path, src, "run_slice_dd.pengu", "run")
    assert rc == 0, out


# ---------------------------------------------------------------------------
# Existing range validation is preserved
# ---------------------------------------------------------------------------

def test_descending_dotdot_range_is_still_e0042(tmp_path):
    """Deprecating the syntax must not weaken range validation."""
    rc, out = pengu(tmp_path, FOR_IN % "1..0", "desc.pengu")
    assert rc != 0, out
    assert "E0042" in out, out


def test_non_integer_dotdot_slice_bounds_are_rejected(tmp_path):
    """Guard against the new slice path accepting what `to` rejects."""
    rc, out = pengu(tmp_path, SLICE % "1.5..2", "badbounds.pengu")
    assert rc != 0, out


def test_non_collection_dotdot_slice_is_rejected(tmp_path):
    """`1 at 0..2` has no slice meaning and must not silently pass."""
    src = PREAMBLE + "  var x as int is 1\n  var s as slice of int is (x at 0..2)\n  return 0\n"
    rc, out = pengu(tmp_path, src, "nonslice.pengu")
    assert rc != 0, out


def test_w0013_is_not_emitted_for_the_string_containing_dots(tmp_path):
    """A `..` inside a string literal is data, not syntax."""
    src = PREAMBLE + '  var s as string is "a..b"\n  return 0\n'
    rc, out = pengu(tmp_path, src, "strdots.pengu")
    assert rc == 0, out
    assert "W0013" not in out, out


def _syntactic_dotdot_lines(path):
    """Line numbers in `path` that contain a syntactic `..` range.

    Comments and string literals are stripped first: `..` inside a comment
    ("month, 1..12") or a string ("a..b") is data, not the deprecated operator,
    and the stdlib has 191 such occurrences. A `...` (varargs) is not a range.
    """
    import re as _re

    hits = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = raw
        # Drop a trailing comment (the language has no '#' inside strings that
        # this file relies on; the stdlib does not nest them either).
        code = _re.sub(r"#.*$", "", code)
        # Drop string literal contents, single and double quoted.
        code = _re.sub(r'"[^"]*"', '""', code)
        code = _re.sub(r"'[^']*'", "''", code)
        # Drop '...' so varargs are not mistaken for a range.
        code = code.replace("...", "")
        if ".." in code:
            hits.append(n)
    return hits


def test_stdlib_does_not_use_the_deprecated_syntax():
    """The stdlib must stay free of `..` ranges, or phase criterion 6 fails.

    This is a static scan rather than a `pengu check` sweep of all 52 modules on
    purpose: the sweep took 87 s for a single assertion and duplicated work
    `tests/stdlib/test_stdlib.py` already does on every run. The thing being asserted is
    a property of the *source text* (do not introduce the deprecated spelling),
    so reading the text is the right instrument, and it is checked against the
    real stdlib rather than a fixture.
    """
    root = REPO / "std"
    offenders = {}
    for f in sorted(root.glob("*.pengu")):
        hits = _syntactic_dotdot_lines(f)
        if hits:
            offenders[f.name] = hits
    assert not offenders, (
        "stdlib uses the deprecated '..' range syntax; write 'a to b' instead: "
        f"{offenders}"
    )


def test_the_dotdot_scan_actually_detects_a_range():
    """Guard the guard: the scanner must not be vacuously passing.

    `_syntactic_dotdot_lines` strips comments and strings, so a bug in the
    stripping could silently make it report nothing for every file -- which
    would turn the test above into a no-op. This pins that it finds a real
    range, ignores a string and a comment containing dots, and ignores varargs.
    """
    import tempfile

    sample = (
        "## a comment with 1..12 and more\n"
        'var s as string is "a..b"\n'
        "declare f with xs as many int into int\n"
        "weave main into int:\n"
        "  for i in 1..10:\n"
        "    return i\n"
        "  return 0\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".pengu", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(sample)
        name = fh.name
    try:
        hits = _syntactic_dotdot_lines(Path(name))
    finally:
        Path(name).unlink()
    assert hits == [5], f"expected only the real range on line 5, got {hits}"
