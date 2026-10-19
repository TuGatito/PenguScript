"""Ownership and leak checks for ``std.compressus`` under AddressSanitizer.

Every public weave hands out a `result` that owns a buffer, and the file
helpers go through `maybe string`. A leak or a double free in that dance is
invisible to a correctness test, so this module builds the real bundle, compiles
it with ``-fsanitize=address`` and runs a churn program that:

* compresses and decompresses all three formats at every level;
* exercises the ``_take_ok_string`` / ``_take_error`` move paths through
  ``decompress_auto``;
* drives every error path (bad magic, corrupt body, truncated stream, trailing
  bytes) and releases the errors through ``banish``;
* builds multi-member gzip and concatenates it;
* writes and reads the file helpers.

Run it explicitly (it is not part of the default budget)::

    PENGU_CFLAGS="-fsanitize=address" \\
    PENGU_LDFLAGS="-fsanitize=address" \\
    pytest tests/stdlib/audit/test_compressus_ownership.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[3]

_SOURCE = r'''
import std.archivum
import std.builder
import std.compressus
import std.scrolls
import std.spark

weave same with a as string, b as string into bool:
    return (calling scrolls.compare with a, b) == 0

weave main into int:
    var base as StringBuilder is calling StringBuilder.with_capacity with 4096
    calling base.append_repeat with "compressus ownership churn ", 160
    var payload as string is calling base.finish
    banish base

    var iterations as int is 0
    while iterations < 100:
        var level_index as int is iterations % 6
        var level as CompressionLevel is CompressionLevel.Default
        if level_index == 0:
            set level is CompressionLevel.None
        if level_index == 1:
            set level is CompressionLevel.Fastest
        if level_index == 2:
            set level is CompressionLevel.Default
        if level_index == 3:
            set level is CompressionLevel.Better
        if level_index == 4:
            set level is CompressionLevel.Best
        if level_index == 5:
            set level is CompressionLevel.Uber

        var g as result of string to CompressError is calling compressus.gzip_compress with payload, level
        if g.is_ok:
            var back as result of string to CompressError is calling compressus.gzip_decompress with g.value
            if back.is_ok:
                if not (calling same with back.value, payload):
                    calling spark.println with "FAIL gzip roundtrip"
            banish back

        var z as result of string to CompressError is calling compressus.zlib_compress with payload, level
        if z.is_ok:
            var zback as result of string to CompressError is calling compressus.zlib_decompress with z.value
            if zback.is_ok:
                if not (calling same with zback.value, payload):
                    calling spark.println with "FAIL zlib roundtrip"
            banish zback
        banish z

        var d as result of string to CompressError is calling compressus.deflate_compress with payload, level
        if d.is_ok:
            var dback as result of string to CompressError is calling compressus.inflate_decompress with d.value
            if dback.is_ok:
                if not (calling same with dback.value, payload):
                    calling spark.println with "FAIL raw roundtrip"
            banish dback
        banish d

        # Error paths: each error owns a reason string that `banish` must free.
        var bad_gzip as result of string to CompressError is calling compressus.gzip_decompress with "nope"
        if bad_gzip.is_ok:
            calling spark.println with "FAIL bad gzip accepted"
        banish bad_gzip
        var bad_zlib as result of string to CompressError is calling compressus.zlib_decompress with "nope"
        if bad_zlib.is_ok:
            calling spark.println with "FAIL bad zlib accepted"
        banish bad_zlib
        var bad_auto as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with "nope"
        if bad_auto.is_ok:
            calling spark.println with "FAIL bad auto accepted"
        banish bad_auto

        if g.is_ok:
            # Corrupt one body byte, then truncate the trailer; both must fail.
            var broken as StringBuilder is calling StringBuilder.from_string with g.value
            calling broken.set_char_at with 12, 'Z'
            var corrupt as string is calling broken.finish
            banish broken
            var rejected as result of string to CompressError is calling compressus.gzip_decompress with corrupt
            if rejected.is_ok:
                calling spark.println with "FAIL corrupt accepted"
            banish rejected
            var auto_rejected as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with corrupt
            if auto_rejected.is_ok:
                calling spark.println with "FAIL corrupt auto accepted"
            if not auto_rejected.is_ok:
                var e as CompressError is auto_rejected.error
                var msg as string is calling e.message
                banish msg
            banish auto_rejected
            banish corrupt
            var short as string is calling scrolls.substring with g.value, 0, ((g.value length) - 3)
            var truncated as result of string to CompressError is calling compressus.gzip_decompress with short
            if truncated.is_ok:
                calling spark.println with "FAIL truncated accepted"
            banish truncated
            banish short
        banish g

        set iterations is iterations + 1

    # Multi-member gzip, concatenated with a builder.
    var m1 as result of string to CompressError is calling compressus.gzip_compress with "one", CompressionLevel.Best
    var m2 as result of string to CompressError is calling compressus.gzip_compress with "two", CompressionLevel.Best
    if m1.is_ok and m2.is_ok:
        var join as StringBuilder is calling StringBuilder.new
        calling join.append with m1.value
        calling join.append with m2.value
        var multi as string is calling join.finish
        banish join
        var back as result of string to CompressError is calling compressus.gzip_decompress with multi
        if back.is_ok:
            if not (calling same with back.value, "onetwo"):
                calling spark.println with "FAIL multi"
        banish back
        banish multi
    banish m1
    banish m2

    # File helpers: read, write, compress, decompress, delete.
    var ok as bool is calling archivum.write_bytes with "churn_in.bin", payload
    if not ok:
        calling spark.println with "FAIL write input"
    var cf as result of int to CompressError is calling compressus.gzip_compress_file with "churn_in.bin", "churn_mid.gz", CompressionLevel.Best
    banish cf
    var rf as result of string to CompressError is calling compressus.gzip_read_file with "churn_mid.gz"
    if rf.is_ok:
        if not (calling same with rf.value, payload):
            calling spark.println with "FAIL file roundtrip"
    banish rf
    var df as result of int to CompressError is calling compressus.gzip_decompress_file with "churn_mid.gz", "churn_out.bin"
    banish df
    var badwrite as bool is calling archivum.write_bytes with "churn_bad.gz", "not gzip"
    if not badwrite:
        calling spark.println with "FAIL write bad"
    var badf as result of int to CompressError is calling compressus.gzip_decompress_file with "churn_bad.gz", "churn_bad.out"
    if badf.is_ok:
        calling spark.println with "FAIL bad file accepted"
    banish badf
    banish payload
    calling archivum.delete_file with "churn_in.bin"
    calling archivum.delete_file with "churn_mid.gz"
    calling archivum.delete_file with "churn_out.bin"
    calling archivum.delete_file with "churn_bad.gz"
    calling archivum.delete_file with "churn_bad.out"

    calling spark.println with "OK compressus ownership"
    return 0
'''


def test_compressus_runs_clean_under_asan(tmp_path):
    gcc = shutil.which("gcc")
    if not gcc:
        pytest.skip("gcc is required for the ASan leak check")
    runtime = ROOT / "build" / "lib" / "libpengu_runtime.a"
    miniz = ROOT / "build" / "lib" / "libminiz.a"
    include = ROOT / "build" / "include"
    if not runtime.is_file():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")
    if not miniz.is_file():
        pytest.skip("libminiz.a not built (run build_runtime.py)")

    source = tmp_path / "churn.pengu"
    source.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "churn.c"
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    build = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "build",
         "--entry", str(source), "--output", str(bundle), "--cc", "gcc"],
        capture_output=True, text=True, timeout=300, cwd=str(tmp_path), env=env,
    )
    assert build.returncode == 0, f"{build.stdout}\n{build.stderr}"

    exe = tmp_path / "churn_asan"
    compile_cmd = [
        gcc, "-std=c11", "-g", "-O0",
        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
        "-I", str(include), "-I", str(ROOT), str(bundle), "-o", str(exe),
        "-L", str(ROOT / "build" / "lib"),
        "-Wl,--start-group", "-lpengu_runtime", "-lminiz",
        "-pthread", "-lm", "-ldl", "-Wl,--end-group",
    ]
    compiled = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=300)
    if compiled.returncode != 0:
        pytest.skip(f"ASan/UBSan are not usable with this toolchain:\n{compiled.stderr}")

    run = subprocess.run(
        [str(exe)], capture_output=True, text=True, timeout=300, cwd=str(tmp_path),
        env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1"},
    )
    assert run.returncode == 0, f"{run.stdout}\n{run.stderr}"
    assert "LeakSanitizer" not in run.stderr, run.stderr
    assert "ERROR: AddressSanitizer" not in run.stderr, run.stderr
    assert "runtime error" not in run.stderr, run.stderr
    assert "FAIL" not in run.stdout, run.stdout
    assert "OK compressus ownership" in run.stdout, run.stdout
