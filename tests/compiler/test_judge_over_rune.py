"""``judge <rune> over <discriminant>:`` — checker, codegen and end-to-end.

The feature has three layers and each is tested at the level that can actually
fail:

* the **checker** (subject/discriminant/binding validation, privacy and
  exhaustiveness) is exercised with :func:`parse_and_check`, which needs no C
  toolchain and reports every diagnostic instead of the first one;
* the **codegen** asserts on the *shape* of the emitted C (``switch``,
  ``default``, ``_judge_subj_N``, ``(void)var;``, ``const``) with
  :func:`emit_c`, and the same bundles are compiled with ``-Wall -Wextra
  -Werror`` so an unused binding or an uninitialized result is a test failure;
* the **corpus** under ``fixtures/judge_over/`` runs each program through the
  real CLI and compares its stdout, which is the only level that proves the
  feature end to end.

The corpus is the conformance suite for this construct: one program per case
listed in the 2.5.0 plan, each with a ``.expected`` file.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "judge_over"


def _cases():
    return sorted(p for p in FIXTURES.glob("*.pengu"))


def _read(case: Path) -> str:
    return case.read_text(encoding="utf-8")


def _expected(case: Path) -> str:
    return case.with_suffix(".expected").read_text(encoding="utf-8")


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
    # `_program_output` keeps the blank separator the driver prints after its
    # "Running" line, so compare stripped text (as the other e2e suites do).
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

_RUNE_PRELUDE = """
omen Kind:
    A
    B
    C

rune R:
    kind as Kind
    v as int
    other as int
"""


@pytest.mark.parametrize("source,code", [
    # 1. plain `judge` on a rune is not a valid subject.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    return judge r:
        when A -> 1
        when B -> 2
        when C -> 3
""", "E0005"),
    # 2. the `over` field must exist.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over nonexistent:
        when A -> 1
        when B -> 2
        when C -> 3
""", "E0013"),
    # 3. the `over` field must be an omen.
    ("""
rune R:
    kind as int
    v as int

weave f with r as R into int:
    judge r over kind:
        when 1 -> 1
        else -> 2
""", "E0005"),
    # 4. a `with` name must be a field of the rune.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with nonexistent -> 1
        when B -> 2
        when C -> 3
""", "E0013"),
    # 5. a private `over` field is rejected from outside its rune.
    ("""
omen Kind:
    A
    B

rune R:
    _kind as Kind
    v as int

weave f with r as R into int:
    judge r over _kind:
        when A -> 1
        when B -> 2
""", "E0043"),
    # 6. missing variants with no `else`.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A -> 1
        when B -> 2
""", "E0044"),
    # 7. guards do not count towards exhaustiveness.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with v if v > 0 -> 1
        when B -> 2
        when C -> 3
""", "E0044"),
    # 9. the bindings are immutable `let`s.
    (_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with v ->
            set v is 5
            v
        when B -> 2
        when C -> 3
""", "E0006"),
])
def test_diagnostics(parse_and_check, source, code):
    errors, _ast, _symbols = parse_and_check(source)
    assert code in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_nested_pattern_is_a_syntax_error():
    """`when Binary with left as Literal ->` is not part of 2.5.0."""
    from pengu_parser.pengu_errors import ParseError
    from pengu_parser.pengu_parser import PenguParser

    with pytest.raises(ParseError) as excinfo:
        PenguParser().parse(_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with v as Literal -> 1
        when B -> 2
        when C -> 3
""")
    assert excinfo.value.code == "E0000"


def test_guarded_variant_without_else_reports_the_variant(parse_and_check):
    """A guarded clause does not cover its variant for exhaustiveness."""
    errors, _ast, _symbols = parse_and_check(_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with v if v > 0 -> 1
        when B -> 2
        when C -> 3
""")
    e0044 = [e for e in errors if e.code == "E0044"]
    assert e0044, [f"{e.code}: {e}" for e in errors]
    assert "A" in str(e0044[0])


def test_guard_does_not_cover_even_with_all_variants_listed(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_RUNE_PRELUDE + """
weave f with r as R into int:
    judge r over kind:
        when A with v if v > 0 -> 1
        when B -> 2
        when C -> 3
""")
    assert any(e.code == "E0044" for e in errors)


def test_over_is_a_soft_keyword(parse_and_check):
    """`over` stays an ordinary identifier outside a `judge` header."""
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var over as int is 5
    return over
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_over_can_name_the_discriminant_field(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
rune R:
    over as K
    v as int

omen K:
    A
    B

weave f with r as R into int:
    judge r over over:
        when A with v -> v
        when B -> 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_non_rune_subject_message_points_at_plain_judge(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f with x as int into int:
    return judge x over kind:
        when A -> 1
        else -> 2
""")
    e0005 = [e for e in errors if e.code == "E0005"]
    assert e0005
    assert "rune" in str(e0005[0])


def test_incompatible_clause_types_are_reported(parse_and_check):
    """A `void` clause cannot share a value `judge` with `int` clauses."""
    errors, _ast, _symbols = parse_and_check(_RUNE_PRELUDE + """
weave stop into void:
    return

weave f with r as R into int:
    judge r over kind:
        when A with v -> v
        when B -> 2
        when C -> 3
        else -> calling stop
""")
    assert any("incompatible return types" in str(e) for e in errors), [
        f"{e.code}: {e}" for e in errors
    ]


# ---------------------------------------------------------------------------
# Codegen shape
# ---------------------------------------------------------------------------

_VALUE_RUNE = """
rune R:
    kind as K
    a as int
    b as int

omen K:
    X
    Y
"""


def test_switch_is_emitted_without_default_when_exhaustive(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a -> a
        when Y with b -> b
""")
    assert "switch (r.kind)" in c, c
    assert "case K_X:" in c and "case K_Y:" in c, c
    assert "default:" not in c, c


def test_default_is_emitted_when_else_is_present(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a -> a
        else -> 0
""")
    assert "default:" in c, c


def test_unused_binding_is_voided(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a, b -> a
        when Y with b -> b
""")
    assert "(void)b;" in c, c


def test_complex_subject_is_materialized(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave make into R:
    return with kind is K.X, a is 1, b is 2

weave main into int:
    return judge (calling make) over kind:
        when X with a -> a
        when Y -> 0
""")
    assert "_judge_subj_" in c, c
    assert "switch (_judge_subj_" in c, c


def test_ref_subject_uses_arrow(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as ref to R into int:
    return judge r over kind:
        when X with a -> a
        when Y -> 0
""")
    assert "switch (r->kind)" in c, c
    assert "int32_t a = r->a;" in c, c


def test_frozen_subject_makes_bindings_const(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as frozen R into int:
    return judge r over kind:
        when X with a -> a
        when Y -> 0
""")
    assert "const int32_t a = r.a;" in c, c


def test_guards_nest_inside_the_case(emit_c):
    c = emit_c(_VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a if a > 0 -> 1
        when X -> 2
        when Y -> 3
""")
    assert "if (a > 0)" in c, c
    assert "case K_X:" in c, c


def test_string_valued_discriminant_uses_comparison(emit_c):
    c = emit_c("""
omen K with string:
    X is "x"
    Y is "y"

rune R:
    kind as K
    a as int

weave f with r as R into int:
    return judge r over kind:
        when X with a -> a
        when Y -> 0
""")
    assert "pengu_string_equal" in c, c


# ---------------------------------------------------------------------------
# Emitted C compiles warning-free
# ---------------------------------------------------------------------------

def _write_and_compile(emit_c, tmp_path, source: str) -> None:
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
             # The shape sources define a weave but no caller, so the C compiler
             # correctly calls it unused; that is a property of the test source,
             # not of the generated switch.
             "-Wno-unused-function",
             "-I", str(root), "-I", str(root / "build" / "include")],
            capture_output=True, text=True, timeout=600,
        )
        assert res.returncode == 0, (
            f"{cc} rejected the generated C:\n{res.stdout}\n{res.stderr}\n---\n"
            + bundle.read_text(encoding="utf-8")
        )


_COMPILE_SOURCES = {
    "value_exhaustive": _VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a -> a
        when Y with b -> b
""",
    "ref_recursive": """
rune E:
    kind as EK
    v as int
    left as ref to E

omen EK:
    Lit
    Neg

weave f with e as ref to E into int:
    judge e over kind:
        when Lit with v -> v
        when Neg with left -> 0 - (calling f with left)
""",
    "guards_and_else": _VALUE_RUNE + """
weave f with r as R into int:
    judge r over kind:
        when X with a if a > 0 -> a
        when Y with b -> b
        else -> 0
""",
    "unused_and_materialized": _VALUE_RUNE + """
weave make into R:
    return with kind is K.X, a is 1, b is 2

weave main into int:
    return judge (calling make) over kind:
        when X with a, b -> a
        when Y -> 0
""",
    "frozen": _VALUE_RUNE + """
weave f with r as frozen R into int:
    return judge r over kind:
        when X with a -> a
        when Y -> 0
""",
    "nested_judge_blocks": """
rune R:
    kind as K
    sub as S

omen K:
    A
    B

omen S:
    P
    Q

weave f with r as R into int:
    judge r over kind:
        when A ->
            judge r.sub:
                when P -> 1
                when Q -> 2
        when B -> 3
""",
}


@pytest.mark.parametrize("case_id", sorted(_COMPILE_SOURCES))
def test_emitted_c_is_warning_free(emit_c, tmp_path, case_id):
    """Representative programs compile under `-Wall -Wextra -Werror`.

    Warnings only appear with a C compiler, which `emit_c` does not need, so
    this is the test that would catch an unused binding or an uninitialized
    result.  The sources are import-free on purpose: ``emit_c`` emits a bundle
    for the one file it is given, so a ``std`` import would fail on a missing
    prototype for reasons unrelated to ``judge over``.
    """
    _write_and_compile(emit_c, tmp_path, _COMPILE_SOURCES[case_id])


def test_strict_c99_judge_over_compiles(emit_c, tmp_path, monkeypatch):
    """`--strict-c99` hoists the switch instead of a GNU statement expression."""
    monkeypatch.setenv("PENGU_STRICT_C99", "1")
    source = _VALUE_RUNE + """
weave f with r as R into int:
    return judge r over kind:
        when X with a -> a
        when Y with b -> b

weave main into int:
    var r as R is with kind is K.X, a is 1, b is 2
    return calling f with r
"""
    c = emit_c(source)
    assert "switch (r.kind)" in c, c
    _write_and_compile(emit_c, tmp_path, source)
