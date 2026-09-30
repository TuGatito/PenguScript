#!/usr/bin/env python3
"""Tests for Production-level Generics (Fase 1: Containers, bounds, cleanup, clone)."""

import shutil
import subprocess
from pathlib import Path

import pytest
from tests.conftest import check_error, check_ok, compile_run, requires_cc, requires_runtime, REPO


def test_bounds_missing_arithmetic_raises_e0049():
    """Bug 1: Arithmetic operator on TypeParam without 'Num' bound raises E0049."""
    src = """
weave bad shard T with a as T, b as T into T:
    return a + b
"""
    check_error(src, contains="E0049")


def test_bounds_missing_ordering_raises_e0049():
    """Ordering comparison on TypeParam without 'Ordo' bound raises E0049."""
    src = """
weave bad shard T with a as T, b as T into bool:
    return a < b
"""
    check_error(src, contains="E0049")


def test_bounds_missing_equality_raises_e0049():
    """Equality comparison on TypeParam without 'Par' bound raises E0049."""
    src = """
weave bad shard T with a as T, b as T into bool:
    return a == b
"""
    check_error(src, contains="E0049")


def test_bounds_satisfied_num():
    """Generic weave with 'where T: Num' passes checker."""
    src = """
weave add_generic shard T where T: Num with a as T, b as T into T:
    return a + b
"""
    check_ok(src)


def test_bounds_satisfied_ordo():
    """Generic weave with 'where T: Ordo' passes checker."""
    src = """
weave min_val shard T where T: Ordo with a as T, b as T into T:
    if a < b:
        return a
    return b
"""
    check_ok(src)


def test_bounds_satisfied_par():
    """Generic weave with 'where T: Par' passes checker."""
    src = """
weave is_same shard T where T: Par with a as T, b as T into bool:
    return a == b
"""
    check_ok(src)


@requires_cc
@requires_runtime
def test_generic_num_execution():
    """Compiles and runs generic sum with where T: Num on list of int."""
    pengu_file = REPO / "tests" / "test_generics" / "test_generic_num.pengu"
    src = pengu_file.read_text(encoding="utf-8")
    res = compile_run(src, tag="test_generic_num")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_nested_list_leak_execution():
    """Compiles and runs nested list and list of strings banishment."""
    pengu_file = REPO / "tests" / "test_generics" / "test_nested_list_leak.pengu"
    src = pengu_file.read_text(encoding="utf-8")
    res = compile_run(src, tag="test_nested_list_leak")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_nested_map_leak_execution():
    """Compiles and runs map of string to list of int with recursive banish."""
    pengu_file = REPO / "tests" / "test_generics" / "test_nested_map_leak.pengu"
    src = pengu_file.read_text(encoding="utf-8")
    res = compile_run(src, tag="test_nested_map_leak")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_valgrind_memory_leaks_clean(tmp_path):
    """Verifies that nested list banishment has zero memory leaks using valgrind if available."""
    valgrind = shutil.which("valgrind")
    if not valgrind:
        pytest.skip("valgrind is not installed on this system")

    pengu_file = REPO / "tests" / "test_generics" / "test_nested_list_leak.pengu"
    src = pengu_file.read_text(encoding="utf-8")

    from pengu_project import PenguBuilder, ProjectConfig
    from tests.conftest import runtime_link_flags, runtime_tail_flags, BUILD_DIR, BUILD_INCLUDE, BUILD_LIB

    entry = tmp_path / "leak_test.pengu"
    entry.write_text(src, encoding="utf-8")
    cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file=str(tmp_path / "bundle.c"))

    exe = tmp_path / "bin"
    cmd = [
        "gcc", str(bundle_path),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}", "-g",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=int-conversion"
    ] + runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]

    c_res = subprocess.run(cmd, capture_output=True, text=True)
    assert c_res.returncode == 0, f"Compilation failed: {c_res.stderr}"

    vg_cmd = [
        valgrind,
        "--leak-check=full",
        "--error-exitcode=42",
        "--show-leak-kinds=all",
        str(exe)
    ]
    vg_res = subprocess.run(vg_cmd, capture_output=True, text=True)
    assert vg_res.returncode == 0, f"Valgrind detected memory leak:\n{vg_res.stderr}\n{vg_res.stdout}"


def test_infinite_type_size_raises_e0050():
    """Bug 9: Recursive value types without indirection raise E0050."""
    check_error("""
rune BadDirect:
    b as BadDirect
""", contains="E0050")

    check_error("""
rune BadGeneric shard T:
    val as T
    next as BadGeneric of T
""", contains="E0050")

    check_error("""
rune CycleA:
    b as CycleB

rune CycleB:
    a as CycleA
""", contains="E0050")


def test_duplicate_concept_binding_raises_e0047():
    """Bug 10: Duplicate concept binding for the same type raises E0047."""
    check_error("""
concept Showable:
    weave show with self as self into string

bind int with Showable:
    weave show with self as self into string:
        return "int"

bind int with Showable:
    weave show with self as self into string:
        return "int again"
""", contains="E0047")


@requires_cc
@requires_runtime
def test_auto_referential_generic_node_execution():
    """Bug 3: Auto-referential generic rune with maybe ref to Node of T executes correctly."""
    src = """rune Node shard T:
    val as T
    next as maybe ref to Node of T

weave main into int:
    var n2 as Node of int with:
        set .val is 20
        set .next is maybe none

    var n1 as Node of int with:
        set .val is 10
        set .next is some (sigil of n2)

    var next_ref as ref to Node of int is n1.next or:
        return 1

    if n1.val + next_ref->val == 30:
        return 0
    return 2
"""
    res = compile_run(src, tag="test_auto_ref_node")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_derive_par_ordo_execution():
    """Derive Par and Ordo on concrete rune generates working ==, !=, < operators."""
    src = """rune Point derive Par, Ordo:
    x as int
    y as int

weave main into int:
    var p1 as Point with:
        set .x is 1
        set .y is 2
    var p2 as Point with:
        set .x is 1
        set .y is 2
    var p3 as Point with:
        set .x is 2
        set .y is 1

    if not (p1 == p2):
        return 1
    if p1 != p2:
        return 2
    if not (p1 < p3):
        return 3
    return 0
"""
    res = compile_run(src, tag="test_derive_point")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_derive_generic_par_ordo_execution():
    """Derive Par and Ordo on generic rune propagates bounds and generates comparison operators."""
    src = """rune Point shard T derive Par, Ordo:
    x as T
    y as T

weave main into int:
    var p1 as Point of int with:
        set .x is 10
        set .y is 20
    var p2 as Point of int with:
        set .x is 10
        set .y is 20
    var p3 as Point of int with:
        set .x is 20
        set .y is 10

    if not (p1 == p2):
        return 1
    if p1 != p2:
        return 2
    if not (p1 < p3):
        return 3
    return 0
"""
    res = compile_run(src, tag="test_derive_generic_point")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_generic_box_of_box_execution():
    """Generic rune containing another generic rune instantiation (Box of Box of int)."""
    src = """rune Box shard T:
    val as T

weave main into int:
    var inner as Box of int with:
        set .val is 99
    var outer as Box of (Box of int) with:
        set .val is inner
    if outer.val.val == 99:
        return 0
    return 1
"""
    res = compile_run(src, tag="test_box_of_box")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_generic_method_with_separate_shard_execution():
    """Generic method with its own shard U inside generic enchanting Box shard T."""
    src = """rune Box shard T:
    val as T

enchanting Box shard T:
    weave get into T:
        return self->val

    weave map shard U with f as (weave with T into U) into Box of U:
        var res as Box of U with:
            set .val is calling f with self->val
        return res

weave double_val with x as int into int:
    return x * 2

weave main into int:
    var b as Box of int with:
        set .val is 21
    var b2 as Box of int is calling b.map with double_val
    if b2.val == 42:
        return 0
    return 1
"""
    res = compile_run(src, tag="test_box_map")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_generic_ritual_method_execution():
    """Generic ritual (static) method on generic rune Box.create with inferred type arg."""
    src = """rune Box shard T:
    val as T

enchanting Box shard T:
    weave ritual create with v as T into Box of T:
        var b as Box of T with:
            set .val is v
        return b

weave main into int:
    var b as Box of int is calling Box.create with 100
    if b.val == 100:
        return 0
    return 1
"""
    res = compile_run(src, tag="test_box_create")
    assert res.returncode == 0

