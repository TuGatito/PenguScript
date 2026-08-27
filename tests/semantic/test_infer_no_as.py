import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestInferNoAs(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_infer_no_as_single_match_passes(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v is with x is 1 and y is 2
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_infer_no_as_no_match_fails(self):
        code = """weave main into void:
  let v is with x is 1
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as ctx:
            self.checker.check(tree)
        self.assertIn("no rune matches", str(ctx.exception).lower())

    def test_infer_no_as_ambiguous_fails(self):
        code = """rune Vec2:
  x as float
  y as float

rune Vec3:
  x as float
  y as float

weave main into void:
  let v is with x is 1 and y is 2
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as ctx:
            self.checker.check(tree)
        self.assertIn("ambiguous", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
