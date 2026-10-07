"""Roadmap Phase 2 / item 2.2.g — PENGU_BOUNDS_CHECK is independent of
PENGU_FRAME_TRACE.

`pengu_assert_bounds` used to be guarded by PENGU_FRAME_TRACE, so disabling the
crash-handler frame trace silently disabled bounds checking (and vice versa).
Both macros must compile in every combination.
"""

import os
import re
import subprocess
import sys

import pytest

from tests.conftest import HAVE_RUNTIME, REPO, have_tool

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


# ---------------------------------------------------------------------------
# Phase 10 / F10-N3 — the *generated* bundle must honour the same macro
# ---------------------------------------------------------------------------

_PROGRAM = "weave main into int:\n    var total as int is 40\n    return total\n"
_MANIFEST = (
    '[project]\nname = "notrace"\nentry = "src/main.pengu"\n\n'
    '[build]\nprofile = "release"\n'
)
_ARTIFACT = re.compile(r"->\s*(\S+)\s*$")


def _sync_effective_header() -> None:
    """Mirrors `build_runtime.build_pengu_runtime`, which copies the header.

    `pengu_paths.runtime_include_dirs()` lists `build/include` **before** the
    repository root, so a stale `build/include/pengu_runtime.h` silently shadows
    the header under test. Without this, reverting the F10-N3 fix in the root
    header would still pass the test below on any machine with a stale build
    directory — a gate that cannot fail is not a gate.
    """
    from tests.conftest import BUILD_INCLUDE

    copy = BUILD_INCLUDE / "pengu_runtime.h"
    source = REPO / "pengu_runtime.h"
    if copy.is_file() and copy.read_bytes() != source.read_bytes():
        copy.write_bytes(source.read_bytes())


@pytest.mark.skipif(not CC, reason="no C compiler available")
@pytest.mark.skipif(not HAVE_RUNTIME, reason="libpengu_runtime.a not built")
def test_the_generated_bundle_compiles_with_the_frame_trace_off(tmp_path):
    """`-DPENGU_FRAME_TRACE=0` must compile the bundle the codegen actually emits.

    F10-N3 (measured): `pengu_install_crash_handler` was defined only inside the
    `#if PENGU_FRAME_TRACE` branch of `pengu_runtime.h`, while
    `pengu_codegen`'s entry-point wrapper calls it unconditionally — so the knob
    `BENCHMARKS.md` documents for its "1.8x vs C" measurement failed with

        error: implicit declaration of function 'pengu_install_crash_handler'

    The snippet test above cannot see it: it never calls the symbol the wrapper
    emits (`pengu_assert_bounds` is outside the guard). The conftest `compile_run`
    helper cannot see it either, because it appends
    `-Wno-error=implicit-function-declaration`. So this test drives the real CLI
    the way a user would, and runs the artifact it produces.
    """
    from tests.conftest import HAVE_CC

    assert HAVE_CC
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.pengu").write_text(_PROGRAM, encoding="utf-8")
    (proj / "pengu.toml").write_text(_MANIFEST, encoding="utf-8")

    env = dict(os.environ, PENGU_CFLAGS="-DPENGU_FRAME_TRACE=0", NO_COLOR="1")
    _sync_effective_header()
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build",
         "--profile", "release"],
        cwd=str(proj), capture_output=True, text=True, timeout=600, env=env,
    )
    assert res.returncode == 0, (
        "the documented `-DPENGU_FRAME_TRACE=0` build failed:\n"
        f"{res.stdout}\n{res.stderr}"
    )

    artifact = None
    for line in reversed(res.stdout.splitlines()):
        found = _ARTIFACT.search(line)
        if found:
            artifact = found.group(1)
            break
    assert artifact, f"no artifact in the build output:\n{res.stdout}"
    run = subprocess.run([artifact], capture_output=True, text=True, timeout=120)
    assert run.returncode == 40, (
        "the frame-trace-off binary did not run the program's own return value "
        f"(got {run.returncode})"
    )

