"""Regression tests for the compiler work that 2.10.0's data modules needed.

Each case is a *language* bug the three modules exposed, not a stdlib test:

* mutually recursive aggregates through a list must be emitted in an order that
  keeps every by-value field complete;
* a derived ``Nexus`` is deep for containers;
* a derived ``Par`` knows how to compare lists, maps, maybe and algebraic omens;
* a multi-field algebraic variant can be built with a nested ``with``;
* a ``.field`` inside a ``with:`` block resolves against the with-target, not
  against an unrelated local with the same name;
* a plain omen implements the derivable concepts (it is a C enum);
* a user method named ``clone`` no longer collides with the derived ``Imago``
  helper;
* an indented ``judge`` clause body produces the clause value.
"""
from __future__ import annotations

import pytest


def test_recursive_aggregate_orders_by_value(emit_c):
    c = emit_c("""
omen Value derive Nexus, Par:
    Null
    Str with text as string
    Arr with items as list of Value

rune Entry derive Nexus:
    key as string
    value as Value

weave main into int:
    var v as Value is with Str is "x"
    var e as Entry is with key is "k", value is v
    var xs as list of Value is list of Value
    calling xs.push with v
    var a as Value is with Arr is xs
    banish a
    banish e
    return 0
""")
    # Entry embeds Value by value, so Value must be defined first; the list
    # payloads are pointers and must not create a dependency edge.
    assert c.index("struct Value {") < c.index("struct Entry {")
    assert "PenguList items;" in c


def test_nested_multi_field_variant_construction(compile_and_run):
    out = compile_and_run("""
import std.spark

omen M derive Nexus:
    A
    R with id as int, name as string, params as list of int

weave main into int:
    var xs as list of int is [7, 8]
    var m as M is with R is with id is 3, name is "n", params is xs
    var ignored as int is judge m:
        when A ->
            calling spark.println with "FAIL A"
            0
        when R with id, name, params ->
            calling spark.println with "{id} {name} {params.len}"
            0
    banish m
    return 0
""")
    assert "3 n 2" in out, out


def test_with_target_beats_same_named_local(emit_c):
    c = emit_c("""
rune Label derive Nexus:
    span as int
    message as string
    primary as bool

rune Pair:
    first as int
    second as int

weave build into Pair:
    var first as Label is with span is 1, message is "m", primary is true
    var a as int is 4
    var b as int is 5
    var out as Pair is with:
        set .first is a
        set .second is b
    banish first
    return out

weave main into int:
    var p as Pair is calling build
    return p.first
""")
    # The `.first` assignment must copy an int, never `sizeof(Label)`.
    assert "sizeof(Label)" not in c, c
    assert "_with_0.first = a;" in c or ".first = a;" in c


def test_plain_omen_derives_nexus(compile_and_run):
    out = compile_and_run("""
import std.spark

omen Kind:
    A
    B

rune Holder derive Nexus, Par:
    key as string
    kind as Kind

weave main into int:
    var h as Holder is with key is "k", kind is Kind.B
    defer banish h
    calling spark.println with "ok"
    return 0
""")
    assert "ok" in out


def test_derived_nexus_is_deep_for_lists(emit_c):
    c = emit_c("""
rune Bag derive Nexus:
    names as list of string

weave main into int:
    var b as Bag is with names is ["a", "b"]
    banish b
    return 0
""")
    body = c.split("static inline void Bag_nexus(void *p) {", 1)[1].split("\n}", 1)[0]
    assert "pengu_banish_string" in body, body
    assert "pengu_banish_list" in body, body


def test_derived_par_compares_containers(compile_and_run):
    out = compile_and_run("""
import std.spark

omen V derive Par, Nexus:
    N
    S with value as string
    A with items as list of V

rune Box derive Par, Nexus:
    xs as list of int
    v as V
    opt as maybe string

weave main into int:
    var v1 as V is with S is "x"
    var v2 as V is with S is "x"
    var xs1 as list of int is [1, 2]
    var xs2 as list of int is [1, 2]
    var a as maybe string is some "hi"
    var b as maybe string is some "hi"
    var x as Box is with xs is xs1, v is v1, opt is a
    var y as Box is with xs is xs2, v is v2, opt is b
    if x == y:
        calling spark.println with "eq"
    else:
        calling spark.println with "ne"
    banish x
    banish y
    return 0
""")
    assert "eq" in out, out


def test_user_clone_method_does_not_collide(compile_and_run):
    out = compile_and_run("""
import std.spark

rune Point derive Imago, Nexus:
    x as int
    y as int

enchanting Point:
    weave clone into Point:
        return with x is 0, y is 0

weave main into int:
    var p as Point is with x is 1, y is 2
    var q as Point is calling p.clone
    defer banish q
    defer banish p
    calling spark.println with "{p.x} {q.x}"
    return 0
""")
    assert "1 0" in out, out


def test_judge_block_clause_value(compile_and_run):
    out = compile_and_run("""
import std.spark

omen K:
    A
    B

weave main into int:
    var k as K is B
    var n as int is 0
    var got as int is judge k:
        when A ->
            set n is 1
            10
        when B ->
            set n is 2
            20
    calling spark.println with "{n} {got}"
    return 0
""")
    assert "2 20" in out, out
