# std/tally.pengu - The Tally (Lists)
# Read-only utilities for dynamic `list of int` collections: emptiness
# checks and scalar reductions (sum, max, min).
#
# Ownership / memory model:
#   * The helpers never allocate, mutate or consume the list they receive:
#     each one takes a `list of int`, reads it through `.len` / element
#     indexing and returns a plain int, so the caller keeps full ownership
#     of the list and may `banish` it afterwards. Empty lists are handled
#     explicitly (see the per-function notes below).
#
# Usage:
#   import std.tally
#   import std.spark
#   var nums as list of int is calling spark.range with 1, 10, 1
#   var total as int is calling tally.sum with nums
#   var hi as int is calling tally.max_val with nums

import std.spark

# ----------------------------------------------------------------------------
# Predicates
# ----------------------------------------------------------------------------

# Returns true when `l` holds no elements (its length is 0). The list is
# only read, never modified.
weave is_empty with l as list of int into bool:
    return (calling l.len) == 0

# ----------------------------------------------------------------------------
# Reductions
# ----------------------------------------------------------------------------

# Returns the arithmetic sum of every element in `l`. An empty list sums to
# 0. Values must fit in `int` - overflow is not checked here.
weave sum with l as list of int into int:
    var total as int is 0
    var i as int is 0
    var n as int is calling l.len
    while i < n:
        set total is total + (l at i)
        set i is i + 1
    return total

# Returns the largest element of `l`. An empty list yields 0; otherwise the
# scan starts from element 0, so a single-element list returns that element.
weave max_val with l as list of int into int:
    var n as int is calling l.len
    if n == 0:
        return 0
    var m as int is l at 0
    var i as int is 1
    while i < n:
        if (l at i) > m:
            set m is l at i
        set i is i + 1
    return m

# Returns the smallest element of `l`. An empty list yields 0; otherwise the
# scan starts from element 0, so a single-element list returns that element.
weave min_val with l as list of int into int:
    var n as int is calling l.len
    if n == 0:
        return 0
    var m as int is l at 0
    var i as int is 1
    while i < n:
        if (l at i) < m:
            set m is l at i
        set i is i + 1
    return m


# std/atlas.pengu - The Atlas (Maps)
# Hash map key-value store utilities for the built-in `map of K to V`
# collections.
#
# Ownership / memory model:
#   * Helpers only read the map they receive: no entry is copied, added,
#     removed or reallocated, and the caller keeps ownership of the map
#     (it can still `banish` it after the call returns).
#
# Usage:
#   import std.atlas
#   var m as map of string to int is { "a": 1, "b": 2 }
#   var n as int is calling atlas.map_len_str_int with m

import std.spark

# Map helper utilities
#
# Returns the number of key -> value entries currently stored in the
# `map of string to int` `m`, equivalent to `calling m.len`. The map is
# only read, never modified.
weave map_len_str_int with m as map of string to int into int:
    return calling m.len


# std/coven.pengu - The Coven (Sets)
# Provides dynamic unique set collections over the built-in hash map:
# SetString holds distinct strings, SetInt holds distinct ints.
#
# Ownership / memory model:
#   * A set OWNS its elements: `add` deep-copies the item (as the key of the
#     backing map), so later changes to the caller's value never leak into
#     the set and no element is ever stored twice.
#   * A set is a rune value record with a single `items` backing map. Build
#     one with new_set_string / new_set_int, then copy, return or `banish`
#     it like any owned value.
#
# Usage:
#   import std.coven
#   var s as SetString is calling coven.new_set_string
#   calling s.add with "apple"
#   if calling s.contains with "apple": ...
#
# Implementation note: both types store their elements as KEYS of a
# `map of string to int` (the int values are unused). SetInt stringifies
# each int with `item to string`, which is unique per int, so membership and
# insertion behave exactly like a mathematical set with O(1) average cost.

import std.spark
import std.atlas

# ----------------------------------------------------------------------------
# Value types
# ----------------------------------------------------------------------------

# A set of unique string elements: inserting a string that is already
# present is a no-op. Use the SetString methods (add, contains, remove,
# len, clear, is_empty) to manipulate it; create one with new_set_string.
rune SetString:
    items as map of string to int

# A set of unique int elements with the same behaviour as SetString. Values
# are stored under their decimal string key (unique per int). Use the SetInt
# methods below; create one with new_set_int.
rune SetInt:
    items as map of string to int

# ----------------------------------------------------------------------------
# Constructors
# ----------------------------------------------------------------------------

# Builds a new, empty SetString ready to receive `add` calls.
weave new_set_string into SetString:
    var m as map of string to int is map of string to int
    return with items is m

# Builds a new, empty SetInt ready to receive `add` calls.
weave new_set_int into SetInt:
    var m as map of string to int is map of string to int
    return with items is m

# ----------------------------------------------------------------------------
# SetString methods
# ----------------------------------------------------------------------------

# Methods attached to every SetString value (each backed by the set's
# `items` hash map of string to int).
enchanting SetString:
    # Inserts `item` into the set. Inserting a string that is already
    # present is a no-op, because a set stores each element at most once.
    weave add with item as string into void:
        calling self->items.put with item , 1

    # Returns true when `item` is currently a member of the set.
    weave contains with item as string into bool:
        return calling self->items.contains with item

    # Removes `item` from the set. Returns true when it was present (and has
    # been removed); returns false when the set did not contain it.
    weave remove with item as string into bool:
        return calling self->items.remove with item

    # Returns the number of distinct elements currently stored in the set.
    weave len into int:
        return calling self->items.len

    # Removes every element, leaving the set empty.
    weave clear into void:
        calling self->items.clear

    # Returns true when the set holds no elements at all.
    weave is_empty into bool:
        return calling self->items.is_empty

# ----------------------------------------------------------------------------
# SetInt methods
# ----------------------------------------------------------------------------

# Methods attached to every SetInt value. Each int is stored under its
# decimal string form (item to string), so the set stays duplicate-free.
enchanting SetInt:
    # Inserts `item` into the set, storing it under the decimal string of
    # the int. Inserting an int that is already present is a no-op.
    weave add with item as int into void:
        calling self->items.put with (item to string) , 1

    # Returns true when `item` is currently a member of the set.
    weave contains with item as int into bool:
        return calling self->items.contains with (item to string)

    # Removes `item` from the set. Returns true when it was present (and has
    # been removed); returns false when the set did not contain it.
    weave remove with item as int into bool:
        return calling self->items.remove with (item to string)

    # Returns the number of distinct elements currently stored in the set.
    weave len into int:
        return calling self->items.len

    # Removes every element, leaving the set empty.
    weave clear into void:
        calling self->items.clear

    # Returns true when the set holds no elements at all.
    weave is_empty into bool:
        return calling self->items.is_empty
