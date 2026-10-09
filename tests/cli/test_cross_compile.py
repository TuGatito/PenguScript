"""Roadmap Phase 3 / §3.5 — cross-compilation (Linux ⇄ Windows).

The runtime archive is host-built in 1.0, so the supported paths are: generate
the C bundle for any target, and link a cross executable when a cross compiler
plus a cross runtime (PENGU_RUNTIME_CROSS) are provided.
"""

import shutil
import subprocess
import sys

import pytest

from pengu_project import (
    CompileFailedError,
    OutputType,
    PenguBuilder,
    ProjectConfig,
    TargetTriple,
    host_os,
    parse_target_triple,
)
from tests.conftest import REPO


def test_parse_target_triple():
    assert parse_target_triple("x86_64-w64-mingw32").os == "windows"
    assert parse_target_triple("i686-w64-mingw32").arch == "i686"
    assert parse_target_triple("aarch64-apple-darwin").os == "darwin"
    assert parse_target_triple("x86_64-unknown-linux-gnu").os == "linux"
    assert parse_target_triple("x86_64-linux-musl").env == "musl"
    assert parse_target_triple("").os == ""
    assert parse_target_triple("x86_64-w64-mingw32").is_windows


def _builder(tmp_path, out_type, name="app", target=""):
    cfg = ProjectConfig(base_dir=str(tmp_path), output=out_type,
                        output_name=name, target=target)
    return PenguBuilder(cfg)


#: These tests describe the Linux/macOS -> Windows cross path.  On a Windows
#: host `x86_64-w64-mingw32` *is* the host, so `is_cross` is False and the cross
#: code is (correctly) never reached; the premise only exists elsewhere.
requires_cross_host = pytest.mark.skipif(
    host_os() == "windows",
    reason="the mingw target is the host here, so there is nothing to cross",
)


def test_artifact_names_follow_target_not_host(tmp_path):
    win = _builder(tmp_path, OutputType.EXE, target="x86_64-w64-mingw32")
    assert win.get_output_artifact_name() == "app.exe"
    assert win.is_cross is (host_os() != "windows")

    dll = _builder(tmp_path, OutputType.SHARED, name="foo", target="x86_64-w64-mingw32")
    assert dll.get_output_artifact_name().endswith(".dll")

    dylib = _builder(tmp_path, OutputType.SHARED, name="foo", target="aarch64-apple-darwin")
    assert dylib.get_output_artifact_name() == "libfoo.dylib"

    so = _builder(tmp_path, OutputType.SHARED, name="foo", target="x86_64-unknown-linux-gnu")
    assert so.get_output_artifact_name() == "libfoo.so"

    host_exe = _builder(tmp_path, OutputType.EXE)
    assert host_exe.is_cross is False


@requires_cross_host
def test_resolve_compiler_missing_cross_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    b = _builder(tmp_path, OutputType.EXE, target="x86_64-w64-mingw32")
    with pytest.raises(CompileFailedError) as exc:
        b.resolve_compiler()
    msg = str(exc.value)
    assert "mingw" in msg.lower()
    assert "PENGU_RUNTIME_CROSS" in msg


@requires_cross_host
def test_resolve_compiler_prefers_triple_gcc(tmp_path, monkeypatch):
    monkeypatch.setattr(
        shutil, "which",
        lambda name: "/usr/bin/" + name if name == "x86_64-w64-mingw32-gcc" else None,
    )
    b = _builder(tmp_path, OutputType.EXE, target="x86_64-w64-mingw32")
    assert b.resolve_compiler() == "x86_64-w64-mingw32-gcc"


def test_resolve_compiler_honours_explicit_cc(tmp_path):
    b = _builder(tmp_path, OutputType.EXE, target="x86_64-w64-mingw32")
    b.config.cc = "my-cross-gcc"
    assert b.resolve_compiler() == "my-cross-gcc"


@requires_cross_host
def test_cross_runtime_flags(tmp_path, monkeypatch):
    b = _builder(tmp_path, OutputType.EXE, target="x86_64-w64-mingw32")
    assert b.cross_runtime_flags() == []
    monkeypatch.setenv("PENGU_RUNTIME_CROSS", str(tmp_path))
    flags = b.cross_runtime_flags()
    assert any(f.startswith("-L") for f in flags)


def test_windows_target_bundle_is_generated_without_cross_cc(tmp_path):
    """A C-only build must work for any target (no cross toolchain needed)."""
    src = tmp_path / "main.pengu"
    src.write_text("weave main into int:\n  return 0\n", encoding="utf-8")
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: xt\n  entry: main.pengu\n", encoding="utf-8"
    )
    out = tmp_path / "win_bundle.c"
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build",
         "--config", str(tmp_path), "--target", "x86_64-w64-mingw32",
         "--output", str(out)],
        capture_output=True, text=True, timeout=180, cwd=str(tmp_path),
    )
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert out.is_file() and "pengu_main" in out.read_text(encoding="utf-8")


def test_cli_exposes_target_flag():
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert "--target" in res.stdout


@pytest.mark.skipif(not shutil.which("x86_64-w64-mingw32-gcc"),
                    reason="MinGW cross compiler not installed")
def test_real_mingw_cross_compile_bundle(tmp_path):
    """Compile-only cross check with a real MinGW toolchain, when available."""
    c = tmp_path / "b.c"
    c.write_text('#include "pengu_runtime.h"\nint main(void){return 0;}\n', encoding="utf-8")
    res = subprocess.run(
        ["x86_64-w64-mingw32-gcc", "-c", str(c), "-o", str(tmp_path / "b.o"),
         f"-I{REPO}", f"-I{REPO / 'build'}", f"-I{REPO / 'build' / 'include'}"],
        capture_output=True, text=True, timeout=180,
    )
    assert res.returncode == 0, res.stderr
