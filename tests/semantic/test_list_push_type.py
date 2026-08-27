import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import TypeMismatchError


class TestListPushType(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_list_push_compatible_type_passes(self):
        code = """weave main into void:
  var l as list of int is list of int with capacity 10
  calling l.push with 5
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_list_push_incompatible_type_fails(self):
        code = """weave main into void:
  var l as list of int is list of int with capacity 10
  calling l.push with "hi"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertIn("push expects int, got string", str(ctx.exception))

    def test_list_of_struct_push_incompatible_type_fails(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  var l as list of Vec2 is list of Vec2 with capacity 10
  calling l.push with 5
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertIn("List of Vec2 push expects Vec2, got int", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
