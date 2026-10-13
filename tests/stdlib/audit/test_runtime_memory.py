"""``tests/stdlib/audit`` — runtime memory-safety regression probes.

Unlike the sibling stdlib suites, these compile the *runtime header* directly
(no PenguScript program) so a primitive that the code generator does not reach
today is still pinned: the specialized ``pengu_map_*_string_int`` entry points
were the two heap-use-after-frees the 2.0.1 audit fixed, and no PenguScript
program exercises them.

The probe is compiled with ASan + UBSan when the compiler supports them; a
memory error aborts the process, and the test fails on the non-zero exit code.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROBE = os.path.join(os.path.dirname(__file__), "runtime_map_probe.c")

pytestmark = pytest.mark.slow

_SANITIZE = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]


def _cc() -> str | None:
    for cand in ("cc", "gcc", "clang"):
        path = shutil.which(cand)
        if path:
            return path
    return None


def _have_runtime() -> bool:
    return os.path.isfile(os.path.join(ROOT, "build", "lib", "libpengu_runtime.a"))


def _supports_sanitizers(cc: str) -> bool:
    try:
        probe = subprocess.run(
            [cc, "-fsanitize=address,undefined", "-x", "c", "-", "-o", os.devnull],
            input="int main(void){return 0;}",
            capture_output=True, text=True, timeout=120,
        )
        return probe.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.fixture(scope="module")
def built_probe(tmp_path_factory):
    cc = _cc()
    if not cc:
        pytest.skip("no C compiler available")
    if not _have_runtime():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")
    flags = _SANITIZE if _supports_sanitizers(cc) else []
    out = tmp_path_factory.mktemp("runtime_probe") / "runtime_map_probe"
    cmd = [
        cc, "-std=c11", "-g", "-O1", *flags,
        "-I", ROOT, "-I", os.path.join(ROOT, "build", "include"),
        PROBE, "-o", str(out),
        "-L", os.path.join(ROOT, "build", "lib"),
        "-lpengu_runtime", "-lpthread", "-lm",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, f"probe build failed:\n{res.stdout}\n{res.stderr}"
    return str(out)


def test_runtime_map_string_int_ownership(built_probe):
    """Rehash and remove must never free the caller's ``PenguString`` payload.

    Reproduces the two pre-2.0.1 use-after-frees: ASan aborts with
    ``heap-use-after-free`` in ``pengu_hash_bytes`` (rehash) or a double free in
    ``pengu_banish_string`` (remove).
    """
    env = dict(os.environ)
    env["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1:abort_on_error=1"
    env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
    res = subprocess.run([built_probe], capture_output=True, text=True,
                         timeout=300, env=env)
    assert res.returncode == 0, (
        f"runtime probe failed ({res.returncode}):\n{res.stdout}\n{res.stderr}"
    )
    assert "runtime_map_probe: ok" in res.stdout, res.stdout
