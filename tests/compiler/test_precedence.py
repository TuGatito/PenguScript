"""Phase 2 item 2.4 — operator precedence and associativity contract.

This file is the regression contract for any change to the LALR grammar. A
grammar refactor is only acceptable if **both** halves of this file stay green:

* the **tree shape** (`parse_expr`) pins associativity, precedence and the root
  node of a boolean expression;
* the **numeric value** (`compile_run`) proves the emitted C still computes the
  documented result, i.e. that the tree shape is actually honoured end to end.

Rule C1 (ROADMAP_2.0 Anexo C): neither half asserts on message prose. The first
half asserts on the parsed AST (a structural object), the second compiles and
executes a program and compares integers.

Why this exists
---------------
`pengu_parser/pengu_grammar.py` declares **no** `%left`/`%right` precedence
table. Every level of the expression cascade therefore produces shift/reduce
conflicts, and Lark resolves each one as *shift*. For a cascade written as
``bit_add: bit_add "+" bit_mul | bit_mul`` shift-wins happens to yield exactly
the right left-associativity, which is why the language works today. That is a
property of the dependency's default heuristic, not a guarantee of the language:
if the resolution ever flips, programs silently change meaning. This file turns
that implicit behaviour into an explicit, checked contract.

The expected values below are the source of truth; a change that perturbs any of
them is a language change and must be rejected or escalated, never "fixed" by
editing the numbers here.
"""

import operator
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pengu_parser.pengu_parser import PenguParser

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"

pytestmark = pytest.mark.timeout(300)


# ===========================================================================
# Half 1 — tree shape (no compiler needed)
# ===========================================================================

@pytest.fixture(scope="module")
def parser():
    return PenguParser()


#: (expression, expected root node, expected child node types)
#: `child_types` is checked only for the non-None entries, in order.
ASSOCIATIVITY_CASES = [
    ("1-2-3", "sub", ["sub", "int_lit"]),
    ("1-(2-3)", "sub", ["int_lit", "paren_expr"]),
    ("1+2+3", "add", ["add", "int_lit"]),
    ("2*3*4", "mul", ["mul", "int_lit"]),
    ("2*3%4", "mod", ["mul", "int_lit"]),
    ("1-2+3", "add", ["sub", "int_lit"]),
    ("8/4/2", "div", ["div", "int_lit"]),
    ("1<<2<<3", "shl", ["shl", "int_lit"]),
    ("1&2&3", "bitwise_and", ["bitwise_and", "int_lit"]),
    ("1|2|3", "bitwise_or", ["bitwise_or", "int_lit"]),
    ("1^2^3", "bitwise_xor", ["bitwise_xor", "int_lit"]),
    # `..` is a real token in the tree, unlike the operator aliases.
]

PRECEDENCE_CASES = [
    ("1+2*3", "add", ["int_lit", "mul"]),
    ("(1+2)*3", "mul", ["paren_expr", "int_lit"]),
    ("1*2+3", "add", ["mul", "int_lit"]),
    ("2*3+4*5", "add", ["mul", "mul"]),
    ("1+2==3", "eq", ["add", "int_lit"]),
    ("1+2<4", "lt", ["add", "int_lit"]),
    ("1<2==true", "eq", ["lt", "true_lit"]),
    # IMPLEMENTED bitwise levels, from the grammar cascade
    # (logic_or | -> logic_and & -> bit_xor ^ -> bit_shift):
    # `^` binds TIGHTER than `&`, which binds TIGHTER than `|`.
    # NOTE: LANGUAGE.md 6.1 lists `|`, `&` and `^` together as one level, so the
    # reference is looser than the implementation for `^`. This contract pins the
    # IMPLEMENTATION, because Phase 2 item 2.4 must not change semantics; the
    # documentation discrepancy is reported separately, not fixed here.
    ("1|2&3", "bitwise_or", ["int_lit", "bitwise_and"]),
    ("1&2|3", "bitwise_or", ["bitwise_and", "int_lit"]),
    ("1^2|3", "bitwise_or", ["bitwise_xor", "int_lit"]),
    ("1&2^3", "bitwise_and", ["int_lit", "bitwise_xor"]),
    ("1^2&3", "bitwise_and", ["bitwise_xor", "int_lit"]),
    ("1+2<<3", "shl", ["add", "int_lit"]),
    ("1<<2+3", "shl", ["int_lit", "add"]),
]

UNARY_CASES = [
    ("-5", "neg", ["int_lit"]),
    ("1 - -5", "sub", ["int_lit", "neg"]),
    ("-1 + 2", "add", ["neg", "int_lit"]),
    ("not true", "log_not", ["true_lit"]),
    ("~1", "bit_not", ["int_lit"]),
]

BOOLEAN_CASES = [
    # `or` binds looser than `and`.
    ("true and false or true", "bool_or", ["bool_and", "true_lit"]),
    ("true or false and true", "bool_or", ["true_lit", "bool_and"]),
    ("not true and false", "bool_and", ["log_not", "false_lit"]),
    ("not (true and false)", "log_not", ["paren_expr"]),
    ("true and true and false", "bool_and", ["bool_and", "false_lit"]),
]

RANGE_CASES = [
    ("1 to 5", "to_expr", ["int_lit", "int_lit"]),
    ("1 .. 5", "range_dotdot", ["int_lit", "..", "int_lit"]),
]

ALL_TREE_CASES = (ASSOCIATIVITY_CASES + PRECEDENCE_CASES + UNARY_CASES
                  + BOOLEAN_CASES + RANGE_CASES)


def _child_types(tree):
    """Child node types, or the literal text for raw Tokens (e.g. `..`)."""
    out = []
    for child in tree.children:
        data = getattr(child, "data", None)
        out.append(str(data) if data is not None else str(child))
    return out


@pytest.mark.parametrize("expr,root,children", ALL_TREE_CASES,
                         ids=[c[0] for c in ALL_TREE_CASES])
def test_tree_shape(parser, expr, root, children):
    """The parsed tree must have exactly this root and these child node types."""
    tree = parser.parse_expr(expr)
    assert str(tree.data) == root, (
        f"{expr!r} parsed as {tree.data!r}, expected {root!r} "
        f"(children: {_child_types(tree)})"
    )
    assert _child_types(tree) == children, (
        f"{expr!r} children were {_child_types(tree)}, expected {children}"
    )


@pytest.mark.parametrize("expr,root,_children", ALL_TREE_CASES,
                         ids=[c[0] for c in ALL_TREE_CASES])
def test_tree_is_stable_across_reparse(parser, expr, root, _children):
    """Re-parsing must be deterministic (guards against cache/table drift)."""
    first, second = parser.parse_expr(expr), parser.parse_expr(expr)
    assert str(first.data) == str(second.data) == root


# ===========================================================================
# Half 2 — numeric value, compiled and executed
# ===========================================================================

#: (label, PenguScript expression, expected integer value)
#: Every one of these is evaluated at run time by the compiled binary, so it
#: proves the emitted C honours the tree shape rather than merely that a tree
#: was built.
NUMERIC_CASES = [
    # The nine cases named by the Phase 2 task, plus the neighbours that pin the
    # levels a precedence table would have to get right.
    ("assoc-sub-left", "1 - 2 - 3", -4),
    ("assoc-sub-paren", "1 - (2 - 3)", 2),
    ("prec-add-mul", "1 + 2 * 3", 7),
    ("prec-paren-mul", "(1 + 2) * 3", 9),
    ("assoc-mod-left", "2 * 3 % 4", 2),
    ("unary-neg", "-5", -5),
    ("sub-then-neg", "1 - -5", 6),
    ("assoc-add-left", "1 + 2 + 3", 6),
    ("assoc-div-left", "8 / 4 / 2", 1),
    ("assoc-mul-left", "2 * 3 * 4", 24),
    ("prec-mul-then-add", "2 * 3 + 4 * 5", 26),
    ("prec-unary-mul", "-2 * 3", -6),
    ("prec-unary-add", "-1 + 2", 1),
    ("prec-add-then-shift", "1 + 2 << 3", 24),
    ("prec-shift-then-add", "1 << 2 + 3", 32),
    ("prec-bitand-xor", "1 & 2 ^ 3", 1),      # ^ tighter: 1 & (2^3) = 1
    ("impl-bitxor-tighter", "3 & 1 ^ 2", 3),   # ^ tighter: 3 & (1^2) = 3
    ("prec-bitor-and", "1 | 2 & 3", 3),
    ("assoc-xor-left", "1 ^ 2 ^ 3", 0),
    ("assoc-and-left", "1 & 2 & 3", 0),
    ("assoc-or-left", "1 | 2 | 3", 3),
    ("assoc-shl-left", "1 << 2 << 3", 32),
    ("cmp-lt-add", "1 + 2 < 4", True),
    ("cmp-eq-deep", "(2 * 3 + 4 * 5) == 26", True),
]


def _tokens(output):
    """Interpolated values: integers as int, booleans as True/False.

    `"{x}"` renders a `bool` as the word `true`/`false` and an integer as digits,
    so a value assertion has to accept both spellings to be meaningful.
    """
    out = []
    for tok in output.replace("\x1b", " ").replace("[", " ").replace(";", " ").split():
        if tok == "true":
            out.append(True)
        elif tok == "false":
            out.append(False)
        elif tok.lstrip("+-").isdigit():
            out.append(int(tok))
    return out


def _run_expression(tmp_path, expr, tag):
    """Compiles and runs a program that prints the value of `expr`."""
    source = (
        "import std.spark\n"
        "weave main into int:\n"
        f'    calling spark.println with "{{{expr}}}"\n'
        "    return 0\n"
    )
    path = tmp_path / f"{tag}.pengu"
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    result = subprocess.run(
        [PY, "-m", MODULE, "run", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return result


@pytest.mark.parametrize("label,expr,expected", NUMERIC_CASES,
                         ids=[c[0] for c in NUMERIC_CASES])
def test_numeric_value(tmp_path, label, expr, expected):
    """The compiled program must compute the documented integer."""
    result = _run_expression(tmp_path, expr, label)
    combined = result.stdout + result.stderr
    assert result.returncode == 0, (
        f"{expr!r} failed to build/run (rc={result.returncode}):\n{combined[:2000]}"
    )
    assert expected in _tokens(combined), (
        f"{expr!r} produced {_tokens(combined)!r}, expected to contain {expected} "
        f"(raw output: {combined[:600]!r})"
    )


def test_boolean_precedence_executes(tmp_path):
    """`and` binds tighter than `or`, and `not` tighter than `and`, at run time."""
    labels = [
        ("true and false or true", 1),
        ("true or false and false", 1),
        ("not true and false", 0),
        ("(true or false) and false", 0),
    ]
    lines = "\n".join(
        f'    calling spark.println with "{{if {e} then 1 else 0}}"'
        for e, _ in labels
    )
    source = (
        "import std.spark\n"
        "weave main into int:\n"
        f"{lines}\n"
        "    return 0\n"
    )
    path = tmp_path / "boolprec.pengu"
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    result = subprocess.run(
        [PY, "-m", MODULE, "run", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined[:2000]
    # The CLI writes build progress to stdout too, so take the LAST len(labels)
    # numeric lines -- those are the values the compiled program printed.
    numbers = _tokens(result.stdout)
    expected = [v for _, v in labels]
    assert numbers[-len(expected):] == expected, (
        f"got {numbers!r}, expected the run to end with {expected!r}\n{result.stdout[:600]}"
    )
