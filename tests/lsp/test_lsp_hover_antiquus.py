#!/usr/bin/env python3
"""Hover markdown for an `antiquus` symbol.

An `antiquus` is registered as a callable (``kind="weave"``), so without an
explicit marker the editor would present it exactly like a type-checked
PenguScript weave.  These tests pin the two halves of the contract:

* the compiler tags the symbol (``Symbol.is_antiquus``), and
* the hover renderer says ``antiquus`` and warns that the body is literal C.
"""

from __future__ import annotations

from pengu_lsp.hover import format_symbol_hover
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_symbols import Symbol
from pengu_parser.pengu_types import FnType, INT_TYPE
from tests.conftest import REPO

SOURCE = '''antiquus double_it with x as int into int:
    """
    return x * 2;
    """
'''


class TestAntiquusIsTaggedByTheChecker:
    def test_symbol_carries_the_antiquus_marker(self):
        parser = PenguParser()
        tree = parser.parse(SOURCE)
        checker = PenguChecker(base_dir=str(REPO))
        checker.check(tree, source=SOURCE, filename="t.pengu")
        sym = checker.symbols.lookup("double_it")
        assert sym is not None
        assert sym.is_antiquus is True
        # Call dispatch is unchanged: it is still a weave-shaped callable.
        assert sym.kind == "weave"

    def test_a_regular_weave_is_not_tagged(self):
        source = "weave double_it with x as int into int:\n    return x * 2\n"
        parser = PenguParser()
        tree = parser.parse(source)
        checker = PenguChecker(base_dir=str(REPO))
        checker.check(tree, source=source, filename="t.pengu")
        assert checker.symbols.lookup("double_it").is_antiquus is False


class TestHover:
    def test_antiquus_hover_says_so_and_warns(self):
        fn = FnType(params=[("x", INT_TYPE)], return_type=INT_TYPE)
        md = format_symbol_hover(
            Symbol(name="double_it", type=fn, kind="weave", is_antiquus=True)
        )
        assert "antiquus double_it" in md
        assert "Unsafe" in md
        assert "literal C" in md

    def test_regular_weave_hover_is_unchanged(self):
        fn = FnType(params=[("x", INT_TYPE)], return_type=INT_TYPE)
        md = format_symbol_hover(Symbol(name="double_it", type=fn, kind="weave"))
        assert "weave double_it" in md
        assert "Unsafe" not in md
