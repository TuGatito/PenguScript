Tenemos problemas. Debido a los cambios que implementaste anteriormente el proyecto no compila en GitHub Actions en ninguna plataforma (Linux, MacOS y Windows). 

Parece ser un problema con los tests. Investiga si el problema es que hay tests desactualizados al estado actual del lenguaje y compilador o si son errores reales.    

Asegurate que todo este bien y correcto para que compilen bien las 3 plataformas en Github Actions. No olvides actualizar el changelog.md

Error de MacOs:

Run python -m pytest tests -q -p no:cacheprovider
.................................F...................................... [  6%]
........................................................................ [ 13%]
........................................................................ [ 19%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 39%]
.............................................................s..ss...... [ 46%]
........................................................................ [ 52%]
........................................................................ [ 59%]
......................................s..............................s.. [ 65%]
..................s.....................s.s............................. [ 72%]
........................................................................ [ 78%]
........................................................................ [ 85%]
........................................................................ [ 92%]
.........................s.............................................. [ 98%]
..............                                                           [100%]
=================================== FAILURES ===================================
_________ TestBuildCommands.test_no_hardcoded_raylib_with_empty_links __________

self = <tests.test_cli_tools.TestBuildCommands object at 0x10bcb0b00>
proj_dir = '/Users/runner/work/PenguScript/PenguScript/build/cli_proj_1l1_5ja7'

    def test_no_hardcoded_raylib_with_empty_links(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig
    
        cfg = ProjectConfig(name="headless", output=OutputType.EXE,
                            output_name="headless_app", links=[],
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "bundle.c", "headless_app.exe")
        cmd_str = " ".join(cmds[0])
        assert "-lraylib" not in cmd_str
>       assert "-l" not in cmd_str
E       AssertionError: assert '-l' not in 'gcc bundle....ead -lm -ldl'
E         
E         '-l' is contained here:
E            -DSTATIC -lpengu_stb -ltomlc17 -lz -lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz -L/opt/homebrew/lib -L/opt/homebrew/opt/libxml2/lib -L/opt/homebrew/Cellar/libmicrohttpd/1.0.10/lib -L/opt/homebrew/Cellar/mbedtls/4.2.0/lib -lmbedtls -lcyaml -lxlsxio_write -lpengu_raymath -lzip -lpcre2-8 -lmbedcrypto -luv -lyaml -lexpat -lxlsxio_read -lsqlite3 -framework CoreFoundation -pthread -lm -ldl
E         ?           ++

tests/test_cli_tools.py:510: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cli_tools.py::TestBuildCommands::test_no_hardcoded_raylib_with_empty_links - AssertionError: assert '-l' not in 'gcc bundle....ead -lm -ldl'
  
  '-l' is contained here:
     -DSTATIC -lpengu_stb -ltomlc17 -lz -lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz -L/opt/homebrew/lib -L/opt/homebrew/opt/libxml2/lib -L/opt/homebrew/Cellar/libmicrohttpd/1.0.10/lib -L/opt/homebrew/Cellar/mbedtls/4.2.0/lib -lmbedtls -lcyaml -lxlsxio_write -lpengu_raymath -lzip -lpcre2-8 -lmbedcrypto -luv -lyaml -lexpat -lxlsxio_read -lsqlite3 -framework CoreFoundation -pthread -lm -ldl
  ?           ++
1 failed, 1084 passed, 9 skipped in 153.81s (0:02:33)
Error: Process completed with exit code 1.

Error de Linux:

Run python -m pytest tests -q -p no:cacheprovider
.................................F...................................... [  6%]
........................................................................ [ 13%]
........................................................................ [ 19%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 39%]
.............................................................s..ss...... [ 46%]
........................................................................ [ 52%]
........................................................................ [ 59%]
......................................s..............................s.. [ 65%]
..................s.....................s.s............................. [ 72%]
........................................................................ [ 78%]
........................................................................ [ 85%]
........................................................................ [ 92%]
.........................s.............................................. [ 98%]
..............                                                           [100%]
=================================== FAILURES ===================================
_________ TestBuildCommands.test_no_hardcoded_raylib_with_empty_links __________

self = <tests.test_cli_tools.TestBuildCommands object at 0x7f9ebb73b490>
proj_dir = '/home/runner/work/PenguScript/PenguScript/build/cli_proj_nj88r8wu'

    def test_no_hardcoded_raylib_with_empty_links(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig
    
        cfg = ProjectConfig(name="headless", output=OutputType.EXE,
                            output_name="headless_app", links=[],
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "bundle.c", "headless_app.exe")
        cmd_str = " ".join(cmds[0])
        assert "-lraylib" not in cmd_str
>       assert "-l" not in cmd_str
E       AssertionError: assert '-l' not in 'gcc bundle....,--end-group'
E         
E         '-l' is contained here:
E         ?           ^^^^^^^^
E           ude/x86_64-linux-gnu -I/usr/include/p11-kit-1 -I/usr/local/include -I/home/runner/work/PenguScript/PenguScript/build/include -I/home/runner/work/PenguScript/PenguScript -L/home/runner/work/PenguScript/PenguScript/build/lib -DSTATIC -Wl,--start-group -lpengu_raymath -lyaml -lz -ltomlc17 -lxlsxio_write -lzip -lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz -L/usr/local/lib -lmbedtls -lmbedcrypto -lxlsxio_read -lcyaml -lsqlite3 -luv -lpengu_stb -lpcre2-8 -lwebui -lexpat -lrt -lcrypto -lssl -pthread -lm -ldl -Wl,--end-group
E         ?           ^^^^^^^^^^

tests/test_cli_tools.py:510: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cli_tools.py::TestBuildCommands::test_no_hardcoded_raylib_with_empty_links - AssertionError: assert '-l' not in 'gcc bundle....,--end-group'
  
  '-l' is contained here:
  ?           ^^^^^^^^
    ude/x86_64-linux-gnu -I/usr/include/p11-kit-1 -I/usr/local/include -I/home/runner/work/PenguScript/PenguScript/build/include -I/home/runner/work/PenguScript/PenguScript -L/home/runner/work/PenguScript/PenguScript/build/lib -DSTATIC -Wl,--start-group -lpengu_raymath -lyaml -lz -ltomlc17 -lxlsxio_write -lzip -lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz -L/usr/local/lib -lmbedtls -lmbedcrypto -lxlsxio_read -lcyaml -lsqlite3 -luv -lpengu_stb -lpcre2-8 -lwebui -lexpat -lrt -lcrypto -lssl -pthread -lm -ldl -Wl,--end-group
  ?           ^^^^^^^^^^
1 failed, 1084 passed, 9 skipped in 146.64s (0:02:26)
Error: Process completed with exit code 1.

Error de Windows:

Run python -m pytest tests -q -p no:cacheprovider
.................................F...................................... [  6%]
........................................................................ [ 13%]
........................................................................ [ 19%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 39%]
........................................................................ [ 46%]
........................................................................ [ 52%]
........................................................................ [ 59%]
......................................s................................. [ 65%]
........................................................................ [ 72%]
s....................................................................... [ 78%]
........................................................................ [ 85%]
........................................................................ [ 92%]
.........................s.............................................. [ 98%]
..............                                                           [100%]
================================== FAILURES ===================================
_________ TestBuildCommands.test_no_hardcoded_raylib_with_empty_links _________

self = <tests.test_cli_tools.TestBuildCommands object at 0x0000024D52892060>
proj_dir = 'D:\\a\\PenguScript\\PenguScript\\build\\cli_proj_xuqorama'

    def test_no_hardcoded_raylib_with_empty_links(self, proj_dir):
        from pengu_project import PenguBuilder, OutputType, ProjectConfig
    
        cfg = ProjectConfig(name="headless", output=OutputType.EXE,
                            output_name="headless_app", links=[],
                            base_dir=proj_dir)
        cmds = PenguBuilder(cfg).build_compile_commands(
            "bundle.c", "headless_app.exe")
        cmd_str = " ".join(cmds[0])
>       assert "-lraylib" not in cmd_str
E       AssertionError: assert '-lraylib' not in 'gcc bundle....,--end-group'
E         
E         '-lraylib' is contained here:
E           pengu_stb -lraylib -lsqlite3 -ltomlc17 -lwebui -lxlsxio_read -lxlsxio_write -lxml2 -lyaml -lz -lzip -Wl,--end-group
E         ?           ++++++++

tests\test_cli_tools.py:509: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_cli_tools.py::TestBuildCommands::test_no_hardcoded_raylib_with_empty_links - AssertionError: assert '-lraylib' not in 'gcc bundle....,--end-group'
  
  '-lraylib' is contained here:
    pengu_stb -lraylib -lsqlite3 -ltomlc17 -lwebui -lxlsxio_read -lxlsxio_write -lxml2 -lyaml -lz -lzip -Wl,--end-group
  ?           ++++++++
1 failed, 1090 passed, 3 skipped in 197.66s (0:03:17)
Error: Process completed with exit code 1.
