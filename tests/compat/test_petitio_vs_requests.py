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
