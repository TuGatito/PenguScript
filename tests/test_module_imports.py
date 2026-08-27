import unittest
import tempfile
import os
from pengu_parser import PenguParser, PenguChecker, resolve_imports
from pengu_parser.pengu_errors import SemanticError


class TestModuleImports(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name
        self.parser = PenguParser()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_linear_module_resolution(self):
        # b.pengu
        b_path = os.path.join(self.base_dir, "b.pengu")
        with open(b_path, "w", encoding="utf-8") as f:
            f.write("rune B:\n  y as int\n")

        # a.pengu
        a_path = os.path.join(self.base_dir, "a.pengu")
        with open(a_path, "w", encoding="utf-8") as f:
            f.write("import b\nrune A:\n  x as int\n")

        order = resolve_imports(self.base_dir, "a.pengu", self.parser)
        self.assertEqual(len(order), 2)
        self.assertTrue(order[0].endswith("b.pengu"))
        self.assertTrue(order[1].endswith("a.pengu"))

    def test_circular_module_resolution_fails(self):
        # a.pengu imports b
        a_path = os.path.join(self.base_dir, "a.pengu")
        with open(a_path, "w", encoding="utf-8") as f:
            f.write("import b\nrune A:\n  x as int\n")

        # b.pengu imports a
        b_path = os.path.join(self.base_dir, "b.pengu")
        with open(b_path, "w", encoding="utf-8") as f:
            f.write("import a\nrune B:\n  y as int\n")

        with self.assertRaises(SemanticError) as ctx:
            resolve_imports(self.base_dir, "a.pengu", self.parser)
        self.assertEqual(ctx.exception.code, "E0004")
        self.assertIn("circular", ctx.exception.help.lower())


if __name__ == "__main__":
    unittest.main()
