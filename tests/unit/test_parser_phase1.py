"""Unit tests for Phase 1 lexical foundations and parser baseline."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput, UnexpectedToken

from penguscript.frontend.ast_nodes import Module
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_parse_empty() -> None:
    """Empty string parses to Module([])."""
    result = parse("")
    assert isinstance(result, Module)
    assert result.declarations == []


def test_parse_comments() -> None:
    """Comment-only input parses to Module([])."""
    result = parse("-- hola\n")
    assert isinstance(result, Module)
    assert result.declarations == []


def test_parse_newlines() -> None:
    """Newlines-only input parses to Module([])."""
    result = parse("\n\n   \n")
    assert isinstance(result, Module)
    assert result.declarations == []


def test_parse_unexpected_token() -> None:
    """Unexpected tokens at top level fail with UnexpectedToken."""
    with pytest.raises(UnexpectedToken):
        parse("*")


def test_good_fixtures() -> None:
    """All good phase1 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase1"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase1 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert isinstance(result, Module), f"Failed for {file}"
        assert result.declarations == []


def test_bad_fixtures() -> None:
    """All bad phase1 fixtures must raise unexpected input errors."""
    bad_dir = FIXTURES_DIR / "bad" / "phase1"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase1 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises(UnexpectedInput) as exc_info:
            parse(content)
        diag = diagnostic_from_exception(exc_info.value)
        assert diag.code in ("E1001", "E1002")
