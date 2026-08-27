import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import TypeMismatchError


class TestForCompBool(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_non_bool_when_in_for_comp_fails(self):
        code = """weave main into void:
  var arr as array of int is array of int with size 4
  var res is for x in arr when 10 then x
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError) as ctx:
            self.checker.check(tree)
        self.assertEqual(ctx.exception.code, "E0005")
        self.assertIn("when condition must be bool", ctx.exception.message)

    def test_bool_when_in_for_comp_passes(self):
        code = """weave main into void:
  var arr as array of int is array of int with size 4
  var res is for x in arr when x > 0 then x
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
