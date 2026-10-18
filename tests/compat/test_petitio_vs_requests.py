"""``std.petitio`` against a real socket, compared with Python's HTTP clients.

The conformance corpus is offline and the stdlib unit test is offline; this file
is the one place that opens a socket. It starts a throwaway `http.server` on an
ephemeral port and:

1. runs one PenguScript program that performs GET, JSON POST, a redirect
   follow, a 404, cookie persistence and a form POST against it;
2. performs the same requests with `urllib.request` (stdlib, always available);
3. asserts the observable results agree (status, body, final URL);
4. repeats the GET with `requests` when that package is installed — it is not a
   runtime dependency of PenguScript, so the check skips instead of failing on a
   bare checkout.

Transport failures (timeout, connection refused, body cap) are asserted from the
`HttpError` variant the wrapper produces, which is the part Python's exceptions
cannot be compared with directly.
"""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep pytest output clean
        pass

    def _send(self, code: int, body: bytes = b"", headers: dict | None = None):
        self.send_response(code)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        url = urlparse(self.path)
        if url.path == "/get":
            payload = {
                "method": "GET",
                "query": {k: v[0] for k, v in parse_qs(url.query).items()},
                "ua": self.headers.get("User-Agent", ""),
                "x-test": self.headers.get("X-Test", ""),
            }
            self._send(200, json.dumps(payload, sort_keys=True).encode(),
                       {"Content-Type": "application/json"})
        elif url.path == "/redirect":
            self._send(302, b"", {"Location": "/get?from=redirect"})
        elif url.path == "/loop":
            self._send(302, b"", {"Location": "/loop"})
        elif url.path == "/slow":
            time.sleep(1.5)
            self._send(200, b"late")
        elif url.path == "/big":
            self._send(200, b"x" * 4096)
        elif url.path == "/cookie":
            self._send(200, b"set", {"Set-Cookie": "sid=abc123; Path=/"})
        elif url.path == "/expire":
            self.send_response(200)
            self.send_header("Set-Cookie", "gone=x; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
            self.send_header("Set-Cookie", "stay=y; Max-Age=3600; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
        elif url.path.startswith("/bytes/"):
            try:
                count = int(url.path.rsplit("/", 1)[1])
            except ValueError:
                count = 0
            self._send(200, b"z" * count)
        elif url.path == "/echo-cookie":
            self._send(200, self.headers.get("Cookie", "").encode())
        else:
            self._send(404, b"nope")

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        url = urlparse(self.path)
        if url.path == "/post":
            payload = {
                "len": len(body),
                "body": body.decode("utf-8", "replace"),
                "type": self.headers.get("Content-Type", ""),
                "auth": self.headers.get("Authorization", ""),
            }
            self._send(200, json.dumps(payload, sort_keys=True).encode(),
                       {"Content-Type": "application/json"})
        else:
            self._send(404, b"nope")

    do_PUT = do_POST  # noqa: N815
    do_PATCH = do_POST  # noqa: N815


@pytest.fixture(scope="module")
def http_base():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _closed_port() -> int:
    """A port nothing listens on (bound then released)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _program(base: str, dead_port: int) -> str:
    return f'''
import std.json
import std.petitio
import std.spark

weave main into int:
    # GET with a header: the server echoes the request in a JSON body.
    var req as Request is calling Request.new with "GET", "{base}/get?a=1"
    calling req.header with "X-Test", "petitio"
    var r1 as result of Response to HttpError is calling req.send
    if not r1.is_ok:
        calling spark.println with "FAIL get"
        return 1
    var resp1 as Response is calling petitio.take_response with (sigil of r1)
    calling spark.println with "GET status={{resp1.status}}"
    calling spark.println with "GET body={{resp1.body}}"
    banish resp1
    banish r1
    banish req

    # JSON POST: the server reports length, body and content type.
    var payload as result of json.JsonValue to json.JsonError is calling json.parse with r"""{{"name":"pengu"}}"""
    var obj as json.JsonValue is payload.value
    var r2 as result of Response to HttpError is calling petitio.post_json with "{base}/post", obj
    if not r2.is_ok:
        calling spark.println with "FAIL post"
        return 2
    var resp2 as Response is calling petitio.take_response with (sigil of r2)
    calling spark.println with "POST status={{resp2.status}}"
    calling spark.println with "POST body={{resp2.body}}"
    banish resp2
    banish r2
    banish payload

    # Redirect: followed by default; the final URL is the target.
    var r3 as result of Response to HttpError is calling petitio.get with "{base}/redirect"
    if not r3.is_ok:
        calling spark.println with "FAIL redirect"
        return 3
    var resp3 as Response is calling petitio.take_response with (sigil of r3)
    calling spark.println with "REDIRECT status={{resp3.status}}"
    calling spark.println with "REDIRECT followed={{resp3.redirected}}"
    calling spark.println with "REDIRECT body={{resp3.body}}"
    banish resp3
    banish r3

    # 404: raise_for_status reports HttpStatus 404.
    var r4 as result of Response to HttpError is calling petitio.get with "{base}/missing"
    if not r4.is_ok:
        calling spark.println with "FAIL 404 transport"
        return 4
    var resp4 as Response is calling petitio.take_response with (sigil of r4)
    calling spark.println with "404 status={{resp4.status}}"
    var raised as result of void to HttpError is calling resp4.raise_for_status
    if raised.is_ok:
        calling spark.println with "FAIL 404 raise_for_status"
    else:
        var e4 as HttpError is calling petitio.take_error with (sigil of raised)
        judge e4:
            when HttpStatus with status ->
                calling spark.println with "404 raised={{status}}"
            else ->
                calling spark.println with "FAIL 404 variant"
        banish e4
    banish raised
    banish resp4
    banish r4

    # Session cookies: the second request carries the first one's cookie.
    var session as Session is calling Session.new
    var r5 as result of Response to HttpError is calling session.get with "{base}/cookie"
    if r5.is_ok:
        var resp5 as Response is calling petitio.take_response with (sigil of r5)
        banish resp5
    banish r5
    var r6 as result of Response to HttpError is calling session.get with "{base}/echo-cookie"
    if r6.is_ok:
        var resp6 as Response is calling petitio.take_response with (sigil of r6)
        calling spark.println with "COOKIE body={{resp6.body}}"
        banish resp6
    banish r6
    banish session

    # Form body.
    var fields as map of string to string is map of string to string
    calling fields.put with "a", "1 2"
    calling fields.put with "b", "x&y"
    var r7 as result of Response to HttpError is calling petitio.post_form with "{base}/post", fields
    if r7.is_ok:
        var resp7 as Response is calling petitio.take_response with (sigil of r7)
        calling spark.println with "FORM body={{resp7.body}}"
        banish resp7
    banish r7
    banish fields

    # Transport failures.
    var slow as Request is calling Request.new with "GET", "{base}/slow"
    calling slow.timeout with 0.3
    var r8 as result of Response to HttpError is calling slow.send
    if r8.is_ok:
        calling spark.println with "FAIL timeout"
        banish r8
    else:
        var e8 as HttpError is calling petitio.take_error with (sigil of r8)
        judge e8:
            when Timeout with seconds ->
                calling spark.println with "FAILS timeout"
            else ->
                calling spark.println with "FAIL timeout variant"
        banish e8
        banish r8
    banish slow

    var refused as result of Response to HttpError is calling petitio.get with "http://127.0.0.1:{dead_port}/x"
    if refused.is_ok:
        calling spark.println with "FAIL refused"
        banish refused
    else:
        var e9 as HttpError is calling petitio.take_error with (sigil of refused)
        judge e9:
            when ConnectionFailed with reason ->
                calling spark.println with "FAILS connection"
            else ->
                calling spark.println with "FAIL refused variant"
        banish e9
        banish refused

    var capped as Request is calling Request.new with "GET", "{base}/big"
    calling capped.max_body_bytes with 100
    var r10 as result of Response to HttpError is calling capped.send
    if r10.is_ok:
        calling spark.println with "FAIL cap"
        banish r10
    else:
        var e10 as HttpError is calling petitio.take_error with (sigil of r10)
        judge e10:
            when BodyTooLarge with max_bytes ->
                calling spark.println with "FAILS cap"
            else ->
                calling spark.println with "FAIL cap variant"
        banish e10
        banish r10
    banish capped

    calling spark.println with "DONE"
    return 0
'''


def _parse(output: str) -> dict[str, str]:
    found = {}
    for line in output.splitlines():
        if "=" in line and not line.startswith(" "):
            key, _, value = line.partition("=")
            found[key.strip()] = value.strip()
    return found


def test_petitio_matches_urllib(compile_and_run, http_base):
    out = compile_and_run(_program(http_base, _closed_port()), timeout=300)
    assert "DONE" in out, out
    assert "FAIL " not in out, out
    assert "FAILS timeout" in out, out
    assert "FAILS connection" in out, out
    assert "FAILS cap" in out, out
    seen = _parse(out)

    # urllib reference for the same GET.
    with urllib.request.urlopen(f"{http_base}/get?a=1", timeout=10) as response:
        reference = json.loads(response.read())
        assert seen["GET status"] == str(response.status)
    get_body = json.loads(seen["GET body"])
    assert get_body["query"] == {"a": "1"}
    assert get_body["x-test"] == "petitio"
    assert get_body["ua"] == "petitio/2.12.0"
    assert reference["query"] == {"a": "1"}

    # JSON POST.
    body = json.dumps({"name": "pengu"}).encode()
    request = urllib.request.Request(
        f"{http_base}/post", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        reference = json.loads(response.read())
        assert seen["POST status"] == str(response.status)
    post_body = json.loads(seen["POST body"])
    assert post_body["body"] == json.dumps({"name": "pengu"}, separators=(",", ":"))
    assert post_body["type"] == "application/json"
    assert reference["len"] == len(body)

    # Redirect.
    with urllib.request.urlopen(f"{http_base}/redirect", timeout=10) as response:
        assert seen["REDIRECT status"] == str(response.status)
    assert seen["REDIRECT followed"] == "true"
    redirect_body = json.loads(seen["REDIRECT body"])
    assert redirect_body["query"] == {"from": "redirect"}

    # 404.
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(f"{http_base}/missing", timeout=10)
    assert seen["404 status"] == str(excinfo.value.code)
    assert seen["404 raised"] == str(excinfo.value.code)

    # Form encoding round-trips through the server's parser.
    form_body = json.loads(seen["FORM body"])
    assert form_body["body"] == "a=1%202&b=x%26y"
    assert form_body["type"] == "application/x-www-form-urlencoded"

    # Cookie persistence: the second request carries `sid=abc123`.
    assert "sid=abc123" in seen["COOKIE body"]


def test_requests_package_matches_when_installed(http_base):
    """Compare with `requests` when it is available (not a dependency)."""
    requests = pytest.importorskip("requests", reason="requests is not installed")
    with requests.get(f"{http_base}/get?q=1", timeout=10) as response:
        assert response.status_code == 200
        assert response.json()["query"] == {"q": "1"}
        assert response.headers["content-type"] == "application/json"


def test_net_error_messages_name_the_failure(compile_and_run, http_base):
    program = f'''
import std.petitio
import std.scrolls
import std.spark

weave main into int:
    var refused as result of Response to HttpError is calling petitio.get with "http://127.0.0.1:{_closed_port()}/x"
    if refused.is_ok:
        calling spark.println with "FAIL"
        return 1
    var e as HttpError is calling petitio.take_error with (sigil of refused)
    var msg as string is calling e.message
    if not (calling scrolls.starts_with with msg, "connection failed: "):
        calling spark.println with "FAIL wrong message: {{msg}}"
    banish msg
    banish e
    banish refused
    calling spark.println with "DONE"
    return 0
'''
    out = compile_and_run(program, timeout=300)
    assert "DONE" in out, out
    assert "FAIL" not in out, out


# ---------------------------------------------------------------------------
# Cookie expiry, streaming and fetch_many against the local server
# ---------------------------------------------------------------------------

def test_cookie_expiry_and_max_age_priority(compile_and_run, http_base):
    program = f'''
import std.petitio
import std.spark

weave main into int:
    var r as result of Response to HttpError is calling petitio.get with "{http_base}/expire"
    if not r.is_ok:
        calling spark.println with "FAIL transport"
        return 1
    var resp as Response is calling petitio.take_response with (sigil of r)
    calling spark.println with "count={{calling resp.cookies.len}}"
    calling spark.println with "gone={{calling resp.cookies.contains with \"gone\"}}"
    calling spark.println with "stay={{calling resp.cookies.contains with \"stay\"}}"
    calling spark.println with "cleared={{resp.cleared_cookies.len}}"
    banish resp
    banish r
    return 0
'''
    out = compile_and_run(program, timeout=300)
    assert "FAIL" not in out, out
    assert "count=1" in out, out
    assert "gone=false" in out, out
    assert "stay=true" in out, out
    assert "cleared=1" in out, out


def test_streaming_to_file_and_callback(compile_and_run, http_base, tmp_path):
    target = tmp_path / "stream.bin"
    program = f'''
import std.archivum
import std.petitio
import std.spark

rune Counter:
    chunks as int
    bytes as i64

weave count_chunk with chunk as string, user as ref to void into bool:
    var counter as ref to Counter is transmute user to ref to Counter
    set counter->chunks is counter->chunks + 1
    set counter->bytes is counter->bytes + (chunk length to i64)
    return true

weave main into int:
    var file_req as Request is calling Request.new with "GET", "{http_base}/bytes/10000"
    var file_result as result of Response to HttpError is calling file_req.send_to_file with "{target}"
    if not file_result.is_ok:
        calling spark.println with "FAIL file"
        return 1
    var file_resp as Response is calling petitio.take_response with (sigil of file_result)
    calling spark.println with "written={{file_resp.bytes_written}}"
    calling spark.println with "body_len={{file_resp.body length}}"
    banish file_resp
    banish file_result
    banish file_req

    var stream_req as Request is calling Request.new with "GET", "{http_base}/bytes/5000"
    var counter as Counter is with chunks is 0, bytes is 0
    var stream_result as result of Response to HttpError is calling stream_req.send_stream with count_chunk, (sigil of counter)
    if not stream_result.is_ok:
        calling spark.println with "FAIL stream"
        return 2
    var stream_resp as Response is calling petitio.take_response with (sigil of stream_result)
    calling spark.println with "chunks={{counter.chunks}}"
    calling spark.println with "callback_bytes={{counter.bytes}}"
    calling spark.println with "stream_written={{stream_resp.bytes_written}}"
    banish stream_resp
    banish stream_result
    banish stream_req
    return 0
'''
    out = compile_and_run(program, timeout=300)
    assert "FAIL" not in out, out
    assert "written=10000" in out, out
    assert "body_len=0" in out, out
    assert target.read_bytes() == b"z" * 10000
    assert "callback_bytes=5000" in out, out
    assert "stream_written=5000" in out, out


def test_fetch_many_order_and_errors(compile_and_run, http_base):
    dead = _closed_port()
    program = f'''
import std.petitio
import std.spark

weave main into int:
    var reqs as list of Request is list of Request
    calling reqs.push with (calling Request.new with "GET", "{http_base}/get?i=0")
    calling reqs.push with (calling Request.new with "GET", "http://127.0.0.1:{dead}/x")
    calling reqs.push with (calling Request.new with "GET", "{http_base}/get?i=2")
    var results as list of result of Response to HttpError is calling petitio.fetch_many with reqs
    calling spark.println with "count={{results.len}}"
    var i as int is 0
    while i < results.len:
        var r as result of Response to HttpError is results at i
        if r.is_ok:
            var resp as Response is calling petitio.take_response with (sigil of r)
            calling spark.println with "{{i}}=ok {{resp.status}}"
            banish resp
        else:
            var failure as HttpError is calling petitio.take_error with (sigil of r)
            judge failure:
                when ConnectionFailed with reason -> calling spark.println with "{{i}}=connection"
                else -> calling spark.println with "{{i}}=other"
            banish failure
        banish r
        set i is i + 1
    banish results
    banish reqs
    return 0
'''
    out = compile_and_run(program, timeout=300)
    assert "count=3" in out, out
    assert "0=ok 200" in out, out
    assert "1=connection" in out, out
    assert "2=ok 200" in out, out


# ---------------------------------------------------------------------------
# Live tests: real services, opt-in with PETITIO_LIVE=1
# ---------------------------------------------------------------------------
#
# They are skipped by default so the suite stays deterministic and offline.
# Each program is retried up to three times: public test services occasionally
# time out, and a flaky network is not a petitio bug.

import os

_LIVE = os.environ.get("PETITIO_LIVE") == "1"
_live = pytest.mark.skipif(
    not _LIVE, reason="set PETITIO_LIVE=1 to run the live HTTP tests")


def _run_live(compile_and_run, source: str, attempts: int = 3) -> str:
    last = None
    for _ in range(attempts):
        last = compile_and_run(source, timeout=300)
        if "FAIL" not in last:
            return last
    return last or ""


@_live
def test_live_httpbin_behaviour(compile_and_run):
    program = '''
import std.json
import std.petitio
import std.spark

weave main into int:
    # A three-hop redirect is followed and reported.
    var redirect as result of Response to HttpError is calling petitio.get with "https://httpbin.org/redirect/3"
    if redirect.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of redirect)
        calling spark.println with "redirect_status={resp.status}"
        calling spark.println with "redirect_followed={resp.redirected}"
        banish resp
    else:
        calling spark.println with "redirect=transport-error"
    banish redirect

    # no_redirects surfaces the 302 itself.
    var raw_req as Request is calling Request.new with "GET", "https://httpbin.org/redirect/3"
    calling raw_req.no_redirects
    var raw as result of Response to HttpError is calling raw_req.send
    if raw.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of raw)
        calling spark.println with "raw_status={resp.status}"
        calling spark.println with "raw_is_redirect={calling resp.is_redirect}"
        banish resp
    else:
        calling spark.println with "raw=transport-error"
    banish raw
    banish raw_req

    # A 418 keeps its status and classification.
    var teapot as result of Response to HttpError is calling petitio.get with "https://httpbin.org/status/418"
    if teapot.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of teapot)
        calling spark.println with "teapot_status={resp.status}"
        calling spark.println with "teapot_client_error={calling resp.is_client_error}"
        banish resp
    else:
        calling spark.println with "teapot=transport-error"
    banish teapot

    # The server-set cookie is visible on the response. `cookies/set` answers a
    # 302 that carries the Set-Cookie, so the redirect is not followed here: the
    # final response of a followed chain does not repeat it.
    var cookie_req as Request is calling Request.new with "GET", "https://httpbin.org/cookies/set?theme=dark"
    calling cookie_req.no_redirects
    var cookie as result of Response to HttpError is calling cookie_req.send
    if cookie.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of cookie)
        calling spark.println with "cookie_status={resp.status}"
        if calling resp.cookies.contains with "theme":
            var value as string is calling resp.cookies.get with "theme"
            calling spark.println with "cookie_theme={value}"
        banish resp
    else:
        calling spark.println with "cookie=transport-error"
    banish cookie
    banish cookie_req

    # A real JSON API.
    var api as result of Response to HttpError is calling petitio.get with "https://jsonplaceholder.typicode.com/posts/1"
    if api.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of api)
        var parsed as result of json.JsonValue to json.JsonError is calling resp.json
        if parsed.is_ok:
            var root as json.JsonValue is parsed.value
            var id as maybe json.JsonValue is calling root.get with "id"
            if id.is_present:
                var idv as json.JsonValue is id.value
                var as_int as maybe i64 is calling idv.as_int
                if as_int.is_present:
                    calling spark.println with "json_id={as_int.value}"
                banish as_int
                banish idv
            banish id
        banish parsed
        banish resp
    else:
        calling spark.println with "json=transport-error"
    banish api

    # Digest authentication answers the 401 challenge.
    var digest_req as Request is calling Request.new with "GET", "https://httpbin.org/digest-auth/auth/pengu/script/sha-256"
    calling digest_req.auth_digest with "pengu", "script"
    var digest as result of Response to HttpError is calling digest_req.send
    if digest.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of digest)
        calling spark.println with "digest_status={resp.status}"
        banish resp
    else:
        calling spark.println with "digest=transport-error"
    banish digest
    banish digest_req

    # A 1-second deadline aborts a 10-second delay.
    var slow_req as Request is calling Request.new with "GET", "https://httpbin.org/delay/10"
    calling slow_req.timeout with 1.0
    var slow as result of Response to HttpError is calling slow_req.send
    if slow.is_ok:
        calling spark.println with "timeout=no"
        banish slow
    else:
        var failure as HttpError is calling petitio.take_error with (sigil of slow)
        judge failure:
            when Timeout with seconds -> calling spark.println with "timeout=yes"
            else -> calling spark.println with "timeout=other-error"
        banish failure
        banish slow
    banish slow_req
    return 0
'''
    out = _run_live(compile_and_run, program)
    assert "redirect_status=200" in out, out
    assert "redirect_followed=true" in out, out
    assert "raw_status=302" in out, out
    assert "raw_is_redirect=true" in out, out
    assert "teapot_status=418" in out, out
    assert "teapot_client_error=true" in out, out
    assert "cookie_status=302" in out, out
    assert "cookie_theme=dark" in out, out
    assert "json_id=1" in out, out
    assert "digest_status=200" in out, out
    assert "timeout=yes" in out, out


@_live
def test_live_tls_http2_streaming_and_parallel(compile_and_run, tmp_path):
    target = tmp_path / "live_stream.bin"
    program = f'''
import std.archivum
import std.chronicle
import std.petitio
import std.spark

weave main into int:
    # HTTP/2 is negotiated with a server that speaks it.
    var h2_req as Request is calling Request.new with "GET", "https://www.google.com/"
    calling h2_req.http_version with HttpVersion.Http2
    calling h2_req.timeout with 20.0
    var h2 as result of Response to HttpError is calling h2_req.send
    if h2.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of h2)
        calling spark.println with "h2_status={{resp.status}}"
        judge resp.http_version:
            when Http2 -> calling spark.println with "h2_protocol=2"
            else -> calling spark.println with "h2_protocol=other"
        banish resp
    else:
        calling spark.println with "h2=transport-error"
    banish h2
    banish h2_req

    # An expired certificate is a TLS error.
    var expired as result of Response to HttpError is calling petitio.get with "https://expired.badssl.com/"
    if expired.is_ok:
        calling spark.println with "expired=accepted"
        banish expired
    else:
        var failure as HttpError is calling petitio.take_error with (sigil of expired)
        judge failure:
            when TlsError with reason -> calling spark.println with "expired=tls-error"
            else -> calling spark.println with "expired=other-error"
        banish failure
        banish expired

    # The same self-signed endpoint works with verification disabled.
    var insecure_req as Request is calling Request.new with "GET", "https://self-signed.badssl.com/"
    calling insecure_req.insecure
    var insecure as result of Response to HttpError is calling insecure_req.send
    if insecure.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of insecure)
        calling spark.println with "insecure_status={{resp.status}}"
        banish resp
    else:
        calling spark.println with "insecure=transport-error"
    banish insecure
    banish insecure_req

    # A binary body streams to disk byte for byte.
    var file_req as Request is calling Request.new with "GET", "https://httpbin.org/stream-bytes/10240"
    var file_result as result of Response to HttpError is calling file_req.send_to_file with "{target}"
    if file_result.is_ok:
        var resp as Response is calling petitio.take_response with (sigil of file_result)
        calling spark.println with "stream_written={{resp.bytes_written}}"
        banish resp
    else:
        calling spark.println with "stream=transport-error"
    banish file_result
    banish file_req
    var size as maybe int is calling archivum.file_size with "{target}"
    if size.is_present:
        calling spark.println with "stream_file={{size.value}}"
    banish size

    # Three one-second transfers in parallel finish well under the serial sum.
    var reqs as list of Request is list of Request
    calling reqs.push with (calling Request.new with "GET", "https://httpbin.org/delay/1")
    calling reqs.push with (calling Request.new with "GET", "https://httpbin.org/delay/1")
    calling reqs.push with (calling Request.new with "GET", "https://httpbin.org/delay/1")
    var watch as chronicle.Stopwatch is calling chronicle.new_stopwatch
    var results as list of result of Response to HttpError is calling petitio.fetch_many with reqs
    var elapsed as float is calling watch.elapsed_sec
    var ok as int is 0
    var i as int is 0
    while i < results.len:
        var r as result of Response to HttpError is results at i
        if r.is_ok:
            var resp as Response is calling petitio.take_response with (sigil of r)
            set ok is ok + 1
            banish resp
        banish r
        set i is i + 1
    calling spark.println with "many_ok={{ok}}"
    calling spark.println with "many_elapsed={{elapsed}}"
    banish results
    banish reqs
    return 0
'''
    out = _run_live(compile_and_run, program)
    assert "h2_status=200" in out, out
    assert "h2_protocol=2" in out, out
    assert "expired=tls-error" in out, out
    assert "insecure_status=200" in out, out
    assert "stream_written=10240" in out, out
    assert "stream_file=10240" in out, out
    assert "many_ok=3" in out, out
    assert "many_elapsed=0." in out or "many_elapsed=1." in out, out
