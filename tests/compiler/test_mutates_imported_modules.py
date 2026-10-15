"""Regression: ``@mutates`` metadata must survive an ``import``.

``mutating_methods`` drives both the statement rewrite (checker) and the
``get_<name>`` alias (inferrer).  It used to be populated **only** in pass 2, the
validation walk, which visits the entry tree alone -- pass 1 is the pass that
also collects imported modules.

The CLI masked this by re-checking every module as its own entry, so
``pengu check``/``run`` were correct while the LSP, which calls
``PenguChecker.check()`` once for the open buffer, reported a **false E0004**:

    Type 'int' has no method 'get_abs'

for code the command line compiled happily.  Registration now happens in pass 1,
where it is a declaration fact rather than a validation one.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


CASES = {
    "numerus_shard": (
        "import std.numerus",
        "var x as int is -5\n    var y as int is calling x.get_abs",
    ),
    "integrum_shard": (
        "import std.integrum",
        "var x as int is 12\n    var y as int is calling x.get_gcd with 18",
    ),
    "fractio_float": (
        "import std.fractio",
        "var x as float is 4.0\n    var y as float is calling x.get_sqrt",
    ),
    "fractio_f64": (
        "import std.fractio",
        "var x as f64 is 4.0\n    var y as f64 is calling x.get_sqrt",
    ),
    "littera_char": (
        "import std.littera",
        "var c as char is 'a'\n    var d as char is calling c.get_to_upper",
    ),
    "logica_bool": (
        "import std.logica",
        "var a as bool is true\n    var b as bool is false\n    var r as bool is calling a.get_implies with b",
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_imported_getter_resolves_in_one_in_process_check(parse_and_check, name):
    """`get_<name>` works in a single `check()`, as the LSP performs it."""
    import_line, body = CASES[name]
    errors, _, _ = parse_and_check(f"""
{import_line}

weave main into int:
    {body}
    return 0
""")
    assert errors == [], [str(e) for e in errors]


def test_the_metadata_is_actually_registered(parse_and_check):
    """Not just "no error": the registry holds the entry, under the right key."""
    _, _, symbols = parse_and_check("""
import std.numerus

weave main into int:
    var x as int is -5
    var y as int is calling x.get_abs
    return y
""")
    assert ("__shard__", "abs") in symbols.mutating_methods
    entry = symbols.mutating_methods[("__shard__", "abs")]
    assert entry["getter"] == "get_abs"
    assert entry["self_is_value"] is True


def test_a_concrete_block_registers_under_its_receiver(parse_and_check):
    _, _, symbols = parse_and_check("""
import std.logica

weave main into int:
    var a as bool is true
    var r as bool is calling a.get_toggle
    return 0
""")
    assert ("bool", "toggle") in symbols.mutating_methods


def test_imported_mutation_still_requires_a_statement(parse_and_check):
    """The alias must not weaken the rule it exists to serve."""
    errors, _, _ = parse_and_check("""
import std.numerus

weave main into int:
    var x as int is -5
    var y as int is calling x.abs
    return y
""")
    assert any(e.code == "E0066" for e in errors), [str(e) for e in errors]


def test_imported_mutating_statement_rewrites_the_receiver(parse_and_check):
    errors, _, _ = parse_and_check("""
import std.numerus

weave main into int:
    var x as int is -5
    calling x.abs
    return x
""")
    assert errors == [], [str(e) for e in errors]
