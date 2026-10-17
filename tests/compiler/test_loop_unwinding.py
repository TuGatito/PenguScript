"""A labeled jump releases the loops it leaves (no unwinding in C).

A `for v in <non-lvalue>` loop materializes the iterable and emits
``pengu_banish_list(&_iter_N);`` after the loop.  A plain `break` reaches that
line; a **labeled** jump that leaves the loop must run it explicitly, or every
iteration leaks a list.  2.6.0 handled the loop that owns the iterable; 2.7.0
handles the loops *between* the jump and its target by recording each entered
loop on a stack and emitting the releases at the jump site.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _compile(emit_c, tmp_path, source: str) -> str:
    bundle = tmp_path / "bundle.c"
    bundle.write_text(emit_c(source), encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    compilers = [c for c in (shutil.which("gcc"), shutil.which("clang")) if c]
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        res = subprocess.run(
            [cc, "-c", str(bundle), "-o", str(tmp_path / f"{Path(cc).name}.o"),
             "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-function",
             "-I", str(root), "-I", str(root / "build" / "include")],
            capture_output=True, text=True, timeout=600,
        )
        assert res.returncode == 0, (
            f"{cc} rejected the generated C:\n{res.stdout}\n{res.stderr}\n---\n"
            + bundle.read_text(encoding="utf-8")
        )
    return bundle.read_text(encoding="utf-8")


_MAKER = """
weave make_list into list of int:
    return [1, 2, 3]
"""


def test_continue_to_an_outer_loop_releases_the_inner_list(emit_c):
    c = emit_c(_MAKER + """
weave scan into int:
    var total as int is 0
    outer: for i from 0 to 3:
        for v in calling make_list:
            if v == 3:
                continue outer
            set total += v
    return total
""")
    # The release is emitted before the jump, and the loop's own release stays
    # for the iterations that end normally.
    jump = c.index("goto _pengu_label_outer_continue;")
    tail = c[max(0, jump - 200):jump]
    assert "pengu_banish_list(&_iter_" in tail, tail
    assert c.count("pengu_banish_list(&_iter_") == 2, c


def test_break_to_an_outer_loop_releases_the_inner_list(emit_c):
    c = emit_c(_MAKER + """
weave scan into int:
    outer: for i from 0 to 3:
        for v in calling make_list:
            if i == 2:
                break outer
    return 0
""")
    jump = c.index("goto _pengu_label_outer_break;")
    tail = c[max(0, jump - 200):jump]
    assert "pengu_banish_list(&_iter_" in tail, tail


def test_two_levels_of_owning_loops_release_both(emit_c):
    c = emit_c(_MAKER + """
weave scan into int:
    outer: for i from 0 to 3:
        for a in calling make_list:
            for b in calling make_list:
                if b == 2:
                    continue outer
    return 0
""")
    jump = c.index("goto _pengu_label_outer_continue;")
    before = c[:jump]
    # Both inner loops' temporaries are released, innermost first.
    assert before.count("pengu_banish_list(&_iter_") >= 2, c


def test_a_jump_without_owning_loops_emits_no_release(emit_c):
    c = emit_c("""
weave scan into int:
    outer: for i from 0 to 3:
        for j from 0 to 3:
            if j == 1:
                continue outer
    return 0
""")
    assert "pengu_banish_list" not in c, c


@pytest.mark.slow
def test_every_owning_loop_compiles_without_warnings(emit_c, tmp_path):
    _compile(emit_c, tmp_path, _MAKER + """
weave scan into int:
    var total as int is 0
    outer: for i from 0 to 3:
        for a in calling make_list:
            for b in calling make_list:
                if b == 2:
                    continue outer
            if a == 1:
                break outer
            set total += a
    return total
""")


@pytest.mark.slow
def test_cross_loop_jump_runs_cleanly(compile_and_run):
    """Behavioural proof: the jump leaves both loops and the result is right."""
    out = compile_and_run(_MAKER + """
import std.spark

weave main into int:
    var total as int is 0
    outer: for i from 0 to 4:
        for v in calling make_list:
            if v == 3:
                continue outer
            if i == 3:
                break outer
            set total += v
    calling spark.println with "total={total}"
    return 0
""", tag="unwind")
    assert out.strip() == "total=9"


def test_return_releases_every_owning_loop(emit_c):
    """`return` unwinds the function, so every active owning loop is released."""
    c = emit_c(_MAKER + """
weave scan with limit as int into int:
    outer: for i from 0 to 2:
        for v in calling make_list:
            if v > limit:
                return v
    return -1
""")
    import re

    # At least one release is immediately followed by the frame pop + return of
    # the early-exit path (the loop's own trailing release is the other one).
    early = [
        m for m in re.finditer(r"pengu_banish_list\(&_iter_\d+\);", c)
        if "pengu_frame_pop();" in c[m.start():m.start() + 300]
        and "return _ret_" in c[m.start():m.start() + 300]
    ]
    assert early, c


@pytest.mark.slow
def test_return_from_inside_an_owning_loop_runs_cleanly(compile_and_run):
    out = compile_and_run(_MAKER + """
import std.spark

weave first_big with limit as int into int:
    outer: for i from 0 to 2:
        for v in calling make_list:
            if v > limit:
                return v
    return -1

weave main into int:
    calling spark.println with "{calling first_big with 1}"
    return 0
""", tag="return_unwind")
    assert out.strip() == "2"
