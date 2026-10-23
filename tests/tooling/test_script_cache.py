"""Regression tests for the script cache and the stable asset lookup.

These are the properties that made ``pengu run`` rebuild on every invocation:

* the cache key must ignore the path of a module (a PyInstaller onefile build
  extracts ``std/`` into a new ``/tmp/_MEI...`` on every run) but keep its
  content and logical identity;
* the import manifest must store root-relative references, so the same manifest
  works with a different std root while still invalidating when a module changes;
* a frozen ``pengu`` must prefer the stable installation assets over ``_MEIPASS``
  and find a TCC placed next to the executable;
* ``run``/``time``/``watch``/``expand`` must agree on the script's base directory.

No C compiler or subprocess is involved except in the two ``slow`` builder tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pengu_cache  # noqa: E402
import pengu_paths  # noqa: E402
import pengu_tcc  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _module_ids(modules, *, entry, base_dir, std_dirs):
    return [
        pengu_cache.logical_module_id(
            str(mod), entry_abs=str(entry), base_dir=str(base_dir),
            std_dirs=[str(d) for d in std_dirs])
        for mod in modules
    ]


@pytest.mark.smoke
def test_script_cache_key_is_layout_independent(tmp_path):
    """Same logical modules, same content, different roots -> same key."""
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    std_a = root_a / "std"
    std_b = root_b / "std"
    _write(std_a / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    _write(std_b / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    entry = _write(tmp_path / "app.pengu", "weave main into int:\n    return 0\n")

    mods_a = [std_a / "spark.pengu", entry]
    mods_b = [std_b / "spark.pengu", entry]
    ids_a = _module_ids(mods_a, entry=entry, base_dir=tmp_path, std_dirs=[std_a])
    ids_b = _module_ids(mods_b, entry=entry, base_dir=tmp_path, std_dirs=[std_b])

    key_a = pengu_cache.script_cache_key(
        str(entry), [str(m) for m in mods_a], version="x", cc="/tmp/A/tcc",
        module_ids=ids_a, entry_id=ids_a[-1])
    key_b = pengu_cache.script_cache_key(
        str(entry), [str(m) for m in mods_b], version="x", cc="/tmp/B/tcc",
        module_ids=ids_b, entry_id=ids_b[-1])
    assert key_a == key_b


@pytest.mark.smoke
def test_script_cache_key_tracks_content_identity_and_flags(tmp_path):
    std = tmp_path / "std"
    spark = _write(std / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    entry = _write(tmp_path / "app.pengu", "weave main into int:\n    return 0\n")
    ids = _module_ids([spark, entry], entry=entry, base_dir=tmp_path, std_dirs=[std])
    base = pengu_cache.script_cache_key(
        str(entry), [str(spark), str(entry)], version="x", cc="gcc",
        module_ids=ids, entry_id=ids[-1])
    _write(spark, 'const SPARK_VERSION as string is "2"\n')
    changed = pengu_cache.script_cache_key(
        str(entry), [str(spark), str(entry)], version="x", cc="gcc",
        module_ids=ids, entry_id=ids[-1])
    assert base != changed
    other_flag = pengu_cache.script_cache_key(
        str(entry), [str(spark), str(entry)], version="x", cc="gcc", profile="release",
        module_ids=ids, entry_id=ids[-1])
    assert changed != other_flag


@pytest.mark.smoke
def test_script_cache_key_includes_runtime_archive(tmp_path):
    std = tmp_path / "std"
    spark = _write(std / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    entry = _write(tmp_path / "app.pengu", "weave main into int:\n    return 0\n")
    ids = _module_ids([spark, entry], entry=entry, base_dir=tmp_path, std_dirs=[std])
    archive = tmp_path / "libpengu_runtime.a"
    archive.write_bytes(b"one")
    first = pengu_cache.script_cache_key(
        str(entry), [str(spark), str(entry)], version="x", cc="gcc",
        runtime_archive=str(archive), module_ids=ids, entry_id=ids[-1])
    archive.write_bytes(b"two")
    second = pengu_cache.script_cache_key(
        str(entry), [str(spark), str(entry)], version="x", cc="gcc",
        runtime_archive=str(archive), module_ids=ids, entry_id=ids[-1])
    assert first != second


@pytest.mark.smoke
def test_import_manifest_remaps_std_root_and_invalidates_on_edit(tmp_path, monkeypatch):
    """A manifest stores `std:...`, so a new extraction root is not a miss."""
    monkeypatch.setenv("PENGU_CACHE_DIR", str(tmp_path / "cache"))
    std_a = tmp_path / "a" / "std"
    std_b = tmp_path / "b" / "std"
    _write(std_a / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    _write(std_b / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    entry = _write(tmp_path / "app.pengu", "weave main into int:\n    return 0\n")
    res_a = {"base_dir": str(tmp_path), "lib_dir": "lib", "src_dir": "src",
             "std_dirs": [str(std_a)]}
    res_b = dict(res_a, std_dirs=[str(std_b)])

    pengu_cache.store_module_list(
        str(entry), [str(std_a / "spark.pengu"), str(entry)], res_a)
    modules = pengu_cache.load_module_list(str(entry), res_b)
    assert modules is not None
    assert modules[0] == str(std_b / "spark.pengu")

    # Same logical module, different content in the *selected* root: invalid.
    _write(std_b / "spark.pengu", 'const SPARK_VERSION as string is "2"\n')
    assert pengu_cache.load_module_list(str(entry), res_b) is None


@pytest.mark.smoke
def test_import_manifest_invalidates_on_resolution_change(tmp_path, monkeypatch):
    monkeypatch.setenv("PENGU_CACHE_DIR", str(tmp_path / "cache"))
    std = tmp_path / "std"
    spark = _write(std / "spark.pengu", 'const SPARK_VERSION as string is "1"\n')
    entry = _write(tmp_path / "app.pengu", "weave main into int:\n    return 0\n")
    res = {"base_dir": str(tmp_path), "lib_dir": "lib", "src_dir": "src",
           "std_dirs": [str(std)]}
    pengu_cache.store_module_list(str(entry), [str(spark), str(entry)], res)

    assert pengu_cache.load_module_list(
        str(entry), dict(res, lib_dir="vendor")) is None
    assert pengu_cache.load_module_list(
        str(entry), dict(res, src_dir="pengu")) is None
    assert pengu_cache.load_module_list(
        str(entry), dict(res, base_dir=str(tmp_path / "other"))) is None


@pytest.mark.smoke
def test_frozen_std_prefers_install_dir_over_meipass(tmp_path, monkeypatch):
    mei = tmp_path / "mei"
    exe = tmp_path / "exe"
    (mei / "std").mkdir(parents=True)
    (exe / "std").mkdir(parents=True)
    monkeypatch.setattr(pengu_paths, "module_root", lambda: mei)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe / "pengu"))
    monkeypatch.setattr(sys, "_MEIPASS", str(mei), raising=False)

    dirs = [str(p) for p in pengu_paths.std_dirs()]
    assert dirs.index(str(exe / "std")) < dirs.index(str(mei / "std"))


@pytest.mark.smoke
def test_find_tcc_next_to_frozen_executable(tmp_path, monkeypatch):
    exe = tmp_path / "exe"
    exe.mkdir()
    (exe / "pengu").write_text("", encoding="utf-8")
    tcc = exe / "tcc" / "tcc"
    tcc.parent.mkdir()
    tcc.write_text("#!/bin/sh\n", encoding="utf-8")
    tcc.chmod(0o755)

    monkeypatch.setattr(sys, "executable", str(exe / "pengu"))
    monkeypatch.setattr(pengu_tcc, "_bundle_base", lambda: str(tmp_path / "empty"))
    monkeypatch.delenv("PENGU_TCC", raising=False)
    monkeypatch.delenv("PENGU_NO_TCC", raising=False)
    assert pengu_tcc.find_tcc() == str(tcc)


@pytest.mark.smoke
def test_script_build_context_uses_script_directory(tmp_path, monkeypatch):
    from pengu_project import _script_build_context

    project = tmp_path / "project"
    _write(project / "pengu.toml", "")
    script = _write(project / "src" / "app.pengu", "weave main into int:\n    return 0\n")
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    base_dir, _manifest, _src, _lib, _inc = _script_build_context(str(script))
    assert Path(base_dir) == project


@pytest.mark.smoke
def test_release_bundles_tcc_where_find_tcc_probes(tmp_path):
    """PyInstaller appends the basename; `DEST=tcc/tcc` landed at tcc/tcc/tcc."""
    from make_release import tcc_add_binary_args

    tcc = tmp_path / "bin" / "tcc"
    tcc.parent.mkdir()
    tcc.write_text("#!/bin/sh\n", encoding="utf-8")
    include = tmp_path / "lib" / "tcc" / "include"
    include.mkdir(parents=True)
    (include / "stdarg.h").write_text("", encoding="utf-8")

    args = tcc_add_binary_args(tcc, ":")
    assert args[0] == f"{tcc}:tcc"
    assert args[1] == f"{include}:tcc/include"


@pytest.mark.slow
def test_builder_uses_supplied_module_order_and_cached_trees(tmp_path, monkeypatch):
    """`bundle()` must not re-resolve and must reuse the resolver's ASTs."""
    from pengu_parser.pengu_symbols import clear_module_tree_cache, resolve_imports
    from pengu_project import OutputType, PenguBuilder, ProjectConfig

    helper = _write(
        tmp_path / "helper.pengu",
        "weave add_one with x as int into int:\n    return x + 1\n",
    )
    entry = _write(
        tmp_path / "app.pengu",
        'import helper\n\nweave main into int:\n    return calling add_one with 1\n',
    )
    cfg = ProjectConfig(
        entry=str(entry), base_dir=str(tmp_path), output=OutputType.C,
        output_name="app", name="app", build_dir=str(tmp_path / "build"),
    )
    clear_module_tree_cache()
    builder = PenguBuilder(cfg)
    builder.entry_as_main = True
    order = resolve_imports(str(tmp_path), str(entry), builder.parser)
    assert str(helper) in [os.path.abspath(p) for p in order]

    # Fail loudly if bundle() resolves imports again.
    import pengu_parser.pengu_symbols as symbols
    monkeypatch.setattr(
        symbols, "resolve_imports",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("re-resolved imports")),
    )

    calls = {"n": 0}
    original_parse = builder.parser.parse

    def counted_parse(*args, **kwargs):
        calls["n"] += 1
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(builder.parser, "parse", counted_parse)
    builder.module_order = order
    bundle_path, is_cached = builder.bundle()
    assert not is_cached
    assert Path(bundle_path).is_file()
    assert calls["n"] == 0, "checker parsed a module instead of reusing cached_module_tree()"
