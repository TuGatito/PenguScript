#!/usr/bin/env python3
"""Regression suite for PenguScript's manual memory management.

PenguScript used to have an implicit ownership model (auto-banish, escape
analysis, a ``borrowed`` modifier).  It does not any more: the compiler never
frees a local for you, never deep-copies on store and never infers a destructor.
This module pins that contract from three angles:

* every ``test_*.pengu`` program under ``tests/test_manual_memory/`` is
  compiled with the real project builder, linked against
  ``libpengu_runtime.a`` and executed, and its exit status is the assertion;
* every ``fail_*.pengu`` program must be rejected with the error code in its
  ``# EXPECTED:`` marker;
* a handful of code-shape assertions prove the *absence* of the removed
  machinery (no scope-exit banish, no element clone on push, no implicit
  destructor, no ``borrowed`` token, runtime ABI 2).
"""
import re
from pathlib import Path

import pytest

from tests.conftest import (
    REPO,
    check_error,
    compile_run,
    gen_bundle,
    requires_cc,
    requires_runtime,
)

MANUAL_DIR = REPO / "tests" / "test_manual_memory"


def _discover(*patterns: str) -> list:
    """Finds programs under ``tests/test_manual_memory`` (sorted, stable ids)."""
    found = []
    for pattern in patterns:
        found.extend(MANUAL_DIR.rglob(pattern))
    return sorted(set(found), key=lambda p: str(p.relative_to(MANUAL_DIR)))


def _test_id(path: Path) -> str:
    return str(path.relative_to(MANUAL_DIR).with_suffix(""))


RUNNABLE = _discover("test_*.pengu")
FAILING = _discover("fail_*.pengu")


def _expected_code(path: Path) -> str:
    match = re.search(r"#\s*EXPECTED:\s*(E\d{4})", path.read_text(encoding="utf-8"))
    assert match, f"{path.name} is missing a '# EXPECTED: EXXXX' marker"
    return match.group(1)


@pytest.mark.parametrize("program", RUNNABLE, ids=_test_id)
@requires_cc
@requires_runtime
def test_manual_memory_program_executes(program: Path):
    """The program compiles, links and exits with status 0."""
    res = compile_run(program.read_text(encoding="utf-8"), tag=program.stem)
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize("program", FAILING, ids=_test_id)
def test_manual_memory_program_reports_expected_error(program: Path):
    """The program is rejected with the documented diagnostic code."""
    check_error(program.read_text(encoding="utf-8"),
                filename=program.name, contains=_expected_code(program))


# --------------------------------------------------------------------------
# Code shape: what the compiler must NOT emit
# --------------------------------------------------------------------------


def test_no_scope_exit_banish_is_generated():
    """An owned local is not released at scope exit; only 'banish' releases it."""
    c = gen_bundle('weave f into void:\n  var s as string is (1 to string)\n  return\n')
    assert "pengu_banish_string(&s)" not in c


def test_banish_is_the_only_release_for_an_explicit_defer():
    """'defer banish s' emits exactly one release, and no scope-exit release."""
    c = gen_bundle(
        'weave f into void:\n  var s as string is (1 to string)\n  defer banish s\n  return\n',
    )
    assert c.count("pengu_banish_string(&s)") == 1


def test_list_push_never_clones_an_element():
    """A container constructor registers no element callback by construction."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var xs as list of string is list of string with capacity 2\n'
        '  calling xs.push with "a"\n'
        '  return\n',
    )
    assert "pengu_list_new_owned" not in c
    assert "pengu_list_new(sizeof(PenguString)" in c


def test_map_put_never_clones_an_element():
    """A map constructor registers no key/value callback either."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var m as map of string to int is map of string to int\n'
        '  calling m.put with "k", 1\n'
        '  return\n',
    )
    assert "pengu_map_new_owned" not in c
    assert "pengu_map_new(sizeof(PenguString), sizeof(int32_t))" in c


def test_no_implicit_nexus_for_a_heap_owning_rune():
    """A rune with a string field gets no destructor unless it derives Nexus."""
    plain = gen_bundle('rune Doc:\n  title as string\nweave f into void:\n  return\n')
    assert "_pengu_cleanup_Doc" not in plain
    assert "Doc_nexus" not in plain

    derived = gen_bundle(
        'rune Doc derive Nexus:\n  title as string\nweave f into void:\n  return\n',
    )
    assert "_pengu_cleanup_Doc" in derived
    assert "Doc_nexus" in derived


def test_no_implicit_imago_for_a_heap_owning_rune():
    """Deep-copy helpers are only generated for an explicit 'derive Imago'."""
    plain = gen_bundle('rune Doc:\n  title as string\nweave f into void:\n  return\n')
    assert "_pengu_clone_Doc" not in plain
    assert "_pengu_auto_clone_Doc" not in plain

    derived = gen_bundle(
        'rune Doc derive Imago:\n  title as string\nweave f into void:\n  return\n',
    )
    assert "_pengu_clone_Doc" in derived


def test_struct_init_does_not_deep_copy_a_string_field():
    """A rune literal stores the string value as written, with no copy."""
    c = gen_bundle(
        'rune Doc:\n  title as string\n'
        'weave f into void:\n  var d as Doc is with title is "spec"\n  return\n',
    )
    assert 'pengu_string_from_cstr("spec")' in c
    assert "pengu_string_copy(pengu_string_from_cstr(\"spec\"))" not in c


def test_some_does_not_clone_its_payload():
    """'some x' boxes the payload bytes; it does not duplicate a heap buffer."""
    c = gen_bundle('weave f into void:\n  var m as maybe string is some "x"\n  return\n')
    assert "memcpy(" in c
    assert "pengu_string_clone" not in c


def test_borrowed_is_not_a_keyword_any_more():
    """'borrowed' no longer lexes as a modifier, so the declaration is a syntax error."""
    check_error(
        "weave main into int:\n  var borrowed x is 1\n  return 0\n",
        contains="E0000",
    )


def test_generated_bundle_requires_runtime_abi_2():
    """The bundle pins the runtime ABI it was generated against."""
    c = gen_bundle('weave main into int:\n  return 0\n')
    assert "_Static_assert(PENGU_ABI_VERSION == 2," in c
