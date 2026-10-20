"""Windows-only ``when os == "windows"`` branches must type-check everywhere.

The host only type-checks the branch it takes, so a Windows-only block can stay
broken until a Windows runner compiles it.  That is how three ``maybe none``
returns in ``std.rites`` (``config_dir``, ``cache_dir``, ``data_dir``) survived
every Linux/macOS run and then failed the Windows ``release`` job with
``[E0014]`` while ``build.pengu`` was importing ``std.rites``.

This test drives the checker with an explicit ``CompileTimeEnv``, the same way
``test_comptime_wasm.py`` drives the wasm branches, so the Windows path is
covered on every host without a Windows toolchain.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_checker import PenguChecker  # noqa: E402
from pengu_parser.pengu_comptime import CompileTimeEnv  # noqa: E402
from pengu_parser.pengu_parser import PenguParser  # noqa: E402


def test_std_rites_windows_branches_type_check() -> None:
    source = (ROOT / "std" / "rites.pengu").read_text(encoding="utf-8")
    ast = PenguParser().parse(source)
    checker = PenguChecker(
        base_dir=str(ROOT),
        compile_env=CompileTimeEnv(os_name="windows", compiler="gcc"),
    )
    checker.check(ast, source=source, filename="std/rites.pengu")
    assert not getattr(checker, "errors", []), [
        getattr(error, "code", "?") for error in checker.errors
    ]
