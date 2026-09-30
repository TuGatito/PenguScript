"""Tests for extended std/cipher.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_cipher_extended(profile):
    """Verify all extended cipher helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_cipher_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"cipher_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Cipher Extended ===" in res.stdout
    assert "constants: OK" in res.stdout
    assert "base64 standard: OK" in res.stdout
    assert "base64 variants: OK" in res.stdout
    assert "hex: OK" in res.stdout
    assert "base32: OK" in res.stdout
    assert "enchanting string: OK" in res.stdout
    assert "json escaping & bug fix: OK" in res.stdout
    assert "json array: OK" in res.stdout
    assert "typed getters: OK" in res.stdout
    assert "navigation & merge: OK" in res.stdout
    assert "kind obj: OK" in res.stdout
    assert "kind arr: OK" in res.stdout
    assert "kind num: OK" in res.stdout
    assert "cipher extended: OK" in res.stdout
