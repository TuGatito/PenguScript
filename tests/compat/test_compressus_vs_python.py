"""``std.compressus`` against CPython's ``gzip`` and ``zlib``.

The gzip (RFC 1952), zlib (RFC 1950) and raw deflate (RFC 1951) byte formats are
standards, so CPython is an oracle: there is no room for "close enough".

The suite generates 50 byte strings — empty, one byte, text, every byte value,
incompressible random data, highly repetitive data and a 64 KiB mixture — and
for each one checks **both directions** of all three formats:

* our compressor -> ``gzip.decompress`` / ``zlib.decompress``;
* ``gzip.compress`` / ``zlib.compress`` -> our decompressor;
* ``crc32`` and ``adler32`` against ``zlib``;
* format detection and ``decompress_auto`` on Python-made streams;
* multi-member gzip (three members concatenated) -> concatenated payload.

One PenguScript program handles all 50 cases: compiling is the expensive part,
and the Python side owns the oracle. ``tests/stdlib/test_compressus.py`` covers
the PenguScript-facing behaviour (levels, errors, file helpers, ownership).
"""
from __future__ import annotations

import gzip
import random
import zlib

import pytest

pytestmark = pytest.mark.slow

PROGRAM = r'''
import std.archivum
import std.compressus
import std.scrolls
import std.spark

weave read_all with path as string into string:
    var m as maybe string is calling archivum.read_bytes with path
    if not (m is present):
        banish m
        return ""
    var out as string is calling scrolls.substring with m.value, 0, (m.value length)
    banish m
    return out

weave write_all with path as string, data as string into void:
    var ok as bool is calling archivum.write_bytes with path, data
    if not ok:
        calling spark.println with "FAIL write {path}"

weave main into int:
    var i as int is 0
    while i < @@COUNT@@:
        var dir as string is "c{i}"
        var data as string is calling read_all with "{dir}/in.bin"

        var gc as result of string to CompressError is calling compressus.gzip_compress with data, CompressionLevel.Best
        if gc.is_ok:
            calling write_all with "{dir}/out_gzip.z", gc.value
        else:
            calling spark.println with "FAIL compress gzip {dir}"
        banish gc
        var zc as result of string to CompressError is calling compressus.zlib_compress with data, CompressionLevel.Best
        if zc.is_ok:
            calling write_all with "{dir}/out_zlib.z", zc.value
        else:
            calling spark.println with "FAIL compress zlib {dir}"
        banish zc
        var rc as result of string to CompressError is calling compressus.deflate_compress with data, CompressionLevel.Best
        if rc.is_ok:
            calling write_all with "{dir}/out_raw.z", rc.value
        else:
            calling spark.println with "FAIL compress raw {dir}"
        banish rc

        var py_gz as string is calling read_all with "{dir}/py_gzip.z"
        var gd as result of string to CompressError is calling compressus.gzip_decompress with py_gz
        if gd.is_ok:
            calling write_all with "{dir}/back_gzip.bin", gd.value
        else:
            calling spark.println with "FAIL decompress gzip {dir}"
        banish gd
        banish py_gz
        var py_zl as string is calling read_all with "{dir}/py_zlib.z"
        var zd as result of string to CompressError is calling compressus.zlib_decompress with py_zl
        if zd.is_ok:
            calling write_all with "{dir}/back_zlib.bin", zd.value
        else:
            calling spark.println with "FAIL decompress zlib {dir}"
        banish zd
        banish py_zl
        var py_raw as string is calling read_all with "{dir}/py_raw.z"
        var rd as result of string to CompressError is calling compressus.inflate_decompress with py_raw
        if rd.is_ok:
            calling write_all with "{dir}/back_raw.bin", rd.value
        else:
            calling spark.println with "FAIL decompress raw {dir}"
        banish rd
        banish py_raw
        var py_multi as string is calling read_all with "{dir}/py_multi.z"
        var md as result of string to CompressError is calling compressus.gzip_decompress with py_multi
        if md.is_ok:
            calling write_all with "{dir}/back_multi.bin", md.value
        else:
            calling spark.println with "FAIL multi {dir}"
        banish md
        banish py_multi

        var py_gz2 as string is calling read_all with "{dir}/py_gzip.z"
        var ad_gz as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with py_gz2
        if ad_gz.is_ok:
            let (plain, fmt) is ad_gz.value
            calling write_all with "{dir}/back_auto_gzip.bin", plain
        else:
            calling spark.println with "FAIL auto gzip {dir}"
        banish ad_gz
        banish py_gz2
        var py_zl2 as string is calling read_all with "{dir}/py_zlib.z"
        var ad_zl as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with py_zl2
        if ad_zl.is_ok:
            let (plain2, fmt2) is ad_zl.value
            calling write_all with "{dir}/back_auto_zlib.bin", plain2
        else:
            calling spark.println with "FAIL auto zlib {dir}"
        banish ad_zl
        banish py_zl2

        var py_gz3 as string is calling read_all with "{dir}/py_gzip.z"
        var gz_detect as maybe CompressionFormat is calling compressus.detect_format with py_gz3
        var gz_word as string is "none"
        if gz_detect is present:
            set gz_word is "known"
        banish gz_detect
        banish py_gz3
        var py_zl3 as string is calling read_all with "{dir}/py_zlib.z"
        var zl_detect as maybe CompressionFormat is calling compressus.detect_format with py_zl3
        var zl_word as string is "none"
        if zl_detect is present:
            set zl_word is "known"
        banish zl_detect
        banish py_zl3
        var nz_detect as maybe CompressionFormat is calling compressus.detect_format with data
        var nz_word as string is "none"
        if nz_detect is present:
            set nz_word is "known"
        banish nz_detect

        var c as u32 is calling compressus.crc32 with data
        var a as u32 is calling compressus.adler32 with data
        calling write_all with "{dir}/result.txt", "{gz_word} {zl_word} {nz_word} {c} {a}"
        banish data
        set i is i + 1
    calling spark.println with "OK"
    return 0
'''


def _write_case(base, index, payload, multi):
    import os

    case = os.path.join(base, f"c{index}")
    os.makedirs(case, exist_ok=True)
    with open(os.path.join(case, "in.bin"), "wb") as f:
        f.write(payload)
    with open(os.path.join(case, "py_gzip.z"), "wb") as f:
        f.write(gzip.compress(payload, mtime=0))
    with open(os.path.join(case, "py_zlib.z"), "wb") as f:
        f.write(zlib.compress(payload))
    with open(os.path.join(case, "py_raw.z"), "wb") as f:
        f.write(zlib.compress(payload)[2:-4])
    with open(os.path.join(case, "py_multi.z"), "wb") as f:
        f.write(multi)


def _looks_like_zlib(data: bytes) -> bool:
    """The same structural header test `std.compressus.detect_format` uses."""
    if len(data) < 2:
        return False
    cmf, flg = data[0], data[1]
    return (cmf & 0x0F) == 8 and (cmf >> 4) <= 7 and ((cmf << 8) | flg) % 31 == 0


def _looks_like_gzip(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B


def _samples():
    rng = random.Random(20241018)
    cases = [
        b"",
        b"\x00",
        b"a",
        b"hello, world",
        b"hello, world\n" * 400,
        bytes(range(256)),
        bytes(range(256)) * 40,
        b"\x00" * 5000,
        b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" * 500,
        b"the quick brown fox jumps over the lazy dog\n" * 700,
    ]
    for _ in range(40):
        size = rng.choice([1, 2, 3, 7, 31, 64, 255, 1024, 4096, 65536])
        mode = rng.randrange(4)
        if mode == 0:
            payload = bytes(rng.randrange(256) for _ in range(size))
        elif mode == 1:
            payload = (b"pengu" * (size // 5 + 1))[:size]
        elif mode == 2:
            payload = bytes(rng.randrange(32, 127) for _ in range(size))
        else:
            payload = bytes(rng.randrange(4) for _ in range(size))
        cases.append(payload)
    return cases


def test_matches_python_for_all_formats(tmp_path, compile_and_run):
    samples = _samples()
    multi_payloads = []
    for index, payload in enumerate(samples):
        # Three members, each a different slice of the payload, so the decoded
        # result is a known concatenation.
        third = len(payload) // 3
        parts = [payload[:third], payload[third:2 * third], payload[2 * third:]]
        multi_payloads.append(b"".join(parts))
        multi = b"".join(gzip.compress(part, mtime=0) for part in parts)
        _write_case(tmp_path, index, payload, multi)

    output = compile_and_run(PROGRAM.replace("@@COUNT@@", str(len(samples))))
    assert "OK" in output, output
    assert "FAIL" not in output, output

    for index, payload in enumerate(samples):
        case = tmp_path / f"c{index}"

        ours_gzip = (case / "out_gzip.z").read_bytes()
        assert gzip.decompress(ours_gzip) == payload, f"case {index}: gzip -> Python"
        assert (case / "back_gzip.bin").read_bytes() == payload, f"case {index}: Python -> gzip"

        ours_zlib = (case / "out_zlib.z").read_bytes()
        assert zlib.decompress(ours_zlib) == payload, f"case {index}: zlib -> Python"
        assert (case / "back_zlib.bin").read_bytes() == payload, f"case {index}: Python -> zlib"

        ours_raw = (case / "out_raw.z").read_bytes()
        assert zlib.decompress(ours_raw, -15) == payload, f"case {index}: raw -> Python"
        assert (case / "back_raw.bin").read_bytes() == payload, f"case {index}: Python -> raw"

        assert (case / "back_multi.bin").read_bytes() == multi_payloads[index], (
            f"case {index}: multi-member"
        )
        assert (case / "back_auto_gzip.bin").read_bytes() == payload, (
            f"case {index}: auto gzip"
        )
        assert (case / "back_auto_zlib.bin").read_bytes() == payload, (
            f"case {index}: auto zlib"
        )

        words = (case / "result.txt").read_text(encoding="utf-8").split()
        assert words[0] == "known", f"case {index}: gzip must be detected"
        assert words[1] == "known", f"case {index}: zlib must be detected"
        # Raw deflate has no magic. Detection is a *structural* header test for
        # zlib, so a random two-byte prefix can legitimately look like one;
        # compare with the same test in Python instead of pretending otherwise.
        expected_nz = "known" if (_looks_like_gzip(payload) or _looks_like_zlib(payload)) else "none"
        assert words[2] == expected_nz, (
            f"case {index}: auto-detection of raw data (got {words[2]}, "
            f"expected {expected_nz})"
        )
        assert int(words[3]) == (zlib.crc32(payload) & 0xFFFFFFFF), (
            f"case {index}: crc32"
        )
        assert int(words[4]) == (zlib.adler32(payload) & 0xFFFFFFFF), (
            f"case {index}: adler32"
        )


def test_empty_gzip_is_a_valid_twenty_byte_stream(tmp_path, compile_and_run):
    """`gzip.compress(b"")` is 20 bytes; ours must be a valid gzip of the same shape.

    The compressed bytes are not required to be identical (the level and the
    implementation of the deflate encoder are allowed to differ), but the
    Python decoder must accept our empty member and return b"".
    """
    program = r'''
import std.archivum
import std.compressus
import std.spark

weave main into int:
    var r as result of string to CompressError is calling compressus.gzip_compress with "", CompressionLevel.Default
    if not r.is_ok:
        calling spark.println with "FAIL compress"
        return 1
    calling spark.println_int with (r.value length)
    calling archivum.write_bytes with "empty.gz", r.value
    banish r
    return 0
'''
    output = compile_and_run(program)
    assert "FAIL" not in output, output
    assert "20" in output.split(), output
    assert gzip.decompress((tmp_path / "empty.gz").read_bytes()) == b""


def _gzip_with_optional_fields(payload: bytes, *, extra: bytes, name: bytes, comment: bytes, bad_fhcrc: bool) -> bytes:
    """A gzip member with FEXTRA + FNAME + FCOMMENT + FHCRC, built by hand.

    Python's ``gzip.compress`` never emits those fields, so the only way to test
    the reader's optional-field walk is to write the header ourselves.
    """
    body = zlib.compress(payload)[2:-4]
    flg = 0x04 | 0x08 | 0x10 | 0x02
    header = b"\x1f\x8b\x08" + bytes([flg]) + b"\x00\x00\x00\x00" + b"\x00\xff"
    header += len(extra).to_bytes(2, "little") + extra
    header += name + b"\x00"
    header += comment + b"\x00"
    crc16 = zlib.crc32(header) & 0xFFFF
    if bad_fhcrc:
        crc16 ^= 0xFFFF
    header += crc16.to_bytes(2, "little")
    trailer = (zlib.crc32(payload) & 0xFFFFFFFF).to_bytes(4, "little")
    trailer += (len(payload) & 0xFFFFFFFF).to_bytes(4, "little")
    return header + body + trailer


def test_gzip_optional_header_fields(tmp_path, compile_and_run):
    """FEXTRA/FNAME/FCOMMENT/FHCRC are parsed, and a bad FHCRC is rejected."""
    payload = b"optional gzip header fields\n" * 30
    good = _gzip_with_optional_fields(
        payload, extra=b"\xde\xad\xbe\xef", name=b"orig.txt", comment=b"made by the test", bad_fhcrc=False
    )
    bad = _gzip_with_optional_fields(
        payload, extra=b"\xde\xad\xbe\xef", name=b"orig.txt", comment=b"made by the test", bad_fhcrc=True
    )
    (tmp_path / "good.gz").write_bytes(good)
    (tmp_path / "bad.gz").write_bytes(bad)

    program = r'''
import std.archivum
import std.compressus
import std.scrolls
import std.spark

weave read_all with path as string into string:
    var m as maybe string is calling archivum.read_bytes with path
    if not (m is present):
        banish m
        return ""
    var out as string is calling scrolls.substring with m.value, 0, (m.value length)
    banish m
    return out

weave main into int:
    var good as result of string to CompressError is calling compressus.gzip_decompress with (calling read_all with "good.gz")
    if not good.is_ok:
        calling spark.println with "FAIL optional fields"
    else:
        calling archivum.write_bytes with "good.out", good.value
    banish good
    var bad as result of string to CompressError is calling compressus.gzip_decompress with (calling read_all with "bad.gz")
    if bad.is_ok:
        calling spark.println with "FAIL bad fhcrc accepted"
    banish bad
    var named as result of string to CompressError is calling compressus.gzip_compress_named with "named payload", "original.bin", CompressionLevel.Default
    if named.is_ok:
        calling archivum.write_bytes with "named.gz", named.value
    else:
        calling spark.println with "FAIL named compress"
    banish named
    calling spark.println with "OK"
    return 0
'''
    output = compile_and_run(program)
    assert "OK" in output, output
    assert "FAIL" not in output, output
    assert (tmp_path / "good.out").read_bytes() == payload
    named = (tmp_path / "named.gz").read_bytes()
    assert gzip.decompress(named) == b"named payload"
    assert named[3] == 0x08, "FNAME flag must be set"
    assert b"original.bin\x00" in named[:64], named[:64]


def test_random_and_malformed_bytes_never_panic(tmp_path, compile_and_run):
    """Fuzz-style corpus: no input may panic a decompressor.

    A `hypothesis` property would recompile the program per example, which is
    the wrong shape for an end-to-end gate. Instead this builds one corpus of
    120 byte strings — pure noise, valid gzip/zlib prefixes with garbage
    bodies, and valid members truncated at a random offset — and one program
    that feeds every one of them to all four decompressors. The program is only
    allowed to exit 0; an `ok` or an `error` result are both correct, a panic is
    not. The same run round-trips every byte string through gzip and checks both
    checksums against `zlib`.
    """
    rng = random.Random(0xC0FFEE)
    valid_gzip = gzip.compress(b"a valid member to truncate", mtime=0)
    valid_zlib = zlib.compress(b"a valid zlib stream to truncate")
    corpus = []
    for index in range(120):
        mode = index % 5
        if mode == 0:
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(2049)))
        elif mode == 1:
            data = b"\x1f\x8b\x08" + bytes(rng.randrange(256) for _ in range(rng.randrange(64)))
        elif mode == 2:
            data = b"\x78\x9c" + bytes(rng.randrange(256) for _ in range(rng.randrange(64)))
        elif mode == 3:
            data = valid_gzip[: rng.randrange(len(valid_gzip) + 1)]
        else:
            data = valid_zlib[: rng.randrange(len(valid_zlib) + 1)]
        corpus.append(data)
        case = tmp_path / f"f{index}"
        case.mkdir()
        (case / "in.bin").write_bytes(data)

    program = r'''
import std.archivum
import std.compressus
import std.scrolls
import std.spark

weave read_all with path as string into string:
    var m as maybe string is calling archivum.read_bytes with path
    if not (m is present):
        banish m
        return ""
    var out as string is calling scrolls.substring with m.value, 0, (m.value length)
    banish m
    return out

weave main into int:
    var i as int is 0
    while i < @@COUNT@@:
        var dir as string is "f{i}"
        var data as string is calling read_all with "{dir}/in.bin"
        var g as result of string to CompressError is calling compressus.gzip_decompress with data
        banish g
        var z as result of string to CompressError is calling compressus.zlib_decompress with data
        banish z
        var d as result of string to CompressError is calling compressus.inflate_decompress with data
        banish d
        var a as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with data
        banish a
        var packed as result of string to CompressError is calling compressus.gzip_compress with data, CompressionLevel.Fastest
        if packed.is_ok:
            var back as result of string to CompressError is calling compressus.gzip_decompress with packed.value
            if back.is_ok:
                calling archivum.write_bytes with "{dir}/roundtrip.bin", back.value
            else:
                calling spark.println with "FAIL roundtrip {dir}"
            banish back
        else:
            calling spark.println with "FAIL compress {dir}"
        banish packed
        var c as u32 is calling compressus.crc32 with data
        var ad as u32 is calling compressus.adler32 with data
        calling archivum.write_bytes with "{dir}/hashes.txt", "{c} {ad}"
        banish data
        set i is i + 1
    calling spark.println with "OK"
    return 0
'''.replace("@@COUNT@@", str(len(corpus)))

    output = compile_and_run(program)
    assert "OK" in output, output
    assert "FAIL" not in output, output
    for index, data in enumerate(corpus):
        case = tmp_path / f"f{index}"
        assert (case / "roundtrip.bin").read_bytes() == data, f"corpus {index}: round-trip"
        words = (case / "hashes.txt").read_text(encoding="utf-8").split()
        assert int(words[0]) == (zlib.crc32(data) & 0xFFFFFFFF), f"corpus {index}: crc32"
        assert int(words[1]) == (zlib.adler32(data) & 0xFFFFFFFF), f"corpus {index}: adler32"
