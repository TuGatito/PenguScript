"""Roadmap 2.0 Phase 8 — compiler bugs found *by* the Phase 8 gates.

Every entry here was discovered while converting a text gate into a gate that
compiles, executes or measures (items 8.1 and 8.4).  They are pinned with
``xfail(strict=True)`` rather than fixed, because each one lives in a phase that
is already closed and the roadmap's rule is to open it as a new item with a
measurement instead of fixing it in the dark:

* ``BUG A`` — `pengu check` is clean and `pengu build` fails: the checker and the
  code generator disagree about the type of the `error` value inside an `or:`
  block.  Found by the compliance corpus.
* ``BUG B`` — a rule-C4 violation: the unsized `array of T` parameter of
  `LANGUAGE.md` §5.0 makes the CLI print a Python traceback instead of a
  diagnostic, because the error is raised during codegen and only check-time
  diagnostics go through the reporter.

`strict=True` means a fix turns these into hard failures so they are promoted to
assertions instead of being forgotten.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO

#: LANGUAGE.md §5.0's own example: an `array of T` parameter without a size.
_BUG_B = """\
weave f with xs as array of int into int:
    return 0

weave main into int:
    return 0
"""

#: `error` is a PenguString inside the `or:` block; reported as mistyped by codegen.
_BUG_A = """\
import std.spark
import std.oracle

weave risky into result of int to string:
    return calling oracle.err_of with "negative"

weave main into int:
    var bad as int is (calling risky) or:
        if error == "negative":
            calling spark.println with "matched"
        0
    return bad
"""

#: The same comparison bound to a local first (the shape the corpus uses).
_BUG_A_INLINE = """\
import std.oracle
import std.spark

weave risky into result of int to string:
    return calling oracle.err_of with "negative"

weave main into int:
    var bad as int is (calling risky) or:
        var matched as bool is error == "negative"
        var n as int is 0
        if matched:
            set n is 1
        n
    return bad
"""


def _cli(args, timeout=600):
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
    )


def _write(tmp_path, source, name):
    entry = tmp_path / name
    entry.write_text(source, encoding="utf-8")
    return entry


@pytest.mark.parametrize("source,name", [
    (_BUG_A, "or_error.pengu"),
    (_BUG_A_INLINE, "or_error_inline.pengu"),
])
def test_check_clean_implies_build_clean_in_an_or_block(tmp_path, source, name):
    """The checker accepting a program must mean the generator can emit it.

    Reported by the item 8.4 author as "BUG A": `error` compared directly inside
    an `or:` block was said to make `check` clean and `build` fail with
    *aggregate value used where an integer was expected*.  **Not reproduced**:
    both forms below build cleanly on this checkout (and the one variant that does
    fail, `result of string to string` with an `int` fallback, is rejected at
    *check* time with the correct `TypeMismatchError`).  The test is therefore a
    positive gate rather than an xfail, so the reported divergence stays checked
    without pretending it exists.
    """
    entry = _write(tmp_path, source, name)
    checked = _cli(["check", "--entry", str(entry)])
    assert checked.returncode == 0, f"check is not clean:\n{checked.stdout}"
    built = _cli(["build", "--entry", str(entry), "--output", str(tmp_path / "b.c")])
    assert built.returncode == 0, (
        "check is clean but build fails, so the two phases disagree:\n"
        f"{built.stdout}\n{built.stderr}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="BUG B (rule C4): an unsized `array of T` parameter raises during codegen "
           "and the CLI leaks a Python traceback instead of a diagnostic",
)
def test_unsized_array_parameter_does_not_traceback(tmp_path):
    """Rule C4: no user input may produce a Python traceback."""
    entry = _write(tmp_path, _BUG_B, "array_param.pengu")
    built = _cli(["build", "--entry", str(entry), "--output", str(tmp_path / "b.c")])
    combined = built.stdout + built.stderr
    assert "Traceback (most recent call last)" not in combined, (
        "the CLI leaked a Python traceback:\n" + combined
    )
    assert built.returncode != 0


#: F8-N10 — an array passed to a variadic C function leaves a dangling reference to
#: a stack temporary.  The reproduction is the compliance corpus program for
#: `LANGUAGE.md` §8.2 (`declare`, external C functions), which passes an array to a
#: variadic `sum_args`.  The program returns the right answer without
#: instrumentation — which is why the suite was green for years — so the pin only
#: runs under AddressSanitizer.
_VARIADIC_REPRO = REPO / "tests" / "compliance" / "020-declare-extern-c.pengu"


@pytest.mark.skipif(
    "sanitize" not in os.environ.get("PENGU_CFLAGS", ""),
    reason="F8-N10 is only observable under AddressSanitizer (see the nightly sanitizers job)",
)
@pytest.mark.xfail(
    strict=True,
    reason="F8-N10: ASan reports 'stack-use-after-scope' in the variadic callee; the "
           "uninstrumented run returns the right value, so only this run sees the "
           "dangling reference",
)
def test_variadic_array_argument_is_stack_use_after_scope(tmp_path):
    """The memory error the sanitizer job found and the plain suite cannot see.

    Polarity: the *bug* is the ASan report, so the assertion is "no report".  It
    currently fails (xfail), and the fix turns it into an XPASS, which `strict`
    converts into a build failure that asks for this marker to be removed.
    """
    assert _VARIADIC_REPRO.is_file(), f"missing reproduction {_VARIADIC_REPRO}"
    bundle = tmp_path / "variadic.c"
    built = _cli(["build", "--entry", str(_VARIADIC_REPRO), "--output", str(bundle)])
    assert built.returncode == 0, f"build failed:\n{built.stdout}\n{built.stderr}"

    from tests.conftest import (BUILD_DIR, BUILD_INCLUDE, BUILD_LIB, default_cc,
                                runtime_link_flags, runtime_tail_flags)

    # The sanitizer flags have to be applied here too: this test compiles the
    # bundle itself, so without them there is no instrumentation and no report.
    import shlex

    extra = shlex.split(os.environ.get("PENGU_CFLAGS", "")) + shlex.split(
        os.environ.get("PENGU_LDFLAGS", "")
    )

    exe = tmp_path / "prog"
    compiled = subprocess.run(
        [default_cc(), str(bundle), f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
         *extra, f"-L{BUILD_LIB}", *runtime_link_flags(), *runtime_tail_flags(),
         "-o", str(exe)],
        capture_output=True, text=True, timeout=600,
    )
    assert compiled.returncode == 0, compiled.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    combined = run.stdout + run.stderr
    assert "AddressSanitizer" not in combined, (
        "AddressSanitizer reported a memory error:\n" + combined[-2000:]
    )
    assert run.returncode == 0, f"rc={run.returncode}\n{combined[-2000:]}"
