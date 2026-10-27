from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"

pytestmark = pytest.mark.skipif(
    not PSC.is_file()
    or subprocess.run([sys.executable, "-c", "import pengu_lsp"], cwd=ROOT).returncode != 0,
    reason="psc o pengu_lsp no disponibles",
)


def frame(o: dict) -> bytes:
    b = json.dumps(o).encode()
    return f"Content-Length: {len(b)}\r\n\r\n".encode() + b


def readf(p: subprocess.Popen) -> dict:
    assert p.stdout is not None
    h = b""
    while b"\r\n\r\n" not in h:
        c = p.stdout.read(1)
        if not c:
            raise EOFError
        h += c
    n = int([l for l in h.decode().split("\r\n") if l.startswith("Content-Length")][0].split(":")[1].strip())
    return json.loads(p.stdout.read(n))


def probe(cmd: list[str]) -> dict:
    env = os.environ.copy()
    env.update(PENGU_STD_DIR=str(ROOT / "std"), PENGU_LIB_DIR=str(ROOT / "build" / "lib"),
               PENGU_INCLUDE_DIR=str(ROOT / "build" / "include"))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    assert p.stdin
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                         "params": {"processId": None, "rootUri": "file:///tmp/f6demo", "capabilities": {}}}))
    p.stdin.flush()
    readf(p)
    text = "weave main into int:\n    var x as int is\n"
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "initialized", "params": {}}))
    p.stdin.write(frame({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
        "textDocument": {"uri": "file:///tmp/psc-f8-parity.pengu", "languageId": "pengu", "version": 1, "text": text},
    }}))
    p.stdin.flush()
    diag = readf(p)
    p.stdin.write(frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}))
    p.stdin.flush()
    p.stdin.close()
    p.wait(timeout=10)
    return diag["params"]["diagnostics"][0]


def test_f8_diagnostics_parity_with_python_lsp() -> None:
    py = probe([sys.executable, "-m", "pengu_lsp", "--stdio"])
    ps = probe([str(PSC), "lsp", "--stdio"])
    assert py["code"] == ps["code"]
    assert py["severity"] == ps["severity"]
    assert py["range"]["start"] == ps["range"]["start"]
