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
PSC = pathlib.Path(os.environ.get("PSC", ROOT / "build" / "psc")).resolve()
PROJECT = ROOT / "tests" / "lsp" / "fixtures" / "project"
DOC = PROJECT / "src" / "main.pengu"
URI = DOC.as_uri()
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode()
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


class Client:
    def __init__(self, project: pathlib.Path = PROJECT) -> None:
        self.project = project
        self.proc = subprocess.Popen(
            [str(PSC), "lsp", "--stdio"],
            cwd=str(project),
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
        assert_eq("server version", init["result"]["serverInfo"]["version"], VERSION)
        assert_true("completion triggers", capabilities["completionProvider"].get("triggerCharacters"))
        assert_eq(
            "on-type removed",
            "documentOnTypeFormattingProvider" in capabilities,
            False,
        )
        assert_true("rename advertised", capabilities.get("renameProvider"))
        assert_eq("position encoding", capabilities.get("positionEncoding"), "utf-16")
        assert_true("inlay hints advertised", capabilities.get("inlayHintProvider"))

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

        # --- std.consortium: hover, completado sintético y definición -------
        consortium = (
            "import std.consortium as cons\n"
            "import std.spark\n"
            "\n"
            "rune Node:\n"
            "    value as int\n"
            "\n"
            "weave main into int:\n"
            "    var n as Node is with value is 7\n"
            "    var r as cons.Rc of Node is calling cons.Rc.new with n\n"
            "    var xs as list of int is list of int\n"
            "    calling xs.push with 1\n"
            "    var v as int is r.get->value\n"
            "    calling spark.println with \"{v}\"\n"
            "    return 0\n"
        )
        cdoc = PROJECT / "src" / "consortium_check.pengu"
        curi = cdoc.as_uri()
        cdiag = client.open(curi, consortium)
        assert_eq("consortium diagnostics", cdiag["diagnostics"], [])

        member = client.request(
            "textDocument/completion",
            {"textDocument": {"uri": curi}, "position": {"line": 11, "character": 22}},
        )
        labels = [item["label"] for item in member["result"]]
        assert_true("Rc.get complete", "get" in labels)
        assert_true("Rc.make_mut complete", "make_mut" in labels)
        assert_true("Rc.downgrade complete", "downgrade" in labels)
        assert_true("Rc.strong_count complete", "strong_count" in labels)
        lmember = client.request(
            "textDocument/completion",
            {"textDocument": {"uri": curi}, "position": {"line": 10, "character": 15}},
        )
        llabels = [item["label"] for item in lmember["result"]]
        assert_true("list.make_unique complete", "make_unique" in llabels)
        assert_true("list.is_shared complete", "is_shared" in llabels)
        assert_true("list.ref_count complete", "ref_count" in llabels)
        assert_true("list.push complete", "push" in llabels)

        chov = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": curi}, "position": {"line": 8, "character": 18}},
        )
        chov_value = chov["result"]["contents"]["value"]
        assert_true("Rc hover is a rune", "rune Rc" in chov_value)
        assert_true("Rc hover shows the doc", "reference-counted" in chov_value)

        cdef = client.request(
            "textDocument/definition",
            {"textDocument": {"uri": curi}, "position": {"line": 8, "character": 18}},
        )
        loc = cdef["result"]
        assert_true("consortium definition", loc is not None)
        first = loc[0] if isinstance(loc, list) else loc
        assert_true("consortium definition path", "consortium" in first.get("uri", ""))

        symbols = client.request("textDocument/documentSymbol", {"textDocument": {"uri": URI}})
        names = [item["name"] for item in symbols["result"]]
        assert_true("outline has Persona", "Persona" in names)
        assert_true("outline has suma", "suma" in names)
        assert_true("outline has main", "main" in names)

        # Documentation separated by one blank line must still attach to the
        # declaration (the raylib wrappers use this convention everywhere).
        doc_gap = PROJECT / "src" / "doc_gap.pengu"
        doc_gap_uri = doc_gap.as_uri()
        client.open(doc_gap_uri, doc_gap.read_text())
        doc_hover = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": doc_gap_uri}, "position": {"line": 2, "character": 8}},
        )
        doc_value = doc_hover["result"]["contents"]["value"]
        assert_true("hover docs across blank line", "Documented with a blank line" in doc_value)

        # Signature help must always answer with the canonical signature, real
        # parameter labels and the doc comment -- and repeated requests must not
        # recycle freed name-pool storage into `documentation` (the old bug wrote
        # "signatures\0..." after a second request).
        sig_doc = PROJECT / "src" / "sig.pengu"
        sig_uri = sig_doc.as_uri()
        client.open(sig_uri, sig_doc.read_text())
        for attempt in range(3):
            sig = client.request(
                "textDocument/signatureHelp",
                {"textDocument": {"uri": sig_uri}, "position": {"line": 7, "character": 29}},
            )["result"]
            assert_eq("signature count", len(sig["signatures"]), 1)
            entry = sig["signatures"][0]
            assert_eq("signature label", entry["label"], "**suma**(a: int, b: int) -> int")
            assert_eq(
                "signature params",
                [p["label"] for p in entry["parameters"]],
                ["a: int", "b: int"],
            )
            assert_eq("signature doc", entry.get("documentation"), " Suma dos enteros.")
            assert_eq("signature active param", sig.get("activeParameter"), 0)
            assert_true(
                "signature doc has no recycled bytes",
                "\x00" not in entry.get("documentation", ""),
            )
        second = client.request(
            "textDocument/signatureHelp",
            {"textDocument": {"uri": sig_uri}, "position": {"line": 7, "character": 41}},
        )["result"]
        assert_eq("signature active param second", second.get("activeParameter"), 1)
        hover_after = client.request(
            "textDocument/hover",
            {"textDocument": {"uri": sig_uri}, "position": {"line": 7, "character": 29}},
        )["result"]["contents"]["value"]
        assert_true("hover after signature", "Suma dos enteros." in hover_after)

        # Rich diagnostics: help/note must survive the LSP serialization.
        bad_uri = (PROJECT / "src" / "bad.pengu").as_uri()
        bad = 'import std.spark\n\nweave main into int:\n    let x as int is "hola"\n    return 0\n'
        bad_diags = client.open(bad_uri, bad)["diagnostics"]
        assert_eq("bad diag count", len(bad_diags), 1)
        assert_true("diagnostic help", "help:" in bad_diags[0]["message"])
        assert_true("diagnostic source", bad_diags[0]["source"] == "psc")
    finally:
        client.shutdown()

    # Rename cross-file: los ids de símbolo son por programa; la identidad
    # debe compararse por declaración (módulo + línea + columna + clase).
    ren = ROOT / "tests" / "lsp" / "fixtures" / "rename"
    lib = ren / "src" / "lib.pengu"
    mainp = ren / "src" / "main.pengu"
    lib_uri = lib.as_uri()
    main_uri = mainp.as_uri()
    rc = Client(ren)
    try:
        rc.request("initialize", {"rootUri": ren.as_uri(), "capabilities": {}})
        lib_text = lib.read_text()
        main_text = mainp.read_text()
        rc.open(lib_uri, lib_text)
        rc.open(main_uri, main_text)
        # Definición: `weave twice` (línea 1, columna 6).
        at_def = rc.request(
            "textDocument/rename",
            {"textDocument": {"uri": lib_uri}, "position": {"line": 1, "character": 7}, "newName": "doble"},
        )["result"]
        assert_true("rename def returns changes", at_def and "changes" in at_def)
        assert_true("rename def edits lib", lib_uri in at_def["changes"])
        assert_true("rename def edits main", main_uri in at_def["changes"])
        # Uso en main: `calling twice` en la línea 3.
        col = main_text.splitlines()[3].index("twice") + 1
        at_use = rc.request(
            "textDocument/rename",
            {"textDocument": {"uri": main_uri}, "position": {"line": 3, "character": col}, "newName": "triple"},
        )["result"]
        assert_true("rename use returns changes", at_use and "changes" in at_use)
        assert_true("rename use edits lib", lib_uri in at_use["changes"])
        assert_true("rename use edits main", main_uri in at_use["changes"])
        new_texts = {
            edit["newText"]
            for edits in at_use["changes"].values()
            for edit in edits
        }
        assert_eq("rename new text", new_texts, {"triple"})
    finally:
        rc.shutdown()

    # `fundere`: hover, completion y definición sobre miembros promovidos.
    fund = ROOT / "tests" / "lsp" / "fixtures" / "fundere"
    fmain = fund / "src" / "main.pengu"
    furi = fmain.as_uri()
    ftext = fmain.read_text()
    flines = ftext.splitlines()

    def fpos(needle: str, delta: int = 0) -> dict:
        for ln, line in enumerate(flines):
            at = line.find(needle)
            if at >= 0:
                return {"line": ln, "character": at + delta}
        raise AssertionError(f"needle {needle!r} not found")

    fc = Client(fund)
    try:
        fc.request("initialize", {"rootUri": fund.as_uri(), "capabilities": {}})
        fdiag = fc.open(furi, ftext)
        assert_eq("fundere fixture diagnostics", fdiag["diagnostics"], [])

        # Hover del campo promovido: tipo del embed y nota de promoción.
        fh = fc.request("textDocument/hover", {"textDocument": {"uri": furi}, "position": fpos("e.position.x", 2)})["result"]
        assert_true("fundere hover exists", fh is not None)
        fhv = fh["contents"]["value"]
        assert_true("fundere hover field", "field position" in fhv)
        assert_true("fundere hover Vec2", "Vec2" in fhv)
        assert_true("fundere hover promoted note", "Promoted by" in fhv)

        # Hover del método promovido.
        mh = fc.request("textDocument/hover", {"textDocument": {"uri": furi}, "position": fpos("e.move", 2)})["result"]
        assert_true("fundere method hover exists", mh is not None)
        assert_true("fundere method hover", "move" in mh["contents"]["value"])

        # Completion tras `e.` mezcla campos propios y promovidos.
        fc_ = fc.request("textDocument/completion", {"textDocument": {"uri": furi}, "position": fpos("e.position.x", 2)})["result"]
        labels = [item["label"] for item in fc_]
        assert_true("fundere completion promoted", "position" in labels and "bounds" in labels)
        assert_true("fundere completion own", "health" in labels)

        # Ir a la definición del campo promovido: la línea `position as Vec2`.
        fd = fc.request("textDocument/definition", {"textDocument": {"uri": furi}, "position": fpos("e.position.x", 2)})["result"]
        assert_true("fundere definition exists", fd is not None)
        decl_line = next(ln for ln, line in enumerate(flines) if line.strip() == "position as Vec2")
        assert_eq("fundere definition uri", fd["uri"], furi)
        assert_eq("fundere definition line", fd["range"]["start"]["line"], decl_line)
    finally:
        fc.shutdown()

    print("OK LSP protocol tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
