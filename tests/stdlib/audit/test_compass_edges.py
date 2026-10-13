"""``std.compass`` — path parsing edges, and the leak regression.

The parser helpers used to allocate a one-byte `string` per inspected byte and a
fresh substring per component. The churn program releases every documented-owned
result (a `list of string` owns each element) and drives the whole public
surface, so under ASan a residual internal allocation fails the run.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.compass

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave chk_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
    banish got

weave eat with s as string into void:
    banish s

weave eat_list with l as list of string into void:
    for e in l:
        banish e
    banish l
"""


def test_compass_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var p as string is "/home/user/docs/file.tar.gz"
    var rel as string is "a/b/c"
    var trailing as string is "/a/b/"
    var root as string is "/"
    var empty as string is ""

    calling chk_s with (calling compass.basename with p), "file.tar.gz", "basename"
    calling chk_s with (calling compass.dirname with p), "/home/user/docs", "dirname"
    calling chk_s with (calling compass.ext with p), ".gz", "ext"
    calling chk_s with (calling compass.stem with p), "file.tar", "stem"
    calling chk_s with (calling compass.file_stem with p), "file.tar", "file_stem"
    calling chk_s with (calling compass.normalize with "a/./b/../c"), "a/c", "normalize dotdot"
    calling chk_s with (calling compass.normalize with ""), ".", "normalize empty is dot"
    calling chk_s with (calling compass.basename with trailing), "b", "basename trailing slash"
    calling chk_s with (calling compass.basename with root), "", "basename root"
    calling chk_s with (calling compass.dirname with "a"), "", "dirname bare name"

    # predicates
    calling eq_b with (calling compass.is_absolute with p), true, "is_absolute"
    calling eq_b with (calling compass.is_absolute with rel), false, "relative is not absolute"
    calling eq_b with (calling compass.is_hidden with ".x"), true, "is_hidden"
    calling eq_b with (calling compass.has_wildcard with "a*"), true, "has_wildcard"
    calling eq_b with (calling compass.has_wildcard with "ab"), false, "no wildcard"

    # maybe-returning
    var par as maybe string is calling compass.parent with p
    calling eq_b with par.is_present, true, "parent present"
    if pv as string is par:
        calling eq_s with pv, "/home/user/docs", "parent value"
    banish par
    var par_root as maybe string is calling compass.parent with root
    calling eq_b with par_root.is_present, false, "parent of root is none"
    banish par_root
    var r1 as maybe string is calling compass.relative_to with "/a/b/c", "/a"
    calling eq_b with r1.is_present, true, "relative_to present"
    banish r1
    var r2 as maybe string is calling compass.relative_to with "/x/y", "/a"
    calling eq_b with r2.is_present, true, "relative_to computes a ../ path"
    banish r2

    # list-returning: owned elements, release each and the list
    var parts as list of string is calling compass.split with p
    calling eq_i with parts.len, 5, "split component count"
    calling eat_list with parts
    var comps as list of string is calling compass.components with p
    calling eq_i with comps.len, 5, "components count"
    calling eat_list with comps
    var sufs as list of string is calling compass.suffixes with p
    calling eq_i with sufs.len, 2, "suffixes count"
    calling eat_list with sufs
    var segs as list of string is list of string
    calling segs.push with "a"
    calling segs.push with "b"
    calling segs.push with "c"
    calling chk_s with (calling compass.join with segs), "a/b/c", "join"
    calling chk_s with (calling compass.join_all with segs), "a/b/c", "join_all"
    banish segs
    var pj as list of string is calling compass.split with p
    var one as string is calling compass.join with pj
    calling eat with one
    calling eat_list with pj

    # string-returning transforms
    calling chk_s with (calling compass.change_ext with p, ".txt"), "/home/user/docs/file.tar.txt", "change_ext"
    calling chk_s with (calling compass.add_ext with "readme", ".md"), "readme.md", "add_ext"
    calling chk_s with (calling compass.with_filename with p, "other.txt"), "/home/user/docs/other.txt", "with_filename"
    calling eat with (calling compass.without_extension with p)

    # empty input never crashes
    calling eq_b with (calling compass.is_absolute with empty), false, "is_absolute empty"
    calling chk_s with (calling compass.ext with empty), "", "ext empty"

    calling spark.println with "DONE"
    return 0
""")


def test_compass_no_internal_leak(compile_and_run):
    out = compile_and_run(_PRE + """
weave churn with p as string into void:
    calling eat with (calling compass.basename with p)
    calling eat with (calling compass.filename with p)
    calling eat with (calling compass.dirname with p)
    calling eat with (calling compass.ext with p)
    calling eat with (calling compass.stem with p)
    calling eat with (calling compass.file_stem with p)
    calling eat with (calling compass.normalize with p)
    calling eat with (calling compass.absolute with p)
    calling eat with (calling compass.with_filename with p, "x.txt")
    calling eat with (calling compass.change_ext with p, ".md")
    calling eat with (calling compass.add_ext with p, ".md")
    calling eat with (calling compass.without_extension with p)
    calling eat_list with (calling compass.split with p)
    calling eat_list with (calling compass.components with p)
    calling eat_list with (calling compass.suffixes with p)
    var parent as maybe string is calling compass.parent with p
    banish parent
    var isabs as bool is calling compass.is_absolute with p
    var hidden as bool is calling compass.is_hidden with p
    var wild as bool is calling compass.has_wildcard with p
    var matches as bool is calling compass.matches with p, "*.gz"
    var hascomp as bool is calling compass.has_component with p, "docs"

weave main into int:
    var paths as list of string is list of string
    calling paths.push with "/home/user/docs/file.tar.gz"
    calling paths.push with "a/b/c"
    calling paths.push with "/a/b/"
    calling paths.push with "/"
    calling paths.push with ""
    var i as int is 0
    while i < 60:
        for p in paths:
            calling churn with p
        set i is i + 1
    banish paths
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
