"""Module-level warning opt-out: ``# pengu: allow-warnings W0001``.

``std.functor`` reinterprets a function pointer with ``transmute`` (the
Zig/Odin thick-function pattern).  That is a deliberate W0001 in a trusted
module; a program that imports it must not inherit a warning about code it
never wrote and cannot change.

The directive is textual, per file and names the exact codes it silences:

* it suppresses only the listed codes;
* it never leaks into another module;
* a typo (an unlisted/unknown code) silences nothing;
* the std module that uses it is warning-free through the real CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_checker import PenguChecker  # noqa: E402
from pengu_parser.pengu_parser import PenguParser  # noqa: E402

_DIRECTIVE = "# pengu: allow-warnings"

_TRANSMUTE = """
weave cast_it with p as ref to int into ref to int:
    return transmute p to ref to int
"""

_UNSAFE = """
weave cast_safely with p as ref to int into ref to int:
    var q as ref to int is null
    unsafe:
        set q is transmute p to ref to int
    return q
"""


def _warnings(source: str, filename: str = "t.pengu") -> list[str]:
    ast = PenguParser().parse(source)
    checker = PenguChecker(filename=filename, base_dir=str(ROOT))
    checker.check(ast, source=source, filename=filename)
    return list(checker.warnings)


def test_transmute_warns_without_the_directive():
    codes = [w.split("]")[0] + "]" for w in _warnings(_TRANSMUTE)]
    assert "[W0001]" in codes, codes


def test_the_directive_silences_the_named_code():
    assert _warnings(f"{_DIRECTIVE} W0001\n{_TRANSMUTE}") == []


def test_the_directive_accepts_several_codes():
    source = f"{_DIRECTIVE} W0001, W0007\n{_UNSAFE}"
    assert _warnings(source) == []


def test_the_directive_accepts_space_separated_codes():
    source = f"{_DIRECTIVE} W0001 W0007\n{_UNSAFE}"
    assert _warnings(source) == []


def test_only_the_named_codes_are_silenced():
    source = f"""{_DIRECTIVE} W0001

weave helper into int:
    return 1

weave shadow into int:
    var helper as int is 2
    return helper
"""
    warnings = _warnings(source)
    assert warnings, "the W0005 shadowing warning disappeared too"
    assert all(w.startswith("[W0005]") for w in warnings), warnings


def test_an_unknown_code_silences_nothing():
    warnings = _warnings(f"{_DIRECTIVE} W9999\n{_TRANSMUTE}")
    assert len(warnings) == 1
    assert warnings[0].startswith("[W0001]"), warnings


def test_the_directive_does_not_leak_to_another_module():
    assert _warnings(f"{_DIRECTIVE} W0001\n{_TRANSMUTE}", "a.pengu") == []
    other = _warnings(_TRANSMUTE, "b.pengu")
    assert any(w.startswith("[W0001]") for w in other), other


def test_a_doc_comment_is_not_a_directive():
    source = f"## {_DIRECTIVE} W0001\n{_TRANSMUTE}"
    assert any(w.startswith("[W0001]") for w in _warnings(source))


def test_importing_std_functor_is_warning_free(pengu_cli, tmp_path):
    script = tmp_path / "main.pengu"
    script.write_text(
        "import std.functor\n"
        "import std.spark\n"
        "\n"
        "weave main into int:\n"
        "    var f as functor.Fn1 of int, int is donum (functor.Fn1 of int, int)\n"
        '    calling spark.println with "{calling f.is_null}"\n'
        "    return 0\n",
        encoding="utf-8",
    )
    res = pengu_cli("check", str(script), cwd=tmp_path)
    combined = res.stdout + res.stderr
    assert res.returncode == 0, combined
    assert "W0001" not in combined, combined
    assert "W0007" not in combined, combined
    assert "warning" not in combined.lower(), combined


def test_std_functor_itself_is_warning_free(pengu_cli):
    res = pengu_cli("check", str(ROOT / "std" / "functor.pengu"), cwd=ROOT)
    combined = res.stdout + res.stderr
    assert res.returncode == 0, combined
    assert "warning" not in combined.lower(), combined
