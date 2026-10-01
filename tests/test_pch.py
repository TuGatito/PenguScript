"""Precompiled-header behaviour (``pengu_runtime.h`` -> ``.gch``).

Two mechanisms are covered:

* the *generated* PCH that ``PenguBuilder._ensure_runtime_pch`` builds inside the
  project's build directory, tied to a signature of the ``-I``/``-D`` flags;
* the *packaged* PCH that ``build_runtime.py`` writes next to the runtime header
  in ``build/include/`` (reused as-is, see ``_runtime_pch_exists``).

Generating a PCH only needs a C compiler and the runtime header, not the built
runtime archive, so these tests do not require ``build_runtime.py`` to have run.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from tests.conftest import have_tool

pytestmark = pytest.mark.skipif(
    not (have_tool("gcc") or have_tool("clang")), reason="no gcc/clang"
)


def _cc() -> str:
    return "gcc" if have_tool("gcc") else "clang"


def _builder(tmp_path, cc=None, use_pch=True, output=None,
             output_name="p", name="p", build_dir=None):
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    script = tmp_path / "p.pengu"
    script.write_text("weave main into int:\n    return 0\n", encoding="utf-8")
    cfg = ProjectConfig(entry=str(script), base_dir=str(tmp_path),
                        output=output or OutputType.C,
                        output_name=output_name, name=name,
                        build_dir=str(build_dir or (tmp_path / "b")))
    cfg.cc = cc or _cc()
    builder = PenguBuilder(cfg)
    builder.use_pch = use_pch
    return builder


def _make_pch(builder, build_dir, base_flags):
    return builder._ensure_runtime_pch(str(build_dir), list(base_flags), builder.config.cc)


def test_pch_generates_gch(tmp_path):
    builder = _builder(tmp_path)
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    pch_dir = _make_pch(builder, build_dir, ["-O0", f"-I{build_dir}", "-DPENGU_TEST=1"])

    assert pch_dir, "PCH generation must succeed on a machine with gcc/clang"
    gch = Path(pch_dir) / "pengu_runtime.h.gch"
    assert gch.is_file()
    assert gch.stat().st_size > 0
    assert (Path(pch_dir) / "pengu_runtime.h").is_file()


def test_pch_reused_across_builds(tmp_path):
    builder = _builder(tmp_path)
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    flags = ["-O0", f"-I{build_dir}"]

    pch_dir = _make_pch(builder, build_dir, flags)
    assert pch_dir
    gch = Path(pch_dir) / "pengu_runtime.h.gch"
    stamp = gch.stat().st_mtime_ns

    # Give the filesystem time to produce a different mtime if it rebuilt.
    time.sleep(0.05)
    pch_dir2 = _make_pch(builder, build_dir, flags)
    assert pch_dir2 == pch_dir
    assert gch.stat().st_mtime_ns == stamp, "an unchanged signature must reuse the .gch"


def test_pch_signature_change_rebuilds(tmp_path):
    builder = _builder(tmp_path)
    build_dir = tmp_path / "b"
    build_dir.mkdir()
    flags = ["-O0", f"-I{build_dir}"]

    pch_dir = _make_pch(builder, build_dir, flags)
    assert pch_dir
    gch = Path(pch_dir) / "pengu_runtime.h.gch"
    stamp = gch.stat().st_mtime_ns

    time.sleep(0.05)
    # Touch the header copy so the stale-check would also trigger a rebuild, and
    # change a define: a different program must not reuse the previous .gch.
    header = Path(pch_dir) / "pengu_runtime.h"
    os.utime(header, None)
    pch_dir2 = _make_pch(builder, build_dir, flags + ["-DPENGU_EXTRA=1"])
    assert pch_dir2 == pch_dir
    assert gch.stat().st_mtime_ns != stamp, "a new signature must rebuild the .gch"


def test_shared_pch_is_discovered_and_preferred(tmp_path, monkeypatch):
    """A .gch shipped next to the runtime header is used without regeneration."""
    from pengu_project import OutputType

    shared = tmp_path / "shared-include"
    shared.mkdir()
    (shared / "pengu_runtime.h").write_text("/* fake */\n", encoding="utf-8")
    (shared / "pengu_runtime.h.gch").write_bytes(b"gch")
    monkeypatch.setenv("PENGU_INCLUDE_DIR", str(shared))

    builder = _builder(tmp_path, output=OutputType.EXE)
    assert builder._runtime_pch_exists() == str(shared)

    script = tmp_path / "p.pengu"
    out = tmp_path / "p"
    commands = builder.build_compile_commands(str(script), str(out))
    assert commands, "expected at least one compile command"
    first_i = next(f for f in commands[0] if f.startswith("-I"))
    assert first_i == f"-I{shared}", (
        "the packaged PCH directory must be the *first* include so gcc finds "
        f"pengu_runtime.h.gch next to it (got {first_i})"
    )


def test_no_pch_never_prefers_the_packaged_pch_dir(tmp_path, monkeypatch):
    from pengu_project import OutputType

    shared = tmp_path / "shared-include"
    shared.mkdir()
    (shared / "pengu_runtime.h.gch").write_bytes(b"gch")
    monkeypatch.setenv("PENGU_INCLUDE_DIR", str(shared))

    builder = _builder(tmp_path, use_pch=False, output=OutputType.EXE)
    commands = builder.build_compile_commands(str(tmp_path / "p.pengu"), str(tmp_path / "p"))
    first_i = next(f for f in commands[0] if f.startswith("-I"))
    assert first_i != f"-I{shared}"


def test_pch_is_skipped_for_tcc(tmp_path, monkeypatch):
    """TCC rejects PCH flags: the .gch directory must not be preferred."""
    from pengu_project import OutputType

    shared = tmp_path / "shared-include"
    shared.mkdir()
    (shared / "pengu_runtime.h.gch").write_bytes(b"gch")
    monkeypatch.setenv("PENGU_INCLUDE_DIR", str(shared))

    builder = _builder(tmp_path, cc="tcc", output=OutputType.EXE)
    commands = builder.build_compile_commands(str(tmp_path / "p.pengu"), str(tmp_path / "p"))
    first_i = next(f for f in commands[0] if f.startswith("-I"))
    assert first_i != f"-I{shared}"
