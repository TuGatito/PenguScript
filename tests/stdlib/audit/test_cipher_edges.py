"""``std.cipher`` — codec round trips, invalid-input edges, and the leak regression.

The codecs used to allocate a one-byte owning `string` per inspected character
(`json_unescape` and the base32/base85/base58 helpers).  The churn program runs
valid and invalid inputs through the whole encoder/decoder surface and releases
every returned value, so a residual internal allocation fails the ASan run.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.cipher

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave chk_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
    banish got

weave eat with s as string into void:
    banish s
"""


def test_cipher_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var hello as string is "hello world"
    var abc as string is "abc"
    var bad as string is "!!!not base64!!!"

    # base64
    var b64 as string is calling cipher.encode_base64 with hello
    calling eq_s with b64, "aGVsbG8gd29ybGQ=", "encode_base64"
    banish b64
    var db64 as maybe string is calling cipher.decode_base64 with "aGVsbG8gd29ybGQ="
    calling eq_b with db64.is_present, true, "decode_base64 present"
    if s as string is db64:
        calling eq_s with s, hello, "decode_base64 value"
    banish db64
    var dbad as maybe string is calling cipher.decode_base64 with bad
    calling eq_b with dbad.is_present, false, "decode_base64 rejects garbage"
    banish dbad
    var urlenc as string is calling cipher.encode_base64_url with hello
    var urldec as maybe string is calling cipher.decode_base64_url with urlenc
    calling eq_b with urldec.is_present, true, "base64url round trip present"
    if us as string is urldec:
        calling eq_s with us, hello, "base64url round trip"
    banish urldec
    banish urlenc
    var nopad as string is calling cipher.encode_base64_nopad with hello
    var nopad_dec as maybe string is calling cipher.decode_base64_nopad with nopad
    calling eq_b with nopad_dec.is_present, true, "base64 nopad round trip present"
    banish nopad_dec
    banish nopad

    # hex
    var hx as string is calling cipher.encode_hex with abc
    calling eq_s with hx, "616263", "encode_hex"
    banish hx
    var dhx as maybe string is calling cipher.decode_hex with "616263"
    calling eq_b with dhx.is_present, true, "decode_hex present"
    if hs as string is dhx:
        calling eq_s with hs, abc, "decode_hex value"
    banish dhx
    var dhbad as maybe string is calling cipher.decode_hex with "zz"
    calling eq_b with dhbad.is_present, false, "decode_hex rejects garbage"
    banish dhbad

    # base32 / base58 / base85 round trips
    var b32 as string is calling cipher.encode_base32 with abc
    var d32 as maybe string is calling cipher.decode_base32 with b32
    calling eq_b with d32.is_present, true, "base32 round trip present"
    if t32 as string is d32:
        calling eq_s with t32, abc, "base32 round trip"
    banish d32
    banish b32
    var b85 as string is calling cipher.encode_base85 with abc
    var d85 as maybe string is calling cipher.decode_base85 with b85
    calling eq_b with d85.is_present, true, "base85 round trip present"
    if t85 as string is d85:
        calling eq_s with t85, abc, "base85 round trip"
    banish d85
    banish b85
    var z85 as string is calling cipher.encode_base85_z85 with abc
    var dz85 as maybe string is calling cipher.decode_base85_z85 with z85
    banish dz85
    banish z85
    var b58 as string is calling cipher.encode_base58 with abc
    var d58 as maybe string is calling cipher.decode_base58 with b58
    calling eq_b with d58.is_present, true, "base58 round trip present"
    if t58 as string is d58:
        calling eq_s with t58, abc, "base58 round trip"
    banish d58
    banish b58

    # url encoding
    var fancy as string is "a b&c"
    var uenc as string is calling cipher.encode_url with fancy
    var udec as maybe string is calling cipher.decode_url with uenc
    calling eq_b with udec.is_present, true, "url round trip present"
    if us2 as string is udec:
        calling eq_s with us2, fancy, "url round trip"
    banish udec
    banish uenc

    # JSON escaping round trip (the exact escape spelling is asserted in the
    # cipher self-tests; here the lossless round trip is what the audit needs).
    var raw as string is "a\\"b\\nc"
    var esc as string is calling cipher.json_escape with raw
    var unesc as string is calling cipher.json_unescape with esc
    calling eq_s with unesc, raw, "json_escape/unescape round trip"
    banish unesc
    banish esc
    var plain as string is "plain"
    var esc2 as string is calling cipher.json_escape with plain
    calling eq_s with esc2, "plain", "json_escape leaves plain text"
    banish esc2

    # checksum and misc predicates
    var crc as string is calling cipher.crc32_hex with abc
    calling eq_i with (calling crc.len), 8, "crc32_hex length"
    banish crc
    var isb as bool is calling cipher.is_base64 with "aGVsbG8="
    var isb2 as bool is calling cipher.is_base64 with "!!!!"
    var len64 as int is calling cipher.base64_length with 3

    calling spark.println with "DONE"
    return 0
""")


def test_cipher_no_internal_leak(compile_and_run):
    out = compile_and_run(_PRE + """
weave churn with s as string into void:
    var a as string is calling cipher.encode_base64 with s
    var ad as maybe string is calling cipher.decode_base64 with a
    banish ad
    banish a
    var c as string is calling cipher.encode_base64_url with s
    var cd as maybe string is calling cipher.decode_base64_url with c
    banish cd
    banish c
    var d as string is calling cipher.encode_base64_nopad with s
    var dd as maybe string is calling cipher.decode_base64_nopad with d
    banish dd
    banish d
    var e as string is calling cipher.encode_hex with s
    var ed as maybe string is calling cipher.decode_hex with e
    banish ed
    banish e
    var g as string is calling cipher.encode_base32 with s
    var gd as maybe string is calling cipher.decode_base32 with g
    banish gd
    banish g
    var i as string is calling cipher.encode_base85 with s
    var id as maybe string is calling cipher.decode_base85 with i
    banish id
    banish i
    var k as string is calling cipher.encode_base85_z85 with s
    var kd as maybe string is calling cipher.decode_base85_z85 with k
    banish kd
    banish k
    var l as string is calling cipher.encode_base58 with s
    var ld as maybe string is calling cipher.decode_base58 with l
    banish ld
    banish l
    var n as string is calling cipher.encode_url with s
    var nd as maybe string is calling cipher.decode_url with n
    banish nd
    banish n
    var o as string is calling cipher.json_escape with s
    var ou as string is calling cipher.json_unescape with o
    banish ou
    banish o
    var q as string is calling cipher.crc32_hex with s
    banish q
    var r as bool is calling cipher.is_base64 with s

weave main into int:
    var inputs as list of string is list of string
    calling inputs.push with "hello world"
    calling inputs.push with "abc"
    calling inputs.push with ""
    calling inputs.push with "!!!not base64!!!"
    var i as int is 0
    while i < 30:
        for s in inputs:
            calling churn with s
        set i is i + 1
    banish inputs
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
