"""Shared plumbing for the LSP test-suite (``tests/lsp/``).

The tests drive the language server the way an editor does: write a buffer,
validate it, then ask for completions. They use the real
:func:`pengu_lsp.server.validate_document` / :mod:`pengu_lsp.completions`
entry points rather than re-implementing the request plumbing, so a change to
the server's caching or the completion handler is covered too.

Two facts about the server shape the fixture below:

* :data:`pengu_lsp.server.server` is a module-level singleton, and it caches
  documents, symbol tables and diagnostics *per URI*. A test that reused
  another test's buffer would silently pass, so the fixture clears those caches
  before every test.
* ``validate_document`` publishes diagnostics through pygls. There is no
  transport under pytest, so the fixture records them instead and exposes them
  as :attr:`LspHarness.diagnostics`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

#: Repository root: ``tests/lsp/conftest.py`` -> ``tests/lsp`` -> ``tests`` ->
#: the checkout.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class LspHarness:
    """Opens one buffer and answers completion requests against it."""

    def __init__(self, directory: Path, name: str = "main.pengu") -> None:
        from pengu_lsp import server as lsp_server

        self._server = lsp_server
        self.directory = directory
        self.path = directory / name
        self.published: List[tuple] = []

    # -- buffer lifecycle ---------------------------------------------------
    @property
    def uri(self) -> str:
        return self._server.path_to_uri(str(self.path))

    @property
    def diagnostics(self) -> List:
        """The diagnostics the last :meth:`open` published."""
        return self.published[-1][1] if self.published else []

    @property
    def symbols(self):
        """The symbol table the server kept for the current buffer."""
        return self._server.server._symbols.get(self.uri)

    def open(self, source: str) -> "LspHarness":
        """Materialises ``source`` on disk, validates it and caches its symbols.

        The buffer is written to disk on purpose: an unsaved buffer is checked
        through a temporary shadow file, and these tests are about symbols, not
        about shadow-path remapping.
        """
        self.path.write_text(source, encoding="utf-8")
        # Drop the content-hash cache entry so a repeat of the same text really
        # re-runs the parse + check instead of replaying the previous result.
        self._server.server._validation_cache.pop(self.uri, None)
        self._server.validate_document(self.uri, source)
        return self

    # -- requests -----------------------------------------------------------
    def complete(self, line: int, character: int) -> List[str]:
        """Completion labels at a 0-based ``(line, character)`` position."""
        from lsprotocol.types import Position
        from pengu_lsp.completions import get_completions

        source = self.path.read_text(encoding="utf-8")
        lines = source.splitlines()
        prefix = lines[line][:character] if 0 <= line < len(lines) else ""
        result = get_completions(
            self.uri,
            Position(line=line, character=character),
            self.symbols,
            prefix,
            self._server._MODULE_CACHE,
            str(self.directory),
            source,
        )
        return [item.label for item in result.items]

    def complete_after(self, marker: str, occurrence: int = 1) -> List[str]:
        """Completion labels right after ``marker`` on the line that has it.

        ``marker`` is matched literally and the cursor lands on its last
        character, which is how a test says "the user just typed this".
        """
        source = self.path.read_text(encoding="utf-8")
        lines = source.splitlines()
        seen = 0
        for index, text in enumerate(lines):
            start = 0
            while True:
                found = text.find(marker, start)
                if found < 0:
                    break
                seen += 1
                if seen == occurrence:
                    column = found + len(marker)
                    return self.complete(index, column)
                start = found + len(marker)
        raise AssertionError(f"marker {marker!r} (occurrence {occurrence}) not found")


@pytest.fixture
def lsp(tmp_path, monkeypatch) -> LspHarness:
    """A clean PenguScript language-server session rooted at ``tmp_path``."""
    from pengu_lsp import server as lsp_server

    harness = LspHarness(tmp_path)

    monkeypatch.setattr(
        lsp_server.server,
        "publish_diagnostics",
        lambda uri, diags: harness.published.append((uri, diags)),
    )

    with lsp_server.server._validation_lock:
        lsp_server.server._symbols.clear()
        lsp_server.server._docs.clear()
        lsp_server.server._validation_cache.clear()
    lsp_server._MODULE_CACHE.clear()

    return harness
