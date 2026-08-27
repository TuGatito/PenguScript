import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError, TypeMismatchError


class TestOrError(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_or_else_and_or_block_valid(self):
        code = """declare open_file with path as string into maybe string
declare print with msg as string into void

weave main into int:
  let opt as maybe string is maybe none
  let fallback is opt or else "default"

  let res is calling open_file with "test.txt" or:
    let err is error
    calling print with err
    return 1

  return 0
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_error_outside_or_block_fails(self):
        code = """weave main into void:
  let err is error
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree)

    def test_or_else_type_mismatch_fails(self):
        code = """weave main into void:
  let opt as maybe int is maybe none
  let val is opt or else "string_fallback"
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
