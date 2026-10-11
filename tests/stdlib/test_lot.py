#!/usr/bin/env python3
"""End-to-end tests for ``std.lot`` (Chunk 6 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.lot`` is the pseudo-random family: seeding, the uniform core (``rand_int``,
``rand_float``, ``rand_range``), the named distributions, the collection helpers
(shuffle/sample/choice/permutation and their generic shard forms) and the
token/text helpers (charsets, hex, base64, UUID, passwords).  Since the module
was migrated to the Pengunic 2.1.0 contract, this suite is also the regression
pin for the eleven lot-relevant bugs of that migration; each of those carries a
``bN_`` prefix in its test name and asserts the observable invariant the fix
promises, never a hard-coded sequence -- the C ``rand()`` sequence is
platform-specific.

The programs never print a raw float: ``float`` renders through ``%g`` and an
exact stdout comparison on a distribution draw would be a guess.  Bounds,
finiteness and closeness are therefore checked *inside* the program (the
prelude's ``lot_finite`` / ``lot_close`` helpers panic on violation) and the
program prints ``ok`` or a boolean; only integers, booleans and alphabet strings
are compared byte-for-byte on the Python side.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: Three levels up: tests/stdlib/test_lot.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]

#: The alphanumeric alphabet ``rand_password`` uses with ``include_symbols``
#: false.  Kept in Python so the password test judges the *output*, not a
#: restatement of the module under test.
ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

#: The raw symbol set ``password_symbols`` documents.  It is 26 characters
#: (``len()`` of the literal in ``std/lot.pengu``), not 25: a test that pinned
#: 25 would fail against the module's own docstring and literal.
PASSWORD_SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_lot_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


#: One-line printers plus invariant helpers spliced into every program, so the
#: program can judge a random draw itself instead of shipping a float to Python.
#: ``lot_finite`` rejects NaN and absurd magnitudes; ``lot_close`` is the 0.001
#: tolerance the module's own internal harness uses; the rest are the small
#: collection predicates the assertions need.
_PRELUDE = '''
weave lot_int with v as int into void:
    calling spark.println with calling spark.str_int with v

weave lot_bool with v as bool into void:
    calling spark.println with calling spark.str_bool with v

weave lot_str with v as string into void:
    calling spark.println with v

weave lot_finite with v as float, label as string into void:
    if v != v:
        calling spark.panic with "{label}: NaN"
    let mag as float is if v < 0.0 then (0.0 - v) else v
    if mag > 1000000000.0:
        calling spark.panic with "{label}: out of range"

weave lot_not_nan with v as float, label as string into void:
    if v != v:
        calling spark.panic with "{label}: NaN"

weave lot_close with got as float, want as float, label as string into void:
    let diff as float is if got >= want then (got - want) else (want - got)
    if diff > 0.001:
        calling spark.panic with "{label}: float mismatch"

weave lot_all_distinct with xs as list of int into bool:
    var i as int is 0
    var n as int is xs.len
    while i < n:
        var j as int is i + 1
        while j < n:
            if (xs at i) == (xs at j):
                return false
            set j is j + 1
        set i is i + 1
    return true

weave lot_all_distinct_str with xs as list of string into bool:
    var i as int is 0
    var n as int is xs.len
    while i < n:
        var j as int is i + 1
        while j < n:
            if (xs at i) == (xs at j):
                return false
            set j is j + 1
        set i is i + 1
    return true

weave lot_has_char with s as string, c as string into bool:
    var i as int is 0
    while i < s.len:
        if (s at i) == c:
            return true
        set i is i + 1
    return false

weave lot_in_charset with s as string, charset as string into bool:
    var i as int is 0
    while i < s.len:
        if not (calling lot_has_char with charset, (s at i)):
            return false
        set i is i + 1
    return true
'''


def _run_main(body: str) -> subprocess.CompletedProcess:
    """Runs ``body`` as the statements of a ``main`` that imports spark and lot."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = [
        "import std.spark",
        "import std.lot",
        "import std.arithmancy",
        "",
        textwrap.dedent(_PRELUDE).strip("\n"),
        "",
        "weave main into int:",
        body,
        "    return 0",
        "",
    ]
    return run_pengu("\n".join(sections))


def _check(body: str, expected: str) -> None:
    """Runs ``body`` and asserts a clean exit plus the exact stdout ``expected``."""
    res = _run_main(body)
    assert res.returncode == 0, res.stderr
    assert res.stdout == expected, res.stderr


# ---------------------------------------------------------------------------
# Version, seeding and the uniform core
# ---------------------------------------------------------------------------

def test_lot_version_is_2_1_0():
    """``LOT_VERSION`` reports the migrated module revision ``2.1.0``."""
    _check("calling lot_str with lot.LOT_VERSION", "2.1.0\n")


def test_seed_reproduces_the_same_stream():
    """Seeding twice with the same value replays the same int and float draws."""
    _check('''
        calling lot.seed with 42
        let first as int is calling lot.rand_int
        let first_float as float is calling lot.rand_float
        calling lot.seed with 42
        let again as int is calling lot.rand_int
        let again_float as float is calling lot.rand_float
        calling lot_bool with (again == first)
        calling lot_bool with (again_float == first_float)
    ''', "true\ntrue\n")


def test_b7_negative_seed_is_repeatable():
    """B7: a negative seed is accepted and replays identically.

    The 2.0.0 C shim truncated the seed instead of hashing it, so two calls
    with ``-7`` could disagree.  Observably: the first draw after ``seed -7`` is
    the same both times, and it is a legal non-negative ``rand_int``.
    """
    _check('''
        calling lot.seed with -7
        let a as int is calling lot.rand_int
        calling lot.seed with -7
        let b as int is calling lot.rand_int
        calling lot_bool with (a == b)
        calling lot_bool with (a >= 0)
    ''', "true\ntrue\n")


def test_seed_from_time_and_pid_leave_a_usable_generator():
    """``seed_from_time`` and ``seed_from_pid`` both leave a usable generator."""
    _check('''
        calling lot.seed_from_time
        calling lot.seed_from_pid
        let r as int is calling lot.rand_int
        calling lot_bool with (r >= 0 and r <= (calling lot.rand_max))
    ''', "true\n")


def test_b10_rand_int_is_always_non_negative_and_within_rand_max():
    """B10: ``rand_int`` clamps libc's possibly-negative ``rand()`` at 0.

    2.0.0 passed the raw value through, so a negative draw was possible.  The
    contract is ``0 <= rand_int <= rand_max``; ``rand_max`` itself must be a
    real ``RAND_MAX`` (at least 32767).
    """
    _check('''
        let top as int is calling lot.rand_max
        calling lot_bool with (top >= 32767)
        var ok as bool is true
        var i as int is 0
        while i < 500:
            let r as int is calling lot.rand_int
            if r < 0 or r > top:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\ntrue\n")


def test_rand_float_stays_in_the_half_open_unit_interval():
    """``rand_float`` is ``>= 0.0`` and strictly ``< 1.0`` on every draw."""
    _check('''
        calling lot.seed with 7
        var ok as bool is true
        var i as int is 0
        while i < 500:
            let u as float is calling lot.rand_float
            if u < 0.0 or u >= 1.0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_rand_range_is_inclusive_at_both_ends():
    """``rand_range(1, 6)`` never leaves ``[1, 6]`` and reaches both endpoints."""
    _check('''
        calling lot.seed with 3
        var ok as bool is true
        var saw_lo as bool is false
        var saw_hi as bool is false
        var i as int is 0
        while i < 400:
            let v as int is calling lot.rand_range with 1, 6
            if v < 1 or v > 6:
                set ok is false
            if v == 1:
                set saw_lo is true
            if v == 6:
                set saw_hi is true
            set i is i + 1
        calling lot_bool with ok
        calling lot_bool with saw_lo
        calling lot_bool with saw_hi
    ''', "true\ntrue\ntrue\n")


def test_rand_range_returns_lo_for_degenerate_and_inverted_bounds():
    """``rand_range`` returns ``lo`` unchanged when ``lo >= hi``."""
    _check('''
        calling lot_int with (calling lot.rand_range with 5, 5)
        calling lot_int with (calling lot.rand_range with 9, 3)
        calling lot_int with (calling lot.rand_range with 0, 0)
        calling lot_int with (calling lot.rand_range with -4, -9)
    ''', "5\n9\n0\n-4\n")


def test_rand_range_float_is_half_open_and_clamps_inverted_bounds():
    """``rand_range_float`` is ``[lo, hi)`` and returns ``lo`` when ``lo >= hi``."""
    _check('''
        calling lot.seed with 11
        calling lot_close with (calling lot.rand_range_float with 3.0, 1.0), 3.0, "inverted"
        var ok as bool is true
        var i as int is 0
        while i < 300:
            let u as float is calling lot.rand_range_float with 2.0, 5.0
            if u < 2.0 or u >= 5.0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_rand_bool_honours_the_absorbing_probabilities():
    """``rand_bool`` (and ``rand_bool_with``) absorb at 0.0 and 1.0."""
    _check('''
        calling lot_bool with ((calling lot.rand_bool with 0.0) == false)
        calling lot_bool with ((calling lot.rand_bool with 1.0) == true)
        calling lot_bool with ((calling lot.rand_bool_with with 0.0) == false)
        calling lot_bool with ((calling lot.rand_bool_with with 1.0) == true)
        let fair as bool is calling lot.rand_bool
        calling lot_bool with (fair == true or fair == false)
    ''', "true\ntrue\ntrue\ntrue\ntrue\n")


def test_rand_bit_rand_sign_and_rand_coin_aliases():
    """``rand_bit`` is 0/1, ``rand_sign`` is -1/1, ``rand_coin`` is a bool."""
    _check('''
        calling lot.seed with 5
        var ok as bool is true
        var saw_zero as bool is false
        var saw_one as bool is false
        var i as int is 0
        while i < 200:
            let bit as int is calling lot.rand_bit
            if bit == 0:
                set saw_zero is true
            else:
                if bit == 1:
                    set saw_one is true
                else:
                    set ok is false
            let sign as int is calling lot.rand_sign
            if sign != -1 and sign != 1:
                set ok is false
            let coin as bool is calling lot.rand_coin
            if coin != true and coin != false:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
        calling lot_bool with saw_zero
        calling lot_bool with saw_one
    ''', "true\ntrue\ntrue\n")


# ---------------------------------------------------------------------------
# The named distributions
# ---------------------------------------------------------------------------

def test_rand_normal_is_finite_and_zero_stddev_returns_mean():
    """``rand_normal``/``rand_gauss`` are finite; a zero sigma is the mean."""
    _check('''
        calling lot.seed with 13
        var i as int is 0
        while i < 200:
            calling lot_finite with (calling lot.rand_normal with 0.0, 1.0), "normal"
            calling lot_finite with (calling lot.rand_gauss with 10.0, 2.0), "gauss"
            set i is i + 1
        calling lot_close with (calling lot.rand_normal with 7.0, 0.0), 7.0, "zero stddev"
        calling lot_str with "ok"
    ''', "ok\n")


def test_rand_exp_is_non_negative():
    """``rand_exp`` is non-negative, and a non-positive rate returns 0.0."""
    _check('''
        calling lot.seed with 17
        var ok as bool is true
        var i as int is 0
        while i < 300:
            let v as float is calling lot.rand_exp with 1.5
            if v < 0.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_exp with 0.0), 0.0, "non-positive rate"
        calling lot_bool with ok
    ''', "true\n")


def test_rand_poisson_is_non_negative():
    """``rand_poisson`` is a non-negative int; a non-positive rate yields 0."""
    _check('''
        calling lot.seed with 19
        var ok as bool is true
        var i as int is 0
        while i < 300:
            let v as int is calling lot.rand_poisson with 3.0
            if v < 0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
        calling lot_int with (calling lot.rand_poisson with 0.0)
    ''', "true\n0\n")


def test_b8_rand_lognormal_with_zero_sigma_returns_exp_of_mu():
    """B8: ``rand_lognormal(mu, 0.0)`` is exactly ``exp(mu)``.

    The old code went deterministic by accident (it dropped mu); the fix
    validates ``sigma`` and returns ``exp(mu)``.  With ``mu = 2.0`` the value
    must be ``e^2 = 7.389056`` within the harness' 0.001 tolerance, and a live
    lognormal draw must stay positive and finite.
    """
    _check('''
        calling lot.seed with 23
        calling lot_close with (calling lot.rand_lognormal with 2.0, 0.0), 7.389056, "exp(2)"
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let v as float is calling lot.rand_lognormal with 0.0, 1.0
            calling lot_finite with v, "lognormal"
            if v <= 0.0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_b2_rand_weibull_is_always_finite_and_non_negative():
    """B2: ``rand_weibull`` never yields ``inf`` or NaN.

    2.0.0 re-drew in a loop that could not terminate on a pathological
    generator and produced ``inf`` for ``u`` close to 1.0.  200 draws with
    ``shape 1.5`` and ``scale 2.0`` must all be finite and ``>= 0``.
    """
    _check('''
        calling lot.seed with 29
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let w as float is calling lot.rand_weibull with 1.5, 2.0
            calling lot_finite with w, "weibull"
            if w < 0.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_weibull with 0.0, 1.0), 0.0, "zero shape"
        calling lot_bool with ok
    ''', "true\n")


def test_b1_rand_gamma_never_returns_a_non_gamma_fallback():
    """B1: the silent ``scale * d`` fallback is gone.

    2.0.0 returned the non-gamma constant ``scale * (shape - 1/3)`` when the
    acceptance loop gave up.  Both branches must now be strictly positive and
    finite: 200 draws at ``(2.0, 1.0)`` and 200 at ``(0.5, 2.0)`` (the
    Ahrens-Dieter shape-below-one path).
    """
    _check('''
        calling lot.seed with 31
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let g as float is calling lot.rand_gamma with 2.0, 1.0
            calling lot_finite with g, "gamma shape 2.0"
            if g <= 0.0:
                set ok is false
            let small as float is calling lot.rand_gamma with 0.5, 2.0
            calling lot_finite with small, "gamma shape 0.5"
            if small <= 0.0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_rand_triangular_respects_its_support_and_bad_mode():
    """``rand_triangular`` stays in ``[lo, hi]`` and returns ``lo`` for bad args."""
    _check('''
        calling lot.seed with 37
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let t as float is calling lot.rand_triangular with 0.0, 5.0, 10.0
            if t < 0.0 or t > 10.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_triangular with 1.0, 99.0, 10.0), 1.0, "bad mode"
        calling lot_close with (calling lot.rand_triangular with 4.0, 4.0, 1.0), 4.0, "inverted"
        calling lot_bool with ok
    ''', "true\n")


def test_rand_beta_stays_in_the_unit_interval_and_validates_params():
    """``rand_beta`` is in ``[0, 1]``; non-positive shapes return 0.0."""
    _check('''
        calling lot.seed with 41
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let b as float is calling lot.rand_beta with 2.0, 5.0
            calling lot_finite with b, "beta"
            if b < 0.0 or b > 1.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_beta with 0.0, 1.0), 0.0, "zero a"
        calling lot_close with (calling lot.rand_beta with 1.0, 0.0), 0.0, "zero b"
        calling lot_bool with ok
    ''', "true\n")


def test_rand_vonmises_is_normalised_to_two_pi():
    """``rand_vonmises`` returns an angle in ``[0, 2*pi)``, even at kappa 0."""
    _check('''
        calling lot.seed with 43
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let angle as float is calling lot.rand_vonmises with 0.0, 4.0
            calling lot_finite with angle, "vonmises"
            if angle < 0.0 or angle >= arithmancy.TWO_PI:
                set ok is false
            set i is i + 1
        let flat as float is calling lot.rand_vonmises with 0.0, 0.0
        if flat < 0.0 or flat >= arithmancy.TWO_PI:
            set ok is false
        calling lot_bool with ok
    ''', "true\n")


def test_rand_pareto_is_at_least_one():
    """``rand_pareto`` is ``>= 1.0``; a non-positive alpha returns 0.0."""
    _check('''
        calling lot.seed with 47
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let v as float is calling lot.rand_pareto with 2.0
            calling lot_finite with v, "pareto"
            if v < 1.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_pareto with 0.0), 0.0, "zero alpha"
        calling lot_bool with ok
    ''', "true\n")


def test_rand_cauchy_is_finite_and_degenerate_returns_location():
    """``rand_cauchy`` draws are numbers (never NaN); gamma 0 returns ``x0``.

    Cauchy is heavy-tailed, so this asks only for "not NaN" rather than a
    magnitude bound: a legitimate tail draw may be very large.
    """
    _check('''
        calling lot.seed with 53
        var i as int is 0
        while i < 200:
            calling lot_not_nan with (calling lot.rand_cauchy with 0.0, 1.0), "cauchy"
            set i is i + 1
        calling lot_close with (calling lot.rand_cauchy with 3.0, 0.0), 3.0, "zero gamma"
        calling lot_str with "ok"
    ''', "ok\n")


def test_rand_chi_squared_is_non_negative():
    """``rand_chi_squared`` is non-negative and finite; ``k <= 0`` returns 0.0."""
    _check('''
        calling lot.seed with 59
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let v as float is calling lot.rand_chi_squared with 3
            calling lot_finite with v, "chi squared"
            if v < 0.0:
                set ok is false
            set i is i + 1
        calling lot_close with (calling lot.rand_chi_squared with 0), 0.0, "zero dof"
        calling lot_bool with ok
    ''', "true\n")


def test_rand_between_and_rand_uniform_alias_their_targets():
    """``rand_between`` and ``rand_uniform`` keep their targets' bounds."""
    _check('''
        calling lot.seed with 61
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let a as int is calling lot.rand_between with 1, 6
            if a < 1 or a > 6:
                set ok is false
            let u as float is calling lot.rand_uniform with 0.0, 4.0
            if u < 0.0 or u >= 4.0:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


# ---------------------------------------------------------------------------
# Collections: shuffle, choice, sample, permutation
# ---------------------------------------------------------------------------

def test_b6_shuffle_preserves_length_members_and_sum():
    """B6: ``shuffle`` permutes the input instead of rebuilding it.

    2.0.0 could drop or duplicate elements.  The multiset test here is length,
    sum, sum of squares and distinctness over ``0..9`` -- all four together
    pin ``{0..9}`` exactly, since no other 10-element multiset from ``0..9``
    can match every moment.
    """
    _check('''
        calling lot.seed with 67
        var xs as list of int is list of int
        var i as int is 0
        while i < 10:
            calling xs.push with i
            set i is i + 1
        let mixed as list of int is calling lot.shuffle with xs
        calling lot_int with (calling mixed.len)
        var total as int is 0
        var sum_sq as int is 0
        var in_range as bool is true
        for v in mixed:
            set total is total + v
            set sum_sq is sum_sq + v * v
            if v < 0 or v > 9:
                set in_range is false
        calling lot_int with total
        calling lot_int with sum_sq
        calling lot_bool with (calling lot_all_distinct with mixed)
        calling lot_bool with in_range
        let empty as list of int is list of int
        let empty_mixed as list of int is calling lot.shuffle with empty
        calling lot_int with (calling empty_mixed.len)
    ''', "10\n45\n285\ntrue\ntrue\n0\n")


def test_shuffle_string_keeps_every_element():
    """``shuffle_string`` returns every input word exactly once."""
    _check('''
        calling lot.seed with 71
        var words as list of string is list of string
        calling words.push with "a"
        calling words.push with "b"
        calling words.push with "c"
        let mixed as list of string is calling lot.shuffle_string with words
        calling lot_int with (calling mixed.len)
        var seen_a as bool is false
        var seen_b as bool is false
        var seen_c as bool is false
        for w in mixed:
            if w == "a":
                set seen_a is true
            if w == "b":
                set seen_b is true
            if w == "c":
                set seen_c is true
        calling lot_bool with (seen_a and seen_b and seen_c)
    ''', "3\ntrue\n")


def test_b9_choice_is_none_on_an_empty_list_and_a_member_otherwise():
    """B9: ``choice`` on an empty list is ``none``, otherwise a real member."""
    _check('''
        calling lot.seed with 73
        let empty as list of int is list of int
        let none_pick as maybe int is calling lot.choice with empty
        calling lot_bool with (none_pick is present)
        var xs as list of int is list of int
        calling xs.push with 7
        calling xs.push with 8
        var ok as bool is true
        var i as int is 0
        while i < 100:
            let pick as maybe int is calling lot.choice with xs
            if pick is present:
                if pick.value != 7 and pick.value != 8:
                    set ok is false
            else:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
        let empty_words as list of string is list of string
        let none_name as maybe string is calling lot.choice_string with empty_words
        calling lot_bool with (none_name is present)
        var words as list of string is list of string
        calling words.push with "x"
        let some_name as maybe string is calling lot.choice_string with words
        calling lot_bool with (some_name is present)
    ''', "false\ntrue\nfalse\ntrue\n")


def test_b3_choice_weighted_survives_int_max_weights():
    """B3: two ``INT_MAX`` weights must not overflow the cumulative total.

    2.0.0 summed the weights in a 32-bit int, so ``2147483647 + 2147483647``
    wrapped and the index fell outside the list (or crashed).  Over 300 draws
    the pick must always be present and one of the two items.
    """
    _check('''
        calling lot.seed with 79
        var items as list of int is list of int
        calling items.push with 0
        calling items.push with 1
        var weights as list of int is list of int
        calling weights.push with 2147483647
        calling weights.push with 2147483647
        var ok as bool is true
        var i as int is 0
        while i < 300:
            let pick as maybe int is calling lot.choice_weighted with items, weights
            if pick is present:
                if pick.value != 0 and pick.value != 1:
                    set ok is false
            else:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_choice_weighted_rejects_empty_mismatched_and_zero_weights():
    """``choice_weighted`` is ``none`` for empty/mismatched/all-zero inputs.

    It additionally never returns an item whose weight is 0: with weights
    ``[0, 7]`` every one of 100 draws must be the second item.
    """
    _check('''
        let empty as list of int is list of int
        let empty_w as list of int is list of int
        let a as maybe int is calling lot.choice_weighted with empty, empty_w
        calling lot_bool with (a is present)
        var items as list of int is list of int
        calling items.push with 1
        calling items.push with 2
        var one_w as list of int is list of int
        calling one_w.push with 5
        let b as maybe int is calling lot.choice_weighted with items, one_w
        calling lot_bool with (b is present)
        var zero_w as list of int is list of int
        calling zero_w.push with 0
        calling zero_w.push with 0
        let c as maybe int is calling lot.choice_weighted with items, zero_w
        calling lot_bool with (c is present)
        calling lot.seed with 83
        var mixed_w as list of int is list of int
        calling mixed_w.push with 0
        calling mixed_w.push with 7
        var ok as bool is true
        var i as int is 0
        while i < 100:
            let pick as maybe int is calling lot.choice_weighted with items, mixed_w
            if pick is present:
                if pick.value != 2:
                    set ok is false
            else:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "false\nfalse\nfalse\ntrue\n")


def test_choice_weighted_string_only_returns_positive_weight():
    """``choice_weighted_string`` ignores zero-weight entries."""
    _check('''
        calling lot.seed with 83
        var words as list of string is list of string
        calling words.push with "x"
        calling words.push with "y"
        var weights as list of int is list of int
        calling weights.push with 0
        calling weights.push with 7
        var ok as bool is true
        var i as int is 0
        while i < 100:
            let pick as maybe string is calling lot.choice_weighted_string with words, weights
            if pick is present:
                if pick.value != "y":
                    set ok is false
            else:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")


def test_sample_is_distinct_and_clamps_k_to_the_pool():
    """``sample`` draws without replacement and clamps ``k`` to the pool size."""
    _check('''
        calling lot.seed with 89
        var xs as list of int is list of int
        var i as int is 0
        while i < 10:
            calling xs.push with i
            set i is i + 1
        let hand as list of int is calling lot.sample with xs, 5
        calling lot_int with (calling hand.len)
        calling lot_bool with (calling lot_all_distinct with hand)
        let all as list of int is calling lot.sample with xs, 99
        calling lot_int with (calling all.len)
        let none as list of int is calling lot.sample with xs, 0
        calling lot_int with (calling none.len)
        var words as list of string is list of string
        calling words.push with "a"
        calling words.push with "b"
        let picks as list of string is calling lot.sample_string with words, 2
        calling lot_int with (calling picks.len)
        calling lot_bool with (calling lot_all_distinct_str with picks)
    ''', "5\ntrue\n10\n0\n2\ntrue\n")


def test_sample_with_replacement_and_sample_string_return_exactly_k():
    """``sample_with_replacement`` returns ``k`` draws from the pool."""
    _check('''
        calling lot.seed with 97
        var xs as list of int is list of int
        calling xs.push with 3
        calling xs.push with 4
        let rolls as list of int is calling lot.sample_with_replacement with xs, 7
        calling lot_int with (calling rolls.len)
        var ok as bool is true
        for r in rolls:
            if r != 3 and r != 4:
                set ok is false
        calling lot_bool with ok
        var words as list of string is list of string
        calling words.push with "a"
        calling words.push with "b"
        let names as list of string is calling lot.sample_string with words, 2
        calling lot_int with (calling names.len)
    ''', "7\ntrue\n2\n")


def test_permutation_is_a_real_permutation_of_zero_to_n_minus_one():
    """``permutation(n)`` holds each of ``0..n-1`` exactly once."""
    _check('''
        calling lot.seed with 101
        let order as list of int is calling lot.permutation with 8
        calling lot_int with (calling order.len)
        calling lot_bool with (calling lot_all_distinct with order)
        var total as int is 0
        var in_range as bool is true
        for v in order:
            set total is total + v
            if v < 0 or v > 7:
                set in_range is false
        calling lot_int with total
        calling lot_bool with in_range
        let zero as list of int is calling lot.permutation with 0
        calling lot_int with (calling zero.len)
    ''', "8\ntrue\n28\ntrue\n0\n")


def test_rand_choice_n_draws_with_replacement_and_string_variant():
    """``rand_choice_n`` is ``sample`` with replacement; the string form agrees."""
    _check('''
        calling lot.seed with 103
        var xs as list of int is list of int
        calling xs.push with 3
        calling xs.push with 4
        let draws as list of int is calling lot.rand_choice_n with xs, 9
        calling lot_int with (calling draws.len)
        var ok as bool is true
        for d in draws:
            if d != 3 and d != 4:
                set ok is false
        calling lot_bool with ok
        var words as list of string is list of string
        calling words.push with "a"
        calling words.push with "b"
        let names as list of string is calling lot.rand_choice_n_string with words, 4
        calling lot_int with (calling names.len)
        let empty as list of int is list of int
        let no_draws as list of int is calling lot.rand_choice_n with empty, 4
        calling lot_int with (calling no_draws.len)
    ''', "9\ntrue\n4\n0\n")


def test_rand_sample_weighted_is_distinct_and_needs_a_positive_weight():
    """``rand_sample_weighted`` draws distinct items or returns empty."""
    _check('''
        calling lot.seed with 107
        var items as list of int is list of int
        var weights as list of int is list of int
        var i as int is 0
        while i < 6:
            calling items.push with i
            calling weights.push with (i + 1)
            set i is i + 1
        let picks as list of int is calling lot.rand_sample_weighted with items, weights, 4
        calling lot_int with (calling picks.len)
        calling lot_bool with (calling lot_all_distinct with picks)
        var zero_w as list of int is list of int
        var j as int is 0
        while j < 6:
            calling zero_w.push with 0
            set j is j + 1
        let bad as list of int is calling lot.rand_sample_weighted with items, zero_w, 2
        calling lot_int with (calling bad.len)
    ''', "4\ntrue\n0\n")


# ---------------------------------------------------------------------------
# Generic shard forms
# ---------------------------------------------------------------------------

def test_generic_shards_work_on_string_lists():
    """Every ``*_shard`` weave instantiates cleanly at ``list of string``."""
    _check('''
        calling lot.seed with 109
        var words as list of string is list of string
        calling words.push with "a"
        calling words.push with "b"
        calling words.push with "c"
        let one as maybe string is calling lot.rand_choice_shard with words
        calling lot_bool with (one is present)
        let mixed as list of string is calling lot.rand_shuffle_shard with words
        calling lot_int with (calling mixed.len)
        var seen_a as bool is false
        var seen_b as bool is false
        var seen_c as bool is false
        for w in mixed:
            if w == "a":
                set seen_a is true
            if w == "b":
                set seen_b is true
            if w == "c":
                set seen_c is true
        calling lot_bool with (seen_a and seen_b and seen_c)
        let picks as list of string is calling lot.rand_sample_shard with words, 2
        calling lot_int with (calling picks.len)
        calling lot_bool with (calling lot_all_distinct_str with picks)
        let perm as list of string is calling lot.rand_permutation_shard with words
        calling lot_int with (calling perm.len)
        let empty as list of string is list of string
        let none as maybe string is calling lot.rand_choice_shard with empty
        calling lot_bool with (none is present)
    ''', "true\n3\ntrue\n2\ntrue\n3\nfalse\n")


def test_generic_shards_work_on_int_lists():
    """The same ``*_shard`` weaves instantiate at ``list of int``."""
    _check('''
        calling lot.seed with 113
        var nums as list of int is list of int
        var i as int is 0
        while i < 5:
            calling nums.push with i
            set i is i + 1
        let one as maybe int is calling lot.rand_choice_shard with nums
        calling lot_bool with (one is present)
        let mixed as list of int is calling lot.rand_shuffle_shard with nums
        calling lot_int with (calling mixed.len)
        calling lot_bool with (calling lot_all_distinct with mixed)
        var total as int is 0
        for v in mixed:
            set total is total + v
        calling lot_int with total
        let picks as list of int is calling lot.rand_sample_shard with nums, 3
        calling lot_int with (calling picks.len)
        calling lot_bool with (calling lot_all_distinct with picks)
        let perm as list of int is calling lot.rand_permutation_shard with nums
        calling lot_int with (calling perm.len)
    ''', "true\n5\ntrue\n10\n3\ntrue\n5\n")


# ---------------------------------------------------------------------------
# Charset generators, bytes and tokens
# ---------------------------------------------------------------------------

def test_charset_generators_respect_alphabet_and_length():
    """Every charset generator draws only from its alphabet, at length ``n``."""
    _check('''
        calling lot.seed with 127
        let letters as string is calling lot.rand_alpha with 24
        calling lot_int with letters.len
        calling lot_bool with (calling lot_in_charset with letters, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        let digits as string is calling lot.rand_digit_string with 12
        calling lot_int with digits.len
        calling lot_bool with (calling lot_in_charset with digits, "0123456789")
        let alnum as string is calling lot.rand_alnum_string with 20
        calling lot_int with alnum.len
        calling lot_bool with (calling lot_in_charset with alnum, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        let hexs as string is calling lot.rand_hex_string with 16
        calling lot_int with hexs.len
        calling lot_bool with (calling lot_in_charset with hexs, "0123456789abcdef")
        let custom as string is calling lot.rand_from_charset with "AB", 8
        calling lot_int with custom.len
        calling lot_bool with (calling lot_in_charset with custom, "AB")
        let blank as string is calling lot.rand_from_charset with "", 4
        calling lot_int with blank.len
        let no_letters as string is calling lot.rand_alpha with 0
        calling lot_int with no_letters.len
    ''', "24\ntrue\n12\ntrue\n20\ntrue\n16\ntrue\n8\ntrue\n0\n0\n")


def test_b4_rand_bytes_produces_real_bytes_and_lowercase_hex():
    """B4: ``rand_bytes`` is bytes, not a string of hex *characters*.

    2.0.0 faked the bytes with random hex characters, so every value was
    ``<= 15``. 32 real draws must all be in ``0..255`` and (with probability
    1 - 16**-32) at least one must exceed 15; ``rand_bytes_hex(4)`` is then 8
    lowercase hex characters.
    """
    _check('''
        calling lot.seed with 131
        let raw as list of int is calling lot.rand_bytes with 32
        calling lot_int with (calling raw.len)
        var in_range as bool is true
        var saw_wide as bool is false
        for b in raw:
            if b < 0 or b > 255:
                set in_range is false
            if b > 15:
                set saw_wide is true
        calling lot_bool with in_range
        calling lot_bool with saw_wide
        let hexs as string is calling lot.rand_bytes_hex with 4
        calling lot_int with hexs.len
        calling lot_bool with (calling lot_in_charset with hexs, "0123456789abcdef")
        let none as list of int is calling lot.rand_bytes with 0
        calling lot_int with (calling none.len)
    ''', "32\ntrue\ntrue\n8\ntrue\n0\n")


def test_byte_string_encodings_have_exact_lengths():
    """``rand_bytes_string`` is ``n`` long; ``rand_hex_upper`` is ``2n`` uppercase."""
    _check('''
        calling lot.seed with 137
        let packed as string is calling lot.rand_bytes_string with 16
        calling lot_int with packed.len
        let blank as string is calling lot.rand_bytes_string with 0
        calling lot_int with blank.len
        let upper as string is calling lot.rand_hex_upper with 4
        calling lot_int with upper.len
        calling lot_bool with (calling lot_in_charset with upper, "0123456789ABCDEF")
    ''', "16\n0\n8\ntrue\n")


def test_rand_base64_pads_to_a_multiple_of_four():
    """``rand_base64`` pads: ``n=1`` gets two ``=``, ``n=2`` one, ``n=3`` none."""
    res = _run_main('''
        calling lot.seed with 139
        let one as string is calling lot.rand_base64 with 1
        let two as string is calling lot.rand_base64 with 2
        let three as string is calling lot.rand_base64 with 3
        let blank as string is calling lot.rand_base64 with 0
        calling lot_str with one
        calling lot_str with two
        calling lot_str with three
        calling lot_int with blank.len
    ''')
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    assert len(lines) == 4, res.stdout
    one, two, three, blank_len = lines
    assert blank_len == "0"
    assert len(one) == 4 and one.endswith("==") and "=" not in one[:2], one
    assert len(two) == 4 and two.endswith("=") and "=" not in two[:3], two
    assert len(three) == 4 and "=" not in three, three
    for token in (one, two, three):
        assert re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", token), token


def test_rand_uuid4_has_the_version_4_shape():
    """``rand_uuid4`` is 36 chars shaped ``8-4-4-4-12`` with version/variant bits."""
    res = _run_main('''
        calling lot.seed with 149
        calling lot_str with (calling lot.rand_uuid4)
        calling lot_str with (calling lot.rand_uuid4)
        calling lot_str with (calling lot.rand_uuid4)
    ''')
    assert res.returncode == 0, res.stderr
    uuids = res.stdout.splitlines()
    assert len(uuids) == 3, res.stdout
    assert len(set(uuids)) == 3, uuids
    for uuid in uuids:
        assert len(uuid) == 36, uuid
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            uuid,
        ), uuid
        assert uuid[8] == "-" and uuid[13] == "-" and uuid[18] == "-" and uuid[23] == "-"
        assert uuid[14] == "4", uuid
        assert uuid[19] in "89ab", uuid


def test_b5_password_symbols_carries_real_braces():
    """B5: ``password_symbols`` carries real ``{`` and ``}`` characters.

    2.0.0 could not express braces (the code generator mistook them for
    interpolation), so the symbol set was missing them.  The weave returns the
    raw literal, 26 characters long, braces included.
    """
    _check('''
        let sym as string is calling lot.password_symbols
        calling lot_int with sym.len
        calling lot_bool with (calling lot_has_char with sym, "{")
        calling lot_bool with (calling lot_has_char with sym, (chr 125))
        calling lot_str with sym
    ''', "26\ntrue\ntrue\n" + PASSWORD_SYMBOLS + "\n")


def test_rand_password_lengths_and_alphabets():
    """``rand_password`` holds length ``n`` and only its documented alphabet."""
    res = _run_main('''
        calling lot.seed with 151
        let strong as string is calling lot.rand_password with 200, true
        let plain as string is calling lot.rand_password with 12
        calling lot_int with strong.len
        calling lot_str with strong
        calling lot_int with plain.len
        calling lot_str with plain
    ''')
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    assert len(lines) == 4, res.stdout
    assert lines[0] == "200"
    strong = lines[1]
    assert len(strong) == 200
    assert set(strong) <= set(ALNUM + PASSWORD_SYMBOLS), sorted(set(strong))
    assert lines[2] == "12"
    plain = lines[3]
    assert len(plain) == 12
    assert set(plain) <= set(ALNUM), sorted(set(plain))


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

def test_b11_thread_safety_smoke_still_works():
    """B11: the module's internal mutex keeps interleaved calls consistent.

    ``std.lot`` guards its global C generator with an internal ``_lock`` /
    ``_unlock`` pair, but exposes no thread API, so a real concurrent race
    cannot be written from a Pengu program.  This smoke test instead hammers
    every shared-state entry point in an interleaved loop (``rand_int``,
    ``rand_float``, ``shuffle``, ``choice_weighted``) and asserts the
    invariants survive 200 rounds: a lock that was left held would hang or
    corrupt these, and the module must stay usable.
    """
    _check('''
        calling lot.seed with 157
        var nums as list of int is list of int
        calling nums.push with 1
        calling nums.push with 2
        calling nums.push with 3
        var weights as list of int is list of int
        calling weights.push with 1
        calling weights.push with 1
        calling weights.push with 1
        var ok as bool is true
        var i as int is 0
        while i < 200:
            let r as int is calling lot.rand_int
            let u as float is calling lot.rand_float
            let mixed as list of int is calling lot.shuffle with nums
            let pick as maybe int is calling lot.choice_weighted with nums, weights
            if r < 0 or u < 0.0 or u >= 1.0:
                set ok is false
            if (calling mixed.len) != 3:
                set ok is false
            if pick is present:
                if pick.value != 1 and pick.value != 2 and pick.value != 3:
                    set ok is false
            else:
                set ok is false
            set i is i + 1
        calling lot_bool with ok
    ''', "true\n")
