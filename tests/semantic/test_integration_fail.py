import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestIntegrationFail(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_complete_program_with_semantic_error(self):
        code = """const MAX as int is 100

rune Vec2:
  x as float
  y as float

weave main into int:
  let v as Vec2 is with x is 10 and y is 20
  set v.x is 50
  return 0
"""
        tree = self.parser.parse(code)
        try:
            self.checker.check(tree)
            self.fail("Expected SemanticError to be raised")
        except SemanticError as e:
            self.assertIsNotNone(e.line)
            self.assertIn("line", str(e))


if __name__ == "__main__":
    unittest.main()
