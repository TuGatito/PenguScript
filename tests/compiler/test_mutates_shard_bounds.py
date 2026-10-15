"""Regression: the ``__shard__`` ``@mutates`` lookup is not a wildcard.

``_mutating_entry`` probes the receiver's own keys first and only then the
``__shard__`` registry.  Treating that fallback as "matches any receiver" made
``string.get_truncate`` resolve to ``std.numerus``'s

    enchanting shard T where T: Num and T: Ordo and T: Par:
        @mutates
        weave truncate into T:

which is a *mutating* method returning ``void`` -- so a perfectly good
``std.scrolls`` call became

    E0005: Immutable binding declared as 'string', but initialized with 'void'

once numerus was annotated.  The fallback now applies the same test ordinary
resolution does: the method must be a real generic shard method, the receiver
must be a type parameter or a primitive, and it must satisfy every ``where``
bound.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_string_get_truncate_is_scrolls_not_the_shard(parse_and_check):
    """`string.get_truncate` returns `string`; numerus' shard must not hijack it."""
    errors, _, _ = parse_and_check("""
import std.numerus
import std.scrolls

weave main into int:
    var s as string is "hello world"
    var t as string is calling s.get_truncate with 5, "..."
    return 0
""")
    assert errors == [], [str(e) for e in errors]


def test_int_get_truncate_is_the_shard(parse_and_check):
    """On a real numeric receiver the shard method does apply."""
    errors, _, _ = parse_and_check("""
import std.numerus

weave main into int:
    var x as int is 5
    var y as int is calling x.get_truncate
    return y
""")
    assert errors == [], [str(e) for e in errors]


def test_shard_getter_does_not_apply_to_a_non_numeric_receiver(parse_and_check):
    """`string.get_abs` must stay unresolvable -- the shard bounds exclude it."""
    errors, _, _ = parse_and_check("""
import std.numerus

weave main into int:
    var s as string is "hi"
    var y as string is calling s.get_abs
    return 0
""")
    assert errors, "a shard method bound to `Num` was offered to `string`"
    assert not any(e.code == "E0066" for e in errors), [str(e) for e in errors]


def test_bounds_are_enforced_for_a_float_receiver(parse_and_check):
    """`float` satisfies `Num`/`Ordo`/`Par`, so `get_truncate` is available."""
    errors, _, _ = parse_and_check("""
import std.numerus

weave main into int:
    var f as float is 3.7
    var g as float is calling f.get_truncate
    return 0
""")
    assert errors == [], [str(e) for e in errors]


def test_integrum_bound_excludes_float(parse_and_check):
    """`fractio`'s `float` methods must not be reached by integrum's shard."""
    errors, _, _ = parse_and_check("""
import std.integrum

weave main into int:
    var f as float is 2.0
    var g as float is calling f.get_gcd with 4.0
    return 0
""")
    assert errors, "`where T: Integrum` was satisfied by `float`"
