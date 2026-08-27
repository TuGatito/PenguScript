import unittest
from pengu_parser import PenguParser, PenguChecker


class TestFunctions(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_functions_and_calls(self):
        code = """weave add with a as int, b as int into int:
  a + b

weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

declare InitWindow with w as int, h as int, title as string into void
declare WindowShouldClose into bool

inline weave fast_add with a as int, b as int into int:
  a + b

weave main into int:
  calling DrawText with text is "hola" and x is 100
  calling DrawText with "hola", 100, 200
  let p_add is sigil of add
  return 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
