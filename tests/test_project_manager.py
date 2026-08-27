import unittest
import tempfile
import os
import shutil
from pengu_project import ProjectConfig, PenguBuilder, OutputType, init_project, clean_project


class TestProjectManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_runtime_copy(self):
        main_code = """weave main into void:
  var x as int is 10
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_code)

        config = ProjectConfig(
            name="test_rt",
            entry="main.pengu",
            output=OutputType.C,
            build_dir="build",
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        bundle_path, _ = builder.bundle()
        self.assertTrue(os.path.isfile(bundle_path))

        rt_path = os.path.join(self.base_dir, "build", "pengu_runtime.h")
        self.assertTrue(os.path.isfile(rt_path), "Expected pengu_runtime.h to be copied to build directory")

    def test_output_dir(self):
        main_code = """weave main into void:
  var msg as string is "test"
"""
        main_path = os.path.join(self.base_dir, "main.pengu")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_code)

        config = ProjectConfig(
            name="app_dir",
            entry="main.pengu",
            build_dir="custom_build",
            output=OutputType.C,
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        bundle_path, _ = builder.bundle()
        expected_path = os.path.abspath(os.path.join(self.base_dir, "custom_build", "bundle.c"))
        self.assertEqual(os.path.abspath(bundle_path), expected_path)
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "bundle.c")))

    def test_profiles(self):
        config_release = ProjectConfig(
            name="release_app",
            output=OutputType.EXE,
            profile="release",
            base_dir=self.base_dir
        )
        builder_release = PenguBuilder(config_release)
        cmds_release = builder_release.build_compile_commands("build/bundle.c", "build/app.exe")
        cmd_str_rel = " ".join(cmds_release[0])
        self.assertIn("-O3", cmd_str_rel)
        self.assertIn("-DNDEBUG", cmd_str_rel)

        config_debug = ProjectConfig(
            name="debug_app",
            output=OutputType.EXE,
            profile="debug",
            base_dir=self.base_dir
        )
        builder_debug = PenguBuilder(config_debug)
        cmds_debug = builder_debug.build_compile_commands("build/bundle.c", "build/app.exe")
        cmd_str_deb = " ".join(cmds_debug[0])
        self.assertIn("-g", cmd_str_deb)
        self.assertIn("-DDEBUG", cmd_str_deb)

    def test_init_by_type(self):
        proj_dir = init_project(name="my_lib", output_type="static", target_dir=self.base_dir)
        yaml_path = os.path.join(proj_dir, "pengu.yaml")
        main_path = os.path.join(proj_dir, "main.pengu")
        gitignore_path = os.path.join(proj_dir, ".gitignore")
        readme_path = os.path.join(proj_dir, "README.md")

        self.assertTrue(os.path.isfile(yaml_path))
        self.assertTrue(os.path.isfile(main_path))
        self.assertTrue(os.path.isfile(gitignore_path))
        self.assertTrue(os.path.isfile(readme_path))

        config = ProjectConfig.load(yaml_path)
        self.assertEqual(config.output, OutputType.STATIC)

        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("weave add", content)
        self.assertIn("Static library", content)

    def test_init_exe_template(self):
        proj_dir = init_project(name="my_game", output_type="exe", target_dir=self.base_dir)
        main_path = os.path.join(proj_dir, "main.pengu")

        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("weave main into void:", content)
        self.assertIn("Hello from my_game!", content)

    def test_no_hardcoded_raylib(self):
        config = ProjectConfig(
            name="standalone",
            output=OutputType.EXE,
            output_name="bin",
            links=[],
            base_dir=self.base_dir
        )
        builder = PenguBuilder(config)
        cmds = builder.build_compile_commands("build/bundle.c", "build/bin.exe")
        cmd_str = " ".join(cmds[0])
        self.assertNotIn("-lraylib", cmd_str)
        self.assertNotIn("-l", cmd_str)


if __name__ == "__main__":
    unittest.main()
