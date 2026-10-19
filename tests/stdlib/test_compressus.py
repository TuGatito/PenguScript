"""End-to-end tests for ``std.compressus``.

The Python-format oracle lives in ``tests/compat/test_compressus_vs_python.py``.
This file covers the PenguScript-facing contract: every level round-trips, the
error taxonomy is honoured, the file helpers touch real files, multi-member
gzip concatenates, the checksums match their published values and the output is
deterministic.

Two compiles are enough for ~60 assertions (see ``tests/stdlib/conftest.py``
for why the standard-library suite batches).
"""
from __future__ import annotations

import pytest

_CHECKSUM_PROGRAM = r'''
import std.builder
import std.compressus
import std.spark
import std.ward

weave main into int:
    # Published values, verified against zlib.crc32 / zlib.adler32.
    calling ward.assert_eq_int with (calling compressus.crc32 with ""), 0
    calling ward.assert_eq_int with (calling compressus.crc32 with "hello"), 907060870
    calling ward.assert_eq_int with (calling compressus.adler32 with ""), 1
    calling ward.assert_eq_int with (calling compressus.adler32 with "hello"), 103547413

    # Continuing a checksum equals checksumming the concatenation.
    var first as u32 is calling compressus.crc32 with "hel"
    var both as u32 is calling compressus.crc32_continue with first, "lo"
    calling ward.assert_eq_int with both, 907060870
    var a1 as u32 is calling compressus.adler32 with "hel"
    var a2 as u32 is calling compressus.adler32_continue with a1, "lo"
    calling ward.assert_eq_int with a2, 103547413
    # A continuing checksum of no bytes returns the seed unchanged.
    calling ward.assert_eq_int with (calling compressus.crc32_continue with both, ""), 907060870

    # Binary data with embedded NULs is checksummed byte-exactly. A string
    # literal stops at a NUL, so the buffer is built one byte at a time; the
    # expected values are Python's zlib.adler32(b"\x00A\x00") and
    # zlib.crc32(b"\x00A\x00").
    var sb as StringBuilder is calling StringBuilder.new
    calling sb.append_char with '\x00'
    calling sb.append_char with 'A'
    calling sb.append_char with '\x00'
    var bin as string is calling sb.finish
    banish sb
    calling ward.assert_eq_int with (bin length), 3
    calling ward.assert_eq_int with ((calling compressus.adler32 with bin) to int), 8716354
    calling ward.assert_eq_int with ((calling compressus.crc32 with bin) to int), 371435350
    banish bin

    calling spark.println with "DONE"
    return 0
'''

_PROGRAM = r'''
import std.archivum
import std.builder
import std.compressus
import std.scrolls
import std.spark
import std.ward

weave same with a as string, b as string into bool:
    return (calling scrolls.compare with a, b) == 0

weave check_as with data as string, format as CompressionFormat, expected as string into void:
    var r as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_as with data, format
    calling ward.assert_true with r.is_ok
    if r.is_ok:
        let (plain, fmt) is r.value
        calling ward.assert_true with (calling same with plain, expected)
    banish r

weave main into int:
    var text as string is "the quick brown fox jumps over the lazy dog\n"

    # --- every level round-trips in every format -------------------------
    var levels as list of CompressionLevel is list of CompressionLevel
    calling levels.push with CompressionLevel.None
    calling levels.push with CompressionLevel.Fastest
    calling levels.push with CompressionLevel.Default
    calling levels.push with CompressionLevel.Better
    calling levels.push with CompressionLevel.Best
    calling levels.push with CompressionLevel.Uber
    var li as int is 0
    while li < levels.len:
        var level as CompressionLevel is levels at li
        var g as result of string to CompressError is calling compressus.gzip_compress with text, level
        calling ward.assert_true with g.is_ok
        if g.is_ok:
            var back as result of string to CompressError is calling compressus.gzip_decompress with g.value
            calling ward.assert_true with back.is_ok
            if back.is_ok:
                calling ward.assert_true with (calling same with back.value, text)
            banish back
        banish g
        var z as result of string to CompressError is calling compressus.zlib_compress with text, level
        calling ward.assert_true with z.is_ok
        if z.is_ok:
            var backz as result of string to CompressError is calling compressus.zlib_decompress with z.value
            calling ward.assert_true with backz.is_ok
            if backz.is_ok:
                calling ward.assert_true with (calling same with backz.value, text)
            banish backz
        banish z
        var d as result of string to CompressError is calling compressus.deflate_compress with text, level
        calling ward.assert_true with d.is_ok
        if d.is_ok:
            var backd as result of string to CompressError is calling compressus.inflate_decompress with d.value
            calling ward.assert_true with backd.is_ok
            if backd.is_ok:
                calling ward.assert_true with (calling same with backd.value, text)
            banish backd
        banish d
        set li is li + 1
    banish levels

    # --- sizes: empty, one byte, ten bytes, 1 KiB, 1 MiB ----------------
    var sizes as list of int is list of int
    calling sizes.push with 0
    calling sizes.push with 1
    calling sizes.push with 10
    calling sizes.push with 1024
    calling sizes.push with 1048576
    var si as int is 0
    while si < sizes.len:
        var n as int is sizes at si
        var sb as StringBuilder is calling StringBuilder.with_capacity with n
        if n > 0:
            calling sb.append_repeat with "abcdefghij", (n / 10) + 1
        var payload as string is calling sb.substring with 0, n
        banish sb
        var g as result of string to CompressError is calling compressus.gzip_compress with payload, CompressionLevel.Best
        calling ward.assert_true with g.is_ok
        if g.is_ok:
            var back as result of string to CompressError is calling compressus.gzip_decompress with g.value
            calling ward.assert_true with back.is_ok
            if back.is_ok:
                calling ward.assert_eq_int with (back.value length), n
                calling ward.assert_true with (calling same with back.value, payload)
            banish back
        banish g
        banish payload
        set si is si + 1
    banish sizes

    # --- empty input is a valid 20-byte gzip ----------------------------
    var eg as result of string to CompressError is calling compressus.gzip_compress with "", CompressionLevel.Default
    calling ward.assert_true with eg.is_ok
    if eg.is_ok:
        calling ward.assert_eq_int with (eg.value length), 20
        var magic as string is calling scrolls.substring with eg.value, 0, 2
        calling ward.assert_true with (calling same with magic, "\x1f\x8b")
        banish magic
    banish eg

    # --- determinism ----------------------------------------------------
    var one as result of string to CompressError is calling compressus.gzip_compress with text, CompressionLevel.Best
    var two as result of string to CompressError is calling compressus.gzip_compress with text, CompressionLevel.Best
    calling ward.assert_true with one.is_ok
    calling ward.assert_true with two.is_ok
    if one.is_ok and two.is_ok:
        calling ward.assert_true with (calling same with one.value, two.value)
    banish one
    banish two

    # --- named gzip keeps the FNAME flag and round-trips -----------------
    var named as result of string to CompressError is calling compressus.gzip_compress_named with text, "notes.txt", CompressionLevel.Best
    calling ward.assert_true with named.is_ok
    if named.is_ok:
        var flags as string is calling scrolls.substring with named.value, 3, 4
        calling ward.assert_eq_int with (calling scrolls.compare with flags, "\x08"), 0
        banish flags
        var nback as result of string to CompressError is calling compressus.gzip_decompress with named.value
        calling ward.assert_true with nback.is_ok
        if nback.is_ok:
            calling ward.assert_true with (calling same with nback.value, text)
        banish nback
    banish named
    var nb as StringBuilder is calling StringBuilder.new
    calling nb.append with "a"
    calling nb.append_char with '\x00'
    calling nb.append with "b"
    var nul_name as string is calling nb.finish
    banish nb
    var nulname as result of string to CompressError is calling compressus.gzip_compress_named with text, nul_name, CompressionLevel.Best
    calling ward.assert_false with nulname.is_ok
    banish nulname
    banish nul_name

    # --- multi-member gzip ----------------------------------------------
    var ma as result of string to CompressError is calling compressus.gzip_compress with "first|", CompressionLevel.Best
    var mb as result of string to CompressError is calling compressus.gzip_compress with "second", CompressionLevel.Best
    calling ward.assert_true with ma.is_ok
    calling ward.assert_true with mb.is_ok
    if ma.is_ok and mb.is_ok:
        var joined as StringBuilder is calling StringBuilder.new
        calling joined.append with ma.value
        calling joined.append with mb.value
        var both as string is calling joined.finish
        banish joined
        var back as result of string to CompressError is calling compressus.gzip_decompress with both
        calling ward.assert_true with back.is_ok
        if back.is_ok:
            calling ward.assert_true with (calling same with back.value, "first|second")
        banish back
        banish both
    banish ma
    banish mb

    # --- error taxonomy -------------------------------------------------
    var bad as result of string to CompressError is calling compressus.gzip_decompress with "this is definitely not gzip"
    calling ward.assert_false with bad.is_ok
    banish bad
    var badz as result of string to CompressError is calling compressus.zlib_decompress with ""
    calling ward.assert_false with badz.is_ok
    banish badz
    var emptyraw as result of string to CompressError is calling compressus.inflate_decompress with ""
    calling ward.assert_true with emptyraw.is_ok
    if emptyraw.is_ok:
        calling ward.assert_eq_int with (emptyraw.value length), 0
    banish emptyraw
    var badauto as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with "not compressed either"
    calling ward.assert_false with badauto.is_ok
    banish badauto

    # A valid gzip whose deflate body was corrupted must be rejected.
    var good as result of string to CompressError is calling compressus.gzip_compress with "some payload to corrupt", CompressionLevel.Best
    calling ward.assert_true with good.is_ok
    if good.is_ok:
        var broken as StringBuilder is calling StringBuilder.from_string with good.value
        calling broken.set_char_at with 12, 'Z'
        var corrupt_bytes as string is calling broken.finish
        banish broken
        var broken_back as result of string to CompressError is calling compressus.gzip_decompress with corrupt_bytes
        calling ward.assert_false with broken_back.is_ok
        banish broken_back
        # Truncating the trailer is Corrupt too, never a silent short read.
        var cut as string is calling scrolls.substring with good.value, 0, ((good.value length) - 4)
        var cut_back as result of string to CompressError is calling compressus.gzip_decompress with cut
        calling ward.assert_false with cut_back.is_ok
        banish cut_back
        banish cut
        # A valid member followed by junk is TrailingData.
        var junked as StringBuilder is calling StringBuilder.from_string with good.value
        calling junked.append with "JUNK"
        var with_junk as string is calling junked.finish
        banish junked
        var junk_back as result of string to CompressError is calling compressus.gzip_decompress with with_junk
        calling ward.assert_false with junk_back.is_ok
        if not junk_back.is_ok:
            var is_trailing as bool is false
            judge junk_back.error:
                when TrailingData ->
                    set is_trailing is true
                else ->
                    set is_trailing is false
            calling ward.assert_true with is_trailing
        banish junk_back
        banish with_junk
        # `decompress_auto` on a corrupted gzip goes through the error-move
        # path (`_take_error`); the returned CompressError must still own a
        # readable reason after the inner result has been released.
        var auto_bad as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with corrupt_bytes
        calling ward.assert_false with auto_bad.is_ok
        if not auto_bad.is_ok:
            var auto_err as CompressError is auto_bad.error
            var auto_msg as string is calling auto_err.message
            calling ward.assert_true with (auto_msg length) > 0
            banish auto_msg
        banish auto_bad
        banish corrupt_bytes
    banish good

    # A zlib stream followed by junk is TrailingData, not a silent success.
    var zj as result of string to CompressError is calling compressus.zlib_compress with "zlib trailing", CompressionLevel.Best
    calling ward.assert_true with zj.is_ok
    if zj.is_ok:
        var zj_sb as StringBuilder is calling StringBuilder.from_string with zj.value
        calling zj_sb.append with "x"
        var zj_bytes as string is calling zj_sb.finish
        banish zj_sb
        var zj_back as result of string to CompressError is calling compressus.zlib_decompress with zj_bytes
        calling ward.assert_false with zj_back.is_ok
        if not zj_back.is_ok:
            var zj_trailing as bool is false
            judge zj_back.error:
                when TrailingData ->
                    set zj_trailing is true
                else ->
                    set zj_trailing is false
            calling ward.assert_true with zj_trailing
        banish zj_back
        banish zj_bytes
    banish zj

    # --- decompress_as: explicit formats and Auto -----------------------
    var as_g as result of string to CompressError is calling compressus.gzip_compress with text, CompressionLevel.Best
    var as_z as result of string to CompressError is calling compressus.zlib_compress with text, CompressionLevel.Best
    var as_d as result of string to CompressError is calling compressus.deflate_compress with text, CompressionLevel.Best
    calling ward.assert_true with as_g.is_ok
    calling ward.assert_true with as_z.is_ok
    calling ward.assert_true with as_d.is_ok
    if as_g.is_ok:
        calling check_as with as_g.value, CompressionFormat.Gzip, text
        calling check_as with as_g.value, CompressionFormat.Auto, text
    if as_z.is_ok:
        calling check_as with as_z.value, CompressionFormat.Zlib, text
        calling check_as with as_z.value, CompressionFormat.Auto, text
    if as_d.is_ok:
        calling check_as with as_d.value, CompressionFormat.RawDeflate, text
        # Raw deflate has no magic: Auto must not pretend to know it.
        var auto_raw as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_as with as_d.value, CompressionFormat.Auto
        calling ward.assert_false with auto_raw.is_ok
        banish auto_raw
    banish as_g
    banish as_z
    banish as_d

    # --- detection ------------------------------------------------------
    var gd as result of string to CompressError is calling compressus.gzip_compress with "detect me", CompressionLevel.Fastest
    var zd as result of string to CompressError is calling compressus.zlib_compress with "detect me", CompressionLevel.Fastest
    calling ward.assert_true with gd.is_ok
    calling ward.assert_true with zd.is_ok
    if gd.is_ok:
        var d as maybe CompressionFormat is calling compressus.detect_format with gd.value
        calling ward.assert_true with (d is present)
        if d is present:
            var is_gzip as bool is false
            judge d.value:
                when Gzip ->
                    set is_gzip is true
                else ->
                    set is_gzip is false
            calling ward.assert_true with is_gzip
        banish d
    if zd.is_ok:
        var dz as maybe CompressionFormat is calling compressus.detect_format with zd.value
        calling ward.assert_true with (dz is present)
        if dz is present:
            var is_zlib as bool is false
            judge dz.value:
                when Zlib ->
                    set is_zlib is true
                else ->
                    set is_zlib is false
            calling ward.assert_true with is_zlib
        banish dz
    banish gd
    banish zd
    var none as maybe CompressionFormat is calling compressus.detect_format with "plain text"
    calling ward.assert_false with (none is present)
    banish none

    # --- file helpers ---------------------------------------------------
    var ok_w as bool is calling archivum.write_bytes with "unit_in.txt", text
    calling ward.assert_true with ok_w
    var cf as result of int to CompressError is calling compressus.gzip_compress_file with "unit_in.txt", "unit_mid.gz", CompressionLevel.Best
    calling ward.assert_true with cf.is_ok
    if cf.is_ok:
        calling ward.assert_true with cf.value > 0
    banish cf
    var df as result of int to CompressError is calling compressus.gzip_decompress_file with "unit_mid.gz", "unit_out.txt"
    calling ward.assert_true with df.is_ok
    if df.is_ok:
        calling ward.assert_eq_int with df.value, text length
    banish df
    var rd as result of string to CompressError is calling compressus.gzip_read_file with "unit_mid.gz"
    calling ward.assert_true with rd.is_ok
    if rd.is_ok:
        calling ward.assert_true with (calling same with rd.value, text)
    banish rd
    var wf as result of void to CompressError is calling compressus.gzip_write_file with "unit_w.gz", text, CompressionLevel.Fastest
    calling ward.assert_true with wf.is_ok
    banish wf
    var wr as result of string to CompressError is calling compressus.gzip_read_file with "unit_w.gz"
    calling ward.assert_true with wr.is_ok
    if wr.is_ok:
        calling ward.assert_true with (calling same with wr.value, text)
    banish wr
    var zcf as result of int to CompressError is calling compressus.zlib_compress_file with "unit_in.txt", "unit_mid.zlib", CompressionLevel.Best
    calling ward.assert_true with zcf.is_ok
    banish zcf
    var zdf as result of int to CompressError is calling compressus.zlib_decompress_file with "unit_mid.zlib", "unit_zout.txt"
    calling ward.assert_true with zdf.is_ok
    banish zdf
    var missing as result of string to CompressError is calling compressus.gzip_read_file with "definitely_missing.txt.gz"
    calling ward.assert_false with missing.is_ok
    banish missing
    var unwritable as result of int to CompressError is calling compressus.gzip_compress_file with "definitely_missing.txt", "x.gz", CompressionLevel.Best
    calling ward.assert_false with unwritable.is_ok
    banish unwritable
    # A corrupt input file exercises the error-move path of *_decompress_file.
    var bad_w as bool is calling archivum.write_bytes with "unit_bad.gz", "this is not a gzip member"
    calling ward.assert_true with bad_w
    var bad_file as result of int to CompressError is calling compressus.gzip_decompress_file with "unit_bad.gz", "unit_bad.out"
    calling ward.assert_false with bad_file.is_ok
    banish bad_file
    var bad_zfile as result of int to CompressError is calling compressus.zlib_decompress_file with "unit_bad.gz", "unit_bad.out"
    calling ward.assert_false with bad_zfile.is_ok
    banish bad_zfile

    # --- cleanup --------------------------------------------------------
    calling archivum.delete_file with "unit_in.txt"
    calling archivum.delete_file with "unit_mid.gz"
    calling archivum.delete_file with "unit_out.txt"
    calling archivum.delete_file with "unit_w.gz"
    calling archivum.delete_file with "unit_mid.zlib"
    calling archivum.delete_file with "unit_zout.txt"
    calling archivum.delete_file with "unit_bad.gz"
    calling archivum.delete_file with "unit_bad.out"

    calling spark.println with "DONE"
    return 0
'''


def test_checksums_match_published_values(compile_and_run):
    output = compile_and_run(_CHECKSUM_PROGRAM)
    assert "DONE" in output, output
    assert "FAIL" not in output, output


def test_formats_levels_errors_and_files(compile_and_run):
    output = compile_and_run(_PROGRAM, timeout=300)
    assert "DONE" in output, output
    assert "FAIL" not in output, output
