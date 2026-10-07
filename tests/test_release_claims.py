"""Phase 9, item 9.11 — the gate for the gate.

`RELEASE_CHECKLIST.md` is the document a release is signed off against.  It used
to contain five claims the audit refuted (AUDIT §13.3 / §18.1), each of which was
unfalsifiable as written.  This module makes that impossible:

* every checkbox in §1 ("Automated") must name a `` `command` `` or a
  `workflow: <file>` — a claim with no way to check it fails the build;
* every checkbox in §2 ("Manual") must be marked `manual:` so author-only actions
  cannot hide among the gates;
* every repository path a box references must exist, so a checklist cannot cite a
  script or a test that was deleted;
* the specific refuted claims cannot come back.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from tests.conftest import REPO

CHECKLIST = REPO / "RELEASE_CHECKLIST.md"

BACKTICK = re.compile(r"`([^`]+)`")
BULLET = re.compile(r"^- \[ \] (.*)$")
#: Only `##` starts a section: `###` is a subheading and must not reset it.
HEADING = re.compile(r"^(#{2}) (.*)$")

#: Paths referenced by a box are repository-relative; only these shapes are
#: validated (a URL or an artifact name is not a file in the tree).
PATH_TOKEN = re.compile(
    r"(?:(?:tests|scripts|docs|benches|vscode-extension)/[\w./-]+"
    r"|\.github/workflows/[\w.-]+\.yml"
    r"|\.github/actions/[\w./-]+"
    r"|\b(?:make_release|extern_manifest|pengu_tcc|pengu_version|pengu_project"
    r"|build_runtime|pengu_paths)\.py\b"
    r"|\b(?:README|SECURITY|BENCHMARKS|CHANGELOG|CONTRIBUTING|LICENSE)\.md\b"
    r"|\bVERSION\b)"
)

MANUAL_SECTION = "Manual"
#: Claims refuted by AUDIT §13.3 / §18.1.  A box may still *mention* them, but
#: only to refute them: the refutation marker must be on the same box.
REFUTED_CLAIMS = {
    "--strict-c99": ("❌", "NOT a portability gate"),
    "MSVC": ("❌", "not a supported compiler"),
    "spctl --assess": ("❌", "not claimed"),
}


def _items() -> List[Tuple[str, str]]:
    """``[(section, item text)]`` for every ``- [ ]`` box, continuations included."""
    section = ""
    items: List[Tuple[str, str]] = []
    current: List[str] = []
    current_section = ""
    for raw in CHECKLIST.read_text(encoding="utf-8").splitlines():
        heading = HEADING.match(raw)
        if heading:
            section = heading.group(2)
            continue
        bullet = BULLET.match(raw)
        if bullet:
            if current:
                items.append((current_section, "\n".join(current)))
            current = [bullet.group(1)]
            current_section = section
            continue
        if current and (raw.startswith("      ") or raw.startswith("\t")):
            current.append(raw.strip())
        elif current and not raw.strip():
            continue
        elif current:
            items.append((current_section, "\n".join(current)))
            current = []
    if current:
        items.append((current_section, "\n".join(current)))
    return items


def _gates(text: str) -> List[str]:
    """Backticked tokens that are actually a reproducible command or a path.

    A bare backtick is not a gate: "``nightly fuzz job``" or "``manual:``" would
    otherwise satisfy the rule without proving anything.  A gate is either an
    invocation (``pytest …``, ``python …``) or a repository path (``docs/…``,
    ``tests/…``).
    """
    gates = []
    for token in BACKTICK.findall(text):
        token = token.strip()
        if not token:
            continue
        first = token.split()[0]
        if first in RUNNERS or first.startswith(("pytest", "python", "git", "gh")):
            gates.append(token)
        elif "/" in token and token.rsplit("/", 1)[-1].endswith(
            (".py", ".sh", ".yml", ".md", ".c", ".json", ".toml")
        ):
            gates.append(token)
    return gates


#: Programs whose invocation counts as a reproducible gate.
RUNNERS = {
    "pytest", "python", "python3", "bash", "sh", "git", "gh", "tar", "unzip",
    "sha256sum", "shasum", "codesign", "spctl", "xattr", "make", "cmake",
    "ninja", "ruff", "curl", "wget", "pengu",
}


def test_the_checklist_has_the_two_sections():
    sections = [HEADING.match(line).group(2)
                for line in CHECKLIST.read_text(encoding="utf-8").splitlines()
                if HEADING.match(line)]
    assert any("Automated" in s for s in sections), sections
    assert any(MANUAL_SECTION in s for s in sections), sections


def test_every_automated_box_has_a_gate():
    """The core of item 9.11: no box may assert something unverifiable."""
    offenders = []
    for section, text in _items():
        if MANUAL_SECTION in section:
            continue
        has_command = bool(_gates(text))
        has_workflow = "workflow:" in text
        if not (has_command or has_workflow):
            offenders.append(f"[{section}] {text.splitlines()[0]}")
    assert offenders == [], (
        "these boxes claim something with no command and no workflow:\n"
        + "\n".join(offenders)
    )


def test_every_manual_box_is_marked_manual():
    offenders = [
        text.splitlines()[0]
        for section, text in _items()
        if MANUAL_SECTION in section and "manual:" not in text
    ]
    assert offenders == [], "manual boxes must be marked `manual:`:\n" + "\n".join(offenders)


def test_automated_boxes_do_not_hide_manual_work():
    offenders = [
        text.splitlines()[0]
        for section, text in _items()
        if MANUAL_SECTION not in section and "manual:" in text
    ]
    assert offenders == [], (
        "a `manual:` marker inside the automated section:\n" + "\n".join(offenders)
    )


def _referenced_paths(text: str) -> List[str]:
    return sorted(set(PATH_TOKEN.findall(text)))


def test_every_path_a_box_references_exists():
    """A box must not cite a script or a test that does not exist."""
    missing: Dict[str, List[str]] = {}
    for _section, text in _items():
        for path in _referenced_paths(text):
            if not (REPO / path).exists():
                missing.setdefault(path, []).append(text.splitlines()[0][:70])
    assert missing == {}, (
        "the checklist cites paths that do not exist:\n"
        + "\n".join(f"  {p}  (in: {uses[0]})" for p, uses in missing.items())
    )


def test_workflow_references_point_at_real_workflows():
    workflows = {p.name for p in (REPO / ".github" / "workflows").glob("*.yml")}
    for _section, text in _items():
        for match in re.finditer(r"workflow:\s*`?([\w./-]+\.yml)`?", text):
            assert match.group(1) in workflows or (REPO / match.group(1)).is_file(), (
                f"unknown workflow: {match.group(1)}"
            )


@pytest.mark.parametrize("claim", sorted(REFUTED_CLAIMS))
def test_refuted_claims_are_not_restated_as_facts(claim):
    """The five AUDIT §13.3 refutations must stay refuted."""
    marker, explanation = REFUTED_CLAIMS[claim]
    boxes_mentioning = [text for _s, text in _items() if claim in text]
    assert boxes_mentioning, f"{claim} disappeared from the checklist; re-check the audit"
    for text in boxes_mentioning:
        assert marker in text, f"{claim} is stated without the refutation marker"
        assert explanation in text, f"{claim} is missing the measured explanation"


def test_the_impossible_fuzz_budget_is_gone():
    """AUDIT §13.3 #8/#9: 72 h in one job cannot exist (GitHub kills at 6 h)."""
    text = CHECKLIST.read_text(encoding="utf-8")
    for match in re.finditer(r"(\d+)\s*h(?:ours?)?", text):
        hours = int(match.group(1))
        if hours <= 6:
            continue
        line = text[: match.start()].splitlines()[-1] + text[match.start():].splitlines()[0]
        assert ("not " in line.lower() or "impossible" in line.lower()
                or "❌" in line), f"impossible budget restated: {line.strip()}"


def test_the_checklist_links_the_release_process():
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "docs/RELEASE.md" in text, "the checklist must link the full process"


def test_release_documents_cross_reference_each_other():
    """RELEASE.md must not duplicate the checklist; it points at it."""
    release = (REPO / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    assert "RELEASE_CHECKLIST.md" in release
    assert "AUDIT_1.0_FASE9.md" in release


def test_no_box_promises_a_gate_that_does_not_run():
    """`workflow: X` must be a workflow whose file exists *and* runs something."""
    for _section, text in _items():
        for match in re.finditer(r"workflow:\s*`?([\w./-]+\.yml)`?", text):
            path = REPO / ".github" / "workflows" / match.group(1)
            if not path.is_file():
                path = REPO / match.group(1)
            body = path.read_text(encoding="utf-8")
            assert "jobs:" in body, f"{match.group(1)} declares no jobs"
            assert re.search(r"^\s+(run|uses):", body, re.MULTILINE), (
                f"{match.group(1)} declares no steps"
            )
