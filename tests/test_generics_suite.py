#!/usr/bin/env python3
"""End-to-end suite for production generics (Fase 1 + derived concepts).

Every ``test_*.pengu`` program under ``tests/test_generics/`` is compiled with
the real project builder, linked against ``libpengu_runtime.a`` and executed;
its exit status is the assertion.  Every ``fail_*.pengu`` program must be
rejected by the checker with the error code recorded in its ``# EXPECTED:``
marker.

The container-ownership programs are additionally checked for memory leaks:
``valgrind`` is used when installed, otherwise the bundled ``tests/leakcheck.c``
interposer (a conservative mark-and-sweep at exit) provides the same
"definitely lost == 0" signal.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    compile_run,
    requires_cc,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

GENERICS_DIR = REPO / "tests" / "test_generics"


def _discover(*patterns: str) -> list:
    """Finds programs under ``tests/test_generics`` recursively (sorted, stable ids)."""
    found = []
    for pattern in patterns:
        found.extend(GENERICS_DIR.rglob(pattern))
    return sorted(set(found), key=lambda p: str(p.relative_to(GENERICS_DIR)))


def _test_id(path: Path) -> str:
    return str(path.relative_to(GENERICS_DIR).with_suffix("")).replace("/", "::")


# Runnable programs: 'test_*.pengu' plus the dedicated leak and gap programs.
RUNNABLE = _discover("test_*.pengu", "leak_*.pengu", "ok_*.pengu", "gap1_*/*.pengu")
# Programs that must be rejected: 'fail_*.pengu' / 'err_*.pengu' with a marker.
FAILING = _discover("fail_*.pengu", "err_*.pengu")
# Ownership/leak programs: the container tests plus the Gap 1 regression set.
LEAK_PROGRAMS = sorted(
    set(_discover("test_list_of_string_cleanup.pengu", "test_map_of_string_to_list.pengu",
                  "test_list_of_box.pengu", "test_derive_imago.pengu",
                  "test_derive_nexus.pengu", "test_derive_omen.pengu",
                  "test_nested_list_leak.pengu", "test_nested_map_leak.pengu",
                  "leak_*.pengu")) | set(_discover("gap1_*/*.pengu")),
    key=lambda p: str(p.relative_to(GENERICS_DIR)),
)


def _expected_code(path: Path) -> str:
    m = re.search(r"#\s*EXPECTED:\s*(E\d{4})", path.read_text(encoding="utf-8"))
    assert m, f"{path.name} is missing a '# EXPECTED: EXXXX' marker"
    return m.group(1)


@pytest.mark.parametrize("program", RUNNABLE, ids=_test_id)
@requires_cc
@requires_runtime
def test_generics_program_executes(program: Path):
    """The program compiles, links and exits with status 0."""
    res = compile_run(program.read_text(encoding="utf-8"), tag=program.stem)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("program", FAILING, ids=_test_id)
def test_generics_program_reports_expected_error(program: Path):
    """The program is rejected with the documented diagnostic code."""
    from tests.conftest import check_error

    check_error(program.read_text(encoding="utf-8"),
                filename=program.name, contains=_expected_code(program))


# --------------------------------------------------------------------------
# Leak checking
# --------------------------------------------------------------------------


def _build_leakcheck(tmp_path: Path) -> Path:
    so = tmp_path / "leakcheck.so"
    src = REPO / "tests" / "leakcheck.c"
    cmd = ["gcc", "-shared", "-fPIC", "-O1", "-o", str(so), str(src), "-ldl", "-lpthread"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"leakcheck build failed: {res.stderr}"
    return so


def _compile_program(program: Path, out_dir: Path) -> Path:
    from pengu_project import PenguBuilder, ProjectConfig

    entry = out_dir / program.name
    entry.write_text(program.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
    bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(out_dir / "bundle.c"))

    exe = out_dir / "bin"
    cmd = [
        "gcc", str(bundle_path),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}", f"-L{BUILD_LIB}", "-g",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=int-conversion",
    ] + runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert res.returncode == 0, f"compilation failed: {res.stderr}"
    return exe


@pytest.mark.parametrize("program", LEAK_PROGRAMS, ids=_test_id)
@requires_cc
@requires_runtime
def test_generics_no_memory_leaks(program: Path, tmp_path: Path):
    """Container ownership: no 'definitely lost' allocation survives the run."""
    exe = _compile_program(program, tmp_path)

    valgrind = shutil.which("valgrind")
    if valgrind:
        cmd = [valgrind, "--leak-check=full", "--error-exitcode=42",
               "--show-leak-kinds=definite", str(exe)]
        env = None
    else:
        so = _build_leakcheck(tmp_path)
        cmd = [str(exe)]
        env = dict(os.environ)
        env["LD_PRELOAD"] = str(so)

    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), env=env)
    assert res.returncode == 0, (
        f"leak detected in {program.name} (exit {res.returncode}):\n"
        f"{res.stderr}\n{res.stdout}"
    )
