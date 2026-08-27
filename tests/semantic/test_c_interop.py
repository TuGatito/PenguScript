import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import UndefinedIdentifierError


class TestCInterop(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_upper_case_with_include_passes(self):
        code = """include "raylib.h"
link "raylib"

weave main into int:
  let k is KEY_W
  let f is FLAG_WINDOW_RESIZABLE
  return k
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_upper_case_without_include_fails(self):
        code = """weave main into int:
  let k is KEY_W
  return k
"""
        tree = self.parser.parse(code)
        with self.assertRaises(UndefinedIdentifierError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
