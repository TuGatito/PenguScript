"""Standalone PenguScript source formatter (no pygls dependency).

Used by the LSP (textDocument/formatting) and by the ``pengu fmt`` CLI command.

The formatter is deliberately conservative: it normalizes indentation and the
cosmetic spacing around ``is`` / ``as`` / ``into`` and after commas, but it must
never alter the *contents* of a literal.  String bytes are program data, so every
literal is located first and copied verbatim; multi-line (triple-quoted) strings
are emitted line by line without reindentation or trailing-space stripping.
"""

import os
import re
from typing import Dict, List, Optional, Tuple


def load_format_config(start_path: str) -> Optional[Dict[str, object]]:
    """Reads formatting settings from a nearby ``.pengufmt.toml`` or ``pengu.yaml``.

    Looks upward from ``start_path`` (bounded walk) for ``.pengufmt.toml`` first
    and then ``pengu.yaml``/``pengu.toml``.  Supported keys: ``tab_size`` (or
    ``indent_size`` / ``indent`` / ``indent_width``), ``insert_spaces`` (or
    ``use_tabs`` / ``tabs``) and ``blank_lines_max``.  Keys may live at the root
    or under a ``[formatting]`` / ``formatting:`` section.  Both ``key = value``
    (TOML) and ``key: value`` (YAML) spellings are accepted.

    Args:
        start_path: File or directory to start searching from.

    Returns:
        A dict with the recognized settings, or None when no config file exists.
    """
    cur = start_path if os.path.isdir(start_path) else os.path.dirname(start_path)
    cur = os.path.abspath(cur)
    cfg_file = None
    for _ in range(8):
        for candidate_name in (".pengufmt.toml", "pengu.yaml", "pengu.toml"):
            candidate = os.path.join(cur, candidate_name)
            if os.path.isfile(candidate):
                cfg_file = candidate
                break
        if cfg_file:
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
        if stripped.startswith("[") and stripped.endswith("]"):
            continue  # TOML section header
        if stripped.endswith(":") and " " not in stripped and "\t" not in stripped:
            continue  # YAML section header
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*[:=]\s*(.+?)\s*$", stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip().strip('"').strip("'")
        if key in ("tab_size", "indent_size", "indent", "indent_width"):
            try:
                result["tab_size"] = int(value)
            except ValueError:
                pass
        elif key in ("insert_spaces",):
            result["insert_spaces"] = value.lower() in ("true", "yes", "1")
        elif key in ("use_tabs", "tabs"):
            result["insert_spaces"] = value.lower() not in ("true", "yes", "1")
        elif key in ("blank_lines_max", "max_blank_lines"):
            try:
                result["blank_lines_max"] = max(0, int(value))
            except ValueError:
                pass
        elif key in ("line_width", "max_line_width"):
            try:
                result["line_width"] = max(0, int(value))
            except ValueError:
                pass
    return result if result else None


_STRING_DELIMS = ('"""', "'''", '"', "'")


def _split_code_and_strings(line: str) -> List[Tuple[bool, str]]:
    """Splits a source line into ``(is_literal, text)`` segments.

    The opening quote stays with the segment so that re-joining the segments is
    byte-for-byte lossless.  Single-quoted char literals, single- and
    triple-quoted strings and raw variants (``r"..."``) are all recognized; the
    ``r``/``R`` prefix itself stays in the preceding code segment, which is
    correct because it is emitted unchanged either way.
    """
    segments: List[Tuple[bool, str]] = []
    i = 0
    n = len(line)
    code_start = 0
    while i < n:
        ch = line[i]
        if ch not in ('"', "'"):
            i += 1
            continue
        delim = next((d for d in _STRING_DELIMS if line.startswith(d, i)), None)
        if delim is None:
            i += 1
            continue
        is_raw = i > 0 and line[i - 1] in ("r", "R")
        j = i + len(delim)
        while j < n:
            if delim in ('"""', "'''"):
                if line.startswith(delim, j):
                    j += len(delim)
                    break
                j += 1
            else:
                if line[j] == "\\" and not is_raw:
                    j += 2
                    continue
                if line[j] == delim:
                    j += 1
                    break
                j += 1
        else:
            j = n
        if code_start < i:
            segments.append((False, line[code_start:i]))
        segments.append((True, line[i:j]))
        i = j
        code_start = i
    if code_start < n:
        segments.append((False, line[code_start:]))
    return segments


def _open_triple(segments: List[Tuple[bool, str]]) -> Optional[str]:
    """Returns the still-open triple-quote delimiter of a line, if any."""
    for is_literal, part in segments:
        if not is_literal:
            continue
        for delim in ('"""', "'''"):
            if part.startswith(delim) and not part.endswith(delim):
                return delim
            if part.startswith(delim) and len(part) < len(delim) * 2:
                return delim
    return None


def _triple_closes(line: str, delim: str) -> bool:
    """True when ``line`` contains the closing delimiter of an open triple string."""
    idx = line.find(delim)
    if idx == -1:
        return False
    if delim in ('"""', "'''"):
        return True
    return True


def _normalize_code_spacing(code: str) -> str:
    """Normalizes cosmetic spacing inside a *code* segment (never a literal)."""
    code = re.sub(r"\s+is\s+", " is ", code)
    code = re.sub(r"\s+as\s+", " as ", code)
    code = re.sub(r"\s+into\s+", " into ", code)
    code = re.sub(r",\s*", ", ", code)
    return code


def _detect_source_unit(lines: List[str], fallback: int) -> int:
    """Detect the indentation unit already used by ``lines``.

    ``tab_size`` describes the *output* format; decoding the input with it is
    what corrupted sources whose unit differed from the requested one.  The
    unit of the input is a property of the file, not of the invocation.

    The smallest non-zero run of leading spaces is the unit: any deeper line is
    a multiple of it in idiomatic PenguScript.  A tab counts as one level.

    Args:
        lines: Source lines (blank lines are ignored).
        fallback: Unit to use when no indented line exists.

    Returns:
        The detected number of spaces per indentation level, or 1 for tabs.
    """
    candidates = []
    for line in lines:
        if not line.strip():
            continue
        leading = line[:len(line) - len(line.lstrip())]
        if not leading:
            continue
        if leading[0] == "\t":
            return 1
        candidates.append(len(leading))
    return min(candidates) if candidates else fallback


def format_pengu_source(text: str, tab_size: int = 2, insert_spaces: bool = True,
                        blank_lines_max: Optional[int] = None) -> str:
    """Formats PenguScript source text according to the standard style.

    Normalizes leading indentation (tabs or ``tab_size`` spaces), strips
    trailing whitespace and enforces consistent spacing around the structural
    keywords ``is`` / ``as`` / ``into`` and after commas. Comment lines
    (``#`` / ``##`` doc comments) keep their content untouched, and literal
    bytes are never modified: code-only spacing rules are applied to the code
    segments of each line, and the body of a multi-line string is copied
    verbatim.

    Args:
        text: Raw document source.
        tab_size: Number of spaces per indentation level in the output (2 by
            default).  The unit used to *decode* the input is detected from the
            source itself, so ``tab_size`` never rescales or collapses it.
        insert_spaces: True to indent with spaces, False to use tabs.
        blank_lines_max: Optional cap on consecutive blank lines (None keeps
            them all).  Blank lines inside a multi-line literal are never
            touched.

    Returns:
        The formatted document text.
    """
    head = "\n".join(text.splitlines()[:5])
    if "@generated" in head:
        return text

    lines = text.splitlines()
    formatted_lines: List[str] = []
    indent_unit = " " * tab_size if insert_spaces else "\t"
    source_unit = _detect_source_unit(lines, tab_size)
    in_triple: Optional[str] = None
    blank_run = 0

    for line in lines:
        # Inside a multi-line literal every byte is string data: emit verbatim.
        if in_triple is not None:
            formatted_lines.append(line)
            if _triple_closes(line, in_triple):
                in_triple = None
            continue

        stripped_right = line.rstrip()
        if not stripped_right:
            blank_run += 1
            if blank_lines_max is not None and blank_run > blank_lines_max:
                continue
            formatted_lines.append("")
            continue
        blank_run = 0

        leading_spaces = len(stripped_right) - len(stripped_right.lstrip(" "))
        leading_tabs = len(stripped_right) - len(stripped_right.lstrip("\t"))

        indent_level = 0
        if leading_tabs > 0:
            indent_level = leading_tabs
        elif leading_spaces > 0:
            indent_level = leading_spaces // source_unit

        # A line that opens a multi-line literal keeps its trailing whitespace:
        # those bytes are string data.  Every other line is right-stripped.
        raw_content = line.lstrip()
        opens_triple = _open_triple(_split_code_and_strings(raw_content))
        content = raw_content.rstrip("\n") if opens_triple is not None else stripped_right.strip()

        # Cosmetic spacing normalization (skip comment lines and literals).
        if not content.startswith("#"):
            segments = _split_code_and_strings(content)
            content = "".join(
                part if is_literal else _normalize_code_spacing(part)
                for is_literal, part in segments
            )
            in_triple = _open_triple(segments)

        formatted_lines.append((indent_unit * indent_level) + content)

    new_full_text = "\n".join(formatted_lines) + ("\n" if text.endswith("\n") else "")
    return new_full_text
