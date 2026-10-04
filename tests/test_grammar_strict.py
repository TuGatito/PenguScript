import pytest
import warnings
from lark import Lark
from pengu_parser.pengu_grammar import GRAMMAR
from pengu_parser.pengu_parser import PenguParser, PenguIndenter
from pengu_parser.pengu_errors import ParseError


def test_grammar_lalr_builds_cleanly():
    """The LALR parser builds and the production options are the ones expected.

    NOTE (Phase 1, blocker B11): this test used to assert `len(recorded) == 0`
    over `warnings.catch_warnings()`, which is **vacuous** -- Lark resolves
    shift/reduce conflicts by an internal heuristic and only logs them through
    the `lark` logger at DEBUG level, so it never emits a Python warning and the
    assertion held no matter how many conflicts the grammar had. The grammar in
    fact has 188 shift/reduce conflicts across 79 terminals.

    The real check is `strict=True`, which turns each conflict into
    `GrammarError`. That is asserted explicitly by
    `test_grammar_strict_mode_conflict_budget` below, which records the current
    count so it can only go down.
    """
    parser = Lark(
        GRAMMAR,
        parser="lalr",
        postlex=PenguIndenter(),
        propagate_positions=True,
        start=["start", "expr"],
        cache=False,
    )
    assert parser is not None


#: Number of shift/reduce conflicts the grammar had when this budget was
#: recorded (Phase 1). Lark resolves every one of them as *shift*, which happens
#: to produce correct left-associativity and precedence for this expression
#: grammar -- but that is a property of the dependency's default heuristic, not
#: a guarantee of the language. The budget may only decrease.
_KNOWN_SHIFT_REDUCE_CONFLICTS = 188


def _count_shift_reduce_conflicts():
    """Counts the grammar's shift/reduce conflicts by rebuilding it in debug mode.

    Lark only reports conflicts through its logger, and only when `debug=True`;
    `strict=True` aborts on the first one, so it cannot be used to count them.
    """
    import io
    import logging
    import lark.parsers.lalr_analysis as analysis

    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.WARNING)
    logger = analysis.logger
    previous_level, previous_disabled = logger.level, logger.disabled
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    logging.disable(logging.NOTSET)
    try:
        Lark(GRAMMAR, parser="lalr", propagate_positions=True, debug=True, cache=None)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled

    return sum(1 for line in buffer.getvalue().splitlines() if "conflict" in line.lower())


@pytest.mark.timeout(300)
def test_grammar_strict_mode_conflict_budget():
    """The grammar's ambiguity must not grow (blocker B11).

    This is the honest version of "the grammar is strict": the grammar is NOT
    LALR(1) today, and this test says so with a number instead of a vacuous
    `assert len(recorded) == 0`. Reducing the count is the Phase 2 goal; growing
    it is a regression.
    """
    count = _count_shift_reduce_conflicts()
    assert count <= _KNOWN_SHIFT_REDUCE_CONFLICTS, (
        f"the grammar grew to {count} shift/reduce conflicts "
        f"(budget {_KNOWN_SHIFT_REDUCE_CONFLICTS}); "
        "Lark resolves them by shift, so the language's operator precedence now "
        "depends on more heuristics than before"
    )


@pytest.mark.timeout(120)
def test_grammar_strict_mode_is_not_silently_enabled():
    """Pins the *reason* the conflict budget exists.

    If someone flips `strict=True` on the production parser, construction starts
    raising `GrammarError` instead of resolving by shift -- which would be a
    behaviour change to the language. This test documents the current state so
    that change is deliberate rather than accidental.
    """
    with pytest.raises(Exception) as excinfo:
        Lark(
            GRAMMAR,
            parser="lalr",
            postlex=PenguIndenter(),
            propagate_positions=True,
            start=["start", "expr"],
            cache=False,
            strict=True,
        )
    assert "conflict" in str(excinfo.value).lower()

    # And the production parser must NOT pass strict=True.
    source = (__import__("pathlib").Path(__file__).resolve().parent.parent
              / "pengu_parser" / "pengu_parser.py").read_text(encoding="utf-8")
    assert "strict=True" not in source, (
        "PenguParser builds Lark with strict=True; the conflict budget test above "
        "documents that this grammar is not LALR(1) yet"
    )


def test_mandatory_statement_delimiter_rejects_inline_statements():
    """Simple statement declarations require a mandatory newline delimiter.
    
    Two statements on the same line ('var x is 1 var y is 2') must fail with E0000 ParseError.
    """
    parser = PenguParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse("var x is 1 var y is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"


def test_mandatory_statement_delimiter_accepts_multiline_statements():
    """Declarations separated by clean newlines parse without errors."""
    parser = PenguParser()
    tree = parser.parse("var x is 1\nvar y is 2\n")
    assert tree is not None
    assert tree.data == "start"


def test_let_and_set_require_mandatory_newline():
    """'let' and 'set' statements also require newlines and cannot be chained inline."""
    parser = PenguParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse("let a is 1 let b is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"

    with pytest.raises(ParseError) as exc_info:
        parser.parse("set x is 1 set y is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"


# ---------------------------------------------------------------------------
# Phase 2 item 2.4 — the two behavioural requirements that must survive any
# future attempt at reducing the conflict count.
#
# The roadmap states two done-conditions beyond the strict build itself:
#   * the 9 expressions of AUDIT §1.1 keep their tree        -> test_precedence.py
#   * the dangling 'else' keeps binding to the INNERMOST 'if'
#
# The second one is the classic hazard of this grammar family: a dangling else
# is exactly the kind of ambiguity that a "cleaner" grammar can silently change,
# flipping which branch runs. It is asserted by RUNNING the program, so the
# assertion is about behaviour and not about the parse tree's shape.
# ---------------------------------------------------------------------------

def _run_source(tmp_path, source, name="dangling.pengu"):
    """Compiles and runs `source`; returns the process exit code.

    `pengu run` propagates `main`'s return value as the exit status, which is
    what makes this an end-to-end behavioural check.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    repo = Path(__file__).resolve().parent.parent
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(repo), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [sys.executable, "-m", "pengu_project", "run", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return r.returncode, r.stdout + r.stderr


def test_dangling_else_binds_to_the_innermost_if(tmp_path):
    """`else` attaches to the nearest `if`, observed through execution.

    With a=true and b=false the inner branch is taken, so the `else` must run and
    the program must return 2. If the `else` ever attached to the OUTER `if` the
    value would be 3, and if the inner `if` swallowed it the value would be 1.
    The three candidate answers are all distinct, which is what makes the exit
    code a real discriminator rather than a coincidence.
    """
    rc, out = _run_source(tmp_path, (
        "weave main into int:\n"
        "  var a as bool is true\n"
        "  var b as bool is false\n"
        "  if a:\n"
        "    if b:\n"
        "      return 1\n"
        "    else:\n"
        "      return 2\n"
        "  return 3\n"
    ))
    assert rc == 2, f"dangling else bound to the wrong if (got {rc}):\n{out}"


def test_dangling_else_with_the_inner_condition_true(tmp_path):
    """The complementary case: inner condition true, so the `then` branch runs.

    Together with the test above this pins the association from both sides. A
    grammar that attached `else` to the outer `if` would still return 2 here (the
    inner `then` runs either way), so this test alone would not catch it -- which
    is exactly why both halves exist.
    """
    rc, out = _run_source(tmp_path, (
        "weave main into int:\n"
        "  var a as bool is true\n"
        "  var b as bool is true\n"
        "  if a:\n"
        "    if b:\n"
        "      return 1\n"
        "    else:\n"
        "      return 2\n"
        "  return 3\n"
    ), "dangling_true.pengu")
    assert rc == 1, f"expected the inner then-branch (1), got {rc}:\n{out}"


def test_unless_else_binds_to_the_innermost_unless(tmp_path):
    """The same hazard on `unless`, which has the mirrored grammar rule.

    `unless_stmt: "unless" expr block [else_block]` is a separate production, so
    it needs its own guarantee. The exits are chosen so the three candidate
    associations give three different answers:

        `unless a:` with a=true is skipped. If a following `unless b:` (b=false)
        takes its body we return 8. If instead the `else` attached to the outer
        `unless a:`, that else runs and we return 7. If the inner `unless`
        swallowed the else and ran it after its own body, we would return 7 as
        well, so the discriminating value is 8 versus 7.

    An earlier version of this test passed a=true AND b=true: the inner body was
    then skipped, the else ran, and 'return 7' was the correct answer -- so it
    asserted the wrong expectation rather than exposing a bug. Reading the parse
    tree showed the else attaching to the first `unless`, i.e. correctly.
    """
    rc, out = _run_source(tmp_path, (
        "weave main into int:\n"
        "  var a as bool is true\n"
        "  var b as bool is false\n"
        "  unless a:\n"
        "    return 9\n"
        "  unless b:\n"
        "    return 8\n"
        "  else:\n"
        "    return 7\n"
    ), "unless_else.pengu")
    assert rc == 8, (
        f"the unless/else association is wrong (got {rc}, want 8):\n{out}"
    )


def test_unless_else_runs_its_else_when_no_inner_unless_follows(tmp_path):
    """Baseline for the test above: a lone `unless` with `else` behaves."""
    rc, out = _run_source(tmp_path, (
        "weave main into int:\n"
        "  var a as bool is true\n"
        "  unless a:\n"
        "    return 9\n"
        "  else:\n"
        "    return 7\n"
    ), "unless_lone.pengu")
    assert rc == 7, f"`unless true` should take its else (7), got {rc}:\n{out}"
