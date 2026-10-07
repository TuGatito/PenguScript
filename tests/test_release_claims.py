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

Phase 10 / item 10.2 extends the same rule to the other two documents a release
publishes — `BENCHMARKS.md` and `SECURITY.md` (see the second half of this file):

* the benchmark page must be **dated** and must publish **every** case the
  harness measures — the previous revision was 6.7× wrong about binary size and
  nothing noticed because an undated table cannot be told from a fresh one;
* every security mitigation must name the test or workflow that gates it, and the
  supported-version table must cover the series `VERSION` actually is;
* the withdrawn claims (a GPG-signed release, PGP report encryption) must stay
  withdrawn.
"""

from __future__ import annotations

import datetime
import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from tests.conftest import REPO

CHECKLIST = REPO / "RELEASE_CHECKLIST.md"
BENCHMARKS = REPO / "BENCHMARKS.md"
SECURITY = REPO / "SECURITY.md"
VERSION_FILE = REPO / "VERSION"

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


# ===========================================================================
# Phase 10 / item 10.2 — BENCHMARKS.md
# ===========================================================================

#: `Measured on **2026-10-07** at ...`
MEASURED_ON = re.compile(r"Measured on \*\*(\d{4}-\d{2}-\d{2})\*\*")

#: A path a claim may cite; only the shapes that are really files in the tree.
DOC_PATH = re.compile(
    r"(?:(?:benches|scripts|docs|tests)/[\w./-]+"
    r"|\.github/workflows/[\w.-]+\.yml"
    r"|\b(?:README|SECURITY|BENCHMARKS|CHANGELOG|CONTRIBUTING|LICENSE)\.md\b)"
)

#: Paths the benchmark page uses as the *output* of a documented command.  The
#: file legitimately does not exist in a clean checkout; its directory must.
BENCHMARK_OUTPUTS = {"benches/results/local.csv"}


def _bench_cases() -> List[str]:
    """Loads `CASES` out of `benches/run_bench.py` (it is not a package)."""
    path = REPO / "benches" / "run_bench.py"
    spec = importlib.util.spec_from_file_location("release_claims_run_bench", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return sorted(module.CASES)


def _benchmarks_text() -> str:
    return BENCHMARKS.read_text(encoding="utf-8")


def test_benchmarks_page_is_dated():
    """An undated measurement table cannot be distinguished from a stale one.

    Measured during Phase 10: this page published 98.4 KiB for hello world while
    the real figure was 659.5 KiB — a 6.7× error that survived because no date
    made the age of the number visible.
    """
    match = MEASURED_ON.search(_benchmarks_text())
    assert match, "BENCHMARKS.md must state `Measured on **YYYY-MM-DD**`"
    measured = datetime.date.fromisoformat(match.group(1))
    # Compared against UTC with one day of slack: the date is written in UTC,
    # and a maintainer west of it would otherwise be "in the future".
    utc_today = datetime.datetime.now(datetime.timezone.utc).date()
    assert measured <= utc_today + datetime.timedelta(days=1), (
        f"BENCHMARKS.md claims a measurement date in the future: {measured}"
    )


def test_benchmarks_page_publishes_every_measured_case():
    """A case the harness measures but the page does not publish is invisible."""
    text = _benchmarks_text()
    missing = [case for case in _bench_cases() if f"`{case}`" not in text]
    assert missing == [], (
        f"benches/run_bench.py measures {missing} but BENCHMARKS.md never shows them"
    )


def test_benchmarks_page_cites_only_existing_paths():
    """A cited input must exist; a documented *output* needs its directory.

    `benches/results/local.csv` is what the reproduce command writes, so the file
    itself is legitimately absent from a clean checkout.  Everything else is a
    citation of something that should be in the tree — a test, a script, a
    workflow — and a deleted one must fail here.
    """
    missing: List[str] = []
    for path in sorted(set(DOC_PATH.findall(_benchmarks_text()))):
        if path in BENCHMARK_OUTPUTS:
            if not (REPO / path).parent.is_dir():
                missing.append(f"{path} (output directory does not exist)")
        elif not (REPO / path).exists():
            missing.append(path)
    assert missing == [], f"BENCHMARKS.md cites paths that do not exist: {missing}"


def test_every_revised_target_states_whether_it_is_met():
    """A target row may not leave the verdict implicit."""
    section = _benchmarks_text().split("## Revised targets", 1)
    assert len(section) == 2, "BENCHMARKS.md lost its `## Revised targets` section"
    body = section[1].split("\n## ", 1)[0]
    rows = [line for line in body.splitlines()
            if line.startswith("|") and "---" not in line]
    assert len(rows) >= 3, f"expected a target table, found {rows}"
    verdicts = re.compile(r"^\|\s*(?:met|\*\*met\*\*|(?:not met|\*\*not met\*\*))", re.I)
    offenders = [row for row in rows[1:]   # rows[0] is the header
                 if not re.search(r"\|\s*(\*\*)?(not )?met", row, re.I)]
    assert offenders == [], (
        "these target rows do not say whether the target is met:\n" + "\n".join(offenders)
    )


def test_benchmarks_page_names_its_environment():
    """Numbers are machine-specific: they must say which machine."""
    text = _benchmarks_text()
    assert "## Reference environment" in text
    for needle in ("gcc", "glibc", "Python"):
        assert needle in text, f"the reference environment does not name {needle}"


# ===========================================================================
# Phase 10 / item 10.2 — SECURITY.md
# ===========================================================================

#: A table row inside §Secure-by-default measures.
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$", re.M)


def _security_text() -> str:
    return SECURITY.read_text(encoding="utf-8")


def _secure_by_default_rows() -> List[Tuple[str, str]]:
    """`[(claim, gate cell)]` for every row of the mitigations table."""
    text = _security_text()
    section = text.split("## Secure-by-default measures", 1)
    assert len(section) == 2, "SECURITY.md lost its mitigations section"
    body = section[1].split("\n## ", 1)[0]
    rows: List[Tuple[str, str]] = []
    for line in body.splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower().startswith(("mitigation", "---")):
            continue
        rows.append((cells[0], cells[1]))
    return rows


def test_every_secure_by_default_claim_names_a_gate():
    """Item 10.2: a security claim with no gate is decoration."""
    rows = _secure_by_default_rows()
    assert len(rows) >= 5, f"expected the mitigations table, found {len(rows)} rows"
    ungated = [claim.split("**")[1] if "**" in claim else claim[:60]
               for claim, gate in rows if not DOC_PATH.findall(gate)]
    assert ungated == [], (
        "these security claims name no test or workflow:\n  " + "\n  ".join(ungated)
    )


def test_every_security_gate_path_exists():
    missing: Dict[str, List[str]] = {}
    for _claim, gate in _secure_by_default_rows():
        for path in DOC_PATH.findall(gate):
            if not (REPO / path).exists():
                missing.setdefault(path, []).append(gate)
    assert missing == {}, (
        "SECURITY.md names gates that do not exist:\n"
        + "\n".join(f"  {p}" for p in missing)
    )


def test_security_supported_versions_cover_the_current_version():
    """The table must have a row that actually covers `VERSION`.

    Reverting `VERSION` to `0.16.0` is covered by the `0.16.x` row; bumping to
    `1.0.0-rc1` is covered by `1.x`; a future `2.0.0` is covered by neither, so
    the table has to be revisited instead of silently going stale.
    """
    from pengu_semver import Version

    version = Version.parse(VERSION_FILE.read_text(encoding="utf-8").strip())
    text = _security_text()
    section = text.split("## Supported versions", 1)
    assert len(section) == 2, "SECURITY.md lost its `## Supported versions` section"
    table = section[1].split("\n## ", 1)[0]

    ranges = re.findall(r"`(\d+(?:\.\d+)?)\.x`", table)
    assert ranges, "the supported-version table declares no `N.x` / `N.M.x` range"
    covered = any(
        (version.major == int(r.split(".")[0]) and "." not in r)
        or f"{version.major}.{version.minor}" == r
        for r in ranges
    )
    assert covered, (
        f"VERSION is {version} and none of the declared ranges "
        f"{ranges} covers it; update SECURITY.md §Supported versions"
    )


def test_the_withdrawn_signature_claims_stay_withdrawn():
    """Item 10.2 refutations: no GPG release key, no PGP report channel.

    The pre-Phase-10 text promised "release artifacts are signed" and a
    fingerprint "published with each signed release"; neither existed. Both are
    withdrawn, and this test keeps them withdrawn.
    """
    text = _security_text()
    assert "GPG signing of the release artifacts is not performed" in text
    assert "PGP-encrypted reports are not offered yet" in text
    for resurrected in (
        "release artifacts are signed and ship with checksums",
        "fingerprint is published with each signed release",
    ):
        assert resurrected not in text, (
            f"a withdrawn claim came back: {resurrected!r}; it has no gate"
        )
