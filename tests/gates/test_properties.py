#!/usr/bin/env python3
"""Property-based tests for the PenguScript toolchain (roadmap 2.0, item 8.7).

The seven properties of ``AUDIT_1.0.md`` §11.5, one test each.  In every line the
first item is the statement and the second the oracle:

1. ``test_property_1_literal_round_trip`` — ``parse(format(ast)) == ast`` over
   generated expression trees; oracle: structural AST equality.
2. ``test_property_2_formatter_idempotency`` — ``fmt(fmt(x)) == fmt(x)``; oracle:
   whole-output text equality (the property that would have caught §6.3).
3. ``test_property_3_formatter_preserves_semantics`` — ``check(fmt(x))`` reports
   what ``check(x)`` reports; oracle: canonical diagnostics, strengthened to a
   byte-identical generated bundle for programs that check cleanly.
4. ``test_property_4_container_round_trip`` — ``push`` n elements gives
   ``len == n`` for n in [0, 1000]; oracle: the compiled program's exit status.
5. ``test_property_5_int32_arithmetic_matches_c`` — ``a op b`` matches C
   ``int32_t``, limits included; oracle: stdout vs a compiled C reference.
6. ``test_property_6_same_type_casts_are_identity`` — ``transmute`` / ``to`` keep
   a same-type value; oracle: the compiled program's exit status.
7. ``test_property_7_compiler_determinism`` — two builds of one source produce
   one bundle; oracle: byte equality of the whole bundle.

Roadmap Annex C rule C1 is respected: no test looks for a hand-picked string
inside an implementation's output.  Text equality is the *whole-output* oracle
only for properties 2, 3 and 7, where the property itself is that the
formatter/compiler output is stable (``fmt(a) == fmt(b)``, never
``"x" in output``).  Every other oracle is a runtime invariant: an exit status,
the stdout of a compiled program, or structural AST equality.

Non-vacuity is guarded by :func:`test_generator_corpus_is_non_trivial`: the
strategies must yield at least 20 valid programs/expressions, and the formatter
must actually rewrite at least 20 of the generated programs, or the file fails.

The strategies are *compositional* over a type-aware subset (``int``, ``bool``,
``string``, ``float``, ``list of int``, ``maybe int``): templates that are valid
by construction, so ``assume`` only ever rejects the rare combination the
checker dislikes instead of filtering the corpus away.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path
from typing import NamedTuple, Sequence, Tuple

import pytest
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from pengu_lsp.formatting import format_pengu_source
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import (
    BUILD_DIR,
    REPO,
    check,
    check_ok,
    compile_run,
    gen_bundle,
    have_tool,
    requires_cc,
    requires_runtime,
)

# The compiler properties build and execute real programs, so a per-example
# wall-clock deadline would only measure the C toolchain.  Health checks are
# suppressed because `assume` rejects the few generated programs the checker
# refuses: the corpus is guarded explicitly instead (see the non-triviality test).
_SUPPRESS = list(HealthCheck)


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _fmt(text: str) -> str:
    """Formats `text` through the library entry point the ``pengu fmt`` CLI uses."""
    return format_pengu_source(text, tab_size=4, insert_spaces=True, blank_lines_max=None)


_PARSER: PenguParser | None = None


def _parser() -> PenguParser:
    """A process-wide parser (building the Lark tables is the expensive part)."""
    global _PARSER
    if _PARSER is None:
        _PARSER = PenguParser()
    return _PARSER


_POSITION_RE = re.compile(r"\[line \d+, col \d+\]")


def _diagnostic_signature(source: str) -> Tuple[str, ...]:
    """Canonical diagnostics of `source`: ``()`` when clean, else ``(code, message)``.

    Source positions are normalised away because the formatter legitimately moves
    columns; the error code and the message text are compared verbatim.  Only real
    compiler diagnostics are captured: anything else (an ``AttributeError`` from a
    checker crash, say) escapes and fails the test.
    """
    try:
        check(source)
    except PenguError as exc:
        code = getattr(exc, "code", None) or ""
        return (str(code), _POSITION_RE.sub("[line N, col N]", str(exc)))
    return ()


# --------------------------------------------------------------------------- #
# Property 1 generator: expression ASTs
# --------------------------------------------------------------------------- #

_NAME_POOL = ("a", "b", "x", "xs", "flag", "s", "q")
_CHAR_POOL = tuple("abcXYZ019 _-+.,:;!?@#$%^&*()[]{}<>/|~")
_SAFE_STRING_ALPHABET = "abcXYZ019 _-+.,:;!?@#$%^&*()[]{}/|~"

#: Literal spellings that pin exactly the bytes the lexer must hand back: plain
#: text, escaped newline/tab/quote/backslash and non-ASCII.
_STRING_SPELLINGS = (
    '""',
    '"a"',
    r'"a\nb"',
    r'"tab\there"',
    r'"quote\"inside"',
    r'"back\\slash"',
    '"héllo wörld"',
    '"x y z"',
)

_INT_BIN_OPS = ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>")
_CMP_OPS = ("==", "!=", "<", "<=", ">", ">=")
_BOOL_BIN_OPS = ("and", "or")
_UN_OPS = ("-", "~", "not")

#: grammar rule -> source-level operator, for the AST decoder
_OP_BY_RULE = {
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
    "mod": "%",
    "bitwise_and": "&",
    "bitwise_or": "|",
    "bitwise_xor": "^",
    "shl": "<<",
    "shr": ">>",
    "eq": "==",
    "ne": "!=",
    "lt": "<",
    "le": "<=",
    "gt": ">",
    "ge": ">=",
    "bool_and": "and",
    "bool_or": "or",
}
_UN_BY_RULE = {"neg": "-", "bit_not": "~", "log_not": "not"}
_LIT_BY_RULE = {"int_lit": "int", "float_lit": "float", "string_lit": "str", "char_lit": "char"}


def _plain_string_literal() -> st.SearchStrategy:
    """A quoted literal over an alphabet that needs no escaping."""
    return st.text(alphabet=_SAFE_STRING_ALPHABET, max_size=6).map(lambda body: '"' + body + '"')


@st.composite
def _leaf_ast(draw) -> tuple:
    kind = draw(st.sampled_from(("int", "float", "str", "char", "bool", "name")))
    if kind == "int":
        return ("int", str(draw(st.integers(0, 2 ** 31 - 1))))
    if kind == "float":
        # Non-negative leaves only: a leading '-' is the unary operator, and the
        # generator must not confuse `-1.5` with the literal `1.5` (the parser
        # sees `neg(float_lit 1.5)`), so negatives enter through `("un", "-", …)`.
        value = draw(st.floats(min_value=0.0, max_value=1e6,
                               allow_nan=False, allow_infinity=False))
        return ("float", repr(value))
    if kind == "str":
        return ("str", draw(st.one_of(st.sampled_from(_STRING_SPELLINGS), _plain_string_literal())))
    if kind == "char":
        return ("char", "'" + draw(st.sampled_from(_CHAR_POOL)) + "'")
    if kind == "bool":
        return ("bool", draw(st.sampled_from(("true", "false"))))
    return ("name", draw(st.sampled_from(_NAME_POOL)))


@st.composite
def _expr_ast(draw, depth: int = 3) -> tuple:
    """An expression *tree*: literals, names, unary and binary operators."""
    if depth <= 0 or draw(st.integers(0, 2)) == 0:
        return draw(_leaf_ast())
    if draw(st.booleans()):
        un_op = draw(st.sampled_from(_UN_OPS))
        return ("un", un_op, draw(_expr_ast(depth=depth - 1)))
    bin_op = draw(st.sampled_from(_INT_BIN_OPS + _CMP_OPS + _BOOL_BIN_OPS))
    return (
        "bin",
        bin_op,
        draw(_expr_ast(depth=depth - 1)),
        draw(_expr_ast(depth=depth - 1)),
    )


def _render_ast(node: tuple) -> str:
    """Renders an AST back to PenguScript source.

    Every compound node is parenthesised, so the tree's shape — not the
    language's precedence table — decides how the parser must group it.
    """
    tag = node[0]
    if tag in ("int", "float", "str", "char", "bool", "name"):
        return node[1]
    if tag == "un":
        _, op, operand = node
        # The space keeps `- -x` / `~ ~x` from lexing as one token.
        return f"({op} {_render_ast(operand)})"
    _, op, left, right = node
    return f"({_render_ast(left)} {op} {_render_ast(right)})"


def _decode_expr(node) -> tuple:
    """Rebuilds the reference AST from a Lark expression tree.

    Leaves carry the literal's *source spelling* (the parser keeps literal text
    verbatim), so equality proves the literal bytes survived the round trip.
    """
    if not hasattr(node, "data"):
        raise AssertionError(f"unexpected leaf in the expression tree: {node!r}")
    rule = str(node.data)
    if rule == "paren_expr":
        return _decode_expr(node.children[0])
    if rule in ("true_lit", "false_lit"):
        return ("bool", "true" if rule == "true_lit" else "false")
    if rule in _LIT_BY_RULE:
        return (_LIT_BY_RULE[rule], str(node.children[0].value))
    if rule == "var_ref":
        return ("name", str(node.children[0].value))
    if rule in _UN_BY_RULE:
        return ("un", _UN_BY_RULE[rule], _decode_expr(node.children[0]))
    if rule in _OP_BY_RULE:
        return (
            "bin",
            _OP_BY_RULE[rule],
            _decode_expr(node.children[0]),
            _decode_expr(node.children[1]),
        )
    raise AssertionError(f"expression rule {rule!r} is not part of the generated subset")


# --------------------------------------------------------------------------- #
# Program generator: statements over the type-aware subset
# --------------------------------------------------------------------------- #

_INT_VARS = ("a", "b")
_BOOL_VARS = ("flag",)
_STR_VARS = ("s",)
_FLOAT_VARS = ("f",)

#: Deliberately *not* the formatter's default unit (4): every generated program
#: is non-canonical, so `fmt(x) != x` and property 2 cannot pass vacuously.
_INDENT_UNITS = (" ", "  ", "   ", "     ", "\t")


def _gen_int(draw, depth: int = 2) -> str:
    if depth <= 0 or draw(st.integers(0, 3)) == 0:
        return draw(st.one_of(
            st.integers(0, 2 ** 31 - 1).map(str),
            st.sampled_from(_INT_VARS),
        ))
    op = draw(st.sampled_from(_INT_BIN_OPS))
    left = _gen_int(draw, depth - 1)
    right = _gen_int(draw, depth - 1)
    if op in ("/", "%"):
        # Keep the divisor non-zero: the generated programs are meant to be
        # runnable, even though properties 2/3/7 only compile them.
        right = f"(({right}) | 1)"
    if op in ("<<", ">>"):
        right = f"(({right}) % 8)"
    return f"(({left}) {op} ({right}))"


def _gen_bool(draw, depth: int = 2) -> str:
    if depth <= 0 or draw(st.integers(0, 3)) == 0:
        return draw(st.one_of(st.sampled_from(("true", "false")), st.sampled_from(_BOOL_VARS)))
    kind = draw(st.sampled_from(("cmp", "not", "bin")))
    if kind == "cmp":
        op = draw(st.sampled_from(_CMP_OPS))
        return f"(({_gen_int(draw, depth - 1)}) {op} ({_gen_int(draw, depth - 1)}))"
    if kind == "not":
        return f"(not ({_gen_bool(draw, depth - 1)}))"
    op = draw(st.sampled_from(_BOOL_BIN_OPS))
    return f"(({_gen_bool(draw, depth - 1)}) {op} ({_gen_bool(draw, depth - 1)}))"


def _gen_string(draw) -> str:
    return draw(st.one_of(
        st.sampled_from(_STRING_SPELLINGS),
        _plain_string_literal(),
        st.sampled_from(_STR_VARS),
        st.just("(s to string)"),
    ))


def _gen_float(draw, depth: int = 1) -> str:
    if depth <= 0 or draw(st.booleans()):
        return draw(st.one_of(
            st.floats(min_value=-1e3, max_value=1e3,
                      allow_nan=False, allow_infinity=False).map(repr),
            st.sampled_from(_FLOAT_VARS),
            st.just("(a to float)"),
        ))
    op = draw(st.sampled_from(("+", "-", "*", "/")))
    return f"(({_gen_float(draw, depth - 1)}) {op} ({_gen_float(draw, depth - 1)}))"


class _Program(NamedTuple):
    """A generated program: ``(indent unit, [(depth, line)])``."""

    unit: str
    body: Tuple[Tuple[int, str], ...]

    @property
    def source(self) -> str:
        return "\n".join(self.unit * depth + text for depth, text in self.body) + "\n"


def _gen_statement(draw, index: int, use_spark: bool) -> list:
    """One statement block; every declaration gets a unique name."""
    kinds = ["let_int", "let_bool", "let_string", "if", "for", "judge", "maybe", "list", "set"]
    if use_spark:
        kinds.append("println")
    kind = draw(st.sampled_from(kinds))
    name = f"v{index}"

    if kind == "let_int":
        return [(1, f"let {name} as int is {_gen_int(draw, 2)}")]
    if kind == "let_bool":
        return [(1, f"let {name} as bool is {_gen_bool(draw, 2)}")]
    if kind == "let_string":
        return [(1, f"let {name} as string is {_gen_string(draw)}")]
    if kind == "set":
        target = draw(st.sampled_from(_INT_VARS))
        return [(1, f"set {target} is {_gen_int(draw, 2)}")]
    if kind == "if":
        return [
            (1, f"if {_gen_bool(draw, 2)}:"),
            (2, f"let {name}a as int is {_gen_int(draw, 1)}"),
            (1, "else:"),
            (2, f"let {name}b as int is {_gen_int(draw, 1)}"),
        ]
    if kind == "for":
        end = draw(st.integers(1, 5))
        return [
            (1, f"for i{index} from 0 to {end}:"),
            (2, f"let {name} as int is {_gen_int(draw, 1)}"),
        ]
    if kind == "judge":
        return [
            (1, f"let {name} as int is judge {_gen_int(draw, 1)}:"),
            (2, f"when 0 -> {_gen_int(draw, 1)}"),
            (2, f"when 1 -> {_gen_int(draw, 1)}"),
            (2, f"else -> {_gen_int(draw, 1)}"),
        ]
    if kind == "maybe":
        return [
            (1, f"let {name} as maybe int is some {_gen_int(draw, 1)}"),
            (1, f"if {name} is present:"),
            (2, f"let {name}b as int is {_gen_int(draw, 1)}"),
        ]
    if kind == "list":
        count = draw(st.integers(0, 4))
        return [
            (1, f"var xs{index} as list of int is list of int"),
            (1, f"for i{index} from 0 to {count}:"),
            (2, f"calling xs{index}.push with {_gen_int(draw, 1)}"),
        ]
    return [(1, f"calling spark.println_int with {_gen_int(draw, 2)}")]


@st.composite
def _program_strategy(draw) -> _Program:
    """A syntactically valid ``main``: preamble, statements, terminating return."""
    unit = draw(st.sampled_from(_INDENT_UNITS))
    use_spark = draw(st.booleans())
    body: list = []
    if use_spark:
        body += [(0, "import std.spark"), (0, "")]
    body.append((0, "weave main into int:"))
    # `a`/`b` are `var` so the generated `set` statements have a legal target.
    body.append((1, "var a as int is " + str(draw(st.integers(0, 500)))))
    body.append((1, "var b as int is " + str(draw(st.integers(0, 500)))))
    body.append((1, "let flag as bool is " + draw(st.sampled_from(("true", "false")))))
    body.append((1, "let s as string is " + draw(st.sampled_from(_STRING_SPELLINGS))))
    body.append((1, "let f as float is " + repr(draw(st.floats(
        min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)))))
    for index in range(draw(st.integers(1, 4))):
        body.extend(_gen_statement(draw, index, use_spark))
    body.append((1, "return " + _gen_int(draw, 2)))
    return _Program(unit=unit, body=tuple(body))


_program_source = _program_strategy().map(lambda program: program.source)


def _generated_or_rejected(source: str) -> None:
    """Rejects (via ``assume``) a generated program the checker refuses.

    Only a real compiler diagnostic is a rejection; a crash inside the checker is
    a compiler bug and must fail the property, not be filtered away.
    """
    try:
        check_ok(source)
    except PenguError:
        assume(False)


#: Semantic errors (not parse errors) whose diagnostics the formatter must not
#: change.  Indented with 2 spaces so the formatter has real work to do.
_INVALID_PROGRAMS = (
    'weave main into int:\n  return "not an int"\n',
    'weave main into int:\n  let a as int is true\n  return a\n',
    'weave main into int:\n  let a as int is 1\n',
    'weave main into int:\n  return unknown_name\n',
    'weave main into int:\n  if 1:\n    return 0\n  return 1\n',
    'weave main into int:\n  var xs as list of int is list of int\n'
    '  calling xs.push with "oops"\n  return 0\n',
)


# --------------------------------------------------------------------------- #
# Property 1 — literal round trip
# --------------------------------------------------------------------------- #


@settings(max_examples=40, deadline=None, suppress_health_check=_SUPPRESS)
@given(ast=_expr_ast())
def test_property_1_literal_round_trip(ast):
    """Property 1: ``parse(format(ast)) == ast`` over generated expression trees.

    Oracle: structural AST equality.  The reference AST holds each literal's
    source spelling, so equality proves the literal bytes — including ``\\n``,
    ``\\t``, ``\\"`` and ``\\\\`` escapes — survived format-then-parse unchanged.
    """
    parser = _parser()
    source = _render_ast(ast)
    tree = parser.parse_expr(source)

    decoded = _decode_expr(tree)
    assert decoded == ast, f"{source!r} round-tripped to {decoded!r}, not {ast!r}"

    # The parser's own tree must also survive a second render/parse cycle, which
    # pins the grouping (parenthesisation) rather than just the leaf payloads.
    reparsed = parser.parse_expr(_render_ast(decoded))
    assert reparsed == tree, f"parser AST changed across a second pass of {source!r}"


# --------------------------------------------------------------------------- #
# Property 2 — formatter idempotency
# --------------------------------------------------------------------------- #


@settings(max_examples=30, deadline=None, suppress_health_check=_SUPPRESS)
@given(source=_program_source)
def test_property_2_formatter_idempotency(source):
    """Property 2: ``fmt(fmt(x)) == fmt(x)`` for valid programs.

    Oracle: whole-output text equality of the formatter applied twice.  This is
    the property that would have caught the §6.3 formatter-corruption bug.
    """
    _generated_or_rejected(source)

    once = _fmt(source)
    # Non-vacuity inside the property itself: generated programs never use the
    # default unit of 4, so a no-op formatter must fail here, not pass silently.
    assert once != source, "the formatter left a non-canonically indented program untouched"

    twice = _fmt(once)
    assert twice == once, (
        "fmt is not idempotent\n"
        f"--- input ---\n{source}\n--- first pass ---\n{once}\n--- second pass ---\n{twice}\n"
    )


# --------------------------------------------------------------------------- #
# Property 3 — formatter semantics preservation
# --------------------------------------------------------------------------- #


@settings(max_examples=30, deadline=None, suppress_health_check=_SUPPRESS)
@given(source=st.one_of(_program_source, st.sampled_from(_INVALID_PROGRAMS)))
def test_property_3_formatter_preserves_semantics(source):
    """Property 3: ``check(fmt(x))`` reports exactly what ``check(x)`` reports.

    Oracle: the canonical diagnostics tuple (error code + message, positions
    normalised).  For programs that check cleanly the oracle is strengthened to
    the whole generated C bundle: ``gen_bundle(fmt(x)) == gen_bundle(x)`` byte
    for byte, so a formatter that changed semantics could not slip through.
    """
    before = _diagnostic_signature(source)
    after = _diagnostic_signature(_fmt(source))
    assert after == before, (
        "the formatter changed the diagnostics\n"
        f"--- input ---\n{source}\n--- formatted ---\n{_fmt(source)}\n"
        f"before={before!r}\nafter={after!r}"
    )
    if before:
        return  # already an error: the diagnostics oracle is the whole property

    assert gen_bundle(_fmt(source), filename="prop3.pengu") == gen_bundle(
        source, filename="prop3.pengu"
    ), f"the formatter changed the generated bundle for\n{source}"


# --------------------------------------------------------------------------- #
# Property 4 — container round trip
# --------------------------------------------------------------------------- #

#: element type -> expression pushed in every iteration of the loop
_PUSH_ELEMENTS = {
    "int": "i",
    "float": "(i to float)",
    "string": '"element-{i}"',
    "bool": "(i % 2 == 0)",
}

_PUSH_PROGRAM = """weave main into int:
    var xs as list of {ty} is list of {ty}
    for i from 0 to {n}:
        calling xs.push with {element}
    if xs.len == {n}:
        return 0
    return 1
"""


@requires_cc
@requires_runtime
@settings(max_examples=8, deadline=None, suppress_health_check=_SUPPRESS)
@given(n=st.integers(min_value=0, max_value=1000),
       element_type=st.sampled_from(sorted(_PUSH_ELEMENTS)))
@example(n=0, element_type="int")
@example(n=1000, element_type="string")
@example(n=1000, element_type="float")
def test_property_4_container_round_trip(n, element_type):
    """Property 4: ``push`` x n gives ``len == n`` for n in [0, 1000].

    Oracle: the runtime invariant, checked by the compiled program itself (it
    exits 0 only when ``len`` equals the n the generator produced) over int,
    float, string and bool element types.
    """
    source = _PUSH_PROGRAM.format(ty=element_type, n=n, element=_PUSH_ELEMENTS[element_type])
    result = compile_run(source, tag="prop4", expect_exit=0)
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# Property 5 — integer arithmetic matches C int32_t
# --------------------------------------------------------------------------- #

_INT32_MIN = -(2 ** 31)
_INT32_MAX = 2 ** 31 - 1


@st.composite
def _int32_case(draw) -> Tuple[int, str, int]:
    """An ``(a, op, b)`` triple with the UB combinations excluded."""
    a = draw(st.integers(min_value=_INT32_MIN, max_value=_INT32_MAX))
    b = draw(st.integers(min_value=_INT32_MIN, max_value=_INT32_MAX))
    op = draw(st.sampled_from(("+", "-", "*", "/", "%")))
    if op in ("/", "%"):
        # Division by zero traps, and INT32_MIN / -1 overflows.
        assume(b != 0 and not (a == _INT32_MIN and b == -1))
    return (a, op, b)


def _c_int32_literal(value: int) -> str:
    return "INT32_MIN" if value == _INT32_MIN else str(value)


def _c_reference_output(cases: Sequence[Tuple[int, str, int]], workdir: Path) -> str:
    """Compiles and runs the C ``int32_t`` reference for `cases`; returns stdout."""
    compiler = next((name for name in ("gcc", "clang", "cc") if have_tool(name)), None)
    assert compiler, "no C compiler on PATH"
    lines = ["#include <stdio.h>", "#include <stdint.h>", "", "int main(void) {"]
    for a, op, b in cases:
        lines.append(
            f'    printf("%d\\n", (int)((int32_t)({_c_int32_literal(a)}) {op} '
            f'(int32_t)({_c_int32_literal(b)})));'
        )
    lines += ["    return 0;", "}"]
    source = workdir / "reference.c"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    exe = workdir / ("reference.exe" if os.name == "nt" else "reference")
    built = subprocess.run(
        [compiler, "-O1", "-fwrapv", "-std=c99", "-o", str(exe), str(source)],
        capture_output=True, text=True, timeout=300,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr
    return run.stdout


def _pengu_arith_source(cases: Sequence[Tuple[int, str, int]]) -> str:
    lines = ["import std.spark", "", "weave main into int:"]
    for a, op, b in cases:
        lines.append(f"    calling spark.println_int with (({a}) {op} ({b}))")
    lines.append("    return 0")
    return "\n".join(lines) + "\n"


@requires_cc
@requires_runtime
@settings(max_examples=6, deadline=None, suppress_health_check=_SUPPRESS)
@given(cases=st.lists(_int32_case(), min_size=1, max_size=6))
@example(cases=[(_INT32_MAX, "+", 1), (_INT32_MIN, "-", 1), (_INT32_MAX, "*", 2)])
@example(cases=[(_INT32_MIN, "/", 2), (7, "/", -3), (7, "%", -3), (-7, "%", 3)])
@example(cases=[(_INT32_MIN, "*", _INT32_MIN), (_INT32_MAX, "-", _INT32_MIN)])
def test_property_5_int32_arithmetic_matches_c(cases):
    """Property 5: ``a op b`` matches C ``int32_t`` semantics, limits included.

    Oracle: the stdout of the Pengu program (built with the documented release
    contract ``-fwrapv``, roadmap 5.1) compared with the stdout of a real C
    reference program compiled from the same triples with ``-fwrapv``.
    """
    with tempfile.TemporaryDirectory(prefix="prop5_", dir=BUILD_DIR) as workdir:
        expected = _c_reference_output(cases, Path(workdir))
    result = compile_run(_pengu_arith_source(cases), tag="prop5",
                         profile="release", expect_exit=0)
    assert result.stdout == expected, (
        f"int32 arithmetic diverges from C for {cases!r}\n"
        f"pengu={result.stdout!r}\nc={expected!r}\n{result.stderr}"
    )


# --------------------------------------------------------------------------- #
# Property 6 — transmute / to keep the value within the same type
# --------------------------------------------------------------------------- #


@st.composite
def _same_type_value(draw) -> Tuple[str, str]:
    """``(type, literal)`` for one of the primitive types."""
    kind = draw(st.sampled_from(("int", "float", "bool", "char", "string")))
    if kind == "int":
        literal = str(draw(st.integers(min_value=_INT32_MIN, max_value=_INT32_MAX)))
    elif kind == "float":
        literal = repr(draw(st.floats(min_value=-1e6, max_value=1e6,
                                      allow_nan=False, allow_infinity=False)))
    elif kind == "bool":
        literal = draw(st.sampled_from(("true", "false")))
    elif kind == "char":
        literal = "'" + draw(st.sampled_from(_CHAR_POOL)) + "'"
    else:
        literal = draw(st.one_of(st.sampled_from(_STRING_SPELLINGS), _plain_string_literal()))
    return (kind, literal)


_SAME_TYPE_PROGRAM = """weave main into int:
    let v as {ty} is {literal}
    let p as {ty} is v to {ty}
    let q as {ty} is transmute v to {ty}
    if p == v and q == v:
        return 0
    return 1
"""


@requires_cc
@requires_runtime
@settings(max_examples=10, deadline=None, suppress_health_check=_SUPPRESS)
@given(value=_same_type_value())
@example(value=("int", "-2147483648"))
@example(value=("int", "2147483647"))
@example(value=("float", "-0.0"))
@example(value=("bool", "true"))
@example(value=("char", "'x'"))
@example(value=("string", r'"a\nb"'))
def test_property_6_same_type_casts_are_identity(value):
    """Property 6: ``to T`` and ``transmute … to T`` do not change a ``T`` value.

    Oracle: the compiled program compares the cast copy with the original and
    exits 0 only when both the ``to`` and the ``transmute`` copy compare equal.
    """
    kind, literal = value
    source = _SAME_TYPE_PROGRAM.format(ty=kind, literal=literal)
    result = compile_run(source, tag="prop6", expect_exit=0)
    assert result.returncode == 0, f"{source}\n{result.stdout}{result.stderr}"


# --------------------------------------------------------------------------- #
# Property 7 — compiler determinism
# --------------------------------------------------------------------------- #

_SUBPROCESS_BUILD = """
import sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0, {repo!r})
from pengu_project import PenguBuilder, ProjectConfig
from tests.conftest import REPO, BUILD_DIR

source = sys.stdin.read()
workdir = Path(tempfile.mkdtemp(prefix="prop7_", dir=BUILD_DIR))
try:
    entry = workdir / "prop7.pengu"
    entry.write_text(source, encoding="utf-8")
    cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
    path, cached = PenguBuilder(cfg).bundle(output_file=str(workdir / "bundle.c"))
    sys.stdout.write(Path(path).read_text(encoding="utf-8"))
finally:
    shutil.rmtree(workdir, ignore_errors=True)
""".format(repo=str(REPO))


def _bundle_in_subprocess(source: str, hash_seed: int, no_dce: bool) -> str:
    """A full project build in a fresh process/dir; returns the bundle text."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(hash_seed)
    if no_dce:
        env["PENGU_NO_DCE"] = "1"
    else:
        env.pop("PENGU_NO_DCE", None)
    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_BUILD], input=source, capture_output=True,
        text=True, cwd=str(REPO), env=env, timeout=300,
    )
    assert proc.returncode == 0, f"subprocess build failed:\n{proc.stderr}"
    return proc.stdout


def _build_twice_in_one_directory(source: str) -> Tuple[bytes, bytes, bool]:
    """Two real builds of the same source in the same build directory.

    Returns ``(first, second, second_was_served_from_cache)``; the second call
    goes through the bundle cache (``.bundle_hash``) path.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    workdir = Path(tempfile.mkdtemp(prefix="prop7cache_", dir=BUILD_DIR))
    try:
        entry = workdir / "prop7.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        output = str(workdir / "bundle.c")
        first_path, _ = PenguBuilder(cfg).bundle(output_file=output)
        first = Path(first_path).read_bytes()
        second_path, cached = PenguBuilder(cfg).bundle(output_file=output)
        return first, Path(second_path).read_bytes(), bool(cached)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@settings(max_examples=3, deadline=None, suppress_health_check=_SUPPRESS)
@given(source=_program_source)
def test_property_7_compiler_determinism(source):
    """Property 7: two builds of one source produce byte-identical C.

    Oracle: byte equality of the whole bundle, (a) across two in-process
    ``gen_bundle`` runs, (b) across two fresh subprocesses with different
    ``PYTHONHASHSEED`` values (the real cross-process check) both with DCE on and
    with ``PENGU_NO_DCE=1``, and (c) across the cache path — two builds in the
    same directory, where the second may be served from ``.bundle_hash``.
    """
    _generated_or_rejected(source)

    assert gen_bundle(source, filename="prop7.pengu") == gen_bundle(source, filename="prop7.pengu")

    with_dce_a = _bundle_in_subprocess(source, hash_seed=1, no_dce=False)
    with_dce_b = _bundle_in_subprocess(source, hash_seed=2, no_dce=False)
    assert with_dce_a == with_dce_b, "the C bundle depends on the process hash seed"

    without_dce_a = _bundle_in_subprocess(source, hash_seed=1, no_dce=True)
    without_dce_b = _bundle_in_subprocess(source, hash_seed=2, no_dce=True)
    assert without_dce_a == without_dce_b, "the DCE-disabled bundle is not deterministic"

    cached_first, cached_second, _ = _build_twice_in_one_directory(source)
    assert cached_first == cached_second, "the build cache changed the bundle bytes"


_DCE_PROGRAM = """import std.spark

weave unused_helper with z as int into int:
    return z * 3

weave main into int:
    calling spark.println_int with 1
    return 0
"""


@pytest.mark.xfail(
    strict=True,
    reason=(
        "counterexample: _DCE_PROGRAM generates 4178 bytes with DCE on and 17030 bytes with "
        "PENGU_NO_DCE=1, but compute_config_hash() ignores PENGU_NO_DCE, so both builds share a "
        "cache key and a rebuild in the same directory can be served the stale bundle"
    ),
)
def test_dce_flag_is_part_of_the_build_cache_key():
    """Extra pin (not one of the 7): the DCE toggle must change the cache key.

    Two builds whose artefacts differ must never share a cache key, otherwise
    ``PENGU_NO_DCE=1`` silently reuses the DCE'd bundle (observed while writing
    property 7).  Both halves are deterministic: the artefacts come from two
    separate fresh directories, and the key is whatever
    ``is_bundle_up_to_date`` compares.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    def build_and_key(no_dce: bool) -> Tuple[bytes, str]:
        if no_dce:
            os.environ["PENGU_NO_DCE"] = "1"
        else:
            os.environ.pop("PENGU_NO_DCE", None)
        workdir = Path(tempfile.mkdtemp(prefix="prop7dce_", dir=BUILD_DIR))
        try:
            entry = workdir / "prop7.pengu"
            entry.write_text(_DCE_PROGRAM, encoding="utf-8")
            cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
            builder = PenguBuilder(cfg)
            path, _ = builder.bundle(output_file=str(workdir / "bundle.c"))
            return Path(path).read_bytes(), builder.compute_config_hash()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    previous = os.environ.pop("PENGU_NO_DCE", None)
    try:
        dce_on, key_on = build_and_key(no_dce=False)
        dce_off, key_off = build_and_key(no_dce=True)
        assert dce_off != dce_on, "PENGU_NO_DCE did not change the generated bundle"
        assert key_off != key_on, (
            "PENGU_NO_DCE changes the bundle but not the build cache key "
            f"({len(dce_on)} vs {len(dce_off)} bytes, same key {key_on[:16]}): a rebuild in the "
            "same directory can be served the stale artefact"
        )
    finally:
        if previous is None:
            os.environ.pop("PENGU_NO_DCE", None)
        else:
            os.environ["PENGU_NO_DCE"] = previous


# --------------------------------------------------------------------------- #
# Non-vacuity guard
# --------------------------------------------------------------------------- #


def test_generator_corpus_is_non_trivial():
    """The strategies must generate a real corpus, or every property is vacuous.

    Requires: at least 20 of 60 drawn expression trees round-trip (with at least
    10 distinct renderings) and at least 20 of 60 drawn programs parse and check
    cleanly — and the formatter rewrites at least 20 of those valid programs.

    This is a plain test (no ``@given``) on purpose: it inspects the corpus the
    generators produce, and hypothesis shrinking would happily reduce that corpus
    to 60 identical minimal values before re-running these assertions.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # SearchStrategy.example() is fine here
        round_trips = 0
        renderings = set()
        parser = _parser()
        for _ in range(60):
            ast = _expr_ast().example()
            source = _render_ast(ast)
            try:
                decoded = _decode_expr(parser.parse_expr(source))
            except PenguError:  # a rendering the grammar rejects does not count
                continue
            assert decoded == ast
            round_trips += 1
            renderings.add(source)

        valid = 0
        rewritten = 0
        for _ in range(60):
            source = _program_source.example()
            try:
                check_ok(source)
            except PenguError:  # a program the checker rejects does not count
                continue
            valid += 1
            if _fmt(source) != source:
                rewritten += 1

    assert round_trips >= 20, f"expression strategy is nearly empty: {round_trips}/60"
    assert len(renderings) >= 10, f"expression strategy is degenerate: {len(renderings)} distinct"
    assert valid >= 20, f"program strategy is nearly empty: {valid}/60 valid programs"
    assert rewritten >= 20, f"the formatter rewrote only {rewritten}/{valid} generated programs"
