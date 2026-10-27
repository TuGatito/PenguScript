from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"

pytestmark = pytest.mark.skipif(not PSC.is_file(), reason="psc/build/psc no está construido")


def env() -> dict[str, str]:
    e = os.environ.copy()
    e["PENGU_STD_DIR"] = str(ROOT / "std")
    e["PENGU_LIB_DIR"] = str(ROOT / "build" / "lib")
    e["PENGU_INCLUDE_DIR"] = str(ROOT / "build" / "include")
    return e


def frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode()
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def read_frame(stream) -> dict:
    header = b""
    while b"\r\n\r\n" not in header:
        ch = stream.read(1)
        if not ch:
            raise EOFError("EOF")
        header += ch
    n = int([l for l in header.decode().split("\r\n") if l.startswith("Content-Length")][0].split(":")[1])
    body = stream.read(n)
    return json.loads(body)


def test_f8_stdio_lifecycle_and_didopen() -> None:
    p = subprocess.Popen(
        [str(PSC), "lsp", "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env(), text=False,
    )
    assert p.stdin and p.stdout
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}}))
    p.stdin.flush()
    r = read_frame(p.stdout)
    assert r["id"] == 1
    assert r["result"]["serverInfo"]["name"] == "psc"
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "initialized", "params": {}}))
    p.stdin.write(frame({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {"textDocument": {"uri": "file:///tmp/psc-lsp-test.pengu", "languageId": "pengu",
                                    "version": 1, "text": "weave main into int:\n    return 0\n"}},
    }))
    p.stdin.flush()
    note = read_frame(p.stdout)
    assert note["method"] == "textDocument/publishDiagnostics"
    p.stdin.write(frame({"jsonrpc": "2.0", "id": "s", "method": "shutdown", "params": None}))
    p.stdin.flush()
    r = read_frame(p.stdout)
    assert r["id"] == "s"
    assert r["result"] is None
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "exit"}))
    p.stdin.flush()
    p.stdin.close()
    assert p.wait(timeout=10) == 0


def test_f8_tcp_lifecycle() -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    p = subprocess.Popen(
        [str(PSC), "lsp", "--tcp", "--host=127.0.0.1", f"--port={port}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env(),
    )
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=10)
        s.sendall(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}}))
        header = b""
        while b"\r\n\r\n" not in header:
            header += s.recv(1)
        n = int([l for l in header.decode().split("\r\n") if l.startswith("Content-Length")][0].split(":")[1])
        body = b""
        while len(body) < n:
            body += s.recv(n - len(body))
        assert json.loads(body)["result"]["serverInfo"]["name"] == "psc"
        s.sendall(frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}))
        s.recv(4096)
        s.sendall(frame({"jsonrpc": "2.0", "method": "exit"}))
        s.close()
        assert p.wait(timeout=10) == 0
    finally:
        if p.poll() is None:
            p.kill()
