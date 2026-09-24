"""Unit tests for pengu_paths and multi-layout asset discovery in PenguScript 0.14.0."""

import os
from pathlib import Path
import pytest

import pengu_paths
import pengu_version
from pengu_project import PENGU_VERSION
from pengu_parser.pengu_symbols import get_stdlib_dirs


def test_version_sync_0_14_0():
    """Verify toolchain version 0.14.0 is synchronized across all modules."""
    assert pengu_version.__version__ == "0.14.0"
    assert pengu_version.FALLBACK_VERSION == "0.14.0"
    assert PENGU_VERSION == "0.14.0"
    assert pengu_version.read_version_file() == "0.14.0"


def test_source_checkout_discovery():
    """Verify default discovery in a source checkout."""
    header = pengu_paths.find_runtime_header()
    assert header is not None
    assert header.is_file()
    assert header.name == "pengu_runtime.h"

    vfile = pengu_paths.find_version_file()
    assert vfile is not None
    assert vfile.is_file()
    assert vfile.name == "VERSION"

    std_dirs = pengu_paths.std_dirs()
    assert len(std_dirs) > 0
    assert any((d / "spark.pengu").is_file() for d in std_dirs)


def test_fhs_layout_resolution(tmp_path, monkeypatch):
    """Verify discovery when assets are placed in an FHS structure."""
    fake_prefix = tmp_path / "usr_local"
    inc_dir = fake_prefix / "include" / "pengu"
    lib_dir = fake_prefix / "lib" / "pengu"
    share_std = fake_prefix / "share" / "pengu" / "std"
    share_dir = fake_prefix / "share" / "pengu"

    inc_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)
    share_std.mkdir(parents=True)

    fake_header = inc_dir / "pengu_runtime.h"
    fake_header.write_text("/* fake runtime */", encoding="utf-8")

    fake_version = share_dir / "VERSION"
    fake_version.write_text("0.14.0-fhs", encoding="utf-8")

    fake_lib = lib_dir / "libpengu_runtime.a"
    fake_lib.write_text("fake lib", encoding="utf-8")

    fake_module = share_std / "spark.pengu"
    fake_module.write_text("weave println into void: pass", encoding="utf-8")

    monkeypatch.setenv("PENGU_PREFIX", str(fake_prefix))

    inc_dirs = pengu_paths.runtime_include_dirs()
    assert inc_dir.resolve() in [d.resolve() for d in inc_dirs]

    lib_dirs = pengu_paths.runtime_lib_dirs()
    assert lib_dir.resolve() in [d.resolve() for d in lib_dirs]

    std_dirs = pengu_paths.std_dirs()
    assert share_std.resolve() in [d.resolve() for d in std_dirs]

    assert pengu_paths.find_runtime_header() == fake_header.resolve()
    assert pengu_paths.find_version_file() == fake_version.resolve()

    # Verify pengu_symbols discovers std module from FHS share dir
    stdlib_dirs = get_stdlib_dirs(str(tmp_path))
    assert str(share_std.resolve()) in [os.path.realpath(d) for d in stdlib_dirs]


def test_env_overrides(tmp_path, monkeypatch):
    """Verify explicit environment variable overrides short-circuit discovery."""
    custom_inc = tmp_path / "custom_include"
    custom_inc.mkdir()
    custom_header = custom_inc / "pengu_runtime.h"
    custom_header.write_text("/* custom */", encoding="utf-8")

    custom_lib = tmp_path / "custom_lib"
    custom_lib.mkdir()

    custom_std = tmp_path / "custom_std"
    custom_std.mkdir()

    custom_vfile = tmp_path / "CUSTOM_VERSION"
    custom_vfile.write_text("9.9.9", encoding="utf-8")

    monkeypatch.setenv("PENGU_INCLUDE_DIR", str(custom_inc))
    monkeypatch.setenv("PENGU_LIB_DIR", str(custom_lib))
    monkeypatch.setenv("PENGU_STD_DIR", str(custom_std))
    monkeypatch.setenv("PENGU_VERSION_FILE", str(custom_vfile))
    monkeypatch.setenv("PENGU_RUNTIME_HEADER", str(custom_header))

    assert custom_inc.resolve() in [d.resolve() for d in pengu_paths.runtime_include_dirs()]
    assert custom_lib.resolve() in [d.resolve() for d in pengu_paths.runtime_lib_dirs()]
    assert custom_std.resolve() in [d.resolve() for d in pengu_paths.std_dirs()]
    assert pengu_paths.find_runtime_header() == custom_header.resolve()
    assert pengu_paths.find_version_file() == custom_vfile.resolve()
    assert pengu_version.read_version_file() == "9.9.9"


def test_nonexistent_prefix_resilience(monkeypatch):
    """Verify no exceptions occur when PENGU_PREFIX points to a nonexistent directory."""
    monkeypatch.setenv("PENGU_PREFIX", "/nonexistent/path/for/sure")
    # All methods must execute cleanly without raising
    _ = pengu_paths.runtime_include_dirs()
    _ = pengu_paths.runtime_lib_dirs()
    _ = pengu_paths.std_dirs()
    _ = pengu_paths.version_files()
    _ = pengu_paths.find_runtime_header()
    _ = pengu_paths.find_std_dir()
    _ = pengu_paths.find_version_file()


def test_pkg_config_graceful_missing():
    """Verify pkg_config helpers return empty lists for nonexistent packages."""
    cflags = pengu_paths.pkg_config_cflags("nonexistent_package_xyz123")
    assert cflags == []
    libs = pengu_paths.pkg_config_libs("nonexistent_package_xyz123")
    assert libs == []
