"""`std.web` — the Emscripten/Web bridge module.

Two layers, mirroring the rest of `tests/wasm/`:

* ``smoke`` — pure Python. The module exists, follows the stdlib conventions
  (``WEB_VERSION``) and stays importable.
* ``slow`` — compile and run on both targets. They skip unless the needed
  toolchain is present (native C compiler; ``emcc`` + ``node`` for wasm).

The acceptance criteria this file covers, from the module's design:

1. `import std.web` compiles natively with no link errors.
2. It compiles for wasm and the bundle contains `emscripten_set_main_loop`.
3. `set_main_loop` + `cancel_main_loop` terminate cleanly under Node.
4. `console_log` reaches the JavaScript console on wasm and stderr natively.
5. `now_ms` is monotonic on both targets.
6. DCE: using only `now_ms` leaves `emscripten_set_main_loop` out of the C.
7. (see `tests/compiler/test_comptime_wasm.py` for the `when wasm:` folding)
8. `std.web` contributes no `emcc` warnings of its own.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
REPO = HERE.parents[1]
STD_WEB = REPO / "std" / "web.pengu"
SMOKE_PROGRAM = HERE / "std_web_smoke.pengu"
STD_DIR = REPO / "std"


def _cli(args, cwd, env=None, timeout=900):
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(cwd),
        env={"PYTHONPATH": str(REPO), **_base_env(), **(env or {})},
    )


def _base_env():
    import os
    return dict(os.environ)


def _stage(tmp_path, source: Path = SMOKE_PROGRAM) -> Path:
    """Copies a fixture program into ``tmp_path`` and returns the copy.

    ``--keep`` puts the build directory next to the *script*, so running the
    repository's fixture in place would write ``tests/wasm/build/`` into the
    working tree. Staging it keeps every artifact inside ``tmp_path``.
    """
    staged = tmp_path / source.name
    staged.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return staged


# ---------------------------------------------------------------------------
# smoke: the module and its conventions
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_std_web_module_exists():
    assert STD_WEB.is_file(), "std/web.pengu is missing"


@pytest.mark.smoke
def test_std_web_follows_the_version_constant_convention():
    """Every std module exports `<MODULE>_VERSION` (LANGUAGE.md §19.0).

    This module was the only one without it; the check is here so the next
    module added does not repeat that.
    """
    text = STD_WEB.read_text(encoding="utf-8")
    assert re.search(r'^\s*const WEB_VERSION as string is "', text, re.M)

    missing = []
    for module in sorted(STD_DIR.glob("*.pengu")):
        expected = f"{module.stem.upper()}_VERSION"
        if not re.search(rf"^\s*const {expected} as string is ", module.read_text(encoding="utf-8"),
                         re.M):
            missing.append(module.name)
    assert not missing, f"std modules without a <MODULE>_VERSION constant: {missing}"


@pytest.mark.smoke
def test_std_web_declares_the_whole_public_api():
    """Both branches must define the same names, or one target silently lacks API.

    The declarations are indented (they live inside the `when` blocks), hence the
    leading ``\\s*``.
    """
    text = STD_WEB.read_text(encoding="utf-8")
    api = ["console_log", "console_warn", "console_error", "console_trace",
           "now_ms", "eval_js", "set_main_loop", "cancel_main_loop",
           "pause_main_loop", "resume_main_loop", "set_timeout", "clear_timeout",
           "IS_WASM"]
    for name in api:
        # One definition per branch: wasm + native.
        assert len(re.findall(rf"^\s*(?:antiquus|weave|const) {name}\b", text, re.M)) == 2, \
            f"'{name}' is not defined exactly once per target branch"
    assert "when wasm:" in text and "when not wasm:" in text


@pytest.mark.smoke
def test_std_web_has_no_em_asm():
    """`EM_ASM` is rejected under `-std=c11`, the dialect this project selects.

    The module *mentions* it in a comment explaining why it is avoided; what must
    not exist is a use of it in code.
    """
    offenders = [line for line in STD_WEB.read_text(encoding="utf-8").splitlines()
                 if "EM_ASM" in line and not line.lstrip().startswith("#")]
    assert not offenders, f"EM_ASM used in code: {offenders}"


# ---------------------------------------------------------------------------
# slow: native
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_std_web_native_smoke(host_runtime, tmp_path):
    """Criterion 1: compiles and runs natively; the stub branch is taken."""
    res = _cli(["run", "--no-cache", "--ephemeral", str(SMOKE_PROGRAM)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "std.web smoke: native" in res.stdout
    assert "std_web_smoke: OK" in res.stdout
    # The wasm-only branch must not run natively.
    assert "tick" not in res.stdout


@pytest.mark.slow
def test_std_web_native_stub_panics(host_runtime, tmp_path):
    """A Web-only entry point fails loudly natively, with an actionable message."""
    script = tmp_path / "stub.pengu"
    script.write_text(
        "import std.spark\nimport std.web\n\n"
        "weave main into int:\n"
        '    calling web.eval_js with "console.log(1)"\n'
        "    return 0\n", encoding="utf-8")
    res = _cli(["run", "--no-cache", "--ephemeral", str(script)], tmp_path)
    assert res.returncode != 0
    assert "std.web.eval_js requires a wasm build" in res.stdout + res.stderr


# ---------------------------------------------------------------------------
# slow: wasm
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_std_web_wasm_smoke(emcc, node, wasm_runtime, tmp_path):
    """Criteria 3 and 4: the loop runs and stops; console output reaches Node."""
    res = _cli(["run", "--target", "wasm32-unknown-emscripten",
                "--no-cache", "--ephemeral", str(SMOKE_PROGRAM)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "std.web smoke: wasm" in res.stdout
    assert "loop registered" in res.stdout
    assert "std_web_smoke: OK" in res.stdout
    # Three ticks, then the loop cancels itself.
    assert res.stdout.count("tick") == 3, res.stdout
    assert "stopping the loop" in res.stdout


@pytest.mark.slow
def test_std_web_wasm_bundle_contains_the_loop_symbol(emcc, node, wasm_runtime, tmp_path):
    """Criterion 2: using the API emits the real Emscripten calls."""
    staged = _stage(tmp_path)
    res = _cli(["run", "--target", "wasm32-unknown-emscripten", "--no-cache",
                "--keep", str(staged)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    bundle = tmp_path / "build" / "std_web_smoke_run" / "bundle.c"
    assert bundle.is_file(), f"missing {bundle}"
    text = bundle.read_text(encoding="utf-8")
    assert "emscripten_set_main_loop" in text
    assert "emscripten_cancel_main_loop" in text
    assert "emscripten_console_log" in text


@pytest.mark.slow
def test_std_web_dce_drops_unused_wasm_helpers(emcc, node, wasm_runtime, tmp_path):
    """Criterion 6: a program using only `now_ms` must not pull in the main loop."""
    script = tmp_path / "only_clock.pengu"
    script.write_text(
        "import std.spark\nimport std.web\n\n"
        "weave main into int:\n"
        "    var t as f64 is calling web.now_ms\n"
        '    calling spark.println with "clock only"\n'
        "    if t <= 0.0:\n        return 1\n    return 0\n", encoding="utf-8")
    res = _cli(["run", "--target", "wasm32-unknown-emscripten", "--no-cache",
                "--keep", str(script)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    bundle = tmp_path / "build" / "only_clock_run" / "bundle.c"
    text = bundle.read_text(encoding="utf-8")
    assert "emscripten_get_now" in text, "now_ms must be emitted"
    for pruned in ("emscripten_set_main_loop", "emscripten_cancel_main_loop",
                   "emscripten_console_log", "emscripten_run_script",
                   "emscripten_set_timeout"):
        assert pruned not in text, f"{pruned} should have been pruned by DCE"


@pytest.mark.slow
def test_std_web_now_ms_is_monotonic_on_both_targets(host_runtime, emcc, node,
                                                     wasm_runtime, tmp_path):
    """Criterion 5: `now_ms` never goes backwards on either target."""
    script = tmp_path / "clock.pengu"
    script.write_text(
        "import std.spark\nimport std.web\n\n"
        "weave burn into int:\n"
        "    var s as int is 0\n"
        "    var i as int is 0\n"
        "    while i < 2000:\n"
        "        set s is s + i\n"
        "        set i is i + 1\n"
        "    return s\n\n"
        "weave main into int:\n"
        "    var t0 as f64 is calling web.now_ms\n"
        "    var sink as int is calling burn\n"
        "    var t1 as f64 is calling web.now_ms\n"
        "    if t1 < t0:\n"
        '        calling spark.println with "FAIL: clock went backwards"\n'
        "        return 1\n"
        "    if t0 <= 0.0:\n"
        '        calling spark.println with "FAIL: clock is zero"\n'
        "        return 1\n"
        '    calling spark.println with "clock monotonic"\n'
        "    return sink - sink\n", encoding="utf-8")

    native = _cli(["run", "--no-cache", "--ephemeral", str(script)], tmp_path)
    assert native.returncode == 0, f"native: {native.stdout}\n{native.stderr}"
    assert "clock monotonic" in native.stdout

    wasm = _cli(["run", "--target", "wasm32-unknown-emscripten", "--no-cache",
                 "--ephemeral", str(script)], tmp_path)
    assert wasm.returncode == 0, f"wasm: {wasm.stdout}\n{wasm.stderr}"
    assert "clock monotonic" in wasm.stdout


@pytest.mark.slow
def test_std_web_emits_no_warnings_of_its_own(emcc, node, wasm_runtime, tmp_path):
    """Criterion 8: no `emcc` diagnostic may point at std/web.pengu.

    Bundle-level warnings from generated helpers are pre-existing and shared by
    every wasm build; what this asserts is that *this module* introduces none.
    """
    staged = _stage(tmp_path)
    res = _cli(["run", "--target", "wasm32-unknown-emscripten", "--no-cache",
                "--keep", str(staged)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    build = tmp_path / "build" / "std_web_smoke_run"
    assert (build / "bundle.c").is_file()

    proc = subprocess.run(
        [emcc, "-c", str(build / "bundle.c"), "-o", str(tmp_path / "probe.o"),
         "-O2", "-Wall", "-Wextra", "-std=c11", "-pthread",
         "-I", str(build), "-I", str(REPO / "build" / "wasm" / "include"),
         "-I", str(REPO)],
        capture_output=True, text=True, timeout=600)
    # A compile error is a failure regardless of warnings.
    assert proc.returncode == 0, f"emcc failed:\n{proc.stderr}"
    offenders = [line for line in proc.stderr.splitlines()
                 if "warning:" in line and "web.pengu" in line]
    assert not offenders, "std/web.pengu produced warnings:\n" + "\n".join(offenders)


@pytest.mark.slow
def test_std_web_native_import_is_warning_free(host_runtime, tmp_path):
    """Criterion 1: importing std.web natively is warning-free.

    Compiled with the project's own flags (``-Wall -std=c11``, what the manifest
    templates and ``build_runtime.py`` use), not ``-Wextra``: the native stubs
    keep their wasm counterparts' parameter lists for API parity, so a few are
    intentionally unread and ``-Wextra`` would report ``-Wunused-parameter`` for
    them. That trade-off is documented in the module's header comment.
    """
    cc = shutil.which("clang") or shutil.which("gcc")
    if not cc:
        pytest.skip("no C compiler")

    staged = _stage(tmp_path)
    res = _cli(["run", "--no-cache", "--keep", str(staged)], tmp_path)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    build = tmp_path / "build" / "std_web_smoke_run"
    proc = subprocess.run(
        [cc, "-c", str(build / "bundle.c"), "-o", str(tmp_path / "native.o"),
         "-O2", "-Wall", "-std=c11", "-pthread",
         "-I", str(build), "-I", str(REPO / "build" / "include"), "-I", str(REPO)],
        capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, f"native compile failed:\n{proc.stderr}"
    warnings = [line for line in proc.stderr.splitlines() if "warning:" in line]
    assert not warnings, "native build warned:\n" + "\n".join(warnings[:10])
