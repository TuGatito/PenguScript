"""ABI v2 layout gate (roadmap Phase 2, items 2.2.a / 2.2.b).

Compiles and runs ``tests/abi/test_abi_layout.c`` against the shipped
``pengu_runtime.h`` and asserts ``sizeof``/``offsetof`` for every runtime struct
plus ``PENGU_ABI_VERSION == 1``.
"""

import shutil
import subprocess
import sys

import pytest

from tests.conftest import REPO, have_tool


def _cc() -> str:
    for cand in ("cc", "gcc", "clang"):
        if have_tool(cand):
            return cand
    return ""


@pytest.mark.skipif(not _cc(), reason="no C compiler available")
def test_runtime_abi_layout(tmp_path):
    cc = _cc()
    src = REPO / "tests" / "abi" / "test_abi_layout.c"
    assert src.is_file()

    exe = tmp_path / "abi_check.exe" if sys.platform == "win32" else tmp_path / "abi_check"
    comp = subprocess.run(
        [cc, "-I", str(REPO), str(src), "-o", str(exe)],
        capture_output=True, text=True, timeout=120,
    )
    assert comp.returncode == 0, f"ABI test did not compile:\n{comp.stderr}"

    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"ABI layout changed:\n{run.stderr}\n{run.stdout}"
    assert "ABI v2 OK" in run.stdout or "ABI v2 SKIP" in run.stdout
