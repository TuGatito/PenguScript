"""Automated LSP integration test — tests the LSP handshake and features
against both Python source and compiled pengu.exe (if available).

This test validates the full LSP protocol flow:
  initialize → initialized → didOpen → completion → hover → shutdown → exit
"""
import json
import os
import subprocess
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable
EXE_PATH = os.path.join(ROOT_DIR, "pengucc_build", "pengu.exe")


def make_lsp_message(method: str, params, msg_id=None) -> bytes:
    """Encodes a JSON-RPC message with Content-Length header."""
    obj = {"jsonrpc": "2.0", "method": method, "params": params}
    if msg_id is not None:
        obj["id"] = msg_id
    body = json.dumps(obj)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    return (header + body).encode("utf-8")


def build_full_conversation() -> bytes:
    """Builds a complete LSP session as a single byte stream."""
    messages = b""
    # 1. initialize
    messages += make_lsp_message("initialize", {
        "processId": None,
        "rootPath": ROOT_DIR,
        "capabilities": {},
        "rootUri": f"file:///{ROOT_DIR.replace(os.sep, '/')}"
    }, msg_id=1)
    # 2. initialized notification
    messages += make_lsp_message("initialized", {})
    # 3. didOpen
    test_code = 'import std.spark\n\nweave main into void:\n    calling spark.println with "Test"\n'
    messages += make_lsp_message("textDocument/didOpen", {
        "textDocument": {
            "uri": "file:///lsp_test_file.pengu",
            "languageId": "pengus",
            "version": 1,
            "text": test_code
        }
    })
    # 4. completion
    messages += make_lsp_message("textDocument/completion", {
        "textDocument": {"uri": "file:///lsp_test_file.pengu"},
        "position": {"line": 3, "character": 4}
    }, msg_id=2)
    # 5. hover
    messages += make_lsp_message("textDocument/hover", {
        "textDocument": {"uri": "file:///lsp_test_file.pengu"},
        "position": {"line": 0, "character": 0}
    }, msg_id=3)
    # 6. shutdown
    messages += make_lsp_message("shutdown", None, msg_id=99)
    # 7. exit
    messages += make_lsp_message("exit", None)
    return messages


def run_lsp_session(cmd: list, timeout: int = 15) -> tuple:
    """Runs an LSP session and returns (responses, stderr_text)."""
    payload = build_full_conversation()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT_DIR,
    )
    stdout, stderr = proc.communicate(input=payload, timeout=timeout)
    # Parse JSON-RPC responses from stdout
    text = stdout.decode("utf-8", errors="replace")
    responses = []
    parts = text.split("Content-Length:")
    for part in parts[1:]:
        try:
            json_start = part.index("{")
            json_body = part[json_start:]
            brace_count = 0
            end = 0
            for ci, ch in enumerate(json_body):
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                if brace_count == 0:
                    end = ci + 1
                    break
            parsed = json.loads(json_body[:end])
            responses.append(parsed)
        except (ValueError, json.JSONDecodeError):
            pass
    return responses, stderr.decode("utf-8", errors="replace")


class TestLSPIntegration(unittest.TestCase):
    """Tests LSP integration via Python source."""

    def _run_and_validate(self, cmd: list, label: str):
        responses, stderr = run_lsp_session(cmd)

        # Should have at least: initialize response, diagnostics, completion, hover, shutdown
        self.assertGreaterEqual(len(responses), 4, f"[{label}] Expected ≥4 responses, got {len(responses)}")

        # 1. Initialize response (id=1)
        init_resp = next((r for r in responses if r.get("id") == 1), None)
        self.assertIsNotNone(init_resp, f"[{label}] Missing initialize response")
        self.assertIn("result", init_resp, f"[{label}] Initialize has no result")
        caps = init_resp["result"].get("capabilities", {})
        self.assertIn("textDocumentSync", caps, f"[{label}] Missing textDocumentSync capability")
        self.assertIn("completionProvider", caps, f"[{label}] Missing completionProvider capability")
        self.assertIn("hoverProvider", caps, f"[{label}] Missing hoverProvider capability")
        self.assertIn("definitionProvider", caps, f"[{label}] Missing definitionProvider capability")

        # 2. Diagnostics notification
        diag_resp = next((r for r in responses if r.get("method") == "textDocument/publishDiagnostics"), None)
        self.assertIsNotNone(diag_resp, f"[{label}] Missing publishDiagnostics notification")

        # 3. Completion response (id=2)
        comp_resp = next((r for r in responses if r.get("id") == 2), None)
        self.assertIsNotNone(comp_resp, f"[{label}] Missing completion response")
        self.assertIn("result", comp_resp, f"[{label}] Completion has no result")

        # 4. Hover response (id=3)
        hover_resp = next((r for r in responses if r.get("id") == 3), None)
        self.assertIsNotNone(hover_resp, f"[{label}] Missing hover response")

        # 5. Shutdown response (id=99)
        shutdown_resp = next((r for r in responses if r.get("id") == 99), None)
        self.assertIsNotNone(shutdown_resp, f"[{label}] Missing shutdown response")

    def test_lsp_python_source(self):
        """Tests LSP protocol with Python source entry point."""
        self._run_and_validate(
            [PYTHON, "pengu_project.py", "lsp", "--stdio"],
            "Python Source"
        )

    @unittest.skipUnless(os.path.exists(EXE_PATH), "pengu.exe not found — skip exe test")
    def test_lsp_compiled_exe(self):
        """Tests LSP protocol with compiled pengu.exe."""
        self._run_and_validate(
            [EXE_PATH, "lsp", "--stdio"],
            "Compiled Exe"
        )


if __name__ == "__main__":
    unittest.main()
