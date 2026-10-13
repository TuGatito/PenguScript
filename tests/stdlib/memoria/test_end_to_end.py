"""``std.memoria`` — end to end.

Three levels: the module's own embedded ``test`` blocks, a realistic dynamic
stack built on ``alloc_array``/``resize_array``/``banish``, and the emitted
symbols (one monomorphized C function per element type).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/memoria/test_end_to_end.py`` -> `memoria` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


def test_module_self_tests_pass():
    """``pengu test --entry std/memoria.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "memoria.pengu")],
        capture_output=True, text=True, timeout=600,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 51 test(s) passed." in res.stdout, res.stdout


def test_dynamic_stack(compile_and_run):
    """A growable int stack: push past capacity, then pop in LIFO order."""
    out = compile_and_run("""
import std.spark
import std.memoria

rune Stack:
    data as ref to int
    len as usize
    cap as usize

weave stack_new with cap as usize into Stack:
    var data as ref to int is calling memoria.alloc_array of int with cap
    return with data is data, len is 0, cap is cap

weave stack_push with s as ref to Stack, v as int into void:
    if s->len >= s->cap:
        let old is s->cap
        set s->cap is old * 2
        set s->data is calling memoria.resize_array of int with s->data, old, s->cap
    var data as ref to int is s->data
    var idx as usize is s->len
    set data at idx is v
    set s->len is s->len + 1

weave stack_pop with s as ref to Stack into int:
    set s->len is s->len - 1
    var data as ref to int is s->data
    var idx as usize is s->len
    return data at idx

weave main into int:
    var s as Stack is calling stack_new with 2
    defer banish s.data

    var i as int is 0
    while i < 10:
        calling stack_push with (sigil of s), i * 10
        set i is i + 1

    # LIFO: 90, 80, 70
    calling spark.println with "{calling stack_pop with (sigil of s)}"
    calling spark.println with "{calling stack_pop with (sigil of s)}"
    calling spark.println with "{calling stack_pop with (sigil of s)}"
    calling spark.println with "{s.len}"
    return 0
""")
    assert "90" in out, out
    assert "80" in out, out
    assert "70" in out, out
    assert "7" in out, out


def test_monomorphized_symbols(tmp_path):
    """Every method instantiates a plain C function named ``memoria_<m>_<T>``."""
    source = tmp_path / "memoria_symbols.pengu"
    source.write_text(
        "import std.memoria\n"
        "weave main into int:\n"
        "    var p as ref to int is calling memoria.alloc of int\n"
        "    var b as ref to byte is calling memoria.alloc_array of byte with 4\n"
        "    var f as ref to float is calling memoria.alloc_array of float with 2\n"
        "    var r as ref to int is calling memoria.resize_array of int with p, 1, 2\n"
        "    var m as maybe ref to int is calling memoria.try_resize_array of int with r, 2, 3\n"
        "    calling memoria.copy of int with r, r, 1\n"
        "    calling memoria.fill of float with f, 1.0, 2\n"
        "    calling memoria.zero of int with r, 1\n"
        "    calling memoria.swap of byte with b, b\n"
        "    let c is calling memoria.compare of int with r, r, 1\n"
        "    let n is calling memoria.bytes_for of f64 with 2\n"
        "    banish f\n"
        "    banish b\n"
        "    banish m\n"
        "    banish r\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "expand", str(source)],
        capture_output=True, text=True, timeout=180,
        cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, f"expand failed:\n{res.stdout}\n{res.stderr}"
    bundle = res.stdout
    for symbol in (
        "memoria_alloc_int",
        "memoria_alloc_array_byte",
        "memoria_alloc_array_float",
        "memoria_resize_array_int",
        "memoria_try_resize_array_int",
        "memoria_copy_int",
        "memoria_fill_float",
        "memoria_zero_int",
        "memoria_swap_byte",
        "memoria_compare_int",
        "memoria_bytes_for_f64",
    ):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), (
            f"{symbol} missing from the bundle"
        )
    # The runtime helpers keep their `pengu_` prefix; the Pengu symbols do not.
    assert "pengu_memoria_alloc" in bundle
    assert "pengu_memoria_resize" in bundle
