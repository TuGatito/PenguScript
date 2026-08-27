import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SelfDotAccessError, SemanticError


class TestEnchanting(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_enchanting_with_arrow_passes(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into void:
    set self->x is self->x + other.x
    set self->y is self->y + other.y
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_self_dot_access_fails(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into void:
    set self.x is self.x + other.x
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SelfDotAccessError):
            self.checker.check(tree)

    def test_enchanting_undefined_rune_fails(self):
        code = """enchanting NonExistent:
  weave foo into void:
    return
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
