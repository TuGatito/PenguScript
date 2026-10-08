import os
import subprocess
from pathlib import Path
import pytest

from pengu_bind import generate_bind_file
from pengu_project import PenguBuilder, ProjectConfig
from tests.conftest import (
    REPO, BUILD_DIR, BUILD_LIB, BUILD_INCLUDE,
    requires_runtime, have_lib, have_tool,
    check_ok, is_windows, runtime_link_flags, runtime_tail_flags
)


def test_companion_typedef_alias(tmp_path):
    # Header A includes B; B defines uLong; A references uLong in a function signature
    header_b = tmp_path / "b.h"
    header_b.write_text("typedef unsigned long uLong;\ntypedef struct UnusedStruct { int a; } UnusedStruct;\n", encoding="utf-8")

    header_a = tmp_path / "a.h"
    header_a.write_text('#include "b.h"\nuLong foo(uLong x);\n', encoding="utf-8")

    out_file = tmp_path / "a.d.pengu"
    generate_bind_file(str(header_a), output=str(out_file), include_paths=[str(tmp_path)])

    content = out_file.read_text(encoding="utf-8")
    assert "alias uLong as u64" in content
    # Should not include unused types from companion header
    assert "UnusedStruct" not in content
    check_ok(content)


def test_chained_companion_typedef(tmp_path):
    # Typedef chain in companion: MyInt -> int, MyInt2 -> MyInt
    header_b = tmp_path / "b.h"
    header_b.write_text("typedef int MyInt;\ntypedef MyInt MyInt2;\n", encoding="utf-8")

    header_a = tmp_path / "a.h"
    header_a.write_text('#include "b.h"\nMyInt2 calculate(MyInt2 a);\n', encoding="utf-8")

    out_file = tmp_path / "a.d.pengu"
    generate_bind_file(str(header_a), output=str(out_file), include_paths=[str(tmp_path)])

    content = out_file.read_text(encoding="utf-8")
    assert "alias MyInt2 as int" in content
    check_ok(content)


def test_companion_struct_typedef_to_opaque(tmp_path):
    # Typedef to struct in companion header -> fallback to opaque
    header_b = tmp_path / "b.h"
    header_b.write_text("struct InternalState;\ntypedef struct InternalState* StatePtr;\n", encoding="utf-8")

    header_a = tmp_path / "a.h"
    header_a.write_text('#include "b.h"\nvoid do_work(StatePtr state);\n', encoding="utf-8")

    out_file = tmp_path / "a.d.pengu"
    generate_bind_file(str(header_a), output=str(out_file), include_paths=[str(tmp_path)])

    content = out_file.read_text(encoding="utf-8")
    assert (
        "alias StatePtr as ref to opaque" in content
        or "alias StatePtr as opaque" in content
        or "alias InternalState as opaque" in content
    )
    check_ok(content)


@requires_runtime
def test_zlib_crc32_end_to_end(tmp_path):
    zlib_h = REPO / "extern" / "zlib-1.3.2" / "zlib.h"
    if not zlib_h.is_file():
        pytest.skip("zlib-1.3.2/zlib.h not found")
    if not have_lib("z"):
        pytest.skip("libz.a not built")

    out_binding = tmp_path / "zlib.d.pengu"
    generate_bind_file(
        str(zlib_h),
        output=str(out_binding),
        defines=["Z_SOLO"],
        include_paths=[str(zlib_h.parent)]
    )

    binding_text = out_binding.read_text(encoding="utf-8")
    assert "alias uLong as" in binding_text
    check_ok(binding_text)

    # Write a test pengu program that imports this generated binding
    test_src = """import zlib

weave main into int:
    var data as string is "hello"
    var crc as zlib.uLong is calling zlib.crc32 with 0, (bytes of data), 5
    calling print with "crc: {crc}"
    return 0
"""
    (tmp_path / "main.pengu").write_text(test_src, encoding="utf-8")

    cfg = ProjectConfig(entry=str(tmp_path / "main.pengu"), base_dir=str(tmp_path), output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file=str(tmp_path / "bundle.c"))

    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    exe = tmp_path / ("bin.exe" if is_windows() else "bin")
    cmd = [
        cc, str(bundle_path),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=int-conversion"
    ]
    cmd += runtime_link_flags()
    cmd += ["-lz"]
    cmd += runtime_tail_flags()
    cmd += ["-o", str(exe)]

    res = subprocess.run(cmd, cwd=str(tmp_path), capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"

    run_res = subprocess.run([str(exe)], cwd=str(tmp_path), capture_output=True, text=True, timeout=120)
    assert run_res.returncode == 0, f"Execution failed ({run_res.returncode}):\n{run_res.stderr}\n{run_res.stdout}"
    assert "crc:" in run_res.stdout
