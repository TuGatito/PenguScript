import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestDestructuring(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_rune_destructuring_valid(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into float:
  let v as Vec2 is with x is 1.0 and y is 2.0
  let px, py is v
  return px + py
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_rune_destructuring_count_mismatch_fails(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v as Vec2 is with x is 1.0 and y is 2.0
  let px, py, pz is v
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)

    def test_array_destructuring_valid(self):
        code = """weave main into int:
  let arr is array of int with size 2
  let a, b is arr
  return a + b
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_destructuring_codegen(self):
        code = """rune Vec2:
  x as float
  y as float

weave test_destructure into void:
  var v as Vec2 is with x is 10.5 and y is 20.5
  let vx, vy is v
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_destruct.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_destruct.pengu"], ".")
        codegen.collect_declarations([("test_destruct.pengu", tree)])
        c_code = codegen.generate_function_definitions()

        self.assertIn("const float vx = _destruct_1.x;", c_code)
        self.assertIn("const float vy = _destruct_1.y;", c_code)


if __name__ == "__main__":
    unittest.main()

