"""Leak checks for the four 2.9.0 fundamental modules.

Valgrind is not part of every developer box, so the test uses GCC's
AddressSanitizer/LeakSanitizer: build the real bundle with ``pengu build``,
compile it with ``-fsanitize=address`` and run it with leak detection on.  A
missing ``gcc`` or an ASan-less toolchain skips instead of failing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[3]

_SOURCE = """
import std.spark
import std.builder
import std.arena
import std.sourcemap
import std.bitset

rune Node:
    value as int
    next as ref to Node

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "hello"
    calling sb.append_int with -42
    var msg as string is calling sb.finish
    defer banish msg

    var a as Arena is calling Arena.new
    defer banish a
    defer calling a.free
    var n as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set n->value is 7
    var raw as ref to byte is calling a.alloc_str with msg
    var cstr as ref to frozen char is calling a.alloc_cstr with msg
    calling a.reset
    calling a.free

    var sm as SourceMap is calling SourceMap.from_source with msg
    defer banish sm
    var p as Position is calling sm.position_at with 0
    var line as string is calling sm.line_text with 1
    defer banish line

    var bs as BitSet is calling BitSet.new with 65
    defer banish bs
    calling bs.set with 0
    var bits as list of int is calling bs.iter_set
    defer banish bits
    var first as maybe int is calling bs.find_first_set
    banish first
    calling spark.println with "OK"
    return 0
"""


def test_fundamentals_run_without_leaks(tmp_path):
    gcc = shutil.which("gcc")
    if not gcc:
        pytest.skip("gcc is required for the ASan leak check")
    runtime = ROOT / "build" / "lib" / "libpengu_runtime.a"
    include = ROOT / "build" / "include"
    if not runtime.is_file():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    source = tmp_path / "leaks.pengu"
    source.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "leaks.c"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    build = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "build",
         "--entry", str(source), "--output", str(bundle), "--cc", "gcc"],
        capture_output=True, text=True, timeout=240, cwd=str(tmp_path), env=env,
    )
    assert build.returncode == 0, f"{build.stdout}\n{build.stderr}"

    exe = tmp_path / "leaks_asan"
    compile_cmd = [
        gcc, "-std=c11", "-g", "-O0", "-fsanitize=address",
        "-I", str(include), "-I", str(ROOT), str(bundle), "-o", str(exe),
        "-L", str(ROOT / "build" / "lib"),
        "-Wl,--start-group", "-lpengu_runtime", "-pthread", "-lm", "-ldl",
        "-Wl,--end-group",
    ]
    compiled = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=240)
    if compiled.returncode != 0:
        pytest.skip(f"ASan is not usable with this toolchain:\n{compiled.stderr}")

    run = subprocess.run(
        [str(exe)], capture_output=True, text=True, timeout=120,
        env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1"},
    )
    assert run.returncode == 0, f"{run.stdout}\n{run.stderr}"
    assert "LeakSanitizer" not in run.stderr, run.stderr
    assert "ERROR: AddressSanitizer" not in run.stderr, run.stderr
    assert "OK" in run.stdout, run.stdout
