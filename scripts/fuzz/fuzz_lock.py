#!/usr/bin/env python3
"""Fuzz the pengu.lock TOML reader/writer round trip (roadmap 5.5)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import run_harness  # noqa: E402


def target(data: bytes) -> None:
    from pengu_lock import dumps, read_lock, write_lock

    tmp = tempfile.mkdtemp(prefix="pengu_fuzz_lock_")
    path = Path(tmp) / "pengu.lock"
    path.write_bytes(data)
    lock = read_lock(tmp)
    if lock is not None:
        write_lock(tmp, lock)
        assert "version = " in dumps(lock)


if __name__ == "__main__":
    seeds = [
        b'version = 1\ntargets = ["linux"]\n\n[[package]]\nname = "a"\ncommit = "abc"\nsha256 = "d"\n',
        b"version = 1\n",
        b"",
    ]
    sys.exit(run_harness("lock", target, seeds, iterations=800))
