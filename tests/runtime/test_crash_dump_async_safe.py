"""Phase 3 item 3.7 — the crash dump is async-signal-safe.

`LANGUAGE.md` and `CHANGELOG.md` claimed the crash handlers write the callstack
"de forma async-signal-safe (utilizando exclusivamente llamadas directas a
`write(2)` / `_write`)". That was false: `pengu_dump_frame_stack` built its
output with `snprintf`, which POSIX does **not** list as async-signal-safe (it
can take a stdio or locale lock, and some libcs allocate internally). The header
itself admitted the gap in a comment. AUDIT_1.0.md §5.2 recorded the
contradiction.

The dump now formats by hand (pointer arithmetic + integer division only), so
the whole crash path depends on `write(2)`/`_write` and `_exit()` alone. The
claim is now true rather than retracted.

Rule C1: the first test **measures the compiled artifact** — it disassembles the
link closure of the crash path and asserts what the linker had to resolve. It
does not grep the header source. The second test **executes** a crashing program.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import (
    requires_no_sanitizer_reason,
    BUILD_INCLUDE,
    REPO,
    compile_run,
    have_tool,
    nm_symbol_name,
    requires_cc,
    requires_runtime,
)

pytestmark = [requires_cc, requires_runtime]

# Not async-signal-safe per POSIX.1-2008 (or not safe in practice): each can take
# a lock, allocate, or touch shared stdio/locale state, so calling one from the
# SIGSEGV handler can deadlock or corrupt state while the process is dying.
UNSAFE_IN_SIGNAL = (
    "snprintf", "vsnprintf", "sprintf", "printf", "fprintf", "vprintf",
    "malloc", "calloc", "realloc", "free",
    "fwrite", "fputs", "puts", "fflush",
    "strerror", "strerror_r", "localtime", "syslog",
    "pthread_mutex_lock", "pthread_mutex_unlock",
)

# Inserted by the compiler itself (-fstack-protector) and reachable only when the
# canary is already smashed, where the process aborts anyway. Not our formatting
# path, so it is explicitly tolerated.
COMPILER_RUNTIME_ALLOWED = ("__stack_chk_fail", "_GLOBAL_OFFSET_TABLE_")


def _crash_closure_undefined_symbols(tmp_path: Path) -> list:
    """Compiles a probe that touches only the crash path, returns `nm -u` names.

    At ``-O0`` GCC emits only the ``static``/``static inline`` functions that are
    actually reached from ``main``, so the undefined symbols of the resulting
    object are exactly the external calls the crash path needs.
    """
    probe = tmp_path / "crash_probe.c"
    probe.write_text(
        '#include "pengu_runtime.h"\n'
        "int main(void) {\n"
        "  pengu_install_crash_handler();\n"
        '  pengu_dump_frame_stack("probe", 11);\n'
        "  return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    obj = tmp_path / "crash_probe.o"
    build = subprocess.run(
        ["gcc", "-O0", "-std=c11", "-I", str(REPO), "-I", str(BUILD_INCLUDE),
         "-c", str(probe), "-o", str(obj)],
        capture_output=True, text=True, timeout=300,
    )
    assert build.returncode == 0, f"probe failed to compile:\n{build.stderr}"

    nm = shutil.which("nm")
    assert nm, "nm is required for this measurement"
    res = subprocess.run([nm, "-u", str(obj)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"nm failed:\n{res.stderr}"
    # `nm_symbol_name` strips Mach-O's leading underscore, so the offender check
    # below is a real gate on macOS too instead of silently matching nothing.
    # MinGW reports a DLL import as `__imp__name`, and the Windows CRT exports
    # `write` as `_write`: strip both so the comparison is against the C name.
    return [_base_symbol(line.split()[-1])
            for line in res.stdout.splitlines() if line.strip()]


def _base_symbol(symbol: str) -> str:
    """`nm` spelling -> the C identifier the source used, on every platform."""
    symbol = nm_symbol_name(symbol)
    if symbol.startswith("__imp_"):
        symbol = symbol[len("__imp_"):]
    return symbol.lstrip("_")


def test_crash_path_calls_no_async_signal_unsafe_function(tmp_path):
    """The compiled crash closure must not reference snprintf/malloc/stdio.

    C2: put `snprintf` back into `pengu_dump_frame_stack` and `snprintf` shows up
    in this list, failing the test.
    """
    symbols = _crash_closure_undefined_symbols(tmp_path)
    # Sanity: the probe really did compile the crash path, not an empty stub.
    assert "write" in symbols, (
        f"the probe does not reference write(); it did not build the crash path: {symbols}"
    )
    offenders = [s for s in symbols if s in UNSAFE_IN_SIGNAL]
    assert not offenders, (
        f"the crash handler references async-signal-unsafe function(s) {offenders}; "
        f"all undefined symbols were: {sorted(set(symbols))}"
    )


@requires_no_sanitizer_reason(
    "UBSan reports the fault before the crash handler writes its dump",
)
def test_crash_handler_still_reports_the_pengu_frame(tmp_path):
    """Hand-formatting must not cost the diagnostic: the frame is still named.

    The trace is checked on stderr, because the fallback disposition would also
    exit 139 — only the handler prints `[PENGU CRASH]` and the frame line.
    """
    res = compile_run(
        "weave boom into int:\n"
        "    var p as ref to int is null\n"
        "    set essence of p is 42\n"
        "    return 0\n"
        "\n"
        "weave main into int:\n"
        "    return calling boom\n",
        tag="crash_trace",
        expect_exit=None,
    )
    assert res.returncode != 0, "the program was supposed to crash"
    err = res.stderr
    assert "[PENGU CRASH]" in err, f"handler did not run:\n{err}"
    assert "Stack trace (most recent call first):" in err, err
    assert re.search(r"at boom \(.*\.pengu:\d+\)", err), (
        f"the frame is missing its name and file:line:\n{err}"
    )


def test_bounds_panic_message_is_unchanged_by_hand_formatting(tmp_path):
    """`pengu_bounds_panic` formats by hand too; its text must be byte-identical.

    This is the path that a SIGSEGV handler may re-enter, so it had to lose
    `snprintf` as well — without changing what the user sees.
    """
    res = compile_run(
        "weave main into int:\n"
        "    var xs as array of int with size 3 is [1, 2, 3]\n"
        "    calling print with ((xs at 5) to string)\n"
        "    return 0\n",
        tag="bounds_text",
        expect_exit=None,
    )
    assert res.returncode != 0
    assert "[PENGU] Index out of bounds: 5 (length 3) at " in res.stderr, (
        f"the bounds message changed:\n{res.stderr}"
    )


@requires_no_sanitizer_reason(
    "UBSan reports the fault before the crash handler writes its dump",
)
def test_the_call_chain_is_reported_when_the_call_is_a_statement():
    """The dump is a *call chain*, not just the innermost function.

    Measured in this session: a chain written with the call in statement position
    reports every frame with its `.pengu` file:line. A chain written the
    idiomatic way — `return calling f` — currently reports only the innermost
    frame, because the codegen emits `pengu_frame_pop()` before evaluating the
    return expression.

    That limitation is **not** pinned here (it is a defect, not a contract): it is
    recorded with its measurement in `AUDIT_1.0_FASE3.md` §14 and deferred to
    1.1. This test protects the part that works, so the frame machinery cannot
    regress unnoticed while the tail-call case is pending.
    """
    res = compile_run(
        "weave inner_fn into int:\n"
        "    var p as ref to int is null\n"
        "    set essence of p is 42\n"
        "    return 0\n"
        "\n"
        "weave mid_fn into int:\n"
        "    var x as int is calling inner_fn\n"
        "    return x\n"
        "\n"
        "weave top_fn into int:\n"
        "    var y as int is calling mid_fn\n"
        "    return y\n"
        "\n"
        "weave main into int:\n"
        "    var z as int is calling top_fn\n"
        "    return z\n",
        tag="crash_chain",
        expect_exit=None,
    )
    assert res.returncode != 0
    frames = re.findall(r"^\s*at (\w+) \(", res.stderr, re.MULTILINE)
    assert frames == ["inner_fn", "mid_fn", "top_fn", "pengu_main"], (
        f"the crash dump lost part of the call chain: {frames}\n{res.stderr}"
    )
    assert re.search(r"at mid_fn \(.*\.pengu:\d+\)", res.stderr), (
        f"frames must carry file:line, not just a name:\n{res.stderr}"
    )
