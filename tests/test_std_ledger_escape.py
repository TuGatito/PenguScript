"""Roadmap Phase 6 / item 6.10 — ``ledger.escape_field`` must match the whole delimiter.

``escape_field`` decided whether to quote a field with ``var dcode as int is ord
delim`` and then compared each character's code point against ``dcode``.  ``ord``
requires a single-character *literal* at compile time but accepts a *variable*
of any length at runtime, where it yields only the first code point.  A
multi-byte delimiter therefore behaved like its first byte:

  * ``escape_field("a:b", "::")`` quoted the field, because it saw ``:``;
  * and no field could ever be matched against the real ``"::"`` sequence.

``escape_field_backslash`` carried the same first-byte comparison and is
covered here too.
"""

import pytest

from tests.conftest import compile_run, requires_runtime


def _program(body: str) -> str:
    return (
        "import std.spark\n"
        "import std.ledger\n"
        "\n"
        "weave probe with label as string, got as string, want as string into void:\n"
        "    if got != want:\n"
        '        calling spark.println with "{label} | got [{got}] want [{want}]"\n'
        "        calling spark.panic with label\n"
        "\n"
        "weave main into void:\n"
        f"{body}"
    )


def _pengu_str(value: str) -> str:
    r"""Quote ``value`` as a PenguScript double-quoted literal.

    Double quotes must be written ``\"`` (``""`` is not an escape), and the
    usual C escapes cover the newline/tab/backslash cases these tests use.
    """
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _cases(fn, cases):
    """Emit ``probe`` calls that compare ``fn(field, delim)`` to ``want``."""
    lines = []
    for i, (field, delim, want) in enumerate(cases):
        var = f"g{i}"
        lines.append(
            f"    var {var} as string is calling {fn} with "
            f"{_pengu_str(field)} , {_pengu_str(delim)}"
        )
        # Label avoids quote characters: it is embedded in a PenguScript string
        # literal. Note also that `calling f with (a, b, c)` is parsed as two
        # arguments, so every case goes through an intermediate variable.
        label = f"{fn} case {i} delim {delim!r}".replace('"', "").replace("'", "")
        lines.append(
            f"    calling probe with {_pengu_str(label)} , {var} , {_pengu_str(want)}"
        )
    return "\n".join(lines) + "\n"


@requires_runtime
def test_multi_char_delimiter_does_not_quote_a_partial_match():
    """``"a:b"`` must not be quoted for delimiter ``"::"``."""
    src = _program(
        _cases(
            "ledger.escape_field",
            [
                ("a:b", "::", "a:b"),
                ("a::b", "::", '"a::b"'),
                ("a::b::c", "::", '"a::b::c"'),
                ("plain", "::", "plain"),
            ],
        )
    )
    compile_run(src, tag="esc_multi")


@requires_runtime
def test_single_char_delimiter_behaviour_is_unchanged():
    src = _program(
        _cases(
            "ledger.escape_field",
            [
                ("a,b", ",", '"a,b"'),
                ("plain", ",", "plain"),
                ("x\ty", "\t", '"x\ty"'),
                ("x;y", ";", '"x;y"'),
            ],
        )
    )
    compile_run(src, tag="esc_single")


@requires_runtime
def test_quotes_and_line_breaks_still_force_quoting():
    src = _program(
        _cases(
            "ledger.escape_field",
            [
                ('a"b', ",", '"a""b"'),
                ("a\nb", ",", '"a\nb"'),
                ("a\rb", ",", '"a\rb"'),
            ],
        )
    )
    compile_run(src, tag="esc_specials")


@requires_runtime
def test_backslash_variant_matches_whole_delimiter():
    src = _program(
        _cases(
            "ledger.escape_field_backslash",
            [
                ("a:b", "::", "a:b"),
                ("a::b", "::", '"a::b"'),
                ('a"b', "::", '"a\\"b"'),
            ],
        )
    )
    compile_run(src, tag="esc_backslash")


@requires_runtime
def test_empty_delimiter_falls_back_to_comma():
    src = _program(
        _cases(
            "ledger.escape_field",
            [
                ("a,b", "", '"a,b"'),
                ("plain", "", "plain"),
            ],
        )
    )
    compile_run(src, tag="esc_empty")
