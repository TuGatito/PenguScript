import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError, InvalidMemoryOpError


class TestPointers(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_sigil_and_essence_valid(self):
        code = """weave main into int:
  var x as int is 42
  let p as ref to int is sigil of x
  let val as int is essence of p
  set essence of p is 100
  return val
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_sigil_of_literal_fails(self):
        code = """weave main into void:
  let p is sigil of 10
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)

    def test_sigil_of_const_fails(self):
        code = """const MAX as int is 100
weave main into void:
  let p is sigil of MAX
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
