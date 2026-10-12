"""Roadmap Phase 6 / item 6.8 — generated bindings must NOT carry ``<MOD>_VERSION``.

The roadmap asked to "add ``<MOD>_VERSION`` to the 19 bindings that lack it" so
that "25/25 bindings have the constant", with ``tests/stdlib/test_std_versioning.py``
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


def test_no_generated_bindings_remain_in_the_core_tree():
    """Phase 1 moved every C binding to a satellite repository.

    The `.d.pengu` files no longer exist here, so the generated half is empty;
    the hand-written modules are the only thing the versioning ratchet scopes.
    """
    bindings = _bindings()
    assert bindings == [], (
        f"generated bindings came back into std/: {[p.name for p in bindings]}"
    )
    hand_written = sorted(p for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu"))
    assert hand_written, "no hand-written modules found"


def test_versioning_policy_excludes_generated_bindings():
    """The ratchet must keep ignoring ``*.d.pengu``; that is the policy.

    The per-module ``<MOD>_VERSION`` ratchet lives in the migration's own
    ``tests/test_<mod>.py`` files now (it used to be pinned by the deleted
    ``tests/stdlib/test_std_versioning.py``).  This check keeps the policy
    observable: only the hand-written modules are in scope.
    """
    scoped = {
        p.name for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu")
    }
    assert scoped, "no hand-written std modules found"
    assert not any(name.endswith(".d.pengu") for name in scoped), (
        "the versioning scope started including generated bindings; bindings "
        "track upstream versions and cannot also track the toolchain"
    )


def test_upstream_binding_versions_are_not_overwritten_by_toolchain_versions():
    """No ``_VERSION`` string constant in a binding may become the toolchain version.

    This is the general guard for the trap: ``RAYLIB_VERSION`` is the raylib
    release, ``SQLITE_VERSION`` the sqlite release, and so on -- none of them is
    the PenguScript ``VERSION``.  Adding a toolchain-tracking constant into a
    generated binding is what this rejects.

    Phase 1 removed the bindings from the core tree, so there is nothing left to
    check; the loop stays so the guard still runs if a `.d.pengu` ever returns.
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
    assert checked == 0, (
        "a *_VERSION string constant appeared in a binding; the upstream "
        f"constants (RAYLIB_VERSION, RAYGUI_VERSION, SQLITE_VERSION) left with "
        f"the bindings in phase 1, found {checked}"
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
