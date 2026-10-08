"""Phase 9, item 9.1 — the external-library manifest verifies what it downloads.

Regression contract: an archive whose stream does not hash to the pinned digest
is refused *before* anything is extracted, and a cached directory is only reused
when the digest that produced it is the one currently pinned.
"""

from __future__ import annotations

import hashlib
import io
import re
import tarfile
from pathlib import Path

import pytest

import extern_manifest
from extern_manifest import DigestMismatchError, download_and_extract_externs

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _make_tar_gz(tmp_path: Path, name: str, payload: str = "int x;\n") -> Path:
    """Write ``<tmp>/payload/<name>`` into a real .tar.gz and return its path."""
    archive = tmp_path / f"{name}.tar.gz"
    member = tmp_path / "payload" / name / "file.c"
    member.parent.mkdir(parents=True, exist_ok=True)
    member.write_text(payload, encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(member, arcname=f"{name}/file.c")
    return archive


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_every_manifest_entry_pins_a_sha256():
    """No entry may be downloaded without a digest (the old behaviour)."""
    assert extern_manifest.MANIFEST, "the manifest must not be empty"
    for name, entry in extern_manifest.MANIFEST.items():
        digest = entry.get("sha256", "")
        assert HEX64.match(digest), f"{name}: sha256 is not pinned/malformed: {digest!r}"
        assert entry.get("url", "").startswith("https://"), f"{name}: url must be https"


def test_manifest_urls_view_matches_the_manifest():
    assert extern_manifest.MANIFEST_URLS == {
        name: entry["url"] for name, entry in extern_manifest.MANIFEST.items()
    }


def test_wrong_digest_fails_before_extracting(tmp_path):
    """C2: revert the verification and this test extracts the payload instead."""
    archive = _make_tar_gz(tmp_path, "fake-lib")
    target = tmp_path / "extern"
    manifest = {"fake-lib": {"url": archive.as_uri(), "sha256": "0" * 64}}
    dirs = {"fake-lib": "fake-lib"}

    with pytest.raises(DigestMismatchError) as excinfo:
        download_and_extract_externs(target, manifest=manifest, expected_dirs=dirs)

    message = str(excinfo.value)
    assert "fake-lib" in message and "0" * 64 in message
    assert not (target / "fake-lib").exists(), "nothing may be extracted on a mismatch"
    # The partial archive must not be left behind either: extern/ is untouched.
    assert list(target.iterdir()) == [], sorted(p.name for p in target.iterdir())


def test_correct_digest_extracts_and_records_the_stamp(tmp_path):
    """Positive control: the same path succeeds when the digest matches."""
    archive = _make_tar_gz(tmp_path, "good-lib")
    digest = _sha256(archive)
    target = tmp_path / "extern"
    manifest = {"good-lib": {"url": archive.as_uri(), "sha256": digest}}
    dirs = {"good-lib": "good-lib"}

    download_and_extract_externs(target, manifest=manifest, expected_dirs=dirs)

    assert (target / "good-lib" / "file.c").is_file()
    stamp = extern_manifest._read_stamp(target)
    assert stamp["good-lib"] == digest


def test_cached_directory_without_a_verified_stamp_is_not_trusted(tmp_path, capsys):
    """The bug the stamp fixes: 'the folder exists' used to mean 'trust me'."""
    archive = _make_tar_gz(tmp_path, "cached-lib", payload="int a;\n")
    digest = _sha256(archive)
    target = tmp_path / "extern"
    manifest = {"cached-lib": {"url": archive.as_uri(), "sha256": digest}}
    dirs = {"cached-lib": "cached-lib"}

    # A directory that predates the pin: present, but with no stamp.
    (target / "cached-lib").mkdir(parents=True)
    (target / "cached-lib" / "orphan.c").write_text("int stale;\n", encoding="utf-8")

    download_and_extract_externs(target, manifest=manifest, expected_dirs=dirs)
    output = capsys.readouterr().out
    assert "RE-VERIFYING" in output
    assert extern_manifest._read_stamp(target)["cached-lib"] == digest


def test_stamped_directory_is_reused_without_downloading(tmp_path):
    """A verified cache is reused; a broken URL proves no download happened."""
    archive = _make_tar_gz(tmp_path, "reused-lib")
    digest = _sha256(archive)
    target = tmp_path / "extern"
    manifest = {"reused-lib": {"url": archive.as_uri(), "sha256": digest}}
    dirs = {"reused-lib": "reused-lib"}

    download_and_extract_externs(target, manifest=manifest, expected_dirs=dirs)

    offline = {"reused-lib": {"url": "https://127.0.0.1:9/nope.tar.gz", "sha256": digest}}
    download_and_extract_externs(target, manifest=offline, expected_dirs=dirs)
    assert (target / "reused-lib" / "file.c").is_file()


def test_verify_mode_returns_non_zero_and_leaves_extern_empty(tmp_path, monkeypatch):
    """`python extern_manifest.py --verify` with a corrupt archive: rc!=0, no writes."""
    archive = _make_tar_gz(tmp_path, "corrupt-lib")
    monkeypatch.setattr(
        extern_manifest,
        "MANIFEST",
        {"corrupt-lib": {"url": archive.as_uri(), "sha256": "f" * 64}},
    )
    target = tmp_path / "extern"
    rc = extern_manifest.main(["--verify", "--extern-dir", str(target)])
    assert rc == 1
    assert not target.exists() or list(target.iterdir()) == []


def test_verify_mode_succeeds_with_the_right_digest(tmp_path, monkeypatch, capsys):
    archive = _make_tar_gz(tmp_path, "ok-lib")
    monkeypatch.setattr(
        extern_manifest,
        "MANIFEST",
        {"ok-lib": {"url": archive.as_uri(), "sha256": _sha256(archive)}},
    )
    target = tmp_path / "extern"
    assert extern_manifest.main(["--verify", "--extern-dir", str(target)]) == 0
    assert "nothing extracted" in capsys.readouterr().out


def test_empty_digest_is_refused(tmp_path):
    """A missing pin must fail loudly, not silently skip verification."""
    archive = _make_tar_gz(tmp_path, "unpinned-lib")
    target = tmp_path / "extern"
    manifest = {"unpinned-lib": {"url": archive.as_uri(), "sha256": ""}}
    with pytest.raises(DigestMismatchError):
        download_and_extract_externs(
            target, manifest=manifest, expected_dirs={"unpinned-lib": "unpinned-lib"}
        )
    assert not (target / "unpinned-lib").exists()


def test_main_reports_a_clean_failure_on_a_bad_digest(tmp_path, monkeypatch, capsys):
    archive = _make_tar_gz(tmp_path, "bad-lib")
    monkeypatch.setattr(
        extern_manifest,
        "MANIFEST",
        {"bad-lib": {"url": archive.as_uri(), "sha256": "1" * 64}},
    )
    rc = extern_manifest.main(["--extern-dir", str(tmp_path / "extern")])
    assert rc == 1
    assert "[FATAL]" in capsys.readouterr().err


def test_manifest_is_not_a_url_dict_anymore():
    """The shape the audit refuted: `{name: url}` had nowhere to store a digest."""
    sample = next(iter(extern_manifest.MANIFEST.values()))
    assert set(sample) >= {"url", "sha256"}


def test_digest_script_check_passes_offline():
    """The pinning tool agrees with the manifest (no network involved)."""
    tool = _load_digest_tool()
    assert tool.check() == 0


def _load_digest_tool():
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "extern_digests.py"
    spec = importlib.util.spec_from_file_location("extern_digests_tool", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declared_archives_are_tarballs_of_a_known_kind():
    """A `.tar.gz`/`.tar.xz`/`.tar.bz2` URL matches the extractor used."""
    for name, entry in extern_manifest.MANIFEST.items():
        url = entry["url"]
        assert any(
            url.endswith(suffix) for suffix in (".tar.gz", ".tar.xz", ".tar.bz2")
        ), f"{name}: {url} is not a tarball this module can extract"


def test_streaming_hasher_reads_in_chunks(monkeypatch, tmp_path):
    """The digest is computed on the stream, never with a single `resp.read()`."""
    payload = b"x" * (3 * extern_manifest.CHUNK_SIZE + 5)
    requested_sizes = []

    class FakeResponse:
        def __init__(self):
            self._buf = io.BytesIO(payload)

        def read(self, size=-1):
            requested_sizes.append(size)
            return self._buf.read(size)

        def getheader(self, _name):
            return str(len(payload))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        extern_manifest.urllib.request, "urlopen", lambda *a, **k: FakeResponse()
    )
    target = tmp_path / "archive.bin"
    computed = extern_manifest._download_verified(
        "fake",
        "https://example.invalid/fake.tar.gz",
        hashlib.sha256(payload).hexdigest(),
        target,
    )
    assert computed == hashlib.sha256(payload).hexdigest()
    assert requested_sizes, "the response must be read at least once"
    assert set(requested_sizes) == {extern_manifest.CHUNK_SIZE}
    assert len(requested_sizes) >= 4, requested_sizes
    assert target.read_bytes() == payload


def test_sha256_of_known_bytes_is_the_pinned_one():
    """Sanity: the hashing used here is plain SHA-256, not something bespoke."""
    assert (
        extern_manifest.hashlib.sha256(b"pengu").hexdigest()
        == "50a7fd573aba1d07865d3ce1b0471bb47d7656e8300ee8af07c217659663d306"
    )

