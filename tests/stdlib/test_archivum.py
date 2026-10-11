#!/usr/bin/env python3
"""End-to-end tests for ``std.archivum`` (Chunk 5 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.archivum`` answers every question twice: the ``maybe``/``bool`` family says
*is it there?* and the ``result of T to IoError`` family says *it failed, and
why*.  These tests pin both, plus the line helpers, the recursive tree helpers
(``copy_tree``/``walk``/``list_files_recursive``), the search helpers, the size
and permission probes and the ``enchanting compass.Path`` methods added by the
``2.1.0`` migration.

Each program builds exactly one unique base directory under ``/tmp`` (the name
embeds its own process id and a per-test suffix), works only inside it and
removes the whole tree before exiting, so no test can observe another test's
state -- or leave litter behind.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_archivum_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


# ---------------------------------------------------------------------------
# Program builders
# ---------------------------------------------------------------------------

#: Imports and the small dump helper every generated program shares.
_PREAMBLE = """\
import std.spark
import std.archivum
import std.compass
import std.rites
import std.oracle

weave dump with items as list of string into void:
    for it in items:
        calling spark.println with it
"""


def _run_arch(body: str, name: str) -> subprocess.CompletedProcess:
    """Runs ``body`` inside a program that owns a unique ``base`` directory.

    ``base`` is ``/tmp/pengu_arch_ext_<pid>_<name>``; the harness removes any
    leftover tree, recreates it, runs ``body`` and deletes it again.  Every
    path a test builds is derived from ``base``, so the tree it touches is
    exactly the one it cleans.
    """
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = [
        _PREAMBLE,
        "weave main into int:",
        "    let pid as int is calling rites.getpid",
        f'    var base as string is "/tmp/pengu_arch_ext_{{(pid to string)}}_{name}"',
        "    if calling archivum.exists with base:",
        "        calling archivum.remove_dir with base, true",
        "    calling archivum.create_dir with base, true",
        body,
        "    if calling archivum.exists with base:",
        "        calling archivum.remove_dir with base, true",
        "    return 0",
        "",
    ]
    return run_pengu("\n".join(sections))


def _print_int(expr: str) -> str:
    """One line of Pengu that prints the ``int`` expression ``expr``."""
    return f"calling spark.println with calling spark.str_int with ({expr})"


def _print_bool(expr: str) -> str:
    """One line of Pengu that prints the ``bool`` expression ``expr``."""
    return f"calling spark.println with calling spark.str_bool with ({expr})"


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``ARCHIVUM_VERSION`` reports the migrated module version ``2.1.0``."""
    res = _run_arch('''
        calling spark.println with archivum.ARCHIVUM_VERSION
    ''', "version")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.1.0\n"


# ---------------------------------------------------------------------------
# Text and byte round-trips
# ---------------------------------------------------------------------------

def test_write_file_then_read_file_round_trips_the_text():
    """``write_file`` stores the exact text and ``read_file`` gives it back."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        {_print_bool('calling archivum.write_file with p, "hello world"')}
        let got as maybe string is calling archivum.read_file with p
        {_print_bool("got is present")}
        calling spark.println with got.value
    ''', "roundtrip")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nhello world\n"


def test_write_text_and_read_text_alias_write_and_read_file():
    """The migrated ``write_text``/``read_text`` pair round-trips the same way."""
    res = _run_arch(f'''
        let p as string is "{{base}}/alias.txt"
        {_print_bool('calling archivum.write_text with p, "alias"')}
        let got as maybe string is calling archivum.read_text with p
        {_print_bool("got is present")}
        calling spark.println with got.value
    ''', "alias")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nalias\n"


def test_write_bytes_and_read_bytes_round_trip_a_buffer():
    """``write_bytes``/``read_bytes`` move an opaque buffer without decoding it."""
    res = _run_arch(f'''
        let p as string is "{{base}}/blob.bin"
        let payload as string is "abcXYZ"
        {_print_bool('calling archivum.write_bytes with p, payload')}
        let got as maybe string is calling archivum.read_bytes with p
        {_print_bool("(got.value) == payload")}
    ''', "bytes")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\n"


def test_append_file_creates_then_appends():
    """``append_file`` creates a missing file and appends to an existing one."""
    res = _run_arch(f'''
        let p as string is "{{base}}/append.txt"
        {_print_bool('calling archivum.append_file with p, "one"')}
        {_print_bool('calling archivum.append_file with p, "two"')}
        let got as maybe string is calling archivum.read_file with p
        {_print_int("got.value length")}
    ''', "append")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\n6\n"


def test_write_lines_and_append_lines_own_the_trailing_newline():
    """``write_lines`` joins with ``\\n`` plus a trailing newline; ``append_lines`` adds one."""
    res = _run_arch(f'''
        let p as string is "{{base}}/lines.txt"
        let first as list of string is ["one", "two"]
        {_print_bool("calling archivum.write_lines with p, first")}
        let after_first as maybe string is calling archivum.read_file with p
        {_print_int("after_first.value length")}
        let more as list of string is ["three"]
        {_print_bool("calling archivum.append_lines with p, more")}
        let after_more as maybe string is calling archivum.read_file with p
        calling spark.println with after_more.value
    ''', "writelines")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n8\ntrue\none\ntwo\nthree\n\n"


# ---------------------------------------------------------------------------
# Lines
# ---------------------------------------------------------------------------

def test_read_lines_splits_on_newline():
    """``read_lines`` splits ``"a\\nb\\nc"`` into the three expected elements."""
    res = _run_arch(f'''
        let p as string is "{{base}}/split.txt"
        calling archivum.write_file with p, "a\\nb\\nc"
        let lines as maybe list of string is calling archivum.read_lines with p
        {_print_int("lines.value.len")}
        calling dump with lines.value
    ''', "readlines")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\na\nb\nc\n"


def test_read_lines_counts_a_trailing_newline_as_an_extra_empty_line():
    """A file ending in ``\\n`` yields one more (empty) element, by contract."""
    res = _run_arch(f'''
        let p as string is "{{base}}/trailing.txt"
        calling archivum.write_file with p, "a\\nb\\n"
        let lines as maybe list of string is calling archivum.read_lines with p
        {_print_int("lines.value.len")}
        let ls as list of string is lines.value
        let last as string is ls at 2
        {_print_int("last length")}
    ''', "trailing")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n0\n"


def test_read_first_n_lines_takes_the_head_and_clamps():
    """``read_first_n_lines`` takes ``n`` leading lines, clamps a large ``n`` and empties on 0."""
    res = _run_arch(f'''
        let p as string is "{{base}}/head.txt"
        calling archivum.write_file with p, "a\\nb\\nc\\nd"
        let head as maybe list of string is calling archivum.read_first_n_lines with p, 2
        {_print_int("head.value.len")}
        calling dump with head.value
        let big as maybe list of string is calling archivum.read_first_n_lines with p, 99
        {_print_int("big.value.len")}
        let zero as maybe list of string is calling archivum.read_first_n_lines with p, 0
        {_print_int("zero.value.len")}
    ''', "head")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\na\nb\n4\n0\n"


def test_read_last_n_lines_takes_the_tail_and_clamps():
    """``read_last_n_lines`` takes the trailing ``n`` lines, clamps a large ``n`` and empties on 0."""
    res = _run_arch(f'''
        let p as string is "{{base}}/tail.txt"
        calling archivum.write_file with p, "a\\nb\\nc\\nd"
        let tail as maybe list of string is calling archivum.read_last_n_lines with p, 2
        {_print_int("tail.value.len")}
        calling dump with tail.value
        let big as maybe list of string is calling archivum.read_last_n_lines with p, 99
        {_print_int("big.value.len")}
        let zero as maybe list of string is calling archivum.read_last_n_lines with p, 0
        {_print_int("zero.value.len")}
    ''', "tail")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\nc\nd\n4\n0\n"


def test_count_lines_counts_the_split_elements():
    """``count_lines`` counts ``\\n``-separated elements (a trailing newline counts once more)."""
    res = _run_arch(f'''
        let p as string is "{{base}}/count.txt"
        calling archivum.write_file with p, "a\\nb\\nc\\n"
        let with_nl as maybe int is calling archivum.count_lines with p
        {_print_int("with_nl.value")}
        let q as string is "{{base}}/count2.txt"
        calling archivum.write_file with q, "a\\nb\\nc"
        let without_nl as maybe int is calling archivum.count_lines with q
        {_print_int("without_nl.value")}
        let missing as maybe int is calling archivum.count_lines with "{{base}}/nope.txt"
        {_print_bool("missing is present")}
    ''', "count")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n3\nfalse\n"


# ---------------------------------------------------------------------------
# Existence and classification
# ---------------------------------------------------------------------------

def test_exists_is_file_is_dir_classify_the_entries():
    """``exists``/``is_file``/``is_dir`` separate files, directories and missing paths."""
    res = _run_arch(f'''
        let f as string is "{{base}}/a.txt"
        let d as string is "{{base}}/adir"
        calling archivum.write_file with f, "x"
        calling archivum.create_dir with d, false
        {_print_bool("calling archivum.exists with f")}
        {_print_bool("calling archivum.is_file with f")}
        {_print_bool("calling archivum.is_dir with f")}
        {_print_bool("calling archivum.exists with d")}
        {_print_bool("calling archivum.is_file with d")}
        {_print_bool("calling archivum.is_dir with d")}
        {_print_bool('calling archivum.exists with "{base}/missing"')}
    ''', "classify")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfalse\ntrue\nfalse\ntrue\nfalse\n"


def test_read_dir_lists_names_and_read_dir_full_joins_them():
    """``read_dir`` returns bare names, ``read_dir_full`` joins each with the directory."""
    res = _run_arch(f'''
        let f as string is "{{base}}/a.txt"
        let d as string is "{{base}}/sub"
        calling archivum.write_file with f, "x"
        calling archivum.create_dir with d, false
        let names as maybe list of string is calling archivum.read_dir with base
        {_print_bool("names is present")}
        {_print_int("names.value.len")}
        let full as list of string is calling archivum.read_dir_full with base
        {_print_int("full.len")}
        let f0 as string is full at 0
        {_print_bool("(calling archivum.is_file with f0) or (calling archivum.is_dir with f0)")}
        let on_file as maybe list of string is calling archivum.read_dir with f
        {_print_bool("on_file is present")}
        let missing as maybe list of string is calling archivum.read_dir with "{{base}}/nope"
        {_print_bool("missing is present")}
    ''', "readdir")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n2\n2\ntrue\nfalse\nfalse\n"


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

def test_create_dir_with_parents_builds_nested_ancestors():
    """``create_dir`` builds missing ancestors only when ``parents`` is true."""
    res = _run_arch(f'''
        let nested as string is "{{base}}/x/y/z"
        {_print_bool("calling archivum.create_dir with nested, true")}
        {_print_bool("calling archivum.is_dir with nested")}
        let single as string is "{{base}}/single"
        {_print_bool("calling archivum.create_dir with single, false")}
        let orphan as string is "{{base}}/missing_parent/child"
        {_print_bool("calling archivum.create_dir with orphan, false")}
        {_print_bool("calling archivum.is_dir with orphan")}
    ''', "createdir")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\nfalse\nfalse\n"


def test_remove_dir_requires_recursive_for_a_non_empty_tree():
    """``remove_dir`` fails on a non-empty directory unless ``recursive`` is true."""
    res = _run_arch(f'''
        let tree as string is "{{base}}/tree"
        let inner as string is "{{base}}/tree/inner"
        calling archivum.create_dir with inner, true
        calling archivum.write_file with "{{base}}/tree/inner/f.txt", "x"
        {_print_bool("calling archivum.remove_dir with tree, false")}
        {_print_bool("calling archivum.remove_dir with tree, true")}
        {_print_bool("calling archivum.exists with tree")}
    ''', "removedir")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\ntrue\nfalse\n"


# ---------------------------------------------------------------------------
# Copy, move and rename
# ---------------------------------------------------------------------------

def test_copy_file_copies_and_honours_overwrite():
    """``copy_file`` refuses an existing destination unless ``overwrite`` is true."""
    res = _run_arch(f'''
        let src as string is "{{base}}/src.txt"
        let dst as string is "{{base}}/dst.txt"
        calling archivum.write_file with src, "S"
        {_print_bool("calling archivum.copy_file with src, dst, false")}
        let got as maybe string is calling archivum.read_file with dst
        {_print_bool('(got.value) == "S"')}
        {_print_bool("calling archivum.copy_file with src, dst, false")}
        {_print_bool("calling archivum.copy_file with src, dst, true")}
    ''', "copyfile")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfalse\ntrue\n"


def test_copy_tree_duplicates_a_nested_tree():
    """``copy_tree`` recreates subdirectories and copies every file below them."""
    res = _run_arch(f'''
        let tree as string is "{{base}}/tree"
        let inner as string is "{{base}}/tree/inner"
        calling archivum.create_dir with inner, true
        calling archivum.write_file with "{{base}}/tree/a.txt", "A"
        calling archivum.write_file with "{{base}}/tree/inner/b.txt", "B"
        let copied as string is "{{base}}/copied"
        {_print_bool("calling archivum.copy_tree with tree, copied")}
        let a as maybe string is calling archivum.read_file with "{{base}}/copied/a.txt"
        let b as maybe string is calling archivum.read_file with "{{base}}/copied/inner/b.txt"
        {_print_bool('(a.value) == "A"')}
        {_print_bool('(b.value) == "B"')}
        let files as list of string is calling archivum.list_files_recursive with copied
        {_print_int("files.len")}
    ''', "copytree")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\n2\n"


def test_move_file_and_rename_relocate_an_entry():
    """``move_file`` and ``rename`` relocate the entry and leave the source gone."""
    res = _run_arch(f'''
        let a as string is "{{base}}/a.txt"
        let b as string is "{{base}}/b.txt"
        let c as string is "{{base}}/c.txt"
        calling archivum.write_file with a, "A"
        {_print_bool("calling archivum.move_file with a, b, false")}
        {_print_bool("calling archivum.exists with a")}
        let got as maybe string is calling archivum.read_file with b
        {_print_bool('(got.value) == "A"')}
        {_print_bool("calling archivum.rename with b, c")}
        {_print_bool("calling archivum.exists with c")}
        {_print_bool("calling archivum.exists with b")}
    ''', "move")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\ntrue\ntrue\ntrue\nfalse\n"


# ---------------------------------------------------------------------------
# Metadata, sizes and permissions
# ---------------------------------------------------------------------------

def test_metadata_reports_size_and_entry_kind():
    """``metadata`` exposes the documented ``size``/``is_file``/``is_dir`` keys."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        calling archivum.write_file with p, "12345"
        let md as maybe map of string to string is calling archivum.metadata with p
        {_print_bool("md is present")}
        let m as map of string to string is md.value
        calling spark.println with (calling m.get with "size")
        calling spark.println with (calling m.get with "is_file")
        calling spark.println with (calling m.get with "is_dir")
        let missing as maybe map of string to string is calling archivum.metadata with "{{base}}/nope"
        {_print_bool("missing is present")}
    ''', "metadata")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n5\ntrue\nfalse\nfalse\n"


def test_file_size_and_dir_size_measure_bytes():
    """``file_size`` reads one file and ``dir_size`` sums a directory, recursively or not."""
    res = _run_arch(f'''
        let f1 as string is "{{base}}/f1.txt"
        let f2 as string is "{{base}}/f2.txt"
        calling archivum.write_file with f1, "12345"
        calling archivum.write_file with f2, "123"
        let one as maybe int is calling archivum.file_size with f1
        {_print_int("one.value")}
        let top as maybe int is calling archivum.dir_size with base, false
        {_print_int("top.value")}
        let sub as string is "{{base}}/sub"
        calling archivum.create_dir with sub, false
        calling archivum.write_file with "{{base}}/sub/big.txt", "1234567"
        let deep as maybe int is calling archivum.dir_size with base, true
        {_print_int("deep.value")}
        let missing as maybe int is calling archivum.file_size with "{{base}}/nope"
        {_print_bool("missing is present")}
        let not_a_dir as maybe int is calling archivum.dir_size with f1, false
        {_print_bool("not_a_dir is present")}
    ''', "sizes")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n8\n15\nfalse\nfalse\n"


def test_permissions_and_read_write_probes():
    """``permissions`` is present for a fresh file and ``is_readable``/``is_writable`` agree."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        calling archivum.write_file with p, "x"
        let perm as maybe int is calling archivum.permissions with p
        {_print_bool("perm is present")}
        {_print_bool("((perm.value) & 292) != 0")}
        {_print_bool("((perm.value) & 146) != 0")}
        {_print_bool("calling archivum.is_readable with p")}
        {_print_bool("calling archivum.is_writable with p")}
        {_print_bool('calling archivum.is_readable with "{base}/nope"')}
        {_print_bool('calling archivum.is_writable with "{base}/nope"')}
        {_print_bool("calling archivum.is_readable with base")}
        {_print_bool("calling archivum.is_writable with base")}
    ''', "perms")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\nfalse\nfalse\nfalse\nfalse\n"


def test_empty_file_and_empty_dir_probes():
    """``is_empty_file``/``is_empty_dir`` look at the entry kind before the size."""
    res = _run_arch(f'''
        let empty as string is "{{base}}/empty.txt"
        let full as string is "{{base}}/full.txt"
        calling archivum.write_file with empty, ""
        calling archivum.write_file with full, "x"
        let edir as string is "{{base}}/edir"
        let ndir as string is "{{base}}/ndir"
        calling archivum.create_dir with edir, false
        calling archivum.create_dir with ndir, false
        calling archivum.write_file with "{{base}}/ndir/inner.txt", "y"
        {_print_bool("calling archivum.is_empty_file with empty")}
        {_print_bool("calling archivum.is_empty_file with full")}
        {_print_bool("calling archivum.is_empty_file with base")}
        {_print_bool("calling archivum.is_empty_dir with edir")}
        {_print_bool("calling archivum.is_empty_dir with ndir")}
        {_print_bool("calling archivum.is_empty_dir with full")}
    ''', "empties")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\nfalse\ntrue\nfalse\nfalse\n"


# ---------------------------------------------------------------------------
# touch, delete and symlinks
# ---------------------------------------------------------------------------

def test_touch_creates_and_delete_file_removes():
    """``touch`` creates a missing file and ``delete_file`` removes it again."""
    res = _run_arch(f'''
        let p as string is "{{base}}/touched.txt"
        {_print_bool("calling archivum.touch with p")}
        {_print_bool("calling archivum.exists with p")}
        {_print_bool("calling archivum.is_file with p")}
        {_print_bool("calling archivum.delete_file with p")}
        {_print_bool("calling archivum.exists with p")}
        let d as string is "{{base}}/d"
        calling archivum.create_dir with d, false
        calling archivum.write_file with "{{base}}/d/inner.txt", "y"
        {_print_bool("calling archivum.delete_file with d")}
        {_print_bool("calling archivum.exists with d")}
    ''', "touch")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\nfalse\nfalse\ntrue\n"


def test_symlink_read_symlink_and_realpath():
    """``symlink``/``read_symlink``/``realpath`` name and resolve the link."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        let link as string is "{{base}}/latest"
        calling archivum.write_file with p, "x"
        {_print_bool("calling archivum.symlink with p, link")}
        {_print_bool("calling archivum.is_symlink with link")}
        let target as maybe string is calling archivum.read_symlink with link
        {_print_bool("(target.value) == p")}
        let abs_path as maybe string is calling archivum.realpath with p
        {_print_bool("abs_path is present")}
        {_print_bool("((abs_path.value) length) > 0")}
    ''', "symlink")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\n"


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def test_find_files_dirs_name_and_ext():
    """The ``find_*`` family filters by kind, exact basename and extension."""
    res = _run_arch(f'''
        let sub as string is "{{base}}/sub"
        calling archivum.create_dir with sub, false
        calling archivum.write_file with "{{base}}/a.txt", "1"
        calling archivum.write_file with "{{base}}/sub/b.log", "2"
        calling archivum.write_file with "{{base}}/sub/c.txt", "3"
        let rec as list of string is calling archivum.find_files with base, true
        {_print_int("rec.len")}
        let flat as list of string is calling archivum.find_files with base, false
        {_print_int("flat.len")}
        let dirs as list of string is calling archivum.find_dirs with base, true
        {_print_int("dirs.len")}
        let by_name as list of string is calling archivum.find_by_name with base, "b.log"
        {_print_int("by_name.len")}
        let by_log as list of string is calling archivum.find_by_ext with base, ".log"
        {_print_int("by_log.len")}
        let by_txt as list of string is calling archivum.find_by_ext with base, "txt"
        {_print_int("by_txt.len")}
    ''', "find")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n1\n1\n1\n2\n"


def test_walk_visits_every_directory():
    """``walk`` returns one inner list per directory, each starting with its own path."""
    res = _run_arch(f'''
        let sub as string is "{{base}}/sub"
        calling archivum.create_dir with sub, false
        calling archivum.write_file with "{{base}}/top.txt", "T"
        calling archivum.write_file with "{{base}}/sub/deep.txt", "D"
        let levels as list of list of string is calling archivum.walk with base
        {_print_int("levels.len")}
        var root_ok as bool is false
        var sub_ok as bool is false
        for node in levels:
            let head as string is node at 0
            if head == base:
                set root_ok is (node.len) == 3
            if head == sub:
                set sub_ok is (node.len) == 2
        {_print_bool("root_ok")}
        {_print_bool("sub_ok")}
        let missing as list of list of string is calling archivum.walk with "{{base}}/nope"
        {_print_int("missing.len")}
    ''', "walk")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\ntrue\ntrue\n0\n"


def test_glob_finds_a_fixture_from_its_own_directory():
    """``glob`` matches by name from the process working directory."""
    res = _run_arch(f'''
        let here as maybe string is calling rites.getcwd
        calling archivum.write_file with "{{base}}/pengu_arch_ext_fixture.txt", "x"
        {_print_bool("calling rites.chdir with base")}
        let hits as list of string is calling archivum.glob with "pengu_arch_ext_fixture.txt"
        {_print_int("hits.len")}
        let fname as string is calling compass.basename with (hits at 0)
        let want_name as string is "pengu_arch_ext_fixture.txt"
        {_print_bool("fname == want_name")}
        let none_hits as list of string is calling archivum.glob with "pengu_arch_ext_no_match.txt"
        {_print_int("none_hits.len")}
        if here is present:
            calling rites.chdir with here.value
    ''', "glob")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n1\ntrue\n0\n"


# ---------------------------------------------------------------------------
# Result variants: the ok paths
# ---------------------------------------------------------------------------

def test_read_file_result_ok_path():
    """``read_file_result`` is ``ok`` with the owned text for a present file."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        calling archivum.write_file with p, "R"
        let r as result of string to archivum.IoError is calling archivum.read_file_result with p
        {_print_bool("r.is_ok")}
        {_print_bool("not (calling r.is_err)")}
        calling spark.println with r.value
    ''', "rfok")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nR\n"


def test_read_file_result_err_paths_carry_the_cause():
    """A missing path is ``NotFound`` and a directory is ``IsADirectory``."""
    res = _run_arch(f'''
        let missing as result of string to archivum.IoError is calling archivum.read_file_result with "{{base}}/nope"
        {_print_bool("calling missing.is_err")}
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let as_dir as result of string to archivum.IoError is calling archivum.read_file_result with base
        {_print_bool("calling as_dir.is_err")}
        {_print_bool("(as_dir.error) == archivum.IoError.IsADirectory")}
    ''', "rferr")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\n"


def test_write_file_result_ok_and_err():
    """``write_file_result`` succeeds with ``ok(0)`` and rejects a directory."""
    res = _run_arch(f'''
        let r as result of int to archivum.IoError is calling archivum.write_file_result with "{{base}}/w.txt", "hi"
        {_print_bool("r.is_ok")}
        {_print_int("r.value")}
        let bad as result of int to archivum.IoError is calling archivum.write_file_result with base, "x"
        {_print_bool("calling bad.is_err")}
        {_print_bool("(bad.error) == archivum.IoError.IsADirectory")}
    ''', "wfres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n0\ntrue\ntrue\n"


def test_delete_file_result_ok_and_err():
    """``delete_file_result`` removes a file, reports ``NotFound`` and refuses a directory."""
    res = _run_arch(f'''
        let p as string is "{{base}}/gone.txt"
        calling archivum.write_file with p, "x"
        let r as result of int to archivum.IoError is calling archivum.delete_file_result with p
        {_print_bool("r.is_ok")}
        {_print_bool("calling archivum.exists with p")}
        let missing as result of int to archivum.IoError is calling archivum.delete_file_result with "{{base}}/nope"
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let as_dir as result of int to archivum.IoError is calling archivum.delete_file_result with base
        {_print_bool("(as_dir.error) == archivum.IoError.IsADirectory")}
    ''', "dfres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\ntrue\ntrue\n"


def test_read_lines_result_ok_and_err():
    """``read_lines_result`` succeeds with lines and reports the failure cause."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        calling archivum.write_file with p, "a\\nb"
        let r as result of list of string to archivum.IoError is calling archivum.read_lines_result with p
        {_print_bool("r.is_ok")}
        {_print_int("r.value.len")}
        let as_dir as result of list of string to archivum.IoError is calling archivum.read_lines_result with base
        {_print_bool("(as_dir.error) == archivum.IoError.IsADirectory")}
        let nope as string is "{{base}}/nope"
        let missing as result of list of string to archivum.IoError is calling archivum.read_lines_result with nope
        {_print_bool("(missing.error) == archivum.IoError.Unknown")}
    ''', "rlres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n2\ntrue\ntrue\n"


def test_write_and_append_lines_result_ok_and_err():
    """``write_lines_result``/``append_lines_result`` report ``ok(0)`` and reject a directory."""
    res = _run_arch(f'''
        let p as string is "{{base}}/lines.txt"
        let first as list of string is ["a", "b"]
        let wrote as result of int to archivum.IoError is calling archivum.write_lines_result with p, first
        {_print_bool("wrote.is_ok")}
        {_print_int("wrote.value")}
        let more as list of string is ["c"]
        let appended as result of int to archivum.IoError is calling archivum.append_lines_result with p, more
        {_print_bool("appended.is_ok")}
        let bad as result of int to archivum.IoError is calling archivum.append_lines_result with base, more
        {_print_bool("calling bad.is_err")}
        {_print_bool("(bad.error) == archivum.IoError.IsADirectory")}
    ''', "wlres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n0\ntrue\ntrue\ntrue\n"


def test_read_dir_result_ok_notfound_and_notafile():
    """``read_dir_result`` succeeds on a directory and distinguishes both error causes."""
    res = _run_arch(f'''
        let f as string is "{{base}}/a.txt"
        calling archivum.write_file with f, "x"
        calling archivum.create_dir with "{{base}}/sub", false
        let r as result of list of string to archivum.IoError is calling archivum.read_dir_result with base
        {_print_bool("r.is_ok")}
        {_print_int("r.value.len")}
        let nope as string is "{{base}}/nope"
        let missing as result of list of string to archivum.IoError is calling archivum.read_dir_result with nope
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let on_file as result of list of string to archivum.IoError is calling archivum.read_dir_result with f
        {_print_bool("(on_file.error) == archivum.IoError.NotAFile")}
    ''', "rdres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n2\ntrue\ntrue\n"


def test_create_dir_result_ok_and_err():
    """``create_dir_result`` creates ancestors and rejects a path occupied by a file."""
    res = _run_arch(f'''
        let nested as string is "{{base}}/a/b"
        let r as result of bool to archivum.IoError is calling archivum.create_dir_result with nested, true
        {_print_bool("r.is_ok")}
        {_print_bool("r.value")}
        {_print_bool("calling archivum.is_dir with nested")}
        let f as string is "{{base}}/file.txt"
        calling archivum.write_file with f, "x"
        let bad as result of bool to archivum.IoError is calling archivum.create_dir_result with f, true
        {_print_bool("calling bad.is_err")}
        {_print_bool("(bad.error) == archivum.IoError.IsADirectory")}
    ''', "cdres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\n"


def test_remove_dir_result_ok_and_err():
    """``remove_dir_result`` reports ``ok``, ``NotFound``, ``NotAFile`` and ``Unknown``."""
    res = _run_arch(f'''
        let tree as string is "{{base}}/tree"
        calling archivum.create_dir with "{{base}}/tree/inner", true
        let r as result of bool to archivum.IoError is calling archivum.remove_dir_result with tree, true
        {_print_bool("r.is_ok")}
        {_print_bool("calling archivum.exists with tree")}
        let missing as result of bool to archivum.IoError is calling archivum.remove_dir_result with "{{base}}/nope"
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let f as string is "{{base}}/file.txt"
        calling archivum.write_file with f, "x"
        let on_file as result of bool to archivum.IoError is calling archivum.remove_dir_result with f
        {_print_bool("(on_file.error) == archivum.IoError.NotAFile")}
        let keep as string is "{{base}}/keep"
        calling archivum.create_dir with "{{base}}/keep/inner", true
        let non_empty as result of bool to archivum.IoError is calling archivum.remove_dir_result with keep, false
        {_print_bool("(non_empty.error) == archivum.IoError.Unknown")}
    ''', "rmres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\ntrue\ntrue\ntrue\n"


def test_copy_file_result_ok_and_err():
    """``copy_file_result`` copies, then reports ``NotFound`` and ``IsADirectory``."""
    res = _run_arch(f'''
        let src as string is "{{base}}/src.txt"
        let dst as string is "{{base}}/dst.txt"
        calling archivum.write_file with src, "S"
        let r as result of bool to archivum.IoError is calling archivum.copy_file_result with src, dst
        {_print_bool("r.is_ok")}
        {_print_bool("r.value")}
        let got as maybe string is calling archivum.read_file with dst
        {_print_bool('(got.value) == "S"')}
        let nope as string is "{{base}}/nope"
        let dst2 as string is "{{base}}/x"
        let missing as result of bool to archivum.IoError is calling archivum.copy_file_result with nope, dst2
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let as_dir as result of bool to archivum.IoError is calling archivum.copy_file_result with base, "{{base}}/y"
        {_print_bool("(as_dir.error) == archivum.IoError.IsADirectory")}
    ''', "cfres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\n"


def test_copy_tree_result_ok_and_err():
    """``copy_tree_result`` copies a tree, then reports ``NotFound`` and ``IsADirectory``."""
    res = _run_arch(f'''
        let tree as string is "{{base}}/tree"
        calling archivum.create_dir with tree, false
        calling archivum.write_file with "{{base}}/tree/a.txt", "A"
        let copied as string is "{{base}}/copied"
        let r as result of bool to archivum.IoError is calling archivum.copy_tree_result with tree, copied
        {_print_bool("r.is_ok")}
        {_print_bool("r.value")}
        let files as list of string is calling archivum.list_files_recursive with copied
        {_print_int("files.len")}
        let nope as string is "{{base}}/nope"
        let dst2 as string is "{{base}}/x"
        let missing as result of bool to archivum.IoError is calling archivum.copy_tree_result with nope, dst2
        {_print_bool("(missing.error) == archivum.IoError.NotFound")}
        let f as string is "{{base}}/file.txt"
        calling archivum.write_file with f, "x"
        let as_dir as result of bool to archivum.IoError is calling archivum.copy_tree_result with f, "{{base}}/y"
        {_print_bool("(as_dir.error) == archivum.IoError.IsADirectory")}
    ''', "ctres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\n1\ntrue\ntrue\n"


def test_touch_result_ok_and_err():
    """``touch_result`` creates the file and rejects a directory with ``IsADirectory``."""
    res = _run_arch(f'''
        let p as string is "{{base}}/new.txt"
        let r as result of bool to archivum.IoError is calling archivum.touch_result with p
        {_print_bool("r.is_ok")}
        {_print_bool("r.value")}
        {_print_bool("calling archivum.is_file with p")}
        let bad as result of bool to archivum.IoError is calling archivum.touch_result with base
        {_print_bool("calling bad.is_err")}
        {_print_bool("(bad.error) == archivum.IoError.IsADirectory")}
    ''', "tres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\n"


def test_metadata_result_ok_and_err():
    """``metadata_result`` is ``ok`` with the map and ``err(NotFound)`` when absent."""
    res = _run_arch(f'''
        let p as string is "{{base}}/a.txt"
        calling archivum.write_file with p, "1234"
        let r as result of map of string to string to archivum.IoError is calling archivum.metadata_result with p
        {_print_bool("r.is_ok")}
        let m as map of string to string is r.value
        calling spark.println with (calling m.get with "size")
        let np as string is "{{base}}/nope"
        let miss as result of map of string to string to archivum.IoError is calling archivum.metadata_result with np
        {_print_bool("(miss.error) == archivum.IoError.NotFound")}
    ''', "mdres")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n4\ntrue\n"


def test_describe_error_names_every_variant():
    """``describe_error`` gives the documented message for every ``IoError``."""
    res = _run_arch('''
        calling spark.println with (calling archivum.describe_error with archivum.IoError.NotFound)
        calling spark.println with (calling archivum.describe_error with archivum.IoError.IsADirectory)
        calling spark.println with (calling archivum.describe_error with archivum.IoError.NotAFile)
        calling spark.println with (calling archivum.describe_error with archivum.IoError.Permission)
        calling spark.println with (calling archivum.describe_error with archivum.IoError.Unknown)
    ''', "describe")
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "no such file or directory\n"
        "is a directory\n"
        "not a regular file\n"
        "permission denied\n"
        "unknown I/O error\n"
    )


# ---------------------------------------------------------------------------
# Temporary locations
# ---------------------------------------------------------------------------

def test_temp_dir_and_temp_file_name_a_usable_location():
    """``temp_dir`` exists and ``temp_file`` hands out a not-yet-created path."""
    res = _run_arch('''
        let tmp as string is calling archivum.temp_dir
        calling spark.println with calling spark.str_bool with (calling archivum.is_dir with tmp)
        let cand as string is calling archivum.temp_file with "archivum_ext_probe"
        calling spark.println with calling spark.str_bool with ((cand length) > 0)
        calling spark.println with calling spark.str_bool with (calling archivum.exists with cand)
        calling spark.println with calling spark.str_bool with (calling archivum.write_file with cand, "t")
        calling spark.println with calling spark.str_bool with (calling archivum.exists with cand)
        calling spark.println with calling spark.str_bool with (calling archivum.delete_file with cand)
    ''', "temp")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfalse\ntrue\ntrue\ntrue\n"


# ---------------------------------------------------------------------------
# Path enchanting
# ---------------------------------------------------------------------------

def test_path_enchanting_exposes_the_filesystem_methods():
    """The ``enchanting compass.Path`` block drives write/read/append/stat/delete."""
    res = _run_arch(f'''
        let p as compass.Path is calling compass.path with "{{base}}/p.txt"
        {_print_bool('calling p.write_text with "path text"')}
        let got as maybe string is calling p.read_text
        let want as string is "path text"
        {_print_bool("(got.value) == want")}
        {_print_bool('calling p.append_text with "!"')}
        let after as maybe string is calling p.read_text
        let want_after as string is "path text!"
        {_print_bool("(after.value) == want_after")}
        let lines as maybe list of string is calling p.read_lines
        {_print_bool("lines is present")}
        let md as maybe map of string to string is calling p.stat
        {_print_bool("md is present")}
        let dir as compass.Path is calling compass.path with base
        let entries as list of string is calling dir.iter_dir
        {_print_int("entries.len")}
        let sub as compass.Path is calling compass.path with "{{base}}/psub"
        {_print_bool("calling sub.mkdir with true")}
        {_print_bool("calling sub.rmdir with true")}
        {_print_bool("calling p.delete")}
        {_print_bool('calling archivum.exists with "{base}/p.txt"')}
    ''', "pathenc")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\ntrue\ntrue\n1\ntrue\ntrue\ntrue\nfalse\n"
