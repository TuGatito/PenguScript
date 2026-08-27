import unittest
from pengu_parser import PenguParser, PenguChecker


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_memory_management(self):
        code = """declare alloc with bytes as int into ref to int

weave test_memory into void:
  let p as ref to int is calling alloc with size of int
  defer banish p
  errdefer banish p
  set essence of p is 10
  banish p
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
