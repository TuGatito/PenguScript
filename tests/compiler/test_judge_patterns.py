"""``judge`` patterns: nested, alternatives, states, tuples and block ``else``.

2.7.0 widened what a `when` clause can say.  Before it, a pattern was one
literal or one variant name, so a recursive rune could only be matched one level
deep (`when Neg -> …` plus a second `judge` in the body).

The layers:

* the **checker** (`parse_and_check`) validates each pattern against the field's
  type, binds the names it introduces and refuses to count a *narrowed* clause as
  coverage of its variant (E0044 when nothing else covers it);
* the **codegen** is asserted on the shape of the emitted C (the extra
  `is_present` / `is_ok` / `->kind ==` condition, one `case` per alternative) and
  the bundles are compiled with ``-Wall -Wextra -Werror``;
* the **corpus** in ``fixtures/judge_patterns/`` runs each program through the
  CLI and compares stdout.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "judge_patterns"

#: A recursive expression rune: the shape nested patterns exist for.
_RECURSIVE = """
omen ExprKind:
    Literal
    Neg
    Binary

rune Expr:
    kind as ExprKind
    int_value as int
    left as ref to Expr
    right as ref to Expr
"""


def _cases():
    return sorted(p for p in FIXTURES.glob("*.pengu"))


def _read(case: Path) -> str:
    return case.read_text(encoding="utf-8")


def _expected(case: Path) -> str:
    return case.with_suffix(".expected").read_text(encoding="utf-8")


def _write_and_compile(emit_c, tmp_path, source: str) -> str:
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
# Conformance corpus
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
    local = tmp_path / case.name
    local.write_text(_read(case), encoding="utf-8")
    check = pengu_cli("check", str(local), cwd=tmp_path)
    assert check.returncode == 0, check.stdout + check.stderr
    build = pengu_cli("build", "--entry", str(local), cwd=tmp_path)
    assert build.returncode == 0, build.stdout + build.stderr
    assert "warning" not in (build.stdout + build.stderr).lower(), build.stdout + build.stderr


# ---------------------------------------------------------------------------
# Nested patterns
# ---------------------------------------------------------------------------

def test_nested_variant_pattern_is_accepted(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_RECURSIVE + """
weave f with e as ref to Expr into int:
    judge e over kind:
        when Literal with int_value -> int_value
        when Neg with left as Literal -> 0 - 1
        when Neg -> 0
        when Binary -> 0
        else -> -1
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_nested_pattern_is_an_extra_condition(emit_c):
    """`left as Literal` lowers to `… && subj.left->kind == ExprKind_Literal`."""
    c = emit_c(_RECURSIVE + """
weave f with e as ref to Expr into int:
    judge e over kind:
        when Neg with left as Literal -> 1
        when Neg -> 2
        when Literal -> 3
        when Binary -> 4
        else -> 0
""")
    assert "left->kind == ExprKind_Literal" in c, c


def test_nested_pattern_binds_the_field(parse_and_check):
    """The narrowed field is still bound, so a guard can read its contents."""
    errors, _ast, _symbols = parse_and_check(_RECURSIVE + """
weave f with e as ref to Expr into int:
    judge e over kind:
        when Neg with left as Literal, right if (right->int_value) > 0 -> 1
        when Neg with left as Literal, right -> (left->int_value)
        when Neg -> 0
        when Literal -> 0
        when Binary -> 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_nested_pattern_requires_the_same_omen(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

omen Other:
    X

rune Leaf:
    other as Other

rune R:
    kind as Kind
    leaf as Leaf

weave f with r as R into int:
    judge r over kind:
        when A with leaf as X -> 1
        when A -> 2
        when B -> 3
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_nested_pattern_on_a_non_rune_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    n as int

weave f with r as R into int:
    judge r over kind:
        when A with n as Literal -> 1
        when A -> 2
        when B -> 3
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_narrowed_clause_does_not_complete_coverage(parse_and_check):
    """A nested pattern is a test: the variant still needs a covering clause."""
    errors, _ast, _symbols = parse_and_check(_RECURSIVE + """
weave f with e as ref to Expr into int:
    judge e over kind:
        when Neg with left as Literal -> 1
        when Literal -> 2
        when Binary -> 3
""")
    assert "E0044" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]
    assert any("Neg" in str(e) for e in errors if e.code == "E0044")


# ---------------------------------------------------------------------------
# Or-patterns
# ---------------------------------------------------------------------------

def test_or_pattern_covers_every_alternative(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B
    C

weave f with k as Kind into int:
    return judge k:
        when Kind.A | Kind.B -> 1
        when Kind.C -> 2
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_or_pattern_leaves_a_missing_variant_uncovered(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B
    C

weave f with k as Kind into int:
    return judge k:
        when Kind.A | Kind.B -> 1
""")
    e0044 = [e for e in errors if e.code == "E0044"]
    assert e0044, [f"{e.code}: {e}" for e in errors]
    assert any("C" in str(e) for e in e0044), [str(e) for e in e0044]


def test_or_pattern_emits_one_case_per_alternative(emit_c):
    c = emit_c("""
omen Kind:
    A
    B
    C

weave f with k as Kind into int:
    return judge k:
        when Kind.A | Kind.B -> 1
        when Kind.C -> 2
""")
    assert "case Kind_A:" in c and "case Kind_B:" in c and "case Kind_C:" in c, c


def test_or_pattern_with_integer_literals(emit_c):
    """Integer patterns are `switch`able, so each alternative is its own `case`."""
    c = emit_c("""
weave f with n as int into int:
    return judge n:
        when 1 | 2 -> 10
        else -> 20
""")
    assert "case 1:" in c and "case 2:" in c, c


def test_or_pattern_binding_must_exist_in_every_alternative(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A with x as int
    B
    C

weave f with k as Kind into int:
    return judge k:
        when A | B with x -> x
        when C -> 0
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


# ---------------------------------------------------------------------------
# maybe / result field states
# ---------------------------------------------------------------------------

def test_state_patterns_on_maybe_and_result(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    opt as maybe int
    res as result of int to string

weave f with r as R into int:
    judge r over kind:
        when A with opt as some -> 1
        when A with opt as none -> 2
        when A -> 3
        when B with res as ok -> 4
        when B with res as err -> 5
        when B -> 6
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_maybe_state_condition_is_emitted(emit_c):
    c = emit_c("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    opt as maybe int

weave f with r as R into int:
    judge r over kind:
        when A with opt as some -> 1
        when A -> 2
        when B -> 3
""")
    assert "r.opt.is_present" in c, c


def test_wrong_state_name_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    opt as maybe int

weave f with r as R into int:
    judge r over kind:
        when A with opt as ok -> 1
        when A -> 2
        when B -> 3
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


# ---------------------------------------------------------------------------
# Tuple destructuring
# ---------------------------------------------------------------------------

def test_tuple_pattern_binds_the_elements(emit_c):
    c = emit_c("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    pair as (int, bool)

weave f with r as R into int:
    judge r over kind:
        when A with pair as (n, flag) -> n
        when B -> 0
""")
    assert ".pair.v0" in c and ".pair.v1" in c, c


def test_tuple_arity_must_match(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    pair as (int, bool)

weave f with r as R into int:
    judge r over kind:
        when A with pair as (a, b, c) -> 1
        when B -> 0
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_tuple_pattern_on_a_non_tuple_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

rune R:
    kind as Kind
    n as int

weave f with r as R into int:
    judge r over kind:
        when A with n as (a, b) -> 1
        when B -> 0
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_narrowing_is_rejected_in_the_plain_judge_form(parse_and_check):
    """A plain `judge` has no rune to test, so `field as <pattern>` is an error.

    Silently ignoring the pattern made the first clause win whatever the field
    held (`when A with opt as none` then `when A with opt` never reached the
    second clause).
    """
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A with opt as int
    B

weave f with k as Kind into int:
    return judge k:
        when A with opt as none -> 1
        when A with opt -> 2
        when B -> 3
""")
    assert "E0005" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]
    assert any("over" in str(e) for e in errors if e.code == "E0005")


# ---------------------------------------------------------------------------
# `else ->` accepts a block body, like `when`
# ---------------------------------------------------------------------------

def test_else_accepts_an_indented_body(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
omen Kind:
    A
    B

weave f with k as Kind into int:
    return judge k:
        when A -> 1
        else ->
            var fallback as int is 2
            fallback
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


@pytest.mark.slow
def test_stdlib_free_pattern_program_compiles_without_warnings(emit_c, tmp_path):
    """Every pattern shape in one program, under gcc/clang `-Werror`.

    The corpus programs print, and `emit_c` emits a single file (an `import`
    contributes no prototype there); the corpus is covered end-to-end by
    `test_corpus_runs_with_expected_output` and by the CLI build's warning check.
    """
    _write_and_compile(emit_c, tmp_path, _RECURSIVE + """
rune Holder:
    kind as ExprKind
    opt as maybe int
    pair as (int, bool)

weave patterns with e as ref to Expr, h as Holder into int:
    judge e over kind:
        when Literal with int_value -> int_value
        when Neg with left as Literal -> 1
        when Neg -> 2
        when Binary | Literal with left -> 3
        else -> 0
    judge h over kind:
        when Literal with opt as some, pair as (n, flag) -> n
        when Literal with opt as none -> 1
        when Neg -> 2
        when Binary -> 3
        else -> 0
""")
