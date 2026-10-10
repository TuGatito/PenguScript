"""`antiquus` — code generation, DCE and the exported-symbol contract.

Two things here cannot be observed by running a single program and therefore do
not belong in ``tests/conformance/``:

* dead-code elimination of an unused ``antiquus`` declared in a ``lib/`` module
  (the program runs either way; only the emitted translation unit differs);
* ``@export("symbol")``, which is an *ABI* promise: the symbol has to be in the
  object file even when no PenguScript code calls it.

Both are measured, not snapshotted: the first asks the real ``pengu expand`` for
the bundle and looks for one identifier, the second builds the program and reads
``nm``.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from tests.conftest import (
    REPO,
    gen_bundle,
    have_tool,
    nm_symbol_name,
    nm_symbol_regex,
    requires_cc,
    requires_runtime,
)

# --------------------------------------------------------------------------
# DCE: `pengu expand` on a throw-away project with a `lib/` vendor module
# --------------------------------------------------------------------------

UNUSED_VENDOR = '''antiquus vendor_never_called into int:
    """
    return 7;
    """

antiquus vendor_always_called into int:
    """
    return 8;
    """
'''

MAIN_WITHOUT_CALL = '''import vendor

weave main into int:
    return 0
'''

MAIN_WITH_CALL = '''import vendor

weave main into int:
    return calling vendor_always_called
'''


def _expand(project, script):
    """Runs ``pengu expand`` with `project` as the project root."""
    env = dict(os.environ)
    env.pop("PENGU_NO_DCE", None)
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "expand", str(script)],
        cwd=str(project), capture_output=True, text=True, timeout=300, env=env,
    )


@pytest.fixture()
def vendor_project(tmp_path):
    """A throw-away project with a prunable ``lib/vendor/pengu/vendor.pengu``."""
    root = tmp_path / "proj"
    (root / "lib" / "vendor" / "pengu").mkdir(parents=True)
    (root / "lib" / "vendor" / "pengu" / "vendor.pengu").write_text(UNUSED_VENDOR, encoding="utf-8")
    return root


def test_unused_antiquus_in_a_lib_module_is_pruned(vendor_project):
    script = vendor_project / "main.pengu"
    script.write_text(MAIN_WITHOUT_CALL, encoding="utf-8")
    res = _expand(vendor_project, script)
    assert res.returncode == 0, res.stderr
    assert "vendor_always_called" not in res.stdout
    assert "vendor_never_called" not in res.stdout


def test_referenced_antiquus_survives(vendor_project):
    script = vendor_project / "used.pengu"
    script.write_text(MAIN_WITH_CALL, encoding="utf-8")
    res = _expand(vendor_project, script)
    assert res.returncode == 0, res.stderr
    assert "vendor_always_called" in res.stdout
    assert "vendor_never_called" not in res.stdout


# --------------------------------------------------------------------------
# @export: the C symbol must be in the object file even when nothing calls it
# --------------------------------------------------------------------------

EXPORTED = '''@export("pengu_antiquus_triple")
antiquus antiquus_triple with x as int into int:
    """
    return x * 3;
    """

weave main into int:
    return 0
'''


@requires_cc
@requires_runtime
def test_exported_antiquus_emits_its_c_symbol(compile_c):
    """`@export` is a root for DCE *and* the name the linker sees.

    Nothing calls `antiquus_triple`, so without the attribute DCE would drop it
    from a module it considers prunable; the program still runs, which is why
    this is measured with `nm` and not with stdout.
    """
    c_text = gen_bundle(EXPORTED, filename="exported.pengu")
    exe = compile_c(c_text, name="antiquus_export")

    listing = subprocess.run(["nm", str(exe)], capture_output=True, text=True, timeout=120)
    assert listing.returncode == 0, listing.stderr
    symbols = {nm_symbol_name(line.split()[-1]) for line in listing.stdout.splitlines() if line.split()}
    assert "pengu_antiquus_triple" in symbols, (
        f"the @export symbol is missing from the binary; nm reported {sorted(symbols)[:20]}"
    )
    assert re.search(nm_symbol_regex("pengu_antiquus_triple"), listing.stdout)


# --------------------------------------------------------------------------
# C diagnostics inside the body point at the antiquus, not at the bundle
# --------------------------------------------------------------------------

BROKEN_BODY = '''antiquus antiquus_broken with x as int into int:
    """
    return x
    """

weave main into int:
    return calling antiquus_broken with 1
'''


@requires_cc
def test_c_error_names_the_antiquus_and_body_line(tmp_path):
    c_text = gen_bundle(BROKEN_BODY, filename="broken.pengu")
    src = tmp_path / "broken.c"
    src.write_text(c_text, encoding="utf-8")
    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    res = subprocess.run(
        [cc, "-fsyntax-only", "-std=c11", str(src), f"-I{REPO}"],
        capture_output=True, text=True, timeout=300,
    )
    assert res.returncode != 0, "the deliberately broken C body compiled cleanly"
    combined = res.stderr + res.stdout
    # `#line 1 "antiquus:antiquus_broken"` makes the compiler blame the antiquus
    # and count lines from 1 inside the body: the one-line body is line 1.
    assert re.search(r"antiquus:antiquus_broken:1", combined), combined
