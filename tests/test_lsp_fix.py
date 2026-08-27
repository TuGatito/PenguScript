#!/usr/bin/env python3
"""Unit tests specifically verifying the 3 LSP bug fixes and consistency improvements."""

import os
import unittest
from lsprotocol.types import Position, Diagnostic

from pengu_parser.pengu_errors import PenguError
from pengu_lsp.server import diagnostics_from_errors, validate_document, server
from pengu_lsp.hover import get_word_at_position


class TestLSPFixes(unittest.TestCase):
    """Verifies span_end calculations, checker check API integration, and hover behavior."""

    def test_span_end(self):
        """Verifies that span_end is correctly mapped to diagnostic range end character."""
        err = PenguError(
            message="Test type mismatch",
            code="E0005",
            line=2,
            col=5,
            span_start=5,
            span_end=10
        )
        code = "line 1\n    let value = 123\n"
        diags = diagnostics_from_errors([err], code)
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].range.start.line, 1)
        self.assertEqual(diags[0].range.start.character, 4)
        self.assertEqual(diags[0].range.end.character, 10)

    def test_checker_api(self):
        """Verifies that valid code passes check() and publishes empty diagnostics list."""
        published = []
        original_publish = server.publish_diagnostics

        def mock_publish(uri, diags):
            published.append((uri, diags))

        server.publish_diagnostics = mock_publish
        try:
            valid_code = "weave main into void:\n  return\n"
            validate_document("file:///main.pengu", valid_code)
            self.assertEqual(len(published), 1)
            self.assertEqual(published[0][0], "file:///main.pengu")
            self.assertEqual(published[0][1], [])
        finally:
            server.publish_diagnostics = original_publish

    def test_publish_api(self):
        """Verifies that server.py defines publish_diagnostics and validate_document uses it."""
        server_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pengu_lsp", "server.py"))
        with open(server_py_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("def publish_diagnostics", content)
        self.assertIn("server.publish_diagnostics", content)

    def test_hover_self_arrow(self):
        """Verifies that hovering over self->x extracts the full identifier consistently."""
        code = "let v is self->x"
        # Character 10 is 'e' in 'self'
        word_self = get_word_at_position(code, Position(line=0, character=10))
        self.assertEqual(word_self, "self->x")

        # Character 15 is 'x'
        word_x = get_word_at_position(code, Position(line=0, character=15))
        self.assertEqual(word_x, "self->x")


if __name__ == "__main__":
    unittest.main()
