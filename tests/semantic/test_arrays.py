import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import TypeMismatchError


class TestArrays(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_array_operations_valid(self):
        code = """weave main into int:
  let arr is array of int with size 10
  let first is arr at 0
  let slice_part is arr at 1 to 4
  let length_val is arr length
  return first
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_array_index_non_int_fails(self):
        code = """weave main into void:
  let arr is array of int with size 10
  let item is arr at "invalid_index"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)

    def test_slice_range_non_int_fails(self):
        code = """weave main into void:
  let arr is array of int with size 10
  let part is arr at "start" to 5
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
