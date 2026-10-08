"""Roadmap Phase 6 / item 6.5 — ``loom`` and ``tally`` overlap resolution.

The roadmap asked to "resolve the duplication (15 names)" by preferring ``loom``
or renaming the ``tally`` family, and flagged the risk that ``tally.mean`` users
expect an ``int``.

Measurement (this test's premise) refutes the "duplication" framing.  Of the 15
shared public names, **zero** share a signature:

===========================  ==============================  ==========================
name                         loom                            tally
===========================  ==============================  ==========================
``mean``                     ``float``                       ``int``
``median``                   ``maybe float``                 ``int``
``mode``                     ``maybe int``                   ``int``
``min_max``                  ``maybe Pair of int and int``   ``list of int``
``enumerate_pairs``          ``list of Pair of int,int``     ``list of list of int``
``windowed``                 ``list of int``, width          ``shard T``, width
``zip_with``                 ``int`` op code                 ``shard T/U/V`` + weave
``running_sum``              ``list of int``                 ``shard T: Num``
``flatten``                  ``list of list of int``         ``list of int``
``take``                     ``n`` required                  ``n`` defaults to 1
``repeat``/``sum``/``scan_left``/``is_sorted_*``  parameter naming only
===========================  ==============================  ==========================

``loom`` is the safe/``maybe`` family (``loom.mean([1,2]) == 1.5``), ``tally``
the lossy ``int`` family (``tally.mean([1,2]) == 1``).  They are two deliberate
API philosophies, not accidental duplicates, so **unifying them is a breaking
change for whichever family loses** and cannot be done inside a 1.0 hardening
phase.  Item 6.5 is therefore deferred to 1.1 with this measurement (see
``AUDIT_1.0_FASE6.md``).

What this file locks down instead is the *coexistence contract* until then:
both modules keep working, both keep their own semantics, and any future
unification has to be a deliberate, versioned decision rather than an accident.
"""

import pytest

from tests.conftest import compile_run, requires_runtime

# A 3-element list and a 2-element list, built explicitly: bare list literals
# cannot be passed in argument position (E0005).
_PREAMBLE = """import std.spark
import std.loom
import std.tally

weave two into list of int:
    var xs as list of int is list of int
    calling xs.push with 1
    calling xs.push with 2
    return xs

weave three into list of int:
    var xs as list of int is list of int
    calling xs.push with 1
    calling xs.push with 2
    calling xs.push with 4
    return xs

weave main into void:
"""


@requires_runtime
def test_loom_and_tally_both_remain_importable_and_distinct():
    """Both modules coexist with their own return types."""
    src = _PREAMBLE + (
        "    var l as float is calling loom.mean with (calling three)\n"
        "    var t as int is calling tally.mean with (calling three)\n"
        # The point is that the two disagree: loom keeps the fraction, tally
        # truncates. Compare with a tolerance so the test does not depend on
        # float formatting.
        "    calling spark.assert with (l > 2.3)\n"
        "    calling spark.assert with (l < 2.4)\n"
        "    calling spark.assert with (t == 2)\n"
    )
    compile_run(src, tag="loom_tally_mean")


@requires_runtime
def test_tally_mean_stays_lossy_int():
    """The contract users already depend on: tally.mean returns int."""
    src = _PREAMBLE + (
        "    var t as int is calling tally.mean with (calling two)\n"
        "    calling spark.assert with (t == 1)\n"
    )
    compile_run(src, tag="tally_mean_int")


@requires_runtime
def test_loom_mean_stays_exact_float():
    src = _PREAMBLE + (
        "    var l as float is calling loom.mean with (calling two)\n"
        "    calling spark.assert with (l == 1.5)\n"
    )
    compile_run(src, tag="loom_mean_float")


@requires_runtime
def test_empty_input_contracts_differ_by_design():
    """``loom`` signals absence with maybe; ``tally`` collapses to 0."""
    src = _PREAMBLE + (
        "    var empty as list of int is list of int\n"
        "    var lmode as maybe int is calling loom.mode with empty\n"
        "    var tmode as int is calling tally.mode with empty\n"
        "    calling spark.assert with (not (lmode is present))\n"
        "    calling spark.assert with (tmode == 0)\n"
    )
    compile_run(src, tag="loom_tally_empty")


@requires_runtime
def test_median_return_shapes_are_incompatible():
    """``loom.median`` is ``maybe float``; ``tally.median`` is ``int``."""
    src = _PREAMBLE + (
        "    var lm as maybe float is calling loom.median with (calling two)\n"
        "    var tm as int is calling tally.median with (calling two)\n"
        "    calling spark.assert with (lm is present)\n"
        "    calling spark.assert with (tm == 1)\n"
    )
    compile_run(src, tag="loom_tally_median")
