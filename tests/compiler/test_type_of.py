"""``type of expr`` — the compile-time type-name operator.

``type of`` never evaluates its operand: it reads the *static* type and lowers to
a borrowed string literal holding the canonical PenguScript spelling.  The three
levels are tested separately:

* the **checker** (the operand is still type-checked, the operator is a soft
  keyword, unknown identifiers inside the operand are E0004) through
  :func:`parse_and_check`;
* the **codegen** asserts that the C is a ``pengu_string_from_cstr("…")``
  literal with no runtime call and no evaluation of the operand, and compiles
  the bundle with ``-Wall -Wextra -Werror``;
* the **corpus** in ``fixtures/type_of/`` runs the programs through the CLI and
  compares their stdout.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "type_of"


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
# Soft keyword / grammar
# ---------------------------------------------------------------------------

def test_type_is_still_an_ordinary_identifier(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var type as int is 5
    return type + 1
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_size_is_still_an_ordinary_identifier(parse_and_check):
    """Regression: the old anonymous ``"size"`` literal made this unparsable."""
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var size as int is 5
    return size
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_size_of_still_works(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    return size of int
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_operand_can_be_named_type(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var type as int is 5
    var s as string is type of type
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_operand_is_still_type_checked(parse_and_check):
    """Not evaluating the operand does not mean not checking it."""
    errors, _ast, _symbols = parse_and_check("""
weave f into int:
    var s as string is type of undefined_thing
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_operand_may_be_a_call(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave get into int:
    return 1

weave f into int:
    var s as string is type of (calling get)
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_type_of_is_a_string(parse_and_check):
    """The operator yields `string`, so it composes with `==` and interpolation."""
    errors, _ast, _symbols = parse_and_check("""
weave f with a as int, b as i64 into bool:
    return (type of a) == "int"
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_type_of_result_type_is_string(parse_and_check):
    errors, _ast, symbols = parse_and_check("""
weave f with a as int into string:
    return type of a
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]
    # The weave returns string, so the operator must have type string for the
    # return statement to type-check at all.


# ---------------------------------------------------------------------------
# Canonical names (unit level, no pipeline)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spelling,canonical", [
    ("int", "int"), ("i32", "int"), ("int32", "int"), ("int32_t", "int"),
    ("i64", "i64"), ("int64_t", "i64"), ("long", "i64"),
    ("byte", "byte"), ("u8", "byte"), ("uint8", "byte"), ("uint8_t", "byte"),
    ("i8", "i8"), ("int8_t", "i8"),
    ("i16", "i16"), ("u16", "u16"), ("u32", "u32"), ("uint", "u32"),
    ("u64", "u64"), ("ulong", "u64"),
    ("usize", "size_t"), ("size_t", "size_t"),
    ("isize", "isize"), ("intptr_t", "isize"),
    ("float", "float"), ("f32", "float"),
    ("f64", "f64"), ("double", "f64"),
    ("char", "char"), ("bool", "bool"), ("string", "string"),
    ("void", "void"), ("opaque", "opaque"),
])
def test_canonical_primitive_names(spelling, canonical):
    from pengu_parser.pengu_types import BaseType, canonical_type_name

    assert canonical_type_name(BaseType(spelling)) == canonical


def test_canonical_composite_names_are_recursive():
    from pengu_parser.pengu_types import (
        ArrayType, BaseType, FrozenType, INT_TYPE, ListType, MapType, MaybeType,
        RefType, ResultType, SliceType, canonical_type_name,
    )

    assert canonical_type_name(RefType(ListType(INT_TYPE))) == "ref to list of int"
    assert canonical_type_name(ListType(RefType(BaseType("Point")))) == "list of ref to Point"
    assert canonical_type_name(MapType(BaseType("string"), INT_TYPE)) == "map of string to int"
    assert canonical_type_name(MaybeType(INT_TYPE)) == "maybe int"
    assert canonical_type_name(ResultType(INT_TYPE, BaseType("string"))) == "result of int to string"
    assert canonical_type_name(SliceType(INT_TYPE)) == "slice of int"
    assert canonical_type_name(ArrayType(INT_TYPE, 4)) == "array of int with size 4"
    assert canonical_type_name(FrozenType(BaseType("Point"))) == "frozen Point"


def test_canonical_rune_name_uses_the_local_base_name():
    from pengu_parser.pengu_types import INT_TYPE, RuneType, canonical_type_name

    assert canonical_type_name(RuneType(name="Point")) == "Point"
    # A monomorphized generic reports the PenguScript spelling, not `Box_int`.
    box = RuneType(name="Box_int", base_name="Box", type_args=[INT_TYPE])
    assert canonical_type_name(box) == "Box of int"


# ---------------------------------------------------------------------------
# Codegen shape
# ---------------------------------------------------------------------------

def test_type_of_emits_a_borrowed_string_literal(emit_c):
    c = emit_c("""
rune Point:
    x as int

weave f with p as Point into string:
    return type of p
""")
    assert 'pengu_string_from_cstr("Point")' in c, c
    # No runtime reflection helper and no runtime type call of any kind.
    assert "pengu_type" not in c, c
    assert "typeof" not in c, c


def test_type_of_does_not_call_the_operand(emit_c):
    c = emit_c("""
weave side_effect into int:
    return 7

weave f into string:
    return type of (calling side_effect)
""")
    assert 'pengu_string_from_cstr("int")' in c, c
    # The call is only referenced by its definition, never invoked.
    assert "side_effect()" not in c, c


def test_type_of_in_a_generic_is_resolved_per_instantiation(emit_c):
    c = emit_c("""
weave describe shard T with x as T into string:
    return "t={type of x}"

weave use into int:
    var a as string is calling describe with 42
    var b as string is calling describe with "hi"
    return 0
""")
    assert 'pengu_string_from_cstr("int")' in c, c
    assert 'pengu_string_from_cstr("string")' in c, c


def test_type_of_does_not_evaluate_inside_a_generic(emit_c):
    c = emit_c("""
weave describe shard T with x as T into string:
    return type of x

weave use into int:
    var a as string is calling describe with 42
    return 0
""")
    assert "_pengu_string" not in c.replace("pengu_string_from_cstr", ""), c


@pytest.mark.slow
def test_generated_c_compiles_without_warnings(emit_c, tmp_path):
    _write_and_compile(emit_c, tmp_path, """
rune Point:
    x as int

weave describe shard T with x as T into string:
    return "valor de tipo {type of x}"

weave f with p as Point into string:
    return "p={p.x} has {type of p}"

weave g into int:
    var xs as list of Point is list of Point
    var s as string is type of xs
    if s == "list of Point" and xs.length == 0:
        return 1
    return 0
""")


@pytest.mark.slow
def test_stdlib_free_type_of_program_compiles_without_warnings(emit_c, tmp_path):
    """`emit_c` emits one file, so an `import std.spark` has no prototype here.

    The corpus programs print, so they are covered end-to-end by
    `test_corpus_runs_with_expected_output` and by the CLI build's warning
    check rather than by this gcc/clang `-Werror` pass.
    """
    _write_and_compile(emit_c, tmp_path, """
rune Point:
    x as int
    y as int

weave kind with p as Point into string:
    return "{p.x}:{p.y} is {type of p}"

weave nested into int:
    var xs as list of ref to Point is list of ref to Point
    var n as int is 0
    if type of xs == "list of ref to Point" and xs.length == 0:
        return 1
    if (type of n) == "int" and n == 0:
        return 2
    return 0
""")


# ---------------------------------------------------------------------------
# Ownership: the result is borrowed, so `banish` is a no-op
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_banish_of_a_type_name_is_a_safe_no_op(compile_and_run):
    """The result is borrowed, so `banish` must not free the literal.

    `pengu_banish_string` clears the struct it is given (defensively, for every
    shape), but it frees only when `is_owned` is set.  A borrowed literal is
    therefore released without touching the static buffer: no crash, no
    double-free, and the string is re-initialised like any other banished value.
    """
    out = compile_and_run("""
import std.spark

weave main into int:
    var s as string is type of 42
    calling spark.println with "before={s}"
    banish s
    calling spark.println with "after_len={s.length}"
    return 0
""", tag="typeof_banish")
    assert out.strip().splitlines() == ["before=int", "after_len=0"]


def test_type_of_in_a_generic_is_not_shadowed_by_a_caller_local(emit_c):
    """Regression: the name reported was the *caller's* same-named local.

    The const folder used to fold `type of x` with the code generator's symbol
    table, which no longer tracks locals (the generator keeps them in
    `local_vars`), so `x` resolved to `main`'s `var x as int` and every
    instantiation reported `int`.  The codegen now infers with its own context.
    """
    c = emit_c("""
weave describe shard T with x as T into string:
    return "tipo {type of x}"

weave main into int:
    var x as int is 5
    var a as string is calling describe with 42
    var b as string is calling describe with "hi"
    return 0
""")
    assert 'pengu_string_from_cstr("int")' in c, c
    assert 'pengu_string_from_cstr("string")' in c, c


@pytest.mark.slow
def test_generic_type_of_e2e_with_a_shadowing_caller_local(compile_and_run):
    out = compile_and_run("""
import std.spark

weave describe shard T with x as T into string:
    return "tipo {type of x}"

weave main into int:
    var x as int is 5
    calling spark.println with (calling describe with 42)
    calling spark.println with (calling describe with "hi")
    return 0
""", tag="typeof_shadow")
    assert out.strip().splitlines() == ["tipo int", "tipo string"]


@pytest.mark.slow
def test_type_of_folds_into_a_const(compile_and_run):
    """The checker *may* fold it (its symbol table tracks locals); a const works."""
    out = compile_and_run("""
import std.spark

const NAME as string is type of 42

weave main into int:
    calling spark.println with "const={NAME}"
    return 0
""", tag="typeof_const")
    assert out.strip() == "const=int"
