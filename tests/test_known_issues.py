"""Known issues that are tracked rather than hidden.

Anything here is a *documented* deviation with a reproducing test, so it cannot
be forgotten and it cannot silently regress into "fixed" without the test being
updated deliberately.
"""

import os

import pytest

from tests.conftest import REPO, compile_run, requires_cc, requires_runtime

pytestmark = [requires_cc, requires_runtime]


def test_auto_banish_container_model_is_leak_free():
    """The core ownership model: a plain container must not leak.

    This is the case the sanitizers workflow asserts with ASan/LeakSanitizer; it
    passes, which is what lets us claim the auto-banish model itself is sound.
    """
    res = compile_run(
        "weave main into int:\n"
        "  var xs as list of int is list of int\n"
        "  calling xs.push with 1\n"
        "  calling xs.push with 2\n"
        "  var s as int is 0\n"
        "  for v in xs:\n"
        "    set s is s + v\n"
        "  if s == 3:\n"
        "    return 0\n"
        "  return 1\n",
        tag="known_banish",
    )
    assert res.returncode == 0, res.stderr


KNOWN_LEAK_ISSUE = """
KNOWN ISSUE — legacy container APIs leak under ASan/LeakSanitizer.

Observed with `-fsanitize=address` on this machine:

    SUMMARY: AddressSanitizer: 1033 byte(s) leaked in 5 allocation(s).

Scope:
  * a minimal `list of int` (push + iterate + auto-banish) is CLEAN, so the
    ownership/auto-banish model is not the cause;
  * the leak appears in the legacy paths exercised by
    `tests/test_std_backward_compat.py` (`coven.SetString` and
    `map of string to int`).

Impact: no memory-safety error (no use-after-free, no overflow, no UB); it is a
"storage not released before exit" report. It is still tracked as a bug because
the project claims "zero leaks in programs free of unsafe/FFI".

The sanitizers workflow deselects that single test by name instead of disabling
leak detection, so the finding stays visible.
"""


@pytest.mark.skipif(
    "sanitize" not in os.environ.get("PENGU_CFLAGS", ""),
    reason="needs PENGU_CFLAGS with -fsanitize=address (see sanitizers.yml)",
)
@pytest.mark.xfail(
    reason="tracked leak in the legacy coven.SetString/map paths; see KNOWN_LEAK_ISSUE",
    strict=False,
)
def test_known_leak_legacy_containers():
    """Reproduces the tracked leak under ASan (xfail until the legacy paths are fixed).

    Only meaningful when the sanitizer flags are active: without ASan there is no
    leak detector to report anything, so the test skips rather than pretending to
    pass.  Not strict: the day the leak is fixed the suite should stay green while
    the xpass shows up as a signal to remove this entry.
    """
    res = compile_run(
        "import std.coven\n"
        "import std.spark\n\n"
        "weave main into int:\n"
        "    var s as coven.SetString is calling coven.new_set_string\n"
        "    calling s.add with \"hi\"\n"
        "    calling spark.assert with calling s.contains with \"hi\"\n"
        "    return 0\n",
        tag="known_leak",
    )
    if "AddressSanitizer: " in (res.stderr or ""):
        pytest.fail("legacy container leaked (see KNOWN_LEAK_ISSUE)")
    assert res.returncode == 0, res.stderr


def test_known_issue_is_documented_in_the_changelog():
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "AddressSanitizer" in changelog
    assert "coven" in changelog or "legacy container" in changelog.lower()


def test_sanitizer_workflow_deselects_by_name_not_by_disabling_detection():
    workflow = (REPO / ".github" / "workflows" / "sanitizers.yml").read_text(encoding="utf-8")
    assert "--deselect" in workflow
    assert "test_std_backward_compat" in workflow
    # detect_leaks must stay on for the sanitizer job.
    assert "detect_leaks=1" in workflow


def test_every_sanitizer_pytest_step_deselects_the_known_leak():
    """Roadmap 8.2 (B9): one variable, consumed by *every* pytest step.

    Regression guard for the bug this item fixes.  The deselect node id used to be
    inlined in the first ``pytest tests`` invocation, so the third ASan step and
    the valgrind step re-ran the leaking ``test_std_backward_compat`` and the job
    was red over a finding that was already documented as a known issue.  Putting
    the literal back into a single step (i.e. reverting the fix) fails here.
    """
    import yaml

    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "sanitizers.yml").read_text(encoding="utf-8")
    )
    shared = (workflow.get("env") or {}).get("PENGU_SANITIZER_DESELECT", "")
    assert "test_std_backward_compat.py::test_std_backward_compat" in shared, (
        "the known-leak node id must be declared once, at workflow level"
    )

    steps = [step for job in (workflow.get("jobs") or {}).values()
             for step in (job.get("steps") or []) if "pytest" in (step.get("run") or "")]
    assert len(steps) >= 4, f"expected the four sanitizer pytest steps, found {len(steps)}"
    missing = [step.get("name") for step in steps
               if "--deselect" not in step["run"] or "PENGU_SANITIZER_DESELECT" not in step["run"]]
    assert missing == [], (
        f"these sanitizer steps would re-run the known leak: {missing}"
    )


def test_the_leak_verdict_is_only_disabled_when_it_is_declared():
    """Phase 8 item 8.2: `detect_leaks=0` narrows the claim, so it must be said out loud.

    The measured leak surface of the stdlib (item 8.19) makes a full-suite
    LeakSanitizer run red for reasons that are tracked, so the job keeps two
    contracts instead of one: memory safety with the leak verdict off, and leak
    freedom with it on.  This test is what stops the first contract from quietly
    becoming the only one - it requires both, requires the audit item to be named
    in the workflow, and forbids disabling the verdict through the job-level env
    where a reader would not notice which step gave up what.
    """
    import yaml

    doc = yaml.safe_load(
        (REPO / ".github" / "workflows" / "sanitizers.yml").read_text(encoding="utf-8")
    )

    def _asan(step):
        return (step.get("env") or {}).get("ASAN_OPTIONS", "")

    steps = [step for job in (doc.get("jobs") or {}).values()
             for step in (job.get("steps") or []) if "pytest" in (step.get("run") or "")]
    off = [s.get("name") for s in steps if "detect_leaks=0" in _asan(s)]
    on = [s.get("name") for s in steps if "detect_leaks=1" in _asan(s)]
    assert off, "no step declares the memory-safety contract (detect_leaks=0)"
    assert on, "no step keeps the strict leak contract (detect_leaks=1)"

    for job_name, job in (doc.get("jobs") or {}).items():
        assert "detect_leaks=0" not in ((job.get("env") or {}).get("ASAN_OPTIONS") or ""), (
            f"{job_name} disables the leak verdict for every step through the job env"
        )
    assert "8.19" in (REPO / ".github" / "workflows" / "sanitizers.yml").read_text(encoding="utf-8"), (
        "the workflow must name the tracked leak item that justifies the split"
    )
