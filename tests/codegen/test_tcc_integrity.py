"""Phase 9, items 9.2/9.3 — the prebuilt TinyCC archive is verified, hard.

The Windows release bundles a downloaded ``tcc.exe``.  A digest mismatch must
abort the build (not warn, not "fall back to no TCC"), the default digest must
live in the code rather than only in a workflow, and the archive must be
extracted through the shared path validator.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import urllib.error
import zipfile
from pathlib import Path

import pytest

import pengu_tcc
from pengu_archive import UnsafeArchiveError
from pengu_tcc import TCC_RELEASE_SHA256, TCC_RELEASE_URL, TccIntegrityError

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[2]


def _make_tcc_zip(path: Path, exe_name: str = "tcc/tcc.exe") -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(exe_name, b"MZ fake tinycc")
        zf.writestr("tcc/include/stdarg.h", b"/* tcc */\n")
    path.write_bytes(buf.getvalue())
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_default_digest_is_pinned_in_the_code():
    """Item 9.3: a default exists in `pengu_tcc`, not only in a workflow."""
    assert HEX64.match(TCC_RELEASE_SHA256), TCC_RELEASE_SHA256
    assert TCC_RELEASE_URL.startswith("https://")
    assert TCC_RELEASE_URL.endswith(".zip")


def test_default_digest_is_the_upstream_archive():
    """The real proof, when the network is available.

    Run with ``PENGU_NETWORK_TESTS=1``; the offline suite only checks shape.
    """
    if os.environ.get("PENGU_NETWORK_TESTS", "").strip() != "1":
        pytest.skip("set PENGU_NETWORK_TESTS=1 to download and verify the archive")
    import urllib.request

    req = urllib.request.Request(
        TCC_RELEASE_URL, headers={"User-Agent": "PenguScript-Release/1"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        actual = hashlib.sha256(resp.read()).hexdigest()
    assert actual == TCC_RELEASE_SHA256


def test_wrong_digest_is_a_hard_failure_and_extracts_nothing(tmp_path):
    """C2: revert the check and the fake `tcc.exe` lands in dest_dir."""
    archive = _make_tcc_zip(tmp_path / "tcc.zip")
    dest = tmp_path / "dest"
    dest.mkdir()

    with pytest.raises(TccIntegrityError) as excinfo:
        pengu_tcc._download_windows_tcc(
            str(dest), url=archive.as_uri(), expected_sha256="0" * 64
        )
    assert "mismatch" in str(excinfo.value)
    assert list(dest.iterdir()) == [], "nothing may be extracted on a mismatch"


def test_correct_digest_extracts_and_returns_the_executable(tmp_path):
    archive = _make_tcc_zip(tmp_path / "tcc.zip")
    dest = tmp_path / "dest"
    dest.mkdir()

    found = pengu_tcc._download_windows_tcc(
        str(dest), url=archive.as_uri(), expected_sha256=_sha256(archive)
    )
    assert found is not None
    assert Path(found).name == "tcc.exe"
    assert Path(found).is_file()


def test_env_override_is_honoured(tmp_path, monkeypatch):
    archive = _make_tcc_zip(tmp_path / "tcc.zip")
    dest = tmp_path / "dest"
    dest.mkdir()
    monkeypatch.setenv("PENGU_TCC_SHA256", _sha256(archive))
    found = pengu_tcc._download_windows_tcc(str(dest), url=archive.as_uri())
    assert found is not None


def test_env_override_with_a_bad_digest_still_fails(tmp_path, monkeypatch):
    archive = _make_tcc_zip(tmp_path / "tcc.zip")
    dest = tmp_path / "dest"
    dest.mkdir()
    monkeypatch.setenv("PENGU_TCC_SHA256", "a" * 64)
    with pytest.raises(TccIntegrityError):
        pengu_tcc._download_windows_tcc(str(dest), url=archive.as_uri())


@pytest.mark.parametrize("bad", ["", "deadbeef"])
def test_an_unpinned_digest_is_refused(tmp_path, bad):
    """No digest (or a truncated one) must abort, not silently skip the check."""
    dest = tmp_path / "dest"
    dest.mkdir()
    with pytest.raises(TccIntegrityError):
        pengu_tcc._download_windows_tcc(
            str(dest), url="https://example.invalid/x.zip", expected_sha256=bad
        )


def test_network_failure_is_not_reported_as_a_corrupt_archive(tmp_path, monkeypatch):
    """A dead mirror is 'no TCC' (optional); a bad digest is fatal.  Different."""

    def boom(*_a, **_k):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    dest = tmp_path / "dest"
    dest.mkdir()
    assert pengu_tcc._download_windows_tcc(str(dest)) is None


def test_a_hostile_zip_is_refused_by_the_shared_validator(tmp_path, monkeypatch):
    """Item 9.4 in situ: `../evil` inside the TCC archive never escapes dest."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.exe", b"MZ")
    archive = tmp_path / "evil.zip"
    archive.write_bytes(buf.getvalue())

    dest = tmp_path / "dest"
    dest.mkdir()
    with pytest.raises(UnsafeArchiveError):
        pengu_tcc._download_windows_tcc(
            str(dest), url=archive.as_uri(), expected_sha256=_sha256(archive)
        )
    assert not (tmp_path / "evil.exe").exists()
    assert list(dest.iterdir()) == []


def test_ensure_tcc_propagates_the_integrity_error(tmp_path, monkeypatch):
    """`make_release.py` must not turn a mismatch into 'release without TCC'."""
    monkeypatch.setattr(pengu_tcc.sys, "platform", "win32")

    def fake_download(dest_dir, url=None, expected_sha256=None):
        raise TccIntegrityError("boom")

    monkeypatch.setattr(pengu_tcc, "_download_windows_tcc", fake_download)
    with pytest.raises(TccIntegrityError):
        pengu_tcc.ensure_tcc(str(tmp_path / "tcc-dist"))


def test_release_workflow_uses_the_shared_module_instead_of_reimplementing_it():
    """Item 9.3: the workflow must not carry its own digest logic."""
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "pengu_tcc" in text, "release.yml must call the shared verifier"
    assert "::notice::TinyCC digest" not in text, "a notice is not a gate"
    # The check that only prints on mismatch is what the audit refuted.
    assert "Get-FileHash" not in text, "the digest check must not be re-implemented in pwsh"


def test_make_release_does_not_swallow_the_mismatch():
    text = (ROOT / "make_release.py").read_text(encoding="utf-8")
    body = text.split("def ensure_tcc_for_release", 1)[1].split("\ndef ", 1)[0]
    assert "except TccIntegrityError" not in body.replace(" ", ""), (
        "a digest mismatch must abort the release, not fall back to gcc"
    )
