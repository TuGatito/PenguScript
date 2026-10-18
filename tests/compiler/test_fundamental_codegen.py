"""Generated-C checks for the four fundamental std modules.

These tests look at the *shape* of the emitted C (one `memcpy`-based append, no
allocation inside `count_ones`, an owned take for `finish`) and then compile the
bundle with every available C compiler under ``-Wall -Wextra -Werror``.  The
``-Wno-unused-function`` is the same concession `test_codegen_hygiene.py` makes:
the runtime and imported std modules intentionally emit inline helpers that a
particular program may not call.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SOURCE = """
import std.spark
import std.builder
import std.arena
import std.sourcemap
import std.bitset

rune Node:
    value as int
    next as ref to Node

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "hello"
    calling sb.append_int with -42
    calling sb.append_float with 1.5
    calling sb.append_bool with true
    var msg as string is calling sb.finish
    defer banish msg

    var a as Arena is calling Arena.new
    defer calling a.free
    defer banish a
    var n as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set n->value is 7
    var raw as ref to byte is calling a.alloc_str with msg
    var cstr as ref to frozen char is calling a.alloc_cstr with msg
    var nums as ref to int is calling arena_alloc of int with (sigil of a), 4
    set nums at 0 is 1
    calling a.reset

    var sm as SourceMap is calling SourceMap.from_source with msg
    defer banish sm
    var p as Position is calling sm.position_at with 0
    var span as Span is calling sm.span_at with 0, (calling sm.source_len)
    let (ps, pe) is calling sm.span_to_positions with span
    var line as string is calling sm.line_text with 1
    defer banish line

    var bs as BitSet is calling BitSet.new with 65
    defer banish bs
    calling bs.set with 0
    calling bs.toggle_all
    var anded as BitSet is calling bs.and_with with (sigil of bs)
    defer banish anded
    var inv as BitSet is calling bs.not
    defer banish inv
    var bits as list of int is calling bs.iter_set
    defer banish bits
    var view as slice of byte is calling bs.to_bytes
    var first as maybe int is calling bs.find_first_set
    banish first
    var ones as int is calling bs.count_ones
    calling spark.println with "{p.line} {ps.col} {pe.col} {ones} {view.length}"
    return 0
"""


def _build_bundle(pengu_cli, tmp_path) -> str:
    source = tmp_path / "fundamentals.pengu"
    source.write_text(_SOURCE, encoding="utf-8")
    bundle = tmp_path / "bundle.c"
    res = pengu_cli("build", "--entry", str(source), "--output", str(bundle))
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    return bundle.read_text(encoding="utf-8")


def _compile(c_code: str, tmp_path, compiler: str, extra: list[str]) -> None:
    bundle = tmp_path / "compile.c"
    bundle.write_text(c_code, encoding="utf-8")
    res = subprocess.run(
        [compiler, "-c", str(bundle), "-o", str(tmp_path / "out.o"),
         "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-Wno-unused-function",
         "-I", str(ROOT), "-I", str(ROOT / "build" / "include"), *extra],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, f"{compiler} rejected the bundle:\n{res.stdout}\n{res.stderr}"


def test_builder_uses_amortised_copy_and_owned_take(pengu_cli, tmp_path):
    c = _build_bundle(pengu_cli, tmp_path)
    assert "pengu_memoria_resize" in c, "append must grow with realloc"
    assert "memcpy" in c, "append must copy bytes with memcpy"
    assert "snprintf" in c, "append_int/append_float must format without a temporary string"
    assert "StringBuilder_take" in c or "_builder_take" in c, "finish must use the owned take"
    assert "StringBuilder_nexus" in c, "banish builder must release the buffer"


def test_arena_releases_blocks_and_uses_bump_pointers(pengu_cli, tmp_path):
    c = _build_bundle(pengu_cli, tmp_path)
    assert "Arena_alloc_aligned" in c
    assert "pengu_memoria_alloc" in c
    assert "pengu_banish_string" in c, "each block is an owned string and is released by free"
    assert "Arena_free" in c


def test_sourcemap_uses_binary_search_and_owned_substrings(pengu_cli, tmp_path):
    c = _build_bundle(pengu_cli, tmp_path)
    assert "SourceMap_position_at" in c
    body = c.split("Position SourceMap_position_at(SourceMap* self, int32_t offset) {", 1)[1].split("\n}", 1)[0]
    assert "lo" in body and "hi" in body, "position_at must binary-search line starts"
    assert "pengu_string_substring" in c


def test_bitset_operations_do_not_allocate(pengu_cli, tmp_path):
    c = _build_bundle(pengu_cli, tmp_path)
    body = c.split("int32_t BitSet_count_ones(BitSet* self) {", 1)[1].split("\n}", 1)[0]
    assert "malloc" not in body and "pengu_memoria_alloc" not in body, body
    assert "BitSet_and_with" in c
    assert "BitSet_not" in c
    assert "BitSet_to_bytes" in c


def test_generated_c_compiles_cleanly_with_every_compiler(pengu_cli, tmp_path):
    c = _build_bundle(pengu_cli, tmp_path)
    compilers = [p for p in (shutil.which("gcc"), shutil.which("clang")) if p]
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        # clang's -Wunused-function is already covered by the project-wide
        # `-Wno-unused-function`; -Werror is about real diagnostics here.
        _compile(c, tmp_path, cc, [])
