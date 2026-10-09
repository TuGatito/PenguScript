"""Phase 3 item 3.6 — arithmetic and bus faults also dump the PenguScript trace.

Before this item the handler covered only `SIGSEGV` and `SIGABRT`, installed via
`signal()`. An integer division by zero therefore killed the process with a bare
"Floating point exception (core dumped)": no `[PENGU CRASH]`, no frame, and
`pengu eval "1/0"` surfaced exit **248** because the CLI turned the negative
subprocess return code (-8, killed by signal 8) into `sys.exit(-8)`.

`ROADMAP_2.0.md` item 3.6 states the acceptance directly:

    Un programa que divide por cero volca los frames de PenguScript;
    test con `-ftrapv`

and the phase criterion repeats it:

    Una división por cero volca los frames y `pengu eval "1/0"` imprime un
    mensaje, no exit 248.

The handler now installs `SIGSEGV`, `SIGABRT`, `SIGFPE`, `SIGILL` and `SIGBUS`
with `sigaction`. `raise()`-ing a signal from a C harness is used to prove each
one is installed: with the handler the process `_exit`s with `128+signo` and
prints the trace, without it Python sees a *negative* return code (killed by the
signal). The two cases are distinguishable, so the test cannot pass vacuously.

Rule C1: every test compiles, links and executes a real program.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    DIVISION_BY_ZERO_TRAPS,
    FAULT_SIGNALS,
    requires_no_sanitizer_reason,
    requires_posix_signal_exit,
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    compile_run,
    have_tool,
    requires_cc,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

pytestmark = [requires_cc, requires_runtime]

# (signal name, expected exit code = 128 + signo) comes from `tests.conftest`,
# which resolves the number through the `signal` module: the literal 135 was
# Linux's SIGBUS and does not hold on macOS, where SIGBUS is 10 (→ 138).
# Delivered with raise(), so the test proves the *installation*, not that
# PenguScript arithmetic reaches it.


def _cc() -> str:
    for cand in ("gcc", "clang", "cc"):
        if have_tool(cand):
            return cand
    return ""


@requires_posix_signal_exit
@pytest.mark.parametrize("signame,expected", FAULT_SIGNALS)
def test_fault_signal_is_installed_by_the_crash_handler(signame, expected, tmp_path):
    """`pengu_install_crash_handler()` must handle each fault signal.

    With the handler: exit 128+signo and a `[PENGU CRASH]` trace on stderr.
    Without it: the process is killed by the signal and the return code is
    negative. `SIGFPE`/`SIGILL`/`SIGBUS` are the three item 3.6 adds.

    C2: drop the `pengu_install_one_signal(SIGFPE)` call and the SIGFPE case
    fails with `returncode == -8` and no trace.
    """
    src = tmp_path / "raise_signal.c"
    src.write_text(
        '#include "pengu_runtime.h"\n'
        "#include <signal.h>\n"
        "int main(void) {\n"
        "  pengu_install_crash_handler();\n"
        f"  raise({signame});\n"
        "  return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    exe = tmp_path / "raise_signal"
    cmd = [_cc(), str(src), f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
           f"-L{BUILD_LIB}"]
    cmd += runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    build = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, f"harness failed to build:\n{build.stderr}"

    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == expected, (
        f"{signame} is not handled: expected exit {expected} (128+signo) from the "
        f"handler, got {run.returncode} "
        f"({'killed by the signal' if run.returncode < 0 else 'unexpected exit'})\n"
        f"stderr: {run.stderr}"
    )
    assert "[PENGU CRASH]" in run.stderr, (
        f"{signame} exited with the right code but printed no trace:\n{run.stderr}"
    )


@requires_no_sanitizer_reason(
    "UBSan reports the division by zero instead of delivering SIGFPE",
)
@requires_posix_signal_exit
@pytest.mark.skipif(
    not DIVISION_BY_ZERO_TRAPS,
    reason="AArch64's SDIV returns 0 for a zero divisor instead of raising "
           "SIGFPE (measured on the macOS arm64 runner: exit 0 with '0'), so "
           "the crash handler is unreachable there",
)
def test_integer_division_by_zero_dumps_frames_and_exits_136():
    """The item's acceptance criterion, end to end through a compiled program.

    This is the case that produced `pengu eval "1/0"` → exit 248 with no message.

    The program divides two `int`s computed at runtime, so the division cannot be
    constant-folded away; what stops the trap on AArch64 is the hardware, not the
    optimiser (see the skip reason above).

    C2: remove the SIGFPE installation and the process dies on signal 8 with no
    `[PENGU CRASH]`, so both assertions fail.
    """
    res = compile_run(
        "weave divide with a as int, b as int into int:\n"
        "    return a / b\n"
        "\n"
        "weave main into int:\n"
        "    var q as int is calling divide with 1, 0\n"
        "    calling print with (q to string)\n"
        "    return 0\n",
        tag="sigfpe_divzero",
        expect_exit=None,
    )
    assert res.returncode == 128 + signal.SIGFPE, (
        f"expected the handler to _exit({128 + signal.SIGFPE}) for SIGFPE, "
        f"got {res.returncode}\n"
        f"stderr: {res.stderr}"
    )
    assert "[PENGU CRASH]" in res.stderr, res.stderr
    assert f"signal/code {signal.SIGFPE}" in res.stderr, (
        f"the dump must name SIGFPE (8):\n{res.stderr}"
    )
    assert re.search(r"at divide \(.*\.pengu:\d+\)", res.stderr), (
        f"the trace must name the faulting weave with file:line:\n{res.stderr}"
    )


@requires_no_sanitizer_reason(
    "UBSan reports the overflow instead of the trap the test asserts",
)
@pytest.mark.skipif(
    sys.platform == "darwin" or os.name == "nt",
    reason="Apple clang lowers -ftrapv to a trap instruction that raises "
           "SIGTRAP, and MinGW's gcc turns it into a fast-fail "
           "(0xC0000409) that never reaches a POSIX-signal handler; neither is "
           "one of the signals the crash handler installs (measured: rc=-5 on "
           "macOS, rc=3221226505 on Windows, no '[PENGU CRASH]'). "
           "test_debug_traps_overflow still asserts that the overflow is "
           "trapped, without requiring the GCC-specific signal",
)
def test_debug_signed_overflow_trap_is_reported():
    """`-ftrapv` (debug builds) turns signed overflow into a trap; it is dumped.

    `compile_run` compiles the debug profile with `-ftrapv`, so this is the
    configuration the roadmap's "test con -ftrapv" asks for.
    """
    res = compile_run(
        "weave overflow into int:\n"
        "    var a as int is 2147483647\n"
        "    return a + 1\n"
        "\n"
        "weave main into int:\n"
        "    calling print with (calling overflow to string)\n"
        "    return 0\n",
        tag="sigfpe_ftrapv",
        expect_exit=None,
    )
    assert res.returncode != 0, "the overflow was not trapped"
    assert "[PENGU CRASH]" in res.stderr, (
        f"a trapped overflow must produce the trace, got rc={res.returncode}:\n"
        f"{res.stderr}"
    )
    assert re.search(r"at overflow \(.*\.pengu:\d+\)", res.stderr), (
        f"the trace must name the faulting weave:\n{res.stderr}"
    )
