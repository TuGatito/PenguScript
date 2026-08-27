#!/usr/bin/env python3
"""Unit and integration tests for PenguScript v0.6 Codegen fixes and optimizations."""

import os
import re
import shutil
import tempfile
import unittest
import subprocess
from typing import Optional

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_project import ProjectConfig, PenguBuilder, OutputType


class TestCodegenFixes(unittest.TestCase):
    """Verifies all C99 strict compliance, optimizations, and syntax generation fixes."""

    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _generate_bundle(self, source: str) -> str:
        """Helper to parse, check, and generate bundle.c string."""
        tree = self.parser.parse(source)
        self.checker.check(tree, source=source, filename="main.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], self.temp_dir)
        codegen.collect_declarations([("main.pengu", tree)])
        return codegen.generate_bundle()

    def test_no_auto(self):
        """Checks that generated C code contains no C++ 'auto' keyword and compiles cleanly."""
        code = """rune Vec2:
  x as int
  y as int

weave main into void:
  var v as Vec2 is with x is 10 and y is 20
  let a, b is v
  var items as list of int is list of int with capacity 4
  for item in items:
    calling print with item
"""

        bundle_c = self._generate_bundle(code)
        # Ensure no standalone 'auto' keyword in C output
        self.assertIsNone(re.search(r"\bauto\b", bundle_c), f"Found 'auto' keyword in bundle.c:\n{bundle_c}")

        # Verify compilation with gcc -std=c11 -Wall -Wextra
        bundle_file = os.path.join(self.temp_dir, "bundle.c")
        obj_file = os.path.join(self.temp_dir, "bundle.o")
        with open(bundle_file, "w", encoding="utf-8") as f:
            f.write(bundle_c)

        runtime_src = os.path.abspath("pengu_runtime.h")
        runtime_dst = os.path.join(self.temp_dir, "pengu_runtime.h")
        shutil.copy(runtime_src, runtime_dst)

        res = subprocess.run(
            ["gcc", "-std=c11", "-Wall", "-Wextra", "-I", self.temp_dir, "-c", bundle_file, "-o", obj_file],
            cwd=self.temp_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Compilation failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_with_desugar(self):
        """Verifies that with player: set x is 10 generates player.x = 10;"""
        code = """rune Player:
  x as int
  y as int

weave main into void:
  var player as Player is with x is 0 and y is 0
  with player:
    set x is 10
    set y is 20
"""
        bundle_c = self._generate_bundle(code)
        self.assertIn("player.x = 10;", bundle_c)
        self.assertIn("player.y = 20;", bundle_c)

    def test_defer_on_return(self):
        """Verifies that defer statements are executed before return statements."""
        code = """weave bar into void:
  return

weave foo into int:
  defer calling bar
  return 1
"""
        bundle_c = self._generate_bundle(code)
        # Verify that bar() is called before return
        self.assertIn("bar();", bundle_c)
        self.assertRegex(bundle_c, r"bar\(\);\s*return\b")

    def test_array_size(self):
        """Verifies that fixed array declarations include [size] in C."""
        code = """weave main into void:
  var arr as array of int is array of int with size 10
"""
        bundle_c = self._generate_bundle(code)
        self.assertIn("arr[10]", bundle_c)


    def test_forward_consistency(self):
        """Verifies consistent standard forward struct and typedef declarations."""
        code = """rune Vec2:
  x as int
  y as int
"""
        bundle_c = self._generate_bundle(code)
        self.assertIn("struct Vec2;", bundle_c)
        self.assertIn("typedef struct Vec2 Vec2;", bundle_c)
        self.assertIn("struct Vec2 {", bundle_c)

    def test_stack_alloc_used(self):
        """Verifies stack allocation annotation or comment for non-escaping variables."""
        code = """rune Vec2:
  x as int
  y as int

weave main into void:
  var v as Vec2 is with x is 1 and y is 2
"""
        bundle_c = self._generate_bundle(code)
        self.assertIn("/* stack */", bundle_c)

    def test_const_folding_codegen(self):
        """Verifies that constant folding generates literal values directly in C."""
        code = """const A as int is 10 + 20

weave main into void:
  var x as int is A
"""
        bundle_c = self._generate_bundle(code)

        self.assertIn("#define A 30", bundle_c)
        self.assertIn("int32_t x = 30;", bundle_c)

    def test_dead_code_elim(self):
        """Verifies that constant condition if-statements eliminate dead branches."""
        code = """weave main into void:
  var x as int is 0
  if true:
    set x is 1
  else:
    set x is 2
"""
        bundle_c = self._generate_bundle(code)
        self.assertIn("/* dead code eliminated (branch always true) */", bundle_c)
        self.assertIn("x = 1;", bundle_c)
        self.assertNotIn("x = 2;", bundle_c)


if __name__ == "__main__":
    unittest.main()
