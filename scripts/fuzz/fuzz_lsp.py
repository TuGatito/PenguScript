#!/usr/bin/env python3
"""Fuzz the language server's document handling (roadmap 5.5).

Feeds malformed text and out-of-range positions through the request handlers,
mirroring what a buggy editor could send.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import run_harness  # noqa: E402


def target(data: bytes) -> None:
    from pengu_lsp.server import PenguLanguageServer

    text = data.decode("utf-8", errors="replace")
    server = PenguLanguageServer()
    server.did_open({"textDocument": {"uri": "file:///fuzz.pengu", "text": text}})
    rng = random.Random(len(text))
    line = rng.randint(0, 40)
    char = rng.randint(0, 80)
    server.document_symbols({"textDocument": {"uri": "file:///fuzz.pengu"}})
    server.document_highlight({
        "textDocument": {"uri": "file:///fuzz.pengu"},
        "position": {"line": line, "character": char},
    })
    server.rename({
        "textDocument": {"uri": "file:///fuzz.pengu"},
        "position": {"line": line, "character": char},
        "newName": text[:16] or "x",
    })
    server.semantic_tokens_full({"textDocument": {"uri": "file:///fuzz.pengu"}})
    server.document_formatting({
        "textDocument": {"uri": "file:///fuzz.pengu"},
        "options": {"tabSize": 2, "insertSpaces": True},
    })


if __name__ == "__main__":
    seeds = [
        b"weave main into int:\n  return 0\n",
        b"",
        b"weave ",
        b"\xff\xfe\x00\x01",
        json.dumps({"nested": "{" * 50}).encode(),
    ]
    sys.exit(run_harness("lsp", target, seeds, iterations=400))
