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


def test_f8_hover_definition_symbols_completion_and_diagnostics() -> None:
    p = subprocess.Popen(
        [str(PSC), "lsp", "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=env(),
    )
    assert p.stdin and p.stdout
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}}))
    p.stdin.flush()
    caps = recv(p.stdout)["result"]["capabilities"]
    assert caps["textDocumentSync"] == 1
    assert caps["hoverProvider"] is True

    text = "weave add with a as int, b as int into int:\n    return a + b\n\nweave main into int:\n    return 0\n"
    uri = "file:///tmp/psc-f8-features.pengu"
    p.stdin.write(frame({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {"textDocument": {"uri": uri, "languageId": "pengu", "version": 1, "text": text}},
    }))
    p.stdin.flush()
    diag = recv(p.stdout)
    assert diag["method"] == "textDocument/publishDiagnostics"

    def req(rid: int, method: str, params: dict) -> dict:
        p.stdin.write(frame({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}))
        p.stdin.flush()
        return recv(p.stdout)["result"]

    hover = req(2, "textDocument/hover", {"textDocument": {"uri": uri}, "position": {"line": 0, "character": 7}})
    assert "weave add with" in hover["contents"]["value"]
    definition = req(3, "textDocument/definition", {"textDocument": {"uri": uri}, "position": {"line": 3, "character": 7}})
    assert definition["range"]["start"]["line"] == 3
    symbols = req(4, "textDocument/documentSymbol", {"textDocument": {"uri": uri}})
    assert {s["name"] for s in symbols} == {"add", "main"}
    completions = req(5, "textDocument/completion", {"textDocument": {"uri": uri}, "position": {"line": 4, "character": 4}})
    assert any(c["label"] == "weave" for c in completions)
    assert any(c["label"] == "add" for c in completions)

    p.stdin.write(frame({"jsonrpc": "2.0", "id": 6, "method": "shutdown", "params": None}))
    p.stdin.flush()
    assert recv(p.stdout)["id"] == 6
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "exit"}))
    p.stdin.flush()
    p.stdin.close()
    assert p.wait(timeout=10) == 0
