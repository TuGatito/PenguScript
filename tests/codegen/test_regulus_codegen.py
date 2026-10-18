"""Generated-C checks for ``std.regulus``.

The regex engine is a separate archive (``libre.a``). This test proves the
bundle that calls it is warning-free and that compiling/banishing 1 000
patterns leaves neither the pattern copy nor the compiled block behind.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SOURCE = r'''
import std.spark
import std.regulus

weave main into int:
    var iter as int is 0
    while iter < 1000:
        var compiled as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
        if not compiled.is_ok:
            calling spark.panic with "compile failed"
        var rx as Regex is compiled.value
        if not (calling rx.is_match with "abc123"):
            calling spark.panic with "match failed"
        var m as maybe Match is calling rx.match with "abc123def456"
        if not (m is present):
            calling spark.panic with "expected a match"
        if m.value.start != 3:
            calling spark.panic with "wrong start"
        banish m
        var all as list of Match is calling rx.matches with "a1b22c333"
        if all.len != 3:
            calling spark.panic with "wrong match count"
        banish all
        var replaced as string is calling rx.replace_all with "a1b22", "N"
        banish replaced
        banish compiled
        set iter is iter + 1
    calling spark.println with "DONE"
    return 0
'''


def _available_compilers() -> list[str]:
    return [cc for cc in ("gcc", "clang") if shutil.which(cc)]


def test_bundle_compiles_cleanly_with_every_compiler(pengu_cli, tmp_path):
    src = tmp_path / "regulus_codegen.pengu"
    src.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "bundle.c"
    res = pengu_cli("build", "--entry", str(src), "--output", str(bundle))
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    text = bundle.read_text(encoding="utf-8")

    assert '#include "re.h"' in text
    assert '#include "utf8.h"' not in text
    assert "regulus__regulus_compile" in text
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
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("no C compiler available")
    if not (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file():
        pytest.skip("libpengu_runtime.a not built")
    if not (ROOT / "build" / "lib" / "libre.a").is_file():
        pytest.skip("libre.a not built (run build_runtime.py)")

    src = tmp_path / "regulus_asan.pengu"
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
         "-Wl,--start-group", "-lpengu_runtime", "-lre", "-pthread", "-lm", "-ldl",
         "-Wl,--end-group"],
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
