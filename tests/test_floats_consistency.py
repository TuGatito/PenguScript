"""Phase 3 item 3.9 — every float-to-text path uses the same format.

Before this item the runtime had two float formats, and which one you got
depended on which code path happened to format the value:

    $ pengu run fl.pengu
    3.140000     # print x        (codegen builtin: printf("%f"))
    3.14         # (x to string)  (pengu_string_from_float: "%g")
    3.140000     # "{x}"          (pengu_string_format_ex: "%f")

`LANGUAGE.md` documented the split as intentional ("`%f` and `to string` format
floats differently (`0.500000` vs `0.5`)"), but it was an accident of
implementation: three functions, two formats, for one value. All three now use
`%g`, and the language reference says so.

Rule C1: each test compiles a program, runs it, and compares the **executed**
output of the three paths. No test inspects generated C text.
"""

import pytest

from tests.conftest import compile_run, requires_cc, requires_runtime

pytestmark = [requires_cc, requires_runtime]

# (tipo PenguScript, literal, texto esperado)
#
# `float`/`f32` are 32-bit (LANGUAGE.md:194-204), so 1e300 overflows to `inf` and
# 1e-300 underflows to `0` — that is correct C semantics for the declared type,
# and it is included on purpose: the three paths must agree on `inf` too.
# `f64`/`double` are 64-bit and carry 1e300 as-is.
CASES = [
    ("float", "3.14", "3.14"),
    ("float", "0.0", "0"),
    ("float", "-0.0", "-0"),
    ("float", "1.0 / 3.0", "0.333333"),
    ("float", "1e300", "inf"),
    ("float", "1e-300", "0"),
    ("f64", "3.14", "3.14"),
    ("f64", "-0.0", "-0"),
    ("f64", "1.0 / 3.0", "0.333333"),
    ("f64", "1e300", "1e+300"),
]


def _three_paths_program(ty: str, literal: str) -> str:
    """prints the same value through `print`, `to string` and `"{...}"`."""
    return (
        "weave main into int:\n"
        f"    var x as {ty} is {literal}\n"
        "    calling print with x\n"
        "    calling print with (x to string)\n"
        '    calling print with "{x}"\n'
        "    return 0\n"
    )


@pytest.mark.parametrize("ty,literal,expected", CASES,
                         ids=[f"{t}:{lit}" for t, lit, _ in CASES])
def test_float_formatting_is_identical_on_every_path(ty, literal, expected):
    """`print x`, `(x to string)` and `"{x}"` must produce byte-identical text.

    C2: set the `%f` branch of `pengu_string_format_ex` back to `"%f"` and the
    interpolation line becomes `3.140000`; set the codegen `print` builtin back
    and the first line does, so the three-way equality fails.
    """
    res = compile_run(_three_paths_program(ty, literal), tag="float_consistency")
    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]

    assert len(lines) == 3, (
        f"expected three lines (print / to string / interpolation), got "
        f"{len(lines)}: {lines!r}\nstderr: {res.stderr}"
    )
    printed, to_string, interpolated = lines
    assert printed == to_string == interpolated, (
        f"{ty} {literal}: the three float-to-text paths disagree — "
        f"print={printed!r} to-string={to_string!r} interpolation={interpolated!r}"
    )
    assert printed == expected, (
        f"{ty} {literal}: expected {expected!r}, got {printed!r}"
    )
