"""Phase 4 item 4.5: `--no-color` and `NO_COLOR` must disable ANSI.

Before this item nothing read the flag or the variable: the CLI printed
`\\033[1;36m`-style escapes unconditionally, so `pengu check | cat -v` showed
`^[[` and `--no-color` was accepted but inert. Every user-facing line now goes
through `emit()` (pengu_project.py), which decides colour in one place:

    --no-color / NO_COLOR present  >  isatty(stream)  >  plain

These tests measure the **bytes the CLI writes** — that output *is* the
observable contract here, and the strongest check is that the coloured and
plain runs differ *only* by ANSI sequences.
"""

import os
import re
import shlex
import shutil
import subprocess
import sys

import pytest

from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]
ANSI_RE = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")


def _pty_argv(command):
    """`script(1)` argv that runs `command` on a pseudo-terminal, portably.

    util-linux (Linux) takes the command as one `-c` *string* and has its own
    `-e` flag; BSD (macOS) takes it as trailing argv and has neither option, so
    `script -qec ...` dies there with "illegal option -- e". Windows has no
    `script`, which the callers already guard with `shutil.which`.
    """
    if sys.platform == "darwin" or "bsd" in sys.platform:
        return ["script", "-q", os.devnull, *command]
    return ["script", "-qec", shlex.join(command), os.devnull]


def _run(args, cwd=None, env=None, text=False):
    base_env = dict(os.environ)
    base_env.pop("NO_COLOR", None)          # the runner may export it
    if env:
        base_env.update(env)
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=text, timeout=120,
        cwd=str(cwd) if cwd else None, env=base_env,
    )


@pytest.fixture()
def project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    return tmp_path / "ok"


# ---------------------------------------------------------------------------
# The flag and the variable both remove ANSI
# ---------------------------------------------------------------------------


def test_no_color_flag_removes_ansi(project):
    res = _run(["--no-color", "check"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert not ANSI_RE.search(res.stdout), res.stdout
    assert b"Checking" in res.stdout


def test_no_color_flag_after_the_subcommand(project):
    res = _run(["check", "--no-color"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert not ANSI_RE.search(res.stdout), res.stdout


@pytest.mark.parametrize("value", ["1", "", "0", "anything"])
def test_no_color_env_var_is_honoured_regardless_of_value(project, value):
    """https://no-color.org: the *presence* of NO_COLOR disables colour."""
    res = _run(["check"], cwd=project, env={"NO_COLOR": value})
    assert res.returncode == 0, res.stderr
    assert not ANSI_RE.search(res.stdout), res.stdout


@pytest.mark.skipif(shutil.which("script") is None, reason="needs a pty (script)")
def test_no_color_only_changes_the_ansi_sequences(project):
    """Coloured (pty) and plain runs must be identical once escapes are stripped."""
    env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
    coloured = subprocess.run(
        _pty_argv([*PENGU, "check"]),
        capture_output=True, timeout=180, cwd=str(project), env=env,
    )
    assert coloured.returncode == 0, coloured.stderr
    assert ANSI_RE.search(coloured.stdout), coloured.stdout

    plain = _run(["--no-color", "check"], cwd=project)
    assert plain.returncode == 0, plain.stderr

    def _normalise(raw):
        # `script(1)` echoes the pty's own control bytes: a CR before every LF,
        # and BSD/macOS additionally echoes the end-of-input as the literal
        # `^D` erased by two backspaces.  Resolve the backspaces the way a
        # terminal would, drop the CRs, and mask the elapsed time (not part of
        # the contract) as before.
        plain_text = ANSI_RE.sub(b"", raw)
        resolved = bytearray()
        for ch in plain_text:
            if ch == 0x08:          # backspace: erase the previous byte
                if resolved:
                    resolved.pop()
            elif ch != 0x0D:        # CR: the pty's line-ending echo
                resolved.append(ch)
        return re.sub(rb"in \d+\.\d+s", b"in X.XXs", bytes(resolved)).strip()

    assert _normalise(coloured.stdout) == _normalise(plain.stdout)


# ---------------------------------------------------------------------------
# Errors keep their message, without colour
# ---------------------------------------------------------------------------


def test_errors_are_still_printed_without_color(project):
    broken = project / "broken.pengu"
    broken.write_text("weave main into int:\n    var x as int is\n", encoding="utf-8")
    res = _run(["--no-color", "check", str(broken)], cwd=project)
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert not ANSI_RE.search(combined), combined
    assert b"rror" in combined, combined


# ---------------------------------------------------------------------------
# The default: colour only on a terminal
# ---------------------------------------------------------------------------


def test_piped_output_has_no_ansi(project):
    """No TTY (captured by the test runner) means no colour by default."""
    res = _run(["check"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert not ANSI_RE.search(res.stdout), res.stdout


@pytest.mark.skipif(shutil.which("script") is None, reason="needs a pty (script)")
def test_tty_output_has_ansi(project):
    """On a real terminal the banner is coloured, which is the point of the flag."""
    env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
    res = subprocess.run(
        _pty_argv([*PENGU, "check"]),
        capture_output=True, timeout=180, cwd=str(project), env=env,
    )
    assert res.returncode == 0, res.stderr
    assert ANSI_RE.search(res.stdout), res.stdout


# ---------------------------------------------------------------------------
# The unit-level contract (fast, no subprocess)
# ---------------------------------------------------------------------------


class _FakeStream:
    def __init__(self, tty):
        self._tty = tty
        self.chunks = []

    def write(self, text):
        self.chunks.append(text)

    def isatty(self):
        return self._tty


def test_emit_unit_precedence(monkeypatch):
    import pengu_project as pp

    monkeypatch.delenv("NO_COLOR", raising=False)

    pp.configure_output(stream=_FakeStream(True))
    assert pp._OUTPUT.color is True

    # explicit flag wins over a TTY
    pp.configure_output(no_color=True, stream=_FakeStream(True))
    assert pp._OUTPUT.color is False
    out = _FakeStream(True)
    pp.emit("plain", color="red", file=out)
    assert out.chunks == ["plain\n"]

    # NO_COLOR present (even empty) wins over a TTY
    monkeypatch.setenv("NO_COLOR", "")
    pp.configure_output(stream=_FakeStream(True))
    assert pp._OUTPUT.color is False

    # a TTY with no opt-out keeps colour
    monkeypatch.delenv("NO_COLOR", raising=False)
    pp.configure_output(stream=_FakeStream(True))
    out2 = _FakeStream(True)
    pp.emit("coloured", color="cyan", file=out2)
    assert out2.chunks == ["\033[1;36mcoloured\033[0m\n"]

    # a pipe is plain
    pp.configure_output(stream=_FakeStream(False))
    out3 = _FakeStream(False)
    pp.emit("piped", color="cyan", file=out3)
    assert out3.chunks == ["piped\n"]

    pp.configure_output()   # restore process defaults for other tests
