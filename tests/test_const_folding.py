import unittest
from pengu_parser import PenguParser, PenguChecker, ConstFolder
from pengu_parser.pengu_symbols import SymbolTable, Symbol
from pengu_parser.pengu_types import INT_TYPE, ArrayType


class TestConstFolding(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_arithmetic_const_folding(self):
        symbols = SymbolTable()
        folder = ConstFolder(symbols)

        tree = self.parser.parse("const X as int is 10 + 20 * 2\n")
        const_node = next(tree.find_data("const_decl"))
        expr_node = const_node.children[-1]

        val = folder.fold(expr_node)
        self.assertEqual(val, 50)

    def test_bitwise_const_folding(self):
        symbols = SymbolTable()
        folder = ConstFolder(symbols)

        tree = self.parser.parse("const FLAGS as int is (1 << 2) | (1 << 4)\n")
        const_node = next(tree.find_data("const_decl"))
        expr_node = const_node.children[-1]

        val = folder.fold(expr_node)
        self.assertEqual(val, 4 | 16)

    def test_array_size_const_folded(self):
        code = """const SIZE as int is 4 + 4
weave main into void:
  var buf as array of int is array of int with size 4 + 4
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
