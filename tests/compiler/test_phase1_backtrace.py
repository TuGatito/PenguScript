#!/usr/bin/env python3
"""Tests for Phase 1 Task 1: Minimal frame backtrace & crash handler."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    HAVE_CC,
    HAVE_RUNTIME,
    REPO,
    gen_bundle,
    have_tool,
    is_windows,
    requires_cc,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)
from pengu_project import PenguBuilder, ProjectConfig


def test_frame_push_pop_emitted_in_bundle():
    """Bundle must emit pengu_frame_push and pengu_frame_pop for weaves."""
    source = """
weave f into int:
    return 1

weave main into int:
    return calling f
"""
    c_code = gen_bundle(source, filename="main.pengu")
    assert re.search(r'pengu_frame_push\("(?:pengu_)?f', c_code) is not None
    assert re.search(r'pengu_frame_push\("pengu_main', c_code) is not None
    assert "pengu_frame_pop();" in c_code


def test_frame_trace_install_only_once():
    """Crash handler declaration must appear exactly once in the generated C/header."""
    source = """
weave main into int:
    return 0
"""
    c_code = gen_bundle(source, filename="main.pengu")
    assert c_code.count('signal(SIGSEGV, pengu_unix_signal_handler)') <= 1
    # bundle includes pengu_runtime.h where pengu_unix_signal_handler is defined once
    runtime_content = (REPO / "pengu_runtime.h").read_text(encoding="utf-8")
    rt_matches = re.findall(r"void\s+pengu_unix_signal_handler", runtime_content)
    assert len(rt_matches) == 1


def test_or_return_pops_frame():
    """Early return on unwrapping must pop the current frame."""
    source = """
weave g with u as maybe int into int:
    let x is u or return 0
    return x

weave main into int:
    var none_m as maybe int is maybe none
    var ignored as int is calling g with none_m
    return 0
"""
    c = gen_bundle(source, filename="main.pengu")
    assert re.search(r"pengu_frame_pop\(\);\s*return\s*\(0\)", c) is not None


def test_lambda_emits_frame_push_with_file_path():
    """Lambdas must push a frame with non-empty source file path and line number."""
    source = """
weave main into int:
    var f as ref to weave with x as int into int is lambda x as int into x + 1
    return 0
"""
    c = gen_bundle(source, filename="src/main.pengu")
    assert 'pengu_frame_push("_pengu_lambda_1", "", ' not in c
    assert re.search(r'pengu_frame_push\("_pengu_lambda_1",\s*"[^"]*main\.pengu",\s*\d+\)', c) is not None


@requires_cc
@requires_runtime
def test_null_deref_dumps_frame_trace():
    """Null pointer dereference must crash and dump frame trace to stderr."""
    if is_windows():
        pytest.skip("Signal / crash handler behavior on Windows null deref differs across CI runners")

    source = """
weave main into int:
    var p as ref to int is null
    var x as int is essence of p
    return x
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_crash_test_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

        cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
        exe = d / ("bin.exe" if is_windows() else "bin")
        cmd = [
            cc,
            str(bundle_path),
            f"-I{REPO}",
            f"-I{BUILD_DIR}",
            f"-I{BUILD_INCLUDE}",
            f"-L{BUILD_LIB}",
            "-Wno-error=implicit-function-declaration",
            "-Wno-error=implicit-int",
            "-Wno-error=int-conversion",
        ]
        cmd += runtime_link_flags()
        cmd += runtime_tail_flags()
        cmd += ["-o", str(exe)]

        res = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=120)
        assert res.returncode == 0, f"Compilation failed: {res.stderr}"

        run_res = subprocess.run([str(exe)], cwd=str(REPO), capture_output=True, text=True, timeout=30)
        assert run_res.returncode != 0
        err = run_res.stderr
        assert "at pengu_main" in err or "pengu_main" in err
        assert "main.pengu" in err
    finally:
        shutil.rmtree(d, ignore_errors=True)
