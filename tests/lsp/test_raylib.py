#!/usr/bin/env python3
"""Optional LSP regression tests against a raylib-pengu checkout.

Set RAYLIB_PENGU to the checkout (default: ../raylib-pengu next to this repo).
The test is skipped when the corpus is not present, so CI without the binding
repository still passes.
"""
from __future__ import annotations

import json
import os
import pathlib
import select
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PSC = pathlib.Path(os.environ.get("PSC", ROOT / "build" / "psc"))
RAYLIB = pathlib.Path(os.environ.get("RAYLIB_PENGU", ROOT.parent / "raylib-pengu"))


def frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode()
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


class Client:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [str(PSC), "lsp", "--stdio"],
            cwd=str(RAYLIB),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.next_id = 1
        self.buffer = b""

    def send(self, obj: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(frame(obj))
        self.proc.stdin.flush()

    def read(self, timeout: float = 20.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if b"\r\n\r\n" in self.buffer:
                head, rest = self.buffer.split(b"\r\n\r\n", 1)
                length = None
                for line in head.split(b"\r\n"):
                    if line.lower().startswith(b"content-length:"):
                        length = int(line.split(b":", 1)[1])
                if length is not None and len(rest) >= length:
                    body, self.buffer = rest[:length], rest[length:]
                    return json.loads(body)
            ready, _, _ = select.select([self.proc.stdout], [], [], 0.2)
            if ready:
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("LSP closed stdout")
                self.buffer += chunk
        raise TimeoutError("no LSP message")

    def request(self, method: str, params: dict) -> dict:
        rid = self.next_id
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            message = self.read()
            if message.get("id") == rid:
                return message

    def notify(self, method: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def open(self, path: pathlib.Path) -> str:
        uri = path.as_uri()
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "pengus",
                    "version": 1,
                    "text": path.read_text(),
                }
            },
        )
        while True:
            message = self.read()
            if message.get("method") == "textDocument/publishDiagnostics":
                return uri

    def shutdown(self) -> None:
        try:
            self.request("shutdown", {})
            self.notify("exit", {})
        finally:
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def main() -> int:
    if not PSC.exists():
        print(f"missing psc at {PSC}", file=sys.stderr)
        return 2
    if not (RAYLIB / "pengu" / "raylib.d.pengu").exists():
        print(f"skip: raylib-pengu not found at {RAYLIB}")
        return 0

    client = Client()
    try:
        client.request("initialize", {"rootUri": RAYLIB.as_uri(), "capabilities": {}})
        binding = client.open(RAYLIB / "pengu" / "raylib.d.pengu")
        semantic = client.request(
            "textDocument/semanticTokens/full", {"textDocument": {"uri": binding}}
        )
        data = semantic["result"]["data"]
        assert len(data) > 0, "raylib.d.pengu has no semantic tokens"
        types = set(data[3::5])
        assert 0 in types, "raylib.d.pengu has no keyword tokens"
        symbols = client.request(
            "textDocument/documentSymbol", {"textDocument": {"uri": binding}}
        )
        assert len(symbols["result"]) > 100, "raylib.d.pengu outline is empty"

        wrapper = client.open(RAYLIB / "pengu" / "raylibx" / "models.pengu")
        hover = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": wrapper}, "position": {"line": 75, "character": 13}},
        )
        value = hover["result"]["contents"]["value"]
        assert "upload" in value, "models.pengu hover has no signature"
        assert "Uploads the mesh" in value, "models.pengu hover lost the ## docs"
    finally:
        client.shutdown()

    print("OK raylib LSP tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
