import unittest
import tempfile
import os
import sys
import shutil
import json
from pengu_project import (
    ProjectConfig, PenguBuilder, OutputType,
    init_project, add_dependency, extract_lib_name
)
from pengu_parser.pengu_symbols import find_module_path, resolve_imports
from pengu_parser.pengu_parser import PenguParser


class TestBindingsAndProjectStructure(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name
        self.parser = PenguParser()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_lib_name(self):
        self.assertEqual(extract_lib_name("libwebui-2-static.a"), "webui-2-static")
        self.assertEqual(extract_lib_name("libraylib.a"), "raylib")
        self.assertEqual(extract_lib_name("webui.lib"), "webui")
        self.assertEqual(extract_lib_name("libfoo.so"), "foo")
        self.assertEqual(extract_lib_name("libbar.dylib"), "bar")
        self.assertEqual(extract_lib_name("foo.dll"), "foo")
        self.assertIsNone(extract_lib_name("readme.txt"))
        self.assertIsNone(extract_lib_name("main.pengu"))

    def test_init_project_creates_structure(self):
        proj_dir = init_project("my_rpg", output_type="exe", target_dir=self.base_dir)
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "src")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "lib")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "include")))
        self.assertTrue(os.path.isdir(os.path.join(proj_dir, "c")))
        self.assertTrue(os.path.isfile(os.path.join(proj_dir, "src", "main.pengu")))
        self.assertTrue(os.path.isfile(os.path.join(proj_dir, "pengu.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(proj_dir, ".gitignore")))
        self.assertTrue(os.path.isfile(os.path.join(proj_dir, "README.md")))

        config = ProjectConfig.load(proj_dir)
        self.assertEqual(config.name, "my_rpg")
        self.assertEqual(config.src_dir, "src")
        self.assertEqual(config.lib_dir, "lib")
        self.assertEqual(config.include_dir, "include")
        self.assertEqual(config.c_dir, "c")
        self.assertEqual(config.resolve_entry(), os.path.abspath(os.path.join(proj_dir, "src", "main.pengu")))

    def test_find_module_path_in_src_and_lib(self):
        proj_dir = os.path.join(self.base_dir, "app")
        os.makedirs(os.path.join(proj_dir, "src", "math"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "webui", "pengu"), exist_ok=True)

        # src/math/vec.pengu
        vec_file = os.path.join(proj_dir, "src", "math", "vec.pengu")
        with open(vec_file, "w", encoding="utf-8") as f:
            f.write("rune Vec2:\n  x as float\n  y as float\n")

        # lib/webui/pengu/webui.pengu
        webui_file = os.path.join(proj_dir, "lib", "webui", "pengu", "webui.pengu")
        with open(webui_file, "w", encoding="utf-8") as f:
            f.write('include "webui.h"\nlink "webui"\nweave new_window into int:\n  return 1\n')

        # 1. Resolve internal src module
        res_vec = find_module_path(proj_dir, "math.vec")
        self.assertIsNotNone(res_vec)
        self.assertEqual(os.path.abspath(res_vec), os.path.abspath(vec_file))

        # 2. Resolve external binding module
        res_webui = find_module_path(proj_dir, "webui")
        self.assertIsNotNone(res_webui)
        self.assertEqual(os.path.abspath(res_webui), os.path.abspath(webui_file))

    def test_resolve_imports_with_binding(self):
        proj_dir = os.path.join(self.base_dir, "game")
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "raylib", "pengu"), exist_ok=True)

        # lib/raylib/pengu/raylib.pengu
        raylib_file = os.path.join(proj_dir, "lib", "raylib", "pengu", "raylib.pengu")
        with open(raylib_file, "w", encoding="utf-8") as f:
            f.write('include "raylib.h"\nlink "raylib"\nweave init_window with w as int, h as int into void:\n  return\n')

        # src/main.pengu
        main_file = os.path.join(proj_dir, "src", "main.pengu")
        with open(main_file, "w", encoding="utf-8") as f:
            f.write('import raylib\n\nweave main into void:\n  calling raylib.init_window with 800, 600\n')

        order = resolve_imports(proj_dir, "src/main.pengu", self.parser)
        self.assertEqual(len(order), 2)
        self.assertTrue(order[0].endswith("raylib.pengu"))
        self.assertTrue(order[1].endswith("main.pengu"))

    def test_bundle_with_binding_and_codegen(self):
        proj_dir = os.path.join(self.base_dir, "gui_app")
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "ui", "pengu"), exist_ok=True)

        ui_file = os.path.join(proj_dir, "lib", "ui", "pengu", "ui.pengu")
        with open(ui_file, "w", encoding="utf-8") as f:
            f.write('include "ui_native.h"\nlink "ui_native"\nweave show_dialog with msg as string into void:\n  calling print with msg\n')

        main_file = os.path.join(proj_dir, "src", "main.pengu")
        with open(main_file, "w", encoding="utf-8") as f:
            f.write('import ui\n\nweave main into void:\n  var txt as string is "Hello UI"\n  calling ui.show_dialog with txt\n')

        config = ProjectConfig(
            name="gui_app",
            base_dir=proj_dir,
            entry="src/main.pengu"
        )
        builder = PenguBuilder(config)
        bundle_path, is_cached = builder.bundle()
        self.assertTrue(os.path.isfile(bundle_path))

        with open(bundle_path, "r", encoding="utf-8") as f:
            c_code = f.read()

        self.assertIn('#include "ui_native.h"', c_code)
        self.assertIn("show_dialog", c_code)
        self.assertIn("pengu_main", c_code)

    def test_build_compile_commands_collects_c_and_lib_dirs(self):
        proj_dir = os.path.join(self.base_dir, "multi_c_proj")
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "include"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "c"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "mylib", "include"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "mylib", "c"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib", "mylib", "lib"), exist_ok=True)

        # Project C glue
        proj_c = os.path.join(proj_dir, "c", "helper.c")
        with open(proj_c, "w", encoding="utf-8") as f:
            f.write("void helper_fn() {}\n")

        # Binding C glue
        binding_c = os.path.join(proj_dir, "lib", "mylib", "c", "mylib_glue.c")
        with open(binding_c, "w", encoding="utf-8") as f:
            f.write("void mylib_c_func() {}\n")

        # Binding precompiled library (dummy file to test detection)
        binding_lib_file = os.path.join(proj_dir, "lib", "mylib", "lib", "libmylib_native.a")
        with open(binding_lib_file, "w", encoding="utf-8") as f:
            f.write("dummy archive")

        config = ProjectConfig(
            name="multi_c_app",
            base_dir=proj_dir,
            entry="src/main.pengu",
            output=OutputType.EXE
        )
        builder = PenguBuilder(config)
        commands = builder.build_compile_commands("build/bundle.c", "build/app.exe")
        self.assertEqual(len(commands), 1)

        cmd_args = commands[0]
        cmd_str = " ".join(cmd_args)

        # Check that helper.c and mylib_glue.c are included
        self.assertTrue(any("helper.c" in arg for arg in cmd_args))
        self.assertTrue(any("mylib_glue.c" in arg for arg in cmd_args))

        # Check include directories
        self.assertTrue(any(arg.startswith("-I") and "include" in arg for arg in cmd_args))
        self.assertTrue(any(arg.startswith("-I") and "mylib" in arg for arg in cmd_args))

        # Check library search directory and link flag
        self.assertTrue(any(arg.startswith("-L") and "mylib" in arg for arg in cmd_args))
        self.assertIn("-lmylib_native", cmd_str)

    def test_add_dependency_local_folder(self):
        # 1. Initialize project
        proj_dir = init_project("main_app", output_type="exe", target_dir=self.base_dir)

        # 2. Create external local binding folder
        ext_binding = os.path.join(self.base_dir, "webui_repo")
        os.makedirs(os.path.join(ext_binding, "pengu"), exist_ok=True)
        os.makedirs(os.path.join(ext_binding, "include"), exist_ok=True)
        os.makedirs(os.path.join(ext_binding, "c"), exist_ok=True)
        os.makedirs(os.path.join(ext_binding, "lib"), exist_ok=True)

        with open(os.path.join(ext_binding, "pengu", "webui.pengu"), "w", encoding="utf-8") as f:
            f.write('weave webui_init into int:\n  return 0\n')
        with open(os.path.join(ext_binding, "include", "webui.h"), "w", encoding="utf-8") as f:
            f.write('int webui_init(void);\n')

        # Create dummy build.py
        with open(os.path.join(ext_binding, "build.py"), "w", encoding="utf-8") as f:
            f.write('print("Building webui...")\n')

        # 3. Add dependency
        added_dir = add_dependency(
            source=ext_binding,
            name="webui",
            config_path=proj_dir,
            run_build=True
        )
        self.assertTrue(os.path.isdir(added_dir))
        self.assertTrue(os.path.isfile(os.path.join(added_dir, "pengu", "webui.pengu")))
        self.assertTrue(os.path.isfile(os.path.join(added_dir, "include", "webui.h")))

        # 4. Verify pengu.yaml contains dependency
        with open(os.path.join(proj_dir, "pengu.yaml"), "r", encoding="utf-8") as f:
            yaml_txt = f.read()
        self.assertIn("webui", yaml_txt)

    def test_legacy_flat_project_compatibility(self):
        # Test project with old flat structure (main.pengu at root, no src/ folder)
        legacy_dir = os.path.join(self.base_dir, "legacy")
        os.makedirs(legacy_dir, exist_ok=True)

        main_pengu = os.path.join(legacy_dir, "main.pengu")
        with open(main_pengu, "w", encoding="utf-8") as f:
            f.write("weave main into void:\n  calling print with 123\n")

        legacy_yaml = os.path.join(legacy_dir, "pengu.yaml")
        with open(legacy_yaml, "w", encoding="utf-8") as f:
            f.write("project:\n  name: legacy\n  entry: main.pengu\n")

        config = ProjectConfig.load(legacy_dir)
        self.assertEqual(config.resolve_entry(), os.path.abspath(main_pengu))

        builder = PenguBuilder(config)
        bundle_path, _ = builder.bundle()
        self.assertTrue(os.path.isfile(bundle_path))


if __name__ == "__main__":
    unittest.main()
