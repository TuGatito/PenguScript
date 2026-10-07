"""CI/CD audit (Fase 7) — the workflows must keep the invariants the review fixed.

GitHub Actions cannot be executed in this environment, so these are static
assertions over the YAML plus real executions of the extracted release-version
logic.  Each test names the finding it pins.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.conftest import REPO

WORKFLOWS = REPO / ".github" / "workflows"
COMPOSITE = REPO / ".github" / "actions" / "setup-pengu" / "action.yml"
RELEASE_VERSION = REPO / "scripts" / "release_version.py"

#: Every workflow file, read from disk rather than listed by hand (Phase 8 /
#: item 8.16): a hand-written list is how `fuzz.yml` kept a 13 h timeout that
#: GitHub kills after 6 h — the invariant simply never ran against it.
ALL_WORKFLOWS = sorted(p.name for p in WORKFLOWS.glob("*.yml"))


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _jobs(doc: dict) -> dict:
    return {k: v for k, v in (doc.get("jobs") or {}).items() if isinstance(v, dict)}


def _triggers(doc: dict) -> dict:
    # PyYAML turns the bare `on:` key into the boolean True.
    return doc.get("on") or doc.get(True) or {}


def _raw(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# S1 — every workflow is well-formed and guarded
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_workflow_is_valid_yaml_with_jobs(name):
    doc = _load(name)
    assert _jobs(doc), f"{name} has no jobs"


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_every_job_has_a_timeout(name):
    """Finding: no timeout-minutes meant the 6 h platform default applied."""
    for job_name, job in _jobs(_load(name)).items():
        assert "timeout-minutes" in job, f"{name}:{job_name} has no timeout-minutes"


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_every_workflow_declares_concurrency_and_read_permissions(name):
    doc = _load(name)
    assert "concurrency" in doc, f"{name} has no concurrency group"
    perms = doc.get("permissions")
    assert perms, f"{name} has no top-level permissions"
    assert perms.get("contents") == "read", f"{name} should default to contents: read"


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_write_permission_is_scoped_to_a_single_job(name):
    """Minimum privilege: contents: write only where the job really needs it."""
    doc = _load(name)
    writers = [j for j, job in _jobs(doc).items()
               if (job.get("permissions") or {}).get("contents") == "write"]
    assert len(writers) <= 1, f"{name}: more than one job can write: {writers}"
    if writers:
        # A writing job must be a release/tag job, never a build matrix entry.
        assert any(k in writers[0] for k in ("tag", "release")), writers


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_third_party_actions_are_not_used(name):
    """Finding: softprops/action-gh-release was unpinned third-party code.

    It was replaced with the first-party `gh` CLI, so there is nothing to pin.
    """
    raw = _raw(name)
    for match in re.finditer(r"uses:\s*([^\s#]+)", raw):
        action = match.group(1)
        if action.startswith("./") or action.startswith("docker://"):
            continue
        owner = action.split("/")[0]
        assert owner in ("actions", "github"), f"{name}: third-party action {action}"


# --------------------------------------------------------------------------- #
# S2 — no double release (the blocking race)
# --------------------------------------------------------------------------- #


def test_only_one_workflow_publishes_a_release():
    publishers = [name for name in ALL_WORKFLOWS
                  if "gh release create" in _raw(name)
                  or "softprops/action-gh-release" in _raw(name)]
    assert publishers == ["release.yml"], publishers


def test_auto_tag_job_does_not_create_a_release():
    """The tag job must only tag: release.yml owns publishing."""
    raw = _raw("ci.yml")
    tag_job = raw[raw.index("auto-tag:"):]
    assert "git push origin" in tag_job
    assert "gh release create" not in tag_job
    assert "softprops" not in tag_job
    assert "download-artifact" not in tag_job.split("auto-tag:")[-1]


def test_release_is_triggered_by_the_tag_push():
    doc = _load("release.yml")
    assert "v*" in str(_triggers(doc).get("push", {}).get("tags", []))


def test_release_never_cancels_in_progress():
    for name in ALL_WORKFLOWS:
        raw = _raw(name)
        if "release-" in raw:
            assert "cancel-in-progress: false" in raw, name


def test_bench_and_release_do_not_cancel_in_progress():
    for name in ("bench.yml", "release.yml"):
        assert "cancel-in-progress: false" in _raw(name), name


# --------------------------------------------------------------------------- #
# S3 — the vUnreleased bug
# --------------------------------------------------------------------------- #


def test_release_version_skips_unreleased():
    """The script must return the newest **released** version, not `Unreleased`.

    Phase 11 (F11-N3): this assertion used to hardcode `v0.16.0`, so promoting the
    changelog to `[1.0.0]` failed a test that was really about *skipping*
    `[Unreleased]`, not about which release was newest. It now derives the
    expectation from `VERSION`, which is what the tag has to match.
    """
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    out = subprocess.run([sys.executable, str(RELEASE_VERSION)],
                         capture_output=True, text=True, cwd=str(REPO))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"v{version}", out.stdout
    assert "unreleased" not in out.stdout.strip().lower(), out.stdout


def test_release_version_fails_when_only_unreleased(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## [Unreleased] — FASE 6\n- work\n", encoding="utf-8")
    out = subprocess.run([sys.executable, str(RELEASE_VERSION), "--changelog", str(cl)],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert "Unreleased" in (out.stderr + out.stdout)


def test_release_version_detects_prereleases(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text(
        "# Changelog\n\n## [Unreleased]\n- wip\n\n## [1.0.0-rc1] - 2026-10-10\n- rc\n",
        encoding="utf-8",
    )
    out = subprocess.run([sys.executable, str(RELEASE_VERSION), "--changelog", str(cl),
                          "--json"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert '"prerelease": "true"' in out.stdout
    assert '"tag_name": "v1.0.0-rc1"' in out.stdout


def test_release_version_writes_github_outputs(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    out_file = tmp_path / "gh_output"
    cl.write_text("# C\n\n## [2.3.4] - 2026-01-01\n- body line\n", encoding="utf-8")
    subprocess.run([sys.executable, str(RELEASE_VERSION), "--changelog", str(cl),
                    "--github-output", str(out_file), "--notes-file", str(tmp_path / "n.md")],
                   check=True, capture_output=True, text=True)
    outputs = out_file.read_text(encoding="utf-8")
    assert "tag_name=v2.3.4" in outputs
    assert "prerelease=false" in outputs
    assert (tmp_path / "n.md").read_text(encoding="utf-8").strip() == "- body line"


def test_no_workflow_parses_the_changelog_inline():
    """Both tagging and notes must go through the shared script."""
    for name in ("ci.yml", "release.yml"):
        raw = _raw(name)
        assert "release_version.py" in raw, name
        assert not re.search(r"\^##\\s\*\\\[", raw), f"{name} still has an inline regex"


# --------------------------------------------------------------------------- #
# S4 — portability and cache
# --------------------------------------------------------------------------- #


def test_abi_layout_step_is_not_hardcoded_to_cc():
    """Finding: `cc` does not exist on Windows runners."""
    raw = _raw("ci.yml")
    step = raw[raw.index("ABI layout matrix"):]
    step = step[: step.index("- name:", 10)] if "- name:" in step[10:] else step
    assert "$RUNNER_OS" in step
    assert "CC_BIN" in step


def test_bench_posix_steps_declare_bash():
    """bench.yml used date/tee/[ which do not exist in pwsh."""
    doc = _load("bench.yml")
    steps = _jobs(doc)["bench"]["steps"]
    for step in steps:
        run = step.get("run", "")
        if any(tok in run for tok in ("$(date", "| tee", "[ -")):
            assert step.get("shell") == "bash", step.get("name")


def test_no_blanket_true_on_dependency_installs():
    for name in ("ci.yml", "release.yml", "bench.yml", "fuzz.yml", "sanitizers.yml"):
        raw = _raw(name)
        assert "pip install -r requirements.txt || true" not in raw, name
        assert "brew install" not in raw or "|| true" not in raw.split("brew install")[1][:200], name


def test_workflows_use_the_shared_composite_action():
    assert COMPOSITE.is_file()
    for name in ("ci.yml", "release.yml", "bench.yml", "sanitizers.yml"):
        assert "./.github/actions/setup-pengu" in _raw(name), name


def test_composite_action_caches_the_runtime_not_build_root():
    text = COMPOSITE.read_text(encoding="utf-8")
    assert "build/lib" in text and "build/include" in text
    assert "extern_manifest.py" in text
    # The whole build/ directory must never be cached.
    assert re.search(r"path:\s*\|\s*\n\s*build/\s*$", text, re.MULTILINE) is None


# --------------------------------------------------------------------------- #
# S5 — release integrity
# --------------------------------------------------------------------------- #


def test_release_publishes_checksums_and_prerelease_flag():
    raw = _raw("release.yml")
    assert "SHA256SUMS" in raw
    assert "--prerelease" in raw
    assert "--verify-tag" in raw
    assert "--notes-file" in raw


def test_release_validates_assets_are_not_empty():
    raw = _raw("release.yml")
    assert "expected at least" in raw


def test_bench_artifact_failure_is_not_swallowed():
    raw = _raw("bench.yml")
    assert "if-no-files-found: error" in raw


def test_no_dead_matrix_config():
    raw = _raw("ci.yml")
    assert "artifact_cmd" not in raw


def test_vsix_is_built_once():
    """The VSIX is platform independent: one job, not one per OS."""
    for name in ("ci.yml", "release.yml"):
        doc = _load(name)
        vsix_jobs = [
            job_name
            for job_name, job in _jobs(doc).items()
            if any("vsix" in (step.get("with") or {}).get("path", "")
                   for step in (job.get("steps") or []))
        ]
        assert vsix_jobs, f"{name} has no job that uploads a VSIX"
        assert len(vsix_jobs) == 1, vsix_jobs
        # It must not be part of the per-OS matrix.
        assert "strategy" not in _jobs(doc)[vsix_jobs[0]]


# --------------------------------------------------------------------------- #
# S6 — dependabot and the sanitizer plumbing
# --------------------------------------------------------------------------- #


def test_dependabot_covers_actions_pip_and_npm():
    doc = yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"] for u in doc["updates"]}
    assert {"github-actions", "pip", "npm"} <= ecosystems


def test_sanitizer_workflow_sets_the_flag_environment():
    doc = _load("sanitizers.yml")
    env = _jobs(doc)["asan-ubsan"]["env"]
    assert "address" in env["PENGU_CFLAGS"] and "undefined" in env["PENGU_CFLAGS"]
    assert "address" in env["PENGU_LDFLAGS"]


def test_env_flags_reach_the_compiler_and_the_cache_key():
    """PENGU_CFLAGS must both be forwarded and invalidate the cache."""
    text = (REPO / "pengu_project.py").read_text(encoding="utf-8")
    assert '_env_flag_list("PENGU_CFLAGS")' in text
    assert '_env_flag_list("PENGU_LDFLAGS")' in text
    assert '"env_cflags": os.environ.get("PENGU_CFLAGS"' in text
    conftest = (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "PENGU_CFLAGS" in conftest
    assert "PENGU_TEST_VALGRIND" in conftest


def test_fuzz_upload_runs_always():
    raw = _raw("fuzz.yml")
    assert "if: always()" in raw
    assert "if-no-files-found: ignore" in raw


# --------------------------------------------------------------------------- #
# S9 — Phase 8: the gates this phase added
# --------------------------------------------------------------------------- #


def test_every_workflow_file_is_covered_by_these_invariants():
    """A new workflow must not be able to skip the invariants above.

    `ALL_WORKFLOWS` is read from disk; this test exists so the reason is visible
    from the suite, and so a workflow added under another extension (`.yaml`) is
    noticed instead of silently ignored.
    """
    on_disk = sorted(p.name for p in WORKFLOWS.glob("*.yml"))
    assert ALL_WORKFLOWS == on_disk
    assert not list(WORKFLOWS.glob("*.yaml")), "a .yaml workflow would escape ALL_WORKFLOWS"


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_every_action_is_pinned_to_a_commit_sha(name):
    """Roadmap 8.15: `uses: owner/repo@v4` is a mutable reference.

    A tag can be re-pointed at any commit, so the workflow would execute code the
    review never saw. Every non-local `uses:` must be a full commit SHA with the
    human-readable version in a trailing comment.
    """
    for action, rest in re.findall(r"uses:\s*([^\s#]+)([^\n]*)", _raw(name)):
        if action.startswith(("./", "docker://")):
            continue
        assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action), (
            f"{name}: {action} is not pinned to a 40-hex commit SHA"
        )
        assert re.search(r"#\s*v\d", rest), f"{name}: {action} has no `# vX` comment"


def test_the_composite_action_is_pinned_too():
    text = COMPOSITE.read_text(encoding="utf-8")
    for action, rest in re.findall(r"uses:\s*([^\s#]+)([^\n]*)", text):
        if action.startswith(("./", "docker://")):
            continue
        assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action), action
        assert re.search(r"#\s*v\d", rest), action


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_no_job_timeout_exceeds_the_platform_ceiling(name):
    """Roadmap 8.16: GitHub kills a job after 6 h of execution.

    A larger `timeout-minutes` can never be reached, so it is a claim the platform
    will not honour. `fuzz.yml` used to declare 13 h (finding F8-N5).
    """
    for job_name, job in _jobs(_load(name)).items():
        assert int(job["timeout-minutes"]) <= 360, (
            f"{name}:{job_name} declares {job['timeout-minutes']} minutes > 360"
        )


def test_nightly_fuzz_budget_is_sharded_within_the_ceiling():
    """Roadmap 8.16: a 72 h-per-harness budget can only exist as shards.

    Shards are parallel *jobs*, so the invariant is about the fuzz seconds each
    harness consumes (``shards x per-shard budget <= 6 h``), not about wall clock:
    the default total must fit the platform ceiling and the workflow must divide it
    rather than trusting the input.
    """
    doc = _load("nightly.yml")
    job = _jobs(doc)["fuzz"]
    matrix = job["strategy"]["matrix"]
    assert set(matrix["harness"]) == {"parser", "bind", "semver", "lock", "lsp"}
    shards = len(matrix["shard"])
    assert shards >= 2, "a single shard cannot fit inside the 6 h ceiling"

    inputs = _triggers(doc)["workflow_dispatch"]["inputs"]
    hours = float(inputs["hours_per_harness"]["default"])
    assert hours <= 6, f"the default budget of {hours} h exceeds the platform ceiling"

    raw = _raw("nightly.yml")
    assert "21600" in raw, "nightly.yml must clamp to GitHub's 6 h ceiling"
    assert "total / SHARDS" in raw, "the budget must be divided across the shards"
    assert int(job["timeout-minutes"]) <= 360


def test_codeql_workflow_analyses_both_languages():
    """Roadmap 8.14: Python *and* the C runtime."""
    job = _jobs(_load("codeql.yml"))["analyze"]
    entries = job["strategy"]["matrix"]["include"]
    languages = {entry["language"] for entry in entries}
    assert {"python", "c-cpp"} <= languages, languages
    raw = _raw("codeql.yml")
    assert "github/codeql-action/init@" in raw
    assert "github/codeql-action/analyze@" in raw
    assert "security-extended" in raw, "the default query suite misses the memory-safety queries"
    assert all(entry["build-mode"] == "none" for entry in entries), entries


def test_cross_compile_workflow_produces_and_runs_a_pe():
    """Roadmap 8.12: a real `.exe`, validated by `file` and executed."""
    raw = _raw("cross-compile.yml")
    assert "gcc-mingw-w64-x86-64" in raw
    assert "x86_64-w64-mingw32-gcc" in raw
    assert "PE32+" in raw, "the .exe must be validated as a PE image, not assumed"
    assert "wine64" in raw, "the .exe must be executed, not just produced"
    assert "--target x86_64-w64-mingw32" in raw


def test_corpora_run_in_their_own_workflow():
    """Roadmap 8.13: both corpora are wired into CI."""
    raw = _raw("compliance.yml")
    assert "tests/test_compliance_corpus.py" in raw
    assert "tests/test_migration_corpus.py" in raw
    assert (REPO / "tests" / "migration" / "EXPECTED.json").is_file()


#: Ratchet (roadmap 8.6).  Raising coverage is a deliberate two-line change —
#: this constant and `.coveragerc` — and lowering it cannot happen by accident.
#: Measured on the commit that closed the phase: **80.20 %** over 19 235
#: statements (`pytest tests --cov --cov-config=.coveragerc`).  The configured
#: floor is 80, i.e. 0.2 points below the measurement, so a run whose collection
#: differs by a hair does not turn the ratchet into a coin flip; the audit records
#: both numbers and the command that produced them.
RECORDED_FLOOR = 80.0


def test_coverage_gate_is_wired_into_the_full_suite():
    """Roadmap 8.6: the full suite runs under coverage with a committed floor."""
    import configparser

    cfg = configparser.ConfigParser()
    cfg.read(REPO / ".coveragerc")
    floor = float(cfg["report"]["fail_under"])
    assert floor > 0, "a zero floor would make the gate vacuous"
    assert floor >= RECORDED_FLOOR, (
        f"the coverage floor was lowered: {floor} < {RECORDED_FLOOR}"
    )
    assert "pengu_project.py" in cfg["run"]["source"]
    assert "pengu_parser" in cfg["run"]["source"]

    raw = _raw("ci.yml")
    assert "--cov" in raw and ".coveragerc" in raw
    assert "coverage.xml" in raw
    assert "pytest-cov" in (REPO / "requirements.txt").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Phase 9 / item 9.5 — the documentation cannot promise a budget the platform
# will not honour.  GitHub kills a job after 6 h, so any "N hours per harness"
# claim above 6 in the two documents that state the fuzzing budget is a lie.
# --------------------------------------------------------------------------- #

FUZZ_DOCS = ("docs/FUZZING.md", "RELEASE_CHECKLIST.md")
HOURS_CLAIM = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:h\b|hours?\b)", re.IGNORECASE
)
NEGATIONS = ("not ", "never", "impossible", "cannot", "can't", "refuted", "no longer")


def _hour_claims(path):
    """Yield ``(lineno, hours, paragraph)`` for every hour figure in the file."""
    lines = (REPO / path).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        for match in HOURS_CLAIM.finditer(line):
            lo = index
            while lo > 0 and lines[lo - 1].strip():
                lo -= 1
            hi = index
            while hi + 1 < len(lines) and lines[hi + 1].strip():
                hi += 1
            paragraph = " ".join(lines[lo:hi + 1])
            yield index + 1, float(match.group(1)), paragraph


@pytest.mark.parametrize("path", FUZZ_DOCS)
def test_fuzz_docs_do_not_promise_more_than_github_allows(path):
    """The refuted claim: `72 hours per harness` in a document, 6 h in reality."""
    offenders = []
    for lineno, hours, paragraph in _hour_claims(path):
        if hours <= 6:
            continue
        lowered = paragraph.lower()
        if any(negation in lowered for negation in NEGATIONS):
            continue  # e.g. "a 72 h promise is *not* a budget"
        offenders.append(f"{path}:{lineno}: {hours} h -- {paragraph[:120]}")
    assert offenders == [], (
        "a fuzz budget above GitHub's 6 h per-job ceiling:\n" + "\n".join(offenders)
    )


def test_the_fuzz_workflows_state_the_same_budget_as_the_docs():
    """The documented numbers must match the YAML, not just each other."""
    nightly_doc = _load("nightly.yml")
    nightly = _jobs(nightly_doc)["fuzz"]
    inputs = _triggers(nightly_doc)["workflow_dispatch"]["inputs"]
    hours = float(inputs["hours_per_harness"]["default"])
    shards = len(nightly["strategy"]["matrix"]["shard"])
    assert hours == 6.0 and shards == 4
    # The invariant is about the fuzz seconds a harness consumes, not wall clock:
    # shards run in parallel (roadmap 8.16).
    assert hours * 60 <= 360, "the total per harness must fit the 6 h ceiling"
    per_shard = hours * 60 / shards
    assert int(nightly["timeout-minutes"]) > per_shard, (
        "a shard's timeout must leave room for checkout/build on top of its budget"
    )

    fuzz_doc = _load("fuzz.yml")
    fuzz = _jobs(fuzz_doc)["fuzz"]
    dispatch = _triggers(fuzz_doc)["workflow_dispatch"]["inputs"]
    assert dispatch["seconds"]["default"] == "21600", "6 h, the platform ceiling"
    assert int(fuzz["timeout-minutes"]) <= 360

    fuzzing_doc = (REPO / "docs" / "FUZZING.md").read_text(encoding="utf-8")
    assert "6 hours per harness across 4 shards" in fuzzing_doc
    checklist = (REPO / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    assert "6 h per harness (4 shards" in checklist


def test_the_compliance_corpus_runs_under_more_than_one_compiler():
    """Roadmap 10.3: the compiler matrix has to be a matrix *in CI*, not prose.

    Measured locally during Phase 10 (2026-10-07): gcc 54/54, clang 54/54, tcc
    not installed. A workflow that compiles every program with the default
    compiler and calls it a "matrix" is the failure mode this pins.
    """
    raw = _raw("compliance.yml")
    assert "matrix:" in raw, "compliance.yml declares no matrix"
    assert "cc: [gcc, clang]" in raw, "the matrix must name the compilers"
    assert "--cc ${{ matrix.cc }}" in raw, (
        "the matrix leg must pass the compiler to the runner, or every leg "
        "compiles with the default one"
    )
    assert "fail-fast: false" in raw, (
        "one compiler failing must not hide the other's result"
    )
