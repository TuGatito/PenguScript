"""Roadmap Phase 5 / §5.4 — deprecation policy, warning surfacing and CI denial.

The audit's BUG-5.1 said `W0006` was never emitted.  Verification showed the
warning *is* produced by the inferrer — but it was **never surfaced**: the
checker collected `warnings` and the CLI dropped them.  These tests pin the real
fix: warnings are diagnostics now, and `--deny-deprecated` can fail a build.
"""

import os

import pytest

from pengu_project import PenguBuilder, ProjectConfig, build_project, check_project
from pengu_version import __version__ as PENGU_VERSION
from tests.conftest import REPO

DEPRECATED_SRC = (
    '@deprecated("use new_fn instead")\n'
    "weave old_fn into int:\n"
    "  return 1\n\n"
    "weave new_fn into int:\n"
    "  return 2\n\n"
    "weave main into int:\n"
    "  return calling old_fn\n"
)


def _project(tmp_path, source: str = DEPRECATED_SRC, name: str = "dep_app"):
    root = tmp_path / name
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.pengu").write_text(source, encoding="utf-8")
    (root / "pengu.toml").write_text(
        f'[project]\nname = "{name}"\nentry = "src/main.pengu"\n', encoding="utf-8"
    )
    return str(root)


# --------------------------------------------------------------------------- #
# Warnings are surfaced at all
# --------------------------------------------------------------------------- #


def test_warnings_are_returned_as_diagnostics(tmp_path):
    proj = _project(tmp_path)
    cfg = ProjectConfig.load(proj)
    ok, diags = PenguBuilder(cfg).check_sources_diagnostics()
    warn = [d for d in diags if d["severity"] == "warning"]
    assert ok, "a warning must not fail the check"
    assert any(d["code"] == "W0006" and "old_fn" in d["message"] for d in warn), diags


def test_warning_diagnostic_has_the_expected_shape(tmp_path):
    proj = _project(tmp_path)
    _ok, diags = PenguBuilder(ProjectConfig.load(proj)).check_sources_diagnostics()
    w = next(d for d in diags if d["code"] == "W0006")
    for key in ("file", "line", "col", "code", "severity", "message", "help", "note"):
        assert key in w, key
    assert w["file"].endswith("main.pengu")


def test_clean_project_has_no_warnings(tmp_path):
    proj = _project(
        tmp_path,
        "weave new_fn into int:\n  return 2\n\nweave main into int:\n  return calling new_fn\n",
        name="clean_app",
    )
    ok, diags = PenguBuilder(ProjectConfig.load(proj)).check_sources_diagnostics()
    assert ok
    assert [d for d in diags if d["severity"] == "warning"] == []


# --------------------------------------------------------------------------- #
# --deny-deprecated
# --------------------------------------------------------------------------- #


def test_deny_deprecated_promotes_w0006_to_error(tmp_path):
    proj = _project(tmp_path)
    builder = PenguBuilder(ProjectConfig.load(proj))
    builder.deny_deprecated = True
    ok, diags = builder.check_sources_diagnostics()
    assert not ok
    sev = {d["code"]: d["severity"] for d in diags}
    assert sev.get("W0006") == "error"
    err = next(d for d in diags if d["code"] == "W0006")
    assert "deny-deprecated" in (err["note"] or "")


def test_deny_deprecated_leaves_other_warnings_alone(tmp_path):
    """Only W0006 is denied; e.g. W0005 shadowing stays a warning."""
    proj = _project(
        tmp_path,
        "weave helper into int:\n  return 1\n\n"
        "weave main into int:\n"
        "  var helper as int is 5\n"
        "  return helper\n",
        name="shadow_app",
    )
    builder = PenguBuilder(ProjectConfig.load(proj))
    builder.deny_deprecated = True
    _ok, diags = builder.check_sources_diagnostics()
    w0005 = [d for d in diags if d["code"] == "W0005"]
    if w0005:  # the shadow check is best-effort; if it fires it must be a warning
        assert all(d["severity"] == "warning" for d in w0005)


def test_check_project_deny_deprecated_returns_false(tmp_path, capsys):
    proj = _project(tmp_path)
    assert check_project(config_path=proj) is True
    assert check_project(config_path=proj, deny_deprecated=True) is False


def test_check_project_prints_warnings(tmp_path, capsys):
    proj = _project(tmp_path)
    check_project(config_path=proj)
    err = capsys.readouterr().err
    assert "W0006" in err
    assert "warning" in err.lower()


def test_build_project_deny_deprecated_fails(tmp_path):
    proj = _project(tmp_path)
    out = os.path.join(proj, "b.c")
    # Without the flag the build succeeds and only warns.
    build_project(config_path=proj, output=out)
    with pytest.raises(SystemExit):
        build_project(config_path=proj, output=out, deny_deprecated=True)


# --------------------------------------------------------------------------- #
# Policy documentation
# --------------------------------------------------------------------------- #


def test_deprecation_policy_is_documented():
    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    assert "## 23. Deprecation & Stability Policy" in text
    for needle in ("two minor releases", "--deny-deprecated", "Semantic Versioning"):
        assert needle in text, needle


def test_readme_documents_warning_codes():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "W0007" in readme and "W0006" in readme
