"""Residual self-hosting-audit cases closed after 3.0.2.

These are the three gaps left open by the first audit pass:

* B1/a — an *imported* generic returning a generic rune, called without
  explicit ``of T`` (the only source of ``T`` is the assignment target);
* B1/b — a generic rune return with no value arguments;
* B2 — a generic ``ritual`` constructor called inside a generic body (with and
  without explicit ``of T``);
* pre-codegen ``\\xNN`` decoding (byte escapes, NUL, neighbouring hex digits).
"""
from __future__ import annotations

from pathlib import Path


def _run_module_program(pengu_cli, tmp_path: Path, module: str, main: str) -> str:
    (tmp_path / "moda.pengu").write_text(module, encoding="utf-8")
    script = tmp_path / "main.pengu"
    script.write_text(main, encoding="utf-8")
    res = pengu_cli("run", "--ephemeral", str(script))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    return res.stdout


def test_b1_imported_generic_without_of_returns_generic_rune(pengu_cli, tmp_path):
    out = _run_module_program(pengu_cli, tmp_path, """
rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T

weave make_box shard T into Box of T:
    return calling Box.empty
""", """
import moda
import std.spark

weave main into int:
    var a as moda.Box of int is calling moda.make_box
    var b as moda.Box of string is calling moda.make_box
    calling spark.println with "ok"
    return 0
""")
    assert "ok" in out


def test_b1_generic_rune_return_without_arguments(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

weave make_box shard T into Box of T:
    return with value is donum T

weave main into int:
    var a as Box of int is calling make_box
    var b as Box of string is calling make_box
    calling spark.println with "ok"
    return 0
""", tag="b1_rune_ret")
    assert out.strip() == "ok"


def test_b2_generic_ritual_in_generic_body_with_of(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T

weave make_box shard T into Box of T:
    return calling Box.empty of T

weave main into int:
    var a as Box of int is calling make_box
    var b as Box of string is calling make_box
    calling spark.println with "ok"
    return 0
""", tag="b2_ritual_generic_explicit")
    assert out.strip() == "ok"


def test_b2_generic_ritual_in_generic_body_without_of(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T

weave make_box shard T into Box of T:
    return calling Box.empty

weave main into int:
    var a as Box of int is calling make_box
    var b as Box of string is calling make_box
    calling spark.println with "ok"
    return 0
""", tag="b2_ritual_generic_implicit")
    assert out.strip() == "ok"


def test_hex_escapes_are_decoded_before_c_codegen(compile_and_run):
    out = compile_and_run("""
import std.spark

weave main into int:
    var nul as string is "\\x00"
    var adjacent as string is "\\x41B"
    var binary as string is "\\x1f\\x8b"
    var text as string is "café \\u{1F600}"
    calling spark.println_int with nul length
    calling spark.println_int with (ord (nul at 0))
    calling spark.println_int with adjacent length
    calling spark.println_int with (ord (adjacent at 0))
    calling spark.println_int with (ord (adjacent at 1))
    calling spark.println_int with binary length
    calling spark.println_int with (ord (binary at 0))
    calling spark.println_int with text length
    return 0
""", tag="hex_escapes")
    assert out.strip().splitlines() == ["1", "0", "2", "65", "66", "2", "31", "10"]


def test_b2_imported_generic_ritual_in_generic_body(pengu_cli, tmp_path):
    out = _run_module_program(pengu_cli, tmp_path, """
rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T
""", """
import moda
import std.spark

weave make_box shard T into moda.Box of T:
    return calling moda.Box.empty

weave main into int:
    var a as moda.Box of int is calling make_box
    var b as moda.Box of string is calling make_box
    calling spark.println with "ok"
    return 0
""")
    assert "ok" in out


def test_b1_imported_generic_without_of_in_generic_body(pengu_cli, tmp_path):
    out = _run_module_program(pengu_cli, tmp_path, """
rune Box shard T:
    value as T

weave make_box shard T into Box of T:
    return with value is donum T
""", """
import moda
import std.spark

weave outer shard T into moda.Box of T:
    return calling moda.make_box

weave main into int:
    var a as moda.Box of int is calling outer
    var b as moda.Box of string is calling outer
    calling spark.println with "ok"
    return 0
""")
    assert "ok" in out


def test_b2_generic_ritual_typed_local_registers_concrete_type(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T

weave make shard T into int:
    var b as Box of T is calling Box.empty
    return 0

weave main into int:
    calling make of int
    calling make of string
    calling spark.println with "ok"
    return 0
""", tag="b2_generic_local_type")
    assert out.strip() == "ok"


def test_b2_generic_ritual_with_value_arguments_in_generic_body(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual make with v as T into Box of T:
        return with value is v

weave make_box shard T with v as T into Box of T:
    return calling Box.make with v

weave main into int:
    var a as Box of int is calling make_box with 7
    var b as Box of string is calling make_box with "x"
    calling spark.println with "ok"
    return 0
""", tag="b2_generic_ritual_args")
    assert out.strip() == "ok"


def test_hex_escapes_in_constants_preserve_nul(compile_and_run):
    out = compile_and_run("""
import std.spark

const ZERO as string is "\x00"
const ADJACENT as string is "\x41B"

weave main into int:
    var z as string is ZERO
    var a as string is ADJACENT
    calling spark.println_int with z length
    calling spark.println_int with (ord (z at 0))
    calling spark.println_int with a length
    return 0
""", tag="hex_const")
    assert out.strip().splitlines() == ["1", "0", "2"]


def test_generic_placeholders_never_reach_the_type_section(compile_and_run):
    """A combined checker pass must not emit `struct Pair_T_U { T first; }`.

    `std.json` uses `oracle.Pair` internally; the multi-module checker used to
    leave `T`/`U` as `BaseType` placeholders in `monomorphized_types`, which
    codegen then materialized.  Importing the module is enough to reproduce.
    """
    out = compile_and_run('''
import std.json
import std.spark

weave main into int:
    var r as result of json.JsonValue to json.JsonError is calling json.parse with r"""{"a": 1}"""
    if r.is_ok:
        calling spark.println with "parsed"
        banish r.value
    banish r
    return 0
''', tag="no_placeholder_types")
    assert out.strip() == "parsed"
