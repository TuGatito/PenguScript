"""The unsaved-`import` half of the `Type 'f32' has no method 'clamp'` report.

An editor holds a buffer that is ahead of the file it will be saved to. The
checker used to build the import graph by re-reading the *file* at
``checker.filename``, so a buffer that had just gained ``import std.numerus`` —
or a document whose on-disk copy differed at all — was checked against the disk:
the imported module was never collected, none of its ``enchanting`` methods were
registered, and the first ``x.clamp`` failed with ``E0004`` until the file was
saved.

``pengu_parser/pengu_symbols.resolve_imports`` now takes ``entry_source`` and
``PenguChecker`` hands it the text it was given, so only the *entry* comes from
memory; dependencies are still read from disk (nobody is editing those).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lsprotocol.types import DiagnosticSeverity

pytestmark = pytest.mark.smoke

SAVED = '''weave main into int:
    var variable_flotante as f32 is 20.0
    return 0
'''

BUFFER = '''import std.numerus

weave main into int:
    var variable_flotante as f32 is 20.0
    let resultado as f32 is calling variable_flotante.clamp with 20.0, -20.0
    return 0
'''

MODULE = '''enchanting int:
    weave local_method into int:
        return self + 1
'''

USES_LOCAL_MODULE = '''import localmod

weave main into int:
    var n as int is 1
    var m as int is calling n.local_method
    return 0
'''


def _errors(lsp) -> list:
    return [
        d.message for d in lsp.diagnostics
        if d.severity == DiagnosticSeverity.Error
    ]


def test_a_buffer_ahead_of_disk_resolves_its_new_import(lsp):
    """The reported reproduction: disk has no import, the buffer does.

    ``open_unsaved`` is what makes this a real reproduction — the file on disk
    stays behind, exactly as it does between two keystrokes.
    """
    lsp.open(SAVED)

    lsp.open_unsaved(BUFFER)

    assert _errors(lsp) == []


def test_disk_matching_the_buffer_is_unchanged(lsp):
    lsp.open(BUFFER)

    assert _errors(lsp) == []


def test_an_unsaved_project_module_is_resolved(lsp):
    """Not just the stdlib: a local module the buffer imports but disk lacks."""
    (lsp.directory / "localmod.pengu").write_text(MODULE, encoding="utf-8")
    lsp.open(SAVED)

    lsp.open_unsaved(USES_LOCAL_MODULE)

    assert _errors(lsp) == []


def test_entry_source_applies_to_the_entry_and_nothing_else(tmp_path):
    """The dependency graph must still be walked on disk.

    ``a.pengu`` exists but says nothing; the *in-memory* text says ``import b``.
    ``b.pengu`` on disk imports ``c.pengu``. The order must therefore be
    c, b, a — proof that the override covered the entry only, and that
    dependencies were still read (and parsed) from disk.
    """
    from pengu_parser.pengu_parser import PenguParser
    from pengu_parser.pengu_symbols import resolve_imports

    (tmp_path / "a.pengu").write_text("weave a into int:\n    return 0\n", encoding="utf-8")
    (tmp_path / "b.pengu").write_text("import c\n\nweave b into int:\n    return 0\n", encoding="utf-8")
    (tmp_path / "c.pengu").write_text("weave c into int:\n    return 0\n", encoding="utf-8")

    order = resolve_imports(
        str(tmp_path), str(tmp_path / "a.pengu"),
        parser=PenguParser(),
        entry_source="import b\n\nweave a into int:\n    return 0\n",
    )

    assert [Path(entry).name for entry in order] == ["c.pengu", "b.pengu", "a.pengu"]


def test_a_missing_file_still_reports_the_import_error(lsp, tmp_path):
    """An import that resolves nowhere must keep raising, not be swallowed."""
    lsp.open('import std.this_module_does_not_exist\n\nweave main into int:\n    return 0\n')

    assert any("Cannot resolve imported module" in msg for msg in _errors(lsp)), lsp.diagnostics
