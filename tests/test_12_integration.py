import unittest
from pengu_parser import PenguParser, PenguChecker


INTEGRATION_CODE = """const MAX as int is 1000
include "raylib.h"
link "raylib"
import src.math.Vec2

rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y
  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx

weave main into int:
  var player as Vec2 is with x is 10 and y is 20
  let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
  var bullets as list of Vec2 is list of Vec2 with capacity MAX
  let part as slice of Vec2 is bullets at 0 to 1
  let evens is for b in bullets when b.x > 0 then b
  if player is present:
    with player:
      set.x is 100
      calling.move with 5, 0
  return 0
"""


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_integration_parse_and_pretty(self):
        tree = self.parser.parse(INTEGRATION_CODE)
        self.assertIsNotNone(tree)
        
        pretty_output = self.parser.pretty(INTEGRATION_CODE)
        self.assertIsInstance(pretty_output, str)
        self.assertIn("rune_decl", pretty_output)
        self.assertIn("enchanting_decl", pretty_output)
        self.assertIn("weave_decl", pretty_output)

    def test_integration_tokens(self):
        tokens = self.parser.get_tokens(INTEGRATION_CODE)
        self.assertTrue(len(tokens) > 0)
        token_values = [str(t) for t in tokens]
        self.assertIn("const", token_values)
        self.assertIn("Vec2", token_values)

    def test_integration_semantic_check(self):
        tree = self.parser.parse(INTEGRATION_CODE)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
