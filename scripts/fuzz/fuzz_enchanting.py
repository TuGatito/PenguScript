#!/usr/bin/env python3
"""Fuzz `enchanting` blocks, including the Phase 2 primitive receivers.

The parser harness already throws random bytes at the lexer.  This one throws
*plausible programs* at the whole front end (parse + semantic check) for the
construct Phase 2 changed:

* `enchanting int:` / `char` / `bool` / every primitive spelling,
* `enchanting shard T where T: <concept>:` with one or more methods,
* method bodies built from `self`-expressions (arithmetic, comparison, method
  calls on `self`, `set self`, `self->field`) so the value-vs-reference rule and
  the E0003/E0006 diagnostics are exercised continuously.

A generated program is allowed to be *invalid* — that is a diagnostic, and
`fuzz_common` treats `PenguError` as expected.  Anything else (an AttributeError
escaping the checker, an unreachable `assert`, a crash in the code generator) is
a finding, which is exactly what a fuzzer is for.

Usage::

    python scripts/fuzz/fuzz_enchanting.py                 # smoke pass
    python scripts/fuzz/fuzz_enchanting.py -max_total_time=300   # with atheris
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import REPO, load_corpus, run_harness  # noqa: E402

#: Receivers worth generating: concrete primitives and the bounded shard form.
RECEIVERS = ["int", "i32", "i64", "u8", "u64", "float", "f64", "char", "bool",
             "byte", "usize", "isize", "shard T where T: Integrum",
             "shard T where T: Num", "shard T", "string"]

#: Body fragments.  Each one is a legal *shape*; whether it type-checks depends
#: on the receiver, which is the point.
BODIES = [
    "return self",
    "return self + self",
    "return self - self",
    "return self * 2",
    "return self / 2",
    "return self % 2",
    "return self % (2 to T)",
    "return self == donum T",
    "return self < self",
    "return self > 0",
    "return 0 - self",
    "if self == self:\n            return self\n        return self",
    "if self < self:\n            return 1\n        return 0",
    "return not self",
    "set self is self\n        return self",
    "return self->value",
    "return self.field",
    "return (self % (2 to T)) == donum T",
    "return self to int",
    "return self to f64",
    "return essence of self",
]

RETURN_TYPES = ["int", "i64", "bool", "char", "f64", "void", "self", "T", "string"]


def _gen_program(rng: random.Random) -> bytes:
    """One random `enchanting` program, as UTF-8 bytes."""
    lines = []
    for _ in range(rng.randint(1, 3)):
        receiver = rng.choice(RECEIVERS)
        # `enchanting shard T ...:` takes the shard itself as the target, which is
        # the form the grammar had to learn; the others are plain types.
        lines.append(f"enchanting {receiver}:")
        for i in range(rng.randint(1, 3)):
            body = rng.choice(BODIES)
            ret = rng.choice(RETURN_TYPES)
            params = ""
            if rng.random() < 0.3:
                params = " with lo as int, hi as int"
            if ret == "void":
                lines.append(f"    weave m{i}{params} into void:")
                lines.append("        return")
            elif ret == "self":
                lines.append(f"    weave m{i}{params} into int:")
            else:
                lines.append(f"    weave m{i}{params} into {ret}:")
            for body_line in body.splitlines():
                lines.append("    " + body_line)
    # A call site, so the inferrer and (when the program is clean) the
    # monomorphizer are exercised too.
    lines.append("")
    lines.append("weave probe with x as int, y as i64 into int:")
    lines.append(f"    if calling x.m{rng.randint(0, 2)}:")
    lines.append("        return 1")
    lines.append("    return 0")
    return ("\n".join(lines) + "\n").encode("utf-8")


def target(data: bytes) -> None:
    """Parses + checks a generated program; diagnostics are expected."""
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    rng = random.Random(int.from_bytes(data[:16].ljust(16, b"\0"), "little"))
    source = _gen_program(rng).decode("utf-8")
    tree = PenguParser().parse(source)
    checker = PenguChecker(base_dir=str(REPO))
    checker.check(tree, source=source, filename="fuzz_enchanting.pengu")


if __name__ == "__main__":
    corpus = load_corpus(["std:.pengu"], limit=20)
    corpus += [b"enchanting int:\n    weave double into int:\n        return self + self\n"]
    sys.exit(run_harness("enchanting", target, corpus, iterations=600))
