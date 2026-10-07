"""Dead-code elimination, TCC integration and PCH behaviour."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import pengu_dce
from pengu_tcc import find_tcc, pick_dev_compiler, tcc_available
from tests.conftest import REPO, requires_cc, requires_runtime


# ---------------------------------------------------------------------------
# DCE
# ---------------------------------------------------------------------------

def _bundle_of(source: str, tmp_path: Path) -> str:
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "prog.pengu"
    script.write_text(source, encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path), output=OutputType.C,
                        output_name="prog", name="prog",
                        build_dir=str(tmp_path / "b"))
    builder = PenguBuilder(cfg)
    builder.entry_as_main = True
    bundle, _ = builder.bundle()
    return Path(bundle).read_text(encoding="utf-8")


def test_prune_weaves_keeps_non_std_and_reachable_std(tmp_path):
    std = str(tmp_path / "std" / "m.pengu")
    proj = str(tmp_path / "main.pengu")
    util = str(tmp_path / "util.pengu")
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": proj,
         "refs": {"helper"}},
        {"name": "helper", "c_name": "helper", "filepath": util,
         "refs": {"used_std"}},
        {"name": "used_std", "c_name": "used_std", "filepath": std,
         "refs": set()},
        {"name": "unused_std", "c_name": "unused_std", "filepath": std,
         "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    kept_names = {w["name"] for w in kept}
    assert kept_names == {"main", "helper", "used_std"}
    assert {w["name"] for w in dropped} == {"unused_std"}


def test_prune_weaves_keeps_std_transitively(tmp_path):
    std = str(tmp_path / "std" / "m.pengu")
    proj = str(tmp_path / "main.pengu")
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": proj,
         "refs": {"a"}},
        {"name": "a", "c_name": "a", "filepath": std, "refs": {"b"}},
        {"name": "b", "c_name": "b", "filepath": std, "refs": set()},
        {"name": "c", "c_name": "c", "filepath": std, "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert {w["name"] for w in kept} == {"main", "a", "b"}
    assert {w["name"] for w in dropped} == {"c"}


def test_prune_weaves_matches_short_names_inside_a_module(tmp_path):
    """``spark_println`` must be kept when a call site writes ``println``."""
    std = str(tmp_path / "std" / "spark.pengu")
    proj = str(tmp_path / "main.pengu")
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": proj,
         "refs": {"spark", "println"}},
        {"name": "spark_println", "c_name": "spark_println", "filepath": std,
         "refs": set()},
        {"name": "spark_version", "c_name": "spark_version", "filepath": std,
         "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert {w["name"] for w in kept} == {"main", "spark_println"}
    assert {w["name"] for w in dropped} == {"spark_version"}


def test_prune_weaves_ignores_the_module_alias(tmp_path):
    """A weave ending in the module name must not be kept by its own suffix.

    Regression: ``unused_vendor`` used to be reduced to the spelling ``vendor``,
    which every call site contains as the module alias, so nothing inside a
    ``lib/`` binding was ever pruned.
    """
    vendor = str(tmp_path / "lib" / "vendor" / "pengu" / "vendor.pengu")
    proj = str(tmp_path / "main.pengu")
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": proj,
         "refs": {"vendor", "used_vendor"}},
        {"name": "used_vendor", "c_name": "used_vendor", "filepath": vendor,
         "refs": set()},
        {"name": "unused_vendor", "c_name": "unused_vendor", "filepath": vendor,
         "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert {w["name"] for w in kept} == {"main", "used_vendor"}
    assert {w["name"] for w in dropped} == {"unused_vendor"}


def test_is_prunable_module_only_matches_std_and_lib(tmp_path):
    # The repository's bundled std/ and a project's lib/ are prunable...
    assert pengu_dce.is_prunable_module(str(REPO / "std" / "spark.pengu"))
    assert pengu_dce.is_prunable_module("/proj/lib/vendor/pengu/v.pengu", "/proj")
    # ...but user source is not, and neither is a project that merely *lives*
    # under a directory called 'lib'.
    assert not pengu_dce.is_prunable_module("/proj/src/main.pengu", "/proj")
    assert not pengu_dce.is_prunable_module("/home/me/lib/proj/main.pengu",
                                            "/home/me/lib/proj")
    # Bindings are emitted as a unit (C declarations + enchanting glue).
    assert not pengu_dce.is_prunable_module(str(REPO / "std" / "sqlite3.d.pengu"))


def test_is_prunable_module_rejects_an_empty_path():
    """No path means no module to prune (the pass is called with optional data)."""
    assert pengu_dce.is_prunable_module("") is False


def test_is_prunable_module_survives_a_cross_drive_relative_path(monkeypatch):
    """On Windows a path and a root can sit on different drives.

    ``os.path.relpath`` raises ``ValueError`` for that pair instead of returning
    a relative path; the pass must treat the root as "not a match" rather than
    propagate the error out of the compiler.
    """
    import pengu_parser.pengu_dce as dce_impl
    import os as _os

    def boom(*_args, **_kwargs):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(_os.path, "relpath", boom)
    assert dce_impl.is_prunable_module("C:/proj/std/m.pengu", "D:/proj") is False


def test_module_stem_strips_only_the_pengu_suffixes():
    """``std/spark.pengu`` -> ``spark``; an unknown path is returned untouched.

    The stem is what ``_is_referenced`` strips as the module prefix, so getting
    it wrong would either prune live weaves or keep dead ones.
    """
    from pengu_parser import pengu_dce as dce_impl

    assert dce_impl._module_stem("std/spark.pengu") == "spark"
    assert dce_impl._module_stem("sqlite3.d.pengu") == "sqlite3"
    assert dce_impl._module_stem("lib/vendor/nodot") == "nodot"
    assert dce_impl._module_stem("") == ""


def test_prune_weaves_uses_the_stem_of_a_suffix_less_filepath(tmp_path):
    """A prunable weave whose file carries no ``.pengu`` suffix still resolves.

    ``is_prunable_module`` decides by directory, not by extension, so the
    module-prefix stripping has to cope with a suffix-less path.
    """
    std = str(tmp_path / "std" / "nodot")
    proj = str(tmp_path / "main.pengu")
    weaves = [
        {"name": "main", "c_name": "pengu_main", "filepath": proj,
         "refs": {"helper"}},
        {"name": "helper", "c_name": "helper", "filepath": std, "refs": set()},
        {"name": "unused", "c_name": "unused", "filepath": std, "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert {w["name"] for w in kept} == {"main", "helper"}
    assert {w["name"] for w in dropped} == {"unused"}


def test_prune_weaves_roots_a_main_declared_inside_a_prunable_module(tmp_path):
    """``main`` is a root even when it lives in a prunable module.

    The code generator accepts an entry point that a ``std``/``lib`` module
    declares; pruning it would emit a bundle with no ``pengu_main``.
    """
    std = str(tmp_path / "std" / "entry.pengu")
    weaves = [
        {"name": "unused", "c_name": "unused", "filepath": std, "refs": set()},
        {"name": "main", "c_name": "pengu_main", "filepath": std, "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert [w["name"] for w in kept] == ["main"]
    assert [w["name"] for w in dropped] == ["unused"]


def test_prune_weaves_never_drops_generic_templates_or_instances(tmp_path):
    """Generic templates and their monomorphizations survive the pass.

    The instances are created *during* body generation -- after this pass has
    already run -- so their substitution must stay exactly as the call sites
    built it; dropping the template or an instance would lose the program.
    """
    std = str(tmp_path / "std" / "m.pengu")
    weaves = [
        {"name": "tpl", "c_name": "tpl", "filepath": std, "refs": set(),
         "is_generic": True},
        {"name": "inst", "c_name": "inst", "filepath": std, "refs": set(),
         "subst_map": {"T": "int"}},
        {"name": "dead", "c_name": "dead", "filepath": std, "refs": set()},
    ]
    kept, dropped = pengu_dce.prune_weaves(weaves, base_dir=str(tmp_path))
    assert {w["name"] for w in kept} == {"tpl", "inst"}
    assert {w["name"] for w in dropped} == {"dead"}


# ---------------------------------------------------------------------------
# DCE reference collection
# ---------------------------------------------------------------------------

def test_collect_references_ignores_non_tree_entries():
    """The statement lists handed in may hold plain values (comments, markers)."""
    assert pengu_dce.collect_references([42, "not a tree", None]) == set()


def test_collect_references_survives_a_broken_scan(monkeypatch):
    """A tree whose token scan fails must not abort the pass.

    The reference set is deliberately best effort: an unexpected node shape
    loses precision (something may be kept that could be dropped) but must never
    break the build.
    """
    from lark import Tree

    def boom(*_args, **_kwargs):
        raise RuntimeError("unexpected node shape")

    monkeypatch.setattr(Tree, "scan_values", boom)
    assert pengu_dce.collect_references([Tree("stmt", [])]) == set()


def test_collect_references_survives_a_broken_walk(monkeypatch):
    """Same contract for the subtree walk that looks for interpolated strings."""
    from lark import Tree

    def boom(*_args, **_kwargs):
        raise RuntimeError("cannot walk")

    monkeypatch.setattr(Tree, "iter_subtrees", boom)
    assert pengu_dce.collect_references([Tree("stmt", [])]) == set()


def test_collect_references_reads_interpolated_expressions_by_text(monkeypatch):
    """Identifiers inside ``"{…}"`` are collected from the literal's text.

    The compiler re-parses those expressions later, so they are not part of the
    AST; scanning the text is what keeps ``cb64_char`` alive when it is only
    named inside an interpolation.  When the real string splitter cannot be
    reached the raw text is scanned as the fallback.
    """
    from lark import Tree
    import pengu_parser.pengu_parser as parser_mod

    def boom(*_args, **_kwargs):
        raise RuntimeError("splitter unavailable")

    monkeypatch.setattr(parser_mod, "extract_string_parts", boom)
    tree = Tree("string_lit", ['"{calling cb64_char with v}"'])
    refs = pengu_dce.collect_references([tree])
    assert "cb64_char" in refs
    assert "calling" in refs


@requires_cc
@requires_runtime
def test_dce_shrinks_a_std_import(tmp_path):
    """A script using only println must not carry the whole of std.spark."""
    source = ('import std.spark\n\n'
              'weave main into int:\n'
              '    calling spark.println with "hi"\n'
              '    return 0\n')
    c = _bundle_of(source, tmp_path)
    lines = len(c.splitlines())
    # Without DCE this bundle is ~430 lines; the threshold leaves a wide margin
    # while still failing if the pass stops working.
    assert lines < 250, f"bundle.c still has {lines} lines"
    assert "pengu_main" in c


# ---------------------------------------------------------------------------
# TCC integration (skipped when TCC is not installed/packaged)
# ---------------------------------------------------------------------------

def test_pick_dev_compiler_prefers_tcc_when_available():
    configured = "gcc"
    chosen = pick_dev_compiler(configured)
    if tcc_available():
        assert "tcc" in os.path.basename(chosen).lower()
    else:
        assert chosen == configured


def test_pengu_dev_cc_overrides(monkeypatch):
    monkeypatch.setenv("PENGU_DEV_CC", "clang")
    assert pick_dev_compiler("gcc") == "clang"


def test_pengu_no_tcc_disables_discovery(monkeypatch):
    monkeypatch.setenv("PENGU_NO_TCC", "1")
    assert find_tcc() is None


@pytest.mark.skipif(not tcc_available(), reason="tcc not installed/packaged")
@requires_cc
@requires_runtime
def test_run_uses_tcc_when_available(tmp_path):
    cache = tmp_path / "cache"
    work = tmp_path / "w"
    work.mkdir()
    script = work / "h.pengu"
    script.write_text('weave main into int:\n    return 0\n', encoding="utf-8")
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache)
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "run", "--verbose", str(script)],
        cwd=str(work), capture_output=True, text=True, timeout=300, env=env,
    )
    assert res.returncode == 0, res.stderr
    assert "tcc" in res.stdout.lower()


def test_tcc_failure_falls_back_to_configured_cc(tmp_path, monkeypatch):
    """A TCC that always fails must not break the build (falls back to gcc)."""
    fake = tmp_path / "tcc"
    fake.write_text("#!/bin/sh\necho 'tcc: fake failure' >&2\nexit 1\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("PENGU_DEV_CC", str(fake))
    assert pick_dev_compiler("gcc") == str(fake)


# ---------------------------------------------------------------------------
# PCH (opt-in)
# ---------------------------------------------------------------------------

def test_pch_is_opt_in(tmp_path):
    """The PCH is off by default (measured: no gain on a normal build)."""
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "p.pengu"
    script.write_text('weave main into int:\n    return 0\n', encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path), output=OutputType.C,
                        output_name="p", name="p", build_dir=str(tmp_path / "b"))
    builder = PenguBuilder(cfg)
    assert builder.use_pch is False
    assert builder.dev_fast_flags is False


def test_pch_signature_tracks_include_and_define_flags(tmp_path):
    sys.path.insert(0, str(REPO))
    from pengu_project import PenguBuilder

    sig_a = PenguBuilder._pch_signature(["-Ifoo", "-DBAR", "-O2", "-Wall"])
    sig_b = PenguBuilder._pch_signature(["-Ifoo", "-DBAR=1", "-O0"])
    assert sig_a != sig_b
    assert "-O2" not in sig_a and "-Wall" not in sig_a


def test_tcc_link_line_has_no_gnu_start_group(tmp_path):
    """TCC's linker driver rejects ``-Wl,--start-group``.

    Regression: every 'pengu run' with TCC used to fail the link and silently
    fall back to gcc (doubling the cache-miss compile time), because the GNU-ld
    archive group was added for every non-MSVC compiler.
    """
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "p.pengu"
    script.write_text("weave main into int:\n    return 0\n", encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path), output=OutputType.EXE,
                        output_name="p", name="p", build_dir=str(tmp_path / "b"),
                        links=["pengu_runtime"])
    cfg.cc = "tcc"
    commands = PenguBuilder(cfg).build_compile_commands(
        str(tmp_path / "bundle.c"), str(tmp_path / "p"))
    assert commands
    tcc_line = " ".join(commands[0])
    assert "--start-group" not in tcc_line
    assert "--end-group" not in tcc_line

    # ...while GNU-ld hosts (gcc on Linux/Windows-MinGW) still get the group for
    # robust archive order.  Apple's ld64 rejects it, so macOS must not see it.
    cfg.cc = "gcc"
    gcc_line = " ".join(PenguBuilder(cfg).build_compile_commands(
        str(tmp_path / "bundle.c"), str(tmp_path / "p"))[0])
    if sys.platform == "darwin":
        assert "--start-group" not in gcc_line
    else:
        assert "--start-group" in gcc_line


def test_find_tcc_prefers_the_packaged_bundle(tmp_path, monkeypatch):
    """Inside a PyInstaller release, TCC lives at ``<sys._MEIPASS>/tcc/tcc``."""
    import pengu_tcc

    bundled = tmp_path / "tcc" / pengu_tcc._exe("tcc")
    bundled.parent.mkdir(parents=True, exist_ok=True)
    bundled.write_text("#!/bin/sh\n", encoding="utf-8")
    bundled.chmod(0o755)

    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert pengu_tcc.find_tcc() == str(bundled)


def test_find_tcc_ignores_a_non_executable_bundle_entry(tmp_path, monkeypatch):
    import pengu_tcc

    bundled = tmp_path / "tcc" / pengu_tcc._exe("tcc")
    bundled.parent.mkdir(parents=True, exist_ok=True)
    bundled.write_text("not executable\n", encoding="utf-8")
    bundled.chmod(0o644)
    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    if os.name == "nt":
        pytest.skip("executable bit is not meaningful on Windows")
    found = pengu_tcc.find_tcc()
    assert found != str(bundled)


def test_find_tcc_probes_the_windows_suffix(tmp_path, monkeypatch):
    """On Windows the bundled binary must be found as ``tcc/tcc.exe``.

    ``make_release.py`` used to hard-code the PyInstaller destination as
    ``tcc/tcc`` even on Windows, so the frozen toolchain never located its
    compiler.  The destination now preserves the source file name; this pins the
    ``_exe`` convention ``find_tcc`` relies on.
    """
    import pengu_tcc

    monkeypatch.setattr(pengu_tcc.sys, "platform", "win32")
    bundled = tmp_path / "tcc" / "tcc.exe"
    bundled.parent.mkdir(parents=True, exist_ok=True)
    bundled.write_text("MZ fake\n", encoding="utf-8")
    bundled.chmod(0o755)
    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert pengu_tcc.find_tcc() == str(bundled)


def test_find_tcc_accepts_a_suffix_less_legacy_archive(tmp_path, monkeypatch):
    """Releases built before the destination fix shipped 'tcc/tcc' on Windows."""
    import pengu_tcc

    monkeypatch.setattr(pengu_tcc.sys, "platform", "win32")
    legacy = tmp_path / "tcc" / "tcc"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("MZ fake\n", encoding="utf-8")
    legacy.chmod(0o755)
    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert pengu_tcc.find_tcc() == str(legacy)


def test_run_project_forwards_pch_and_no_dce(monkeypatch):
    """'pengu run --no-dce' (project mode, no script) must not be ignored."""
    sys.path.insert(0, str(REPO))
    from pengu_project import OutputType, ProjectConfig, run_project

    captured = {}

    class FakeConfig:
        output = OutputType.C  # not an executable: run_project stops after build
        base_dir = "."

    monkeypatch.setattr(ProjectConfig, "load",
                        classmethod(lambda cls, *a, **k: FakeConfig()))

    def fake_build_project(config_path=None, **kwargs):
        captured.update(kwargs)
        captured["config_path"] = config_path
        return "artifact"

    monkeypatch.setattr("pengu_project.build_project", fake_build_project)
    assert run_project(no_dce=True, pch=True) == 0
    assert captured.get("no_dce") is True
    assert captured.get("pch") is True

    captured.clear()
    assert run_project() == 0
    assert captured.get("no_dce") is False
    assert captured.get("pch") is False


def test_tcc_add_binary_args_keep_the_executable_name(tmp_path):
    """Release packaging must preserve 'tcc.exe' as the destination name.

    Regression: ``make_release.py`` hard-coded ``tcc/tcc``; on Windows the frozen
    toolchain probes ``tcc/tcc.exe`` and therefore never found its compiler.
    """
    sys.path.insert(0, str(REPO))
    from make_release import tcc_add_binary_args

    # Unix 'make install' layout: <prefix>/bin/tcc + <prefix>/lib/tcc/include.
    prefix = tmp_path / "tcc-dist"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "lib" / "tcc" / "include").mkdir(parents=True)
    (prefix / "lib" / "tcc" / "include" / "stdarg.h").write_text("", encoding="utf-8")
    unix_bin = prefix / "bin" / "tcc"
    unix_bin.write_text("", encoding="utf-8")
    args = tcc_add_binary_args(unix_bin, ":")
    assert args[0].endswith("tcc/tcc")
    assert not args[0].endswith("tcc.exe")
    assert args[1].endswith("tcc/include")
    assert str(prefix / "lib" / "tcc" / "include") in args[1]

    # Windows prebuilt layout: tcc.exe and include/ side by side.
    win_dir = tmp_path / "tcc_20221020"
    (win_dir / "include").mkdir(parents=True)
    (win_dir / "include" / "stdarg.h").write_text("", encoding="utf-8")
    win_bin = win_dir / "tcc.exe"
    win_bin.write_text("", encoding="utf-8")
    win_args = tcc_add_binary_args(win_bin, ";")
    assert win_args[0].endswith("tcc/tcc.exe"), win_args
    assert win_args[1].endswith("tcc/include")
    assert str(win_dir / "include") in win_args[1]

    # CI archive layout: the PowerShell step copies tcc.exe to the archive root
    # while the headers stay inside the unpacked '<version>/include' subtree.
    root = tmp_path / "staged"
    (root / "tcc_20221020" / "include").mkdir(parents=True)
    (root / "tcc_20221020" / "include" / "stdarg.h").write_text("", encoding="utf-8")
    root_bin = root / "tcc.exe"
    root_bin.write_text("", encoding="utf-8")
    ci_args = tcc_add_binary_args(root_bin, ";")
    assert ci_args[0].endswith("tcc/tcc.exe")
    assert len(ci_args) == 2, f"include tree not found next to the staged tcc: {ci_args}"
    assert ci_args[1].endswith("tcc/include")
    assert "tcc_20221020" in ci_args[1]


def test_find_tcc_discovers_the_make_release_staging_layout(tmp_path, monkeypatch):
    """``ensure_tcc("build/tcc-dist")`` installs at ``.../tcc-dist/bin/tcc``.

    A checkout that ran the release packager must see the staged compiler, which
    is what ``pengu doctor`` reports before/after packaging.
    """
    import pengu_tcc

    staged = (tmp_path / "build" / "tcc-dist" / "tcc-dist" / "bin"
              / pengu_tcc._exe("tcc"))
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text("", encoding="utf-8")
    staged.chmod(0o755)

    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(pengu_tcc, "__file__", str(tmp_path / "pengu_tcc.py"))
    assert pengu_tcc.find_tcc() == str(staged)
