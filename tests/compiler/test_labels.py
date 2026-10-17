"""Labels on ``break`` / ``continue`` — checker, codegen and end-to-end.

``outer: for line in lines:`` names a loop so that ``break outer`` /
``continue outer`` can leave it from any depth.  As with every other construct
here, each layer is tested where it can actually fail:

* the **checker** (unknown label E0004, non-enclosing label E0007, duplicate
  label E0069, bare ``break``/``continue`` unchanged) runs through
  :func:`parse_and_check`, which needs no C toolchain and returns *every*
  diagnostic;
* the **codegen** is asserted on the shape of the emitted C — a ``goto`` plus
  the two anchors, the ``continue`` anchor last inside the body and the
  ``break`` anchor right after the loop — and the same bundles are compiled with
  ``-Wall -Wextra -Werror`` by both gcc and clang when available;
* the **corpus** in ``fixtures/labels/`` runs each program through the real CLI
  and compares its stdout, which is the only level that proves the jump lands
  where the language says it does.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "labels"

#: Two nested loops with every anchor shape in one program.
_TWO_LEVELS = """
weave f into int:
    outer: for i from 0 to 3:
        for j from 0 to 3:
            if j == 1:
                continue outer
            if j == 2:
                break outer
    return 0
"""


def _cases():
    return sorted(p for p in FIXTURES.glob("*.pengu"))


def _read(case: Path) -> str:
    return case.read_text(encoding="utf-8")


def _expected(case: Path) -> str:
    return case.with_suffix(".expected").read_text(encoding="utf-8")


def _write_and_compile(emit_c, tmp_path, source: str) -> str:
    """Emits the bundle for ``source`` and compiles it with every C compiler.

    Returns the emitted C so the caller can also assert on its shape.
    """
    bundle = tmp_path / "bundle.c"
    bundle.write_text(emit_c(source), encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    compilers = [c for c in (shutil.which("gcc"), shutil.which("clang")) if c]
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        res = subprocess.run(
            [cc, "-c", str(bundle), "-o", str(tmp_path / f"{Path(cc).name}.o"),
             "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-function",
             "-I", str(root), "-I", str(root / "build" / "include")],
            capture_output=True, text=True, timeout=600,
        )
        assert res.returncode == 0, (
            f"{cc} rejected the generated C:\n{res.stdout}\n{res.stderr}\n---\n"
            + bundle.read_text(encoding="utf-8")
        )
    return bundle.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Conformance corpus — parse + check
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", _cases(), ids=lambda p: p.stem)
def test_corpus_checks_clean(parse_and_check, case):
    errors, _ast, _symbols = parse_and_check(_read(case), filename=str(case))
    assert errors == [], [f"{e.code}: {e}" for e in errors]


@pytest.mark.slow
@pytest.mark.parametrize("case", _cases(), ids=lambda p: p.stem)
def test_corpus_runs_with_expected_output(compile_and_run, case):
    out = compile_and_run(_read(case), tag=case.stem)
    assert out.strip() == _expected(case).strip()


@pytest.mark.slow
@pytest.mark.parametrize("case", _cases(), ids=lambda p: p.stem)
def test_corpus_cli_check_and_build(pengu_cli, tmp_path, case):
    """``pengu check`` and ``pengu build`` accept every corpus program.

    The program is copied into ``tmp_path`` so the build artefacts land there
    instead of inside the checked-in fixture directory.
    """
    local = tmp_path / case.name
    local.write_text(_read(case), encoding="utf-8")
    check = pengu_cli("check", str(local), cwd=tmp_path)
    assert check.returncode == 0, check.stdout + check.stderr
    build = pengu_cli("build", "--entry", str(local), cwd=tmp_path)
    assert build.returncode == 0, build.stdout + build.stderr
    assert "warning" not in (build.stdout + build.stderr).lower(), build.stdout + build.stderr


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def test_unknown_label_is_undefined_identifier(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    outer: for i from 0 to 3:
        break nope
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_label_of_a_sibling_loop_does_not_enclose(parse_and_check):
    """A label is only a target while the statement is nested inside it."""
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    first: for i from 0 to 3:
        break first
    second: for k from 0 to 3:
        break first
    return 0
""")
    assert "E0007" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_label_from_another_function_is_not_visible(parse_and_check):
    """Labels are function-local: a weave cannot break into its caller's loop."""
    errors, _ast, _symbols = parse_and_check("""
weave inner into int:
    break outer
    return 0

weave outer into int:
    outer: for i from 0 to 3:
        return 0
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


@pytest.mark.parametrize("source", [
    # The classic mistake: the same label on two nested loops.
    """
weave f into int:
    outer: for i from 0 to 3:
        outer: for j from 0 to 3:
            break outer
    return 0
""",
    # ... and on two sibling loops, which would emit two identical C labels.
    """
weave f into int:
    same: for i from 0 to 3:
        break same
    same: for j from 0 to 3:
        break same
    return 0
""",
    """
weave f into int:
    var i as int is 0
    same: while i < 3:
        set i += 1
    same: for k from 0 to 3:
        break same
    return 0
""",
])
def test_duplicate_label_in_one_function_is_e0069(parse_and_check, source):
    errors, _ast, _symbols = parse_and_check(source)
    assert "E0069" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_same_label_in_two_functions_is_fine(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave a into int:
    outer: for i from 0 to 3:
        break outer
    return 0

weave b into int:
    outer: for i from 0 to 3:
        break outer
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_bare_break_outside_a_loop_still_e0007(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    break
    return 0
""")
    assert "E0007" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_labeled_break_outside_any_loop_is_e0004(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    continue outer
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_continue_to_a_while_rechecks_the_condition(parse_and_check):
    """`continue label` is not `break label`: the loop must stay well-formed."""
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var i as int is 0
    counting: while i < 10:
        set i += 1
        if i == 3:
            continue counting
        if i == 6:
            break counting
    return i
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


# ---------------------------------------------------------------------------
# Parse tree
# ---------------------------------------------------------------------------

def test_parser_attaches_the_label_to_the_loop_node(parse_and_check):
    """The `labeled_loop` wrapper is flattened away; the loop carries the name."""
    from lark import Tree

    _errors, ast, _symbols = parse_and_check(_TWO_LEVELS)
    labelled = [n for n in ast.iter_subtrees()
                if isinstance(n, Tree) and getattr(n, "loop_label", None)]
    assert [n.loop_label for n in labelled] == ["outer"]
    assert labelled[0].data == "for_range_stmt"
    assert not any(isinstance(n, Tree) and n.data == "labeled_loop"
                   for n in ast.iter_subtrees())


def test_loop_children_are_unchanged_by_a_label(parse_and_check):
    """A label must not shift the loop's children (checker/codegen index them)."""
    from lark import Tree

    _errors, ast, _symbols = parse_and_check("""
weave f into int:
    outer: for i from 0 to 3 step 2:
        return 0
    return 0
""")
    loop = next(n for n in ast.iter_subtrees()
                if isinstance(n, Tree) and n.data == "for_range_stmt")
    assert str(loop.children[0]) == "i"
    assert len(loop.children) == 5          # var, start, end, step, block


def test_labels_are_not_module_symbols(parse_and_check):
    _errors, _ast, symbols = parse_and_check(_TWO_LEVELS)
    assert symbols.lookup("outer") is None
    assert "outer" not in getattr(symbols, "functions", {})


# ---------------------------------------------------------------------------
# Codegen shape
# ---------------------------------------------------------------------------

def test_goto_and_both_anchors_are_emitted(emit_c):
    c = emit_c(_TWO_LEVELS)
    assert "goto _pengu_label_outer_continue;" in c, c
    assert "goto _pengu_label_outer_break;" in c, c
    assert "_pengu_label_outer_continue: ;" in c, c
    assert "_pengu_label_outer_break: ;" in c, c


def test_anchors_are_unique_and_ordered(emit_c):
    """`continue` last inside the body, `break` after the loop, one each."""
    c = emit_c(_TWO_LEVELS)
    cont = c.index("_pengu_label_outer_continue: ;")
    brk = c.index("_pengu_label_outer_break: ;")
    assert cont < brk, c
    # The continue anchor is the last thing before the outer loop's closing
    # brace; the break anchor follows that brace.
    assert c.count("_pengu_label_outer_continue: ;") == 1, c
    assert c.count("_pengu_label_outer_break: ;") == 1, c
    assert c.count("goto _pengu_label_outer_continue;") == 1, c
    assert c.count("goto _pengu_label_outer_break;") == 1, c
    # Step expression of the labeled for-loop sits between the anchors.
    assert "_pengu_label_outer_continue: ;" in c[:brk]


def test_unlabeled_loops_emit_no_generated_labels(emit_c):
    c = emit_c("""
weave f into int:
    for i from 0 to 3:
        for j from 0 to 3:
            if j == 1:
                continue
            if j == 2:
                break
    return 0
""")
    assert "_pengu_label_" not in c, c


def test_label_on_while_uses_the_same_anchors(emit_c):
    c = emit_c("""
weave f into int:
    var i as int is 0
    counting: while i < 3:
        set i += 1
        if i == 1:
            continue counting
        if i == 2:
            break counting
    return i
""")
    assert "goto _pengu_label_counting_continue;" in c, c
    assert "goto _pengu_label_counting_break;" in c, c


def test_each_anchor_is_emitted_only_when_jumped_to(emit_c):
    """An anchor nothing targets would be `-Wunused-label` under `-Werror`."""
    c = emit_c("""
weave f into int:
    outer: for i from 0 to 3:
        inner: for j from 0 to 3:
            if j == 1:
                continue outer
            if j == 2:
                break inner
    return 0
""")
    # Used: 'continue outer' and 'break inner'.
    assert c.count("_pengu_label_outer_continue: ;") == 1, c
    assert c.count("_pengu_label_inner_break: ;") == 1, c
    # Unused: no 'break outer', no 'continue inner'.
    assert "_pengu_label_outer_break" not in c, c
    assert "_pengu_label_inner_continue" not in c, c
    # A label nobody jumps to at all costs nothing.
    plain = emit_c("""
weave f into int:
    quiet: for i from 0 to 3:
        return 0
    return 0
""")
    assert "_pengu_label_quiet" not in plain, plain


@pytest.mark.slow
def test_generated_c_compiles_without_warnings(emit_c, tmp_path):
    _write_and_compile(emit_c, tmp_path, _TWO_LEVELS)


@pytest.mark.slow
def test_stdlib_free_label_program_compiles_without_warnings(emit_c, tmp_path):
    """The whole feature on one program, under gcc/clang -Werror.

    The corpus programs call `spark.println`, which `emit_c` cannot resolve (it
    emits a single file, so an `import` contributes no prototype); the corpus is
    covered by `test_corpus_runs_with_expected_output` and by the CLI build's
    warning check instead.
    """
    _write_and_compile(emit_c, tmp_path, """
weave scan with lines as list of string into int:
    var seen as int is 0
    outer: for line in lines:
        for ch in line:
            if ch == ";":
                continue outer
            if ch == "}":
                break outer
            set seen += 1
    return seen
""")


# ---------------------------------------------------------------------------
# One-line bodies (collateral fix)
# ---------------------------------------------------------------------------

def test_one_line_else_accepts_break_and_continue(parse_and_check):
    """Regression: `if c: break` parsed but `else: break` was a syntax error.

    `else_block` only had the indented form, so the asymmetry surfaced as soon
    as one-line labeled jumps became idiomatic.
    """
    errors, _ast, _symbols = parse_and_check("""
weave f with xs as list of int into int:
    outer: for x in xs:
        if x > 0: break outer
        else: continue outer
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_break_anchor_precedes_a_materialized_iterable_release(emit_c):
    """A `break label` out of an owning loop must still release it.

    `for v in calling make()` copies the list into a temporary and banishes it
    after the loop; with the `_break` anchor after that call, jumping out of the
    loop would leak.  The anchor is emitted before the release, so both the
    normal exit and the jump run it.
    """
    c = emit_c("""
weave make_list into list of int:
    return [1, 2, 3]

weave scan into int:
    var total as int is 0
    inner: for v in calling make_list:
        if v == 2:
            break inner
        set total += v
    return total
""")
    anchor = c.index("_pengu_label_inner_break: ;")
    release = c.index("pengu_banish_list(&_iter")
    assert anchor < release, c
    # The release is only emitted once: the jump falls through it.
    assert c.count("pengu_banish_list(&_iter") == 1, c


def test_unlabeled_for_over_a_temp_still_releases_once(emit_c):
    c = emit_c("""
weave make_list into list of int:
    return [1, 2, 3]

weave scan into int:
    var total as int is 0
    for v in calling make_list:
        set total += v
    return total
""")
    assert c.count("pengu_banish_list(&_iter") == 1, c
    assert "_pengu_label_" not in c, c
