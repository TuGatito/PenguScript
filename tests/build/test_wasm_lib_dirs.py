"""WebAssembly library-directory selection.

A wasm object and a host object are not interchangeable.  The builder must
therefore search ``lib/wasm/`` (and ``lib/<binding>/lib/wasm/``) for an
``emscripten`` target, and must not hand the linker a host ``lib/`` archive.
"""
from __future__ import annotations

from pathlib import Path

from pengu_project import PenguBuilder, ProjectConfig


def _builder(base: Path, target: str) -> PenguBuilder:
    config = ProjectConfig._from_dict(
        {
            "project": {"name": "wasm-dirs", "entry": "main.pengu"},
            "build": {"target": target, "lib_dir": "lib"},
        },
        str(base),
    )
    return PenguBuilder(config)


def test_wasm_target_searches_only_lib_wasm(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "libhost.a").write_text("", encoding="utf-8")
    (tmp_path / "lib" / "wasm").mkdir()
    (tmp_path / "lib" / "wasm" / "libraylib.a").write_text("", encoding="utf-8")

    lib_dirs, links = _builder(tmp_path, "wasm32-unknown-emscripten").collect_lib_dirs_and_links()

    assert str(tmp_path / "lib" / "wasm") in lib_dirs
    assert str(tmp_path / "lib") not in lib_dirs
    assert "raylib" in links
    assert "host" not in links


def test_wasm_target_uses_binding_lib_wasm(tmp_path):
    binding = tmp_path / "lib" / "raylib-pengu"
    (binding / "lib" / "wasm").mkdir(parents=True)
    (binding / "lib" / "libraylib.a").write_text("", encoding="utf-8")
    (binding / "lib" / "wasm" / "libraylib.a").write_text("", encoding="utf-8")

    lib_dirs, links = _builder(tmp_path, "wasm32-unknown-emscripten").collect_lib_dirs_and_links()

    assert str(binding / "lib" / "wasm") in lib_dirs
    assert str(binding / "lib") not in lib_dirs
    assert "raylib" in links


def test_native_target_still_searches_host_lib(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "libraylib.a").write_text("", encoding="utf-8")

    lib_dirs, links = _builder(tmp_path, "").collect_lib_dirs_and_links()

    assert str(tmp_path / "lib") in lib_dirs
    assert "raylib" in links
