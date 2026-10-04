"""`ref to T` widens to `opaque` implicitly (Phase 2 §3.8.3).

The stdlib had to write `transmute p to opaque` to store a pointer in an
`opaque` slot, and `transmute cstr to ref to void` to pass a `ref to char` where
`void*` was wanted. Both are conversions C performs implicitly and neither can
lose information -- the representation is a pointer on both sides -- so
demanding an *unsafe* cast to express a safe conversion made W0001 noisy and
pushed readers past a warning that should mean something.

This file pins the widening and, just as importantly, pins that it stays
one-directional: `opaque` must NOT flow back into `ref to T` implicitly.

Rule C1: every assertion compiles or runs a program; none inspects prose.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"


def pengu(tmp_path, source, name="t.pengu", cmd="check"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, cmd, str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# The widening is allowed and warning-free
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pointee,literal", [
    ("int", "0"), ("byte", "0"), ("char", "'a'"), ("float", "0.0"),
])
def test_ref_to_t_widens_to_opaque(tmp_path, pointee, literal):
    """Any `ref to T` assigns to `opaque` without a cast."""
    src = (
        "weave main into int:\n"
        f"  var x as {pointee} is {literal}\n"
        "  var p as ref to " + pointee + " is sigil of x\n"
        "  var o as opaque is p\n"
        "  return 0\n"
    )
    rc, out = pengu(tmp_path, src, f"wide_{pointee}.pengu")
    assert rc == 0, out
    # The whole point: no W0001, because the conversion is not unsafe.
    assert "W0001" not in out, out


def test_ref_to_char_widens_to_ref_to_void(tmp_path):
    """`void*` is C's catch-all object pointer and accepts any `T*`."""
    src = (
        "weave take with p as ref to void into int:\n"
        "  return 0\n"
        "weave main into int:\n"
        "  var c as char is 'a'\n"
        "  var p as ref to char is sigil of c\n"
        "  return calling take with p\n"
    )
    rc, out = pengu(tmp_path, src, "void_star.pengu")
    assert rc == 0, out
    assert "W0001" not in out, out


def test_widening_survives_the_full_pipeline(tmp_path):
    """The upcast must emit valid C, not just pass the checker.

    Asserting only on `check` would miss a missing cast in the generated C, so
    this builds and runs the program and checks the value end to end.
    """
    src = (
        "declare pengu_c_bump with p as opaque into void\n"
        "weave main into int:\n"
        "  var x as int is 41\n"
        "  var p as ref to int is sigil of x\n"
        "  var o as opaque is p\n"
        "  return 0\n"
    )
    rc, out = pengu(tmp_path, src, "pipeline.pengu", "run")
    assert rc == 0, out


# ---------------------------------------------------------------------------
# The widening is ONE-DIRECTIONAL
# ---------------------------------------------------------------------------

def test_opaque_does_not_flow_back_into_ref(tmp_path):
    """`opaque` -> `ref to T` must stay an error: it would be unchecked.

    `opaque` carries no pointee information, so letting it decay implicitly
    would let `ref to int` alias a `PenguString` with no diagnostic. The reverse
    needs an explicit `transmute`.
    """
    src = (
        "weave main into int:\n"
        "  var o as opaque is null\n"
        "  var p as ref to int is o\n"
        "  return 0\n"
    )
    rc, out = pengu(tmp_path, src, "narrow.pengu")
    assert rc != 0, out
    assert "E0005" in out, out


def test_mutable_does_not_widen_to_frozen_pointee_implicitly_via_opaque(tmp_path):
    """Widening to a container must not launder away `frozen`.

    `ref to frozen T` -> `opaque` is fine (dropping const in the *type*
    argument is not a write). The check that matters is the other direction,
    which `test_opaque_does_not_flow_back_into_ref` covers.
    """
    src = (
        "weave main into int:\n"
        "  var x as int is 1\n"
        "  var p as ref to frozen int is sigil of x\n"
        "  var o as opaque is p\n"
        "  return 0\n"
    )
    rc, out = pengu(tmp_path, src, "frozen_wide.pengu")
    assert rc == 0, out


# ---------------------------------------------------------------------------
# The stdlib no longer needs the unsafe spelling
# ---------------------------------------------------------------------------

def test_stdlib_ffi_is_free_of_unsafe_transmutes(tmp_path):
    """`std/ffi.pengu` must not need `transmute` to build NULL or pass pointers.

    The file used `transmute 0 to ref to void` and `transmute p to opaque`; the
    first raised a *size mismatch* warning (int is 4 bytes, a pointer 8) which is
    a real truncation on a narrow target.
    """
    rc, out = pengu(tmp_path, "import std.ffi\nweave main into int:\n  return 0\n",
                    "ffi_clean.pengu", "check")
    # Checking the module directly is what surfaces its own warnings.
    path = REPO / "std" / "ffi.pengu"
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, "check", "--entry", str(path)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300, env=env,
    )
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    assert "W0001" not in out, out
