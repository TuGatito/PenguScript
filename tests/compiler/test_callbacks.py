"""C callbacks: function-pointer types, passing Pengu functions to C APIs.

Covers the three pieces that made callbacks unusable:

* ``FnType`` vs ``ref to weave …`` compatibility (declaring and assigning a
  function-pointer variable, including through an alias),
* calling *through* a function-pointer variable,
* emitting a cast to the declared callback type, which is what makes C APIs
  whose prototypes carry qualifiers the binding cannot express compile under
  GCC 14+.
"""

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import compile_run, gen_bundle, requires_runtime

CALLBACK_TYPES = """alias Cb as ref to weave with x as int into int

declare apply with fn as ref to weave with x as int into int, v as int into int

weave twice with x as int into int:
    return x * 2
"""


def check(source: str):
    """Parses + type-checks ``source``; returns the checker."""
    tree = PenguParser().parse(source)
    checker = PenguChecker(base_dir=".")
    checker.check(tree, source=source, filename="t.pengu")
    return checker


class TestFunctionPointerTypes:
    def test_var_declared_as_ref_to_weave(self):
        check(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    var cb as ref to weave with x as int into int is lambda x as int into x + 1\n"
            "    return calling cb with 41\n"
        )

    def test_var_declared_as_alias(self):
        check(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    var cb as Cb is lambda x as int into x + 1\n"
            "    return calling cb with 41\n"
        )

    def test_weave_name_as_value(self):
        check(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    var cb as Cb is twice\n"
            "    return calling cb with 21\n"
        )

    def test_weave_passed_to_callback_param(self):
        check(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    return calling apply with twice, 21\n"
        )

    def test_lambda_passed_to_callback_param(self):
        check(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    return calling apply with lambda x as int into x * 2, 21\n"
        )

    def test_signature_mismatch_is_rejected(self):
        with pytest.raises(PenguError) as info:
            check(
                CALLBACK_TYPES
                + "\nweave wrong with x as string into int:\n"
                "    return 0\n\n"
                "weave main into int:\n"
                "    var cb as ref to weave with x as int into int is wrong\n"
                "    return 0\n"
            )
        assert "but initialized with" in str(info.value)

    def test_emitted_declarator_is_a_function_pointer(self):
        code = gen_bundle(
            CALLBACK_TYPES
            + "\nweave main into int:\n"
            "    var cb as ref to weave with x as int into int is twice\n"
            "    return calling cb with 21\n"
        )
        assert "int32_t (*cb)(int32_t)" in code
        # No pointer-to-function-pointer spelling.
        assert "(*)(int32_t)*" not in code

    @requires_runtime
    def test_atexit_callback_runs(self):
        res = compile_run(
            "import std.spark\n\n"
            'include "stdlib.h"\n\n'
            "declare atexit with fn as ref to weave into void into int\n\n"
            "weave bye into void:\n"
            '    calling spark.println with "bye from callback"\n\n'
            "weave main into int:\n"
            "    calling atexit with bye\n"
            "    return 0\n",
            tag="atexit_cb",
        )
        assert "bye from callback" in res.stdout
