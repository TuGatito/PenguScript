import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import ConstInsideWeaveError, VarLetTopLevelError


class TestScope(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_valid_scope(self):
        code = """const MAX as int is 100
const PI as float is 3.14

weave compute with a as int into int:
  var x as int is a
  let y as int is 20
  set x is x + y
  return x
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_var_top_level_fails(self):
        code = """var global_x as int is 10
weave main into void:
  return
"""
        tree = self.parser.parse(code)
        with self.assertRaises(VarLetTopLevelError):
            self.checker.check(tree)

    def test_let_top_level_fails(self):
        code = """let global_y as int is 10
weave main into void:
  return
"""
        tree = self.parser.parse(code)
        with self.assertRaises(VarLetTopLevelError):
            self.checker.check(tree)

    def test_const_inside_weave_fails(self):
        code = """weave main into int:
  const LOCAL_MAX as int is 10
  return LOCAL_MAX
"""
        tree = self.parser.parse(code)
        with self.assertRaises(ConstInsideWeaveError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
