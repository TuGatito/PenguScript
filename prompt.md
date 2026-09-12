Actualmente Github Actions no puede terminar los procesos para subir el artefacto de linux y mac ya que no pasan los tests.

Solo funciono en windows

Asegurate de saber si es error del test, que es antiguo, o si es un error real del compilador. Luego solucionalos para que los tests pasen y Github Actions pueda terminar satisfactoriamente.

Asegurate de no romper nada en el proceso.

El log de Linux:
Run python -m pytest tests -q -p no:cacheprovider
......................................................F................. [ 8%]
........................................................................ [ 16%]
........................................................................ [ 24%]
........................................................................ [ 33%]
........................................................................ [ 41%]
........................................................................ [ 49%]
.............................................................s..ss.....F [ 57%]
........................................................................ [ 66%]
........................................................................ [ 74%]
............................s..............................s............ [ 82%]
........s.....................s.s....................................... [ 90%]
........................................................................ [ 99%]
........ [100%]
=================================== FAILURES =================================== \***\*\_\_\_\*\*** TestArchivumTree.test_copy_tree_and_list_files_recursive \***\*\_\_\_\*\***

self = <tests.test_cli_tools.TestArchivumTree object at 0x7f6d527bb890>

        def test_copy_tree_and_list_files_recursive(self):
            import uuid
            tag = uuid.uuid4().hex[:10]
            rel_src = f"build/archivum_tree_{tag}_src"
            rel_dst = f"build/archivum_tree_{tag}_dst"
            src_dir = os.path.join(REPO, rel_src.replace("/", os.sep))
            dst_dir = os.path.join(REPO, rel_dst.replace("/", os.sep))
            shutil.rmtree(src_dir, ignore_errors=True)
            shutil.rmtree(dst_dir, ignore_errors=True)
            try:
                source = f"""\
    import std.spark
    import std.archivum

    weave main into int:
        var ok_root as bool is calling archivum.create_dir with "{rel_src}", true
        if ok_root == false:
            calling spark.println with "mkdir failed"
            return 1
        var ok_a as bool is calling archivum.write_file with "{rel_src}/a.txt", "alpha"
        if ok_a == false:
            return 1
        var ok_sub as bool is calling archivum.create_dir with "{rel_src}/sub", true
        if ok_sub == false:
            return 1
        var ok_b as bool is calling archivum.write_file with "{rel_src}/sub/b.txt", "beta"
        if ok_b == false:
            return 1
        var copied as bool is calling archivum.copy_tree with "{rel_src}", "{rel_dst}"
        if copied == false:
            calling spark.println with "copy failed"
            return 1
        var files as list of string is calling archivum.list_files_recursive with "{rel_dst}"
        if files.len == 2:
            calling spark.println with "list ok"
        var a_ok as bool is calling archivum.is_file with "{rel_dst}/a.txt"
        var b_ok as bool is calling archivum.is_file with "{rel_dst}/sub/b.txt"
        if a_ok:
            if b_ok:
                calling spark.println with "copy_tree ok"
        return 0
    """
                res = compile_run(source, tag=f"arch_{tag}")
                assert res.returncode == 0, res.stderr

>               assert "list ok" in res.stdout
>
> E AssertionError: assert 'list ok' in ''
> E + where '' = CompletedProcess(args=['/home/runner/work/PenguScript/PenguScript/build/pengu_arch_5a2d169afb_zb8vwk63/bin'], returncode=0, stdout='', stderr='').stdout

tests/test_cli_tools.py:971: AssertionError \***\*\_\_\_\*\*** TestArchivumTree.test_copy_tree_and_list_files_recursive \***\*\_\_\_\*\***

self = <tests.test_ffi_libs.TestArchivumTree object at 0x7f6d5246cb90>

        @requires_runtime
        def test_copy_tree_and_list_files_recursive(self):
            src_dir = REPO / "build" / "pengu_ffi_arch_src"
            dst_dir = REPO / "build" / "pengu_ffi_arch_dst"
            for d in (src_dir, dst_dir):
                shutil.rmtree(d, ignore_errors=True)
            try:
                demo = r"""import std.spark
    import std.archivum

    weave main into int:
        var ok_root as bool is calling archivum.create_dir with "{src}", true
        if ok_root == false:
            calling spark.println with "mkdir failed"
            return 1
        var ok_a as bool is calling archivum.write_file with "{src}/a.txt", "alpha"
        if ok_a == false:
            return 1
        var ok_sub as bool is calling archivum.create_dir with "{src}/sub", true
        if ok_sub == false:
            return 1
        var ok_b as bool is calling archivum.write_file with "{src}/sub/b.txt", "beta"
        if ok_b == false:
            return 1
        var copied as bool is calling archivum.copy_tree with "{src}", "{dst}"
        if copied == false:
            calling spark.println with "copy failed"
            return 1
        var files as list of string is calling archivum.list_files_recursive with "{dst}"
        if files.len == 2:
            calling spark.println with "list ok"
        var a_ok as bool is calling archivum.is_file with "{dst}/a.txt"
        var b_ok as bool is calling archivum.is_file with "{dst}/sub/b.txt"
        if a_ok:
            if b_ok:
                calling spark.println with "copy_tree ok"
        return 0
    """.format(src=TestArchivumTree.REL_SRC, dst=TestArchivumTree.REL_DST)
                res = compile_run(demo, tag="archivum")

>               _expect_stdout(res, "list ok", "copy_tree ok")

tests/test_ffi_libs.py:1018:

---

res = CompletedProcess(args=['/home/runner/work/PenguScript/PenguScript/build/pengu_archivum_az_sgs_b/bin'], returncode=0, stdout='', stderr='')
markers = ('list ok', 'copy_tree ok')

    def _expect_stdout(res: subprocess.CompletedProcess, *markers: str):
        for marker in markers:

>           assert marker in res.stdout, f"missing {marker!r} in output:\n{res.stdout}"
>
> E AssertionError: missing 'list ok' in output:
> E  
> E assert 'list ok' in ''
> E + where '' = CompletedProcess(args=['/home/runner/work/PenguScript/PenguScript/build/pengu_archivum_az_sgs_b/bin'], returncode=0, stdout='', stderr='').stdout

tests/test_ffi_libs.py:125: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cli_tools.py::TestArchivumTree::test_copy_tree_and_list_files_recursive - AssertionError: assert 'list ok' in ''

- where '' = CompletedProcess(args=['/home/runner/work/PenguScript/PenguScript/build/pengu_arch_5a2d169afb_zb8vwk63/bin'], returncode=0, stdout='', stderr='').stdout
  FAILED tests/test_ffi_libs.py::TestArchivumTree::test_copy_tree_and_list_files_recursive - AssertionError: missing 'list ok' in output:

assert 'list ok' in ''

- where '' = CompletedProcess(args=['/home/runner/work/PenguScript/PenguScript/build/pengu_archivum_az_sgs_b/bin'], returncode=0, stdout='', stderr='').stdout
  2 failed, 862 passed, 8 skipped in 125.68s (0:02:05)
  Error: Process completed with exit code 1.

El log de MacOS:
Run python -m pytest tests -q -p no:cacheprovider
......................................................F................. [ 8%]
........................................................................ [ 16%]
........................................................................ [ 24%]
........................................................................ [ 33%]
........................................................................ [ 41%]
........................................................................ [ 49%]
.............................................................s..ss.....F [ 57%]
........................................................................ [ 66%]
........................................................................ [ 74%]
............................s..............................s............ [ 82%]
........s.....................s.s....................................... [ 90%]
........................................................................ [ 99%]
........ [100%]
=================================== FAILURES =================================== \***\*\_\_\_\*\*** TestArchivumTree.test_copy_tree_and_list_files_recursive \***\*\_\_\_\*\***

self = <tests.test_cli_tools.TestArchivumTree object at 0x10b369f90>

        def test_copy_tree_and_list_files_recursive(self):
            import uuid
            tag = uuid.uuid4().hex[:10]
            rel_src = f"build/archivum_tree_{tag}_src"
            rel_dst = f"build/archivum_tree_{tag}_dst"
            src_dir = os.path.join(REPO, rel_src.replace("/", os.sep))
            dst_dir = os.path.join(REPO, rel_dst.replace("/", os.sep))
            shutil.rmtree(src_dir, ignore_errors=True)
            shutil.rmtree(dst_dir, ignore_errors=True)
            try:
                source = f"""\
    import std.spark
    import std.archivum

    weave main into int:
        var ok_root as bool is calling archivum.create_dir with "{rel_src}", true
        if ok_root == false:
            calling spark.println with "mkdir failed"
            return 1
        var ok_a as bool is calling archivum.write_file with "{rel_src}/a.txt", "alpha"
        if ok_a == false:
            return 1
        var ok_sub as bool is calling archivum.create_dir with "{rel_src}/sub", true
        if ok_sub == false:
            return 1
        var ok_b as bool is calling archivum.write_file with "{rel_src}/sub/b.txt", "beta"
        if ok_b == false:
            return 1
        var copied as bool is calling archivum.copy_tree with "{rel_src}", "{rel_dst}"
        if copied == false:
            calling spark.println with "copy failed"
            return 1
        var files as list of string is calling archivum.list_files_recursive with "{rel_dst}"
        if files.len == 2:
            calling spark.println with "list ok"
        var a_ok as bool is calling archivum.is_file with "{rel_dst}/a.txt"
        var b_ok as bool is calling archivum.is_file with "{rel_dst}/sub/b.txt"
        if a_ok:
            if b_ok:
                calling spark.println with "copy_tree ok"
        return 0
    """
                res = compile_run(source, tag=f"arch_{tag}")
                assert res.returncode == 0, res.stderr

>               assert "list ok" in res.stdout
>
> E AssertionError: assert 'list ok' in ''
> E + where '' = CompletedProcess(args=['/Users/runner/work/PenguScript/PenguScript/build/pengu_arch_b5dc26b42c_qg407k81/bin'], returncode=0, stdout='', stderr='').stdout

tests/test_cli_tools.py:971: AssertionError \***\*\_\_\_\*\*** TestArchivumTree.test_copy_tree_and_list_files_recursive \***\*\_\_\_\*\***

self = <tests.test_ffi_libs.TestArchivumTree object at 0x10b7a3250>

        @requires_runtime
        def test_copy_tree_and_list_files_recursive(self):
            src_dir = REPO / "build" / "pengu_ffi_arch_src"
            dst_dir = REPO / "build" / "pengu_ffi_arch_dst"
            for d in (src_dir, dst_dir):
                shutil.rmtree(d, ignore_errors=True)
            try:
                demo = r"""import std.spark
    import std.archivum

    weave main into int:
        var ok_root as bool is calling archivum.create_dir with "{src}", true
        if ok_root == false:
            calling spark.println with "mkdir failed"
            return 1
        var ok_a as bool is calling archivum.write_file with "{src}/a.txt", "alpha"
        if ok_a == false:
            return 1
        var ok_sub as bool is calling archivum.create_dir with "{src}/sub", true
        if ok_sub == false:
            return 1
        var ok_b as bool is calling archivum.write_file with "{src}/sub/b.txt", "beta"
        if ok_b == false:
            return 1
        var copied as bool is calling archivum.copy_tree with "{src}", "{dst}"
        if copied == false:
            calling spark.println with "copy failed"
            return 1
        var files as list of string is calling archivum.list_files_recursive with "{dst}"
        if files.len == 2:
            calling spark.println with "list ok"
        var a_ok as bool is calling archivum.is_file with "{dst}/a.txt"
        var b_ok as bool is calling archivum.is_file with "{dst}/sub/b.txt"
        if a_ok:
            if b_ok:
                calling spark.println with "copy_tree ok"
        return 0
    """.format(src=TestArchivumTree.REL_SRC, dst=TestArchivumTree.REL_DST)
                res = compile_run(demo, tag="archivum")

>               _expect_stdout(res, "list ok", "copy_tree ok")

tests/test_ffi_libs.py:1018:

---

res = CompletedProcess(args=['/Users/runner/work/PenguScript/PenguScript/build/pengu_archivum_qmfkl92k/bin'], returncode=0, stdout='', stderr='')
markers = ('list ok', 'copy_tree ok')

    def _expect_stdout(res: subprocess.CompletedProcess, *markers: str):
        for marker in markers:

>           assert marker in res.stdout, f"missing {marker!r} in output:\n{res.stdout}"
>
> E AssertionError: missing 'list ok' in output:
> E  
> E assert 'list ok' in ''
> E + where '' = CompletedProcess(args=['/Users/runner/work/PenguScript/PenguScript/build/pengu_archivum_qmfkl92k/bin'], returncode=0, stdout='', stderr='').stdout

tests/test_ffi_libs.py:125: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cli_tools.py::TestArchivumTree::test_copy_tree_and_list_files_recursive - AssertionError: assert 'list ok' in ''

- where '' = CompletedProcess(args=['/Users/runner/work/PenguScript/PenguScript/build/pengu_arch_b5dc26b42c_qg407k81/bin'], returncode=0, stdout='', stderr='').stdout
  FAILED tests/test_ffi_libs.py::TestArchivumTree::test_copy_tree_and_list_files_recursive - AssertionError: missing 'list ok' in output:

assert 'list ok' in ''

- where '' = CompletedProcess(args=['/Users/runner/work/PenguScript/PenguScript/build/pengu_archivum_qmfkl92k/bin'], returncode=0, stdout='', stderr='').stdout
  2 failed, 862 passed, 8 skipped in 80.36s (0:01:20)
  Error: Process completed with exit code 1.
