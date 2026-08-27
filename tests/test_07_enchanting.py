import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SelfDotAccessError


class TestEnchanting(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_enchanting_with_arrow(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    (self->x * self->x + self->y * self->y) to float

  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

weave main into void:
  let a as Vec2 is with x is 10 and y is 20
  let b as Vec2 is with x is 5 and y is 5
  let c is calling a.add with b
  var d as Vec2 is a
  calling d.move with 10, 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_self_dot_access_fails(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave move with dx as float into void:
    set self.x is self.x + dx
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SelfDotAccessError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
