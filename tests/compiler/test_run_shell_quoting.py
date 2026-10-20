"""Regression: a shell line that starts with a quoted program must run.

``rites.shell_escape`` always quotes its argument, so the canonical
``build.pengu`` emits ``"<cc>" -c ... -o ...``.  On Windows ``system()`` runs
``cmd.exe /c``, whose legacy quote handling strips the first and last quote
when the line begins with one and contains more than two quotes.  The command
therefore arrived at cmd.exe as ``C:\\...\\gcc.exe" -c ...`` and
``pengu add --trust`` silently skipped the native build, leaving
``lib/lib<name>.a`` absent (the Windows release failure).

``pengu_c_exec`` now wraps such a line in one extra pair of quotes before
calling ``system()``.  This test exercises the same path through the CLI: the
program asks ``rites.run_shell`` to run a quoted interpreter and the child's
exit status has to survive.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from .conftest import BUILD_LIB


@pytest.mark.slow
def test_run_shell_starts_with_a_quoted_program(pengu_cli, pengu_root, tmp_path: Path) -> None:
    if not (BUILD_LIB / "libpengu_runtime.a").is_file():
        pytest.skip("runtime archive not built in this environment")

    # `as_posix()` keeps the path free of backslash escapes in the PenguScript
    # string literal; Windows accepts forward slashes.  A space in the path is
    # the case that *needs* quoting, and `shell_escape` quotes unconditionally
    # today, so the bug reproduces with any path.
    python_path = Path(sys.executable).as_posix()
    marker = tmp_path / "quoted_shell_ran.txt"
    code = (
        "import pathlib; "
        f"pathlib.Path('{marker.name}').write_text('ok', encoding='utf-8')"
    )
    script = tmp_path / "quoted_shell.pengu"
    script.write_text(
        f"""import std.rites

weave main into int:
    let py as string is "{python_path}"
    let py_q as string is calling rites.shell_escape with py
    let code_q as string is calling rites.shell_escape with "{code}"
    let cmd as string is "{{py_q}} -c {{code_q}}"
    return calling rites.run_shell with cmd
""",
        encoding="utf-8",
    )

    result = pengu_cli("run", str(script), cwd=tmp_path)
    # `run_shell` returns the raw `system()` status, so the portable assertion
    # is the side effect, not the child's exit code.
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_text(encoding="utf-8") == "ok"
