"""Regressions for the self-hosting audit (AUDITORIA_AUTO_HOSPEDAJE.md).

Each test fails on 3.0.1 and passes after the corresponding fix.  The C-shape
assertions are intentionally specific: emitting the right *call* while still
defining the unspecialized `_T` template would compile-fail, so both the caller
and the definition matter.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_b1_generic_calls_generic_emits_concrete_specializations(emit_c):
    c = emit_c("""
import std.spark

weave ident shard T with x as T into T:
    return x

weave twice shard T with x as T into T:
    var y as T is calling ident with x
    return y

weave main into int:
    calling spark.println_int with calling twice with 5
    calling spark.println with calling twice with "hi"
    return 0
""", filename="b1.pengu")
    assert "ident_int(" in c
    assert "ident_string(" in c
    assert "ident_T(" not in c


def test_b1_generic_chain_three_levels(compile_and_run):
    out = compile_and_run("""
import std.spark

weave inc shard T with x as T into T:
    return x

weave middle shard T with x as T into T:
    return calling inc with x

weave outer shard T with x as T into T:
    return calling middle with x

weave main into int:
    calling spark.println_int with calling outer with 9
    calling spark.println with calling outer with "chain"
    return 0
""", tag="b1_chain")
    assert out.strip().splitlines() == ["9", "chain"]


def test_b1_generic_method_calls_generic_function(compile_and_run):
    out = compile_and_run("""
import std.spark

weave ident shard T with x as T into T:
    return x

enchanting shard T:
    weave echo_back with x as T into T:
        return calling ident with x

weave main into int:
    var x as int is 4
    calling spark.println_int with (calling x.echo_back with x)
    return 0
""", tag="b1_method")
    assert out.strip() == "4"


def test_b2_ritual_constructor_uses_the_requested_specialization(emit_c, compile_and_run):
    source = """
rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T
    weave ritual make with v as T into Box of T:
        return with value is v
    weave get into T:
        return self->value

weave main into int:
    var a as Box of int is calling Box.empty of int
    var b as Box of string is calling Box.empty of string
    var c as Box of int is calling Box.make of int with 7
    var d as Box of string is calling Box.make of string with "ok"
    return 0
"""
    c = emit_c(source, filename="b2.pengu")
    assert "Box_empty_int(" in c
    assert "Box_empty_string(" in c
    assert "Box_make_int(" in c
    assert "Box_make_string(" in c
    assert "Box_empty_int(); /* stack */" in c
    assert "Box_string b = Box_empty_string();" in c
    # The assignment target also binds the constructor's T when `of T` is
    # omitted (`Box.empty` is a common spelling in tests and docs).
    out = compile_and_run(source, tag="b2")
    assert out.strip() == ""


def test_b2_expected_type_binds_parameterless_constructor(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T

weave main into int:
    var a as Box of int is calling Box.empty
    var b as Box of string is calling Box.empty
    calling spark.println with "ok"
    return 0
""", tag="b2_expected")
    assert out.strip() == "ok"


def test_b2b_qualified_type_constructor(emit_c, compile_and_run):
    source = """
import std.compass
import std.spark

weave main into int:
    var p as compass.Path is calling compass.Path.from_str with "/tmp/x"
    calling spark.println with calling p.name
    return 0
"""
    c = emit_c(source, filename="b2b.pengu")
    assert "compass.Path.from_str" not in c
    assert "Path_from_str(" in c
    out = compile_and_run(source, tag="b2b")
    assert out.strip() == "x"


def test_b7_deep_nesting_is_a_diagnostic_not_a_recursion_crash(pengu_cli, tmp_path):
    deep = "weave main into int:\n    return " + "(" * 1000 + "1" + ")" * 1000 + "\n"
    script = tmp_path / "deep.pengu"
    script.write_text(deep, encoding="utf-8")
    res = pengu_cli("check", str(script))
    text = (res.stdout or "") + (res.stderr or "")
    assert res.returncode != 0
    assert "E0000" in text
    assert "maximum supported depth" in text
    assert "0:0" not in text


def test_b7_legal_nesting_still_compiles(compile_and_run):
    expr = "(" * 200 + "7" + ")" * 200
    out = compile_and_run(f"""
import std.spark
weave main into int:
    calling spark.println_int with {expr}
    return 0
""", tag="b7_ok")
    assert out.strip() == "7"


def test_b10_parse_float_values(compile_and_run):
    out = compile_and_run("""
import std.spark

weave main into int:
    var xs as list of string is ["3.5", "-0.25", "1e3"]
    for s in xs:
        var m as maybe float is calling spark.parse_float with s
        if m is present:
            calling spark.println_float with m.value
        else:
            calling spark.println with "none"
        banish m
    return 0
""", tag="b10")
    lines = out.strip().splitlines()
    assert lines[0] == "3.5"
    assert lines[1] == "-0.25"
    assert lines[2] == "1000"


def test_b11_chr_in_interpolation_is_one_byte(compile_and_run):
    out = compile_and_run("""
import std.spark
weave main into int:
    var s as string is "a{(chr 200)}b"
    calling spark.println_int with s length
    calling spark.println_int with (ord (s at 1))
    banish s
    return 0
""", tag="b11")
    assert out.strip().splitlines() == ["3", "200"]


def test_b12_documented_qualified_examples_compile_and_run(compile_and_run):
    out = compile_and_run("""
import std.compass
import std.chronicle
import std.spark

weave main into int:
    let p as compass.Path is calling compass.Path.from_str with "a/b.txt"
    calling spark.println with calling p.name
    var sw as chronicle.Stopwatch is calling chronicle.Stopwatch.new
    calling spark.println_float with sw.started_at
    return 0
""", tag="b12")
    lines = out.strip().splitlines()
    assert lines[0] == "b.txt"
    assert float(lines[1]) >= 0.0


def test_b9_bundle_generation_is_byte_deterministic(pengu_cli, tmp_path):
    """Two independent compilations produce the same C (B9).

    The current codegen uses insertion-ordered Python dicts, but this test is
    the regression barrier for the future self-hosted codegen: source-order
    emission, stable symbol IDs and no map iteration in output paths.
    """
    source = """
import std.spark
import std.atlas

rune Point:
    x as int
    y as int

weave main into int:
    var m as map of string to int is map of string to int
    calling m.put with "b", 2
    calling m.put with "a", 1
    var ks as list of string is calling m.keys_sorted
    for k in ks:
        calling spark.println with k
        banish k
    banish ks
    banish m
    return 0
"""
    script = tmp_path / "determinism.pengu"
    script.write_text(source, encoding="utf-8")
    first = tmp_path / "first.c"
    second = tmp_path / "second.c"
    for out in (first, second):
        res = pengu_cli("expand", str(script), "-o", str(out))
        assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    assert first.read_bytes() == second.read_bytes()
