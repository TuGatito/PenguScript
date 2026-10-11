#!/usr/bin/env python3
"""End-to-end tests for ``std.compass`` (Chunk 4 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.compass`` is path manipulation: pure string helpers (``join``,
``basename``, ``dirname``, ``normalize``, ``relative_to``, the glob matcher ...)
plus the ``Path`` rune.  Only ``exists``/``is_file``/``is_dir`` touch the real
filesystem, so this suite is deliberately platform-stable: it uses POSIX-style
literals and asserts the *shape* of environment-dependent values (``cwd``,
``absolute``, ``expand_user``, ``current_dir`` are only checked for
non-emptiness / absoluteness), never a host-specific path.  The filesystem cases
use ``/`` for a guaranteed-existing entry or a throw-away
``tempfile.TemporaryDirectory``.

A former ``cp_change_ext`` use-after-free is fixed and pinned here:
``change_ext(path, "")`` and ``without_extension(path)`` used to return a buffer
that ``defer banish st`` had already released whenever the path had no directory
part (a bare filename), so those inputs printed non-deterministic garbage.
``test_extension_removal_is_stable_for_a_bare_filename`` and
``test_path_without_suffix_is_stable_for_a_bare_filename`` cover the bare case
and keep the directory-bearing branch pinned alongside it.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
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
    with tempfile.TemporaryDirectory(prefix="pengu_compass_") as td:
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

#: Assertion helpers woven into every program.  ``show_s``/``show_b``/``show_i``
#: render a tagged value as ``tag<value>`` so a whole table is one exact compare;
#: ``show_ms`` renders a ``maybe string`` as ``tag<value>`` or ``tag<none>``.
#: The two ``probe_*`` weaves turn the glob matcher into a printed table row.
_HELPERS = """
weave show_s with tag as string, value as string into void:
    calling spark.println with "{tag}<{value}>"

weave show_b with tag as string, value as bool into void:
    calling spark.println with "{tag}<{calling spark.str_bool with value}>"

weave show_i with tag as string, value as int into void:
    calling spark.println with "{tag}<{calling spark.str_int with value}>"

weave show_ms with tag as string, m as maybe string into void:
    if m is present:
        calling spark.println with "{tag}<{m.value}>"
    else:
        calling spark.println with "{tag}<none>"

weave probe_match with path as string, pattern as string into void:
    let got as bool is calling compass.matches with path, pattern
    calling spark.println with "[{path}][{pattern}]={calling spark.str_bool with got}"

weave probe_pmatch with path as string, pattern as string into void:
    let p as compass.Path is calling compass.new_path with path
    let got as bool is calling p.matches with pattern
    calling spark.println with "[{path}][{pattern}]={calling spark.str_bool with got}"
"""


def _run_main(body: str, helpers: str = _HELPERS) -> subprocess.CompletedProcess:
    """Runs ``body`` as the body of a ``main`` that imports spark and compass."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = ["import std.spark", "import std.compass"]
    if helpers:
        sections += ["", textwrap.dedent(helpers).strip("\n")]
    sections += ["", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections))


# ---------------------------------------------------------------------------
# Version, separators and platform flags
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``COMPASS_VERSION`` reports the migrated module version ``2.1.0``."""
    res = _run_main('calling show_s with "version", compass.COMPASS_VERSION')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "version<2.1.0>\n"


def test_separator_is_a_slash_and_platform_flags_are_consistent():
    """On POSIX the separator is ``/``, ``alt_separator`` is none and unix is true."""
    res = _run_main('''
        calling show_s with "sep", calling compass.separator
        calling show_ms with "alt", calling compass.alt_separator
        calling show_b with "unix", calling compass.is_unix
        calling show_b with "windows", calling compass.is_windows
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "sep</>\nalt<none>\nunix<true>\nwindows<false>\n"


# ---------------------------------------------------------------------------
# Joining
# ---------------------------------------------------------------------------

def test_join_and_join_all_use_the_separator():
    """``join`` and its twin ``join_all`` produce ``a/b`` from ``["a", "b"]``."""
    res = _run_main('''
        let parts as list of string is ["a", "b"]
        calling show_s with "join", calling compass.join with parts
        calling show_s with "join_all", calling compass.join_all with parts
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "join<a/b>\njoin_all<a/b>\n"


def test_join_skips_empty_segments_and_empty_list():
    """Empty segments are skipped and an empty part list yields the empty string."""
    res = _run_main('''
        let parts as list of string is ["a", "", "b"]
        let empty as list of string is list of string
        calling show_s with "skip", calling compass.join with parts
        calling show_s with "empty", calling compass.join with empty
        calling show_s with "empty_all", calling compass.join_all with empty
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "skip<a/b>\nempty<>\nempty_all<>\n"


def test_join_keeps_absolute_first_part_and_resolves_parents():
    """An absolute segment resets the buffer; ``..`` collapses the preceding segment."""
    res = _run_main('''
        let abs_parts as list of string is ["/a", "b"]
        let up_parts as list of string is ["a", "..", "b"]
        calling show_s with "abs", calling compass.join with abs_parts
        calling show_s with "up", calling compass.join with up_parts
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "abs</a/b>\nup<b>\n"


# ---------------------------------------------------------------------------
# Names: basename / dirname / ext / stem
# ---------------------------------------------------------------------------

def test_basename_and_filename_agree_on_the_final_component():
    """``basename``/``filename`` skip trailing separators and give "" for roots."""
    res = _run_main('''
        calling show_s with "base", calling compass.basename with "/tmp/a.txt"
        calling show_s with "file", calling compass.filename with "/tmp/a.txt"
        calling show_s with "trail", calling compass.basename with "a/"
        calling show_s with "seps", calling compass.basename with "//"
        calling show_s with "root", calling compass.basename with "/"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "base<a.txt>\nfile<a.txt>\ntrail<a>\nseps<>\nroot<>\n"


def test_dirname_drops_the_final_segment():
    """``dirname`` keeps the root, drops a bare name and returns "" with no parent."""
    res = _run_main('''
        calling show_s with "nested", calling compass.dirname with "/tmp/a.txt"
        calling show_s with "bare", calling compass.dirname with "a.txt"
        calling show_s with "root", calling compass.dirname with "/"
        calling show_s with "leaf", calling compass.dirname with "/a"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "nested</tmp>\nbare<>\nroot</>\nleaf</>\n"


def test_ext_stem_and_file_stem_agree_on_the_final_dot():
    """Only the last dot counts and a leading dot is not an extension."""
    res = _run_main('''
        calling show_s with "ext", calling compass.ext with "a.tar.gz"
        calling show_s with "ext_dot", calling compass.ext with ".bashrc"
        calling show_s with "stem", calling compass.stem with "/tmp/a.tar.gz"
        calling show_s with "file_stem", calling compass.file_stem with "a.txt"
        calling show_s with "stem_dot", calling compass.stem with ".bashrc"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "ext<.gz>\next_dot<>\nstem<a.tar>\nfile_stem<a>\nstem_dot<.bashrc>\n"
    )


def test_has_ext_detects_a_dotted_extension():
    """``has_ext`` is true exactly when the basename has a non-leading dot."""
    res = _run_main('''
        calling show_b with "yes", calling compass.has_ext with "a.txt"
        calling show_b with "dotfile", calling compass.has_ext with ".bashrc"
        calling show_b with "bare", calling compass.has_ext with "a"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "yes<true>\ndotfile<false>\nbare<false>\n"


# ---------------------------------------------------------------------------
# Absolute / relative / normalize / parent
# ---------------------------------------------------------------------------

def test_is_absolute_and_is_relative_are_complements():
    """A leading separator is absolute; a bare name is relative."""
    res = _run_main('''
        calling show_b with "abs_slash", calling compass.is_absolute with "/a"
        calling show_b with "abs_bare", calling compass.is_absolute with "a"
        calling show_b with "rel_bare", calling compass.is_relative with "a"
        calling show_b with "rel_slash", calling compass.is_relative with "/a"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "abs_slash<true>\nabs_bare<false>\nrel_bare<true>\nrel_slash<false>\n"
    )


def test_normalize_collapses_separators_and_dot_segments():
    """``normalize`` folds ``//``, ``.`` and a resolvable ``..``."""
    res = _run_main('''
        calling show_s with "seps", calling compass.normalize with "a//b"
        calling show_s with "dot", calling compass.normalize with "a/./b"
        calling show_s with "parent", calling compass.normalize with "a/b/../c"
        calling show_s with "trailing", calling compass.normalize with "a/b/.."
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "seps<a/b>\ndot<a/b>\nparent<a/c>\ntrailing<a>\n"


def test_normalize_preserves_leading_parents_empty_and_root():
    """Leading ``..`` stays, ``""`` becomes ``.`` and a root absorbs ``..``."""
    res = _run_main('''
        calling show_s with "leads", calling compass.normalize with "../.."
        calling show_s with "empty", calling compass.normalize with ""
        calling show_s with "root", calling compass.normalize with "/"
        calling show_s with "abs_up", calling compass.normalize with "/a/../.."
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "leads<../..>\nempty<.>\nroot</>\nabs_up</>\n"


def test_parent_is_none_for_roots_and_leaves():
    """``parent`` is ``some`` only when a directory part exists."""
    res = _run_main('''
        calling show_ms with "nested", calling compass.parent with "/a/b"
        calling show_ms with "leaf", calling compass.parent with "a"
        calling show_ms with "root", calling compass.parent with "/"
        calling show_ms with "rel_nested", calling compass.parent with "a/b"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "nested</a>\nleaf<none>\nroot<none>\nrel_nested<a>\n"


# ---------------------------------------------------------------------------
# Splitting into components
# ---------------------------------------------------------------------------

def test_split_and_components_keep_the_root_component():
    """``split``/``components`` emit the root separator as its own element."""
    res = _run_main('''
        let sp as list of string is calling compass.split with "/a/b"
        calling show_i with "split_len", sp.len
        let co as list of string is calling compass.components with "/a/b"
        calling show_i with "comp_len", co.len
        calling show_s with "comp0", co at 0
        calling show_s with "comp2", co at 2
        let rel as list of string is calling compass.components with "a//b"
        calling show_i with "rel_len", rel.len
        calling show_s with "rel0", rel at 0
        let empty as list of string is calling compass.split with ""
        calling show_i with "empty_len", empty.len
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "split_len<3>\ncomp_len<3>\ncomp0</>\ncomp2<b>\n"
        "rel_len<2>\nrel0<a>\nempty_len<0>\n"
    )


def test_has_component_matches_a_whole_segment():
    """``has_component`` compares components exactly, never substrings."""
    res = _run_main('''
        calling show_b with "b", calling compass.has_component with "/a/b/c", "b"
        calling show_b with "z", calling compass.has_component with "/a/b/c", "z"
        calling show_b with "partial", calling compass.has_component with "/a/bc", "b"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "b<true>\nz<false>\npartial<false>\n"


# ---------------------------------------------------------------------------
# Rewriting extensions and names
# ---------------------------------------------------------------------------

def test_change_ext_with_extension_and_without_extension():
    """``change_ext`` adds a missing dot; ``without_extension`` drops the last one."""
    res = _run_main('''
        calling show_s with "with_dot", calling compass.change_ext with "/tmp/a.txt", ".md"
        calling show_s with "no_dot", calling compass.change_ext with "/tmp/a.txt", "md"
        calling show_s with "bare_append", calling compass.change_ext with "a", ".txt"
        calling show_s with "with_extension", calling compass.with_extension with "a", "txt"
        let nested as string is calling compass.without_extension with "/tmp/a.txt"
        calling show_s with "without_extension", nested
        let twice as string is calling compass.without_extension with nested
        calling show_s with "without_extension_twice", twice
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "with_dot</tmp/a.md>\nno_dot</tmp/a.md>\nbare_append<a.txt>\n"
        "with_extension<a.txt>\nwithout_extension</tmp/a>\n"
        "without_extension_twice</tmp/a>\n"
    )


def test_extension_removal_is_stable_for_a_bare_filename():
    """Regression: stripping a bare name's extension no longer reads freed memory.

    ``cp_change_ext`` used to hand back the ``st`` temporary that ``defer banish
    st`` had already released when the path had no directory part, so these exact
    inputs printed non-deterministic garbage.  ``nested_control`` keeps the
    directory-bearing branch pinned next to the fixed one.
    """
    res = _run_main('''
        calling show_s with "change_ext_empty", calling compass.change_ext with "a.txt", ""
        calling show_s with "without_extension", calling compass.without_extension with "a.txt"
        calling show_s with "with_extension_empty", calling compass.with_extension with "a.txt", ""
        calling show_s with "with_extension_md", calling compass.with_extension with "a.txt", ".md"
        calling show_s with "nested_control", calling compass.without_extension with "/tmp/a.txt"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "change_ext_empty<a>\nwithout_extension<a>\nwith_extension_empty<a>\n"
        "with_extension_md<a.md>\nnested_control</tmp/a>\n"
    )


def test_with_filename_replaces_the_final_component():
    """``with_filename`` keeps the directory and swaps the basename."""
    res = _run_main('''
        calling show_s with "nested", calling compass.with_filename with "/tmp/a.txt", "b.md"
        calling show_s with "bare", calling compass.with_filename with "a.txt", "b.md"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "nested</tmp/b.md>\nbare<b.md>\n"


def test_add_ext_only_fills_a_missing_extension():
    """``add_ext`` is a no-op when the path already carries an extension."""
    res = _run_main('''
        calling show_s with "bare", calling compass.add_ext with "a", ".txt"
        calling show_s with "no_dot", calling compass.add_ext with "a", "txt"
        calling show_s with "keep", calling compass.add_ext with "a.txt", ".md"
        calling show_s with "empty_ext", calling compass.add_ext with "a", ""
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "bare<a.txt>\nno_dot<a.txt>\nkeep<a.txt>\nempty_ext<a>\n"


# ---------------------------------------------------------------------------
# relative_to, suffixes, hidden / unc / root / wildcard / drive
# ---------------------------------------------------------------------------

def test_relative_to_child_parent_and_none():
    """``relative_to`` walks down, walks up with ``..`` or gives ``none``."""
    res = _run_main('''
        calling show_ms with "child", calling compass.relative_to with "/a/b/c", "/a/b"
        calling show_ms with "up", calling compass.relative_to with "/a/b", "/a/c"
        let none as maybe string is calling compass.relative_to with "/x/y", "a/b"
        calling show_b with "none_present", (none is present)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "child<c>\nup<../b>\nnone_present<false>\n"


def test_has_suffix_and_suffixes_split_at_dots():
    """The empty suffix always matches; ``suffixes`` skips a leading dot."""
    res = _run_main('''
        calling show_b with "gz", calling compass.has_suffix with "a.tar.gz", ".gz"
        calling show_b with "empty", calling compass.has_suffix with "a", ""
        calling show_b with "no", calling compass.has_suffix with "a", "b"
        let sfx as list of string is calling compass.suffixes with "a.tar.gz"
        calling show_i with "len", sfx.len
        calling show_s with "first", sfx at 0
        calling show_s with "second", sfx at 1
        let dotfile as list of string is calling compass.suffixes with ".bashrc"
        calling show_i with "dotfile_len", dotfile.len
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "gz<true>\nempty<true>\nno<false>\nlen<2>\nfirst<tar>\nsecond<gz>\n"
        "dotfile_len<0>\n"
    )


def test_is_hidden_is_unc_is_root():
    """Dotfiles are hidden, ``.``/``..`` are not, ``//x`` is UNC and ``/`` is root."""
    res = _run_main('''
        calling show_b with "dotfile", calling compass.is_hidden with ".bashrc"
        calling show_b with "dot", calling compass.is_hidden with "."
        calling show_b with "dotdot", calling compass.is_hidden with ".."
        calling show_b with "plain", calling compass.is_hidden with "a.txt"
        calling show_b with "unc", calling compass.is_unc with "//server/share"
        calling show_b with "not_unc", calling compass.is_unc with "/a"
        calling show_b with "root", calling compass.is_root with "/"
        calling show_b with "not_root", calling compass.is_root with "a"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "dotfile<true>\ndot<false>\ndotdot<false>\nplain<false>\n"
        "unc<true>\nnot_unc<false>\nroot<true>\nnot_root<false>\n"
    )


def test_has_wildcard_and_drive():
    """``has_wildcard`` sees ``*`` and ``?``; a POSIX path has no drive prefix."""
    res = _run_main('''
        calling show_b with "star", calling compass.has_wildcard with "a*c"
        calling show_b with "question", calling compass.has_wildcard with "a?c"
        calling show_b with "plain", calling compass.has_wildcard with "abc"
        calling show_b with "empty", calling compass.has_wildcard with ""
        calling show_s with "drive_posix", calling compass.drive with "/a/b"
        calling show_s with "drive_empty", calling compass.drive with ""
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "star<true>\nquestion<true>\nplain<false>\nempty<false>\n"
        "drive_posix<>\ndrive_empty<>\n"
    )


# ---------------------------------------------------------------------------
# Glob table
# ---------------------------------------------------------------------------

def test_matches_glob_table():
    """``matches`` pins ``*``, ``?``, ``a*b``, the empty pattern and a miss."""
    res = _run_main('''
        calling probe_match with "a.txt", "*.txt"
        calling probe_match with "a.txt", "a?txt"
        calling probe_match with "axxb", "a*b"
        calling probe_match with "abc", "a*b"
        calling probe_match with "abc", ""
        calling probe_match with "abc", "*.md"
        calling probe_match with "", ""
        calling probe_match with "", "*"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "[a.txt][*.txt]=true\n"
        "[a.txt][a?txt]=true\n"
        "[axxb][a*b]=true\n"
        "[abc][a*b]=false\n"
        "[abc][]=false\n"
        "[abc][*.md]=false\n"
        "[][]=true\n"
        "[][*]=true\n"
    )


def test_matches_is_anchored_and_case_sensitive():
    """The matcher is anchored; a pattern with a separator sees the whole path."""
    res = _run_main('''
        calling probe_match with "dir/a.txt", "*.txt"
        calling probe_match with "dir/a.txt", "dir/*.txt"
        calling probe_match with "dir/a.txt", "*/*.txt"
        calling probe_match with "/a", "/*"
        calling probe_match with "ABC", "abc"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "[dir/a.txt][*.txt]=true\n"
        "[dir/a.txt][dir/*.txt]=true\n"
        "[dir/a.txt][*/*.txt]=true\n"
        "[/a][/*]=true\n"
        "[ABC][abc]=false\n"
    )


# ---------------------------------------------------------------------------
# The Path rune
# ---------------------------------------------------------------------------

def test_path_constructors_agree_and_expose_to_string():
    """``new_path`` and ``path`` wrap the same raw text, readable via ``to_string``."""
    res = _run_main('''
        let a as compass.Path is calling compass.new_path with "/tmp/notes.tar.gz"
        let b as compass.Path is calling compass.path with "/tmp/notes.tar.gz"
        calling show_s with "new_path", calling a.to_string
        calling show_s with "path", calling b.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "new_path</tmp/notes.tar.gz>\npath</tmp/notes.tar.gz>\n"
    )


def test_path_name_stem_suffix_suffixes_and_drive():
    """The read-only ``Path`` accessors mirror the string helpers."""
    res = _run_main('''
        let p as compass.Path is calling compass.new_path with "/tmp/notes.tar.gz"
        calling show_s with "name", calling p.name
        calling show_s with "stem", calling p.stem
        calling show_s with "suffix", calling p.suffix
        calling show_b with "has_suffix", calling p.has_suffix
        let sfx as list of string is calling p.suffixes
        calling show_i with "suffixes_len", sfx.len
        calling show_s with "first", sfx at 0
        calling show_s with "second", sfx at 1
        calling show_s with "drive", calling p.drive
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "name<notes.tar.gz>\nstem<notes.tar>\nsuffix<.gz>\nhas_suffix<true>\n"
        "suffixes_len<2>\nfirst<tar>\nsecond<gz>\ndrive<>\n"
    )


def test_path_parent_parts_and_components():
    """``parent``/``parts``/``components`` expose the directory structure."""
    res = _run_main('''
        let p as compass.Path is calling compass.new_path with "/tmp/notes.tar.gz"
        calling show_ms with "parent", calling p.parent
        let parts as list of string is calling p.parts
        calling show_i with "parts_len", parts.len
        calling show_s with "part0", parts at 0
        calling show_s with "part2", parts at 2
        let comps as list of string is calling p.components
        calling show_i with "components_len", comps.len
        let root as compass.Path is calling compass.new_path with "/"
        calling show_ms with "root_parent", calling root.parent
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "parent</tmp>\nparts_len<3>\npart0</>\npart2<notes.tar.gz>\n"
        "components_len<3>\nroot_parent<none>\n"
    )


def test_path_predicates():
    """``is_absolute``/``is_relative``/``is_root``/``is_empty``/``is_hidden``/suffixes."""
    res = _run_main('''
        let abs_p as compass.Path is calling compass.new_path with "/tmp/a.txt"
        let rel_p as compass.Path is calling compass.new_path with "a.txt"
        let root as compass.Path is calling compass.new_path with "/"
        let empty as compass.Path is calling compass.new_path with ""
        let hidden as compass.Path is calling compass.new_path with ".bashrc"
        calling show_b with "abs", calling abs_p.is_absolute
        calling show_b with "abs_rel", calling abs_p.is_relative
        calling show_b with "rel", calling rel_p.is_relative
        calling show_b with "root", calling root.is_root
        calling show_b with "empty", calling empty.is_empty
        calling show_b with "hidden", calling hidden.is_hidden
        calling show_b with "suffix", calling abs_p.has_suffix_with with ".txt"
        calling show_b with "suffix_no", calling abs_p.has_suffix_with with ".md"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "abs<true>\nabs_rel<false>\nrel<true>\nroot<true>\nempty<true>\n"
        "hidden<true>\nsuffix<true>\nsuffix_no<false>\n"
    )


def test_path_matches_glob_table():
    """``Path.matches`` uses the same matcher as the module-level ``matches``."""
    res = _run_main('''
        calling probe_pmatch with "a.txt", "*.txt"
        calling probe_pmatch with "a.txt", "a?txt"
        calling probe_pmatch with "axxb", "a*b"
        calling probe_pmatch with "abc", ""
        calling probe_pmatch with "abc", "*.md"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "[a.txt][*.txt]=true\n"
        "[a.txt][a?txt]=true\n"
        "[axxb][a*b]=true\n"
        "[abc][]=false\n"
        "[abc][*.md]=false\n"
    )


def test_path_normalize_and_relative_to():
    """``Path.normalize`` returns a new rune and ``relative_to`` a ``maybe string``."""
    res = _run_main('''
        let messy as compass.Path is calling compass.new_path with "a//b/./c/../d"
        let clean as compass.Path is calling messy.normalize
        calling show_s with "normalized", calling clean.to_string
        let target as compass.Path is calling compass.new_path with "/a/b/c"
        calling show_ms with "child", calling target.relative_to with "/a/b"
        let up as compass.Path is calling compass.new_path with "/a/b"
        calling show_ms with "up", calling up.relative_to with "/a/c"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "normalized<a/b/d>\nchild<c>\nup<../b>\n"


def test_path_rewrites_suffix_and_name():
    """``with_suffix``/``with_name``/``add_suffix``/``without_suffix`` return new runes."""
    res = _run_main('''
        let p as compass.Path is calling compass.new_path with "/tmp/notes.tar.gz"
        let ws as compass.Path is calling p.with_suffix with "md"
        calling show_s with "with_suffix", calling ws.to_string
        let bare as compass.Path is calling compass.new_path with "a.txt"
        let bws as compass.Path is calling bare.with_suffix with "md"
        calling show_s with "with_suffix_bare", calling bws.to_string
        let wn as compass.Path is calling p.with_name with "other.txt"
        calling show_s with "with_name", calling wn.to_string
        let named as compass.Path is calling compass.new_path with "a"
        let bn as compass.Path is calling named.with_name with "b.md"
        calling show_s with "with_name_bare", calling bn.to_string
        let added as compass.Path is calling named.add_suffix with ".txt"
        calling show_s with "add_suffix", calling added.to_string
        let kept as compass.Path is calling added.add_suffix with ".md"
        calling show_s with "add_suffix_keep", calling kept.to_string
        let nos as compass.Path is calling p.without_suffix
        calling show_s with "without_suffix", calling nos.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "with_suffix</tmp/notes.tar.md>\nwith_suffix_bare<a.md>\n"
        "with_name</tmp/other.txt>\nwith_name_bare<b.md>\n"
        "add_suffix<a.txt>\nadd_suffix_keep<a.txt>\nwithout_suffix</tmp/notes.tar>\n"
    )


def test_path_without_suffix_is_stable_for_a_bare_filename():
    """Regression: ``Path.without_suffix`` on a bare name is stable; nested stays pinned."""
    res = _run_main('''
        let bare as compass.Path is calling compass.new_path with "a.txt"
        let stripped as compass.Path is calling bare.without_suffix
        calling show_s with "bare", calling stripped.to_string
        let nested as compass.Path is calling compass.new_path with "/tmp/a.txt"
        let nested_stripped as compass.Path is calling nested.without_suffix
        calling show_s with "nested", calling nested_stripped.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "bare<a>\nnested</tmp/a>\n"


def test_path_to_uri_and_to_string():
    """``to_uri`` renders a stable ``file://`` URI and encodes spaces."""
    res = _run_main('''
        let plain as compass.Path is calling compass.new_path with "/tmp/notes.txt"
        calling show_s with "uri", calling plain.to_uri
        let spaced as compass.Path is calling compass.new_path with "/tmp/my docs/a.txt"
        calling show_s with "uri_spaces", calling spaced.to_uri
        let rel as compass.Path is calling compass.new_path with "a/b.txt"
        calling show_s with "uri_relative", calling rel.to_uri
        calling show_s with "to_string", calling plain.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "uri<file:///tmp/notes.txt>\nuri_spaces<file:///tmp/my%20docs/a.txt>\n"
        "uri_relative<file:///a/b.txt>\nto_string</tmp/notes.txt>\n"
    )


def test_path_to_absolute_and_expand_user_are_shape_stable():
    """Only the shape of environment-dependent paths is asserted."""
    res = _run_main('''
        let rel as compass.Path is calling compass.new_path with "notes.txt"
        let abs_p as compass.Path is calling rel.to_absolute
        calling show_b with "to_absolute", calling abs_p.is_absolute
        let tilde as compass.Path is calling compass.new_path with "~/notes"
        let expanded as compass.Path is calling tilde.expand_user
        let text as string is calling expanded.to_string
        calling show_b with "expand_nonempty", (text length) > 0
        let plain as compass.Path is calling compass.new_path with "notes"
        let plain_expanded as compass.Path is calling plain.expand_user
        calling show_s with "expand_plain", calling plain_expanded.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "to_absolute<true>\nexpand_nonempty<true>\nexpand_plain<notes>\n"
    )


def test_current_dir_cwd_and_path_join_helpers():
    """``current_dir``/``cwd`` are non-empty and absolute; ``path_join`` builds a rune."""
    res = _run_main('''
        let here as compass.Path is calling compass.current_dir
        calling show_b with "current_dir_abs", calling here.is_absolute
        let here_text as string is calling here.to_string
        calling show_b with "current_dir_nonempty", (here_text length) > 0
        let text as string is calling compass.cwd
        calling show_b with "cwd_nonempty", (text length) > 0
        let parts as list of string is ["x", "y.txt"]
        let joined as compass.Path is calling compass.path_join with parts
        calling show_s with "path_join", calling joined.to_string
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "current_dir_abs<true>\ncurrent_dir_nonempty<true>\n"
        "cwd_nonempty<true>\npath_join<x/y.txt>\n"
    )


def test_string_absolute_and_expand_user_are_shape_stable():
    """``absolute`` returns an absolute string; ``expand_user`` a non-empty one."""
    res = _run_main('''
        let rel_abs as string is calling compass.absolute with "notes.txt"
        calling show_b with "absolute_rel", calling compass.is_absolute with rel_abs
        let abs_abs as string is calling compass.absolute with "/x/y"
        calling show_s with "absolute_abs", abs_abs
        let expanded as string is calling compass.expand_user with "~/notes"
        calling show_b with "expand_user_nonempty", (expanded length) > 0
        let tilde as string is calling compass.expand_user with "~"
        calling show_b with "expand_tilde_nonempty", (tilde length) > 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "absolute_rel<true>\nabsolute_abs</x/y>\n"
        "expand_user_nonempty<true>\nexpand_tilde_nonempty<true>\n"
    )


# ---------------------------------------------------------------------------
# Filesystem-touching behaviour
# ---------------------------------------------------------------------------

def test_filesystem_root_exists_and_is_a_directory():
    """``/`` exists and is a directory on every POSIX host."""
    res = _run_main('''
        let root as compass.Path is calling compass.new_path with "/"
        calling show_b with "exists", calling root.exists
        calling show_b with "is_dir", calling root.is_dir
        calling show_b with "is_file", calling root.is_file
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "exists<true>\nis_dir<true>\nis_file<false>\n"


def test_path_exists_is_file_and_is_dir_in_a_temporary_directory():
    """``exists``/``is_file``/``is_dir`` classify a real file, a real dir and a miss."""
    with tempfile.TemporaryDirectory(prefix="pengu_compass_fs_") as td:
        root = Path(td)
        (root / "file.txt").write_text("x", encoding="utf-8")
        body = '''
            let dir as compass.Path is calling compass.new_path with "@DIR@"
            calling show_b with "dir_exists", calling dir.exists
            calling show_b with "dir_is_dir", calling dir.is_dir
            calling show_b with "dir_is_file", calling dir.is_file
            let file as compass.Path is calling compass.new_path with "@FILE@"
            calling show_b with "file_exists", calling file.exists
            calling show_b with "file_is_file", calling file.is_file
            calling show_b with "file_is_dir", calling file.is_dir
            let missing as compass.Path is calling compass.new_path with "@MISSING@"
            calling show_b with "missing_exists", calling missing.exists
            calling show_b with "missing_is_file", calling missing.is_file
            calling show_b with "missing_is_dir", calling missing.is_dir
        '''
        body = (body.replace("@DIR@", str(root))
                    .replace("@FILE@", str(root / "file.txt"))
                    .replace("@MISSING@", str(root / "nope.txt")))
        res = _run_main(body)
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "dir_exists<true>\ndir_is_dir<true>\ndir_is_file<false>\n"
        "file_exists<true>\nfile_is_file<true>\nfile_is_dir<false>\n"
        "missing_exists<false>\nmissing_is_file<false>\nmissing_is_dir<false>\n"
    )
