import unittest
from pengu_parser import PenguParser, PenguChecker


class TestStructs(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_struct_definitions_and_access(self):
        code = """rune Vec2:
  x as float
  y as float

echo Value:
  i as int
  f as float

alias MyInt as int
alias Texture as opaque

omen Result:
  Ok with value as int
  Err with msg as string

weave struct_test into void:
  var v as Vec2 is with x is 10 and y is 20
  let vx is v.x
  set v.x is 100.0

  var vp as ref to Vec2 is sigil of v
  set vp->x is 100.0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
