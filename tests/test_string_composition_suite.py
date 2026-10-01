#!/usr/bin/env python3
"""End-to-end suite for the single string-composition operator.

``+``/``+=`` never concatenate: dynamic strings are built only with ``"{expr}"``
interpolation.  This suite pins that contract down end to end:

* ``err_*.pengu`` must be rejected by the checker with the code recorded in the
  program's ``# EXPECTED:`` marker (``E0005``).
* ``ok_*.pengu`` are compiled with the real project builder, linked against
  ``libpengu_runtime.a`` and executed; their exit status is the assertion.
* ``leak_*.pengu`` additionally run under ``valgrind`` when installed, otherwise
  under the bundled ``tests/leakcheck.c`` interposer, and must report zero
  definitely-lost allocations.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    build_leakcheck,
    compile_run,
    requires_cc,
    requires_leakcheck,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

COMPOSITION_DIR = REPO / "tests" / "test_string_composition"


def _discover(*patterns: str) -> list:
    found = []
    for pattern in patterns:
        found.extend(COMPOSITION_DIR.rglob(pattern))
    return sorted(set(found), key=lambda p: str(p.relative_to(COMPOSITION_DIR)))


def _test_id(path: Path) -> str:
    return str(path.relative_to(COMPOSITION_DIR).with_suffix("")).replace("/", "::")


RUNNABLE = _discover("ok_*.pengu", "test_*.pengu", "leak_*.pengu")
FAILING = _discover("err_*.pengu", "fail_*.pengu")
LEAK_PROGRAMS = _discover("leak_*.pengu")

#: Same known codegen leak as in test_generics_suite: a `(value to string)`
#: temporary passed straight to a call is never released.  `leak_binary_interp`
#: ends with `calling spark.println with (joined length to string)`, which
#: lowers to `spark_println((pengu_to_string(joined.len)))` → 2 bytes lost.
#: Non-strict: the leak is intermittently hidden by the interposer's
#: conservative reachability marking, so a strict marker would flake to XPASS.
#: The deterministic strict pin lives in
#: `test_call_argument_string_temporary_is_released` below.
_KNOWN_STRING_TEMP_LEAKS = {"leak_binary_interp"}
_KNOWN_LEAK_REASON = (
    "known codegen leak: a '(value to string)' temporary passed as a call "
    "argument is never released"
)
LEAK_PARAMS = [
    pytest.param(
        program,
        id=_test_id(program),
        marks=[pytest.mark.xfail(strict=False, reason=_KNOWN_LEAK_REASON)]
        if program.stem in _KNOWN_STRING_TEMP_LEAKS else [],
    )
    for program in LEAK_PROGRAMS
]


def _expected_code(path: Path) -> str:
    m = re.search(r"#\s*EXPECTED:\s*(E\d{4})", path.read_text(encoding="utf-8"))
    assert m, f"{path.name} is missing a '# EXPECTED: EXXXX' marker"
    return m.group(1)


@pytest.mark.parametrize("program", RUNNABLE, ids=_test_id)
@requires_cc
@requires_runtime
def test_string_composition_program_executes(program: Path):
    """The program compiles, links and exits with status 0."""
    res = compile_run(program.read_text(encoding="utf-8"), tag=program.stem)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("program", FAILING, ids=_test_id)
def test_string_composition_program_reports_expected_error(program: Path):
    """String '+'/'+=' is rejected with the documented diagnostic."""
    from tests.conftest import check_error

    check_error(program.read_text(encoding="utf-8"),
                filename=program.name, contains=_expected_code(program))


def _build_leakcheck(tmp_path: Path) -> Path:
    """Delegates to the shared helper (skips where the interposer cannot exist)."""
    return build_leakcheck(tmp_path)


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


@pytest.mark.parametrize("program", LEAK_PARAMS)
@requires_cc
@requires_runtime
@requires_leakcheck
def test_string_composition_no_memory_leaks(program: Path, tmp_path: Path):
    """Interpolated temporaries and owned slots release every allocation."""
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


@pytest.mark.xfail(
    strict=True,
    reason="known codegen leak: owned string temporaries passed as call "
           "arguments are never released (see the leak_* suites)",
)
@requires_cc
def test_call_argument_string_temporary_is_released():
    """Deterministic pin for the leak the LD_PRELOAD suites report.

    `calling spark.println with (n to string)` lowers to
    `spark_println((pengu_to_string(n)))`; the temporary owns a fresh 2-byte
    buffer that nothing ever frees.  The assertion is deliberately
    mechanism-agnostic: any fix must emit *some* release in `pengu_main`.

    Strict xfail: as soon as the compiler owns its expression temporaries this
    test XPASSes and CI asks for the marker (and the two leak xfails) to be
    removed.
    """
    from tests.conftest import gen_bundle

    c = gen_bundle(
        "import std.spark\n"
        "\n"
        "weave main into int:\n"
        "    var n as int is 7\n"
        "    calling spark.println with (n to string)\n"
        "    return 0\n"
    )
    body = c.split("pengu_main(void) {", 1)[1]
    assert "pengu_to_string" in body, "expected the to-string temporary in main"
    assert "pengu_banish_string" in body, (
        "the '(n to string)' temporary is never released: main frees nothing"
    )
