import os
import tempfile
import shutil
import unittest
from pengu_parser import PenguParser, PenguChecker, resolve_imports
from pengu_parser.pengu_errors import SemanticError, PenguError


class TestModuleResolution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.parser = PenguParser()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_file(self, rel_path: str, content: str) -> str:
        full_path = os.path.join(self.temp_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return full_path

    def test_linear_module_resolution(self):
        # a -> b -> c
        self._write_file("c.pengu", """rune Point:
  x as int
  y as int
""")
        self._write_file("b.pengu", """import c

weave make_point into c.Point:
  with x is 1 and y is 2
""")
        self._write_file("a.pengu", """import b

weave main into void:
  let p is calling b.make_point
""")
        order = resolve_imports(self.temp_dir, "a.pengu", self.parser)
        base_names = [os.path.basename(p) for p in order]
        self.assertEqual(base_names, ["c.pengu", "b.pengu", "a.pengu"])

    def test_circular_module_dependency_fails(self):
        # a -> b -> a
        self._write_file("a.pengu", """import b
weave a_fn into void:
  return
""")
        self._write_file("b.pengu", """import a
weave b_fn into void:
  return
""")
        with self.assertRaises(SemanticError) as ctx:
            resolve_imports(self.temp_dir, "a.pengu", self.parser)

        err_str = str(ctx.exception).lower()
        self.assertIn("circular", err_str)
        self.assertEqual(ctx.exception.code, "E0004")

    def test_package_init_module_resolution(self):
        self._write_file("math/vector.pengu", """rune Vec2:
  x as float
  y as float
""")
        self._write_file("math/__init__.pengu", """import math.vector
""")
        self._write_file("main.pengu", """import math
weave main into void:
  return
""")
        order = resolve_imports(self.temp_dir, "main.pengu", self.parser)
        base_names = [os.path.basename(p) for p in order]
        self.assertEqual(base_names, ["vector.pengu", "__init__.pengu", "main.pengu"])


if __name__ == "__main__":
    unittest.main()
