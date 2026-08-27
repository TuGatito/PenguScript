import unittest
from pengu_parser import PenguParser, PenguChecker


class TestControl(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_control_flow(self):
        code = """rune Player:
  x as float
  y as float

enchanting Player:
  weave move with dist as int into void:
    set self->x is self->x + dist

rune File:
  name as string

declare open with path as string into maybe File
declare print with val as string into void

weave test_flow with opt_x as maybe int, key as string, arr as list of int into int:
  var x as int is 0
  let color is if x > 10 then "red" else "blue"

  if file as File is calling open with "data.txt" is present:
    calling print with file.name

  if opt_x is present:
    return 1

  unless opt_x is present:
    return 1

  let state as string is judge key:
    when "w" -> "up"
    when "s" -> "down"
    else -> "idle"

  while x < 10:
    set x is x + 1
    if x == 5: continue
    if x == 9: break

  for i from 0 to 10:
    calling print with "loop"

  for item in arr:
    calling print with "item"

  var player as Player is with x is 10 and y is 20
  with player:
    set.x is 100
    set.y is 200
    calling.move with 5

  return 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
