import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError, TypeMismatchError


class TestInference(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_primitive_inference(self):
        code = """weave main into void:
  var x is 10
  let y is 3.14
  let s is "hi"
  let b is true
  set x is 20
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_struct_with_type_annotation(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v as Vec2 is with x is 10 and y is 20
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_struct_without_as_inferred_automatically(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v is with x is 10 and y is 20
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_struct_unknown_fields_fails(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v is with unknown_field is 10
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
