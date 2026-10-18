"""End-to-end tests for ``std.petitio`` (the libcurl HTTP client).

Two layers:

* `test_offline_contracts` compiles one program that exercises the whole
  network-free surface: URL codec, `parse_url`, request builders, response
  queries, the error model and the explicit `take_*` moves.
* `test_error_model_matches_the_c_bridge` is a Python-only guard that the
  `HttpError` variants stay in lockstep with ``enum petitio_error`` in
  ``std_c/petitio.h``: the wrapper maps integer codes to variants by position,
  so a reordered enum would silently mislabel every transport failure.

The live-socket behaviour (status, headers, redirects, cookies, timeouts) is
covered against a real local server in
``tests/compat/test_petitio_vs_requests.py``; keeping the socket out of this
file makes the offline half fast and deterministic.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_PROGRAM = r'''
import std.json
import std.petitio
import std.spark
import std.scrolls

weave eq_s with got as string, want as string, name as string into void:
    if (calling scrolls.compare with got, want) != 0:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave make_response with status as int into Response:
    var headers as map of string to string is map of string to string
    calling headers.put with "content-type", "application/json"
    var cookies as map of string to string is map of string to string
    var cleared as list of string is list of string
    var response as Response is:
        status is status
        headers is headers
        body is r"""{"ok":true}"""
        url is "https://example.com/"
        elapsed_sec is 0.1
        bytes_written is 0
        http_version is HttpVersion.Http11
        redirected is false
        cookies is cookies
        cleared_cookies is cleared
    return response

weave main into int:
    # URL codec
    var enc as string is calling petitio.url_encode with "a b&ñ"
    calling eq_s with enc, "a%20b%26%C3%B1", "encode"
    var dec as string is calling petitio.url_decode with enc
    calling eq_s with dec, "a b&ñ", "decode round trip"
    banish dec
    banish enc
    var params as map of string to string is map of string to string
    calling params.put with "z", "1"
    calling params.put with "a", "2 3"
    var qs as string is calling petitio.build_query_string with params
    calling eq_s with qs, "a=2%203&z=1", "query sorted and encoded"
    banish qs
    var url2 as string is calling petitio.with_query with "https://h/p", params
    calling eq_s with url2, "https://h/p?a=2%203&z=1", "with_query"
    banish url2
    banish params

    # parse_url
    var parsed as result of UrlParts to string is calling petitio.parse_url with "https://u:p@h:99/a?b=1#c"
    if not parsed.is_ok:
        calling spark.println with "FAIL parse_url"
        return 1
    var parts as UrlParts is parsed.value
    calling eq_s with parts.scheme, "https", "scheme"
    calling eq_s with parts.userinfo, "u:p", "userinfo"
    calling eq_s with parts.host, "h", "host"
    calling eq_i with parts.port, 99, "port"
    calling eq_s with parts.path, "/a", "path"
    calling eq_s with parts.query, "b=1", "query"
    calling eq_s with parts.fragment, "c", "fragment"
    banish parsed
    var bad as result of UrlParts to string is calling petitio.parse_url with "nope"
    if bad.is_ok:
        calling spark.println with "FAIL bad url accepted"
    banish bad

    # Request defaults and builders
    var req as Request is calling Request.new with "post", "https://example.com/x"
    defer banish req
    calling eq_s with req.method, "POST", "method upper-cased"
    calling eq_b with req.follow_redirects, true, "follow redirects"
    calling eq_i with req.max_redirects, 30, "max redirects"
    calling eq_b with req.verify_tls, true, "verify tls"
    calling req.header with "X-Test", "1"
    calling req.header with "x-test", "2"
    calling eq_i with req.headers.len, 1, "header replacement is CI"
    calling eq_b with (calling req.has_header with "X-TEST"), true, "has_header CI"
    var removed as bool is calling req.remove_header with "x-test"
    calling eq_b with removed, true, "remove_header"

    var payload as result of json.JsonValue to json.JsonError is calling json.parse with r"""{"n":1}"""
    if not payload.is_ok:
        calling spark.println with "FAIL json fixture"
        return 1
    var obj as json.JsonValue is payload.value
    calling req.json_body with obj
    calling eq_s with req.body, r"""{"n":1}""", "json body"
    var ctype as string is calling req.headers.get with "content-type"
    calling eq_s with ctype, "application/json", "json type"
    banish payload

    calling req.auth_basic with "u", "p"
    calling req.auth_bearer with "t"
    calling req.proxy with "http://127.0.0.1:1", ""
    calling req.timeout with 1.5
    calling req.connect_timeout with 0.25
    calling req.no_redirects
    calling req.insecure
    calling req.max_body_bytes with 2048
    calling eq_s with req.basic_user, "u", "basic user"
    calling eq_s with req.bearer_token, "t", "bearer"
    calling eq_b with req.verify_tls, false, "insecure"
    calling eq_i with (req.max_body_bytes to int), 2048, "cap"
    calling req.multipart_field with "field", "v"
    calling eq_i with req.parts.len, 1, "multipart part"

    # Protocol version + authentication modes.
    judge req.http_version:
        when Http11 -> calling spark.println with "version=Http11"
        else -> calling spark.println with "FAIL default version"
    calling req.http_version with HttpVersion.Http2
    judge req.http_version:
        when Http2 -> calling spark.println with "version=Http2"
        else -> calling spark.println with "FAIL Http2"
    calling req.auth_digest with "u", "p"
    judge req.auth_mode:
        when DigestAuth -> calling spark.println with "auth=DigestAuth"
        else -> calling spark.println with "FAIL digest mode"
    calling req.socks_proxy with "127.0.0.1:1080", ""
    calling eq_s with req.proxy, "socks5h://127.0.0.1:1080", "socks proxy"

    # fetch_many on an empty list is a valid no-op.
    var no_requests as list of Request is list of Request
    var no_results as list of result of Response to HttpError is calling petitio.fetch_many with no_requests
    calling eq_i with no_results.len, 0, "empty batch"
    banish no_results
    banish no_requests

    # Response queries + errors
    var ok_resp as Response is calling make_response with 200
    defer banish ok_resp
    calling eq_b with (calling ok_resp.is_ok), true, "200 ok"
    var found as string is calling ok_resp.header with "Content-Type"
    calling eq_s with found, "application/json", "response header CI"
    banish found
    var text as string is calling ok_resp.text
    calling eq_s with text, r"""{"ok":true}""", "response text"
    banish text
    calling eq_i with (ok_resp.bytes_written to int), 0, "hand-built bytes_written"

    var e as HttpError is with TooManyRedirects is 4
    var msg as string is calling e.message
    calling eq_s with msg, "too many redirects (limit 4)", "error message"
    banish msg
    banish e

    # Explicit moves
    var box as result of Response to HttpError is calling ok_of with (calling make_response with 201)
    var moved as Response is calling petitio.take_response with (sigil of box)
    calling eq_i with moved.status, 201, "take_response"
    banish box
    banish moved

    var err_box as result of Response to HttpError is calling err_of with (with Timeout is 2.0)
    var moved_err as HttpError is calling petitio.take_error with (sigil of err_box)
    calling eq_s with (calling moved_err.message), "request timed out after 2s", "take_error"
    banish moved_err
    banish err_box

    calling spark.println with "DONE"
    return 0
'''


def test_offline_contracts(compile_and_run):
    out = compile_and_run(_PROGRAM)
    assert "DONE" in out, out
    assert "FAIL" not in out, out


def _c_enum_variants() -> list[str]:
    header = (ROOT / "std_c" / "petitio.h").read_text(encoding="utf-8")
    body = re.search(r"typedef enum petitio_error\s*\{(.*?)\}", header, re.S)
    assert body, "enum petitio_error not found in std_c/petitio.h"
    names = re.findall(r"\b(PETITIO_[A-Z_]+)\s*=", body.group(1))
    assert names, "enum petitio_error has no values"
    return names


def _wrapper_variants() -> list[str]:
    source = (ROOT / "std" / "petitio.pengu").read_text(encoding="utf-8")
    body = re.search(r"omen HttpError derive Nexus:\n(.*?)\n\n", source, re.S)
    assert body, "omen HttpError not found in std/petitio.pengu"
    return re.findall(r"^    ([A-Z][A-Za-z0-9]*)\b", body.group(1), re.M)


def test_error_model_matches_the_c_bridge():
    """The wrapper maps C error codes to variants by *position*.

    ``_error_from_code`` compares the integer code with literals, and the first
    nine variants must line up with ``enum petitio_error`` for those codes to
    mean what the C bridge says. A reordered enum or variant list would turn a
    timeout into a TLS error without any compile-time complaint.
    """
    c_names = _c_enum_variants()
    wrapper = _wrapper_variants()
    # PETITIO_OK is the success code and has no error variant.
    expected = ["ConnectionFailed", "Timeout", "TooManyRedirects", "InvalidUrl",
                "TlsError", "ProtocolError", "BodyTooLarge", "OutOfMemory",
                "Unsupported", "IoError", "Cancelled"]
    assert [n for n in c_names if n != "PETITIO_OK"] == [
        "PETITIO_CONNECTION_FAILED", "PETITIO_TIMEOUT", "PETITIO_TOO_MANY_REDIRECTS",
        "PETITIO_INVALID_URL", "PETITIO_TLS_ERROR", "PETITIO_PROTOCOL_ERROR",
        "PETITIO_BODY_TOO_LARGE", "PETITIO_OUT_OF_MEMORY", "PETITIO_UNSUPPORTED",
        "PETITIO_IO_ERROR", "PETITIO_CANCELLED",
    ]
    assert wrapper[:len(expected)] == expected, wrapper
    assert len(wrapper) == len(expected) + 1 and wrapper[-1] == "HttpStatus"


def test_module_self_tests(has_cc):
    """`pengu test --entry std/petitio.pengu`: every in-module block passes.

    The module tests exercise the private helpers (cookie parsing, URL codec,
    the take_* ownership contract) that the compiled-program tests above cannot
    reach from outside the module.
    """
    import subprocess
    import sys

    if not has_cc:
        pytest.skip("no C compiler available")
    if not (ROOT / "build" / "lib" / "libpengu_runtime.a").is_file():
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "petitio.pengu")],
        capture_output=True, text=True, timeout=900,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    assert "All " in res.stdout or "passed" in res.stdout, res.stdout
    assert "[PANIC]" not in res.stdout + res.stderr, res.stdout + res.stderr


def test_cookie_files_round_trip(compile_and_run, tmp_path):
    target = tmp_path / "cookies.txt"
    program = f'''
import std.petitio
import std.spark

weave main into int:
    var session as Session is calling Session.new
    calling session.set_cookie with "sid", "abc"
    calling session.set_cookie with "theme", "dark"
    var saved as result of void to HttpError is calling session.save_cookies_to_file with "{target}"
    if not saved.is_ok:
        calling spark.println with "FAIL save"
        return 1
    banish saved
    var other as Session is calling Session.new
    var loaded as result of int to HttpError is calling other.load_cookies_from_file with "{target}"
    if not loaded.is_ok:
        calling spark.println with "FAIL load"
        return 2
    calling spark.println with "loaded={{loaded.value}}"
    banish loaded
    var sid as string is calling other.cookie with "sid"
    calling spark.println with "sid={{sid}}"
    banish sid
    var missing as string is calling other.cookie with "absent"
    calling spark.println with "missing_len={{missing length}}"
    banish missing
    banish other
    banish session
    return 0
'''
    out = compile_and_run(program)
    assert "FAIL" not in out, out
    assert "loaded=2" in out, out
    assert "sid=abc" in out, out
    assert "missing_len=0" in out, out
    assert target.is_file()
