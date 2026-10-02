#!/usr/bin/env python3
"""C1 regression tests: the ``PenguString`` ownership flag (``is_owned``).

``pengu_banish_string`` must release *only* heap buffers the runtime allocated
itself.  Static views (string literals, ``from_cstr`` views, the ``from_bool``
rodata view) must be left untouched, while ``new`` / ``format`` results must be
released exactly once.

Every test here compiles and RUNS a small ``.pengu`` program (the same
``compile_run`` plumbing the rest of the suite uses) and asserts its exit code
and stdout.  The last test additionally runs the binary under the glibc
``LD_PRELOAD`` leak interposer to prove the owned buffers are really freed.
"""
import os
import shutil
import subprocess
from pathlib import Path

from tests.conftest import (
    REPO,
    compile_run,
    requires_cc,
    requires_leakcheck,
    requires_runtime,
)

# ---------------------------------------------------------------------------
# Programs under test
# ---------------------------------------------------------------------------

# 1. A string literal lowers to `pengu_string_from_cstr` (a `.rodata` view).
#    Banishing it must be a no-op, not a `free()` of static memory.
LITERAL_BANISH = (
    'weave main into int:\n'
    '  var s is "hello"\n'
    '  banish s\n'
    '  return 0\n'
)

# 2. A `const` string is emitted as `pengu_string_from_cstr("...")` too; copying
#    it into a local aliases the static view.  (An explicit `ref to char` ->
#    `string` conversion is rejected by the checker with TypeMismatchError, so
#    this is the reachable static-view path besides a bare literal.)
CONST_VIEW_BANISH = (
    'const G_STATIC as string is "immutable"\n'
    'weave main into int:\n'
    '  var s is G_STATIC\n'
    '  banish s\n'
    '  return 0\n'
)

# 3. `bool to string` lowers to `pengu_string_from_bool`, which returns a
#    `.rodata` view ("true"/"false").  Banishing it must not free rodata.
BOOL_BANISH = (
    'weave main into int:\n'
    '  var c as bool is true\n'
    '  var s as string is (c to string)\n'
    '  defer banish s\n'
    '  calling print with s\n'
    '  return 0\n'
)

# 4. `to string` on int/float goes through `pengu_string_new`; interpolation
#    goes through `pengu_string_format_ex`.  Both own their buffers, so the
#    explicit bans must release them (and the program must still run cleanly).
OWNED_BANISH = (
    'weave main into int:\n'
    '  var a as string is (123 to string)\n'
    '  var b as string is (4.5 to string)\n'
    '  var c as string is "n={a} f={b}"\n'
    '  defer banish a\n'
    '  defer banish b\n'
    '  defer banish c\n'
    '  calling print with c\n'
    '  return 0\n'
)

# 5. Banishing the same non-owned view twice: the first call must not free the
#    literal and the second must be a harmless no-op.
DOUBLE_BANISH = (
    'weave main into int:\n'
    '  var s is "hello"\n'
    '  banish s\n'
    '  banish s\n'
    '  return 0\n'
)

# Double banish on an owned buffer: the first `defer` frees it, the explicit
# `banish` afterwards must see `is_owned == 0` and do nothing.
DOUBLE_BANISH_OWNED = (
    'weave main into int:\n'
    '  var s as string is (7 to string)\n'
    '  defer banish s\n'
    '  banish s\n'
    '  return 0\n'
)


# ---------------------------------------------------------------------------
# 1-3. Non-owned views must not be freed
# ---------------------------------------------------------------------------

@requires_cc
@requires_runtime
def test_banish_string_literal_does_not_crash():
    """Banishing a string literal (static `.rodata` view) is a safe no-op."""
    res = compile_run(LITERAL_BANISH, tag="own_literal")
    assert res.returncode == 0, res.stderr


@requires_cc
@requires_runtime
def test_banish_static_cstr_view_does_not_crash():
    """Banishing a `const` string view (`from_cstr`) is a safe no-op."""
    res = compile_run(CONST_VIEW_BANISH, tag="own_const_view")
    assert res.returncode == 0, res.stderr


@requires_cc
@requires_runtime
def test_banish_bool_to_string_does_not_crash():
    """Banishing a `bool to string` view (`from_bool` rodata) is a safe no-op."""
    res = compile_run(BOOL_BANISH, tag="own_bool")
    assert res.returncode == 0, res.stderr
    assert "true" in res.stdout


# ---------------------------------------------------------------------------
# 4. Owned results must be released
# ---------------------------------------------------------------------------

@requires_cc
@requires_runtime
def test_banish_owned_new_and_format_results_runs_clean():
    """`new` (int/float -> string) and format results survive an explicit ban."""
    res = compile_run(OWNED_BANISH, tag="own_owned")
    assert res.returncode == 0, res.stderr
    assert "n=123 f=4.5" in res.stdout


@requires_cc
@requires_runtime
@requires_leakcheck
def test_owned_results_are_actually_released(tmp_path: Path):
    """Run the owned-string program under the leak interposer: no leaks."""
    from tests.test_string_composition_suite import _build_leakcheck, _compile_program

    program = tmp_path / "owned_strings.pengu"
    program.write_text(OWNED_BANISH, encoding="utf-8")
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
        f"owned string buffers were not released (exit {res.returncode}):\n"
        f"{res.stderr}\n{res.stdout}"
    )
    assert "n=123 f=4.5" in res.stdout


# ---------------------------------------------------------------------------
# 5. Double banish is idempotent
# ---------------------------------------------------------------------------

@requires_cc
@requires_runtime
def test_double_banish_non_owned_does_not_crash():
    """Banishing a literal twice must not free static memory."""
    res = compile_run(DOUBLE_BANISH, tag="own_double_lit")
    assert res.returncode == 0, res.stderr


@requires_cc
@requires_runtime
def test_double_banish_owned_does_not_crash():
    """Banishing an owned buffer twice must not double-free."""
    res = compile_run(DOUBLE_BANISH_OWNED, tag="own_double_owned")
    assert res.returncode == 0, res.stderr
