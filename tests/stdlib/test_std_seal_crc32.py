"""Roadmap Phase 6 / item 6.1 — ``seal.crc32`` must be an unsigned 32-bit value.

Before this fix the runtime declared ``int pengu_c_seal_crc32(...)`` and
returned ``(int)crc32(...)``, so every checksum >= ``0x80000000`` came back
negative: ``crc32("a")`` was ``-390611389`` instead of ``3904355907``.  That
made the result impossible to compare against the reference implementations
(Python ``zlib.crc32``, ``cksum``, the CRC column of a PNG chunk).

The roadmap quoted ``390611389`` as the expected value for ``"a"``; that number
is itself wrong.  The IEEE 802.3 CRC-32 of the single byte ``a`` is
``0xE8B7BE43`` = ``3904355907`` (``zlib.crc32(b"a")``), and the tests below pin
the real constant.
"""

import re
import zlib

import pytest

from tests.conftest import bundle_project, compile_run, requires_runtime

# Reference values straight from Python's zlib, computed at import time so the
# expectation cannot silently drift from the C library the runtime links.
CRC_A = zlib.crc32(b"a")
CRC_HELLO = zlib.crc32(b"hello")
CRC_EMPTY = zlib.crc32(b"")

# The public API must be declared as an unsigned 32-bit value.  The C ABI of
# ``pengu_c_seal_crc32`` is bit-identical either way (a 32-bit register), which
# is why the fix lives in the declared types: ``int``/``int32_t`` makes the
# full-range checksum visible as a negative number to every PenguScript caller.
_CRC_SIGNATURE = re.compile(r"\b(?:u?int(?:8|16|32|64)_t)\s+seal_crc32\s*\(")
_CRC_FUNCTION = re.compile(r"^static inline \S+ seal_crc32\(", re.M)


def _crc_program(expectations: str) -> str:
    return (
        "import std.spark\n"
        "import std.seal\n"
        "\n"
        "weave main into void:\n"
        f"{expectations}"
    )


@requires_runtime
def test_crc32_is_declared_unsigned_in_generated_c():
    """The generated C must spell the checksum ``uint32_t``, not ``int32_t``.

    This is the regression gate that actually distinguishes fixed from broken:
    the C ABI is a 32-bit register either way, so only the declared type decides
    whether callers see 3904355907 or -390611389.
    """
    src = (
        "import std.seal\n"
        "\n"
        "weave main into void:\n"
        '    var v as u32 is calling seal.crc32 with "a"\n'
    )
    c_text = bundle_project(src, tag="crc32_sig")
    m = _CRC_FUNCTION.search(c_text)
    assert m, "seal_crc32 not found in the generated C"
    signature = m.group(0)
    # Match the whole return-type token: ``int32_t`` is a substring of
    # ``uint32_t``, so a naive ``not in`` check would reject the correct code.
    ret_type = re.match(r"static inline (\w+) seal_crc32\(", signature)
    assert ret_type, f"unexpected seal_crc32 signature: {signature!r}"
    assert ret_type.group(1) == "uint32_t", (
        f"seal.crc32 must return uint32_t, generated C returns "
        f"{ret_type.group(1)!r} (pre-1.0 was int32_t, which made every "
        f"checksum >= 0x80000000 negative)"
    )
    # The raw runtime bridge is declared in the header the bundle includes.
    assert _CRC_SIGNATURE.search(c_text) or "uint32_t pengu_c_seal_crc32" in c_text


@requires_runtime
def test_crc32_of_single_byte_is_unsigned():
    """``crc32("a")`` is 0xE8B7BE43, i.e. above INT_MAX, so it proves u32."""
    assert CRC_A == 0xE8B7BE43, "reference constant drifted"
    src = _crc_program(
        '    var v as u32 is calling seal.crc32 with "a"\n'
        f'    calling spark.assert with (v == {CRC_A})\n'
        # Widening into a 64-bit int keeps the magnitude; the signed 32-bit
        # pre-1.0 shape produced exactly -(2**32 - CRC_A) here.
        "    var wide as i64 is v to i64\n"
        f"    calling spark.assert with (wide == {CRC_A})\n"
        f"    calling spark.assert with (wide != {CRC_A - 2 ** 32})\n"
    )
    compile_run(src, tag="crc32_u32")


@requires_runtime
def test_crc32_matches_zlib_for_plain_values():
    src = _crc_program(
        '    var hello as u32 is calling seal.crc32 with "hello"\n'
        f'    calling spark.assert with (hello == {CRC_HELLO})\n'
        '    var empty as u32 is calling seal.crc32 with ""\n'
        f'    calling spark.assert with (empty == {CRC_EMPTY})\n'
    )
    compile_run(src, tag="crc32_zlib")


@requires_runtime
def test_crc32_is_never_negative():
    """Every byte string must land in ``[0, 2**32)``; regression guard."""
    lines = []
    for payload in ("a", "ab", "abc", "hello", "PenguScript"):
        want = zlib.crc32(payload.encode())
        lines.append(f'    var v_{len(lines)} as u32 is calling seal.crc32 with "{payload}"')
        lines.append(f"    calling spark.assert with (v_{len(lines) - 1} == {want})")
    compile_run(_crc_program("\n".join(lines) + "\n"), tag="crc32_range")


@requires_runtime
def test_to_crc32_enchantment_is_unsigned():
    """The string enchantment returns the same u32 as the module function."""
    src = (
        "import std.spark\n"
        "import std.seal\n"
        "\n"
        "weave main into void:\n"
        '    var s as string is "a"\n'
        "    var via_method as u32 is calling s.to_crc32\n"
        "    var via_fn as u32 is calling seal.crc32 with s\n"
        "    calling spark.assert with (via_method == via_fn)\n"
        f"    calling spark.assert with (via_method == {CRC_A})\n"
    )
    compile_run(src, tag="crc32_method")


@requires_runtime
def test_crc32_file_is_unsigned(tmp_path):
    """``crc32_file`` yields the same unsigned checksum as ``crc32``."""
    target = tmp_path / "payload.bin"
    target.write_bytes(b"a")
    src = (
        "import std.spark\n"
        "import std.seal\n"
        "\n"
        "weave main into void:\n"
        f'    var m as maybe u32 is calling seal.crc32_file with "{target}"\n'
        "    if m is present:\n"
        f"        calling spark.assert with (m.value == {CRC_A})\n"
        "    else:\n"
        '        calling spark.panic with "crc32_file returned none"\n'
    )
    compile_run(src, tag="crc32_file")
