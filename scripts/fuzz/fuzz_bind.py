#!/usr/bin/env python3
"""Fuzz the C header -> binding generator (roadmap 5.5).

Inputs are *generated headers*: random declarations plus seeded real headers
from the repo, so both the preprocessor path and the pycparser path are hit.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import REPO, load_corpus, run_harness  # noqa: E402

TYPES = ["int", "unsigned int", "float", "double", "char *", "void *", "size_t",
         "long long", "struct Fwd *", "uint32_t", "const char *"]
QUALIFIERS = ["", "const ", "static ", "volatile ", "static const "]


def _gen_header(rng: random.Random) -> bytes:
    lines = ["#ifndef FUZZ_H", "#define FUZZ_H", "typedef unsigned long size_t;",
             "typedef unsigned int uint32_t;", "struct Fwd;"]
    for i in range(rng.randint(1, 25)):
        kind = rng.randrange(6)
        t = rng.choice(TYPES)
        if kind == 0:
            lines.append(f"{rng.choice(QUALIFIERS)}{t} fn_{i}({t} a, {t} b);")
        elif kind == 1:
            lines.append(f"struct S{i} {{ {t} a; {t} b; }};")
        elif kind == 2:
            lines.append(f"enum E{i} {{ E{i}_A = {rng.randint(-5, 500)}, E{i}_B }};")
        elif kind == 3:
            lines.append(f"#define MACRO_{i} ({rng.randint(0, 99)})")
        elif kind == 4:
            lines.append(f"typedef {t} Alias{i};")
        else:
            lines.append(f"union U{i} {{ {t} a; int b; }};")
    lines.append("#endif")
    return ("\n".join(lines) + "\n").encode()


def target(data: bytes) -> None:
    from pengu_bind import generate_bind_file

    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="pengu_fuzz_bind_"))
    header = tmp / "fuzz.h"
    header.write_bytes(data)
    try:
        generate_bind_file(str(header), output=str(tmp / "out.d.pengu"))
    except EXPECTED_BIND:
        pass


def main() -> int:
    rng = random.Random(1234)
    seeds = [_gen_header(rng) for _ in range(40)]
    seeds += load_corpus(["std_c:.h", "build/include:.h", "extern:.h"], limit=20)
    return run_harness("bind", target, seeds, iterations=200)


if __name__ == "__main__":
    from fuzz_common import EXPECTED

    EXPECTED_BIND = EXPECTED
    sys.exit(main())
