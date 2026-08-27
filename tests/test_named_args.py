import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import TypeMismatchError, SemanticError


class TestNamedArgs(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_valid_named_args_after_positional(self):
        code = """weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

weave main into void:
  calling DrawText with "hello", x is 10, y is 20
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)

    def test_positional_after_named_fails(self):
        code = """weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  return

weave main into void:
  calling DrawText with x is 10, "hello"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertIn("Positional", str(ctx.exception))
        self.assertEqual(ctx.exception.code, "E0005")

    def test_non_default_param_after_default_fails(self):
        code = """weave bad_fn with a as int is 10, b as int into void:
  return
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as ctx:
            self.checker.check(tree)
        self.assertIn("Non-default parameter", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
