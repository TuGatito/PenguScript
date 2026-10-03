import os
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pengu_assets import (
    AssetConfig,
    generate,
    _collect,
    _asset_const_name,
    _c_ident,
    _sanitize_module,
)


def test_empty_assets_dir_returns_none(tmp_path):
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="arca",
        embed=True,
    )
    assert generate(cfg) is None


def test_embed_mode_generates_both_files(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hello.txt").write_bytes(b"hello world")
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="arca",
        embed=True,
    )
    result = generate(cfg)
    assert result is not None
    assert result["count"] == 1
    assert Path(result["interface"]).is_file()
    assert Path(result["impl"]).is_file()
    c_text = Path(result["impl"]).read_text(encoding="utf-8")
    assert "0x68, 0x65, 0x6C, 0x6C, 0x6F" in c_text  # "hello"
    assert "@generated" in Path(result["interface"]).read_text(encoding="utf-8")


def test_disk_mode_generates_disk_reader(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "x.bin").write_bytes(b"\x00\x01\x02")
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="arca",
        embed=False,
    )
    result = generate(cfg)
    assert result is not None
    c_text = Path(result["impl"]).read_text(encoding="utf-8")
    assert "fopen" in c_text
    assert "PENGU_ASSETS_DIR" in c_text


def test_exclude_pattern(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "keep.txt").write_bytes(b"k")
    (tmp_path / "assets" / "skip.psd").write_bytes(b"s")
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="arca",
        embed=True,
        exclude=["*.psd"],
    )
    result = generate(cfg)
    assert result is not None
    assert result["count"] == 1


from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    requires_cc,
    requires_runtime,
)
from pengu_project import PenguBuilder, ProjectConfig, OutputType, fmt_files


def _make_project(proj: Path, source: str, embed: bool = True, module: str = "arca") -> ProjectConfig:
    (proj / "src").mkdir(parents=True, exist_ok=True)
    (proj / "src" / "main.pengu").write_text(source, encoding="utf-8")
    lib = str(BUILD_LIB.resolve()).replace("\\", "/")
    inc = str(BUILD_INCLUDE.resolve()).replace("\\", "/")
    root = str(BUILD_DIR.resolve()).replace("\\", "/")
    embed_str = "true" if embed else "false"
    (proj / "pengu.yaml").write_text(
        'project:\n'
        '  name: "test_assets_app"\n'
        '  version: "0.1.0"\n'
        '  entry: "src/main.pengu"\n'
        '  output: "exe"\n'
        '  output_name: "test_assets_app"\n'
        '\n'
        'assets:\n'
        '  dir: "assets"\n'
        f'  module: "{module}"\n'
        f'  embed: {embed_str}\n'
        '\n'
        'build:\n'
        '  build_dir: "build"\n'
        '  links: ["pengu_runtime"]\n'
        f'  lib_dirs: ["{lib}"]\n'
        f'  include_dirs: ["{inc}", "{root}"]\n',
        encoding="utf-8",
    )
    return ProjectConfig.load(str(proj))


@requires_cc
@requires_runtime
def test_end_to_end_embed(tmp_path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "msg.txt").write_text("Hello from embedded assets!", encoding="utf-8")
    (assets_dir / "data.bin").write_bytes(b"\x01\x02\x03\x04")

    cname = _asset_const_name("msg.txt")
    source = f"""import arca
import std.spark

weave main into int:
    if calling arca.count != 2:
        return 10
    if not calling arca.has with "msg.txt":
        return 11
    if not calling arca.has with arca.{cname}:
        return 12
    if calling arca.has with "nonexistent.txt":
        return 13
    var n0 as string is calling arca.name with 0
    if n0 == "":
        return 14
    var s as string is calling arca.string with "msg.txt"
    if s != "Hello from embedded assets!":
        return 15
    banish s
    var b as slice of byte is calling arca.bytes with "data.bin"
    if b length != 4:
        return 16
    calling spark.println with "OK_EMBED"
    return 0
"""
    cfg = _make_project(tmp_path, source, embed=True)
    builder = PenguBuilder(cfg)
    artifact, is_cached = builder.compile()
    assert os.path.isfile(artifact)
    assert not is_cached

    res = subprocess.run([artifact], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, f"Failed with {res.returncode}: {res.stderr}\n{res.stdout}"
    assert "OK_EMBED" in res.stdout

    # Test cache hit
    artifact2, is_cached2 = PenguBuilder(cfg).compile()
    assert is_cached2

    # Invalidate cache by modifying asset
    (assets_dir / "msg.txt").write_text("Modified asset content!", encoding="utf-8")
    artifact3, is_cached3 = PenguBuilder(cfg).compile()
    assert not is_cached3


@requires_cc
@requires_runtime
def test_end_to_end_disk(tmp_path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "disk.txt").write_text("Hello from disk!", encoding="utf-8")

    source = """import arca
import std.spark

weave main into int:
    if not calling arca.has with "disk.txt":
        return 20
    var s as string is calling arca.string with "disk.txt"
    if s != "Hello from disk!":
        return 21
    calling spark.println with "OK_DISK"
    return 0
"""
    cfg = _make_project(tmp_path, source, embed=False)
    builder = PenguBuilder(cfg)
    artifact, _ = builder.compile()
    assert os.path.isfile(artifact)

    res = subprocess.run([artifact], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, f"Failed with {res.returncode}: {res.stderr}\n{res.stdout}"
    assert "OK_DISK" in res.stdout

    # Test PENGU_ASSETS_DIR override
    alt_dir = tmp_path / "alt_assets"
    alt_dir.mkdir()
    (alt_dir / "disk.txt").write_text("Hello from alt disk!", encoding="utf-8")

    source_alt = """import arca
import std.spark

weave main into int:
    var s as string is calling arca.string with "disk.txt"
    if s == "Hello from alt disk!":
        calling spark.println with "OVERRIDE_OK"
        return 0
    return 22
"""
    cfg_alt = _make_project(tmp_path, source_alt, embed=False)
    artifact_alt, _ = PenguBuilder(cfg_alt).compile()
    env = dict(os.environ)
    env["PENGU_ASSETS_DIR"] = str(alt_dir)
    res_alt = subprocess.run([artifact_alt], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert res_alt.returncode == 0, f"Failed with {res_alt.returncode}: {res_alt.stderr}\n{res_alt.stdout}"
    assert "OVERRIDE_OK" in res_alt.stdout


def test_cli_assets_list_and_force(tmp_path):
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "sample.txt").write_text("sample content", encoding="utf-8")
    _make_project(tmp_path, "weave main into int:\n    return 0\n")

    cmd_list = [sys.executable, str(REPO / "pengu_project.py"), "assets", "--list"]
    res_list = subprocess.run(cmd_list, cwd=tmp_path, capture_output=True, text=True)
    assert res_list.returncode == 0
    assert "sample.txt" in res_list.stdout
    assert "14 bytes" in res_list.stdout

    cmd_force = [sys.executable, str(REPO / "pengu_project.py"), "assets", "--force"]
    res_force = subprocess.run(cmd_force, cwd=tmp_path, capture_output=True, text=True)
    assert res_force.returncode == 0
    assert (tmp_path / "src" / "arca.pengu").is_file()
    assert (tmp_path / "build" / "arca_assets.c").is_file()


def test_fmt_skips_generated_arca(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    arca_path = src_dir / "arca.pengu"
    ugly_content = "## @generated\nweave   foo   into   void:\n    return\n"
    arca_path.write_text(ugly_content, encoding="utf-8")

    fmt_files([str(src_dir)], write=True)
    assert arca_path.read_text(encoding="utf-8") == ugly_content


def test_ident_collision_avoidance():
    # Paths that would collide with naive regex cleaning
    c1 = _c_ident("shaders/main.vs")
    c2 = _c_ident("shaders_main.vs")
    assert c1 != c2

    k1 = _asset_const_name("my-file.txt")
    k2 = _asset_const_name("my_file.txt")
    assert k1 != k2

    # Leading digits must produce valid identifiers (prefixed with _)
    num_const = _asset_const_name("123.txt")
    assert num_const.isidentifier()
    assert not num_const.startswith("ASSET_123")  # should have leading underscore after ASSET_


def test_module_sanitization(tmp_path):
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="my-custom-module.v1",
        embed=True,
    )
    assert cfg.module == "my_custom_module_v1"
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "test.txt").write_bytes(b"hello")
    res = generate(cfg)
    assert res is not None
    assert Path(res["interface"]).name == "my_custom_module_v1.pengu"
    header_text = Path(res["header"]).read_text(encoding="utf-8")
    assert "MY_CUSTOM_MODULE_V1_ASSETS_H" in header_text
    assert "int _my_custom_module_v1_count(void);" in header_text


def test_disk_mode_caches_missing_files(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "file.txt").write_bytes(b"data")
    cfg = AssetConfig(
        project_root=tmp_path,
        src_dir=tmp_path / "src",
        build_dir=tmp_path / "build",
        assets_dir=tmp_path / "assets",
        module="arca",
        embed=False,
    )
    res = generate(cfg)
    c_text = Path(res["impl"]).read_text(encoding="utf-8")
    assert "int attempted;" in c_text
    assert "e->attempted = 1;" in c_text


def test_empty_assets_dir_does_not_walk_project_root(tmp_path):
    # Simulate a project or script run with assets_dir=""
    src = tmp_path / "main.pengu"
    src.write_text("weave main into int:\n    return 0\n", encoding="utf-8")
    dummy = tmp_path / "large_dummy.dat"
    dummy.write_bytes(b"x" * 1024)

    cfg = ProjectConfig(
        entry="main.pengu",
        base_dir=str(tmp_path),
        output=OutputType.EXE,
        output_name="main",
        name="main",
        assets_dir="",
    )
    builder = PenguBuilder(cfg)
    fp1 = builder.compute_sources_fingerprint([str(src)])

    # Modifying dummy file in root must NOT change fingerprint when assets_dir is ""
    dummy.write_bytes(b"y" * 1024)
    fp2 = builder.compute_sources_fingerprint([str(src)])
    assert fp1 == fp2





# ---------------------------------------------------------------------------
# Phase 3 / 3.4 — large assets (.incbin), NUL-safe arca.string(), long paths
# ---------------------------------------------------------------------------

from pengu_assets import _emit_embedded_c, _emit_disk_c, _incbin_threshold


def test_incbin_threshold_used_for_large_assets(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    blob = assets / "big.bin"
    blob.write_bytes(b"\x00" * 2048)

    c_large = _emit_embedded_c(
        "arca", [("big.bin", blob)], project_root=tmp_path, incbin_threshold=1024
    )
    assert ".incbin" in c_large
    assert "big.bin" in c_large
    assert "(size_t)2048" in c_large

    c_small = _emit_embedded_c(
        "arca", [("big.bin", blob)], project_root=tmp_path, incbin_threshold=0
    )
    assert ".incbin" not in c_small
    assert "static const unsigned char" in c_small
    assert "(size_t)2048" in c_small

    # Below the threshold keeps the portable byte array.
    c_below = _emit_embedded_c(
        "arca", [("big.bin", blob)], project_root=tmp_path, incbin_threshold=4096
    )
    assert ".incbin" not in c_below


def test_incbin_disabled_by_env(monkeypatch):
    monkeypatch.setenv("PENGU_ASSETS_INCBIN_THRESHOLD", "0")
    assert _incbin_threshold() == 0
    monkeypatch.setenv("PENGU_ASSETS_INCBIN_THRESHOLD", "2048")
    assert _incbin_threshold() == 2048
    monkeypatch.delenv("PENGU_ASSETS_INCBIN_THRESHOLD", raising=False)


def test_generated_string_helper_is_length_exact(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "b.bin").write_bytes(b"\x01\x02")
    for c_text in (
        _emit_embedded_c("arca", [("b.bin", assets / "b.bin")]),
        _emit_disk_c("arca", [("b.bin", assets / "b.bin")]),
    ):
        assert "PenguString _arca_string(const char* name)" in c_text
        assert "pengu_sigil_alloc" in c_text
        assert "s.len = (int)n;" in c_text


def test_disk_reader_has_no_fixed_path_buffer(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "d.bin").write_bytes(b"x")
    c_text = _emit_disk_c("arca", [("d.bin", assets / "d.bin")])
    assert "char path[1024]" not in c_text
    assert "malloc(need)" in c_text


@requires_cc
@requires_runtime
def test_end_to_end_embedded_nul_bytes_preserved(tmp_path):
    """`arca.string()` must not truncate at embedded NUL bytes."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    payload = bytes([0x41, 0x00, 0x42, 0x00, 0x01, 0x02, 0xFF])  # 7 bytes, two NULs
    (assets_dir / "bin.dat").write_bytes(payload)

    source = """import arca

weave main into int:
    var s as string is calling arca.string with "bin.dat"
    if s length != 7:
        return 30
    var b as slice of byte is calling arca.bytes with "bin.dat"
    if b length != 7:
        return 31
    if (b at 0) != 65:
        return 32
    if (b at 1) != 0:
        return 33
    if (b at 2) != 66:
        return 34
    if (b at 3) != 0:
        return 35
    if (b at 6) != 255:
        return 36
    return 0
"""
    cfg = _make_project(tmp_path, source, embed=True)
    artifact, _ = PenguBuilder(cfg).compile()
    res = subprocess.run([artifact], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, f"rc={res.returncode}: {res.stderr}\n{res.stdout}"


@requires_cc
@requires_runtime
def test_end_to_end_large_asset_incbin(tmp_path, monkeypatch):
    """>threshold asset is embedded via .incbin and round-trips exactly."""
    monkeypatch.setenv("PENGU_ASSETS_INCBIN_THRESHOLD", "4096")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    import hashlib
    payload = (bytes(range(256)) * 8192)  # 2 MB with every byte value incl. NUL
    assert len(payload) == 2 * 1024 * 1024
    (assets_dir / "big.bin").write_bytes(payload)

    source = """import arca

weave main into int:
    var b as slice of byte is calling arca.bytes with "big.bin"
    if b length != 2097152:
        return 40
    if (b at 0) != 0:
        return 41
    if (b at 1) != 1:
        return 42
    if (b at 255) != 255:
        return 43
    if (b at 256) != 0:
        return 44
    var s as string is calling arca.string with "big.bin"
    if s length != 2097152:
        return 45
    return 0
"""
    cfg = _make_project(tmp_path, source, embed=True)
    asset_c = Path(PenguBuilder(cfg).get_build_directory()) / "arca_assets.c"
    builder = PenguBuilder(cfg)
    builder.generate_assets(force=True)
    assert ".incbin" in asset_c.read_text(encoding="utf-8")
    artifact, _ = builder.compile()
    res = subprocess.run([artifact], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, f"rc={res.returncode}: {res.stderr}\n{res.stdout}"
