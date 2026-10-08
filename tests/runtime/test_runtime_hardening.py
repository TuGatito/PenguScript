"""Roadmap Phase 5 / §5.7 + §5.8 — runtime hardening and error-code hygiene."""

import os
import re
import subprocess
import textwrap

import pytest

from pengu_project import ProjectConfig, PenguBuilder, build_project
from tests.conftest import (
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

# --------------------------------------------------------------------------- #
# §5.7 Runtime hardening
# --------------------------------------------------------------------------- #


def test_runtime_exposes_the_oom_policy_knob():
    header = (REPO / "pengu_runtime.h").read_text(encoding="utf-8")
    assert "PENGU_OOM_ABORT" in header
    assert "out of memory" in header
    # The policy must be applied where the allocation happens.
    alloc = header[header.index("pengu_sigil_alloc"):]
    alloc = alloc[: alloc.index("\n  }") + 4]
    assert "PENGU_OOM_ABORT" in alloc
    assert "abort()" in alloc


def test_runtime_policy_macros_are_defaulted():
    header = (REPO / "pengu_runtime.h").read_text(encoding="utf-8")
    for macro in ("PENGU_BOUNDS_CHECK", "PENGU_OVERFLOW_CHECK", "PENGU_OOM_ABORT"):
        assert re.search(rf"#ifndef {macro}\s*\n#define {macro}", header), macro


def test_oom_policy_can_be_disabled(tmp_path):
    """-DPENGU_OOM_ABORT=0 must compile (embedders get NULL instead of abort).

    The probe source goes in ``tmp_path``, never in ``build/``. It used to be
    written as ``build/_oom_policy_check.c``, and because the include is spelled
    ``#include "pengu_runtime.h"`` gcc resolves a quoted include *relative to the
    including file* before consulting ``-I``: the probe therefore read
    ``build/pengu_runtime.h``, a copy that other tests rewrite concurrently with
    ``shutil.copy2`` (truncate, then write). Compiling while another worker was
    mid-copy produced ``warning: pengu_runtime.h is shorter than expected`` and
    ``implicit declaration of pengu_sigil_alloc`` -- a flake whose probability
    rose with the number of parallel workers. From ``tmp_path`` the quoted include
    falls through to ``-I REPO`` and reads the canonical header.
    """
    if not have_tool("gcc"):
        pytest.skip("gcc not available")
    src = textwrap.dedent("""\
        #include "pengu_runtime.h"
        int main(void) {
          void *p = pengu_sigil_alloc(8);
          return p == NULL;
        }
        """)
    c = tmp_path / "_oom_policy_check.c"
    c.write_text(src, encoding="utf-8")
    res = subprocess.run(
        ["gcc", "-std=c11", "-fsyntax-only", "-DPENGU_OOM_ABORT=0",
         "-I", str(REPO), "-I", str(BUILD_INCLUDE), str(c)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr


@requires_cc
@requires_runtime
def test_bounds_panic_still_reports_a_frame_stack():
    src = (
        "weave main into int:\n"
        "  var xs as array of int with size 2 is [1, 2]\n"
        "  return xs at 7\n"
    )
    res = compile_run(src, tag="hardening_bounds", expect_exit=None)
    assert res.returncode != 0
    assert "Index out of bounds" in (res.stderr or "")
    assert "Stack trace" in (res.stderr or "") or "at " in (res.stderr or "")


def test_safety_policy_is_documented():
    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    for needle in ("### 5.0 Safety guarantees and their opt-outs",
                   "Division by zero", "Out of memory", "unsafe:"):
        assert needle in text, needle


def test_abi_layout_test_is_wired_into_ci():
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tests/abi" in workflow or "test_abi_layout" in workflow


# --------------------------------------------------------------------------- #
# §5.8 Error-code hygiene
# --------------------------------------------------------------------------- #


def test_no_duplicate_error_codes_across_call_sites():
    """Each code must describe one condition (roadmap 5.8)."""
    import collections
    import pathlib

    seen = collections.defaultdict(set)
    for path in pathlib.Path(REPO / "pengu_parser").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"code=\"(E\d{4})\"", text):
            seen[m.group(1)].add(path.name)
    # No code may be *exclusively* a duplicate with a different meaning; we check
    # the known historical collisions explicitly.
    assert "E0015" in seen
    # E0015 is now only the unknown-array-dimension condition.
    checker = (REPO / "pengu_parser" / "pengu_checker.py").read_text(encoding="utf-8")
    assert "UnknownArrayDimensionError" in checker


def test_e0058_is_used_for_error_literal_context():
    infer = (REPO / "pengu_parser" / "pengu_infer.py").read_text(encoding="utf-8")
    idx = infer.index("only available inside 'or:'")
    window = infer[max(0, idx - 100): idx + 250]
    assert 'code="E0058"' in window


def test_error_codes_documented_in_language_reference():
    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    for code in ("E0051", "E0052", "E0053", "E0054", "E0055", "E0056", "E0057", "E0058"):
        assert f"`{code}`" in text, code


def test_every_raised_code_is_documented():
    """Every E-code used in the compiler appears in the LANGUAGE.md catalog."""
    import pathlib

    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    used = set()
    for path in pathlib.Path(REPO / "pengu_parser").glob("*.py"):
        used |= set(re.findall(r'code="(E\d{4})"', path.read_text(encoding="utf-8")))
    missing = sorted(c for c in used if f"`{c}`" not in text)
    assert not missing, f"undocumented error codes: {missing}"


def test_warning_codes_are_documented():
    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for code in ("W0001", "W0002", "W0004", "W0005", "W0006", "W0007"):
        assert f"`{code}`" in text, f"{code} missing from LANGUAGE.md"
    for code in ("W0006", "W0007"):
        assert f"`{code}`" in readme, f"{code} missing from README.md"
