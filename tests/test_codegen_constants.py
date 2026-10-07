#!/usr/bin/env python3
"""Global-constant lowering (`pengu_parser/pengu_codegen/constants.py`).

`const NAME as type is value` is evaluated at compile time and emitted as a C
`#define` (or `static const` for the typed forms).  Which spelling a constant
gets decides both its C type and whether it can be used where the C compiler
needs a constant expression, so this file pins the mapping for each value kind.

Nothing here compiles C: the bundle text is the deliverable being asserted on,
which keeps the test hermetic and runnable on every platform.
"""

from __future__ import annotations

import pytest

from tests.conftest import (
    gen_bundle,
    requires_cc,
    requires_runtime,
)


def _constants_section(source: str) -> str:
    """Returns the 'Global Constants' block of the generated bundle."""
    c = gen_bundle(source, filename="consts.pengu")
    marker = " * Global Constants"
    assert marker in c, "the bundle has no global-constants section"
    # Everything between the header comment's closing '*/' and the next block.
    body = c.split(marker, 1)[1].split("*/", 1)[1]
    return body.split("/*", 1)[0]


def test_string_constant_becomes_an_owned_pengu_string_define():
    section = _constants_section(
        'const GREETING as string is "hello"\n'
        "weave main into int:\n"
        "    return 0\n"
    )
    assert '#define GREETING pengu_string_from_cstr("hello")' in section


def test_bool_constant_becomes_true_or_false():
    section = _constants_section(
        "const FLAG as bool is true\n"
        "const OTHER as bool is false\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    assert "#define FLAG true" in section
    assert "#define OTHER false" in section


def test_numeric_constants_keep_their_literal_form():
    section = _constants_section(
        "const COUNTER as int is 0\n"
        "const SCALE is 1.5\n"
        "const BIG as int is 12000000\n"
        "weave main into int:\n"
        "    return COUNTER\n"
    )
    assert "#define COUNTER 0" in section
    assert "#define SCALE 1.5" in section
    assert "#define BIG 12000000" in section


def test_a_typed_null_pointer_constant_is_a_static_definition():
    """`ref to char` is a real C pointer, not a string: it cannot be a #define."""
    section = _constants_section(
        "const NO_CHAR as ref to char is null\n"
        "weave main into int:\n"
        "    return 0\n"
    )
    assert "static char* NO_CHAR = NULL;" in section


def test_a_program_without_constants_has_no_constants_section():
    c = gen_bundle("weave main into int:\n    return 0\n", filename="none.pengu")
    assert "Global Constants" not in c


@requires_cc
@requires_runtime
def test_a_constant_is_usable_as_an_array_size():
    """The value must fold, which is what makes the `#define` spelling matter."""
    from tests.conftest import compile_run

    res = compile_run(
        "const COLS as int is 3\n"
        "\n"
        "weave main into int:\n"
        "    var grid as array of int with size COLS is [1, 2, 3]\n"
        "    return (grid at 2) - 3\n"
    )
    assert res.returncode == 0, res.stderr
