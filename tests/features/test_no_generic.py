"""Roadmap Phase 2 / item 2.2.e — the generated bundle does not rely on C11
``_Generic``.

`pengu_to_string(x)` was a `_Generic` macro; the code generator now knows the
static type and calls the concrete `pengu_string_from_*` producer instead.
"""

from tests.conftest import gen_bundle

_SOURCES = {
    "int_to_string": (
        'weave main into int:\n'
        '  var n as int is 7\n'
        '  var s as string is n to string\n'
        '  return s length\n'
    ),
    "float_to_string": (
        'weave main into int:\n'
        '  var f as float is 1.5\n'
        '  var s as string is f to string\n'
        '  return s length\n'
    ),
    "bool_to_string": (
        'weave main into int:\n'
        '  var b as bool is true\n'
        '  var s as string is b to string\n'
        '  return s length\n'
    ),
}


def test_generated_c_has_no_generic_macro():
    for name, src in _SOURCES.items():
        c = gen_bundle(src)
        assert "_Generic" not in c, f"{name}: _Generic leaked into the bundle"
        assert "pengu_to_string" not in c, f"{name}: pengu_to_string leaked into the bundle"


def test_typed_producer_is_emitted():
    c = gen_bundle(_SOURCES["int_to_string"])
    assert "pengu_string_from_int" in c
    c = gen_bundle(_SOURCES["float_to_string"])
    assert "pengu_string_from_float" in c
    c = gen_bundle(_SOURCES["bool_to_string"])
    assert "pengu_string_from_bool" in c
