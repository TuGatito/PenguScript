import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import ConstInsideWeaveError, VarLetTopLevelError


class TestVars(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_valid_globals_and_locals(self):
        code = """const MAX_ENTITIES as int is 1000
const PI as float is 3.14

rune Vec2:
  x as float
  y as float

weave main into int:
  var x as int is 10
  let y as int is 20
  var my_vec as Vec2 is with x is 1.0 and y is 2.0
  let a, b is my_vec
  set x is x + 1
  return 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_const_inside_weave_fails(self):
        code = """weave main into int:
  const LOCAL_MAX as int is 100
  return 0
"""
        tree = self.parser.parse(code)
        with self.assertRaises(ConstInsideWeaveError):
            self.checker.check(tree)

    def test_var_top_level_fails(self):
        code = """var global_x as int is 10
weave main into int:
  return 0
"""
        tree = self.parser.parse(code)
        with self.assertRaises(VarLetTopLevelError):
            self.checker.check(tree)

    def test_let_top_level_fails(self):
        code = """let global_y as int is 10
weave main into int:
  return 0
"""
        tree = self.parser.parse(code)
        with self.assertRaises(VarLetTopLevelError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
