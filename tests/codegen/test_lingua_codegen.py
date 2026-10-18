"""Generated-C checks for ``std.lingua``.

Two properties belong here rather than in the behaviour tests:

* the bundle compiles under ``-Wall -Wextra -Werror`` with every available C
  compiler, including the header-only ``utf8.h`` body;
* a loop that decodes and re-encodes 1 000 strings leaves no allocation behind.
  The second check is run under AddressSanitizer's leak detector, which is the
  CI substitute for valgrind on this project (``docs/FUZZING.md``).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SOURCE = r'''
import std.spark
import std.lingua

weave main into int:
    var iter as int is 0
    while iter < 1000:
        var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with "año😀"
        if not decoded.is_ok:
            calling spark.panic with "decode failed"
        var cps as list of Codepoint is decoded.value
        var encoded as result of string to LinguaError is calling lingua.encode with cps
        if not encoded.is_ok:
            calling spark.panic with "encode failed"
        var text as string is encoded.value
        var count as int is calling lingua.codepoint_count with text
        if count != 4:
            calling spark.panic with "count mismatch"
        if (calling lingua.utf16_length with text) != 5:
            calling spark.panic with "utf16 mismatch"
        banish encoded
        banish decoded
        set iter is iter + 1
    calling spark.println with "DONE"
    return 0
'''


def _available_compilers() -> list[str]:
    return [cc for cc in ("gcc", "clang") if shutil.which(cc)]


def test_bundle_compiles_cleanly_with_every_compiler(pengu_cli, tmp_path):
    src = tmp_path / "lingua_codegen.pengu"
    src.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "bundle.c"
    res = pengu_cli("build", "--entry", str(src), "--output", str(bundle))
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    text = bundle.read_text(encoding="utf-8")

    assert '#include "utf8.h"' in text
    assert "lingua__lingua_scan" in text
    # The bridge uses int64_t for bounds checks, never __auto_type: TinyCC does
    # not implement the latter (pengu_tcc.py treats TCC as a supported compiler).
    assert "__auto_type" not in text

    compilers = _available_compilers()
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        obj = tmp_path / f"bundle_{cc}.o"
        res = subprocess.run(
            [cc, "-c", str(bundle), "-o", str(obj), "-O0", "-std=c11",
             "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
             "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
             "-I", str(ROOT / "std_c")],
            capture_output=True, text=True, timeout=600,
        )
        assert res.returncode == 0, f"{cc} rejected the bundle:\n{res.stdout}\n{res.stderr}"


def test_no_leaks_under_address_sanitizer(pengu_cli, tmp_path):
    if sys.platform != "linux":
        pytest.skip("ASan leak detection runs on the Linux CI job")
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no C compiler available")
    if not (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file():
        pytest.skip("libpengu_runtime.a not built")

    src = tmp_path / "lingua_asan.pengu"
    src.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "bundle.c"
    res = pengu_cli("build", "--entry", str(src), "--output", str(bundle))
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"

    exe = tmp_path / "asan_app"
    link = subprocess.run(
        [cc, str(bundle), "-o", str(exe), "-O0", "-g", "-std=c11",
         "-fsanitize=address", "-fno-omit-frame-pointer",
         "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
         "-I", str(ROOT / "std_c"),
         "-L", str(ROOT / "build" / "lib"),
         "-lpengu_runtime", "-pthread", "-lm", "-ldl"],
        capture_output=True, text=True, timeout=600,
    )
    assert link.returncode == 0, f"ASan link failed:\n{link.stdout}\n{link.stderr}"

    env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=1"}
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300, env=env)
    combined = run.stdout + run.stderr
    assert "AddressSanitizer" not in combined, combined
    assert "LeakSanitizer" not in combined, combined
    assert run.returncode == 0, combined
    assert "DONE" in run.stdout
