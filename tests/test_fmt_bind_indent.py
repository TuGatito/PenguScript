"""Phase 4 item 4.2 (A7): the formatting contract of generated artifacts.

``pengu bind`` emitted a fixed 2-space indent in its template while the stdlib
(and the ``pengu fmt`` default) use 4.  The result was that the tool's own output
did not pass its own formatter: ``pengu fmt --check std/`` reported 13 of the 25
``std/*.d.pengu`` bindings as needing reformatting.

The generator now emits 4 spaces.  The assertions here are behavioural: the
generated binding must be *parseable* and must be *clean* under the formatter,
which is the property the tool is supposed to guarantee about its own output.
"""

import subprocess
import sys

import pytest

from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

HEADER = """\
/* Minimal header for the bind indentation test. */
typedef struct Penguin {
    int beak;
    int flipper;
} Penguin;
enum Mood { MOOD_CALM = 0, MOOD_HUNGRY = 1 };
int pengu_feed(Penguin *p, int fish);
"""


@pytest.fixture()
def binding(tmp_path):
    header = tmp_path / "min_bind.h"
    header.write_text(HEADER, encoding="utf-8")
    out = tmp_path / "min_bind.d.pengu"
    res = subprocess.run(
        [*PENGU, "bind", str(header), "--output", str(out)],
        capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, res.stderr
    return out


def _nesting(path):
    """(kind-name, member indent widths) for records/enums in a binding."""
    current = None
    nesting = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            kind, _, rest = line.partition(" ")
            current = rest.rstrip(":") if kind in ("rune", "omen", "echo") else None
            if current is not None:
                nesting[current] = []
            continue
        if current is not None:
            nesting[current].append(len(line) - len(line.lstrip()))
    return nesting


def test_generated_binding_is_clean_under_pengu_fmt(binding):
    res = subprocess.run(
        [*PENGU, "fmt", "--check", str(binding)],
        capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, f"generated binding is not formatted:\n{res.stdout}{res.stderr}"


def test_records_and_enums_are_indented_by_four(binding):
    nesting = _nesting(binding)
    assert nesting, binding.read_text(encoding="utf-8")
    for name, widths in nesting.items():
        assert widths, name
        assert min(widths) == 4, f"{name}: {widths}"


def test_generated_binding_is_valid_penguscript(binding):
    res = subprocess.run(
        [*PENGU, "check", "--entry", str(binding)],
        capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"


def test_std_bindings_are_clean_under_pengu_fmt():
    """``pengu fmt --check std/`` must be idempotent: 0 files would change."""
    res = subprocess.run(
        [*PENGU, "fmt", "--check", str(REPO / "std")],
        capture_output=True, text=True, timeout=300,
    )
    assert res.returncode == 0, (
        "pengu fmt --check std/ reports changes:\n"
        + "\n".join(ln for ln in res.stdout.splitlines() if "would" in ln)
    )


def test_std_module_sources_are_clean_under_pengu_fmt():
    """The 52 ``std/*.pengu`` modules are already in the 4-space convention."""
    modules = sorted((REPO / "std").glob("*.pengu"))
    assert len(modules) > 40
    res = subprocess.run(
        [*PENGU, "fmt", "--check", *[str(m) for m in modules]],
        capture_output=True, text=True, timeout=300,
    )
    assert res.returncode == 0, (
        "\n".join(ln for ln in res.stdout.splitlines() if "would" in ln)
    )
