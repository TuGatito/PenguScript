"""The VS Code extension must find `pengu` without the GUI session's `PATH`.

A VS Code started from the desktop does not inherit the `PATH` a login shell
builds — on Linux the session's own `PATH` comes from systemd, so a `pengu`
exported from `~/.bashrc` is invisible to the editor. The extension used to spawn
a bare `pengu` and die with `spawn pengu ENOENT`, with nothing in the UI saying
what was missing or where it had looked.

`vscode-extension/src/penguPath.ts` now resolves the executable in a documented
order (setting → `$PENGU_BIN_PATH` → `PATH` → the usual release locations) and
`extension.ts` turns "not found" into an actionable message. That module is
deliberately free of the `vscode` API and takes every input — and even the
`isFile` predicate — as an option, so it runs under plain Node against a
synthetic filesystem.

The checks live in ``vscode-extension/test/pengu_path_check.js`` and this test
only drives them. It skips when Node or the extension's ``node_modules`` is
absent (a fresh checkout that never ran ``npm install``, which is also what
``make_release.py`` does before packaging the ``.vsix``).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = ROOT / "vscode-extension"
#: The driver that holds the expectations (see its own docstring).
DRIVER = EXT_DIR / "test" / "pengu_path_check.js"
#: Invoked through Node so the same command works on Windows (``tsc.cmd``).
TSC = EXT_DIR / "node_modules" / "typescript" / "bin" / "tsc"
MODULE = EXT_DIR / "src" / "penguPath.ts"

pytestmark = pytest.mark.smoke


def test_the_extension_locates_pengu_without_the_shell_path(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not on PATH")
    if not TSC.is_file():
        pytest.skip("vscode-extension/node_modules is not installed")
    if not MODULE.is_file() or not DRIVER.is_file():
        pytest.skip("the extension's path resolver is not in this checkout")

    build = tmp_path / "pengupath"
    compile_proc = subprocess.run(
        [
            node, str(TSC), str(MODULE),
            "--outDir", str(build),
            "--module", "commonjs",
            "--target", "ES2020",
            "--lib", "ES2020",
            "--strict",
        ],
        cwd=str(EXT_DIR), capture_output=True, text=True, timeout=300,
    )
    assert compile_proc.returncode == 0, compile_proc.stdout + compile_proc.stderr

    check_proc = subprocess.run(
        [node, str(DRIVER), str(build)],
        cwd=str(EXT_DIR), capture_output=True, text=True, timeout=120,
    )
    assert check_proc.returncode == 0, check_proc.stdout + check_proc.stderr
    assert "ALL OK" in check_proc.stdout
