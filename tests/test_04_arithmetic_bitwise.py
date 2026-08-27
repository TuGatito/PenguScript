import unittest
from pengu_parser import PenguParser, PenguChecker


class TestArithmeticBitwise(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_arithmetic_and_conversions(self):
        code = """include "raylib.h"

weave compute into void:
  let a is 10 + 20 * 2
  let b is (10 + 20) * 2
  let f as float is 10 to float
  let bits is transmute f to int
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_bitwise_operations(self):
        code = """include "raylib.h"

weave flags_test into void:
  let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
  let masked is flags & 0xFF
  let xored is flags ^ 1
  let not_flags is ~flags
  let shifted is 1 << 5
  let rshift is 32 >> 2
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
