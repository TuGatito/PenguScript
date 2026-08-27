import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import MutabilityError


class TestMutability(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_var_is_mutable(self):
        code = """weave main into void:
  var x as int is 10
  set x is 20
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_let_is_immutable_fails(self):
        code = """weave main into void:
  let x as int is 10
  set x is 20
"""
        tree = self.parser.parse(code)
        with self.assertRaises(MutabilityError):
            self.checker.check(tree)

    def test_const_is_immutable_fails(self):
        code = """const MAX as int is 100
weave main into void:
  set MAX is 200
"""
        tree = self.parser.parse(code)
        with self.assertRaises(MutabilityError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
