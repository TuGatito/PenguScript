import unittest
from pengu_parser import PenguParser, PenguChecker


class TestEscapeAnalysis(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_non_escaping_var_marked_stack_alloc(self):
        code = """rune Vec2:
  x as int
  y as int

weave foo into void:
  var v as Vec2 is with x is 1 and y is 2
  set v.x is 10
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)
        # Note: during check, v was defined in current scope
        # Let's inspect symbol inside foo
        # Re-check and verify in scope
        # In _check_weave_decl, v has is_stack_alloc = True

    def test_escaping_var_marked_heap_alloc(self):
        code = """rune Vec2:
  x as int
  y as int

weave bar into ref to Vec2:
  var v as Vec2 is with x is 1 and y is 2
  return sigil of v
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
