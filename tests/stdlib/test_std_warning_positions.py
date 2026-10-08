"""Roadmap Phase 6 / item 6.3 — warnings must carry their AST position.

``pengu check`` renders diagnostics from the checker's warning channel, which is
a ``List[str]``.  The W0001 (``transmute``) warnings were appended with no
position at all, so every one surfaced as ``file:0:0`` and was impossible to
locate; the pre-Phase-6 audit measured exactly that on ``std/filum.pengu``.

By the time this item was executed, Phase 2 had already removed every
``transmute`` from the stdlib (which is why the stdlib now emits 0 W0001), so
the bug is reproduced here with a purpose-built source file.  The item was
genuinely open: the diagnostic path was still positionless.

The fix has the inferrer attach an ``on line L col C`` suffix to the warnings it
can locate, and teaches ``pengu check`` to parse that suffix back into the
structured diagnostic's ``line``/``col`` fields.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"

# Two transmutes at known positions: lines 5 and 9 (1-based), `transmute`
# starting at column 12 in both.
_SOURCE = """import std.spark

weave null_void into ref to void:
    let z as int is 0
    return transmute z to ref to void

weave null_char into ref to char:
    let z as int is 0
    return transmute z to ref to char

weave main into void:
    calling spark.println with "done"
"""

_W0001 = re.compile(r":(\d+):(\d+) \[W0001\]")


def _cli(args, cwd=None, timeout=300):
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(REPO), existing) if p)
    return subprocess.run(
        [PY, "-m", MODULE] + list(args),
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


@pytest.fixture
def warn_project(tmp_path):
    """Writes ``_SOURCE`` into a scratch dir and returns (dir, entry path)."""
    entry = tmp_path / "t_warn.pengu"
    entry.write_text(_SOURCE, encoding="utf-8")
    return tmp_path, entry


def _warn_positions(warn_project):
    _, entry = warn_project
    result = _cli(["check", "--entry", str(entry)])
    return _W0001.findall(result.stdout + result.stderr), result


def test_w0001_reports_real_line_and_column(warn_project):
    positions, result = _warn_positions(warn_project)
    assert positions, (
        f"no W0001 diagnostic emitted\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert ("5", "12") in positions, f"expected 5:12 among {positions}"
    assert ("9", "12") in positions, f"expected 9:12 among {positions}"
    assert ("0", "0") not in positions, (
        f"W0001 still reported without a position: {positions}"
    )


def test_w0001_fires_once_per_transmute_site(warn_project):
    positions, _ = _warn_positions(warn_project)
    assert len(positions) == 2, f"expected 2 W0001 diagnostics, got {positions}"


def test_w0001_json_output_has_position(warn_project):
    """The structured (JSON-lines) channel must carry line/col, not just text."""
    import json

    _, entry = warn_project
    result = _cli(["check", "--entry", str(entry), "--json"])
    diags = []
    for line in (result.stdout + result.stderr).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            diags.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    w0001 = [d for d in diags if d.get("code") == "W0001"]
    assert w0001, f"no structured W0001 diagnostic in:\n{result.stdout}\n{result.stderr}"
    lines = sorted(d.get("line") for d in w0001)
    assert lines == [5, 9], f"structured diagnostics lost position: {w0001}"
    assert all(d.get("col") == 12 for d in w0001), f"missing column: {w0001}"
