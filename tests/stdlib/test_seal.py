#!/usr/bin/env python3
"""End-to-end tests for ``std.seal`` (Chunk 7 of the Pengunic 2.0 migration).

Every case compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout and exit code.  Nothing inspects the generated C.

``std.seal`` is the checksum, digest, MAC, KDF and compression module: CRC-32,
MD5, SHA-1, SHA-2, SHA-3, BLAKE2, HMAC, PBKDF2, HKDF, scrypt, gzip and zlib.
This suite is also the regression pin for the Chunk 7 seal bugs; each of those
carries a ``bug_`` prefix and asserts the observable invariant the fix promises
(see ``docs/BUGS_FIXED_CHUNK7.md``).

Digest expectations are Python's ``hashlib`` / ``hmac`` / ``zlib`` values, so the
suite is a parity check against the reference implementation, not a restatement
of the module under test.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``).
"""
from __future__ import annotations

import hashlib
import hmac
import subprocess
import sys
import tempfile
import textwrap
import zlib
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: tests/stdlib/test_seal.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_seal_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(REPO))


def out_of(source: str) -> str:
    """Runs a program that prints one line and returns that line (stripped)."""
    res = run_pengu(source)
    assert res.returncode == 0, f"program failed:\n{res.stdout}\n{res.stderr}"
    return res.stdout.strip()


def digest_lines(digests) -> str:
    """A program that prints the hex digest of ``"hello"`` for each named weave."""
    calls = "\n".join(
        f'            calling spark.println with (calling seal.{name} with "hello")'
        if extra is None else
        f'            calling spark.println with (calling seal.{name} with "hello", {extra})'
        for name, extra in digests
    )
    return f"""
        import std.seal
        import std.spark
        weave main into int:
{calls}
            return 0
    """


# ---------------------------------------------------------------------------
# Version and one-shot digests
# ---------------------------------------------------------------------------

def test_version_is_the_frozen_contract():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with seal.SEAL_VERSION
            return 0
    """) == "2.1.0"


def test_sha2_family_matches_python():
    names = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
    res = run_pengu(digest_lines([(n, None) for n in names]))
    assert res.returncode == 0, res.stderr
    expected = [getattr(hashlib, n)(b"hello").hexdigest() for n in names]
    assert res.stdout.strip().splitlines() == expected


def test_sha3_family_matches_python():
    names = ["sha3_224", "sha3_256", "sha3_384", "sha3_512"]
    res = run_pengu(digest_lines([(n, None) for n in names]))
    assert res.returncode == 0, res.stderr
    expected = [getattr(hashlib, n)(b"hello").hexdigest() for n in names]
    assert res.stdout.strip().splitlines() == expected


def test_sha3_empty_input_matches_python():
    call = "\n".join(
        f'            calling spark.println with (calling seal.{n} with "")'
        for n in ("sha3_224", "sha3_256", "sha3_384", "sha3_512")
    )
    res = run_pengu(f"""
        import std.seal
        import std.spark
        weave main into int:
{call}
            return 0
    """)
    assert res.returncode == 0, res.stderr
    expected = [getattr(hashlib, n)(b"").hexdigest()
                for n in ("sha3_224", "sha3_256", "sha3_384", "sha3_512")]
    assert res.stdout.strip().splitlines() == expected


def test_blake2_matches_python_including_digest_sizes():
    assert out_of(digest_lines([("blake2b", None), ("blake2s", None)])) == \
        hashlib.blake2b(b"hello").hexdigest() + "\n" + hashlib.blake2s(b"hello").hexdigest()
    # A custom digest size changes the digest, not just its truncation.
    res = run_pengu(digest_lines([("blake2b", "32"), ("blake2b", "16")]))
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().splitlines() == [
        hashlib.blake2b(b"hello", digest_size=32).hexdigest(),
        hashlib.blake2b(b"hello", digest_size=16).hexdigest(),
    ]


def test_blake2_rejects_out_of_range_digest_sizes():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as string is calling seal.blake2b with "hello", 0
            var b as string is calling seal.blake2s with "hello", 33
            calling spark.println with "{(a length)} {(b length)}"
            return 0
    """) == "0 0"


def test_long_input_crosses_block_boundaries():
    """1000 deterministic bytes exercise every compression block boundary."""
    data = bytes((i * 7 + 3) % 256 for i in range(1000))
    source_lines = ['            var data as string is ""',
                    "            var codes as list of int is list of int"]
    for value in data:
        source_lines.append(f"            calling codes.push with {value}")
    source_lines.append("            for code in codes:")
    source_lines.append('                set data is "{data}{(chr code)}"')
    for name in ("sha256", "sha3_256", "blake2b", "blake2s"):
        source_lines.append(f"            calling spark.println with (calling seal.{name} with data)")
    src = ("import std.seal\nimport std.spark\n\nweave main into int:\n"
           + "\n".join(source_lines) + "\n            return 0\n")
    res = run_pengu(src)
    assert res.returncode == 0, res.stderr
    expected = [
        hashlib.sha256(data).hexdigest(),
        hashlib.sha3_256(data).hexdigest(),
        hashlib.blake2b(data).hexdigest(),
        hashlib.blake2s(data).hexdigest(),
    ]
    assert res.stdout.strip().splitlines() == expected


# ---------------------------------------------------------------------------
# HMAC
# ---------------------------------------------------------------------------

def test_hmac_matches_python_for_every_algorithm():
    cases = [
        ("hmac_md5", hashlib.md5),
        ("hmac_sha1", hashlib.sha1),
        ("hmac_sha256", hashlib.sha256),
        ("hmac_sha384", hashlib.sha384),
        ("hmac_sha512", hashlib.sha512),
        ("hmac_sha3_256", hashlib.sha3_256),
        ("hmac_sha3_512", hashlib.sha3_512),
    ]
    call = "\n".join(
        f'            calling spark.println with (calling seal.{name} with "key", "msg")'
        for name, _ in cases
    )
    res = run_pengu(f"""
        import std.seal
        import std.spark
        weave main into int:
{call}
            return 0
    """)
    assert res.returncode == 0, res.stderr
    expected = [hmac.new(b"key", b"msg", mod).hexdigest() for _, mod in cases]
    assert res.stdout.strip().splitlines() == expected


def test_bug_s4_hmac_hashes_an_over_long_key_first():
    key = "k" * 100
    assert out_of(f"""
        import std.seal
        import std.spark
        weave main into int:
            var parts as list of string is list of string with capacity 100
            var i as int is 0
            while i < 100:
                calling parts.push with "k"
                set i is i + 1
            var key as string is ""
            for p in parts:
                set key is "{{key}}{{p}}"
            calling spark.println with (calling seal.hmac_sha256 with key, "msg")
            calling spark.println with (calling seal.hmac_sha512 with key, "msg")
            return 0
    """).splitlines() == [
        hmac.new(b"k" * 100, b"msg", hashlib.sha256).hexdigest(),
        hmac.new(b"k" * 100, b"msg", hashlib.sha512).hexdigest(),
    ]


def test_bug_s2_hmac_is_binary_safe():
    """Keys and messages with embedded NULs must hash as real bytes."""
    key = b"a\x00b"
    msg = b"a\x00b"
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var zc as int is 0
            var key as string is "a{(chr zc)}b"
            var msg as string is "a{(chr zc)}b"
            calling spark.println with "{(key length)}"
            calling spark.println with (calling seal.hmac_sha256 with key, "msg")
            calling spark.println with (calling seal.hmac_sha256 with "key", msg)
            return 0
    """).splitlines() == [
        "3",
        hmac.new(key, b"msg", hashlib.sha256).hexdigest(),
        hmac.new(b"key", msg, hashlib.sha256).hexdigest(),
    ]


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def test_pbkdf2_matches_python():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with (calling seal.pbkdf2_hmac_sha256 with "password", "salt", 1000, 32)
            calling spark.println with (calling seal.pbkdf2_hmac_sha512 with "password", "salt", 100, 32)
            return 0
    """).splitlines() == [
        hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 1000, 32).hex(),
        hashlib.pbkdf2_hmac("sha512", b"password", b"salt", 100, 32).hex(),
    ]


def test_pbkdf2_rejects_invalid_parameters():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as string is calling seal.pbkdf2_hmac_sha256 with "pw", "salt", 0, 32
            var b as string is calling seal.pbkdf2_hmac_sha256 with "pw", "salt", 10, 0
            calling spark.println with "{(a length)} {(b length)}"
            return 0
    """) == "0 0"


def test_hkdf_matches_rfc_5869_construction():
    def hkdf(ikm, salt, info, length):
        prk = hmac.new(salt, ikm, hashlib.sha256).digest()
        t = b""
        okm = b""
        counter = 1
        while len(okm) < length:
            t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
            okm += t
            counter += 1
        return okm[:length].hex()

    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with (calling seal.hkdf_sha256 with "ikm", "salt", "info", 42)
            calling spark.println with (calling seal.hkdf_sha256 with "ikm", "", "info", 32)
            return 0
    """).splitlines() == [
        hkdf(b"ikm", b"salt", b"info", 42),
        hkdf(b"ikm", b"\x00" * 32, b"info", 32),
    ]


def test_scrypt_matches_python():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with (calling seal.scrypt with "password", "salt", 16, 1, 1, 32)
            calling spark.println with (calling seal.scrypt with "password", "salt", 16, 2, 1, 16)
            return 0
    """).splitlines() == [
        hashlib.scrypt(b"password", salt=b"salt", n=16, r=1, p=1, dklen=32).hex(),
        hashlib.scrypt(b"password", salt=b"salt", n=16, r=2, p=1, dklen=16).hex(),
    ]


def test_scrypt_validates_parameters():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as string is calling seal.scrypt with "pw", "salt", 15, 1, 1, 32
            var b as string is calling seal.scrypt with "pw", "salt", 16, 0, 1, 32
            var c as string is calling seal.scrypt with "pw", "salt", 16, 1, 1, 0
            calling spark.println with "{(a length)} {(b length)} {(c length)}"
            return 0
    """) == "0 0 0"


# ---------------------------------------------------------------------------
# CRC-32
# ---------------------------------------------------------------------------

def test_crc32_matches_zlib_and_composes():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with ((calling seal.crc32 with "hello") to string)
            var part as u32 is calling seal.crc32_update with 0, "hel"
            var total as u32 is calling seal.crc32_update with part, "lo"
            calling spark.println with (total to string)
            calling spark.println with (((calling seal.crc32 with "hello") == total) to string)
            return 0
    """).splitlines() == [str(zlib.crc32(b"hello")), str(zlib.crc32(b"hello")), "true"]


def test_crc32_file_streams_a_large_file(tmp_path):
    payload = bytes((i * 31 + 7) % 256 for i in range(300_000))
    target = tmp_path / "blob.bin"
    target.write_bytes(payload)
    assert out_of(f"""
        import std.seal
        import std.spark
        weave main into int:
            var c as maybe u32 is calling seal.crc32_file with "{target}"
            if v as u32 is c:
                calling spark.println with (v to string)
            return 0
    """) == str(zlib.crc32(payload))


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

def test_gzip_and_zlib_levels_round_trip():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var ok as int is 0
            var level as int is 1
            while level <= 9:
                var packed as maybe string is calling seal.gzip_level with "hello hello hello", level
                if gz as string is packed:
                    var back as maybe string is calling seal.unzip with gz
                    if raw as string is back:
                        if raw == "hello hello hello":
                            set ok is ok + 1
                var zpacked as maybe string is calling seal.zlib_compress_level with "hello hello hello", level
                if z as string is zpacked:
                    var zback as maybe string is calling seal.zlib_decompress_auto with z
                    if zraw as string is zback:
                        if zraw == "hello hello hello":
                            set ok is ok + 1
                set level is level + 1
            calling spark.println with (ok to string)
            return 0
    """) == "18"


def test_zlib_decompress_auto_accepts_both_wrappers():
    res = run_pengu("""
        import std.seal
        import std.spark
        weave main into int:
            var gz as maybe string is calling seal.gzip with "payload"
            var zl as maybe string is calling seal.zlib_compress with "payload"
            if g as string is gz:
                if raw as string is calling seal.zlib_decompress_auto with g:
                    calling spark.println with raw
            if z as string is zl:
                if raw2 as string is calling seal.zlib_decompress_auto with z:
                    calling spark.println with raw2
            var junk as maybe string is calling seal.zlib_decompress_auto with "junk"
            calling spark.println with ((junk is present) to string)
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().splitlines() == ["payload", "payload", "false"]


def test_bug_s13_result_wrappers_agree():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var legacy as ResultString is calling seal.try_gzip with "payload"
            var native as result of string to string is calling seal.try_gzip_native with "payload"
            calling spark.println with "{(legacy.is_ok)} {(native.is_ok)}"
            var bad as result of string to string is calling seal.try_unzip_native with "not a stream"
            calling spark.println with "{(bad.is_ok)}"
            return 0
    """).splitlines() == ["true true", "false"]


def test_gzip_file_helpers_round_trip(tmp_path):
    source = tmp_path / "plain.txt"
    source.write_text("hello hello hello", encoding="utf-8")
    packed = tmp_path / "packed.gz"
    restored = tmp_path / "restored.txt"
    res = run_pengu(f"""
        import std.seal
        import std.spark
        weave main into int:
            if not (calling seal.gzip_file with "{source}", "{packed}"):
                return 1
            if not (calling seal.unzip_file with "{packed}", "{restored}"):
                return 2
            var raw as maybe string is calling seal.unzip_file_to_bytes with "{packed}"
            if v as string is raw:
                calling spark.println with v
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "hello hello hello"
    assert restored.read_text(encoding="utf-8") == "hello hello hello"


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def test_const_time_eq_and_digest_compare():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with ((calling seal.const_time_eq with "abc", "abc") to string)
            calling spark.println with ((calling seal.const_time_eq with "abc", "abd") to string)
            calling spark.println with ((calling seal.digest_compare with "ABCD", "abcd") to string)
            calling spark.println with ((calling seal.digest_compare with "ABCD", "abce") to string)
            return 0
    """).splitlines() == ["true", "false", "true", "false"]


def test_bug_s19_verify_hash_rejects_unknown_algorithms():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var digest as string is calling seal.sha256 with "hello"
            calling spark.println with ((calling seal.verify_hash with "hello", "nope", "") to string)
            calling spark.println with ((calling seal.verify_hash with "hello", "sha256", "") to string)
            calling spark.println with ((calling seal.verify_hash with "hello", "sha256", digest) to string)
            return 0
    """).splitlines() == ["false", "false", "true"]


def test_bug_s11_verify_hash_is_case_insensitive():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var digest as string is calling seal.sha256 with "hello"
            var upper as string is calling digest.upper
            calling spark.println with ((calling seal.verify_hash with "hello", "sha256", upper) to string)
            calling spark.println with ((calling seal.verify_hash with "hello", "SHA256", upper) to string)
            calling spark.println with ((calling seal.verify_md5 with "hello", "5D41402ABC4B2A76B9719D911017C592") to string)
            return 0
    """).splitlines() == ["true", "true", "true"]


def test_hash_algorithm_registry():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var algos as list of string is calling seal.hash_algos
            calling spark.println with (algos.len to string)
            calling spark.println with ((calling seal.is_valid_hash_alg with "SHA3-256") to string)
            calling spark.println with ((calling seal.is_valid_hash_alg with "crc32") to string)
            calling spark.println with ((calling seal.hash_length with "sha512") to string)
            calling spark.println with ((calling seal.hash_length with "nope") to string)
            return 0
    """).splitlines() == ["12", "true", "false", "128", "0"]


def test_hash_stream_dispatches_by_name():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with (calling seal.hash_stream with "hello", "sha3-256")
            calling spark.println with (calling seal.hash_stream with "hello", "blake2b")
            var unknown as string is calling seal.hash_stream with "hello", "nope"
            calling spark.println with (((unknown length) == 0) to string)
            return 0
    """).splitlines() == [
        hashlib.sha3_256(b"hello").hexdigest(),
        hashlib.blake2b(b"hello").hexdigest(),
        "true",
    ]


# ---------------------------------------------------------------------------
# Streaming digests and MACs
# ---------------------------------------------------------------------------

def test_hash_state_streams_like_the_one_shot():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var h as HashState is calling HashState.new_sha256
            calling h.update with "hel"
            calling h.update with "lo"
            calling spark.println with (calling h.finalize)
            var h3 as HashState is calling HashState.new_sha3_256
            calling spark.println with (calling h3.algorithm)
            calling h3.update with "he"
            calling h3.update with "llo"
            calling spark.println with (calling h3.finalize)
            var hb as HashState is calling HashState.new_blake2b
            calling hb.update with "hello"
            calling spark.println with (calling hb.finalize)
            return 0
    """).splitlines() == [
        hashlib.sha256(b"hello").hexdigest(),
        "sha3-256",
        hashlib.sha3_256(b"hello").hexdigest(),
        hashlib.blake2b(b"hello").hexdigest(),
    ]


def test_hash_state_raw_and_module_level_wrappers():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var h as HashState is calling HashState.new_sha512
            calling seal.hash_update with (sigil of h), "hello"
            var raw as string is calling seal.hash_finalize_raw with (sigil of h)
            calling spark.println with ((raw length) to string)
            var h2 as HashState is calling HashState.new_md5
            calling seal.hash_update with (sigil of h2), "hello"
            calling spark.println with (calling seal.hash_finalize with (sigil of h2))
            return 0
    """).splitlines() == ["64", hashlib.md5(b"hello").hexdigest()]


def test_hmac_state_streams_like_the_one_shot():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var m as HmacState is calling HmacState.new_sha256 with "key"
            calling m.update with "ms"
            calling m.update with "g"
            calling spark.println with (calling m.finalize)
            calling spark.println with (calling m.algorithm)
            var m2 as HmacState is calling HmacState.new_sha512 with "key"
            calling m2.update with "msg"
            calling spark.println with (calling m2.finalize)
            return 0
    """).splitlines() == [
        hmac.new(b"key", b"msg", hashlib.sha256).hexdigest(),
        "sha256",
        hmac.new(b"key", b"msg", hashlib.sha512).hexdigest(),
    ]


# ---------------------------------------------------------------------------
# Hex helpers and randomness
# ---------------------------------------------------------------------------

def test_bug_s3_hex_to_bytes_validates_its_input():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as maybe string is calling seal.hex_to_bytes with "6869"
            var b as maybe string is calling seal.hex_to_bytes with "abc"
            var c as maybe string is calling seal.hex_to_bytes with "zz"
            if v as string is a:
                calling spark.println with v
            calling spark.println with "{(b is present)} {(c is present)}"
            return 0
    """).splitlines() == ["hi", "false false"]


def test_random_bytes_are_fresh_and_correctly_sized():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as string is calling seal.random_bytes with 32
            var b as string is calling seal.random_bytes with 32
            var token as string is calling seal.random_token_hex with 8
            calling spark.println with "{(a length)} {(b length)} {(token length)}"
            calling spark.println with ((calling seal.const_time_eq with a, b) to string)
            return 0
    """).splitlines() == ["32 32 16", "false"]


# ---------------------------------------------------------------------------
# File digests
# ---------------------------------------------------------------------------

def test_file_digests_match_the_one_shot(tmp_path):
    payload = bytes((i * 13 + 5) % 256 for i in range(200_000))
    target = tmp_path / "data.bin"
    target.write_bytes(payload)
    assert out_of(f"""
        import std.seal
        import std.spark
        weave main into int:
            var a as maybe string is calling seal.md5_file with "{target}"
            var b as maybe string is calling seal.sha1_file with "{target}"
            var c as maybe string is calling seal.sha256_file with "{target}"
            var d as maybe string is calling seal.sha512_file with "{target}"
            var e as maybe string is calling seal.sha224_file with "{target}"
            var f as maybe string is calling seal.sha384_file with "{target}"
            var g as maybe string is calling seal.sha3_256_file with "{target}"
            var h as maybe string is calling seal.blake2b_file with "{target}"
            if v1 as string is a:
                calling spark.println with v1
            if v2 as string is b:
                calling spark.println with v2
            if v3 as string is c:
                calling spark.println with v3
            if v4 as string is d:
                calling spark.println with v4
            if v5 as string is e:
                calling spark.println with v5
            if v6 as string is f:
                calling spark.println with v6
            if v7 as string is g:
                calling spark.println with v7
            if v8 as string is h:
                calling spark.println with v8
            return 0
    """).splitlines() == [
        hashlib.md5(payload).hexdigest(),
        hashlib.sha1(payload).hexdigest(),
        hashlib.sha256(payload).hexdigest(),
        hashlib.sha512(payload).hexdigest(),
        hashlib.sha224(payload).hexdigest(),
        hashlib.sha384(payload).hexdigest(),
        hashlib.sha3_256(payload).hexdigest(),
        hashlib.blake2b(payload).hexdigest(),
    ]


def test_missing_file_returns_none():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var a as maybe string is calling seal.sha256_file with "/nonexistent/path/file.bin"
            var b as maybe u32 is calling seal.crc32_file with "/nonexistent/path/file.bin"
            calling spark.println with "{(a is present)} {(b is present)}"
            return 0
    """) == "false false"


def test_verify_hash_file(tmp_path):
    payload = b"verify me"
    target = tmp_path / "v.bin"
    target.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    assert out_of(f"""
        import std.seal
        import std.spark
        weave main into int:
            calling spark.println with ((calling seal.verify_hash_file with "{target}", "sha256", "{digest}") to string)
            calling spark.println with ((calling seal.verify_hash_file with "{target}", "sha256", "00") to string)
            calling spark.println with ((calling seal.verify_hash_file with "{target}", "nope", "{digest}") to string)
            return 0
    """).splitlines() == ["true", "false", "false"]


# ---------------------------------------------------------------------------
# Enchantments
# ---------------------------------------------------------------------------

def test_string_enchantments_delegate():
    assert out_of("""
        import std.seal
        import std.spark
        weave main into int:
            var hello as string is "hello"
            calling spark.println with (calling hello.to_md5)
            calling spark.println with (calling hello.to_sha256)
            calling spark.println with (calling hello.to_sha3_256)
            calling spark.println with (calling hello.to_blake2b)
            calling spark.println with ((calling hello.to_crc32) to string)
            return 0
    """).splitlines() == [
        hashlib.md5(b"hello").hexdigest(),
        hashlib.sha256(b"hello").hexdigest(),
        hashlib.sha3_256(b"hello").hexdigest(),
        hashlib.blake2b(b"hello").hexdigest(),
        str(zlib.crc32(b"hello")),
    ]
