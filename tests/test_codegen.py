import unittest
import tempfile
import os
import subprocess
import sys
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_project import ProjectConfig, PenguBuilder, OutputType


class TestCodegen(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_forward_declarations(self):
        code = """rune Node:
  value as int
  next as maybe ref to Node

rune Tree:
  root as maybe ref to Node
  count as int

weave create_tree into Tree:
  var n as Node is with value is 10 and next is maybe none
  return with root is maybe none and count is 1
"""
        parser = PenguParser()
        checker = PenguChecker(base_dir=self.base_dir)
        ast = parser.parse(code)
        checker.check(ast, source=code)

        codegen = PenguCodegen(checker.symbols, ["main.pengu"], self.base_dir)
        codegen.collect_declarations([("main.pengu", ast)])
        bundle_c = codegen.generate_bundle()

        # Verify forward declarations appear before type definitions
        pos_fwd_node = bundle_c.find("typedef struct Node Node;")
        pos_fwd_tree = bundle_c.find("typedef struct Tree Tree;")
        pos_def_node = bundle_c.find("struct Node {")
        pos_def_tree = bundle_c.find("struct Tree {")

        self.assertNotEqual(pos_fwd_node, -1)
        self.assertNotEqual(pos_fwd_tree, -1)
        self.assertNotEqual(pos_def_node, -1)
        self.assertNotEqual(pos_def_tree, -1)

        self.assertLess(pos_fwd_node, pos_def_node)
        self.assertLess(pos_fwd_tree, pos_def_tree)

    def test_topological_order(self):
        # b.pengu defines Vec2
        b_code = """rune Vec2:
  x as float
  y as float

weave vec2_add with a as Vec2, b as Vec2 into Vec2:
  return with x is a.x + b.x and y is a.y + b.y
"""
        b_path = os.path.join(self.base_dir, "b.pengu")
        with open(b_path, "w", encoding="utf-8") as f:
            f.write(b_code)

        # a.pengu imports b and uses Vec2
        a_code = """import b

weave main into void:
  var v1 as Vec2 is with x is 1.0 and y is 2.0
  var v2 as Vec2 is with x is 3.0 and y is 4.0
  var v3 as Vec2 is calling vec2_add with v1 and v2
"""
        a_path = os.path.join(self.base_dir, "a.pengu")
        with open(a_path, "w", encoding="utf-8") as f:
            f.write(a_code)

        config = ProjectConfig(
            name="test_topo",
            entry="a.pengu",
            output=OutputType.EXE,
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        bundle_path, _ = builder.bundle()

        with open(bundle_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that vec2_add definition appears before main definition
        pos_vec_add = content.find("Vec2 vec2_add(Vec2 a, Vec2 b)")
        pos_main = content.find("void pengu_main(void)")

        self.assertNotEqual(pos_vec_add, -1)
        self.assertNotEqual(pos_main, -1)
        self.assertLess(pos_vec_add, pos_main)

    def test_no_need_after(self):
        # Mutual / Forward function usage
        code = """weave is_even with n as int into bool:
  if n == 0:
    return true
  return calling is_odd with n - 1

weave is_odd with n as int into bool:
  if n == 0:
    return false
  return calling is_even with n - 1

weave main into void:
  var res as bool is calling is_even with 4
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(code)

        config = ProjectConfig(
            name="mutual_fn",
            entry="main.pengu",
            output=OutputType.OBJ,
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        obj_path, _ = builder.compile()

        self.assertTrue(os.path.isfile(obj_path))

    def test_bundle_compiles_and_runs(self):
        code = """weave main into void:
  var msg as string is "Hello from PenguScript v0.6!"
  calling print with msg
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(code)

        config = ProjectConfig(
            name="hello_app",
            entry="main.pengu",
            output=OutputType.EXE,
            output_name="hello_app",
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        exe_path, _ = builder.compile()

        self.assertTrue(os.path.isfile(exe_path))

        # Run compiled binary
        res = subprocess.run([exe_path], capture_output=True, text=True, cwd=self.base_dir)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Hello from PenguScript v0.6!", res.stdout)

    def test_static_lib(self):
        code = """weave add with a as int, b as int into int:
  return a + b

weave sub with a as int, b as int into int:
  return a - b
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(code)

        config = ProjectConfig(
            name="math_lib",
            entry="main.pengu",
            output=OutputType.STATIC,
            output_name="libmath",
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        lib_path, _ = builder.compile()

        self.assertTrue(os.path.isfile(lib_path))
        self.assertTrue(lib_path.endswith(".a") or lib_path.endswith(".lib"))


if __name__ == "__main__":
    unittest.main()
