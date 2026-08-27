import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_errors import PenguError


class TestMultiError(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_multi_error_accumulation_and_rendering(self):
        code = """weave main into void:
  let a as int is 3.14
  let b as int is "hello"
  let c as int is true
"""
        tree = self.parser.parse(code)
        try:
            self.checker.check(tree)
            self.fail("Expected PenguError to be raised")
        except PenguError as err:
            self.assertTrue(hasattr(err, "all_errors"))
            self.assertGreaterEqual(len(err.all_errors), 3)
            self.assertTrue(hasattr(err, "rendered_all"))
            self.assertGreaterEqual(err.rendered_all.count("error["), 3)
            self.assertGreaterEqual(err.rendered_all.count("-->"), 3)


if __name__ == "__main__":
    unittest.main()
