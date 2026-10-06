"""Phase 4 item 4.16: every subcommand documents its contract in `--help`.

Only one of the 25 subparsers had an epilog before this item, so `pengu build
--help` explained the flags but never the exit codes or a runnable example. The
contract is checked structurally (the parser objects), not by grepping text.
"""

import re
import subprocess
import sys

import pytest

from pengu_project import create_cli_parser
from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]


def _subparsers():
    parser = create_cli_parser()
    action = next(a for a in parser._actions if getattr(a, "choices", None))
    return action.choices


def test_every_subcommand_has_a_description_and_epilog():
    subs = _subparsers()
    assert len(subs) == 27, sorted(subs)   # 25 + benchmark (4.15) + new (4.14)
    for name, sub in sorted(subs.items()):
        assert sub.description, f"{name} has no description"
        assert len(sub.description.split()) >= 4, (name, sub.description)
        assert sub.epilog, f"{name} has no epilog"
        assert "Exit codes" in sub.epilog, (name, sub.epilog)
        assert "Example" in sub.epilog, (name, sub.epilog)


def test_every_epilog_names_a_concrete_command():
    for name, sub in sorted(_subparsers().items()):
        assert f"pengu {name}" in sub.epilog, (name, sub.epilog)


@pytest.mark.parametrize("command", sorted(_subparsers()))
def test_help_renders_the_contract(command):
    res = subprocess.run([*PENGU, command, "--help"],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert "Exit codes" in res.stdout, res.stdout
    assert "Example" in res.stdout, res.stdout
    assert f"pengu {command}" in res.stdout


def test_help_lists_the_exit_codes_of_the_main_paths():
    """Spot-check the codes that behaviour tests rely on."""
    def helps(cmd):
        return subprocess.run([*PENGU, cmd, "--help"], capture_output=True,
                              text=True, timeout=60).stdout

    assert "0 built, 1 build error, 2 bad usage" in helps("build")
    assert "0 all passed, 1 a test failed" in helps("test")
    assert "1 --check found changes" in helps("fmt")
    assert "128+signal" in helps("eval")
