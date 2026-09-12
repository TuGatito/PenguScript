#!/usr/bin/env python3
"""Tests for Phase 1 Task 2: Opt-in bounds checking and debug profile."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
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


def test_bounds_check_emitted_in_debug():
    """Debug profile must emit pengu_assert_bounds."""
    source = """
weave main into int:
    var xs as array of int with size 3 is [1, 2, 3]
    var y as int is xs at 0
    return y
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_bounds_dbg_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
        bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
        c_code = Path(bundle_path).read_text(encoding="utf-8")
        assert "pengu_assert_bounds(" in c_code
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_no_bounds_check_in_release():
    """Release profile must NOT emit pengu_assert_bounds."""
    source = """
weave main into int:
    var xs as array of int with size 3 is [1, 2, 3]
    var y as int is xs at 0
    return y
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_bounds_rel_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="release", output="c")
        bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
        c_code = Path(bundle_path).read_text(encoding="utf-8")
        assert "pengu_assert_bounds(" not in c_code
    finally:
        shutil.rmtree(d, ignore_errors=True)


@requires_cc
@requires_runtime
def test_out_of_bounds_panics():
    """Out-of-bounds access under debug profile must panic with non-zero exit and message."""
    source = """
weave main into int:
    var xs as array of int with size 3 is [1, 2, 3]
    calling print with ((xs at 5) to string)
    return 0
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_oob_test_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
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
        assert "Index out of bounds" in err
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_when_debug_conditional():
    """`when debug:` emits block only under debug profile, stripped under release."""
    source = """
weave main into int:
    when debug:
        calling print with "in_debug\\n"
    return 0
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_wdbg_test_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")

        # Debug profile
        cfg_dbg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
        bundle_dbg, _ = PenguBuilder(cfg_dbg).bundle(output_file=str(d / "bundle_dbg.c"))
        c_dbg = Path(bundle_dbg).read_text(encoding="utf-8")
        assert "in_debug" in c_dbg

        # Release profile
        cfg_rel = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="release", output="c")
        bundle_rel, _ = PenguBuilder(cfg_rel).bundle(output_file=str(d / "bundle_rel.c"))
        c_rel = Path(bundle_rel).read_text(encoding="utf-8")
        assert "in_debug" not in c_rel
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_bounds_check_with_slice():
    """Slice indexing in debug profile must emit check against .len."""
    source = """
weave main into int:
    var xs as array of int with size 4 is [10, 20, 30, 40]
    var s as slice of int is xs at 0 to 2
    var y as int is s at 1
    return y
"""
    d = Path(tempfile.mkdtemp(prefix="pengu_slice_test_", dir=BUILD_DIR))
    try:
        entry = d / "main.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
        bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
        c_code = Path(bundle_path).read_text(encoding="utf-8")
        assert "pengu_assert_bounds(" in c_code
        assert ".len" in c_code
    finally:
        shutil.rmtree(d, ignore_errors=True)
