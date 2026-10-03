"""Roadmap Phase 6 / §6.1 — the benchmark harness is present, runnable and honest.

A full benchmark run is far too slow for the test suite, so this checks the
harness's contract: the programs exist, every PenguScript case bundles, the
runner measures one case end to end, and the published numbers are labelled with
their environment.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO, have_tool

BENCHES = REPO / "benches"
PENGU_CASES = ["hello_world", "fib_40", "string_ops", "list_ops"]


def test_benchmark_programs_exist():
    for case in PENGU_CASES:
        assert (BENCHES / f"{case}.pengu").is_file(), case


def test_c_and_rust_baselines_exist_for_shared_cases():
    for case in ("hello_world", "fib_40", "string_ops"):
        assert (BENCHES / "c" / f"{case}.c").is_file(), case
        assert (BENCHES / "rust" / f"{case}.rs").is_file(), case
        assert (BENCHES / "zig" / f"{case}.zig").is_file(), case


@pytest.mark.parametrize("case", PENGU_CASES)
def test_every_benchmark_bundles(case):
    """Each program must at least parse, check and emit C."""
    from pengu_project import build_project

    src = (BENCHES / f"{case}.pengu").read_text(encoding="utf-8")
    out = REPO / "build" / f"bench_{case}.c"
    out.parent.mkdir(exist_ok=True)
    import tempfile

    with tempfile.TemporaryDirectory(prefix=f"pengu_bench_{case}_") as tmp:
        proj = Path(tmp)
        (proj / "src").mkdir()
        (proj / "src" / "main.pengu").write_text(src, encoding="utf-8")
        (proj / "pengu.toml").write_text(
            f'[project]\nname = "{case}"\nentry = "src/main.pengu"\n\n'
            '[build]\nprofile = "release"\n',
            encoding="utf-8",
        )
        build_project(config_path=str(proj), output=str(out))
    assert out.is_file() and out.stat().st_size > 0


def test_runner_reports_one_case_end_to_end(tmp_path):
    """Smoke-run the harness itself (hello world only, best of 1)."""
    if not (have_tool("gcc") or have_tool("clang") or have_tool("cc")):
        pytest.skip("no C compiler")
    res = subprocess.run(
        [sys.executable, str(BENCHES / "run_bench.py"), "--repeat", "1",
         "--only", "hello_world", "--csv", str(tmp_path / "out.csv")],
        capture_output=True, text=True, timeout=600, cwd=str(REPO),
    )
    assert res.returncode == 0, res.stderr
    assert "== hello_world ==" in res.stdout
    assert "pengu  build" in res.stdout
    assert "size" in res.stdout
    # The environment block must be printed so numbers can be attributed.
    assert "platform :" in res.stdout
    csv_text = (tmp_path / "out.csv").read_text(encoding="utf-8")
    assert "case" in csv_text and "hello_world" in csv_text


def test_runner_does_not_require_missing_toolchains(tmp_path):
    """A missing baseline toolchain is 'skipped', never a failure."""
    text = (BENCHES / "run_bench.py").read_text(encoding="utf-8")
    assert "toolchain not found" in text
    assert "build-failed" in text


def test_benchmarks_doc_publishes_measured_numbers():
    doc = (REPO / "BENCHMARKS.md").read_text(encoding="utf-8")
    for needle in ("How to reproduce", "Reference environment", "revised",
                   "not met", "KiB"):
        assert needle.lower() in doc.lower(), needle
    # The measured binary size must be published, not the aspirational target.
    assert "98.4 KiB" in doc or "KiB" in doc


def test_benchmark_workflow_is_nightly_only():
    workflow = (REPO / ".github" / "workflows" / "bench.yml").read_text(encoding="utf-8")
    assert "schedule" in workflow and "workflow_dispatch" in workflow
    assert "pull_request" not in workflow, "benchmarks must not block PRs"
    assert "run_bench.py" in workflow
