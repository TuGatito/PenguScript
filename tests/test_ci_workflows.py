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

ALL_WORKFLOWS = ["ci.yml", "release.yml", "bench.yml", "fuzz.yml", "sanitizers.yml"]


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
    out = subprocess.run([sys.executable, str(RELEASE_VERSION)],
                         capture_output=True, text=True, cwd=str(REPO))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "v0.16.0", out.stdout


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
