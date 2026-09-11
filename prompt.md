En Github actions ninguna plataforma logra pasar los tests para despue subir el archivo y distribuirlo. Te voy a pasar cada log de cada plataforma. Asgurate si es error por que el tests esta desactualizado con las novedades del lenguaje y el compilador o si esta mal echo, o, si es error en el compilador.

Tambien, mejora el Github Action para que este cree un tag en automatico cuando los tests pasen en todas las plataformas y se hayan subido los artifacts

Los datos como version, titulo y que cambios se hicienron debe tormalos del changelog.md que tu vas a ir actulizando conforme avanzamos en el proyecto. De esta manera podra tener un registro de todo lo que se ha hecho. Y actualizalo cuando termines de resolver este problema e implementar la mejora.

error de linux:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 52%]
.............................................................s..ss...... [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
............................s..............................s............ [ 88%]
........s....................FF......................................... [ 97%]
........................ [100%]
=================================== FAILURES ===================================
** TestBindingOmenVariants.test*bare_module_qualified_variants_build_and_run ***

self = <tests.test_p3_criticals.TestBindingOmenVariants object at 0x7f5a38c2bed0>

    @requires_cc
    @requires_runtime
    def test_bare_module_qualified_variants_build_and_run(self):
        """raylib.FLAG_MSAA_4X_HINT, raylib.KEY_RIGHT and raylib.SHADER_UNIFORM_FLOAT emit unprefixed C names."""
        src = (
            "import std.raylib\n\n"
            "weave main into int:\n"
            "    calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT\n"
            "    var d as bool is calling raylib.IsKeyDown with raylib.KEY_RIGHT\n"
            "    var u as ShaderUniformDataType is raylib.SHADER_UNIFORM_FLOAT\n"
            "    return 0\n"
        )
        c_code = bundle_project(src, tag="c1_bare_variants")
        assert "SetConfigFlags(FLAG_MSAA_4X_HINT);" in c_code
        assert "IsKeyDown(KEY_RIGHT);" in c_code
        assert "SHADER_UNIFORM_FLOAT" in c_code
        assert "raylib_FLAG_MSAA_4X_HINT" not in c_code
        assert "raylib_KEY_RIGHT" not in c_code
        assert "raylib_SHADER_UNIFORM_FLOAT" not in c_code

>       res = compile_run(src, tag="c1_bare_run", extra_libs=RAYLIB_LIBS)

              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_p3_criticals.py:48:

---

source = 'import std.raylib\n\nweave main into int:\n calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT\n var d...lib.IsKeyDown with raylib.KEY_RIGHT\n var u as ShaderUniformDataType is raylib.SHADER_UNIFORM_FLOAT\n return 0\n'
tag = 'c1_bare_run'
extra_libs = ['-lraylib', '-lGL', '-lm', '-lpthread', '-ldl', '-lrt', ...]
cwd = None, timeout = 180

    def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                    timeout: int = 180) -> subprocess.CompletedProcess:
        """Writes ``source`` to a temp project, bundles, compiles and runs it.

        Returns the CompletedProcess of the executed binary. Decorating tests with
        ``@requires_runtime`` gives a nicer skip message than the internal asserts.
        """
        assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
        assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

        from pengu_project import PenguBuilder, ProjectConfig

        d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
        try:
            entry = d / f"{tag}.pengu"
            entry.write_text(source, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

            cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
            exe = d / ("bin.exe" if is_windows() else "bin")
            cmd = [cc, str(bundle_path),
                   f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
                   f"-L{BUILD_LIB}"]
            # GCC 14 turns implicit declarations / int-conversion into errors by
            # default; generated C may trigger those warnings on newer toolchains,
            # so keep them as warnings across compilers.
            cmd += ["-Wno-error=implicit-function-declaration",
                    "-Wno-error=implicit-int",
                    "-Wno-error=int-conversion"]
            cmd += runtime_link_flags()
            if extra_libs:
                cmd += list(extra_libs)
            cmd += runtime_tail_flags()
            cmd += ["-o", str(exe)]

            res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                                 text=True, timeout=timeout)

>           assert res.returncode == 0, (

                f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
            )

E AssertionError: Compilation failed (1):
E /usr/bin/ld: cannot find -lraylib: No such file or directory
E collect2: error: ld returned 1 exit status
E  
E  
E assert 1 == 0
E + where 1 = CompletedProcess(args=['gcc', '/home/runner/work/PenguScript/PenguScript/build/pengu_c1_bare_run_o1ofwvc6/bundle.c', '...', stderr='/usr/bin/ld: cannot find -lraylib: No such file or directory\ncollect2: error: ld returned 1 exit status\n').returncode

tests/conftest.py:258: AssertionError
_ TestBindingOmenVariants.test_regression_nested_unqualified_and_const_variants _

self = <tests.test_p3_criticals.TestBindingOmenVariants object at 0x7f5a38c2bd90>

    @requires_cc
    @requires_runtime
    def test_regression_nested_unqualified_and_const_variants(self):
        """raylib.KeyboardKey.KEY_RIGHT, unqualified KEY_RIGHT, and raylib.RAYWHITE build and run."""
        src = (
            "import std.raylib\n\n"
            "weave main into int:\n"
            "    var a as bool is calling raylib.IsKeyDown with raylib.KeyboardKey.KEY_RIGHT\n"
            "    var b as bool is calling raylib.IsKeyDown with KEY_RIGHT\n"
            "    var c as raylib.Color is raylib.RAYWHITE\n"
            "    return 0\n"
        )
        c_code = bundle_project(src, tag="c1_regression")
        assert "IsKeyDown(KEY_RIGHT);" in c_code
        assert "RAYWHITE" in c_code

>       res = compile_run(src, tag="c1_regression_run", extra_libs=RAYLIB_LIBS)

              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_p3_criticals.py:67:

---

source = 'import std.raylib\n\nweave main into int:\n var a as bool is calling raylib.IsKeyDown with raylib.KeyboardKey.KEY\_...var b as bool is calling raylib.IsKeyDown with KEY_RIGHT\n var c as raylib.Color is raylib.RAYWHITE\n return 0\n'
tag = 'c1_regression_run'
extra_libs = ['-lraylib', '-lGL', '-lm', '-lpthread', '-ldl', '-lrt', ...]
cwd = None, timeout = 180

    def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                    timeout: int = 180) -> subprocess.CompletedProcess:
        """Writes ``source`` to a temp project, bundles, compiles and runs it.

        Returns the CompletedProcess of the executed binary. Decorating tests with
        ``@requires_runtime`` gives a nicer skip message than the internal asserts.
        """
        assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
        assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

        from pengu_project import PenguBuilder, ProjectConfig

        d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
        try:
            entry = d / f"{tag}.pengu"
            entry.write_text(source, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

            cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
            exe = d / ("bin.exe" if is_windows() else "bin")
            cmd = [cc, str(bundle_path),
                   f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
                   f"-L{BUILD_LIB}"]
            # GCC 14 turns implicit declarations / int-conversion into errors by
            # default; generated C may trigger those warnings on newer toolchains,
            # so keep them as warnings across compilers.
            cmd += ["-Wno-error=implicit-function-declaration",
                    "-Wno-error=implicit-int",
                    "-Wno-error=int-conversion"]
            cmd += runtime_link_flags()
            if extra_libs:
                cmd += list(extra_libs)
            cmd += runtime_tail_flags()
            cmd += ["-o", str(exe)]

            res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                                 text=True, timeout=timeout)

>           assert res.returncode == 0, (

                f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
            )

E AssertionError: Compilation failed (1):
E /usr/bin/ld: cannot find -lraylib: No such file or directory
E collect2: error: ld returned 1 exit status
E  
E  
E assert 1 == 0
E + where 1 = CompletedProcess(args=['gcc', '/home/runner/work/PenguScript/PenguScript/build/pengu_c1_regression_run_uqdfdfqq/bundle...', stderr='/usr/bin/ld: cannot find -lraylib: No such file or directory\ncollect2: error: ld returned 1 exit status\n').returncode

tests/conftest.py:258: AssertionError
=========================== short test summary info ============================
FAILED tests/test_p3_criticals.py::TestBindingOmenVariants::test_bare_module_qualified_variants_build_and_run - AssertionError: Compilation failed (1):
/usr/bin/ld: cannot find -lraylib: No such file or directory
collect2: error: ld returned 1 exit status

assert 1 == 0

- where 1 = CompletedProcess(args=['gcc', '/home/runner/work/PenguScript/PenguScript/build/pengu_c1_bare_run_o1ofwvc6/bundle.c', '...', stderr='/usr/bin/ld: cannot find -lraylib: No such file or directory\ncollect2: error: ld returned 1 exit status\n').returncode
  FAILED tests/test_p3_criticals.py::TestBindingOmenVariants::test_regression_nested_unqualified_and_const_variants - AssertionError: Compilation failed (1):
  /usr/bin/ld: cannot find -lraylib: No such file or directory
  collect2: error: ld returned 1 exit status

assert 1 == 0

- where 1 = CompletedProcess(args=['gcc', '/home/runner/work/PenguScript/PenguScript/build/pengu_c1_regression_run_uqdfdfqq/bundle...', stderr='/usr/bin/ld: cannot find -lraylib: No such file or directory\ncollect2: error: ld returned 1 exit status\n').returncode
  2 failed, 808 passed, 6 skipped in 98.45s (0:01:38)
  Error: Process completed with exit code 1.

error de mac:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 52%]
.............................................................s..ss...... [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
............................s..............................s............ [ 88%]
........s....................FF......................................... [ 97%]
........................ [100%]
=================================== FAILURES ===================================
** TestBindingOmenVariants.test*bare_module_qualified_variants_build_and_run ***

self = <tests.test_p3_criticals.TestBindingOmenVariants object at 0x108aae990>

    @requires_cc
    @requires_runtime
    def test_bare_module_qualified_variants_build_and_run(self):
        """raylib.FLAG_MSAA_4X_HINT, raylib.KEY_RIGHT and raylib.SHADER_UNIFORM_FLOAT emit unprefixed C names."""
        src = (
            "import std.raylib\n\n"
            "weave main into int:\n"
            "    calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT\n"
            "    var d as bool is calling raylib.IsKeyDown with raylib.KEY_RIGHT\n"
            "    var u as ShaderUniformDataType is raylib.SHADER_UNIFORM_FLOAT\n"
            "    return 0\n"
        )
        c_code = bundle_project(src, tag="c1_bare_variants")
        assert "SetConfigFlags(FLAG_MSAA_4X_HINT);" in c_code
        assert "IsKeyDown(KEY_RIGHT);" in c_code
        assert "SHADER_UNIFORM_FLOAT" in c_code
        assert "raylib_FLAG_MSAA_4X_HINT" not in c_code
        assert "raylib_KEY_RIGHT" not in c_code
        assert "raylib_SHADER_UNIFORM_FLOAT" not in c_code

>       res = compile_run(src, tag="c1_bare_run", extra_libs=RAYLIB_LIBS)

              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_p3_criticals.py:48:

---

source = 'import std.raylib\n\nweave main into int:\n calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT\n var d...lib.IsKeyDown with raylib.KEY_RIGHT\n var u as ShaderUniformDataType is raylib.SHADER_UNIFORM_FLOAT\n return 0\n'
tag = 'c1_bare_run'
extra_libs = ['-lraylib', '-lGL', '-lm', '-lpthread', '-ldl', '-lrt', ...]
cwd = None, timeout = 180

    def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                    timeout: int = 180) -> subprocess.CompletedProcess:
        """Writes ``source`` to a temp project, bundles, compiles and runs it.

        Returns the CompletedProcess of the executed binary. Decorating tests with
        ``@requires_runtime`` gives a nicer skip message than the internal asserts.
        """
        assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
        assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

        from pengu_project import PenguBuilder, ProjectConfig

        d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
        try:
            entry = d / f"{tag}.pengu"
            entry.write_text(source, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

            cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
            exe = d / ("bin.exe" if is_windows() else "bin")
            cmd = [cc, str(bundle_path),
                   f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
                   f"-L{BUILD_LIB}"]
            # GCC 14 turns implicit declarations / int-conversion into errors by
            # default; generated C may trigger those warnings on newer toolchains,
            # so keep them as warnings across compilers.
            cmd += ["-Wno-error=implicit-function-declaration",
                    "-Wno-error=implicit-int",
                    "-Wno-error=int-conversion"]
            cmd += runtime_link_flags()
            if extra_libs:
                cmd += list(extra_libs)
            cmd += runtime_tail_flags()
            cmd += ["-o", str(exe)]

            res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                                 text=True, timeout=timeout)

>           assert res.returncode == 0, (

                f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
            )

E AssertionError: Compilation failed (1):
E ld: warning: ignoring duplicate libraries: '-ldl', '-lm'
E ld: library 'raylib' not found
E clang: error: linker command failed with exit code 1 (use -v to see invocation)
E  
E  
E assert 1 == 0
E + where 1 = CompletedProcess(args=['gcc', '/Users/runner/work/PenguScript/PenguScript/build/pengu_c1_bare_run_a1uhypjl/bundle.c', ...m'\nld: library 'raylib' not found\nclang: error: linker command failed with exit code 1 (use -v to see invocation)\n").returncode

tests/conftest.py:258: AssertionError
_ TestBindingOmenVariants.test_regression_nested_unqualified_and_const_variants _

self = <tests.test_p3_criticals.TestBindingOmenVariants object at 0x108aaead0>

    @requires_cc
    @requires_runtime
    def test_regression_nested_unqualified_and_const_variants(self):
        """raylib.KeyboardKey.KEY_RIGHT, unqualified KEY_RIGHT, and raylib.RAYWHITE build and run."""
        src = (
            "import std.raylib\n\n"
            "weave main into int:\n"
            "    var a as bool is calling raylib.IsKeyDown with raylib.KeyboardKey.KEY_RIGHT\n"
            "    var b as bool is calling raylib.IsKeyDown with KEY_RIGHT\n"
            "    var c as raylib.Color is raylib.RAYWHITE\n"
            "    return 0\n"
        )
        c_code = bundle_project(src, tag="c1_regression")
        assert "IsKeyDown(KEY_RIGHT);" in c_code
        assert "RAYWHITE" in c_code

>       res = compile_run(src, tag="c1_regression_run", extra_libs=RAYLIB_LIBS)

              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_p3_criticals.py:67:

---

source = 'import std.raylib\n\nweave main into int:\n var a as bool is calling raylib.IsKeyDown with raylib.KeyboardKey.KEY\_...var b as bool is calling raylib.IsKeyDown with KEY_RIGHT\n var c as raylib.Color is raylib.RAYWHITE\n return 0\n'
tag = 'c1_regression_run'
extra_libs = ['-lraylib', '-lGL', '-lm', '-lpthread', '-ldl', '-lrt', ...]
cwd = None, timeout = 180

    def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                    timeout: int = 180) -> subprocess.CompletedProcess:
        """Writes ``source`` to a temp project, bundles, compiles and runs it.

        Returns the CompletedProcess of the executed binary. Decorating tests with
        ``@requires_runtime`` gives a nicer skip message than the internal asserts.
        """
        assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
        assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

        from pengu_project import PenguBuilder, ProjectConfig

        d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
        try:
            entry = d / f"{tag}.pengu"
            entry.write_text(source, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

            cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
            exe = d / ("bin.exe" if is_windows() else "bin")
            cmd = [cc, str(bundle_path),
                   f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
                   f"-L{BUILD_LIB}"]
            # GCC 14 turns implicit declarations / int-conversion into errors by
            # default; generated C may trigger those warnings on newer toolchains,
            # so keep them as warnings across compilers.
            cmd += ["-Wno-error=implicit-function-declaration",
                    "-Wno-error=implicit-int",
                    "-Wno-error=int-conversion"]
            cmd += runtime_link_flags()
            if extra_libs:
                cmd += list(extra_libs)
            cmd += runtime_tail_flags()
            cmd += ["-o", str(exe)]

            res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                                 text=True, timeout=timeout)

>           assert res.returncode == 0, (

                f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
            )

E AssertionError: Compilation failed (1):
E ld: warning: ignoring duplicate libraries: '-ldl', '-lm'
E ld: library 'raylib' not found
E clang: error: linker command failed with exit code 1 (use -v to see invocation)
E  
E  
E assert 1 == 0
E + where 1 = CompletedProcess(args=['gcc', '/Users/runner/work/PenguScript/PenguScript/build/pengu_c1_regression_run_x6purqdz/bundl...m'\nld: library 'raylib' not found\nclang: error: linker command failed with exit code 1 (use -v to see invocation)\n").returncode

tests/conftest.py:258: AssertionError
=========================== short test summary info ============================
FAILED tests/test_p3_criticals.py::TestBindingOmenVariants::test_bare_module_qualified_variants_build_and_run - AssertionError: Compilation failed (1):
ld: warning: ignoring duplicate libraries: '-ldl', '-lm'
ld: library 'raylib' not found
clang: error: linker command failed with exit code 1 (use -v to see invocation)

assert 1 == 0

- where 1 = CompletedProcess(args=['gcc', '/Users/runner/work/PenguScript/PenguScript/build/pengu_c1_bare_run_a1uhypjl/bundle.c', ...m'\nld: library 'raylib' not found\nclang: error: linker command failed with exit code 1 (use -v to see invocation)\n").returncode
  FAILED tests/test_p3_criticals.py::TestBindingOmenVariants::test_regression_nested_unqualified_and_const_variants - AssertionError: Compilation failed (1):
  ld: warning: ignoring duplicate libraries: '-ldl', '-lm'
  ld: library 'raylib' not found
  clang: error: linker command failed with exit code 1 (use -v to see invocation)

assert 1 == 0

- where 1 = CompletedProcess(args=['gcc', '/Users/runner/work/PenguScript/PenguScript/build/pengu_c1_regression_run_x6purqdz/bundl...m'\nld: library 'raylib' not found\nclang: error: linker command failed with exit code 1 (use -v to see invocation)\n").returncode
  2 failed, 808 passed, 6 skipped in 118.30s (0:01:58)
  Error: Process completed with exit code 1.

error de windows:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 52%]
........................................................................ [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
............................s........................................... [ 88%]
........F............................................................... [ 97%]
........................ [100%]
================================== FAILURES ===================================
**\*\*\*\***\_**\*\*\*\*** TestRlgl.test_rlgl_coexistence_with_raylib **\*\*\*\***\_\_**\*\*\*\***
self = <tests.test_p2_features.TestRlgl object at 0x00000189B3135590>
@requires_cc
@requires_runtime
@requires_lib("raylib")
def test_rlgl_coexistence_with_raylib(self):
"""A program importing both std.raylib and std.rlgl bundles, compiles, and shares Matrix without conflict."""
src = (
"import std.raylib as rl\n"
"import std.rlgl as rlgl\n"
"weave main into int:\n"
" calling rl.InitWindow with 100, 100, \"rlgl_test\"\n"
" calling rlgl.rlMatrixMode with rlgl.RL_MODELVIEW\n"
" calling rlgl.rlPushMatrix\n"
" var mat as rl.Matrix is calling rlgl.rlGetMatrixModelview\n"
" calling rlgl.rlSetMatrixModelview with mat\n"
" calling rlgl.rlBegin with rlgl.RL_TRIANGLES\n"
" calling rlgl.rlColor4ub with 255, 0, 0, 255\n"
" calling rlgl.rlVertex3f with 0.0, 1.0, 0.0\n"
" calling rlgl.rlVertex3f with -1.0, -1.0, 0.0\n"
" calling rlgl.rlVertex3f with 1.0, -1.0, 0.0\n"
" calling rlgl.rlEnd\n"
" calling rlgl.rlPopMatrix\n"
" calling rl.CloseWindow\n"
" if mat.m0 > 0.99 and mat.m0 < 1.01:\n"
" return 0\n"
" return 1\n"
)
libs = ["-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"] if is_windows() else ["-lraylib", "-lm"]
c_code = bundle_project(src, tag="rlgl_coexist")
assert "rlgl.h" in c_code
assert "raylib.h" in c_code
assert "rlBegin(" in c_code
assert "InitWindow(" in c_code

>       res = compile_run(src, tag="rlgl_coexist", extra_libs=libs)

              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_p2_features.py:385:

---

source = 'import std.raylib as rl\nimport std.rlgl as rlgl\nweave main into int:\n calling rl.InitWindow with 100, 100, "rlg...lgl.rlPopMatrix\n calling rl.CloseWindow\n if mat.m0 > 0.99 and mat.m0 < 1.01:\n return 0\n return 1\n'
tag = 'rlgl_coexist'
extra_libs = ['-lraylib', '-lopengl32', '-lgdi32', '-lwinmm'], cwd = None
timeout = 180
def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
timeout: int = 180) -> subprocess.CompletedProcess:
"""Writes `source` to a temp project, bundles, compiles and runs it.

        Returns the CompletedProcess of the executed binary. Decorating tests with
        ``@requires_runtime`` gives a nicer skip message than the internal asserts.
        """
        assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
        assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

        from pengu_project import PenguBuilder, ProjectConfig

        d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
        try:
            entry = d / f"{tag}.pengu"
            entry.write_text(source, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

            cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
            exe = d / ("bin.exe" if is_windows() else "bin")
            cmd = [cc, str(bundle_path),
                   f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
                   f"-L{BUILD_LIB}"]
            # GCC 14 turns implicit declarations / int-conversion into errors by
            # default; generated C may trigger those warnings on newer toolchains,
            # so keep them as warnings across compilers.
            cmd += ["-Wno-error=implicit-function-declaration",
                    "-Wno-error=implicit-int",
                    "-Wno-error=int-conversion"]
            cmd += runtime_link_flags()
            if extra_libs:
                cmd += list(extra_libs)
            cmd += runtime_tail_flags()
            cmd += ["-o", str(exe)]

            res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                                 text=True, timeout=timeout)
            assert res.returncode == 0, (
                f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
            )
            run_res = subprocess.run([str(exe)], cwd=str(cwd or REPO),
                                     capture_output=True, text=True, timeout=timeout)

>           assert run_res.returncode == 0, (

                f"Execution failed ({run_res.returncode}):\n"
                f"{run_res.stderr}\n{run_res.stdout}"
            )

E AssertionError: Execution failed (3221225477):
E  
E INFO: Initializing raylib 6.0
E INFO: Platform backend: DESKTOP (GLFW)
E INFO: Supported raylib modules:
E INFO: > rcore:..... loaded (mandatory)
E INFO: > rlgl:...... loaded (mandatory)
E INFO: > rshapes:... loaded (optional)
E INFO: > rtextures:. loaded (optional)
E INFO: > rtext:..... loaded (optional)
E INFO: > rmodels:... loaded (optional)
E INFO: > raudio:.... loaded (optional)
E WARNING: GLFW: Error: 65542 Description: WGL: The driver does not appear to support OpenGL
E WARNING: GLFW: Failed to initialize Window
E WARNING: SYSTEM: Failed to initialize platform
E  
E assert 3221225477 == 0
E + where 3221225477 = CompletedProcess(args=['D:\\a\\PenguScript\\PenguScript\\build\\pengu_rlgl_coexist_6v81k8xq\\bin.exe'], returncode=322...pport OpenGL\nWARNING: GLFW: Failed to initialize Window\nWARNING: SYSTEM: Failed to initialize platform\n', stderr='').returncode
tests\conftest.py:263: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_p2_features.py::TestRlgl::test_rlgl_coexistence_with_raylib - AssertionError: Execution failed (3221225477):

INFO: Initializing raylib 6.0
INFO: Platform backend: DESKTOP (GLFW)
INFO: Supported raylib modules:
INFO: > rcore:..... loaded (mandatory)
INFO: > rlgl:...... loaded (mandatory)
INFO: > rshapes:... loaded (optional)
INFO: > rtextures:. loaded (optional)
INFO: > rtext:..... loaded (optional)
INFO: > rmodels:... loaded (optional)
INFO: > raudio:.... loaded (optional)
WARNING: GLFW: Error: 65542 Description: WGL: The driver does not appear to support OpenGL
WARNING: GLFW: Failed to initialize Window
WARNING: SYSTEM: Failed to initialize platform

assert 3221225477 == 0

- where 3221225477 = CompletedProcess(args=['D:\\a\\PenguScript\\PenguScript\\build\\pengu_rlgl_coexist_6v81k8xq\\bin.exe'], returncode=322...pport OpenGL\nWARNING: GLFW: Failed to initialize Window\nWARNING: SYSTEM: Failed to initialize platform\n', stderr='').returncode
  1 failed, 814 passed, 1 skipped in 228.50s (0:03:48)
  Error: Process completed with exit code 1.
