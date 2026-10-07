"""Phase 9, item 9.6 — the tag created by CI must actually start the release.

Premise verified before this file existed (audit §18.1 #10): a push performed
with the repository's ``GITHUB_TOKEN`` does **not** create a new workflow run, so
``release.yml``'s ``push: tags`` trigger never fired for the tag ``ci.yml``
pushed.  ``workflow_dispatch`` is the documented exception, so the handoff is an
explicit dispatch.

The end-to-end fork run the roadmap asks for cannot be executed in this
environment (no GitHub credentials, no fork), so what is pinned here is the
mechanism plus the fact that it stays single-publisher.  The limitation is
recorded in ``AUDIT_1.0_FASE9.md`` and ``docs/RELEASE.md``.
"""

from __future__ import annotations

import re

import pytest
import yaml

from tests.conftest import REPO
from tests.test_ci_workflows import ALL_WORKFLOWS, _jobs, _raw, _triggers

WORKFLOWS = REPO / ".github" / "workflows"


def test_auto_tag_dispatches_the_release_workflow():
    """C2: remove the dispatch step and this test fails."""
    raw = _raw("ci.yml")
    assert "gh workflow run release.yml" in raw, (
        "the tag job must dispatch release.yml; a GITHUB_TOKEN push cannot do it"
    )
    assert "-f version=" in raw, "release.yml needs the tag as its input"


def test_auto_tag_has_actions_write_permission():
    """`contents: write` cannot start a run: dispatching needs `actions: write`."""
    job = _jobs(yaml.safe_load(_raw("ci.yml").replace("'on':", "on:")))["auto-tag"]
    assert job["permissions"]["actions"] == "write", job["permissions"]
    assert job["permissions"]["contents"] == "write", (
        "the job still has to create and push the tag"
    )


def test_the_dispatch_is_gated_on_this_job_having_created_the_tag():
    """A human-pushed tag already triggered release.yml: do not publish twice."""
    raw = _raw("ci.yml")
    assert "created=true" in raw and "created=false" in raw
    assert "steps.tag.outputs.created == 'true'" in raw
    assert "id: tag" in raw


def test_release_accepts_a_dispatch_with_a_required_version():
    doc = yaml.safe_load(_raw("release.yml"))
    dispatch = _triggers(doc).get("workflow_dispatch")
    assert dispatch is not None, "release.yml must be dispatchable"
    assert dispatch["inputs"]["version"]["required"] is True


def test_only_one_workflow_still_publishes_a_release():
    """The previous phase's invariant must survive this change."""
    publishers = []
    for name in ALL_WORKFLOWS:
        raw = _raw(name)
        if re.search(r"gh release create|softprops/action-gh-release", raw):
            publishers.append(name)
    assert publishers == ["release.yml"], publishers


def test_no_workflow_dispatches_a_release_from_itself():
    """ci.yml dispatches release.yml, never itself (that would loop)."""
    raw = _raw("ci.yml")
    for match in re.finditer(r"gh workflow run ([^\s]+)", raw):
        assert match.group(1) != "ci.yml"


def test_a_tag_push_still_triggers_the_release_for_human_pushes():
    """The dispatch is an addition, not a replacement: `git push --tags` works."""
    doc = yaml.safe_load(_raw("release.yml"))
    push = _triggers(doc).get("push")
    assert push and "v*" in push["tags"]


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_the_dispatch_target_exists(name):
    """A `gh workflow run X` must name a workflow file that is in the repo."""
    for match in re.finditer(r"gh workflow run (\S+)", _raw(name)):
        target = match.group(1)
        assert (WORKFLOWS / target).is_file(), f"{name} dispatches a missing {target}"
