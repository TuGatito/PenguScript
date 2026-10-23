"""Smart linking of the vendored ``std_c/`` libraries.

The contract (LANGUAGE.md §19.1, docs/BINDINGS.md) is that importing a binding
is what pulls its C dependencies into *this* executable:

* no import -> no ``#include``, no ``-l``, no C symbols;
* ``std.lingua`` -> ``utf8.h`` only (header-only, no archive);
* ``std.regulus`` -> ``re.h`` + ``-lre`` + ``re_*`` symbols;
* ``std.petitio`` -> ``petitio.h`` + ``-lpetitio`` + ``-lcurl`` + ``petitio_*``;
* ``std.compressus`` -> ``miniz_bind.h`` + ``-lminiz`` + ``mz_*`` symbols;
* several -> the union, and nothing else.

The test builds six throwaway projects and inspects three independent pieces
of evidence: the generated ``bundle.c``, the compiler/linker command line
(``--verbose``) and the final binary (``nm``). Checking only one of them can
pass for the wrong reason: an ``#include`` can be dead code, a ``-l`` can be
dropped by a cache hit, and ``nm`` sees code that was linked but never run.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _have_cc() -> bool:
    return bool(shutil.which("gcc") or shutil.which("clang") or shutil.which("cc"))


def _have_runtime() -> bool:
    return (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file()


def _have_regex_archive() -> bool:
    return (ROOT / "build" / "lib" / "libre.a").is_file()


def _have_petitio_archive() -> bool:
    return (ROOT / "build" / "lib" / "libpetitio.a").is_file()


def _have_miniz_archive() -> bool:
    return (ROOT / "build" / "lib" / "libminiz.a").is_file()


pytestmark = pytest.mark.skipif(
    not (_have_cc() and _have_runtime() and _have_regex_archive()),
    reason="C compiler, libpengu_runtime.a or libre.a not available "
           "(run build_runtime.py)",
)


SOURCES = {
    "hello": """import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
""",
    "lingua": """import std.spark
import std.lingua

weave main into int:
    calling spark.println_int with (calling lingua.codepoint_count with "ñ😀")
    return 0
""",
    "regulus": """import std.spark
import std.regulus

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if cr.is_ok:
        var rx as Regex is cr.value
        defer banish rx
        calling spark.println_bool with (calling rx.is_match with "abc123")
    return 0
""",
    "both": """import std.spark
import std.lingua
import std.regulus

weave main into int:
    calling spark.println_int with (calling lingua.codepoint_count with "ñ")
    var cr as result of Regex to RegexError is calling Regex.compile with "a+"
    if cr.is_ok:
        var rx as Regex is cr.value
        defer banish rx
        calling spark.println_bool with (calling rx.is_match with "baa")
    return 0
""",
    # `url_encode` is offline: the program builds and links, it never opens a
    # socket. That is all this test needs (it inspects the bundle and the link
    # line, then `nm`).
    "petitio": """import std.spark
import std.petitio

weave main into int:
    var encoded as string is calling petitio.url_encode with "a b"
    calling spark.println with encoded
    banish encoded
    var version as string is calling petitio.libcurl_version
    calling spark.println with version
    banish version
    return 0
""",
    # Offline round-trip: the only thing this program needs from the operating
    # system is memory. It proves the miniz archive is enough on its own, and
    # the assertions below prove it is the *only* archive added.
    "compressus": """import std.spark
import std.compressus

weave main into int:
    var r as result of string to CompressError is calling compressus.gzip_compress with "hello hello hello", CompressionLevel.Best
    if not r.is_ok:
        banish r
        return 1
    var back as result of string to CompressError is calling compressus.gzip_decompress with r.value
    banish r
    if not back.is_ok:
        banish back
        return 1
    calling spark.println with back.value
    banish back
    var crc as u32 is calling compressus.crc32 with "hello"
    if crc == 0:
        return 1
    return 0
""",
    # The union case: several bindings at once must not pull an archive twice
    # and must not lose one either. `std.regulus` and `std.petitio` used to be
    # impossible to import together (their omen variants shared simple names);
    # Track B4 renamed the variants, so this covers the archive-heavy union and
    # the former collision in one build.
    "all_std_c": """import std.spark
import std.lingua
import std.regulus
import std.petitio
import std.compressus

weave main into int:
    calling spark.println_int with (calling lingua.codepoint_count with "ñ")
    var cr as result of Regex to RegexError is calling Regex.compile with "a+"
    if cr.is_ok:
        var rx as Regex is cr.value
        defer banish rx
        calling spark.println_bool with (calling rx.is_match with "baa")
    var encoded as string is calling petitio.url_encode with "a b"
    banish encoded
    var version as string is calling petitio.libcurl_version
    banish version
    var z as result of string to CompressError is calling compressus.zlib_compress with "hello", CompressionLevel.Fastest
    banish z
    var crc as u32 is calling compressus.crc32 with "hello"
    if crc == 0:
        return 1
    return 0
""",
}


def _build(tmp_path: Path, name: str) -> tuple[str, str, Path]:
    """Builds one project; returns (bundle text, verbose output, executable)."""
    project = tmp_path / name
    project.mkdir()
    (project / "main.pengu").write_text(SOURCES[name], encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "build", "--verbose"],
        capture_output=True, text=True, timeout=300, cwd=str(project), env=env,
    )
    assert res.returncode == 0, (
        f"build failed for {name}:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    bundle = (project / "build" / "bundle.c").read_text(encoding="utf-8")
    exe = project / "build" / ("app.exe" if os.name == "nt" else "app")
    assert exe.is_file(), f"no executable for {name}: {list((project / 'build').iterdir())}"
    return bundle, res.stdout + res.stderr, exe


def _symbols(exe: Path) -> str:
    tool = shutil.which("nm")
    if not tool:
        return ""
    res = subprocess.run([tool, str(exe)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return res.stdout


@pytest.mark.parametrize(
    "name, lingua, regulus, petitio, compressus",
    [
        ("hello", False, False, False, False),
        ("lingua", True, False, False, False),
        ("regulus", False, True, False, False),
        ("both", True, True, False, False),
        ("petitio", False, False, True, False),
        ("compressus", False, False, False, True),
        ("all_std_c", True, True, True, True),
    ],
)
def test_smart_linking_matrix(tmp_path, name, lingua, regulus, petitio, compressus):
    if petitio and not _have_petitio_archive():
        pytest.skip("libpetitio.a not built (install libcurl headers and run build_runtime.py)")
    if compressus and not _have_miniz_archive():
        pytest.skip("libminiz.a not built (run build_runtime.py)")
    bundle, log, exe = _build(tmp_path, name)

    # 1. Headers are emitted exactly for the imported binding.
    assert ('#include "utf8.h"' in bundle) is lingua, (
        f"{name}: utf8.h include mismatch\n{bundle[:2000]}"
    )
    assert ('#include "re.h"' in bundle) is regulus, (
        f"{name}: re.h include mismatch\n{bundle[:2000]}"
    )
    assert ('#include "petitio.h"' in bundle) is petitio, (
        f"{name}: petitio.h include mismatch\n{bundle[:2000]}"
    )
    assert ('#include "miniz_bind.h"' in bundle) is compressus, (
        f"{name}: miniz_bind.h include mismatch\n{bundle[:2000]}"
    )

    # 2. The archive reaches the link line exactly for the modules that own one.
    link_lines = [line for line in log.splitlines() if "running C compiler" in line]
    assert link_lines, f"{name}: no compiler command in verbose output"
    link_line = link_lines[-1]
    assert ("-lre" in link_line) is regulus, (
        f"{name}: -lre mismatch\n{link_line}"
    )
    assert ("-lpetitio" in link_line) is petitio, (
        f"{name}: -lpetitio mismatch\n{link_line}"
    )
    assert ("-lcurl" in link_line) is petitio, (
        f"{name}: -lcurl mismatch (std.petitio must pull libcurl)\n{link_line}"
    )
    assert ("-lminiz" in link_line) is compressus, (
        f"{name}: -lminiz mismatch\n{link_line}"
    )

    # 3. The symbols really are (or are not) in the produced executable.
    symbols = _symbols(exe)
    if symbols:
        assert ("re_compile_dynamic_ex" in symbols) is regulus, (
            f"{name}: re_* symbols mismatch"
        )
        assert ("lingua_codepoint_count" in symbols) is lingua, (
            f"{name}: lingua_* symbols mismatch"
        )
        # The program calls `libcurl_version`, so that bridge function (and
        # the libcurl symbol it uses) must be present.  `-ffunction-sections`
        # plus `--gc-sections` then drops every other petitio entry point,
        # which is the second half of the smart-linking contract.
        assert ("petitio_version" in symbols) is petitio, (
            f"{name}: petitio_* symbols mismatch"
        )
        assert ("curl_version_info" in symbols) is petitio, (
            f"{name}: libcurl symbols must follow std.petitio"
        )
        if petitio:
            assert "petitio_request_new" not in symbols, (
                "unreferenced petitio entry points must be garbage-collected"
            )
        # `std.compressus` is the only module that pulls miniz.  Both the
        # archive symbol (`mz_crc32`, used by every gzip member and by the
        # public hash) and the generated wrapper (`compressus_crc32`, called by
        # both matrix programs) follow the import.  `--gc-sections` then drops
        # the wrapper entry points the program does not call, which is the
        # second half of the contract.
        assert ("mz_crc32" in symbols) is compressus, (
            f"{name}: miniz symbols must follow std.compressus"
        )
        assert ("compressus_crc32" in symbols) is compressus, (
            f"{name}: compressus_* symbols mismatch"
        )
        if compressus:
            assert "compressus_gzip_compress_file" not in symbols, (
                "unreferenced compressus entry points must be garbage-collected"
            )
        if not compressus:
            # The ZIP API is compiled out by `miniz_bind.h`; a program that
            # does not import the module must not see even that symbol.
            assert "mz_zip_reader_init" not in symbols


def test_the_raw_archives_are_small_and_separate():
    """The whole point: the vendored archives are satellites, not the runtime."""
    runtime = (ROOT / "build" / "lib" / "libpengu_runtime.a").stat().st_size
    regex = (ROOT / "build" / "lib" / "libre.a").stat().st_size
    assert regex < runtime, "libre.a should be a small satellite archive"
    assert regex > 0
    if _have_petitio_archive():
        petitio = (ROOT / "build" / "lib" / "libpetitio.a").stat().st_size
        assert 0 < petitio < runtime, "libpetitio.a should be a small satellite archive"
    if _have_miniz_archive():
        miniz = (ROOT / "build" / "lib" / "libminiz.a").stat().st_size
        # miniz is a real deflate engine, so it is not required to be smaller
        # than the core runtime archive (which is split into per-subsystem
        # objects). What matters is that it stays a *separate* satellite with
        # only the configured subset: the ZIP/stdio/PNG half is compiled out,
        # so the archive is a fraction of the 350 KB upstream translation unit.
        assert 0 < miniz < 150_000, "libminiz.a should not contain the ZIP/stdio APIs"
        assert "miniz.o" not in subprocess.run(
            [shutil.which("ar") or "ar", "t", str(ROOT / "build" / "lib" / "libpengu_runtime.a")],
            capture_output=True, text=True, timeout=60,
        ).stdout, "miniz must not be folded into the core runtime archive"
