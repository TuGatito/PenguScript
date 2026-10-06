"""Roadmap Phase 6 / item 6.9 — ``cipher.decode_base64`` must reject stray ``=``.

The decoder stripped whitespace, required ``len % 4 == 0`` and then walked the
input in quanta, reading ``clean at (pos + 2)`` / ``(pos + 3)``.  A ``=`` that
appeared anywhere other than the final quantum was treated as an ordinary data
character, so ``"QQ==QQ=="`` was accepted instead of rejected: the first
quantum length byte came from ``dec``.

These tests pin the RFC 4648 contract: ``=`` may only close the string, at most
two of them, and only in the final quantum.
"""

import pytest

from tests.conftest import compile_run, requires_runtime


def _program(body: str) -> str:
    return (
        "import std.spark\n"
        "import std.cipher\n"
        "\n"
        "weave probe with label as string, s as string into void:\n"
        "    var m as maybe string is calling cipher.decode_base64 with s\n"
        "    if m is present:\n"
        '        calling spark.println with "{label}|present|{m.value}"\n'
        "    else:\n"
        '        calling spark.println with "{label}|none|"\n'
        "\n"
        "weave main into void:\n"
        f"{body}"
    )


def _assertions(expectations):
    lines = []
    for i, (label, payload, want) in enumerate(expectations):
        var = f"v{i}"
        lines.append(f'    var {var} as maybe string is calling cipher.decode_base64 with "{payload}"')
        if want is None:
            lines.append(f"    calling spark.assert with (not ({var} is present))")
            lines.append(
                f'    calling spark.assert with (not (calling cipher.is_base64 with "{payload}"))'
            )
        else:
            lines.append(f"    if {var} is present:")
            lines.append(f'        calling spark.assert with ({var}.value == "{want}")')
            lines.append("    else:")
            lines.append(f'        calling spark.panic with "expected present for {label}"')
    return "\n".join(lines) + "\n"


@requires_runtime
def test_padding_only_at_end_is_accepted():
    src = _program(
        _assertions(
            [
                ("a1", "QQ==", "A"),
                ("a2", "QUI=", "AB"),
                ("a3", "QUJD", "ABC"),
                ("a4", "aGVsbG8=", "hello"),
            ]
        )
    )
    compile_run(src, tag="b64_ok")


@requires_runtime
def test_double_padded_quantum_is_rejected():
    """``"QQ==QQ=="`` was the concrete bug: it must decode to none."""
    src = _program(
        '    calling spark.assert with (not (calling cipher.is_base64 with "QQ==QQ=="))\n'
        '    var m as maybe string is calling cipher.decode_base64 with "QQ==QQ=="\n'
        "    calling spark.assert with (not (m is present))\n"
        '    calling spark.assert with (not (calling cipher.is_base64 with "QQ==QQ"))\n'
        '    calling spark.assert with (not (calling cipher.is_base64 with "QQ=QQ=="))\n'
    )
    compile_run(src, tag="b64_midpad")


@requires_runtime
def test_excessive_or_short_padding_is_rejected():
    src = _program(
        _assertions(
            [
                ("p3", "Q===", None),
                ("p4", "QUJD====", None),
                ("p5", "=", None),
                ("p6", "====", None),
            ]
        )
    )
    compile_run(src, tag="b64_badpad")


@requires_runtime
def test_whitespace_is_still_ignored():
    """The padding pass must run after whitespace stripping, not before."""
    src = _program(
        _assertions(
            [
                ("w1", "aGVs bG8=", "hello"),
                ("w2", "aGVs\\nbG8=", "hello"),
            ]
        )
    )
    compile_run(src, tag="b64_ws")
