"""Compile-time `wasm` / `wasm_target` variables.

These are the two additions the WebAssembly target needed in the comptime
environment (`pengu_parser/pengu_comptime.py`). They behave like
`os`/`arch`/`compiler`: a bare name inside a `when` condition, resolved before
code generation, so the untaken branch disappears from `bundle.c`.

The tests build the checker with an explicit `CompileTimeEnv` rather than going
through the CLI: the point is the *resolution* rule, and a subprocess build would
only re-prove the end-to-end path (which `tests/wasm/test_std_web.py` covers).

Note on assert shapes: the generator lowers `return N` to
``int32_t _ret_K = N;`` followed by ``return _ret_K;``, so these tests look for
the distinctive *value*, never for a literal ``return N;``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_comptime import (  # noqa: E402
    CompileTimeEnv,
    parse_cli_defines,
)
from pengu_parser.pengu_checker import PenguChecker  # noqa: E402
from pengu_parser.pengu_codegen import PenguCodegen  # noqa: E402
from pengu_parser.pengu_parser import PenguParser  # noqa: E402


def _emit(source: str, env: CompileTimeEnv, filename: str = "t.pengu") -> str:
    """Parses + checks + emits a bundle under `env` (which folds the `when`s)."""
    ast = PenguParser().parse(source)
    checker = PenguChecker(base_dir=str(ROOT), compile_env=env)
    checker.check(ast, source=source, filename=filename)
    codegen = PenguCodegen(checker.symbols, [filename], str(ROOT),
                           compile_env=checker.compile_env)
    codegen.collect_declarations([(filename, ast)])
    return codegen.generate_bundle()


def _checker_errors(source: str, env: CompileTimeEnv) -> set:
    ast = PenguParser().parse(source)
    checker = PenguChecker(base_dir=str(ROOT), compile_env=env)
    try:
        checker.check(ast, source=source, filename="t.pengu")
    except Exception:
        pass  # diagnostics are also accumulated on the checker
    return {getattr(e, "code", "") for e in getattr(checker, "errors", [])}


# ---------------------------------------------------------------------------
# The environment object
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_default_env_is_native():
    env = CompileTimeEnv()
    assert env.wasm_target == ""
    assert env.is_wasm is False
    assert env.defined("wasm") is False


@pytest.mark.smoke
@pytest.mark.parametrize("target", ["emscripten", "wasi"])
def test_wasm_target_sets_both_spellings(target):
    env = CompileTimeEnv(wasm_target=target)
    assert env.wasm_target == target
    assert env.is_wasm is True
    # `when wasm:` and `when defined(wasm):` must never disagree.
    assert env.defined("wasm") is True


@pytest.mark.smoke
def test_wasm_target_survives_copy_and_override():
    """The env is copied per module; losing the target would flip every `when`."""
    env = CompileTimeEnv(wasm_target="emscripten")
    assert env.copy().wasm_target == "emscripten"
    assert env.copy().is_wasm is True
    other = env.with_override(is_debug=True)
    assert other.wasm_target == "emscripten"
    assert other.is_debug is True


@pytest.mark.smoke
def test_cli_define_wasm_is_an_independent_way_in():
    """`-D wasm` satisfies `defined(wasm)`; it does not invent a target name."""
    env = parse_cli_defines(["wasm"])
    assert env.defined("wasm") is True
    assert env.wasm_target == ""


# ---------------------------------------------------------------------------
# Branch selection in emitted C
# ---------------------------------------------------------------------------

_SWITCH = """\
weave pick into int:
    when wasm:
        return 101
    when not wasm:
        return 202
    return 303
"""

_TARGET = """\
weave which into int:
    when wasm_target == "emscripten":
        return 401
    when wasm_target == "wasi":
        return 502
    return 603
"""


@pytest.mark.smoke
def test_when_wasm_folds_to_the_wasm_branch():
    c = _emit(_SWITCH, CompileTimeEnv(wasm_target="emscripten"))
    assert "101" in c
    assert "202" not in c


@pytest.mark.smoke
def test_when_wasm_folds_to_the_native_branch_by_default():
    c = _emit(_SWITCH, CompileTimeEnv())
    assert "202" in c
    assert "101" not in c


@pytest.mark.smoke
def test_define_wasm_selects_the_wasm_branch_in_both_spellings():
    """`-D wasm` must mean the same to `when wasm:` and `when defined(wasm):`.

    Both weaves use a mutually exclusive `when`/`when not` pair so the losing
    branch disappears entirely; a bare `when` would leave its trailing code
    behind (unreachable, but still in the emitted C).
    """
    source = """\
weave pick into int:
    when wasm:
        return 101
    when not wasm:
        return 202
    return 303

weave pick2 into int:
    when defined(wasm):
        return 404
    when not defined(wasm):
        return 505
    return 606
"""
    c = _emit(source, parse_cli_defines(["wasm"]))
    assert "101" in c and "404" in c
    assert "202" not in c and "505" not in c


@pytest.mark.smoke
@pytest.mark.parametrize("target,present,absent", [
    ("emscripten", "401", "502"),
    ("wasi", "502", "401"),
])
def test_wasm_target_compares_like_any_string(target, present, absent):
    c = _emit(_TARGET, CompileTimeEnv(wasm_target=target))
    assert present in c
    assert absent not in c


@pytest.mark.smoke
def test_native_gets_the_fallback_branch():
    c = _emit(_TARGET, CompileTimeEnv())
    assert "603" in c
    assert "401" not in c
    assert "502" not in c


@pytest.mark.smoke
def test_wasm_target_is_empty_natively():
    c = _emit("""\
weave f into int:
    when wasm_target == "":
        return 707
    when wasm_target != "":
        return 808
    return 909
""", CompileTimeEnv())
    assert "707" in c
    assert "808" not in c


@pytest.mark.smoke
def test_unresolvable_when_condition_is_still_an_error():
    """`when` stays a compile-time constant check (E0039): bare names are not
    silently treated as true just because `wasm` became resolvable."""
    codes = _checker_errors("when zzz:\n    weave x into int:\n        return 1\n",
                            CompileTimeEnv())
    assert "E0039" in codes, f"expected E0039, got {sorted(codes)}"


@pytest.mark.smoke
def test_unknown_identifier_in_when_body_is_not_defined_by_the_wasm_branch():
    """A name that only exists in the *untaken* branch must not leak."""
    source = """\
when wasm:
    weave only_wasm into int:
        return 1

weave main into int:
    return calling only_wasm
"""
    # Native: `only_wasm` is folded away, so calling it is undefined.
    codes = _checker_errors(source, CompileTimeEnv())
    assert codes, "calling a folded-away weave should be a diagnostic"
