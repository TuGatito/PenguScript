"""Regression tests for the v0.15.0 memory-subsystem audit repairs.

Each test pins one confirmed property so a future change cannot silently
reintroduce the original bug.  PenguScript now uses manual memory management:
the compiler never releases a local at scope exit, never deep-copies on store
and never derives a destructor, so the assertions here describe what the
generator emits and what an explicit ``banish`` lowers to.

* C2/C3 — ``x to string`` on a string/bool must not allocate,
* C4 — ``set`` overwrites; there is no release-before-assign (the previous
  buffer leaks, which is documented and expected without an explicit banish),
* C5 — ``list of maybe``/``list of result`` store elements by memcpy: no
  element clone/cleanup callbacks are registered,
* C6/C7 — ``_release_payload_stmts`` handles algebraic omens and nested maybe
  when the programmer writes ``banish``,
* H1 — a local algebraic omen is only released by an explicit ``banish``,
* H4 — there is no escape analysis; a ``sigil of`` element never changes codegen,
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


def test_to_string_identity_aliases_without_release():
    """'s1 to string' aliases s1's buffer: nothing is released implicitly."""
    src = (
        'weave f into void:\n'
        '  var s1 as string is (1 to string)\n'
        '  var s2 as string is s1 to string\n'
        '  return\n'
    )
    c = gen_bundle(src)
    assert "PenguString s2 = s1;" in c
    assert "pengu_banish_string(&s2)" not in c
    # s1 owns the buffer, but there is no scope-exit release any more.
    assert "pengu_banish_string(&s1)" not in c

    # Only an explicit banish releases, and it frees the aliased buffer once.
    explicit = src.replace('  return\n', '  banish s1\n  return\n')
    assert "pengu_banish_string(&s1);" in gen_bundle(explicit)


def test_bool_to_string_emits_no_release():
    """'bool to string' yields the static "true"/"false" rodata view."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var b as bool is true\n'
        '  var s as string is b to string\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_int_to_string_is_fresh_heap_released_only_explicitly():
    """'int to string' allocates a fresh heap buffer; manual memory frees it only on 'banish'."""
    src = (
        'weave f into void:\n'
        '  var n as int is 42\n'
        '  var s as string is n to string\n'
        '  return\n'
    )
    c = gen_bundle(src)
    assert "pengu_string_from_int" in c
    assert "pengu_banish_string(&s);" not in c

    explicit = src.replace('  return\n', '  banish s\n  return\n')
    assert "pengu_banish_string(&s);" in gen_bundle(explicit)


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


def test_set_fresh_value_overwrites_without_release():
    """'set xs is [...]' overwrites the list; the previous buffer leaks (documented)."""
    src = (
        'weave main into int:\n'
        '  var i as int is 0\n'
        '  var xs as list of int is list of int\n'
        '  while i < 10:\n'
        '    set xs is [i, i + 1]\n'
        '    set i is i + 1\n'
        '  return 0\n'
    )
    c = gen_bundle(src)
    # No release-before-assign: the old buffer is simply dropped.
    assert "_old_" not in c
    assert "pengu_banish_list" not in c
    # The overwrite itself still happens.
    assert "xs = " in c

    # The manual replacement is an explicit banish before the overwrite.
    manual = src.replace('    set xs is [i, i + 1]\n', '    banish xs\n    set xs is [i, i + 1]\n')
    assert "pengu_banish_list(&xs);" in gen_bundle(manual)


def test_set_non_owning_value_does_not_release():
    """'set s is other' aliases another local: no release may be emitted."""
    c = gen_bundle(
        'weave f with a as string into void:\n'
        '  var s as string is (1 to string)\n'
        '  set s is a\n'
        '  return\n'
    )
    assert "pengu_banish_string((PenguString *)(&_old" not in c


def test_self_assignment_does_not_release():
    """'set s is s' is a no-op; nothing is released for it either."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var s as string is (1 to string)\n'
        '  set s is s\n'
        '  return\n'
    )
    assert "_old_" not in c
    assert "pengu_banish_string(&s);" not in c


def test_string_field_reassign_does_not_deep_copy_or_release():
    """A 'set d.field' stores the new string directly and does not free the old cell.

    There is no implicit deep copy and no release-before-assign: the old cell
    keeps pointing at its buffer and the new value is stored as written.
    """
    c = gen_bundle(
        'rune Doc:\n'
        '  title as string\n'
        'weave f into void:\n'
        '  var d as Doc is with title is "a"\n'
        '  set d.title is "b"\n'
        '  return\n'
    )
    assert 'd.title = pengu_string_from_cstr("b")' in c
    assert "pengu_string_copy" not in c
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


def test_list_of_maybe_does_not_register_element_callbacks():
    """A list of maybe stores PenguMaybe by memcpy: no clone/cleanup callbacks."""
    c = gen_bundle(
        'weave main into int:\n'
        '  var l as list of maybe int is list of maybe int\n'
        '  return 0\n'
    )
    assert "pengu_list_new_owned" not in c
    assert "pengu_list_new(sizeof(PenguMaybe)" in c
    assert "_pengu_elem_cleanup_maybe_int" not in c
    assert "_pengu_elem_clone_maybe_int" not in c


def test_list_of_result_does_not_register_element_callbacks():
    """A list of result stores PenguResult by memcpy: no clone/cleanup callbacks."""
    c = gen_bundle(
        'weave main into int:\n'
        '  var l as list of result of int to string is list of result of int to string\n'
        '  return 0\n'
    )
    assert "pengu_list_new_owned" not in c
    assert "pengu_list_new(sizeof(PenguResult)" in c
    assert "_pengu_elem_clone_result_int_string" not in c


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
# H1 — algebraic omen explicit banish (+ omen list payload init)
# ---------------------------------------------------------------------------


def test_algebraic_omen_local_has_no_implicit_cleanup():
    """A local omen is never cleaned up implicitly; an explicit 'banish' releases it.

    There is no ``_pengu_auto_cleanup_<Omen>`` and no scope-exit release any
    more.  Writing ``banish e`` lowers to the omen's generated cleanup helper,
    which walks the live variant's payload.
    """
    src = (
        'omen Event:\n'
        '  Msg with text as string\n'
        '  Tick\n'
        'weave f into void:\n'
        '  var e as Event is with Msg is "{1}"\n'
        '  return\n'
    )
    c = gen_bundle(src)
    assert "_pengu_auto_cleanup_Event" not in c
    assert "_pengu_cleanup_Event(&e)" not in c

    explicit = src.replace('  return\n', '  banish e\n  return\n')
    assert "_pengu_cleanup_Event(&e);" in gen_bundle(explicit)


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
# H4 — no escape analysis (a sigil of an element changes nothing)
# ---------------------------------------------------------------------------


def test_sigil_of_element_does_not_change_codegen():
    """Taking the address of an element no longer suppresses a release.

    There is no escape analysis any more: the release is emitted only when the
    programmer writes ``banish``, sigil or not.
    """
    c = gen_bundle(
        'weave f into ref to int:\n'
        '  var xs as list of int is [1, 2, 3]\n'
        '  return sigil of xs at 0\n'
    )
    assert "pengu_banish_list(&xs)" not in c

    explicit = gen_bundle(
        'weave f into ref to int:\n'
        '  var xs as list of int is [1, 2, 3]\n'
        '  banish xs\n'
        '  return sigil of xs at 0\n'
    )
    assert "pengu_banish_list(&xs)" in explicit


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
    """Leak gate for the manual reassign loop: valgrind when present, else ASan.

    With manual memory the loop must free the previous list itself, so the
    program banishes before every overwrite and once more at the end.

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
        '    banish xs\n'
        '    set xs is [i, i + 1, i + 2]\n'
        '    set i is i + 1\n'
        '  banish xs\n'
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
