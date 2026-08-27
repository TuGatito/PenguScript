import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import TypeMismatchError


class TestMaybe(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_maybe_valid(self):
        code = """rune User:
  name as string

weave main into string:
  let u as maybe User is maybe none
  let guest as string is "guest"
  let u2 as maybe string is maybe none
  let result is u2 or else guest
  return result
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_maybe_none_without_type_fails(self):
        code = """weave main into void:
  let u is maybe none
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
