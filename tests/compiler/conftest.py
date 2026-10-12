"""Shared plumbing for the compiler test-suite (``tests/compiler/``).

Three levels, cheapest first:

* :func:`parse_and_check` — parse + semantic check, no C toolchain. Tens of
  milliseconds per case; this is where almost every test lives.
* :func:`emit_c` — the same, plus code generation, so a test can assert on the
  *shape* of the emitted C (``int_clamp(int32_t self, …)``) without compiling it.
* :func:`compile_and_run` — the full pipeline (Pengu source -> gcc -> stdout).
  Slow, needs a C compiler and ``build/lib/libpengu_runtime.a``; it is the only
  level that proves the whole feature works, and it is the only one that skips.

Notes for whoever adds the next test here:

* ``PenguChecker``'s first positional argument is the *source text*, not a
  ``SymbolTable``: the checker owns its symbol table
  (``checker.symbols``), and ``check()`` **raises** the first
  :class:`~pengu_parser.pengu_errors.PenguError` instead of returning it.  The
  fixtures below wrap both facts once so no test has to remember them.
* ``--strict-markers`` is on in ``pytest.ini``, so a new marker has to be
  registered there before it can be used.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

#: Repository root: ``tests/compiler/conftest.py`` -> ``tests/compiler`` ->
#: ``tests`` -> the checkout.
COMPILER_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures" / "primitives"

if str(COMPILER_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPILER_ROOT))

#: The runtime archive and the header directory the builder links against.
BUILD_LIB = COMPILER_ROOT / "build" / "lib"
BUILD_INCLUDE = COMPILER_ROOT / "build" / "include"


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return (BUILD_LIB / "libpengu_runtime.a").is_file()


@pytest.fixture(scope="session")
def pengu_root() -> Path:
    """The repository root, for tests that need to read a real file."""
    return COMPILER_ROOT


@pytest.fixture(scope="session")
def has_cc() -> bool:
    """True when a C compiler is on PATH (the e2e tests skip without one)."""
    return _have_cc()


@pytest.fixture
def parse_and_check():
    """Parses + type-checks a source string. Returns ``(errors, ast, symbols)``.

    ``errors`` is the complete list of diagnostics (empty on success); the
    fixture never raises for a *diagnostic*, only for a compiler crash, so a
    test can assert on the error codes it expects.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_errors import PenguError
    from pengu_parser.pengu_parser import PenguParser

    def _run(source: str, filename: str = "t.pengu"):
        ast = PenguParser().parse(source)
        checker = PenguChecker(base_dir=str(COMPILER_ROOT))
        try:
            checker.check(ast, source=source, filename=filename)
        except PenguError as exc:
            errors = list(getattr(exc, "all_errors", None) or [exc])
            return errors, ast, checker.symbols
        return [], ast, checker.symbols

    return _run


@pytest.fixture
def emit_c():
    """Parses + checks + emits the whole C bundle for a source string.

    Asserts the source is clean: code generation on top of error recovery would
    only make a failure harder to read.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_codegen import is_release_unsafe, set_release_unsafe
    from pengu_parser.pengu_parser import PenguParser

    def _run(source: str, filename: str = "t.pengu") -> str:
        ast = PenguParser().parse(source)
        checker = PenguChecker(base_dir=str(COMPILER_ROOT))
        checker.check(ast, source=source, filename=filename)
        # `_RELEASE_UNSAFE` is a process-wide switch: leaving it set would make
        # the *next* test's bundle depend on this one's profile.
        previous = is_release_unsafe()
        set_release_unsafe(False)
        try:
            codegen = PenguCodegen(checker.symbols, [filename], str(COMPILER_ROOT),
                                   compile_env=checker.compile_env)
            codegen.collect_declarations([(filename, ast)])
            return codegen.generate_bundle()
        finally:
            set_release_unsafe(previous)

    return _run


#: Progress lines `pengu run` prints to stdout before the program's own output.
#: The e2e fixture strips everything up to and including the last one, so an
#: assertion sees exactly what the program printed.
_CLI_NOISE = re.compile(r"^\s+(Scripting|Compiling|Building|Linking|Finished|Running|Cached)\b")


def _program_output(stdout: str) -> str:
    """The program's stdout, without the driver's progress chatter."""
    lines = stdout.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(" ") and "Running " in lines[i]:
            return "\n".join(lines[i + 1:]) + ("\n" if lines[i + 1:] else "")
    return "\n".join(l for l in lines if not _CLI_NOISE.match(l))


@pytest.fixture
def pengu_cli(pengu_root, tmp_path):
    """Runs ``pengu_project.py <args>`` in ``tmp_path``; returns CompletedProcess.

    For the few checks that are about the *driver* rather than the front end
    (multi-module coherence, a whole program's exit status).  No C compiler is
    required unless the subcommand builds something.
    """
    def _run(*args: str, cwd: Path | None = None, env: dict | None = None,
             timeout: int = 240) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(pengu_root / "pengu_project.py"), *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd or tmp_path),
            env={**os.environ, "PYTHONPATH": str(pengu_root), **(env or {})},
        )

    return _run


@pytest.fixture
def compile_and_run(pengu_root, tmp_path, has_cc):
    """Full pipeline: source -> binary -> its stdout. Requires a C compiler.

    Uses the documented CLI (``pengu run``) rather than gcc directly: the CLI is
    what a user runs, and it owns the include/library/link flags.  Progress
    lines are stripped so the return value is the program's output.
    """
    if not has_cc:
        pytest.skip("no C compiler available")
    if not _have_runtime():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")

    def _run(source: str, tag: str = "t", timeout: int = 240) -> str:
        script = tmp_path / f"{tag}.pengu"
        script.write_text(source, encoding="utf-8")
        # cwd is the temp directory on purpose: a stray `pengu.toml` or `lib/`
        # in the repository must not change what this program resolves.
        result = subprocess.run(
            [sys.executable, str(pengu_root / "pengu_project.py"), "run",
             "--ephemeral", str(script)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(pengu_root)},
        )
        assert result.returncode == 0, (
            f"pengu run failed ({result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
        return _program_output(result.stdout)

    return _run
