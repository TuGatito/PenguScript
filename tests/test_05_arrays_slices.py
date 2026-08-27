import unittest
from pengu_parser import PenguParser, PenguChecker


class TestArraysSlices(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_arrays_and_slices(self):
        code = """const MAX_ENTITIES as int is 100

rune Vec2:
  x as float
  y as float

weave test_collections into void:
  let arr is array of int with size 10
  let first is arr at 0
  set arr at 0 is 99

  let part as slice of int is arr at 1 to 3
  let n is part length

  let evens is for x in arr when x % 2 == 0 then x
  let doubled is for x in arr then x * 2

  var vertices as list of Vec2 is list of Vec2 with capacity MAX_ENTITIES
  var lookup as map of int to Vec2 is map of int to Vec2

  let name is "player1"
  let x is 10
  let msg is "player {name} at {x}"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
