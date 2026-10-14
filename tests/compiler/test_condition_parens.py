"""Branch conditions must not carry an extra pair of parentheses.

Regression for `-Wparentheses-equality`: `if a == b:` used to reach the C
compiler as ``if ((a == b))``, the exact shape clang reports as "equality
comparison with extraneous parentheses" (it is also the shape of the classic
``if ((a = b))`` typo). Every comparison in every `std` module goes through the
same emitter, so a small program importing one module produced dozens of
warnings -- measured: 50 warnings, 23 of them this one.

The fix lives in the branch emitters (`stmts.py` `if`/`unless`, `loops.py`
`while`), which wrap the condition in a pair of their own. The expression
translator keeps its parentheses, which are *not* redundant in operand position
(``(a == b) + x``), so the removal is a targeted unwrap implemented as
`pengu_codegen._base.unwrap_condition`.

The unit tests below pin the unwrap rule itself; the emission tests pin where it
is applied; the slow test proves the warning is actually gone.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_codegen._base import unwrap_condition  # noqa: E402


# ---------------------------------------------------------------------------
# smoke: the unwrap rule
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@pytest.mark.parametrize("code,expected", [
    # The bug: one redundant pair around a whole comparison.
    ("(a == b)", "a == b"),
    ("(a != b)", "a != b"),
    ("(a < b)", "a < b"),
    ("(me > other)", "me > other"),
    # Nested pairs: drop exactly one.
    ("((a == b))", "(a == b)"),
    ("((a && b) || c)", "(a && b) || c"),
])
def test_unwrap_removes_one_redundant_pair(code, expected):
    assert unwrap_condition(code) == expected


@pytest.mark.smoke
@pytest.mark.parametrize("code", [
    "f(x)",                      # no outer pair at all
    "(a) + (b)",                 # a sequence, not one wrapped expression
    "(a == b) && (c == d)",      # the first pair closes before the end
    "a == b",
    "((a == b)",                 # unbalanced: never touch it
    "(a == b))",
    "",
    "(",
    ")",
])
def test_unwrap_leaves_everything_else_alone(code):
    assert unwrap_condition(code) == code


@pytest.mark.smoke
@pytest.mark.parametrize("code,expected", [
    # A parenthesised literal must not unbalance the scan.
    ('("(")', '"("'),
    ('(s == "(")', 's == "("'),
    ('((s == "(") && t)', '(s == "(") && t'),
    ('(")")', '")"'),
    # Escapes: a backslash before a quote does not close the literal.
    ("('\\'')", "'\\''"),
    ('("a\\\\")', '"a\\\\"'),
])
def test_unwrap_skips_string_and_char_literals(code, expected):
    assert unwrap_condition(code) == expected


# ---------------------------------------------------------------------------
# smoke: where the unwrap is applied
# ---------------------------------------------------------------------------

def _condition_with(c: str, keyword: str, marker: str) -> str:
    """The C text inside the first ``keyword (...)`` whose body contains `marker`.

    The bundle is a text blob (the runtime header is only `#include`d), and it
    contains other generated `if (...)`s, so the search is anchored on a marker
    from the test's own condition. `unwrap_condition(cond) == cond` is then the
    invariant that matters: the emitter added no redundant pair of its own.
    """
    idx = 0
    while True:
        kw = c.find(f"{keyword} (", idx)
        if kw < 0:
            raise AssertionError(f"no {keyword!r} whose condition contains {marker!r}")
        start = kw + len(keyword) + 2
        depth = 1
        i = start
        while depth and i < len(c):
            if c[i] == "(":
                depth += 1
            elif c[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = c[start:i]
        if marker in body:
            return body
        idx = i + 1


@pytest.mark.smoke
def test_if_condition_is_not_double_wrapped(emit_c):
    c = emit_c("""\
weave f with a as int, b as int into int:
    if a == b:
        return 1
    return 0
""")
    cond = _condition_with(c, "if", "a == b")
    assert cond == "a == b"
    assert unwrap_condition(cond) == cond  # nothing left to unwrap
    assert "if ((a == b))" not in c


@pytest.mark.smoke
def test_while_condition_is_not_double_wrapped(emit_c):
    c = emit_c("""\
weave f with n as int into int:
    var i as int is 0
    while i < n:
        set i is i + 1
    return i
""")
    cond = _condition_with(c, "while", "i < n")
    assert cond == "i < n"
    assert unwrap_condition(cond) == cond
    assert "while ((i < n))" not in c


@pytest.mark.smoke
def test_unless_condition_is_not_double_wrapped(emit_c):
    """`unless a == b` becomes `if (!(a == b))`, not `if (!((a == b)))`."""
    c = emit_c("""\
weave f with a as int, b as int into int:
    unless a == b:
        return 1
    return 0
""")
    cond = _condition_with(c, "if", "a == b")
    assert cond == "!(a == b)"
    assert "if (!((a == b)))" not in c


@pytest.mark.smoke
def test_boolean_operands_keep_their_parentheses(emit_c):
    """Only the *outer* pair goes; operands still need theirs."""
    c = emit_c("""\
weave f with a as int, b as int, n as int into int:
    if a == b and n > a:
        return 1
    return 0
""")
    cond = _condition_with(c, "if", "n > a")
    assert cond == "(a == b) && (n > a)"
    assert unwrap_condition(cond) == cond


@pytest.mark.smoke
def test_string_comparison_condition_is_untouched(emit_c):
    """A call-shaped condition already has no envelope pair to remove."""
    c = emit_c("""\
weave f with s as string, t as string into int:
    if s == t:
        return 1
    return 0
""")
    cond = _condition_with(c, "if", "pengu_string_equal")
    assert cond == "pengu_string_equal(s, t)"


@pytest.mark.smoke
def test_operand_position_keeps_its_parentheses(emit_c):
    """A comparison that is an *operand* keeps its parentheses, and the emitter
    still adds no redundant pair of its own.

    The source's own `( ... )` around each operand legitimately survives -- that
    is precedence, not noise -- so this asserts the invariant rather than a
    pretty-printed string.
    """
    c = emit_c("""\
weave f with a as int, b as int into int:
    var x as int is 0
    if (a == b) and ((a + b) == 2):
        set x is 1
    return x
""")
    cond = _condition_with(c, "if", "a + b")
    assert unwrap_condition(cond) == cond, f"emitter added a redundant pair: {cond}"
    # The arithmetic comparison kept exactly the parentheses it needs inside `&&`.
    assert "((a + b) == 2)" in cond, cond


@pytest.mark.smoke
def test_explicit_source_parentheses_do_not_double_up(emit_c):
    """`if (a == b):` must not become `if ((a == b))`.

    The source's `paren_expr` used to add a pair on top of the one the comparison
    translator already emitted, so this shape warned even once the branch
    emitters stopped adding their own.
    """
    c = emit_c("""\
weave f with a as int, b as int into int:
    if (a == b):
        return 1
    var i as int is 0
    while (i == a):
        set i is i + 1
    return i
""")
    assert _condition_with(c, "if", "a == b") == "a == b"
    assert _condition_with(c, "while", "i == a") == "i == a"
    assert "if ((a == b))" not in c
    assert "while ((i == a))" not in c


@pytest.mark.smoke
def test_parentheses_around_a_plain_value_are_kept(emit_c):
    """`(5)` still needs its pair: unwrapping must not delete the only one."""
    c = emit_c("""\
weave f into int:
    if (1 == 1):
        return (2)
    return (0)
""")
    assert return_values(c) >= {"2", "0"}


def return_values(c: str) -> set:
    """The distinct integer literals assigned to a `_ret_` temporary."""
    import re as _re
    return set(_re.findall(r"_ret_\d+ = (\d+);", c))


@pytest.mark.smoke
def test_filtered_comprehension_condition_is_not_double_wrapped(emit_c):
    """The comprehension/filter emitter (`for x in xs when cond then x`) too.

    Found by asserting the invariant over a real bundle rather than by trusting
    the grep for the three reported sites.
    """
    c = emit_c("""\
weave f with xs as list of int into list of int:
    return for x in xs when x == 2 then x
""")
    cond = _condition_with(c, "if", "x == 2")
    assert unwrap_condition(cond) == cond, f"comprehension filter left a pair: {cond}"
    assert "if ((x == 2))" not in c


@pytest.mark.smoke
def test_element_comparison_shapes_are_unwrapped():
    """The element-comparison shapes the generator builds for inline
    `contains` / `index_of` loops pass through the same unwrap.

    Those loops live in `exprs.py` and are emitted for fixed arrays and slices.
    No `std` module currently exposes such a method (`slice of int` has no
    `contains`), so this pins the *shape* instead of driving it through the front
    end: whatever `_make_elem_eq` returns, wrapping it the way the emitter does
    must leave nothing redundant.
    """
    for cmp in ("(x == item)",
                "(memcmp(&(x), &(item), sizeof(int32_t)) == 0)",
                "pengu_string_equal(x, item)"):
        emitted = f"({unwrap_condition(cmp)})"
        assert unwrap_condition(emitted) == unwrap_condition(cmp), cmp


# ---------------------------------------------------------------------------
# slow: the warning is actually gone, and behaviour is unchanged
# ---------------------------------------------------------------------------

_CONDITION_SOURCE = """\
import std.spark

weave main into int:
    var a as int is 3
    var b as int is 3
    var n as int is 2
    var hits as int is 0
    if a == b:
        set hits is hits + 1
    if a != n:
        set hits is hits + 1
    if n < a:
        set hits is hits + 1
    while n > 0:
        set n is n - 1
        set hits is hits + 1
    unless a == n:
        set hits is hits + 1
    calling spark.println_int with hits
    return 0
"""


@pytest.mark.slow
def test_no_extraneous_parentheses_warning(tmp_path, pengu_root):
    """Compile a bundle full of `==` conditions and require a clean -Wextra run.

    Uses clang specifically: `-Wparentheses-equality` is a clang diagnostic.
    """
    cc = shutil.which("clang")
    if not cc:
        pytest.skip("clang not on PATH (the warning is clang-specific)")
    if not (pengu_root / "build" / "include" / "pengu_runtime.h").is_file():
        pytest.skip("runtime headers not staged (run build_runtime.py)")

    script = tmp_path / "cond.pengu"
    script.write_text(_CONDITION_SOURCE, encoding="utf-8")
    # The environment must be inherited, not replaced: CI has no TCC bundle, so
    # the driver falls back to the bare name 'gcc', whose own driver locates
    # 'cc1'/'ld' through PATH.  A stripped env made gcc die with
    # "cannot execute 'cc1'" on Linux runners (macOS 'gcc' is clang, which
    # resolves its toolchain by absolute path, so only Linux broke).
    build = subprocess.run(
        [sys.executable, str(pengu_root / "pengu_project.py"), "run",
         "--no-cache", "--keep", str(script)],
        capture_output=True, text=True, timeout=600, cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(pengu_root)})
    assert build.returncode == 0, f"{build.stdout}\n{build.stderr}"

    bundle_dir = tmp_path / "build" / "cond_run"
    proc = subprocess.run(
        [cc, "-c", str(bundle_dir / "bundle.c"), "-o", str(tmp_path / "cond.o"),
         "-O2", "-Wall", "-Wextra", "-std=c11",
         "-I", str(bundle_dir), "-I", str(pengu_root / "build" / "include"),
         "-I", str(pengu_root)],
        capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, f"compile failed:\n{proc.stderr}"
    offenders = [line for line in proc.stderr.splitlines()
                 if "parentheses-equality" in line]
    assert not offenders, "extraneous parentheses came back:\n" + "\n".join(offenders)


@pytest.mark.slow
def test_conditions_still_evaluate_the_same(compile_and_run):
    """The unwrap must be a pure formatting change."""
    out = compile_and_run(_CONDITION_SOURCE, tag="cond_behaviour")
    # a==b (1), a!=n (1), n<a (1), while n>0 twice (2), unless a==n (1) = 6
    assert out.strip().endswith("6"), out
