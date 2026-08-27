import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import TypeMismatchError


class TestTypesCompat(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_implicit_float_to_int_fails(self):
        code = """weave main into void:
  let x as int is 3.14
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertEqual(ctx.exception.code, "E0005")

    def test_explicit_float_to_int_cast_passes(self):
        code = """weave main into void:
  let x as int is 3.14 to int
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

    def test_explicit_int_to_float_cast_passes(self):
        code = """weave main into void:
  let x as float is 3 to float
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
