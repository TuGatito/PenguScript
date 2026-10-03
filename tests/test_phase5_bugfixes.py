"""Roadmap Phase 5 / §5.0 — audit-driven bug fixes (pre-flight).

Each test pins one finding from the Phase 5 audit.  Findings that the audit got
wrong are recorded as *refutation* tests so nobody "fixes" working behaviour.
"""

import os
import subprocess
import sys

import pytest

from pengu_project import (
    ProjectConfig,
    _dump_toml,
    _lock_target,
    add_dependency,
    init_project,
    remove_dependency,
)
from tests.conftest import REPO, gen_bundle, have_tool

# --------------------------------------------------------------------------- #
# BUG-5.7 — _dump_toml must not turn None into ""
# --------------------------------------------------------------------------- #


def test_dump_toml_rejects_none():
    with pytest.raises(TypeError):
        _dump_toml({"key": None})
    with pytest.raises(TypeError):
        _dump_toml({"nested": {"key": None}})


def test_dump_toml_still_handles_valid_values():
    text = "\n".join(_dump_toml({"a": "s", "b": 1, "c": True, "d": ["x"], "e": 1.5}))
    assert 'a = "s"' in text and "b = 1" in text and "c = true" in text


# --------------------------------------------------------------------------- #
# BUG-5.8 — lock target triples are canonicalized
# --------------------------------------------------------------------------- #


def test_lock_target_folds_equivalent_windows_triples():
    mingw = _lock_target(ProjectConfig(target="x86_64-w64-mingw32"))
    gnu = _lock_target(ProjectConfig(target="x86_64-pc-windows-gnu"))
    assert mingw == gnu == "x86_64-windows-gnu"


def test_lock_target_keeps_distinct_platforms_distinct():
    assert _lock_target(ProjectConfig(target="aarch64-apple-darwin")) == "aarch64-darwin"
    assert _lock_target(ProjectConfig(target="x86_64-unknown-linux-gnu")) == "x86_64-linux-gnu"


def test_lock_target_defaults_to_host():
    assert _lock_target(ProjectConfig(target=""))


# --------------------------------------------------------------------------- #
# BUG-5.9 — the emitted bundle asserts the runtime ABI version
# --------------------------------------------------------------------------- #


def test_bundle_static_asserts_abi_version():
    c = gen_bundle("weave main into int:\n  return 0\n")
    assert "_Static_assert(PENGU_ABI_VERSION == 1" in c
    # Guarded so strict C99 (no _Static_assert) still compiles.
    assert "__STDC_VERSION__" in c


def test_bundle_abi_assert_is_c99_safe():
    if not have_tool("gcc"):
        pytest.skip("gcc not available")
    c = gen_bundle("weave main into int:\n  return 0\n")
    path = REPO / "build" / "_abi_assert_check.c"
    path.parent.mkdir(exist_ok=True)
    path.write_text(c, encoding="utf-8")
    try:
        res = subprocess.run(
            ["gcc", "-std=c99", "-pedantic-errors", "-fsyntax-only",
             "-I", str(REPO), "-I", str(REPO / "build"), "-I", str(REPO / "build" / "include"),
             str(path)],
            capture_output=True, text=True,
        )
        assert res.returncode == 0, res.stderr
    finally:
        path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# BUG-5.10 / BUG-5.17 — diagnostics arrive from the checker, with unique codes
# --------------------------------------------------------------------------- #


def _diagnostics_for(source: str):
    from tests.conftest import BUILD_DIR

    d = BUILD_DIR / "phase5_diag"
    d.mkdir(parents=True, exist_ok=True)
    (d / "src").mkdir(exist_ok=True)
    (d / "src" / "main.pengu").write_text(source, encoding="utf-8")
    (d / "pengu.yaml").write_text(
        "project:\n  name: diag\n  entry: src/main.pengu\n", encoding="utf-8"
    )
    from pengu_project import PenguBuilder

    cfg = ProjectConfig.load(str(d))
    ok, diags = PenguBuilder(cfg).check_sources_diagnostics()
    return ok, diags


def test_error_literal_outside_or_block_has_unique_code():
    ok, diags = _diagnostics_for(
        "weave main into int:\n"
        "  var x as int is error\n"
        "  return x\n"
    )
    codes = {d["code"] for d in diags}
    assert not ok
    assert "E0058" in codes, f"expected E0058, got {codes}"
    assert "E0015" not in codes


def test_error_codes_are_unique_per_class():
    """No two distinct error classes may share a code."""
    import inspect

    from pengu_parser import pengu_errors

    seen: dict = {}
    duplicates = []
    for _name, obj in inspect.getmembers(pengu_errors, inspect.isclass):
        code = getattr(obj, "code", None)
        if not isinstance(code, str) or not code.startswith("E"):
            continue
        if code in seen and seen[code] is not obj:
            # Subclasses inheriting the same code from a shared base are fine.
            if not (issubclass(obj, seen[code]) or issubclass(seen[code], obj)):
                duplicates.append(f"{code}: {seen[code].__name__} vs {obj.__name__}")
        seen.setdefault(code, obj)
    assert not duplicates, "duplicate error codes:\n  " + "\n  ".join(duplicates)


# --------------------------------------------------------------------------- #
# BUG-5.14 — oversized headers are rejected before pycparser
# --------------------------------------------------------------------------- #


def test_oversized_header_is_rejected(tmp_path, monkeypatch):
    from pengu_bind import _check_header_size

    monkeypatch.setenv("PENGU_BIND_MAX_BYTES", "64")
    big = tmp_path / "big.h"
    big.write_text("int x;\n" * 100, encoding="utf-8")
    # HeaderParseError derives from RuntimeError (pengu_bind has its own base).
    with pytest.raises(RuntimeError) as exc:
        _check_header_size(str(big))
    assert "too large" in str(exc.value)


def test_small_header_is_accepted(tmp_path, monkeypatch):
    from pengu_bind import _check_header_size

    monkeypatch.setenv("PENGU_BIND_MAX_BYTES", "1024")
    small = tmp_path / "small.h"
    small.write_text("int x;\n", encoding="utf-8")
    _check_header_size(str(small))  # must not raise


# --------------------------------------------------------------------------- #
# BUG-5.15 — dependency build scripts require explicit trust
# --------------------------------------------------------------------------- #


def _dep_with_build_script(tmp_path, marker: str):
    dep = tmp_path / "dep"
    (dep / "pengu").mkdir(parents=True)
    (dep / "pengu" / "m.pengu").write_text("weave f into int:\n  return 1\n", encoding="utf-8")
    (dep / "build.py").write_text(
        f"open({marker!r}, 'w').write('ran')\n", encoding="utf-8"
    )
    return dep


def test_build_script_skipped_without_trust(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PENGU_TRUST_ALL", raising=False)
    marker = str(tmp_path / "ran.txt")
    dep = _dep_with_build_script(tmp_path, marker)
    init_project("t_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "t_app")

    add_dependency(source=str(dep), name="dep", config_path=proj, run_build=True)
    assert not os.path.exists(marker), "build.py ran without trust"
    assert "not trusted" in capsys.readouterr().err


def test_build_script_runs_with_trust(tmp_path, monkeypatch):
    monkeypatch.delenv("PENGU_TRUST_ALL", raising=False)
    marker = str(tmp_path / "ran.txt")
    dep = _dep_with_build_script(tmp_path, marker)
    init_project("t2_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "t2_app")

    add_dependency(source=str(dep), name="dep", config_path=proj, run_build=True,
                   trusted=True)
    assert os.path.exists(marker), "trusted build.py did not run"


def test_trust_all_env_bypasses_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_TRUST_ALL", "1")
    marker = str(tmp_path / "ran.txt")
    dep = _dep_with_build_script(tmp_path, marker)
    init_project("t3_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "t3_app")

    add_dependency(source=str(dep), name="dep", config_path=proj, run_build=True)
    assert os.path.exists(marker)


# --------------------------------------------------------------------------- #
# Refutations — behaviour the audit reported as broken but which works
# --------------------------------------------------------------------------- #


def _checker_warnings(source: str):
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    checker = PenguChecker(base_dir=".")
    checker.check(PenguParser().parse(source), source=source, filename="t.pengu")
    return [str(w) for w in checker.warnings]


def test_refutation_deprecated_emits_w0006_for_weave():
    """BUG-5.1 claimed W0006 is dead code; the inferrer does emit it."""
    warnings = _checker_warnings(
        '@deprecated("use new_fn")\n'
        "weave old_fn into int:\n"
        "  return 1\n\n"
        "weave main into int:\n"
        "  return calling old_fn\n"
    )
    assert any("W0006" in w and "old_fn" in w for w in warnings), warnings


def test_refutation_deprecated_emits_w0006_for_rune():
    """BUG-5.2 claimed @deprecated never reaches rune symbols."""
    warnings = _checker_warnings(
        '@deprecated("use NewRune")\n'
        "rune OldRune:\n"
        "  x as int\n\n"
        "rune NewRune:\n"
        "  y as int\n\n"
        "weave main into int:\n"
        "  var r as OldRune is with x is 1\n"
        "  return r.x\n"
    )
    assert any("W0006" in w and "OldRune" in w for w in warnings), warnings


def test_refutation_format_lookahead_is_in_bounds():
    """BUG-5.4: `p[3]` is only read when p[1] and p[2] are non-NUL."""
    header = (REPO / "pengu_runtime.h").read_text(encoding="utf-8")
    line = next(ln for ln in header.splitlines() if "p[1] == 'l' && p[2] == 'l'" in ln)
    # The && chain short-circuits, so p[3] cannot be read past the terminator.
    assert line.index("p[1]") < line.index("p[2]") < line.index("p[3]")
