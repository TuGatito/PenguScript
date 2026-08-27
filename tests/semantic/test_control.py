import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import InvalidControlFlowError, TypeMismatchError


class TestControl(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_control_flow_valid(self):
        code = """rune File:
  name as string

declare open with path as string into maybe File

weave main with arr as list of int into int:
  if file as File is calling open with "f.txt" is present:
    let n is file.name

  var i as int is 0
  while i < 10:
    set i is i + 1
    if i == 5: break
    if i == 3: continue

  for item in arr:
    let val is item

  for idx from 0 to 10 step 2:
    set i is idx

  return 0
"""
        tree = self.parser.parse(code)
        self.checker.check(tree)

    def test_break_outside_loop_fails(self):
        code = """weave main into void:
  break
"""
        tree = self.parser.parse(code)
        with self.assertRaises(InvalidControlFlowError):
            self.checker.check(tree)

    def test_continue_outside_loop_fails(self):
        code = """weave main into void:
  continue
"""
        tree = self.parser.parse(code)
        with self.assertRaises(InvalidControlFlowError):
            self.checker.check(tree)

    def test_for_from_non_int_fails(self):
        code = """weave main into void:
  for i from "start" to 10:
    let x is i
"""
        tree = self.parser.parse(code)
        with self.assertRaises(TypeMismatchError):
            self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
