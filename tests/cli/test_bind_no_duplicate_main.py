"""Phase 4 item 4.13: `pengu_bind.py` no longer carries a duplicate CLI.

`pengu_bind.py` had a `main()` with a full argparse parser copied from
`pengu_project.py`'s `bind` subcommand, reachable only by running the module as
a script — which nothing does (the CLI imports `generate_bind_file` directly).
Two copies of the same contract drift apart; the library function is the API.
"""

import ast
import importlib
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]
BIND_SOURCE = REPO / "pengu_bind.py"


def test_module_has_no_main_and_no_script_guard():
    src = BIND_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    functions = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "main" not in functions, functions

    # No `if __name__ == "__main__":` block either: the module is a library.
    guards = [
        n for n in tree.body
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name)
        and n.test.left.id == "__name__"
    ]
    assert not guards, "the script entry point should be gone"


def test_module_is_still_importable_without_main():
    module = importlib.import_module("pengu_bind")
    assert callable(module.generate_bind_file)
    assert not hasattr(module, "main")


def test_pengu_bind_subcommand_still_works(tmp_path):
    header = tmp_path / "bird.h"
    header.write_text("typedef struct Bird { int wings; } Bird;\n"
                      "int bird_fly(Bird *b);\n", encoding="utf-8")
    out = tmp_path / "bird.d.pengu"
    res = subprocess.run(
        [*PENGU, "bind", str(header), "--output", str(out)],
        capture_output=True, text=True, timeout=180,
        env=dict(os.environ, NO_COLOR="1"),
    )
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    assert "rune Bird:" in text and "wings as int" in text
    assert "bird_fly" in text


def test_regen_tool_still_imports_the_library_api():
    """`regen_std_bindings.py` depends on the API, not the removed CLI."""
    src = (REPO / "regen_std_bindings.py").read_text(encoding="utf-8")
    assert "from pengu_bind import generate_bind_file" in src
