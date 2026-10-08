#!/usr/bin/env python3
"""Meta-tests: the testing rules in ``AGENT_TESTING.md``, enforced.

A rule that lives only in a document is a rule that gets broken by the first agent
in a hurry. Each check here corresponds to one rule, and each one is written so it
passes on the tree as it is today *and* stops the tree getting worse.

``tests/_test_policy_baseline.json`` is the frozen snapshot these checks compare
against, and ``tools/gen_test_policy_baseline.py`` is the only thing allowed to
change it. That makes every change to the suite's shape a visible, reviewable
diff -- including the deliberate shrinking the migration is aiming at. It is the
same ratchet idiom as ``fail_under`` in ``.coveragerc``.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

TESTS = Path(__file__).resolve().parent
BASELINE_PATH = TESTS / "_test_policy_baseline.json"
CONFORMANCE_DIR = TESTS / "conformance"

pytestmark = pytest.mark.smoke


def _baseline() -> Dict[str, Any]:
    assert BASELINE_PATH.is_file(), (
        "tests/_test_policy_baseline.json is missing; run: "
        "python tools/gen_test_policy_baseline.py"
    )
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen_test_policy_baseline", REPO / "tools" / "gen_test_policy_baseline.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _root_test_files() -> List[str]:
    """Test modules directly under ``tests/``, not in its area packages.

    Non-recursive on purpose: the suite's bulk lives in ``tests/<area>/`` (and in
    ``tests/conformance/``), and the root is meant to stay small enough to read.
    """
    return sorted(p.name for p in TESTS.glob("test_*.py"))


#: The mission's ceiling for root test files. The frozen baseline above already
#: pins the exact set, but that is a ratchet on *change*: regenerating it would
#: happily record 40 files. This is the criterion itself.
MAX_ROOT_TEST_FILES = 15


#: This file contains the very patterns it searches for, so every scan here skips
#: it. Otherwise the enforcer lands on its own allowlist, which is precisely the
#: kind of quiet wrongness these checks exist to catch.
_SELF = Path(__file__).name


def _files_matching(pattern: str) -> List[str]:
    rx = re.compile(pattern)
    return sorted(
        p.name for p in TESTS.glob("test_*.py")
        if p.name != _SELF
        and rx.search(p.read_text(encoding="utf-8", errors="replace"))
    )


# --------------------------------------------------------------------------
# Rule: adding a feature must not add a root test file
# --------------------------------------------------------------------------


def test_the_root_test_set_stays_small() -> None:
    """The root of `tests/` must stay small enough to read.

    The bulk belongs in `tests/<area>/` packages and in `tests/conformance/`, where
    a case is data rather than Python. A file added at the root should be a
    cross-cutting gate, not a home for a new behaviour test.
    """
    actual = _root_test_files()
    assert len(actual) <= MAX_ROOT_TEST_FILES, (
        f"{len(actual)} test files sit directly under tests/, over the "
        f"{MAX_ROOT_TEST_FILES} the layout allows: {actual}. Put behaviour cases in "
        f"tests/conformance/ and area tests in tests/<area>/."
    )


def test_root_test_files_match_the_frozen_baseline() -> None:
    """The suite's shape may only change deliberately.

    Both directions are failures, and both have one fix:

    * a file that is *new* -- put the case in ``tests/conformance/`` instead. A
      conformance case is data; it needs no Python and cannot rot.
    * a file that is *gone* -- regenerate the baseline, so the shrink is recorded
      in the diff instead of happening quietly.

    Without the second half this would not be a ratchet: the set could shrink to
    nothing while the baseline still described the old suite.
    """
    expected = set(_baseline()["root_test_files"])
    actual = set(_root_test_files())

    added = sorted(actual - expected)
    removed = sorted(expected - actual)
    assert not added and not removed, (
        f"the root test-file set changed.\n"
        f"  NEW (not allowed -- add the case to tests/conformance/ instead): {added}\n"
        f"  GONE (regenerate the baseline to record the shrink): {removed}\n"
        f"  fix: python tools/gen_test_policy_baseline.py"
    )


def test_the_baseline_is_not_hand_edited() -> None:
    """The baseline is generated, so it must equal what the generator produces."""
    module = _load_generator()
    expected = module.render(module.build_baseline())
    actual = BASELINE_PATH.read_text(encoding="utf-8")
    assert actual == expected, (
        "tests/_test_policy_baseline.json does not match the tree it describes; "
        "run: python tools/gen_test_policy_baseline.py"
    )


# --------------------------------------------------------------------------
# Rule 1: an end-to-end test judges behaviour, never the generated C
# --------------------------------------------------------------------------


def test_only_allowlisted_files_read_generated_c() -> None:
    """Rule 1. The allowlist may only shrink.

    Asserting ``"..." in bundle_c`` pins the *implementation*: a legitimate
    refactor of the code generator turns the test red without any behaviour
    having changed. The right home for such a case is ``tests/conformance/``
    (compile and run it) or, when the runtime genuinely cannot notice the
    regression, a justified snapshot in ``tests/test_snapshots_c.py``.
    """
    offenders = _files_matching(r"bundle_c|generated_c")
    allowed = set(_baseline()["may_read_generated_c"])
    new = [name for name in offenders if name not in allowed]
    assert not new, (
        f"these files inspect generated C, which rule 1 forbids: {new}.\n"
        f"Compile and run the program instead (tests/conformance/), or add a "
        f"justified snapshot to tests/test_snapshots_c.py."
    )


def test_the_conformance_corpus_never_inspects_generated_c() -> None:
    """The corpus is data: a case's .pengu plus its .expected/.exit, nothing else."""
    bad = []
    for path in CONFORMANCE_DIR.rglob("*.pengu"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"bundle\.c|generated_c|assert\s+.*\bin c\b", text):
            bad.append(str(path.relative_to(REPO)))
    assert not bad, (
        f"a conformance case must not inspect generated C: {bad}. "
        f"A case is judged by its stdout and exit code."
    )


# --------------------------------------------------------------------------
# Rule 7: no test sleeps
# --------------------------------------------------------------------------


def test_only_allowlisted_files_sleep() -> None:
    """Rule 7. A sleep is a guess about timing; it flakes on a loaded machine.

    The allowlist holds the three cases that use ``time.sleep`` to force a
    distinct file mtime before a cache assertion. That is an ordering device, not
    a wait for a side effect, and it is the only defensible form.
    """
    offenders = _files_matching(r"\btime\.sleep\(")
    allowed = set(_baseline()["may_sleep"])
    new = [name for name in offenders if name not in allowed]
    assert not new, (
        f"these files call time.sleep: {new}. Rule 7: use determinism, or force "
        f"the ordering explicitly (os.utime) instead of waiting for it."
    )


# --------------------------------------------------------------------------
# The smoke tier's promise: no C compilation
# --------------------------------------------------------------------------


def test_the_smoke_tier_spawns_nothing() -> None:
    """`pengu selftest --smoke` promises speed; a smoke test that compiles C is not one.

    The CI `smoke` job runs with ``build-runtime: false`` precisely because these
    files need no toolchain. A subprocess here would make that job fail for
    environmental reasons, which is the least useful kind of red.
    """
    baseline = _baseline()
    assert baseline["smoke_files_with_subprocess"] == [], (
        f"a smoke-marked file spawns a process: "
        f"{baseline['smoke_files_with_subprocess']}. The smoke tier must run "
        f"without a C compiler and without the runtime archive."
    )


# --------------------------------------------------------------------------
# Corpus invariants that keep `--affected` honest
# --------------------------------------------------------------------------


def test_every_case_is_covered_by_the_dependency_graph() -> None:
    """A case missing from `_deps.json` is invisible to `--affected`."""
    graph_path = CONFORMANCE_DIR / "_deps.json"
    assert graph_path.is_file(), (
        "tests/conformance/_deps.json is missing; run: "
        "python tools/gen_conformance_deps.py"
    )
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    mapped = {k for k in graph if k != "_meta"}
    on_disk = {
        p.relative_to(CONFORMANCE_DIR).with_suffix("").as_posix()
        for p in CONFORMANCE_DIR.rglob("*.pengu")
        if p.with_suffix(".expected").is_file()
    }
    assert mapped == on_disk, (
        f"the dependency graph and the corpus disagree: "
        f"only in graph={sorted(mapped - on_disk)}, "
        f"only on disk={sorted(on_disk - mapped)}"
    )


def test_no_leftover_migration_directory() -> None:
    """`tests/_migrated/` is a staging area, not a destination (Fase 7)."""
    leftover = TESTS / "_migrated"
    assert not leftover.exists(), (
        f"{leftover.relative_to(REPO)} still exists. Migrated files are either "
        f"converted or deleted; a permanent staging directory hides both."
    )
