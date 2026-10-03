#!/usr/bin/env python3
"""Fuzz the lexer + LALR parser (roadmap 5.5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import REPO, load_corpus, run_harness  # noqa: E402


def target(data: bytes) -> None:
    from pengu_parser.pengu_parser import PenguParser

    text = data.decode("utf-8", errors="replace")
    PenguParser().parse(text)


if __name__ == "__main__":
    corpus = load_corpus(["tests/std_programs:.pengu", "tests:.pengu", "std:.pengu"], limit=300)
    sys.exit(run_harness("parser", target, corpus))
