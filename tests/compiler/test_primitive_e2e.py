"""Phase 2 — end to end: Pengu source, real C compiler, real process.

Marked ``slow`` and skipped without a C compiler (or without a built runtime):
everything here shells out.  Each case is a *program*, so a failure is a real
one — the emitted C did not compile, or it compiled and printed the wrong thing.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


def test_int_clamp_runs(compile_and_run):
    out = compile_and_run("""
import std.spark

enchanting int:
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

weave main into int:
    var x as int is 200
    var y as int is calling x.clamp with 0, 120
    calling spark.println with "{y}"
    return 0
""")
    assert "120" in out


def test_chained_primitive_methods_run(compile_and_run):
    out = compile_and_run("""
import std.spark

enchanting int:
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self
    weave double into int:
        return self + self

weave main into int:
    var x as int is 200
    var y as int is calling x.clamp with 0, 120
    calling spark.println with "{calling y.double}"
    return 0
""")
    assert "240" in out


def test_shard_primitive_runs(compile_and_run):
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave main into int:
    var a as int is 4
    var b as i64 is 7
    if calling a.is_even:
        calling spark.println with "a par"
    if not calling b.is_even:
        calling spark.println with "b impar"
    return 0
""")
    assert "a par" in out
    assert "b impar" in out


def test_char_and_bool_methods_run(compile_and_run):
    out = compile_and_run("""
import std.spark

enchanting char:
    weave to_upper into char:
        if self >= 'a' and self <= 'z':
            return (self - 'a') + 'A'
        return self

enchanting bool:
    weave to_int into int:
        if self:
            return 1
        return 0

weave main into int:
    var c as char is 'q'
    var listo as bool is true
    calling spark.println with "{calling c.to_upper}"
    calling spark.println with "{calling listo.to_int}"
    return 0
""")
    assert "Q" in out
    assert "1" in out


def test_rune_enchanting_still_works(compile_and_run):
    """The regression that matters most: the value rule must not touch runes."""
    out = compile_and_run("""
import std.spark

rune Player:
    name as string
    hp as int

enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

weave main into int:
    var p as Player is with name is "Ada", hp is 50
    calling p.heal with 25
    calling spark.println with "{p.hp}"
    return 0
""")
    assert "75" in out


def test_primitive_methods_are_opt_in_at_runtime(compile_and_run):
    """Two modules, two primitives, one generic body: the happy path of the goal."""
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T
    weave is_odd into bool:
        return not calling self.is_even

enchanting int:
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

weave main into int:
    var edad as int is 200
    var corregida as int is calling edad.clamp with 0, 120
    if calling corregida.is_even and calling corregida.is_odd is false:
        calling spark.println with "ok {corregida}"
    return 0
""")
    assert "ok 120" in out


def test_cross_module_coherence_fails_the_build(pengu_cli, tmp_path):
    """The driver checks both modules with one symbol table, so the collision is
    a real build error (not just a unit-level one)."""
    (tmp_path / "moda.pengu").write_text("""
enchanting int:
    weave clamp with lo as int, hi as int into int:
        return self
""", encoding="utf-8")
    (tmp_path / "modb.pengu").write_text("""
enchanting int:
    weave clamp with lo as int, hi as int into int:
        return self
""", encoding="utf-8")
    entry = tmp_path / "main.pengu"
    entry.write_text("""
import moda
import modb

weave main into int:
    var x as int is 1
    return calling x.clamp with 0, 1
""", encoding="utf-8")
    result = pengu_cli("check", str(entry))
    assert result.returncode != 0, result.stdout
    assert "E0047" in (result.stdout + result.stderr)


def test_concept_binding_on_a_primitive_still_runs(compile_and_run):
    """`std.atlas` implements `Ordered` for every primitive with `bind`, and its
    methods take `ref to int` (`essence of self`).  The Phase 2 value rule must
    not change that: this is the shipped path, exercised as a program."""
    out = compile_and_run("""
import std.spark
import std.atlas

weave main into int:
    var a as int is 1
    var b as int is 2
    calling spark.println with "{calling a.cmp with b}"
    return 0
""")
    assert "-1" in out


def test_shard_method_tuple_return_runs(compile_and_run):
    """`div_rem` on a `shard T` receiver: the product struct is really defined."""
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Integrum:
    weave div_rem with other as T into (T, T):
        return (self / other), (self % other)

weave main into int:
    var a as int is 17
    var b as i64 is 17
    let (q, r) is calling a.div_rem with 5
    let (s, t) is calling b.div_rem with 5
    calling spark.println with "{q} {r} {s to int} {t to int}"
    return 0
""")
    assert "3 2 3 2" in out


def test_local_receiver_monomorphization_runs(compile_and_run):
    """`gcd`-style delegation on a local of type `T` links for every width."""
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Integrum:
    weave double_abs into T:
        var n as T is self
        if n < donum T:
            set n is 0 - n
        return n + n

    weave twice_doubled into T:
        var n as T is self
        return calling n.double_abs

weave main into int:
    var a as int is -7
    var b as i16 is -7
    var c as u8 is 7
    calling spark.println with "{calling a.twice_doubled} {calling b.twice_doubled to int} {calling c.twice_doubled}"
    return 0
""")
    assert "14 14 14" in out


def test_f64_literal_precision_runs(compile_and_run):
    """The `f64` annotation really buys double precision at runtime."""
    out = compile_and_run("""
import std.spark

weave main into int:
    var pi as f64 is 3.141592653589793
    var expected as f64 is 6.283185307179586
    var got as f64 is pi * 2.0
    var d as f64 is got - expected
    if d < 0.0:
        set d is 0.0 - d
    calling spark.println with "{d < 1e-15}"
    var casted as f64 is (3.141592653589793 to f64)
    var d2 as f64 is casted - pi
    if d2 < 0.0:
        set d2 is 0.0 - d2
    calling spark.println with "{d2 < 1e-15}"
    return 0
""")
    assert "true\ntrue" in out, out
