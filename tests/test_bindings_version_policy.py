"""Roadmap Phase 6 / item 6.8 — generated bindings must NOT carry ``<MOD>_VERSION``.

The roadmap asked to "add ``<MOD>_VERSION`` to the 19 bindings that lack it" so
that "25/25 bindings have the constant", with ``tests/test_std_versioning.py``
verifying it.  Measurement refutes the premise on three independent grounds:

1. The versioning test already scopes itself to *hand-written* modules
   (``_hand_written_modules()`` filters out ``*.d.pengu``) because a generated
   binding mirrors an upstream C API: its ``_VERSION`` constants are the
   **upstream library's** version, not the toolchain's.
   ``SQLITE_VERSION = "3.53.4"``, ``SQLITE_VERSION_NUMBER = 3053004``,
   ``RAYLIB_VERSION = "6.0"`` — adding a toolchain-tracking ``SQLITE_VERSION``
   would have to *overwrite* the upstream value.

2. Two bindings would collide outright: ``RAYLIB_VERSION`` and
   ``RAYGUI_VERSION`` already exist and are the raylib/raygui release numbers.

3. The 4.9 policy (``the stdlib is coupled to the compiler in 1.x``) requires
   every ``<MOD>_VERSION`` to equal ``VERSION``.  A binding cannot satisfy that
   while still faithfully mirroring its header, so the two requirements are
   mutually exclusive by construction.

So the correct action is **N/A, nothing to do**: the "25/25" target contradicts
the policy that 4.9 established, and the exclusion is deliberate.  This test
pins that reasoning so a future change does not silently start demanding
toolchain versions inside generated files.
"""

import re
from pathlib import Path

import pytest

from pengu_version import __version__ as PENGU_VERSION
from tests.conftest import REPO

STD = REPO / "std"
VERSION_RE = re.compile(r'^const\s+(\w+_VERSION)\s+as\s+string\s+is\s+"([^"]*)"', re.M)


def _bindings():
    return sorted(STD.glob("*.d.pengu"))


def test_bindings_exist_and_are_the_generated_half():
    bindings = _bindings()
    assert bindings, "no generated bindings found"
    hand_written = sorted(p for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu"))
    assert hand_written, "no hand-written modules found"
    # The two sets must not overlap.
    assert not ({p.name for p in bindings} & {p.name for p in hand_written})


def test_versioning_policy_excludes_generated_bindings():
    """The ratchet must keep ignoring ``*.d.pengu``; that is the policy."""
    import tests.test_std_versioning as tv

    scoped = {p.name for p in tv._hand_written_modules()}
    assert not any(name.endswith(".d.pengu") for name in scoped), (
        "test_std_versioning started including generated bindings; bindings "
        "track upstream versions and cannot also track the toolchain"
    )


def test_upstream_binding_versions_are_not_overwritten_by_toolchain_versions():
    """No ``_VERSION`` string constant in a binding may become the toolchain version.

    This is the general guard for the trap: ``RAYLIB_VERSION`` is the raylib
    release, ``SQLITE_VERSION`` the sqlite release, and so on -- none of them is
    the PenguScript ``VERSION``.  Adding a toolchain-tracking constant into a
    generated binding is what this rejects.
    """
    checked = 0
    for path in _bindings():
        for name, value in VERSION_RE.findall(path.read_text(encoding="utf-8")):
            # Skip constants that merely *contain* VERSION as a suffix of a
            # longer upstream name (e.g. SQLITE_VERSION_NUMBER is an integer and
            # is not matched by VERSION_RE anyway).
            assert value != PENGU_VERSION, (
                f"{path.name}: {name} = {value!r} equals the toolchain VERSION; "
                f"binding constants must stay upstream library versions"
            )
            checked += 1
    assert checked == 3, (
        "expected exactly 3 upstream *_VERSION string constants in bindings "
        f"(RAYLIB_VERSION, RAYGUI_VERSION, SQLITE_VERSION); found {checked}"
    )


def test_no_binding_has_a_second_conflicting_module_version():
    """Adding ``<MOD>_VERSION`` where the upstream already defines one collides."""
    collisions = []
    for path in _bindings():
        stem = path.name[: -len(".d.pengu")].upper()
        occurrences = [
            (name, value)
            for name, value in VERSION_RE.findall(path.read_text(encoding="utf-8"))
            if name == f"{stem}_VERSION"
        ]
        if len(occurrences) > 1:
            collisions.append(f"{path.name}: {occurrences}")
    assert not collisions, "duplicate module version constants:\n  " + "\n  ".join(collisions)
