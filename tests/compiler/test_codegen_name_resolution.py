"""Module-scoped name resolution and private fields.

Three bugs found while building `std.petitio`, all of the same family: a symbol
resolved by its **bare name** against the merged global table instead of the
module the code actually names.

* `scrolls.contains(a: string, b: string)` was emitted as tally's generic
  `contains_string(list, string)` once any module importing `std.tally`
  (`std.json` → `std.arena` → …) was in the program.  A qualified call must win.
* A concrete `compare(a: string, b: string)` was routed through memoria's
  `compare shard T` because both were named `compare`, and the call was then
  rejected with "could not infer type parameter(s) T".
* A private `_field` (LANGUAGE.md §9.1) was type-checked but not *typed* at
  codegen time: the inferrer built for codegen had no filename, so
  `TypeInferrer._is_owner_module` could not match and `b->_items` inferred as
  `None`, breaking `for x in b->_items`.
"""
from __future__ import annotations


def test_qualified_call_wins_over_another_modules_generic(compile_and_run):
    out = compile_and_run("""
import std.spark
import std.scrolls
import std.tally

weave main into int:
    # `string.contains` (concrete) must not resolve to list.contains (generic).
    calling spark.println_bool with (calling scrolls.contains with "abc", "b")
    calling spark.println_bool with (calling scrolls.contains with "abc", "z")

    # The generic still works through its own module.
    var xs as list of int is [10, 20]
    calling spark.println_bool with (calling tally.contains with xs, 20)
    var total as int is calling tally.sum with xs
    calling spark.println_int with total
    banish xs
    return 0
""")
    assert [line for line in out.splitlines() if line] == ["true", "false", "true", "30"], out


def test_concrete_function_wins_over_another_modules_generic(compile_and_run):
    out = compile_and_run("""
import std.spark
import std.memoria
import std.scrolls

weave main into int:
    # memoria also exports `compare`, but over `ref to T`; this call is the
    # concrete string comparator and must keep its own signature.
    calling spark.println_int with (calling scrolls.compare with "a", "b")
    calling spark.println_int with (calling scrolls.compare with "b", "a")
    calling spark.println_int with (calling scrolls.compare with "a", "a")

    # memoria.compare keeps working with its own arguments.
    var x as int is 7
    var y as int is 7
    calling spark.println_int with (calling memoria.compare of int with (sigil of x), (sigil of y), 1)
    return 0
""")
    assert [line for line in out.splitlines() if line] == ["-1", "1", "0", "0"], out


def test_private_fields_are_typed_inside_their_module(compile_and_run):
    out = compile_and_run("""
import std.spark
import std.scrolls

rune Bag:
    label as string
    _items as list of string

rune Config:
    name as string
    _mode as string

weave count_items with b as ref to Bag into int:
    var n as int is 0
    for item in b->_items:
        set n is n + 1
    return n

weave describe with c as ref to Config into string:
    return "{c->name}/{c->_mode}"

weave main into int:
    var items as list of string is ["a", "b", "c"]
    var bag as Bag is:
        label is "bag"
        _items is items
    defer banish items
    calling spark.println_int with (calling count_items with (sigil of bag))

    var cfg as Config is:
        name is "app"
        _mode is "fast"
    var text as string is calling describe with (sigil of cfg)
    calling spark.println with text
    banish text
    return 0
""")
    assert [line for line in out.splitlines() if line] == ["3", "app/fast"], out
