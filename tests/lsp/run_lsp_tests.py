#!/usr/bin/env python3
"""Protocol-level LSP regression tests for psc.

Runs `psc lsp --stdio` against a fixture project, without VS Code. This is the
suite that CI runs so hover/completion/inlay/tokens/docs cannot silently rot.
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
PROJECT = ROOT / "tests" / "lsp" / "fixtures" / "project"
DOC = PROJECT / "src" / "main.pengu"
URI = DOC.as_uri()


def frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode()
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


class Client:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [str(PSC), "lsp", "--stdio"],
            cwd=str(PROJECT),
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

    def read(self, timeout: float = 15.0) -> dict:
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
                assert self.proc.stdout is not None
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
            msg = self.read()
            if msg.get("id") == rid:
                return msg

    def notify(self, method: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def open(self, uri: str, text: str) -> dict:
        self.notify(
            "textDocument/didOpen",
            {"textDocument": {"uri": uri, "languageId": "pengus", "version": 1, "text": text}},
        )
        while True:
            msg = self.read()
            if msg.get("method") == "textDocument/publishDiagnostics":
                return msg["params"]

    def shutdown(self) -> None:
        try:
            self.request("shutdown", {})
            self.notify("exit", {})
        finally:
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def assert_eq(name: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


def assert_true(name: str, value) -> None:
    if not value:
        raise AssertionError(f"{name}: expected truthy, got {value!r}")


def main() -> int:
    if not PSC.exists():
        print(f"missing psc at {PSC}", file=sys.stderr)
        return 2
    text = DOC.read_text()
    client = Client()
    try:
        init = client.request(
            "initialize",
            {"rootUri": PROJECT.as_uri(), "capabilities": {}},
        )
        capabilities = init["result"]["capabilities"]
        assert_eq("server version", init["result"]["serverInfo"]["version"], "0.15.0")
        assert_true("completion triggers", capabilities["completionProvider"].get("triggerCharacters"))
        assert_eq(
            "on-type key",
            "moreTriggerCharacters" in capabilities["documentOnTypeFormattingProvider"],
            True,
        )

        diagnostics = client.open(URI, text)
        assert_eq("std import diagnostics", diagnostics["diagnostics"], [])

        hover = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": URI}, "position": {"line": 11, "character": 9}},
        )
        value = hover["result"]["contents"]["value"]
        assert_true("hover has string type", "string" in value)
        assert_true("hover has size", "Size" in value)

        hover_fn = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": URI}, "position": {"line": 7, "character": 7}},
        )
        fn_value = hover_fn["result"]["contents"]["value"]
        assert_true("hover signature", "suma" in fn_value and "int" in fn_value)
        assert_true("hover docs", "Suma dos enteros" in fn_value)

        inlay = client.request(
            "textDocument/inlayHint",
            {
                "textDocument": {"uri": URI},
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}},
            },
        )
        labels = [item["label"] for item in inlay["result"]]
        assert_true("inlay b is string", ": string" in labels)
        assert_true("inlay inferred strings", labels.count(": string") == 2)
        assert_true("inlay does not lie", ": int" not in labels)

        completion = client.request(
            "textDocument/completion",
            {"textDocument": {"uri": URI}, "position": {"line": 0, "character": 11}},
        )
        labels = [item["label"] for item in completion["result"]]
        assert_true("std modules complete", any(label == "std.spark" for label in labels))
        assert_true("std docs module complete", any(label == "std.archivum" for label in labels))

        member = client.request(
            "textDocument/completion",
            {"textDocument": {"uri": URI}, "position": {"line": 16, "character": 25}},
        )
        member_labels = [item["label"] for item in member["result"]]
        assert_true("module member complete", "println" in member_labels)

        lens = client.request("textDocument/codeLens", {"textDocument": {"uri": URI}})
        commands = [item["command"]["command"] for item in lens["result"]]
        assert_eq("code lens command", commands, ["pengus.run"])
        assert_true("code lens arguments", "arguments" in lens["result"][0]["command"])

        semantic = client.request("textDocument/semanticTokens/full", {"textDocument": {"uri": URI}})
        semantic_data = semantic["result"]["data"]
        assert_true("semantic data", len(semantic_data) > 0)
        semantic_types = semantic_data[3::5]
        assert_true("semantic keywords", 0 in semantic_types)
        assert_true("semantic types", 1 in semantic_types)
        assert_true("semantic functions", 2 in semantic_types)
        assert_true("legend has type", "type" in capabilities["semanticTokensProvider"]["legend"]["tokenTypes"])
        assert_true("legend has namespace", "namespace" in capabilities["semanticTokensProvider"]["legend"]["tokenTypes"])

        definition = client.request(
            "textDocument/definition",
            {"textDocument": {"uri": URI}, "position": {"line": 11, "character": 9}},
        )
        assert_true("definition returns location", definition["result"] is not None)

        symbols = client.request("textDocument/documentSymbol", {"textDocument": {"uri": URI}})
        names = [item["name"] for item in symbols["result"]]
        assert_true("outline has Persona", "Persona" in names)
        assert_true("outline has suma", "suma" in names)
        assert_true("outline has main", "main" in names)

        # Rich diagnostics: help/note must survive the LSP serialization.
        bad_uri = (PROJECT / "src" / "bad.pengu").as_uri()
        bad = 'import std.spark\n\nweave main into int:\n    let x as int is "hola"\n    return 0\n'
        bad_diags = client.open(bad_uri, bad)["diagnostics"]
        assert_eq("bad diag count", len(bad_diags), 1)
        assert_true("diagnostic help", "help:" in bad_diags[0]["message"])
        assert_true("diagnostic source", bad_diags[0]["source"] == "psc")
    finally:
        client.shutdown()

    print("OK LSP protocol tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
