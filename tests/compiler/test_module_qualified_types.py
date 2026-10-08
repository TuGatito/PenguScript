"""Phase 1 — module-qualified type resolution and cross-module diagnostics.

Rule C1 (ROADMAP_2.0 Anexo C): these tests run the real compiler and assert on
structured results (exit codes and ``Exxxx`` codes), never on prose.

Two blockers live here:

* **B6** — `_resolve_call_target()` referenced an undefined ``node``, so
  accessing a private symbol of another module raised ``NameError`` instead of
  the documented ``E0043``. A compiler must not crash on user error.
* **B7** — a type re-exported through a module (`dep.Vec`, declared in `lib`)
  resolved to a ``RuneType`` with empty ``fields``, so
  ``var v as dep.Vec is with x is 1.0`` was rejected with ``E0013`` and the note
  ``Rune 'dep.Vec' fields are: .``. That breaks the C binding chain, where 25
  stdlib modules declare types owned by their upstream module.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"


def cli(args, cwd=None, timeout=300):
    """Runs the real CLI; PYTHONPATH makes the repo module importable anywhere."""
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    return subprocess.run(
        [PY, "-m", MODULE] + list(args),
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _write(root: Path, name: str, body: str) -> Path:
    p = root / name
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# B6 — private symbol access must be E0043, not a Python NameError (item 1.4)
# ---------------------------------------------------------------------------

def test_private_symbol_access_raises_E0043(tmp_path):
    """Regression for B6: this used to raise NameError('node' is not defined)."""
    _write(tmp_path, "lib.pengu", "weave _secret into int:\n  return 1\n")
    entry = _write(tmp_path, "main.pengu",
                   "import lib\nweave main into int:\n  return calling lib._secret\n")
    r = cli(["check", str(entry)], cwd=tmp_path)
    combined = r.stdout + r.stderr
    assert "E0043" in combined, combined
    assert "Traceback (most recent call last)" not in combined, combined
    assert "NameError" not in combined, combined
    assert r.returncode == 1


def test_public_symbol_access_still_works(tmp_path):
    """The E0043 guard must not reject genuinely public symbols."""
    _write(tmp_path, "lib.pengu",
           "weave _secret into int:\n  return 1\nweave pub into int:\n  return 2\n")
    entry = _write(tmp_path, "main.pengu",
                   "import lib\nweave main into int:\n  return calling lib.pub\n")
    r = cli(["check", str(entry)], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_python_traceback_on_private_access_anywhere(tmp_path):
    """A span of cross-module access forms must never produce a traceback.

    This is the generalised guard: whatever the diagnostic, the front end must
    stay a compiler and not leak an interpreter exception.
    """
    _write(tmp_path, "lib.pengu",
           "weave _a into int:\n  return 1\n"
           "rune _T:\n  z as int\n")
    programs = [
        "import lib\nweave main into int:\n  return calling lib._a\n",
        "import lib\nweave main into int:\n  var v as lib._T is with z is 1\n  return v.z\n",
        "import lib\nweave main into int:\n  return lib._missing\n",
    ]
    for i, body in enumerate(programs):
        entry = _write(tmp_path, f"p{i}.pengu", body)
        r = cli(["check", str(entry)], cwd=tmp_path)
        combined = r.stdout + r.stderr
        assert "Traceback (most recent call last)" not in combined, (i, combined)


# ---------------------------------------------------------------------------
# B7 — a re-exported type must keep its fields (items 1.5 / 1.6)
# ---------------------------------------------------------------------------

def test_qualified_type_preserves_fields(tmp_path):
    """Regression for B7: `dep.Vec` used to resolve to a field-less RuneType."""
    _write(tmp_path, "lib.pengu", "rune Vec:\n    x as f32\n    y as f32\n")
    _write(tmp_path, "dep.pengu",
           "import lib\ndeclare vadd with a as Vec, b as Vec into Vec\n")
    entry = _write(
        tmp_path, "main.pengu",
        "import dep\n"
        "weave main into int:\n"
        "    var v as dep.Vec is with x is 1.0, y is 2.0\n"
        "    return (v.x to int)\n",
    )
    r = cli(["check", str(entry)], cwd=tmp_path)
    combined = r.stdout + r.stderr
    assert "E0013" not in combined, combined
    assert r.returncode == 0, combined


def test_unqualified_type_still_preserves_fields(tmp_path):
    """The unqualified spelling must keep working (it already did)."""
    _write(tmp_path, "lib.pengu", "rune Vec:\n    x as f32\n    y as f32\n")
    _write(tmp_path, "dep.pengu",
           "import lib\ndeclare vadd with a as Vec, b as Vec into Vec\n")
    entry = _write(
        tmp_path, "main.pengu",
        "import dep\n"
        "weave main into int:\n"
        "    var v as Vec is with x is 1.0, y is 2.0\n"
        "    return (v.x to int)\n",
    )
    r = cli(["check", str(entry)], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_stdlib_raymath_vector2_fields(tmp_path):
    """The real stdlib case from LANGUAGE.md block 94.

    `std/raymath.d.pengu` declares `Vector2Zero into Vector2` and imports
    `std.raylib`, which owns the `Vector2` rune -- exactly the re-export shape
    that B7 broke.
    """
    entry = _write(
        tmp_path, "main.pengu",
        "import std.raylib\n"
        "import std.raymath\n"
        "weave main into int:\n"
        "    var position as raymath.Vector2 is with x is 400.0, y is 225.0\n"
        "    return (position.x to int)\n",
    )
    r = cli(["check", str(entry)], cwd=tmp_path)
    combined = r.stdout + r.stderr
    assert "E0013" not in combined, combined
    assert "does not exist on Rune" not in combined, combined
    assert r.returncode == 0, combined


def test_empty_fields_note_is_not_an_empty_list(tmp_path):
    """Item 1.10: the E0013 note must never read `fields are: .`.

    If a rune's definition genuinely cannot be reached, saying so is useful;
    printing an empty list only reveals an internal bug.
    """
    entry = _write(
        tmp_path, "main.pengu",
        "rune Empty:\n    pass_through as int\n"
        "weave main into int:\n"
        "    var e as Empty is with nonexistent_field is 1\n"
        "    return 0\n",
    )
    r = cli(["check", str(entry)], cwd=tmp_path)
    combined = r.stdout + r.stderr
    assert "fields are: ." not in combined, combined
