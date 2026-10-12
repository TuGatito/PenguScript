#!/usr/bin/env python3
"""End-to-end tests for ``std.cipher`` (Chunk 7 of the Pengunic 2.0 migration).

Every case compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout and exit code.  Nothing inspects the generated C: the
contract under test is behaviour.

``std.cipher`` is the encoding and JSON module: Base64/Hex/Base32/Base85/Z85/
Base58, percent-encoding, CRC-32, the legacy flat JSON surface and the generic
``JsonValue`` tree.  This suite is also the regression pin for the Chunk 7
cipher bugs; each of those carries a ``bug_`` prefix and asserts the observable
invariant the fix promises (see ``docs/BUGS_FIXED_CHUNK7.md``).

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: tests/stdlib/test_cipher.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]

#: Opens a program that needs to spell double quotes: raw strings cannot hold
#: one, so the fixtures below write ``^`` and this prelude turns it into a quote.
QUOTE_PRELUDE = '''
        import std.spark
        import std.cipher

        ## Turns the `^` placeholder into a double quote.
        weave dq with s as string into string:
            var qn as int is 34
            return calling s.replace_all with "^", (chr qn)
'''


def run_pengu(source: str, *args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_cipher_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(REPO))


def byte_source(values, tail):
    """Builds a program whose ``data`` holds the raw byte ``values``.

    The bytes are produced by a runtime ``chr`` over an ``int`` list: a constant
    ``chr N`` with ``N > 127`` is folded into a UTF-8 C literal (two bytes) and a
    constant ``chr 0`` vanishes entirely, both documented compiler findings.
    """
    lines = ["    import std.cipher", "    import std.spark", "",
             "    weave main into int:",
             '        var data as string is ""',
             "        var codes as list of int is list of int"]
    for value in values:
        lines.append(f"        calling codes.push with {value}")
    lines.append("        for code in codes:")
    lines.append('            set data is "{data}{(chr code)}"')
    lines.extend("        " + line for line in tail)
    lines.append("        return 0")
    return "\n".join(lines)

def out_of(source: str) -> str:
    """Runs a program that prints one line and returns that line (stripped)."""
    res = run_pengu(source)
    assert res.returncode == 0, f"program failed:\n{res.stdout}\n{res.stderr}"
    return res.stdout.strip()


# ---------------------------------------------------------------------------
# Base64
# ---------------------------------------------------------------------------

def test_version_is_the_frozen_contract():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            calling spark.println with cipher.CIPHER_VERSION
            return 0
    """) == "2.1.0"


def test_base64_round_trip_matches_python():
    payload = "hello world"
    expected = base64.b64encode(payload.encode()).decode()
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var enc as string is calling cipher.encode_base64 with "{payload}"
            calling spark.println with enc
            return 0
    """) == expected
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var dec as maybe string is calling cipher.decode_base64 with "{expected}"
            if v as string is dec:
                calling spark.println with v
            return 0
    """) == payload


def test_bug_c15_decode_base64_rejects_misplaced_padding():
    """Padding may only close the string; 2.0.0 accepted ``QQ==QQ==``."""
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var a as maybe string is calling cipher.decode_base64 with "QQ==QQ=="
            var b as maybe string is calling cipher.decode_base64 with "===="
            var c as maybe string is calling cipher.decode_base64 with "Q==="
            calling spark.println with "{(a is present)} {(b is present)} {(c is present)}"
            return 0
    """) == "false false false"


def test_bug_c14_decoders_validate_the_alphabet():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var a as maybe string is calling cipher.decode_base64 with "AB*D"
            var b as maybe string is calling cipher.decode_base64 with "AB-D"
            var c as maybe string is calling cipher.decode_base64_url with "AB-D"
            calling spark.println with "{(a is present)} {(b is present)} {(c is present)}"
            return 0
    """) == "false false true"


def test_base64_url_and_unpadded_variants():
    raw = bytes([251, 255, 0])
    expected_url = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var b251 as int is 251
            var b255 as int is 255
            var b0 as int is 0
            var blob as string is "{{(chr b251)}}{{(chr b255)}}{{(chr b0)}}"
            calling spark.println with (calling cipher.encode_base64_url with blob)
            return 0
    """) == expected_url
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var d as maybe string is calling cipher.decode_base64_url with "{expected_url}"
            if v as string is d:
                var h as string is calling cipher.encode_hex with v
                calling spark.println with h
            return 0
    """) == "fbff00"


def test_base64_helpers_and_aliases():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            calling spark.println with ((calling cipher.base64_length with 0) to string)
            calling spark.println with ((calling cipher.base64_length with 1) to string)
            calling spark.println with ((calling cipher.base64_length with 4) to string)
            calling spark.println with ((calling cipher.is_base64 with "aGk=") to string)
            calling spark.println with ((calling cipher.is_base64 with "aGk") to string)
            return 0
    """).splitlines() == ["0", "4", "8", "true", "false"]


# ---------------------------------------------------------------------------
# Hex and Base32
# ---------------------------------------------------------------------------

def test_hex_round_trip_and_rejections():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            calling spark.println with (calling cipher.encode_hex with "hi")
            var a as maybe string is calling cipher.decode_hex with "abc"
            var b as maybe string is calling cipher.decode_hex with "zz"
            var c as maybe string is calling cipher.decode_hex with "6869"
            calling spark.println with "{(a is present)} {(b is present)}"
            if v as string is c:
                calling spark.println with v
            return 0
    """).splitlines() == ["6869", "false false", "hi"]


def test_base32_round_trip_for_every_length():
    """Every length from 0 to 20 exercises each partial-group case."""
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var ok as int is 0
            var n as int is 0
            while n <= 20:
                var data as string is ""
                var j as int is 0
                while j < n:
                    set data is "{data}{(chr j)}"
                    set j is j + 1
                var enc as string is calling cipher.encode_base32 with data
                var dec as maybe string is calling cipher.decode_base32 with enc
                if v as string is dec:
                    if v == data:
                        set ok is ok + 1
                set n is n + 1
            calling spark.println with (ok to string)
            return 0
    """) == "21"


def test_bug_c19_base32_padding_must_close_the_string():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var a as maybe string is calling cipher.decode_base32 with "AA======AA======"
            var b as maybe string is calling cipher.decode_base32 with "NBUQ===="
            var c as maybe string is calling cipher.decode_base32 with "nbuq ===="
            calling spark.println with "{(a is present)}"
            if v as string is b:
                calling spark.println with v
            if w as string is c:
                calling spark.println with w
            return 0
    """).splitlines() == ["false", "hi", "hi"]


# ---------------------------------------------------------------------------
# Base85, Z85 and Base58
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [b"", b"a", b"ab", b"abc", b"abcd", bytes(range(1, 11))])
def test_base85_matches_python(payload):
    expected = base64.b85encode(payload).decode()
    assert out_of(byte_source(list(payload), [
        "calling spark.println with (calling cipher.encode_base85 with data)",
    ])) == expected
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var dec as maybe string is calling cipher.decode_base85 with "{expected}"
            if v as string is dec:
                calling spark.println with (calling cipher.encode_hex with v)
            return 0
    """) == payload.hex()


def test_z85_matches_the_zeromq_vector():
    raw = bytes([0x86, 0x4F, 0xD2, 0x6F, 0xB5, 0x59, 0xF7, 0x5B])
    assert out_of(byte_source(list(raw), [
        "calling spark.println with (calling cipher.encode_base85_z85 with data)",
        'var dec as maybe string is calling cipher.decode_base85_z85 with "HelloWorld"',
        "if v as string is dec:",
        "    calling spark.println with (calling cipher.encode_hex with v)",
        'var short as string is calling cipher.encode_base85_z85 with "abc"',
        'calling spark.println with "{(short length) == 0}"',
    ])).splitlines() == ["HelloWorld", raw.hex(), "true"]


def test_base58_matches_a_reference_implementation():
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    def b58(data: bytes) -> str:
        n = int.from_bytes(data, "big") if data else 0
        out = ""
        while n > 0:
            n, r = divmod(n, 58)
            out = alphabet[r] + out
        zeros = len(data) - len(data.lstrip(b"\x00"))
        return "1" * zeros + out

    payload = b"\x01\x02hello"
    expected = b58(payload)
    assert out_of(byte_source(list(payload), [
        "calling spark.println with (calling cipher.encode_base58 with data)",
    ])) == expected
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var dec as maybe string is calling cipher.decode_base58 with "{expected}"
            if v as string is dec:
                calling spark.println with (calling cipher.encode_hex with v)
            return 0
    """) == payload.hex()
    # A leading zero byte becomes a leading "1" (built from a variable: a literal
    # `chr 0` is folded into the C format string and would vanish).
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var zc as int is 0
            var data as string is "{(chr zc)}{(chr 1)}"
            calling spark.println with (calling cipher.encode_base58 with data)
            return 0
    """) == "12"


# ---------------------------------------------------------------------------
# URL encoding and CRC-32
# ---------------------------------------------------------------------------

def test_url_encoding_matches_urllib():
    from urllib.parse import quote
    text = "a b/c?d=e&f"
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            calling spark.println with (calling cipher.encode_url with "{text}")
            return 0
    """) == quote(text, safe="")
    encoded = quote(text, safe="")
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var dec as maybe string is calling cipher.decode_url with "{encoded}"
            if v as string is dec:
                calling spark.println with v
            return 0
    """) == text


def test_crc32_hex_matches_zlib():
    import zlib
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            calling spark.println with (calling cipher.crc32_hex with "hello")
            calling spark.println with (calling cipher.crc32_hex with "")
            return 0
    """).splitlines() == [format(zlib.crc32(b"hello"), "08x"), "00000000"]


# ---------------------------------------------------------------------------
# JSON escaping
# ---------------------------------------------------------------------------

def test_bug_c2_json_unescape_combines_surrogate_pairs():
    assert out_of(r"""
        import std.cipher
        import std.spark
        weave main into int:
            var decoded as string is calling cipher.json_unescape with "\\uD83D\\uDE00"
            calling spark.println with (calling cipher.encode_hex with decoded)
            return 0
    """) == "\U0001F600".encode().hex()


def test_json_escape_matches_python_for_ascii():
    text = 'a"b\\c\nd\te\x01f'
    pengu_text = 'a\\"b\\\\c\\nd\\te\\u0001f'
    expected = json.dumps(text)[1:-1]
    assert out_of(f"""
        import std.cipher
        import std.spark
        weave main into int:
            var src as string is "{pengu_text}"
            calling spark.println with (calling cipher.json_escape with src)
            return 0
    """) == expected


# ---------------------------------------------------------------------------
# Legacy flat JSON
# ---------------------------------------------------------------------------

def test_bug_c5_parse_json_is_strict():
    """Trailing commas, incomplete literals, empty values and junk are rejected."""
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var a as maybe map of string to string is calling cipher.parse_json with (calling dq with r"{^a^: tru}")
            var b as maybe map of string to string is calling cipher.parse_json with (calling dq with r"{^a^: 1,}")
            var c as maybe map of string to string is calling cipher.parse_json with (calling dq with r"{^a^:}")
            var d as maybe map of string to string is calling cipher.parse_json with (calling dq with r"{^a^: 1} trailing")
            var e as maybe map of string to string is calling cipher.parse_json with (calling dq with r"{^a^: 1 2 3}")
            calling spark.println with "{(a is present)} {(b is present)} {(c is present)} {(d is present)} {(e is present)}"
            return 0
    """) == "false false false false false"


def test_bug_c8_parse_json_keeps_nested_braces():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^a^: {^b^: 1}}"
            var m as maybe map of string to string is calling cipher.parse_json with doc
            if mv as map of string to string is m:
                calling spark.println with (calling mv.get with "a")
            return 0
    """) == '{"b": 1}'


def test_bug_c24_stringify_json_sorts_keys():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var m as map of string to string is map of string to string
            calling m.put with "b", "2"
            calling m.put with "a", "1"
            calling m.put with "c", "3"
            var out as maybe string is calling cipher.stringify_json with m
            if s as string is out:
                calling spark.println with s
            return 0
    """) == '{"a":1,"b":2,"c":3}'


def test_parse_json_array_and_serializer():
    res = run_pengu(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"[1, ^two^, true]"
            var xs as maybe list of string is calling cipher.parse_json_array with doc
            if items as list of string is xs:
                var out as maybe string is calling cipher.stringify_json_array with items
                if s as string is out:
                    calling spark.println with s
            var bad as maybe list of string is calling cipher.parse_json_array with "[1, 2,]"
            calling spark.println with "{(bad is present)}"
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().splitlines() == ['[1,"two",true]', "false"]


def test_bug_c5_parse_value_validates_the_whole_input():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var a as maybe string is calling cipher.parse_value with "1 2 3"
            var b as maybe string is calling cipher.parse_value with "tru"
            calling spark.println with "{(a is present)} {(b is present)}"
            calling spark.println with "{(calling cipher.is_valid_json_value with "1 2 3")}"
            return 0
    """).splitlines() == ["false false", "false"]


def test_pretty_json_and_file_helpers(tmp_path):
    target = tmp_path / "doc.json"
    res = run_pengu(QUOTE_PRELUDE + f"""
        import std.archivum
        weave main into int:
            var m as map of string to string is map of string to string
            calling m.put with "b", "2"
            calling m.put with "a", "1"
            if not (calling cipher.write_json_file_pretty with "{target}", m, 2):
                return 1
            var back as maybe map of string to string is calling cipher.read_json_file with "{target}"
            if bm as map of string to string is back:
                if (calling bm.get with "a") != "1":
                    return 2
            var raw as maybe string is calling archivum.read_file with "{target}"
            if text as string is raw:
                calling spark.println with text
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == '{\n  "a": 1,\n  "b": 2\n}'


# ---------------------------------------------------------------------------
# Generic JsonValue tree
# ---------------------------------------------------------------------------

def test_parse_json_value_builds_the_generic_tree():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^name^: ^Ada^, ^age^: 36, ^tags^: [^a^, ^b^], ^ok^: true}"
            var v as maybe cipher.JsonValue is calling cipher.parse_json_value with doc
            if jv as cipher.JsonValue is v:
                calling spark.println with (calling cipher.json_value_type with jv)
                calling spark.println with ((calling cipher.json_value_len with jv) to string)
                if nv as cipher.JsonValue is calling cipher.json_value_get with jv, "name":
                    calling spark.println with (calling cipher.json_value_to_string with nv)
                if av as cipher.JsonValue is calling cipher.json_value_get with jv, "age":
                    if iv as int is calling cipher.json_value_as_int with av:
                        calling spark.println with (iv to string)
                if tv as cipher.JsonValue is calling cipher.json_value_get with jv, "tags":
                    if fv as cipher.JsonValue is calling cipher.json_value_at with tv, 0:
                        calling spark.println with (calling cipher.json_value_to_string with fv)
            return 0
    """).splitlines() == ["object", "4", "Ada", "36", "a"]


def test_parse_json_value_is_strict_and_surrogate_aware():
    assert out_of(QUOTE_PRELUDE + r"""
        weave main into int:
            var bad as maybe cipher.JsonValue is calling cipher.parse_json_value with (calling dq with r"{^a^: 1,}")
            var lone as maybe cipher.JsonValue is calling cipher.parse_json_value with (calling dq with r"^\uD83D^")
            calling spark.println with "{(bad is present)} {(lone is present)}"
            var pair as string is calling dq with r"^\uD83D\uDE00^"
            if pv as cipher.JsonValue is calling cipher.parse_json_value with pair:
                calling spark.println with (calling cipher.encode_hex with (calling cipher.json_value_to_string with pv))
            return 0
    """).splitlines() == ["false false", "\U0001F600".encode().hex()]


def test_generic_round_trip_and_canonical_form():
    doc = {"b": 1, "a": {"d": 2, "c": [True, None, "x"]}}
    literal = json.dumps(doc, separators=(",", ":"))
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    res = run_pengu(QUOTE_PRELUDE + f"""
        weave main into int:
            var doc as string is calling dq with r"{{^b^: 1, ^a^: {{^d^: 2, ^c^: [true, null, ^x^]}}}}"
            if jv as cipher.JsonValue is calling cipher.parse_json_value with doc:
                calling spark.println with (calling cipher.stringify_json_value with jv)
                calling spark.println with (calling cipher.json_dumps_canonical with jv)
                var text as string is calling cipher.stringify_json_value with jv
                var again as maybe cipher.JsonValue is calling cipher.parse_json_value with text
                if av as cipher.JsonValue is again:
                    var same as bool is calling cipher.json_value_equal with jv, av
                    calling spark.println with "{{same}}"
            return 0
    """)
    assert res.returncode == 0, res.stderr
    lines = res.stdout.strip().splitlines()
    # Both serializers sort object members, so the compact form is already the
    # canonical form; the input order is not preserved (documented).
    assert lines[0] == canonical
    assert lines[1] == canonical
    assert lines[2] == "true"


def test_stringify_json_value_pretty_indents():
    res = run_pengu("""
        import std.cipher
        import std.spark
        weave main into int:
            if jv as cipher.JsonValue is calling cipher.parse_json_value with "[1, 2]":
                calling spark.println with (calling cipher.stringify_json_value_pretty with jv, 2)
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "[\n  1,\n  2\n]"


def test_json_value_coercions_and_predicates():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"[42, 4.5, ^7^, true, null]"
            if xs as list of cipher.JsonValue is calling cipher.parse_json_to_list with doc:
                var i0 as maybe int is calling cipher.json_value_as_int with (xs at 0)
                var i1 as maybe int is calling cipher.json_value_as_int with (xs at 2)
                if a as int is i0:
                    calling spark.println with (a to string)
                if b as int is i1:
                    calling spark.println with (b to string)
                calling spark.println with "{(calling cipher.json_value_is_float with (xs at 1))} {(calling cipher.json_value_is_null with (xs at 4))}"
            return 0
    """).splitlines() == ["42", "7", "true true"]


def test_parse_json_to_map_and_deep_clone():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^a^: [1, 2]}"
            if m as map of string to cipher.JsonValue is calling cipher.parse_json_to_map with doc:
                var v as cipher.JsonValue is m at "a"
                var copy as cipher.JsonValue is calling cipher.json_value_deep_clone with v
                calling spark.println with "{(calling cipher.json_value_equal with v, copy)}"
                calling spark.println with (calling cipher.stringify_json_value with copy)
            return 0
    """).splitlines() == ["true", "[1,2]"]


# ---------------------------------------------------------------------------
# JSON Pointer, Patch and Merge Patch
# ---------------------------------------------------------------------------

def test_json_pointer_get_resolves_escapes_and_arrays():
    doc = {"users": [{"name": "Ada"}, {"name": "Bob"}], "a/b": 1, "m~n": 2}
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^users^: [{^name^: ^Ada^}, {^name^: ^Bob^}], ^a/b^: 1, ^m~n^: 2}"
            if jv as cipher.JsonValue is calling cipher.parse_json_value with doc:
                if nv as cipher.JsonValue is calling cipher.json_pointer_get with jv, "/users/1/name":
                    calling spark.println with (calling cipher.json_value_to_string with nv)
                if sv as cipher.JsonValue is calling cipher.json_pointer_get with jv, "/a~1b":
                    if x as int is calling cipher.json_value_as_int with sv:
                        calling spark.println with (x to string)
                var root_ok as bool is (calling cipher.json_pointer_get with jv, "") is present
                var bad_ok as bool is (calling cipher.json_pointer_get with jv, "users") is present
                calling spark.println with "{root_ok} {bad_ok}"
            return 0
    """).splitlines() == ["Bob", "1", "true false"]


def test_json_patch_applies_operations():
    patch = [
        {"op": "add", "path": "/c", "value": 3},
        {"op": "replace", "path": "/a", "value": 9},
        {"op": "remove", "path": "/b/0"},
        {"op": "test", "path": "/c", "value": 3},
        {"op": "move", "from": "/c", "path": "/d"},
    ]
    expected = json.dumps({"a": 9, "b": [2], "d": 3}, separators=(",", ":"), sort_keys=True)
    res = run_pengu(QUOTE_PRELUDE + f"""
        weave main into int:
            var doc as string is calling dq with r"{{^a^: 1, ^b^: [1, 2]}}"
            var pdoc as string is calling dq with r"{json.dumps(patch, separators=(",", ":")).replace('"', '^').replace(':', ': ')}"
            if dv as cipher.JsonValue is calling cipher.parse_json_value with doc:
                if pv as cipher.JsonValue is calling cipher.parse_json_value with pdoc:
                    var r as result of cipher.JsonValue to string is calling cipher.json_patch with dv, pv
                    if r.is_ok:
                        var out as cipher.JsonValue is calling r.unwrap
                        calling spark.println with (calling cipher.json_dumps_canonical with out)
                    else:
                        calling spark.println with "ERR"
            return 0
    """)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == expected


def test_json_patch_reports_failures():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^a^: 1}"
            var patch as string is calling dq with r"[{^op^: ^test^, ^path^: ^/a^, ^value^: 2}]"
            if dv as cipher.JsonValue is calling cipher.parse_json_value with doc:
                if pv as cipher.JsonValue is calling cipher.parse_json_value with patch:
                    var r as result of cipher.JsonValue to string is calling cipher.json_patch with dv, pv
                    calling spark.println with "{(r.is_ok)}"
            var bad as string is calling dq with r"{^op^: ^test^}"
            if dv2 as cipher.JsonValue is calling cipher.parse_json_value with doc:
                if bv as cipher.JsonValue is calling cipher.parse_json_value with bad:
                    var r2 as result of cipher.JsonValue to string is calling cipher.json_patch with dv2, bv
                    calling spark.println with "{(r2.is_ok)}"
            return 0
    """).splitlines() == ["false", "false"]


def test_json_merge_patch_follows_rfc_7396():
    target = {"a": 1, "b": {"x": 1, "y": 2}}
    patch = {"a": None, "b": {"y": 5, "z": 6}}
    expected = json.dumps({"b": {"x": 1, "y": 5, "z": 6}}, separators=(",", ":"), sort_keys=True)
    assert out_of(QUOTE_PRELUDE + f"""
        weave main into int:
            var doc as string is calling dq with r"{{^a^: 1, ^b^: {{^x^: 1, ^y^: 2}}}}"
            var patch as string is calling dq with r"{{^a^: null, ^b^: {{^y^: 5, ^z^: 6}}}}"
            if dv as cipher.JsonValue is calling cipher.parse_json_value with doc:
                if pv as cipher.JsonValue is calling cipher.parse_json_value with patch:
                    calling spark.println with (calling cipher.json_dumps_canonical with (calling cipher.json_merge_patch with dv, pv))
            return 0
    """) == expected


# ---------------------------------------------------------------------------
# Legacy getters and paths
# ---------------------------------------------------------------------------

def test_bug_c9_json_get_float_bounds_the_exponent():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var huge as string is calling dq with r"{^a^: 1e1000000}"
            if m as map of string to string is calling cipher.parse_json with huge:
                var f as maybe float is calling cipher.json_get_float with m, "a"
                if v as float is f:
                    calling spark.println with "{(v > 1000000.0)}"
            var normal as string is calling dq with r"{^a^: -2.5e2}"
            if m2 as map of string to string is calling cipher.parse_json with normal:
                var g as maybe float is calling cipher.json_get_float with m2, "a"
                if v2 as float is g:
                    calling spark.println with "{(v2 < -249.0 and v2 > -251.0)}"
            return 0
    """).splitlines() == ["true", "true"]


def test_typed_getters_and_json_kind():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var doc as string is calling dq with r"{^n^: 42, ^f^: 1.5, ^b^: true, ^s^: ^hi^}"
            if m as map of string to string is calling cipher.parse_json with doc:
                if i as int is calling cipher.json_get_int with m, "n":
                    calling spark.println with (i to string)
                calling spark.println with (calling cipher.json_get_or with m, "missing", "fallback")
                calling spark.println with "{(calling cipher.json_has with m, "b")} {(calling cipher.json_get_bool with m, "b").value}"
                var is_number as bool is (calling cipher.json_kind_of with (calling m.get with "f")) == cipher.JsonKind.JsonNumber
                calling spark.println with "{is_number}"
            return 0
    """).splitlines() == ["42", "fallback", "true true", "true"]


def test_bug_c23_json_path_walks_arrays():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var arr as string is calling dq with r"[{^b^: 1}, {^b^: 2}]"
            var top as string is calling dq with r"{^b^: 9}"
            var m as map of string to string is map of string to string
            calling m.put with "users", arr
            calling m.put with "top", top
            if a as string is calling cipher.json_path with m, "users[1].b":
                calling spark.println with a
            if b as string is calling cipher.json_path with m, "top.b":
                calling spark.println with b
            var missing as bool is (calling cipher.json_path with m, "users[9].b") is present
            calling spark.println with "{missing}"
            return 0
    """).splitlines() == ["2", "9", "false"]


def test_legacy_merge_and_clone():
    assert out_of(QUOTE_PRELUDE + """
        weave main into int:
            var a as map of string to string is map of string to string
            calling a.put with "x", "1"
            var b as map of string to string is map of string to string
            calling b.put with "x", "2"
            calling b.put with "y", "3"
            var merged as map of string to string is calling cipher.json_merge with a, b
            var clone as map of string to string is calling cipher.json_deep_clone with merged
            var out as maybe string is calling cipher.stringify_json with clone
            if s as string is out:
                calling spark.println with s
            return 0
    """) == '{"x":2,"y":3}'


def test_typed_map_serializers():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var ints as map of string to int is map of string to int
            calling ints.put with "b", 2
            calling ints.put with "a", 1
            calling spark.println with (calling cipher.stringify_json_map_int with ints)
            var flags as map of string to bool is map of string to bool
            calling flags.put with "z", true
            calling spark.println with (calling cipher.stringify_json_map_bool with flags)
            return 0
    """).splitlines() == ['{"a":1,"b":2}', '{"z":true}']


def test_string_enchantments():
    assert out_of("""
        import std.cipher
        import std.spark
        weave main into int:
            var text as string is "hello"
            calling spark.println with (calling text.to_base64)
            calling spark.println with (calling text.to_hex)
            calling spark.println with (calling text.to_base32)
            calling spark.println with (calling text.to_base58)
            calling spark.println with (calling text.to_crc32_hex)
            return 0
    """).splitlines() == ["aGVsbG8=", "68656c6c6f", "NBSWY3DP", "Cn8eVZg", "3610a686"]


# ---------------------------------------------------------------------------
# Performance regression
# ---------------------------------------------------------------------------

def test_bug_c1_encoding_a_large_input_is_linear():
    """256 KiB must encode in well under the 5 s the quadratic loop needed per 64 KiB.

    2.0.0's encoder re-interpolated its accumulator on every step: 74 KiB took
    3.5 s, so 256 KiB would take roughly a minute.  The fixed encoder allocates
    once and finishes in milliseconds; the bound is deliberately loose so a slow
    runner cannot make this flaky.
    """
    res = run_pengu("""
        import std.spark
        import std.cipher
        import std.chronicle
        weave main into int:
            var parts as list of string is list of string with capacity 16384
            var i as int is 0
            while i < 16384:
                calling parts.push with "0123456789abcdef"
                set i is i + 1
            var data as string is ""
            for p in parts:
                set data is "{data}{p}"
            var t0 as float is calling chronicle.monotonic
            var enc as string is calling cipher.encode_base64 with data
            var t1 as float is calling chronicle.monotonic
            var elapsed as int is ((t1 - t0) * 1000.0) to int
            calling spark.println with "{(enc length)} {elapsed}"
            return 0
    """, timeout=300)
    assert res.returncode == 0, res.stderr
    length, elapsed = res.stdout.split()
    assert int(length) == 349528
    assert int(elapsed) < 5000, f"256 KiB took {elapsed} ms; the encoder is not linear"
