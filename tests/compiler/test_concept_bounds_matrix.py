"""Phase 2 item 2.1 — the concept-bound capability matrix.

Rule C1 (ROADMAP_2.0 Anexo C): these tests **compile** real sources with the real
checker and assert on the resulting diagnostic code. They do not read a table and
compare strings; they ask the compiler.

Rule C2: reverting the `CONCEPT_OPERATORS` table makes the assertions that
`Num` does NOT grant `==`/`<` fail, because the old code short-circuited those
checks through `TypeParam.is_numeric()`.

The contract (AUDIT_1.0_FASE2.md §1.1) is a **monotone chain**:

    none  -> everything (an unconstrained parameter makes no promise)
    Num       -> + - * / and unary -
    Integrum  -> Num plus % & | ^ << >> ~
    Par       -> == !=
    Ordo      -> < <= > >=

so adding a bound can only ever *add* capabilities. Before Phase 2, `Num`
satisfied `is_numeric()`, which the `==` and `<` checks also consulted, so
`T: Num` accepted `a < b` while `T: Par` rejected it -- adding a bound removed a
capability.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"

#: Internal operator name -> (source expression, result type, concept-table name).
OPERATORS = {
    "add": ("a + b", "T"),
    "sub": ("a - b", "T"),
    "mul": ("a * b", "T"),
    "div": ("a / b", "T"),
    "mod": ("a % b", "T"),
    "band": ("a & b", "T"),
    "bor": ("a | b", "T"),
    "shl": ("a << b", "T"),
    "eq": ("a == b", "bool"),
    "ne": ("a != b", "bool"),
    "lt": ("a < b", "bool"),
    "gt": ("a > b", "bool"),
    "le": ("a <= b", "bool"),
    "ge": ("a >= b", "bool"),
}

#: What each bound grants. This is the contract; `Num` must NOT grant `eq`/`lt`.
EXPECTED: dict = {
    # An UNBOUNDED `shard T` grants nothing: it may be instantiated with a rune
    # or a string, where these operators have no C translation. This is the
    # established behaviour (`tests/test_generics/fail_bounds_missing.pengu`
    # expects E0049 for `a + b` on an unbounded T). `where T: Any` is the
    # deliberate escape hatch and is tested separately below.
    None: set(),
    "Num": {"add", "sub", "mul", "div"},
    "Integrum": {"add", "sub", "mul", "div", "mod", "band", "bor", "shl"},
    "Par": {"eq", "ne"},
    "Ordo": {"lt", "gt", "le", "ge"},
}


def check(tmp_path, source, name="t.pengu"):
    """Runs the real CLI on `source` and returns (rc, combined output)."""
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
    return r.returncode, r.stdout + r.stderr


def probe(tmp_path, bound, op):
    """True when `bound` compiles an expression using `op` on a `T` value."""
    expr, ret = OPERATORS[op]
    where = "" if bound is None else f" where T: {bound}"
    src = (
        f"weave f shard T{where} with a as T, b as T into {ret}:\n"
        f"  return {expr}\n"
    )
    rc, out = check(tmp_path, src, f"probe_{bound}_{op}.pengu")
    if rc == 0:
        return True
    # Only E0049 counts as "the bound does not grant this"; anything else is a
    # different failure and must not be silently read as an expected rejection.
    assert "E0049" in out, f"{bound}/{op} failed for an unexpected reason:\n{out}"
    return False


# ---------------------------------------------------------------------------
# The matrix itself
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bound", [None, "Num", "Integrum", "Par", "Ordo"])
@pytest.mark.parametrize("op", sorted(OPERATORS))
def test_capability_matrix(tmp_path, bound, op):
    """Each (bound, operator) pair behaves exactly as the contract states.

    This is the 30-pair matrix of AUDIT_1.0.md §3.1, measured by compiling.
    """
    expected = op in EXPECTED[bound]
    actual = probe(tmp_path, bound, op)
    assert actual is expected, (
        f"bound {bound!r} with operator {op!r}: expected "
        f"{'accepted' if expected else 'E0049'}, got "
        f"{'accepted' if actual else 'E0049'}"
    )


def test_num_does_not_grant_equality(tmp_path):
    """The specific incoherence this item fixes.

    `T: Num` used to accept `a == b`, which made `Par` grant nothing.
    """
    assert probe(tmp_path, "Num", "eq") is False


def test_num_does_not_grant_ordering(tmp_path):
    """`T: Num` used to accept `a < b`, which made `Ordo` grant nothing."""
    assert probe(tmp_path, "Num", "lt") is False


def test_par_grants_equality_but_not_ordering(tmp_path):
    """`Par` is equality-only; ordering needs `Ordo`."""
    assert probe(tmp_path, "Par", "eq") is True
    assert probe(tmp_path, "Par", "lt") is False


def test_ordo_grants_ordering_but_not_equality(tmp_path):
    """`Ordo` is ordering-only; equality needs `Par`."""
    assert probe(tmp_path, "Ordo", "lt") is True
    assert probe(tmp_path, "Ordo", "eq") is False


# ---------------------------------------------------------------------------
# Monotonicity: adding a bound must never remove a capability
# ---------------------------------------------------------------------------

#: Monotonicity pairs. Both sides must be *constrained*: an unbounded
#: `shard T` is not the empty intersection, it is the absence of a promise (the
#: instantiation may be anything), so `[]` -> `["Num"]` is a *restriction*, not
#: an extension. Only constrained -> constrained is monotone, and that is the
#: property worth pinning.
CHAIN = [
    (["Num"], ["Num", "Ordo"]),        # add ordering to arithmetic
    (["Num"], ["Num", "Par"]),         # add equality to arithmetic
    (["Num"], ["Integrum"]),           # refine to integers
    (["Par"], ["Par", "Ordo"]),        # add ordering to equality
    (["Ordo"], ["Par", "Ordo"]),       # add equality to ordering
    (["Integrum"], ["Integrum", "Par"]),
    (["Par"], ["Num", "Par", "Ordo"]), # everything at once
]


@pytest.mark.parametrize("base,extended", CHAIN)
def test_adding_a_bound_never_removes_capability(tmp_path, base, extended):
    """Monotonicity, checked operator by operator by compiling.

    Before Phase 2 this failed in the most visible way: `T: Num` accepted
    `a < b`, `T: Num and T: Ordo` accepted it, but `T: Ordo` alone did not --
    and, worse, `T: Par` did not either.
    """
    base_bound = " and ".join(f"T: {b}" for b in base)
    ext_bound = " and ".join(f"T: {b}" for b in extended)
    for op in OPERATORS:
        expr, ret = OPERATORS[op]
        src_base = (
            f"weave f shard T where {base_bound} with a as T, b as T into {ret}:\n"
            f"  return {expr}\n"
        )
        src_ext = (
            f"weave f shard T where {ext_bound} with a as T, b as T into {ret}:\n"
            f"  return {expr}\n"
        )
        ok_base = check(tmp_path, src_base, f"mono_base_{op}.pengu")[0] == 0
        ok_ext = check(tmp_path, src_ext, f"mono_ext_{op}.pengu")[0] == 0
        assert not (ok_base and not ok_ext), (
            f"{base} accepted {op} but {extended} rejected it: adding a bound "
            "removed a capability"
        )


def test_unbounded_parameter_grants_nothing(tmp_path):
    """An unconstrained `shard T` has no concept evidence, so operators are rejected.

    It remains usable for operations that need no concept (`weave identity
    shard T with x as T into T`), which is asserted separately.
    """
    for op in OPERATORS:
        assert probe(tmp_path, None, op) is False, op


def test_unbounded_parameter_still_allows_concept_free_operations(tmp_path):
    """Passing an unconstrained `T` through must keep working.

    Rejecting every operator on an unbounded parameter must not make the
    parameter unusable: `identity`, `forward`, and container plumbing need no
    concept at all.
    """
    programs = {
        "identity": (
            "weave ident shard T with x as T into T:\n  return x\n"
            "weave main into int:\n  var a as int is calling ident with 5\n  return a\n"
        ),
        "in_list": (
            "weave first shard T with xs as list of T into T:\n  return (xs at 0)\n"
            "weave main into int:\n  var xs as list of int is [7, 8]\n"
            "  var v as int is calling first with xs\n  return v\n"
        ),
        "in_rune": (
            "rune Box shard T:\n  value as T\n"
            "weave make shard T with v as T into Box of T:\n"
            "  return with value is v\n"
            "weave main into int:\n  var b as Box of int is calling make with 3\n"
            "  return b.value\n"
        ),
    }
    for name, src in programs.items():
        rc, out = check(tmp_path, src, f"free_{name}.pengu")
        assert rc == 0, f"{name} no longer compiles:\n{out}"


def test_any_bound_is_open(tmp_path):
    """`where T: Any` is the explicit spelling of "unconstrained"."""
    for op in OPERATORS:
        expr, ret = OPERATORS[op]
        src = (
            f"weave f shard T where T: Any with a as T, b as T into {ret}:\n"
            f"  return {expr}\n"
        )
        assert check(tmp_path, src, f"any_{op}.pengu")[0] == 0, op
