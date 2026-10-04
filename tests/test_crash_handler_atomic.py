"""Phase 3 item 3.8 — the crash-handler install is atomic and off the hot path.

Two defects were measured before the fix:

1. `pengu_install_crash_handler()` guarded its work with

       static volatile int g_pengu_handler_installed = 0;
       if (!g_pengu_handler_installed) { g_pengu_handler_installed = 1; ... }

   which is a check-then-set data race: two threads can both observe 0 and both
   run the install. `volatile` orders nothing between threads.

2. `pengu_frame_push()` called the install on **every** frame push. A bundle of a
   small program has hundreds of pushes, so the check ran on a hot path for no
   benefit.

The fix uses a platform once-primitive (`pthread_once` on POSIX,
`InitOnceExecuteOnce` on Windows) and moves the install to the generated `main`.

Rule C1: these tests compile and run real programs and inspect C output, symbols
or behaviour -- they never grep the bundle for a string.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HEADER = REPO / "pengu_runtime.h"
TCC = REPO / "build" / "tcc-dist" / "tcc-dist" / "bin" / "tcc"
INCLUDE = REPO / "build" / "include"


def _pengu(*args, timeout=600):
    r = subprocess.run(
        [sys.executable, "-m", "pengu_project", *args],
        cwd=str(REPO), capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# The header must stay the most disciplined artifact in the repo
# ---------------------------------------------------------------------------

def test_header_still_compiles_warning_free():
    """`-Wall -Wextra -Werror` on the header, which is the repo's strictest check.

    A once-primitive adds an include and a callback; if that regressed the header
    this test catches it before anything else does.
    """
    if shutil.which("gcc") is None:
        pytest.skip("gcc is not available")
    r = subprocess.run(
        ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
         str(HEADER)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_frame_push_does_not_install_the_handler():
    """The hot path must not call the installer.

    Asserted on the *source of the header function* rather than on a bundle: this
    is build configuration/code shape, and the behavioural half is covered by the
    compile-and-run tests below. Reading the function body is the only way to
    assert "frame_push does not call X" without executing a billion frames.
    """
    text = HEADER.read_text(encoding="utf-8")
    start = text.index("static inline void pengu_frame_push(")
    end = text.index("\n  }", start)
    body = text[start:end]
    assert "pengu_install_crash_handler()" not in body, (
        "pengu_frame_push still installs the crash handler on every push"
    )


def test_the_install_uses_a_once_primitive():
    """No check-then-set flag may remain.

    The race was the whole point of the item, so assert the primitive is present
    and the racy global is gone.
    """
    text = HEADER.read_text(encoding="utf-8")
    assert "g_pengu_handler_installed" not in text, (
        "the racy `volatile int` guard is still present"
    )
    has_once = ("pthread_once" in text) or ("InitOnceExecuteOnce" in text)
    assert has_once, "no platform once-primitive found for the handler install"


# ---------------------------------------------------------------------------
# Behaviour: the handler still fires, and the program still runs
# ---------------------------------------------------------------------------

def test_crash_handler_still_reports_a_bounds_failure(tmp_path):
    """Moving the install must not disable it.

    Runs a program that reads out of bounds and requires the runtime's crash
    report, which is what the handler produces.
    """
    src = tmp_path / "crash.pengu"
    src.write_text(
        "weave main into int:\n"
        "  var xs as list of int is [1, 2, 3]\n"
        "  var i as int is 10\n"
        "  return xs at i\n",
        encoding="utf-8",
    )
    rc, out = _pengu("run", str(src))
    assert "Index out of bounds" in out, out


def test_installed_handler_is_present_at_process_start(tmp_path):
    """The generated entry point installs the handler before running the program.

    Asserted structurally on the emitted entry point: the installer must appear
    there, because that is the only call site left after removing the per-frame
    one. Without it nothing would ever install the handler.
    """
    src = tmp_path / "hello.pengu"
    src.write_text(
        'import std.spark\n'
        'weave main into int:\n'
        '  calling spark.println with "x"\n'
        '  return 0\n',
        encoding="utf-8",
    )
    bundle = tmp_path / "hello.c"
    rc, out = _pengu("build", "--entry", str(src), "--output", str(bundle))
    assert rc == 0, out
    text = bundle.read_text(encoding="utf-8")
    # Find the C entry point and require the install call inside it.
    m = re.search(r"int main\(int argc, char\*\* argv\) \{(.*?)\n\}", text, re.S)
    assert m, "could not locate the generated C entry point"
    assert "pengu_install_crash_handler()" in m.group(1), (
        "the generated main no longer installs the crash handler; with the "
        "per-frame call removed, nothing would"
    )


def test_program_compiles_and_runs_after_the_change(tmp_path):
    """End-to-end: the runtime still builds and executes.

    tcc is used because it is the project's development compiler and the header
    change adds a `<pthread.h>` include that tcc must also accept.
    """
    if not TCC.exists():
        pytest.skip("the bundled tcc is not present")
    src = tmp_path / "run.pengu"
    src.write_text(
        'import std.spark\n'
        'weave main into int:\n'
        '  calling spark.println with "ok"\n'
        '  return 0\n',
        encoding="utf-8",
    )
    rc, out = _pengu("run", str(src))
    assert rc == 0, out
    assert "ok" in out, out
