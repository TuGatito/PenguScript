"""Roadmap 2.0 Phase 8, item 8.5 — the migration corpus.

`tests/migration/<version>/<program>.pengu` holds one program written in the
syntax of each published version from 0.10.0 onward, with the outcome
`MIGRATION.md` documents for it in `EXPECTED.json`.  The corpus is not a
regression suite for the *current* language: it is the input a future breaking
change (and the deferred `pengu migrate` rewriter, roadmap 4.14b) will be judged
against.  That is why two of the programs are expected to FAIL.

Coverage scope, measured rather than assumed: `CHANGELOG.md` lists 36 published
versions (0.3.0 … 1.0.0), but `MIGRATION.md` §2 — the normative migration table —
starts at 0.10.0, because that is the only release with a breaking change and the
pre-0.10 syntax is not documented in any current normative document.  Inventing
"historical" programs for 0.3.0–0.9.1 that nothing can verify would be worse than
recording the gap, so the range asserted below is `>= 0.10.0` and the gap is
documented in `tests/migration/README.md` and AUDIT_1.0_FASE8.md.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from pengu_semver import Version
from tests.conftest import REPO, requires_cc, requires_runtime

MIGRATION_DIR = Path(__file__).resolve().parent / "migration"
EXPECTED_PATH = MIGRATION_DIR / "EXPECTED.json"

#: The first version `MIGRATION.md` documents (the only breaking change in the
#: project's history landed there); everything earlier is out of the doc's scope.
FIRST_DOCUMENTED = Version.parse("0.10.0")


def _expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


def _programs() -> list:
    return _expected()["programs"]


def _published_versions() -> set:
    """Versions with a released CHANGELOG heading (not `Unreleased`)."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    found = set()
    for raw in re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE):
        found.add(raw)
    return found


def _check(program: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "check", "--entry", str(program)],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
    )


def _reported_code(text: str) -> str:
    """The structured ``[Exxxx]`` diagnostic token the CLI emits, if any."""
    match = re.search(r"\[([EW]\d{4})\]", text)
    return match.group(1) if match else ""


def test_corpus_covers_every_documented_published_version():
    """No version in the documented range may lose its example silently.

    Coverage is asserted at the **minor** line, not at the patch level, and that is
    a deliberate consequence of the project's own stability contract
    (`MIGRATION.md` §1): additive changes ship in minor releases and only a major
    release may remove or change a signature.  A patch release therefore *cannot*
    introduce new surface syntax, so writing 14 near-identical "0.13.1 … 0.13.14"
    programs would be corpus theatre.  Symbols are real versions: every entry's
    `version` must exist in `CHANGELOG.md`.
    """
    published = _published_versions()
    published_minors = {v.rsplit(".", 1)[0] for v in published
                        if Version.parse(v) >= FIRST_DOCUMENTED}
    covered_minors = {entry["version"].rsplit(".", 1)[0] for entry in _programs()}
    assert published_minors - covered_minors == set(), (
        f"published minor lines with no migration program: "
        f"{sorted(published_minors - covered_minors)}"
    )
    unknown = {entry["version"] for entry in _programs()} - published
    assert unknown == set(), (
        f"EXPECTED.json names versions that are not in CHANGELOG.md: {sorted(unknown)}"
    )


def test_every_corpus_file_is_declared_and_vice_versa():
    """An undeclared program would never run; a stale entry would never fail."""
    on_disk = {str(p.relative_to(MIGRATION_DIR)) for p in MIGRATION_DIR.rglob("*.pengu")}
    declared = {entry["file"] for entry in _programs()}
    assert on_disk - declared == set(), f"undeclared corpus programs: {sorted(on_disk - declared)}"
    assert declared - on_disk == set(), f"EXPECTED.json lists missing files: {sorted(declared - on_disk)}"


def test_the_breaking_versions_in_the_doc_are_covered_by_a_failing_program():
    """`MIGRATION.md` §2 and the corpus must agree about what breaks.

    Parses the doc's breaking-change table (it is the normative list) and requires
    that each version it marks as breaking has at least one `expects: error`
    program.  A new breaking release with no corpus entry fails here.
    """
    doc = (REPO / "MIGRATION.md").read_text(encoding="utf-8")
    section = doc.split("## 2. Breaking changes by version", 1)[1].split("## 3.", 1)[0]
    breaking = set()
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not re.fullmatch(r"`?\d+\.\d+\.\d+`?", cells[0]):
            continue
        if "none" in cells[1].lower() or "**none**" in line:
            continue
        breaking.add(cells[0].strip("`"))
    assert breaking, "could not parse the breaking-change table from MIGRATION.md"

    failing_versions = {entry["version"] for entry in _programs() if entry["expects"] == "error"}
    assert breaking - failing_versions == set(), (
        f"MIGRATION.md documents breaking changes with no failing corpus program: "
        f"{sorted(breaking - failing_versions)}"
    )


@pytest.mark.parametrize("entry", _programs(), ids=lambda e: e["file"])
def test_migration_program_behaves_as_documented(entry):
    """Each program is driven through the real CLI and asserted on its rc/code."""
    program = MIGRATION_DIR / entry["file"]
    assert program.is_file(), f"missing corpus program {program}"

    res = _check(program)
    if entry["expects"] == "error":
        assert res.returncode != 0, (
            f"{entry['file']} was documented to fail with {entry['code']} but check passed:\n"
            f"{res.stdout}"
        )
        assert _reported_code(res.stdout + res.stderr) == entry["code"], (
            f"{entry['file']} reported "
            f"{_reported_code(res.stdout + res.stderr) or 'no code'}, documented {entry['code']}"
        )
        assert "Traceback (most recent call last)" not in (res.stdout + res.stderr), (
            f"{entry['file']} produced a Python traceback (rule C4)"
        )
    else:
        assert res.returncode == 0, (
            f"{entry['file']} no longer checks cleanly (documented as ok):\n"
            f"{res.stdout}\n{res.stderr}"
        )


@pytest.mark.parametrize(
    "entry",
    [e for e in _programs() if e["expects"] == "ok"],
    ids=lambda e: e["file"],
)
@requires_cc
@requires_runtime
def test_migrated_programs_still_build_and_run(entry, tmp_path):
    """`ok` means the program runs, not just that it type-checks.

    Compiling is what catches a change that keeps the syntax valid but breaks the
    lowering; the expected exit code makes the behavioural claim explicit.
    """
    program = MIGRATION_DIR / entry["file"]
    bundle = tmp_path / f"{program.stem}.c"
    built = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build",
         "--entry", str(program), "--output", str(bundle)],
        capture_output=True, text=True, timeout=900, cwd=str(REPO),
    )
    assert built.returncode == 0, f"build failed:\n{built.stdout}\n{built.stderr}"

    from tests.conftest import default_cc, runtime_link_flags, runtime_tail_flags
    from tests.conftest import BUILD_DIR, BUILD_INCLUDE, BUILD_LIB

    exe = tmp_path / "prog"
    cc = default_cc()
    compile_res = subprocess.run(
        [cc, str(bundle), f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
         f"-L{BUILD_LIB}", *runtime_link_flags(), *runtime_tail_flags(), "-o", str(exe)],
        capture_output=True, text=True, timeout=600,
    )
    assert compile_res.returncode == 0, f"C compile failed:\n{compile_res.stderr}"
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    assert run.returncode == entry["rc"], (
        f"{entry['file']} exited {run.returncode}, documented {entry['rc']}\n{run.stderr}"
    )
