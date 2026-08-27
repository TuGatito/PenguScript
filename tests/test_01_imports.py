import unittest
from pengu_parser import PenguParser, PenguChecker


class TestImports(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_import_dotted_path(self):
        code = """import src.components.Player
import src.math.Vec2
import my_module
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_include_c_header(self):
        code = """include "raylib.h"
include "pengu_runtime.h"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_link_library(self):
        code = """link "raylib"
link "m"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_combined_imports(self):
        code = """import src.math.Vec2
include "raylib.h"
link "raylib"
link "m"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
