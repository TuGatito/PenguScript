"""Roadmap Phase 2 / item 2.2.g — PENGU_BOUNDS_CHECK is independent of
PENGU_FRAME_TRACE.

`pengu_assert_bounds` used to be guarded by PENGU_FRAME_TRACE, so disabling the
crash-handler frame trace silently disabled bounds checking (and vice versa).
Both macros must compile in every combination.
"""

import subprocess

import pytest

from tests.conftest import REPO, have_tool

CC = next((c for c in ("cc", "gcc", "clang") if have_tool(c)), "")

_SRC = '#include "pengu_runtime.h"\nint main(void){ pengu_assert_bounds(0, 1, "x"); return 0; }\n'


@pytest.mark.skipif(not CC, reason="no C compiler available")
@pytest.mark.parametrize("bounds,trace", [(1, 1), (1, 0), (0, 1), (0, 0)])
def test_bounds_and_frame_trace_are_independent(tmp_path, bounds, trace):
    src = tmp_path / "probe.c"
    src.write_text(_SRC, encoding="utf-8")
    exe = tmp_path / "probe"
    cmd = [
        CC, "-I", str(REPO),
        f"-DPENGU_BOUNDS_CHECK={bounds}",
        f"-DPENGU_FRAME_TRACE={trace}",
        str(src), "-o", str(exe),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, (
        f"PENGU_BOUNDS_CHECK={bounds}/PENGU_FRAME_TRACE={trace} failed to compile:\n{res.stderr}"
    )
