"""P0 toolchain hardening — regression tests.

Covers the five "production hygiene" items from `PRODUCTION_READINESS.md`:

* the exit status of `weave main` reaches the process (it used to be discarded),
* generated C carries `#line` directives pointing at the `.pengu` sources,
* the incremental build cache keys on *content* (entry + modules + C glue), so
  two programs built in the same directory can never share a stale artifact,
* `pengu_init` exposes `argc`/`argv` to `rites.get_args()`,
* every version string in the tree comes from `VERSION`.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    bundle_project,
    gen_bundle,
    requires_cc,
    requires_runtime,
)

PY = sys.executable
PROJECT_SCRIPT = str(REPO / "pengu_project.py")

HELLO_A = 'import std.spark\n\nweave main into int:\n    calling spark.println with "PROGRAM-A"\n    return 0\n'
HELLO_B = 'import std.spark\n\nweave main into int:\n    calling spark.println with "PROGRAM-B"\n    return 0\n'


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _scratch(prefix: str) -> Path:
    """Creates a unique scratch directory under build/ (repo root untouched)."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"p0_{prefix}_", dir=BUILD_DIR))


def _build_project(proj: Path, source: str, name: str = "app", entry: str = "src/main.pengu") -> str:
    """Writes a runtime-linked project and builds it, returning the artifact path.

    The configuration mirrors ``tests/test_cli_tools.py::runtime_yaml``: the
    project links the repo's built runtime archives from ``build/``.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    (proj / "src").mkdir(parents=True, exist_ok=True)
    (proj / entry).write_text(source, encoding="utf-8")
    lib = str(BUILD_LIB.resolve()).replace("\\", "/")
    inc = str(BUILD_INCLUDE.resolve()).replace("\\", "/")
    root = str(BUILD_DIR.resolve()).replace("\\", "/")
    (proj / "pengu.yaml").write_text(
        'project:\n'
        f'  name: "{name}"\n'
        '  version: "0.1.0"\n'
        f'  entry: "{entry}"\n'
        '  output: "exe"\n'
        f'  output_name: "{name}"\n'
        '\n'
        'build:\n'
        '  build_dir: "build"\n'
        '  links: ["pengu_runtime"]\n'
        f'  lib_dirs: ["{lib}"]\n'
        f'  include_dirs: ["{inc}", "{root}"]\n',
        encoding="utf-8",
    )
    cfg = ProjectConfig.load(str(proj))
    artifact, _ = PenguBuilder(cfg).compile()
    return artifact


def _run(artifact: str, args=None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Runs a built artifact and returns the completed process."""
    return subprocess.run([artifact] + list(args or []), capture_output=True,
                          text=True, timeout=timeout)


# --------------------------------------------------------------------------
# P0.1 — exit status
# --------------------------------------------------------------------------


@requires_runtime
class TestExitStatus:
    """`weave main`'s return value is the process exit status."""

    def test_return_value_becomes_the_exit_code(self, tmp_path):
        proj = _scratch("exit42")
        try:
            artifact = _build_project(proj, "weave main into int:\n    return 42\n")
            assert _run(artifact).returncode == 42
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_zero_is_still_zero(self, tmp_path):
        proj = _scratch("exit0")
        try:
            artifact = _build_project(proj, "weave main into int:\n    return 0\n")
            assert _run(artifact).returncode == 0
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_void_main_still_runs_and_exits_zero(self):
        # 'into void' must not skip the program body: only a value-returning
        # 'main' can be captured as the exit status.
        proj = _scratch("exitvoid")
        try:
            artifact = _build_project(
                proj,
                "import std.spark\n\n"
                "weave main into void:\n"
                '    calling spark.println with "VOID-MAIN-RAN"\n'
                "    return\n",
            )
            res = _run(artifact)
            assert res.returncode == 0
            assert "VOID-MAIN-RAN" in res.stdout
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_small_int_main_is_widened(self, tmp_path):
        proj = _scratch("exitu8")
        try:
            artifact = _build_project(proj, "weave main into u8:\n    return 3\n")
            assert _run(artifact).returncode == 3
        finally:
            shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------
# P0.2 — #line directives
# --------------------------------------------------------------------------


class TestLineDirectives:
    """Generated C points diagnostics back at the .pengu sources."""

    def test_statements_carry_markers(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var x as int is 1\n"
            "    return x\n",
            filename="marker.pengu",
        )
        markers = re.findall(r'^#line (\d+) "([^"]+)"$', code, flags=re.M)
        assert markers, "no #line directives were emitted"
        assert any(name.endswith("marker.pengu") for _, name in markers)

    def test_marker_lines_match_the_source(self):
        code = bundle_project(
            "declare tick with v as int into void\n\n"
            "weave main into int:\n"
            "    var x as int is 1\n"
            "    calling tick with x\n"
            "    return x\n",
            tag="p0_lines",
        )
        # 'calling tick with x' is line 5 of the bundle's copy of the source.
        assert re.search(r'#line 5 "p0_lines\.pengu"', code), \
            [ln for ln in code.splitlines() if ln.startswith("#line")][:8]

    def test_function_definition_has_a_marker(self):
        code = gen_bundle("weave helper into int:\n    return 1\n\n"
                          "weave main into int:\n    return calling helper\n",
                          filename="fnmark.pengu")
        assert re.search(r'#line 1 "[^"]*fnmark\.pengu"\s*\nint32_t helper\(void\)', code)
        assert re.search(r'#line 4 "[^"]*fnmark\.pengu"\s*\nint32_t pengu_main\(void\)', code)

    def test_generated_sections_reset_attribution(self):
        code = bundle_project(
            "weave main into int:\n    return 0\n",
            tag="p0_reset",
        )
        # The entry wrapper is compiler-generated: it must not be attributed to
        # the user's file.
        entry = code.index("Entry Point Wrapper")
        assert '#line 1 "bundle.c"' in code[:entry]

    def test_no_markers_inside_statement_expressions(self):
        # A value-position 'if' becomes a GCC statement expression, which may end
        # up as the argument of the pengu_to_string(...) macro: a directive there
        # would break the macro invocation.
        code = bundle_project(
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var n as int is 2\n"
            "    var x as int is if n > 1:\n"
            "        10\n"
            "    else:\n"
            "        20\n"
            "    var s as string is x to string\n"
            "    calling spark.println with s\n"
            "    return 0\n",
            tag="p0_expr",
        )
        assert "__extension__" in code
        for match in re.finditer(r"__extension__", code):
            snippet = code[match.start():match.start() + 400]
            # The statement expression ends at the matching '})));'; a marker may
            # follow it but never appear inside.
            end = snippet.find("})));")
            inside = snippet[:end] if end != -1 else snippet
            assert "#line" not in inside, inside[:200]

    @requires_cc
    def test_compiler_error_is_reported_against_the_pengu_source(self, tmp_path):
        """A C-level failure caused by generated code names the .pengu line.

        Uses a construct that currently type-checks but emits invalid C
        (`xs length`); if that codegen bug is fixed the build succeeds and there
        is nothing to assert, so the test skips instead of failing.
        """
        proj = _scratch("lineerr")
        try:
            src = (
                "import std.spark\n\n"
                "weave main into int:\n"
                "    var xs as array of int with size 3 is [4, 5, 6]\n"
                "    var i as int is 0\n"
                "    while i < (xs length):\n"
                "        set i is i + 1\n"
                "    return 0\n"
            )
            (proj / "src").mkdir(parents=True, exist_ok=True)
            (proj / "src" / "main.pengu").write_text(src, encoding="utf-8")
            res = subprocess.run(
                [PY, PROJECT_SCRIPT, "build", "-c", str(proj), "--entry", "src/main.pengu"],
                cwd=str(REPO), capture_output=True, text=True, timeout=900,
            )
            out = re.sub(r"\x1b\[[0-9;]*m", "", (res.stdout or "") + (res.stderr or ""))
            if res.returncode == 0:
                pytest.skip("'xs length' now compiles: the codegen bug was fixed")
            assert "main.pengu:" in out, out[-600:]
            assert "bundle.c:" not in out.split("main.pengu:")[0][-200:]
        finally:
            shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------
# P0.3 — build cache
# --------------------------------------------------------------------------


@requires_runtime
class TestBuildCache:
    """The cache key is content-based and entry-aware."""

    def test_different_programs_never_share_a_binary(self):
        proj = _scratch("cachecross")
        try:
            art_a = _build_project(proj, HELLO_A, name="appa")
            assert "PROGRAM-A" in _run(art_a).stdout

            art_b = _build_project(proj, HELLO_B, name="appb")
            assert "PROGRAM-B" in _run(art_b).stdout

            # Rewrite program A with an *older* mtime than the cached bundle: the
            # old mtime-only cache considered that "up to date" and shipped B.
            entry = proj / "src" / "main.pengu"
            entry.write_text(HELLO_A, encoding="utf-8")
            old = time.time() - 3600
            os.utime(entry, (old, old))

            art_a2 = _build_project(proj, HELLO_A, name="appa")
            assert "PROGRAM-A" in _run(art_a2).stdout
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_unchanged_sources_are_cached(self):
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _scratch("cachehit")
        try:
            _build_project(proj, HELLO_A)
            bundle = proj / "build" / "bundle.c"
            stamp = bundle.stat().st_mtime_ns
            time.sleep(0.01)
            cfg = ProjectConfig.load(str(proj))
            _, cached = PenguBuilder(cfg).bundle()
            assert cached is True
            assert bundle.stat().st_mtime_ns == stamp
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_touching_a_source_keeps_the_cache(self):
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _scratch("cachetouch")
        try:
            _build_project(proj, HELLO_A)
            entry = proj / "src" / "main.pengu"
            os.utime(entry, None)  # mtime bump, identical content
            time.sleep(0.01)
            cfg = ProjectConfig.load(str(proj))
            _, cached = PenguBuilder(cfg).bundle()
            assert cached is True
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_content_change_invalidates_the_cache(self):
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _scratch("cachebust")
        try:
            _build_project(proj, HELLO_A)
            (proj / "src" / "main.pengu").write_text(
                HELLO_A.replace("PROGRAM-A", "PROGRAM-A2"), encoding="utf-8")
            cfg = ProjectConfig.load(str(proj))
            _, cached = PenguBuilder(cfg).bundle()
            assert cached is False
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_config_change_invalidates_the_cache(self):
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _scratch("cachecfg")
        try:
            _build_project(proj, HELLO_A)
            cfg = ProjectConfig.load(str(proj))
            cfg.defines = list(cfg.defines or []) + ["EXTRA_FLAG"]
            _, cached = PenguBuilder(cfg).bundle()
            assert cached is False
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_stale_single_token_hash_file_is_rebuilt(self):
        """`.bundle_hash` files written by older versions must be treated as stale."""
        from pengu_project import PenguBuilder, ProjectConfig

        proj = _scratch("cacheold")
        try:
            _build_project(proj, HELLO_A)
            hash_file = proj / "build" / ".bundle_hash"
            hash_file.write_text("deadbeef", encoding="utf-8")
            cfg = ProjectConfig.load(str(proj))
            _, cached = PenguBuilder(cfg).bundle()
            assert cached is False
        finally:
            shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------
# P0.4 — argv
# --------------------------------------------------------------------------


@requires_runtime
class TestArguments:
    def test_program_arguments_reach_rites(self):
        proj = _scratch("argv")
        try:
            src = (
                "import std.spark\n"
                "import std.rites as rites\n\n"
                "weave main into int:\n"
                "    var n as int is calling rites.get_argc\n"
                '    calling spark.println with "argc={n}"\n'
                "    var i as int is 1\n"
                "    while i < n:\n"
                "        calling spark.println with (calling rites.get_argv with i)\n"
                "        set i is i + 1\n"
                "    return 0\n"
            )
            artifact = _build_project(proj, src)
            res = _run(artifact, ["alpha", "beta"])
            assert res.returncode == 0
            lines = res.stdout.split()
            assert lines[0] == "argc=3"
            assert lines[1:] == ["alpha", "beta"]
        finally:
            shutil.rmtree(proj, ignore_errors=True)


# --------------------------------------------------------------------------
# P0.5 — one version, everywhere
# --------------------------------------------------------------------------


class TestVersion:
    def test_version_file_drives_the_module(self):
        from pengu_version import FALLBACK_VERSION, __version__, read_version_file

        assert read_version_file() == __version__
        assert FALLBACK_VERSION == __version__

    def test_generated_banner_uses_the_version(self):
        from pengu_version import __version__

        code = gen_bundle("weave main into int:\n    return 0\n")
        assert f"/* Auto-generated by PenguScript v{__version__} */" in code

    def test_codegen_fallback_module_constant_matches(self):
        from pengu_parser.pengu_codegen import PENGU_VERSION
        from pengu_version import __version__

        assert PENGU_VERSION == __version__

    def test_readme_badge_and_extension_manifest_match(self):
        from pengu_version import __version__

        readme = (REPO / "README.md").read_text(encoding="utf-8")
        assert f"badge/version-{__version__}-" in readme

        manifest = json.loads((REPO / "vscode-extension" / "package.json").read_text(encoding="utf-8"))
        assert manifest["version"] == __version__

    def test_no_stale_version_claims_in_sources(self):
        from pengu_version import __version__

        grammar_head = (REPO / "pengu_parser" / "pengu_grammar.py").read_text(
            encoding="utf-8").splitlines()[0]
        assert not re.search(r"v\d+\.\d+\.\d+", grammar_head)

        runtime_head = "\n".join(
            (REPO / "pengu_runtime.h").read_text(encoding="utf-8").splitlines()[:6])
        assert not re.search(r"v\d+\.\d+\.\d+", runtime_head)
        assert __version__ in (REPO / "VERSION").read_text(encoding="utf-8")

    def test_cli_reports_the_version(self):
        res = subprocess.run([PY, PROJECT_SCRIPT, "--version"],
                             cwd=str(REPO), capture_output=True, text=True, timeout=120)
        from pengu_version import __version__

        assert res.returncode == 0
        assert res.stdout.strip() == f"pengu {__version__}"
