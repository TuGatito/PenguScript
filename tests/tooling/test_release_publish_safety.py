"""Regression tests for the release publishing path.

The `Publish GitHub Release` job of `release.yml` died with exit code 127
(`pengu: command not found`) and no release was created, because the release
title was spliced into the shell script with
`${{ steps.changelog.outputs.title }}`.  That title comes from the CHANGELOG
heading

    ## [2.1.0] — 2026-10-13 — Binding templates & `pengu add` fixes

and GitHub substitutes the expression *before* bash parses the script, so the
backticks became a command substitution.  `ci.yml` interpolated the same title
into `git tag -a -m` and got away with it only because the failure was silent:
the v2.1.0 tag carries a mutilated message (`… Binding templates &  fixes`).

These tests keep free-form text (a CHANGELOG heading, a `workflow_dispatch`
input) out of every `run:` script, and execute the publish script verbatim
against a stub `gh` so the failure cannot come back unnoticed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterator, Tuple

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"

#: Any `${{ … }}` expression: everything GitHub substitutes before bash runs.
_EXPRESSION_RE = re.compile(r"\$\{\{[^{}]*\}\}")
#: An expression reading the changelog title (the value with backticks in it).
_TITLE_EXPRESSION_RE = re.compile(r"\$\{\{[^{}]*outputs\.title[^{}]*\}\}")
#: The only values a `run:` script may interpolate: things the workflow itself
#: defines (`matrix.*`) or GitHub's fixed vocabulary (`github.event_name`).
_ALLOWED_EXPRESSION_RE = re.compile(
    r"^\$\{\{\s*(?:matrix\.[A-Za-z0-9_]+|github\.event_name)\s*\}\}$"
)

_WORKFLOW_NAMES = sorted(path.name for path in WORKFLOWS.glob("*.yml"))


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _steps(doc: dict) -> Iterator[Tuple[str, dict]]:
    """Yields ``(job name, step)`` for every step of every job."""
    for job_name, job in (doc.get("jobs") or {}).items():
        for step in (job or {}).get("steps") or []:
            if isinstance(step, dict):
                yield job_name, step


def _run_steps(doc: dict) -> Iterator[Tuple[str, str, str]]:
    """Yields ``(job name, step name, run script)`` for every ``run:`` step."""
    for job_name, step in _steps(doc):
        script = step.get("run")
        if isinstance(script, str):
            yield job_name, step.get("name") or "<unnamed>", script


def _find_step(doc: dict, name: str) -> dict:
    for _job_name, step in _steps(doc):
        if step.get("name") == name:
            return step
    raise AssertionError(f"no workflow step named {name!r}")


def _import_make_release():
    """Loads the repository-root ``make_release.py`` without touching sys.path."""
    spec = importlib.util.spec_from_file_location(
        "make_release_under_test", REPO / "make_release.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Static guards: no workflow may execute free-form text.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", _WORKFLOW_NAMES)
def test_no_workflow_interpolates_the_changelog_title_into_a_script(name: str) -> None:
    offenders = [
        f"{job} / {step}"
        for job, step, script in _run_steps(_load(name))
        if _TITLE_EXPRESSION_RE.search(script)
    ]
    assert offenders == [], (
        f"{name}: the changelog title is free-form text; pass it through the step "
        f"`env:` instead of `${{{{ … }}}}` (offending steps: {offenders})"
    )


@pytest.mark.parametrize("name", _WORKFLOW_NAMES)
def test_run_scripts_only_interpolate_workflow_defined_values(name: str) -> None:
    """The repo-wide rule: text from a file or an input never reaches `run:`."""
    offenders = [
        f"{job} / {step} -> {expression}"
        for job, step, script in _run_steps(_load(name))
        for expression in _EXPRESSION_RE.findall(script)
        if not _ALLOWED_EXPRESSION_RE.match(expression)
    ]
    assert offenders == [], (
        f"{name}: pass these through the step `env:` instead of `${{{{ … }}}}` "
        f"(offending steps: {offenders})"
    )


def test_publish_step_passes_the_title_through_the_environment() -> None:
    step = _find_step(_load("release.yml"), "Publish GitHub Release")
    env: Dict[str, str] = step.get("env") or {}
    assert _TITLE_EXPRESSION_RE.search(str(env.get("RELEASE_TITLE", ""))), (
        "Publish GitHub Release must read the title from RELEASE_TITLE"
    )
    assert not _EXPRESSION_RE.search(step["run"]), (
        "the publish script is executed verbatim by the test below: it must not "
        "contain any GitHub expression"
    )


def test_auto_tag_takes_its_message_and_version_from_the_environment() -> None:
    doc = _load("ci.yml")
    tag_step = _find_step(doc, "Create Git Tag if Not Exists")
    env: Dict[str, str] = tag_step.get("env") or {}
    assert _TITLE_EXPRESSION_RE.search(str(env.get("CHANGELOG_TITLE", "")))
    assert _EXPRESSION_RE.search(str(env.get("CHANGELOG_TAG", "")))
    script = tag_step["run"]
    assert not _EXPRESSION_RE.search(script)
    assert '"$CHANGELOG_TITLE"' in script, "git tag -m must use the environment value"

    dispatch = _find_step(doc, "Dispatch the publishing workflow for the new tag")
    dispatch_env: Dict[str, str] = dispatch.get("env") or {}
    assert "CHANGELOG_TAG" in dispatch_env
    assert not _EXPRESSION_RE.search(dispatch["run"])


@pytest.mark.parametrize("name", ["ci.yml", "release.yml"])
def test_vsix_steps_sync_the_extension_version_after_npm_ci(name: str) -> None:
    script = _find_step(_load(name), "Build VSIX")["run"]
    assert "--sync-extension-version" in script, (
        f"{name}: a bare `vsce package` stamps the .vsix with the extension "
        f"manifest's own version (the v2.1.0 release shipped pengus-2.0.0.vsix)"
    )
    assert script.index("npm ci") < script.index("--sync-extension-version"), (
        f"{name}: sync after `npm ci`, which validates package-lock.json"
    )


# ---------------------------------------------------------------------------
# Behavioural guard: run the publish script exactly as bash sees it.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="the publish step is a POSIX shell script",
)
@pytest.mark.parametrize("prerelease", ["false", "true"])
def test_publish_script_keeps_a_backticked_title_literal(tmp_path, prerelease: str) -> None:
    script = _find_step(_load("release.yml"), "Publish GitHub Release")["run"]
    assert not _EXPRESSION_RE.search(script)

    bindir = tmp_path / "bin"
    bindir.mkdir()
    args_file = tmp_path / "gh-args.txt"
    gh = bindir / "gh"
    gh.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$GH_ARGS_FILE"\n',
        encoding="utf-8",
    )
    gh.chmod(0o755)

    (tmp_path / "release_notes.md").write_text("notes\n", encoding="utf-8")
    assets = tmp_path / "final-assets"
    assets.mkdir()
    (assets / "pengu-linux-x64.tar.gz").write_text("x", encoding="utf-8")

    title = "PenguScript v2.1.1 - 2026-10-13 — Binding templates & `pengu add` fixes"
    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{bindir}{os.pathsep}{env.get('PATH', '')}",
            "GH_TOKEN": "stub",
            "GH_ARGS_FILE": str(args_file),
            "RELEASE_TITLE": title,
            "RELEASE_TAG": "v2.1.1",
            "IS_PRERELEASE": prerelease,
        }
    )

    proc = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"

    argv = args_file.read_text(encoding="utf-8").splitlines()
    assert argv[:2] == ["release", "create"], argv
    assert "v2.1.1" in argv
    assert title in argv, f"the title was mangled: {argv}"
    assert ("--prerelease" in argv) is (prerelease == "true")


# ---------------------------------------------------------------------------
# The version sync itself.
# ---------------------------------------------------------------------------
def test_sync_extension_version_uses_VERSION_and_is_idempotent(tmp_path) -> None:
    make_release = _import_make_release()
    manifest = tmp_path / "package.json"
    manifest.write_text(
        json.dumps({"name": "pengus", "version": "0.0.1"}, indent=4) + "\n",
        encoding="utf-8",
    )

    expected = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert make_release.sync_extension_version(manifest) is True
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == expected
    # A second run is a no-op, so the release workflow can always call it.
    assert make_release.sync_extension_version(manifest) is False

    assert make_release.sync_extension_version(manifest, "9.9.9") is True
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == "9.9.9"
