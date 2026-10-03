"""Phase 2 items 2.7 (`many` parameters) and 2.9 (ASCII identifiers).

Rule C1 (ROADMAP_2.0 Anexo C): every claim here is settled by compiling the
source and inspecting the diagnostic, not by grepping the manual.

Item 2.7 — the roadmap asked whether call-site *spread* (`f(...xs)`) exists. It
does not: `VARARGS` (`...`) is only a declaration-site token. `many T` is
accepted on a `weave` and rejected inside a `declare`, which is the opposite of
what LANGUAGE.md §4/§8 implied. Both facts are pinned here and documented.

Item 2.9 — identifiers are ASCII only. `NAME` is
``[a-zA-Z_][a-zA-Z0-9_]*``, so a non-ASCII identifier is an E0000. String
literals are full Unicode, which makes the restriction worth stating explicitly.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"


def check(tmp_path, source, name="t.pengu"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, "check", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    import re
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# Item 2.7 — `many` parameters and call-site spread
# ---------------------------------------------------------------------------

def test_many_is_accepted_on_a_weave(tmp_path):
    """`many T` in a `weave` signature parses today."""
    rc, out = check(
        tmp_path,
        "weave sum_many with xs as many int into int:\n  return 0\n"
        "weave main into int:\n  return calling sum_many with 1, 2\n",
    )
    assert rc == 0, out


def test_many_is_rejected_in_a_declare(tmp_path):
    """`many T` in a `declare` is rejected with E0005.

    This is the inverse of what LANGUAGE.md's concept table implied, so it is
    pinned: `declare` takes the C-style `...` form instead.
    """
    rc, out = check(
        tmp_path,
        "declare printf_like with fmt as string, args as many int into int\n"
        "weave main into int:\n"
        '  var r as int is calling printf_like with "x", 1, 2\n  return r\n',
    )
    assert rc != 0, out
    assert "E0005" in out, out
    assert "many" in out, out


def test_call_site_spread_is_not_supported(tmp_path):
    """`f(...xs)` must stay a syntax error until spread is implemented.

    Tripwire: if someone adds a spread production, this fails, which is the
    signal to implement the lowering (the C call has to expand a runtime
    container into N arguments) and update the docs -- not to ship the syntax
    alone.
    """
    rc, out = check(
        tmp_path,
        "weave sum_many with xs as many int into int:\n  return 0\n"
        "weave main into int:\n  var a as list of int is [1]\n"
        "  return calling sum_many with ...a\n",
    )
    assert rc != 0, (
        "call-site spread now parses. Implement the lowering and update "
        "LANGUAGE.md §8 before flipping this test.\n" + out
    )
    assert "E0000" in out, out


def test_variadic_call_with_listed_arguments_works(tmp_path):
    """The supported way to call a variadic: list the arguments."""
    rc, out = check(
        tmp_path,
        "weave three with a as int, b as int, c as int into int:\n"
        "  return a + b + c\n"
        "weave main into int:\n  return calling three with 1, 2, 3\n",
    )
    assert rc == 0, out


# ---------------------------------------------------------------------------
# Item 2.9 — identifiers are ASCII
# ---------------------------------------------------------------------------

NON_ASCII_IDENTIFIERS = ["日本語", "café", "naïve", "Ω", "变量"]


@pytest.mark.parametrize("name", NON_ASCII_IDENTIFIERS)
def test_non_ascii_identifiers_are_rejected(tmp_path, name):
    """A non-ASCII identifier is a syntax error, in every declaration position."""
    rc, out = check(tmp_path, f"const {name} as int is 1\n", f"id_{abs(hash(name))}.pengu")
    assert rc != 0, f"{name!r} was accepted as an identifier:\n{out}"
    assert "E0000" in out, out


def test_non_ascii_identifier_in_a_weave_name_is_rejected(tmp_path):
    """The restriction is lexical, not position-specific."""
    rc, out = check(tmp_path, "weave función into int:\n  return 0\n")
    assert rc != 0, out
    assert "E0000" in out, out


def test_non_ascii_is_fine_inside_string_literals(tmp_path):
    """The restriction applies to identifiers only; strings are full Unicode.

    This is the asymmetry worth documenting: `"日本語"` is a valid string, while
    `日本語` as a name is not.
    """
    rc, out = check(
        tmp_path,
        'weave main into int:\n'
        '  var s as string is "日本語 café Ω"\n'
        '  return (s length to int)\n',
    )
    assert rc == 0, out


def test_ascii_identifiers_are_accepted(tmp_path):
    """Guard against over-reach: the full ASCII identifier grammar works."""
    rc, out = check(
        tmp_path,
        "const MAX_VALUE_2 as int is 1\n"
        "weave _private_helper into int:\n  return MAX_VALUE_2\n"
        "weave camelCase into int:\n  return calling _private_helper\n",
    )
    assert rc == 0, out
