"""Standalone PenguScript source formatter (no pygls dependency).

Used by the LSP (textDocument/formatting) and by the ``pengu fmt`` CLI command.
"""

import os
import re
from typing import Dict, List, Optional


def load_format_config(start_path: str) -> Optional[Dict[str, object]]:
    """Reads formatting settings from a nearby ``pengu.yaml``.

    Looks upward from ``start_path`` (bounded walk) for a project config file
    and extracts the supported keys: ``tab_size`` (or ``indent_size`` /
    ``indent``) and ``insert_spaces`` (or ``use_tabs``). Keys may live at the
    root or under a ``formatting:`` section.

    Args:
        start_path: File or directory to start searching from.

    Returns:
        A dict with ``tab_size`` (int) and ``insert_spaces`` (bool) entries for
        every key found, or None when no config file exists.
    """
    cur = start_path if os.path.isdir(start_path) else os.path.dirname(start_path)
    cur = os.path.abspath(cur)
    cfg_file = None
    for _ in range(8):
        candidate = os.path.join(cur, "pengu.yaml")
        if os.path.isfile(candidate):
            cfg_file = candidate
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    if cfg_file is None:
        return None

    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None

    result: Dict[str, object] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":") and " " not in stripped and "\t" not in stripped:
            continue  # section header, not a key/value pair
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+?)\s*$", stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if key in ("tab_size", "indent_size", "indent", "indent_width"):
            try:
                result["tab_size"] = int(value)
            except ValueError:
                pass
        elif key in ("insert_spaces",):
            result["insert_spaces"] = value.strip().lower() in ("true", "yes", "1")
        elif key in ("use_tabs",):
            result["insert_spaces"] = value.strip().lower() not in ("true", "yes", "1")
    return result if result else None


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
