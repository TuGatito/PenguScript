import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestInferenceNoAs(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_single_rune_match_infers_automatically(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v is with x is 1.0 and y is 2.0
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_explicit_as_vec2_passes(self):
        code = """rune Vec2:
  x as float
  y as float

weave main into void:
  let v as Vec2 is with x is 1.0 and y is 2.0
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_no_matching_rune_fails(self):
        code = """weave main into void:
  let v is with x is 1.0 and y is 2.0
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)

    def test_ambiguous_matching_runes_fails(self):
        code = """rune Vec2:
  x as float
  y as float

rune Point2D:
  x as float
  y as float

weave main into void:
  let v is with x is 1.0 and y is 2.0
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
