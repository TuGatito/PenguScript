import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import InvalidMemoryOpError, UndefinedIdentifierError, TypeMismatchError


class TestDeferBanish(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_valid_defer_and_banish(self):
        code = """rune Player:
  id as int

weave cleanup with p as ref to Player into void:
  return

weave main into void:
  var p as ref to Player is sigil of with id is 1
  defer calling cleanup with p
  banish p
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

    def test_banish_non_ref_fails(self):
        code = """weave main into void:
  let x is 10
  banish x
"""
        tree = self.parser.parse(code)
        with self.assertRaises(InvalidMemoryOpError) as ctx:
            self.checker.check(tree)
        self.assertEqual(ctx.exception.code, "E0008")

    def test_size_of_valid_and_undefined(self):
        code_valid = """rune Vec2:
  x as float
  y as float

weave main into void:
  let s is size of Vec2
"""
        tree = self.parser.parse(code_valid)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

        code_invalid = """weave main into void:
  let s is size of NonExistentType
"""
        tree_inv = self.parser.parse(code_invalid)
        with self.assertRaises(UndefinedIdentifierError) as ctx:
            self.checker.check(tree_inv)
        self.assertEqual(ctx.exception.code, "E0004")


if __name__ == "__main__":
    unittest.main()
