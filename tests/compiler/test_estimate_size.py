"""The LSP size estimator must match the runtime structs it claims to measure.

Hover is the only caller, but a wrong number is still a wrong answer shown to
the user.  `result` used to be estimated as `ok_size + err_size + 4`, which is
not the C layout at all and made `result of int to int` look like 12 bytes.
"""
from __future__ import annotations

import pytest

from pengu_parser.pengu_types import (
    INT_TYPE,
    STRING_TYPE,
    ListType,
    MapType,
    MaybeType,
    ResultType,
    estimate_size,
)

pytestmark = pytest.mark.smoke


def test_result_is_the_fixed_pengu_result_layout():
    assert estimate_size(ResultType(ok_type=INT_TYPE, err_type=STRING_TYPE)) == 24
    assert estimate_size(ResultType(ok_type=INT_TYPE, err_type=INT_TYPE)) == 24
    assert estimate_size(ResultType(ok_type=STRING_TYPE, err_type=STRING_TYPE)) == 24


def test_maybe_is_the_fixed_pengu_maybe_layout():
    assert estimate_size(MaybeType(element=INT_TYPE)) == 16
    assert estimate_size(MaybeType(element=STRING_TYPE)) == 16


def test_container_sizes_match_the_abi_v2_structs():
    assert estimate_size(ListType(element=INT_TYPE)) == 24
    assert estimate_size(MapType(key=STRING_TYPE, value=INT_TYPE)) == 32
