"""``std.archivum`` — file I/O edges and the ownership of what it returns.

`archivum` returns caller-owned payloads in three shapes that are easy to leak:
a `maybe string` for a whole file, a `maybe list of string` whose elements the
C bridge allocated, and a `maybe map of string to string` whose keys *and*
values are owned.  The helpers below release each shape correctly; the churn
program proves that doing so is leak-free under ASan.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.archivum
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

weave join2 with a as string, b as string into string:
    var parts as list of string is list of string
    calling parts.push with a
    calling parts.push with b
    var out as string is calling compass.join with parts
    banish parts
    return out

weave eat_maybe_list with ml as maybe list of string into void:
    if l as list of string is ml:
        for e in l:
            banish e
    banish ml

weave eat_list with l as list of string into void:
    for e in l:
        banish e
    banish l

weave eat_maybe_map with mm as maybe map of string to string into void:
    if m as map of string to string is mm:
        for k in m:
            var v as string is m at k
            banish k
            banish v
    banish mm
"""


def test_archivum_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var dir as string is "arch_tmp"
    calling archivum.create_dir with dir, true
    var path as string is calling join2 with dir, "data.txt"
    var content as string is "line1\\nline2\\nline3\\n"

    calling eq_b with (calling archivum.write_file with path, content), true, "write_file"
    calling eq_b with (calling archivum.exists with path), true, "exists"
    calling eq_b with (calling archivum.is_file with path), true, "is_file"
    calling eq_b with (calling archivum.is_dir with path), false, "file is not a dir"
    calling eq_b with (calling archivum.is_dir with dir), true, "is_dir"
    calling eq_b with (calling archivum.append_file with path, "line4\\n"), true, "append_file"

    # read_file owns its buffer
    var rf as maybe string is calling archivum.read_file with path
    calling eq_b with rf.is_present, true, "read_file present"
    if got as string is rf:
        calling eq_s with got, "line1\\nline2\\nline3\\nline4\\n", "read_file content"
    banish rf

    var rb as maybe string is calling archivum.read_bytes with path
    calling eq_b with rb.is_present, true, "read_bytes present"
    banish rb

    # read_lines returns four owned lines
    var rl as maybe list of string is calling archivum.read_lines with path
    calling eq_b with rl.is_present, true, "read_lines present"
    if lines as list of string is rl:
        calling eq_i with lines.len, 5, "read_lines count"
    calling eat_maybe_list with rl

    var cl as maybe int is calling archivum.count_lines with path
    if n as int is cl:
        calling eq_i with n, 5, "count_lines"
    banish cl

    var sz as maybe int is calling archivum.file_size with path
    calling eq_b with sz.is_present, true, "file_size present"
    if nbytes as int is sz:
        calling eq_b with (nbytes > 0), true, "file_size positive"
    banish sz

    # metadata: every key and value is owned by the caller
    var md as maybe map of string to string is calling archivum.metadata with path
    calling eq_b with md.is_present, true, "metadata present"
    if m as map of string to string is md:
        calling eq_b with (calling m.contains with "size"), true, "metadata size key"
    calling eat_maybe_map with md

    # read_dir / read_dir_full own each element
    var rd as maybe list of string is calling archivum.read_dir with dir
    calling eq_b with rd.is_present, true, "read_dir present"
    if names as list of string is rd:
        calling eq_i with names.len, 1, "read_dir count"
    calling eat_maybe_list with rd

    var rdf as list of string is calling archivum.read_dir_full with dir
    calling eq_i with rdf.len, 1, "read_dir_full count"
    calling eat_list with rdf

    # write_lines / read_first_n_lines / read_last_n_lines
    var lines_out as list of string is list of string
    calling lines_out.push with "a"
    calling lines_out.push with "b"
    calling lines_out.push with "c"
    var lines_path as string is calling join2 with dir, "lines.txt"
    calling eq_b with (calling archivum.write_lines with lines_path, lines_out), true, "write_lines"
    banish lines_out
    var first2 as maybe list of string is calling archivum.read_first_n_lines with lines_path, 2
    calling eq_b with first2.is_present, true, "read_first_n_lines present"
    calling eat_maybe_list with first2
    var last2 as maybe list of string is calling archivum.read_last_n_lines with lines_path, 2
    calling eq_b with last2.is_present, true, "read_last_n_lines present"
    calling eat_maybe_list with last2

    # copy / move / delete
    var dst as string is calling join2 with dir, "copy.txt"
    calling eq_b with (calling archivum.copy_file with path, dst, true), true, "copy_file"
    calling eq_b with (calling archivum.exists with dst), true, "copied file exists"
    calling eq_b with (calling archivum.move_file with dst, path, true), true, "move_file"
    calling eq_b with (calling archivum.delete_file with path), true, "delete_file"
    calling eq_b with (calling archivum.exists with path), false, "deleted file is gone"

    # missing paths never crash and take the absence branch
    var missing as string is calling join2 with dir, "nope.txt"
    var rmiss as maybe string is calling archivum.read_file with missing
    calling eq_b with rmiss.is_present, false, "missing read_file is none"
    banish rmiss
    var rdir_miss as maybe list of string is calling archivum.read_dir with missing
    calling eq_b with rdir_miss.is_present, false, "missing read_dir is none"
    banish rdir_miss
    var smiss as maybe int is calling archivum.file_size with missing
    calling eq_b with smiss.is_present, false, "missing file_size is none"
    banish smiss

    calling archivum.remove_dir with dir, true
    calling eq_b with (calling archivum.exists with dir), false, "removed dir is gone"

    banish path
    banish content
    banish dir
    banish lines_path
    banish dst
    banish missing

    calling spark.println with "DONE"
    return 0
""")


def test_archivum_no_internal_leak(compile_and_run):
    out = compile_and_run(_PRE + """
weave churn with path as string, dir as string into void:
    var a as maybe string is calling archivum.read_file with path
    banish a
    var b as maybe string is calling archivum.read_bytes with path
    banish b
    var c as maybe list of string is calling archivum.read_lines with path
    calling eat_maybe_list with c
    var d as maybe int is calling archivum.count_lines with path
    banish d
    var e as maybe int is calling archivum.file_size with path
    banish e
    var f as maybe map of string to string is calling archivum.metadata with path
    calling eat_maybe_map with f
    var g as maybe list of string is calling archivum.read_dir with dir
    calling eat_maybe_list with g
    var h as list of string is calling archivum.read_dir_full with dir
    calling eat_list with h
    var i as bool is calling archivum.exists with path
    var j as bool is calling archivum.is_file with path
    var k as bool is calling archivum.is_dir with dir
    var l as bool is calling archivum.is_readable with path
    var m as bool is calling archivum.is_writable with path
    var n as maybe float is calling archivum.modified_time with path
    banish n
    var o as maybe int is calling archivum.permissions with path
    banish o

weave main into int:
    var dir as string is "arch_churn"
    calling archivum.create_dir with dir, true
    var path as string is calling join2 with dir, "f.txt"
    var content as string is "one\\ntwo\\nthree\\n"
    calling archivum.write_file with path, content
    var iter as int is 0
    while iter < 25:
        calling churn with path, dir
        set iter is iter + 1
    calling archivum.remove_dir with dir, true
    banish path
    banish content
    banish dir
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
