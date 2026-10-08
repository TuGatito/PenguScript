"""Phase 4 item 4.10 (A3): `--target-compiler` must match the real compiler.

The help promised ``default: infer from --cc`` but the code generator fell back
to ``"gcc"`` unconditionally, so ``pengu build --target-compiler msvc`` with the
default gcc emitted ``__forceinline`` and died inside the C compiler:

    error: expected '=', ',', ';', 'asm' or '__attribute__' before 'fast'
    error: nombre de tipo '__forceinline' desconocido

Nothing told the user that the two flags disagreed. They are now validated
before any C is compiled, and an omitted ``--target-compiler`` is inferred from
``--cc`` (which is what the help has always claimed).
"""

import json
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

SOURCE = (
    "@inline\n"
    "weave fast with x as int into int:\n"
    "    return x + 1\n"
    "\n"
    "weave main into int:\n"
    "    return calling fast with 1\n"
)


def _run(args, cwd=None):
    env = dict(os.environ, NO_COLOR="1")
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300,
        cwd=str(cwd) if cwd else None, env=env,
    )


@pytest.fixture()
def project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    p = tmp_path / "ok"
    (p / "src" / "main.pengu").write_text(SOURCE, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# The mismatch is rejected, with an actionable message
# ---------------------------------------------------------------------------


@requires_cc
@requires_runtime
def test_msvc_dialect_with_gcc_is_rejected(project):
    res = _run(["build", "--target-compiler", "msvc", "--cc", "gcc",
                "--output", "build/out"], cwd=project)
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert "does not match the C compiler" in combined, combined
    assert "msvc" in combined and "gcc" in combined
    # The confusing compiler error must not be what the user sees.
    assert "__forceinline" not in combined, combined
    assert "unknown type name" not in combined, combined


@requires_cc
@requires_runtime
def test_mismatch_is_reported_as_json_when_asked(project):
    res = _run(["build", "--json", "--target-compiler", "msvc", "--cc", "gcc"],
               cwd=project)
    assert res.returncode != 0
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    objects = [json.loads(ln) for ln in lines]
    assert objects[0]["type"] == "diagnostic"
    assert "does not match the C compiler" in objects[0]["message"]
    assert objects[-1] == {"type": "summary", "ok": False, "errors": 1, "warnings": 0}


# ---------------------------------------------------------------------------
# Coherent pairs keep building
# ---------------------------------------------------------------------------


@requires_cc
@requires_runtime
def test_matching_dialect_builds(project):
    res = _run(["build", "--target-compiler", "gcc", "--cc", "gcc"], cwd=project)
    assert res.returncode == 0, res.stderr


@requires_cc
@requires_runtime
def test_target_compiler_is_inferred_from_cc(project):
    """Omitting the flag must not produce a spurious mismatch."""
    res = _run(["build", "--cc", "gcc"], cwd=project)
    assert res.returncode == 0, res.stderr


def test_inference_and_validation_unit():
    from pengu_project import _compiler_dialect, _validate_target_compiler

    assert _compiler_dialect("gcc") == "gcc"
    assert _compiler_dialect("/usr/bin/gcc-13") == "gcc"
    assert _compiler_dialect("clang") == "clang"
    assert _compiler_dialect("clang-cl") == "msvc"
    assert _compiler_dialect("cl") == "msvc"
    assert _compiler_dialect("cl.exe") == "msvc"
    assert _compiler_dialect("tcc") == "tcc"
    assert _compiler_dialect("cc") == "gcc"

    # coherent
    assert _validate_target_compiler("gcc", "gcc") is None
    assert _validate_target_compiler("gcc", "") is None
    assert _validate_target_compiler("cl", "msvc") is None
    assert _validate_target_compiler("clang", "clang") is None
    assert _validate_target_compiler("clang", "gcc") is None      # clang takes GNU attrs
    assert _validate_target_compiler("tcc", "tcc") is None

    # mismatched
    assert _validate_target_compiler("gcc", "msvc") is not None
    assert _validate_target_compiler("cl", "gcc") is not None
    assert _validate_target_compiler("tcc", "msvc") is not None
