import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestStruct(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_struct_field_access_valid(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into float:
  let v as Vec2 is with x is 10 and y is 20
  return v.x + v.y
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_struct_nonexistent_field_fails(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into float:
  let v as Vec2 is with x is 10 and y is 20
  return v.z
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)

    def test_primitive_field_access_fails(self):
        code = """weave main into int:
  let n as int is 10
  return n.x
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
