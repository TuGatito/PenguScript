import unittest
from pengu_parser import PenguParser, PenguChecker


class TestMaybeResult(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_maybe_and_result_patterns(self):
        code = """declare open_file with path as string into maybe string
declare print with msg as string into void

weave maybe_test into int:
  let user as maybe string is maybe none
  let name is user or else "guest"
  let u is user or return 1

  let file is calling open_file with "data.txt" or:
    let err is error
    calling print with err
    return 1

  let file2 is try calling open_file with "other.txt"
  return 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
