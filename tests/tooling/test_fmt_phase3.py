"""Roadmap Phase 3 / §3.10 (fmt --diff/--stdin/config) and §3.12 (on-type)."""

import subprocess
import sys

from lsprotocol.types import (
    DocumentOnTypeFormattingParams,
    FormattingOptions,
    Position,
    TextDocumentIdentifier,
)

from pengu_lsp.formatting import format_pengu_source, load_format_config
from tests.conftest import REPO

URI = "file:///fmt.pengu"


def _run_fmt(args, stdin=None):
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "fmt", *args],
        capture_output=True, text=True, timeout=60, input=stdin,
    )


def test_fmt_stdin_formats_to_stdout():
    src = "weave f into int:\n   return   1\n"
    res = _run_fmt(["--stdin"], stdin=src)
    assert res.returncode == 0, res.stderr
    # `return   1` is left alone by design; indentation is not a multiple of 2
    # so it is normalized to one level.
    assert res.stdout.endswith("\n")
    assert "weave f into int:" in res.stdout


def test_fmt_stdin_check_only(tmp_path):
    # The default unit is 4 (item 4.2); a source already in the default unit is
    # clean, a source in another unit is rescaled and therefore reported.
    good = "weave f into int:\n    return 1\n"
    res = _run_fmt(["--stdin", "--check"], stdin=good)
    assert res.returncode == 0
    bad = "weave f into int:\n   return 1\n"
    res2 = _run_fmt(["--stdin", "--check"], stdin=bad)
    assert res2.returncode == 1


def test_fmt_diff_prints_unified_diff_without_writing(tmp_path):
    p = tmp_path / "d.pengu"
    original = "weave f into int:\n   return 1\n"
    p.write_text(original, encoding="utf-8")
    res = _run_fmt([str(p), "--diff"])
    assert res.returncode == 0, res.stderr
    assert "---" in res.stdout and "+++ " in res.stdout
    assert "@@" in res.stdout
    # `--diff` is a dry run: the file must not be modified.
    assert p.read_text(encoding="utf-8") == original


def test_pengufmt_toml_is_honoured(tmp_path):
    (tmp_path / ".pengufmt.toml").write_text(
        "[formatting]\ntab_size = 4\nblank_lines_max = 1\n", encoding="utf-8"
    )
    target = tmp_path / "t.pengu"
    cfg = load_format_config(str(target))
    assert cfg is not None
    assert cfg.get("tab_size") == 4
    assert cfg.get("blank_lines_max") == 1

    src = "weave f into int:\n\n\n\n    return 1\n"
    out = format_pengu_source(src, tab_size=4, insert_spaces=True, blank_lines_max=1)
    assert "\n\n\n" not in out
    assert "    return 1" in out


def test_blank_lines_max_none_keeps_blanks():
    src = "weave f into int:\n\n\n\n  return 1\n"
    out = format_pengu_source(src)
    assert "\n\n\n" in out


def test_pengu_yaml_still_supported_for_format_config(tmp_path):
    (tmp_path / "pengu.yaml").write_text(
        "formatting:\n  indent: 3\n  use_tabs: true\n", encoding="utf-8"
    )
    cfg = load_format_config(str(tmp_path / "x.pengu"))
    assert cfg and cfg.get("tab_size") == 3 and cfg.get("insert_spaces") is False


def _register(source, uri=URI):
    from pengu_lsp.server import server

    server._docs[uri] = source
    return server


def _on_type(source, line, ch):
    from pengu_lsp.server import on_type_formatting

    _register(source)
    params = DocumentOnTypeFormattingParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=line, character=0),
        ch=ch,
        options=FormattingOptions(tab_size=2, insert_spaces=True),
    )
    return on_type_formatting(params)


def test_on_type_colon_indents_next_line():
    src = "weave f into int:\n  if true:\n  return 1\n"
    edits = _on_type(src, 1, ":")
    assert edits, "typing ':' must indent the following line"
    e = edits[0]
    assert e.range.start.line == 2
    assert e.new_text == "    "


def test_on_type_newline_after_colon_indents_new_line():
    src = "weave f into int:\n    if true:\n\n"
    edits = _on_type(src, 2, "\n")
    assert edits
    assert edits[0].new_text == "      "


def test_on_type_newline_aligns_with_previous_statement():
    src = "weave f into int:\n    var a as int is 1\n\n"
    edits = _on_type(src, 2, "\n")
    assert edits
    assert edits[0].new_text == "    "


def test_on_type_no_edit_when_already_correct():
    src = "weave f into int:\n  if true:\n    return 1\n"
    assert _on_type(src, 1, ":") is None
