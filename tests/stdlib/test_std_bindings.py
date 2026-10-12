"""Regressions found while auditing std/ for production use.

Covers: single-element array literals, bare-literal statements and UTF-8 BOM
tolerance. The cross-module binding tests that used to live here exercised
``std.raylib``/``std.raygui``/``std.nanosvg``, which Phase 1 moved out of the
tree.
"""

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import compile_run, gen_bundle, requires_runtime


class TestSingleElementArrayLiteral:
    """`[0]` is an initializer list, not the scalar 0 (ConstFolder collapsed it)."""

    def test_single_element_is_braced(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var p as array of byte with size 1 is [0]\n"
            "    return 0\n"
        )
        assert "uint8_t p[1] = { 0 };" in code

    def test_single_non_zero_element_is_braced(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var a as array of int with size 1 is [7]\n"
            "    return 0\n"
        )
        assert "int32_t a[1] = { 7 };" in code

    def test_multi_element_unchanged(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var a as array of int with size 2 is [1, 2]\n"
            "    return 0\n"
        )
        assert "int32_t a[2] = { 1, 2 };" in code

    @requires_runtime
    def test_single_element_array_runs(self):
        res = compile_run(
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var p as array of byte with size 1 is [0]\n"
            "    var a as array of int with size 1 is [7]\n"
            "    calling spark.println with ((a at 0) to string)\n"
            "    return 0\n",
            tag="array_single",
        )
        assert "7" in res.stdout


class TestBareLiteralStatements:
    """`x[0]` is not Pengu indexing: it used to compile as a stray '[0]'."""

    def test_c_style_indexing_is_rejected(self):
        with pytest.raises(PenguError) as info:
            PenguChecker(base_dir=".").check(
                PenguParser().parse(
                    "weave main into int:\n"
                    "    var arr as array of int with size 3 is [10, 20, 30]\n"
                    "    var p as ref to void is sigil of arr[0]\n"
                    "    return 0\n"
                ),
                source="weave main into int:\n",
                filename="t.pengu",
            )
        assert getattr(info.value, "code", "") == "E0005"
        assert "is not a statement" in str(info.value)
        assert "'x at i'" in (info.value.help or "")

    def test_bare_array_literal_is_rejected(self):
        with pytest.raises(PenguError) as info:
            PenguChecker(base_dir=".").check(
                PenguParser().parse("weave main into int:\n    [1, 2]\n    return 0\n"),
                source="weave main into int:\n",
                filename="t.pengu",
            )
        assert "An array literal is not a statement" in str(info.value)

    def test_proper_indexing_is_fine(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var arr as array of int with size 3 is [10, 20, 30]\n"
            "    var p as ref to void is sigil of (arr at 0)\n"
            "    return 0\n"
        )
        assert "int32_t arr[3] = { 10, 20, 30 };" in code


class TestBomTolerance:
    """Editors on Windows write a UTF-8 BOM; it must not break parsing."""

    def test_bom_is_ignored(self):
        tree = PenguParser().parse("\ufeffweave main into int:\n    return 0\n")
        assert tree is not None

    def test_bom_in_expression(self):
        tree = PenguParser().parse_expr("\ufeff1 + 2")
        assert tree is not None

    def test_bomless_source_still_parses(self):
        tree = PenguParser().parse("weave main into int:\n    return 0\n")
        assert tree is not None

