#!/usr/bin/env python3
"""Tests for PenguScript v0.6 Language Server Protocol (LSP) features."""

import unittest
from lsprotocol.types import (
    Position,
    DiagnosticSeverity,
)

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError

from pengu_lsp.server import diagnostics_from_errors, validate_document, server
from pengu_lsp.completions import get_completions
from pengu_lsp.hover import get_hover, get_word_at_position


class TestPenguLSP(unittest.TestCase):
    """Test suite for LSP diagnostics, completions, and hover info."""

    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_diagnostics_multi_error(self):
        """Checks that multiple checker errors are converted to LSP diagnostics."""
        code = """rune Vec2:
  x as int

weave main into void:
  var a as int is "hello"
  var b as float is a + "world"
"""
        tree = self.parser.parse(code)
        try:
            self.checker.check(tree, source=code, filename="test.pengu")
            errors = []
        except PenguError as e:
            errors = e.all_errors if hasattr(e, "all_errors") and e.all_errors else [e]

        self.assertGreater(len(errors), 0, "Checker should find type mismatch errors")

        diags = diagnostics_from_errors(errors, code)
        self.assertEqual(len(diags), len(errors))

        # Validate diagnostic structure
        for diag in diags:
            self.assertEqual(diag.severity, DiagnosticSeverity.Error)
            self.assertEqual(diag.source, "pengus")
            self.assertIn("[E0005]", diag.message)
            self.assertIn("help:", diag.message)

    def test_diagnostics_clean_code(self):
        """Checks that clean code produces empty diagnostics."""
        code = """rune Vec2:
  x as int
  y as int

weave add with a as int and b as int into int:
  return a + b
"""
        tree = self.parser.parse(code)
        try:
            self.checker.check(tree, source=code, filename="test.pengu")
            errors = []
        except PenguError as e:
            errors = e.all_errors if hasattr(e, "all_errors") and e.all_errors else [e]

        self.assertEqual(len(errors), 0)

        diags = diagnostics_from_errors(errors, code)
        self.assertEqual(len(diags), 0)

    def test_completion_contains_weave_and_keywords(self):
        """Verifies that completion items contain core language keywords and snippets."""
        uri = "file:///test.pengu"
        pos = Position(line=0, character=0)
        completions = get_completions(uri, pos, symbols=None)

        labels = [item.label for item in completions.items]
        self.assertIn("weave", labels)
        self.assertIn("rune", labels)
        self.assertIn("echo", labels)
        self.assertIn("omen", labels)
        self.assertIn("var", labels)
        self.assertIn("let", labels)
        self.assertIn("with", labels)
        self.assertIn("self->", labels)
        self.assertIn("sigil of", labels)
        self.assertIn("defer", labels)
        self.assertIn("errdefer", labels)
        self.assertIn("banish", labels)
        self.assertIn("int", labels)
        self.assertIn("string", labels)

    def test_completion_contains_workspace_symbols(self):
        """Verifies that checked symbols appear in the completion list."""
        code = """rune Player:
  x as int
  y as int

weave calculate_score with p as int into int:
  return p * 10
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        uri = "file:///test.pengu"
        pos = Position(line=5, character=0)
        completions = get_completions(uri, pos, symbols=self.checker.symbols)

        labels = [item.label for item in completions.items]
        self.assertIn("Player", labels)
        self.assertIn("calculate_score", labels)

    def test_hover_returns_keyword_doc(self):
        """Verifies that hover returns markdown documentation for keywords."""
        code = "weave main into void:\n  return\n"
        pos = Position(line=0, character=2) # hover over 'weave'
        hover = get_hover("file:///test.pengu", pos, symbols=None, text=code)

        self.assertIsNotNone(hover)
        self.assertIn("**weave**", hover.contents.value)

    def test_hover_returns_symbol_type(self):
        """Verifies that hover returns the type and kind of defined symbols."""
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  var v as Vec2 is with x is 1.0 and y is 2.0
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        # Hover over 'Vec2'
        pos_vec = Position(line=0, character=6)
        hover_vec = get_hover("file:///test.pengu", pos_vec, symbols=self.checker.symbols, text=code)
        self.assertIsNotNone(hover_vec)
        self.assertIn("rune Vec2", hover_vec.contents.value)

        # Hover over 'main'
        pos_main = Position(line=4, character=7)
        hover_main = get_hover("file:///test.pengu", pos_main, symbols=self.checker.symbols, text=code)
        self.assertIsNotNone(hover_main)
        self.assertIn("main", hover_main.contents.value)

    def test_hover_doc_comments(self):
        """Verifies that doc comments preceding declarations are extracted into Symbol.doc and shown in hover."""
        code = """# Computes the sum of two integers.
# Returns the calculated integer result.
weave add with a as int and b as int into int:
    return a + b
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        sym = self.checker.symbols.lookup("add")
        self.assertIsNotNone(sym)
        self.assertIsNotNone(sym.doc)
        self.assertIn("Computes the sum of two integers.", sym.doc)
        self.assertIn("Returns the calculated integer result.", sym.doc)

        hover = get_hover("file:///test.pengu", Position(line=2, character=7), symbols=self.checker.symbols, text=code)
        self.assertIsNotNone(hover)
        self.assertIn("Computes the sum of two integers.", hover.contents.value)

    def test_hover_type_sizes(self):
        """Verifies that type sizes (in bytes) are computed and displayed in hover."""
        code = """rune Player:
  name as string
  health as int
  is_alive as bool

weave main into void:
  var p as Player is with name is "Hero" and health is 100 and is_alive is true
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        # Hover over Player (struct: string(16) + int(4) + bool(1) = 21 bytes)
        hover_player = get_hover("file:///test.pengu", Position(line=0, character=7), symbols=self.checker.symbols, text=code)
        self.assertIsNotNone(hover_player)
        self.assertIn("21 bytes", hover_player.contents.value)
        self.assertIn("name as string  // 128 bits / 16 bytes", hover_player.contents.value)
        self.assertIn("health as int  // 32 bits / 4 bytes", hover_player.contents.value)
        self.assertIn("is_alive as bool  // 8 bits / 1 bytes", hover_player.contents.value)

    def test_module_completion_and_hover(self):
        """Verifies module-scoped completions and hover for stdlib modules."""
        code = """import std.spark

weave main into void:
  calling spark.println with "Hello LSP"
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        mod_sym = self.checker.symbols.lookup("spark")
        self.assertIsNotNone(mod_sym)
        self.assertIsNotNone(mod_sym.module_scope)
        self.assertIn("println", mod_sym.module_scope.symbols)

        # Test dot completion: 'spark.'
        completions = get_completions("file:///test.pengu", Position(line=3, character=16), symbols=self.checker.symbols, line_prefix="  calling spark.")
        labels = [item.label for item in completions.items]
        self.assertIn("println", labels)
        self.assertIn("print_line", labels)

        # Test hover on 'spark.println'
        hover_println = get_hover("file:///test.pengu", Position(line=3, character=17), symbols=self.checker.symbols, text=code)
        self.assertIsNotNone(hover_println)
        self.assertIn("println", hover_println.contents.value)

    def test_definition_navigation(self):
        """Verifies definition request resolution for local symbols and module members."""
        from pengu_lsp.server import definition
        from lsprotocol.types import DefinitionParams, TextDocumentIdentifier

        code = """import std.spark

weave my_helper with val as int into int:
    return val * 2

weave main into void:
    var res as int is calling my_helper with 10
    calling spark.println with "Done"
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        server._symbols["file:///test.pengu"] = self.checker.symbols
        server._docs["file:///test.pengu"] = code

        # Jump to definition of 'my_helper' on line 6 (0-indexed)
        params_local = DefinitionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.pengu"),
            position=Position(line=6, character=32)
        )
        loc_local = definition(params_local)
        self.assertIsNotNone(loc_local)
        self.assertTrue(loc_local.uri.endswith("test.pengu"))
        self.assertEqual(loc_local.range.start.line, 2)  # Line 3 (0-indexed 2)

        # Jump to definition of 'spark.println' on line 7
        params_mod = DefinitionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.pengu"),
            position=Position(line=7, character=20)
        )
        loc_mod = definition(params_mod)
        self.assertIsNotNone(loc_mod)
        self.assertTrue(loc_mod.uri.endswith("spark.pengu"))

    def test_scoped_and_dot_field_completions(self):
        """Verifies local variable suggestions and rune dot field completions."""
        code = """rune Character:
    name as string
    hp as int
    is_alive as bool

weave main into void:
    var player as Character is with name is "Hero" and hp is 100 and is_alive is true
    var outer_secret as int is 42
    if outer_secret > 0:
        var inner_flag as bool is true
        calling print with player.name
"""
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")

        # 1. Scoped local completion inside if block (line 10, 0-indexed line 9)
        res_if = get_completions("file:///test.pengu", Position(line=9, character=8), symbols=self.checker.symbols, line_prefix="        ")
        labels_if = [it.label for it in res_if.items]
        self.assertIn("player", labels_if)
        self.assertIn("outer_secret", labels_if)
        self.assertIn("inner_flag", labels_if)

        # 2. Dot completion on 'player.' (exclusive field completion)
        res_dot = get_completions("file:///test.pengu", Position(line=9, character=30), symbols=self.checker.symbols, line_prefix="        calling print with player.")
        fields = [(it.label, it.detail) for it in res_dot.items]
        self.assertEqual(len(fields), 3)
        self.assertIn(("name", "string"), fields)
        self.assertIn(("hp", "int"), fields)
        self.assertIn(("is_alive", "bool"), fields)

        # 3. Arrow completion on 'player->'
        res_arrow = get_completions("file:///test.pengu", Position(line=9, character=31), symbols=self.checker.symbols, line_prefix="        calling print with player->")
        arrow_fields = [it.label for it in res_arrow.items]
        self.assertIn("name", arrow_fields)
        self.assertIn("hp", arrow_fields)

        # 4. Calling context completion on 'calling '
        res_calling = get_completions("file:///test.pengu", Position(line=9, character=16), symbols=self.checker.symbols, line_prefix="        calling ")
        calling_labels = [it.label for it in res_calling.items]
        self.assertIn("print", calling_labels)
        self.assertIn("main", calling_labels)
        # Should not include keywords like 'while' or 'if'
        self.assertNotIn("while", calling_labels)
        self.assertNotIn("if", calling_labels)


if __name__ == "__main__":
    unittest.main()


