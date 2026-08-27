import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import TypeMismatchError


class TestNamedPositional(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_positional_after_named_fails(self):
        code = """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with x is 1 and 2
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertEqual(ctx.exception.code, "E0005")
        self.assertIn("Positional argument after named argument", ctx.exception.message)

    def test_positional_after_multiple_named_fails(self):
        code = """weave foo with x as int, y as int, z as int into void:
  return

weave main into void:
  calling foo with x is 1 and y is 2 and 3
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertEqual(ctx.exception.code, "E0005")
        self.assertIn("Positional argument after named argument", ctx.exception.message)

    def test_all_positional_passes(self):
        code = """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with 1 and 2
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

    def test_positional_before_named_passes(self):
        code = """weave foo with a as int, x as int, y as int into void:
  return

weave main into void:
  calling foo with 1 and x is 2 and y is 3
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

    def test_all_named_passes(self):
        code = """weave foo with x as int, y as int into void:
  return

weave main into void:
  calling foo with x is 1 and y is 2
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
