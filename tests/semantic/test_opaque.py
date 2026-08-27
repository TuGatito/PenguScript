import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SemanticError


class TestOpaque(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_instantiate_opaque_alias_fails(self):
        code = """alias Texture as opaque

weave main into void:
  let t as Texture is with x is 1
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as ctx:
            self.checker.check(tree)
        self.assertIn("Cannot instantiate opaque type 'Texture' with 'with'", str(ctx.exception))

    def test_instantiate_opaque_directly_fails(self):
        code = """weave main into void:
  let t as opaque is with x is 1
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as ctx:
            self.checker.check(tree)
        self.assertIn("cannot instantiate opaque type", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
