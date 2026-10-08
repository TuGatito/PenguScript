"""Roadmap Phase 5 / §5.5 — the fuzzing harnesses actually run and stay clean.

Runs each harness in its deterministic smoke mode with a small budget, so a
regression in robustness fails the normal suite without needing atheris.  Any
minimised crash committed to ``tests/fuzz_corpus/`` is replayed here too.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO

FUZZ_DIR = REPO / "scripts" / "fuzz"
CORPUS_DIR = REPO / "tests" / "fuzz_corpus"


def _fuzz_common():
    """Imports scripts/fuzz/fuzz_common.py without polluting sys.path globally."""
    if str(FUZZ_DIR) not in sys.path:
        sys.path.insert(0, str(FUZZ_DIR))
    import fuzz_common

    return fuzz_common


def _load(name: str):
    _fuzz_common()
    spec = importlib.util.spec_from_file_location(f"fuzz_{name}", FUZZ_DIR / f"fuzz_{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(FUZZ_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        if str(FUZZ_DIR) in sys.path:
            sys.path.remove(str(FUZZ_DIR))
    return module


def _run(name: str, iterations: int) -> None:
    common = _fuzz_common()
    EXPECTED, mutate = common.EXPECTED, common.mutate
    module = _load(name)
    target = module.target
    seeds = [b"weave main into int:\n  return 0\n", b"", b"\xff\xfe\x00", b"@deprecated(\"x\")\n"]

    # committed corpus (if any) first, then mutations
    if CORPUS_DIR.is_dir():
        seeds += [p.read_bytes() for p in sorted(CORPUS_DIR.glob(f"{name}_*"))]

    import random

    rng = random.Random(4242)
    cases = list(seeds) + [mutate(rng.choice(seeds), rng) for _ in range(iterations)]
    for data in cases:
        try:
            target(data)
        except EXPECTED:
            continue
        except RecursionError:
            continue  # a "too complex" diagnostic path, not a memory-safety bug


@pytest.mark.parametrize("harness", ["parser", "semver", "lock", "lsp"])
def test_harness_survives_hostile_input(harness):
    _run(harness, iterations=60)


def test_bind_harness_survives_generated_headers():
    """fuzz_bind generates its own headers, so it exercises the full pipeline."""
    if not (FUZZ_DIR / "fuzz_bind.py").is_file():
        pytest.skip("bind harness missing")
    module = _load("bind")
    import random

    EXPECTED = _fuzz_common().EXPECTED

    rng = random.Random(99)
    for _ in range(8):
        data = module._gen_header(rng)
        try:
            module.target(data)
        except EXPECTED:
            pass


def test_harness_helpers():
    common = _fuzz_common()
    EXPECTED, load_corpus, mutate = common.EXPECTED, common.load_corpus, common.mutate

    assert mutate(b"", __import__("random").Random(1))
    assert mutate(b"abcdef", __import__("random").Random(2))
    assert load_corpus(["std:.pengu"], limit=5)
    from pengu_parser.pengu_errors import PenguError

    assert issubclass(PenguError, EXPECTED)


def test_fuzzing_docs_and_ci_exist():
    assert (REPO / "docs" / "FUZZING.md").is_file()
    # Phase 12 merged fuzz.yml into the nightly workflow's `fuzz` job.
    workflow = (REPO / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8")
    for needle in ("scripts/fuzz/fuzz_", "schedule", "PENGU_FUZZ_SMOKE"):
        assert needle in workflow, needle


def test_all_harnesses_are_present():
    for name in ("parser", "bind", "semver", "lock", "lsp"):
        assert (FUZZ_DIR / f"fuzz_{name}.py").is_file(), name
