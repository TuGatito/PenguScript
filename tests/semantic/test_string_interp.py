import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import UndefinedIdentifierError


class TestStringInterpolation(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_known_variable_interpolation_passes(self):
        code = """weave main into void:
  let name is "bob"
  let s is "hi {name}"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_unknown_variable_interpolation_fails(self):
        code = """weave main into void:
  let s is "hi {unknown}"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(UndefinedIdentifierError) as ctx:
            self.checker.check(tree)
        self.assertIn("Undefined variable 'unknown' in string interpolation", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
