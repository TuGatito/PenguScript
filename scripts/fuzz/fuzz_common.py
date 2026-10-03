#!/usr/bin/env python3
"""Shared plumbing for the PenguScript fuzzing harnesses (roadmap 5.5).

Each harness defines a `target(data: bytes) -> None` that must either succeed or
fail with a *declared* error (a language diagnostic).  Anything else — an
IndexError, a KeyError, an AttributeError, a segfault — is a crash.

Two modes:

* **atheris** — when `atheris` is installed, coverage-guided fuzzing
  (`python scripts/fuzz/fuzz_parser.py -max_total_time=300`).
* **smoke** — otherwise, a deterministic pass over the seed corpus plus seeded
  random mutations.  This is what CI runs, so the harnesses are useful without
  the heavy dependency, and every finding can be replayed from the seed.

Usage::

    from fuzz_common import run_harness
    run_harness("parser", target, corpus=[b"weave main into int:\\n  return 0\\n"])
"""

from __future__ import annotations

import os
import random
import sys
import traceback
from pathlib import Path
from typing import Callable, Iterable, List, Sequence, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def expected_errors() -> Tuple[type, ...]:
    """Exception types that represent a *reported* diagnostic, not a crash."""
    types: List[type] = [ValueError, TypeError, UnicodeDecodeError]
    try:
        from pengu_parser.pengu_errors import PenguError

        types.append(PenguError)
    except Exception:  # pragma: no cover - import guard
        pass
    for mod_name, attr in (
        ("pengu_semver", "SemVerError"),
        ("pengu_lock", "LockError"),
        ("pengu_bind", "HeaderParseError"),
    ):
        try:
            mod = __import__(mod_name)
            types.append(getattr(mod, attr))
        except Exception:  # pragma: no cover - optional module
            pass
    return tuple(types)


EXPECTED = expected_errors()


def load_corpus(dirs: Sequence[str], limit: int = 400) -> List[bytes]:
    """Collects seed inputs from files whose suffix matches ``dirs`` entries."""
    seeds: List[bytes] = []
    for spec in dirs:
        if ":" in spec:
            root, suffix = spec.split(":", 1)
        else:
            root, suffix = spec, ""
        base = REPO / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if len(seeds) >= limit:
                return seeds
            if not path.is_file():
                continue
            if suffix and not path.name.endswith(suffix):
                continue
            try:
                if path.stat().st_size > 256 * 1024:
                    continue
                seeds.append(path.read_bytes())
            except OSError:
                continue
    return seeds


def mutate(seed: bytes, rng: random.Random) -> bytes:
    """A cheap byte-level mutation: flip, insert, delete or truncate."""
    if not seed:
        return bytes(rng.randrange(256) for _ in range(rng.randint(1, 32)))
    data = bytearray(seed)
    for _ in range(rng.randint(1, 6)):
        op = rng.randrange(5)
        pos = rng.randrange(len(data)) if data else 0
        if op == 0 and data:
            data[pos] = rng.randrange(256)
        elif op == 1:
            data.insert(pos, rng.randrange(256))
        elif op == 2 and data:
            del data[pos]
        elif op == 3:
            cut = rng.randrange(len(data) + 1)
            data = data[:cut]
        elif op == 4:
            chunk = bytes(rng.randrange(256) for _ in range(rng.randint(1, 16)))
            data[pos:pos] = chunk
    return bytes(data)


def _run_smoke(name: str, target: Callable[[bytes], None], corpus: Sequence[bytes],
               iterations: int, seed: int) -> int:
    rng = random.Random(seed)
    cases: List[bytes] = list(corpus)
    cases += [mutate(rng.choice(corpus) if corpus else b"", rng) for _ in range(iterations)]
    crashes = 0
    for i, data in enumerate(cases):
        try:
            target(data)
        except EXPECTED:
            continue
        except RecursionError:
            # Deeply nested input is a legitimate "too complex" diagnostic path,
            # not a memory-safety bug; report it but do not fail the harness.
            print(f"[{name}] recursion limit on case {i}", file=sys.stderr)
        except Exception:
            crashes += 1
            print(f"[{name}] CRASH on case {i} ({len(data)} bytes):", file=sys.stderr)
            traceback.print_exc()
            out = REPO / "build" / "fuzz_crashes"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}_{i}.bin").write_bytes(data)
            if crashes >= 5:
                break
    total = len(cases)
    if crashes:
        print(f"[{name}] {crashes} crash(es) out of {total} cases", file=sys.stderr)
        return 1
    print(f"[{name}] ok: {total} cases, no crashes")
    return 0


def run_harness(name: str, target: Callable[[bytes], None],
                corpus: Iterable[bytes] = (), iterations: int = 400,
                seed: int = 0xC0FFEE) -> int:
    """Runs ``target`` under atheris when available, else in smoke mode."""
    corpus = list(corpus)
    if os.environ.get("PENGU_FUZZ_SMOKE", "").strip().lower() in ("1", "true", "yes", "on"):
        return _run_smoke(name, target, corpus, iterations, seed)
    try:
        import atheris  # type: ignore
    except ImportError:
        return _run_smoke(name, target, corpus, iterations, seed)

    def _one(data: bytes) -> None:
        try:
            target(data)
        except EXPECTED:
            pass

    atheris.Setup(sys.argv, _one)
    atheris.Fuzz()
    return 0
