"""Smart linking of the vendored ``std_c/`` libraries.

The contract (LANGUAGE.md §19.1, docs/BINDINGS.md) is that importing a binding
is what pulls its C dependencies into *this* executable:

* no import -> no ``#include``, no ``-l``, no C symbols;
* ``std.lingua`` -> ``utf8.h`` only (header-only, no archive);
* ``std.regulus`` -> ``re.h`` + ``-lre`` + ``re_*`` symbols;
* both -> both.

The test builds four throwaway projects and inspects three independent pieces
of evidence: the generated ``bundle.c``, the compiler/linker command line
(``--verbose``) and the final binary (``nm``). Checking only one of them can
pass for the wrong reason: an ``#include`` can be dead code, a ``-l`` can be
dropped by a cache hit, and ``nm`` sees code that was linked but never run.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file()


def _have_regex_archive() -> bool:
    return (ROOT / "build" / "lib" / "libre.a").is_file()


pytestmark = pytest.mark.skipif(
    not (_have_cc() and _have_runtime() and _have_regex_archive()),
    reason="C compiler, libpengu_runtime.a or libre.a not available "
           "(run build_runtime.py)",
)


SOURCES = {
    "hello": """import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
""",
    "lingua": """import std.spark
import std.lingua

weave main into int:
    calling spark.println_int with (calling lingua.codepoint_count with "ñ😀")
    return 0
""",
    "regulus": """import std.spark
import std.regulus

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if cr.is_ok:
        var rx as Regex is cr.value
        defer banish rx
        calling spark.println_bool with (calling rx.is_match with "abc123")
    return 0
""",
    "both": """import std.spark
import std.lingua
import std.regulus

weave main into int:
    calling spark.println_int with (calling lingua.codepoint_count with "ñ")
    var cr as result of Regex to RegexError is calling Regex.compile with "a+"
    if cr.is_ok:
        var rx as Regex is cr.value
        defer banish rx
        calling spark.println_bool with (calling rx.is_match with "baa")
    return 0
""",
}


def _build(tmp_path: Path, name: str) -> tuple[str, str, Path]:
    """Builds one project; returns (bundle text, verbose output, executable)."""
    project = tmp_path / name
    project.mkdir()
    (project / "main.pengu").write_text(SOURCES[name], encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "build", "--verbose"],
        capture_output=True, text=True, timeout=300, cwd=str(project), env=env,
    )
    assert res.returncode == 0, (
        f"build failed for {name}:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    bundle = (project / "build" / "bundle.c").read_text(encoding="utf-8")
    exe = project / "build" / ("app.exe" if os.name == "nt" else "app")
    assert exe.is_file(), f"no executable for {name}: {list((project / 'build').iterdir())}"
    return bundle, res.stdout + res.stderr, exe


def _symbols(exe: Path) -> str:
    tool = shutil.which("nm")
    if not tool:
        return ""
    res = subprocess.run([tool, str(exe)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return res.stdout


@pytest.mark.parametrize(
    "name, lingua, regulus",
    [
        ("hello", False, False),
        ("lingua", True, False),
        ("regulus", False, True),
        ("both", True, True),
    ],
)
def test_smart_linking_matrix(tmp_path, name, lingua, regulus):
    bundle, log, exe = _build(tmp_path, name)

    # 1. Headers are emitted exactly for the imported binding.
    assert ('#include "utf8.h"' in bundle) is lingua, (
        f"{name}: utf8.h include mismatch\n{bundle[:2000]}"
    )
    assert ('#include "re.h"' in bundle) is regulus, (
        f"{name}: re.h include mismatch\n{bundle[:2000]}"
    )

    # 2. The archive reaches the link line exactly for std.regulus.
    link_lines = [line for line in log.splitlines() if "running C compiler" in line]
    assert link_lines, f"{name}: no compiler command in verbose output"
    link_line = link_lines[-1]
    assert ("-lre" in link_line) is regulus, (
        f"{name}: -lre mismatch\n{link_line}"
    )

    # 3. The symbols really are (or are not) in the produced executable.
    symbols = _symbols(exe)
    if symbols:
        assert ("re_compile_dynamic_ex" in symbols) is regulus, (
            f"{name}: re_* symbols mismatch"
        )
        assert ("lingua_codepoint_count" in symbols) is lingua, (
            f"{name}: lingua_* symbols mismatch"
        )


def test_the_raw_archives_are_small_and_separate():
    """The whole point: the regex archive is one member, not part of the runtime."""
    runtime = (ROOT / "build" / "lib" / "libpengu_runtime.a").stat().st_size
    regex = (ROOT / "build" / "lib" / "libre.a").stat().st_size
    assert regex < runtime, "libre.a should be a small satellite archive"
    assert regex > 0
