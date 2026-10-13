"""``std.oracle`` — maybe / result edge cases and leak churn.

Pins the presence/absence contract (`is_some`/`is_none`, `unwrap_or`,
`unwrap_err`), the generic `map`/`filter` helpers, and that every box and its
payload are released exactly once.  Under ASan the churn loop catches a box or
payload that is never freed.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.oracle

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave inc with x as int into int:
    return x + 1

weave is_even with x as int into bool:
    return (x % 2) == 0
"""


def test_oracle_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    # --- maybe int -------------------------------------------------
    var s as maybe int is calling oracle.some_int with 3
    var n as maybe int is calling oracle.none_int
    calling eq_b with (calling s.is_some), true, "some is_some"
    calling eq_b with (calling s.is_none), false, "some is_none"
    calling eq_b with (calling n.is_some), false, "none is_some"
    calling eq_b with (calling n.is_none), true, "none is_none"
    calling eq_i with (calling s.unwrap), 3, "unwrap present"
    calling eq_i with (calling n.unwrap_or with 9), 9, "unwrap_or none"
    calling eq_i with (calling s.unwrap_or with 9), 3, "unwrap_or present"
    calling eq_i with (calling oracle.unwrap_int with s), 3, "oracle.unwrap_int"
    calling eq_i with (calling oracle.unwrap_or_int with n, 9), 9, "oracle.unwrap_or_int"

    var mapped as maybe int is calling s.map with inc
    calling eq_i with (calling mapped.unwrap), 4, "map present"
    banish mapped
    var kept as maybe int is calling s.filter with is_even
    calling eq_b with (calling kept.is_some), false, "filter rejects odd"
    banish kept
    var tl as list of int is calling s.to_list
    calling eq_i with tl.len, 1, "to_list present"
    banish tl
    var nl as list of int is calling n.to_list
    calling eq_i with nl.len, 0, "to_list none"
    banish nl
    var described as string is calling s.describe
    banish described

    # empty string payload is still a present maybe
    var es as maybe string is calling oracle.some_string with ""
    calling eq_b with (calling es.is_some), true, "empty string is present"
    banish es
    var ns as maybe string is calling oracle.none_string
    calling eq_b with (calling ns.is_none), true, "none string"
    banish ns

    banish s
    banish n

    # --- result of int to string -----------------------------------
    var okr as result of int to string is calling ok_of with 5
    var errr as result of int to string is calling err_of with "boom"
    calling eq_b with (calling okr.is_ok), true, "ok is_ok"
    calling eq_b with (calling okr.is_err), false, "ok is_err"
    calling eq_b with (calling errr.is_ok), false, "err is_ok"
    calling eq_b with (calling errr.is_err), true, "err is_err"
    calling eq_i with (calling okr.unwrap), 5, "unwrap ok"
    calling eq_s with (calling errr.unwrap_err), "boom", "unwrap_err"
    calling eq_i with (calling okr.unwrap_or with 9), 5, "unwrap_or ok"
    calling eq_i with (calling errr.unwrap_or with 9), 9, "unwrap_or err"
    var om as maybe int is calling okr.to_maybe
    calling eq_b with (calling om.is_some), true, "ok to_maybe"
    banish om
    var em as maybe int is calling errr.to_maybe
    calling eq_b with (calling em.is_some), false, "err to_maybe"
    banish em
    var rtl as list of int is calling okr.to_list
    banish rtl
    var rdesc as string is calling errr.describe
    banish rdesc
    banish okr
    banish errr

    # legacy concrete wrappers
    var li as ResultInt is calling oracle.result_ok_int with 7
    calling eq_b with (calling li.is_ok), true, "ResultInt ok"
    banish li.error_msg
    var le as ResultInt is calling oracle.result_err_int with "bad"
    calling eq_b with (calling le.is_ok), false, "ResultInt err"
    banish le.error_msg

    # Pair / Triple runes derive Nexus, so `banish` releases their fields.
    var p as oracle.Pair of string and int is with first is "k", second is 1
    banish p
    var tri as oracle.Triple of int and int and int is with first is 1, second is 2, third is 3
    banish tri

    calling spark.println with "DONE"
    return 0
""")


def test_oracle_no_internal_leak(compile_and_run):
    out = compile_and_run(_PRE + """
weave churn with s as maybe int, n as maybe int, okr as result of int to string, errr as result of int to string into void:
    var a as maybe int is calling s.map with inc
    banish a
    var b as maybe int is calling s.filter with is_even
    banish b
    var c as maybe int is calling s.or_else with n
    banish c
    var d as maybe int is calling s.and with n
    banish d
    var e as list of int is calling s.to_list
    banish e
    var f as string is calling s.describe
    banish f
    var g as maybe int is calling okr.to_maybe
    banish g
    var h as maybe string is calling errr.err
    banish h
    var i as string is calling okr.describe
    banish i
    var j as int is calling s.unwrap_or_else with inc_fallback

weave inc_fallback into int:
    return 0

weave main into int:
    var iter as int is 0
    while iter < 300:
        var s as maybe int is calling oracle.some_int with iter
        var n as maybe int is calling oracle.none_int
        var okr as result of int to string is calling ok_of with iter
        var errr as result of int to string is calling err_of with "e"
        calling churn with s, n, okr, errr
        banish s
        banish n
        banish okr
        banish errr
        set iter is iter + 1
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
