import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_types import ResultType, EchoType


class TestResultEcho(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_result_alias_and_usage(self):
        code = """alias MyResult as result of int to string

weave main into void:
  var x as int is 10
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)
        self.assertIn("MyResult", self.checker.symbols.aliases)
        alias_t = self.checker.symbols.aliases["MyResult"]
        self.assertIsInstance(alias_t.target, ResultType)

    def test_echo_declaration(self):
        code = """echo MyEcho:
  a as int
  b as float

weave main into void:
  var x as int is 10
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)
        self.assertIn("MyEcho", self.checker.symbols.echos)
        echo_t = self.checker.symbols.echos["MyEcho"]
        self.assertIsInstance(echo_t, EchoType)
        self.assertIn("a", echo_t.fields)
        self.assertIn("b", echo_t.fields)


if __name__ == "__main__":
    unittest.main()
