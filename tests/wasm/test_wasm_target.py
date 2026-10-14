"""Tests for the ``wasm32-unknown-emscripten`` (WebAssembly) target.

The suite is split by cost, mirroring ``tests/compiler``:

* ``smoke`` -- pure Python. Triple parsing, artifact naming, dialect mapping and
  the wasm runtime-archive lookup. No emcc, no Node, no built runtime, so these
  run everywhere (including the CI smoke job, which installs neither).
* ``slow`` -- compile with emcc and execute with Node. They skip unless the
  Emscripten SDK is active and ``build/wasm/lib/libpengu_runtime.a`` exists.

See ``docs/WASM.md`` for the user-facing story and ``conftest.py`` for why the
CLI (rather than the builder internals) is the unit under test.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import pengu_project as P


# ---------------------------------------------------------------------------
# smoke: triple parsing and target classification
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_parse_target_triple_emscripten():
    """The Emscripten triple must classify as its own OS, not as the host.

    Regression guard: before this target existed, ``parse_target_triple``
    returned ``os=""`` for ``wasm32-unknown-emscripten``, so the triple was
    silently dropped and the build produced a *native* binary.
    """
    triple = P.parse_target_triple("wasm32-unknown-emscripten")
    assert triple.os == "emscripten"
    assert triple.arch == "wasm32"
    assert triple.is_emscripten
    assert not triple.is_wasi
    # `is_cross` is what makes resolve_compiler() look for emcc at all.
    assert triple.os != P.host_os()


@pytest.mark.smoke
@pytest.mark.parametrize("text", ["wasm", "wasm32", "emscripten", "WASM", " wasm32 "])
def test_wasm_alias_spellings(text):
    """``--target wasm`` and friends are the convenience spelling."""
    assert P.parse_target_triple(text).is_emscripten


@pytest.mark.smoke
def test_parse_target_triple_wasi():
    """WASI is recognised so it can be refused with a clear message."""
    assert P.parse_target_triple("wasm32-wasi").is_wasi
    assert not P.parse_target_triple("wasm32-wasi").is_emscripten


@pytest.mark.smoke
def test_existing_triples_are_unchanged():
    """The new branches must not steal the pre-existing Windows/macOS/Linux cases."""
    win = P.parse_target_triple("x86_64-w64-mingw32")
    assert (win.os, win.env) == ("windows", "mingw")
    mac = P.parse_target_triple("aarch64-apple-darwin")
    assert mac.os == "darwin"
    linux = P.parse_target_triple("x86_64-unknown-linux-gnu")
    assert (linux.os, linux.env) == ("linux", "gnu")
    assert P.parse_target_triple("").os == ""


@pytest.mark.smoke
def test_lock_target_is_canonical_for_wasm():
    """A wasm target lands in pengu.lock as a stable, canonical string."""
    class _Cfg:
        target = "wasm32-unknown-emscripten"

    assert P._lock_target(_Cfg()) == "wasm32-emscripten"
    # Unparsed triples still fall back to the raw string.
    class _Raw:
        target = "riscv64-unknown-elf"

    assert P._lock_target(_Raw()) == "riscv64-unknown-elf"


# ---------------------------------------------------------------------------
# smoke: artifact naming
# ---------------------------------------------------------------------------

class _FakeBuilder:
    """Just enough of PenguBuilder for the naming/compiler helpers.

    The *real* methods are bound onto this stub, so the assertions exercise
    ``PenguBuilder.get_output_artifact_name`` / ``resolve_compiler`` themselves
    rather than a re-implementation of them in the test.
    """

    def __init__(self, target: str, output: P.OutputType | None = None,
                 name: str = "app", cc: str = ""):
        self._target = target
        self.config = type("C", (), {"output": output, "output_name": name, "cc": cc})()

    @property
    def target_triple(self):
        return P.parse_target_triple(self._target)

    @property
    def target_os(self):
        triple = self.target_triple
        return triple.os if triple and triple.os else P.host_os()

    @property
    def is_cross(self):
        return self.target_os != P.host_os()

    def get_output_artifact_name(self) -> str:
        return P.PenguBuilder.get_output_artifact_name(self)

    def resolve_compiler(self) -> str:
        return P.PenguBuilder.resolve_compiler(self)


@pytest.mark.smoke
@pytest.mark.parametrize("out_type,expected", [
    (P.OutputType.EXE, "app.html"),
    (P.OutputType.STATIC, "app.a"),
    (P.OutputType.OBJ, "app.o"),
    (P.OutputType.C, "bundle.c"),
])
def test_output_artifact_name_html(out_type, expected):
    """EXE is a *page* on wasm: emcc -o app.html writes app.html + app.js + app.wasm."""
    assert _FakeBuilder("wasm32-unknown-emscripten", out_type).get_output_artifact_name() \
        == expected


@pytest.mark.smoke
def test_output_artifact_name_native_unchanged():
    """The wasm branch must not change host naming."""
    assert _FakeBuilder("", P.OutputType.EXE).get_output_artifact_name() == "app"
    assert _FakeBuilder("x86_64-w64-mingw32", P.OutputType.EXE).get_output_artifact_name() \
        == "app.exe"
    assert _FakeBuilder("", P.OutputType.STATIC).get_output_artifact_name() == "app.a"
    assert _FakeBuilder("x86_64-w64-mingw32", P.OutputType.STATIC).get_output_artifact_name() \
        == "app.lib"
    assert _FakeBuilder("aarch64-apple-darwin", P.OutputType.SHARED) \
        .get_output_artifact_name() == "libapp.dylib"


# ---------------------------------------------------------------------------
# smoke: compiler resolution
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_resolve_compiler_finds_emcc(monkeypatch):
    """An emscripten target resolves to emcc, never to a host gcc."""
    monkeypatch.setattr(P.shutil, "which", lambda name: f"/fake/{name}" if name == "emcc" else None)
    assert _FakeBuilder("wasm32-unknown-emscripten", cc="gcc").resolve_compiler() \
        == "/fake/emcc"


@pytest.mark.smoke
def test_resolve_compiler_keeps_an_explicit_emcc(monkeypatch):
    """`--cc /path/to/emcc` wins and is not re-probed."""
    monkeypatch.setattr(P.shutil, "which", lambda name: None)
    assert _FakeBuilder("wasm32-unknown-emscripten", cc="/opt/emcc").resolve_compiler() \
        == "/opt/emcc"


@pytest.mark.smoke
def test_resolve_compiler_without_emcc_explains_the_sdk(monkeypatch):
    """A missing SDK must produce the emsdk instructions, not a MinGW message."""
    monkeypatch.setattr(P.shutil, "which", lambda name: None)
    with pytest.raises(P.CompileFailedError) as excinfo:
        _FakeBuilder("wasm32-unknown-emscripten", cc="gcc").resolve_compiler()
    message = str(excinfo.value)
    assert "emcc" in message
    assert "emsdk" in message and "emsdk_env.sh" in message
    assert "mingw" not in message.lower()


@pytest.mark.smoke
def test_resolve_compiler_refuses_wasi(monkeypatch):
    """WASI is refused by name instead of probing for wasm32-wasi-gcc."""
    monkeypatch.setattr(P.shutil, "which", lambda name: None)
    with pytest.raises(P.CompileFailedError) as excinfo:
        _FakeBuilder("wasm32-wasi", cc="gcc").resolve_compiler()
    message = str(excinfo.value)
    assert "WASI" in message and "not supported" in message


# ---------------------------------------------------------------------------
# smoke: compiler dialect
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_compiler_dialect_emcc():
    """emcc is clang-based, so it is the GNU dialect -- but named distinctly."""
    assert P._compiler_dialect("emcc") == "emcc"
    assert P._compiler_dialect("/opt/emsdk/upstream/emscripten/emcc") == "emcc"


@pytest.mark.smoke
@pytest.mark.parametrize("requested", ["emcc", "clang", "gcc"])
def test_validate_target_compiler_emcc_is_coherent(requested):
    """`--target-compiler` may be spelled emcc, clang or gcc with emcc."""
    assert P._validate_target_compiler("emcc", requested) is None


@pytest.mark.smoke
def test_validate_target_compiler_emcc_rejects_msvc():
    """mvc attributes are still rejected for emcc."""
    assert P._validate_target_compiler("emcc", "msvc") is not None


@pytest.mark.smoke
def test_target_compiler_choices_include_emcc():
    """The argparse surface accepts emcc (both the build/run and test parsers)."""
    parser = P.create_cli_parser()
    # Walk the subparsers and collect the choices of every --target-compiler.
    found = []
    for action in _walk_actions(parser):
        if "--target-compiler" in getattr(action, "option_strings", ()):
            found.append(tuple(action.choices))
    assert found, "no --target-compiler option found"
    for choices in found:
        assert "emcc" in choices
        for name in ("gcc", "clang", "msvc", "tcc"):
            assert name in choices, "pre-existing dialect choices must survive"


def _walk_actions(parser):
    """Yields every action of a parser and, recursively, of its subparsers."""
    import argparse

    for action in parser._actions:  # noqa: SLF001 - argparse exposes no public API
        yield action
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for sub in action.choices.values():
                yield from _walk_actions(sub)


# ---------------------------------------------------------------------------
# smoke: runtime archive lookup
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_wasm_runtime_lib_dirs_exclude_the_host_archive(monkeypatch):
    """A wasm build must never be pointed at ``build/lib`` (host objects).

    Mixing them does not fail cleanly: the wasm linker answers with an
    unrelated-looking "invalid object file". The two searches are disjoint.
    """
    monkeypatch.delenv("PENGU_LIB_DIR", raising=False)
    monkeypatch.delenv("PENGU_RUNTIME_CROSS", raising=False)
    dirs = P._wasm_runtime_lib_dirs()
    host_lib = os.path.join(os.path.dirname(os.path.abspath(P.__file__)), "build", "lib")
    assert host_lib not in dirs
    # And the host lookup must not start offering wasm archives either.
    host_dirs = [str(d) for d in P.runtime_lib_dirs()]
    assert not any(d.endswith(os.path.join("build", "wasm", "lib")) for d in host_dirs)


@pytest.mark.smoke
def test_wasm_runtime_lib_dirs_honour_pengu_lib_dir(monkeypatch, tmp_path):
    """PENGU_LIB_DIR stays an *override* for the wasm lookup too."""
    monkeypatch.setenv("PENGU_LIB_DIR", str(tmp_path))
    assert P._wasm_runtime_lib_dirs() == [str(tmp_path)]


@pytest.mark.smoke
def test_missing_wasm_runtime_message_is_actionable():
    """The error must name the wasm-specific build command."""
    msg = P._missing_runtime_archive_message("emscripten")
    assert "build_runtime.py --target emscripten" in msg
    assert "wasm" in msg.lower()


@pytest.mark.smoke
def test_missing_host_runtime_message_unchanged():
    """The host message must keep its original wording."""
    msg = P._missing_runtime_archive_message()
    assert "libpengu_runtime.a not found" in msg
    assert "build_runtime.py" in msg


@pytest.mark.smoke
def test_wasm_shell_file_is_found():
    """The custom HTML shell ships next to the CLI."""
    shell = P._wasm_shell_file()
    assert shell is not None and os.path.isfile(shell)
    assert shell.endswith("pengu_wasm_shell.html")


@pytest.mark.smoke
def test_wasm_shell_can_be_disabled(monkeypatch):
    """PENGU_WASM_SHELL=default falls back to Emscripten's own page."""
    monkeypatch.setenv("PENGU_WASM_SHELL", "default")
    assert P._wasm_shell_file() is None


# ---------------------------------------------------------------------------
# slow: end to end
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_build_hello_wasm_and_run_with_node(tmp_path, emcc, node, wasm_runtime, wasm_root):
    """`pengu run --target wasm` builds app.html (+ .js/.wasm) and node runs it."""
    project = tmp_path / "hello"
    (project / "src").mkdir(parents=True)
    (project / "pengu.toml").write_text(
        '[project]\nname = "hello"\nversion = "0.1.0"\n'
        'entry = "src/main.pengu"\noutput = "exe"\noutput_name = "hello"\n\n'
        '[build]\nsrc_dir = "src"\nbuild_dir = "build"\ncflags = ["-std=c11"]\n',
        encoding="utf-8")
    (project / "src" / "main.pengu").write_text(
        'import std.spark\n\nweave main into int:\n'
        '    calling spark.println with "hello from wasm"\n    return 0\n',
        encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "build",
         "--config", str(project), "--target", "wasm32-unknown-emscripten"],
        capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"

    html = project / "build" / "hello.html"
    js = project / "build" / "hello.js"
    wasm = project / "build" / "hello.wasm"
    assert html.is_file(), "EXE output for wasm must be app.html"
    assert js.is_file() and wasm.is_file(), "emcc -o app.html also writes app.js + app.wasm"

    run = subprocess.run([node, str(js)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    assert "hello from wasm" in run.stdout


@pytest.mark.slow
def test_wasm_static_archive_contains_wasm_objects(tmp_path, emcc, emar_path, wasm_root):
    """`output = "static"` on wasm produces an archive of wasm objects (emar)."""
    project = tmp_path / "libproj"
    (project / "src").mkdir(parents=True)
    (project / "pengu.toml").write_text(
        '[project]\nname = "libproj"\nversion = "0.1.0"\n'
        'entry = "src/lib.pengu"\noutput = "static"\noutput_name = "libproj"\n\n'
        '[build]\nsrc_dir = "src"\nbuild_dir = "build"\ncflags = ["-std=c11"]\n',
        encoding="utf-8")
    (project / "src" / "lib.pengu").write_text(
        "weave add_one with x as int into int:\n    return x + 1\n",
        encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "build",
         "--config", str(project), "--target", "wasm32-unknown-emscripten"],
        capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"

    archive = project / "build" / "libproj.a"
    assert archive.is_file()
    # `ar` would have written a host archive; the member must be a wasm module.
    extract = tmp_path / "extract"
    extract.mkdir()
    subprocess.run([emar_path, "x", str(archive)], cwd=str(extract),
                   capture_output=True, text=True, timeout=300, check=True)
    members = list(extract.iterdir())
    assert members, "the archive has no members"
    magic = members[0].read_bytes()[:4]
    assert magic == b"\x00asm", f"archive member is not a wasm object (magic={magic!r})"


@pytest.mark.slow
def test_wasm_shared_output_is_refused(tmp_path, emcc, wasm_root):
    """A wasm shared library needs -fPIC everywhere; we refuse instead of lying."""
    project = tmp_path / "shproj"
    (project / "src").mkdir(parents=True)
    (project / "pengu.toml").write_text(
        '[project]\nname = "shproj"\nversion = "0.1.0"\n'
        'entry = "src/lib.pengu"\noutput = "shared"\noutput_name = "shproj"\n\n'
        '[build]\nsrc_dir = "src"\nbuild_dir = "build"\ncflags = ["-std=c11"]\n',
        encoding="utf-8")
    (project / "src" / "lib.pengu").write_text(
        "weave add_one with x as int into int:\n    return x + 1\n",
        encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "build",
         "--config", str(project), "--target", "wasm32-unknown-emscripten"],
        capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode != 0
    assert "shared libraries are not supported" in (res.stdout + res.stderr)


@pytest.mark.slow
def test_wasi_target_is_refused_clearly(tmp_path, wasm_root):
    """WASI is a roadmap item: refuse it by name, not with a MinGW message."""
    project = tmp_path / "wasiproj"
    (project / "src").mkdir(parents=True)
    (project / "pengu.toml").write_text(
        '[project]\nname = "wasiproj"\nversion = "0.1.0"\n'
        'entry = "src/main.pengu"\noutput = "exe"\noutput_name = "wasiproj"\n\n'
        '[build]\nsrc_dir = "src"\nbuild_dir = "build"\ncflags = ["-std=c11"]\n',
        encoding="utf-8")
    (project / "src" / "main.pengu").write_text(
        'import std.spark\n\nweave main into int:\n    return 0\n', encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "build",
         "--config", str(project), "--target", "wasm32-wasi"],
        capture_output=True, text=True, timeout=300,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert "WASI" in combined
    assert "not supported" in combined


@pytest.mark.slow
def test_filum_stress_native(host_runtime, wasm_root):
    """The stress program passes on the host (baseline for the wasm run)."""
    script = Path(__file__).parent / "filum_stress.pengu"
    res = subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "run",
         "--no-cache", "--ephemeral", str(script)],
        capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "filum_stress: OK" in res.stdout
    for marker in ("FAIL:", "LeakSanitizer", "AddressSanitizer"):
        assert marker not in res.stdout + res.stderr


@pytest.mark.slow
def test_filum_stress_wasm(run_wasm_script):
    """The same stress program passes on wasm, with real Worker threads."""
    source = (Path(__file__).parent / "filum_stress.pengu").read_text(encoding="utf-8")
    res = run_wasm_script(source, tag="filum_stress")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "filum_stress: OK" in res.stdout
    assert "FAIL:" not in res.stdout


@pytest.mark.slow
def test_filum_handle_leakcheck_native(leakcheck_binary):
    """Every filum handle is released (deterministic; LSAN cannot see these)."""
    binary = leakcheck_binary()
    res = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "filum_leakcheck: OK" in res.stdout
    assert "FAIL" not in res.stdout


@pytest.mark.slow
def test_filum_handle_leakcheck_is_not_vacuous(leakcheck_binary):
    """The harness must *notice* the leak it deliberately creates."""
    binary = leakcheck_binary("leakcheck_selftest")
    res = subprocess.run([str(binary), "selftest"], capture_output=True, text=True,
                         timeout=300)
    assert "was detected" in res.stdout
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"


@pytest.mark.slow
def test_filum_handle_leakcheck_wasm(leakcheck_wasm_js, node):
    """The same handle accounting holds on the wasm runtime."""
    js = leakcheck_wasm_js()
    res = subprocess.run([node, str(js)], capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "filum_leakcheck: OK" in res.stdout
    assert "FAIL" not in res.stdout


@pytest.mark.slow
def test_wasm_runtime_archive_builds(tmp_path, emcc, wasm_root, wasm_runtime):
    """`build_runtime.py --target emscripten` is idempotent and reports the artifact."""
    res = subprocess.run(
        [sys.executable, str(wasm_root / "build_runtime.py"), "--target", "emscripten"],
        capture_output=True, text=True, timeout=900, cwd=str(wasm_root),
        env={**os.environ, "PYTHONPATH": str(wasm_root)})
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "libpengu_runtime.a" in res.stdout


def _make_test_project(tmp_path, body: str):
    """A minimal project with one ``test`` block in its entry point."""
    project = tmp_path / "tproj"
    (project / "src").mkdir(parents=True)
    (project / "pengu.toml").write_text(
        '[project]\nname = "tproj"\nversion = "0.1.0"\n'
        'entry = "src/main.pengu"\noutput = "exe"\noutput_name = "tproj"\n\n'
        '[build]\nsrc_dir = "src"\nbuild_dir = "build"\ncflags = ["-std=c11"]\n',
        encoding="utf-8")
    (project / "src" / "main.pengu").write_text(body, encoding="utf-8")
    return project


def _run_pengu_test(project, wasm_root, target: str, timeout: int = 900):
    return subprocess.run(
        [sys.executable, str(wasm_root / "pengu_project.py"), "test",
         "--config", str(project), "--target", target],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "PYTHONPATH": str(wasm_root)})


#: A program that deliberately leaks `maybe` cells. `maybe T` is an owned heap
#: cell (`some val` boxes the payload), so a received value that is never
#: `banish`ed leaks. Used to prove the sanitizer harness is not silently inert.
#:
#: Shape note: this is the loop form, which reproduces reliably. A single `recv`
#: in the function body did NOT leak in testing (the generator appears to release
#: a function-scoped owned local on the way out), so a minimal version of this
#: program would have made the harness look inert.
_LEAKY_PENGU = """\
import std.spark
import std.filum

weave main into int:
    var ch as filum.ChanInt is calling filum.chan_int with 4
    var i as int is 0
    while i < 5:
        var sent as bool is calling ch.send with i
        var m as maybe int is calling ch.recv
        var got as int is -1
        if v as int is m:
            set got is v
        set i is i + 1
    calling filum.free_chan_int with (sigil of ch)
    calling spark.println with "leaky program finished"
    return 0
"""

#: The flags that make Emscripten's ASan actually check for leaks.
#:
#: `-fsanitize=address` alone is NOT enough: LeakSanitizer reports from an
#: `atexit` hook, and `EXIT_RUNTIME=0` (the default this project uses) never
#: tears the runtime down, so LSan stays silent and a leaky program still exits
#: 0. Verified both ways: without `-s EXIT_RUNTIME=1` the program below is
#: reported clean; with it, `LeakSanitizer: detected memory leaks`.
_WASM_ASAN_ENV = {
    "PENGU_CFLAGS": "-fsanitize=address -fno-omit-frame-pointer",
    "PENGU_LDFLAGS": "-fsanitize=address -s EXIT_RUNTIME=1",
}


@pytest.mark.slow
def test_wasm_asan_harness_detects_a_leak(run_wasm_script):
    """The wasm ASan+LSan flags must be load-bearing.

    Without this, a "no leaks" assertion could pass against an uninstrumented
    build and prove nothing -- which is exactly what happened here first: script
    mode prefers the bundled TCC, which silently ignores `-fsanitize=...`.
    """
    res = run_wasm_script(_LEAKY_PENGU, tag="leaky_wasm", env=_WASM_ASAN_ENV)
    combined = res.stdout + res.stderr
    assert "LeakSanitizer" in combined or "AddressSanitizer" in combined, \
        f"LSan did not report the deliberate leak:\n{combined}"
    assert res.returncode != 0


@pytest.mark.slow
def test_wasm_stress_has_no_leaks(run_wasm_script):
    """filum_stress under an instrumented wasm build: no leaks, no UB."""
    source = (Path(__file__).parent / "filum_stress.pengu").read_text(encoding="utf-8")
    res = run_wasm_script(source, tag="filum_stress_asan", env=_WASM_ASAN_ENV)
    combined = res.stdout + res.stderr
    assert "filum_stress: OK" in res.stdout, f"{res.stdout}\n{res.stderr}"
    assert "FAIL:" not in res.stdout
    for marker in ("LeakSanitizer", "AddressSanitizer", "runtime error", "Sanitizer"):
        assert marker not in combined, f"{marker} in output:\n{combined}"
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"


@pytest.mark.slow
def test_native_stress_has_no_leaks(run_host_script):
    """The same program under native ASan + UBSan + LSan.

    ``PENGU_DEV_CC=clang`` is required: script mode prefers the bundled TCC, and
    TCC silently ignores ``-fsanitize=...`` (measured), so the run would look
    clean while being completely uninstrumented.
    """
    if not shutil.which("clang"):
        pytest.skip("clang not on PATH (needed for the sanitizers)")
    source = (Path(__file__).parent / "filum_stress.pengu").read_text(encoding="utf-8")
    res = run_host_script(source, tag="filum_stress_asan", env={
        "PENGU_DEV_CC": "clang",
        "PENGU_CFLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer "
                        "-fno-sanitize-recover=all",
        "PENGU_LDFLAGS": "-fsanitize=address,undefined",
    })
    combined = res.stdout + res.stderr
    assert "filum_stress: OK" in res.stdout, f"{res.stdout}\n{res.stderr}"
    for marker in ("LeakSanitizer", "AddressSanitizer", "runtime error", "Sanitizer"):
        assert marker not in combined, f"{marker} in output:\n{combined}"
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"


@pytest.mark.slow
def test_pengu_test_target_wasm(tmp_path, emcc, node, wasm_runtime, wasm_root):
    """`pengu test --target wasm` runs the test bundle through Node.

    Regression guard: ``test_project`` exec'd the built artifact directly, so a
    wasm target tried to execute ``app.html`` (``PermissionError``). It now goes
    through the same loader path as ``pengu run``.
    """
    project = _make_test_project(
        tmp_path,
        'import std.trial\n\n'
        'weave add with a as int, b as int into int:\n'
        '    return a + b\n\n'
        'test "adds two numbers":\n'
        '    calling trial.assert_eq_int with (calling add with 2, 3), 5\n\n'
        'weave main into int:\n    return 0\n')
    res = _run_pengu_test(project, wasm_root, "wasm32-unknown-emscripten")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "All 1 test(s) passed" in res.stdout


@pytest.mark.slow
def test_pengu_test_target_wasm_propagates_failure(tmp_path, emcc, node,
                                                   wasm_runtime, wasm_root):
    """A failing test must still exit non-zero through Node."""
    project = _make_test_project(
        tmp_path,
        'import std.trial\n\n'
        'test "this one fails":\n'
        '    calling trial.assert_eq_int with 1, 2\n\n'
        'weave main into int:\n    return 0\n')
    res = _run_pengu_test(project, wasm_root, "wasm32-unknown-emscripten")
    assert res.returncode == 1, f"{res.stdout}\n{res.stderr}"
    # The panic report is on stderr; the runner's own progress is on stdout.
    assert "[PANIC]" in res.stdout + res.stderr


@pytest.mark.slow
def test_exec_reports_unsupported_on_wasm(run_wasm_script):
    """`exec`/`spawn` cannot work in wasm: they must fail loudly, not fake success.

    ``pengu_c_exec`` is guarded by ``#if PENGU_EMSCRIPTEN`` because Emscripten's
    ``system()`` is a stub whose return status a caller could misread as success.
    ``rites.run_shell`` is the thin public wrapper that reaches it.
    """
    res = run_wasm_script(
        'import std.spark\nimport std.rites\n\n'
        'weave main into int:\n'
        '    var rc as int is calling rites.run_shell with "echo hi"\n'
        '    if rc < 0:\n        return 7\n    return 0\n',
        tag="exec_wasm")
    assert res.returncode == 7, \
        f"expected the documented -1:\n{res.stdout}\n{res.stderr}"
    assert "exec no soportado en wasm" in res.stderr


@pytest.mark.slow
def test_exec_still_works_on_the_host(run_host_script):
    """The guard must be wasm-only: the host keeps a working exec()."""
    res = run_host_script(
        'import std.spark\nimport std.rites\n\n'
        'weave main into int:\n'
        '    var rc as int is calling rites.run_shell with "exit 0"\n'
        '    if rc == 0:\n        return 0\n    return 9\n',
        tag="exec_host")
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "no soportado" not in res.stderr
