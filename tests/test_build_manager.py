import unittest
import tempfile
import os
import sys
import json
from pengu_project import ProjectConfig, PenguBuilder, OutputType


class TestBuildManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_config_load_yaml(self):
        yaml_content = """project:
  name: "physics_app"
  version: "0.2.0"
  entry: "main.pengu"
  output: "static"
  output_name: "libphysics"

build:
  links: ["m", "pthread"]
  cflags: ["-O3", "-Wall"]
"""
        yaml_path = os.path.join(self.base_dir, "pengu.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        config = ProjectConfig.load(yaml_path)
        self.assertEqual(config.name, "physics_app")
        self.assertEqual(config.version, "0.2.0")
        self.assertEqual(config.output, OutputType.STATIC)
        self.assertEqual(config.output_name, "libphysics")
        self.assertEqual(len(config.links), 2)
        self.assertIn("m", config.links)
        self.assertIn("pthread", config.links)

    def test_config_load_json(self):
        data = {
            "project": {
                "name": "web_server",
                "version": "1.0.0",
                "entry": "server.pengu",
                "output": "shared",
                "output_name": "libserver"
            },
            "build": {
                "links": ["ssl", "crypto"],
                "include_dirs": ["./include"],
                "lib_dirs": ["./lib"]
            }
        }
        json_path = os.path.join(self.base_dir, "pengu.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        config = ProjectConfig.load(json_path)
        self.assertEqual(config.name, "web_server")
        self.assertEqual(config.entry, "server.pengu")
        self.assertEqual(config.output, OutputType.SHARED)
        self.assertEqual(config.links, ["ssl", "crypto"])
        self.assertEqual(config.include_dirs, ["./include"])
        self.assertEqual(config.lib_dirs, ["./lib"])

    def test_bundle_c_only(self):
        entry_code = """weave main into void:
  var x as int is 42
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(entry_code)

        config = ProjectConfig(
            name="test_c",
            entry="main.pengu",
            output=OutputType.C,
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        bundle_path, is_cached = builder.bundle()
        self.assertTrue(os.path.isfile(bundle_path))

        with open(bundle_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("pengu_runtime.h", content)
        self.assertIn("main.pengu", content)

        # compile with output=c should return bundle.c without executing compiler
        out, _ = builder.compile(bundle_path)
        self.assertEqual(out, bundle_path)

    def test_compile_exe_custom_links(self):
        config = ProjectConfig(
            name="game",
            output=OutputType.EXE,
            output_name="game_bin",
            links=["raylib", "m"],
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        commands = builder.build_compile_commands("bundle.c", "game_bin.exe")
        self.assertEqual(len(commands), 1)
        cmd_str = " ".join(commands[0])
        self.assertIn("-lraylib", cmd_str)
        self.assertIn("-lm", cmd_str)

    def test_output_types(self):
        # 1. OBJ
        config_obj = ProjectConfig(output=OutputType.OBJ, output_name="mod", base_dir=self.base_dir)
        builder_obj = PenguBuilder(config_obj)
        cmds_obj = builder_obj.build_compile_commands("bundle.c", "mod.o")
        self.assertEqual(cmds_obj[0][:4], ["gcc", "-c", "bundle.c", "-o"])

        # 2. STATIC
        config_static = ProjectConfig(output=OutputType.STATIC, output_name="mylib", base_dir=self.base_dir)
        builder_static = PenguBuilder(config_static)
        cmds_static = builder_static.build_compile_commands("bundle.c", "mylib.a")
        self.assertEqual(len(cmds_static), 2)
        self.assertEqual(cmds_static[1][:3], ["ar", "rcs", "mylib.a"])

        # 3. SHARED
        config_shared = ProjectConfig(output=OutputType.SHARED, output_name="mylib", base_dir=self.base_dir)
        builder_shared = PenguBuilder(config_shared)
        cmds_shared = builder_shared.build_compile_commands("bundle.c", "mylib.dll")
        if sys.platform == "win32":
            self.assertIn("-shared", cmds_shared[0])
            self.assertNotIn("-fPIC", cmds_shared[0])
        else:
            self.assertIn("-fPIC", cmds_shared[0])
            self.assertIn("-shared", cmds_shared[0])

        # 4. C
        config_c = ProjectConfig(output=OutputType.C, base_dir=self.base_dir)
        builder_c = PenguBuilder(config_c)
        cmds_c = builder_c.build_compile_commands("bundle.c", "bundle.c")
        self.assertEqual(cmds_c, [])

    def test_no_hardcoded_raylib(self):
        config = ProjectConfig(
            name="headless",
            output=OutputType.EXE,
            output_name="headless_app",
            links=[],
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        commands = builder.build_compile_commands("bundle.c", "headless_app.exe")
        cmd_str = " ".join(commands[0])
        self.assertNotIn("-lraylib", cmd_str)
        self.assertNotIn("-l", cmd_str)


if __name__ == "__main__":
    unittest.main()
