"""Regression tests for the v0.15.0 memory-subsystem audit repairs.

Each test pins one confirmed bug so a future change cannot silently reintroduce
it.  The audit's C1 (``PenguString.is_owned``) already landed at HEAD; the tests
here cover the remaining confirmed items:

* C2/C3 — ``x to string`` on a string/bool must not be auto-banished,
* C4 — release-before-assign on ``set`` for provably-unaliased auto-owned locals
  (M1 static / M2 struct-field reassignment are left conservative: a live view
  of the old cell cannot be ruled out statically, so the release is skipped),
* C5 — ``list of maybe``/``list of result`` deep-clone + element cleanup,
* C6/C7 — ``_release_payload_stmts`` handles algebraic omens and nested maybe,
* H1 — local algebraic omens are released at scope exit,
* H4 — ``sigil of x.field``/``x at i`` counts as an escape,
* H5 — returning a slice of a stack array is rejected (E0051).

Bonus regressions found while fixing: the omen-variant payload used to be
translated against the variant struct (``with Items is [1, 2, 3]`` emitted an
invalid ``PenguList`` initializer) and ``(some s) or:`` did not free the box
because the parenthesised operand was not unwrapped.
"""

import os
import shutil
import subprocess

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    check_error,
    compile_run,
    gen_bundle,
    requires_cc,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

# ---------------------------------------------------------------------------
# C2/C3 — to-string ownership
# ---------------------------------------------------------------------------


def test_to_string_identity_is_not_auto_banished():
    """'s1 to string' reuses s1's buffer: the binding must not release it."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var s1 as string is (1 to string)\n'
        '  var s2 as string is s1 to string\n'
        '  return\n'
    )
    assert "PenguString s2 = s1;" in c
    assert "pengu_banish_string(&s2)" not in c
    # s1 still owns its own buffer and is released exactly once.
    assert "pengu_banish_string(&s1);" in c


def test_bool_to_string_is_not_auto_banished():
    """'bool to string' yields the static "true"/"false" rodata view."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var b as bool is true\n'
        '  var s as string is b to string\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_int_to_string_is_auto_banished():
    """'int to string' allocates a fresh heap buffer and must be released."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var n as int is 42\n'
        '  var s as string is n to string\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s);" in c


@requires_cc
@requires_runtime
def test_to_string_identity_runs_clean():
    src = (
        'weave main into int:\n'
        '  var s1 as string is (1 to string)\n'
        '  var s2 as string is s1 to string\n'
        '  if (s2 length) == (s1 length):\n'
        '    return 0\n'
        '  return 1\n'
    )
    assert compile_run(src, tag="to_string_identity").returncode == 0


# ---------------------------------------------------------------------------
# C4/M1/M2 — release-before-assign
# ---------------------------------------------------------------------------


def test_set_fresh_value_releases_previous_list():
    """A loop reassigning a fresh list frees the previous buffer each round."""
    c = gen_bundle(
        'weave main into int:\n'
        '  var i as int is 0\n'
        '  var xs as list of int is list of int\n'
        '  while i < 10:\n'
        '    set xs is [i, i + 1]\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    # The old value is stashed and released around the assignment, and the final
    # value is still auto-banished at scope exit.
    assert "PenguList _old_" in c
    assert c.count("pengu_banish_list") >= 2


def test_set_borrowed_value_does_not_release():
    """'set s is other' aliases another local: no release may be emitted."""
    c = gen_bundle(
        'weave f with a as string into void:\n'
        '  var s as string is (1 to string)\n'
        '  set s is a\n'
        '  return\n'
    )
    assert "pengu_banish_string((PenguString *)(&_old" not in c


def test_self_assignment_does_not_release():
    """'set s is s' is a no-op; releasing the old value would dangle s."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var s as string is (1 to string)\n'
        '  set s is s\n'
        '  return\n'
    )
    assert "_old_" not in c
    assert "pengu_banish_string(&s);" in c


def test_string_field_reassign_keeps_old_cell_aliases_safe():
    """A 'set d.field' deep-copies the new value but does *not* release the old
    cell: another binding ('var v is d.title') may still view it, so releasing
    would dangle.  The remaining leak is a documented M2 follow-up."""
    c = gen_bundle(
        'rune Doc:\n'
        '  title as string\n'
        'weave f into void:\n'
        '  var d as Doc is with title is "a"\n'
        '  set d.title is "b"\n'
        '  return\n'
    )
    assert "d.title = pengu_string_copy(pengu_string_from_cstr(\"b\"))" in c
    assert "_old_" not in c


@requires_cc
@requires_runtime
def test_element_swap_with_view_runs_clean():
    """Regression for std/atlas sort_strings: swapping list elements while a
    view ('tmp is ks at 0') is live must not free the viewed buffer."""
    src = (
        'weave main into int:\n'
        '  var ks as list of string is ["a", "b", "c"]\n'
        '  var tmp as string is ks at 0\n'
        '  set ks at 0 is ks at 1\n'
        '  set ks at 1 is tmp\n'
        '  if (ks at 0) == "b":\n'
        '    return 0\n'
        '  return 1\n'
    )
    assert compile_run(src, tag="element_swap_view").returncode == 0


def test_static_var_reassign_is_left_alone():
    """Static reassignment keeps the old buffer (aliasing a static cannot be
    ruled out statically); this pins the conservative M1 decision."""
    c = gen_bundle(
        'weave tick into int:\n'
        '  static var s as string is "a{1}"\n'
        '  set s is "{s}!"\n'
        '  return s length\n'
    )
    assert "PenguString _old_" not in c


@requires_cc
@requires_runtime
def test_reassign_loop_runs_clean():
    src = (
        'weave main into int:\n'
        '  var i as int is 0\n'
        '  var xs as list of int is list of int\n'
        '  while i < 200:\n'
        '    set xs is [i, i + 1, i + 2]\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="reassign_loop").returncode == 0


@requires_cc
@requires_runtime
def test_static_reassign_runs_clean():
    src = (
        'weave tick into int:\n'
        '  static var s as string is "a{1}"\n'
        '  set s is "{s}!"\n'
        '  return 0\n'
        'weave main into int:\n'
        '  var i as int is 0\n'
        '  while i < 50:\n'
        '    set i is i + (calling tick) + 1\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="static_reassign").returncode == 0


# ---------------------------------------------------------------------------
# C5 — containers of maybe/result
# ---------------------------------------------------------------------------


def test_list_of_maybe_registers_element_callbacks():
    c = gen_bundle(
        'weave main into int:\n'
        '  var l as list of maybe int is list of maybe int\n'
        '  return 0\n'
    )
    assert "pengu_list_new_owned(sizeof(PenguMaybe)" in c
    assert "_pengu_elem_cleanup_maybe_int" in c
    assert "_pengu_elem_clone_maybe_int" in c


def test_list_of_result_registers_element_callbacks():
    c = gen_bundle(
        'weave main into int:\n'
        '  var l as list of result of int to string is list of result of int to string\n'
        '  return 0\n'
    )
    assert "pengu_list_new_owned(sizeof(PenguResult)" in c
    assert "_pengu_elem_clone_result_int_string" in c


@requires_cc
@requires_runtime
def test_list_of_maybe_push_runs_clean():
    src = (
        'weave main into int:\n'
        '  var l as list of maybe int is list of maybe int\n'
        '  var i as int is 0\n'
        '  while i < 50:\n'
        '    var m as maybe int is some i\n'
        '    calling l.push with m\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="list_of_maybe").returncode == 0


@requires_cc
@requires_runtime
def test_list_of_result_push_runs_clean():
    src = (
        'weave main into int:\n'
        '  var l as list of result of int to string is list of result of int to string\n'
        '  var i as int is 0\n'
        '  while i < 50:\n'
        '    var r as result of int to string is calling ok_of with i\n'
        '    calling l.push with r\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="list_of_result").returncode == 0


@requires_cc
@requires_runtime
def test_nested_maybe_list_runs_clean():
    """Nested element clone helpers must not shadow each other's temporaries."""
    src = (
        'weave main into int:\n'
        '  var l as list of maybe (maybe int) is list of maybe (maybe int)\n'
        '  var mm as maybe (maybe int) is some (some 5)\n'
        '  calling l.push with mm\n'
        '  var l3 as list of maybe (maybe (maybe int)) is list of maybe (maybe (maybe int))\n'
        '  var x as maybe (maybe (maybe int)) is some (some (some 9))\n'
        '  calling l3.push with x\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="nested_maybe").returncode == 0


# ---------------------------------------------------------------------------
# C6/C7 — _release_payload_stmts
# ---------------------------------------------------------------------------


@requires_cc
@requires_runtime
def test_maybe_maybe_runs_clean():
    """'maybe maybe T' used to emit invalid C ('m.value_m->value')."""
    src = (
        'weave main into int:\n'
        '  var mm as maybe maybe int is some (some 42)\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="maybe_maybe").returncode == 0


@requires_cc
@requires_runtime
def test_maybe_omen_runs_clean():
    src = (
        'omen Event:\n'
        '  Msg with text as string\n'
        '  Tick\n'
        'weave main into int:\n'
        '  var m as maybe Event is some (with Msg is "{1}")\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="maybe_omen").returncode == 0


# ---------------------------------------------------------------------------
# H1 — algebraic omen auto-banish (+ omen list payload init)
# ---------------------------------------------------------------------------


def test_algebraic_omen_local_is_auto_banished():
    c = gen_bundle(
        'omen Event:\n'
        '  Msg with text as string\n'
        '  Tick\n'
        'weave f into void:\n'
        '  var e as Event is with Msg is "{1}"\n'
        '  return\n'
    )
    assert "_pengu_auto_cleanup_Event" in c


@requires_cc
@requires_runtime
def test_omen_list_payload_init_is_valid_c():
    """'with Items is [1, 2, 3]' used to emit a raw '{ 1, 2, 3 }' PenguList."""
    src = (
        'omen Event:\n'
        '  Items with xs as list of int\n'
        '  Tick\n'
        'weave main into int:\n'
        '  var e as Event is with Items is [1, 2, 3]\n'
        '  return 0\n'
    )
    assert compile_run(src, tag="omen_list_payload").returncode == 0


# ---------------------------------------------------------------------------
# H3 — '(some s) or:' must free the box (parenthesised operand)
# ---------------------------------------------------------------------------


def test_parenthesised_or_block_frees_box():
    c = gen_bundle(
        'weave f into void:\n'
        '  var s as string is "{1}bc"\n'
        '  var x as string is (some s) or:\n'
        '    ""\n'
        '  return\n'
    )
    assert "free(_res_" in c


# ---------------------------------------------------------------------------
# H4 — escape analysis sees sigil of x.field / x at i
# ---------------------------------------------------------------------------


def test_sigil_of_element_disables_auto_banish():
    """Taking the address of an element of a heap list lets the list escape."""
    c = gen_bundle(
        'weave f into ref to int:\n'
        '  var xs as list of int is [1, 2, 3]\n'
        '  return sigil of xs at 0\n'
    )
    assert "pengu_banish_list(&xs)" not in c


# ---------------------------------------------------------------------------
# H5 — returning a slice of a stack array
# ---------------------------------------------------------------------------


def test_return_slice_of_stack_array_is_rejected():
    check_error(
        'weave f into slice of int:\n'
        '  var arr as array of int with size 4 is [1, 2, 3, 4]\n'
        '  return arr at 0 to 2\n',
        contains="E0051",
    )


def test_return_slice_of_list_is_allowed():
    from tests.conftest import check_ok
    check_ok(
        'weave f with xs as list of int into slice of int:\n'
        '  return xs at 0 to 2\n'
    )


# ---------------------------------------------------------------------------
# Optional valgrind gate for the reassign loop
# ---------------------------------------------------------------------------


@requires_cc
@requires_runtime
def test_valgrind_reassign_loop_is_leak_free(tmp_path):
    """Leak gate for the reassign loop: valgrind when present, else ASan.

    ASan intercepts malloc/free globally, so it also tracks allocations made by
    the non-instrumented static runtime; ``-fsanitize=address`` is probed first
    and the test skips when the toolchain has no sanitizer runtime.
    """
    valgrind = shutil.which("valgrind")

    from pengu_project import PenguBuilder, ProjectConfig

    src = (
        'weave main into int:\n'
        '  var i as int is 0\n'
        '  var xs as list of int is list of int\n'
        '  while i < 50:\n'
        '    set xs is [i, i + 1, i + 2]\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    entry = tmp_path / "reassign.pengu"
    entry.write_text(src, encoding="utf-8")
    cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file=str(tmp_path / "bundle.c"))

    base_cmd = [
        "gcc", str(bundle_path),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}", f"-L{BUILD_LIB}", "-g",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=int-conversion",
    ] + runtime_link_flags() + runtime_tail_flags()

    if valgrind:
        exe = tmp_path / "bin_vg"
        c_res = subprocess.run(base_cmd + ["-o", str(exe)], capture_output=True, text=True)
        assert c_res.returncode == 0, f"Compilation failed: {c_res.stderr}"
        vg_res = subprocess.run(
            [valgrind, "--leak-check=full", "--error-exitcode=42",
             "--show-leak-kinds=all", str(exe)],
            capture_output=True, text=True,
        )
        assert vg_res.returncode == 0, (
            f"Valgrind detected leaks:\n{vg_res.stderr}\n{vg_res.stdout}"
        )
        return

    # Probe for a working ASan runtime before relying on it.
    probe_src = tmp_path / "probe.c"
    probe_src.write_text("int main(void){return 0;}", encoding="utf-8")
    probe = subprocess.run(
        ["gcc", str(probe_src), "-fsanitize=address", "-o", str(tmp_path / "probe")],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        pytest.skip("neither valgrind nor the ASan runtime is available")

    exe = tmp_path / "bin_asan"
    c_res = subprocess.run(
        base_cmd + ["-fsanitize=address", "-fno-omit-frame-pointer", "-o", str(exe)],
        capture_output=True, text=True,
    )
    assert c_res.returncode == 0, f"Compilation failed: {c_res.stderr}"
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:exitcode=42")
    run = subprocess.run([str(exe)], capture_output=True, text=True, env=env)
    assert run.returncode == 0, (
        f"ASan detected leaks (exit {run.returncode}):\n{run.stderr}"
    )
