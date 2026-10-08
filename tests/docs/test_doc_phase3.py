"""Roadmap Phase 3 / §3.11 — `pengu doc`: Doxygen tags, deprecation, search."""

import json
import re

from pengu_doc import _doc_or, doc_project


def _project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "## Adds two numbers.\n"
        "## @param a first operand\n"
        "## @param b second operand\n"
        "## @return the sum\n"
        "weave add with a as int, b as int into int:\n"
        "    return a + b\n"
        "\n"
        "## Old helper.\n"
        "## @deprecated use add instead\n"
        '@deprecated("use add")\n'
        "weave old_add with a as int, b as int into int:\n"
        "    return a + b\n"
        "\n"
        "## A 2D point.\n"
        "rune Point:\n"
        "    x as int\n"
        "    y as int\n"
        "\n"
        "## Traffic light state.\n"
        "omen Light:\n"
        "    Red\n"
        "    Green\n"
        "\n"
        "## Renderable thing.\n"
        "concept Render:\n"
        "    weave draw into void\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: doctest\n  entry: src/main.pengu\n", encoding="utf-8"
    )
    return tmp_path


class _FakeSym:
    def __init__(self, doc, attributes=None):
        self.doc = doc
        self.attributes = attributes or {}


def test_doc_or_renders_doxygen_tags_as_bullets():
    sym = _FakeSym("Adds two numbers.\n@param a first\n@param b second\n@return the sum")
    out = _doc_or(sym, "fallback")
    assert out.startswith("Adds two numbers.")
    assert "- `@param a first`" in out
    assert "- `@return the sum`" in out
    assert "fallback" not in out


def test_doc_or_deprecated_attribute_badge():
    sym = _FakeSym("Old helper.", {"deprecated": ["use add"]})
    out = _doc_or(sym, "fallback")
    assert "Deprecated" in out and "use add" in out


def test_doc_or_deprecated_tag_badge():
    sym = _FakeSym("Old helper.\n@deprecated use add instead")
    out = _doc_or(sym, "fallback")
    assert "Deprecated" in out


def test_doc_project_index_and_search(tmp_path):
    proj = _project(tmp_path)
    index_path = doc_project(config_path=str(proj))
    assert index_path.endswith("index.md")
    index_md = (proj / "docs" / "index.md").read_text(encoding="utf-8")

    # Categorized index.
    for section in ("### Concepts", "### Functions", "### Omens", "### Runes"):
        assert section in index_md
    assert "[`old_add`]" in index_md
    assert "`[deprecated]`" in index_md
    assert "Symbol search (HTML)" in index_md

    # Self-contained HTML search page with the embedded index.
    html = (proj / "docs" / "index.html").read_text(encoding="utf-8")
    assert 'id="q"' in html and "DATA =" in html
    m = re.search(r"const DATA = (\[.*?\]);", html, re.S)
    assert m, "embedded JSON index not found"
    data = json.loads(m.group(1))
    names = {e["name"] for e in data}
    assert {"add", "old_add", "Point", "Light", "Render"} <= names
    assert next(e for e in data if e["name"] == "old_add")["deprecated"] is True
    assert next(e for e in data if e["name"] == "add")["signature"].startswith("**add**(")


def test_doc_project_renders_tags_in_module_page(tmp_path):
    proj = _project(tmp_path)
    doc_project(config_path=str(proj))
    page = (proj / "docs" / "src_main.md").read_text(encoding="utf-8")
    assert "- `@param a first operand`" in page
    assert "⚠️ **Deprecated**" in page


def test_doc_renders_hash_and_double_hash_equally(tmp_path):
    """`#` and `##` are both doc text (the .d.pengu convention is `#`)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "# Single-hash documented function.\n"
        "weave single into int:\n"
        "    return 1\n"
        "\n"
        "## Double-hash documented function.\n"
        "weave double into int:\n"
        "    return 2\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: hashes\n  entry: src/main.pengu\n", encoding="utf-8"
    )
    doc_project(config_path=str(tmp_path))
    page = (tmp_path / "docs" / "src_main.md").read_text(encoding="utf-8")
    assert "Single-hash documented function." in page
    assert "Double-hash documented function." in page
