from __future__ import annotations

import json
import os
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


def frame(o: dict) -> bytes:
    b = json.dumps(o).encode()
    return f"Content-Length: {len(b)}\r\n\r\n".encode() + b


def recv(stream) -> dict:
    h = b""
    while b"\r\n\r\n" not in h:
        c = stream.read(1)
        if not c:
            raise EOFError
        h += c
    n = int([l for l in h.decode().split("\r\n") if l.startswith("Content-Length")][0].split(":")[1])
    return json.loads(stream.read(n))


def test_f8_1000_unchanged_didchange() -> None:
    p = subprocess.Popen(
        [str(PSC), "lsp", "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env(),
    )
    assert p.stdin and p.stdout
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}}))
    p.stdin.flush()
    recv(p.stdout)
    uri = "file:///tmp/psc-f8-stress.pengu"
    text = "weave main into int:\n    return 0\n"
    p.stdin.write(frame({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {"textDocument": {"uri": uri, "languageId": "pengu", "version": 1, "text": text}},
    }))
    p.stdin.flush()
    recv(p.stdout)
    for i in range(1000):
        p.stdin.write(frame({
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {"textDocument": {"uri": uri, "version": i + 2},
                       "contentChanges": [{"text": text}]},
        }))
    p.stdin.flush()
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}))
    p.stdin.flush()
    assert recv(p.stdout)["id"] == 2
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "exit"}))
    p.stdin.flush()
    p.stdin.close()
    assert p.wait(timeout=20) == 0
