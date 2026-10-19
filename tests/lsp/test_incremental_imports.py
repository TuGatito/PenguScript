"""Incremental correctness for imports, caches and per-buffer state.

These pin the parts of the language server that must stay correct while it is
fast: a module edit on disk or in another unsaved buffer invalidates every
importer that depends on it (and only those), an entry document's own import
aliases are never overwritten by a module that imports the same thing, and the
per-buffer state is released on ``didClose``.
"""
from __future__ import annotations

import asyncio
import os
import time

from lsprotocol.types import (
    DidChangeWatchedFilesParams,
    DidCloseTextDocumentParams,
    FileChangeType,
    FileEvent,
    TextDocumentIdentifier,
)

from pengu_lsp import server as lsp_server

LIB_V1 = """\
weave greet with x as int into int:
    return x + 1
"""

LIB_V2 = """\
weave greet with x as int into int:
    return x * 2

weave extra into int:
    return 42
"""

MAIN = """\
import lib

weave main into int:
    return calling lib.greet with 1
"""


def _bump_mtime(path) -> None:
    """Makes a disk rewrite visible even on a coarse-mtime filesystem."""
    future = time.time() + 2
    os.utime(path, (future, future))


def _module_members(lsp, alias: str) -> set:
    import_symbol = lsp.symbols.lookup(alias)
    assert import_symbol is not None and import_symbol.module_scope is not None
    return set(import_symbol.module_scope.symbols)


def _open_lib_project(lsp, lib_text: str = LIB_V1):
    """Writes lib.pengu next to the harness buffer and validates main."""
    lib_path = lsp.directory / "lib.pengu"
    lib_path.write_text(lib_text, encoding="utf-8")
    lsp.open(MAIN)
    return lib_path


def test_editing_a_dependency_on_disk_invalidates_the_import_bundle(lsp):
    lib_path = _open_lib_project(lsp)
    assert "greet" in _module_members(lsp, "lib")
    assert "extra" not in _module_members(lsp, "lib")

    lib_path.write_text(LIB_V2, encoding="utf-8")
    _bump_mtime(lib_path)
    lsp.open(MAIN)

    members = _module_members(lsp, "lib")
    assert "greet" in members and "extra" in members, members


def test_editing_a_dependency_transitively_invalidates_its_importers(lsp):
    """main -> b -> c: editing c must refresh b's cached export bundle.

    Imported modules re-export the types they import, so `b.Vec` exists without
    `b` declaring `Vec`.  That re-export is exactly what a stale bundle would
    keep hiding after `c` gains a type.
    """
    c_path = lsp.directory / "c.pengu"
    c_path.write_text("rune Vec:\n    x as int\n", encoding="utf-8")
    (lsp.directory / "b.pengu").write_text(
        "import c\n\nweave mid into int:\n    return 2\n", encoding="utf-8"
    )
    main = "import b\n\nweave main into int:\n    return calling b.mid\n"
    lsp.open(main)

    assert "Vec" in _module_members(lsp, "b")

    c_path.write_text(
        "rune Vec:\n    x as int\n\nrune Extra:\n    y as int\n",
        encoding="utf-8",
    )
    _bump_mtime(c_path)
    lsp.open(main)

    members = _module_members(lsp, "b")
    assert "Extra" in members, members


def test_an_unsaved_imported_buffer_is_used_by_the_importer(lsp):
    lib_path = _open_lib_project(lsp)
    lib_uri = lsp_server.path_to_uri(str(lib_path))
    overlay = "weave greet with x as int into int:\n    return x\n\nweave from_buffer into int:\n    return 9\n"
    try:
        lsp._server.server._docs[lib_uri] = overlay
        lsp.open(MAIN)
        members = _module_members(lsp, "lib")
        assert "from_buffer" in members, members
        assert "extra" not in members, members
    finally:
        lsp._server.server._docs.pop(lib_uri, None)

    lsp.open(MAIN)
    members = _module_members(lsp, "lib")
    assert "from_buffer" not in members, members
    assert "greet" in members, members


def test_entry_import_aliases_are_not_overwritten_by_module_imports(lsp):
    source = """\
import std.spark
import std.loom

weave main into int:
    calling spark.println with "hello"
    return 0
"""
    lsp.open(source)
    spark = lsp.symbols.lookup("spark")
    assert spark is not None
    # std.loom also imports spark, deeper in its file.  The entry document's
    # alias must keep *its* line and its own module file.
    assert spark.line == 1, (spark.line, spark.file_path)
    assert spark.file_path and spark.file_path.endswith("spark.pengu"), spark.file_path
    loom = lsp.symbols.lookup("loom")
    assert loom is not None and loom.line == 2


def test_plain_completion_does_not_list_imported_module_members(lsp):
    source = """\
import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
"""
    lsp.open(source)
    labels = lsp.complete(2, 0)
    assert "spark" in labels, labels
    assert "println" not in labels, labels
    assert not any(label.startswith("spark_") for label in labels), [
        label for label in labels if label.startswith("spark_")
    ]
    assert len(labels) < 300, len(labels)


def test_watched_file_change_revalidates_only_dependent_documents(lsp, monkeypatch):
    lib_path = _open_lib_project(lsp)
    lib_uri = lsp_server.path_to_uri(str(lib_path))

    other_path = lsp.directory / "other.pengu"
    other_text = "weave other into int:\n    return 0\n"
    other_path.write_text(other_text, encoding="utf-8")
    other_uri = lsp_server.path_to_uri(str(other_path))
    lsp_server.validate_document(other_uri, other_text)

    lib_path.write_text(LIB_V2, encoding="utf-8")
    _bump_mtime(lib_path)

    calls = []
    original = lsp_server._compute_diagnostics

    def _spy(uri, source, *args, **kwargs):
        calls.append(uri)
        return original(uri, source, *args, **kwargs)

    monkeypatch.setattr(lsp_server, "_compute_diagnostics", _spy)
    lsp_server.did_change_watched_files(
        DidChangeWatchedFilesParams(
            changes=[FileEvent(uri=lib_uri, type=FileChangeType.Changed)],
        )
    )

    assert lsp.uri in calls, calls
    assert other_uri not in calls, calls


def test_closing_a_document_releases_every_per_buffer_structure(lsp):
    lsp.open(MAIN + "\n")
    assert lsp.uri in lsp._server.server._docs
    assert lsp.uri in lsp._server.server._symbols

    asyncio.run(
        lsp_server._wire_did_close(
            DidCloseTextDocumentParams(
                text_document=TextDocumentIdentifier(uri=lsp.uri),
            )
        )
    )

    assert lsp.uri not in lsp._server.server._docs
    assert lsp.uri not in lsp._server.server._symbols
    assert lsp.uri not in lsp._server.server._validation_cache


def test_a_superseded_validation_does_not_touch_published_state(lsp):
    lsp.open("weave first into int:\n    return 0\n")
    previous = lsp._server.server._symbols[lsp.uri]

    result = lsp_server._compute_diagnostics(
        lsp.uri,
        "weave second into int:\n    return 1\n",
        lambda: True,
    )

    assert result is None
    assert lsp._server.server._symbols[lsp.uri] is previous
