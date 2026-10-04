"""Tests for `tools/grammar_conflicts.py` (Phase 2 item 2.4 instrumentation).

The tool exists because nine attempts at reducing the grammar's shift/reduce
conflicts failed, all of them after reading a token dump by eye and then editing a
production. The lesson recorded in AUDIT_1.0_FASE2.md §17-§18 is that the token
stream and the conflict *ownership* must be measured first. These tests keep the
instrument honest -- a diagnostic that silently reports the wrong owner is worse
than none, and an earlier version of this one did exactly that.

Rule C1: assertions are about numbers, token names and rule names taken from the
real grammar, never about prose.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "grammar_conflicts.py"


def run_tool(*args, timeout=300):
    r = subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=str(REPO), capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# --tokens
# ---------------------------------------------------------------------------

def test_token_dump_reports_the_structural_stream():
    """`--tokens` must show the indenter's structural tokens for a real program."""
    rc, out = run_tool("--tokens", "weave f into int:\\n  return 1\\n")
    assert rc == 0, out
    for token in ("_NEWLINE", "_INDENT", "_DEDENT"):
        assert token in out, out
    assert "counts:" in out, out


def test_token_dump_reports_the_measured_counts():
    """The counts printed are the ones the indenter really emits.

    For `weave f: return 1` the stream is `_NEWLINE _INDENT _NEWLINE _DEDENT`: two
    newlines (one terminating the signature line, one terminating `return 1`)
    against a single dedent.
    """
    rc, out = run_tool("--tokens", "weave f into int:\\n  return 1\\n")
    assert rc == 0, out
    assert "'_NEWLINE': 2" in out, out
    assert "'_DEDENT': 1" in out, out


@pytest.mark.parametrize("src", [
    "weave f into int:\\n  return 1\\n",
    "weave f into int:\\n  if true:\\n    return 1\\n  return 2\\n",
])
def test_token_dump_warns_that_counts_do_not_prove_unambiguity(src):
    """The tool must push the reader to count production ownership.

    Nine attempts at item 2.4 drew conclusions from the shape of a dump and were
    wrong. The counts are never equal -- `_NEWLINE` terminates every source line
    while `_DEDENT` only closes a block -- so an earlier version of this test that
    asserted a "balanced" case existed was asserting something impossible.
    """
    rc, out = run_tool("--tokens", src)
    assert rc == 0, out
    reminder = [l for l in out.splitlines() if l.startswith("REMINDER:")]
    assert reminder, out
    assert "PRODUCTION" in reminder[0], reminder
    assert "unambiguous" in reminder[0], reminder


# ---------------------------------------------------------------------------
# --conflicts
# ---------------------------------------------------------------------------

def test_conflict_count_matches_the_recorded_budget():
    """`--conflicts` and the budget test must agree.

    If they ever disagree, the grammar moved without the budget being updated --
    exactly the silent growth the budget exists to prevent.
    """
    sys.path.insert(0, str(REPO))
    from tests.test_grammar_strict import _KNOWN_SHIFT_REDUCE_CONFLICTS

    rc, out = run_tool("--conflicts", "--top", "3")
    assert rc == 0, out
    first = out.splitlines()[0]
    assert first.startswith("shift/reduce conflicts: "), out
    reported = int(first.split(":")[1].strip())
    assert reported == _KNOWN_SHIFT_REDUCE_CONFLICTS, (
        f"tool reports {reported}, budget pins {_KNOWN_SHIFT_REDUCE_CONFLICTS}"
    )


def test_conflict_report_names_the_dominant_rule():
    """`return_stmt` owns the largest share, which is what made it the lever."""
    rc, out = run_tool("--conflicts", "--top", "1")
    assert rc == 0, out
    assert "return_stmt" in out, out


def test_conflict_report_groups_by_terminal_for_a_rule():
    """The per-rule terminal breakdown is printed for the requested rule."""
    rc, out = run_tool("--conflicts", "--rule", "bit_add")
    assert rc == 0, out
    assert "terminals conflicting inside 'bit_add'" in out, out
    for terminal in ("STAR", "SLASH", "PERCENT"):
        assert terminal in out, out


# ---------------------------------------------------------------------------
# --actions  (the measurement the nine attempts never made)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rule", ["return_stmt", "bit_add"])
def test_actions_attributes_a_conflict_to_the_reduced_rule(rule):
    """`--actions` names the rule Lark declines to reduce, and says so.

    The owner is the first `<rule ...>` line after the header. An earlier version
    matched the rule name anywhere in the block, which is wrong: every block lists
    several rules, so it reported whichever happened to appear.
    """
    rc, out = run_tool("--actions", "--rule", rule, "--top", "1")
    assert rc == 0, out
    assert f"<{rule}" in out, out
    # Some conflicts list only the reduced rule, so a "shifted" line is not
    # guaranteed -- asserting one was a test bug, not a tool bug.
    assert "reduced (the action being skipped)" in out, out
    assert "shift" in out, out


def test_actions_says_so_when_a_rule_owns_nothing():
    """Negative half: `--actions` must not invent an attribution."""
    rc, out = run_tool("--actions", "--rule", "__definitely_not_a_rule__")
    assert rc == 0, out
    assert "no conflict is owned by" in out, out
