"""Automatic ``Donum`` for runes — the concept rule and its diagnostics.

A ``rune``/``echo`` whose fields all have a zero value *is* ``Donum``: no
``derive Donum`` and no ``bind X with Donum:`` are needed, because ``donum T``
lowers to ``(T){0}`` and a struct is zero-initialisable exactly when its fields
are.  The rule is recursive, follows wrappers (``seal``/``alias``/``frozen``/
``ref``/``array``), and deliberately excludes the container types, whose zeroed
form has no storage.

Layout of this module:

* the **rule** is exercised at the type level and through :func:`parse_and_check`
  (positive cases, the container/reference cases, the generic bound E0049, and
  the ``derive Donum`` E0005);
* the **codegen** asserts ``(T){0}`` and that the negative cases never reach C;
* the **corpus** in ``fixtures/donum/`` runs the programs through the CLI.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "donum"

_POINT = """
rune Point:
    x as int
    y as int
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
# Positive rule: the rune is Donum when every field is
# ---------------------------------------------------------------------------

def test_rune_with_defaultable_fields_is_donum(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_POINT + """
weave f into int:
    var p as Point is donum Point
    return p.x
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_rule_is_recursive(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_POINT + """
rune Wrap:
    p as Point

rune Outer:
    w as Wrap
    n as int

weave f into int:
    var o as Outer is donum Outer
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_container_field_breaks_the_rule(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
rune Container:
    items as list of int

weave f into int:
    var c as Container is donum Container
    return 0
""")
    assert "E0049" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]
    messages = " ".join(str(e) for e in errors)
    assert "Donum" in messages


@pytest.mark.parametrize("declaration", [
    "seal UserId as int",
    "alias Meters as int",
])
def test_seal_and_alias_delegate_to_the_underlying_type(parse_and_check, declaration):
    errors, _ast, _symbols = parse_and_check(declaration + """
weave f into int:
    return 0
""" + declaration.replace("seal UserId as int", "").replace("alias Meters as int", "") + f"""
weave g into int:
    var v as {"UserId" if "UserId" in declaration else "Meters"} is donum {"UserId" if "UserId" in declaration else "Meters"}
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_frozen_and_ref_are_defaultable(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_POINT + """
weave f into int:
    var p as frozen Point is donum (frozen Point)
    var r as ref to Point is donum (ref to Point)
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_array_of_a_donum_rune_is_donum(parse_and_check):
    errors, _ast, _symbols = parse_and_check(_POINT + """
weave f into int:
    var a as array of Point with size 4 is donum (array of Point with size 4)
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_generic_rune_with_a_defaultable_bound_is_donum(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
rune Box shard T:
    value as T

weave zero shard T where T: Donum into Box of T:
    return donum (Box of T)
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_generic_rune_without_the_bound_is_e0049(parse_and_check):
    """`donum (Box of T)` needs `T: Donum`; an unbounded T is not defaultable."""
    errors, _ast, _symbols = parse_and_check("""
rune Box shard T:
    value as T

weave zero shard T into Box of T:
    return donum (Box of T)
""")
    assert "E0049" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


# ---------------------------------------------------------------------------
# Negative rule: containers stay out, with an actionable message
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("type_spelling", [
    "list of int",
    "map of string to int",
    "slice of int",
    "maybe int",
    "result of int to string",
])
def test_containers_do_not_implement_donum(parse_and_check, type_spelling):
    errors, _ast, _symbols = parse_and_check(f"""
weave f into int:
    var v as {type_spelling} is donum ({type_spelling})
    return 0
""")
    assert "E0049" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]
    message = " ".join(str(e) for e in errors)
    assert "does not implement 'Donum'" in message, message
    assert "zero" in message, message


# ---------------------------------------------------------------------------
# `derive Donum` is rejected with the automatic-rule explanation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("keyword", ["rune", "echo"])
def test_derive_donum_is_e0005_with_an_explanation(parse_and_check, keyword):
    errors, _ast, _symbols = parse_and_check(f"""
{keyword} Thing derive Donum:
    x as int

weave f into int:
    return 0
""")
    codes = [e.code for e in errors]
    assert "E0005" in codes, [f"{c}: {e}" for c, e in zip(codes, errors)]
    message = " ".join(str(e) for e in errors)
    assert "automatic" in message, message
    assert "no 'derive' is needed" in message, message


def test_derive_donum_does_not_change_the_type(parse_and_check):
    """The rejected clause must not make the rune non-defaultable as a bonus."""
    errors, _ast, _symbols = parse_and_check(_POINT + """
weave f into int:
    var p as Point is donum Point
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


# ---------------------------------------------------------------------------
# Codegen
# ---------------------------------------------------------------------------

def test_donum_rune_lowers_to_a_compound_literal(emit_c):
    c = emit_c(_POINT + """
weave f into int:
    var p as Point is donum Point
    return p.x
""")
    assert "(Point){0}" in c, c
    # Nothing was generated to make 'Point' defaultable: no derive helper.
    assert "_pengu_donum" not in c, c
    assert "memset" not in c, c


def test_donum_array_lowers_to_a_brace_initialiser(emit_c):
    """An array is not assignable in C, so `(T[N]){0}` cannot initialise it."""
    c = emit_c(_POINT + """
weave f into int:
    var a as array of Point with size 2 is donum (array of Point with size 2)
    return 0
""")
    assert "(Point[2]){0}" not in c, c
    assert "Point a[2] = {0};" in c or "a[2] = {0}" in c, c


@pytest.mark.slow
def test_generated_c_compiles_without_warnings(emit_c, tmp_path):
    _write_and_compile(emit_c, tmp_path, _POINT + """
rune Wrap:
    p as Point

seal UserId as int

weave f into int:
    var p as Point is donum Point
    var w as Wrap is donum Wrap
    var u as UserId is donum UserId
    var a as array of Point with size 2 is donum (array of Point with size 2)
    var a0 as Point is a at 0
    return p.x + w.p.x + u + a0.x
""")


@pytest.mark.slow
def test_stdlib_free_donum_program_compiles_without_warnings(emit_c, tmp_path):
    """`emit_c` emits a single file, so corpus programs' `import` has no effect.

    The corpus is covered end-to-end by `test_corpus_runs_with_expected_output`
    and by the CLI build's warning check.
    """
    _write_and_compile(emit_c, tmp_path, _POINT + """
rune Wrap:
    p as Point

seal UserId as int
alias Meters as int

weave f into int:
    var p as Point is donum Point
    var w as Wrap is donum Wrap
    var u as UserId is donum UserId
    var m as Meters is donum Meters
    var a as array of Point with size 2 is donum (array of Point with size 2)
    var a0 as Point is a at 0
    var b as byte is donum byte
    var c as char is donum char
    return p.x + w.p.x + u + m + a0.x + b + (c to int)
""")


# ---------------------------------------------------------------------------
# Type-level rule (no pipeline): automatic_donum and implements_concept
# ---------------------------------------------------------------------------

def test_automatic_donum_needs_the_symbol_table_for_nominal_fields():
    """A bare nominal placeholder is not decided without symbols."""
    from pengu_parser.pengu_types import INT_TYPE, RuneType, automatic_donum

    field = RuneType(name="Point")          # placeholder: no fields
    assert automatic_donum(field, None) is None
    assert automatic_donum(INT_TYPE, None) is None


def test_containers_are_never_automatically_donum():
    from pengu_parser.pengu_types import (
        INT_TYPE, ListType, MapType, MaybeType, ResultType, SliceType,
        automatic_donum,
    )

    for container in (ListType(INT_TYPE), MapType(INT_TYPE, INT_TYPE),
                      SliceType(INT_TYPE), MaybeType(INT_TYPE),
                      ResultType(INT_TYPE, INT_TYPE)):
        assert automatic_donum(container, None) is False


def test_reference_is_always_donum():
    from pengu_parser.pengu_types import INT_TYPE, RefType, automatic_donum

    assert automatic_donum(RefType(INT_TYPE), None) is True


def test_char_and_byte_are_defaultable_like_their_aliases():
    """Regression: `byte`/`char` lacked `Donum` while `u8`/`i8` had it."""
    from pengu_parser.pengu_types import BaseType, type_implements_builtin_concept

    for spelling in ("char", "byte", "u8", "i8"):
        assert type_implements_builtin_concept(BaseType(spelling), "Donum"), spelling
