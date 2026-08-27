import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import TypeMismatchError


class TestImplicitReturn(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_implicit_return_matching_type_passes(self):
        code = """weave add with a as int, b as int into int:
  a + b
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_implicit_return_type_mismatch_fails(self):
        code = """weave get_name into int:
  "pengu"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)

    def test_return_without_value_in_non_void_fails(self):
        code = """weave get_number into int:
  return
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
