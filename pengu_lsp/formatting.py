"""Standalone PenguScript source formatter (no pygls dependency).

Used by the LSP (textDocument/formatting) and by the ``pengu fmt`` CLI command.
"""

import re
from typing import List


def format_pengu_source(text: str, tab_size: int = 2, insert_spaces: bool = True) -> str:
    """Formats PenguScript source text according to the standard style.

    Normalizes leading indentation (tabs or ``tab_size`` spaces), strips
    trailing whitespace and enforces consistent spacing around the structural
    keywords ``is`` / ``as`` / ``into`` and after commas. Comment lines
    (``#`` / ``##`` doc comments) keep their content untouched.

    Args:
        text: Raw document source.
        tab_size: Number of spaces per indentation level (2 by default).
        insert_spaces: True to indent with spaces, False to use tabs.

    Returns:
        The formatted document text.
    """
    lines = text.splitlines()
    formatted_lines: List[str] = []
    indent_unit = " " * tab_size if insert_spaces else "\t"

    for line in lines:
        stripped_right = line.rstrip()
        if not stripped_right:
            formatted_lines.append("")
            continue

        leading_spaces = len(stripped_right) - len(stripped_right.lstrip(" "))
        leading_tabs = len(stripped_right) - len(stripped_right.lstrip("\t"))

        indent_level = 0
        if leading_tabs > 0:
            indent_level = leading_tabs
        elif leading_spaces > 0:
            indent_level = leading_spaces // tab_size

        content = stripped_right.strip()

        # Cosmetic spacing normalization (skip comment lines).
        if not content.startswith("#"):
            content = re.sub(r"\s+is\s+", " is ", content)
            content = re.sub(r"\s+as\s+", " as ", content)
            content = re.sub(r"\s+into\s+", " into ", content)
            content = re.sub(r",\s*", ", ", content)

        formatted_lines.append((indent_unit * indent_level) + content)

    new_full_text = "\n".join(formatted_lines) + ("\n" if text.endswith("\n") else "")
    return new_full_text
